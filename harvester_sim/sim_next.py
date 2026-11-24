"""
sim_next.py - follow-up studies requested in the design review.

  1. Transducer on the driver: put a second bimorph on the driver beam.
  2. Gain law + optimisation under uncertainty (median gain, snap risk).
  3. Sweep-past magnet geometry with a finite-size (sub-dipole) force model.
  4. Recorded vehicle vibration (and band-limited synthetic noise) as input.
  5. First experiment: predictions for a 0.1-0.5 m/s^2 frequency sweep.

Builds on sim.py (same parameters, same Step-1/Step-2 results).
Run:  python sim_next.py  [path/to/measurement_08.csv]
Outputs: plots/1x_*.png, results/next_tables.md, results/next_summary.json
"""
import contextlib
import io
import json
import os
import sys
import time

import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sim as S
from sim import MM, LBL, L_PIEZO

RNG = np.random.default_rng(20261123)
PLOTS, RESULTS = S.PLOTS, S.RESULTS
COL = S.COL
STRAIN_LIMIT = 500e-6          # PZT-5A dynamic strain limit used for design (500 microstrain)
RHO_PZT = 7800.0
DEFAULT_REC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "car_measurement_08.csv")

# =============================================================================
# Generic vectorised simulator (RK4, many systems at once)
# =============================================================================
def simulate(P, exc, T=3.0, dt=5e-5, t_steady=1.0, mode="coax", table=None,
             keep=None, keep_every=10, K_contact=2e6, C_contact=5.0):
    """P: dict of 1-D arrays (one entry per system). Keys used:
         kd md mbd cd kp mp mbp cp th Cp R    (piezo on the piezo beam)
         thd Cpd Rd                           (transducer on the driver, 0 = none)
         coax: C dc g0      side: s0 (rest offset) and `table` (Fz on piezo vs s)
       exc: ('sine', A[N], f[N], t_ramp) or ('series', a_of_t sampled at dt/2, scale[N])
       Returns per-system statistics over t >= t_steady (+ kept traces)."""
    N = len(P["kd"])
    g = {k: np.asarray(v, float) * np.ones(N) for k, v in P.items()}
    Y = np.zeros((6, N))
    if mode == "side":
        s_grid, Fz_tab = table                    # Fz_tab: (N, ns)  force on piezo, +z
        s_lo, ds = s_grid[0], s_grid[1] - s_grid[0]
        ns = len(s_grid)
        rows = np.arange(N)

    def base(t, n2):
        if exc[0] == "sine":
            _, A, f, tr = exc
            return A * min(t / tr, 1.0) * np.sin(2 * np.pi * f * t)
        return exc[1][n2] * exc[2]

    def mag(xd, xp, vd, vp):
        if mode == "none":
            return np.zeros(N), None
        if mode == "coax":
            d = g["g0"] + xp - xd
            Fm = g["C"] / np.maximum(d, g["dc"]) ** 4
            pen = g["dc"] - d
            Fc = np.where(pen > 0, np.maximum(K_contact * pen - C_contact * (vp - vd), 0.0), 0.0)
            return Fm - Fc, d                       # +ve pulls the two together
        s = g["s0"] + xp - xd
        u = np.clip((s - s_lo) / ds, 0, ns - 1.001)
        i0 = u.astype(int); w = u - i0
        Fz = (1 - w) * Fz_tab[rows, i0] + w * Fz_tab[rows, i0 + 1]
        return -Fz, s                               # Fz acts on piezo (+z); driver gets -Fz

    def f(t, n2, Y):
        xd, vd, xp, vp, V, Vd = Y
        ab = base(t, n2)
        Fn, _ = mag(xd, xp, vd, vp)
        ad = (-g["cd"] * vd - g["kd"] * xd - g["thd"] * Vd - g["mbd"] * ab + Fn) / g["md"]
        ap = (-g["cp"] * vp - g["kp"] * xp - g["th"] * V - g["mbp"] * ab - Fn) / g["mp"]
        dV = (g["th"] * vp - V / g["R"]) / g["Cp"]
        dVd = (g["thd"] * vd - Vd / g["Rd"]) / g["Cpd"]
        return np.array([vd, ad, vp, ap, dV, dVd])

    nst = int(round(T / dt))
    st = dict(Vpk=np.zeros(N), V2=np.zeros(N), Vd2=np.zeros(N), Vdpk=np.zeros(N),
              xdpk=np.zeros(N), xppk=np.zeros(N), Pdamp_d=np.zeros(N), Pdamp_p=np.zeros(N),
              gmin=np.full(N, np.inf), contact=np.zeros(N, bool), cnt=0)
    tr = {k: [] for k in ("t", "xd", "xp", "V", "Vd", "a")} if keep is not None else None
    for n in range(nst):
        t = n * dt
        k1 = f(t, 2 * n, Y); k2 = f(t + dt / 2, 2 * n + 1, Y + dt / 2 * k1)
        k3 = f(t + dt / 2, 2 * n + 1, Y + dt / 2 * k2); k4 = f(t + dt, 2 * n + 2, Y + dt * k3)
        Y = Y + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        if mode == "coax":
            d = g["g0"] + Y[2] - Y[0]
            st["gmin"] = np.minimum(st["gmin"], d)
            st["contact"] |= d <= g["dc"] * 1.02
        if t + dt >= t_steady:
            st["cnt"] += 1
            st["Vpk"] = np.maximum(st["Vpk"], np.abs(Y[4])); st["V2"] += Y[4] ** 2
            st["Vdpk"] = np.maximum(st["Vdpk"], np.abs(Y[5])); st["Vd2"] += Y[5] ** 2
            st["xdpk"] = np.maximum(st["xdpk"], np.abs(Y[0])); st["xppk"] = np.maximum(st["xppk"], np.abs(Y[2]))
            st["Pdamp_d"] += g["cd"] * Y[1] ** 2; st["Pdamp_p"] += g["cp"] * Y[3] ** 2
        if keep is not None and n % keep_every == 0:
            tr["t"].append(t + dt); tr["xd"].append(Y[0, keep]); tr["xp"].append(Y[2, keep])
            tr["V"].append(Y[4, keep]); tr["Vd"].append(Y[5, keep]); tr["a"].append(base(t + dt, 2 * n + 2) * np.ones(N)[keep])
    c = max(st["cnt"], 1)
    out = dict(Vpk=st["Vpk"], Vrms=np.sqrt(st["V2"] / c), P=st["V2"] / c / g["R"],
               Vdpk=st["Vdpk"], Vdrms=np.sqrt(st["Vd2"] / c), Pd=st["Vd2"] / c / g["Rd"],
               xdpk=st["xdpk"], xppk=st["xppk"], Pdamp_d=st["Pdamp_d"] / c, Pdamp_p=st["Pdamp_p"] / c,
               gmin=st["gmin"], contact=st["contact"])
    if tr is not None:
        out["trace"] = {k: np.array(v) for k, v in tr.items()}
    return out


def base_params(p, th):
    """Turn a sim.system_params dict into simulate() inputs (no driver transducer)."""
    q = {k: p[k] for k in ("kd", "md", "mbd", "cd", "kp", "mp", "mbp", "cp", "C", "dc", "g0", "Cp", "R")}
    q.update(th=th, thd=0.0, Cpd=1e-9, Rd=1e6)
    return q


def stack(plist):
    keys = plist[0].keys()
    return {k: np.array([p[k] for p in plist], float) for k in keys}


