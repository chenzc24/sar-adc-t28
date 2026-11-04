"""Bounded selected Liberty semantics, Python2.7/3. No CCS numeric expansion."""
from __future__ import print_function
import math
import re

CHUNK=65536
STRUCT=re.compile(br'[{}"/]')
QUOTE=re.compile(br'["\\]')
SPACE=re.compile(br'[\s\\]+')
WORD=re.compile(br'[^\s{}():;,"\\/]+')
NUMBER=re.compile(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?')


class ParseError(Exception):pass
class SemanticBound(Exception):pass


class Lexer(object):
    def __init__(self,source,limits):
        self.source=source;self.limits=limits;self.buf=b'';self.pos=0;self.total=0;self.line=1;self.look=None
    def more(self):
        self.buf=self.buf[self.pos:];self.pos=0
        chunk=self.source.read_some(CHUNK)
        self.buf+=chunk
        return bool(chunk)
    def need(self,n=1):
        while len(self.buf)-self.pos<n:
            if not self.more():return len(self.buf)-self.pos>=n
        return True
    def advance(self,n):
        self.line+=self.buf[self.pos:self.pos+n].count(b'\n');self.pos+=n;self.total+=n
    def comment(self):
        if not self.need(2) or self.buf[self.pos:self.pos+2] not in [b'/*',b'//']:return False
        block=self.buf[self.pos:self.pos+2]==b'/*';self.advance(2)
        while True:
            mark=self.buf.find(b'*/' if block else b'\n',self.pos)
            if mark>=0:
                self.advance(mark-self.pos+(2 if block else 1));return True
            left=len(self.buf)-self.pos
            self.advance(max(0,left-(1 if block else 0)))
            if not self.more():
                if block:raise ParseError('Unclosed comment')
                return True
    def quoted(self,capture):
        if not self.need() or self.buf[self.pos:self.pos+1]!=b'"':raise ParseError('Expected quote')
        self.advance(1);parts=[];size=0
        while True:
            if not self.need():raise ParseError('Unclosed quoted string')
            match=QUOTE.search(self.buf,self.pos)
            stop=match.start() if match else len(self.buf)
            blob=self.buf[self.pos:stop];self.advance(len(blob))
            if capture:
                parts.append(blob);size+=len(blob)
                if size>self.limits['selected_string_max_bytes']:raise SemanticBound('selected_string_bytes')
            if not match:continue
            char=self.buf[self.pos:self.pos+1];self.advance(1)
            if char==b'"':return b''.join(parts).decode('utf-8','replace') if capture else None
            if not self.need():raise ParseError('Incomplete string escape')
            char=self.buf[self.pos:self.pos+1];self.advance(1)
            if char==b'\r' and self.need() and self.buf[self.pos:self.pos+1]==b'\n':self.advance(1)
            elif char!=b'\n' and capture:
                parts.append(char);size+=1
                if size>self.limits['selected_string_max_bytes']:raise SemanticBound('selected_string_bytes')
    def skip_space(self):
        while self.need():
            match=SPACE.match(self.buf,self.pos)
            if match:self.advance(match.end()-self.pos);continue
            if self.comment():continue
            return
    def raw_token(self):
        self.skip_space()
        if not self.need():return ('eof','',self.total)
        start=self.total;char=self.buf[self.pos:self.pos+1]
        if char==b'"':return ('string',self.quoted(True),start)
        if char in [b'{',b'}',b'(',b')',b':',b';',b',']:
            self.advance(1);return ('punct',char.decode('ascii'),start)
        pieces=[];size=0
        while self.need():
            match=WORD.match(self.buf,self.pos)
            if not match:break
            blob=match.group(0);pieces.append(blob);size+=len(blob);self.advance(len(blob))
            if size>4096:raise SemanticBound('identifier_bytes')
            if self.pos<len(self.buf):break
        if not pieces:raise ParseError('Unexpected syntax at byte'+str(self.total))
        return ('word',b''.join(pieces).decode('utf-8','replace'),start)
    def peek(self):
        if self.look is None:self.look=self.raw_token()
        return self.look
    def take(self):
        out=self.peek();self.look=None;return out
    def expect(self,value):
        tok=self.take()
        if tok[:2]!=('punct',value):raise ParseError('Expected '+value+' at byte'+str(tok[2]))
    def skip_group(self):
        if self.look is not None:raise ParseError('Internal skip lookahead mismatch')
        depth=1
        while depth:
            if not self.need():raise ParseError('Unclosed skipped group')
            match=STRUCT.search(self.buf,self.pos)
            if not match:self.advance(len(self.buf)-self.pos);continue
            self.advance(match.start()-self.pos);char=self.buf[self.pos:self.pos+1]
            if char==b'"':self.quoted(False)
            elif char==b'/' and self.comment():continue
            else:
                self.advance(1)
                if char==b'{':depth+=1
                elif char==b'}':depth-=1
                if depth>64:raise SemanticBound('group_nesting')
    def skip_statement(self):
        if self.look is not None:raise ParseError('Internal statement lookahead mismatch')
        depth=0
        while self.need():
            char=self.buf[self.pos:self.pos+1]
            if char==b'"':self.quoted(False)
            elif char==b'/' and self.comment():continue
            else:
                self.advance(1)
                if char==b'(':depth+=1
                elif char==b')':depth-=1
                elif char==b';' and depth==0:return
                elif char in [b'{',b'}']:raise ParseError('Unexpected brace in attribute')
        raise ParseError('Unclosed attribute')


LIB_ATTR=set(['time_unit','voltage_unit','current_unit','pulling_resistance_unit','leakage_power_unit',
    'capacitive_load_unit','delay_model','revision','date','nom_voltage','nom_temperature','nom_process',
    'default_operating_conditions','slew_lower_threshold_pct_rise','slew_upper_threshold_pct_rise',
    'slew_lower_threshold_pct_fall','slew_upper_threshold_pct_fall','input_threshold_pct_rise',
    'input_threshold_pct_fall','output_threshold_pct_rise','output_threshold_pct_fall','slew_derate_from_library',
    'default_max_transition','default_max_capacitance','default_input_pin_cap','default_output_pin_cap','default_inout_pin_cap'])
THRESHOLD_ATTR=set(name for name in LIB_ATTR if 'threshold_pct_' in name or name=='slew_derate_from_library')
PIN_ATTR=set(['direction','clock','capacitance','rise_capacitance','fall_capacitance','rise_capacitance_range',
    'fall_capacitance_range','max_capacitance','min_capacitance','max_transition','min_transition',
    'min_pulse_width_high','min_pulse_width_low','minimum_period',
    'related_power_pin','related_ground_pin','function','state_function','input_voltage','output_voltage'])|LIB_ATTR
ARC_ATTR=set(['related_pin','timing_type','timing_sense','when','sdf_cond','sdf_cond_start','sdf_cond_end',
    'related_output_pin','interdependence_id','mode','default_timing'])
TABLES=set(['cell_rise','cell_fall','rise_transition','fall_transition','rise_constraint','fall_constraint',
    'retaining_rise','retaining_fall','retain_rise_slew','retain_fall_slew'])


def scalar(tokens):
    if len(tokens)==1:
        value=tokens[0][1]
        if tokens[0][0]=='string':return value
        if value in ['true','false']:return value=='true'
        if NUMBER.match(value) and NUMBER.match(value).group(0)==value:
            value=float(value)
            if math.isnan(value) or math.isinf(value):raise ParseError('Nonfinite numeric metadata')
            return value
        return value
    return ' '.join(t[1] for t in tokens)


def numbers(args,limit):
    out=[]
    for arg in args:
        for value in re.split(r'[,\s]+',str(arg).strip()):
            if not value:continue
            try:number=float(value)
            except ValueError:raise ParseError('Invalid numeric table metadata')
            if math.isnan(number) or math.isinf(number):raise ParseError('Nonfinite table metadata')
            out.append(number)
            if len(out)>limit:raise SemanticBound('selected_table_numbers')
    return out


class Semantics(object):
    def __init__(self,source,cfg):
        self.cfg=cfg;self.lex=Lexer(source,cfg);self.groups=0
        self.result=dict(library=None,library_attributes={},templates={},operating_conditions={},voltage_definitions={},target_cell=None,
            skipped_groups=0,selected_groups=0,duplicate_attributes=[],parser_complete=False)
    def args(self):
        self.lex.expect('(');out=[];current=[];total=0
        while True:
            token=self.lex.take()
            if token[0]=='eof':raise ParseError('Unclosed arguments')
            if token[:2] in [('punct',','),('punct',')')]:
                if current:out.append(scalar(current));current=[]
                if token[1]==')':return out
            else:
                current.append(token);total+=len(token[1])
                if total>self.cfg['selected_string_max_bytes']:raise SemanticBound('selected_argument_bytes')
    def attr(self):
        tokens=[];size=0
        while True:
            tok=self.lex.take()
            if tok[:2]==('punct',';'):return scalar(tokens)
            if tok[0]=='eof' or tok[:2] in [('punct','{'),('punct','}')]:raise ParseError('Unclosed scalar attribute')
            tokens.append(tok);size+=len(tok[1])
            if size>self.cfg['selected_string_max_bytes']:raise SemanticBound('selected_attribute_bytes')
    def allowed(self,context,name):
        if context=='library':return name in LIB_ATTR
        if context=='pin':return name in PIN_ATTR
        if context=='timing':return name in ARC_ATTR
        if context=='cell':return name in ['cell_footprint','max_transition','max_capacitance','dont_use'] or name in THRESHOLD_ATTR
        if context=='ff':return name in ['clocked_on','clocked_on_also','next_state','clear','preset','clear_preset_var1','clear_preset_var2']
        if context=='template':return name.startswith(('variable_','index_'))
        if context=='table':return name.startswith('index_') or name=='values'
        return context in ['operating_conditions','voltage']
    def mode(self,context,name,args):
        if context=='library':
            if name=='cell' and args==[self.cfg['target_cell']]:return 'cell'
            if name=='lu_table_template':return 'template'
            if name=='operating_conditions':return 'operating_conditions'
            if name in ['input_voltage','output_voltage']:return 'voltage'
        if context=='cell':
            if name=='pin' and len(args)==1 and args[0] in self.cfg['target_pins']:return 'pin'
            if name in ['ff','ff_bank']:return 'ff'
        if context=='pin' and name=='timing':return 'timing'
        if context=='timing' and name in TABLES:return 'table'
        return None
    def add_attr(self,obj,name,value):
        if len(obj['attributes'])>=256:raise SemanticBound('selected_attributes')
        if name in obj['attributes']:self.result['duplicate_attributes'].append(dict(group=obj['kind'],name=name))
        if name.startswith('index_'):value=numbers(value if isinstance(value,list) else [value],128)
        elif name=='values':
            values=numbers(value if isinstance(value,list) else [value],self.cfg['table_value_max_count'])
            if not values:raise ParseError('Empty selected numeric table')
            value=dict(count=len(values),min=min(values) if values else None,max=max(values) if values else None,
                matrix_not_retained=True)
        obj['attributes'][name]=value
    def group(self,context,name,args,offset,depth=0):
        self.groups+=1
        if self.groups>self.cfg['selected_group_max_count'] or depth>32:raise SemanticBound('selected_group_count_or_depth')
        obj=dict(kind=name,arguments=args,member_header_offset=offset,attributes={},groups=[])
        while True:
            token=self.lex.take()
            if token[:2]==('punct','}'):return obj
            if token[:2]==('punct',';'):continue
            if token[0]!='word':raise ParseError('Expected attribute/group name at byte'+str(token[2]))
            key=token[1];nexttok=self.lex.take()
            if nexttok[:2]==('punct',':'):
                if self.allowed(context,key):self.add_attr(obj,key,self.attr())
                else:self.lex.skip_statement()
            elif nexttok[:2]==('punct','('):
                self.lex.look=nexttok;arguments=self.args();end=self.lex.take()
                if end[:2]==('punct',';'):
                    if self.allowed(context,key):self.add_attr(obj,key,arguments)
                elif end[:2]==('punct','{'):
                    mode=self.mode(context,key,arguments)
                    if mode:
                        child=self.group(mode,key,arguments,token[2],depth+1);self.result['selected_groups']+=1
                        if context=='library':
                            if mode=='cell':
                                if self.result['target_cell'] is not None:raise ParseError('Duplicate target cell')
                                self.result['target_cell']=child
                            elif mode=='template':self.result['templates'][str(arguments[0])]=child
                            elif mode=='operating_conditions':self.result['operating_conditions'][str(arguments[0])]=child
                            else:self.result['voltage_definitions'][key+':'+str(arguments[0])]=child
                        else:obj['groups'].append(child)
                    else:self.lex.skip_group();self.result['skipped_groups']+=1
                else:raise ParseError('Expected group opening or complex-attribute end')
            else:raise ParseError('Expected colon or argument list')
    def parse(self):
        token=self.lex.take()
        if token[:2]!=('word','library'):raise ParseError('Expected one Liberty library group')
        args=self.args();self.lex.expect('{');self.result['library']=args[0] if args else None
        library=self.group('library','library',args,token[2]);self.result['library_attributes']=library['attributes']
        if self.lex.take()[0]!='eof':raise ParseError('Extra syntax after Liberty library')
        self.result['parser_complete']=True;self.result['member_semantic_bytes_consumed']=self.lex.total
        return resolve(self.result)


def resolve(result):
    cell=result['target_cell'];refs=set();arcs=[]
    if cell:
        for pin in cell['groups']:
            if pin['kind']!='pin':continue
            for group in pin['groups']:
                if group['kind']!='timing':continue
                arc=dict(pin=pin['arguments'][0],attributes=group['attributes'],tables=[])
                for table in group['groups']:
                    template=str(table['arguments'][0]) if table['arguments'] else None
                    if template and template!='scalar':refs.add(template)
                    definition=result['templates'].get(template)
                    attrs=definition['attributes'] if definition else {}
                    effective={};sources={};variables={}
                    for n in ['1','2','3']:
                        axis='index_'+n;variable='variable_'+n
                        if axis in table['attributes']:effective[n]=table['attributes'][axis];sources[n]='arc_override'
                        elif axis in attrs:effective[n]=attrs[axis];sources[n]='template'
                        if variable in attrs:variables[n]=attrs[variable]
                    values=table['attributes'].get('values');count=1
                    for vector in effective.values():count*=len(vector)
                    arc['tables'].append(dict(kind=table['kind'],template=template,template_resolved=bool(definition) or template=='scalar',
                        variables=variables,effective_axes=effective,axis_sources=sources,values_summary=values,
                        value_count_matches_axes=values['count']==count if values else None,
                        member_header_offset=table['member_header_offset']))
                arcs.append(arc)
    result['timing_arcs']=arcs;result['referenced_templates']={name:result['templates'][name] for name in refs if name in result['templates']}
    result['unresolved_template_references']=sorted(refs-set(result['templates']))
    result.pop('templates')
    return result
