# Stream 1 - Defect Detection from Vibration Data

## Run
    pip install -r requirements.txt        # Tkinter ships with Python (Linux: apt install python3-tk)
    python sample_data.py                  # creates demo CSVs in data/samples/
    python main.py                         # login: admin / Admin@123
    python -m unittest tests/test_system.py -v

## Layout
| File | Purpose |
|---|---|
| config/defect_template.json | Machine specs, rpm variation range, defect types, intensity thresholds |
| core/detector.py | FFT + envelope analysis; compares data with template; grades Low/Medium/High/Critical |
| core/db.py | SQLite: users, access_log, analysis_runs (iteration count), defect_events (separate table) |
| core/auth.py | Login, forgot-password (6-digit code, 10 min, single use), password rules |
| core/report.py | Summary by defect type + CSV export for Power BI |
| gui.py / main.py | Login, alerts, report (filter by user / date range / both; expand rows for detail) |

## Detection logic
1. Find shaft speed inside nominal rpm +/- variation range.
2. Spectrum amplitude at 1x (Unbalance), 2x (Misalignment), 3x-5x (Looseness).
3. Envelope spectrum (band-pass 2-4.5 kHz + Hilbert) at BPFO / BPFI computed from bearing specs.
4. Highest threshold reached sets intensity; below the Low threshold = no defect.
Edit thresholds in the JSON only; no code change needed.

## Forgot password email
Set SMTP_HOST, SMTP_USER, SMTP_PASS for real email. Without them the code is written to data/outbox.txt (demo mode).

## Power BI (weeks 9-12)
Report tab -> "Export CSV" -> Power BI Desktop: Get Data > Text/CSV. Suggested visuals: count by defect_type, stacked by intensity, slicers for username and ts.

## Work breakdown status
Weeks 1-4: template + CSV format, thresholds, login/forgot password, schema - done.
Weeks 5-8: multi-defect logic, alerts, access + defect + iteration logging, unit tests - done.
Weeks 9-12: report module and Power BI export - done. Threshold tuning on real plant data, and demo/handover, remain.
