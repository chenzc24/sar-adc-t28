"""Selected native-pin reference comparison. Python2.7/3; no slew rescaling."""
from __future__ import print_function
import gzip
import hashlib
import math
import os
import re
import struct


def unit(value,kind):
    if kind=='capacitance' and isinstance(value,list) and len(value)==2:value=str(value[0])+str(value[1])
    if not isinstance(value,type(u'')) and not isinstance(value,str):return None
    match=re.match(r'^\s*([0-9.+eE-]+)\s*([a-zA-Z]+)\s*$',value)
    if not match:return None
    factors={'s':1.,'ms':1e-3,'us':1e-6,'ns':1e-9,'ps':1e-12,'fs':1e-15} if kind=='time' else {'f':1.,'mf':1e-3,'uf':1e-6,'nf':1e-9,'pf':1e-12,'ff':1e-15}
    try:return float(match.group(1))*factors[match.group(2).lower()]
    except (ValueError,KeyError):return None


def pin_objects(semantic):
    cell=semantic.get('target_cell') or {}
    return {p['arguments'][0]:p for p in cell.get('groups',[]) if p['kind']=='pin'}


def threshold_basis(semantic):
    library=semantic['library_attributes'];cell=(semantic.get('target_cell') or {}).get('attributes',{})
    result={}
    for name,obj in pin_objects(semantic).items():
        if name not in ['CP','D','CDN']:continue
        pin=obj['attributes'];result[name]={}
        for edge in ['rise','fall']:
            record={}
            for key in ['slew_lower_threshold_pct_'+edge,'slew_upper_threshold_pct_'+edge,'slew_derate_from_library']:
                if key in pin:record[key]=dict(value=pin[key],source='pin')
                elif key in cell:record[key]=dict(value=cell[key],source='cell')
                elif key in library:record[key]=dict(value=library[key],source='library')
                else:record[key]=dict(value=None,source='not_explicit_in_selected_scope')
            low=record['slew_lower_threshold_pct_'+edge]['value'];high=record['slew_upper_threshold_pct_'+edge]['value']
            record['raw_threshold_interval_available']=isinstance(low,(int,float)) and isinstance(high,(int,float)) and 0<low<high<100
            record['derate_applied']=False
            result[name][edge]=record
    return result


def crossing(a,b,index,fraction):
    x=a[index]-fraction*a[1];y=b[index]-fraction*b[1]
    direction=1 if x<0<=y else -1 if x>0>=y else 0
    if not direction:return None
    return dict(time_s=a[0]-x*(b[0]-a[0])/(y-x),direction=direction,native_bracket_s=[a[0],b[0]])


def reference_edges(path,meta,basis):
    pack=struct.Struct('<5d');levels={};hits={}
    for name in ['CP','D','CDN']:
        wanted=set([.5])
        for edge,record in basis.get(name,{}).items():
            if record['raw_threshold_interval_available']:
                wanted.add(record['slew_lower_threshold_pct_'+edge]['value']/100.)
                wanted.add(record['slew_upper_threshold_pct_'+edge]['value']/100.)
        levels[name]=wanted;hits[name]={f:[] for f in wanted}
    h=hashlib.sha256();count=0;previous=None;last=None
    with gzip.open(path,'rb') as source:
        while True:
            blob=source.read(pack.size)
            if not blob:break
            if len(blob)!=pack.size:raise ValueError('Incomplete compact native reference row')
            h.update(blob);row=pack.unpack(blob);count+=1;last=row[0]
            if row[1]<=0 or any(math.isnan(v) or math.isinf(v) for v in row):raise ValueError('Invalid native reference voltage/time')
            if previous is not None:
                if row[0]<=previous[0]:raise ValueError('Nonincreasing compact reference')
                for index,name in enumerate(['CP','D','CDN'],2):
                    for fraction in levels[name]:
                        event=crossing(previous,row,index,fraction)
                        if event:
                            hits[name][fraction].append(event)
                            if len(hits[name][fraction])>1024:raise ValueError('Native crossing-reference bound exceeded')
            elif row[0]!=0:raise ValueError('Compact reference must start at0')
            previous=row
    if count!=meta['native_points'] or count*pack.size!=meta['decoded_bytes'] or h.hexdigest()!=meta['decoded_sha256'] or abs(last-20e-9)>1e-15:raise ValueError('Native compact reference identity/count mismatch')
    result={}
    for name in ['CP','D','CDN']:
        result[name]={}
        for edge,direction in [('rise',1),('fall',-1)]:
            record=basis.get(name,{}).get(edge,{})
            if not record.get('raw_threshold_interval_available'):
                result[name][edge]=dict(status='unknown_library_threshold_basis',events=[]);continue
            low=record['slew_lower_threshold_pct_'+edge]['value']/100.;high=record['slew_upper_threshold_pct_'+edge]['value']/100.
            events=[]
            for half in hits[name][.5]:
                if half['direction']!=direction:continue
                lower=[v for v in hits[name][low] if v['direction']==direction and abs(v['time_s']-half['time_s'])<=.25e-9]
                upper=[v for v in hits[name][high] if v['direction']==direction and abs(v['time_s']-half['time_s'])<=.25e-9]
                item=dict(halfrail=half,lower=None,upper=None,raw_interval_s=None,status='missing_or_ambiguous_threshold_crossing')
                if len(lower)==len(upper)==1:
                    interval=(upper[0]['time_s']-lower[0]['time_s'])*direction
                    item.update(lower=lower[0],upper=upper[0],raw_interval_s=interval if interval>=0 else None,
                        status='measured_raw_threshold_interval' if interval>=0 else 'unexpected_crossing_order')
                events.append(item)
            values=[v['raw_interval_s'] for v in events if v['raw_interval_s'] is not None]
            result[name][edge]=dict(status='raw_measurement_only_no_derate_applied',events=events,
                raw_range_s=[min(values),max(values)] if values else None,native_event_count=len(events))
    return result


