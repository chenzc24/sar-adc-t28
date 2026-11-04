"""Reference-only managed native measurement reduction. Python2.7/3 stdlib.

Approximate boundary replay and native simulation measurements are distinct.
No acceptance contract is approved here. Missing terminal currents are fatal.
"""
from __future__ import print_function
import argparse
import array
import hashlib
import json
import math
import os
import re
import struct
import sys
import zlib

MIB = 1024 * 1024
try:
    STRING_TYPES = (basestring,)
except NameError:
    STRING_TYPES = (str,)


def norm(name):
    return name.replace('\\', '').lower()


def finite(value):
    return not math.isnan(value) and not math.isinf(value)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for blob in iter(lambda: handle.read(65536), b''):
            h.update(blob)
    return h.hexdigest()


def safe_file(root, relative):
    if (not isinstance(relative, STRING_TYPES) or os.path.isabs(relative) or
            '..' in relative.replace('\\', '/').split('/')):
        raise ValueError('Unsafe relative path')
    root = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, relative))
    if not path.startswith(root + os.sep) or not os.path.isfile(path):
        raise ValueError('Required file missing or outside declared root: ' + relative)
    return path


def read_json(path, cap=4*MIB):
    if os.path.getsize(path) > cap:
        raise ValueError('Metadata input cap exceeded')
    with open(path) as handle:
        return json.load(handle)


class Budget(object):
    def __init__(self, directory, limit):
        if limit <= 0 or limit > 32*MIB:
            raise ValueError('Output cap must be <=32MiB')
        self.directory, self.limit = directory, limit
        self.bytes = sum(os.path.getsize(os.path.join(directory, f))
                         for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)))

    def reserve(self, amount):
        if self.bytes + amount > self.limit:
            raise ValueError('Derived output exceeds fixed byte cap')
        self.bytes += amount

    def new(self, name):
        path = os.path.join(self.directory, name)
        if os.path.exists(path):
            raise ValueError('Preserve existing artifact: ' + name)
        return path

    def json(self, name, value):
        blob = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode('ascii')
        path = self.new(name)
        temporary = path+'.partial'
        if os.path.exists(temporary):
            raise ValueError('Preserve partial metadata: '+name)
        self.reserve(len(blob))
        with open(temporary, 'wb') as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(temporary,path)


class NativeGzip(object):
    def __init__(self, budget, name, columns):
        self.budget, self.name, self.columns = budget, name, columns
        self.handle = open(budget.new(name), 'wb')
        self.encoder = zlib.compressobj(6, zlib.DEFLATED, 31)
        self.packer = struct.Struct('<' + 'd'*len(columns))
        self.sha, self.raw_sha = hashlib.sha256(), hashlib.sha256()
        self.rows, self.bytes, self.closed = 0, 0, False

    def _emit(self, blob):
        self.budget.reserve(len(blob))
        self.handle.write(blob)
        self.sha.update(blob)
        self.bytes += len(blob)

    def row(self, values):
        blob = self.packer.pack(*values)
        self.raw_sha.update(blob)
        self._emit(self.encoder.compress(blob))
        self.rows += 1

    def close(self):
        if not self.closed:
            try:
                self._emit(self.encoder.flush())
            finally:
                self.handle.close()
                self.closed = True

    def receipt(self):
        return dict(file=self.name, rows=self.rows, columns=self.columns,
                    compressed_bytes=self.bytes, sha256=self.sha.hexdigest(),
                    uncompressed_bytes=self.rows*self.packer.size,
                    uncompressed_sha256=self.raw_sha.hexdigest(),
                    representation='little-endian f64, gzip lossless; existing native timestamps only')


