"""Frozen nominal-voltage PT copies; no source circuit changes."""
import hashlib,json,re
from setup import W,ROOT,write,recipe

cases=[]
for tag,corner,temp in [('tt','tt',27),('ff-cold','ff',-40),('ff-hot','ff',125),('ss-cold','ss',-40),('ss-hot','ss',125)]:
    for multi,source in [(4,'cmpdesign-edge-b2i2-ff-hot-v1'),(8,'cmpdesign-combo-a8-ff-hot-v1')]:
        run='cmpdesign-pt09-a%d-%s-v1'%(multi,tag)
        dest=W/'testbenches'/run;base=W/'testbenches'/source
        assert not dest.exists() and not (ROOT/'management/runs'/(run+'.yaml')).exists(),run
        dest.mkdir(parents=True)
        (dest/'dut.scs').write_bytes((base/'dut.scs').read_bytes())
        models=(base/'models.scs').read_text()
        assert models.count('ffmacro_mos_moscap')==1
        write(dest/'models.scs',models.replace('ffmacro_mos_moscap',corner+'macro_mos_moscap'))
        old=(base/'test.scs').read_text();lines=old.splitlines();changes=[]
        for i,line in enumerate(lines):
            if line.startswith('VCK '):
                prefix,wave=line.split('wave=[');tokens=wave.rstrip(']').split()
                assert len(tokens)%2==0
                for j in range(1,len(tokens),2):
                    assert float(tokens[j]) in (0,.99)
                    if float(tokens[j])==.99:tokens[j]='0.9'
                lines[i]=prefix+'wave=['+' '.join(tokens)+']'
            elif line.startswith('VSA4_'):
                assert 'dc=0.99' in line
                lines[i]=line.replace('dc=0.99','dc=0.9')
            elif line.startswith('simulatorOptions '):
                lines[i]=line.replace('temp=125 ', 'temp=%d '%temp)
            if line!=lines[i]:changes.append(line.split()[0])
        assert set(changes)<=set(['VCK','VSA4_driven','VSA4_held','simulatorOptions'])
        assert len([x for x in changes if x.startswith('VSA4_')])==2
        write(dest/'test.scs','\n'.join(lines)+'\n')
        cfg=json.loads((base/'measure.json').read_text())
        cfg.pop('single_variable',None);cfg.pop('combined_changes',None)
        cfg.update(run_id=run,vdd=.9,corner=corner,temperature_c=temp,
          pt09_provenance=dict(source_run_id=source,M2_M4_multi=multi,M3_M5_multi=2,M8_M9_multi=2,
          fixed_input_history=True,fixed_loads=True,fixed_edge_times=True,terminal_limit_unchanged=True))
        assert cfg['terminal_limit_V']==.99
        # Legacy variant metadata described an earlier sizing experiment, not this DUT.
        cfg.pop('variants',None)
        cfg['candidates']['A4'].update(input=2,precharge=2,precharge_latch=multi)
        write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
        recipe(run,dest,cfg['signals'],cfg['stop_s'],'edge500_reduce.py',dict(corner=corner,vdd=.9,temperature_c=temp,rise_ps=200,fall_ps=500,M2_M4_multi=multi,M3_M5_multi=2,M8_M9_multi=2,noise=False,mismatch=False,PEX=False))
        write(dest/'validation.json',json.dumps(dict(source_run_id=source,dut_byte_identical=True,changed_test_lines=changes,sha256={n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}),indent=2)+'\n')
        cases.append(run)
print('\n'.join(cases))
