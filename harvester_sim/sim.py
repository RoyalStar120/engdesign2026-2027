#!/usr/bin/env python3
"""
Magnetically plucked dual-cantilever piezoelectric energy harvester
-------------------------------------------------------------------
Re-analysis of the poster "Design and Optimization of a Magnetically Plucked
Piezoelectric Vibration Energy Harvester" (A. Yenamandra, HS-EGSD-0192).

  Step 1  Rebuild analytical chain (poster Tables 2-10), fix the Section 8
          snap-distance error and propagate it downstream.
  Step 2  Redesign search: margin >= MARGIN_MIN, 1.5x snap safety factor,
          natural frequencies inside the 18-30 Hz objective.
  Step 3  Time-domain simulation (base -> driver SDOF -> dipole force ->
          piezo SDOF -> piezo electrical coupling), sweeps, FFT.
  Step 4  Plots -> ./plots, tables/summary -> ./results

Run:   python sim.py            (about 1-3 min on a laptop)
All SI units internally; mm / mN only for printing.
"""
import json
import os
import time

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from scipy.signal import find_peaks

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# =============================================================================
# PARAMETERS  (edit here)
# =============================================================================
MM = 1e-3
# --- materials (poster "Properties of Materials") ---
E_PETG, RHO_PETG, T_PETG = 2.1e9, 1270.0, 1.0 * MM
E_PZT, T_PZT = 66e9, 0.2 * MM
E_CU, RHO_CU, T_CU = 117e9, 8960.0, 0.1 * MM
WIDTH = 10 * MM                         # cantilever width
L_PIEZO = np.array([85.0, 95.0, 105.0]) * MM
DRIVER_OFFSET = 10 * MM                 # driver length = piezo length - offset

# --- poster section flexural rigidities (Table 5), used to reproduce k_piezo ---
EI_POSTER = {"A": 1.750e-3, "B": 7.232e-3, "C": 1.461e-2, "D": 1.750e-3}
# Piezo segment lengths (illegible on poster). A = clamp end, D = tip end.
# Chosen by least-squares fit to Table 6 (see fit_segments()); D absorbs the
# remaining length so one layout serves all three cantilevers.
SEG_LA, SEG_LB, SEG_LC = 0.0 * MM, 11.6 * MM, 45.4 * MM

# --- magnets (N52 cylinder, poster) ---
MU0 = 4e-7 * np.pi
BR = 1.48
MAG_D, MAG_H = 5 * MM, 2 * MM
RHO_MAG = 7500.0                        # NdFeB density (reproduces driver m_eff)

# --- lumped-model coefficients ---
MEFF_COEF = 0.2357                      # m_eff = 0.2357*mu*L + m_tip (poster)
MBASE_COEF = 0.375                      # base-excitation participating mass
                                        # = int(mu*phi) for static tip shape

# --- design rules ---
SAFETY = 1.5                            # d_safe = SAFETY * d_snap
DELTA_REQ = 0.5 * MM                    # poster: 0.5 mm tip deflection ~ 50 V
MARGIN_MIN = 1.5                        # required F_avail / F_req (redesign)
SWING_MIN = 1.2                         # required per-cycle force swing
                                        # [F(d_safe) - F(d_safe + 2 X_rel)] / F_req
                                        # at driver resonance, A_BASE (added after
                                        # the sim showed static preload != pluck)
FD_BAND = (16.0, 30.0)                  # driver natural frequency window [Hz]
FP_BAND = (18.0, 30.0)                  # piezo natural frequency window [Hz]

# --- dynamics ---
ZETA_D, ZETA_P = 0.015, 0.015
A_BASE = 2.0                            # base acceleration amplitude [m/s^2] (~0.2 g)
T_SIM, T_RAMP, T_STEADY = 3.0, 0.3, 1.0 # sim length, input ramp, steady window start
K_CONTACT, C_CONTACT = 2e6, 5.0         # magnet face contact penalty
SWEEP_F = np.arange(5.0, 40.01, 0.5)    # Hz
DT_RK4 = 1e-5                           # fixed step for the vectorised sweeps
FS_OUT = 20000.0                        # output sample rate of main runs

# --- electrical (bimorph 40 x 5 x 0.5 mm, two 0.2 mm PZT-5A layers in series) ---
EPS0 = 8.854e-12
EPS33T_REL = 1700.0
K31 = 0.34                              # PZT-5A material coupling
BIMORPH_L, BIMORPH_W = 40 * MM, 5 * MM
CP = 0.5 * EPS33T_REL * EPS0 * BIMORPH_L * BIMORPH_W / T_PZT   # series layers
R_LOAD = 1e6
V_CAL, X_CAL = 50.0, 0.5 * MM           # poster claim used to calibrate theta

HERE = os.path.dirname(os.path.abspath(__file__))
PLOTS = os.path.join(HERE, "plots")
RESULTS = os.path.join(HERE, "results")

# =============================================================================
# POSTER VALUES (Tables 2-10) for comparison
# =============================================================================
POSTER = {
    "bt": {"PETG": 10.0, "PZT": 314.3, "Cu": 557.1},                  # mm
    "ybar": {"A/D": 0.500, "B": 0.966, "C": 1.023},                    # mm
    "I": {"A/D": 0.833, "B": 3.444, "C": 6.959},                       # mm^4
    "EI": {"A/D": 1.750e-3, "B": 7.232e-3, "C": 1.461e-2},
    "k_p": [43.9, 28.4, 18.9], "k_d": [12.4, 8.55, 6.12],
    "meff_p": [0.001215, 0.001337, 0.001460],
    "meff_d": [0.000520, 0.000549, 0.000579],
    "f_p": [30.2, 23.2, 18.1], "f_d": [24.6, 19.9, 16.4],
    "m_dip": 0.04625, "C": 1.284e-9,
    "dsnap_p": [4.13, 4.67, 5.22], "dsnap_d": [5.54, 6.14, 6.84],
    "dsafe": [8.3, 9.2, 10.3],
    "Freq": [22.0, 14.2, 9.5], "Favail": [269.0, 179.0, 114.0],
    "margin": [12.0, 13.0, 12.0],
}
LBL = ["85 mm", "95 mm", "105 mm"]


# =============================================================================
# helpers
# =============================================================================
def pct(new, old):
    return 100.0 * (new - old) / old


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def g(x, n=3):
    return f"{x:.{n}g}"


def section_props(layers):
    """layers: bottom->top list of (E, t, w). Transformed-section to PETG.
    Returns (ybar, I_transformed, EI)."""
    y, A, yc, I0 = 0.0, [], [], []
    for E, t, w in layers:
        bt = w * E / E_PETG
        A.append(bt * t); yc.append(y + t / 2); I0.append(bt * t ** 3 / 12); y += t
    A, yc = np.array(A), np.array(yc)
    yb = (A * yc).sum() / A.sum()
    I = sum(I0) + (A * (yc - yb) ** 2).sum()
    return yb, I, E_PETG * I


def k_series(Lt, EI=EI_POSTER, LA=SEG_LA, LB=SEG_LB, LC=SEG_LC, shares=False):
    """Tip stiffness of a stepped cantilever under tip load (poster Sec. 5):
    delta/P = sum (s_out^3 - s_in^3)/(3 EI), s measured from the tip."""
    LD = Lt - LA - LB - LC
    LCD, LBCD = LC + LD, LB + LC + LD
    terms = np.array([(Lt ** 3 - LBCD ** 3) / EI["A"], (LBCD ** 3 - LCD ** 3) / EI["B"],
                      (LCD ** 3 - LD ** 3) / EI["C"], LD ** 3 / EI["D"]]) / 3
    k = 1.0 / terms.sum()
    return (k, terms / terms.sum()) if shares else k


def k_driver(L, t=T_PETG, b=WIDTH):
    return 3 * E_PETG * (b * t ** 3 / 12) / L ** 3


def magnet_mass(D, h):
    return RHO_MAG * np.pi * (D / 2) ** 2 * h


def dipole(D, h, Br=BR):
    return Br * np.pi * (D / 2) ** 2 * h / MU0


def force_const(m1, m2):
    """F(d) = C/d^4, coaxial point dipoles."""
    return 3 * MU0 * m1 * m2 / (2 * np.pi)