# =============================================================================
# 1. Transducer on the driver
# =============================================================================
def driver_transducer(s1, red, th_phys):
    """Bond the same 40 x 5 mm PZT/Cu/PZT bimorph on the driver, starting x0 from the clamp.
    Stepped-beam stiffness, k31-based coupling, mode-shape-weighted added mass, root strain.
    The dead tip mass is re-tuned so the driver keeps its design f_d."""
    rows, cands = [], []
    for i in range(3):
        d = red[i]["design"]
        p0 = S.system_params("redesign", i, s1, red)
        L, t, b = d["L_d"], d["t_d"], d["b_d"]
        EI0 = S.E_PETG * b * t ** 3 / 12
        lay = [(S.E_PETG, t, b), (S.E_PZT, S.T_PZT, S.BIMORPH_W), (S.E_CU, S.T_CU, S.BIMORPH_W),
               (S.E_PZT, S.T_PZT, S.BIMORPH_W)]
        yb, I, EIs = S.section_props(lay)
        bt = S.BIMORPH_W * S.E_PZT / S.E_PETG
        Ipzt = sum(bt * S.T_PZT ** 3 / 12 + bt * S.T_PZT * (yc - yb) ** 2
                   for yc in (t + S.T_PZT / 2, t + S.T_PZT + S.T_CU + S.T_PZT / 2))
        frac = Ipzt / I
        z_out = t + 2 * S.T_PZT + S.T_CU - yb            # outer PZT fibre from neutral axis
        mu_add = S.BIMORPH_W * (2 * S.T_PZT * RHO_PZT + S.T_CU * S.RHO_CU)
        mud = S.RHO_PETG * b * t
        mtip = S.magnet_mass(d["D_d"], d["h_d"])
        for lb in (40 * MM, 20 * MM, 10 * MM):
            for x0 in np.arange(0, 41, 2.5) * MM:
                x1 = x0 + lb
                if x1 > L - 0.5 * d["D_d"]:          # leave room for the tip magnet
                    continue
                # tip compliance of stepped cantilever: int (L-x)^2/EI dx
                seg = [(0, x0, EI0), (x0, x1, EIs), (x1, L, EI0)]
                comp = np.array([((L - a) ** 3 - (L - c) ** 3) / (3 * E) for a, c, E in seg])
                k = 1 / comp.sum()
                share = comp[1] / comp.sum()
                kap2 = S.K31 ** 2 * share * frac
                Cpd = S.CP * lb / S.BIMORPH_L
                th_d = np.sqrt(kap2 * k * Cpd)
                # added mass weighted by the static tip-load shape phi = (3 xi^2 - xi^3)/2
                xi = np.linspace(x0 / L, x1 / L, 200)
                phi = (3 * xi ** 2 - xi ** 3) / 2
                m_add_eff = mu_add * L * np.trapezoid(phi ** 2, xi)
                mb_add = mu_add * L * np.trapezoid(phi, xi)
                m_beam = S.MEFF_COEF * mud * L + m_add_eff
                # re-tune dead tip mass to keep f_d
                m_target = k / (2 * np.pi * p0["fd"]) ** 2
                m_dead = m_target - m_beam - mtip
                if m_dead < 0:
                    continue
                md = m_target
                strain_per_m = k * (L - x0) * z_out / EIs        # strain per metre of tip deflection
                cands.append(dict(i=i, lb=lb, x0=x0, k=k, md=md, m_dead=m_dead,
                                  mbd=S.MBASE_COEF * mud * L + mb_add + mtip + m_dead,
                                  cd=2 * S.ZETA_D * np.sqrt(k * md), kap2=kap2, th_d=th_d, Cpd=Cpd,
                                  Rd=1 / (2 * np.pi * p0["fd"] * Cpd), strain_per_m=strain_per_m,
                                  share=share, frac=frac))
    # simulate all candidates (coaxial redesign geometry, physical theta) + reference
    plist, meta = [], []
    for i in range(3):
        p0 = S.system_params("redesign", i, s1, red)
        q = base_params(p0, th_phys[i]); plist.append(q); meta.append(dict(i=i, ref=True))
    for c in cands:
        p0 = S.system_params("redesign", c["i"], s1, red)
        q = base_params(p0, th_phys[c["i"]])
        q.update(kd=c["k"], md=c["md"], mbd=c["mbd"], cd=c["cd"], thd=c["th_d"], Cpd=c["Cpd"], Rd=c["Rd"])
        plist.append(q); meta.append(dict(c, ref=False))
    A = np.full(len(plist), S.A_BASE)
    fe = np.array([S.system_params("redesign", m["i"], s1, red)["fd"] for m in meta])
    r = simulate(stack(plist), ("sine", A, fe, 0.3), T=3.0, dt=5e-5)
    for j, m in enumerate(meta):
        m.update(Pp=r["P"][j], Pd=r["Pd"][j], Vdpk=r["Vdpk"][j], Vpk=r["Vpk"][j], xd=r["xdpk"][j],
                 Pdamp=r["Pdamp_d"][j], gmin=r["gmin"][j], contact=bool(r["contact"][j]))
        m["strain"] = m["strain_per_m"] * m["xd"] if not m["ref"] else np.nan
    best = []
    for i in range(3):
        ref = next(m for m in meta if m["ref"] and m["i"] == i)
        ok = [m for m in meta if not m["ref"] and m["i"] == i and m["strain"] <= STRAIN_LIMIT]
        root = max((m for m in meta if not m["ref"] and m["i"] == i and m["x0"] == 0),
                   key=lambda m: m["Pd"])
        sel = max(ok, key=lambda m: m["Pd"]) if ok else None
        best.append(dict(ref=ref, root=root, sel=sel))
    return best, meta


# =============================================================================
# 2. Gain law and optimisation under uncertainty
# =============================================================================
def rel_complex(kd, md, mbd, kp, mp, mbp, f, zd, zp, a):
    w, wd, wp = 2 * np.pi * f, np.sqrt(kd / md), np.sqrt(kp / mp)
    Xd = -(mbd / md) * a / (wd ** 2 - w ** 2 + 2j * zd * wd * w)
    Xp = -(mbp / mp) * a / (wp ** 2 - w ** 2 + 2j * zp * wp * w)
    return Xd - Xp


def eq_gap(C, g0, ks, n=40):
    """Static equilibrium gap: ks (g0 - d) = C / d^4 (magnets pull the tips together)."""
    d = np.array(g0, float) * np.ones(np.broadcast(C, g0, ks).shape)
    for _ in range(n):
        d = g0 - C / (ks * np.maximum(d, 1e-4) ** 4)
    return d


def gain_law(kd, md, mbd, kp, mp, mbp, C, g0, zd):
    """Closed-form power gain over the same beams without magnets (paper eq. 20):
         G = (1 + q^2) (Delta / (Delta - k_m))^2,   q = k_m (m_bd/m_d) / (2 zeta_d m_bp w_d^2)
       k_m = 4C/d_e^5 (magnetic coupling stiffness at the equilibrium gap d_e),
       Delta = k_p - m_p w_d^2, evaluated at the driver resonance w_d^2 = k_d/m_d.
       Returns G, k_m, Delta."""
    ks = kd * kp / (kd + kp)
    de = eq_gap(C, g0, ks)
    km = 4 * C / de ** 5
    wd2 = kd / md
    Delta = kp - mp * wd2
    q = km * (mbd / md) / (2 * zd * mbp * wd2)
    G = (1 + q ** 2) * (Delta / (Delta - km)) ** 2
    return G, km, Delta


def lin_resp(kd, md, mbd, kp, mp, mbp, C, g0, th, w, zd, zp, A=None, magnets=True):
    """Exact linear two-mode model (magnets = coupling spring k_m at the equilibrium gap) with the
    piezo circuit. Returns average power into R, |x_d - x_p| amplitude, equilibrium gap, k_m."""
    A = S.A_BASE if A is None else A
    ks = kd * kp / (kd + kp)
    de = eq_gap(C, g0, ks)
    km = 4 * C / de ** 5 if magnets else 0.0 * C
    cd = 2 * zd * np.sqrt(kd * md); cp = 2 * zp * np.sqrt(kp * mp)
    Ze = 1j * w * th ** 2 / (1j * w * S.CP + 1 / S.R_LOAD)
    a11 = -w ** 2 * md + 1j * w * cd + kd - km
    a22 = -w ** 2 * mp + 1j * w * cp + kp - km + Ze
    b1, b2 = -mbd * A, -mbp * A
    det = a11 * a22 - km * km
    Xd = (b1 * a22 - km * b2) / det
    Xp = (a11 * b2 - km * b1) / det
    V = 1j * w * th * Xp / (1j * w * S.CP + 1 / S.R_LOAD)
    return np.abs(V) ** 2 / (2 * S.R_LOAD), np.abs(Xd - Xp), (de if magnets else g0), km


def driver_mode(kd, md, kp, mp, km):
    """Undamped frequency (Hz) of the driver-dominated mode of the coupled pair."""
    a, b = (kd - km) / md, (kp - km) / mp
    c = km / np.sqrt(md * mp)
    mean, half = (a + b) / 2, np.sqrt(((a - b) / 2) ** 2 + c ** 2)
    lo, hi = mean - half, mean + half
    # the driver-dominated mode is the one closer to the uncoupled driver value a
    lam = np.where(np.abs(lo - a) <= np.abs(hi - a), lo, hi)
    return np.sqrt(np.maximum(lam, 1e-9)) / (2 * np.pi)


def at_driver_mode(sy, th, zd, zp, A=None):
    """Power with and without magnets, closest approach / snap ratio, at the driver mode."""
    ks = sy["kd"] * sy["kp"] / (sy["kd"] + sy["kp"])
    de = eq_gap(sy["C"], sy["g0"], ks)
    km = 4 * sy["C"] / de ** 5
    f = driver_mode(sy["kd"], sy["md"], sy["kp"], sy["mp"], km)
    w = 2 * np.pi * f
    P, X, de, km = lin_resp(sy["kd"], sy["md"], sy["mbd"], sy["kp"], sy["mp"], sy["mbp"], sy["C"], sy["g0"], th, w, zd, zp, A)
    P0, _, _, _ = lin_resp(sy["kd"], sy["md"], sy["mbd"], sy["kp"], sy["mp"], sy["mbp"], sy["C"], sy["g0"], th, w, zd, zp, A,
                           magnets=False)
    ratio = (de - X) / S.d_snap(ks, sy["C"])
    return dict(f=f, P=P, P0=P0, G=P / P0, ratio=ratio, km=km, de=de)


