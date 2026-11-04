"""Audit bounded in-flight observer log snapshots; no raw-wave or live mutation."""
import csv,json,math,re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'verification/sar8_campaign/fft_live_audit'
LSB=1.8/256
FIELDS=['frame','code','compares','writes','updates','captures','early_code','valid','rail_error_v','aperture_s','source_v','held_v','final_top_v','conversion_s']
def q(v):return max(0,min(255,int(math.floor((v+.9)/LSB))))
def main():
    snap=json.loads((OUT/'snapshot.json').read_text());report={'snapshot_time':snap['beijing_time'],'variants':{}};allrows={}
    for label in ['a','b']:
        text=(OUT/(label+'_spectre_snapshot.out')).read_text()
        rows=[[float(x) for x in m.group(1).split(',')] for m in re.finditer(r'R4MEAS,([^\r\n]+)\r?\n',text)]
        assert all(len(r)==14 for r in rows)
        assert [int(r[0]) for r in rows]==list(range(len(rows)))
        allrows[label]=rows;warm=snap['runs'][label]['context']['warmup'];measured=rows[warm:]
        bad=[int(r[0]) for r in rows if r[2:6]!=[8,8,8,16] or r[1]!=r[6] or r[7]!=1 or not 0<r[13]<60e-9]
        item={'total_frames':len(rows),'warmup_frames':warm,'measured_frames':len(measured),'bad_protocol_or_validity_frames':bad,'first_frame':dict(zip(FIELDS,rows[0]))}
        for col,name in [(10,'source_aperture'),(11,'held')]:
            mismatches=[]
            for r in measured:
                ideal=q(r[col]);difference=int(r[1])-ideal
                if difference:
                    frac=(r[col]+.9)/LSB%1
                    mismatches.append({'frame':int(r[0]),'actual_code':int(r[1]),'ideal_code':ideal,'difference_lsb':difference,'nearest_ideal_boundary_distance_lsb':min(frac,1-frac)})
            item[name]={'mismatch_count':len(mismatches),'max_abs_difference_lsb':max([abs(r['difference_lsb']) for r in mismatches] or [0]),'mismatches':mismatches}
        t=np.array([r[9] for r in measured]);omega=2*np.pi*snap['runs'][label]['context']['frequency_hz'];X=np.column_stack((np.ones(len(t)),np.sin(omega*t),np.cos(omega*t)));coefs={};fits={}
        for name,y in [('source',np.array([r[10] for r in measured])),('held',np.array([r[11] for r in measured])),('codes',np.array([(r[1]+.5)*LSB-.9 for r in measured]))]:
            c=np.linalg.lstsq(X,y,rcond=None)[0];res=(y-X@c)/LSB;coefs[name]=c
            fits[name]={'offset_v':float(c[0]),'sin_v':float(c[1]),'cos_v':float(c[2]),'residual_max_lsb':float(max(abs(res))),'residual_rms_lsb':float(np.sqrt(np.mean(res**2)))}
        item['partial_sine_fit']=fits
        item['equivalent_held_lag_ns']=float(np.angle(complex(coefs['source'][1],coefs['source'][2])/complex(coefs['held'][1],coefs['held'][2]))/omega*1e9)
        item['conversion_ns']=[min(r[13] for r in measured)*1e9,max(r[13] for r in measured)*1e9]
        report['variants'][label]=item
        with (OUT/(label+'_frames.csv')).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(FIELDS+['ideal_from_source','ideal_from_held']);w.writerows(r+[q(r[10]),q(r[11])] for r in rows)
    a,b=allrows['a'],allrows['b'];common=min(len(a),len(b));report['ab_common_measured_frames']=common-8
    report['ab_different_codes']=[{'frame':int(x[0]),'a':int(x[1]),'b':int(y[1])} for x,y in zip(a[8:],b[8:]) if x[1]!=y[1]]
    report['limitations']=['In-flight observer records only; final native raw decode crosscheck pending','Ideal source-aperture mismatch includes effective tracking/aperture phase and gain errors','Held value is observer TOPP-TOPN at fixed frame+41.8ns, not an independent ideal ADC oracle','Partial sine fit removes DC/amplitude/phase; it is not final1024FFT nor proof of no distortion','CMI warnings retained; no electrical qualification']
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({v:{k:r[k] for k in ['total_frames','measured_frames','bad_protocol_or_validity_frames','equivalent_held_lag_ns','conversion_ns']} for v,r in report['variants'].items()},indent=2))
if __name__=='__main__':main()