def d_snap(k, C):
    """|dF/dd| = 4C/d^5 = k  ->  d = (4C/k)^(1/5)."""
    return (4 * C / k) ** 0.2


def fn(k, m):
    return np.sqrt(k / m) / (2 * np.pi)


# =============================================================================
# STEP 1 — analytical chain
# =============================================================================
def fit_segments():
    Ls, kt = L_PIEZO, np.array(POSTER["k_p"])

    def res(p):
        return [k_series(L, LA=0.0, LB=p[0], LC=p[1]) / k - 1 for L, k in zip(Ls, kt)]
    s = least_squares(res, [0.02, 0.04], bounds=([0, 0], [0.08, 0.08]))
    return s.x


def step1():
    out, T = {}, {}
    # ---- Table 2: transformed widths
    n = {"PETG": 1.0, "PZT": E_PZT / E_PETG, "Cu": E_CU / E_PETG}
    T["t2"] = md_table(["Layer", "E (GPa)", "n", "b_tr (mm) recomputed", "poster", "% diff"],
                       [[k, {"PETG": 2.1, "PZT": 66, "Cu": 117}[k], f"{n[k]:.2f}",
                         f"{WIDTH * n[k] / MM:.1f}", POSTER["bt"][k],
                         f"{pct(WIDTH * n[k] / MM, POSTER['bt'][k]):+.2f}"] for k in n])

    # ---- Tables 3/4/5: section properties
    P, Z, C = (E_PETG, T_PETG, WIDTH), (E_PZT, T_PZT, WIDTH), (E_CU, T_CU, WIDTH)
    Zn, Cn = (E_PZT, T_PZT, BIMORPH_W), (E_CU, T_CU, BIMORPH_W)
    cand = {
        "A/D: PETG": [P],
        "B: PETG + Cu (inferred, exact match)": [P, C],
        "C cand. 1: PETG + PZT + Cu": [P, Z, C],
        "C cand. 2: PETG + PZT + PZT": [P, Z, Z],
        "C cand. 3: symmetric PZT/PETG/PZT": [Z, P, Z],
        "C physical: PETG + 5 mm-wide PZT/Cu/PZT bimorph": [P, Zn, Cn, Zn],
    }
    rows, sec = [], {}
    for name, lay in cand.items():
        yb, I, EI = section_props(lay)
        sec[name] = (yb, I, EI)
        key = "A/D" if name.startswith("A/D") else ("B" if name.startswith("B") else "C")
        rows.append([name, f"{yb / MM:.3f}", POSTER["ybar"][key], f"{I / MM ** 4:.3f}",
                     POSTER["I"][key], f"{EI:.3e}", f"{POSTER['EI'][key]:.3e}",
                     f"{pct(EI, POSTER['EI'][key]):+.1f}"])
    T["t345"] = md_table(["Section / stack", "ybar (mm)", "poster ybar", "I (mm^4)",
                          "poster I", "EI (N m^2)", "poster EI", "EI % diff"], rows)
    # poster internal consistency: EI = E_PETG * I ?
    cons = [[k, f"{POSTER['I'][k]:.3f}", f"{E_PETG * POSTER['I'][k] * MM ** 4:.3e}",
             f"{POSTER['EI'][k]:.3e}",
             f"{POSTER['EI'][k] / POSTER['EI']['A/D']:.2f}"] for k in ("A/D", "B", "C")]
    T["t5cons"] = md_table(["Section", "poster I (mm^4)", "E_PETG*I", "poster EI",
                            "EI / EI_PETG"], cons)
    out["sections"] = {k: [v[0] / MM, v[1] / MM ** 4, v[2]] for k, v in sec.items()}

    # ---- segment fit + Table 6/7
    lb, lc = fit_segments()
    out["seg_fit_raw_mm"] = [0.0, lb / MM, lc / MM]
    kp = np.array([k_series(L) for L in L_PIEZO])
    Ld = L_PIEZO - DRIVER_OFFSET
    kd = k_driver(Ld)
    T["t67"] = md_table(
        ["Length", "k_piezo (N/m)", "poster", "% diff", "L_D tip (mm)",
         "Driver L (mm)", "k_driver (N/m)", "poster", "% diff"],
        [[LBL[i], f"{kp[i]:.2f}", POSTER["k_p"][i], f"{pct(kp[i], POSTER['k_p'][i]):+.2f}",
          f"{(L_PIEZO[i] - SEG_LA - SEG_LB - SEG_LC) / MM:.1f}", f"{Ld[i] / MM:.0f}",
          f"{kd[i]:.2f}", POSTER["k_d"][i], f"{pct(kd[i], POSTER['k_d'][i]):+.2f}"]
         for i in range(3)])
    # energy shares (used for coupling estimate)
    shares = np.array([k_series(L, shares=True)[1] for L in L_PIEZO])

    # ---- Table 8: masses / frequencies
    mmag = magnet_mass(MAG_D, MAG_H)
    mu_d = RHO_PETG * WIDTH * T_PETG
    meff_d = MEFF_COEF * mu_d * Ld + mmag
    # piezo: back-fit mu_p and m_tip from the poster's own m_eff column
    A = np.vstack([MEFF_COEF * L_PIEZO, np.ones(3)]).T
    (mu_p, mtip_fit), *_ = np.linalg.lstsq(A, np.array(POSTER["meff_p"]), rcond=None)
    rho_pzt_impl = (mu_p / WIDTH - RHO_PETG * T_PETG - RHO_CU * T_CU) / (2 * T_PZT)
    meff_p_rep = MEFF_COEF * mu_p * L_PIEZO + mtip_fit
    meff_p_phys = MEFF_COEF * mu_p * L_PIEZO + mmag
    fp_rep, fp_phys, fd = fn(kp, meff_p_rep), fn(kp, meff_p_phys), fn(kd, meff_d)
    rows = []
    for i in range(3):
        rows.append([f"Piezo {LBL[i]}", f"{kp[i]:.1f}", f"{meff_p_rep[i]:.6f}",
                     POSTER["meff_p"][i], f"{fp_rep[i]:.1f}", POSTER["f_p"][i],
                     f"{pct(fp_rep[i], POSTER['f_p'][i]):+.1f}",
                     f"{fp_phys[i]:.1f}"])
    for i in range(3):
        rows.append([f"Driver {Ld[i] / MM:.0f} mm", f"{kd[i]:.2f}", f"{meff_d[i]:.6f}",
                     POSTER["meff_d"][i], f"{fd[i]:.1f}", POSTER["f_d"][i],
                     f"{pct(fd[i], POSTER['f_d'][i]):+.1f}", f"{fd[i]:.1f}"])
    T["t8"] = md_table(["Cantilever", "k (N/m)", "m_eff (kg)", "poster m_eff",
                        "f_n (Hz)", "poster f_n", "% diff",
                        "f_n w/ real magnet mass (Hz)"], rows)
    out.update(mu_p=mu_p, mtip_fit=mtip_fit, rho_pzt_impl=rho_pzt_impl, mmag=mmag,
               kp=kp, kd=kd, Ld=Ld, meff_d=meff_d, meff_p_phys=meff_p_phys,
               fp_rep=fp_rep, fp_phys=fp_phys, fd=fd, shares=shares)

    # ---- Section 7 magnet
    mdip = dipole(MAG_D, MAG_H)
    Cf = force_const(mdip, mdip)
    out.update(mdip=mdip, C=Cf)
    T["t7"] = md_table(["Quantity", "recomputed", "poster", "% diff"],
                       [["m (A m^2)", f"{mdip:.5f}", POSTER["m_dip"], f"{pct(mdip, POSTER['m_dip']):+.2f}"],
                        ["C in F=C/d^4 (N m^4)", f"{Cf:.4e}", f"{POSTER['C']:.3e}", f"{pct(Cf, POSTER['C']):+.2f}"],
                        ["magnet mass (g)", f"{mmag * 1e3:.3f}", "-", "-"]])

    # ---- Sections 8-10 corrected
    dsp, dsd = d_snap(kp, Cf), d_snap(kd, Cf)
    ks = kp * kd / (kp + kd)
    dss = d_snap(ks, Cf)
    dsafe = SAFETY * dsd
    Fav = Cf / dsafe ** 4
    Freq = kp * DELTA_REQ
    margin = Fav / Freq
    # strict two-body (series stiffness) version
    dsafe_s = SAFETY * dss
    margin_s = Cf / dsafe_s ** 4 / Freq
    out.update(dsnap_p=dsp, dsnap_d=dsd, dsnap_series=dss, dsafe=dsafe, Favail=Fav,
               Freq=Freq, margin=margin, dsafe_series=dsafe_s, margin_series=margin_s)

    T["t9"] = md_table(
        ["Config", "d_snap piezo (mm)", "d_snap driver (mm)", "d_safe = 1.5 d_snap,drv (mm)",
         "d_snap two-body k_series (mm)", "d_safe two-body (mm)"],
        [[LBL[i], f"{dsp[i] / MM:.2f}", f"{dsd[i] / MM:.2f} <- governs",
          f"{dsafe[i] / MM:.1f}", f"{dss[i] / MM:.2f}", f"{dsafe_s[i] / MM:.1f}"]
         for i in range(3)])
    T["t10"] = md_table(
        ["Config", "F_req (mN)", "F_avail (mN)", "Margin", "Margin (two-body)",
         "static pluck defl. F_avail/k_p (mm)"],
        [[LBL[i], f"{Freq[i] * 1e3:.1f}", f"{Fav[i] * 1e3:.2f}", f"{margin[i]:.2f}x",
          f"{margin_s[i]:.2f}x", f"{Fav[i] / kp[i] / MM:.3f}"] for i in range(3)])

    # ---- before/after
    vpm = V_CAL / X_CAL  # poster calibration, V per m
    ba = []
    for i in range(3):
        q = [
            ("d_snap piezo (mm)", POSTER["dsnap_p"][i], dsp[i] / MM),
            ("d_snap driver (mm)", POSTER["dsnap_d"][i], dsd[i] / MM),
            ("d_safe (mm)", POSTER["dsafe"][i], dsafe[i] / MM),
            ("F_req (mN)", POSTER["Freq"][i], Freq[i] * 1e3),
            ("F_avail (mN)", POSTER["Favail"][i], Fav[i] * 1e3),
            ("Margin (x)", POSTER["margin"][i], margin[i]),
            ("Static pluck deflection (mm)", POSTER["Favail"][i] / 1e3 / POSTER["k_p"][i] / MM,
             Fav[i] / kp[i] / MM),
            ("Implied V at 100 V/mm (V)", POSTER["Favail"][i] / 1e3 / POSTER["k_p"][i] * vpm,
             Fav[i] / kp[i] * vpm),
        ]
        for name, old, new in q:
            ba.append([LBL[i], name, f"{old:.3g}", f"{new:.3g}", f"{pct(new, old):+.0f}%"])
    T["ba"] = md_table(["Config", "Quantity", "Poster", "Corrected", "% change"], ba)
    return out, T


