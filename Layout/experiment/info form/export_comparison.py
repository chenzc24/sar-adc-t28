"""Export complete V4 GDS records/geometry and LayoutML representation, read only.

Prerequisite: run the upstream importer/compiler commands recorded in README.md.
No live OA reads, design edits, rule checks, or browser approximations are used.
"""
import hashlib
import json
import shutil
import struct
from collections import Counter
from pathlib import Path

import klayout.db as k

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
WORK = PROJECT / 'work/layout/layoutml-v4-info'
SOURCE = PROJECT / 'work/layout/comparator-redesign/official-v4.gds'
EXPECTED = 'af089c02ae82219e312d9006609eb6206c150cb025d2ca3c342974652e933ea7'
CDL_EXPECTED = 'e5e3e20693a0b0123573650419d222aaffb3bb11388b388b3e0b2865ebc0aca4'
TOP = 'sar_strongarm_t28_core'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def j(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))

NAMES = '''HEADER BGNLIB LIBNAME UNITS ENDLIB BGNSTR STRNAME ENDSTR BOUNDARY PATH SREF AREF TEXT LAYER DATATYPE WIDTH XY ENDEL SNAME COLROW TEXTNODE NODE TEXTTYPE PRESENTATION SPACING STRING STRANS UINTEGER MAG ANGLE USTRING REFLIBS FONTS PATHTYPE GENERATIONS ATTRTABLE STYPTABLE STRTYPE ELFLAGS ELKEY LINKTYPE LINKKEYS NODETYPE PROPATTR PROPVALUE BOX BOXTYPE PLEX BGNEXTN ENDEXTN TAPENUM TAPECODE STRCLASS RESERVED FORMAT MASK ENDMASKS LIBDIRSIZE SRFNAME LIBSECUR'''.split()

def real_gds(b):
    if not any(b):
        return 0.0
    return (-1 if b[0] & 128 else 1) * (int.from_bytes(b[1:], 'big') / 2**(8*(len(b)-1))) * 16.0**((b[0] & 127)-64)

def decode(dtype, body):
    if dtype == 0:
        return None
    if dtype == 1:
        return [f'0x{int.from_bytes(body[i:i+2], "big"):04x}' for i in range(0,len(body),2)]
    if dtype in (2,3):
        width = 2 if dtype == 2 else 4
        return [int.from_bytes(body[i:i+width], 'big', signed=True) for i in range(0,len(body),width)]
    if dtype in (4,5):
        width = 4 if dtype == 4 else 8
        return [real_gds(body[i:i+width]) for i in range(0,len(body),width)]
    if dtype == 6:
        return body.rstrip(b'\0').decode('latin1')
    return {'unknown_datatype_payload_hex':body.hex()}

def record_dump(data):
    offset, result = 0, []
    while offset+4 <= len(data):
        size, typ, dtype = struct.unpack('>HBB', data[offset:offset+4])
        if size < 4:
            break
        assert size % 2 == 0 and offset+size <= len(data)
        raw = data[offset:offset+size]
        result.append(dict(index=len(result), offset_bytes=offset, length_bytes=size,
                           record_type=typ, record_name=NAMES[typ] if typ<len(NAMES) else f'UNKNOWN_{typ}',
                           datatype=dtype, value=decode(dtype,raw[4:]), raw_record_hex=raw.hex()))
        offset += size
        if typ == 4:
            break
    trailer = data[offset:]
    assert b''.join(bytes.fromhex(r['raw_record_hex']) for r in result)+trailer == data
    return result, trailer

def point(p):
    return [p.x, p.y]

def shape_dict(s):
    base = {'bbox_dbu': [s.bbox().left,s.bbox().bottom,s.bbox().right,s.bbox().top]}
    if s.is_box():
        base.update(type='box')
    elif s.is_polygon() or s.is_simple_polygon():
        p = s.polygon
        base.update(type='polygon', hull_dbu=[point(v) for v in p.each_point_hull()],
                    holes_dbu=[[point(v) for v in p.each_point_hole(h)] for h in range(p.holes())])
    elif s.is_path():
        p = s.path
        base.update(type='path', points_dbu=[point(v) for v in p.each_point()], width_dbu=p.width,
                    begin_extension_dbu=p.bgn_ext, end_extension_dbu=p.end_ext, round_ends=p.round)
    elif s.is_text():
        t = s.text
        base.update(type='text', text=t.string, position_dbu=[t.x,t.y], transform=str(t.trans),
                    size_dbu=t.size, font=t.font, halign=str(t.halign), valign=str(t.valign))
    else:
        raise ValueError('Unsupported shape in this export: '+str(s))
    base['properties'] = {str(key):value for key,value in s.properties().items()}
    return base

def flatten(path):
    layout=k.Layout()
    layout.read(str(path))
    assert layout.cell(TOP) is not None
    original_cells=[dict(name=c.name, shapes=sum(c.shapes(li).size() for li in layout.layer_indexes()),
                         instance_records=sum(1 for _ in c.each_inst())) for c in layout.each_cell()]
    cell=layout.cell(TOP)
    cell.flatten(-1,False)
    rows=[]
    for li in sorted(layout.layer_indexes(), key=lambda v:(layout.get_info(v).layer,layout.get_info(v).datatype)):
        info=layout.get_info(li)
        for s in cell.shapes(li).each():
            rows.append(dict(id=len(rows),layer=info.layer,datatype=info.datatype,**shape_dict(s)))
    return layout,rows,original_cells

