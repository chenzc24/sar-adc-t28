"""Stream named MM65 fields independently; missing values are explicit, never0."""
from __future__ import print_function
import hashlib,json,math,os,re,struct
from stream_gzip import GzipWriter


def norm(s):return s.replace('\\','').lower()
def finite(x):return not math.isnan(x) and not math.isinf(x)
def quoted(line):
    m=re.match(r'^"([^"]+)"\s*(.*)$',line)
    return (m.group(1),m.group(2)) if m else (None,None)
def explicit_unit(line):
    m=re.search(r'"units?"\s*(?:STRING\s+)?"([^"]+)"',line)
    return m.group(1) if m else None
def scale(unit,family):
    m=re.match(r'^([afpnumkMGT]?)('+family+r')$',unit or '')
    if not m:return None
    return {'a':1e-18,'f':1e-15,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'':1.,'k':1e3,'M':1e6,'G':1e9,'T':1e12}[m.group(1)]


def capture(path,output,cfg):
    fields=cfg['fields'];refs=cfg['reference_signals'];wanted=dict((k,norm(v['save'])) for k,v in fields.items())
    wanted.update((k,norm(v['save'])) for k,v in refs.items())
    labels=list(cfg['field_order'])+list(cfg['reference_order']);columns=['time']+labels
    types={};traces={};aliases={};selected={};metadata={};values={};seen=set();group=None;prop=None
    section=None;sweep=None;now=None;previous=None;ended=False;points=0;invalid=[];snapshots={};maxgap=0.
    stats={k:dict(valid_native_points=0,unavailable_native_points=0,invalid_updates=0,min_raw=None,max_raw=None) for k in fields}
    digest=hashlib.sha256();writer=GzipWriter(os.path.join(output,'fields.native.bin.gz'),cfg['compressed_field_cap_bytes'])
    pack=struct.Struct('<'+'d'*len(columns))
    def make_snapshot(at,a,b):
        tm0,va=a;tm1,vb=b
        result={}
        for key in labels:
            x=va.get(key);y=vb.get(key)
            if at==tm0:v=x
            elif at==tm1:v=y
            else:v=None if x is None or y is None else x+(y-x)*(at-tm0)/(tm1-tm0)
            result[key]=v
        op={k:dict(raw_value=result[k],reported_unit=metadata[k]['reported_unit'],
            scale_to_SI=metadata[k]['scale_to_SI'],SI_value=(result[k]*metadata[k]['scale_to_SI'] if result[k] is not None and metadata[k]['scale_to_SI'] is not None else None)) for k in fields}
        def difference(a,b):return result[a]-result[b] if result[a] is not None and result[b] is not None else None
        vds=difference('node_d','node_s');vgs=difference('node_g','node_s')
        comparisons={}
        for key,node in [('vds',vds),('vgs',vgs)]:
            model=op[key]['SI_value'];raw=op[key]['raw_value']
            comparisons[key]=dict(node_difference_V=node,reported_SI_value=model,
                reported_minus_node_V=model-node if model is not None and node is not None else None,
                raw_number_minus_node_number=raw-node if raw is not None and node is not None else None,
                unit_qualified=metadata[key]['scale_to_SI'] is not None,sign_or_internal_voltage_convention_not_assigned=True)
        for key in ['ids','id']:
            model=op[key]['SI_value'];total=result['total_d']
            comparisons[key]=dict(named_reported_SI_value=model,total_terminal_D_A=total,
                numerical_difference_A=model-total if model is not None and total is not None else None,
                pure_channel_or_component_sum_interpretation=False)
        return dict(time_s=at,native_bracket_s=[tm0,tm1],sampling='native point if exact; otherwise linear estimate within original bracket',
            named_fields=op,reference_values=result,node_comparisons=comparisons)
    def snapshot():
        # Missing headers and invalid updates stay None, rendered as explicit NaN in binary.
        row=dict(values)
        for key in fields:
            x=row.get(key);s=stats[key]
            if x is None:s['unavailable_native_points']+=1
            else:
                s['valid_native_points']+=1
                if s['min_raw'] is None or x<s['min_raw']:s.update(min_raw=x,min_time_s=now)
                if s['max_raw'] is None or x>s['max_raw']:s.update(max_raw=x,max_time_s=now)
        writer.write(pack.pack(*([now]+[row.get(k) if row.get(k) is not None else float('nan') for k in labels])))
        return (now,row)
    try:
        with open(path,'rb') as source:
            for blob in source:
                digest.update(blob);line=blob.decode('ascii').strip()
                if line in ['HEADER','TYPE','SWEEP','TRACE','VALUE','END']:
                    section=line
                    if line=='VALUE':
                        for label,request in wanted.items():
                            native=aliases.get(request);entry=traces.get(native,{})
                            unit=entry.get('unit') or types.get(entry.get('type'),{}).get('unit')
                            family=fields[label]['expected_dimension'] if label in fields else refs[label]['unit']
                            metadata[label]=dict(requested_signal=request,native_signal=native,
                                reported_unit=unit,scale_to_SI=scale(unit,family) if label in fields else 1.,
                                unit_basis='native TRACE/TYPE property' if label in fields else 'original voltage/current measurement contract',
                                status='trace_exposed' if native is not None else 'requested_trace_not_exposed',
                                trace_declaration=entry.get('declaration'))
                            if native is not None:selected.setdefault(native,[]).append(label)
                        if sweep!='time':raise ValueError('Time sweep required')
                        continue
                    if line!='END':continue
                    ended=True;marker=True;key=None;tail=None
                else:
                    if not line:continue
                    if prop is not None:
                        unit=explicit_unit(line)
                        if unit:prop['unit']=unit
                        if line==')':prop=None
                        continue
                    key,tail=quoted(line)
                    if key is None:continue
                    if section=='TYPE':
                        item=dict(unit=explicit_unit(line));types[key]=item
                        if 'PROP(' in line and ')' not in line[line.index('PROP('):]:prop=item
                        continue
                    if section=='SWEEP':
                        if sweep is None:sweep=key
                        continue
                    if section=='TRACE':
                        if tail.startswith('GROUP'):
                            if tail!='GROUP 1':raise ValueError('Unsupported native non-scalar GROUP; no auto retry')
                            group=norm(key);continue
                        native=norm(key);type_ref=re.match(r'^"([^"]+)"',tail)
                        item=dict(type=type_ref.group(1) if type_ref else None,unit=explicit_unit(line),declaration=tail[:240])
                        if native in traces:raise ValueError('Duplicate native TRACE')
                        traces[native]=item;aliases[native]=native
                        if group is not None:aliases[group]=native;group=None
                        if 'PROP(' in line and ')' not in line[line.index('PROP('):]:prop=item
                        continue
                    if section!='VALUE':continue
                    marker=key==sweep
                    if not marker:
                        native=aliases.get(norm(key));targets=selected.get(native,[])
                        if not targets:continue
                        try:x=float(tail);valid=finite(x)
                        except ValueError:x=None;valid=False
                        for label in targets:
                            if label in seen:raise ValueError('Duplicate selected field update')
                            seen.add(label);values[label]=x if valid else None
                            if not valid:
                                if label in stats:stats[label]['invalid_updates']+=1
                                if len(invalid)<20:invalid.append(dict(field=label,time_s=now,rendered=tail[:80]))
                        continue
                if now is not None:
                    current=snapshot();points+=1
                    if previous is not None:
                        if current[0]<=previous[0]:raise ValueError('Nonincreasing native field time')
                        maxgap=max(maxgap,current[0]-previous[0])
                        for at in cfg['snapshot_times_s']:
                            if str(at) not in snapshots and previous[0]<=at<=current[0]:snapshots[str(at)]=make_snapshot(at,previous,current)
                    previous=current
                if ended:break
                now=float(tail)
                if not finite(now) or (points==0 and now!=0):raise ValueError('Native field history must start at0')
                seen=set()
        if not ended or previous is None or abs(previous[0]-cfg['stop_s'])>1e-15:raise ValueError('Native field END missing')
    finally:writer.close()
    missing=[k for k in fields if metadata[k]['status']!='trace_exposed']
    invalid_fields=[k for k in fields if stats[k]['invalid_updates']]
    unavailable=[k for k in fields if stats[k]['unavailable_native_points']]
    columns_meta=dict(names=columns,field_metadata=metadata,missing_numeric_encoding='Explicit IEEE NaN; never zero or interpolation across missing/invalid values',
        native_rows=points,source_raw_sha256=digest.hexdigest(),binary=writer.proof())
    with open(os.path.join(output,'fields.columns.json'),'w') as f:json.dump(columns_meta,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    return dict(status='complete_named_field_capture' if not missing and not invalid_fields and not unavailable else 'incomplete_or_invalid_named_fields_recorded',
        requested_fields=list(cfg['field_order']),missing_fields=missing,invalid_fields=invalid_fields,unavailable_fields=unavailable,invalid_update_examples=invalid,
        field_metadata={k:metadata[k] for k in fields},field_statistics=stats,native_points=points,max_native_gap_s=maxgap,
        source_raw_sha256=digest.hexdigest(),snapshots=snapshots,returned_fields=writer.proof(),
        missing_values_never_zero_filled=True,unit_scaling_not_inferred=True,pure_channel_current_identified=False,
        reverse_VDS_convention_not_assigned=True,no_automatic_retry=True)