def validate_config(cfg):
    if cfg.get('schema_version') != 1 or cfg.get('acceptance_pass') is not None:
        raise ValueError('Schema1 and unapproved acceptance required')
    selected_v, selected_i = [norm(x) for x in cfg['voltage_saves']], [norm(x) for x in cfg['current_saves']]
    if (not selected_v or not selected_i or len(set(selected_v)) != len(selected_v) or
            len(set(selected_i)) != len(selected_i) or set(selected_v) & set(selected_i)):
        raise ValueError('Invalid or duplicate selected signals')
    equations = dict((norm(n), [norm(t) for t in terms]) for n, terms in cfg['kcl_terms'].items())
    if len(equations) != 5 or any(not terms or len(set(terms)) != len(terms) or
                                not set(terms) <= set(selected_i) for terms in equations.values()):
        raise ValueError('Five complete current KCL equations required')
    catalog = dict((norm(n), item) for n, item in cfg['terminal_current_catalog'].items())
    if set(catalog) != set(selected_i):
        raise ValueError('Every selected current needs an explicit terminal catalog record')
    for node, terms in equations.items():
        incident = set(n for n, item in catalog.items() if norm(item['node']) == node)
        if set(terms) != incident:
            raise ValueError('KCL incidence disagrees with complete terminal catalog: '+node)
    selected = set(selected_v+selected_i)
    if ('vdd!' not in selected or not set(equations) <= set(selected_v) or
            not set(norm(x) for x in cfg['diagnostic_voltage_columns']) <= set(selected_v) or
            not set(norm(x) for x in cfg['edge_nodes']) <= set(selected_v) or
            not set(norm(x) for x in cfg['initial_witness_v']) <= set(selected_v)):
        raise ValueError('Missing required voltage measurement')
    for pair in cfg.get('selected_mos_pair_screens', []):
        if len(pair['nodes']) != 2 or not set(norm(n) for n in pair['nodes']) <= set(selected_v+['0']):
            raise ValueError('Missing selected MOS terminal voltage')
    a, b, stop = cfg['diagnostic_start_s'], cfg['diagnostic_stop_s'], cfg['source_history_stop_s']
    if not 0 <= a < b <= stop or cfg['max_total_output_bytes'] > 32*MIB:
        raise ValueError('Invalid history/window/output budget')
    peaks=cfg['source_peaks']
    if len(peaks)!=4 or len(set(norm(x['fixture_node']) for x in peaks))!=4:
        raise ValueError('Four distinct source native peak records required')
    for item in peaks:
        if ('time_s' not in item or 'time_ns' in item or
                not isinstance(item['time_s'],(int,float)) or not finite(item['time_s']) or
                not a<=item['time_s']<=b or item['kind'] not in ['min','max'] or
                norm(item['fixture_node']) not in selected_v or
                not isinstance(item['value_v'],(int,float)) or not finite(item['value_v'])):
            raise ValueError('Source native peak requires explicit SI time_s and finite selected voltage')
    return sorted(selected), sorted(selected_i), equations


