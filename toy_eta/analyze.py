#!/usr/bin/env python3
"""Turn results/tables.npz into regret tables. Usage: analyze.py [results_dir]"""
import csv
import json
import os
import sys

import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "results")
Z = dict(np.load(os.path.join(out, "tables.npz")))
meta = json.load(open(os.path.join(out, "meta.json")))
ETAS = np.array(meta["etas"])
FAM = meta["families"]
BUD = meta["budgets"]
BETA = meta["beta"]
HOR = 350
J = Z["J_true"]
N = len(J)
seed = Z["seed"].astype(int)
fam = Z["family"].astype(int)
rng = np.random.default_rng(0)
idx = np.arange(N)


def ci(x, B=4000):
    b = rng.integers(0, len(x), (B, len(x)))
    m = x[b].mean(1)
    return x.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)


def loso_best(table, mask):
    """Best single candidate from other seeds (mask selects the training instances)."""
    sel = np.zeros(len(table), int)
    for s in np.unique(seed):
        sel[seed == s] = np.nanmean(table[mask & (seed != s)], 0).argmin()
    return sel


def even_subset(k):
    return {3: [1, 4, 7], 5: [0, 2, 4, 6, 8], 7: [0, 1, 3, 4, 5, 7, 8]}[k]


def hill(table, start, k):
    """Noisy hill climb on the 1-D log grid: walk from start, keep best observed."""
    sel = np.zeros(len(table), int)
    for n in range(len(table)):
        seen = {start[n]: table[n, start[n]]}
        while len(seen) < k:
            b = min(seen, key=seen.get)
            nb = [i for i in (b + 1, b - 1) if 0 <= i < table.shape[1] and i not in seen]
            if not nb:
                rest = [i for i in range(table.shape[1]) if i not in seen]
                nb = [min(rest, key=lambda i: abs(i - b))]
            seen[nb[0]] = table[n, nb[0]]
        sel[n] = min(seen, key=seen.get)
    return sel


selectors = {}  # name -> (index array, real transitions)
JE = Z["J_E_m"][:, :, 0]
selectors["A_ideal"] = (loso_best(J, fam == 0), 0)
selectors["A_pop"] = (loso_best(J, np.ones(N, bool)), 0)
selectors["B"] = (Z["Jh_B"].argmin(1), 0)
for b in BUD:
    selectors[f"C_{b}"] = (Z[f"Jh_C_{b}"].argmin(1), b)
    selectors[f"D_nopen_{b}"] = (Z[f"Jh_Dm_{b}"].argmin(1), b)
    selectors[f"D_pen_{b}"] = ((Z[f"Jh_Dm_{b}"] + BETA * Z[f"Jh_Ds_{b}"]).argmin(1), b)
for k in (3, 5, 7):
    sub = even_subset(k)
    selectors[f"E_{k}"] = (np.array(sub)[JE[:, sub].argmin(1)], k * HOR)
    selectors[f"E_3starts_{k}x3"] = (np.array(sub)[Z["J_E_m"].mean(2)[:, sub].argmin(1)], 3 * k * HOR)
    selectors[f"E_unpaired_{k}"] = (np.array(sub)[Z["J_E_unpaired"][:, sub].argmin(1)], k * HOR)
    selectors[f"E_hill_{k}"] = (hill(JE, selectors["A_ideal"][0], k), k * HOR)
selectors["F"] = (J.argmin(1), 9 * HOR)

jm = J.min(1)
miss = Z["true_G"] + Z["true_R"]
reg = {n: J[idx, s] - jm for n, (s, _) in selectors.items()}
rows = []
for n, (s, tr) in selectors.items():
    m, lo, hi = ci(reg[n])
    rows.append(dict(selector=n, transitions=tr, regret=round(m, 4), ci_lo=round(lo, 4), ci_hi=round(hi, 4),
                     median=round(float(np.median(reg[n])), 4), frac_gt_0p05=round(float((reg[n] > 0.05).mean()), 3),
                     miss_cost=round(float(miss[idx, s].mean()), 4)))
