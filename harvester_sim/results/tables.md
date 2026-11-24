## t2

| Layer | E (GPa) | n | b_tr (mm) recomputed | poster | % diff |
|---|---|---|---|---|---|
| PETG | 2.1 | 1.00 | 10.0 | 10.0 | +0.00 |
| PZT | 66 | 31.43 | 314.3 | 314.3 | -0.00 |
| Cu | 117 | 55.71 | 557.1 | 557.1 | +0.01 |

## t345

| Section / stack | ybar (mm) | poster ybar | I (mm^4) | poster I | EI (N m^2) | poster EI | EI % diff |
|---|---|---|---|---|---|---|---|
| A/D: PETG | 0.500 | 0.5 | 0.833 | 0.833 | 1.750e-03 | 1.750e-03 | +0.0 |
| B: PETG + Cu (inferred, exact match) | 0.966 | 0.966 | 3.444 | 3.444 | 7.233e-03 | 7.232e-03 | +0.0 |
| C cand. 1: PETG + PZT + Cu | 1.118 | 1.023 | 5.900 | 6.959 | 1.239e-02 | 1.461e-02 | -15.2 |
| C cand. 2: PETG + PZT + PZT | 1.148 | 1.023 | 7.048 | 6.959 | 1.480e-02 | 1.461e-02 | +1.3 |
| C cand. 3: symmetric PZT/PETG/PZT | 0.700 | 1.023 | 46.510 | 6.959 | 9.767e-02 | 1.461e-02 | +568.5 |
| C physical: PETG + 5 mm-wide PZT/Cu/PZT bimorph | 1.176 | 1.023 | 7.547 | 6.959 | 1.585e-02 | 1.461e-02 | +8.5 |

## t5cons

| Section | poster I (mm^4) | E_PETG*I | poster EI | EI / EI_PETG |
|---|---|---|---|---|
| A/D | 0.833 | 1.749e-03 | 1.750e-03 | 1.00 |
| B | 3.444 | 7.232e-03 | 7.232e-03 | 4.13 |
| C | 6.959 | 1.461e-02 | 1.461e-02 | 8.35 |

## t67

| Length | k_piezo (N/m) | poster | % diff | L_D tip (mm) | Driver L (mm) | k_driver (N/m) | poster | % diff |
|---|---|---|---|---|---|---|---|---|
| 85 mm | 43.89 | 43.9 | -0.01 | 28.0 | 75 | 12.44 | 12.4 | +0.36 |
| 95 mm | 28.40 | 28.4 | -0.01 | 38.0 | 85 | 8.55 | 8.55 | -0.01 |
| 105 mm | 18.89 | 18.9 | -0.04 | 48.0 | 95 | 6.12 | 6.12 | +0.05 |

## t8

| Cantilever | k (N/m) | m_eff (kg) | poster m_eff | f_n (Hz) | poster f_n | % diff | f_n w/ real magnet mass (Hz) |
|---|---|---|---|---|---|---|---|
| Piezo 85 mm | 43.9 | 0.001215 | 0.001215 | 30.3 | 30.2 | +0.2 | 28.9 |
| Piezo 95 mm | 28.4 | 0.001337 | 0.001337 | 23.2 | 23.2 | -0.0 | 22.2 |
| Piezo 105 mm | 18.9 | 0.001460 | 0.00146 | 18.1 | 18.1 | +0.0 | 17.4 |
| Driver 75 mm | 12.44 | 0.000519 | 0.00052 | 24.6 | 24.6 | +0.2 | 24.6 |
| Driver 85 mm | 8.55 | 0.000549 | 0.000549 | 19.9 | 19.9 | -0.2 | 19.9 |
| Driver 95 mm | 6.12 | 0.000579 | 0.000579 | 16.4 | 16.4 | -0.2 | 16.4 |

## t7

| Quantity | recomputed | poster | % diff |
|---|---|---|---|
| m (A m^2) | 0.04625 | 0.04625 | +0.00 |
| C in F=C/d^4 (N m^4) | 1.2834e-09 | 1.284e-09 | -0.04 |
| magnet mass (g) | 0.295 | - | - |