def design_pool(s1, th_phys, n_keep=3000):
    """Re-run the Step-2 grid with the gap safety factor as an extra design variable.
    Nominal rules kept: f_d 16-30 Hz, f_p 18-30 Hz, margin >= 1.5, dipole validity.
    The swing rule is replaced by the gain / power objective."""
    grids = dict(
        L_d=np.arange(30, 121, 2.0) * MM, t_d=np.array([1.0, 1.5, 2.0, 2.5, 3.0]) * MM,
        b_d=np.array([10.0, 15.0, 20.0]) * MM, D_d=np.array([5.0, 6.0, 8.0, 10.0, 12.7]) * MM,
        h_d=np.array([2.0, 3.0, 4.0, 5.0, 6.0, 8.0]) * MM, m_add=np.array([0.0, 1.0, 2.0, 3.0]) * 1e-3,
        D_p=np.array([3.0, 4.0, 5.0, 6.0]) * MM, h_p=np.array([1.0, 1.5, 2.0, 3.0]) * MM)
    mesh = np.meshgrid(*[grids[v] for v in S.DESIGN_VARS], indexing="ij")
    flat = {v: m.ravel() for v, m in zip(S.DESIGN_VARS, mesh)}
    pools = []
    for i, Lp in enumerate(L_PIEZO):
        kp, mu_p = s1["kp"][i], s1["mu_p"]
        r = S.evaluate(Lp, kp, mu_p, **flat)
        base = ((r["fd"] >= 16) & (r["fd"] <= 30) & (r["fp"] >= 18) & (r["fp"] <= 30))
        idx = np.nonzero(base)[0]
        out = []
        for SF in (1.2, 1.35, 1.5, 1.75, 2.0, 2.5):
            dsn = S.d_snap(r["ks"][idx], r["C"][idx])
            dmin = SF * dsn
            Fav = r["C"][idx] / dmin ** 4
            big = np.maximum.reduce([flat["D_d"][idx], flat["h_d"][idx], flat["D_p"][idx]])
            ok = (Fav / r["Freq"] >= S.MARGIN_MIN) & (dmin >= 2 * big)
            j = idx[ok]
            if j.size == 0:
                continue
            mud = S.RHO_PETG * flat["b_d"][j] * flat["t_d"][j]
            mmd = S.magnet_mass(flat["D_d"][j], flat["h_d"][j]) + flat["m_add"][j]
            mmp = S.magnet_mass(flat["D_p"][j], flat["h_p"][j])
            mbd = S.MBASE_COEF * mud * flat["L_d"][j] + mmd
            mbp = S.MBASE_COEF * mu_p * Lp + mmp
            Xr = np.abs(rel_complex(r["kd"][j], r["md"][j], mbd, kp, r["mp"][j], mbp, r["fd"][j],
                                    S.ZETA_D, S.ZETA_P, S.A_BASE))
            out.append(dict(j=j, SF=np.full(j.size, SF), kd=r["kd"][j], md=r["md"][j], mbd=mbd,
                            mbeam=S.MEFF_COEF * mud * flat["L_d"][j], kp=np.full(j.size, kp),
                            mp=r["mp"][j], mbp=mbp, C=r["C"][j], fd=r["fd"][j], fp=r["fp"][j],
                            dsnap=dsn[ok], dmin=dmin[ok], g0=dmin[ok] + Xr,
                            dc=0.5 * (flat["h_d"][j] + flat["h_p"][j]), margin=(Fav / r["Freq"])[ok]))
        pool = {k: np.concatenate([o[k] for o in out]) for k in out[0]}
        nom = at_driver_mode(pool, th_phys[i], S.ZETA_D, S.ZETA_P)
        okn = nom["ratio"] >= 1.2
        pool = {k: v[okn] for k, v in pool.items()}
        for k in ("G", "P", "f"):
            pool[k + "_lin"] = nom[k][okn]
        pool["G_law"] = gain_law(pool["kd"], pool["md"], pool["mbd"], pool["kp"], pool["mp"], pool["mbp"],
                                 pool["C"], pool["g0"], S.ZETA_D)[0]
        n = pool["G_lin"].size
        keep = np.unique(np.concatenate([np.argsort(-pool["G_lin"])[:n_keep], np.argsort(-pool["P_lin"])[:n_keep],
                                         np.argsort(-pool["G_law"])[:300], RNG.choice(n, min(n, 1500), replace=False)]))
        pool = {k: v[keep] for k, v in pool.items()}
        pool["design"] = [{v: float(flat[v][jj]) for v in S.DESIGN_VARS} for jj in pool["j"]]
        pool["n_feasible_nominal"] = int(n)
        pools.append(pool)
    return pools


def draws(M):
    """Distributions as in the paper's Monte Carlo (judgements, not measurements)."""
    return dict(zd=RNG.uniform(0.015, 0.05, M), zp=RNG.uniform(0.01, 0.03, M),
                ekd=RNG.normal(0, 0.07, M), ekp=RNG.normal(0, 0.07, M), eC=RNG.normal(0, 0.07, M),
                eg=RNG.normal(0, 0.5 * MM, M), th=np.exp(RNG.normal(0, np.log(2) / 2, M)))


def perturb(sy, dr, k=None):
    g = (lambda x: x) if k is None else (lambda x: x[k])
    c = (lambda x: np.asarray(x)[..., None]) if k is None else (lambda x: x)
    return dict(kd=c(sy["kd"]) * (1 + g(dr["ekd"])), md=c(sy["md"]), mbd=c(sy["mbd"]),
                kp=c(sy["kp"]) * (1 + g(dr["ekp"])), mp=c(sy["mp"]), mbp=c(sy["mbp"]),
                C=c(sy["C"]) * (1 + g(dr["eC"])), g0=c(sy["g0"]) + g(dr["eg"]), dc=c(sy["dc"]))


def mc_eval(sy, dr, th):
    q = perturb(sy, dr)
    r = at_driver_mode(q, th * dr["th"], dr["zd"], dr["zp"])
    lat = r["ratio"] < 1.0
    G = np.where(lat, 0.0, r["G"])
    GL = np.where(lat, 0.0, gain_law(q["kd"], q["md"], q["mbd"], q["kp"], q["mp"], q["mbp"], q["C"], q["g0"], dr["zd"])[0])
    return dict(G=G, GL=GL, P=np.where(lat, 0.0, r["P"]), ratio=r["ratio"], f=r["f"])


def sysdict(src, j=None):
    keys = ("kd", "md", "mbd", "kp", "mp", "mbp", "C", "dc", "g0", "fd", "fp", "mbeam")
    return {k: (src[k][j] if j is not None else src[k]) for k in keys if k in src}


def td_params(sy, th, zd, zp, C=None):
    return dict(kd=sy["kd"], md=sy["md"], mbd=sy["mbd"], cd=2 * zd * np.sqrt(sy["kd"] * sy["md"]),
                kp=sy["kp"], mp=sy["mp"], mbp=sy["mbp"], cp=2 * zp * np.sqrt(sy["kp"] * sy["mp"]),
                C=sy["C"] if C is None else C, dc=sy["dc"], g0=sy["g0"], Cp=S.CP, R=S.R_LOAD, th=th,
                thd=0.0, Cpd=1e-9, Rd=1e6)