# =============================================================================
# STEP 2 — redesign search
# =============================================================================
DESIGN_VARS = ["L_d", "t_d", "b_d", "D_d", "h_d", "m_add", "D_p", "h_p"]
BASE = dict(L_d=None, t_d=T_PETG, b_d=WIDTH, D_d=MAG_D, h_d=MAG_H, m_add=0.0,
            D_p=MAG_D, h_p=MAG_H)


def evaluate(L_p, kp, mu_p, L_d, t_d, b_d, D_d, h_d, m_add, D_p, h_p):
    """Vectorised design metrics. Piezo beam (bimorph + PETG layup) unchanged."""
    kd = k_driver(L_d, t_d, b_d)
    mmd, mmp = magnet_mass(D_d, h_d) + m_add, magnet_mass(D_p, h_p)
    md = MEFF_COEF * RHO_PETG * b_d * t_d * L_d + mmd
    mp = MEFF_COEF * mu_p * L_p + mmp
    C = force_const(dipole(D_d, h_d), dipole(D_p, h_p))
    ks = kd * kp / (kd + kp)
    dsafe = SAFETY * d_snap(ks, C)
    Fav = C / dsafe ** 4
    Freq = kp * DELTA_REQ
    fd_, fp_ = fn(kd, md), fn(kp, mp)
    Xrel = rel_amp(kd, md, MBASE_COEF * RHO_PETG * b_d * t_d * L_d + mmd,
                   kp, mp, MBASE_COEF * mu_p * L_p + mmp, fd_)
    swing = (Fav - C / (dsafe + 2 * Xrel) ** 4) / Freq
    return dict(kd=kd, md=md, mp=mp, C=C, ks=ks, fd=fd_, fp=fp_,
                dsafe=dsafe, Fav=Fav, Freq=Freq, margin=Fav / Freq, Xrel=Xrel, swing=swing,
                margin_poster_rule=C / (SAFETY * d_snap(np.minimum(kd, kp), C)) ** 4 / Freq)


def rel_amp(kd, md, mbd, kp, mp, mbp, f_exc):
    """Linear steady-state |x_d - x_p| under base accel A_BASE at f_exc (no magnets)."""
    w, wd, wp = 2 * np.pi * f_exc, np.sqrt(kd / md), np.sqrt(kp / mp)
    Xd = -(mbd / md) * A_BASE / (wd ** 2 - w ** 2 + 2j * ZETA_D * wd * w)
    Xp = -(mbp / mp) * A_BASE / (wp ** 2 - w ** 2 + 2j * ZETA_P * wp * w)
    return np.abs(Xd - Xp)


def step2(s1):
    grids = dict(
        L_d=np.arange(30, 121, 1.0) * MM,
        t_d=np.array([1.0, 1.5, 2.0, 2.5, 3.0]) * MM,
        b_d=np.array([10.0, 15.0, 20.0]) * MM,
        D_d=np.array([5.0, 6.0, 8.0, 10.0, 12.7]) * MM,
        h_d=np.array([2.0, 3.0, 4.0, 5.0, 6.0, 8.0]) * MM,
        m_add=np.array([0.0, 1.0, 2.0, 3.0]) * 1e-3,
        D_p=np.array([3.0, 4.0, 5.0, 6.0]) * MM,
        h_p=np.array([1.0, 1.5, 2.0, 3.0]) * MM,
    )
    mesh = np.meshgrid(*[grids[v] for v in DESIGN_VARS], indexing="ij")
    flat = {v: m.ravel() for v, m in zip(DESIGN_VARS, mesh)}
    chosen = []
    for i, Lp in enumerate(L_PIEZO):
        base = dict(BASE, L_d=Lp - DRIVER_OFFSET)
        r = evaluate(Lp, s1["kp"][i], s1["mu_p"], **flat)
        ok = ((r["margin"] >= MARGIN_MIN) & (r["swing"] >= SWING_MIN)
              & (r["fd"] >= FD_BAND[0]) & (r["fd"] <= FD_BAND[1])
              & (r["fp"] >= FP_BAND[0]) & (r["fp"] <= FP_BAND[1])
              # point-dipole validity: closest approach >= 2x largest magnet dimension
              & (r["dsafe"] >= 2 * np.maximum.reduce([flat["D_d"], flat["h_d"], flat["D_p"]])))
        # prefer up-conversion (f_p > f_d) when achievable
        ok_up = ok & (r["fp"] >= 1.1 * r["fd"])
        use = ok_up if ok_up.any() else ok
        cost = sum(np.abs(np.log(flat[v] / base[v])) for v in DESIGN_VARS if v != "m_add")
        cost = cost + flat["m_add"] / 1e-3 * 0.5        # 0.5 cost per gram of dead mass
        cost = np.where(use, cost - 0.01 * r["margin"], np.inf)
        j = int(np.argmin(cost))
        if not np.isfinite(cost[j]):
            chosen.append(None)
            continue
        des = {v: float(flat[v][j]) for v in DESIGN_VARS}
        met = {k: float(np.broadcast_to(v, cost.shape)[j]) for k, v in r.items()}
        chosen.append(dict(design=des, metrics=met, n_feasible=int(ok.sum()),
                           upconv=bool(ok_up.any())))
    return chosen, grids