## t9

| Config | d_snap piezo (mm) | d_snap driver (mm) | d_safe = 1.5 d_snap,drv (mm) | d_snap two-body k_series (mm) | d_safe two-body (mm) |
|---|---|---|---|---|---|
| 85 mm | 10.32 | 13.28 <- governs | 19.9 | 13.96 | 20.9 |
| 95 mm | 11.26 | 14.31 <- governs | 21.5 | 15.09 | 22.6 |
| 105 mm | 12.21 | 15.30 <- governs | 22.9 | 16.18 | 24.3 |

## t10

| Config | F_req (mN) | F_avail (mN) | Margin | Margin (two-body) | static pluck defl. F_avail/k_p (mm) |
|---|---|---|---|---|---|
| 85 mm | 21.9 | 8.16 | 0.37x | 0.30x | 0.186 |
| 95 mm | 14.2 | 6.04 | 0.43x | 0.34x | 0.213 |
| 105 mm | 9.4 | 4.63 | 0.49x | 0.39x | 0.245 |

## ba

| Config | Quantity | Poster | Corrected | % change |
|---|---|---|---|---|
| 85 mm | d_snap piezo (mm) | 4.13 | 10.3 | +150% |
| 85 mm | d_snap driver (mm) | 5.54 | 13.3 | +140% |
| 85 mm | d_safe (mm) | 8.3 | 19.9 | +140% |
| 85 mm | F_req (mN) | 22 | 21.9 | -0% |
| 85 mm | F_avail (mN) | 269 | 8.16 | -97% |
| 85 mm | Margin (x) | 12 | 0.372 | -97% |
| 85 mm | Static pluck deflection (mm) | 6.13 | 0.186 | -97% |
| 85 mm | Implied V at 100 V/mm (V) | 613 | 18.6 | -97% |
| 95 mm | d_snap piezo (mm) | 4.67 | 11.3 | +141% |
| 95 mm | d_snap driver (mm) | 6.14 | 14.3 | +133% |
| 95 mm | d_safe (mm) | 9.2 | 21.5 | +133% |
| 95 mm | F_req (mN) | 14.2 | 14.2 | -0% |
| 95 mm | F_avail (mN) | 179 | 6.04 | -97% |
| 95 mm | Margin (x) | 13 | 0.426 | -97% |
| 95 mm | Static pluck deflection (mm) | 6.3 | 0.213 | -97% |
| 95 mm | Implied V at 100 V/mm (V) | 630 | 21.3 | -97% |
| 105 mm | d_snap piezo (mm) | 5.22 | 12.2 | +134% |
| 105 mm | d_snap driver (mm) | 6.84 | 15.3 | +124% |
| 105 mm | d_safe (mm) | 10.3 | 22.9 | +123% |
| 105 mm | F_req (mN) | 9.5 | 9.45 | -1% |
| 105 mm | F_avail (mN) | 114 | 4.63 | -96% |
| 105 mm | Margin (x) | 12 | 0.49 | -96% |
| 105 mm | Static pluck deflection (mm) | 6.03 | 0.245 | -96% |
| 105 mm | Implied V at 100 V/mm (V) | 603 | 24.5 | -96% |

## redlog

