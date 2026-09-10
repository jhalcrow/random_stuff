#!/usr/bin/env python3
"""Least-squares fit of Yang's row-1 nuke magnitude against every candidate driver.

Thirteen observations of the SAME skill across wildly different fights.  Eyeballing pairs of
them produced three wrong hypotheses in a row, because the candidate drivers are correlated:
march size, own archer count and army_min move together in most reports.  This does the honest
thing and regresses log(kills per trigger) on the logs of all of them at once.

  python3 kingshot/nuke_fit.py
"""
import itertools, math

# (label, own archers, army_min, own total, target total, caster arch atk/leth, target def/hp)
OBS = [
    ('Baron 203,610',        61_083, 203_610, 203_610, 534_000, (1831.5, 1741.1), (3150.0, 3150.0),   772.0),
    ('Baron 100,000',        30_000, 100_000, 100_000, 534_000, (1831.5, 1741.1), (3150.0, 3150.0),   411.4),
    ('Baron 50,000',         15_000,  50_000,  50_000, 534_000, (1831.5, 1741.1), (3150.0, 3150.0),   146.0),
    ('Narses attack 10k',     3_000,  10_000,  10_000, 123_570, (1509.6, 2017.2), ( 514.3,  294.6),   658.0),
    ('Narses defence 5k',     1_500,   5_000,   5_000, 123_570, (1509.6, 2017.2), ( 514.3,  294.6),   462.0),
    ('Terry def 10k mine',    3_000,  10_000,  10_000, 226_932, (2417.4, 2203.3), ( 897.5, 1281.4),    54.8),
    ('Terry def theirs',     79_426,  10_000, 226_932,  10_000, (1482.7, 1318.2), (2009.9, 1920.5),    87.7),
    ('Terry atk 20k mine',    6_000,  20_000,  20_000, 189_110, (2387.5, 2190.8), (1140.5, 1309.5),    66.2),
    ('Terry atk 20k theirs', 56_733,  20_000, 189_110,  20_000, (1507.1, 1328.3), (1994.3, 1909.9),    76.0),
    ('Terry atk 10k ALL-INF',     0,  10_000,  10_000, 226_932, (2387.5, 2190.8), (1140.5, 1309.5),    21.3),
    ('Terry atk 10k theirs', 68_079,  10_000, 226_932,  10_000, (1507.1, 1328.3), (1994.3, 1909.9),    62.0),
    ('Earthling mine',      401_515, 663_292, 923_309, 663_292, (1907.9, 2706.5), (2108.3, 2080.4),  9045.0),
    ('Earthling theirs',    578_298, 663_292, 663_292, 923_309, (2179.1, 2291.5), (2030.0, 2230.9),  3682.0),
]

def features(o):
    _, arch, amin, own, tgt, (a_atk, a_leth), (d_def, d_hp), _ = o
    return {
        'own archers': arch + 1,          # +1 so the all-infantry point is usable in log space
        'army_min': amin,
        'own total': own,
        'target total': tgt,
        'A caster': (100 + a_atk) * (100 + a_leth),
        'D target': (100 + d_def) * (100 + d_hp),
    }

NAMES = list(features(OBS[0]))


def fit(keys):
    """OLS of log(per-trigger) on log of the chosen features plus an intercept."""
    X = [[1.0] + [math.log(features(o)[k]) for k in keys] for o in OBS]
    y = [math.log(o[-1]) for o in OBS]
    n, p = len(X), len(keys) + 1
    # normal equations, solved by Gauss-Jordan
    A = [[sum(X[r][i] * X[r][j] for r in range(n)) for j in range(p)] + [sum(X[r][i] * y[r] for r in range(n))]
         for i in range(p)]
    for c in range(p):
        piv = max(range(c, p), key=lambda r: abs(A[r][c]))
        if abs(A[piv][c]) < 1e-12:
            return None
        A[c], A[piv] = A[piv], A[c]
        d = A[c][c]
        A[c] = [v / d for v in A[c]]
        for r in range(p):
            if r != c and A[r][c]:
                f = A[r][c]
                A[r] = [v - f * w for v, w in zip(A[r], A[c])]
    beta = [A[i][p] for i in range(p)]
    resid = [y[r] - sum(beta[i] * X[r][i] for i in range(p)) for r in range(n)]
    rms = math.sqrt(sum(e * e for e in resid) / n)
    return beta, rms, resid


if __name__ == '__main__':
    print(f'{len(OBS)} observations of Yang row 1.  Fitting log(kills per trigger).\n')
    print('Single drivers, each on its own:')
    for k in NAMES:
        b, rms, _ = fit([k])
        print(f'  {k:14s} exponent {b[1]:+6.2f}   rms log error {rms:.3f}  (x{math.exp(rms):.2f})')

    print('\nBest pair and triple by rms:')
    best = []
    for r in (2, 3):
        cands = [(fit(list(c))[1], c) for c in itertools.combinations(NAMES, r) if fit(list(c))]
        cands.sort()
        for rms, c in cands[:3]:
            b, _, _ = fit(list(c))
            terms = '  '.join(f'{k}^{b[i+1]:+.2f}' for i, k in enumerate(c))
            print(f'  rms {rms:.3f} (x{math.exp(rms):.2f})   {terms}')
        best.append(cands[0])

    print('\nResiduals of the best two-driver fit:')
    rms, c = best[0]
    b, _, resid = fit(list(c))
    for o, e in sorted(zip(OBS, resid), key=lambda t: -abs(t[1])):
        print(f'  {o[0]:22s} observed {o[-1]:8,.0f}   model x{math.exp(-e):.2f} off')
