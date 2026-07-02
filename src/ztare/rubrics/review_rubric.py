"""
Pre-run rubric review

Runs a pre-flight rubric review against a project's current charter, compiled
workspace summary, and rubric JSON. Writes a durable review artifact and an
optional patch proposal artifact.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from ztare.common.llm_runtime import LLMRuntime, LLMRuntimeError, MODEL_MAP
from ztare.common.paths import PROJECTS_DIR, REPO_ROOT, RUBRICS_DIR
from ztare.common.utils import parse_llm_json


CHECK_NAMES = (
    "gaming_surface_coverage",
    "evidence_anchor_requirement",
    "score_ceiling_reachability_without_evidence",
    "criterion_independence",
    "persona_blind_spot_coverage",
    "charter_spirit_coverage",
)

WORKSPACE_SUMMARY_FILES = (
    "facts.md",
    "candidate_claims.md",
)

EVIDENCE_DEPENDENT_CHECKS = {
    "evidence_anchor_requirement",
    "score_ceiling_reachability_without_evidence",
}

PLACEHOLDER_LINES = {
    "- None identified.",
    "# Facts",
    "# Candidate Claims",
}

DEFAULT_PRE_RUN_GAP_SEVERITY = "degrading"


class RubricReviewError(RuntimeError):
    """Raised when rubric review cannot complete."""


def _status_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def _file_ts() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def resolve_project_dir(project_arg: str) -> Path:
    candidate = Path(project_arg)
    if candidate.exists():
        return candidate.resolve()
    fallback = PROJECTS_DIR / project_arg
    if fallback.exists():
        return fallback.resolve()
    raise FileNotFoundError(f"Project not found: {project_arg}")


def resolve_rubric_path(rubric_arg: str) -> Path:
    candidate = Path(rubric_arg)
    if candidate.exists():
        return candidate.resolve()
    if not candidate.suffix:
        candidate = RUBRICS_DIR / f"{rubric_arg}.json"
    else:
        candidate = RUBRICS_DIR / rubric_arg
    if candidate.exists():
        return candidate.resolve()
    raise FileNotFoundError(f"Rubric not found: {rubric_arg}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_workspace_evidence_surface(project_dir: Path) -> dict[str, Any]:
    workspace_dir = project_dir / "workspace"
    sections: list[str] = []
    files_used: list[str] = []
    for name in WORKSPACE_SUMMARY_FILES:
        path = workspace_dir / name
        if path.exists():
            text = read_text(path).strip()
            if text:
                files_used.append(str(path.relative_to(project_dir)))
                sections.append(text)
    if sections:
        return {
            "mode": "workspace_summary",
            "files": files_used,
            "text": "\n\n".join(sections).strip(),
        }

    evidence_path = project_dir / "evidence.txt"
    if not evidence_path.exists() or not read_text(evidence_path).strip():
        # Fresh project with no evidence yet — return empty surface so
        # rubric-review can still emit evidence gaps without crashing.
        # evidence_surface_ready() will return False and cause attribution
        # will mark evidence-dependent checks accordingly.
        return {
            "mode": "empty",
            "files": [],
            "text": "",
        }
    evidence_text = read_text(evidence_path).strip()
    return {
        "mode": "evidence_fallback",
        "files": [str(evidence_path.relative_to(project_dir))],
        "text": evidence_text[:3000],
    }


def evidence_surface_ready(evidence_surface: dict[str, Any]) -> bool:
    text = str(evidence_surface.get("text", "")).strip()
    if not text:
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    substantive_lines = [line for line in lines if line not in PLACEHOLDER_LINES]
    substantive_text = "\n".join(substantive_lines).strip()
    if not substantive_text:
        return False
    return len(substantive_text.encode("utf-8")) >= 200


def build_review_prompt(
    *,
    project_name: str,
    charter_text: str,
    evidence_surface: dict[str, Any],
    rubric_payload: dict[str, Any],
) -> str:
    rubric_json = json.dumps(rubric_payload, indent=2, sort_keys=True)
    return f"""You are reviewing a ZTARE rubric before a run starts.

