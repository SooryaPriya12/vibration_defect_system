import csv
from collections import defaultdict
RANK = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}

def summarize(rows):
    """-> ({defect_type: {'count','max','by_intensity','events'}}, {intensity: total})."""
    s, tot = {}, defaultdict(int)
    for r in rows:
        g = s.setdefault(r["defect_type"], {"count": 0, "max": "Low", "by_intensity": defaultdict(int), "events": []})
        g["count"] += 1; g["by_intensity"][r["intensity"]] += 1; g["events"].append(r); tot[r["intensity"]] += 1
        if RANK[r["intensity"]] > RANK[g["max"]]: g["max"] = r["intensity"]
    return s, dict(tot)

def export_csv(rows, path):
    """Flat file for Power BI (Get Data > Text/CSV)."""
    cols = ("ts", "username", "machine_id", "defect_type", "intensity", "amplitude", "frequency_hz", "source_file")
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in rows: w.writerow([r[k] for k in cols])
