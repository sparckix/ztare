"""On-demand single-claim adversarial — falsify ONE claim fast, without a full paid run.

The GP-119 inverter normally fires in-loop against the promoted champion thesis. This exposes the SAME
Popper/Munger inversion against a single claim the operator picks: one model call → 2-4 falsification tests,
each with a pre-committed fail criterion. NO side effects — it does not touch the run's inverter_review.json
or inject constraints (that adjudication is the in-loop job). CLI is master; the workbench renders the tests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _brief_evidence_summary(project_dir: Path, limit: int = 1400) -> str:
    """A short slice of the project's compiled evidence to ground the inversion (best-effort, optional)."""
    for name in ("compiled_evidence.txt", "evidence.txt"):
        path = project_dir / name
        if path.exists():
            try:
                return path.read_text(encoding="utf-8", errors="replace")[:limit]
            except Exception:  # noqa: BLE001 — grounding is best-effort
                return ""
    return ""


def falsify_claim(project: str, claim: str, model: str = "", repo_root: Path | None = None) -> dict[str, Any]:
    """Run the inverter against one claim and return its falsification tests (no persistence)."""
    from ztare.validator.inverter_agent import _produce_inverter_review, _default_inverter_model

    repo_root = repo_root or _repo_root()
    project_dir = Path(project) if Path(project).is_absolute() else (repo_root / "projects" / project)
    inverter_model = model or _default_inverter_model()
    review = _produce_inverter_review(
        project_dir=project_dir,
        champion_thesis=claim,
        champion_score=70,  # on-demand: a neutral "worth testing" framing (no in-loop score exists here)
        champion_weakest_point="",
        evidence_summary=_brief_evidence_summary(project_dir),
        inverter_model=inverter_model,
    )
    return {
        "ok": True,
        "project": project,
        "claim": claim,
        "model": inverter_model,
        "tests": review.get("tests", []) if isinstance(review.get("tests"), list) else [],
        "overall_assessment": str(review.get("overall_assessment", "")),
        "confidence_survives": review.get("confidence_the_champion_survives"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare research falsify",
                                     description="Falsify ONE claim on demand (the in-loop inverter, one claim, no full run).")
    parser.add_argument("--project", required=True)
    parser.add_argument("--claim", required=True, help="The claim to stress-test.")
    parser.add_argument("--model", default="", help="Inverter model (default: the configured inverter model).")
    parser.add_argument("--repo", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="Emit the falsification tests as JSON (for the workbench).")
    args = parser.parse_args(argv)
    result = falsify_claim(args.project, args.claim, args.model, args.repo)
    if args.json:
        print(json.dumps(result))
        return 0
    print(f"Claim: {result['claim']}")
    conf = result.get("confidence_survives")
    if conf is not None:
        print(f"Inverter's confidence it survives: {conf}")
    if result.get("overall_assessment"):
        print(f"Assessment: {result['overall_assessment']}")
    for t in result["tests"]:
        head = t.get("popper_test") or t.get("munger_inversion") or "(test)"
        print(f"  • {head}")
        if t.get("fail_criterion"):
            print(f"      fails if: {t['fail_criterion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