Project: {project_name}
Timestamp: {_status_ts()}

Your job is to do one pre-run review only.

First, perform a hard scenario-validity admissibility check:
- Ask whether the operative scenario defined in the charter has already been superseded or contradicted by the current evidence surface.
- Return only "pass" or "fail".
- If fail, name the evidence that makes the current frame inadmissible and suggest the smallest charter/rubric revision needed.
- IMPORTANT: An empty or thin evidence surface is NOT grounds for a scenario-validity failure. Scenario validity fails only when real-world events have made the charter's operative scenario no longer live, not when evidence has not yet been compiled. If the evidence surface is thin but the scenario itself is still operative in the world, return "pass".

Second, if the scenario is still admissible, review the rubric on these five checks:
1. gaming_surface_coverage
   - Does the rubric have criteria that target the known failure modes for this project class, such as fabricated support, omitted hard tests, or polished but weak claims?
   - In ZTARE terms: a rubric with gaming-surface gaps lets a mutator score highly by optimizing surface presentation (fluency, structure, apparent rigor) without satisfying the core empirical demand of the thesis. Flag any criterion absent from the rubric that would catch this.
2. evidence_anchor_requirement
   - Does the rubric require claims to be tied to observable support from the provided evidence rather than rewarding internally coherent free reasoning?
3. score_ceiling_reachability_without_evidence
   - Could this rubric still award a high score to a thesis that cites support not present in the actual project materials?
4. criterion_independence
   - Do any two rubric criteria collapse into each other so that satisfying one would effectively satisfy the other automatically?
5. persona_blind_spot_coverage
   - Is the rubric persona likely to miss the actual weak spots for this project class or be charmed by fluent, confident, but weakly supported claims?
   - In ZTARE terms: a persona with blind spots scores presentation quality rather than falsification quality. A resistant persona explicitly demands a named observable, a falsification direction, and a stated revision path, not just a well-framed argument. Flag if the persona description lacks any of these demands.
6. charter_spirit_coverage
   - Does the rubric capture what the charter implicitly requires, or only what was explicitly named in the brief?
   - Read the charter's Core Question and identify implicit analytical demands: second-order effects, dynamic modeling, distributional analysis, counterfactual discipline, sensitivity to assumptions, capital structure, irreversibility, and so on. Check whether any rubric dimension or criterion would penalize a thesis that ignores these demands entirely.
   - A rubric passes this check only if: (a) at least one criterion explicitly penalizes static first-order analysis when second-order effects are knowable from the evidence, OR (b) the persona names a specific modeling failure mode it will penalize even absent an explicit criterion. A rubric that only scores what the brief explicitly mentioned will miss all the reasoning quality the charter's spirit demands.
   - Example of a failing case: charter asks "model positive and negative externalities dynamically"; rubric only scores "causal attribution" and "mechanism pricing" — a static voucher NPV calculation can score 94/100 without touching any second-order effect.

For each check:
- set status to "pass" or "fail"
- if fail, state the issue plainly
- propose the smallest rubric-level fix

Return strict JSON only. No markdown fences. Use this schema exactly:
{{
  "scenario_validity": {{
    "status": "pass|fail",
    "issue": "...",
    "evidence_ref": ["..."],
    "suggested_revision": "..."
  }},
  "checks": [
    {{
      "check_name": "gaming_surface_coverage",
      "status": "pass|fail",
      "issue": "...",
      "proposed_fix": "..."
    }}
  ],
  "evidence_gaps": [
    {{
      "target": "...",
      "severity": "degrading|enriching|blocking",
      "fetch_query": "...",
      "source_hint": "..."
    }}
  ],
  "overall_summary": "..."
}}