# =============================================================================
# STEP 3 — dynamics
# =============================================================================
def system_params(kind, i, s1, red):
    """Return lumped parameters for one design/length.
    kind: 'asdrawn'  poster magnets & lengths, closest approach = poster d_safe
          'corrected' poster magnets & lengths, closest approach = corrected d_safe
          'redesign'  Step-2 design"""
    Lp, kp, mu_p = L_PIEZO[i], s1["kp"][i], s1["mu_p"]
    if kind in ("redesign", "nomag"):     # nomag = redesign geometry with magnets removed
        d = red[i]["design"]
    else:
        d = dict(BASE, L_d=Lp - DRIVER_OFFSET)
    kd = k_driver(d["L_d"], d["t_d"], d["b_d"])
    mud = RHO_PETG * d["b_d"] * d["t_d"]
    mmd, mmp = magnet_mass(d["D_d"], d["h_d"]) + d["m_add"], magnet_mass(d["D_p"], d["h_p"])
    md = MEFF_COEF * mud * d["L_d"] + mmd
    mp = MEFF_COEF * mu_p * Lp + mmp
    C = force_const(dipole(d["D_d"], d["h_d"]), dipole(d["D_p"], d["h_p"]))
    ks = kd * kp / (kd + kp)
    if kind == "asdrawn":
        dmin = POSTER["dsafe"][i] * MM
    elif kind == "corrected":
        dmin = s1["dsafe"][i]
    else:
        dmin = red[i]["metrics"]["dsafe"]
    p = dict(kd=kd, md=md, mbd=MBASE_COEF * mud * d["L_d"] + mmd, cd=2 * ZETA_D * np.sqrt(kd * md),
             kp=kp, mp=mp, mbp=MBASE_COEF * mu_p * Lp + mmp, cp=2 * ZETA_P * np.sqrt(kp * mp),
             C=C, dc=0.5 * (d["h_d"] + d["h_p"]), fd=fn(kd, md), fp=fn(kp, mp),
             Freq=kp * DELTA_REQ, dsnap=d_snap(ks, C), dmin=dmin, Cp=CP, R=R_LOAD)
    # rest gap: closest approach at design excitation (driver resonance) = dmin
    p["Xrel"] = float(rel_amp(kd, md, p["mbd"], kp, mp, p["mbp"], p["fd"]))
    p["g0"] = dmin + p["Xrel"]
    if kind == "nomag":
        p["C"] = 0.0
    p["th_poster"] = CP * V_CAL / X_CAL
    return p


def coupling_estimates(s1):
    """theta from (a) poster calibration, (b) physical bound k31^2 * energy share."""
    # PZT share of bending stiffness in the stiffened section, using the real
    # hardware: 5 mm-wide PZT/Cu/PZT bimorph bonded on the 10 mm PETG strip.
    lay = [(E_PETG, T_PETG, WIDTH), (E_PZT, T_PZT, BIMORPH_W), (E_CU, T_CU, BIMORPH_W),
           (E_PZT, T_PZT, BIMORPH_W)]
    yb, I, _ = section_props(lay)
    bt = BIMORPH_W * E_PZT / E_PETG
    Ipzt = 0.0
    for yc in (T_PETG + T_PZT / 2, T_PETG + T_PZT + T_CU + T_PZT / 2):
        Ipzt += bt * T_PZT ** 3 / 12 + bt * T_PZT * (yc - yb) ** 2
    frac_pzt = Ipzt / I
    kap2 = K31 ** 2 * s1["shares"][:, 2] * frac_pzt      # section C carries the PZT
    th_phys = np.sqrt(kap2 * s1["kp"] * CP)
    th_post = CP * V_CAL / X_CAL
    return dict(frac_pzt=frac_pzt, kappa2_phys=kap2, th_phys=th_phys, th_poster=th_post,
                kappa2_poster=th_post ** 2 / (s1["kp"] * CP),
                vpm_phys=th_phys / CP, vpm_poster=th_post / CP,
                U_mech=0.5 * s1["kp"] * X_CAL ** 2, U_elec=0.5 * CP * V_CAL ** 2)


def rhs_factory(p, th, f_exc):
    def rhs(t, y):
        xd, vd, xp, vp, V = y
        ab = A_BASE * min(t / T_RAMP, 1.0) * np.sin(2 * np.pi * f_exc * t)
        d = p["g0"] + xp - xd
        Fm = p["C"] / max(d, p["dc"]) ** 4
        pen = p["dc"] - d
        Fc = max(K_CONTACT * pen - C_CONTACT * (vp - vd), 0.0) if pen > 0 else 0.0
        Fn = Fm - Fc
        ad = (-p["cd"] * vd - p["kd"] * xd - p["mbd"] * ab + Fn) / p["md"]
        ap = (-p["cp"] * vp - p["kp"] * xp - th * V - p["mbp"] * ab - Fn) / p["mp"]
        dV = (th * vp - V / p["R"]) / p["Cp"]
        return [vd, ad, vp, ap, dV]
    return rhs


def run_case(p, th, f_exc):
    t_eval = np.arange(0, T_SIM, 1 / FS_OUT)
    sol = solve_ivp(rhs_factory(p, th, f_exc), (0, T_SIM), np.zeros(5), method="LSODA",
                    t_eval=t_eval, rtol=1e-7, atol=[1e-10, 1e-8, 1e-10, 1e-8, 1e-5],
                    max_step=2e-4)
    xd, vd, xp, vp, V = sol.y
    t = sol.t
    d = p["g0"] + xp - xd
    return analyse(t, xd, xp, V, d, p, f_exc)


def analyse(t, xd, xp, V, d, p, f_exc):
    ss = t >= T_STEADY
    F = p["C"] / np.maximum(d, p["dc"]) ** 4
    # a pluck = per-cycle force SWING (closest-approach force minus force at the
    # preceding farthest point) >= F_req.  Static preload is not a pluck.
    dss, Fss = d[ss], F[ss]
    mins, _ = find_peaks(-dss)
    maxs, _ = find_peaks(dss)
    sw = np.array([Fss[m] - Fss[maxs[maxs < m][-1]] for m in mins if (maxs < m).any()])
    if sw.size == 0:
        sw = np.zeros(1)
    plucks = int((sw >= p["Freq"]).sum())
    weak = int((sw >= 0.1 * p["Freq"]).sum())
    contact = d <= p["dc"] * 1.02
    last = t >= T_SIM - 0.25 * (T_SIM - T_STEADY)
    stuck = bool(contact[last].mean() > 0.5)
    # FFT
    Vs = V[ss] - V[ss].mean()
    nfft = 8 * len(Vs)
    spec = np.abs(np.fft.rfft(Vs * np.hanning(len(Vs)), nfft)) * 2 / (0.5 * len(Vs))
    fr = np.fft.rfftfreq(nfft, t[1] - t[0])

    def band(f0, bw=1.5):
        m = (fr > f0 - bw) & (fr < f0 + bw)
        return float(spec[m].max()) if m.any() else 0.0
    return dict(t=t, xd=xd, xp=xp, V=V, d=d, fr=fr, spec=spec,
                swing=float(np.median(sw) / p["Freq"]), plucks=plucks, plucks_per_s=plucks / (T_SIM - T_STEADY), weak=weak,
                min_gap=float(d.min()), contact=bool(contact.any()), stuck=stuck,
                first_contact=float(t[contact][0]) if contact.any() else None,
                peak_xp=float(np.abs(xp[ss]).max()), peak_xd=float(np.abs(xd[ss]).max()),
                Vpk=float(np.abs(V[ss]).max()), Vrms=float(np.sqrt(np.mean(V[ss] ** 2))),
                P_avg=float(np.mean(V[ss] ** 2) / p["R"]),
                A_fexc=band(f_exc), A_fp=band(p["fp"]) if abs(p["fp"] - f_exc) > 2 else float("nan"))