class Baseline(object):
    """Small frozen native-voltage table; interpolation is diagnostic only."""
    def __init__(self, inputs, cfg):
        self.cfg = cfg
        p = safe_file(inputs, cfg['file'])
        if os.path.getsize(p) > 4*MIB or digest(p) != cfg['sha256']:
            raise ValueError('Frozen native diagnostic hash/size mismatch')
        self.columns = cfg['columns']
        self.width = len(self.columns)
        self.values = array.array('d')
        with open(p, 'rb') as handle:
            self.values.fromfile(handle, os.path.getsize(p)//8)
        if sys.byteorder != 'little':
            self.values.byteswap()
        if (os.path.getsize(p)%8 or len(self.values)%self.width or
                len(self.values)//self.width != cfg['rows']):
            raise ValueError('Malformed source native diagnostic')
        self.rows, self.index = cfg['rows'], 0
        self.mapping = dict((norm(new), self.columns.index(old)) for old, new in cfg['signal_mapping'].items())
        self.errors = dict((n, dict(max_abs_v=0., max_abs_time_s=None, sum_sq_v2=0., samples=0)) for n in self.mapping)
        previous = None
        for i in range(self.rows):
            t = self.values[i*self.width]
            if not finite(t) or (previous is not None and t <= previous):
                raise ValueError('Invalid source native diagnostic times')
            previous = t
        if any(not finite(v) for v in self.values):
            raise ValueError('Nonfinite source native diagnostic')

    def observe(self, t, values):
        if t < self.values[0] or t > self.values[-self.width]:
            return
        while self.index+1 < self.rows and self.values[(self.index+1)*self.width] < t:
            self.index += 1
        left, right = self.index*self.width, min(self.index+1, self.rows-1)*self.width
        tl, tr = self.values[left], self.values[right]
        fraction = 0. if tr == tl else (t-tl)/(tr-tl)
        for node, col in self.mapping.items():
            expected = self.values[left+col] + fraction*(self.values[right+col]-self.values[left+col])
            delta = values[node]-expected
            item = self.errors[node]
            item['samples'] += 1
            item['sum_sq_v2'] += delta*delta
            if item['max_abs_time_s'] is None or abs(delta) > item['max_abs_v']:
                item.update(max_abs_v=abs(delta), max_abs_time_s=t)

    def report(self):
        out = {}
        for n, item in self.errors.items():
            if not item['samples']:
                raise ValueError('No diagnostic waveform overlap with source')
            out[n] = dict(item, native_sample_weighted_rms_v=math.sqrt(item['sum_sq_v2']/item['samples']))
        return dict(diagnostic_only=True, acceptance_pass=None, source_native_sha256=self.cfg['sha256'],
                    comparison='Frozen original native voltages linearly evaluated at NEW native timestamps; no invented measured samples',
                    source_native_time_range_s=[self.values[0],self.values[-self.width]], voltage_errors=out)

    def edge_diagnostics(self, observed, vdd):
        records = {}
        for node, col in self.mapping.items():
            expected=[]
            for row in range(self.rows-1):
                left,right=row*self.width,(row+1)*self.width
                a,b=self.values[left+col]-.5*vdd,self.values[right+col]-.5*vdd
                if (a<0<=b) or (a>0>=b):
                    expected.append(dict(direction='rising' if b>a else 'falling',
                        estimated_time_s=self.values[left]-a*(self.values[right]-self.values[left])/(b-a),
                        before_time_s=self.values[left],after_time_s=self.values[right]))
            actual=[x for x in observed.get(node,[]) if
                    x['before_time_s']>=self.values[0] and x['after_time_s']<=self.values[-self.width]]
            pairs=[]
            for source,new in zip(expected,actual):
                pairs.append(dict(source=source,measured=new,
                    same_direction=source['direction']==new['direction'],
                    error_time_s=new['estimated_time_s']-source['estimated_time_s']))
            records[node]=dict(source_events=len(expected),measured_events=len(actual),ordinal_pairs=pairs,
                               equal_event_count=len(expected)==len(actual))
        return dict(diagnostic_only=True,acceptance_pass=None,constant_source_vdd_v=vdd,
                    matching='Ordinal pairs only within common native-bracket coverage; unmatched counts are reported, not accepted',nodes=records)


def extrema(stats, name, value, t):
    item = stats.get(name)
    if item is None:
        stats[name] = dict(min=value, max=value, min_time_s=t, max_time_s=t)
    else:
        if value < item['min']:
            item.update(min=value, min_time_s=t)
        if value > item['max']:
            item.update(max=value, max_time_s=t)


def summarize(path, cfg, budget, baseline=None):
    selected, currents, equations = validate_config(cfg)
    wanted = set(selected)
    nodes = sorted(equations)
    incident = sorted(set(t for terms in equations.values() for t in terms))
    diagnostic_v = [norm(n) for n in cfg['diagnostic_voltage_columns']]
    full_cols = ['time','vdd!']+nodes+incident+['kcl:'+n for n in nodes]
    fault_cols = ['time']+diagnostic_v+currents+['kcl:'+n for n in nodes]
    full = NativeGzip(budget, 'kcl.full.native.f64le.gz', full_cols)
    fault = NativeGzip(budget, 'fault.native.f64le.gz', fault_cols)
    stats, initial, kcl_stats, edges, pair_stats = {}, {}, {}, {}, {}
    values, seen, canonical, aliases, binding, selected_by_native = {}, set(), set(), {}, {}, {}
    previous_t, previous_i, previous_kcl = None, {}, {}
    previous_edges, snapshots, charge = {}, {}, dict((n,dict(signed_C=0.,abs_C=0.,fault_signed_C=0.,fault_abs_C=0.)) for n in currents)
    fault_first, fault_last, last_fault_i, last_fault_t = None, None, {}, None
    points, held, max_gap, raw_bytes = 0, 0, 0., 0
    raw_sha = hashlib.sha256()
    section, sweep, group, prop, current_t, ended = None, None, None, False, None, False

    def snapshot(t):
        missing = wanted-set(values)
        if missing:
            raise ValueError('Uninitialized selected native values: '+', '.join(sorted(missing)))
        if values['vdd!'] <= 0:
            raise ValueError('Nonpositive native VDD')
        for n in selected:
            extrema(stats,n,values[n],t)
        residual = dict((n,sum(values[x] for x in terms)) for n,terms in equations.items())
        for n, val in residual.items():
            norm_a=sum(abs(values[x]) for x in equations[n])
            item=kcl_stats.setdefault(n,dict(max_abs_a=0.,time_s=t,max_l1_incident_a=0.,
                max_residual_over_l1=0.,max_residual_over_l1_time_s=t,
                signed_integral_C=0.,abs_integral_C=0.,fault_max_abs_a=0.))
            if abs(val)>item['max_abs_a']:
                item.update(max_abs_a=abs(val),time_s=t,incident_at_max_a=dict((x,values[x]) for x in equations[n]))
            item['max_l1_incident_a']=max(item['max_l1_incident_a'],norm_a)
            ratio=abs(val)/norm_a if norm_a else 0.
            if ratio>item['max_residual_over_l1']:
                item.update(max_residual_over_l1=ratio,max_residual_over_l1_time_s=t)
            if previous_t is not None:
                dt=t-previous_t
                item['signed_integral_C']+=(val+previous_kcl[n])*.5*dt
                item['abs_integral_C']+=(abs(val)+abs(previous_kcl[n]))*.5*dt
            if cfg['diagnostic_start_s']<=t<=cfg['diagnostic_stop_s']:
                item['fault_max_abs_a']=max(item['fault_max_abs_a'],abs(val))
        for n in currents:
            if previous_t is not None:
                item=charge[n];old=previous_i[n];now=values[n];dt=t-previous_t
                item['signed_C']+=(old+now)*.5*dt
                item['abs_C']+=(abs(old)+abs(now))*.5*dt
            if last_fault_t is not None and cfg['diagnostic_start_s']<=t<=cfg['diagnostic_stop_s']:
                item=charge[n];old=last_fault_i[n];now=values[n];dt=t-last_fault_t
                item['fault_signed_C']+=(old+now)*.5*dt
                item['fault_abs_C']+=(abs(old)+abs(now))*.5*dt
        for raw_node in cfg['edge_nodes']:
            node=norm(raw_node);x=values[node]-.5*values['vdd!'];old=previous_edges.get(node)
            if old is not None and ((old[1]<0<=x) or (old[1]>0>=x)):
                if sum(len(v) for v in edges.values())>=cfg['max_edge_events']:
                    raise ValueError('Half-VDD event count cap exceeded')
                at=old[0]-old[1]*(t-old[0])/(x-old[1])
                edges.setdefault(node,[]).append(dict(direction='rising' if x>old[1] else 'falling',
                    estimated_time_s=at,before_time_s=old[0],after_time_s=t,
                    before_voltage_v=old[2],after_voltage_v=values[node],
                    before_vdd_v=old[3],after_vdd_v=values['vdd!']))
            previous_edges[node]=(t,x,values[node],values['vdd!'])
        for screen in cfg.get('selected_mos_pair_screens',[]):
            n1,n2=[norm(x) for x in screen['nodes']]
            val=(0. if n1=='0' else values[n1])-(0. if n2=='0' else values[n2])
            extrema(pair_stats,screen['instance']+':'+screen['terminal'],val,t)
        full.row([t,values['vdd!']]+[values[n] for n in nodes]+[values[n] for n in incident]+[residual[n] for n in nodes])
        if cfg['diagnostic_start_s']<=t<=cfg['diagnostic_stop_s']:
            fault.row([t]+[values[n] for n in diagnostic_v]+[values[n] for n in currents]+[residual[n] for n in nodes])
            for item in cfg['source_peaks']:
                node=norm(item['fixture_node']);val=values[node];old=snapshots.get(node)
                if old is None or (val>old['voltage_v'] if item['kind']=='max' else val<old['voltage_v']):
                    snapshots[node]=dict(time_s=t,voltage_v=val,all_selected_currents_a=dict((n,values[n]) for n in currents),
                                         node_kcl_a=residual.copy())
            if baseline is not None:
                baseline.observe(t,values)
        return residual

    try:
        with open(path,'rb') as source:
            while True:
                raw=source.readline(65537)
                if not raw:break
                if len(raw)>65536:raise ValueError('Native line cap exceeded')
                raw_bytes+=len(raw);raw_sha.update(raw)
                line=raw.decode('ascii').strip()
                if line in ('HEADER','TYPE','SWEEP','TRACE','VALUE','END'):
                    if group is not None and line!='TRACE':raise ValueError('Dangling native GROUP')
                    section=line
                    if line=='VALUE':
                        if sweep!='time' or not wanted<=canonical:
                            raise ValueError('Required TRACE/time missing: '+', '.join(sorted(wanted-canonical)))
                        for n in selected:selected_by_native.setdefault(binding[n],[]).append(n)
                    if line!='END':continue
                    ended=True
                else:
                    if not line or section not in ('SWEEP','TRACE','VALUE'):continue
                    if prop:
                        if line==')':prop=False
                        continue
                    if not line.startswith('"'):continue
                    _,key,tail=line.split('"',2);tail=tail.strip()
                    if section=='SWEEP':
                        if sweep is None:sweep=key
                        elif key!=sweep:raise ValueError('Multiple sweep variables unsupported')
                        prop='PROP(' in tail and ')' not in tail[tail.index('PROP('):]
                        continue
                    if section=='TRACE':
                        prop='PROP(' in tail and ')' not in tail[tail.index('PROP('):]
                        if tail.startswith('GROUP'):
                            if tail!='GROUP 1' or group is not None:raise ValueError('Unsupported native GROUP')
                            group=key;continue
                        name=norm(key)
                        if name in canonical:raise ValueError('Duplicate canonical TRACE: '+name)
                        canonical.add(name);aliases[key]=name;binding[name]=name
                        if group is not None:
                            alias=norm(group)
                            if alias!=name and alias in canonical:raise ValueError('Duplicate GROUP alias')
                            canonical.add(alias);aliases[group]=name;binding[alias]=name;group=None
                        continue
                    value=float(tail)
                    if not finite(value):raise ValueError('Nonfinite native scalar')
                    if key!=sweep:
                        name=aliases.get(key)
                        if current_t is None:raise ValueError('Native value precedes time')
                        if name is None:raise ValueError('Unknown native VALUE key: '+key)
                        for n in selected_by_native.get(name,[]):
                            if n in seen:raise ValueError('Duplicate selected update at native point')
                            values[n]=value;seen.add(n)
                        continue
                if current_t is not None:
                    if previous_t is not None and current_t<=previous_t:raise ValueError('Non-increasing native times')
                    if not points and current_t!=0:raise ValueError('Native history must start at zero')
                    if previous_t is not None:max_gap=max(max_gap,current_t-previous_t)
                    residual=snapshot(current_t)
                    if not points:initial=dict(values)
                    if cfg['diagnostic_start_s']<=current_t<=cfg['diagnostic_stop_s']:
                        if fault_first is None:fault_first=current_t
                        fault_last=current_t;last_fault_t=current_t
                        last_fault_i=dict((n,values[n]) for n in currents)
                    previous_t=current_t;previous_i=dict((n,values[n]) for n in currents);previous_kcl=residual
                    held+=len(wanted-seen);points+=1
                if ended:
                    # No early-stop hash: include actual file bytes, reject extra data.
                    while True:
                        extra=source.read(65536)
                        if not extra:break
                        raw_sha.update(extra);raw_bytes+=len(extra)
                        if extra.strip():raise ValueError('Unexpected data after native END')
                    break
                if current_t is not None and value<=current_t:raise ValueError('Non-increasing native time marker')
                current_t=value;seen=set()
        if (not ended or not points or not fault.rows or
                abs(current_t-cfg['source_history_stop_s'])>1e-18):
            raise ValueError('Incomplete native simulation/diagnostic window')
    finally:
        try:full.close()
        finally:fault.close()
    errors={}
    for item in cfg['source_peaks']:
        n=norm(item['fixture_node']);measured=snapshots[n]
        errors[n]=dict(diagnostic_only=True,measured_native_peak_v=measured['voltage_v'],
            measured_native_time_s=measured['time_s'],source_native_peak_v=item['value_v'],
            source_native_time_s=item['time_s'],error_v=measured['voltage_v']-item['value_v'],
            error_time_s=measured['time_s']-item['time_s'])
    initial_errors=dict((norm(n),initial[norm(n)]-v) for n,v in cfg['initial_witness_v'].items())
    return dict(analysis_complete=True,native_points=points,native_PSF_END=True,
        first_native_time_s=0.,last_native_time_s=current_t,raw_sha256=raw_sha.hexdigest(),raw_bytes=raw_bytes,
        held_values_from_sparse_updates=held,max_native_gap_s=max_gap,
        trace_bindings=dict((n,binding[n]) for n in selected),
        all_selected_currents_present_and_initialized=True,selected_current_count=len(currents),
        voltage_and_current_extrema=stats,initial_native_values=initial,
        initial_witness_error_v=initial_errors,initial_unavailable_from_source=cfg['initial_unavailable_from_source'],
        half_vdd_events=edges,edge_method='Estimate from adjacent native samples of Vnode-0.5VDD; waveform knots unchanged',
        node_kcl=kcl_stats,current_charge_trapezoids=charge,
        charge_method='Signed and absolute-current trapezoids on consecutive native knots; fault integration uses only native knots within window, no fabricated boundary samples',
        fault_integral_actual_native_interval_s=[fault_first,fault_last],peak_snapshots=snapshots,
        source_peak_reproduction_diagnostic=errors,
        source_wave_reproduction_diagnostic=baseline.report() if baseline is not None else None,
        source_half_vdd_event_diagnostics=baseline.edge_diagnostics(edges,cfg['source_diagnostic']['constant_vdd_v']) if baseline is not None else None,
        native_exports=[full.receipt(),fault.receipt()],
        selected_mos_pair_extrema=pair_stats,mos_pair_scope=cfg.get('mos_pair_scope'),
        current_interpretation=cfg['current_interpretation'],boundary_provenance=cfg['boundary_provenance'],
        measurement_provenance='Native simulator terminal-current/voltage samples. KCL sums/integrals and crossing estimates are explicitly derived; no native samples interpolated/decimated.',
        proposed_contract=cfg['proposed_contract'],acceptance_pass=None,circuit_repair_claim=False)


def preserve_log(run,budget):
    source=safe_file(run,'spectre.out')
    if os.path.getsize(source)>2*MIB:raise ValueError('Original simulator log exceeds explicit2MiB cap')
    target=budget.new('spectre.original.log')
    codes={};h=hashlib.sha256()
    with open(source,'rb') as src,open(target,'wb') as dest:
        for raw in src:
            budget.reserve(len(raw));dest.write(raw);h.update(raw)
            line=raw.decode('ascii','replace')
            for code in re.findall(r'\bCMI-\d+\b',line):codes[code]=codes.get(code,0)+1
    return dict(file='spectre.original.log',sha256=h.hexdigest(),bytes=os.path.getsize(source),
                unmodified_complete_log=True,CMI_code_occurrences=codes,CMI_present=bool(codes),
                warning_count_scope='Logged occurrences only; simulator maxwarns/maxw may suppress repeats. No electrical PASS inferred from absent CMI text.')


def analyze(run,output):
    run,output=os.path.realpath(run),os.path.realpath(output)
    if os.path.normcase(output)!=os.path.normcase(os.path.join(run,'derived')):
        raise ValueError('Expected managed run/derived output directory')
    cfg_path=safe_file(run,'inputs/measurement.json');cfg=read_json(cfg_path);validate_config(cfg)
    if os.path.basename(run)==cfg['source_run']:
        raise ValueError('Historical source run is read-only; use a new managed fixture run')
    if not os.path.isdir(output):os.makedirs(output)
    if os.listdir(output):raise ValueError('Preserve existing derived output; fresh directory required')
    state=read_json(safe_file(run,'simulation.state.json'))
    native=state.get('native',{})
    if (state.get('status')!='complete' or state.get('exit_code')!=0 or
            not native.get('native_analysis_pass') or not native.get('zero_error_footer')):
        raise ValueError('Native simulation not complete/PASS/zero-error')
    with open(safe_file(run,'raw/logStatus')) as handle:
        if not re.search(r'\b'+re.escape(cfg['analysis_name'])+r'\s+PASS\b',handle.read(65536)):
            raise ValueError('Exact transient PASS missing')
    for relative,expected in cfg['required_input_sha256'].items():
        if digest(safe_file(run,'inputs/'+relative))!=expected:raise ValueError('Frozen input hash mismatch: '+relative)
    paths=[f for f in os.listdir(os.path.join(run,'raw')) if f.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('Expected exactly one native ASCII transient')
    budget=Budget(output,cfg['max_total_output_bytes'])
    log=preserve_log(run,budget)
    baseline=Baseline(os.path.join(run,'inputs'),cfg['source_diagnostic'])
    result=summarize(safe_file(run,'raw/'+paths[0]),cfg,budget,baseline)
    result.update(scope=cfg['scope'],measurement_sha256=digest(cfg_path),original_simulator_log=log,
                  native_warning_codes=native.get('warning_codes'),native_effective_settings=native.get('effective_settings'),
                  native_simulator_version=native.get('version'),source_run=cfg['source_run'])
    budget.json('native.columns.json',dict(exports=result['native_exports'],time_unit='s',voltage_unit='V',current_unit='A',
        KCL='sum of all incident saved wrapper-port currents; currents positive into components, multiplicity already included'))
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*MIB:raise ValueError('Analysis RSS exceeds256MiB')
    else:result['analysis_peak_rss_bytes']=None
    result['derived_bytes_before_result']=budget.bytes
    # This is intentionally the final output write; any prior failure leaves no result.json.
    budget.json('result.json',result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',required=True)
    parser.add_argument('--output-dir',required=True)
    args=parser.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS)
        cap=240*MIB if hard==resource.RLIM_INFINITY else min(240*MIB,hard)
        resource.setrlimit(resource.RLIMIT_AS,(cap,hard))
    result=analyze(args.run_dir,args.output_dir)
    print('REFERENCE_NATIVE_CURRENT_KCL_OK',result['native_points'],'acceptance_pass=null')


if __name__=='__main__':main()