def dump_geometry(f, layout, rows):
    f.write('ALL_FLATTENED_SHAPES_JSONL\n')
    f.write(j(dict(top=TOP,dbu_um=layout.dbu,coordinate_rule='integer DBU; multiply by dbu_um for micrometres',
                   shape_count=len(rows), note='Exact polygon/path/text coordinates, not bounding boxes alone.'))+'\n')
    for row in rows:
        f.write(j(row)+'\n')
    f.write('END_ALL_FLATTENED_SHAPES\n')

def main():
    assert digest(SOURCE)==EXPECTED
    assert digest(WORK/'comparator-reference.cdl')==CDL_EXPECTED
    bundle=WORK/'bundle'
    for ext,name in [('lml','layoutml.flat.lml'),('meso.lml','layoutml.meso.lml'),('store.json','layoutml.store.json')]:
        shutil.copyfile(bundle/f'{TOP}.{ext}',OUT/name)
    shutil.copyfile(WORK/'comparator-reference.cdl',OUT/'reference.cdl')
    records,trailer=record_dump(SOURCE.read_bytes())
    a, arows, cells=flatten(SOURCE)
    b, brows, bcells=flatten(WORK/'roundtrip.gds')
    with (OUT/'01_gds_complete.txt').open('w',encoding='utf-8',newline='\n') as f:
        f.write('COMPARATOR V4 — COMPLETE SOURCE GDS RECORDS AND FLATTENED GEOMETRY\n')
        f.write(j(dict(run='comp-v4-20261117-pex',source_sha256=EXPECTED,dbu_um=a.dbu,
                       source_bytes=SOURCE.stat().st_size,cells=cells))+'\n')
        f.write('ALL_GDS_RECORDS_JSONL (raw_record_hex permits byte-exact reconstruction)\n')
        for r in records:
            f.write(j(r)+'\n')
        f.write(j(dict(trailing_bytes=len(trailer),trailing_hex=trailer.hex()))+'\nEND_ALL_GDS_RECORDS\n')
        dump_geometry(f,a,arows)
    store=json.loads((OUT/'layoutml.store.json').read_text(encoding='utf-8'))
    with (OUT/'02_layoutml_complete.txt').open('w',encoding='utf-8',newline='\n') as f:
        f.write('COMPARATOR V4 — COMPLETE LAYOUTML IMPORT AND RECOMPILED GEOMETRY\n')
        f.write('Source matches 01_gds_complete.txt. This is importer/compiler output, NOT an OA query or a browser DOM dump.\n')
        f.write('No abridgment. LML alone does not contain full PCell geometry; the full store follows.\n')
        for name in ['layoutml.flat.lml','layoutml.meso.lml','layoutml.store.json','reference.cdl']:
            f.write('\nBEGIN '+name+'\n'+(OUT/name).read_text(encoding='utf-8')+'\nEND '+name+'\n')
        f.write('\nThe following geometry is compiled by upstream meso_compiler.py; it may differ from source GDS.\n')
        dump_geometry(f,b,brows)
    assert a.dbu == b.dbu
    diffs=[]
    for layer,datatype in sorted(set((x.layer,x.datatype) for lay in (a,b) for x in lay.layer_infos())):
        regs=[]
        for lay in (a,b):
            li=lay.find_layer(layer,datatype)
            regs.append(k.Region(lay.cell(TOP).begin_shapes_rec(li)).merged() if li is not None else k.Region())
        missing,added=regs[0]-regs[1],regs[1]-regs[0]
        diffs.append(dict(layer=layer,datatype=datatype,source_union_area_um2=regs[0].area()*a.dbu**2,
                          layoutml_union_area_um2=regs[1].area()*a.dbu**2,
                          missing_area_um2=missing.area()*a.dbu**2,added_area_um2=added.area()*a.dbu**2,
                          xor_area_um2=(missing.area()+added.area())*a.dbu**2))
    ports=[dict(realization=key,**p) for key,v in store['realizations'].items() for p in v.get('ports_local_nm',[])]
    report=dict(geometry_equal=all(x['xor_area_um2']==0 for x in diffs),layers=diffs,
                scope='Polygon union only; excludes text, hierarchy, PCell editability, net correctness and DRC/LVS.',
                imported_surface_ports=ports,imported_surface_port_nets=sorted(set(p['net'] for p in ports)))
    (OUT/'geometry_diff.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest=dict(run='comp-v4-20261117-pex',top=TOP,source_gds=str(SOURCE),source_sha256=EXPECTED,
                  source_remote='thu-wei:/server_local_ssd/chenzc_intern25/sar-adc-t28/layout/evidence/comp-v4-20261117-pex/fixture.gds',
                  cdl_sha256=CDL_EXPECTED,layoutml_commit='e19fb224207147ddb531d0ea2b1812b5862fd7e4',
                  source_records=len(records),source_trailing_bytes=len(trailer),raw_record_reconstruction_verified=True,
                  source_cells=cells,source_flat_shapes=len(arows),layoutml_flat_shapes=len(brows),
                  source_shape_types=dict(Counter(r['type'] for r in arows)),
                  layoutml_shape_types=dict(Counter(r['type'] for r in brows)),
                  surface_ports=len(ports),geometry_equal=report['geometry_equal'],
                  differing_layers=sum(x['xor_area_um2']!=0 for x in diffs),
                  artifacts={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in OUT.iterdir()
                             if p.is_file() and p.suffix in ('.txt','.lml','.json','.cdl') and p.name!='manifest.json'})
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:manifest[key] for key in ['source_records','source_flat_shapes','layoutml_flat_shapes',
                                                   'surface_ports','geometry_equal','differing_layers']},indent=2))

if __name__=='__main__':
    main()
