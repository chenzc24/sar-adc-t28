/* Runs against the exact snapshot and the same registry used by the browser. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const {calculate, definitions} = require(path.join(root, 'review/app/formulas.js'));
const data = JSON.parse(fs.readFileSync(path.join(root, 'output/review/data.json'),'utf8'));
const {spec, context, model} = data;
const b = calculate(spec,context);
function near(actual, expected, tolerance) { assert.ok(Math.abs(actual-expected) < tolerance, `${actual} != ${expected}`); }
near(b.lsb, 0.0017578125, 1e-12);
near(b.sndr,55.94,1e-9);
near(b.total,0.000905164,1e-9);
near(b.sampling_noise,0.00031640625,1e-12);
near(b.quantization,0.000507437,1e-9);
near(b.rss,0.000821345,1e-9);
near(b.jitter,0.000320738,1e-9);
near(b.capacitance,82.787e-15,0.001e-15);
near(b.settling,0.000439453125,1e-12);
near(b.hold,0.000439,1e-12);
assert.ok(b.feasible);
for (const m of model.metrics) {
  assert.ok(definitions[m.formula], `unregistered formula ${m.formula}`);
  assert.equal(definitions[m.formula].unit,m.unit);
  assert.ok(Number.isFinite(b[m.formula]));
}
for (const e of data.evidence) for (const o of e.observations) {
  if (!o.metric || e.stale) continue;
  assert.equal(o.gate,Math.abs(o.value)<o.limit?'pass':'fail',e.id+' '+o.label);
}
const savedEvidence = JSON.stringify(data.evidence);
const savedSpec = JSON.stringify(spec);
const changed = calculate(spec,context,{sampling:0.3,enob:9.8});
assert.ok(!changed.feasible);
assert.ok(changed.capacitance < b.capacitance);
assert.equal(changed.hold,b.hold);
assert.equal(JSON.stringify(data.evidence),savedEvidence);
assert.equal(JSON.stringify(spec),savedSpec);
const impossible = calculate(spec,context,{enob:12});
assert.equal(impossible.analog,null);
assert.equal(impossible.analog_feasible,false);
assert.throws(()=>calculate(spec,context,{sampling:0}));
assert.throws(()=>calculate(spec,context,{enob:NaN}));
console.log('PASS: benchmark values, formula bindings/units, evidence gates, scenario isolation, infeasible/invalid inputs');
