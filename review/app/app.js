(function () {
  'use strict';
  const data = JSON.parse(document.getElementById('review-data').textContent);
  const flows = data.flows;
  const blocks = Object.fromEntries(flows.blocks.map(b => [b.id, b]));
  const values = ReviewMath.calculate(data.spec, data.context);
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const audit = data.evidence.find(e => e.id === 'current_audit');
  const obs = audit.observations;
  const hold = obs.find(o => o.metric === 'hold');
  const bottom = data.evidence.find(e => e.id === 'bottom_screen').observations[0];
  const decision = data.evidence.find(e => e.id === 'strongarm_interface').observations.find(o => o.unit === 's');
  const ab = data.evidence.find(e => e.id === 'fast_ab').observations;
  const fmt = (n, digits = 3) => Number(n).toFixed(digits);
  const tokens = {
    ...Object.fromEntries(Object.entries(values).filter(([,v]) => typeof v === 'number').map(([k,v]) => [k, fmt(v * 1000)])),
    bits: data.spec.converter.resolution_bits,
    rate: data.spec.converter.sample_rate_hz / 1e6,
    enob: data.spec.targets.enob_min_bits,
    span: data.spec.input.differential_range_v[1] - data.spec.input.differential_range_v[0],
    vdd: data.spec.supplies.vdd_v,
    sndr: fmt(values.sndr, 2),
    capacitance: fmt(values.capacitance * 1e15, 2),
    jitter_ps: data.spec.error_budget.clock_jitter_rms_ps,
    sample_ns: data.spec.timing_budget.sample_ns,
    conversion_ns: data.spec.timing_budget.conversion_ns,
    bit_ns: data.spec.timing_budget.bit_cycle_ns,
    audit_hold: fmt(hold.value * 1000),
    audit_hold_abs: fmt(Math.abs(hold.value) * 1000),
    hold_ratio: fmt(Math.abs(hold.value) / hold.limit, 1),
    input_current: fmt(obs.find(o => o.unit === 'A').value * 1e6),
    gap_loss: fmt(obs.find(o => o.label === '非重叠区输出变化').value * 1000),
    discharge_loss: fmt(obs.find(o => o.label === '栅放电区输出变化').value * 1000),
    bottom_hold: fmt(bottom.value * 1000, 5),
    decision_ps: fmt(decision.value * 1e12, 1),
    thick_hold: fmt(ab[0].value * 1000),
    split_bound: fmt(Math.abs(ab[1].value) * 1000)
  };
  const expand = text => String(text ?? '').replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (!(key in tokens)) throw new Error('Unknown flow token: ' + key);
    return tokens[key];
  });

  const pick=(g,id,x={})=>({...flows.graphs[g].nodes.find(n=>n.id===id),...x});
  const edge=(from,to,kind='next')=>({from,to,kind});
  const maps={};
  const configs={
    sampling:['sample_budget','sample_limit','sampling_branch'],
    cdac:['sample_budget','sample_limit','cdac_branch'],
    reference:['ref_budget','ref_limit',null],
    comparator:['cmp_budget','cmp_limit','cmp_branch'],
    clock:['clk_budget','clk_limit','clock_branch']
  };
  const result=id=>configs[id][2]?pick('workflow',configs[id][2]):{
    title:'Reference',line:'一阶约束已有；buffer 管级待验证',
    sub:'尚无完整物理 buffer 通过证据',detail:'目前只有参考网络的一阶建立约束，需要实现真实缓冲器并验证瞬态负载、输出阻抗和噪声。',tone:'planned',tag:'待设计',blocks:['reference']
  };
  maps.all={
    title:'从总指标到五个电路分支',
    note:'设计依赖图 · 每个电路 block 集中显示指标、进度和入口，不再分开查阅。',
    columns:5,
    nodes:[
      pick('theory','system',{row:1,col:2,span:3,title:'SAR ADC · 理论 benchmark 与架构基线',
        sub:'σ模拟 = √(σ总² − σ量化²) = {{analog}} mV RMS；σ总 {{total}} mV',
        detail:pick('theory','system').detail+' '+pick('theory','budget').detail+' '+pick('workflow','behavioral').detail+' '+pick('workflow','macro').detail}),
      ...Object.entries(configs).map(([id,[budget]],i)=>({
        ...result(id),id,row:2,col:i+1,span:1,title:blocks[id].title,blocks:[id],focus:id,
        line:id==='cdac'?'Cside ≥ {{capacitance}} fF（热噪声下限）':pick('theory',budget).line,sub:result(id).line,
        detail:blocks[id].description+' '+pick('theory',budget).detail+' '+result(id).detail
      })),
      pick('workflow','integrate',{row:3,col:2,span:3,title:'模块汇合 → 全管级 ADC → 版图后仿',
        detail:pick('workflow','integrate').detail+' '+pick('workflow','layout').detail})
    ],
    edges:Object.keys(configs).flatMap(id=>[edge('system',id,'allocate'),edge(id,'integrate','pending')])
  };
  const st=id=>pick('sampling_theory',id), sw=id=>pick('sampling_workflow',id);
  maps.sampling={
    title:'Bootstrap · 获取与关断，两条链一起审查',
    note:'VIN → 采样开关 → CDAC → 比较器；电荷保存在 CDAC。左侧看获取，右侧看关断后的电荷准确度。',
    columns:4,
    nodes:[
      {...st('sample_root'),row:1,col:1,span:4,canvas:'sampling'},
      {...st('cap'),row:2,col:1,span:2,title:'获取链 · 热噪声 → 电容 → Ron',
        line:'σsample ≤ {{sampling_noise}} mV RMS → Cside ≥ {{capacitance}} fF',
        sub:'40 ns RC 示例：Rs + Ron ≤ 21.242 kΩ',
        detail:st('random').detail+' '+st('cap').line+'。'+st('cap').detail+' '+st('rc').line+'。'+st('rc').detail},
      {...st('deterministic'),row:2,col:3,span:2,title:'关断链 · 独立的原始保持误差要求'},
      {...sw('ideal'),row:3,col:1,span:2},
      {...sw('driver'),row:3,col:3,span:2},
      {...sw('input_path'),row:4,col:1,span:2,title:'电流审计 → 去掉输入加载通路',
        line:'25.858 µA → 约 34.3 pA',
        sub:'厚栅 MN9 变体保持误差 {{thick_hold}} mV；仍失败',
        detail:sw('input_path').detail+' '+sw('fix').detail},
      {...sw('charge_loss'),row:4,col:3,span:2,title:'电荷审计 → 分离关断控制',
        line:'−8.755 → −{{split_bound}} mV，仍未达标',
        sub:'后者仅为理想分离门控边界，不是管级成果',
        detail:sw('charge_loss').detail+' '+sw('isolate').detail},
      {...sw('next_topology'),row:5,col:1,span:4,detail:sw('next_topology').detail+' '+sw('acceptance').detail}
    ],
    edges:[edge('sample_root','cap','allocate'),edge('sample_root','deterministic','allocate'),edge('cap','ideal','derive'),edge('deterministic','driver'),{...edge('ideal','driver'),axis:'horizontal'},edge('driver','input_path'),edge('driver','charge_loss'),edge('input_path','next_topology','pending'),edge('charge_loss','next_topology','pending')]
  };
  for(const [id,[budget,limit]] of Object.entries(configs)){
    if(id==='sampling')continue;
    maps[id]={title:blocks[id].title+' · 从约束到下一步',note:blocks[id].description,columns:4,nodes:[
      pick('theory',budget,{id:'requirement',row:1,col:1,span:4,canvas:id}),
      pick('theory',limit,{id:'constraint',row:2,col:1,span:4}),
      {...result(id),id:'result',row:3,col:1,span:4,focus:undefined},
      {id:'next',row:4,col:1,span:4,title:'下一步 / 验收缺口',line:{
        cdac:'扩大底板采样余量，同时解决应力告警',
        reference:'实现真实参考缓冲器，验证动态负载与噪声',
        comparator:'优化噪声与失调，再联合检查速度和回踢',
        clock:'落实真实非重叠时序、边沿与 jitter'
      }[id],sub:'模块通过后，回到全 ADC 联合验收',detail:'当前结果只覆盖上方注明的模型和条件。仍需对应管级电路、输入范围、PVT 和适用的噪声 / 失配检查，不能把单点结果升级为整体通过。',blocks:[id],tone:'planned'}
    ],edges:[edge('requirement','constraint','allocate'),edge('constraint','result'),edge('result','next','pending')]};
  }
  let state={focus:'all'}, graph, resizeFrame;
  for(const [module,map] of Object.entries(maps)) {
    if(module==='all')continue;
    for(const node of map.nodes) {
      const note=data.node_notes[module+'/'+node.id];
      if(!note)throw new Error('Missing node analysis: '+module+'/'+node.id);
      Object.assign(node,note);
    }
  }
  const ns='http://www.w3.org/2000/svg';
  function svgElement(tag,attrs={}) {
    const el=document.createElementNS(ns,tag);
    for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);
    return el;
  }
  function drawEdges() {
    if (!graph) return;
    const canvas = $('flow-canvas');
    const svg = $('flow-edges');
    const origin = canvas.getBoundingClientRect();
    svg.setAttribute('viewBox', `0 0 ${canvas.clientWidth} ${canvas.clientHeight}`);
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', canvas.clientHeight);
    svg.replaceChildren();
    const defs = svgElement('defs');
    for (const type of ['normal','tentative']) {
      const marker = svgElement('marker', {id:'arrow-'+type,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto'});
      marker.append(svgElement('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:type === 'normal' ? '#8193a8' : '#bc965c'}));
      defs.append(marker);
    }
    svg.append(defs);
    for (const edge of graph.edges) {
      const from = document.querySelector(`[data-node="${edge.from}"]`).getBoundingClientRect();
      const to = document.querySelector(`[data-node="${edge.to}"]`).getBoundingClientRect();
      const horizontal = edge.axis === 'horizontal';
      const x1 = (horizontal ? from.right : from.left + from.width / 2) - origin.left;
      const y1 = (horizontal ? from.top + from.height / 2 : from.bottom) - origin.top;
      const x2 = (horizontal ? to.left : to.left + to.width / 2) - origin.left;
      const y2 = (horizontal ? to.top + to.height / 2 : to.top) - origin.top;
      const middle = horizontal ? (x1+x2)/2 : (y1+y2)/2;
      const d = horizontal ? `M${x1},${y1} H${middle} V${y2} H${x2-3}` : `M${x1},${y1} V${middle} H${x2} V${y2-3}`;
      const tentative = ['allocate','pending'].includes(edge.kind);
      svg.append(svgElement('path',{d,class:'flow-edge '+(tentative ? 'tentative' : ''),'marker-end':`url(#arrow-${tentative ? 'tentative' : 'normal'})`,'data-from':edge.from,'data-to':edge.to}));
      if (edge.label) {
        const label = svgElement('text',{x:horizontal ? middle : (x1+x2)/2,y:horizontal ? y1-8 : middle-7,'text-anchor':'middle',class:'edge-label'});
        label.textContent = edge.label;
        svg.append(label);
      }
    }
  }


  function render(){
    graph=maps[state.focus];
    $('view').classList.toggle('module-view',state.focus!=='all');
    $('view').classList.toggle('single-chain',state.focus!=='all' && state.focus!=='sampling');
    $('flow-title').textContent=graph.title;
    $('flow-note').textContent=graph.note;
    $('breadcrumb').textContent=state.focus==='all'?'全 ADC / 设计总图':'全 ADC / '+blocks[state.focus].title;
    $('show-all').hidden=state.focus==='all';
    $('legend').innerHTML='<span><i class="solid"></i>推导 / 验证步骤</span><span><i class="dashed"></i>暂定分配 / 待完成</span>';
    $('flow-nodes').style.setProperty('--columns',graph.columns);
    $('flow-nodes').innerHTML=graph.nodes.map((n,i)=>`<article class="flow-node ${esc(n.tone||'')} ${state.focus==='sampling' && n.span===4?'wide-node':''}" style="grid-column:${n.col}/span ${n.span||1};grid-row:${n.row}" data-node="${n.id}">
      ${state.focus!=='all'?`<span class="node-index">${String(i+1).padStart(2,'0')} / ${esc(blocks[state.focus].subtitle)}</span>`:''}
      <span class="node-top"><b>${esc(n.title)}</b>${n.tag?`<small class="node-tag">${esc(n.tag)}</small>`:''}</span>
      <span class="node-line">${esc(expand(n.line))}</span><span class="node-sub">${esc(expand(n.sub))}</span>
      ${n.reasons?`<ul class="node-reasons">${n.reasons.map(reason=>`<li>${esc(expand(reason))}</li>`).join('')}</ul>`:''}
      ${n.focus?`<button class="branch-button" data-block="${n.focus}">进入模块分支 →</button>`:''}
      ${(n.figures||[]).filter(id=>data.figures[id].available).map(id=>`<button class="figure-button" data-figure="${id}">查看${esc(data.figures[id].kind)} ↗</button>`).join('')}
      <details class="inline-detail"><summary>展开依据与说明</summary><p>${esc(expand(n.detail))}</p></details>
      ${state.focus==='sampling' && ['sample_root','ideal','input_path','charge_loss'].includes(n.id)?`<button class="figure-button" data-topology="${n.id==='input_path'?'shared':n.id==='charge_loss'?'reset':'bootstrap'}">电路联动 · 抽象样例 ↗</button>`:n.canvas?`<details class="inline-detail canvas-inline"><summary>电路视图 · Canvas 预留</summary><p>${esc(blocks[n.canvas].description)} 尚未连接；此处预留对应模块原理图与相位 / 电荷路径。</p></details>`:''}
    </article>`).join('');
    $('budget-footnote').textContent=state.focus==='all'
      ?'初始分配可迭代，非唯一合理解。含量化的分配 RSS = '+fmt(values.rss*1000)+' mV，其中包含 '+fmt(values.distortion*1000)+' mV RMS 等效失真余量；采样与 CDAC 共享采样噪声预算，不重复计入。'
      :'已审阅实验快照；绿色表示做过该实验，不表示模块整体通过。';
    requestAnimationFrame(drawEdges);
  }
  document.addEventListener('click',e=>{
    const b=e.target.closest('button');
    if(b?.dataset.figure){
      const figure=data.figures[b.dataset.figure];
      $('figure-kind').textContent=figure.kind;
      $('figure-title').textContent=figure.title;
      $('figure-caption').textContent=figure.caption;
      $('figure-image').src=figure.src;
      $('figure-image').alt=figure.title+'。'+figure.caption;
      $('figure-dialog').showModal(); return;
    }
    if(b?.id==='close-figure'){$('figure-dialog').close();return;}
    const focus=b?.dataset.block || (b?.id==='show-all'?'all':null);
    if(!focus)return;
    state.focus=focus;
    history.pushState(null,'',focus==='all'?'#all':'#module/'+focus);
    render(); window.scrollTo(0,0);
  });
  function readHash(){
    const p=location.hash.slice(1).split('/');
    const focus=p[0]==='module'?p[1]:p[0];
    state.focus=Object.hasOwn(maps,focus)?focus:'all';
  }
  new ResizeObserver(()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(drawEdges);}).observe($('flow-nodes'));
  window.addEventListener('hashchange',()=>{readHash();render();window.scrollTo(0,0);});
  window.addEventListener('popstate',()=>{readHash();render();});
  $('spec-line').textContent=`${tokens.bits} bit · ${tokens.rate} MS/s · ${tokens.vdd} V`;
  $('review-date').textContent='整理至 '+data.meta.reviewed_at;
  $('stale-banner').hidden=!data.meta.needs_review;
  readHash();render();
})();
