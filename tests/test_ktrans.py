"""Verifier for DCE-MRI Ktrans / ve / Vp estimation."""

import json
import os

# Ground-truth values (hidden from agent)
_KTRANS_TRUE = 0.25
_VE_TRUE = 0.30
_KTRANS_REL_TOL = 0.22
_VE_REL_TOL = 0.15
_N_TUMOR_VOXELS_TRUE = 36


def _load_output():
    path = "/app/output.json"
    assert os.path.isfile(path), f"Output file not found: {path}"
    with open(path) as fh:
        return json.load(fh)


def test_output_file_exists():
    """output.json must be present at /app/output.json."""
    _load_output()


def test_required_keys_present():
    """output.json must contain all required keys."""
    data = _load_output()
    required = {
        "Ktrans",
        "ve",
        "kep_min_inv",
        "fit_rmse_mM",
        "n_tumor_voxels_used",
        "ktrans_voxel_median",
        "ve_voxel_median",
        "ktrans_ci95",
        "ve_ci95",
        "bootstrap_samples",
    }
    missing = sorted(required - set(data.keys()))
    assert not missing, f"Missing required keys: {missing}. Found: {list(data.keys())}"


def test_ktrans_in_range():
    """Ktrans must be within tolerance of ground truth."""
    data = _load_output()
    ktrans = float(data["Ktrans"])
    lo = _KTRANS_TRUE * (1.0 - _KTRANS_REL_TOL)
    hi = _KTRANS_TRUE * (1.0 + _KTRANS_REL_TOL)
    assert lo <= ktrans <= hi, (
        f"Ktrans = {ktrans:.6f} min^-1 is outside acceptable range "
        f"[{lo:.4f}, {hi:.4f}]"
    )


def test_ve_in_range():
    """ve must be within tolerance of ground truth."""
    data = _load_output()
    ve = float(data["ve"])
    lo = _VE_TRUE * (1.0 - _VE_REL_TOL)
    hi = _VE_TRUE * (1.0 + _VE_REL_TOL)
    assert lo <= ve <= hi, (
        f"ve = {ve:.6f} is outside acceptable range [{lo:.4f}, {hi:.4f}]"
    )


def test_kep_consistency():
    """kep_min_inv must be numerically consistent with Ktrans/ve."""
    data = _load_output()
    ktrans = float(data["Ktrans"])
    ve = float(data["ve"])
    kep = float(data["kep_min_inv"])
    expected = ktrans / ve
    assert abs(kep - expected) <= 1e-4, (
        f"kep inconsistency: reported={kep:.6f}, expected={expected:.6f}"
    )


def test_rmse_is_small():
    """Model fit RMSE must be below the noise-limited ceiling for SPGR-derived Ct.

    The concentration curves are inverted from SPGR signals carrying mild Rician
    noise, which sets a small realistic floor on the mean-curve RMSE. The ceiling
    rejects catastrophically wrong fits while accepting any correctly implemented
    signal-to-concentration pipeline.
    """
    data = _load_output()
    rmse = float(data["fit_rmse_mM"])
    assert 0.0 <= rmse <= 0.15, f"fit_rmse_mM too large: {rmse:.8f}"


def test_voxel_count_is_correct():
    """Number of tumor voxels used should match hidden ROI voxel count."""
    data = _load_output()
    n_vox = int(data["n_tumor_voxels_used"])
    assert n_vox == _N_TUMOR_VOXELS_TRUE, (
        f"n_tumor_voxels_used={n_vox} expected {_N_TUMOR_VOXELS_TRUE}"
    )


def test_voxelwise_medians_are_reasonable():
    """Voxelwise median parameters should match the physiological ground truth."""
    data = _load_output()
    k_med = float(data["ktrans_voxel_median"])
    ve_med = float(data["ve_voxel_median"])
    assert 0.205 <= k_med <= 0.295, f"ktrans_voxel_median out of range: {k_med:.6f}"
    assert 0.255 <= ve_med <= 0.345, f"ve_voxel_median out of range: {ve_med:.6f}"


def test_bootstrap_metadata():
    """Bootstrap metadata should indicate a meaningful resampling run."""
    data = _load_output()
    n_boot = int(data["bootstrap_samples"])
    assert 50 <= n_boot <= 2000, f"bootstrap_samples out of range: {n_boot}"


def test_ktrans_ci95_validity():
    """Ktrans CI must be non-inverted, bounded, and contain the fitted estimate."""
    data = _load_output()
    lo, hi = data["ktrans_ci95"]
    k = float(data["Ktrans"])
    lo = float(lo)
    hi = float(hi)
    assert lo <= hi, f"Invalid ktrans_ci95 ordering: [{lo}, {hi}]"
    assert lo <= k <= hi, f"Ktrans {k:.6f} not inside ktrans_ci95 [{lo:.6f}, {hi:.6f}]"
    assert (hi - lo) <= 0.12, f"ktrans_ci95 width too large: {hi - lo:.6f}"


def test_ve_ci95_validity():
    """ve CI must be non-inverted, bounded, and contain the fitted estimate."""
    data = _load_output()
    lo, hi = data["ve_ci95"]
    ve = float(data["ve"])
    lo = float(lo)
    hi = float(hi)
    assert lo <= hi, f"Invalid ve_ci95 ordering: [{lo}, {hi}]"
    assert lo <= ve <= hi, f"ve {ve:.6f} not inside ve_ci95 [{lo:.6f}, {hi:.6f}]"
    assert (hi - lo) <= 0.12, f"ve_ci95 width too large: {hi - lo:.6f}"
