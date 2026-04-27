from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


CONSTRAINT_SEVERITIES = {"blocking", "degrading", "enriching"}
CONSTRAINT_PRODUCERS = {
    "meta_judge",
    "verification_gate",
    "adjudicator",
    "inferred",
    "structural_extractor",
    "trajectory_extractor",
    "negative_space_extractor",
}
DEFAULT_NON_APPLICABILITY = (
    "Only non-applicable when the thesis no longer makes this class of claim."
)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_constraint_severity(value: Any) -> str:
    normalized = _clean_text(value).lower()
    return normalized if normalized in CONSTRAINT_SEVERITIES else "degrading"


def _normalize_constraint_producer(value: Any) -> str:
    normalized = _clean_text(value).lower()
    return normalized if normalized in CONSTRAINT_PRODUCERS else "meta_judge"


def _normalize_failure_family(value: Any) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", _clean_text(value).lower()).strip("_")
    return normalized or "other"


def build_constraint_proposal(
    *,
    constraint: Any,
    applies_to: Any,
    failure_family: Any,
    severity: Any = "degrading",
    producer: Any = "meta_judge",
    rationale: Any = "",
    non_applicability_condition: Any = "",
) -> dict[str, str]:
    constraint_text = _clean_text(constraint) or "unspecified constraint"
    applies_to_text = _clean_text(applies_to) or "project scope"
    failure_family_text = _normalize_failure_family(failure_family)
    rationale_text = _clean_text(rationale) or constraint_text
    non_applicability_text = (
        _clean_text(non_applicability_condition) or DEFAULT_NON_APPLICABILITY
    )
    return {
        "constraint": constraint_text,
        "applies_to": applies_to_text,
        "failure_family": failure_family_text,
        "severity": _normalize_constraint_severity(severity),
        "producer": _normalize_constraint_producer(producer),
        "rationale": rationale_text,
        "non_applicability_condition": non_applicability_text,
    }


