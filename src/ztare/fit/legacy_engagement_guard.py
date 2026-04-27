"""GP-157 v5.0 legacy 1D fit primitive engagement guard.

Two defense-in-depth checks for the legacy `enable_fit_primitive` path
in autoresearch_loop.py, mirroring what Cage v5.0's
`OneDFitEngine.can_handle()` will enforce once Phase 3c lands:

1. **Engagement gate** — refuse to engage when `cage_meta.class` is
   declared and is not "1d". The legacy path's loud-fail stub would
   otherwise overwrite a substrate's authored test_model.py with a
   crash stub, destroying VISIBLE_SET / HOLDOUT_SET / custom I_model.
2. **Stub write target** — when the substrate authored its own
   test_model.py (signaled by `features.py` existing alongside it),
   the loud-fail stub goes to a sidecar `_fit_stub.py`. The substrate's
   authored test_model.py is never overwritten.

Both are also a reflexive lesson from the gp158 ZTARE-on-ZTARE audit:
audit-of-design-prose did not surface this code-level defect because
the legacy path was not the substrate. The guard is small, testable,
and runs deterministically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Any


def should_engage_legacy_1d_fit_primitive(
    *,
    enable_fit_primitive_flag: bool,
    cage_meta: Mapping[str, Any] | None,
) -> tuple[bool, str]:
    """Return (engage, reason).

    Engages iff:
      - rubric flag is True, AND
      - cage_meta is unset OR cage_meta.class is unset OR cage_meta.class == "1d".

    Refuses on declared non-1d classes — the legacy path's loud-fail
    stub would clobber the substrate's authored test_model.py.
    """
    if not enable_fit_primitive_flag:
        return False, "rubric flag enable_fit_primitive is False"

    meta = cage_meta or {}
    declared_class = (meta.get("class") or "").strip().lower()
    if declared_class and declared_class != "1d":
        return False, (
            f"cage_meta.class={declared_class!r} (not '1d'); use "
            f"enable_fit_primitive_features for nd_features substrates, "
            f"or run without a fit primitive for substrates with authored test_model.py"
        )
    return True, "engagement OK"


def resolve_layer3_stub_target(test_model_path: Path) -> tuple[Path, bool]:
    """Return (stub_target_path, would_clobber_authored_substrate).

    SIDECAR ALWAYS (2026-04-25 night): the loud-fail stub now writes to
    `_fit_stub.py` REGARDLESS of features.py presence. Previously the
    sidecar was features.py-conditional, leaving 1D substrates without
    features.py (gp159 / gp160 / gp161 / gp145 / gp146) at risk of
    test_model.py clobbering on FIT_DECLARATION-missing iters. Per
    GP-157 v5.0 panel synthesis, the gate harness imports I_model from
    test_model.py dynamically (gp145/gp154 pattern) — it never imports
    `_fit_stub.py` — so sidecar is always safe. The stub's purpose is
    debug/audit visibility; routing it to a sidecar preserves the
    substrate's authored test_model.py and the mutator's submission.

    The second tuple element is now ALWAYS True when the stub diverts:
    every authored test_model.py is "authored" in the sense that it
    has VISIBLE_SET / HOLDOUT_SET / I_model contract surface that
    must not be overwritten by a debug stub.
    """
    return test_model_path.parent / "_fit_stub.py", True
