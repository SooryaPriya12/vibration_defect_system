"""Compare vibration data with a defect template and grade defect intensity."""
import json
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt, hilbert

def load_template(path):
    with open(path) as f:
        return json.load(f)

def load_vibration(path, fallback_fs):
    """CSV with column 'accel_g' (+ optional 'time' in seconds). Returns (signal, fs)."""
    df = pd.read_csv(path)
    col = "accel_g" if "accel_g" in df.columns else df.columns[-1]
    x = df[col].to_numpy(float)
    fs = fallback_fs
    if "time" in df.columns and len(df) > 1:
        fs = 1.0 / float(np.median(np.diff(df["time"].to_numpy(float))))
    if len(x) < 1024 or not np.isfinite(x).all():
        raise ValueError("Vibration file is too short or contains invalid values.")
    return x, fs

def _spectrum(x, fs):
    w = np.hanning(len(x))
    amp = np.abs(np.fft.rfft((x - x.mean()) * w)) * 2 / w.sum()
    return np.fft.rfftfreq(len(x), 1 / fs), amp

def _peak(f, a, fc, tol):
    m = (f >= fc - tol) & (f <= fc + tol)
    return float(a[m].max()) if m.any() else 0.0

def bearing_freqs(shaft_hz, b):
    r = b["ball_dia_mm"] / b["pitch_dia_mm"] * np.cos(np.radians(b["contact_angle_deg"]))
    n = b["n_balls"]
    return {"BPFO": n / 2 * shaft_hz * (1 - r), "BPFI": n / 2 * shaft_hz * (1 + r)}

def grade(amp, thresholds, levels):
    """Highest level whose threshold is met, else None (no defect)."""
    lvl = None
    for name, t in zip(levels, thresholds):
        if amp >= t:
            lvl = name
    return lvl

def analyze(x, fs, tpl):
    """Returns (list of detected defects, info). Each defect: name, intensity, amplitude, frequency_hz."""
    spec = tpl["specs"]
    f, a = _spectrum(x, fs)
    nom, var = spec["nominal_rpm"], spec["rpm_variation_pct"] / 100
    band = (f >= nom * (1 - var) / 60) & (f <= nom * (1 + var) / 60)   # allowed rpm variation range
    shaft = float(f[band][np.argmax(a[band])])
    base = {"shaft": shaft, **bearing_freqs(shaft, spec["bearing"])}
    lo, hi = spec["envelope_band_hz"]
    sos = butter(4, [lo, min(hi, fs / 2 * 0.95)], btype="band", fs=fs, output="sos")
    env = np.abs(hilbert(sosfiltfilt(sos, x)))
    ef, ea = _spectrum(env, fs)
    found = []
    for d in tpl["defects"]:
        ff, aa = (ef, ea) if d["method"] == "envelope" else (f, a)
        best = max(((_peak(ff, aa, o * base[d["base"]], d["tolerance_hz"]), o * base[d["base"]])
                    for o in d["orders"]), key=lambda t: t[0])
        lvl = grade(best[0], d["thresholds"], tpl["intensity_levels"])
        if lvl:
            found.append({"name": d["name"], "intensity": lvl,
                          "amplitude": round(best[0], 4), "frequency_hz": round(float(best[1]), 2)})
    info = {"shaft_hz": round(shaft, 2), "rpm": round(shaft * 60, 1), "rms_g": round(float(np.sqrt(np.mean(x**2))), 4)}
    return found, info