def proposal_signature(proposal: dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            "constraint": _clean_text(proposal.get("constraint", "")).lower(),
            "applies_to": _clean_text(proposal.get("applies_to", "")).lower(),
            "failure_family": _normalize_failure_family(proposal.get("failure_family", "")),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def sanitize_constraint_proposals(raw_constraints: Any) -> list[dict[str, str]]:
    if not isinstance(raw_constraints, list):
        return []
    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw_constraints:
        if not isinstance(item, dict):
            continue
        proposal = build_constraint_proposal(
            constraint=item.get("constraint"),
            applies_to=item.get("applies_to"),
            failure_family=item.get("failure_family"),
            severity=item.get("severity", "degrading"),
            producer=item.get("producer", "meta_judge"),
            rationale=item.get("rationale", ""),
            non_applicability_condition=item.get("non_applicability_condition", ""),
        )
        signature = proposal_signature(proposal)
        if signature in seen:
            continue
        seen.add(signature)
        cleaned.append(proposal)
    return cleaned


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _empty_ledger(project: str, confirmation_threshold_runs: int) -> dict[str, Any]:
    return {
        "project": project,
        "updated_on": _now_iso(),
        "confirmation_threshold_runs": confirmation_threshold_runs,
        "confirmed_constraint_count": 0,
        "provisional_constraint_count": 0,
        "confirmed_constraints": [],
        "provisional_constraints": [],
    }


def _source_example_key(example: dict[str, Any]) -> tuple[int | None, int | None]:
    return (
        int(example.get("run_id")) if example.get("run_id") is not None else None,
        int(example.get("iteration_index")) if example.get("iteration_index") is not None else None,
    )


def update_derived_constraints_ledger(
    *,
    project: str,
    ledger_path: Path,
    proposals: list[dict[str, Any]],
    run_id: int,
    iteration_index: int,
    source_score: int | None,
    weakest_point: str,
    score_regime_fingerprint: str | None,
    artifact_role: str = "latest",
    confirmation_threshold_runs: int = 2,
) -> dict[str, Any]:
    existing = _load_json(ledger_path) or _empty_ledger(project, confirmation_threshold_runs)
    existing_threshold = int(existing.get("confirmation_threshold_runs", confirmation_threshold_runs) or confirmation_threshold_runs)
    threshold = max(2, existing_threshold)

    entries_by_signature: dict[str, dict[str, Any]] = {}
    for bucket_name in ("confirmed_constraints", "provisional_constraints"):
        for item in existing.get(bucket_name, []):
            if not isinstance(item, dict):
                continue
            signature = str(item.get("signature", "")).strip()
            if not signature:
                continue
            restored = dict(item)
            seen_run_ids = sorted(
                {
                    int(run)
                    for run in restored.get("seen_run_ids", [])
                    if isinstance(run, int) or str(run).isdigit()
                }
            )
            restored["seen_run_ids"] = seen_run_ids
            restored["seen_count_runs"] = len(seen_run_ids)
            source_examples = restored.get("source_examples", [])
            if not isinstance(source_examples, list):
                source_examples = []
            restored["source_examples"] = [
                example
                for example in source_examples
                if isinstance(example, dict)
            ]
            entries_by_signature[signature] = restored

    for proposal in sanitize_constraint_proposals(proposals):
        signature = proposal_signature(proposal)
        entry = entries_by_signature.get(signature)
        if entry is None:
            entry = {
                "signature": signature,
                "constraint": proposal["constraint"],
                "applies_to": proposal["applies_to"],
                "failure_family": proposal["failure_family"],
                "severity": proposal["severity"],
                "producer": proposal["producer"],
                "rationale": proposal["rationale"],
                "non_applicability_condition": proposal["non_applicability_condition"],
                "seen_run_ids": [],
                "seen_count_runs": 0,
                "first_seen_run_id": run_id,
                "last_seen_run_id": run_id,
                "latest_iteration_index": iteration_index,
                "latest_score_regime_fingerprint": score_regime_fingerprint or "",
                "source_examples": [],
            }
            entries_by_signature[signature] = entry

        entry.update(
            {
                "constraint": proposal["constraint"],
                "applies_to": proposal["applies_to"],
                "failure_family": proposal["failure_family"],
                "severity": proposal["severity"],
                "producer": proposal["producer"],
                "rationale": proposal["rationale"],
                "non_applicability_condition": proposal["non_applicability_condition"],
                "latest_iteration_index": iteration_index,
                "latest_score_regime_fingerprint": score_regime_fingerprint or "",
            }
        )

        seen_run_ids = {int(run) for run in entry.get("seen_run_ids", [])}
        seen_run_ids.add(int(run_id))
        entry["seen_run_ids"] = sorted(seen_run_ids)
        entry["seen_count_runs"] = len(entry["seen_run_ids"])
        entry["first_seen_run_id"] = min(entry["seen_run_ids"])
        entry["last_seen_run_id"] = max(entry["seen_run_ids"])

        source_example = {
            "run_id": int(run_id),
            "iteration_index": int(iteration_index),
            "artifact_role": artifact_role,
            "score": source_score,
            "weakest_point": _clean_text(weakest_point),
        }
        existing_examples = entry.get("source_examples", [])
        if not isinstance(existing_examples, list):
            existing_examples = []
        if _source_example_key(source_example) not in {
            _source_example_key(example)
            for example in existing_examples
            if isinstance(example, dict)
        }:
            existing_examples.append(source_example)
        entry["source_examples"] = existing_examples[-5:]
        entry["status"] = (
            "confirmed" if entry["seen_count_runs"] >= threshold else "provisional"
        )

    all_entries = sorted(
        entries_by_signature.values(),
        key=lambda item: (
            -int(item.get("seen_count_runs", 0)),
            str(item.get("constraint", "")).lower(),
            str(item.get("applies_to", "")).lower(),
        ),
    )
    confirmed = [dict(item) for item in all_entries if item.get("status") == "confirmed"]
    provisional = [dict(item) for item in all_entries if item.get("status") != "confirmed"]

    for index, item in enumerate(confirmed, start=1):
        item["constraint_id"] = f"DC-{index:03d}"
    for index, item in enumerate(provisional, start=1):
        item["constraint_id"] = f"PC-{index:03d}"

    payload = {
        "project": project,
        "updated_on": _now_iso(),
        "confirmation_threshold_runs": threshold,
        "confirmed_constraint_count": len(confirmed),
        "provisional_constraint_count": len(provisional),
        "confirmed_constraints": confirmed,
        "provisional_constraints": provisional,
    }
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


DOWNGRADABLE_PRODUCERS = {
    "structural_extractor",
    "trajectory_extractor",
    "negative_space_extractor",
}
DEFAULT_STAGNATION_DOWNGRADE_THRESHOLD = 6


def downgrade_constraints_on_stagnation(
    *,
    ledger_path: Path,
    stagnation_count: int,
    threshold: int = DEFAULT_STAGNATION_DOWNGRADE_THRESHOLD,
    producer_filter: set[str] | None = None,
) -> dict[str, Any] | None:
    """Demote one confirmed constraint back to provisional when the loop is
    starving under its own prior. Narrow by design: only acts on producers in
    ``producer_filter`` (default: the two cross-artifact extractors), never on
    judge-produced constraints. Picks the most recently confirmed entry in the
    filter and strips it from the confirmed bucket for the current run.

    This is a retraction *mechanism*, not a retraction *trigger*. It is not
    called from `_refresh_derived_constraints_from_eval`. The caller (loop
    control / emergency-pivot path) is responsible for deciding when to invoke
    it. Keeping the trigger out of this module prevents stagnation-count
    semantics from leaking into constraint-ledger code.

    Returns the updated ledger payload, or None if nothing was changed.
    """
    if stagnation_count < threshold:
        return None
    filter_set = producer_filter or DOWNGRADABLE_PRODUCERS

    ledger = _load_json(ledger_path)
    if not ledger:
        return None
    confirmed = [
        item
        for item in ledger.get("confirmed_constraints", [])
        if isinstance(item, dict)
    ]
    provisional = [
        item
        for item in ledger.get("provisional_constraints", [])
        if isinstance(item, dict)
    ]

    candidates = [
        item for item in confirmed if item.get("producer") in filter_set
    ]
    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            int(item.get("last_seen_run_id") or 0),
            int(item.get("latest_iteration_index") or 0),
        ),
        reverse=True,
    )
    victim = candidates[0]
    victim_signature = victim.get("signature")
    if not victim_signature:
        return None

    new_confirmed = [
        item for item in confirmed if item.get("signature") != victim_signature
    ]
    demoted = dict(victim)
    demoted["status"] = "provisional"
    history = demoted.get("downgrade_history", [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "downgraded_on": _now_iso(),
            "stagnation_count": int(stagnation_count),
            "threshold": int(threshold),
            "reason": "stagnation_downgrade",
        }
    )
    demoted["downgrade_history"] = history
    new_provisional = provisional + [demoted]

    for index, item in enumerate(new_confirmed, start=1):
        item["constraint_id"] = f"DC-{index:03d}"
    for index, item in enumerate(new_provisional, start=1):
        item["constraint_id"] = f"PC-{index:03d}"

    payload = {
        "project": ledger.get("project", ""),
        "updated_on": _now_iso(),
        "confirmation_threshold_runs": int(
            ledger.get("confirmation_threshold_runs", 2) or 2
        ),
        "confirmed_constraint_count": len(new_confirmed),
        "provisional_constraint_count": len(new_provisional),
        "confirmed_constraints": new_confirmed,
        "provisional_constraints": new_provisional,
    }
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def write_derived_constraints_brief(ledger: dict[str, Any], output_path: Path) -> None:
    confirmed = ledger.get("confirmed_constraints", [])
    provisional = ledger.get("provisional_constraints", [])
    lines = [
        "# Derived Constraints",
        "",
        "These are adversarially surfaced structural limits. They are not primary evidence.",
        "",
        f"- Confirmed: {len(confirmed)}",
        f"- Provisional: {len(provisional)}",
        "",
    ]

    if confirmed:
        lines.extend(["## Confirmed", ""])
        for item in confirmed:
            lines.append(
                f"- {item.get('constraint_id', 'DC-???')} [{item.get('seen_count_runs', 0)} runs | "
                f"{item.get('failure_family', 'other')} | {item.get('applies_to', 'project scope')}]: "
                f"{item.get('constraint', '')}"
            )
            lines.append(f"  Rationale: {item.get('rationale', '')}")
            lines.append(
                f"  Non-applicability: {item.get('non_applicability_condition', DEFAULT_NON_APPLICABILITY)}"
            )
            lines.append("")

    if provisional:
        lines.extend(["## Provisional", ""])
        for item in provisional[:8]:
            lines.append(
                f"- {item.get('constraint_id', 'PC-???')} [{item.get('seen_count_runs', 0)} runs | "
                f"{item.get('failure_family', 'other')}]: {item.get('constraint', '')}"
            )
            lines.append(f"  Applies to: {item.get('applies_to', 'project scope')}")
            lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_confirmed_constraints_prompt_section(
    ledger_source: Path | dict[str, Any] | None,
) -> str:
    if ledger_source is None:
        return ""
    if isinstance(ledger_source, Path):
        ledger = _load_json(ledger_source) or {}
    elif isinstance(ledger_source, dict):
        ledger = ledger_source
    else:
        return ""
    confirmed = ledger.get("confirmed_constraints", [])
    if not isinstance(confirmed, list) or not confirmed:
        return ""

    confirmed = sorted(confirmed, key=lambda x: x.get("seen_count_runs", 0), reverse=True)[:20]

    lines = [
        "ADVERSARIALLY SURFACED CONSTRAINTS (READ-ONLY):",
        "These are NOT primary evidence. They are structural limits discovered across prior independent runs.",
        "Your thesis may comply with them directly or explicitly argue non-applicability with justification.",
    ]
    for item in confirmed:
        lines.append(
            "- "
            f"{item.get('constraint_id', 'DC-???')} "
            f"[{item.get('seen_count_runs', 0)} runs | "
            f"{item.get('failure_family', 'other')} | "
            f"{item.get('applies_to', 'project scope')}]: "
            f"{item.get('constraint', '')}"
        )
        lines.append(
            f"  Non-applicability condition: {item.get('non_applicability_condition', DEFAULT_NON_APPLICABILITY)}"
        )
    return "\n".join(lines)


