"""Freeze one source-bound clock export via the existing managed entry."""
import hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'scripts/management'))
import execution
def main():
    run='sar8phys-clock-reference-v1';files=[(R/'scripts/sar8_mc/physical_input/extract_reference.py','extract_reference.py'),(R/'scripts/sar8_campaign/native_stream.py','native_stream.py')]
    spec={'schema_version':1,'run_id':run,'kind':'analysis_only','source_run_id':'sar8mc-b-tt-nominal-v1','design_id':'sar8_l90_mmain2_stdcell_v1','entry':'extract_reference.py','analyzer':'extract_reference.py',
      'inputs':[{'source':p.relative_to(R).as_posix(),'name':n,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,n in files],
      'summary_signals':['sample','xdut.seq_sample','xdut.cmp_clk'],'expected_stop_s':1059e-9,'qualification_scope':'Native clock export only, source simulation remains read-only',
      'spectre_args':['+preset=mx','+mt=4','-preset_override','+lqtimeout','60'],
      'resources':{'threads':4,'simulation_rss_mib':1024,'simulation_virtual_mib':8192,'analysis_rss_mib':256,'analysis_virtual_mib':1024,'max_output_mib':32,'simulation_wall_seconds':3600,'analysis_wall_seconds':600,'queue_timeout_seconds':86400}}
    p=R/'management/recipes'/(run+'.yaml');p.write_text(json.dumps(spec,indent=2)+'\n')
    print(json.dumps(execution.register(str(p.relative_to(R)))))
    print(json.dumps(execution.phase('analyze',run,True)))
if __name__=='__main__':main()