def compare(semantic,references,folder):
    attrs=semantic['library_attributes'];pins=pin_objects(semantic)
    time_scale=unit(attrs.get('time_unit'),'time');cap_scale=unit(attrs.get('capacitive_load_unit'),'capacitance')
    basis=threshold_basis(semantic);measured={}
    for case,meta in references['cases'].items():measured[case]=reference_edges(os.path.join(folder,meta['file']),meta,basis)
    conditions=dict(time_scale_s=time_scale,capacitance_scale_F=cap_scale,library_attributes=attrs,
        threshold_basis=basis,pin_limits={},actual_edges=measured,axis_relations=[],
        slew_derating_semantics_applied=False,effective_actual_Q_load_F=None,
        actual_load_note='Exact unchanged transistor/RC first-hop networks; no fitted effective lumped output capacitance.',
        table_axis_is_not_absolute_reliability_limit=True,model_pairing_proven=False,whole_circuit_qualified=None)
    for name,obj in pins.items():
        limit={}
        for key,scale,default in [('max_transition',time_scale,'default_max_transition'),('max_capacitance',cap_scale,'default_max_capacitance')]:
            if key in obj['attributes']:value=obj['attributes'][key];source='pin'
            elif key in (semantic.get('target_cell') or {}).get('attributes',{}):value=semantic['target_cell']['attributes'][key];source='cell'
            else:value=attrs.get(default);source='library_explicit_default' if default in attrs else 'unknown'
            limit[key]=dict(raw=value,SI_value=value*scale if isinstance(value,(float,int)) and scale is not None else None,source=source)
        limit['declared_pin_attributes']=obj['attributes'];conditions['pin_limits'][name]=limit
    for arc_index,arc in enumerate(semantic['timing_arcs']):
        related=str(arc['attributes'].get('related_pin','')).split();timing=str(arc['attributes'].get('timing_type',''))
        related_edge='rise' if timing.endswith('_rising') or timing=='rising_edge' else 'fall' if timing.endswith('_falling') or timing=='falling_edge' else None
        for table in arc['tables']:
            values=table.get('values_summary')
            if values and time_scale is not None:table['values_time_extrema_s']=[values['min']*time_scale,values['max']*time_scale]
            for axis,vector in table['effective_axes'].items():
                variable=table['variables'].get(axis);pin=None;edge=None
                if variable=='constrained_pin_transition':
                    pin=arc['pin'];edge='rise' if table['kind']=='rise_constraint' else 'fall' if table['kind']=='fall_constraint' else None
                elif variable in ['related_pin_transition','input_net_transition']:
                    pin=related[0] if len(related)==1 else None;edge=related_edge
                record=dict(arc_index=arc_index,pin=arc['pin'],related_pin=arc['attributes'].get('related_pin'),
                    timing_type=timing,when=arc['attributes'].get('when'),table=table['kind'],template=table['template'],
                    axis=axis,variable=variable,axis_raw_values=vector,mapped_reference_pin=pin,mapped_edge=edge)
                if variable and 'capacitance' in variable:
                    record.update(axis_range_F=[min(vector)*cap_scale,max(vector)*cap_scale] if vector and cap_scale is not None else None,
                        comparison='actual_effective_output_load_unknown')
                elif pin in basis and vector and time_scale is not None:
                    bounds=[min(vector)*time_scale,max(vector)*time_scale];relations={}
                    for case,case_edges in measured.items():
                        directions=[edge] if edge else ['rise','fall'];ranges=[case_edges[pin][e].get('raw_range_s') for e in directions]
                        ranges=[v for v in ranges if v]
                        observed=[min(v[0] for v in ranges),max(v[1] for v in ranges)] if ranges else None
                        relations[case]=dict(raw_measured_interval_range_s=observed,
                            raw_interval_below_axis_min=observed[0]<bounds[0] if observed else None,
                            raw_interval_above_axis_max=observed[1]>bounds[1] if observed else None,
                            interpretation='raw interval vs declared axis only; no STA slew-derate normalization or timing qualification')
                    record.update(axis_range_s=bounds,raw_interval_relations=relations)
                else:record['comparison']='unknown_axis_units_or_reference_mapping'
                conditions['axis_relations'].append(record)
    return conditions
