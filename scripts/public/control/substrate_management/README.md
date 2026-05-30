# scripts/public/control/substrate_management/

> **Up:** [control/](../README.md) · [scripts/](../../../README.md)

Substrate state management for clean experiment runs. These two are
inverses: one preserves the current state, the other clears it so a
cross-family rerun cannot inherit the previous champion.

| Script | What it does |
|---|---|
| `freeze_substrate_artifacts.py` | Freeze a substrate's current artifacts into a timestamped `frozen_<ts>/` directory. |
| `reset_substrate_for_cross_family.py` | Move artifacts out so a cross-family rerun starts clean and cannot inherit the existing champion (Bug #45, 2026-04-25). |

## Related

- Used before a cross-family validation run; see [audits/](../../audits/README.md) for the rescoring side.
