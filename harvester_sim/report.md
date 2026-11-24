# Magnetically Plucked Piezo Harvester: Re-analysis, Correction, Redesign, Simulation

Source: poster "Design and Optimization of a Magnetically Plucked Piezoelectric Vibration Energy Harvester" (A. Yenamandra, HS-EGSD-0192).
Code: [sim.py](sim.py) (one file, parameters at the top). Run with `python sim.py` (~2.5 min). Plots are in [plots/](plots/). All generated tables are in [results/tables.md](results/tables.md), and the full run log is [results_run.log](results_run.log).

## Bottom line

1. **The poster's Section 8 snap distances are wrong by a factor of about 2.4.** Its own formula, d_snap = (4C/k)^(1/5), gives 13.3 / 14.3 / 15.3 mm for the drivers, not 5.54 / 6.14 / 6.84 mm. Carrying that through:
   - d_safe becomes 19.9 / 21.5 / 22.9 mm.
   - F_avail becomes 8.2 / 6.0 / 4.6 mN.
   - The force margin is **0.37 / 0.43 / 0.49×, not 12×**.
   - **The design as drawn cannot pluck the piezo.** If it is built with the poster's gaps (8–10 mm closest approach), the simulation shows the magnets **snap together and stay stuck** at all three lengths.
2. **Tables 2 and 5–8 reproduce to within 0.4%, and the Section 7 magnet values match.** Two inconsistencies turned up along the way:
   - Section C's neutral axis and I don't correspond to any physical layer stack.
   - Table 8 uses a piezo tip mass of 0.17 g, while the driver uses 0.295 g for the identical magnet.
3. **The 50 V at 0.5 mm calibration is physically impossible.** With the bimorph's 7.5 nF capacitance, 50 V stores 9.4 µJ. Bending the 85 mm beam 0.5 mm stores only 5.5 µJ, and less for the longer beams. A first-principles estimate gives about **5–8 V/mm**, not 100 V/mm.
4. **A redesign that meets every rule exists for all three piezo lengths** (85/95/105 mm, piezo beam unchanged). The rules are: margin ≥ 1.5 (achieved 1.61–1.71×), the 1.5× snap safety factor, driver and piezo f_n inside the band, and no capture. The main changes are a large 12.7 mm driver magnet on a stiffer, shorter driver. In simulation it plucks once per cycle at ~16 Hz with no magnet contact.
5. **The redesign does not reach 50 V.** With physically estimated coupling, peak output at the driver resonance is **3.3 / 3.6 / 7.9 V** (1 MΩ load). Even with the poster's own (impossible) calibration it is only 13–17 V.
6. **The pull-and-release pluck works, but it can't show up as frequency up-conversion while the piezo is held to 18–30 Hz.**
   - In a single pull-and-release test, the redesigned piezo is pulled ~0.7 mm, and after the driver swings away it vibrates freely at its own f_n with 54–73% of that amplitude (~2 V).
   - In continuous operation, the driver returns after only f_p/f_d = 1.1–1.6 piezo cycles. Each new pluck lands before any ring-down can develop, so the output stays locked to the input frequency (plus a 2× harmonic).
   - The piezo's f_n is also inside the ambient band. In the sweep, the highest voltage comes from exciting the piezo directly at its own resonance, **and it is almost the same with the magnets removed.**

---

## Step 1: Rebuilt analytical chain

### Table 2: Transformed widths ✔
| Layer | E (GPa) | n | b_tr (mm) | poster |
|---|---|---|---|---|
| PETG | 2.1 | 1.00 | 10.0 | 10.0 |
| PZT | 66 | 31.43 | 314.3 | 314.3 |
| Cu | 117 | 55.71 | 557.1 | 557.1 |

### Tables 3, 4, 5: Neutral axis, I, EI (transformed to PETG, b = 10 mm)
I searched all layer stacks of PETG/PZT/Cu (thicknesses 1.0 / 0.2 / 0.1 mm), with both area conventions.

