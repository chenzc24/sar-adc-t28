"""Comparator input-referred noise from decision probabilities (Python 2.7/3, no numpy).

Reads the CMPNZ strobes of sar8_comp_noise in spectre.out, counts positive decisions per input
level and fits P(+) = Phi((v - mu) / sigma) by maximum likelihood (Newton on log sigma).
Standard errors come from the observed information matrix.
"""
from __future__ import print_function
import argparse, json, math, re


def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def loglik(rows, mu, ls):
    s = math.exp(ls); total = 0.
    for v, k, n in rows:
        p = min(max(phi((v - mu) / s), 1e-300), 1 - 1e-16)
        total += k * math.log(p) + (n - k) * math.log(1 - p)
    return total


def fit(rows):
    mu = sum(v * n for v, k, n in rows) / sum(n for v, k, n in rows)
    # Start from the spread of levels that are neither all + nor all -.
    mixed = [v for v, k, n in rows if 0 < k < n] or [v for v, k, n in rows]
    ls = math.log(max(max(mixed) - min(mixed), 1e-5) / 2)
    h = 1e-6
    for _ in range(200):
        f = lambda a, b: loglik(rows, a, b)
        g = [(f(mu + h, ls) - f(mu - h, ls)) / (2 * h), (f(mu, ls + h) - f(mu, ls - h)) / (2 * h)]
        H = [[(f(mu + h, ls) - 2 * f(mu, ls) + f(mu - h, ls)) / h ** 2, 0], [0, (f(mu, ls + h) - 2 * f(mu, ls) + f(mu, ls - h)) / h ** 2]]
        H[0][1] = H[1][0] = (f(mu + h, ls + h) - f(mu + h, ls - h) - f(mu - h, ls + h) + f(mu - h, ls - h)) / (4 * h * h)
        det = H[0][0] * H[1][1] - H[0][1] ** 2
        if det <= 0 or H[0][0] >= 0:
            # Not concave here: take a damped gradient step.
            mu += 1e-9 * g[0]; ls += 1e-3 * (1 if g[1] > 0 else -1); continue
        d0 = (H[1][1] * g[0] - H[0][1] * g[1]) / det; d1 = (H[0][0] * g[1] - H[0][1] * g[0]) / det
        mu -= d0; ls -= max(min(d1, 1.), -1.)
        if abs(d0) < 1e-12 and abs(d1) < 1e-9:
            break
    cov = [[H[1][1] / det * -1, H[0][1] / det], [H[0][1] / det, H[0][0] / det * -1]]
    sigma = math.exp(ls)
    return dict(mu_v=mu, sigma_v=sigma, mu_se_v=math.sqrt(max(cov[0][0], 0)),
                sigma_se_v=sigma * math.sqrt(max(cov[1][1], 0)), loglik=loglik(rows, mu, ls))


def main():
    p = argparse.ArgumentParser(); p.add_argument('--run-dir', required=True); p.add_argument('--output-dir', required=True)
    a = p.parse_args()
    ctx = json.load(open(a.run_dir + '/inputs/context.json'))
    lines = list(open(a.run_dir + '/spectre.out'))
    rec = [m.group(1).split(',') for m in (re.search(r'CMPNZ,([^\r\n]+)', l) for l in lines) if m]
    rec = [(int(r[0]), int(r[1]), float(r[2]), int(r[3])) for r in rec]
    cfg = ctx['noise_fixture']
    total = cfg['levels'] * cfg['per_level']
    assert len(rec) >= total and [r[0] for r in rec[:total]] == list(range(total)), (len(rec), total)
    rec = rec[:total]
    levels = {}
    for cycle, level, v, pol in rec:
        assert level == cycle // cfg['per_level']
        row = levels.setdefault(level, dict(input_v=v, positive=0, negative=0, unresolved=0))
        assert abs(row['input_v'] - v) < 1e-12
        row['positive' if pol > 0 else 'negative' if pol < 0 else 'unresolved'] += 1
    table = [levels[k] for k in sorted(levels)]
    # Unresolved decisions are excluded from the fit and reported.
    rows = [(r['input_v'], r['positive'], r['positive'] + r['negative']) for r in table]
    result = fit(rows)
    lsb = cfg['lsb_v']
    result.update(sigma_lsb=result['sigma_v'] / lsb, budget_lsb=cfg['budget_lsb'],
                  within_budget=result['sigma_v'] / lsb <= cfg['budget_lsb'],
                  levels=table, unresolved=sum(r['unresolved'] for r in table), decisions=total,
                  monotonic=all(table[i]['positive'] <= table[i + 1]['positive'] + 3 * math.sqrt(cfg['per_level'])
                                for i in range(len(table) - 1)),
                  warning_codes=sorted(set(x for l in lines for x in re.findall(r'WARNING \(([^)]+)\)', l))),
                  analysis_complete=True, context=ctx, electrical_verdict='deferred_not_qualified')
    with open(a.output_dir + '/result.json', 'w') as f:
        json.dump(result, f, indent=2); f.write('\n')
    print('COMP_NOISE_ANALYSIS', round(result['sigma_v'] * 1e3, 4), 'mV', round(result['sigma_lsb'], 4), 'LSB')


if __name__ == '__main__':
    main()
