import sys, json, numpy as np
sys.path.insert(0, '../harvester_sim')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sim

NAVY, CORAL, PALE, GREY, INK = '#1F3A68', '#E07A5F', '#F6D3C7', '#9AA3B5', '#2B2F3A'
plt.rcParams.update({'font.family': 'Arial', 'font.size': 9, 'axes.edgecolor': '#8a93a6',
    'axes.labelcolor': INK, 'xtick.color': INK, 'ytick.color': INK, 'axes.spines.top': False,
    'axes.spines.right': False, 'savefig.dpi': 220, 'savefig.bbox': 'tight'})

# ---------- Fig: everyday vibration sources (Roundy et al. 2003, Table 2)
src = [("Person tapping heel", 1, 3), ("Car instrument panel", 13, 3), ("HVAC vents, office", 60, 0.85),
       ("Base of machine tool", 70, 10), ("CD on notebook PC", 75, 0.6), ("Windows by busy road", 100, 0.7),
       ("2nd-floor office floor", 100, 0.2), ("Clothes dryer", 121, 3.5), ("Microwave oven", 121, 2.5),
       ("Door frame after closing", 125, 3), ("Car engine compartment", 200, 12)]
fig, ax = plt.subplots(figsize=(3.6, 2.7))
y = np.arange(len(src))[::-1]
for yi, (n, f, a) in zip(y, src):
    ax.barh(yi, f, color=CORAL if f <= 30 else NAVY, height=0.62)
    ax.text(f + 3, yi, f"{f} Hz", va='center', fontsize=7.5, color=INK)
ax.set_yticks(y); ax.set_yticklabels([s[0] for s in src], fontsize=7.8)
ax.set_xlim(0, 235); ax.set_xlabel("Frequency of strongest vibration (Hz)")
ax.tick_params(axis='y', length=0)
fig.savefig('figs/sources.png'); plt.close(fig)

# ---------- Fig: narrow resonance of a linear harvester (illustrative)
fn, z = 20.0, 0.015
f = np.linspace(10, 30, 2000); r = f / fn
P = r**2 / ((1 - r**2)**2 + (2*z*r)**2); P /= P.max()
fig, ax = plt.subplots(figsize=(3.4, 2.2))
ax.axvspan(15, 25, color=PALE, alpha=0.7, lw=0)
ax.text(15.3, 0.9, "where a car's vibration\ncan wander (example)", fontsize=7.5, color='#a34a33')
ax.plot(f, P*100, color=NAVY, lw=1.8)
bw = 2*z*fn
ax.annotate(f"strong output only\nwithin about {bw:.1f} Hz", xy=(fn + bw/2, 50), xytext=(22.2, 55),
            fontsize=7.5, color=NAVY, arrowprops=dict(arrowstyle='->', color=NAVY, lw=0.8))
ax.set_xlabel("Vibration frequency (Hz)"); ax.set_ylabel("Power (% of peak)")
ax.set_xlim(10, 30); ax.set_ylim(0, 105)
fig.savefig('figs/resonance.png'); plt.close(fig)

# ---------- Simulation sweeps (physical coupling), 85 and 105 mm, with and without magnets

import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    s1, _ = sim.step1()
red = json.load(open('../harvester_sim/results/summary.json'))['redesign']
for r in red:
    r['metrics'] = {k: v for k, v in r['metrics'].items()}
th = sim.coupling_estimates(s1)['th_phys']
F = np.round(np.arange(5, 40.01, 0.25), 2)
plist, thl, fl, tags = [], [], [], []
for i in (0, 2):
    for kind in ('redesign', 'nomag'):
        p = sim.system_params(kind, i, s1, red)
        for f_ in F:
            plist.append(p); thl.append(th[i]); fl.append(f_); tags.append((i, kind))
res = sim.sweep_rk4(plist, thl, fl)
out = {}
for (i, kind), v, c in zip(tags, res['Vpk'], res['contact']):
    out.setdefault(f"{i}_{kind}", []).append(float(v))
