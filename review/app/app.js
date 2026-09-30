(function () {
  'use strict';
  const D = JSON.parse(document.getElementById('review-data').textContent);
  const M = D.model;
  const index = list => Object.fromEntries(list.map(x => [x.id, x]));
  const metrics = index(M.metrics), steps = index(M.steps), evidence = index(D.evidence), modules = index(M.modules);
  const kindLabels = {derived: '条件推导', allocation: '暂定分配', model: '模型预测'};
  const workLabels = {complete: '实验 / 工作完成', planned: '待开展', blocked: '受阻', active: '进行中'};
  const verdictLabels = {scoped: '限域结果', fail: '未达整体验收', diagnostic: '诊断证据', unverified: '未验证'};
  const $ = id => document.getElementById(id);
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let state = {module: 'sampling', tab: 'theory', type: 'metric', id: 'hold'};
  let scenario = {};
  let values = ReviewMath.calculate(D.spec, D.context);
  const baseline = ReviewMath.calculate(D.spec, D.context);
  const auditRecord = evidence.current_audit;
  const holdObservation = auditRecord.observations.find(o => o.metric === 'hold');
  const heldMv = (holdObservation.value * 1000).toFixed(3);
  const holdLimitMv = (baseline.hold * 1000).toFixed(3);
  const holdRatio = (Math.abs(holdObservation.value) / holdObservation.limit).toFixed(1);
  const badge = (label, cls = '') => `<span class="badge ${esc(cls)}">${esc(label)}</span>`;
  const selected = (type, id) => state.type === type && state.id === id;
  const metricValue = (m, v = values) => v[m.formula] === null ? '不可行' : (v[m.formula] * m.scale).toFixed(m.unit === 'F' ? 2 : 3);
  const metricStale = m => D.sources.spec.stale || m.sources.some(s => D.sources[s].stale);
  const stepStale = s => s.evidence.some(e => evidence[e].stale);
  const link = (type, id, label) => `<button class="text-link" data-select="${esc(type)}" data-id="${esc(id)}">${esc(label)}</button>`;
  const sourceLinks = ids => ids.map(id => `<button class="text-link source-link" data-source="${esc(id)}">↗ ${esc(D.sources[id].path)}${D.sources[id].stale ? ' · 待复核' : ''}</button>`).join('');
  const evidenceLinks = ids => ids.map(id => `<button class="evidence-link" data-select="evidence" data-id="${esc(id)}"><b>${esc(evidence[id].title)} ↗</b><span>${esc(evidence[id].stale ? '来源已变化，结论待复核' : evidence[id].scope)}</span></button>`).join('');
  function formatObservation(o) {
    const units = {V: [1000, 'mV'], A: [1e6, 'µA'], s: [1e12, 'ps'], F: [1e15, 'fF'], count: [1, '条']};
    const [scale, label] = units[o.unit];
    return `${(o.value * scale).toFixed(o.unit === 'count' ? 0 : 3)} ${label}`;
  }
  function card(id) {
    const m = metrics[id];
    return `<button class="metric-card ${selected('metric', id) ? 'selected' : ''}" data-select="metric" data-id="${id}" aria-pressed="${selected('metric', id)}">${badge(kindLabels[m.kind], m.kind)}<span class="card-title">${esc(m.title)}</span><span class="card-value">${metricValue(m)}</span><span class="card-unit">${esc(m.display_unit)}</span><span class="card-formula">${esc(m.expression)}</span></button>`;
  }
  function allocationIds() { return ['sampling_noise', 'comparator_noise', 'reference_noise', 'jitter', 'distortion']; }
  function theory() {
    const leaves = M.metrics.filter(m => m.module === state.module && !['lsb','total','analog',...allocationIds()].includes(m.id));
    const heading = state.module === 'system' ? '量化与确定性边界' : `${modules[state.module].title} · 约束落点`;
    const parts = ['quantization', ...allocationIds()];
    return `<div class="section-caption"><h2><span class="section-index">A</span>从系统要求到误差余量</h2><span>全差分 · ${D.spec.converter.resolution_bits} bit · ${D.spec.input.dynamic_test_level_dbfs} dBFS</span></div>
      <div class="metric-grid roots">${['lsb','total','analog'].map(card).join('')}</div>
      <div class="chain-arrow">总方差扣除量化项 → 工程分配</div>
      <div class="section-caption"><h2><span class="section-index">B</span>模拟误差预算分支</h2><span>分配可调整，不是唯一理论解</span></div>
      <div class="metric-grid allocation-grid">${allocationIds().map(card).join('')}</div>
      <div class="budget-bars" role="img" aria-label="量化及各分配项的方差占比，基于不相关假设">${parts.map(id => `<span style="width:${(values[id] ** 2 / values.rss ** 2 * 100).toFixed(4)}%"></span>`).join('')}</div>
      <div class="summary-strip"><span>含量化 RSS <strong>${(values.rss * 1000).toFixed(3)}</strong> mV</span><span>预测 ENOB <strong>${values.predicted_enob.toFixed(3)}</strong></span>${badge(values.feasible ? '假设下预算闭合' : '预算不闭合', values.feasible ? 'scoped' : 'fail')}</div>
      <p class="small muted">量化项 ${(values.quantization * 1000).toFixed(3)} mV RMS。失真为等效预留；RSS 闭合不代表电路通过。</p>
      <div class="section-caption section-gap"><h2><span class="section-index">C</span>${esc(heading)}</h2><span>点击节点查看前提与验证步骤</span></div>
      <div class="constraint-grid">${leaves.length ? leaves.map(m => card(m.id)).join('') : `<div class="empty-state">本模块暂无进一步形式化约束节点。请在设计进度中查看已有证据与待补范围。</div>`}</div>
      ${state.module === 'sampling' ? `<div class="notice danger section-gap"><b>当前瓶颈 · ${auditRecord.stale ? '历史结论待复核' : '原始保持误差未达标'}</b><p>${heldMv} mV / ${holdLimitMv} mV 约束。输入加载通路已确认；关断误差的唯一归因仍需消融实验。</p>${link('step','audit','查看最近诊断 →')}&nbsp;&nbsp;${link('step','topology','查看下一设计步骤 →')}</div>` : ''}
      <details class="scenario" ${Object.keys(scenario).length ? 'open' : ''}><summary>预算候选预览 <span class="muted small"> / 不修改基线或实测数据</span></summary>
        <form id="scenario-form" class="scenario-controls"><label>ENOB 下限<input name="enob" type="number" min="1" max="24" step="0.1" value="${scenario.enob ?? D.spec.targets.enob_min_bits}" required></label><label>采样噪声分配 / LSB<input name="sampling" type="number" min="0.001" max="2" step="0.001" value="${scenario.sampling ?? D.spec.error_budget.sampling_noise_rms_lsb}" required></label><button class="primary-button" type="submit">计算候选</button><button class="quiet-button" type="button" id="reset-scenario">恢复基线</button></form>
        <div id="scenario-result" class="scenario-result" aria-live="polite">${Object.keys(scenario).length ? `候选：Cside 下限 ${metricValue(metrics.capacitance)} fF（基线 ${metricValue(metrics.capacitance, baseline)} fF）。关联 RC、开关和 reference 需重评；历史观测未变。` : '仅预览 ENOB 与采样分配变化。保持误差门限固定采用实验配置，不随噪声预算变化。'}</div>
      </details>`;
  }
  function workflow() {
    const list = M.steps.filter(s => s.module === state.module);
    return `<div class="stage-rail" aria-label="设计抽象层次"><span>架构 / 行为</span><span>一阶动态</span><span>电气宏模型</span><span class="current">管级模块 ← 当前主线</span><span>全转换</span><span>版图 / 后仿</span></div>
      <div class="section-caption"><h2>步骤、方法与验收边界</h2><span>${list.length} 个步骤 · 不计算虚假完成率</span></div>
      <p class="workflow-intro">工作完成 ≠ 指标通过。按方法、结果与覆盖范围分别审查。</p>
      <div class="workflow-list">${list.map(s => `<article class="step ${s.id === 'topology' ? 'next' : ''}"><button class="step-card ${selected('step',s.id) ? 'selected' : ''}" data-select="step" data-id="${s.id}"><div class="step-top"><b>${esc(s.title)}</b>${badge(workLabels[s.work], s.work === 'blocked' ? 'warning' : '')}</div><div class="step-method">${esc(s.method)}</div><div class="badges">${badge(stepStale(s) ? '来源变化 · 待复核' : verdictLabels[s.verdict], stepStale(s) ? 'warning' : s.verdict)}${badge(s.coverage)}</div><div class="step-result">${esc(s.result)}</div><div class="step-next">下一步 / ${esc(s.next)}</div></button></article>`).join('')}</div>`;
  }
  function circuit() {
    const bindings = M.circuits.filter(c => c.modules.includes(state.module));
    return `<div class="section-caption"><h2>电路联动接口位</h2><span>不建立未经核对的原理图副本</span></div><div class="circuit-slot"><div class="slot-icon" aria-hidden="true">[ · · ]</div><h2>Analog Canvas</h2><p>预留相位、电荷路径与电路对象的可视化空间。以后从这里关联当前指标、设计步骤和实际电路。</p>${badge('尚未连接 · 当前 OA 未核对', 'warning')}</div>
      ${bindings.map(c => `<section class="binding"><h3>历史电路绑定 / ${esc(c.id)}</h3><dl><dt>Library / Cell / View</dt><dd>${esc(c.library)} / ${esc(c.cell)} / ${esc(c.view)}</dd><dt>Testbench</dt><dd>${esc(c.testbench)}</dd><dt>已记录导出 SHA-256</dt><dd class="hash">${esc(c.netlist_sha256)}</dd></dl><p class="small muted">${esc(c.note)}</p>${evidenceLinks(c.evidence)}</section>`).join('') || '<div class="empty-state section-gap">本模块尚未整理电路绑定。没有绑定不代表远端不存在电路。</div>'}
      <div class="notice section-gap">本版只保存可追溯绑定，不请求连接、不嵌入远端页面、不更改 OA。原始电路与功能示意图今后会分别标识。</div>`;
  }
  function observationTable(record) {
    return `<table class="evidence-table"><tbody>${record.observations.map(o => `<tr><td>${esc(o.label)}${o.metric ? `<br>${link('metric',o.metric,metrics[o.metric].title)}<br><span class="small muted">原始门限 ${formatObservation({value:o.limit,unit:o.unit})}</span>` : ''}</td><td>${formatObservation(o)}${o.gate ? `<br>${badge(record.stale ? '待复核' : o.gate === 'pass' ? '该指标限域通过' : '该指标未通过', record.stale ? 'warning' : o.gate === 'pass' ? 'scoped' : 'fail')}` : ''}</td></tr>`).join('')}</tbody></table>`;
  }
  function metricInspector(m) {
    const relatedSteps = M.steps.filter(s => s.metrics.includes(m.id));
    const relatedEvidence = [...new Set(relatedSteps.flatMap(s => s.evidence))];
    const children = M.metrics.filter(x => x.parents.includes(m.id));
    return `<div class="inspector-head"><span class="eyebrow">CONSTRAINT / ${esc(m.id.toUpperCase())}</span><h2>${esc(m.title)}</h2>${badge(kindLabels[m.kind],m.kind)}${metricStale(m) ? ' '+badge('来源变化 · 待复核','warning') : ''}<div class="inspector-value">${metricValue(m)}<small>${esc(m.display_unit)}</small></div></div><div class="inspector-body"><h3>推导 / 约束表达式</h3><div class="formula-block">${esc(m.expression)}</div><p>${esc(m.premise)}</p>
      ${Object.keys(scenario).length ? '<p class="notice warning">当前显示候选理论值。下方实验仍属于原始基线，适用性需重评。</p>' : ''}
      ${m.id === 'hold' ? `<div class="gate-result"><span class="small">Full-control · 历史原始保持误差</span><div><strong>${heldMv}</strong> <span class="small">mV</span></div><p>绝对值 / 门限 = ${holdRatio}× · ${auditRecord.stale ? '待复核，不重判历史结果' : '未通过'}</p><p>不是热噪声，也未扣除拟合或校准。</p></div>` : ''}
      <h3>上游依据</h3><div class="relation-list">${m.parents.length ? m.parents.map(id => link('metric',id,'↑ '+metrics[id].title)).join('') : '<span class="muted">系统配置直接输入</span>'}</div>
      ${children.length ? `<h3>下游影响</h3><div class="relation-list">${children.map(x => link('metric',x.id,'↓ '+x.title)).join('')}</div>` : ''}
      <h3>对应设计步骤</h3><div class="relation-list">${relatedSteps.map(s => link('step',s.id,s.title)).join('') || '<span class="muted">待补步骤映射</span>'}</div>
      <details><summary>公式输入与来源</summary><p class="small">计算注册项：${esc(m.formula)} / SI 单位 ${esc(m.unit)}</p><p class="small">输入：${esc(ReviewMath.definitions[m.formula].inputs.join(' · '))}</p>${sourceLinks(m.sources)}</details><details><summary>相关实验证据 (${relatedEvidence.length})</summary>${evidenceLinks(relatedEvidence)}</details></div>`;
  }
  function stepInspector(s) {
    return `<div class="inspector-head"><span class="eyebrow">WORKFLOW / ${esc(s.id.toUpperCase())}</span><h2>${esc(s.title)}</h2><div class="badges">${badge(workLabels[s.work])}${badge(stepStale(s) ? '来源变化 · 待复核' : verdictLabels[s.verdict],stepStale(s) ? 'warning' : s.verdict)}</div></div><div class="inspector-body"><h3>目的</h3><p>${esc(s.purpose)}</p><h3>方法性质 / 验证覆盖</h3><p>${esc(s.method)}<br><span class="muted">${esc(s.coverage)}</span></p><h3>当前结果</h3><p>${esc(s.result)}</p><h3>下一步 / 验证意图</h3><p>${esc(s.next)}</p><h3>受哪些指标约束</h3><div class="relation-list">${s.metrics.map(id => link('metric',id,metrics[id].title)).join('')}</div><h3>步骤依赖（不代表已通过）</h3><div class="relation-list">${s.depends_on.map(id => link('step',id,'↑ '+steps[id].title)).join('') || '<span class="muted">架构起点</span>'}</div><h3>实验与原始依据</h3>${evidenceLinks(s.evidence) || '<p class="muted">尚无该步骤的实验证据。不以计划替代结果。</p>'}</div>`;
  }
  function evidenceInspector(e) {
    return `<div class="inspector-head"><span class="eyebrow">EVIDENCE / ${esc(e.id.toUpperCase())}</span><h2>${esc(e.title)}</h2>${badge(e.stale ? '来源变化 · 待复核' : '已整理的历史证据',e.stale ? 'warning' : 'diagnostic')}</div><div class="inspector-body">${Object.keys(scenario).length ? '<p class="notice warning">预算候选不改变下列历史观测和原始门限。是否适用于候选方案需重新评价。</p>' : ''}<h3>条件与覆盖</h3><p>${esc(e.scope)}</p><h3>结论</h3><p>${esc(e.result)}</p>${observationTable(e)}<h3>证据边界 / 尚未证明</h3><ul class="limit-list">${e.limitations.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>${e.netlist_sha256 ? `<details><summary>网表版本指纹</summary><p class="hash">${esc(e.netlist_sha256)}</p><p class="muted small">历史导出指纹；当前 OA 未实时核对。</p></details>`:''}<h3>来源（内嵌快照，可离线查看）</h3>${sourceLinks(e.sources)}${e.artifact_path ? `<details><summary>原始附件可用性</summary><p class="hash">${esc(e.artifact_path)}</p><p>${e.artifact_available ? '构建时目录存在；本版未重新校验全部原始波形。' : '当前本地未找到目录；报告可读，原始波形不可据此复验。'}</p></details>` : ''}</div>`;
  }
  function renderInspector() {
    $('inspector').innerHTML = state.type === 'metric' ? metricInspector(metrics[state.id]) : state.type === 'step' ? stepInspector(steps[state.id]) : evidenceInspector(evidence[state.id]);
  }
  function render() {
    $('modules').innerHTML = M.modules.map((m,i)=>`<button class="module-button ${m.id === state.module ? 'active' : ''}" data-module="${m.id}" ${m.id === state.module ? 'aria-current="page"' : ''}><span class="module-number">0${i+1}</span><span><span class="module-title">${esc(m.title)}</span><span class="module-coverage">${esc(m.coverage)}</span></span></button>`).join('');
    $('page-title').textContent = modules[state.module].title;
    $('breadcrumb').textContent = modules[state.module].title;
    $('page-subtitle').textContent = modules[state.module].subtitle + ' · 以证据区分已知、假设与待验证';
    document.querySelectorAll('[data-tab]').forEach(b => b.setAttribute('aria-selected',String(b.dataset.tab === state.tab)));
    $('view').setAttribute('aria-labelledby','tab-'+state.tab);
    $('view').innerHTML = ({theory,workflow,circuit})[state.tab]();
    renderInspector();
    const suffix = state.type === 'metric' ? state.id : state.type+':'+state.id;
    const hash = `#${state.module}/${state.tab}/${suffix}`;
    if (location.hash !== hash) history.replaceState(null,'',hash);
  }
  function select(type,id) {
    if (type === 'metric' && metrics[id]) { state.module = metrics[id].module; }
    else if (type === 'step' && steps[id]) { state.module = steps[id].module; state.tab = 'workflow'; }
    else if (type !== 'evidence' || !evidence[id]) return;
    state.type = type; state.id = id;
    render();
    if (innerWidth < 1021) $('inspector').scrollIntoView({behavior:'auto',block:'start'});
  }
  function openSource(id) {
    const source = D.sources[id];
    if (!source) return;
    $('document-title').textContent = source.path;
    $('document-meta').textContent = `构建时文本快照 · ${source.stale ? '与已审查指纹不一致，待复核' : '与已审查指纹一致'} · SHA-256 ${source.sha256}`;
    $('document-text').textContent = source.text;
    $('document-dialog').showModal();
  }
  document.addEventListener('click', ev => {
    const button = ev.target.closest('button');
    if (!button) return;
    if (button.dataset.module) {
      state.module = button.dataset.module;
      const m = M.metrics.find(m=>m.module === state.module);
      state.type = m ? 'metric' : 'step'; state.id = m ? m.id : M.steps.find(s=>s.module === state.module).id;
      render();
    } else if (button.dataset.tab) { state.tab = button.dataset.tab; render(); }
    else if (button.dataset.select) select(button.dataset.select,button.dataset.id);
    else if (button.dataset.source) openSource(button.dataset.source);
    else if (button.id === 'reset-scenario') { scenario = {}; values = baseline; render(); }
    else if (button.id === 'close-dialog') $('document-dialog').close();
    else if (button.id === 'snapshot-button') {
      $('document-title').textContent = '快照与维护说明';
      $('document-meta').textContent = '只读展示 · 不修改参数 / 网表 / OA · 不连接 Canvas';
      $('document-text').textContent = `整理日期：${M.reviewed_at}\n构建时间：${D.meta.generated_at}\n构建时仓库 HEAD：${D.meta.source_commit}（不等于每份实验的运行提交）\nModel SHA-256：${D.meta.model_sha256}\nEvidence SHA-256：${D.meta.evidence_sha256}\n\n本页面是构建快照，不自动监听文件或远端状态。\n所有原文内嵌；关闭网络也可审查。\n\n维护入口：review/model.yaml、review/evidence.yaml\n重建：.venv/Scripts/python.exe scripts/review/build.py\n核对来源变化后才执行 --record-source-lock。\n\n待复核来源：${D.meta.stale_sources.join(', ') || '无'}\n\n范围：采样/Bootstrap 完整样板；其他模块仅导入部分证据。\n系统级功耗、全部器件可靠性和全管级 ADC 尚未验收。`;
      $('document-dialog').showModal();
    }
  });
  document.addEventListener('submit', ev=>{
    if (ev.target.id !== 'scenario-form') return;
    ev.preventDefault();
    try {
      const f = new FormData(ev.target);
      const next = {enob:Number(f.get('enob')),sampling:Number(f.get('sampling'))};
      const calculated = ReviewMath.calculate(D.spec,D.context,next);
      scenario = next; values = calculated; render();
    } catch (error) { $('scenario-result').textContent = error.message; $('scenario-result').setAttribute('role','alert'); }
  });
  function restoreHash() {
    const [module,tab,target] = location.hash.slice(1).split('/');
    if (!modules[module] || !['theory','workflow','circuit'].includes(tab)) return;
    let [type,id] = (target || '').includes(':') ? target.split(':') : ['metric',target];
    if (!(type === 'metric' ? metrics : type === 'step' ? steps : type === 'evidence' ? evidence : {})[id]) return;
    state = {module,tab,type,id};
  }
  window.addEventListener('hashchange',()=>{restoreHash();render();});
  $('snapshot-date').textContent = M.reviewed_at+' · 已整理';
  document.querySelector('.project-tag').textContent = `${D.spec.converter.resolution_bits} BIT / ${D.spec.converter.sample_rate_hz / 1e6} MS/s / ${D.spec.supplies.vdd_v} V`;
  $('build-version').textContent = 'Snapshot '+D.meta.source_commit+' · 本地 / 离线';
  if (D.meta.stale_sources.length) {
    $('stale-banner').hidden = false;
    $('stale-banner').textContent = '来源已变化，相关结论需复核：'+D.meta.stale_sources.map(x=>D.sources[x].path).join('、');
  }
  restoreHash();render();
})();
