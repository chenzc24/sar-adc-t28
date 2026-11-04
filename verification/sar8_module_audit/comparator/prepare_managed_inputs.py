"""Local-only packaging of accepted D2 fixtures; never creates shared recipes."""
from __future__ import annotations
import json
from pathlib import Path
import build_d_fixture as d

HERE = Path(__file__).resolve().parent
OUT = HERE / "managed_inputs" / "d2"
STREAM_SOURCE = d.ROOT / "output/sar8_physical_repair/sar8fix-loaded-both-rx2-end210-sscold/stream.cpp"
STREAM_SHA = "3452d0a660c712d25caddf6da41e20996012ffadd4a9604b8cfe3f0c26519827"
LOADED_REMOTE = d.ROOT / "scripts/sar8_physical_repair/loaded_remote.py"
NAMES = ["vdd!", "cmp_clk", "topp", "topn", "xdut.comp_p", "xdut.comp_n",
         "xdut.xcomp.x", "xdut.xcomp.y", "xdut.xctrl.xtim.pr", "xdut.xctrl.xtim.nr",
         "xdut.xctrl.xtim.raw", "xdut.xctrl.xtim.dec", "xdut.xctrl.data",
         "xdut.xctrl.phi_w", "d0", "reg_reset"]
EVENTS = ["cmp_clk", "xdut.comp_p", "xdut.comp_n", "xdut.xctrl.xtim.pr",
          "xdut.xctrl.xtim.nr", "xdut.xctrl.xtim.raw", "xdut.xctrl.xtim.raw_d",
          "xdut.xctrl.xtim.dec", "xdut.xctrl.data", "xdut.xctrl.phi_w", "d0", "reg_reset"]


def stream_source():
    if d.sha(STREAM_SOURCE.read_bytes()) != STREAM_SHA:
        raise ValueError("Frozen loaded stream changed")
    text = STREAM_SOURCE.read_text()
    # Existing implementation otherwise silently ignores the final60ns.
    assert text.count("f<2") == 2 and text.count("100e-9") == 2
    text = text.replace("f<2", "f<1").replace("100e-9", "260e-9")
    declaration = r'''
 vector<string> snames;vector<int>sidx;vector<double>sprev;string sline;
 ifstream sfile(config+"snapshot_nodes.txt");while(getline(sfile,sline))if(!sline.empty())snames.push_back(sline);
 struct Check{string label;double at;};vector<Check>checks;size_t ci=0;
 ifstream cfile(config+"check_times.txt");while(getline(cfile,sline)){istringstream z(sline);Check c;z>>c.label>>c.at;if(!c.label.empty())checks.push_back(c);}
 ofstream sout(prefix+".samples.tsv");sout<<setprecision(17)<<"kind\tlabel\ttime_s";for(auto&n:snames)sout<<'\t'<<n;sout<<'\n';
 ofstream lout(prefix+".reset90.tsv");lout<<setprecision(17);
 vector<string>lnames={"xdut.comp_p","xdut.comp_n","xdut.xcomp.x","xdut.xcomp.y"};vector<int>lidx;vector<double>lprev;
 vector<int>triggeridx;vector<double>triggerprev;
'''
    anchor = " auto snapshot=[&](){"
    assert text.count(anchor) == 1
    text = text.replace(anchor, declaration + "\n" + anchor)
    init = r'''
    for(auto&n:snames)sidx.push_back(index(n));sprev.resize(sidx.size());
    for(auto&n:lnames)lidx.push_back(index(n));lprev.resize(lidx.size());
    triggeridx={index("cmp_clk"),index("xdut.xctrl.phi_w")};triggerprev.resize(2);
'''
    anchor = '    ofstream cols(prefix+".columns");'
    assert text.count(anchor) == 1
    text = text.replace(anchor, init + "\n" + anchor)
    capture = r'''
  auto sample=[&](const string&kind,const string&label,double at){
   double f=(t==oldtime?1:(at-oldtime)/(t-oldtime));sout<<kind<<'\t'<<label<<'\t'<<at;
   for(size_t j=0;j<sidx.size();++j)sout<<'\t'<<(sprev[j]+f*(val(sidx[j])-sprev[j]));sout<<'\n';
  };
  for(size_t j=0;j<triggeridx.size();++j){double now=val(triggeridx[j])-.5*val(supplyidx),before=triggerprev[j];
   if(oldtime>=0 && ((before<0&&now>=0)||(before>0&&now<=0))){double at=oldtime-before*(t-oldtime)/(now-before);
    sample(j==0?(now>before?"clock_rise":"clock_fall"):(now>before?"write_rise":"write_fall"),j==0?"cmp_clk":"phi_w",at);}
   triggerprev[j]=now;
  }
  if(oldtime>=0)while(ci<checks.size()&&checks[ci].at<=t){
   if(checks[ci].at<oldtime)throw runtime_error("missed fixed checkpoint");
   sample("fixed",checks[ci].label,checks[ci].at);++ci;
  }
  for(size_t j=0;j<lidx.size();++j){double now=val(lidx[j])-.9*val(supplyidx),before=lprev[j];
   if(oldtime>=0&&((before<0&&now>=0)||(before>0&&now<=0)))lout<<lnames[j]<<'\t'<<(now>before?1:0)<<'\t'<<(oldtime-before*(t-oldtime)/(now-before))<<'\n';
   lprev[j]=now;
  }
  for(size_t j=0;j<sidx.size();++j)sprev[j]=val(sidx[j]);
'''
    anchor = "  oldtime=t;++points;"
    assert text.count(anchor) == 1
    text = text.replace(anchor, capture + "\n" + anchor)
    return text