def robust_search(s1, red, th_phys):
    pools = design_pool(s1, th_phys)
    # ---- check the gain law and the exact linear model against the nonlinear simulation ----
    val = [(i, j) for i, pool in enumerate(pools) for j in RNG.choice(pool["G_lin"].size, 40, replace=False)]
    plist, fe = [], []
    for mg in (True, False):
        for i, j in val:
            plist.append(td_params(sysdict(pools[i], j), th_phys[i], S.ZETA_D, S.ZETA_P, C=None if mg else 0.0))
            fe.append(pools[i]["f_lin"][j])
    r = simulate(stack(plist), ("sine", np.full(len(plist), S.A_BASE), np.array(fe), 0.3), T=4.0, dt=4e-5, t_steady=2.0)
    nv = len(val)
    ok = ~r["contact"][:nv]
    G_sim = (r["P"][:nv] / r["P"][nv:])[ok]
    G_lin = np.array([pools[i]["G_lin"][j] for i, j in val])[ok]
    G_law = np.array([pools[i]["G_law"][j] for i, j in val])[ok]
    def stats(Gp):
        lg, ls = np.log(Gp), np.log(G_sim)
        e = np.abs(Gp / G_sim - 1)
        return dict(r2=float(1 - np.sum((lg - ls) ** 2) / np.sum((ls - ls.mean()) ** 2)),
                    ratio=float(np.exp(np.median(lg - ls))), med_err=float(np.median(e)), p90_err=float(np.percentile(e, 90)))
    weak = G_sim < 6
    law = dict(n=int(ok.sum()), lin=stats(G_lin), law=stats(G_law), G_sim=G_sim, G_lin=G_lin, G_law=G_law,
               len_idx=np.array([i for i, _ in val])[ok],
               law_weak=dict(n=int(weak.sum()), med_err=float(np.median(np.abs(G_law[weak] / G_sim[weak] - 1)))))
    # ---- Monte Carlo search: closest approach >= 1.2 d_snap in at least 95 % of draws ----
    M = 400
    dr = draws(M)
    results = []
    for i, pool in enumerate(pools):
        mc = mc_eval(sysdict(pool), dr, th_phys[i])
        medG, medP = np.median(mc["G"], axis=1), np.median(mc["P"], axis=1)
        p_low = (mc["ratio"] < 1.2).mean(axis=1)
        feas = p_low <= 0.05
        jg = int(np.argmax(np.where(feas, medG, -1)))
        jp = int(np.argmax(np.where(feas, medP, -1)))
        jl = int(np.argmax(np.where(feas, np.median(mc["GL"], axis=1), -1)))
        p0 = S.system_params("redesign", i, s1, red); d0 = red[i]["design"]
        cur = dict(sysdict(p0), mbeam=S.MEFF_COEF * S.RHO_PETG * d0["b_d"] * d0["t_d"] * d0["L_d"])
        mcc = mc_eval({k: np.array([v]) for k, v in cur.items()}, dr, th_phys[i])
        nomc = at_driver_mode(cur, th_phys[i], S.ZETA_D, S.ZETA_P)
        def summ(mcx, j, design, sy, SF, nomG, nomP, fd, fp, margin):
            return dict(design=design, sys=sy, SF=SF, G_nom=float(nomG), P_nom=float(nomP) * 1e6,
                        medG=float(np.median(mcx["G"][j])), p5G=float(np.percentile(mcx["G"][j], 5)),
                        medGL=float(np.median(mcx["GL"][j])),
                        medP=float(np.median(mcx["P"][j])) * 1e6, p5P=float(np.percentile(mcx["P"][j], 5)) * 1e6,
                        p_low=float((mcx["ratio"][j] < 1.2).mean()), p_15=float((mcx["ratio"][j] < 1.5).mean()),
                        p_latch=float((mcx["ratio"][j] < 1.0).mean()), fd=float(fd), fp=float(fp), margin=float(margin),
                        G_hist=mcx["G"][j], P_hist=mcx["P"][j])
        ent = {"current redesign": summ(mcc, 0, d0, cur, float("nan"), nomc["G"], nomc["P"], p0["fd"], p0["fp"],
                                        red[i]["metrics"]["margin"])}
        for name, j in (("max median gain", jg), ("max median power", jp), ("max median gain-law value", jl)):
            ent[name] = summ(mc, j, pool["design"][j], dict(sysdict(pool, j), mbeam=pool["mbeam"][j]), float(pool["SF"][j]),
                             pool["G_lin"][j], pool["P_lin"][j], pool["fd"][j], pool["fp"][j], pool["margin"][j])
            ent[name]["dmin"] = float(pool["dmin"][j]); ent[name]["g0"] = float(pool["g0"][j])
        ent["current redesign"]["dmin"] = float(p0["dmin"]); ent["current redesign"]["g0"] = float(p0["g0"])
        results.append(dict(i=i, ent=ent, n_pool=pool["n_feasible_nominal"]))
    # ---- nonlinear time-domain check on 48 shared draws, each at its own driver mode ----
    K = 48
    plist, tags, fe = [], [], []
    names = ("current redesign", "max median gain", "max median power")
    for res in results:
        i = res["i"]
        for name in names:
            sy = res["ent"][name]["sys"]
            for k in range(K):
                q = {kk: float(np.squeeze(v)) for kk, v in perturb(sy, dr, k).items()}
                f0 = float(at_driver_mode(q, th_phys[i] * dr["th"][k], dr["zd"][k], dr["zp"][k])["f"])
                for mg in (True, False):
                    plist.append(td_params(q, th_phys[i] * dr["th"][k], dr["zd"][k], dr["zp"][k], C=None if mg else 0.0))
                    tags.append((i, name, k, mg)); fe.append(f0)
    r = simulate(stack(plist), ("sine", np.full(len(plist), S.A_BASE), np.array(fe), 0.3), T=4.0, dt=2.5e-5, t_steady=2.0)
    tags = np.array([(t[0], names.index(t[1]), t[2], t[3]) for t in tags])
    td = {}
    for res in results:
        i = res["i"]
        for n_, name in enumerate(names):
            w = np.nonzero((tags[:, 0] == i) & (tags[:, 1] == n_) & (tags[:, 3] == 1))[0]
            wo = np.nonzero((tags[:, 0] == i) & (tags[:, 1] == n_) & (tags[:, 3] == 0))[0]
            latched = r["contact"][w]
            G = np.where(latched, 0.0, r["P"][w] / r["P"][wo])
            res["ent"][name]["td"] = dict(medG=float(np.median(G)), medP=float(np.median(np.where(latched, 0, r["P"][w]))) * 1e6,
                                          platch=float(latched.mean()))
    return results, law, dr


# =============================================================================
# 3. Sweep-past geometry, finite-size magnets
# =============================================================================
def cyl_points(D, h, nr=5, nt=12, nz=5):
    """Sub-dipole points of a cylinder magnetised along y. Returns (pts[n,3], dV[n])."""
    pts, dV = [], []
    redges = np.linspace(0, D / 2, nr + 1)
    for a, b in zip(redges[:-1], redges[1:]):
        rm = 0.5 * (a + b); area = np.pi * (b ** 2 - a ** 2)
        for th in np.linspace(0, 2 * np.pi, nt, endpoint=False) + (np.pi / nt if a > 0 else 0):
            for yz in (np.arange(nz) + 0.5) / nz - 0.5:
                pts.append((rm * np.cos(th), yz * h, rm * np.sin(th)))
                dV.append(area / nt * h / nz)
    return np.array(pts), np.array(dV)


def side_force(Dd, hd, Dp, hp, gap, s, Br=S.BR):
    """Force on the piezo magnet (vector, y = across the gap, z = beam motion) when its
    centre is offset by s along z. Both magnets magnetised along +y (attracting).
    gap = face-to-face distance at s = 0. Sum over sub-dipoles."""
    P1, V1 = cyl_points(Dd, hd); P2, V2 = cyl_points(Dp, hp)
    M = Br / S.MU0
    m1, m2 = M * V1, M * V2
    yc = hd / 2 + gap + hp / 2
    Fy = np.zeros(len(s)); Fz = np.zeros(len(s))
    K = 3 * S.MU0 / (4 * np.pi)
    for k, sk in enumerate(s):
        r = (P2[None, :, :] + np.array([0, yc, sk])) - P1[:, None, :]
        rx, ry, rz = r[..., 0], r[..., 1], r[..., 2]
        r2 = rx ** 2 + ry ** 2 + rz ** 2
        pre = K * m1[:, None] * m2[None, :] / r2 ** 2.5
        # F = pre [ 2 r_y yhat + r - 5 r_y^2 r / r^2 ]
        fac = 1 - 5 * ry ** 2 / r2
        Fy[k] = np.sum(pre * (2 * ry + ry * fac))
        Fz[k] = np.sum(pre * rz * fac)
    return Fy, Fz


def check_force_model():
    """Coaxial far-field check against C/d^4 and the sign/shape of Fz(s)."""
    d = np.array([10, 15, 20, 30]) * MM
    out = []
    for dd in d:
        gap = dd - MAG_H
        Fy, _ = side_force(S.MAG_D, S.MAG_H, S.MAG_D, S.MAG_H, gap, np.array([0.0]))
        C = S.force_const(S.dipole(S.MAG_D, S.MAG_H), S.dipole(S.MAG_D, S.MAG_H))
        out.append((dd / MM, -Fy[0] * 1e3, C / dd ** 4 * 1e3))
    return out


MAG_H = S.MAG_H


def lateral_k(s1, i, d):
    """Sideways (width-direction) tip stiffness of piezo and driver beams."""
    EIy = {"A": S.E_PETG * S.T_PETG * S.WIDTH ** 3 / 12,
           "B": S.E_PETG * S.T_PETG * S.WIDTH ** 3 / 12 + S.E_CU * S.T_CU * S.BIMORPH_W ** 3 / 12,
           "C": S.E_PETG * S.T_PETG * S.WIDTH ** 3 / 12 + (2 * S.E_PZT * S.T_PZT + S.E_CU * S.T_CU) * S.BIMORPH_W ** 3 / 12,
           "D": S.E_PETG * S.T_PETG * S.WIDTH ** 3 / 12}
    kyp = S.k_series(L_PIEZO[i], EI=EIy)
    kyd = 3 * S.E_PETG * d["t_d"] * d["b_d"] ** 3 / 12 / d["L_d"] ** 3
    return kyp, kyd


def short_piezo(s1, red, L=60 * MM):
    """Variant: the 105 mm redesign driver with a shortened piezo beam (same layup, 4 x 2 mm magnet),
    so f_p is several times f_d. Breaks the 18-30 Hz piezo band on purpose."""
    p = dict(S.system_params("redesign", 2, s1, red))
    k, sh = S.k_series(L, shares=True)
    mmp = S.magnet_mass(4 * MM, 2 * MM)
    mp = S.MEFF_COEF * s1["mu_p"] * L + mmp
    ce = S.coupling_estimates(s1)
    kap2 = S.K31 ** 2 * sh[2] * ce["frac_pzt"]
    p.update(kp=k, mp=mp, mbp=S.MBASE_COEF * s1["mu_p"] * L + mmp, cp=2 * S.ZETA_P * np.sqrt(k * mp),
             fp=S.fn(k, mp), Freq=k * S.DELTA_REQ)
    return p, float(np.sqrt(kap2 * k * S.CP)), L