Requirements:
- Include all six checks exactly once in the checks array.
- Do not invent evidence outside the provided materials.
- If a check passes, keep issue/proposed_fix short and empty if appropriate.
- If scenario_validity is "fail", you should still fill the checks array, but the run remains inadmissible.
- If the evidence surface is thin, include pre-run evidence gaps that would help bootstrap evidence collection before the first loop run.

=== PROJECT CHARTER ===
{charter_text}

=== CURRENT EVIDENCE SURFACE ({evidence_surface["mode"]}) ===
{evidence_surface["text"]}

=== RUBRIC JSON ===
{rubric_json}
"""


def _normalize_status(value: Any) -> str:
    lowered = str(value or "").strip().lower()
    return "pass" if lowered == "pass" else "fail"


def normalize_evidence_gaps(raw_gaps: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if not isinstance(raw_gaps, list):
        return normalized
    for item in raw_gaps:
        if not isinstance(item, dict):
            continue
        target = str(item.get("target", "")).strip()
        fetch_query = str(item.get("fetch_query", "")).strip()
        source_hint = str(item.get("source_hint", "")).strip()
        severity = str(item.get("severity", DEFAULT_PRE_RUN_GAP_SEVERITY)).strip().lower()
        if not target or not fetch_query:
            continue
        if severity not in {"degrading", "enriching", "blocking"}:
            severity = DEFAULT_PRE_RUN_GAP_SEVERITY
        normalized.append(
            {
                "target": target,
                "severity": severity,
                "fetch_query": fetch_query,
                "source_hint": source_hint,
            }
        )
    return normalized


def normalize_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    scenario = payload.get("scenario_validity", {}) if isinstance(payload, dict) else {}
    checks = payload.get("checks", []) if isinstance(payload, dict) else []
    check_map: dict[str, dict[str, Any]] = {}
    for item in checks if isinstance(checks, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("check_name", "")).strip()
        if name in CHECK_NAMES:
            check_map[name] = {
                "check_name": name,
                "status": _normalize_status(item.get("status")),
                "issue": str(item.get("issue", "")).strip(),
                "proposed_fix": str(item.get("proposed_fix", "")).strip(),
                "cause": str(item.get("cause", "")).strip(),
            }

    normalized_checks: list[dict[str, Any]] = []
    for name in CHECK_NAMES:
        normalized_checks.append(
            check_map.get(
                name,
                {
                    "check_name": name,
                    "status": "fail",
                    "issue": "Check missing from model output.",
                    "proposed_fix": "Return all required checks exactly once.",
                    "cause": "",
                },
            )
        )

    normalized = {
        "scenario_validity": {
            "status": _normalize_status(scenario.get("status")),
            "issue": str(scenario.get("issue", "")).strip(),
            "evidence_ref": [
                str(item).strip()
                for item in scenario.get("evidence_ref", [])
                if str(item).strip()
            ]
            if isinstance(scenario.get("evidence_ref", []), list)
            else [],
            "suggested_revision": str(scenario.get("suggested_revision", "")).strip(),
        },
        "checks": normalized_checks,
        "evidence_gaps": normalize_evidence_gaps(
            payload.get("evidence_gaps", []) if isinstance(payload, dict) else []
        ),
        "overall_summary": str(payload.get("overall_summary", "")).strip(),
    }
    return normalized


def build_patch_payload(*, rubric_path: Path, normalized_review: dict[str, Any]) -> dict[str, Any] | None:
    failed_checks = [
        {
            "check_name": item["check_name"],
            "issue": item["issue"],
            "proposed_fix": item["proposed_fix"],
            "cause": item.get("cause", ""),
        }
        for item in normalized_review["checks"]
        if item["status"] == "fail"
    ]
    scenario_validity = normalized_review["scenario_validity"]
    if scenario_validity["status"] == "pass" and not failed_checks:
        return None
    return {
        "rubric_file": str(rubric_path),
        "scenario_validity": {
            "status": scenario_validity["status"],
            "evidence_ref": scenario_validity["evidence_ref"],
            "suggested_revision": scenario_validity["suggested_revision"],
        },
        "checks_failed": failed_checks,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_evidence_gaps_payload(
    *,
    project_name: str,
    model_family: str,
    evidence_surface_ready_flag: bool,
    normalized_review: dict[str, Any],
) -> dict[str, Any] | None:
    gaps = normalized_review.get("evidence_gaps", [])
    if not gaps:
        return None
    # Write gaps regardless of evidence_surface_ready — an existing baseline
    # evidence.txt does not mean all gaps are filled; fetch_evidence uses the
    # gap list to enrich the surface further.
    return {
        "project": project_name,
        "judge_model": MODEL_MAP[model_family],
        "generated_on": _status_ts(),
        "artifact_role": "pre_run_rubric_review",
        "describes_baseline": "pre_run",
        "evidence_surface_ready": False,
        "weakest_point": normalized_review.get("overall_summary", ""),
        "evidence_gaps": gaps,
    }


def review_exit_code(review_payload: dict[str, Any]) -> int:
    if review_payload["scenario_validity"]["status"] == "fail":
        return 2
    if review_payload["checks_failed"]:
        return 1
    return 0


def run_rubric_review(
    *,
    project: str,
    rubric: str,
    model_family: str,
) -> dict[str, Any]:
    if model_family not in MODEL_MAP:
        raise ValueError(f"Unsupported model family: {model_family}")

    project_dir = resolve_project_dir(project)
    rubric_path = resolve_rubric_path(rubric)
    workspace_dir = project_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    charter_path = project_dir / "project_charter.md"
    if not charter_path.exists():
        raise FileNotFoundError(f"Project charter not found: {charter_path}")

    evidence_surface = load_workspace_evidence_surface(project_dir)
    charter_text = read_text(charter_path).strip()
    rubric_payload = json.loads(read_text(rubric_path))

    prompt = build_review_prompt(
        project_name=project_dir.name,
        charter_text=charter_text,
        evidence_surface=evidence_surface,
        rubric_payload=rubric_payload,
    )

    runtime = LLMRuntime()
    model_id = MODEL_MAP[model_family]
    try:
        from ztare.common.dispatch_model import dispatch_call_text

        response = dispatch_call_text(
            "rubric_review",
            prompt,
            llm_response_call=lambda p: runtime.call_text(
                p,
                model_id=model_id,
                retries=4,
                timeout_seconds=300,
                request_label="rubric_review request",
                transient_wait_seconds=5,
                timeout_wait_seconds=2,
            ),
            repo=REPO_ROOT,
            timeout_seconds=300,
        )
    except LLMRuntimeError as exc:
        raise RubricReviewError(
            f"Rubric review LLM call failed after retries: {exc}"
        ) from exc
    except Exception as exc:
        raise RubricReviewError(
            f"Rubric review dispatch failed after retries: {exc}"
        ) from exc

    parsed = parse_llm_json(response.text)
    if not isinstance(parsed, dict):
        raise RubricReviewError("Rubric review model output was not a JSON object.")
    normalized_review = normalize_review_payload(parsed)
    is_surface_ready = evidence_surface_ready(evidence_surface)
    if not is_surface_ready:
        for item in normalized_review["checks"]:
            if (
                item["check_name"] in EVIDENCE_DEPENDENT_CHECKS
                and item["status"] == "fail"
                and not item.get("cause")
            ):
                item["cause"] = "evidence_surface_empty"
    patch_payload = build_patch_payload(
        rubric_path=rubric_path.relative_to(REPO_ROOT)
        if rubric_path.is_relative_to(REPO_ROOT)
        else rubric_path,
        normalized_review=normalized_review,
    )

    ts = _file_ts()
    review_path = workspace_dir / f"rubric_review_{ts}.json"
    review_payload = {
        "project": project_dir.name,
        "rubric": rubric_path.stem,
        "generated_on": _status_ts(),
        "model_family": model_family,
        "model_id": model_id,
        "evidence_surface": {
            "mode": evidence_surface["mode"],
            "files": evidence_surface["files"],
        },
        "evidence_surface_ready": is_surface_ready,
        "scenario_validity": normalized_review["scenario_validity"],
        "checks": normalized_review["checks"],
        "checks_failed": [
            item for item in normalized_review["checks"] if item["status"] == "fail"
        ],
        "evidence_gaps_proposed": bool(normalized_review["evidence_gaps"]),
        "evidence_gaps": normalized_review["evidence_gaps"],
        "overall_summary": normalized_review["overall_summary"],
        "llm_raw_text": response.text,
        "patch_proposed": patch_payload is not None,
    }
    write_json(review_path, review_payload)

    patch_path: Path | None = None
    if patch_payload is not None:
        patch_path = workspace_dir / f"rubric_patch_{ts}.json"
        write_json(patch_path, patch_payload)

    evidence_gaps_path: Path | None = None
    latest_evidence_gaps_path: Path | None = None
    evidence_gaps_payload = build_evidence_gaps_payload(
        project_name=project_dir.name,
        model_family=model_family,
        evidence_surface_ready_flag=is_surface_ready,
        normalized_review=normalized_review,
    )
    if evidence_gaps_payload is not None:
        evidence_gaps_path = workspace_dir / f"evidence_gaps_{ts}.json"
        latest_evidence_gaps_path = workspace_dir / "latest_evidence_gaps.json"
        write_json(evidence_gaps_path, evidence_gaps_payload)
        write_json(latest_evidence_gaps_path, evidence_gaps_payload)

    return {
        "review_path": review_path,
        "patch_path": patch_path,
        "evidence_gaps_path": evidence_gaps_path,
        "latest_evidence_gaps_path": latest_evidence_gaps_path,
        "review_payload": review_payload,
        "scenario_failed": normalized_review["scenario_validity"]["status"] == "fail",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run pre-run rubric review.")
    parser.add_argument("--project", required=True, help="Project name under projects/ or explicit path.")
    parser.add_argument("--rubric", default=None, help="Rubric name under rubrics/ or explicit path (defaults to --project).")
    parser.add_argument("--model", default="gemini", choices=sorted(MODEL_MAP.keys()))
    parser.add_argument("--json", action="store_true", help="Emit the review payload + artifact paths as one JSON object on stdout (for the workbench).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.rubric is None:
        args.rubric = args.project
    result = run_rubric_review(
        project=args.project,
        rubric=args.rubric,
        model_family=args.model,
    )
    review_path = result["review_path"]
    patch_path = result["patch_path"]
    review_payload = result["review_payload"]
    if getattr(args, "json", False):
        # One machine-readable object for the workbench: the review payload plus where artifacts landed.
        print(json.dumps({
            "ok": True,
            "review_payload": review_payload,
            "review_path": str(review_path) if review_path is not None else "",
            "patch_path": str(patch_path) if patch_path is not None else "",
            "evidence_gaps_path": str(result.get("evidence_gaps_path") or ""),
            "scenario_failed": bool(result.get("scenario_failed")),
        }))
        return review_exit_code(review_payload)
    print(f"Rubric review written to: {review_path}")
    if patch_path is not None:
        print(f"Rubric patch proposal written to: {patch_path}")
    if result["evidence_gaps_path"] is not None:
        print(f"Pre-run evidence gaps written to: {result['evidence_gaps_path']}")
        print(f"Latest evidence gaps updated: {result['latest_evidence_gaps_path']}")
    if not review_payload.get("evidence_surface_ready", True):
        print(
            "⚠️ Evidence surface is thin — run workspace-update + evidence-compile "
            "before acting on evidence-anchor failures as pure rubric fixes."
        )
    print(f"Scenario validity: {review_payload['scenario_validity']['status']}")
    print(f"Checks failed: {len(review_payload['checks_failed'])}/{len(review_payload['checks'])}")
    return review_exit_code(review_payload)


if __name__ == "__main__":
    raise SystemExit(main())