def sweep_rk4(plist, thlist, flist):
    """Vectorised fixed-step RK4 over many (system, frequency) pairs."""
    N = len(plist)
    P = {k: np.array([pp[k] for pp in plist]) for k in
         ("kd", "md", "mbd", "cd", "kp", "mp", "mbp", "cp", "C", "dc", "g0", "Cp", "R", "Freq")}
    th = np.array(thlist); fe = np.array(flist)
    Y = np.zeros((5, N))

    def f(t, Y):
        xd, vd, xp, vp, V = Y
        ab = A_BASE * min(t / T_RAMP, 1.0) * np.sin(2 * np.pi * fe * t)
        d = P["g0"] + xp - xd
        Fm = P["C"] / np.maximum(d, P["dc"]) ** 4
        pen = P["dc"] - d
        Fc = np.where(pen > 0, np.maximum(K_CONTACT * pen - C_CONTACT * (vp - vd), 0.0), 0.0)
        Fn = Fm - Fc
        return np.array([vd, (-P["cd"] * vd - P["kd"] * xd - P["mbd"] * ab + Fn) / P["md"],
                         vp, (-P["cp"] * vp - P["kp"] * xp - th * V - P["mbp"] * ab - Fn) / P["mp"],
                         (th * vp - V / P["R"]) / P["Cp"]])
    nst = int(round(T_SIM / DT_RK4)); h = DT_RK4
    Vpk = np.zeros(N); V2 = np.zeros(N); xpk = np.zeros(N); dmin = np.full(N, np.inf)
    cnt = 0; contact = np.zeros(N, bool); plucks = np.zeros(N)
    Flastmax = np.full(N, np.inf)
    dprev2 = dprev = None
    for n in range(nst):
        t = n * h
        k1 = f(t, Y); k2 = f(t + h / 2, Y + h / 2 * k1)
        k3 = f(t + h / 2, Y + h / 2 * k2); k4 = f(t + h, Y + h * k3)
        Y = Y + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        d = P["g0"] + Y[2] - Y[0]
        dmin = np.minimum(dmin, d)
        contact |= d <= P["dc"] * 1.02
        if t >= T_STEADY:
            Vpk = np.maximum(Vpk, np.abs(Y[4])); V2 += Y[4] ** 2; cnt += 1
            xpk = np.maximum(xpk, np.abs(Y[2]))
            if dprev2 is not None:
                Fprev = P["C"] / np.maximum(dprev, P["dc"]) ** 4
                lmax = (dprev > dprev2) & (dprev >= d)
                Flastmax = np.where(lmax, Fprev, Flastmax)
                lmin = (dprev < dprev2) & (dprev <= d)
                plucks += lmin & (Fprev - Flastmax >= P["Freq"])
        dprev2, dprev = dprev, d
    return dict(Vpk=Vpk, Vrms=np.sqrt(V2 / cnt), xpk=xpk, dmin=dmin, contact=contact,
                plucks_per_s=plucks / (T_SIM - T_STEADY))


def qs_position(p, xd):
    """Quasi-static piezo tip position (<= 0, pulled toward the driver) with the
    driver held at xd. NaN if no stable equilibrium exists (snap-in)."""
    from scipy.optimize import brentq
    D = p["g0"] - xd
    us = D - (4 * p["C"] / p["kp"]) ** 0.2          # deflection at the stability limit
    f = lambda u: p["kp"] * u - p["C"] / (D - u) ** 4
    if us <= 0 or f(us) < 0:
        return np.nan
    return -brentq(f, 0.0, us)


def pluck_release(p, th, tau, t_after=0.4):
    """Single pluck: piezo starts in static equilibrium, pulled toward the driver
    at closest approach (x_d = +X_rel). The driver then retreats to -X_rel along a
    half-cosine lasting tau and stays there. No base excitation. Returns the time
    history and ring ratio R = (free-vibration amplitude after release) / (pull)."""
    X = p["Xrel"]

    def xd(t):
        return X * np.cos(np.pi * min(t, tau) / tau)

    def rhs(t, y):
        xp, vp, V = y
        F = p["C"] / max(p["g0"] + xp - xd(t), p["dc"]) ** 4
        return [vp, (-p["cp"] * vp - p["kp"] * xp - th * V - F) / p["mp"],
                (th * vp - V / p["R"]) / p["Cp"]]
    x0, x_end = qs_position(p, X), qs_position(p, -X)
    T = tau + t_after
    t = np.linspace(0, T, 8000)
    sol = solve_ivp(rhs, (0, T), [x0, 0.0, 0.0], method="LSODA", t_eval=t,
                    max_step=2e-4, rtol=1e-8, atol=1e-11)
    after = sol.t > tau
    pull = abs(x0 - x_end)
    ring = float(np.max(np.abs(sol.y[0][after] - x_end)))
    return dict(t=sol.t, xd=np.array([xd(tt) for tt in sol.t]), xp=sol.y[0], V=sol.y[2],
                x_end=x_end, pull=pull, ring=ring, R=ring / pull,
                Vpk_after=float(np.abs(sol.y[2][after]).max()), tau=tau)


# =============================================================================
# PLOTS
# =============================================================================
COL = ["#1f77b4", "#d62728", "#2ca02c"]


def plot_force_gap(s1):
    d = np.linspace(2, 40, 600) * MM
    C = s1["C"]
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    ax[0].loglog(d / MM, C / d ** 4 * 1e3, "k", lw=2, label="F(d) = C/d$^4$")
    for i in range(3):
        ax[0].axhline(s1["Freq"][i] * 1e3, color=COL[i], ls=":", lw=1)
        ax[0].plot(s1["dsafe"][i] / MM, s1["Favail"][i] * 1e3, "o", color=COL[i],
                   label=f"{LBL[i]}: corrected d_safe, F_avail={s1['Favail'][i] * 1e3:.1f} mN (F_req dotted)")
        ax[0].plot(POSTER["dsafe"][i], POSTER["Favail"][i], "x", color=COL[i], ms=10, mew=2)
    ax[0].plot([], [], "kx", label="poster d_safe / F_avail (wrong)")
    ax[0].set(xlabel="center-to-center gap d (mm)", ylabel="attractive force (mN)",
              title="Magnet force vs gap")
    ax[0].legend(fontsize=7.5); ax[0].grid(which="both", alpha=.3)
    ax[1].loglog(d / MM, 4 * C / d ** 5, "k", lw=2, label="|dF/dd| = 4C/d$^5$")
    for i in range(3):
        ax[1].axhline(s1["kd"][i], color=COL[i], ls="--", lw=1)
        ax[1].axhline(s1["kp"][i], color=COL[i], ls="-.", lw=.8)
        ax[1].plot(s1["dsnap_d"][i] / MM, s1["kd"][i], "o", color=COL[i], ms=8,
                   label=f"{LBL[i]} driver k={s1['kd'][i]:.1f}: snap {s1['dsnap_d'][i] / MM:.1f} mm (poster {POSTER['dsnap_d'][i]})")
        ax[1].plot(s1["dsnap_p"][i] / MM, s1["kp"][i], "s", color=COL[i], ms=6, mfc="none")
        ax[1].plot(POSTER["dsnap_d"][i], s1["kd"][i], "x", color=COL[i], ms=10, mew=2)
        ax[1].plot(POSTER["dsnap_p"][i], s1["kp"][i], "+", color=COL[i], ms=10, mew=2)
    ax[1].plot([], [], "kx", label="poster d_snap (x driver, + piezo)")
    ax[1].plot([], [], "ks", mfc="none", label="corrected piezo snap (k-line -.)")
    ax[1].set(xlabel="gap d (mm)", ylabel="stiffness (N/m)", ylim=(1, 1e4),
              title="Snap-in: magnetic stiffness = spring stiffness")
    ax[1].legend(fontsize=7.5); ax[1].grid(which="both", alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "01_force_vs_gap_snap.png"), dpi=140)
    plt.close(fig)


def plot_before_after(s1):
    qs = [("d_snap driver (mm)", POSTER["dsnap_d"], s1["dsnap_d"] / MM, False),
          ("d_safe (mm)", POSTER["dsafe"], s1["dsafe"] / MM, False),
          ("F_avail (mN)", POSTER["Favail"], s1["Favail"] * 1e3, True),
          ("Force margin (x)", POSTER["margin"], s1["margin"], True)]
    fig, ax = plt.subplots(1, 4, figsize=(15, 4))
    x = np.arange(3)
    for a, (name, old, new, log) in zip(ax, qs):
        a.bar(x - .2, old, .4, color="#999999", label="poster")
        a.bar(x + .2, new, .4, color="#d62728", label="corrected")
        for xi, o, n_ in zip(x, old, new):
            a.text(xi - .2, o, f"{o:.3g}", ha="center", va="bottom", fontsize=8)
            a.text(xi + .2, n_, f"{n_:.3g}", ha="center", va="bottom", fontsize=8)
        if log:
            a.set_yscale("log")
        if "margin" in name:
            a.axhline(1, color="k", lw=1); a.axhline(MARGIN_MIN, color="g", ls="--", lw=1)
        a.set_xticks(x, LBL); a.set_title(name); a.grid(axis="y", alpha=.3)
    ax[0].legend()
    fig.suptitle("Poster vs corrected Section 8-10 values (F_req unchanged: 22.0 / 14.2 / 9.5 mN)")
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "02_before_after.png"), dpi=140)
    plt.close(fig)


