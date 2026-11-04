"""Python 2.7/3 bounded comparison of native VA events and independent pin probes."""
from __future__ import print_function
import argparse,csv,hashlib,json,os,re


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True);parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();base=args.run_dir
    context=json.load(open(base+'/inputs/context.json'))
    expected={}
    for row in csv.DictReader(open(base+'/inputs/expected.csv')):
        expected[(int(row['id']),int(row['frame']))]=[float(row[k]) for k in ['held','code','cmp','write','update','cap','sample_close','seq_close','last_update','finished','problem','issue_bit','pin_code']]
    records={};probes={};warnings=set();invalid=[]
    for line in open(base+'/spectre.out'):
        warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
        if 'BMODEL_INVALID,' in line:invalid.append(line.strip())
        m=re.search(r'BMODEL,([^\r\n]+)',line)
        if m:
            fields=m.group(1).split(',');key=(int(fields[0]),int(fields[1]))
            assert key not in records,'Duplicate model event'
            records[key]=list(map(float,fields[2:]))
        m=re.search(r'BPROBE,([^\r\n]+)',line)
        if m:
            fields=m.group(1).split(',');key=(int(fields[0]),int(fields[1]))
            assert key not in probes,'Duplicate output probe'
            probes[key]=int(fields[2])
    assert not invalid,invalid[:2]
    assert len(expected)==context['expected_records']
    assert set(records)==set(expected),'Missing/extra native frame records'
    assert set(probes)==set(expected),'Missing/extra independent pin probes'
    failures=[];max_time_error=0.;maximum_input_error=0.;counts={}
    for key,want in sorted(expected.items()):
        got=records[key]
        assert len(got)==12
        maximum_input_error=max(maximum_input_error,abs(got[0]-want[0]))
        if abs(got[0]-want[0])>1e-9:failures.append([key,'input',got[0],want[0]])
        for index in [1,2,3,4,5,10,11]:
            if got[index]!=want[index]:failures.append([key,'field_'+str(index),got[index],want[index]])
        for index in [6,7,8,9]:
            error=abs(got[index]-want[index]);max_time_error=max(max_time_error,error)
            if error>context['time_tolerance_s']:failures.append([key,'time_'+str(index),got[index],want[index]])
        if probes[key]!=int(want[12]):failures.append([key,'output_pin_code',probes[key],want[12]])
        name=context['scenario_names'][key[0]]
        row=counts.setdefault(name,dict(frames=0,complete=0,deadline=0,stuck=0))
        row['frames']+=1
        row[{0:'complete',1:'deadline',2:'stuck'}[int(got[10])]]+=1
    h=hashlib.sha256()
    with open(base+'/spectre.out','rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    result=dict(analysis_complete=True,python_VA_crosscheck_pass=not failures,
        frame_records=len(records),independent_pin_probes=len(probes),
        frames_per_scenario=context['frames'],scenarios=counts,
        max_time_error_s=max_time_error,max_input_error_v=maximum_input_error,
        failures=failures[:30],failure_count=len(failures),warning_codes=sorted(warnings),
        context=context,spectre_log_sha256=h.hexdigest(),
        qualification='Behavioral algorithm and scheduling only; no transistor stress, noise-yield or PVT qualification')
    with open(args.output_dir+'/result.json','w') as out:json.dump(result,out,indent=2);out.write('\n')
    assert not failures,'VA/Python or independent output pin crosscheck failed'
    print('BEHAVIORAL_CROSSCHECK_OK',len(records),len(probes))


if __name__=='__main__':main()
