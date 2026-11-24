# Recorded vehicle vibration

`car_measurement_08.csv` is measurement 08 from:

Witulska, J., & Wyłomańska, A. (2026). *Vibration measurements with observer-declared variance change points* (Version 1.0.0) [Data set]. https://github.com/witulska/vibration-changepoint-dataset. License: CC BY 4.0.

Related article: Witulska, J., & Wyłomańska, A. (2022). Identification of the structure break point for data with changing variance. *Mathematica Applicanda*, 50(1), 65–106. https://doi.org/10.14708/ma.v50i1.7155

The file is unchanged. It is a smartphone G-force recording from a car (Physics Toolbox Sensor Suite, at most 100 Hz per sensor). Columns: `time_s` (s), `gforce_x/y/z` (g). The route alternates asphalt and cobblestone. The observer-marked segments are asphalt 92.7–103.5, 185.2–198.0 and 280.0–306.2 s, and stone 103.5–138.0 and 198.0–280.0 s. `sim_next.py` uses the z axis, band-passed to 3–45 Hz.