def plot_time(runs, systems, i):
    kinds = ["asdrawn", "corrected", "redesign"]
    titles = ["Poster as drawn (d_min = poster d_safe)", "Poster, corrected d_safe",
              "Redesign"]
    fig, ax = plt.subplots(3, 3, figsize=(16, 10), sharex="col")
    for c, k in enumerate(kinds):
        r, p = runs[k][i]["poster"], systems[k][i]
        rp = runs[k][i]["phys"]
        w = r["t"] >= T_SIM - 0.4
        t = r["t"][w]
        ax[0, c].plot(t, r["d"][w] / MM, "k")
        ax[0, c].axhline(p["dsnap"] / MM, color="r", ls="--", label=f"two-body snap {p['dsnap'] / MM:.1f} mm")
        ax[0, c].axhline(p["dc"] / MM, color="m", ls=":", label="contact")
        ax[0, c].set_title(f"{LBL[i]} - {titles[c]}\n"
                           f"{'CAPTURED / STUCK' if r['stuck'] else ('contact events' if r['contact'] else 'no contact')}, "
                           f"plucks/s={r['plucks_per_s']:.0f}", fontsize=9)
        ax[0, c].set_ylabel("gap d (mm)"); ax[0, c].legend(fontsize=7)
        ax[1, c].plot(t, r["xd"][w] / MM, label="driver x_d")
        ax[1, c].plot(t, r["xp"][w] / MM, label="piezo x_p")
        ax[1, c].set_ylabel("tip displacement (mm)"); ax[1, c].legend(fontsize=7)
        ax[2, c].plot(t, r["V"][w], color="C3", label=f"poster theta: Vpk={r['Vpk']:.1f} V")
        ax[2, c].plot(t, rp["V"][w], color="C2", label=f"physical theta: Vpk={rp['Vpk']:.1f} V")
        ax[2, c].set_ylabel(f"V across {R_LOAD / 1e6:g} MOhm"); ax[2, c].set_xlabel("t (s)")
        ax[2, c].legend(fontsize=7)
        for a in ax[:, c]:
            a.grid(alpha=.3)
    fig.suptitle(f"Time domain at f_exc = driver f_n, base accel {A_BASE} m/s$^2$", fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, f"03_time_{LBL[i].split()[0]}mm.png"), dpi=120)
    plt.close(fig)


def plot_fft(runs, systems, s1):
    fig, ax = plt.subplots(2, 3, figsize=(16, 7))
    for row, k in enumerate(["corrected", "redesign"]):
        for i in range(3):
            r, p = runs[k][i]["phys"], systems[k][i]
            a = ax[row, i]
            m = r["fr"] <= 120
            a.semilogy(r["fr"][m], r["spec"][m] + 1e-6, "k", lw=1)
            a.axvline(p["fd"], color="b", ls="--", label=f"input = driver f_n {p['fd']:.1f} Hz")
            a.axvline(p["fp"], color="r", ls="--", label=f"piezo f_n {p['fp']:.1f} Hz")
            a.set_title(f"{'Poster (corrected gap)' if k == 'corrected' else 'Redesign'} {LBL[i]}: "
                        f"plucks/s={r['plucks_per_s']:.0f}", fontsize=9)
            a.set_xlabel("Hz"); a.set_ylabel("|V| (V, physical theta)")
            a.legend(fontsize=7); a.grid(alpha=.3)
    fig.suptitle("Output voltage spectrum (steady state). Up-conversion = energy at piezo f_n above the input frequency")
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "04_fft_upconversion.png"), dpi=130)
    plt.close(fig)


def plot_sweep(sw):
    fig, ax = plt.subplots(2, 3, figsize=(16, 8), sharex=True)
    for i in range(3):
        for k, st in (("corrected", "--"), ("redesign", "-")):
            for th, colr in (("poster", "C3"), ("phys", "C2")):
                r = sw[(k, i, th)]
                ax[0, i].plot(SWEEP_F, r["Vpk"], st, color=colr,
                              label=f"{k}, {th} theta")
                bad = r["contact"]
                ax[0, i].plot(SWEEP_F[bad], r["Vpk"][bad], "kx", ms=6)
            r = sw[(k, i, "phys")]
            if k == "redesign":
                ax[0, i].plot(SWEEP_F, sw[("nomag", i, "phys")]["Vpk"], ":", color="C2",
                              label="redesign, magnets removed (phys theta)")
            ax[1, i].plot(SWEEP_F, r["dmin"] / MM, st, color="k", label=f"{k}: min gap")
            ax[1, i].plot(SWEEP_F, r["xpk"] / MM, st, color="C1", label=f"{k}: peak piezo defl.")
        ax[0, i].set_title(f"{LBL[i]} (x = magnet contact/snap)"); ax[0, i].set_ylabel("peak V")
        ax[0, i].set_yscale("log"); ax[0, i].grid(alpha=.3, which="both")
        ax[1, i].axhline(DELTA_REQ / MM, color="C1", ls=":", lw=1)
        ax[1, i].set_ylabel("mm"); ax[1, i].set_xlabel("excitation frequency (Hz)")
        ax[1, i].set_yscale("log"); ax[1, i].grid(alpha=.3, which="both")
    ax[0, 0].legend(fontsize=7); ax[1, 0].legend(fontsize=7)
    fig.suptitle(f"Frequency sweep, base accel {A_BASE} m/s$^2$, rest gap fixed per design")
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "05_sweep_peakV.png"), dpi=130)
    plt.close(fig)


def plot_pluck(plk, curves, runs, systems):
    fig, ax = plt.subplots(2, 3, figsize=(16, 9))
    for i in range(3):
        r, p = plk[i], systems["redesign"][i]
        a = ax[0, i]
        a.plot(r["t"] * 1e3, r["xd"] / MM, "C0", label="driver x_d (prescribed retreat)")
        a.plot(r["t"] * 1e3, r["xp"] / MM, "C1", lw=2, label="piezo x_p")
        a.axvline(r["tau"] * 1e3, color="k", ls=":", lw=1)
        a.text(r["tau"] * 1e3, a.get_ylim()[1] * 0.9, " driver parked", fontsize=8)
        a2 = a.twinx()
        a2.plot(r["t"] * 1e3, r["V"], "C2", lw=1, alpha=.8)
        a2.set_ylabel("V (physical theta)", color="C2")
        a.set_title(f"Redesign {LBL[i]}: single pull & release\n"
                    f"pulled {r['pull'] / MM:.2f} mm, rings {r['ring'] / MM:.2f} mm (R={r['R']:.2f}), "
                    f"V_pk after release {r['Vpk_after']:.1f} V", fontsize=9)
        a.set_xlabel("t (ms)"); a.set_ylabel("tip displacement (mm)")
        a.legend(fontsize=7, loc="lower right"); a.grid(alpha=.3)
    a = ax[1, 0]
    for i in range(3):
        fr, R = curves[i]
        a.semilogx(fr, R, color=COL[i], label=LBL[i])
        p = systems["redesign"][i]
        a.plot(plk[i]["tau"] * p["fp"], plk[i]["R"], "o", color=COL[i])
    a.axvspan(0.01, 0.5, color="g", alpha=.08)
    a.text(0.03, 0.15, "sharp release:\nreal pluck", color="g", fontsize=9)
    a.set_xlabel("release time / piezo period  (tau / T_p)")
    a.set_ylabel("ring amplitude / pull amplitude")
    a.set_title("How fast must the magnet let go?  (dots = redesign, tau = T_d/2)", fontsize=9)
    a.legend(fontsize=8); a.grid(alpha=.3, which="both")
    for c, i in zip((1, 2), (0, 2)):
        r, p = runs["redesign"][i]["phys"], systems["redesign"][i]
        w = r["t"] >= T_SIM - 0.25
        a = ax[1, c]
        a.plot(r["t"][w] * 1e3, r["xp"][w] / MM, "C1", lw=2, label="piezo x_p")
        a.plot(r["t"][w] * 1e3, r["xd"][w] / MM * 0.1, "C0", lw=1, label="driver x_d (x0.1)")
        tmin = r["t"][w][find_peaks(-r["d"][w])[0]]
        for tt in tmin:
            a.axvline(tt * 1e3, color="r", lw=.8, ls="--")
        a.set_title(f"Steady state, redesign {LBL[i]} at {p['fd']:.1f} Hz: red = each pluck\n"
                    f"only f_p/f_d = {p['fp'] / p['fd']:.2f} piezo cycles between plucks -> no visible ring-down",
                    fontsize=9)
        a.set_xlabel("t (ms)"); a.set_ylabel("mm"); a.legend(fontsize=7); a.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "07_pluck_release.png"), dpi=130)
    plt.close(fig)