def prepare():
    frozen = d.DEST
    manifest = json.loads((frozen / "manifest.json").read_text())
    for name, sha in manifest["files"].items():
        assert d.sha((frozen / name).read_bytes()) == sha, name
    cells = d.blocks((frozen / "cells.scs").read_text())
    root_ports = d.ports(cells["audit_comparator_d"])
    binding = {p: p for p in root_ports}
    binding.update(VDD="VDD!", VSS="0")
    flat = d.flatten(cells, "audit_comparator_d", binding)
    records, pairs, indexes = [], [], {}
    for instance, item in sorted(flat.items()):
        model = item["model"]
        if not model.startswith(("nch_", "pch_")):
            continue
        if model not in ["nch_mac", "pch_mac", "nch_18_mac", "pch_18_mac", "nch_na18_mac"]:
            raise ValueError("Unclassified model " + model)
        group = ("comparator" if instance.startswith("XDUT.XCOMP.") else
                 "receiver" if any(p in instance for p in [".XTIM.X002.", ".XTIM.X003."]) else
                 "register" if ".XBIT" in instance else "forward_detection")
        nodes = dict(zip("dgsb", item["nodes"]))
        for a, b in ["ds", "gs", "gd", "gb", "bd", "bs"]:
            pair = tuple(sorted([nodes[a].lower(), nodes[b].lower()]))
            if pair not in indexes:
                indexes[pair] = len(pairs);pairs.append(pair)
            records.append(dict(instance=instance, model=model, group=group,
                                terminal=a+b, nodes=list(pair), pair_index=indexes[pair],
                                limit_v=.99 if model in ["nch_mac", "pch_mac"] else 1.98))
    assert len(records) == 467 * 6
    checks = [("initial", 0.)]
    for i, start in enumerate(d.START_NS):
        checks.extend([("pre_update_"+str(i), (start-8-.1)*1e-9),
                       ("pre_compare_"+str(i), (start-.1)*1e-9),
                       ("pre_fall_"+str(i), (start+11.9)*1e-9)])
    checks.append(("end", 260e-9))
    selected = sorted(set(NAMES + EVENTS + ["vvdd:1"]))
    assert 8*(len(selected)+1)*13002 < 8*1024*1024
    common = {
        "mapping.json": d.json_text(dict(records=records, pairs=pairs, stop_s=260e-9,
            compact_collection_max_bytes=32*1024*1024,
            measurement_scope="native crossings/interpolation; 90% reset is a reported level definition, not timing qualification",
            cycles=[dict(index=i, start_ns=start, expected_DATA=int(sign>0), expected_D0=int(sign>0))
                    for i,(start,sign) in enumerate(zip(d.START_NS,d.SIGNS))])),
        "pairs.txt": "\n".join(" ".join(p) for p in pairs)+"\n",
        "selected.txt": "\n".join(selected)+"\n",
        "events.txt": "\n".join(EVENTS)+"\n",
        "products.txt": "VDD vdd! vvdd:1\n",
        "snapshot_nodes.txt": "\n".join(NAMES)+"\n",
        "check_times.txt": "\n".join(label+" "+format(at,'.17g') for label,at in checks)+"\n",
        "stream.cpp": stream_source()
    }
    common["package_manifest.json"] = d.json_text(dict(
        status="local_only_not_Spectre_compiled", simulation_pass=None,
        frozen_v2_manifest_sha256=d.sha((frozen/'manifest.json').read_bytes()),
        frozen_stream_source=str(STREAM_SOURCE.relative_to(d.ROOT)).replace('\\','/'),
        frozen_stream_sha256=STREAM_SHA,
        reused_loaded_remote_sha256=d.sha(LOADED_REMOTE.read_bytes()),
        adaptations=["single full260ns native energy interval", "native PHI_W/clock snapshots", "fixed pre-update/pre-compare checkpoints", "native90% precharge crossings"],
        files={name:d.sha(text.encode()) for name,text in common.items()},
        compact_binary_upper_bound_bytes=8*(len(selected)+1)*13002,
        all_MOS_pairs=len(records), unique_pairs=len(pairs)))
    proposals = []
    for label in d.CORNERS:
        run = "sar8audit-comp-d2-"+label
        inputs = [dict(source=str((frozen/'cells.scs').relative_to(d.ROOT)).replace('\\','/'),name='cells.scs'),
                  dict(source=str((frozen/(label+'.scs')).relative_to(d.ROOT)).replace('\\','/'),name='test.scs'),
                  dict(source=str(LOADED_REMOTE.relative_to(d.ROOT)).replace('\\','/'),name='loaded_remote.py'),
                  dict(source=str((HERE/'remote_reduce.py').relative_to(d.ROOT)).replace('\\','/'),name='remote_reduce.py')]
        inputs += [dict(source=str((OUT/name).relative_to(d.ROOT)).replace('\\','/'),name=name) for name in common]
        for item in inputs:
            if item['name'] in common:
                item['sha256']=d.sha(common[item['name']].encode())
            else:
                item['sha256']=d.sha((d.ROOT/item['source']).read_bytes())
        proposals.append(dict(run_id=run, design_id='sar8_comparator_D2_diagnostic',entry='test.scs',
            analyzer='remote_reduce.py', inputs=inputs,expected_stop_s=260e-9,
            summary_signals=['CMP_CLK','XDUT.COMP_P','XDUT.COMP_N'],
            qualification_scope='Ideal-input comparator/receiver diagnostic; no ADC async timing or statistical qualification',
            oa_parity='netlist_only',
            test_conditions=dict(corner=d.CORNERS[label][0],vdd=d.CORNERS[label][1],temperature_c=d.CORNERS[label][2],noise=False,mismatch=False,PEX=False),
            resources=dict(threads=4,simulation_rss_mib=1024,simulation_virtual_mib=8192,
                analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=8192,
                simulation_wall_seconds=1800,analysis_wall_seconds=900,queue_timeout_seconds=7200),
            parent_only_create_recipe=True, collection_limit_bytes=32*1024*1024))
    common['parent_recipe_inputs.json']=d.json_text(proposals)
    return common


if __name__=='__main__':
    artifacts=prepare()
    d.emit(artifacts,OUT)
    print(d.json_text({'local_package':str(OUT),'files':list(artifacts),'remote_operations':0}))