def run_derived_constraints_fixture_regression() -> dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "workspace" / "derived_constraints.json"
        first = update_derived_constraints_ledger(
            project="fixture_project",
            ledger_path=ledger_path,
            proposals=[
                {
                    "constraint": "ESM permanence must be separated from automaticity",
                    "applies_to": "euro fiscal stabilizer classification",
                    "failure_family": "definitional_trap",
                    "severity": "blocking",
                    "producer": "meta_judge",
                    "rationale": "The evaluator repeatedly surfaced the same classification trap.",
                    "non_applicability_condition": "Only if the thesis no longer classifies ESM-like instruments.",
                },
                {
                    "constraint": "ESM permanence must be separated from automaticity",
                    "applies_to": "euro fiscal stabilizer classification",
                    "failure_family": "definitional_trap",
                    "severity": "blocking",
                    "producer": "meta_judge",
                    "rationale": "Duplicate in the same run should dedupe.",
                    "non_applicability_condition": "Only if the thesis no longer classifies ESM-like instruments.",
                },
            ],
            run_id=101,
            iteration_index=0,
            source_score=67,
            weakest_point="ESM label trap",
            score_regime_fingerprint="abc123",
        )
        second = update_derived_constraints_ledger(
            project="fixture_project",
            ledger_path=ledger_path,
            proposals=[
                {
                    "constraint": "ESM permanence must be separated from automaticity",
                    "applies_to": "euro fiscal stabilizer classification",
                    "failure_family": "definitional_trap",
                    "severity": "blocking",
                    "producer": "meta_judge",
                    "rationale": "The same limit repeated in a second run.",
                    "non_applicability_condition": "Only if the thesis no longer classifies ESM-like instruments.",
                }
            ],
            run_id=202,
            iteration_index=1,
            source_score=83,
            weakest_point="same seam repeated",
            score_regime_fingerprint="def456",
        )
        prompt_section = render_confirmed_constraints_prompt_section(second)

    cases = [
        {
            "case_id": "same_run_duplicates_do_not_fake_confirmation",
            "passed": (
                first["confirmed_constraint_count"] == 0
                and first["provisional_constraint_count"] == 1
                and first["provisional_constraints"][0]["seen_count_runs"] == 1
            ),
        },
        {
            "case_id": "second_distinct_run_promotes_constraint",
            "passed": (
                second["confirmed_constraint_count"] == 1
                and second["provisional_constraint_count"] == 0
                and second["confirmed_constraints"][0]["seen_count_runs"] == 2
                and second["confirmed_constraints"][0]["constraint_id"] == "DC-001"
            ),
        },
        {
            "case_id": "confirmed_constraints_render_as_prompt_context",
            "passed": (
                "ADVERSARIALLY SURFACED CONSTRAINTS" in prompt_section
                and "DC-001" in prompt_section
                and "automaticity" in prompt_section
            ),
        },
    ]
    return {
        "suite": "derived_constraints_fixture_regression",
        "all_passed": all(case["passed"] for case in cases),
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run derived constraints fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_derived_constraints_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Derived constraints fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
