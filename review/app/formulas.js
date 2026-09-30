/* Shared browser/Node calculation registry. SI units in, SI units out. */
(function (root) {
  'use strict';
  const definitions = {
    lsb: {unit: 'V', inputs: ['converter.resolution_bits', 'input.differential_range_v']},
    total: {unit: 'V', inputs: ['targets.enob_min_bits', 'input.dynamic_test_level_dbfs']},
    quantization: {unit: 'V', inputs: ['lsb']},
    analog: {unit: 'V', inputs: ['total', 'quantization']},
    sampling_noise: {unit: 'V', inputs: ['error_budget.sampling_noise_rms_lsb', 'lsb']},
    comparator_noise: {unit: 'V', inputs: ['error_budget.comparator_noise_rms_lsb', 'lsb']},
    reference_noise: {unit: 'V', inputs: ['error_budget.reference_switching_noise_rms_lsb', 'lsb']},
    distortion: {unit: 'V', inputs: ['error_budget.distortion_unmodeled_rms_lsb', 'lsb']},
    jitter: {unit: 'V', inputs: ['error_budget.clock_jitter_rms_ps', 'error_budget.jitter_budget_input_hz']},
    capacitance: {unit: 'F', inputs: ['sampling_noise', 'temperature_k']},
    settling: {unit: 'V', inputs: ['error_budget.cdac_settling_abs_max_lsb', 'lsb']},
    hold: {unit: 'V', inputs: ['full18.conditions.raw_error_limit_v']},
    offset: {unit: 'V', inputs: ['error_budget.comparator_offset_abs_max_lsb', 'lsb']}
  };
  function calculate(spec, context, scenario = {}) {
    const b = spec.error_budget;
    const n = spec.converter.resolution_bits;
    const span = spec.input.differential_range_v[1] - spec.input.differential_range_v[0];
    const enob = scenario.enob ?? spec.targets.enob_min_bits;
    const alpha = scenario.sampling ?? b.sampling_noise_rms_lsb;
    if (![n, span, enob, alpha, context.temperature_k, context.hold_limit_v].every(Number.isFinite) ||
        !Number.isInteger(n) || n < 1 || n > 24 || span <= 0 || enob <= 0 || enob > 24 ||
        alpha <= 0 || alpha > 2 || context.temperature_k <= 0 || context.hold_limit_v <= 0) {
      throw new Error('参数必须有效：位数 1–24，ENOB > 0，采样分配 0 < α ≤ 2。');
    }
    const lsb = span / (2 ** n);
    const signal = span / 2 * 10 ** (spec.input.dynamic_test_level_dbfs / 20) / Math.SQRT2;
    const sndr = 6.02 * enob + 1.76;
    const total = signal / 10 ** (sndr / 20);
    const quantization = lsb / Math.sqrt(12);
    const sampling_noise = alpha * lsb;
    const comparator_noise = b.comparator_noise_rms_lsb * lsb;
    const reference_noise = b.reference_switching_noise_rms_lsb * lsb;
    const distortion = b.distortion_unmodeled_rms_lsb * lsb;
    const jitter = 2 * Math.PI * b.jitter_budget_input_hz * signal * b.clock_jitter_rms_ps * 1e-12;
    const variance = total ** 2 - quantization ** 2;
    const rss = Math.hypot(quantization, sampling_noise, comparator_noise, reference_noise, jitter, distortion);
    const predicted_sndr = 20 * Math.log10(signal / rss);
    return {
      lsb, total, quantization, analog: variance < 0 ? null : Math.sqrt(variance),
      sampling_noise, comparator_noise, reference_noise, jitter, distortion,
      capacitance: 2 * 1.380649e-23 * context.temperature_k / sampling_noise ** 2,
      settling: b.cdac_settling_abs_max_lsb * lsb,
      hold: context.hold_limit_v,
      offset: b.comparator_offset_abs_max_lsb * lsb,
      signal, sndr, rss, predicted_sndr, predicted_enob: (predicted_sndr - 1.76) / 6.02,
      feasible: rss <= total, analog_feasible: variance >= 0,
      variance_margin: total ** 2 - rss ** 2
    };
  }
  const api = {definitions, calculate};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ReviewMath = api;
})(typeof globalThis === 'undefined' ? this : globalThis);
