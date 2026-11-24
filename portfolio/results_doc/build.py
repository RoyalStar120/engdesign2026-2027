import json, re, html, pathlib
ROOT = pathlib.Path('/Users/sidharth/engineeringdesign2026-2027')
T = {}
cur = None
for line in (ROOT/'harvester_sim/results/tables.md').read_text().splitlines():
    if line.startswith('## '): cur = line[3:].strip(); T[cur] = []; continue
    if cur and line.startswith('|') and not re.match(r'^\|[-| ]+\|$', line):
        T[cur].append([c.strip() for c in line.strip('|').split('|')])
bench = json.loads((ROOT/'harvester_sim/results/bench_readouts.json').read_text())

def fix(s):
    s = html.escape(s)
    for a, b in [('^-1','⁻¹'),('^-3','⁻³'),('^3','³'),('^4','⁴'),('^0.8','^0.8'),('^2','²'),('kappa','κ'),('theta','θ'),('ybar','ȳ'),('uW','µW'),('uJ','µJ'),('&lt;- governs','◂ governs'),('k_series','k<sub>series</sub>')]:
        s = s.replace(a, b)
    s = re.sub(r'\b([fdkFLDhtmX])_([a-z]+)\b', r'\1<sub>\2</sub>', s)
    return s

def table(rows, cols=None, hl=None, cls='', rename=None):
    head, body = rows[0], rows[1:]
    idx = cols if cols is not None else list(range(len(head)))
    names = [ (rename or {}).get(head[i], head[i]) for i in idx]
    out = [f'<table class="t {cls}"><thead><tr>' + ''.join(f'<th>{fix(n)}</th>' for n in names) + '</tr></thead><tbody>']
    for r in body:
        c = ' class="hl"' if hl and hl(r) else ''
        out.append(f'<tr{c}>' + ''.join(f'<td>{fix(r[i])}</td>' for i in idx) + '</tr>')
    return '\n'.join(out) + '</tbody></table>'

def fig(path, cap, w='100%'):
    return f'<figure style="width:{w}"><img src="{path}"><figcaption>{cap}</figcaption></figure>'

P = 'file://' + str(ROOT/'harvester_sim/plots') + '/'
F = 'file://' + str(ROOT/'portfolio/figs') + '/'

# time-domain table, split by theta
sim = T['sim']
simcols = [0,1,3,4,5,6,7,8,10,11,12,13,15]
def sim_rows(th):
    rows = [sim[0]] + [r for r in sim[1:] if r[2] == th]
    for r in rows[1:]:
        r[1] = {'asdrawn':'Poster as drawn','corrected':'Corrected gap','redesign':'Redesign','nomag':'Redesign, magnets removed'}[r[1]]
    return rows
simren = {'f_exc=f_d (Hz)':'Shake f (Hz)','f_p (Hz)':'Piezo f (Hz)','median swing/F_req':'Swing / F_req','full plucks/s':'Plucks / s','P avg (uW)':'Power (uW)','rest gap (mm)':'Rest gap (mm)','min gap (mm)':'Min gap (mm)','snap gap (mm)':'Snap gap (mm)','peak x_d (mm)':'Driver tip (mm)','peak x_p (mm)':'Piezo tip (mm)'}

# sweep split
sw = T['sweep']
def sw_rows(th):
    rows = [sw[0]] + [r[:] for r in sw[1:] if r[2] == th]
    for r in rows[1:]:
        r[1] = {'corrected':'Corrected gap','redesign':'Redesign','nomag':'Redesign, magnets removed'}[r[1]]
    return rows

# bench table
DN = {'asdrawn':'Poster as drawn','corrected':'Corrected gap','redesign':'Redesign'}
def bench_tab(th):
    rows = [['Design','Piezo','Status','Driver f','Piezo f','Cycles / pluck','Min gap','Snap gap','Plucks / s','Piezo tip','V peak','Power']]
    for b in bench:
        if b['theta'] != th: continue
        rows.append([DN[b['design']], f"{b['len']} mm", b['pill'], b['r_fd'], b['r_fp'], b['r_cyc'], b['r_gap'], b['r_snap'], b['r_pl'], b['r_xp'], b['r_vpk'], b['r_p'].replace('µW','uW')])
    return table(rows, hl=lambda r: r[0]=='Redesign' and r[1]=='105 mm', cls='small')

before_after = T['ba']
ba_rows = [['Quantity','85 mm: poster → ours','95 mm: poster → ours','105 mm: poster → ours']]
qs = [r[1] for r in before_after[1:9]]
for q in qs:
    row = [q]
    for L in ['85 mm','95 mm','105 mm']:
        r = next(x for x in before_after[1:] if x[0]==L and x[1]==q)
        row.append(f'{r[2]} → {r[3]}')
    ba_rows.append(row)

# ---- follow-up studies (design review), built from harvester_sim/results/next_*.{md,json}
N = {}
cur = None
for line in (ROOT/'harvester_sim/results/next_tables.md').read_text().replace('|error|', 'abs. error').splitlines():
    if line.startswith('## '): cur = line[3:].strip(); N[cur] = []; continue
    if cur and line.startswith('|') and not re.match(r'^\|[-| ]+\|$', line):
        N[cur].append([c.strip() for c in line.strip('|').split('|')])
