(function () {
  'use strict';
  const data = JSON.parse(document.getElementById('review-data').textContent);
  const flows = data.flows;
  const blocks = Object.fromEntries(flows.blocks.map(b => [b.id, b]));
  const values = ReviewMath.calculate(data.spec, data.context);
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = (n, digits = 3) => Number(n).toFixed(digits);
  const tokens = ReviewPresentation.tokens(data, values);
  const expand = text => String(text ?? '').replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (!(key in tokens)) throw new Error('Unknown flow token: ' + key);
    return tokens[key];
  });

  const maps = flows.graphs;
  let state={focus:'all'}, graph, resizeFrame;
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
    $('view').classList.toggle('single-chain',graph.layout==='chain');
    $('flow-title').textContent=graph.title;
    $('flow-note').textContent=graph.note;
    $('breadcrumb').textContent=state.focus==='all'?'全 ADC / 设计总图':'全 ADC / '+blocks[state.focus].title;
    $('show-all').hidden=state.focus==='all';
    $('legend').innerHTML='<span><i class="solid"></i>推导 / 验证步骤</span><span><i class="dashed"></i>暂定分配 / 待完成</span>';
    $('flow-nodes').style.setProperty('--columns',graph.columns);
    $('flow-nodes').innerHTML=graph.nodes.map((n,i)=>`<article class="flow-node ${esc(n.tone||'')} ${graph.layout==='branch' && n.span===graph.columns?'wide-node':''}" style="grid-column:${n.col}/span ${n.span||1};grid-row:${n.row}" data-node="${n.id}">
      ${state.focus!=='all'?`<span class="node-index">${String(i+1).padStart(2,'0')} / ${esc(blocks[state.focus].subtitle)}</span>`:''}
      <span class="node-top"><b>${esc(n.title)}</b>${n.needs_review?'<small class="node-tag">需复核</small>':n.tag?`<small class="node-tag">${esc(n.tag)}</small>`:''}</span>
      <span class="node-line">${esc(expand(n.line))}</span><span class="node-sub">${esc(expand(n.sub))}</span>
      ${n.reasons?`<ul class="node-reasons">${n.reasons.map(reason=>`<li>${esc(expand(reason))}</li>`).join('')}</ul>`:''}
      ${n.focus?`<button class="branch-button" data-block="${n.focus}">进入模块分支 →</button>`:''}
      ${(n.figures||[]).filter(id=>data.figures[id].available).map(id=>`<button class="figure-button" data-figure="${id}">查看${esc(data.figures[id].kind)} ↗</button>`).join('')}
      <details class="inline-detail"><summary>展开依据与说明</summary><p>${esc(expand(n.detail))}</p></details>
      ${n.topology_topic?`<button class="figure-button" data-topology="${n.topology_topic}">电路联动 · 抽象样例 ↗</button>`:n.canvas?`<details class="inline-detail canvas-inline"><summary>电路视图 · Canvas 预留</summary><p>${esc(blocks[n.canvas].description)} 尚未连接；此处预留对应模块原理图与相位 / 电荷路径。</p></details>`:''}
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
