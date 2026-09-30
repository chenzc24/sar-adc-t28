// Display projection only. Formula and evidence sources remain authoritative.
const ReviewPresentation = {
  tokens(data, values) {
    const fmt = (n, digits = 3) => Number(n).toFixed(digits);
  const audit = data.evidence.find(e => e.id === 'current_audit');
  const obs = audit.observations;
  const hold = obs.find(o => o.metric === 'hold');
  const bottom = data.evidence.find(e => e.id === 'bottom_screen').observations[0];
  const decision = data.evidence.find(e => e.id === 'strongarm_interface').observations.find(o => o.unit === 's');
  const ab = data.evidence.find(e => e.id === 'fast_ab').observations;

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

    return tokens;
  }
};