J = json.loads((ROOT/'harvester_sim/results/next_summary.json').read_text())
LB = ['85 mm', '95 mm', '105 mm']
dr = J['drv']
rb = {r['config']: r for r in J['robust']}
sp = J['sweep_past']
ex = J['experiment']
veh = J['vehicle']

def vt(road, src, cfg, design, col=4):
    for r in N['vehicle'][1:]:
        if r[0] == road and r[1] == src and r[2] == cfg and r[3] == design:
            return float(r[col])
    return float('nan')

veh_rows = [['Piezo', 'Design', 'Asphalt, recorded (µW)', 'Cobblestone, recorded (µW)', 'Cobblestone, synthetic noise (µW)',
             'Driver PZT strain, cobblestone (µε)']]
for cfg in LB:
    for dsn in ('Magnets removed', 'Redesign (coaxial)', 'Sweep-past', 'Redesign + driver bimorph'):
        stn = next((r[6] for r in N['vehicle'][1:] if r[0] == 'cobblestone' and r[1] == 'recorded' and r[2] == cfg and r[3] == dsn), '-')
        veh_rows.append([cfg, dsn, f"{vt('asphalt','recorded',cfg,dsn):.2f}", f"{vt('cobblestone','recorded',cfg,dsn):.2f}",
                         f"{vt('cobblestone','synthetic noise',cfg,dsn):.2f}", stn])
g_rec = [vt('cobblestone','recorded',c,'Redesign (coaxial)')/vt('cobblestone','recorded',c,'Magnets removed') for c in LB]
g_syn = [vt('cobblestone','synthetic noise',c,'Redesign (coaxial)')/vt('cobblestone','synthetic noise',c,'Magnets removed') for c in LB]
g_asp = [vt('asphalt','recorded',c,'Redesign (coaxial)')/vt('asphalt','recorded',c,'Magnets removed') for c in LB]
bim_x = [vt('cobblestone','recorded',c,'Redesign + driver bimorph')/vt('cobblestone','recorded',c,'Redesign (coaxial)') for c in LB]

def rbv(cfg, name, key):
    return rb[cfg][name][key]

e105 = {a: ex[f'105 mm {a}'] for a in ('0.1', '0.2', '0.3', '0.5')}
exp_rows = [['Piezo', 'a (m/s²)', 'Lower mode, driver peak (Hz)', 'Upper mode, voltage peak (Hz)', 'Theory modes (Hz)', 'Voltage dip (Hz)', 'V peak at f_d, magnets (mV)',
             'V peak at f_d, dummy masses (mV)', 'Power gain at f_d', 'Gain law', 'Driver tip at f_d (mm)', 'Closest gap (mm)']]
for cfg in LB:
    for a in ('0.1', '0.2', '0.3', '0.5'):
        e = ex[f'{cfg} {a}']
        exp_rows.append([cfg, a, f"{e['f_lo']:.1f}", f"{e['f_hi']:.1f}", f"{e['f_lin_lo']:.2f} / {e['f_lin_hi']:.2f}", f"{e['f_dip']:.1f}",
                         f"{e['Vpk_fd']*1e3:.0f}", f"{e['Vpk0_fd']*1e3:.0f}", f"{e['G_fd']:.2f}", f"{e['G_law']:.2f}",
                         f"{e['Xd_fd']*1e3:.2f}", f"{e['gmin']*1e3:.1f}"])

drv_tab = table(N['drv'], cols=[0, 1, 2, 3, 4, 5, 6, 8, 9, 10], cls='small',
                rename={'kappa^2 driver': 'κ² driver', 'P driver bimorph (uW)': 'P driver bimorph (µW)', 'P piezo (uW)': 'P piezo (µW)',
                        'PZT strain (ue)': 'PZT strain (µε)', 'position from clamp (mm)': 'Bimorph position from clamp (mm)'},
                hl=lambda r: r[1].startswith('best'))
law_tab = table(N['law'])
rob_tab = table(N['robust'], cols=[0, 1, 2, 3, 4, 7, 9, 10, 12, 13, 14], cls='small',
                rename={'median P (uW)': 'median P (µW)', 'median P, nonlinear sim (uW)': 'median P, nonlinear (µW)',
                        'median gain, nonlinear sim (48)': 'median gain, nonlinear', 'P nominal (uW)': 'P nominal (µW)'},
                hl=lambda r: r[1] == 'max median power')
rdes_tab = table(N['robust_design'], cls='small', hl=lambda r: r[1] == 'max median power')
sp_tab = table(N['sweep_past'], cols=[0, 1, 2, 3, 5, 6, 8, 9, 10, 12, 13], cls='small',
               rename={'P avg (uW)': 'P avg (µW)'}, hl=lambda r: r[0] == '105 mm' and r[1] == 'most power')
fc_tab = table(N['fcheck'])