def plot_margin_param(s1, red):
    specs = [("D_d", "driver magnet diameter (mm)", MM), ("h_d", "driver magnet height (mm)", MM),
             ("t_d", "driver thickness (mm)", MM), ("L_d", "driver length (mm)", MM),
             ("D_p", "piezo magnet diameter (mm)", MM), ("m_add", "driver added tip mass (g)", 1e-3)]
    fig, ax = plt.subplots(2, 3, figsize=(16, 8))
    for a, (v, lab, unit) in zip(ax.ravel(), specs):
        for i in range(3):
            if red[i] is None:
                continue
            d0 = red[i]["design"]
            x0 = d0[v]
            xs = np.linspace(max(x0 * 0.3, 0.0) if v != "m_add" else 0.0,
                             x0 * 2.5 if v != "m_add" else 5e-3, 300)
            xs = xs[xs > 0] if v != "m_add" else xs
            dd = {k: np.full_like(xs, val) for k, val in d0.items()}; dd[v] = xs
            r = evaluate(L_PIEZO[i], s1["kp"][i], s1["mu_p"], **dd)
            inband = ((r["fd"] >= FD_BAND[0]) & (r["fd"] <= FD_BAND[1])
                      & (r["fp"] >= FP_BAND[0]) & (r["fp"] <= FP_BAND[1]))
            a.plot(xs / unit, np.where(inband, r["margin"], np.nan), color=COL[i], lw=2,
                   label=f"{LBL[i]} (in f band)")
            a.plot(xs / unit, np.where(~inband, r["margin"], np.nan), color=COL[i], lw=1, ls=":")
            a.plot(x0 / unit, red[i]["metrics"]["margin"], "o", color=COL[i])
        a.axhline(MARGIN_MIN, color="g", ls="--", label=f"required {MARGIN_MIN}x")
        a.axhline(1.0, color="k", lw=.8)
        a.set_xlabel(lab); a.set_ylabel("margin F_avail/F_req (two-body snap)")
        a.grid(alpha=.3)
    ax[0, 0].legend(fontsize=7)
    fig.suptitle("Margin vs one design parameter (others at the redesign point; dotted = f_n outside band)")
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "06_margin_vs_parameter.png"), dpi=130)
    plt.close(fig)


