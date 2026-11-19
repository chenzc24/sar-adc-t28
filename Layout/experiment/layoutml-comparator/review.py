"""Review this Meso-LML file using the upstream compiler and the electrical source."""
import argparse
import copy
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import time
from contact_audit import audit
from floorplan_audit import physical, decision_access

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NETLIST = ROOT / 'design/xtor/comparator/comparator.scs'
WORK = ROOT / 'work/layout/layoutml-clean-comparator'
SOURCE = HERE / 'strongarm.meso.lml'


def evaluate(mc):
    text = SOURCE.read_text(encoding='utf-8')
    compiled = mc.compile_meso_to_layers_nm(text, {})
    store = compiled['store']
    a = mc.parse_lml_ast(compiled['flat_lml'], store)
    ports = {}
    shapes = []
    connections = []
    devices = {}
    for ln in NETLIST.read_text().splitlines():
        match = re.match(r'\s*(M\w+) \((\w+) (\w+) (\w+) (\w+)\) (\w+) l=30n w=(500n|1u) multi=1 nf=1 ', ln)
        if match:
            name,d,g,s,b,m,w = match.groups()
            devices[name]=(d,g,s,b,m,1000 if w=='1u' else 500)
    found=set()
    for pc in a['pcells']:
        entry=store['realizations'][pc['realization']]
        local={p['port']:p for p in entry['ports_local_nm']}
        for key,p in local.items():
            b=mc.transform_local_box(p['box'], *pc['atNm'],pc['orient'])
            ports[pc['id'],key]=(p['net'],tuple(b))
            shapes.append((p['net'],'met1',tuple(b)))
        for explicit in pc['ports']:
            assert (explicit['net'],tuple(explicit['box']))==ports[pc['id'],explicit['port']]
        for i,line in enumerate(pc['devices']):
            name=line.split()[1]
            d,g,s,b,m,w=devices[name]
            assert name not in found
            found.add(name)
            assert line.split()[2]==m and f'B=&{b}' in line and f'SD=&{s},&{d}' in line
            assert {local[f'SD_{i}']['net'],local[f'SD_{i+1}']['net']}=={s,d}
            assert local[f'G_{i+1}']['net']==g
            assert f'nf=1' in line and f'L=0.03' in line and int(float(re.search(r'W=([\d.]+)',line)[1])*1000)==w
            od=entry['layers_dbu_nm']['diff'][0]
            assert od[3]-od[1]==w
            gates=[r for r in entry['layers_dbu_nm']['poly'] if r[1]<=od[1] and r[3]>=od[3]]
            assert len(gates)==len(pc['devices']) and gates[i][2]-gates[i][0]==30
    assert found==set(devices) and len(found)==11
    metrics={}
    cuts=defaultdict(list)
    for rt in a['routes']:
        net=rt['net']
        tracks=defaultdict(list)
        for path in rt['paths']:
            for rect in path['segRects']:
                shapes.append((net,path['layer'],tuple(rect)))
            for (x,y),(xx,yy) in zip(path['ptsNm'],path['ptsNm'][1:]):
                vertical=x==xx
                assert vertical or y==yy
                tracks[path['layer'],vertical,x if vertical else y].append(sorted((y,yy) if vertical else (x,xx)))
        lengths=Counter()
        for (layer,_,_),intervals in tracks.items():
            end=-10**12
            for low,high in sorted(intervals):
                lengths[layer]+=max(0,high-max(end,low))
                end=max(end,high)
        for via in rt['vias']:
            first=len(shapes)
            x0,y0,x1,y1=via['bBox']
            assert x1-x0==y1-y0==110
            assert len(via['metalLayers'])==2
            for layer in via['metalLayers']:
                shapes.append((net,layer,tuple(via['bBox'])))
            connections.append((first,first+1))
            cuts['via' if via['mBot']==1 else 'via2'].append((x0+30,y0+30,x1-30,y1-30))
        metrics[net]={'metal_nm':dict(lengths),'total_nm':sum(lengths.values()),'vias':len(rt['vias'])}
    for p in a['cellPorts']:
        shapes.append((p['name'],p['layer'],tuple(p['box'])))
    for layer in ('met1','met2','met3'):
        assert Counter(r for _,l,r in shapes if l==layer)==Counter(map(tuple,compiled['layers_nm'][layer])),layer
    for l,rects in cuts.items():
        assert Counter(rects)==Counter(map(tuple,compiled['layers_nm'][l])),l
    # Connectivity is inferred from touching conductors and physical via stacks,
    # using logical net names only to score the resulting components.
    parent=list(range(len(shapes)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    def join(i,j):
        parent[root(i)]=root(j)
    for i,j in connections:
        join(i,j)
    shorts=[]
    gaps={}
    for i,(n,l,b) in enumerate(shapes):
        for j in range(i):
            nn,ll,bb=shapes[j]
            if l!=ll:
                continue
            dx=max(b[0]-bb[2],bb[0]-b[2],0)
            dy=max(b[1]-bb[3],bb[1]-b[3],0)
            if n!=nn:
                distance=(dx*dx+dy*dy)**0.5
                if l not in gaps or distance<gaps[l][0]:
                    gaps[l]=[round(distance,2),n,nn,b,bb]
            if dx==dy==0:
                join(i,j)
                if n!=nn:
                    shorts.append((n,nn,l,b,bb))
    islands=defaultdict(set)
    for i,(n,l,b) in enumerate(shapes):
        islands[n].add(root(i))
    opens={n:len(v) for n,v in islands.items() if len(v)!=1}
    layers=compiled['layers_nm']
    bbox=[min(r[0] for v in layers.values() for r in v),min(r[1] for v in layers.values() for r in v),
          max(r[2] for v in layers.values() for r in v),max(r[3] for v in layers.values() for r in v)]
    pins={p['name'] for p in a['cellPorts']}
    assert pins==set('CLK OUTN OUTP VDD VINN VINP VSS'.split())
    assert set(metrics)==pins|{'X','Y','TAIL'}
    report=dict(bbox_nm=bbox,area_um2=(bbox[2]-bbox[0])*(bbox[3]-bbox[1])/1e6,
                devices=len(found),term_access=len(ports),pins=sorted(pins),nets=metrics,
                opens=opens,shorts=shorts,min_metal_gap_nm=gaps,
                non_grid_rects={l:sum(any(z%5 for z in r) for r in rr) for l,rr in layers.items() if any(any(z%5 for z in r) for r in rr)},
                netlist_sha256=sha256(NETLIST.read_bytes()).hexdigest(),lml_sha256=sha256(SOURCE.read_bytes()).hexdigest())
    report['contact_audit']=audit(a,layers,shapes)
    report['physical_geometry']=physical(a,layers,bbox)
    report['decision_paths_to_output_pin']=decision_access(a,ports)
    return report,compiled,a,shapes


def native_view(compiled,a,upstream):
    import meso_compiler as mc
    import pcell_synth
    viewer = upstream / 'prototype/viewer'
    html = (viewer / 'index.html').read_text(encoding='utf-8')
    # The upstream WebGL renderer submits a filled bounding box for a polygon
    # overlay. Draw compiler-width segment rectangles for orthogonal paths.
    # Keep the original fallback for diagonal segments in the bundled viewer.
    predicate = '(hasNonOrtho || p.ptsNm.length > 2)'
    assert html.count(predicate) == 1
    html = html.replace(predicate, 'hasNonOrtho')
    start = html.index('window.DEFAULT_STORE =')
    end = html.index('</script>', start)
    store=copy.deepcopy(compiled['store'])
    content=SOURCE.read_text(encoding='utf-8')
    preview=content
    for pc in a['pcells']:
        orient=pc['orient']
        if orient=='R0':
            continue
        entry=copy.deepcopy(store['realizations'][pc['realization']])
        layers=entry['layers_dbu_nm']
        for layer,rects in layers.items():
            layers[layer]=[mc.transform_local_box(r,0,0,orient) for r in rects]
        for p in entry['ports_local_nm']:
            p['box']=mc.transform_local_box(p['box'],0,0,orient)
        rid=pcell_synth._compute_realization_sha(layers,entry['ports_local_nm'])
        entry['sha256']=rid
        store['realizations'][rid]=entry
        pattern=r'(?m)^(  pcell '+pc['id']+r' .*) \{$'
        preview=re.sub(pattern,lambda m:m[1].replace('orient='+orient,'orient=R0')+f' realization={rid} {{',preview)
    proof=mc.compile_meso_to_layers_nm(preview,store)
    assert {l:Counter(map(tuple,r)) for l,r in proof['layers_nm'].items()}=={l:Counter(map(tuple,r)) for l,r in compiled['layers_nm'].items()}
    bundle = {'review.meso.lml':preview,SOURCE.name:content}
    html = (html[:start] + 'window.DEFAULT_STORE = ' + json.dumps(store)
            + ';\nwindow.SAMPLE_FILES = ' + json.dumps(bundle) + ';\n' + html[end:])
    def script(match):
        name = match[1].split('?')[0]
        if name == 'virtuoso-samples.js':
            return ''
        return '<script>' + (viewer / name).read_text(encoding='utf-8') + '</script>'
    html = re.sub(r'<script src="([^"]+)"></script>',script,html)
    (WORK/'layoutml-viewer.html').write_text(html,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--layoutml',type=Path,required=True)
    parser.add_argument('--native',action='store_true')
    args=parser.parse_args()
    up=args.layoutml.resolve()
    sys.path.insert(0,str(up/'explorations/Q-tech-decoupling'))
    import meso_compiler as mc
    start=time.perf_counter()
    report,compiled,ast,shapes=evaluate(mc)
    report['compile_check_s']=round(time.perf_counter()-start,3)
    WORK.mkdir(exist_ok=True,parents=True)
    (WORK/'check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    if report['opens'] or report['shorts']:
        raise SystemExit('Compiled metal connectivity failed. See check.json.')
    contact=report['contact_audit']
    if any(contact[key] for key in ('co_lower_not_enclosed','co_upper_not_enclosed','via_enclosure_fail',
                                    'weak_or_open_nets','partially_landed_ports','unsupported_path_ends',
                                    'duplicate_collinear_nm')):
        raise SystemExit('Contact or route geometry failed. See check.json.')
    physical_checks = report['physical_geometry']
    if (report['non_grid_rects'] or any(physical_checks[k] for k in
            ('well_assignment_errors','foreign_active_overlaps','dummy_crossings_over_active_or_tap',
             'opposite_implant_overlaps')) or any(not w['body_taps'] for w in physical_checks['well_components'])):
        raise SystemExit('Floorplan geometry failed. See check.json.')
    if args.native:
        native_view(compiled,ast,up)