| Config | Parameter | Old | New | Why |
|---|---|---|---|---|
| 85 mm | L_d | 75 mm | 56 mm | sets driver k (k ~ L^-3) and f_d |
| 85 mm | t_d | 1 mm | 1.5 mm | driver k ~ t^3: stiffer driver raises F_avail ~ k^0.8 |
| 85 mm | D_d | 5 mm | 12.7 mm | bigger driver magnet: C ~ m_d m_p, and acts as tip mass so a stiffer driver stays at 16-30 Hz |
| 85 mm | h_d | 2 mm | 8 mm | same as D_d (volume) |
| 85 mm | m_add | 0 g | 2 g | dead tip mass to pull f_d back into band |
| 85 mm | D_p | 5 mm | 6 mm | piezo magnet: C ~ m_p but adds piezo mass (lowers f_p) |
| 85 mm | h_p | 2 mm | 3 mm | same as D_p |
| 95 mm | L_d | 85 mm | 40 mm | sets driver k (k ~ L^-3) and f_d |
| 95 mm | D_d | 5 mm | 12.7 mm | bigger driver magnet: C ~ m_d m_p, and acts as tip mass so a stiffer driver stays at 16-30 Hz |
| 95 mm | h_d | 2 mm | 8 mm | same as D_d (volume) |
| 105 mm | L_d | 95 mm | 66 mm | sets driver k (k ~ L^-3) and f_d |
| 105 mm | t_d | 1 mm | 1.5 mm | driver k ~ t^3: stiffer driver raises F_avail ~ k^0.8 |
| 105 mm | D_d | 5 mm | 12.7 mm | bigger driver magnet: C ~ m_d m_p, and acts as tip mass so a stiffer driver stays at 16-30 Hz |
| 105 mm | h_d | 2 mm | 6 mm | same as D_d (volume) |
| 105 mm | D_p | 5 mm | 4 mm | piezo magnet: C ~ m_p but adds piezo mass (lowers f_p) |

## red

| Config | k_d (N/m) | k_p (N/m) | f_d (Hz) | f_p (Hz) | C (N m^4) | d_safe (mm) | F_req (mN) | F_avail (mN) | Margin (two-body) | Margin (poster rule) | X_rel @f_d (mm) | force swing / F_req | static pluck defl. (mm) | # feasible grid pts | f_p >= 1.1 f_d |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 85 mm | 100.9 | 43.9 | 16.1 | 25.7 | 7.154e-08 | 37.2 | 21.9 | 37.4 | 1.71x | 2.28x | 6.60 | 1.20x | 0.85 | 210 | yes |
| 95 mm | 82.0 | 28.4 | 16.4 | 22.2 | 3.312e-08 | 34.3 | 14.2 | 23.8 | 1.68x | 2.13x | 6.32 | 1.20x | 0.84 | 5575 | yes |
| 105 mm | 61.6 | 18.9 | 16.1 | 18.0 | 1.590e-08 | 32.0 | 9.4 | 15.2 | 1.61x | 2.00x | 6.62 | 1.21x | 0.81 | 3392 | yes |

## sim

