# MagPluck: TSA Engineering Design 2026–27 (Team 10)

MagPluck is a non-contact, magnetically plucked piezoelectric vibration harvester. A soft driver beam (about 16 Hz) acts on a piezoelectric bimorph beam through a pair of attracting magnets, so nothing ever touches the brittle piezo. This repository holds the simulation, the results, the portfolio and the paper.

Everything here is a simulation study. No prototype has been built yet. Section 14 of the results PDF proposes the first experiment.

## What is where

| Path | What it is |
|---|---|
| `deliverables/` | Final files: results PDF, portfolio v9, IEEE paper v3, 90 s simulation demo video |
| `harvester_sim/sim.py` | Main model: re-checks the poster's beam and magnet math, runs the redesign search (2.3 M designs per length), time-domain runs, the 1,278-point frequency sweep and the pull-and-release test |
| `harvester_sim/sim_next.py` | Follow-up studies from the design review (see below) |
| `harvester_sim/plucked_harvester_bench.html` | Interactive bench (sideways view) shown in the video. Open it in a browser |
| `harvester_sim/results/` | Every table (`tables.md`, `next_tables.md`), JSON summaries and run logs |
| `harvester_sim/plots/` | All figures (01–07 from `sim.py`, 11–15 from `sim_next.py`) |
| `harvester_sim/data/` | Recorded car vibration used in Study 4 (CC BY 4.0, see its README) |
| `portfolio/` | Portfolio sources, figures and PDF versions; `results_doc/build.py` builds the results PDF |
| `tools/video/` | Playwright scripts that recorded the demo video and the bench readouts |

## Running it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cd harvester_sim
../.venv/bin/python sim.py        # about 2.5 min
../.venv/bin/python sim_next.py   # about 9 min
cd ../portfolio/results_doc && ../../.venv/bin/python build.py
# then print MagPluck_Simulation_Results.html to PDF (headless Chrome --print-to-pdf)
```

## Headline results (2 m/s², 1 MΩ load, physical coupling estimate)

- The original poster's snap distances were about 2.4× too small. Built as drawn, the magnets latch, and the real force margin is 0.37–0.49×, not 12×.
- The redesign plucks with no contact. Output is 3.3 / 3.6 / 7.9 V peak and about 4 / 5 / 28 µW for the 85 / 95 / 105 mm piezo beams. Gap margin is 1.44–1.50× snap.
- The device works as a magnetically coupled two-mode resonator, not a frequency up-converter.

## Follow-up studies (`sim_next.py`, Sections 10–14 of the results PDF)

1. **Piezo on the driver.** The driver loses about 2.2 mW to damping. A second bimorph placed 2.5–22.5 mm from the driver clamp, kept under 500 µε, adds about 340 µW (105 mm). That is roughly 12× the piezo beam's output, and the biggest single improvement found.
2. **Gain law and optimisation under uncertainty.**
   - The closed-form gain law (paper eq. 20) holds near the current design but over-predicts across the wider design space. The exact linear two-mode model matches the nonlinear simulation (R² 0.90).
   - Re-optimising for median power over 400 Monte Carlo draws, with closest approach ≥ 1.2× snap in 95% of draws, raises the 105 mm median power from about 9 to about 85 µW in the nonlinear check.
3. **Sweep-past magnets.** A finite-size (sub-dipole) force model shows that small magnets sliding past each other give a fast release: ring/pull about 0.95 against 0.54–0.73 for the coaxial layout. Steady power is 2–3× higher, but it is still not up-conversion while the piezo stays at 18–26 Hz.
4. **Recorded vehicle vibration.** On a real cobblestone recording the magnets add 1.03–1.29× power, close to the 1.35× for synthetic noise. The driver bimorph adds 2.2–2.6×.
5. **First experiment.** Predictions for a safe 0.1–0.5 m/s² shaker sweep: mode frequencies, voltages, the voltage dip and power gain for each beam length.

## Credits

The car vibration recording is from Witulska, J., & Wyłomańska, A., *Vibration measurements with observer-declared variance change points* (v1.0.0, CC BY 4.0), https://github.com/witulska/vibration-changepoint-dataset.