json.dump({'F': F.tolist(), **out, 'any_contact': bool(res['contact'].any())}, open('figs/sweep.json', 'w'))
print('contact anywhere:', res['contact'].any())

# plain beam (no magnets), 105 mm
V = np.array(out['2_nomag'])
fig, ax = plt.subplots(figsize=(3.3, 2.2))
ax.plot(F, V, color=NAVY, lw=1.8)
k = np.argmax(V)
ax.annotate(f"{V[k]:.0f} V at {F[k]:.1f} Hz\n(its natural frequency)", xy=(F[k], V[k]), xytext=(24, V[k]*0.8),
            fontsize=7.5, color=NAVY, arrowprops=dict(arrowstyle='->', color=NAVY, lw=0.8))
j = np.argmin(abs(F-10))
ax.annotate(f"{V[j]:.1f} V at 10 Hz", xy=(10, V[j]), xytext=(6, V[k]*0.45), fontsize=7.5, color=CORAL,
            arrowprops=dict(arrowstyle='->', color=CORAL, lw=0.8))
ax.set_xlabel("Vibration frequency (Hz)"); ax.set_ylabel("Peak voltage (V)"); ax.set_xlim(5, 40); ax.set_ylim(0, None)
fig.savefig('figs/plain_sweep.png'); plt.close(fig)

# with vs without magnets, 85 mm
Vm, Vn = np.array(out['0_redesign']), np.array(out['0_nomag'])
fig, ax = plt.subplots(figsize=(3.4, 2.25))
ax.plot(F, Vn, color=GREY, lw=1.5, ls='--', label='same beams, magnets removed')
ax.plot(F, Vm, color=NAVY, lw=1.8, label='with magnets (our design)')
k = np.argmin(abs(F-16.0))
ax.annotate(f"extra working peak\nfrom the pluck: {Vm[k]:.1f} V\nvs {Vn[k]:.1f} V without magnets", xy=(F[k], Vm[k]),
            xytext=(5.6, max(Vm)*0.55), fontsize=7.2, color=CORAL, arrowprops=dict(arrowstyle='->', color=CORAL, lw=0.8))
ax.set_yscale('log'); ax.set_ylim(0.1, 40)
ax.set_xlabel("Vibration frequency (Hz)"); ax.set_ylabel("Peak voltage (V, log scale)"); ax.set_xlim(5, 40)
ax.legend(frameon=False, fontsize=7, loc='upper right')
fig.savefig('figs/magnet_sweep.png'); plt.close(fig)

# single pull & release, 105 mm
p = sim.system_params('redesign', 2, s1, red)
r = sim.pluck_release(p, th[2], tau=0.5/p['fd'])
t = r['t']*1000
fig, (a1, a2) = plt.subplots(2, 1, figsize=(3.5, 2.9), sharex=True, gridspec_kw={'height_ratios': [1.1, 1]})
a1.plot(t, (r['xd'])*1000, color=GREY, lw=1.4, label='driver magnet swings away')
a1.plot(t, (r['xp']-r['x_end'])*1000*5, color=NAVY, lw=1.6, label='piezo beam tip (×5)')
a1.axvline(r['tau']*1000, color=CORAL, lw=0.8, ls=':'); a1.text(r['tau']*1000+5, 5.2, 'release', color=CORAL, fontsize=7.5)
a1.set_ylabel('Tip motion (mm)'); a1.legend(frameon=False, fontsize=6.8, loc='lower right')
a2.plot(t, r['V'], color=CORAL, lw=1.3); a2.set_ylabel('Voltage (V)'); a2.set_xlabel('Time (ms)')
fig.align_ylabels(); fig.savefig('figs/pluck.png'); plt.close(fig)
print('pluck', r['pull']*1e3, r['ring']*1e3, r['Vpk_after'], p['fd'], p['fp'], p['g0'], p['dsnap'])
print('10Hz nomag105', V[j], 'peak', V[k] if False else max(V), F[np.argmax(V)])
print('85: Vm16', Vm[np.argmin(abs(F-16))], 'Vn16', Vn[np.argmin(abs(F-16))], 'max', max(Vm), max(Vn))
