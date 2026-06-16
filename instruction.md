# DCE-MRI Pharmacokinetic Parameter Estimation

Estimate pharmacokinetic parameters from a DCE-MRI acquisition. All input data are in `/app/data/`. Write results to `/app/output.json`. You have **1800 seconds**.

---

## Input Data

| File               | Description                                                                                                                                                     |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vfa_mri.nii.gz`   | 4D NIfTI `(32, 32, 1, 5)` - pre-contrast multi-flip-angle SPGR volumes                                                                                          |
| `dce_4d.nii.gz`    | 4D NIfTI `(32, 32, 1, 50)` - dynamic SPGR signal time series                                                                                                    |
| `tumor_roi.nii.gz` | 3D binary NIfTI `(32, 32, 1)` - tumor region mask                                                                                                               |
| `aif.csv`          | Columns: `time_min`, `Ca_mM` - arterial input function (irregularly sampled)                                                                                    |
| `params.json`      | Scan parameters: `TR_ms`, `flip_angle_deg`, `r1_relaxivity_mM_per_s`, `n_timepoints`, `dt_s`, `bolus_arrival_s`, `vfa_flip_angles_deg`, `n_precontrast_volumes` |

---

## Output Schema

```json
{
  "Ktrans": <float>,
  "ve": <float>,
  "kep_min_inv": <float>,
  "fit_rmse_mM": <float>,
  "n_tumor_voxels_used": <int>,
  "ktrans_voxel_median": <float>,
  "ve_voxel_median": <float>,
  "ktrans_ci95": [<float>, <float>],
  "ve_ci95": [<float>, <float>],
  "bootstrap_samples": <int>
}
```

`Ktrans` in min^-1. `kep_min_inv` = Ktrans / ve.