sp105 = sp['105 mm']['power']
sps = sp['60 mm piezo + 105 mm driver']['power'] if sp.get('60 mm piezo + 105 mm driver') else None
r105 = rb['105 mm']

NEW_SUMMARY = f'''
<div class="box coral"><h3>After the design review: five follow-up studies</h3>
<ul>
<li><b>Piezo on the driver (Section 10).</b> The driver loses {dr[2]['Pdamp_mW']:.1f} mW to damping at 2 m/s² (105 mm). A second bimorph on the driver, placed where its strain stays under 500 µε, adds {dr[2]['sel']['Pd_uW']:.0f} µW, about {dr[2]['sel']['Pd_uW']/dr[2]['Pp_uW']:.0f}× what the piezo beam makes. This is the biggest single improvement we found.</li>
<li><b>Design under uncertainty (Section 11).</b> The paper's closed-form gain law is only reliable close to our current design. The exact linear two-mode model it comes from matches the full simulation (R² {J['law']['lin']['r2']:.2f}). Searching for the best median result, with assumed spreads in damping, stiffness, magnet strength, gap and coupling, gives a 105 mm design with a median power of {r105['max median power']['td']['medP']:.0f} µW in the full simulation, against {r105['current redesign']['td']['medP']:.0f} µW for the current redesign.</li>
<li><b>Sweep-past magnets (Section 12).</b> With small driver magnets sliding past the piezo magnet, the release is fast (0.05–0.34 piezo periods) and the piezo rings at about 95% of its pull. Steady output at 105 mm rises to {sp105['P_uW']:.0f} µW. Even so, the energy stays at the shaking frequency, so this is still not frequency up-conversion.</li>
<li><b>Recorded car vibration (Section 13).</b> On a real cobblestone recording the magnets add {min(g_rec):.2f}–{max(g_rec):.2f}× power. That is close to the paper's 1.35× for synthetic noise, and far below the 4–5× seen for a pure tone. The driver bimorph adds {min(bim_x):.1f}–{max(bim_x):.1f}× on the same road.</li>
<li><b>First experiment (Section 14).</b> A sweep at 0.1–0.5 m/s² is safe: the closest gap stays above {min(ex[k]['gmin'] for k in ex)*1e3:.0f} mm. The table gives the two mode frequencies, the voltages and the power gain we predict for each beam length.</li>
</ul></div>
'''