def sweep_past(s1, red, th_phys):
    """Sweep-past layout: the driver magnet slides past the piezo magnet across a sideways gap.
    Same beams as the redesign; the driver magnet is resized (dead mass keeps f_d) and the gap chosen."""
    s_grid = np.arange(-25, 25.001, 0.25) * MM
    gaps = np.array([1.5, 2, 3, 4, 6, 8]) * MM
    dmags = [(D * MM, h * MM) for D in (3, 4, 5, 6, 8) for h in (1, 2, 3)]
    cases = []
    for i in range(3):
        d = red[i]["design"]
        cases.append((LBL[i], i, S.system_params("redesign", i, s1, red), th_phys[i], d["D_p"], d["h_p"], d))
    ps, ths, Ls = short_piezo(s1, red)
    cases.append((f"{Ls / MM:.0f} mm piezo + 105 mm driver", 3, ps, ths, 4 * MM, 2 * MM, red[2]["design"]))
    meta = []
    for name, i, p0, thi, Dp, hp, d in cases:
        kyp, kyd = lateral_k(s1, min(i, 2), d)
        if i == 3:
            kyp *= (L_PIEZO[2] / Ls) ** 3            # shorter piezo is stiffer sideways too
        kys = kyp * kyd / (kyp + kyd)
        for Dd, hd in dmags:
            for gp in gaps:
                Fy, Fz = side_force(Dd, hd, Dp, hp, gp, s_grid)
                Fy1, _ = side_force(Dd, hd, Dp, hp, gp + 0.1 * MM, np.array([0.0]))
                Fy0 = Fy[np.argmin(np.abs(s_grid))]
                lat_margin = kys / abs((Fy1[0] - Fy0) / (0.1 * MM))
                Fpk = np.max(np.abs(Fz)); s_pk = abs(s_grid[np.argmax(np.abs(Fz))])
                pull = Fpk / p0["kp"]
                ok = (lat_margin >= 1.5) and (Fpk >= 1.5 * p0["Freq"]) and (pull + s_pk <= 0.8 * p0["Xrel"])
                meta.append(dict(case=name, i=i, p=p0, th=thi, Dd=Dd, hd=hd, gap=gp, Fz=Fz, Fpk=Fpk, s_pk=s_pk, pull=pull,
                                 margin=Fpk / p0["Freq"], lat_margin=lat_margin, ok=ok, fd=p0["fd"], fp=p0["fp"]))
    feas = [m for m in meta if m["ok"]]
    runs = []
    for m in feas:
        for s0 in (0.0, 3 * MM):
            runs.append(dict(m, s0=s0))
    plist = []
    for m in runs:
        q = base_params(m["p"], m["th"]); q["s0"] = m["s0"]; plist.append(q)
    r = simulate(stack(plist), ("sine", np.full(len(runs), S.A_BASE), np.array([m["fd"] for m in runs]), 0.3), T=3.0,
                 dt=4e-5, mode="side", table=(s_grid, np.array([m["Fz"] for m in runs])), keep=np.arange(len(runs)), keep_every=5)
    tr = r["trace"]
    for j, m in enumerate(runs):
        t = tr["t"]; ss = t >= 1.0
        V = tr["V"][ss, j]
        n = 8 * len(V)
        e = np.abs(np.fft.rfft((V - V.mean()) * np.hanning(len(V)), n)) ** 2
        fr = np.fft.rfftfreq(n, t[1] - t[0])
        tot = e[(fr > 2) & (fr < 300)].sum()
        band = lambda f0, bw=1.0: e[(fr > f0 - bw) & (fr < f0 + bw)].sum()
        harm = sum(band(k * m["fd"]) for k in range(1, 20))
        m.update(Vpk=r["Vpk"][j], P=r["P"][j], xp=r["xppk"][j], xd=r["xdpk"][j],
                 fp_share=band(m["fp"], 1.5) / tot, nonharm=max(0.0, 1 - harm / tot))
    best = {}
    for name, i, p0, thi, Dp, hp, d in cases:
        c = [m for m in runs if m["case"] == name]
        if not c:
            best[name] = None; continue
        b = max(c, key=lambda m: m["P"])
        bu = max(c, key=lambda m: m["nonharm"])
        v = 2 * np.pi * p0["fd"] * p0["Xrel"]
        best[name] = dict(power=b, upconv=bu, rel=single_pass(p0, thi, b, s_grid, v),
                          rel_u=single_pass(p0, thi, bu, s_grid, v), n_feasible=len([m for m in meta if m["case"] == name and m["ok"]]),
                          n_total=len([m for m in meta if m["case"] == name]), i=i, p=p0)
    return meta, best, s_grid, cases


def single_pass(p, th, b, s_grid, v, T=0.6):
    """Driver moves at constant speed v from s=-20 mm to +20 mm past the piezo (quasi-static
    start), then stops. Measures pull (max piezo deflection before release) and free ring."""
    from scipy.integrate import solve_ivp
    Fz = b["Fz"]
    z0 = -20 * MM
    tpass = 40 * MM / v

    def zd(t):
        return z0 + v * min(t, tpass)

    def rhs(t, y):
        xp, vp, V = y
        s = b["s0"] + xp - zd(t)
        F = np.interp(s, s_grid, Fz)
        return [vp, (-p["cp"] * vp - p["kp"] * xp - th * V + F) / p["mp"], (th * vp - V / p["R"]) / p["Cp"]]
    t = np.linspace(0, tpass + T, 12000)
    sol = solve_ivp(rhs, (0, t[-1]), [0.0, 0.0, 0.0], method="LSODA", t_eval=t, max_step=1e-4, rtol=1e-8, atol=1e-11)
    xp, V = sol.y[0], sol.y[2]
    # release time: when |s| passes s_pk with the piezo's peak pull
    pull = np.max(np.abs(xp[sol.t <= tpass]))
    after = sol.t > tpass
    ring = np.max(np.abs(xp[after]))
    # 10-90 % force-fall time during release
    s_tr = b["s0"] + xp - np.array([zd(tt) for tt in sol.t])
    F_tr = np.interp(s_tr, s_grid, Fz)
    k_pk = int(np.argmax(np.abs(F_tr)))
    Fp = abs(F_tr[k_pk]); tail = np.abs(F_tr[k_pk:])
    t90 = sol.t[k_pk + np.argmax(tail < 0.9 * Fp)]; t10 = sol.t[k_pk + np.argmax(tail < 0.1 * Fp)]
    return dict(t=sol.t, xp=xp, V=V, zd=np.array([zd(tt) for tt in sol.t]), pull=pull, ring=ring, R=ring / pull,
                t_rel=t10 - t90, T_p=1 / p["fp"], Vpk=np.max(np.abs(V[after])), tpass=tpass)


# =============================================================================
# 4. Recorded vehicle vibration
# =============================================================================
def load_recording(path, fs=2000.0):
    import csv
    rows = list(csv.reader(open(path)))
    h = rows[0]; a = np.array(rows[1:], float)
    t = a[:, 0]; z = a[:, h.index("gforce_z")] * 9.80665
    tt = np.arange(t[0], t[-1], 1 / fs)
    zz = np.interp(tt, t, z)
    sos = butter(4, [3.0, 45.0], btype="band", fs=fs, output="sos")
    zz = sosfiltfilt(sos, zz)
    return tt, zz, fs, (t, z)


def vehicle_runs(s1, red, th_phys, sp_best, drv_best, path):
    tt, az, fs, raw = load_recording(path)
    segs = {"asphalt": (280.0, 306.0), "cobblestone": (210.0, 270.0)}
    out = {}
    # systems: redesign coax (3), magnets removed (3), sweep-past best (3), coax + driver transducer (3)
    plist, tags, modes = [], [], []
    for i in range(3):
        p0 = S.system_params("redesign", i, s1, red)
        q = base_params(p0, th_phys[i]); plist.append(q); tags.append((i, "Redesign (coaxial)"))
        q = base_params(p0, th_phys[i]); q["C"] = 0.0; plist.append(q); tags.append((i, "Magnets removed"))
        sel = drv_best[i]["sel"]
        if sel is not None:
            q = base_params(p0, th_phys[i])
            q.update(kd=sel["k"], md=sel["md"], mbd=sel["mbd"], cd=sel["cd"], thd=sel["th_d"], Cpd=sel["Cpd"], Rd=sel["Rd"])
            plist.append(q); tags.append((i, "Redesign + driver bimorph"))
    sp_list, sp_tags, sp_tabs = [], [], []
    for i in range(3):
        bb = sp_best.get(LBL[i])
        if bb is None:
            continue
        b = bb["power"]
        p0 = S.system_params("redesign", i, s1, red)
        q = base_params(p0, th_phys[i]); q["s0"] = b["s0"]
        sp_list.append(q); sp_tags.append((i, "Sweep-past")); sp_tabs.append(b["Fz"])
    s_grid = np.arange(-25, 25.001, 0.25) * MM
    for name, (t0, t1) in segs.items():
        m = (tt >= t0) & (tt < t1)
        a = az[m]
        # synthetic noise: white noise band-passed to the same band, same RMS
        wn = sosfiltfilt(butter(4, [3.0, 45.0], btype="band", fs=fs, output="sos"), RNG.normal(size=a.size))
        wn *= a.std() / wn.std()
        dt = 1 / fs / 2 * 0 + 2.5e-4        # integrate at 4 kHz; input sampled at dt/2 = 8 kHz
        def up(x):
            tx = np.arange(x.size) / fs
            tq = np.arange(0, tx[-1], dt / 2)
            return np.interp(tq, tx, x), tq[-1]
        res = {}
        for src, sig in (("recorded", a), ("synthetic noise", wn)):
            series, Tlen = up(sig)
            T = Tlen - 2 * dt
            r1 = simulate(stack(plist), ("series", series, np.ones(len(plist))), T=T, dt=dt, t_steady=2.0,
                          keep=np.arange(len(plist)), keep_every=4)
            r2 = simulate(stack(sp_list), ("series", series, np.ones(len(sp_list))), T=T, dt=dt, t_steady=2.0,
                          mode="side", table=(s_grid, np.array(sp_tabs)))
            for j, tg in enumerate(tags):
                res[(src,) + tg] = dict(P=r1["P"][j] + r1["Pd"][j], Pp=r1["P"][j], Pd=r1["Pd"][j], Vpk=r1["Vpk"][j],
                                       gmin=r1["gmin"][j], contact=bool(r1["contact"][j]), xd=r1["xdpk"][j])
            for j, tg in enumerate(sp_tags):
                res[(src,) + tg] = dict(P=r2["P"][j], Pp=r2["P"][j], Pd=0.0, Vpk=r2["Vpk"][j], gmin=np.nan,
                                       contact=False, xd=r2["xdpk"][j])
            if src == "recorded":
                res["trace"] = (r1["trace"], tags)
        f, Pxx = welch(a, fs=fs, nperseg=4096)
        out[name] = dict(res=res, rms=float(a.std()), f=f, Pxx=Pxx, seg=(t0, t1),
                         rms_band=float(np.sqrt(np.trapezoid(Pxx[(f > 14) & (f < 32)], f[(f > 14) & (f < 32)]))))
    return out, (tt, az, raw)


