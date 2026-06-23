"""Research Director role extension (GP-172).

Per the Research Director mandate (`org/roles/research_director.md`
and the maintainer-only Research Director role seam),
the Director is responsible for verifying any quantitative claim from
an offline sub-agent or apparatus iteration against published literature
anchors before it enters verified_axioms.json.

This module is the role's executable extension. It is NOT imported by
autoresearch_loop or any apparatus code path. It is loaded only by the
role's runtime — currently a Claude Code session (the human Director
embodied as Claude); in future, an org-OS daemon process bound to the
role definition.

PUBLIC API
----------
The Director invokes:

    from ztare.role_extensions.research_director import triangulate
    summary = triangulate(project_dir, anchors)

`triangulate` evaluates the project's just-promoted form (read from
test_model.py) at each literature anchor, compares to the published
expected value, and returns a verdict dict. Tolerance defaults to 0.13
dex (~35%). Anchors come from the project's rubric under
`research_director_literature_anchors`.

PROCEDURAL TRIGGERS (per RD-1.1-TRIANGULATION mandate)
-------------------------------------------------------
The Director SHOULD invoke triangulate after any of:
  - A champion promotion in the project (raw_score >= 70)
  - An offline sub-agent reports quantitative results
  - A literature claim is being added to verified_axioms

If any anchor disagrees by more than tolerance_dex, the form is
downgraded to UNVERIFIED. Director MUST NOT promote the form to
verified_axioms.external_consistency_checks unless verdict is VERIFIED.
The triangulation record is persisted to
`workspace/research_director_triangulation_<label>.md`.

ARCHITECTURAL BOUNDARY
----------------------
- Apparatus (`src/ztare/validator/autoresearch_loop.py`): substrate-
  agnostic ZTARE loop. Does NOT call triangulate.
- Role extension (this file): substrate-aware logic the Director runs
  as part of its session work.
- Role mandate (`org/roles/research_director.md`): markdown config the
  role reads to know its triggers and rules.
- Rubric (`rubrics/<project>.json`): per-substrate anchors the role
  reads as data.

Future org-OS will run roles as daemons that load this module when the
role's mandate fires a trigger. The module's API is shaped to support
that wiring without changes.
"""
from __future__ import annotations

import importlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_test_model(project_dir: Path):
    """Load the project's test_model.py with a fresh sys.modules entry."""
    project_str = str(project_dir)
    if project_str not in sys.path:
        sys.path.insert(0, project_str)
    if "test_model" in sys.modules:
        del sys.modules["test_model"]
    return importlib.import_module("test_model")


def triangulate(
    project_dir: Path | str,
    anchors: list[dict],
    *,
    tolerance_dex_default: float = 0.13,
) -> dict:
    """Evaluate the project's I_model at each anchor, compare to expected.

    Parameters
    ----------
    project_dir : Path or str
        Project directory containing test_model.py and features.py.
    anchors : list of dict
        Each anchor:
            {
                "label": str,
                "x": float (g_bar in m/s² for gravity substrates),
                "expected_y": float (published reference value),
                "tolerance_dex": float (optional, default 0.13),
                "source": str (citation),
                "features": dict (optional override of feature dict),
                "system_class": str (optional, default "A"),
            }
    tolerance_dex_default : float
        Per-anchor tolerance can override; this is the fallback.

    Returns
    -------
    dict with keys:
        verdict : "VERIFIED" | "LITERATURE_DISAGREEMENT" | "NO_ANCHORS" | error
        anchors : list of per-anchor result dicts
        n_disagreements : int
    """
    project_dir = Path(project_dir)
    if not anchors:
        return {"verdict": "NO_ANCHORS", "anchors": [], "n_disagreements": 0}

    tm = _load_test_model(project_dir)
    I_model = (
        getattr(tm, "I_model", None)
        or getattr(tm, "f", None)
        or getattr(tm, "model", None)
    )
    if I_model is None:
        raise RuntimeError(f"{project_dir}/test_model.py defines no I_model/f/model")

    results: list[dict[str, Any]] = []
    n_disagreements = 0
    for anchor in anchors:
        try:
            features = dict(anchor.get("features") or {})
            features.setdefault("x", float(anchor["x"]))
            features.setdefault("system_class", anchor.get("system_class", "A"))
            expected_y = float(anchor["expected_y"])
            label = anchor.get("label", "<unnamed>")
            source = anchor.get("source", "<no source>")
            tol_dex = float(anchor.get("tolerance_dex", tolerance_dex_default))
            y_pred = float(I_model(features))
            if expected_y > 0 and y_pred > 0:
                log_ratio = math.log10(y_pred / expected_y)
                in_tol = abs(log_ratio) <= tol_dex
            else:
                log_ratio = float("nan")
                in_tol = False
            results.append({
                "label": label,
                "source": source,
                "x": features["x"],
                "expected_y": expected_y,
                "predicted_y": y_pred,
                "log10_ratio": log_ratio,
                "tolerance_dex": tol_dex,
                "in_tolerance": in_tol,
            })
            if not in_tol:
                n_disagreements += 1
        except Exception as exc:  # noqa: BLE001
            results.append({"label": anchor.get("label", "?"), "error": str(exc)})
            n_disagreements += 1

    verdict = "VERIFIED" if n_disagreements == 0 else "LITERATURE_DISAGREEMENT"
    return {"verdict": verdict, "anchors": results, "n_disagreements": n_disagreements}


