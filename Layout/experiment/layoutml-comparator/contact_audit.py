"""Geometry-only contact and routing checks for the LayoutML StrongARM draft (nm)."""
from collections import Counter, defaultdict


def contains(outer,inner,margin=0):
    return (outer[0]+margin<=inner[0] and outer[1]+margin<=inner[1]
            and outer[2]-margin>=inner[2] and outer[3]-margin>=inner[3])


def audit(ast,layers,shapes):
    from meso_compiler import transform_local_box
    contacts=layers['mcon']
    lower=layers['poly']+layers['diff']+layers['tap']
    bad_lower=[r for r in contacts if not any(contains(b,r) for b in lower)]
    bad_upper=[r for r in contacts if not any(contains(b,r) for b in layers['met1'])]
    gate_landings=[]
    for pc in ast['pcells']:
        master=ast['_storeObj']['realizations'][pc['realization']]
        for idx,device in enumerate(pc['devices'],start=1):
            port=next(p for p in master['ports_local_nm'] if p['port']==f'G_{idx}')
            pad=transform_local_box(port['box'],*pc['atNm'],pc['orient'])
            cut,=[c for c in contacts if contains(pad,c)]
            stem=transform_local_box(master['layers_dbu_nm']['poly'][idx-1],*pc['atNm'],pc['orient'])
            enclosure=[min(cut[0]-b[0],cut[1]-b[1],b[2]-cut[2],b[3]-cut[3])
                       for b in layers['poly']
                       if min(b[2],stem[2])>max(b[0],stem[0]) and min(b[3],stem[3])>max(b[1],stem[1])]
            gate_landings.append({'device':device.split()[1],'poly_enclosure_nm':max(enclosure),
                                  'centered_on_m1':pad[0]+pad[2]==cut[0]+cut[2] and pad[1]+pad[3]==cut[1]+cut[3]})
    cuts={l:layers[l] for l in ('via','via2')}
    bad_via=[]
    for layer,lo,hi in [('via','met1','met2'),('via2','met2','met3')]:
        for r in cuts[layer]:
            if not all(any(contains(b,r,30) for b in layers[m]) for m in [lo,hi]):
                bad_via.append([layer,r])
    # Keep the two networks distinct even where two foreign conductors just touch.
    # Within each net require a positive-area junction; edge contact alone is weak.
    parent=list(range(len(shapes)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    for i,(net,layer,b) in enumerate(shapes):
        for j in range(i):
            n,l,c=shapes[j]
            if (n,l)==(net,layer) and min(c[2],b[2])>max(c[0],b[0]) and min(c[3],b[3])>max(c[1],b[1]):
                parent[root(i)]=root(j)
    pin_errors=[]
    for p in ast['cellPorts']:
        # Cell ports are appended at the end of the reviewer's shape inventory.
        conductors=shapes[:-len(ast['cellPorts'])]
        if not any(n==p['name'] and l==p['layer'] and contains(b,p['box']) for n,l,b in conductors):
            pin_errors.append(p['name'])
    duplicate_length=0
    stubs=[]
    for rt in ast['routes']:
        n=rt['net']
        for v in rt['vias']:
            i,j=[next(i for i,(net,l,b) in enumerate(shapes) if net==n and l==layer and tuple(v['bBox'])==b)
                 for layer in v['metalLayers']]
            parent[root(i)]=root(j)
        tracks=defaultdict(list)
        for p in rt['paths']:
            for a,b in zip(p['ptsNm'],p['ptsNm'][1:]):
                k=0 if a[0]==b[0] else 1
                tracks[p['layer'],k,a[k]].append(sorted((a[1-k],b[1-k])))
            others=Counter(tuple(b) for net,l,b in shapes if (net,l)==(n,p['layer']))
            others.subtract(tuple(b) for b in p['segRects'])
            for x,y in (p['ptsNm'][0],p['ptsNm'][-1]):
                if not any(count>0 and contains(b,(x,y,x,y)) for b,count in others.items()):
                    stubs.append([n,p['layer'],[x,y]])
        for spans in tracks.values():
            end=-10**9
            for a,b in sorted(spans):
                duplicate_length+=max(0,min(b,end)-a)
                end=max(end,b)
    islands=defaultdict(set)
    for i,(n,_,_) in enumerate(shapes):
        islands[n].add(root(i))
    return dict(co=len(contacts),gate_landings=gate_landings,co_lower_not_enclosed=bad_lower,co_upper_not_enclosed=bad_upper,
                via_cuts=sum(map(len,cuts.values())),via_enclosure_fail=bad_via,
                weak_or_open_nets={n:len(v) for n,v in islands.items() if len(v)!=1},
                partially_landed_ports=pin_errors,unsupported_path_ends=stubs,
                duplicate_collinear_nm=duplicate_length)