| Section / stack | ȳ (mm) | poster ȳ | I (mm⁴) | poster I | EI (N·m²) | poster EI |
|---|---|---|---|---|---|---|
| A/D: PETG | 0.500 | 0.500 | 0.833 | 0.833 | 1.750e-3 | 1.750e-3 |
| **B: PETG + Cu only** (exact match) | 0.966 | 0.966 | 3.444 | 3.444 | 7.233e-3 | 7.232e-3 |
| C cand. 1: PETG + PZT + Cu | 1.118 | 1.023 | 5.900 | 6.959 | 1.239e-2 | 1.461e-2 |
| C cand. 2: PETG + PZT + PZT | 1.148 | 1.023 | 7.048 | 6.959 | 1.480e-2 | 1.461e-2 |
| C cand. 3: symmetric PZT/PETG/PZT | 0.700 | 1.023 | 46.51 | 6.959 | 9.767e-2 | 1.461e-2 |
| C real hardware: PETG + 5 mm-wide PZT/Cu/PZT bimorph | 1.176 | 1.023 | 7.547 | 6.959 | 1.585e-2 | 1.461e-2 |

Self-consistency:
- **EI = E_PETG·I holds for every row of Table 5**, and the stiffness ratios are 1.00 / 4.13 / 8.35.
- **Section B is self-consistent, but it is PETG plus a 0.1 mm copper layer with no PZT.** That is an odd "piezo" section.
- **Section C is not self-consistent.** No stack gives both ȳ = 1.023 mm and I = 6.959 mm⁴. The nearest matches either get I right with ȳ ≈ 1.15 mm (two PZT layers on top), or are 15% off in I.
- The suspicion is correct: a symmetric bimorph-on-substrate gives ȳ = 0.700 mm, but then I = 46.5 mm⁴ (6.7× the poster's), which would make k_piezo far higher.
- The poster also treats the PZT as 10 mm wide. The bimorph listed under "Important Dimensions" is 5 mm wide.

**Decision:** to reproduce Tables 6–8, the poster's EI values are used as given. The real-hardware stack is used only for the coupling estimate.

### Tables 6 and 7: Spring constants ✔
The piezo uses the series-segment formula, which is the exact tip-load result: δ/P = Σ(s_out³ − s_in³)/(3EI), with s measured from the tip. The segment lengths are illegible on the poster, so I fitted them by least squares, with one layout shared by all three lengths:
- **L_A = 0** (the stiffened region starts at the clamp)
- **L_B = 11.6 mm**
- **L_C = 45.4 mm**
- **L_D = remainder at the tip** (28 / 38 / 48 mm)

The raw fit was 11.628 / 45.403 mm.

| Length | k_piezo | poster | % | Driver L | k_driver = 3EI/L³ | poster | % |
|---|---|---|---|---|---|---|---|
| 85 mm | 43.89 | 43.9 | −0.01 | 75 mm | 12.44 | 12.4 | +0.36 |
| 95 mm | 28.40 | 28.4 | −0.01 | 85 mm | 8.55 | 8.55 | −0.01 |
| 105 mm | 18.89 | 18.9 | −0.04 | 95 mm | 6.12 | 6.12 | +0.05 |

### Table 8: Natural frequencies ✔ (with one inconsistency)
m_eff = 0.2357·µ·L + m_tip. The "0.2375" in the poster text is a typo. The driver values follow from first principles:
- µ = ρ·b·t = 0.0127 kg/m
- m_tip = N52 magnet mass = 0.295 g (ρ = 7500 kg/m³)

For the piezo, a linear fit to the poster's own m_eff column gives µ = 0.0520 kg/m, which implies a plausible PZT density of 7580 kg/m³. But it also gives **m_tip = 0.174 g**, not the 0.295 g of the identical magnet the driver carries. With the real magnet mass, the piezo frequencies drop slightly (last column). Those physical values are used in the redesign and the simulation.

| Cantilever | k | m_eff (kg) | poster m_eff | f_n (Hz) | poster | f_n with real magnet |
|---|---|---|---|---|---|---|
| Piezo 85 | 43.9 | 0.001215 | 0.001215 | 30.3 | 30.2 | 28.9 |
| Piezo 95 | 28.4 | 0.001337 | 0.001337 | 23.2 | 23.2 | 22.2 |
| Piezo 105 | 18.9 | 0.001460 | 0.001460 | 18.1 | 18.1 | **17.4 (< 18 Hz objective)** |
| Driver 75 | 12.44 | 0.000519 | 0.000520 | 24.6 | 24.6 | 24.6 |
| Driver 85 | 8.55 | 0.000549 | 0.000549 | 19.9 | 19.9 | 19.9 |
| Driver 95 | 6.12 | 0.000579 | 0.000579 | 16.4 | 16.4 | 16.4 |

### Section 7: Magnet ✔
m = B_r·V/µ₀ = 0.04625 A·m², and C = 3µ₀m²/(2π) = 1.2834e-9 N·m⁴ (poster 1.284e-9).

### Table 9: Snap distance (CORRECTED)
The snap condition is |dF/dd| = 4C/d⁵ = k, so **d_snap = (5.134e-9 / k)^(1/5)**.

| Config | d_snap piezo (mm) | d_snap driver (mm) | d_safe = 1.5·d_snap,drv (mm) | two-body d_snap, k_series (mm) | two-body d_safe (mm) |
|---|---|---|---|---|---|
| 85 mm | 10.32 | **13.28** ← governs | **19.9** | 13.96 | 20.9 |
| 95 mm | 11.26 | **14.31** ← governs | **21.5** | 15.09 | 22.6 |
| 105 mm | 12.21 | **15.30** ← governs | **22.9** | 16.18 | 24.3 |

The extra columns correct a second, smaller error. When both cantilevers are free, the gap closes through both springs in series, so the correct snap criterion is |dF/dd| = k_d·k_p/(k_d + k_p). That is softer than either spring alone, so snap happens even farther out. The redesign uses this stricter two-body criterion.

### Table 10: Force check (CORRECTED)
| Config | F_req = k_p × 0.5 mm (mN) | F_avail (mN) | Margin | Margin (two-body) | Static pluck deflection (mm) |
|---|---|---|---|---|---|
| 85 mm | 21.9 | 8.16 | **0.37×** | 0.30× | 0.186 |
| 95 mm | 14.2 | 6.04 | **0.43×** | 0.34× | 0.213 |
| 105 mm | 9.4 | 4.63 | **0.49×** | 0.39× | 0.245 |

### Before / after ([plots/02_before_after.png](plots/02_before_after.png), [plots/01_force_vs_gap_snap.png](plots/01_force_vs_gap_snap.png))
| Quantity | 85 mm poster → corrected | 95 mm | 105 mm |
|---|---|---|---|
| d_snap piezo (mm) | 4.13 → 10.3 (+150%) | 4.67 → 11.3 (+141%) | 5.22 → 12.2 (+134%) |
| d_snap driver (mm) | 5.54 → 13.3 (+140%) | 6.14 → 14.3 (+133%) | 6.84 → 15.3 (+124%) |
| d_safe (mm) | 8.3 → 19.9 (+140%) | 9.2 → 21.5 (+133%) | 10.3 → 22.9 (+123%) |
| F_req (mN) | 22.0 → 21.9 (0%) | 14.2 → 14.2 (0%) | 9.5 → 9.45 (−1%) |
| F_avail (mN) | 269 → 8.16 (−97%) | 179 → 6.04 (−97%) | 114 → 4.63 (−96%) |
| Margin | 12× → 0.37× (−97%) | 13× → 0.43× (−97%) | 12× → 0.49× (−96%) |
| Static pluck deflection F_avail/k_p (mm) | 6.13 → 0.186 | 6.30 → 0.213 | 6.03 → 0.245 |
| Implied V at the poster's 100 V/mm | 613 → 18.6 V | 630 → 21.3 V | 603 → 24.5 V |

I could not reconstruct the arithmetic behind the poster's d_snap values; they don't match any simple variant of the formula. Conclusions affected:
- "Force margins were 12×": false (0.4×).
- "Reliable plucking without magnet snapping": false at the poster's gaps (they are inside the snap distance).
- "Off resonance can constantly reach at least 50 V": not supported (see Step 3).

---

## Step 2: Redesign

**Rules enforced:**
- Static margin F_avail/F_req ≥ **1.5**, evaluated with the stricter two-body snap criterion.
- d_safe = 1.5 × d_snap.
- Driver f_n in 16–30 Hz.
- Piezo f_n in 18–30 Hz, computed with the real magnet mass.
- Closest approach ≥ 2× the largest magnet dimension, so the point-dipole force law stays valid.
- Prefer f_p ≥ 1.1·f_d, so the piezo sits above the input frequency.

**One rule I added after the first simulation:** a per-cycle force swing of [F(d_safe) − F(d_safe + 2X_rel)] / F_req ≥ **1.2**, at the driver resonance and 2 m/s². The first redesign met the static margin, yet the simulation showed the static force at the rest gap was already about 1× F_req. A preload deflects the piezo once and produces no voltage; only the swing plucks it. A swing of ≥ 1.5 is infeasible across the whole search grid (the best is 1.30 / 1.48 / 1.42×), so 1.2 is used.

**The search:** a grid of 2.3 M designs per length. It covers driver length, thickness and width; driver magnet D and h; added driver tip mass; and piezo magnet D and h. The piezo beam itself is unchanged: same bimorph, same layup, and the poster's 85/95/105 mm lengths are kept as baselines. N52 is kept, since it is already the strongest grade. The chosen design is the feasible one with the smallest total log-change from the poster.

**Why it works:**
- F_avail at d_safe scales as C^0.2·k^0.8. The stiffer driver therefore helps most, but on its own it pushes f_d above 30 Hz.
- A **large driver magnet** fixes that. C scales with m_d·m_p, so it raises C, and its mass brings f_d back down to ~16 Hz.
- The piezo magnet stays small, so f_p stays in band.
- Low f_d also maximises driver amplitude (X ∝ 1/ω²), and amplitude is what produces force swing.

### Changes log
| Config | Parameter | Old | New | Why |
|---|---|---|---|---|
| 85 mm | driver length | 75 mm | 56 mm | k ∝ L⁻³ (stiffer driver) |
| 85 mm | driver thickness | 1 mm | 1.5 mm | k ∝ t³ |
| 85 mm | driver magnet | Ø5 × 2 mm | Ø12.7 × 8 mm | C ∝ m_d·m_p; magnet mass keeps f_d ≈ 16 Hz |
| 85 mm | driver added tip mass | 0 g | 2 g | pulls f_d into band |
| 85 mm | piezo magnet | Ø5 × 2 mm | Ø6 × 3 mm | more C; f_p still 25.7 Hz |
| 95 mm | driver length | 85 mm | 40 mm | k ∝ L⁻³ |
| 95 mm | driver magnet | Ø5 × 2 mm | Ø12.7 × 8 mm | as above |
| 105 mm | driver length | 95 mm | 66 mm | k ∝ L⁻³ |
| 105 mm | driver thickness | 1 mm | 1.5 mm | k ∝ t³ |
| 105 mm | driver magnet | Ø5 × 2 mm | Ø12.7 × 6 mm | as above |
| 105 mm | piezo magnet | Ø5 × 2 mm | Ø4 × 2 mm | lighter tip lifts f_p from 17.4 to 18.0 Hz (the original fails the 18 Hz floor) |

Width (10 mm) and grade (N52) are unchanged. The driver-to-piezo length offset is no longer 10 mm (it becomes 29 / 55 / 39 mm), so the **driver needs a riser block** to put the two magnets at the same height.

### Redesign performance
| Config | k_d | k_p | f_d | f_p | d_safe (mm) | F_req (mN) | F_avail (mN) | Margin (two-body) | Margin (poster rule) | Swing / F_req | Static pluck deflection (mm) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 85 mm | 100.9 | 43.9 | 16.1 | 25.7 | 37.2 | 21.9 | 37.4 | **1.71×** | 2.28× | 1.20 | 0.85 |
| 95 mm | 82.0 | 28.4 | 16.4 | 22.2 | 34.3 | 14.2 | 23.8 | **1.68×** | 2.13× | 1.20 | 0.84 |
| 105 mm | 61.6 | 18.9 | 16.1 | 18.0 | 32.0 | 9.4 | 15.2 | **1.61×** | 2.00× | 1.21 | 0.81 |

Sensitivity plot: [plots/06_margin_vs_parameter.png](plots/06_margin_vs_parameter.png).
- Margin rises steeply with driver thickness and shortening, but f_d soon leaves the band (dotted segments).
- Magnet size helps only weakly, as the C^0.2 scaling predicts.
- Added dead mass changes only frequency, not margin.

---

## Step 3: Time-domain simulation

**Model** (in `rhs_factory` and `sweep_rk4`):
- Base acceleration a·sin(2πft), with a 0.3 s ramp-in.
- Driver and piezo are each a lumped SDOF: k_eff, m_eff, ζ = 0.015, and a base-forcing participating mass of 0.375·µL + m_tip.
- Coaxial dipole attraction F = C/d⁴, with d = g₀ − (x_d − x_p). The force is clamped at face contact d_c = (h_d + h_p)/2, and a stiff contact penalty applies beyond it.
- Piezo electrical coupling: m·ẍ + c·ẋ + k·x + θV = F and C_p·V̇ + V/R = θ·ẋ.
- C_p = 7.53 nF (40 × 5 mm bimorph, two 0.2 mm PZT-5A layers in series, ε₃₃ᵀ = 1700ε₀), with R = 1 MΩ.

**Rest gap:** g₀ = (design minimum gap) + (linear relative amplitude at driver resonance, 2 m/s² ≈ 0.2 g). The design minimum gap is the poster's d_safe for "as drawn", the corrected d_safe for "corrected", and the redesign d_safe for "redesign".

**Solvers:** the main runs use LSODA (stiff, rtol 1e-7, max step 0.2 ms). The 1278-case sweep uses vectorised RK4 at dt = 10 µs. **The two solvers agree to within 0.03% on V_pk and the minimum gap.**

**A pluck** is a cycle in which the force swing F(d_min) − F(preceding d_max) ≥ F_req. **Captured** means the magnets are in contact for more than 50% of the final 0.5 s.

### Coupling calibration (θ)
| Config | θ poster (50 V at 0.5 mm) | κ² = θ²/(k·C_p) | θ physical | κ² physical | V/mm physical | U_mech at 0.5 mm | U_elec at 50 V |
|---|---|---|---|---|---|---|---|
| 85 mm | 7.53e-4 N/V | **1.71** | 6.11e-5 | 0.0113 | 8.1 | 5.49 µJ | 9.41 µJ |
| 95 mm | 7.53e-4 | **2.65** | 4.69e-5 | 0.0103 | 6.2 | 3.55 µJ | 9.41 µJ |
| 105 mm | 7.53e-4 | **3.98** | 3.61e-5 | 0.0092 | 4.8 | 2.36 µJ | 9.41 µJ |

**Poster calibration.** κ² > 1 means the electrical energy exceeds the mechanical strain energy, which violates energy conservation. In the simulation it shows up as heavy electrical stiffening: the "poster θ" curves peak at 36–40 Hz in the sweep, which is an artefact.

**Physical estimate.** κ² ≈ k₃₁² × (strain-energy share of the PZT-bearing section, 30–37%) × (PZT share of section EI, 26%), with k₃₁ = 0.34.

**Results are reported for both calibrations; treat "physical θ" as the realistic number.**

### Manual-pluck cross-check (Figs. 6–8, measured through a 40× divider, 5 ms sampling)
| Deflection | Measured | 100 V/mm linear | Error | Physical θ (85 mm) |
|---|---|---|---|---|
| 0.45 mm | 45 V | 45 V | 0% | 3.7 V |
| 1.0 mm | 74 V | 100 V | +35% | 8.1 V |
| 1.5 mm | 148 V | 150 V | +1% | 12.2 V |

The measured data are non-linear: the 1 mm point sits 26% below the line through the other two. There are also measurement reasons to doubt them:
- The piezo time constant into a divider is sub-millisecond, but sampling was every 5 ms, so peaks are under-sampled.
- The divider ratio and the impedance it presents are unknown.
- Hand-pluck deflections were probably not measured directly.

**I treat 100 V/mm as unverified and physically implausible.** The ~10× gap to the physical estimate is the largest single uncertainty in this report.

### Time-domain results at f_exc = driver f_n, 2 m/s² ([plots/03_time_85mm.png](plots/03_time_85mm.png), [95](plots/03_time_95mm.png), [105](plots/03_time_105mm.png))
"phys" means physical θ, 1 MΩ load.

| Config | Design | Rest gap (mm) | Min gap (mm) | Two-body snap (mm) | Magnets | Swing / F_req | Plucks/s | Peak x_p (mm) | V_pk phys | V_rms phys | P_avg phys (µW) | V_pk poster θ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 85 | as drawn | 11.8 | 1.84 | 14.0 | **CAPTURED** | – | 0 | 2.61 (stuck) | 2.70 | 1.84 | 3.4 | 5.9 |
| 95 | as drawn | 14.6 | 1.79 | 15.1 | **CAPTURED** | – | 0 | 3.99 (stuck) | 4.56 | 2.90 | 8.4 | 6.9 |
| 105 | as drawn | 18.2 | 1.84 | 16.2 | **CAPTURED** | – | 0 | 6.76 (stuck) | 8.46 | 5.35 | 28.7 | 7.9 |
| 85 | corrected gap | 23.4 | 21.1 | 14.0 | ok | 0.11 | 0 | 0.52 | 2.57 | 1.80 | 3.2 | 5.8 |
| 95 | corrected gap | 26.9 | 23.1 | 15.1 | ok | 0.17 | 0 | 1.05 | 4.09 | 2.78 | 7.7 | 7.3 |
| 105 | corrected gap | 30.9 | 24.9 | 16.2 | ok | 0.25 | 0 | 2.70 | 7.68 | 5.10 | 26.0 | 8.0 |
| 85 | **redesign** | 43.8 | 37.2 | 24.8 | ok | 1.13 | **15** | 1.05 | **3.29** | 1.96 | 3.8 | 16.7 |
| 95 | **redesign** | 40.7 | 34.0 | 22.9 | ok | 1.23 | **16** | 1.37 | **3.60** | 2.31 | 5.3 | 14.6 |
| 105 | **redesign** | 38.6 | 30.8 | 21.3 | ok | 1.46 | **16** | 3.14 | **7.92** | 5.27 | 27.8 | 12.9 |
| 85 | redesign, magnets removed | 43.8 | – | – | – | 0 | 0 | 0.17 | 0.84 | 0.59 | 0.35 | 4.2 |
| 95 | redesign, magnets removed | 40.7 | – | – | – | 0 | 0 | 0.33 | 1.28 | 0.89 | 0.79 | 4.8 |
| 105 | redesign, magnets removed | 38.6 | – | – | – | 0 | 0 | 1.26 | 3.69 | 2.39 | 5.7 | 5.6 |

How to read this:
- **As drawn:** the magnets are captured within the ramp-in at every length, so it is a failure.
- **Corrected gap:** safe, but the force swing is only 11–26% of F_req, so there is no real plucking. Whatever voltage exists comes from base excitation of the piezo itself, and in the 105 mm case its f_n of 17.4 Hz is right next to the 16.4 Hz input.
- **Redesign:** one full pluck per input cycle, the gap stays more than 9 mm outside the snap distance, and the magnets raise output 2.1–3.9× over the same geometry without magnets.

### Spectrum and up-conversion ([plots/04_fft_upconversion.png](plots/04_fft_upconversion.png))
The output is dominated by the input frequency. The redesign adds a clear 2·f_exc harmonic: for 85 mm, 32 Hz at about 18% of the fundamental. The component at the piezo's own f_n is 1% or less of the fundamental.

**The "frequency up-conversion" claimed on the poster is not reproduced in continuous operation.** The single pluck below shows that the pluck itself is real.

### Single pull-and-release test ([plots/07_pluck_release.png](plots/07_pluck_release.png))
This test isolates one pluck:
- The piezo starts in static equilibrium, pulled toward the driver at its closest approach.
- The driver then retreats over half its natural period and stops.
- There is no base excitation, and the coupling is physical θ.

| Config | f_d | f_p | Piezo cycles per pluck (f_p/f_d) | Release time | Release / T_p | Pull (mm) | Free ring after release (mm) | Ring / pull | V_pk after release |
|---|---|---|---|---|---|---|---|---|---|
| 85 mm | 16.1 | 25.7 | 1.60 | 31 ms | 0.80 | 0.69 | 0.37 | 0.54 | 2.36 V |
| 95 mm | 16.4 | 22.2 | 1.35 | 30 ms | 0.68 | 0.69 | 0.44 | 0.64 | 2.28 V |
| 105 mm | 16.1 | 18.0 | 1.12 | 31 ms | 0.56 | 0.70 | 0.51 | 0.73 | 1.78 V |

- **The mechanism works as intended.** After the magnet lets go, the piezo vibrates back and forth at its own f_n and decays over ~0.4 s (ζ = 0.015).
- **Two conditions decide whether it looks like a pluck in continuous operation:**
  1. **The release must be fast compared with the piezo's period.** Ring/pull is above 0.75 only when the release takes less than ~0.5 T_p, and it falls below 0.2 once the release takes more than ~1.5 T_p. In this coaxial geometry the release takes about half a driver period, because the force fades smoothly as the driver retreats.
  2. **The piezo needs several cycles between plucks to show a ring-down,** which means f_p must be several times f_d.
- **These two conditions conflict.** Raising f_p makes the same release slower relative to T_p. Meeting both needs either:
  - a **sharper release**, such as a pass-by geometry where the driver magnet sweeps across the piezo magnet at peak speed, or a stop-limited snap-off that deliberately crosses d_snap; or
  - a **piezo f_n well above the 18–30 Hz objective**. Only the driver needs to match ambient vibration; for up-conversion the piezo should be several times higher.

  Both options break a rule that this redesign keeps: the 1.5× snap safety factor or the piezo frequency band.

### Frequency sweep, 5–40 Hz ([plots/05_sweep_peakV.png](plots/05_sweep_peakV.png))
| Config | Design | Best f (Hz) | Max V_pk phys | Range with full plucks and no contact | V_pk at 10 Hz phys |
|---|---|---|---|---|---|
| 85 | corrected | 28.5 | 15.9 | none | 0.36 |
| 95 | corrected | 22.0 | 19.4 | none | 0.53 |
| 105 | corrected | 17.5 | 20.8 | none | 0.79 |
| 85 | redesign | 25.5 | 17.5 | 16.0 Hz only | 0.52 |
| 95 | redesign | 21.5 | 18.1 | 16.5 Hz only | 0.60 |
| 105 | redesign | 17.5 | 23.7 | 16.0–17.5 Hz | 0.81 |
| 85 | magnets removed | 26.0 | 17.3 | none | 0.43 |
| 95 | magnets removed | 22.5 | 16.9 | none | 0.51 |
| 105 | magnets removed | 18.0 | 21.0 | none | 0.71 |

None of the 1278 sweep points makes magnet contact with the corrected or redesigned gaps. What the sweep shows:
- **The best voltage (16–24 V peak) always occurs at the piezo's own resonance, and removing the magnets barely changes it.** Because the piezo f_n is inside the ambient band, it already works as a conventional resonant harvester.
- Plucking adds a narrow second peak at the driver resonance: 3.3–7.9 V physical, about 0.5–1 Hz wide.
- **Off resonance (10 Hz), output is below 1 V for every design.** The poster's "off resonance can constantly reach at least 50 V" is not supported.

---

## Can the corrected design reach 50 V?
**No.**
- **With the physically estimated coupling:** the plucked peak is 3–8 V and the best-case resonant peak is ~24 V, both at 0.2 g.
- **With the poster's own 100 V/mm calibration:** the redesign gives 13–17 V peak at the plucking frequency. Reaching 50 V would take about 0.5 mm of *dynamic* swing at a θ that violates energy conservation.

The poster's 45–148 V manual-pluck readings, if real, came from multi-millimetre hand deflections, far more than any magnet in this geometry can deliver safely.

## Caveats
- **Lumped SDOF models** (static-deflection mode shape, 0.2357 coefficient) and a **single mode** each. The base-participation factor 0.375·µL is an approximation.
- **The point-dipole force law** under-predicts force at d < 2D. The redesign enforces d ≥ 2D, but the poster's original 8 mm gaps with 5 mm magnets are at the edge of validity. Side-by-side (non-coaxial) offsets or tilt from bending are ignored.
- **The section-C EI and the segment lengths are fitted, not derived.** The real bimorph stack gives an 8.5% higher EI_C. The PZT is treated as 10 mm wide for EI (poster convention) but 5 mm wide for C_p and coupling.
- **Coupling θ** is an order-of-magnitude estimate (k₃₁ = 0.34, ε₃₃ᵀ = 1700ε₀, series bimorph, full electrode coverage). The real value could differ by about 2×. A clamped-beam open-circuit measurement with a scope would settle it.
- **Damping** is ζ = 0.015 for both beams. PETG is lossy and could easily be 0.03–0.05, which would halve driver amplitude and break the force-swing criterion. The excitation level is 2 m/s²; check it against the actual source. The poster's Table 1 vehicle values are 0.01–0.2, with units not stated.
- **Contact** is a penalty spring. Captured-magnet behaviour is qualitative only.
- **Not modelled:** PETG creep, magnet-to-beam bonding, the riser block for the redesigned drivers, and gravity sag (the beams' orientation is unclear from Fig. 4).