def write_record(
    project_dir: Path | str,
    summary: dict,
    *,
    label: str | None = None,
) -> Path:
    """Persist a markdown record of a triangulation summary.

    Output: `<project_dir>/workspace/research_director_triangulation_<label>.md`
    """
    project_dir = Path(project_dir)
    workspace = project_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    if label is None:
        label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = workspace / f"research_director_triangulation_{label}.md"

    lines = [
        f"# Research Director triangulation — {label}",
        "",
        f"**Verdict**: {summary['verdict']} ({summary['n_disagreements']}/{len(summary['anchors'])} disagree)",
        f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"**Authority**: RD-1.1-TRIANGULATION (GP-172 mandate)",
        f"**Loaded by**: Research Director role extension (src/ztare/role_extensions/research_director.py)",
        "",
        "| Anchor | x | Expected y | Predicted y | log10(ratio) | Tol (dex) | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in summary["anchors"]:
        if "error" in r:
            lines.append(f"| {r['label']} | ERROR | | | | | {r['error']} |")
            continue
        status = "✓" if r["in_tolerance"] else "✗ DISAGREE"
        lines.append(
            f"| {r['label']} | {r['x']:.3e} | {r['expected_y']:.3e} | "
            f"{r['predicted_y']:.3e} | {r['log10_ratio']:+.3f} | "
            f"±{r['tolerance_dex']} | {status} |"
        )
    lines.append("")
    lines.append("**Source citations:**")
    for r in summary["anchors"]:
        if "source" in r:
            lines.append(f"- **{r['label']}**: {r['source']}")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def validate_gpu_launch_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Validate Director GPU run packets before paid/scientific launch.

    This is the executable counterpart of RD-1.7. It intentionally validates
    metadata, not physics: a caller still has to inspect the referenced parity
    artifact. The point is to prevent orchestration from treating GPU preflight
    as solver validity.
    """

    missing: list[str] = []
    warnings: list[str] = []

    for field in (
        "run_root",
        "batch_label",
        "exact_command",
        "host",
        "expected_device_residency",
        "telemetry_files",
        "hard_admissibility_gates",
        "kill_conditions",
    ):
        if not packet.get(field):
            missing.append(field)

    solver_swap = bool(packet.get("accelerated_solver")) and bool(
        packet.get("reference_solver")
    )
    source_response = bool(packet.get("source_response_run", True))
    instrument_experiment = bool(packet.get("instrument_experiment", False))
    operator_override = bool(packet.get("operator_override_unvalidated_solver", False))
    parity_artifact = packet.get("same_geometry_solver_parity_artifact")

    if solver_swap and source_response and not parity_artifact:
        if instrument_experiment:
            warnings.append(
                "solver parity missing; packet is allowed only as labeled instrument_experiment"
            )
        elif operator_override:
            warnings.append(
                "solver parity missing; packet relies on explicit operator override"
            )
        else:
            missing.append("same_geometry_solver_parity_artifact")

    verdict = "BLOCK" if missing else "ALLOW_WITH_WARNINGS" if warnings else "ALLOW"
    return {
        "verdict": verdict,
        "missing": missing,
        "warnings": warnings,
        "rule": "RD-1.7-SOLVER-PARITY-BEFORE-GPU-SOURCE",
    }


def validate_experiment_launch_contract(
    project_dir: Path | str,
    rubric_path: Path | str,
) -> dict[str, Any]:
    """Validate rubric/project launch contract before recommending ZTARE.

    This is the Research Director's lightweight mirror of the Makefile
    preflight. It catches the class of failure where a rubric advertises a hard
    gate but the project lacks required companion artifacts.
    """

    project_dir = Path(project_dir)
    rubric_path = Path(rubric_path)
    missing: list[str] = []
    warnings: list[str] = []

    if not project_dir.is_dir():
        missing.append(str(project_dir))
    if not rubric_path.is_file():
        missing.append(str(rubric_path))
        rubric: dict[str, Any] = {}
    else:
        rubric = json.loads(rubric_path.read_text())

    for name in ("project_charter.md", "evidence.txt", "thesis.md"):
        if not (project_dir / name).is_file():
            missing.append(str(project_dir / name))
    if not (project_dir / "raw").is_dir():
        missing.append(str(project_dir / "raw"))

    if rubric.get("holdout_hard_gate"):
        for name in ("gate_harness.py", "evidence_holdout.txt"):
            if not (project_dir / name).is_file():
                missing.append(str(project_dir / name))

    mode = str(rubric.get("rubric_mode") or "kepler").lower()
    if mode == "newton":
        dims = rubric.get("dimensions") or []
        gy = [d for d in dims if "generative yield" in str(d.get("name", "")).lower()]
        if not gy:
            missing.append("rubric.dimensions[Generative Yield]")
        elif float(gy[0].get("weight", 0)) < 15:
            missing.append("rubric.dimensions[Generative Yield].weight>=15")
        charter = project_dir / "project_charter.md"
        if charter.is_file() and "secondary observable" not in charter.read_text(errors="ignore").lower():
            missing.append(str(charter) + "::Secondary observable")
    elif mode not in {"kepler", "newton"}:
        missing.append("rubric.rubric_mode in {kepler,newton}")

    if rubric.get("disable_evidence_fit_gate") and not rubric.get("disable_evidence_fit_gate_reason"):
        warnings.append("disable_evidence_fit_gate lacks reason")
    if rubric.get("disable_uniqueness_gap_gate") and not rubric.get("disable_uniqueness_gap_gate_reason"):
        warnings.append("disable_uniqueness_gap_gate lacks reason")

    verdict = "BLOCK" if missing else "ALLOW_WITH_WARNINGS" if warnings else "ALLOW"
    return {
        "verdict": verdict,
        "missing": missing,
        "warnings": warnings,
        "rule": "RD-1.8-RUBRIC-LAUNCH-CONTRACT-PREFLIGHT",
    }


# Future daemon API — uniform across roles. Today the Director (Claude
# Code session) calls triangulate() directly; tomorrow the org-OS daemon
# will call run(trigger, context) and dispatch to the relevant action.
def run(trigger: str, context: dict) -> dict:
    """Daemon-style entry point. Future org-OS uses this; today unused.

    Triggers (per the GP-172 mandate):
      - "champion_promotion": context = {project_dir, anchors, label}
                              → invoke triangulate + write_record
      - "axiom_promotion_request": context = {project_dir, claim, ...}
                                   → invoke triangulate before allow
    """
    if trigger == "champion_promotion":
        summary = triangulate(context["project_dir"], context.get("anchors") or [])
        path = write_record(
            context["project_dir"], summary, label=context.get("label")
        )
        return {"summary": summary, "record": str(path)}
    if trigger == "axiom_promotion_request":
        summary = triangulate(context["project_dir"], context.get("anchors") or [])
        return {"summary": summary, "may_promote": summary["verdict"] == "VERIFIED"}
    if trigger == "gpu_launch_packet":
        return validate_gpu_launch_packet(context["packet"])
    raise ValueError(f"unknown trigger: {trigger}")