NEW_SECTIONS = f'''
<h2 class="pb">10. Follow-up: a piezo on the driver beam</h2>
<p>In the 105 mm design at 2 m/s², the shaking puts about 2.3 mW into the device, and almost all of it is lost as heat in the driver beam ({dr[2]['Pdamp_mW']:.2f} mW in our model; the paper's audit gives 2.1 mW). The piezo beam turns only {dr[2]['Pp_uW']:.0f} µW of it into electricity. So we tested putting the same 40 × 5 mm bimorph on the driver too.</p>
<p>For each placement, the model:</p>
<ul>
<li>recomputes the driver's stiffness as a stepped beam;</li>
<li>estimates its coupling from k<sub>31</sub> and the bimorph's share of bending energy;</li>
<li>adds the bimorph's mass weighted by the bending shape;</li>
<li>re-tunes the dead tip mass so the driver stays at its design frequency;</li>
<li>drives the driver bimorph into its own matched load (about 1.3 MΩ for a 40 mm bimorph, more for shorter ones).</li>
</ul>
<p>The catch is strain. The driver swings about 5 mm, and a bimorph at the clamp would bend to 1,000–1,700 µε, above the roughly 500 µε that PZT survives over many cycles. So the table shows two options for each length: at the clamp with no strain limit, and the best placement that stays under 500 µε.</p>
{drv_tab}
<p class="note">Strain is at the outer PZT surface at the peak driver deflection in steady shaking at 2 m/s², driver frequency. "P piezo" is the original piezo beam's output in the same run.</p>
{fig(P+'11_driver_bimorph.png','<b>Figure 13.</b> Every placement tried: driver-bimorph power against peak PZT strain. Colour is the distance from the clamp. The dotted line is what the piezo beam makes on its own.')}
<div class="box"><h3>What this means for the design</h3>
<p>Even with the strain limit, a bimorph 10–30 mm from the driver clamp makes 200–340 µW, which is 10–80 times the piezo beam's output. The driver is where the energy is. The magnets still help the piezo beam a little, but a two-transducer design (or a single tuned beam with a transducer) would be the better design. The stepped-beam and coupling numbers are estimates, so a measured coupling on a real driver would be the first thing to check.</p></div>

<h2 class="pb">11. Gain law and design under uncertainty</h2>
<p>The "gain" is the power with magnets divided by the power of the same beams with the magnets removed, at the driver's own resonance. Our paper's gain law (eq. 20) gives it in closed form:</p>
<p style="text-align:center">G ≈ (1 + q²) · (Δ / (Δ − k<sub>m</sub>))², with q = k<sub>m</sub> / (2 ζ<sub>d</sub> m<sub>bp</sub> ω<sub>d</sub>²)</p>
<p>Here k<sub>m</sub> = 4C/d<sub>e</sub>⁵ is the magnets' coupling stiffness and Δ = k<sub>p</sub> − m<sub>p</sub>ω<sub>d</sub>². We first checked the law and the exact linear two-mode model it comes from against the full nonlinear simulation on 120 random designs from the search grid:</p>
{law_tab}
<p>The closed-form law is fine near our current design (3.9 against 4.8 simulated for 105 mm). Across the whole design space it is often far too high, because it assumes weak coupling. The exact linear model is accurate (median error {J['law']['lin']['med_err']*100:.0f}%), so we used it as the objective.</p>
<p>We then re-ran the design search with the gap safety factor as an extra variable (1.2–2.5). Each design was scored over 400 random draws, using the paper's spreads:</p>
<ul>
<li>driver damping 0.015–0.05;</li>
<li>piezo damping 0.01–0.03;</li>
<li>both stiffnesses and the magnet constant ±7% (1σ);</li>
<li>gap ±0.5 mm;</li>
<li>coupling θ within a factor of 2.</li>
</ul>
<p>A design is allowed only if its closest approach stays at least 1.2 times the snap gap in 95% of draws. The best designs were then re-checked on 48 draws with the full nonlinear simulation.</p>
{rob_tab}
{rdes_tab}
{fig(P+'12_gain_law_robust.png','<b>Figure 14.</b> Left: the gain law (x) and the exact linear model (o) against the nonlinear simulation. Middle and right: gain and power over 400 draws for the current redesign (dotted), the max-median-gain design (solid) and the max-median-power design (dashed).')}
<div class="box"><h3>What changed and why</h3>
<p>Both optimised designs use a longer, thicker, wider driver with the large magnet and a tighter gap (1.35× snap instead of 1.5×). This raises the magnetic coupling while keeping the closest approach above 1.2× snap in at least 95% of draws. The median gain at 105 mm rises from {r105['current redesign']['medG']:.1f} to {r105['max median gain']['medG']:.1f}, and the median power from {r105['current redesign']['medP']:.0f} to {r105['max median power']['medP']:.0f} µW (linear model).</p>
<p>Maximising gain and maximising power pick different designs. A high gain can come from a weak no-magnet baseline, so <b>median power is the better target</b>. The gain law on its own picks designs that the exact model rates much lower (row "max median gain-law value").</p></div>

<h2 class="pb">12. Sweep-past magnet geometry</h2>
<p>In the current layout the magnets face each other along the shaking direction, so the pull fades slowly as the driver backs away. In a sweep-past layout the two magnets sit side by side across a small sideways gap, and the driver magnet slides past the piezo magnet. The force along the motion then rises, flips sign and dies within a few millimetres, so the release is fast.</p>
<p>Point dipoles are not accurate at a few millimetres, so we built a finite-size force model: each cylinder is split into 300 small dipoles. It agrees with the point-dipole formula far away and is lower up close, as expected for flat magnets:</p>
{fc_tab}
<p>Search: driver magnet 3–8 mm across and 1–3 mm thick (dead mass keeps the driver frequency), gaps 1.5–8 mm, rest offset 0 or 3 mm. Rules applied:</p>
<ul>
<li>the pull must be at least 1.5 × F<sub>req</sub>;</li>
<li>the sideways attraction must stay 1.5 times below the beams' sideways stiffness;</li>
<li>the driver must clear the force peak by 20% of its stroke, so it actually lets go.</li>
</ul>
<p>The 12.7 mm magnets of the coaxial redesign are far too strong here: they drag the piezo along the whole stroke.</p>
{sp_tab}
{fig(P+'13_sweep_past.png','<b>Figure 15.</b> Left: force on the piezo as the driver magnet slides past. Middle: one pass at the driver’s peak speed, so the piezo rings after a fast release. Right: steady power at 2 m/s², coaxial against sweep-past.')}
<div class="box"><h3>Result</h3>
<p>Sweep-past gives the "true pluck" the review asked for in a single pass: release in {sp105['release_over_Tp']:.2f} of a piezo period and ring/pull {sp105['ring_over_pull']:.2f}, against 0.56 and 0.73 for the coaxial layout. It also roughly doubles or triples steady power ({sp105['P_uW']:.0f} µW at 105 mm against 28 µW).</p>
<p>But with the piezo at 18–26 Hz the driver comes back before the ring builds up, so almost all the voltage is still at the shaking frequency and its harmonics. A 60 mm piezo beam at {sps['fp']:.0f} Hz does ring between passes (about 8% of the energy off the shake harmonics), but it is so stiff that the magnets barely move it and the power collapses to {sps['P_uW']:.1f} µW. True up-conversion needs a stiff, high-frequency piezo and a much stronger pluck, which this size of device cannot give safely.</p></div>

<h2 class="pb">13. Recorded vehicle vibration</h2>
<p>Instead of a steady tone, we drove the model with a real car recording: a phone accelerometer on a route with asphalt and cobblestone (Witulska &amp; Wyłomańska, CC BY 4.0). We used the vertical axis, band-passed to 3–45 Hz. Segments:</p>
<ul>
<li>asphalt, 280–306 s: {veh['asphalt']['rms']:.2f} m/s² rms;</li>
<li>cobblestone, 210–270 s: {veh['cobblestone']['rms']:.2f} m/s² rms.</li>
</ul>
<p>For comparison, "synthetic noise" is Gaussian noise with the same band and rms, like the paper's random-vibration test. The phone was inside the car, so this shows the kind of spectrum, not the exact level at a mounting point.</p>
{table(veh_rows, cls='small', hl=lambda r: r[1]=='Redesign + driver bimorph')}
{fig(P+'14_vehicle.png','<b>Figure 16.</b> The car recording, its spectrum with our beam frequencies marked, and the 105 mm piezo voltage on cobblestone with and without magnets.')}
<div class="box"><h3>Result</h3>
<p>The road spectrum is broad, with no strong peak at 16 Hz, so each resonance catches only a slice of it. The magnets add {min(g_rec):.2f}–{max(g_rec):.2f}× on cobblestone (asphalt {min(g_asp):.2f}–{max(g_asp):.2f}×), close to the synthetic-noise result ({min(g_syn):.2f}–{max(g_syn):.2f}×) and to the paper's 1.35×.</p>
<p>No run had magnet contact. The driver bimorph (Section 10 placement) adds {min(bim_x):.1f}–{max(bim_x):.1f}× on the same road, and its peak strain on cobblestone stays at 311–340 µε, under the 500 µε limit. A rougher road or a harder mounting point could still exceed it, so a travel stop is a sensible safeguard.</p></div>

<h2 class="pb">14. Proposed first experiment</h2>
<p>This is the cheapest test of the model, and it is safe: a low-amplitude frequency sweep on a shaker. At 0.5 m/s² the driver tip moves only about {e105['0.5']['Xd_fd']*1e3:.1f} mm (105 mm design), and the closest gap stays above {min(ex[k]['gmin'] for k in ex)*1e3:.0f} mm.</p>
<ol>
<li><b>Ring-down first.</b> Clamp each beam alone and flick it. Measure its natural frequency and damping from the decay (log decrement). Put these into the model before comparing.</li>
<li><b>Sweep with magnets.</b> Mount both beams on the shaker at the design rest gap. Hold a = 0.1, 0.2, 0.3 and 0.5 m/s² (phone or accelerometer on the base) and step 12–30 Hz in 0.1 Hz steps, waiting 5 s at each. Record the piezo voltage amplitude on a scope (1 MΩ input = our load).</li>
<li><b>Sweep with dummy masses.</b> Swap both magnets for non-magnetic slugs of the same mass and repeat. Same mass means the same frequencies, so the ratio is the gain.</li>
<li><b>Compare</b> with the table below.</li>
</ol>
<p>Pass criteria:</p>
<ul>
<li>both mode frequencies within ±0.5 Hz of the re-predicted values (read the lower mode from the driver tip's motion, e.g. slow-motion video against a ruler, because in the 105 mm design it shows only as a shoulder in the voltage);</li>
<li>a voltage dip where the magnets cancel the base shaking (the "Voltage dip" column): this sharp feature is easy to find and is a direct sign of the magnetic coupling;</li>
<li>gain at f<sub>d</sub> within ±30%;</li>
<li>gain the same at every amplitude to within 10% (the model says it barely changes from 0.1 to 0.5 m/s²).</li>
</ul>
{table(exp_rows, cls='small', hl=lambda r: r[0]=='105 mm')}
{fig(P+'15_experiment_prediction.png','<b>Figure 17.</b> Predicted sweep for each beam length: power divided by a², so the curves for different amplitudes overlap if the device behaves linearly. Red: magnets; grey: dummy masses. Dotted lines: theory mode frequencies.')}
<p class="note">The two modes are the magnetically coupled pair: the lower is driver-led, the upper piezo-led. For 105 mm the theory gives {e105['0.1']['f_lin_lo']:.2f} and {e105['0.1']['f_lin_hi']:.2f} Hz (the paper reports 15.97 and 17.64 Hz).</p>
'''

doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>MagPluck Simulation Results</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700&family=Space+Grotesk:wght@500;600&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&display=swap">
<style>
@page {{ size: letter; margin: 0.55in 0.6in 0.6in; @bottom-right {{ content: counter(page); font-family: Outfit, Arial, sans-serif; font-size: 9pt; color: #1F3A68; }} @bottom-left {{ content: "MagPluck · Team 10 · Simulation Results"; font-family: "Source Sans 3", Arial, sans-serif; font-size: 8pt; color: #5D6576; }} }}
:root {{ --navy:#1F3A68; --coral:#C9573A; --coralbg:#FBE9E3; --ink:#24282F; --mute:#5D6576; --rule:#C9D0DE; --tint:#EEF2F8; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:"Source Sans 3",Arial,sans-serif; font-size:10.2pt; line-height:1.38; color:var(--ink); background:#fff; }}
h1 {{ font-family:Outfit,Arial,sans-serif; color:var(--navy); font-size:26pt; font-weight:700; margin:0 0 4px; }}
h2 {{ font-family:Outfit,Arial,sans-serif; color:var(--navy); font-size:14pt; font-weight:600; margin:18px 0 4px; padding-top:6px; border-top:1.6px solid var(--navy); break-after:avoid; }}
h3 {{ font-family:"Space Grotesk",Arial,sans-serif; color:var(--navy); font-size:10.6pt; font-weight:500; margin:10px 0 3px; break-after:avoid; }}
p {{ margin:0 0 6px; max-width:7.2in; }}
ul {{ margin:2px 0 8px; padding-left:18px; }} li {{ margin-bottom:3px; }}
.kicker {{ font-family:Outfit,Arial,sans-serif; font-size:8.5pt; letter-spacing:.09em; text-transform:uppercase; color:var(--coral); font-weight:600; }}
.meta {{ color:var(--mute); font-size:9.5pt; margin-bottom:12px; }}
.box {{ background:var(--tint); border-radius:6px; padding:9px 12px; margin:8px 0 10px; break-inside:avoid; }}
.box.coral {{ background:var(--coralbg); }}
.box h3 {{ margin-top:0; }}
.stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:10px 0 12px; }}
.stat {{ border:1.4px solid var(--navy); border-radius:6px; padding:7px 9px; }}
.stat b {{ display:block; font-family:Outfit,Arial,sans-serif; font-size:17pt; color:var(--navy); line-height:1.1; }}
.stat span {{ font-size:8.4pt; color:var(--mute); }}
table.t {{ width:100%; border-collapse:collapse; font-size:8.6pt; margin:4px 0 4px; break-inside:auto; }}
table.t th {{ font-family:Outfit,Arial,sans-serif; font-weight:600; color:var(--navy); text-align:left; border-bottom:1.6px solid var(--navy); padding:3px 4px; vertical-align:bottom; }}
table.t td {{ border-bottom:1px solid var(--rule); padding:2.6px 4px; vertical-align:top; }}
table.t tr {{ break-inside:avoid; }}
table.t td:first-child {{ white-space:nowrap; }}
.pair {{ display:flex; gap:10px; break-inside:avoid; }} .pair figure {{ margin:6px 0; }}
table.t.small {{ font-size:7.7pt; }}
table.t.small td, table.t.small th {{ padding:2.4px 3px; }}
table.t tr.hl td {{ background:var(--coralbg); }}
table.t tr.hl td:first-child {{ color:var(--coral); font-weight:700; }}
.note {{ font-size:8.4pt; color:var(--mute); margin:2px 0 10px; }}
figure {{ margin:8px auto 10px; break-inside:avoid; }}
figure img {{ width:100%; display:block; border:1px solid var(--rule); }}
figcaption {{ font-size:8.4pt; margin-top:3px; }}
figcaption b {{ font-family:Outfit,Arial,sans-serif; color:var(--navy); font-weight:600; }}
.pb {{ break-before:page; }}
.toc {{ columns:2; font-size:9.6pt; margin:0 0 6px; padding-left:18px; }}
</style></head><body>

<div class="kicker">TSA Engineering Design 2026–27 · Team 10</div>
<h1>MagPluck Simulation Results</h1>
<div class="meta">Every result from our harvester simulation in one place: the hand calculations it checks, the redesign search, the time-domain runs, the frequency sweep, and the readouts from the interactive bench shown in our video.</div>

<div class="stats">
<div class="stat"><b>0.4×</b><span>force margin of the poster design once the snap distance is fixed (poster claimed 12×)</span></div>
<div class="stat"><b>1.61–1.71×</b><span>force margin of our redesign, all three lengths</span></div>
<div class="stat"><b>7.9 V</b><span>peak output, 105 mm redesign at 16.1 Hz, 0.2 g, 1 MΩ</span></div>
<div class="stat"><b>~28 µW</b><span>average power at the same point; no magnet contact</span></div>
</div>

<div class="box"><h3>What the simulation found</h3>
<ul>
<li><b>The poster's snap distances are about 2.4 times too small.</b> Its own formula, d<sub>snap</sub> = (4C/k)<sup>1/5</sup>, gives 13.3 / 14.3 / 15.3 mm, not 5.5 / 6.1 / 6.8 mm. With the right numbers the force margin falls from 12× to 0.37–0.49×.</li>
<li><b>Built as drawn, the magnets snap together and stay stuck</b> at all three lengths. In the simulation the gap closes to about 2 mm and never opens again.</li>
<li><b>Our redesign plucks once every shake cycle with no contact.</b> It uses a stiffer, shorter driver with a larger 12.7 mm magnet. The piezo beam is unchanged. Margin is 1.61–1.71× and the closest gap stays 1.44–1.50× the snap distance.</li>
<li><b>Output is 3.3 / 3.6 / 7.9 V peak</b> for the 85 / 95 / 105 mm piezo beams with a realistic piezo coupling. That is far below the poster's 50 V target. The poster's 100 V/mm calibration would need more electrical energy than the beam stores.</li>
<li><b>Pull and release works:</b> after the driver lets go, the piezo rings at its own frequency with 54–73% of the pull. But in steady shaking the next pluck arrives after only 1.1–1.6 piezo cycles, so the output stays at the shake frequency.</li>
</ul></div>
{NEW_SUMMARY}
<div class="note">Model: two lumped spring–mass cantilevers (driver and piezo), damping ratio 0.015, coaxial magnet force F = C/d⁴ with a contact spring, piezo coupled to a 7.53 nF bimorph and 1 MΩ load. Base shaking is 2 m/s² (about 0.2 g) unless noted. "Physical θ" is our first-principles coupling estimate; "poster θ" is the poster's 50 V at 0.5 mm calibration. Main runs use LSODA; the 1,278-point sweep uses RK4 at 10 µs. The two agree to 0.03%.</div>



<h2 class="pb">1. Beam and magnet numbers</h2>
<p>We rebuilt each step of the poster's beam math. Tables 2 and 5–8 match to within 0.4%.</p>
<h3>Transformed widths (Table 2)</h3>
{table(T['t2'])}
<h3>Neutral axis, I and EI for each section (Tables 3–5)</h3>
{table(T['t345'], cls='small')}
<p class="note">Section C on the poster does not match any real layer stack. We used the poster's EI values to reproduce its tables, and the real bimorph stack (last row) only for the coupling estimate.</p>
<h3>Spring constants (Tables 6–7)</h3>
{table(T['t67'])}
<h3>Natural frequencies (Table 8)</h3>
{table(T['t8'], hl=lambda r: r[0]=='Piezo 105 mm')}
<p class="note">The poster's piezo masses imply a 0.17 g tip magnet, but the identical driver magnet weighs 0.295 g. With the real mass the 105 mm piezo drops to 17.4 Hz, just under the 18 Hz floor.</p>
<h3>Magnet strength (Section 7)</h3>
{table(T['t7'])}

<h2 class="pb">2. Snap distance and force check</h2>
<p>Snap happens when the magnet pull gets stiffer than the beam: 4C/d⁵ = k. We design the closest approach to be 1.5 times this distance. When both beams are free, they act like two springs in series, so the snap gap is a little larger (two-body column).</p>
<h3>Snap distance, corrected (Table 9)</h3>
{table(T['t9'])}
<h3>Force check, corrected (Table 10)</h3>
{table(T['t10'])}
<h3>Poster versus corrected</h3>
{table(ba_rows, cls='small')}
{fig(P+'01_force_vs_gap_snap.png','<b>Figure 1.</b> Magnet force and beam spring force against gap. Where the magnet curve gets steeper than the spring, the magnets snap.')}
{fig(P+'02_before_after.png','<b>Figure 2.</b> Poster numbers next to corrected numbers for each beam length.')}

<h2 class="pb">3. Redesign</h2>
<p>We searched about 2.3 million designs per beam length. Each one had to meet every rule: force margin of at least 1.5 (two-body), closest approach 1.5× the snap gap, driver at 16–30 Hz, piezo at 18–30 Hz with the real magnet mass, gap at least twice the magnet size, and a force swing of at least 1.2× F<sub>req</sub> each cycle. We kept the feasible design closest to the original.</p>
<h3>What changed</h3>
{table(T['redlog'], cls='small')}
<h3>Redesign performance</h3>
{table(T['red'], cols=[0,1,2,3,4,6,7,8,9,10,11,12,13,14], cls='small')}
<p class="note">The driver is now shorter than the piezo by 29 / 55 / 39 mm, so it needs a riser block to put the two magnets at the same height.</p>
{fig(P+'06_margin_vs_parameter.png','<b>Figure 3.</b> How force margin changes as each design variable moves. Dotted segments leave the 16–30 Hz driver band.')}

<h2 class="pb">4. Time-domain runs</h2>
<p>Each run shakes the base at the driver's natural frequency for several seconds. The rest gap is the design gap plus the expected swing. "Captured" means the magnets touch for more than half of the last 0.5 s.</p>
<h3>Physical coupling (our estimate)</h3>
{table(sim_rows('phys'), cols=simcols, cls='small', rename=simren, hl=lambda r: r[1]=='Redesign' and r[0]=='105 mm')}
<h3>Poster coupling (50 V at 0.5 mm)</h3>
{table(sim_rows('poster'), cols=simcols, cls='small', rename=simren)}
<p class="note">Solver check (redesign 85 mm, physical θ): LSODA 3.292 V and RK4 3.292 V; minimum gap 37.186 mm in both.</p>
{fig(P+'03_time_105mm.png','<b>Figure 4.</b> Tip motion, gap and voltage over time, 105 mm piezo, for the poster, corrected and redesigned layouts.')}
{fig(P+'03_time_95mm.png','<b>Figure 5.</b> Same, 95 mm piezo.', '88%')}
{fig(P+'03_time_85mm.png','<b>Figure 6.</b> Same, 85 mm piezo.', '88%')}
{fig(P+'04_fft_upconversion.png','<b>Figure 7.</b> Frequency content of the voltage. Energy sits at the shake frequency and its 2× harmonic, not at the piezo’s own frequency.')}

<h2 class="pb">5. Pull and release</h2>
<p>One pluck on its own: the driver swings in, pulls the piezo, then swings away and lets it ring.</p>
{table(T['pluck_release'], cls='small')}
{fig(P+'07_pluck_release.png','<b>Figure 8.</b> A single pull and release for each redesign. After release the piezo rings at its own frequency and dies out over about 0.4 s.')}
<div class="box"><h3>Why steady shaking does not show the ring-down</h3>
<p>Two things must be true for a visible pluck: the release must be quick compared with one piezo cycle, and the piezo needs several cycles before the next pluck. Raising the piezo frequency helps the second but hurts the first. Getting both would mean breaking the 1.5× snap rule or moving the piezo above the 18–30 Hz band.</p></div>
<div class="pair">{fig(F+'pluck_step1.png','<b>Figure 9.</b> Pluck step 1 in the interactive bench: driver swings close.', '50%')}
{fig(F+'pluck_step3.png','<b>Figure 10.</b> Pluck step 3: driver has swung away and the piezo beam rings.', '50%')}</div>

<h2 class="pb">6. Frequency sweep, 5–40 Hz</h2>
<p>1,278 runs across frequency, design and beam length. None of them made magnet contact with the corrected or redesigned gaps.</p>
<h3>Physical coupling</h3>
{table(sw_rows('phys'), cols=[0,1,3,4,5,6,7], cls='small', hl=lambda r: r[1]=='Redesign' and r[0]=='105 mm')}
<h3>Poster coupling</h3>
{table(sw_rows('poster'), cols=[0,1,3,4,5,6,7], cls='small')}
<ul>
<li>The highest voltage (16–24 V) always comes at the piezo's own resonance, and it is almost the same with the magnets removed.</li>
<li>Plucking adds a narrow second peak at the driver resonance: 3.3–7.9 V, about 0.5–1 Hz wide.</li>
<li>Away from resonance (10 Hz) every design gives less than 1 V.</li>
</ul>
{fig(P+'05_sweep_peakV.png','<b>Figure 11.</b> Peak voltage across the sweep for each design and beam length.')}
{fig(F+'magnet_sweep_sim.png','<b>Figure 12.</b> 85 mm redesign with and without magnets. The pluck peak is 3.6 V with magnets and 0.8 V without.', '80%')}

<h2 class="pb">7. Piezo coupling</h2>
<p>The poster assumes 50 V at 0.5 mm of tip bend. A bimorph with 7.5 nF of capacitance at 50 V holds 9.4 µJ, more than the 2.4–5.5 µJ that bending the beam 0.5 mm stores. Our estimate from the material constants is 5–8 V per mm.</p>
{table(T['coupling'], cls='small')}
<h3>Hand-pluck readings against each calibration</h3>
{table(T['pluck'])}
<p class="note">κ² above 1 means more electrical energy than mechanical energy, which cannot happen. Our physical estimate could be off by about 2×; a clamped-beam scope test would settle it.</p>

<h2>8. Interactive bench readouts</h2>
<p>These are the live readouts from the sideways bench in our video, taken after 9 seconds of running at real-time speed with the base frequency set to the driver's natural frequency and 2 m/s² shaking. They match the Python runs in Section 4 to within a few percent.</p>
<h3>Physical coupling</h3>
{bench_tab('phys')}
<h3>Poster coupling</h3>
{bench_tab('poster')}
<p class="note">Min gap and V peak are over the last 1 s. Power is the average into 1 MΩ.</p>

{NEW_SECTIONS}
<h2 class="pb">15. Limits of the model</h2>
<ul>
<li>Each beam is one lumped spring–mass with one mode.</li>
<li>The point-magnet force law is less accurate closer than two magnet diameters. The redesign keeps the gap above that.</li>
<li>Section C's EI and the segment lengths are fitted to the poster, not measured.</li>
<li>The coupling θ is an estimate and could be off by about 2×.</li>
<li>Damping is 0.015 for both beams. PETG may be lossier (0.03–0.05), which would cut the driver swing.</li>
<li>Contact is a stiff spring, so stuck-magnet behaviour is only roughly right.</li>
<li>Not included: PETG creep, how the magnets are glued on, the riser block, and gravity sag.</li>
<li>The driver-bimorph coupling uses the same k<sub>31</sub> energy-share estimate as the piezo beam, and the 500 µε limit is a common design value for PZT, not a measured one.</li>
<li>The sweep-past model ignores the beams' twisting and sideways motion (it only checks sideways snap), and it treats the two magnets as perfectly lined up along the beams.</li>
<li>The Monte Carlo spreads are judgements, not measurements. The car recording comes from a phone inside the cabin and has no mounting-point transfer function.</li>
</ul>
</body></html>'''
(ROOT/'portfolio/results_doc/MagPluck_Simulation_Results.html').write_text(doc)
print('ok')
