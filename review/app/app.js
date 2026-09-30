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
  let state = {focus: 'all', tab: 'theory', node: null};
  let graph;
  let resizeFrame;
  const ns = 'http://www.w3.org/2000/svg';

  function svgElement(tag, attrs = {}) {
    const el = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
    return el;
  }

  function circuitMap() {
    const rects = {
      sampling: [110, 32, 160, 62],
      cdac: [360, 32, 155, 62],
      comparator: [610, 32, 160, 62],
      reference: [360, 151, 155, 53],
      clock: [850, 126, 180, 66]
    };
    $('circuit-map').innerHTML = `<svg viewBox="0 0 1120 224" class="block-wires" aria-hidden="true"><defs><marker id="circuit-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/></marker></defs>
      <g class="signal-wire"><path d="M55 63 H108"/><path d="M272 63 H358"/><path d="M517 63 H608"/><path d="M772 63 H940 V124"/><path d="M1032 159 H1090"/><path d="M438 149 V96"/></g>
      <g class="control-wire"><path d="M848 157 H785 V116 H485 V96"/><path d="M880 194 V215 H190 V96"/><path d="M900 194 V208 H690 V96"/></g>
      <g class="wire-text"><text x="18" y="58">VIN±</text><text x="294" y="54">采样</text><text x="541" y="54">残差</text><text x="835" y="53">判决</text><text x="1039" y="147">DOUT</text><text x="448" y="137">VREF</text><text x="604" y="110">逐位切换控制</text><text x="243" y="210">采样相位</text><text x="701" y="202">比较时钟</text></g>
      </svg>${Object.entries(rects).map(([id,[x,y,w,h]]) => `<button class="circuit-block" data-block="${id}" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px"><strong>${esc(blocks[id].title)}</strong><span>${esc(blocks[id].subtitle)}</span></button>`).join('')}`;
  }

  function activeBlocks() {
    const node = graph.nodes.find(n => n.id === state.node);
    return node ? node.blocks : state.focus === 'all' ? [] : [state.focus];
  }

  function highlight() {
    const active = activeBlocks();
    document.querySelectorAll('.circuit-block').forEach(el => {
      el.classList.toggle('active', active.includes(el.dataset.block));
      el.setAttribute('aria-pressed', String(active.includes(el.dataset.block)));
    });
    document.querySelectorAll('.flow-node').forEach(el => {
      const node = graph.nodes.find(n => n.id === el.dataset.node);
      el.classList.toggle('selected', el.dataset.node === state.node);
      el.classList.toggle('related', active.length > 0 && node.blocks.some(b => active.includes(b)));
      el.classList.toggle('subdued', active.length > 0 && node.blocks.length > 0 && !node.blocks.some(b => active.includes(b)));
    });
    const names = active.map(id => blocks[id].title).join(' + ');
    $('canvas-context').textContent = names ? '对应电路：' + names : '对应电路：SAR ADC 全局';
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

  function detail() {
    const node = graph.nodes.find(n => n.id === state.node);
    const panel = $('node-detail');
    if (!node) { panel.hidden = true; return; }
    panel.hidden = false;
    const hardware = node.blocks.map(b => blocks[b].title).join(' + ') || 'ADC 全局';
    panel.innerHTML = `<div class="detail-title"><div><span>${esc(hardware)}</span><h3>${esc(node.title)}</h3></div><button id="close-detail" class="quiet-button" aria-label="收起说明">×</button></div><p>${esc(expand(node.detail))}</p>${node.focus === 'sampling' && state.focus !== 'sampling' ? '<button class="branch-button" data-block="sampling">展开 Bootstrap 的步骤分支 →</button>' : ''}`;
  }

  function render() {
    graph = flows.graphs[state.focus === 'sampling' ? 'sampling_'+state.tab : state.tab];
    if (!graph.nodes.some(n => n.id === state.node)) state.node = null;
    $('flow-title').textContent = graph.title;
    $('flow-note').textContent = graph.note;
    $('legend').innerHTML = state.tab === 'theory'
      ? '<span><i class="solid"></i>推导 / 约束关系</span><span><i class="dashed"></i>暂定分配</span>'
      : '<span><i class="dot done"></i>已做</span><span><i class="dot fail"></i>问题</span><span><i class="dot planned"></i>待做</span>';
    $('show-all').hidden = state.focus === 'all';
    $('flow-nodes').style.setProperty('--columns', graph.columns);
    $('flow-nodes').innerHTML = graph.nodes.map(node => `<button class="flow-node ${esc(node.tone || '')}" style="grid-column:${node.col}/span ${node.span || 1};grid-row:${node.row}" data-node="${node.id}"><span class="node-top"><b>${esc(node.title)}</b>${node.tag ? `<small class="node-tag">${esc(node.tag)}</small>` : ''}</span><span class="node-line">${esc(expand(node.line))}</span><span class="node-sub">${esc(expand(node.sub))}</span></button>`).join('');
    $('budget-footnote').textContent = state.tab === 'theory' && state.focus !== 'sampling'
      ? `另预留 ${fmt(values.distortion*1000)} mV RMS 等效失真 / 未建模误差；包含量化后的 RSS 为 ${fmt(values.rss*1000)} mV。预算在假设下闭合，不代表电路通过。`
      : state.focus !== 'all' && state.focus !== 'sampling' ? '上方所选 block 在流程图中高亮；共享节点保留，用于看清上下游。' : '';
    document.querySelectorAll('[data-tab]').forEach(el => el.setAttribute('aria-selected',String(el.dataset.tab === state.tab)));
    $('view').setAttribute('aria-labelledby','tab-'+state.tab);
    highlight(); detail();
    requestAnimationFrame(drawEdges);
    const hash = `#${state.focus}/${state.tab}${state.node ? '/'+state.node : ''}`;
    if (location.hash !== hash) history.replaceState(null,'',hash);
  }

  document.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.dataset.block) { state.focus = button.dataset.block; state.node = null; render(); }
    else if (button.dataset.tab) { state.tab = button.dataset.tab; state.node = null; render(); }
    else if (button.dataset.node) { state.node = state.node === button.dataset.node ? null : button.dataset.node; highlight(); detail(); }
    else if (button.id === 'show-all') { state.focus = 'all'; state.node = null; render(); }
    else if (button.id === 'close-detail') { state.node = null; highlight(); detail(); }
  });
  document.querySelector('.tabs').addEventListener('keydown', event => {
    if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    event.preventDefault();
    state.tab = event.key === 'Home' ? 'theory' : event.key === 'End' ? 'workflow' : state.tab === 'theory' ? 'workflow' : 'theory';
    state.node = null; render(); $('tab-'+state.tab).focus();
  });
  function readHash() {
    const [focus,tab,node] = location.hash.slice(1).split('/');
    if (node && ['hold','lsb','total'].includes(node)) return;
    if ((focus === 'all' || focus in blocks) && ['theory','workflow'].includes(tab)) state = {focus,tab,node:node || null};
  }
  const observer = new ResizeObserver(() => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(drawEdges);
  });
  observer.observe($('flow-nodes'));
  window.addEventListener('hashchange', () => {readHash();render();});
  $('spec-line').textContent = `${tokens.bits} bit · ${tokens.rate} MS/s · ${tokens.vdd} V`;
  $('review-date').textContent = '整理至 '+data.meta.reviewed_at;
  $('stale-banner').hidden = !data.meta.needs_review;
  circuitMap(); readHash(); render();
})();