# =============================================================================
# MAIN
# =============================================================================
def main():
    t0 = time.time()
    os.makedirs(PLOTS, exist_ok=True); os.makedirs(RESULTS, exist_ok=True)
    s1, T = step1()

    # ---------- verification gate: Tables 5-8 must match the poster ----------
    checks = {
        "k_piezo (T6)": (s1["kp"], POSTER["k_p"]), "k_driver (T7)": (s1["kd"], POSTER["k_d"]),
        "m_eff driver (T8)": (s1["meff_d"], POSTER["meff_d"]),
        "f_piezo (T8)": (s1["fp_rep"], POSTER["f_p"]), "f_driver (T8)": (s1["fd"], POSTER["f_d"]),
        "magnet m (S7)": (np.array([s1["mdip"]]), [POSTER["m_dip"]]),
        "C (S7)": (np.array([s1["C"]]), [POSTER["C"]]),
    }
    print("=== VERIFICATION vs poster (tolerance 1%) ===")
    allok = True
    for name, (a, b) in checks.items():
        err = np.max(np.abs(pct(np.asarray(a), np.asarray(b))))
        ok = err < 1.0; allok &= ok
        print(f"  {name:20s} max |err| = {err:6.3f}%  {'OK' if ok else 'FAIL'}")
    print("  segment fit (raw, mm):", np.round(s1["seg_fit_raw_mm"], 3),
          " used:", [SEG_LA / MM, SEG_LB / MM, SEG_LC / MM])
    if not allok:
        raise SystemExit("Reproduction of Tables 5-8 failed - not trusting downstream results.")

    print("\n=== STEP 1: corrected Sections 8-10 ===")
    print(T["t9"]); print(T["t10"]); print("\nBefore/after:\n" + T["ba"])

    # ---------- Step 2 ----------
    red, grids = step2(s1)
    log_rows, red_rows = [], []
    why = {"L_d": "sets driver k (k ~ L^-3) and f_d",
           "t_d": "driver k ~ t^3: stiffer driver raises F_avail ~ k^0.8",
           "b_d": "driver k ~ b",
           "D_d": "bigger driver magnet: C ~ m_d m_p, and acts as tip mass so a stiffer driver stays at 16-30 Hz",
           "h_d": "same as D_d (volume)",
           "m_add": "dead tip mass to pull f_d back into band",
           "D_p": "piezo magnet: C ~ m_p but adds piezo mass (lowers f_p)",
           "h_p": "same as D_p"}
    for i, r in enumerate(red):
        if r is None:
            print(f"{LBL[i]}: NO feasible redesign in grid"); continue
        base = dict(BASE, L_d=L_PIEZO[i] - DRIVER_OFFSET)
        for v in DESIGN_VARS:
            old, new = base[v], r["design"][v]
            if abs(new - old) > 1e-12:
                u = 1e3 if v == "m_add" else 1 / MM
                unit = "g" if v == "m_add" else "mm"
                log_rows.append([LBL[i], v, f"{old * u:.3g} {unit}", f"{new * u:.3g} {unit}", why[v]])
        m = r["metrics"]
        red_rows.append([LBL[i], f"{m['kd']:.1f}", f"{s1['kp'][i]:.1f}", f"{m['fd']:.1f}",
                         f"{m['fp']:.1f}", f"{m['C']:.3e}", f"{m['dsafe'] / MM:.1f}",
                         f"{m['Freq'] * 1e3:.1f}", f"{m['Fav'] * 1e3:.1f}", f"{m['margin']:.2f}x",
                         f"{m['margin_poster_rule']:.2f}x", f"{m['Xrel'] / MM:.2f}", f"{m['swing']:.2f}x",
                         f"{m['Fav'] / s1['kp'][i] / MM:.2f}",
                         r["n_feasible"], "yes" if m["fp"] >= 1.1 * m["fd"] else "no"])
    T["redlog"] = md_table(["Config", "Parameter", "Old", "New", "Why"], log_rows)
    T["red"] = md_table(["Config", "k_d (N/m)", "k_p (N/m)", "f_d (Hz)", "f_p (Hz)", "C (N m^4)",
                         "d_safe (mm)", "F_req (mN)", "F_avail (mN)", "Margin (two-body)",
                         "Margin (poster rule)", "X_rel @f_d (mm)", "force swing / F_req",
                         "static pluck defl. (mm)", "# feasible grid pts",
                         "f_p >= 1.1 f_d"], red_rows)
    print("\n=== STEP 2: redesign ===\n" + T["redlog"] + "\n\n" + T["red"])

    # ---------- Step 3 ----------
    cp_ = coupling_estimates(s1)
    print(f"\nCp = {CP * 1e9:.2f} nF; theta_poster = {cp_['th_poster']:.3e} N/V "
          f"(kappa^2 = {np.round(cp_['kappa2_poster'], 2)}); theta_phys = {np.round(cp_['th_phys'], 7)} "
          f"(kappa^2 = {np.round(cp_['kappa2_phys'], 4)})")
    print(f"Energy check @0.5 mm: U_mech = {np.round(cp_['U_mech'] * 1e6, 2)} uJ, "
          f"U_elec(50 V) = {cp_['U_elec'] * 1e6:.2f} uJ")

    kinds = ["asdrawn", "corrected", "redesign", "nomag"]
    systems = {k: [system_params(k, i, s1, red) for i in range(3)] for k in kinds}
    runs = {k: [] for k in kinds}
    sim_rows = []
    for k in kinds:
        for i in range(3):
            p = systems[k][i]
            rr = {"poster": run_case(p, cp_["th_poster"], p["fd"]),
                  "phys": run_case(p, cp_["th_phys"][i], p["fd"])}
            runs[k].append(rr)
            for th in ("poster", "phys"):
                r = rr[th]
                status = "STUCK (captured)" if r["stuck"] else ("contact/snap" if r["contact"] else "ok")
                sim_rows.append([LBL[i], k, th, f"{p['g0'] / MM:.2f}", f"{p['fd']:.1f}", f"{p['fp']:.1f}",
                                 f"{r['min_gap'] / MM:.2f}", f"{p['dsnap'] / MM:.1f}", status,
                                 f"{r['swing']:.2f}",
                                 f"{r['plucks_per_s']:.0f}", f"{r['peak_xd'] / MM:.2f}",
                                 f"{r['peak_xp'] / MM:.3f}", f"{r['Vpk']:.2f}", f"{r['Vrms']:.2f}",
                                 f"{r['P_avg'] * 1e6:.2f}",
                                 "-" if np.isnan(r["A_fp"]) else f"{r['A_fp'] / max(r['A_fexc'], 1e-12):.2f}"])
            print(f"  ran {k:9s} {LBL[i]}  ({time.time() - t0:.0f}s)")
    T["sim"] = md_table(["Config", "Design", "theta", "rest gap (mm)", "f_exc=f_d (Hz)", "f_p (Hz)",
                         "min gap (mm)", "snap gap (mm)", "magnets", "median swing/F_req", "full plucks/s",
                         "peak x_d (mm)", "peak x_p (mm)", "V peak", "V rms", "P avg (uW)",
                         "|V(f_p)|/|V(f_exc)|"], sim_rows)
    print("\n=== STEP 3: time-domain (f_exc = driver f_n) ===\n" + T["sim"])

    # cross-check: fixed-step RK4 vs LSODA on redesign 85 mm
    p = systems["redesign"][0]
    chk = sweep_rk4([p], [cp_["th_phys"][0]], [p["fd"]])
    T["xcheck"] = (f"Solver cross-check (redesign 85 mm, physical theta): LSODA Vpk = "
                   f"{runs['redesign'][0]['phys']['Vpk']:.3f} V, RK4(dt={DT_RK4:g}) Vpk = {chk['Vpk'][0]:.3f} V; "
                   f"min gap {runs['redesign'][0]['phys']['min_gap'] / MM:.3f} vs {chk['dmin'][0] / MM:.3f} mm")
    print(T["xcheck"])

    # sweeps
    plist, thl, fl, keys = [], [], [], []
    for k in ("corrected", "redesign", "nomag"):
        for i in range(3):
            for th in ("poster", "phys"):
                thv = cp_["th_poster"] if th == "poster" else cp_["th_phys"][i]
                for f in SWEEP_F:
                    plist.append(systems[k][i]); thl.append(thv); fl.append(f)
                keys.append((k, i, th))
    print(f"\nsweeping {len(plist)} cases (vectorised RK4)...")
    swr = sweep_rk4(plist, thl, fl)
    sw, nF = {}, len(SWEEP_F)
    for j, key in enumerate(keys):
        sw[key] = {k: v[j * nF:(j + 1) * nF] for k, v in swr.items()}
    sweep_rows = []
    for k in ("corrected", "redesign", "nomag"):
        for i in range(3):
            for th in ("poster", "phys"):
                r = sw[(k, i, th)]
                j = int(np.argmax(r["Vpk"]))
                works = (r["plucks_per_s"] > 0) & ~r["contact"]
                band = SWEEP_F[works]
                sweep_rows.append([LBL[i], k, th, f"{SWEEP_F[j]:.1f}", f"{r['Vpk'][j]:.1f}",
                                   f"{band.min():.1f}-{band.max():.1f}" if band.size else "none",
                                   int(r["contact"].sum()),
                                   f"{np.interp(10.0, SWEEP_F, r['Vpk']):.2f}"])
    T["sweep"] = md_table(["Config", "Design", "theta", "f at max V (Hz)", "max V peak",
                           "f range with full plucks & no contact (Hz)",
                           "# sweep pts with magnet contact", "V peak @10 Hz"], sweep_rows)
    print(T["sweep"])

    # manual pluck cross-check
    meas = [(0.45, 45), (1.0, 74), (1.5, 148)]
    T["pluck"] = md_table(["tip defl. (mm)", "measured (V)", "poster-calib. 100 V/mm", "% err",
                           "physical theta 85 mm (V)"],
                          [[x, v, f"{x * MM * cp_['vpm_poster']:.0f}",
                            f"{pct(x * MM * cp_['vpm_poster'], v):+.0f}",
                            f"{x * MM * cp_['vpm_phys'][0]:.1f}"] for x, v in meas])
    T["coupling"] = md_table(
        ["Config", "theta poster (N/V)", "kappa^2 poster", "theta physical (N/V)", "kappa^2 physical",
         "V/mm physical", "U_mech @0.5mm (uJ)", "U_elec @50V (uJ)"],
        [[LBL[i], f"{cp_['th_poster']:.2e}", f"{cp_['kappa2_poster'][i]:.2f}", f"{cp_['th_phys'][i]:.2e}",
          f"{cp_['kappa2_phys'][i]:.4f}", f"{cp_['vpm_phys'][i] * MM:.1f}",
          f"{cp_['U_mech'][i] * 1e6:.2f}", f"{cp_['U_elec'] * 1e6:.2f}"] for i in range(3)])

    # plots
    plot_force_gap(s1); plot_before_after(s1)
    for i in range(3):
        plot_time(runs, systems, i)
    plot_fft(runs, systems, s1); plot_sweep(sw); plot_margin_param(s1, red)

    # single pull-and-release test (redesign, physical theta)
    plk, curves, prow = [], [], []
    for i in range(3):
        p = systems["redesign"][i]
        th = cp_["th_phys"][i]
        r = pluck_release(p, th, 0.5 / p["fd"])        # natural retreat = half driver period
        plk.append(r)
        fr = np.logspace(-1.5, 0.5, 18)
        curves.append((fr, [pluck_release(p, th, x / p["fp"])["R"] for x in fr]))
        prow.append([LBL[i], f"{p['fd']:.1f}", f"{p['fp']:.1f}", f"{p['fp'] / p['fd']:.2f}",
                     f"{r['tau'] * 1e3:.0f}", f"{r['tau'] * p['fp']:.2f}", f"{r['pull'] / MM:.2f}",
                     f"{r['ring'] / MM:.2f}", f"{r['R']:.2f}", f"{r['Vpk_after']:.2f}"])
    T["pluck_release"] = md_table(["Config", "f_d (Hz)", "f_p (Hz)", "f_p/f_d (piezo cycles per pluck)",
                                   "release time (ms)", "release / T_p", "pull (mm)",
                                   "free ring after release (mm)", "ring / pull", "V_pk after release"], prow)
    print("\n=== Single pull-and-release test ===\n" + T["pluck_release"])
    plot_pluck(plk, curves, runs, systems)

    # write tables + summary
    with open(os.path.join(RESULTS, "tables.md"), "w") as fh:
        for k, v in T.items():
            fh.write(f"## {k}\n\n{v}\n\n")
    summ = dict(seg_fit_mm=s1["seg_fit_raw_mm"], mu_p=s1["mu_p"], mtip_fit=s1["mtip_fit"],
                rho_pzt_impl=s1["rho_pzt_impl"], mmag=s1["mmag"], Cp=CP,
                frac_pzt=cp_["frac_pzt"], shares=s1["shares"].tolist(),
                redesign=red, systems={k: [{kk: float(vv) for kk, vv in p.items()} for p in v]
                                       for k, v in systems.items()})
    with open(os.path.join(RESULTS, "summary.json"), "w") as fh:
        json.dump(summ, fh, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(f"\nDone in {time.time() - t0:.0f}s. Plots -> {PLOTS}, tables -> {RESULTS}/tables.md")


if __name__ == "__main__":
    main()