with open(os.path.join(out, "regret.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
print(f"N={N} instances, oracle J mean {jm.mean():.4f}, seeds {len(np.unique(seed))}")
print(f"{'selector':18s}{'trans':>6s}{'regret':>9s}{'95% CI':>18s}{'median':>8s}{'>0.05':>7s}{'miss':>7s}")
for r in rows:
    print(f"{r['selector']:18s}{r['transitions']:6d}{r['regret']:9.4f}  [{r['ci_lo']:.4f},{r['ci_hi']:.4f}]{r['median']:8.4f}{r['frac_gt_0p05']:7.2f}{r['miss_cost']:7.3f}")

# per family
names = ["A_ideal", "A_pop", "B"] + [f"C_{b}" for b in BUD] + [f"D_pen_{b}" for b in BUD] + ["E_3", "E_5", "E_7", "E_hill_3"]
print("\nregret by family")
print(f"{'':10s}" + "".join(f"{n[:9]:>10s}" for n in names))
frows = []
for i, fn in enumerate(FAM):
    mask = fam == i
    vals = [reg[n][mask].mean() for n in names]
    frows.append(dict(family=fn, **{n: round(v, 4) for n, v in zip(names, vals)}))
    print(f"{fn:10s}" + "".join(f"{v:10.4f}" for v in vals))
with open(os.path.join(out, "regret_by_family.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=frows[0].keys())
    w.writeheader()
    w.writerows(frows)

# paired comparisons
pairs = []
for b in BUD:
    pairs.append((f"D_pen_{b}", f"C_{b}"))
    pairs.append((f"D_pen_{b}", f"D_nopen_{b}"))
    pairs.append((f"D_pen_{b}", "A_pop"))
    pairs.append((f"C_{b}", "A_pop"))
    for k in (3, 5, 7):
        pairs.append((f"D_pen_{b}", f"E_{k}"))
        pairs.append((f"C_{b}", f"E_{k}"))
print("\npaired: mean(a-b) on regret, negative = a better; 95% bootstrap CI")
prow = []
for a_, b_ in pairs:
    d = reg[a_] - reg[b_]
    m, lo, hi = ci(d)
    wins = float((d < -1e-9).mean())
    loses = float((d > 1e-9).mean())
    prow.append(dict(a=a_, b=b_, diff=round(m, 4), lo=round(lo, 4), hi=round(hi, 4), a_better=round(wins, 3), b_better=round(loses, 3)))
    print(f"{a_:14s} vs {b_:12s} {m:8.4f} [{lo:.4f},{hi:.4f}]  a better {wins:.2f}  b better {loses:.2f}")
print("\npaired D_pen vs C and vs E_3 by family, per budget")
for i, fn in enumerate(FAM):
    mask = fam == i
    s = f"{fn:10s}"
    for b in BUD:
        m, lo, hi = ci((reg[f"D_pen_{b}"] - reg[f"C_{b}"])[mask])
        s += f"  D-C@{b}: {m:7.3f} [{lo:6.3f},{hi:6.3f}]"
        prow.append(dict(a=f"D_pen_{b}|{fn}", b=f"C_{b}|{fn}", diff=round(m, 4), lo=round(lo, 4), hi=round(hi, 4), a_better="", b_better=""))
    print(s)
with open(os.path.join(out, "paired.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=prow[0].keys())
    w.writeheader()
    w.writerows(prow)

# question 1 from randomised plants
print("\nQ1: eta* vs plant, instance level")
best = np.log2(ETAS[J.argmin(1)])
for i, name, x in ((1, "delay h", Z["p_d"] * 0.02), (2, "lag T", Z["p_T"])):
    m = fam == i
    c = np.corrcoef(np.argsort(np.argsort(x[m])), np.argsort(np.argsort(best[m])))[0, 1]
    print(f"  {FAM[i]}: rank corr(log eta*, {name}) = {c:.3f}, geo-mean eta* = {2 ** best[m].mean():.2f}")
print("  geo-mean eta* per family:", {FAM[i]: round(float(2 ** best[fam == i].mean()), 2) for i in range(len(FAM))})
print("  eta* histogram per family (eta index 0..8):")
for i in range(len(FAM)):
    print(f"    {FAM[i]:10s}", np.bincount(J[fam == i].argmin(1), minlength=9))
print("  mean J(eta) per family:")
for i in range(len(FAM)):
    print(f"    {FAM[i]:10s}", " ".join(f"{v:6.3f}" for v in J[fam == i].mean(0)))

# question 3
print("\nQ3: position RMSE (m), median over instances [mean in parentheses]; eta=2 / eta=8")
qrows = []
for H in ("1", "10", "50", "cl"):
    for b in BUD:
        s = f"  H={H:3s} N={b:5d} "
        for name in "BCD":
            for eta in ("2", "8"):
                v = Z[f"pe_{name}_{H}_{b}_{eta}"]
                qrows.append(dict(model=name, H=H, N=b, eta=eta, median=float(np.median(v)), mean=float(v.mean())))
                s += f"{name}@{eta}: {np.median(v):.4f} ({v.mean():.4f})  "
        print(s)
with open(os.path.join(out, "prediction_error.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=qrows[0].keys())
    w.writeheader()
    w.writerows(qrows)
print("  closed-loop gap by family, eta=8, N=5000: median C / D")
for i, fn in enumerate(FAM):
    m = fam == i
    print(f"    {fn:10s} C {np.median(Z['pe_C_cl_5000_8'][m]):.4f}  D {np.median(Z['pe_D_cl_5000_8'][m]):.4f}  B {np.median(Z['pe_B_cl_5000_8'][m]):.4f}")

# grey-box identification quality
print("\nC fit error at N=5000, median abs: d(steps) %.2f  T %.3f  k %.3f  delta %.3f" % (
    np.median(np.abs(Z["fit_d_5000"] - Z["p_d"])), np.median(np.abs(Z["fit_T_5000"] - Z["p_T"])),
    np.median(np.abs(Z["fit_k_5000"] - Z["p_k"])), np.median(np.abs(Z["fit_delta_5000"] - Z["p_delta"]))))

# schedule experiment
if "S_true" in Z:
    ok = ~np.isnan(Z["S_true"][:, 0])
    S = Z["S_true"][ok]
    S_E = Z["S_E_m"][ok][:, :, 0]
    S_Em = Z["S_E_m"][ok]
    S_U = Z["S_E_unpaired"][ok]
    n = len(S)
    ix = np.arange(n)
    sm = S.min(1)
    sd = seed[ok]
    fm = fam[ok]
    lv = np.array(np.meshgrid(*[np.arange(5)] * 3, indexing="ij")).reshape(3, -1).T
    diag = np.where((lv[:, 0] == lv[:, 1]) & (lv[:, 1] == lv[:, 2]))[0]
    code = lambda c: int(c[0] * 25 + c[1] * 5 + c[2])

    def loso(t, mask):
        sel = np.zeros(n, int)
        for s in np.unique(sd):
            sel[sd == s] = t[mask & (sd != s)].mean(0).argmin()
        return sel

    def coord(table, k):
        sel = np.zeros(n, int)
        for q in range(n):
            cur = [2, 2, 2]
            seen = {code(cur): table[q, code(cur)]}
            c = 0
            stale = 0
            while len(seen) < min(k, 125):
                before = len(seen)
                base = list(cur)
                for l in sorted(range(5), key=lambda l_: abs(l_ - base[c])):
                    if len(seen) >= k:
                        break
                    t = list(base)
                    t[c] = l
                    if code(t) not in seen:
                        seen[code(t)] = table[q, code(t)]
                b = min(seen, key=seen.get)
                cur = [b // 25, (b // 5) % 5, b % 5]
                c = (c + 1) % 3
                stale = stale + 1 if len(seen) == before else 0
                if stale >= 3 and len(seen) < k:  # all axis lines through the best are used up
                    rest = [i for i in range(125) if i not in seen]
                    i = min(rest, key=lambda r: int(np.abs(lv[r] - np.array(cur)).sum()))
                    seen[i] = table[q, i]
                    stale = 0
            sel[q] = min(seen, key=seen.get)
        return sel

    sel = {}
    sel["A_fixed_loso"] = (diag[loso(S[:, diag], fm == 0)], 0)
    sel["A_sched_ideal"] = (loso(S, fm == 0), 0)
    sel["A_sched_pop"] = (loso(S, np.ones(n, bool)), 0)
    sel["A_fixed_pop"] = (diag[loso(S[:, diag], np.ones(n, bool))], 0)
    sel["F_fixed(5 diag)"] = (diag[S[:, diag].argmin(1)], 5 * HOR)
    sel["B"] = (Z["Sh_B"][ok].argmin(1), 0)
    for b in BUD:
        sel[f"C_{b}"] = (Z[f"Sh_C_{b}"][ok].argmin(1), b)
        sel[f"D_nopen_{b}"] = (Z[f"Sh_Dm_{b}"][ok].argmin(1), b)
        sel[f"D_pen_{b}"] = ((Z[f"Sh_Dm_{b}"] + BETA * Z[f"Sh_Ds_{b}"])[ok].argmin(1), b)
    rg = np.random.default_rng(1)
    for k in (5, 10, 25):
        perms = np.argsort(rg.random((n, 125)), axis=1)[:, :k]
        sel[f"E_random_{k}"] = (perms[ix, S_E[ix[:, None], perms].argmin(1)], k * HOR)
        sel[f"E_random_unp_{k}"] = (perms[ix, S_U[ix[:, None], perms].argmin(1)], k * HOR)
        sel[f"E_coord_{k}"] = (coord(S_E, k), k * HOR)
        sel[f"E_coord_unp_{k}"] = (coord(S_U, k), k * HOR)
        # same real budget spent as k//3 candidates from 3 common starts
        q3 = max(1, k // 3)
        p3 = perms[:, :q3]
        sel[f"E_random_3st_{k}"] = (p3[ix, S_Em.mean(2)[ix[:, None], p3].argmin(1)], q3 * 3 * HOR)
    sel["F_sched"] = (S.argmin(1), 125 * HOR)
    srow = []
    sreg = {}
    print(f"\nSchedule experiment, N={n}, oracle J {sm.mean():.4f}; fixed-eta 9-grid oracle on same instances {J[ok].min(1).mean():.4f}")
    print(f"{'selector':30s}{'trans':>7s}{'regret':>9s}{'95% CI':>18s}{'median':>8s}{'miss%':>7s}")
    fail = Z["S_true_fail"][ok]
    for nm, (s, tr) in sel.items():
        r = S[ix, s] - sm
        sreg[nm] = r
        m, lo, hi = ci(r)
        srow.append(dict(selector=nm, transitions=tr, regret=round(m, 4), lo=round(lo, 4), hi=round(hi, 4),
                         median=round(float(np.median(r)), 4), miss_frac=round(float(fail[ix, s].mean()), 3)))
        print(f"{nm:30s}{tr:7d}{m:9.4f}  [{lo:.4f},{hi:.4f}]{np.median(r):8.4f}{fail[ix, s].mean():7.3f}")
    with open(os.path.join(out, "schedule_regret.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=srow[0].keys())
        w.writeheader()
        w.writerows(srow)
    print("paired schedule comparisons (a-b):")
    cmp = []
    for b in BUD:
        cmp += [(f"D_pen_{b}", f"C_{b}"), (f"D_pen_{b}", "E_coord_10"), (f"D_pen_{b}", "E_random_10"), (f"C_{b}", "E_coord_10"), (f"C_{b}", "E_random_10"),
                (f"D_pen_{b}", "E_random_3st_25"), (f"C_{b}", "E_random_3st_25"),
                (f"D_pen_{b}", "F_fixed(5 diag)"), (f"C_{b}", "F_fixed(5 diag)"), (f"D_pen_{b}", "A_sched_pop"), (f"C_{b}", "A_sched_pop")]
    for a_, b_ in cmp:
        m, lo, hi = ci(sreg[a_] - sreg[b_])
        print(f"  {a_:12s} vs {b_:18s} {m:8.4f} [{lo:.4f},{hi:.4f}]")
    print("schedule regret by family:")
    nms = ["A_sched_pop", "F_fixed(5 diag)", "C_1000", "C_5000", "D_pen_1000", "D_pen_5000", "E_random_10", "E_coord_10", "E_coord_25"]
    print(f"{'':10s}" + "".join(f"{q[:11]:>12s}" for q in nms))
    for i, fn in enumerate(FAM):
        m = fm == i
        print(f"{fn:10s}" + "".join(f"{sreg[q][m].mean():12.4f}" for q in nms))
    print("gain of schedule oracle over fixed-9 oracle by family:", {FAM[i]: round(float((J[ok].min(1) - sm)[fm == i].mean()), 3) for i in range(len(FAM))})

# post-hoc: grey box plus linear drift map (not in the original design)
cp_path = os.path.join(out, "cplus.npz")
if os.path.exists(cp_path):
    P = dict(np.load(cp_path))
    assert (P["seed"] == Z["seed"]).all() and (P["family"] == Z["family"]).all()
    assert np.allclose(P["p_T"], Z["p_T"]) and np.allclose(P["p_A"], Z["p_A"]), "instances differ"
    print("\nPOST-HOC C+ (grey box + ridge RBF drift map), same plants, fresh logs")
    for b in BUD:
        rp = J[idx, P[f"Jh_Cp_{b}"].argmin(1)] - jm
        m, lo, hi = ci(rp)
        s_ = f"fixed eta N={b}: C+ {m:.4f} [{lo:.4f},{hi:.4f}]"
        m2, l2, h2 = ci(rp - reg[f"D_pen_{b}"])
        s_ += f"  C+ - D: {m2:.4f} [{l2:.4f},{h2:.4f}]"
        rs = S[ix, P[f"Sh_Cp_{b}"].argmin(1)] - sm
        m3, l3, h3 = ci(rs)
        m4, l4, h4 = ci(rs - sreg[f"D_pen_{b}"])
        print(s_ + f" | schedule: C+ {m3:.4f} [{l3:.4f},{h3:.4f}]  C+ - D: {m4:.4f} [{l4:.4f},{h4:.4f}]")
    print("by family, C+ minus D_pen regret, fixed eta:")
    for i, fn in enumerate(FAM):
        m_ = fam == i
        t_ = f"  {fn:10s}"
        for b in BUD:
            rp = J[idx, P[f"Jh_Cp_{b}"].argmin(1)] - jm
            q, lo, hi = ci((rp - reg[f"D_pen_{b}"])[m_])
            t_ += f" N={b}: C+ {rp[m_].mean():.3f}, diff {q:7.3f} [{lo:6.3f},{hi:6.3f}]"
        print(t_)

# cost-matched comparisons
print("\ncost-matched, paired regret difference a-b")
for a_, b_ in (("D_pen_1000", "E_hill_3"), ("C_1000", "E_hill_3"), ("C_200", "E_hill_3"), ("D_pen_5000", "E_3starts_5x3"),
               ("C_5000", "E_3starts_5x3"), ("D_pen_5000", "E_3starts_7x3")):
    m, lo, hi = ci(reg[a_] - reg[b_])
    print(f"  {a_:12s} vs {b_:14s} {m:8.4f} [{lo:.4f},{hi:.4f}]")
print("tables with NaN outside schedule columns:", [k for k, v in Z.items() if np.isnan(v).any()])