| Config | Design | theta | rest gap (mm) | f_exc=f_d (Hz) | f_p (Hz) | min gap (mm) | snap gap (mm) | magnets | median swing/F_req | full plucks/s | peak x_d (mm) | peak x_p (mm) | V peak | V rms | P avg (uW) | |V(f_p)|/|V(f_exc)| |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 85 mm | asdrawn | poster | 11.78 | 24.6 | 28.9 | 1.87 | 14.0 | STUCK (captured) | 0.00 | 0 | 7.72 | 2.245 | 5.86 | 4.15 | 17.21 | 0.00 |
| 85 mm | asdrawn | phys | 11.78 | 24.6 | 28.9 | 1.84 | 14.0 | STUCK (captured) | 0.00 | 0 | 8.08 | 2.606 | 2.70 | 1.84 | 3.40 | 0.01 |
| 95 mm | asdrawn | poster | 14.61 | 19.9 | 22.2 | 1.82 | 15.1 | STUCK (captured) | 0.00 | 0 | 9.82 | 3.027 | 6.92 | 4.89 | 23.88 | 0.05 |
| 95 mm | asdrawn | phys | 14.61 | 19.9 | 22.2 | 1.79 | 15.1 | STUCK (captured) | 0.00 | 0 | 10.78 | 3.990 | 4.56 | 2.90 | 8.40 | 0.05 |
| 105 mm | asdrawn | poster | 18.20 | 16.4 | 17.4 | 1.85 | 16.2 | STUCK (captured) | 0.00 | 0 | 12.39 | 4.104 | 7.88 | 5.56 | 30.89 | - |
| 105 mm | asdrawn | phys | 18.20 | 16.4 | 17.4 | 1.84 | 16.2 | STUCK (captured) | 0.00 | 0 | 15.11 | 6.756 | 8.46 | 5.35 | 28.67 | - |
| 85 mm | corrected | poster | 23.39 | 24.6 | 28.9 | 21.07 | 14.0 | ok | 0.11 | 0 | 1.80 | 0.186 | 5.80 | 4.00 | 15.97 | 0.00 |
| 85 mm | corrected | phys | 23.39 | 24.6 | 28.9 | 21.08 | 14.0 | ok | 0.11 | 0 | 1.47 | 0.524 | 2.57 | 1.80 | 3.23 | 0.00 |
| 95 mm | corrected | poster | 26.87 | 19.9 | 22.2 | 23.09 | 15.1 | ok | 0.17 | 0 | 3.64 | 0.204 | 7.27 | 4.64 | 21.52 | 0.05 |
| 95 mm | corrected | phys | 26.87 | 19.9 | 22.2 | 23.11 | 15.1 | ok | 0.17 | 0 | 2.86 | 1.053 | 4.09 | 2.78 | 7.70 | 0.05 |
| 105 mm | corrected | poster | 30.85 | 16.4 | 17.4 | 24.73 | 16.2 | ok | 0.26 | 0 | 6.02 | 0.215 | 8.01 | 5.10 | 26.01 | - |
| 105 mm | corrected | phys | 30.85 | 16.4 | 17.4 | 24.88 | 16.2 | ok | 0.25 | 0 | 4.26 | 2.697 | 7.68 | 5.10 | 26.00 | - |
| 85 mm | redesign | poster | 43.78 | 16.1 | 25.7 | 37.40 | 24.8 | ok | 1.07 | 14 | 5.71 | 0.780 | 16.69 | 9.57 | 91.51 | 0.00 |
| 85 mm | redesign | phys | 43.78 | 16.1 | 25.7 | 37.19 | 24.8 | ok | 1.13 | 15 | 5.61 | 1.045 | 3.29 | 1.96 | 3.84 | 0.01 |
| 95 mm | redesign | poster | 40.66 | 16.4 | 22.2 | 34.39 | 22.9 | ok | 1.12 | 14 | 5.67 | 0.721 | 14.57 | 8.21 | 67.33 | 0.00 |
| 95 mm | redesign | phys | 40.66 | 16.4 | 22.2 | 33.95 | 22.9 | ok | 1.23 | 16 | 5.43 | 1.370 | 3.60 | 2.31 | 5.34 | 0.01 |
| 105 mm | redesign | poster | 38.59 | 16.1 | 18.0 | 31.96 | 21.3 | ok | 1.14 | 14 | 6.14 | 0.644 | 12.93 | 7.20 | 51.82 | - |
| 105 mm | redesign | phys | 38.59 | 16.1 | 18.0 | 30.79 | 21.3 | ok | 1.46 | 16 | 5.16 | 3.140 | 7.92 | 5.27 | 27.78 | - |
| 85 mm | nomag | poster | 43.78 | 16.1 | 25.7 | 37.31 | 24.8 | ok | 0.00 | 0 | 6.52 | 0.070 | 4.22 | 2.99 | 8.96 | 0.00 |
| 85 mm | nomag | phys | 43.78 | 16.1 | 25.7 | 37.27 | 24.8 | ok | 0.00 | 0 | 6.52 | 0.171 | 0.84 | 0.59 | 0.35 | 0.00 |
| 95 mm | nomag | poster | 40.66 | 16.4 | 22.2 | 34.45 | 22.9 | ok | 0.00 | 0 | 6.25 | 0.077 | 4.75 | 3.35 | 11.25 | 0.00 |
| 95 mm | nomag | phys | 40.66 | 16.4 | 22.2 | 34.41 | 22.9 | ok | 0.00 | 0 | 6.25 | 0.334 | 1.28 | 0.89 | 0.79 | 0.00 |
| 105 mm | nomag | poster | 38.59 | 16.1 | 18.0 | 32.08 | 21.3 | ok | 0.00 | 0 | 6.58 | 0.092 | 5.60 | 3.97 | 15.77 | - |
| 105 mm | nomag | phys | 38.59 | 16.1 | 18.0 | 32.09 | 21.3 | ok | 0.00 | 0 | 6.58 | 1.256 | 3.69 | 2.39 | 5.71 | - |

