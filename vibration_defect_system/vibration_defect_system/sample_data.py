"""Generate demo vibration CSVs: python sample_data.py"""
import numpy as np, pandas as pd, os
FS, T, RPM = 10000, 4, 1800

def make(unb=0.0, mis=0.0, loose=0.0, bpfo=0.0, bpfi=0.0, rpm=RPM, seed=0):
    rng = np.random.default_rng(seed); t = np.arange(FS * T) / FS; f = rpm / 60
    x = 0.03 * np.sin(2*np.pi*f*t) + 0.02 * rng.standard_normal(t.size)
    x += unb*np.sin(2*np.pi*f*t) + mis*np.sin(2*np.pi*2*f*t) + loose*sum(np.sin(2*np.pi*k*f*t) for k in (3, 4, 5))/3
    r = 7.94/39.04
    for amp, fc in ((bpfo, 4.5*f*(1-r)), (bpfi, 4.5*f*(1+r))):   # 9 balls -> n/2 = 4.5
        if amp:
            tt = np.arange(0, 0.01, 1/FS); burst = amp*np.exp(-tt*900)*np.sin(2*np.pi*3000*tt)
            for k in range(int(T*fc)):
                i = int(k/fc*FS); x[i:i+burst.size] += burst[:x.size-i]
    return t, x

CASES = {"healthy": {}, "unbalance_medium": {"unb": 0.25}, "misalignment_high": {"mis": 0.35},
         "looseness_low": {"loose": 0.2}, "bearing_outer_race": {"bpfo": 1.0, "seed": 1},
         "bearing_inner_critical_plus_unbalance": {"bpfi": 4.0, "unb": 0.1, "seed": 2}}
if __name__ == "__main__":
    os.makedirs("data/samples", exist_ok=True)
    for n, kw in CASES.items():
        t, x = make(**kw); pd.DataFrame({"time": t, "accel_g": x}).to_csv(f"data/samples/{n}.csv", index=False)
    print("Wrote", len(CASES), "files to data/samples/")