# =============================================================================
# 5. First experiment: low-amplitude sweep predictions
# =============================================================================
def experiment(s1, red, th_phys):
    amps = np.array([0.1, 0.2, 0.3, 0.5])
    freqs = np.arange(10.0, 32.01, 0.1)
    plist, tags = [], []
    for i in range(3):
        p0 = S.system_params("redesign", i, s1, red)
        for a in amps:
            for f in freqs:
                for mg in (True, False):
                    q = base_params(p0, th_phys[i])
                    if not mg:
                        q["C"] = 0.0
                    q["_a"] = a; q["_f"] = f
                    plist.append(q); tags.append((i, a, f, mg))
    A = np.array([p.pop("_a") for p in plist]); F = np.array([p.pop("_f") for p in plist])
    r = simulate(stack(plist), ("sine", A, F, 0.3), T=5.0, dt=1e-4, t_steady=3.5)
    tab = {}
    for i in range(3):
        p0 = S.system_params("redesign", i, s1, red)
        # linear two-mode prediction (magnets = negative coupling spring k_m at the equilibrium gap)
        ks = p0["kd"] * p0["kp"] / (p0["kd"] + p0["kp"])
        de = float(eq_gap(p0["C"], p0["g0"], ks)); km = 4 * p0["C"] / de ** 5
        K = np.array([[p0["kd"] - km, km], [km, p0["kp"] - km]]); Mm = np.diag([p0["md"], p0["mp"]])
        ev = np.sort(np.sqrt(np.linalg.eigvals(np.linalg.solve(Mm, K)).real) / (2 * np.pi))
        G_law = float(gain_law(p0["kd"], p0["md"], p0["mbd"], p0["kp"], p0["mp"], p0["mbp"], p0["C"], p0["g0"], S.ZETA_D)[0])
        for a in amps:
            w = [n for n, t in enumerate(tags) if t[0] == i and t[1] == a and t[3]]
            wo = [n for n, t in enumerate(tags) if t[0] == i and t[1] == a and not t[3]]
            P, P0 = r["P"][w], r["P"][wo]
            def peak_near(f0, bw=1.0):
                from scipy.signal import find_peaks
                pk, _ = find_peaks(P)
                pk = pk[np.abs(freqs[pk] - f0) <= bw]
                if pk.size == 0:
                    m = np.abs(freqs - f0) <= bw
                    return int(np.nonzero(m)[0][np.argmax(P[m])])
                return int(pk[np.argmin(np.abs(freqs[pk] - f0))])
            Xd = r["xdpk"][w]
            mlo = np.abs(freqs - ev[0]) <= 1.0
            klo = int(np.nonzero(mlo)[0][np.argmax(Xd[mlo])])          # lower mode: peak of driver motion
            khi = peak_near(ev[1])                                       # upper mode: peak of piezo voltage
            mdip = (freqs > ev[0] - 1.5) & (freqs < ev[1])
            kdip = int(np.nonzero(mdip)[0][np.argmin((P / P0)[mdip])])   # where the magnets hurt most
            k = int(np.argmin(np.abs(freqs - p0["fd"])))
            kk = klo
            tab[(i, a)] = dict(f_lo=float(freqs[klo]), f_hi=float(freqs[khi]), G_lo=float(P[klo] / P0[klo]),
                               f_dip=float(freqs[kdip]), G_dip=float(P[kdip] / P0[kdip]), f_lin_lo=float(ev[0]), f_lin_hi=float(ev[1]),
                               f_pz0=float(freqs[int(np.argmax(P0))]), P=P, P0=P0,
                               G_fd=float(P[k] / P0[k]), G_mode=float(P[kk] / P0[kk]), G_law=G_law,
                               Vpk_fd=float(r["Vpk"][w][k]), Vpk0_fd=float(r["Vpk"][wo][k]),
                               Vpk_max=float(r["Vpk"][w].max()), gmin=float(r["gmin"][w].min()),
                               Xd_fd=float(r["xdpk"][w][k]), km=km, de=de)
    return amps, freqs, tab


# =============================================================================
# plots + tables
# =============================================================================
def savefig(fig, name):
    fig.savefig(os.path.join(PLOTS, name), dpi=160, bbox_inches="tight"); plt.close(fig)