## xcheck

Solver cross-check (redesign 85 mm, physical theta): LSODA Vpk = 3.292 V, RK4(dt=1e-05) Vpk = 3.292 V; min gap 37.186 vs 37.186 mm

## sweep

| Config | Design | theta | f at max V (Hz) | max V peak | f range with full plucks & no contact (Hz) | # sweep pts with magnet contact | V peak @10 Hz |
|---|---|---|---|---|---|---|---|
| 85 mm | corrected | poster | 40.0 | 9.4 | none | 0 | 2.75 |
| 85 mm | corrected | phys | 28.5 | 15.9 | none | 0 | 0.36 |
| 95 mm | corrected | poster | 40.0 | 11.6 | none | 0 | 3.87 |
| 95 mm | corrected | phys | 22.0 | 19.4 | none | 0 | 0.53 |
| 105 mm | corrected | poster | 36.0 | 11.7 | none | 0 | 5.01 |
| 105 mm | corrected | phys | 17.5 | 20.8 | none | 0 | 0.79 |
| 85 mm | redesign | poster | 16.0 | 18.4 | 16.0-16.0 | 0 | 3.02 |
| 85 mm | redesign | phys | 25.5 | 17.5 | 16.0-16.0 | 0 | 0.52 |
| 95 mm | redesign | poster | 16.5 | 13.3 | none | 0 | 3.68 |
| 95 mm | redesign | phys | 21.5 | 18.1 | 16.5-16.5 | 0 | 0.60 |
| 105 mm | redesign | poster | 16.0 | 11.9 | 16.0-16.0 | 0 | 4.60 |
| 105 mm | redesign | phys | 17.5 | 23.7 | 16.0-17.5 | 0 | 0.81 |
| 85 mm | nomag | poster | 40.0 | 12.2 | none | 0 | 3.32 |
| 85 mm | nomag | phys | 26.0 | 17.3 | none | 0 | 0.43 |
| 95 mm | nomag | poster | 40.0 | 11.5 | none | 0 | 3.92 |
| 95 mm | nomag | phys | 22.5 | 16.9 | none | 0 | 0.51 |
| 105 mm | nomag | poster | 37.5 | 11.5 | none | 0 | 4.80 |
| 105 mm | nomag | phys | 18.0 | 21.0 | none | 0 | 0.71 |

## pluck

| tip defl. (mm) | measured (V) | poster-calib. 100 V/mm | % err | physical theta 85 mm (V) |
|---|---|---|---|---|
| 0.45 | 45 | 45 | +0 | 3.7 |
| 1.0 | 74 | 100 | +35 | 8.1 |
| 1.5 | 148 | 150 | +1 | 12.2 |

## coupling

| Config | theta poster (N/V) | kappa^2 poster | theta physical (N/V) | kappa^2 physical | V/mm physical | U_mech @0.5mm (uJ) | U_elec @50V (uJ) |
|---|---|---|---|---|---|---|---|
| 85 mm | 7.53e-04 | 1.71 | 6.11e-05 | 0.0113 | 8.1 | 5.49 | 9.41 |
| 95 mm | 7.53e-04 | 2.65 | 4.69e-05 | 0.0103 | 6.2 | 3.55 | 9.41 |
| 105 mm | 7.53e-04 | 3.98 | 3.61e-05 | 0.0092 | 4.8 | 2.36 | 9.41 |

## pluck_release

| Config | f_d (Hz) | f_p (Hz) | f_p/f_d (piezo cycles per pluck) | release time (ms) | release / T_p | pull (mm) | free ring after release (mm) | ring / pull | V_pk after release |
|---|---|---|---|---|---|---|---|---|---|
| 85 mm | 16.1 | 25.7 | 1.60 | 31 | 0.80 | 0.69 | 0.37 | 0.54 | 2.36 |
| 95 mm | 16.4 | 22.2 | 1.35 | 30 | 0.68 | 0.69 | 0.44 | 0.64 | 2.28 |
| 105 mm | 16.1 | 18.0 | 1.12 | 31 | 0.56 | 0.70 | 0.51 | 0.73 | 1.78 |

