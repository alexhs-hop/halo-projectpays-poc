"""Reference (oracle) solution: quantitative DCE-MRI pharmacokinetic estimation.

Pipeline:
  1. VFA T10 mapping  - per-voxel SPGR linearization across 5 flip angles.
  2. SPGR inversion   - convert dynamic signal to tissue concentration Ct(t).
  3. AIF preparation  - read whole-blood arterial Ca, convert to plasma
                        Cp = Ca/(1-Hct) with the standard population
                        haematocrit (not provided in params), then cubic-spline
                        onto a high-resolution grid.
  4. Extended Tofts   - non-linear least squares for Ktrans, ve, Vp (the plasma
                        volume term keeps Ktrans/ve unbiased even though Vp is
                        not part of the requested output).
  5. Robust summary   - voxelwise medians + bootstrap 95% CIs.
"""

import json

import numpy as np
import nibabel as nib
from scipy.optimize import curve_fit
from scipy.interpolate import CubicSpline

# ---------------------------------------------------------------------------
# Load inputs
# ---------------------------------------------------------------------------
roi = nib.load("/app/data/tumor_roi.nii.gz").get_fdata().astype(bool)
with open("/app/data/params.json") as fh:
    p = json.load(fh)

TR_ms = float(p["TR_ms"])
r1 = float(p["r1_relaxivity_mM_per_s"])
fa_deg = float(p["flip_angle_deg"])
# The AIF is whole-blood arterial concentration; params.json does not provide a
# haematocrit, so apply the standard population value by convention.
hct = 0.42

# ---------------------------------------------------------------------------
# Phase 1: VFA T10 mapping
# ---------------------------------------------------------------------------
vfa = nib.load("/app/data/vfa_mri.nii.gz").get_fdata()[roi, :]  # (N, 5)
vfa_angles = np.radians(np.array(p["vfa_flip_angles_deg"]))
Y = vfa / np.sin(vfa_angles)
X = vfa / np.tan(vfa_angles)
mX = X.mean(axis=1, keepdims=True)
mY = Y.mean(axis=1, keepdims=True)
slope = np.sum((X - mX) * (Y - mY), axis=1) / np.sum((X - mX) ** 2, axis=1)
intercept = np.squeeze(mY) - slope * np.squeeze(mX)
E10 = np.clip(slope, 1e-9, 1 - 1e-9)
T10_ms = -TR_ms / np.log(E10)
S0 = intercept / (1.0 - E10)

# ---------------------------------------------------------------------------
# Phase 2: dynamic signal -> tissue concentration
# ---------------------------------------------------------------------------
dce = nib.load("/app/data/dce_4d.nii.gz").get_fdata()[roi, :]  # (N, 50)
fa = np.radians(fa_deg)
S0c = S0[:, None]
R = dce / S0c
E1 = np.clip((np.sin(fa) - R) / (np.sin(fa) - R * np.cos(fa)), 1e-9, 1 - 1e-9)
R1_t = -np.log(E1) / (TR_ms / 1000.0)
R10 = (1000.0 / T10_ms)[:, None]
Ct = np.maximum((R1_t - R10) / r1, 0.0)  # (N, 50)
Ct_mean = Ct.mean(axis=0)

# ---------------------------------------------------------------------------
# Phase 3: AIF -> plasma, spline to high-res grid
# ---------------------------------------------------------------------------
aif = np.loadtxt("/app/data/aif.csv", delimiter=",", skiprows=1)
aif_t_min = aif[:, 0]
Ca = aif[:, 1]
Cp = Ca / (1.0 - hct)  # whole-blood arterial -> plasma
spline = CubicSpline(aif_t_min, Cp, bc_type="natural", extrapolate=False)

t_scan = np.arange(p["n_timepoints"]) * float(p["dt_s"])  # seconds
dt_hi = 0.1
t_hi_s = np.arange(0.0, t_scan[-1] + dt_hi, dt_hi)
t_hi_min = t_hi_s / 60.0
Cp_hi = np.nan_to_num(spline(t_hi_min), nan=0.0)
Cp_scan = np.nan_to_num(spline(t_scan / 60.0), nan=0.0)


def conv(ktrans, ve):
    kep = ktrans / ve
    out = np.zeros(len(t_scan))
    dt_min = dt_hi / 60.0
    for n, ts in enumerate(t_scan):
        m = int(round(ts / dt_hi))
        tau = t_hi_min[: m + 1]
        y = Cp_hi[: m + 1] * np.exp(-kep * (ts / 60.0 - tau))
        if len(y) >= 2:
            out[n] = (0.5 * y[0] + y[1:-1].sum() + 0.5 * y[-1]) * dt_min
    return out


def model(_t, ktrans, ve, vp):
    return vp * Cp_scan + ktrans * conv(ktrans, ve)


# ---------------------------------------------------------------------------
# Phase 4: Extended Tofts fit (mean curve)
# ---------------------------------------------------------------------------
def fit(y, p0=(0.1, 0.2, 0.03), maxfev=20000):
    popt, _ = curve_fit(model, t_scan, y, p0=p0,
                        bounds=([0, 0.01, 0], [5, 1, 0.5]), maxfev=maxfev)
    return float(popt[0]), float(popt[1]), float(popt[2])


Ktrans, ve, Vp = fit(Ct_mean)
kep = Ktrans / ve
Ct_pred = model(t_scan, Ktrans, ve, Vp)
rmse = float(np.sqrt(np.mean((Ct_pred - Ct_mean) ** 2)))

# ---------------------------------------------------------------------------
# Phase 5: voxelwise medians + bootstrap CIs
# ---------------------------------------------------------------------------
vk, vv = [], []
for ct in Ct:
    try:
        ki, vei, _ = fit(ct, p0=(Ktrans, ve, Vp), maxfev=10000)
        vk.append(ki)
        vv.append(vei)
    except Exception:
        pass
vk = np.array(vk)
vv = np.array(vv)

rng = np.random.default_rng(2026)
bk, bv = [], []
for _ in range(200):
    sel = rng.integers(0, Ct.shape[0], size=Ct.shape[0])
    try:
        ki, vei, _ = fit(Ct[sel].mean(axis=0), p0=(Ktrans, ve, Vp), maxfev=10000)
        bk.append(ki)
        bv.append(vei)
    except Exception:
        pass
bk = np.array(bk)
bv = np.array(bv)
k_ci = np.quantile(bk, [0.025, 0.975]).tolist()
v_ci = np.quantile(bv, [0.025, 0.975]).tolist()

out = {
    "Ktrans": round(Ktrans, 6),
    "ve": round(ve, 6),
    "kep_min_inv": round(kep, 6),
    "fit_rmse_mM": round(rmse, 8),
    "n_tumor_voxels_used": int(Ct.shape[0]),
    "ktrans_voxel_median": round(float(np.median(vk)), 6),
    "ve_voxel_median": round(float(np.median(vv)), 6),
    "ktrans_ci95": [round(float(k_ci[0]), 6), round(float(k_ci[1]), 6)],
    "ve_ci95": [round(float(v_ci[0]), 6), round(float(v_ci[1]), 6)],
    "bootstrap_samples": int(len(bk)),
}
with open("/app/output.json", "w") as fh:
    json.dump(out, fh, indent=2)

print(json.dumps(out, indent=2))
