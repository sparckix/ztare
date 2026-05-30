# scripts/public/utilities/framer/

> **Up:** [utilities/](../README.md) · [scripts/](../../../README.md)

GP-152 Framer MDL verification. The v1.0 to v1.3 patch cycle each had a
math error because the Jacobian term was patched rather than derived;
these two scripts are the from-first-principles checks that settled it.

| Script | What it does |
|---|---|
| `backtest_framer_mdl_v2_vs_v1.py` | v2.0 raw-coordinate BIC vs v1.x framed-coordinate with Jacobian patches, head to head. |
| `verify_v1_3_frame_invariance.py` | Verifies the v1.3 MDL formula with the first-principles BIC coefficient is frame-invariant. |

The older one-shot `test_v2_*` suite was archived to
`scripts/public/_archive/framer_v2_validation_20260517/` (idle,
unreferenced). Re-run these by hand if the framer is revisited.
