"""Figure I redrawn in the Plucked Harvester Bench style (same data as magnet_sweep.png)."""
import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fm.fontManager.addfont("/System/Library/Fonts/Menlo.ttc")
d = json.load(open("portfolio/figs/sweep.json"))
F = np.array(d["F"]); on = np.array(d["0_redesign"]); off = np.array(d["0_nomag"])
SHEET, INK, INK2, GRID, RULE, PZT, STEEL, VOLT = "#FAFBF9", "#1C2321", "#5A6561", "#E3E8E4", "#CCD4CF", "#9B2C2C", "#6E7980", "#1D6C88"
plt.rcParams.update({"font.family": "Menlo", "font.size": 8.2})
fig, ax = plt.subplots(figsize=(3.5, 2.35), dpi=300)
fig.patch.set_facecolor(SHEET); ax.set_facecolor(SHEET)
ax.semilogy(F, off, color=STEEL, lw=1.3, ls=(0, (4, 3)), label="magnets removed")
ax.semilogy(F, on, color=PZT, lw=1.6, label="with magnets (MagPluck)")
i = int(np.argmin(abs(F - 16.0)))
ax.annotate(f"pluck peak: {on[i]:.1f} V\nvs {off[i]:.1f} V without", xy=(F[i], on[i]), xytext=(5.6, 9.5),
            color=VOLT, fontsize=7.4, arrowprops=dict(arrowstyle="->", color=VOLT, lw=0.9))
ax.set_xlim(5, 40); ax.set_xlabel("base frequency (Hz)", color=INK2); ax.set_ylabel("peak voltage (V, log)", color=INK2)
ax.grid(True, which="major", color=GRID, lw=0.8); ax.grid(True, which="minor", axis="y", color=GRID, lw=0.4)
for s in ax.spines.values(): s.set_color(RULE)
ax.tick_params(colors=INK2, labelsize=7.4)
ax.legend(loc="lower right", frameon=False, fontsize=7, labelcolor=INK)
fig.tight_layout(pad=0.4)
fig.savefig("portfolio/figs/magnet_sweep_sim.png", facecolor=SHEET)
print("16 Hz:", on[i], off[i], "ratio", on[i]/off[i])
