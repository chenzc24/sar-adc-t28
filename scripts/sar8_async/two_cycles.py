"""Two-period observation of unchanged native logic, then truthful timing plots."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.text import Text
from oa import ROOT,OUT
from simulate import source,deck,defaults,run
from suite import statement,monitor_rows
from audit import normalized_blocks
from analyze import load,edges,at

CASE="two_cycles_keynodes_aps_01"
FIG=ROOT/"docs/figures/sar8_async_two_cycles"
SUMMARY=ROOT/"verification/sar8_async/two_cycle_summary.json"

# All displayed raw nodes are explicitly saved; no timing state is guessed
# from a schematic, stimulus expression or separate simulation.
GROUPS={
    "frame": ["RST_N","SAMPLE","HOLD_START","PREPARE","DEADLINE","XCTRL.WORK_RST"],
    "ownership": ["XCTRL.SYS_RST","XCTRL.ACCEPT","XCTRL.HOLD","XCTRL.KILL","BASE","BUSY"],
    "sequence": ["XCTRL.TRIAL","XCTRL.EVAL","CAPTURE","XCTRL.RESET","ADVANCE","PUBLISH"],
    "comparator": ["COMP_P","COMP_N","CMP_CLK","CMP_RESET","XCTRL.DATA","XCTRL.DEC_VALID"],
    "guards": ["XCTRL.RESET_OK","XCTRL.BAD","XCTRL.LAST","XCTRL.XSEQ.TD","XCTRL.XCMPIF.RV_D","XCTRL.XCMPIF.CR_D"],
    "publication": ["XCTRL.COMMIT","XCTRL.XSTATUS.PUB_D","VALID","FAULT","XCTRL.XSEQ.CAP_D","XCTRL.XSEQ.ADV_D"],
    "analog_plant": ["VIN","TOPP","TOPN","VDD"],
}
TOKENS=[f"XCTRL.T{i}" for i in range(7,-1,-1)]
WORK=[f"XCTRL.W{i}" for i in range(7,-1,-1)]
TRIAL=[f"CODE{i}" for i in range(7,-1,-1)]
OUTPUT=[f"D{i}" for i in range(7,-1,-1)]
SEL0=[f"SEL0_{i}" for i in range(7,-1,-1)]
SEL1=[f"SEL1_{i}" for i in range(7,-1,-1)]
SIGNALS=list(dict.fromkeys(sum(GROUPS.values(),[])+TOKENS+WORK+TRIAL+OUTPUT+SEL0+SEL1))


def simulate():
    original=source("tb_sar8a_logic","recovery")
    assert normalized_blocks(original)==normalized_blocks(source("tb_sar8a_logic","human_final"))
    text=statement(original,"VVIN","VVIN (VIN 0) vsource type=pwl wave=[0 0.123 101n 0.123 102n -0.3 202n -0.3]")
    assert normalized_blocks(text)==normalized_blocks(original),"DUT mutation"
    text=deck(text,defaults(),"202n",SIGNALS,maxstep="200p")
    text+='\nXOBSERVER (VDD 0 SAMPLE CMP_CLK CAPTURE ADVANCE VALID FAULT D7 D6 D5 D4 D3 D2 D1 D0) sar8a_monitor\n'
    text+='ahdl_include "sar8a_monitor.va"\n'
    result=run(CASE,text,scope="unchanged_native_async_logic_two_period_observation_ideal_ADC_plant",
               includes=[ROOT/"models/veriloga/sar8a_monitor.va"],mode="aps")
    assert result["ok"],result["errors"]


def decode(w,nets):
    return sum((1<<(len(nets)-1-i))*(w[n.lower()]>.45).astype(int) for i,n in enumerate(nets))


def reduce_display(t,v,lo,hi,bins=2800):
    """Keep actual first/min/max/last samples per display bin, never averages.

    This bounds vector-figure size without hiding narrow pulses/undershoot.
    Analysis always uses full original solver samples.
    """
    ix=np.flatnonzero((t>=lo)&(t<=hi));assert len(ix)>1
    if len(ix)<4*bins:return t[ix],v[ix]
    bucket=np.minimum(bins-1,((t[ix]-lo)*bins/(hi-lo)).astype(int))
    starts=np.r_[0,np.flatnonzero(np.diff(bucket))+1];stops=np.r_[starts[1:],len(ix)]
    keep=[]
    for a,b in zip(starts,stops):
        seg=ix[a:b]
        keep.extend((int(seg[0]),int(seg[np.argmin(v[seg])]),int(seg[np.argmax(v[seg])]),int(seg[-1])))
    keep=np.unique(keep)
    return t[keep],v[keep]


def save(fig,name,vector=False):
    FIG.mkdir(parents=True,exist_ok=True)
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer();box=fig.bbox
    for artist in fig.findobj(Text):
        if not artist.get_visible() or not artist.get_text().strip():continue
        b=artist.get_window_extent(renderer)
        assert b.x0>=-2 and b.y0>=-2 and b.x1<=box.width+2 and b.y1<=box.height+2,(name,artist.get_text(),b)
    fig.savefig(FIG/(name+".png"),dpi=160)
    if vector:
        buffer=io.StringIO();fig.savefig(buffer,format="svg")
        # Matplotlib path records end in spaces; normalize generated text
        # without changing any coordinate or the rendered geometry.
        text="\n".join(line.rstrip() for line in buffer.getvalue().splitlines())+"\n"
        (FIG/(name+".svg")).write_text(text,encoding="utf-8",newline="\n")
    plt.close(fig)


def phase_background(ax,w,*,labels=False):
    acq=edges(w,"SAMPLE");ends=edges(w,"SAMPLE",rising=False)
    starts=edges(w,"HOLD_START");outcomes=np.sort(np.r_[edges(w,"VALID"),edges(w,"FAULT")])
    for a,b in zip(acq[:2],ends[:2]):
        ax.axvspan(a,b,color="#2176ae",alpha=.07,zorder=0)
        if labels:ax.text((a+b)/2,1.01,"采样",transform=ax.get_xaxis_transform(),ha="center",va="bottom",color="#21648c")
    for a in starts[:2]:
        matches=outcomes[(outcomes>a)&(outcomes<100*(int(a//100)+1))]
        assert len(matches),"No same-frame outcome for conversion shading"
        b=matches[0]
        ax.axvspan(a,b,color="#188b5b",alpha=.06,zorder=0)
        if labels:ax.text((a+b)/2,1.01,"异步转换",transform=ax.get_xaxis_transform(),ha="center",va="bottom",color="#18734f")
    ax.axvline(acq[1],color="#a54138",lw=.8,ls="--",alpha=.7)


def raw_panels(w,panels,name,title,lim=(0,202),*,annotations=None,zero=False):
    fig,axes=plt.subplots(len(panels),1,figsize=(12,2*len(panels)+1.1),sharex=True)
    axes=np.atleast_1d(axes);t=w["time"]*1e9
    for ax,(label,nets) in zip(axes,panels):
        vals=[]
        for j,net in enumerate(nets):
            v=w[net.lower()];tx,vy=reduce_display(t,v,*lim)
            ax.plot(tx,vy,lw=1,color=("#176c96","#bf6314","#764ba2")[j%3],
                    ls=("-","--",":")[j%3],label=net.replace("XCTRL.",""))
            vals.extend((float(v[(t>=lim[0])&(t<=lim[1])].min()),float(v[(t>=lim[0])&(t<=lim[1])].max())))
        low=min(vals);high=max(vals);pad=max(.055,.12*(high-low));ax.set_ylim(low-pad,high+pad)
        ax.set_yticks([y for y in ax.get_yticks() if low-pad<=y<=high+pad])
        ax.set_ylabel(label+"\n(V)",fontsize=10);ax.grid(alpha=.18)
        if len(nets)>1:ax.legend(loc="upper right",fontsize=9,ncol=min(3,len(nets)))
        if lim==(0,202):phase_background(ax,w)
        if zero:ax.axhline(0,color="#555555",lw=.65,ls=":")
        ax.spines[["top","right"]].set_visible(False)
    if annotations:
        for row,x,y,text in annotations:
            axes[row].annotate(text,(x,y),xytext=(.51,.18),textcoords="axes fraction",fontsize=10,
                               arrowprops=dict(arrowstyle="->",color="#a54138"),color="#a54138")
    axes[-1].set_xlim(*lim);axes[-1].set_xlabel("Time (ns)")
    axes[-1].set_xticks([x for x in axes[-1].get_xticks() if lim[0]<=x<=lim[1]])
    fig.suptitle(title,fontsize=13,y=.985)
    fig.subplots_adjust(left=.16,right=.975,top=.94,bottom=.065,hspace=.17)
    save(fig,name)


def lanes(w,rows,name,title,*,buses=(),overview=False):
    t=w["time"]*1e9;n=len(rows)+len(buses)
    height=max(5.2,.47*n+2.0)
    fig,ax=plt.subplots(figsize=(12,height))
    positions=np.arange(n)[::-1];names=[]
    for y,(label,net) in zip(positions,rows):
        v=w[net.lower()];tx,vy=reduce_display(t,v,0,202)
        ax.plot(tx,y+.65*vy/.9,lw=.9,color="#176c96")
        ax.hlines(y,0,202,color="#c5ccd0",lw=.45);names.append(label)
    for y,(label,nets) in zip(positions[len(rows):],buses):
        v=decode(w,nets);ix=np.r_[0,np.flatnonzero(np.diff(v))+1,len(t)-1]
        decimal=label in ("DOUT","OUTPUT")
        ax.hlines([y+.09,y+.57],0,202,color="#466472",lw=.65)
        for a,b in zip(ix[:-1],ix[1:]):
            x0,x1=float(t[a]),float(t[b]);val=int(v[a])
            ax.vlines(x0,y+.09,y+.57,color="#466472",lw=.7)
            if x1-x0>=3.8:ax.text((x0+x1)/2,y+.34,str(val) if decimal else f"{val:02X}",ha="center",va="center",fontsize=8.5)
        names.append(label+(" [dec]" if decimal else " [hex]"))
    ax.set_yticks(positions+.33,names,fontsize=9)
    ax.tick_params(axis="y",length=0,pad=8)
    ax.set_xlim(0,202);ax.set_ylim(-.5,n+.5);ax.set_xlabel("Time (ns)")
    ax.set_xticks(np.arange(0,201,10));ax.grid(axis="x",alpha=.16)
    ax.spines[["top","right","left"]].set_visible(False)
    phase_background(ax,w,labels=True)
    if overview:
        caps=edges(w,"CAPTURE")
        for i,ct in enumerate(caps):
            ax.text(ct,n+.24,f"b{7-i%8}",ha="center",va="center",fontsize=8,color="#176c96")
    fig.suptitle(title,fontsize=13,y=.99)
    fig.text(.19,.12/height,"蓝底：采样；绿底：转换；红虚线：第二周期采样沿。每条电压线独立基线：0 → 0.9 V。",fontsize=9)
    fig.subplots_adjust(left=.19,right=.98,top=1-.85/height,bottom=1.0/height)
    save(fig,name,vector=True)


def plot():
    font_path=Path("C:/Windows/Fonts/msyh.ttc")
    if font_path.exists():
        font_manager.fontManager.addfont(font_path)
        plt.rcParams["font.family"]=font_manager.FontProperties(fname=font_path).get_name()
    plt.rcParams.update({"axes.unicode_minus":False,"font.size":10,"svg.fonttype":"none","path.simplify":False})
    w=load(CASE);rows,log=monitor_rows(CASE)
    assert len(rows)==2,rows
    assert all(r["code"]==want and r["cap"]==r["eval"]==r["adv"]==8 and r["valid"]==1 and r["fault"]==0
               for r,want in zip(rows,(145,85))),rows
    assert {n.lower() for n in SIGNALS}<set(w),"Missing real trace"
    rises=edges(w,"SAMPLE");assert len(rises)==3
    assert np.allclose(np.diff(rises),100,atol=1e-6)
    assert all(at(w,f"D{i}",120)>.45 if 145&(1<<i) else at(w,f"D{i}",120)<.45 for i in range(8))
    cmi=len(re.findall(r"WARNING \(CMI-",log));suppressed=sum(map(int,re.findall(r"(\d+) warnings suppressed",log)))
    t=w["time"]*1e9;m=(t>=100.9)&(t<=102);ix=np.flatnonzero(m);j=ix[np.argmin(w["capture"][m])]
    boundaries=[]
    for sample in rises[1:]:
        mask=(t>=sample-.1)&(t<=sample+.8);indices=np.flatnonzero(mask)
        i=indices[np.argmin(w["capture"][mask])]
        boundaries.append(dict(sample_ns=float(sample),capture_min_ns=float(t[i]),
            capture_min_v=float(w["capture"][i]),context="between requested periods" if sample<150 else "after second period, closing context"))
    result=json.loads((OUT/"results"/(CASE+".json")).read_text())
    simulated=(OUT/"decks"/(CASE+".scs")).read_text(encoding="utf-8")
    assert normalized_blocks(simulated)==normalized_blocks(source("tb_sar8a_logic","recovery"))
    proof=dict(case=CASE,scope="native_controller_ideal_sampled_DAC_and_comparator_plant",
        native_full_ADC=False,execution_ok=True,functional_pass=True,qualified=False,
        all_saved_traces_finite=True,native_subcircuits_unchanged=True,
        mode=result["mode"],model_sha256=result["model_sha256"],
        simulator_version=re.search(r"(?m)^Version (.+)$",log)[1].strip(),
        mos_section="ttmacro_mos_moscap",supply_v=.9,temperature_c=27,maxstep_s=200e-12,
        exact_sampling_edges_ns=rises.tolist(),sampling_periods_ns=np.diff(rises).tolist(),
        frames=rows,saved_voltage_nodes=len(SIGNALS),signal_groups=GROUPS,
        token= TOKENS,working_word=WORK,trial_word=TRIAL,output_word=OUTPUT,sel0=SEL0,sel1=SEL1,
        valid_edges_ns=edges(w,"VALID").tolist(),commit_edges_ns=edges(w,"XCTRL.COMMIT").tolist(),
        capture_edges_ns=edges(w,"CAPTURE").tolist(),
        cross_frame_capture_min_v=float(w["capture"][j]),cross_frame_capture_min_ns=float(t[j]),
        reset_boundaries=boundaries,
        cross_frame_capture_half_supply_rises=edges(w,"CAPTURE")[(edges(w,"CAPTURE")>=100.9)&(edges(w,"CAPTURE")<=102)].tolist(),
        printed_CMI_warnings=cmi,suppressed_warnings=suppressed,soa_clean=cmi==0 and suppressed==0,
        raw_saved_export_sha256=hashlib.sha256(source("tb_sar8a_logic","recovery").encode()).hexdigest(),
        simulation_deck_sha256=json.loads((OUT/"results"/(CASE+".json")).read_text())["deck_sha256"],
        display_reduction="Actual first/min/max/last samples per time bin; full samples used for analysis",
        bus_decoding="Bit7 MSB, threshold0.45V; transient words are NOT final ADC outputs",
        original_fault_case="recovery_fault_stuck_aps, first two periods: success then intentionally stuck comparator")
    SUMMARY.write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
    overview=[(n,n) for n in ("RST_N","SAMPLE","HOLD_START","DEADLINE","PREPARE")]
    overview += [(n,"XCTRL."+n) for n in ("WORK_RST","ACCEPT","HOLD","TRIAL","RESET_OK","EVAL")]
    overview += [(n,n) for n in ("CMP_CLK","COMP_P","COMP_N")]
    overview += [("DEC_VALID","XCTRL.DEC_VALID"),("CAPTURE","CAPTURE"),("RESET","XCTRL.RESET"),
                 ("ADVANCE","ADVANCE"),("PUBLISH req","PUBLISH"),("COMMIT","XCTRL.COMMIT"),
                 ("VALID","VALID"),("FAULT","FAULT"),("BASE","BASE")]
    lanes(w,overview,"two_cycles_overview","异步 SAR · 两个完整采样周期 · 原生控制器 / 理想 ADC plant · APS / TT 0.9 V 27°C",
          buses=[("TOKEN",TOKENS),("WORK",WORK),("TRIAL CODE",TRIAL),("DOUT",OUTPUT)],overview=True)
    titles={"frame":"帧输入与工作复位","ownership":"启动、HOLD 与参考所有权","sequence":"异步序列状态",
            "comparator":"比较器轨道与合格判决","guards":"复位确认、末位与保护延时","publication":"末位发布、锁存与状态","analog_plant":"理想输入 / DAC plant 的模拟节点（非物理 CDAC）"}
    for group,nets in GROUPS.items():
        raw_panels(w,[(n.replace("XCTRL.",""),[n]) for n in nets],"nodes_"+group,
                   titles[group]+" · 两周期实测电压 · APS / TT")
    for name,nets,title in (("token",TOKENS,"one-hot token"),("work",WORK,"工作字 W[7:0]"),
            ("trial",TRIAL,"试探字 CODE[7:0]"),("output",OUTPUT,"输出字 DOUT[7:0]"),
            ("sel0",SEL0,"参考低端选择 SEL0[7:0]"),("sel1",SEL1,"参考高端选择 SEL1[7:0]")):
        lanes(w,[(n.replace("XCTRL.",""),n) for n in nets],"bits_"+name,title+" · 原生节点电压",
              buses=[(name.upper(),nets)])
    raw_panels(w,[("TRIAL / guard",["XCTRL.TRIAL","XCTRL.XSEQ.TD"]),("CMP_CLK",["CMP_CLK"]),
        ("Comparator rails",["COMP_P","COMP_N"]),("DEC_VALID",["XCTRL.DEC_VALID"]),
        ("CAPTURE",["CAPTURE"]),("RESET / ADVANCE",["XCTRL.RESET","ADVANCE"])],
        "one_bit_detail","一位握手放大 · 从试探 / 比较到锁存 / 复位 / 推进",lim=(43,53.2))
    raw_panels(w,[("SAMPLE / WORK_RST",["SAMPLE","XCTRL.WORK_RST"]),("KILL",["XCTRL.KILL"]),
        ("WORK bit7 / bit0",["XCTRL.W7","XCTRL.W0"]),("CAPTURE",["CAPTURE"]),
        ("CMP_CLK",["CMP_CLK"]),("VALID / FAULT",["VALID","FAULT"])],"cross_frame_detail",
        "跨帧采样 / 复位放大 · 保留真实 CAPTURE 下冲",lim=(100.85,101.8),zero=True,
        annotations=[(3,float(t[j]),float(w["capture"][j]),f'{w["capture"][j]*1000:.2f} mV @ {t[j]:.3f} ns')])
    last=boundaries[-1]
    raw_panels(w,[("SAMPLE / WORK_RST",["SAMPLE","XCTRL.WORK_RST"]),("KILL",["XCTRL.KILL"]),
        ("WORK bit6 / bit0",["XCTRL.W6","XCTRL.W0"]),("CAPTURE",["CAPTURE"]),
        ("CMP_CLK",["CMP_CLK"]),("VALID / FAULT",["VALID","FAULT"])],"closing_frame_detail",
        "第二周期结束后的复位上下文 · 此处仍有 CMI 器件应力告警",lim=(200.85,201.8),zero=True,
        annotations=[(3,last["capture_min_ns"],last["capture_min_v"],
                      f'{last["capture_min_v"]*1000:.2f} mV @ {last["capture_min_ns"]:.3f} ns')])
    fault=load("recovery_fault_stuck_aps")
    raw_panels(fault,[("SAMPLE",["SAMPLE"]),("CMP_CLK",["CMP_CLK"]),("CAPTURE",["CAPTURE"]),
         ("ADVANCE",["ADVANCE"]),("VALID / FAULT",["VALID","FAULT"]),("BASE",["BASE"])],
         "fault_comparison","旧故障对照 · 第一周期成功 / 第二周期人为卡住比较器 · 不是两次正常转换")
    print(json.dumps({k:proof[k] for k in ("frames","saved_voltage_nodes","valid_edges_ns",
        "cross_frame_capture_min_v","cross_frame_capture_min_ns","soa_clean")},indent=2))


def main():
    ap=argparse.ArgumentParser();ap.add_argument("command",choices=["simulate","plot"]);args=ap.parse_args()
    if args.command=="simulate":simulate()
    else:plot()


if __name__=="__main__":main()