def main(rec_path):
    t0 = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        s1, _ = S.step1()
        red, _ = S.step2(s1)
    th = S.coupling_estimates(s1)["th_phys"]
    T, summ = {}, {}

    # ---------- 1. driver transducer ----------
    print("1. driver transducer ...", flush=True)
    drv, drv_all = driver_transducer(s1, red, th)
    rows = []
    for i, b in enumerate(drv):
        ref, root, sel = b["ref"], b["root"], b["sel"]
        rows.append([LBL[i], "no driver bimorph", "-", f"{ref['Pdamp'] * 1e3:.2f}", "-", "-",
                     f"{ref['Pp'] * 1e6:.1f}", "-", f"{ref['xd'] / MM:.2f}", f"{ref['Vpk']:.2f}", "-"])
        for tag, m in (("at clamp, no strain limit", root), ("best within 500 ue strain", sel)):
            if m is None:
                continue
            rows.append([LBL[i], tag, f"{m['x0'] / MM:.1f}-{(m['x0'] + m['lb']) / MM:.1f}", f"{m['Pdamp'] * 1e3:.2f}",
                         f"{m['kap2']:.4f}", f"{m['Pd'] * 1e6:.0f}", f"{m['Pp'] * 1e6:.1f}",
                         f"{(m['Pd'] + m['Pp']) / ref['Pp']:.1f}x", f"{m['xd'] / MM:.2f}", f"{m['Vdpk']:.1f}",
                         f"{m['strain'] * 1e6:.0f}"])
    T["drv"] = S.md_table(["Config", "Driver bimorph", "position from clamp (mm)", "driver damping loss (mW)",
                           "kappa^2 driver", "P driver bimorph (uW)", "P piezo (uW)", "total / piezo-only",
                           "driver tip (mm)", "V peak (driver)", "PZT strain (ue)"], rows)
    summ["drv"] = [dict(Pdamp_mW=b["ref"]["Pdamp"] * 1e3, Pp_uW=b["ref"]["Pp"] * 1e6,
                        root_Pd_uW=b["root"]["Pd"] * 1e6, root_strain_ue=b["root"]["strain"] * 1e6,
                        sel=None if b["sel"] is None else dict(x0_mm=b["sel"]["x0"] / MM, lb_mm=b["sel"]["lb"] / MM,
                                                                Pd_uW=b["sel"]["Pd"] * 1e6, Pp_uW=b["sel"]["Pp"] * 1e6,
                                                                strain_ue=b["sel"]["strain"] * 1e6, m_dead_g=b["sel"]["m_dead"] * 1e3,
                                                                kd=b["sel"]["k"], Rd_Mohm=b["sel"]["Rd"] / 1e6,
                                                                Vdpk=b["sel"]["Vdpk"], gmin_mm=b["sel"]["gmin"] / MM))
                   for b in drv]
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    for i in range(3):
        c = [m for m in drv_all if not m["ref"] and m["i"] == i]
        for lb, mk in ((40 * MM, "o"), (20 * MM, "s"), (10 * MM, "^")):
            cc = [m for m in c if m["lb"] == lb]
            ax[i].scatter([m["strain"] * 1e6 for m in cc], [m["Pd"] * 1e6 for m in cc], marker=mk, s=22,
                          c=[m["x0"] / MM for m in cc], cmap="viridis", label=f"{lb / MM:.0f} mm bimorph")
        ax[i].axvline(STRAIN_LIMIT * 1e6, color="#d62728", ls="--", lw=1)
        ax[i].axhline(drv[i]["ref"]["Pp"] * 1e6, color="k", ls=":", lw=1)
        ax[i].set_xscale("log"); ax[i].set_yscale("log")
        ax[i].xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax[i].set_title(f"{LBL[i]} redesign: driver bimorph options", fontsize=9)
        ax[i].set_xlabel("peak PZT strain (microstrain)"); ax[i].set_ylabel("driver bimorph power (uW)")
        ax[i].text(STRAIN_LIMIT * 1e6 * 1.05, ax[i].get_ylim()[0] * 1.5, "500 ue limit", color="#d62728", fontsize=7)
        ax[i].text(ax[i].get_xlim()[0] * 1.1, drv[i]["ref"]["Pp"] * 1e6 * 1.15, "piezo beam alone", fontsize=7)
    ax[0].legend(fontsize=7, loc="lower right")
    fig.suptitle("Driver bimorph: power vs strain (colour = distance of bimorph from the clamp, mm)", fontsize=10)
    savefig(fig, "11_driver_bimorph.png")

    # ---------- 2. gain law + robust search ----------
    print("2. gain law + robust search ...", flush=True)
    rob, law, dr = robust_search(s1, red, th)
    T["law"] = S.md_table(["Predictor", "designs", "median predicted / simulated", "median abs. error", "90th pct abs. error", "R² (log gain)"],
                          [["Gain law, eq. 20 (closed form)", law["n"], f"{law['law']['ratio']:.2f}", f"{law['law']['med_err'] * 100:.0f}%",
                            f"{law['law']['p90_err'] * 100:.0f}%", f"{law['law']['r2']:.2f}"],
                           ["Exact linear two-mode model", law["n"], f"{law['lin']['ratio']:.2f}", f"{law['lin']['med_err'] * 100:.0f}%",
                            f"{law['lin']['p90_err'] * 100:.0f}%", f"{law['lin']['r2']:.2f}"],
                           [f"Gain law, designs with simulated gain < 6", law["law_weak"]["n"], "-",
                            f"{law['law_weak']['med_err'] * 100:.0f}%", "-", "-"]])
    rows, drows = [], []
    for res in rob:
        i = res["i"]
        for name, e in res["ent"].items():
            tdv = e.get("td")
            rows.append([LBL[i], name, f"{e['G_nom']:.1f}", f"{e['medG']:.1f}", f"{e['p5G']:.1f}", f"{e['medGL']:.1f}",
                         f"{e['P_nom']:.1f}", f"{e['medP']:.1f}", f"{e['p5P']:.2f}",
                         f"{e['p_15'] * 100:.0f}%", f"{e['p_low'] * 100:.1f}%", f"{e['p_latch'] * 100:.1f}%",
                         "-" if tdv is None else f"{tdv['medG']:.1f}", "-" if tdv is None else f"{tdv['medP']:.1f}",
                         "-" if tdv is None else f"{tdv['platch'] * 100:.0f}%"])
            d = e["design"]
            drows.append([LBL[i], name, f"{d['L_d'] / MM:.0f}", f"{d['t_d'] / MM:.1f}", f"{d['b_d'] / MM:.0f}",
                          f"{d['D_d'] / MM:.1f} x {d['h_d'] / MM:.0f}", f"{d['m_add'] * 1e3:.0f}", f"{d['D_p'] / MM:.0f} x {d['h_p'] / MM:.1f}",
                          "1.5 (two-body)" if not np.isfinite(e["SF"]) else f"{e['SF']:.2f}", f"{e['dmin'] / MM:.1f}", f"{e['g0'] / MM:.1f}",
                          f"{e['fd']:.1f}", f"{e['fp']:.1f}", f"{e['margin']:.2f}"])
    T["robust"] = S.md_table(["Config", "Design", "gain, nominal", "median gain", "5th pct gain", "median gain-law value",
                              "P nominal (uW)", "median P (uW)", "5th pct P (uW)", "below 1.5x snap", "below 1.2x snap",
                              "inside snap gap", "median gain, nonlinear sim (48)", "median P, nonlinear sim (uW)", "latched, sim"], rows)
    T["robust_design"] = S.md_table(["Config", "Design", "driver L (mm)", "t (mm)", "b (mm)", "driver magnet (mm)", "added mass (g)",
                                     "piezo magnet (mm)", "gap safety factor", "closest approach (mm)", "rest gap (mm)",
                                     "f_d (Hz)", "f_p (Hz)", "margin"], drows)
    summ["law"] = {k: v for k, v in law.items() if not isinstance(v, np.ndarray)}
    summ["robust"] = [{"config": LBL[r_["i"]], "n_pool": r_["n_pool"],
                       **{n: {k: v for k, v in e.items() if k not in ("G_hist", "P_hist", "sys")} for n, e in r_["ent"].items()}}
                      for r_ in rob]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    for i in range(3):
        m = law["len_idx"] == i
        ax[0].scatter(law["G_sim"][m], law["G_law"][m], s=14, color=COL[i], marker="x", label=f"{LBL[i]} gain law")
        ax[0].scatter(law["G_sim"][m], law["G_lin"][m], s=14, facecolors="none", edgecolors=COL[i], label=f"{LBL[i]} linear model")
    lim = [1, max(law["G_sim"].max(), law["G_law"].max()) * 1.2]
    ax[0].plot(lim, lim, "k--", lw=1); ax[0].set_xscale("log"); ax[0].set_yscale("log")
    ax[0].set_xlabel("power gain, nonlinear simulation"); ax[0].set_ylabel("predicted power gain")
    ax[0].legend(fontsize=6, ncol=2); ax[0].set_title("Gain law (x) and exact linear model (o) vs simulation", fontsize=9)
    for res in rob:
        i = res["i"]
        for name, ls in (("current redesign", ":"), ("max median gain", "-"), ("max median power", "--")):
            e = res["ent"][name]
            g = np.sort(e["G_hist"]); p = np.sort(e["P_hist"]) * 1e6
            y = np.linspace(0, 1, g.size)
            ax[1].plot(g, y, color=COL[i], ls=ls, lw=1.4)
            ax[2].plot(np.maximum(p, 1e-3), y, color=COL[i], ls=ls, lw=1.4)
    ax[1].set_xscale("log"); ax[2].set_xscale("log")
    ax[1].set_xlabel("power gain from magnets (400 draws)"); ax[1].set_ylabel("fraction of draws below")
    ax[2].set_xlabel("power into 1 MΩ, µW (400 draws)")
    from matplotlib.lines import Line2D
    hs = [Line2D([], [], color="k", ls=":", label="current redesign"), Line2D([], [], color="k", ls="-", label="max median gain"),
          Line2D([], [], color="k", ls="--", label="max median power")] + [Line2D([], [], color=COL[i], label=LBL[i]) for i in range(3)]
    ax[1].legend(handles=hs, fontsize=7)
    ax[1].set_title("Gain under uncertainty (400 draws)", fontsize=9)
    ax[2].set_title("Power under uncertainty (same designs)", fontsize=9)
    savefig(fig, "12_gain_law_robust.png")

    # ---------- 3. sweep-past ----------
    print("3. sweep-past ...", flush=True)
    chk = check_force_model()
    T["fcheck"] = S.md_table(["centre distance (mm)", "sub-dipole model (mN)", "point dipole C/d^4 (mN)"],
                             [[f"{a:.0f}", f"{b:.3f}", f"{c:.3f}"] for a, b, c in chk])
    sp_meta, sp_best, s_grid, sp_cases = sweep_past(s1, red, th)
    rows = []
    for name, bb in sp_best.items():
        if bb is None:
            rows.append([name, "no layout passes the rules"] + ["-"] * 13); continue
        for tag, b, rl in (("most power", bb["power"], bb["rel"]), ("most energy off the f_d harmonics", bb["upconv"], bb["rel_u"])):
            rows.append([name, tag, f"{b['Dd'] / MM:.0f} x {b['hd'] / MM:.0f}", f"{b['gap'] / MM:.1f}", f"{b['s0'] / MM:.0f}",
                         f"{b['pull']:.4f}" if False else f"{b['pull'] / MM:.2f}", f"{b['lat_margin']:.1f}", f"{rl['t_rel'] * 1e3:.1f}",
                         f"{rl['t_rel'] / rl['T_p']:.2f}", f"{rl['R']:.2f}", f"{b['fd']:.1f} / {b['fp']:.1f}", f"{b['Vpk']:.2f}",
                         f"{b['P'] * 1e6:.1f}", f"{b['fp_share'] * 100:.1f}%", f"{b['nonharm'] * 100:.1f}%"])
    T["sweep_past"] = S.md_table(["Case", "Pick", "driver magnet (mm)", "gap (mm)", "rest offset (mm)", "static pull (mm)",
                                  "sideways snap margin", "release time (ms)", "release / T_p", "ring / pull", "f_d / f_p (Hz)",
                                  "V peak (steady)", "P avg (uW)", "voltage energy near f_p", "energy off f_d harmonics"], rows)
    T["sweep_past_count"] = S.md_table(["Case", "layouts tried", "layouts passing the rules"],
                                       [[n, bb["n_total"], bb["n_feasible"]] for n, bb in sp_best.items() if bb is not None])
    summ["sweep_past"] = {n: (None if bb is None else {
        k: dict(Dd_mm=b["Dd"] / MM, hd_mm=b["hd"] / MM, gap_mm=b["gap"] / MM, s0_mm=b["s0"] / MM, pull_mm=b["pull"] / MM,
                lat_margin=b["lat_margin"], Vpk=b["Vpk"], P_uW=b["P"] * 1e6, fp_share=b["fp_share"], nonharm=b["nonharm"],
                release_ms=rl["t_rel"] * 1e3, release_over_Tp=rl["t_rel"] / rl["T_p"], ring_over_pull=rl["R"], fd=b["fd"], fp=b["fp"])
        for k, b, rl in (("power", bb["power"], bb["rel"]), ("upconv", bb["upconv"], bb["rel_u"]))}) for n, bb in sp_best.items()}
    fig, ax = plt.subplots(1, 3, figsize=(15, 3.9))
    d = red[2]["design"]
    for (Dd, hd, gp), cc in zip(((4, 2, 2), (5, 2, 3), (6, 3, 4)), ("#1f77b4", "#2ca02c", "#d62728")):
        Fy, Fz = side_force(Dd * MM, hd * MM, d["D_p"], d["h_p"], gp * MM, s_grid)
        ax[0].plot(s_grid / MM, Fz * 1e3, color=cc, label=f"driver magnet {Dd}x{hd} mm, gap {gp} mm")
    ax[0].axhline(0, color="k", lw=0.5)
    ax[0].set_xlabel("piezo offset from driver magnet, s (mm)"); ax[0].set_ylabel("force on piezo along its motion (mN)")
    ax[0].set_title("Sweep-past force (finite-size magnets), 4 x 2 mm piezo magnet", fontsize=8); ax[0].legend(fontsize=7)
    k = 0
    for name, bb in sp_best.items():
        if bb is None:
            continue
        rl = bb["rel"]
        ax[1].plot(rl["t"] * 1e3, rl["xp"] / MM, color=(COL + ["#9467bd"])[k], lw=1,
                   label=f"{name}: ring/pull {rl['R']:.2f}, release {rl['t_rel'] / rl['T_p']:.2f} T_p")
        k += 1
    ax[1].set_xlabel("time (ms)"); ax[1].set_ylabel("piezo tip (mm)"); ax[1].legend(fontsize=6)
    ax[1].set_title("One pass of the driver magnet at its peak speed", fontsize=9)
    names = [n for n, bb in sp_best.items() if bb is not None]
    x = np.arange(len(names))
    coax = [drv[bb["i"]]["ref"]["Pp"] * 1e6 if bb["i"] < 3 else np.nan for bb in (sp_best[n] for n in names)]
    ax[2].bar(x - 0.2, coax, 0.4, color="#7f7f7f", label="coaxial redesign")
    ax[2].bar(x + 0.2, [sp_best[n]["power"]["P"] * 1e6 for n in names], 0.4, color="#d62728", label="sweep-past")
    ax[2].set_xticks(x, [n.replace(" + ", "\n+ ") for n in names], fontsize=7)
    ax[2].set_ylabel("average power (µW), 2 m/s² at f_d"); ax[2].legend(fontsize=7)
    ax[2].set_title("Same beams, two magnet layouts", fontsize=9)
    savefig(fig, "13_sweep_past.png")

    # ---------- 4. vehicle vibration ----------
    print("4. vehicle vibration ...", flush=True)
    veh, (tt, az, raw) = vehicle_runs(s1, red, th, sp_best, drv, rec_path)
    rows = []
    for seg, v in veh.items():
        for src in ("recorded", "synthetic noise"):
            for i in range(3):
                for name in ("Redesign (coaxial)", "Magnets removed", "Redesign + driver bimorph", "Sweep-past"):
                    k = (src, i, name)
                    if k not in v["res"]:
                        continue
                    r_ = v["res"][k]
                    stn = f"{drv[i]['sel']['strain_per_m'] * r_['xd'] * 1e6:.0f}" if name == "Redesign + driver bimorph" else "-"
                    rows.append([seg, src, LBL[i], name, f"{r_['P'] * 1e6:.2f}", f"{r_['Pd'] * 1e6:.2f}", stn, f"{r_['Vpk']:.2f}",
                                 "-" if not np.isfinite(r_["gmin"]) else f"{r_['gmin'] / MM:.1f}",
                                 "yes" if r_["contact"] else "no"])
    T["vehicle"] = S.md_table(["Road", "Input", "Config", "Design", "P total (uW)", "of which driver bimorph (uW)", "driver PZT peak strain (ue)",
                               "V peak piezo", "min gap (mm)", "magnet contact"], rows)
    summ["vehicle"] = {seg: dict(rms=v["rms"], rms_14_32=v["rms_band"], seg=v["seg"]) for seg, v in veh.items()}
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
    traw, zraw = raw
    ax[0].plot(tt, az, lw=0.3, color="#555")
    for seg, v in veh.items():
        ax[0].axvspan(*v["seg"], color="#d62728" if seg == "cobblestone" else "#1f77b4", alpha=0.15, label=seg)
    ax[0].set_xlabel("time (s)"); ax[0].set_ylabel("vertical accel, 3-45 Hz (m/s²)"); ax[0].legend(fontsize=8)
    ax[0].set_title("Car recording (phone accelerometer, CC BY 4.0)", fontsize=9)
    for seg, v in veh.items():
        ax[1].semilogy(v["f"], v["Pxx"], label=f"{seg} ({v['rms']:.2f} m/s² rms)")
    for i in range(3):
        p0 = S.system_params("redesign", i, s1, red)
        ax[1].axvline(p0["fd"], color="k", ls=":", lw=0.8)
        ax[1].axvline(p0["fp"], color=COL[i], ls="--", lw=0.8)
    top = max(v["Pxx"][(v["f"] > 4) & (v["f"] < 45)].max() for v in veh.values())
    ax[1].set_ylim(top * 1e-4, top * 3)
    ax[1].set_xlim(0, 50); ax[1].set_xlabel("frequency (Hz)"); ax[1].set_ylabel("PSD ((m/s²)²/Hz)")
    ax[1].set_title("Spectrum (dotted f_d ≈ 16 Hz, dashed f_p)", fontsize=9); ax[1].legend(fontsize=8)
    trc, tags = veh["cobblestone"]["res"]["trace"]
    j = tags.index((2, "Redesign (coaxial)")); j0 = tags.index((2, "Magnets removed"))
    m = (trc["t"] > 20) & (trc["t"] < 23)
    ax[2].plot(trc["t"][m], trc["V"][m, j], color="#d62728", lw=0.8, label="with magnets")
    ax[2].plot(trc["t"][m], trc["V"][m, j0], color="#555", lw=0.8, ls="--", label="magnets removed")
    ax[2].set_xlabel("time (s)"); ax[2].set_ylabel("piezo voltage (V)"); ax[2].legend(fontsize=8)
    ax[2].set_title("105 mm redesign on cobblestone (3 s window)", fontsize=9)
    savefig(fig, "14_vehicle.png")

    # ---------- 5. experiment ----------
    print("5. experiment predictions ...", flush=True)
    amps, freqs, ex = experiment(s1, red, th)
    rows = []
    for i in range(3):
        for a in amps:
            e = ex[(i, a)]
            rows.append([LBL[i], f"{a:.1f}", f"{e['f_lo']:.2f}", f"{e['f_hi']:.2f}", f"{e['f_lin_lo']:.2f}", f"{e['f_lin_hi']:.2f}",
                         f"{e['f_pz0']:.2f}", f"{e['Vpk_fd'] * 1e3:.0f}", f"{e['Vpk0_fd'] * 1e3:.0f}", f"{e['G_fd']:.2f}", f"{e['f_dip']:.1f} ({e['G_dip']:.2f}x)",
                         f"{e['G_law']:.2f}", f"{e['Vpk_max'] * 1e3:.0f}", f"{e['gmin'] / MM:.1f}"])
    T["experiment"] = S.md_table(["Config", "a (m/s²)", "lower mode, sim, driver peak (Hz)", "upper mode, sim, voltage peak (Hz)", "lower mode, theory (Hz)",
                                  "upper mode, theory (Hz)", "piezo peak, magnets removed (Hz)", "V peak at f_d (mV)",
                                  "V peak at f_d, magnets removed (mV)", "power gain at f_d (sim)", "largest loss from magnets: f (gain)", "power gain (law)",
                                  "largest V peak in sweep (mV)", "closest gap (mm)"], rows)
    summ["experiment"] = {f"{LBL[i]} {a}": {k: v for k, v in ex[(i, a)].items() if np.isscalar(v)} for (i, a) in ex}
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
    for i in range(3):
        for a, ls in zip(amps, ("-", "--", "-.", ":")):
            e = ex[(i, a)]
            ax[i].semilogy(freqs, e["P"] / a ** 2 * 1e6, color="#d62728", ls=ls, lw=1.1, label=f"{a} m/s², magnets")
            ax[i].semilogy(freqs, e["P0"] / a ** 2 * 1e6, color="#555", ls=ls, lw=0.9, label=f"{a} m/s², no magnets")
        e = ex[(i, amps[0])]
        for fm in (e["f_lin_lo"], e["f_lin_hi"]):
            ax[i].axvline(fm, color="k", lw=0.6, ls=":")
        ax[i].set_xlim(12, 30)
        ax[i].set_title(f"{LBL[i]} redesign: predicted sweep (dotted = theory modes)", fontsize=9)
        ax[i].set_xlabel("shaker frequency (Hz)"); ax[i].set_ylabel("power / a² (µW per (m/s²)²)")
    ax[0].legend(fontsize=6, ncol=2)
    savefig(fig, "15_experiment_prediction.png")

    with open(os.path.join(RESULTS, "next_tables.md"), "w") as fh:
        for k, v in T.items():
            fh.write(f"## {k}\n\n{v}\n\n")
    with open(os.path.join(RESULTS, "next_summary.json"), "w") as fh:
        json.dump(summ, fh, indent=1, default=lambda o: float(o) if np.isscalar(o) else str(o))
    for k, v in T.items():
        print(f"\n## {k}\n{v}")
    print(f"\ndone in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REC)
