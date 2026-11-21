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


def derivatives(rows, mu, ls):
    """Gradient and Hessian in (mu, log sigma), with central differences scaled to sigma."""
    f = lambda a, b: loglik(rows, a, b)
    hm, hl = 1e-3 * math.exp(ls), 1e-3
    f0 = f(mu, ls)
    g = [(f(mu + hm, ls) - f(mu - hm, ls)) / (2 * hm), (f(mu, ls + hl) - f(mu, ls - hl)) / (2 * hl)]
    H00 = (f(mu + hm, ls) - 2 * f0 + f(mu - hm, ls)) / hm ** 2
    H11 = (f(mu, ls + hl) - 2 * f0 + f(mu, ls - hl)) / hl ** 2
    H01 = (f(mu + hm, ls + hl) - f(mu + hm, ls - hl) - f(mu - hm, ls + hl) + f(mu - hm, ls - hl)) / (4 * hm * hl)
    return g, [[H00, H01], [H01, H11]]


def fit(rows):
    # Start at the level nearest 50 % positive and the spread of the mixed levels.
    mu = min(rows, key=lambda r: abs(r[1] - r[2] / 2.))[0]
    mixed = [v for v, k, n in rows if 0 < k < n] or [v for v, k, n in rows]
    ls = math.log(max(max(mixed) - min(mixed), 1e-5) / 4)
    for _ in range(200):
        g, H = derivatives(rows, mu, ls)
        det = H[0][0] * H[1][1] - H[0][1] ** 2
        if det > 0 and H[0][0] < 0:
            d0 = (H[1][1] * g[0] - H[0][1] * g[1]) / det
            d1 = (H[0][0] * g[1] - H[0][1] * g[0]) / det
        else:
            # Not concave here: step along the gradient, scaled to the current sigma.
            s = math.exp(ls)
            d0, d1 = -0.1 * s * (1 if g[0] > 0 else -1), -0.1 * (1 if g[1] > 0 else -1)
        # Damped step: never move mu by more than one sigma or log sigma by more than 0.5.
        s = math.exp(ls)
        d0, d1 = max(min(d0, s), -s), max(min(d1, .5), -.5)
        old = loglik(rows, mu, ls)
        for _ in range(30):
            if loglik(rows, mu - d0, ls - d1) >= old - 1e-12:
                break
            d0, d1 = d0 / 2, d1 / 2
        mu, ls = mu - d0, ls - d1
        if abs(d0) < 1e-6 * s and abs(d1) < 1e-6:
            break
    # Covariance from a fresh Hessian at the converged point.
    g, H = derivatives(rows, mu, ls)
    det = H[0][0] * H[1][1] - H[0][1] ** 2
    if not (det > 0 and H[0][0] < 0):
        raise ValueError('Probit likelihood not concave at the fit; widen or refine the input levels')
    cov = [[-H[1][1] / det, H[0][1] / det], [H[0][1] / det, -H[0][0] / det]]
    sigma = math.exp(ls)
    return dict(mu_v=mu, sigma_v=sigma, mu_se_v=math.sqrt(cov[0][0]), sigma_se_v=sigma * math.sqrt(cov[1][1]),
                loglik=loglik(rows, mu, ls), gradient=g)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--run-dir', required=True); p.add_argument('--output-dir', required=True)
    p.add_argument('--source-run-dir', help='Completed simulation of an analysis-only rerun')
    a = p.parse_args()
    data = a.source_run_dir or a.run_dir
    ctx = json.load(open(data + '/inputs/context.json'))
    lines = list(open(data + '/spectre.out'))
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
                  analysis_complete=True, context=ctx, source_run_dir=a.source_run_dir, electrical_verdict='deferred_not_qualified')
    with open(a.output_dir + '/result.json', 'w') as f:
        json.dump(result, f, indent=2); f.write('\n')
    print('COMP_NOISE_ANALYSIS', round(result['sigma_v'] * 1e3, 4), 'mV', round(result['sigma_lsb'], 4), 'LSB')


if __name__ == '__main__':
    main()
