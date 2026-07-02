"""The epistemic payload of an autoresearch run — one CLI surface, no sprawl.

Single source of truth for the run's eval output so the CLI and the forensic workbench stay in
parity (the workbench shells out to `ztare autoresearch eval-results`, it does not read
`latest_eval_results.json` off disk). One verb, `--facet` to scope — not six per-primitive verbs.

Data sources (read-only):
  * `projects/<p>/latest_eval_results.json` (or `champion_eval_results.json` with --champion) — the
    judge's structured output: score, weakest_point, logic_gaps, friction_points, debate_summary,
    adversarial_alignment, probability_dag, verified_axioms, evidence_gaps, derived_constraints,
    score_contract.
  * `projects/<p>/workspace/derived_constraints.json` — the persistent constraint LEDGER
    (confirmed/provisional + confirmation threshold), merged in for the `constraints` facet.

Honesty note: `adversarial_alignment` is the judge's free-text self-assessment, NOT a computed
gaming metric. We surface it as labelled narrative (`is_narrative: true`), never as a hard
"real/gamed" verdict. A real trust signal must come from anti-Goodhart mechanisms (rotating rubric /
committee / cross-family / score caps / latent-distance), which live in run config + telemetry, not
here.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Markers that mean the inverter's prose is a kernel process/error note, not a real assessment —
# never surface these to a human, and treat the default 0.5 confidence as "no signal" when present.
_INVERTER_NOISE = re.compile(
    r"inverter failed|max retries|error code|quota|exceeded|truncat|salvag|partial|"
    r"structured prefix|provider chain|parse error|json",
    re.IGNORECASE,
)

SCHEMA = "ztare-eval-results-v1"

FACETS = ("full", "weakest", "debate", "trust", "constraints", "contract", "axioms", "dag",
          "open-questions", "discriminators", "inverter", "charter-drift", "meta-audit", "coherence")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _read_open_questions(proot: Path) -> list[dict[str, str]]:
    """Parse workspace/open_questions.md into [{question, why, blocking}]. Each top-level '- ' bullet is
    a question; its '  - Why it matters:' / '  - Blocking effect:' sub-bullets fill why/blocking."""
    path = proot / "workspace" / "open_questions.md"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    out: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    for raw in lines:
        if raw.startswith("- "):
            if cur:
                out.append(cur)
            cur = {"question": raw[2:].strip(), "why": "", "blocking": ""}
        elif cur is not None:
            s = raw.strip()
            low = s.lower()
            if low.startswith("- why it matters:"):
                cur["why"] = s.split(":", 1)[1].strip()
            elif low.startswith("- blocking effect:"):
                cur["blocking"] = s.split(":", 1)[1].strip()
    if cur:
        out.append(cur)
    return [q for q in out if q["question"]]


def _read_discriminators(proot: Path) -> list[dict[str, Any]]:
    """The cheapest experiments to separate rival hypotheses (next_discriminator_queue.jsonl)."""
    path = proot / "workspace" / "next_discriminator_queue.jsonl"
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                test = str(row.get("cheapest_discriminator") or row.get("discriminator") or "").strip()
                if test:
                    out.append({
                        "test": test,
                        "auto_testable": bool(row.get("auto_testable")),
                        "can_support_promotion": bool(row.get("can_support_promotion")),
                    })
    except Exception:
        return out
    return out


def _read_inverter_review(proot: Path) -> dict[str, Any]:
    """The post-champion adversary's falsification tests (workspace/inverter_review.json). Framed for
    humans as "what would prove this wrong" — each test = what you'd measure + pass/fail."""
    data = _read_json(proot / "workspace" / "inverter_review.json")
    if not isinstance(data, dict):
        return {}
    tests = []
    for t in data.get("tests") if isinstance(data.get("tests"), list) else []:
        if not isinstance(t, dict):
            continue
        test = str(t.get("popper_test") or t.get("munger_inversion") or "").strip()
        if not test:
            continue
        proc = t.get("procedure")
        steps = ([str(s).strip() for s in proc if str(s).strip()] if isinstance(proc, list)
                 else ([str(proc).strip()] if str(proc or "").strip() else []))
        tests.append({
            "test": test,
            "doubt": str(t.get("munger_inversion") or "").strip(),
            "steps": steps,
            "passes_if": str(t.get("pass_criterion") or "").strip(),
            "fails_if": str(t.get("fail_criterion") or "").strip(),
            "auto_testable": bool(t.get("auto_testable")),
        })
    # Drop kernel process/error chatter (quota, truncated JSON, salvage notes) — never show it.
    raw_assessment = str(data.get("overall_assessment") or "").strip()
    degraded = bool(_INVERTER_NOISE.search(raw_assessment))
    assessment = "" if degraded else raw_assessment
    if not tests and not assessment:
        return {}
    conf = data.get("confidence_the_champion_survives")
    # The 0.5 default on a degraded run is not a real signal — suppress it.
    survival = None
    if not degraded and isinstance(conf, (int, float)) and not isinstance(conf, bool):
        survival = conf
    return {
        "tests": tests,
        "assessment": assessment,
        "survival_confidence": survival,
        "test_count": len(tests),
    }


def _read_charter_drift(proot: Path) -> dict[str, Any]:
    """Did the run's thesis drift off the charter's real intent? (workspace/mform_pending.json — the
    General Office / M-Form charter-alignment audit.) Plain one-liner + the criterion it added."""
    data = _read_json(proot / "workspace" / "mform_pending.json")
    if not isinstance(data, dict) or not data.get("gap_detected"):
        return {}
    return {
        "drift_detected": True,
        "gap": str(data.get("gap_description") or "").strip(),
        "added_criterion": str(data.get("adversarial_criterion") or "").strip(),
        "criterion_name": str(data.get("criterion_name") or "").strip(),
    }


def _read_meta_audit(proot: Path) -> dict[str, Any]:
    """Post-run meta-audit: did the score CAP because the evaluator was gamed or too narrow? A
    cross-family LLM explains why (post_run_meta_audit.json). The real 'is the score trustworthy' answer."""
    d = _read_json(proot / "workspace" / "post_run_meta_audit.json")
    if not isinstance(d, dict) or not d.get("succeeded"):
        return {}
    ns = d.get("narrow_scoped_gate")
    narrow = ""
    if isinstance(ns, dict):
        narrow = str(ns.get("name") or ns.get("gate") or "").strip()
    elif ns:
        narrow = str(ns).strip()
    out = {
        "cap_pattern": str(d.get("cap_pattern") or "").strip(),
        "gates_missed": _str_list(d.get("gates_engaged_not_flagged")),
        "recommendations": _str_list(d.get("detection_recommendations")),
        "narrow_gate": narrow,
    }
    return out if (out["cap_pattern"] or out["gates_missed"] or out["narrow_gate"]) else {}


def _read_coherence(proot: Path) -> dict[str, Any]:
    """Epistemic-coherence audit: four DETERMINISTIC (no-LLM) structural checks on whether the result is
    a real law or a curve-fit (epistemic_coherence_<run>.json). Trustworthy because it's code-computed."""
    paths = sorted((proot / "workspace").glob("epistemic_coherence_*.json"))
    d = _read_json(paths[-1]) if paths else None
    if not isinstance(d, dict):
        return {}
    labels = [
        ("check_1_kolmogorov_vs_yield", "Explains more than it costs"),
        ("check_2_boundary_collapse", "Holds at the extremes"),
        ("check_3_cross_class_degeneracy", "Same rule across cases"),
        ("check_4_type_theoretic_coherence", "Internally consistent"),
    ]
    checks = []
    for key, label in labels:
        c = d.get(key)
        if isinstance(c, dict) and c.get("verdict"):
            v = str(c.get("verdict")).strip().lower()
            checks.append({"label": label, "pass": ("pass" in v or "ok" in v or "coherent" in v) and "fail" not in v, "verdict": str(c.get("verdict")).strip()})
    return {"checks": checks} if checks else {}


def _str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _alignment_read(text: str) -> str:
    """The leading qualifier of the judge's alignment note (high/medium/low/…) — a label, not a metric."""
    head = str(text or "").strip().lower()
    for word in ("very high", "high", "strong", "medium", "moderate", "partial", "low", "weak", "none"):
        if head.startswith(word):
            return word
    return ""


def _dag_summary(dag: Any) -> dict[str, Any]:
    if not isinstance(dag, dict):
        return {}
    nodes = dag.get("nodes") if isinstance(dag.get("nodes"), list) else []
    edges = dag.get("edges") if isinstance(dag.get("edges"), list) else []

    def _num(v: Any) -> Any:
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    return {
        "outcome": dag.get("outcome"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        # full graph for the visualization
        "nodes": [
            {"id": str(n.get("id") or ""), "label": str(n.get("label") or ""),
             "probability": _num(n.get("probability")), "watch_signal": str(n.get("watch_signal") or "")}
            for n in nodes if isinstance(n, dict)
        ],
        "edges": [
            {"from": str(e.get("from") or ""), "to": str(e.get("to") or ""), "weight": _num(e.get("weight"))}
            for e in edges if isinstance(e, dict)
        ],
    }


def _constraints_ledger(proot: Path, eval_data: dict[str, Any]) -> dict[str, Any]:
    """The persistent ledger (derived_constraints.json) + what this run proposed (eval derived_constraints)."""
    ledger = _read_json(proot / "workspace" / "derived_constraints.json") or {}

    def rows(value: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in value if isinstance(value, list) else []:
            if isinstance(item, dict):
                out.append({"constraint": str(item.get("constraint") or item.get("statement") or "").strip(),
                            "status": str(item.get("status") or "").strip()})
            elif str(item).strip():
                out.append({"constraint": str(item).strip(), "status": ""})
        return [r for r in out if r["constraint"]]

    return {
        "confirmed_count": int(ledger.get("confirmed_constraint_count") or 0),
        "provisional_count": int(ledger.get("provisional_constraint_count") or 0),
        "confirmation_threshold_runs": ledger.get("confirmation_threshold_runs"),
        "updated_on": ledger.get("updated_on") or "",
        "confirmed": rows(ledger.get("confirmed_constraints")),
        "provisional": rows(ledger.get("provisional_constraints")),
        # What THIS run's evaluator derived/proposed (may not yet be in the ledger).
        "proposed_this_run": rows(eval_data.get("derived_constraints")),
    }


def build_eval_results(project: str, repo_root: Path, *, champion: bool = False) -> dict[str, Any]:
    proot = repo_root / "projects" / project
    source = "champion" if champion else "latest"
    fname = "champion_eval_results.json" if champion else "latest_eval_results.json"
    # eval results live at the project root, with a workspace/ fallback.
    eval_data = _read_json(proot / fname) or _read_json(proot / "workspace" / fname)
    if eval_data is None:
        return {"ok": False, "schema": SCHEMA, "project": project, "source": source,
                "error": f"no {fname} found for project {project!r} (run the loop first)"}

    alignment_text = str(eval_data.get("adversarial_alignment") or "").strip()
    contract = eval_data.get("score_contract") if isinstance(eval_data.get("score_contract"), dict) else {}

    return {
        "ok": True,
        "schema": SCHEMA,
        "project": project,
        "source": source,
        "score": eval_data.get("score"),
        "weakest_point": str(eval_data.get("weakest_point") or "").strip(),
        "logic_gaps": _str_list(eval_data.get("logic_gaps")),
        "friction_points": _str_list(eval_data.get("friction_points")),
        "debate_summary": str(eval_data.get("debate_summary") or "").strip(),
        # Labelled as the judge's narrative — NOT a computed trust/gaming metric.
        "adversarial_alignment": {
            "text": alignment_text,
            "read": _alignment_read(alignment_text),
            "is_narrative": True,
            "note": "judge's self-assessment, not a computed gaming metric",
        },
        "probability_dag": _dag_summary(eval_data.get("probability_dag")),
        "verified_axioms": _str_list(eval_data.get("verified_axioms")),
        # What the hardening process GAVE UP / ruled out — half the verdict story (audit P0-4, P1-3).
        "retired_axioms": _str_list(eval_data.get("retired_axioms_approved")),
        "non_claims": _str_list(eval_data.get("non_claims")),
        # Is the score TRUSTWORTHY? — the post-run gaming/cap meta-audit + deterministic coherence checks.
        "meta_audit": _read_meta_audit(proot),
        "coherence": _read_coherence(proot),
        "evidence_gap_count": int(contract.get("evidence_gap_count") or 0),
        "score_contract": {
            "mode": contract.get("mode"),
            "evidence_gap_count": contract.get("evidence_gap_count"),
            "blocking_evidence_gap_count": contract.get("blocking_evidence_gap_count"),
            "degrading_evidence_gap_count": contract.get("degrading_evidence_gap_count"),
            "enriching_evidence_gap_count": contract.get("enriching_evidence_gap_count"),
            "evidence_boundary_ceiling_detected": contract.get("evidence_boundary_ceiling_detected"),
            "derived_constraint_proposal_count": contract.get("derived_constraint_proposal_count"),
        },
        "constraints": _constraints_ledger(proot, eval_data),
        "open_questions": _read_open_questions(proot),
        "discriminators": _read_discriminators(proot),
        "inverter": _read_inverter_review(proot),
        "charter_drift": _read_charter_drift(proot),
    }


def apply_facet(payload: dict[str, Any], facet: str) -> dict[str, Any]:
    """Return one sub-view so a screen fetches only what it renders (no per-primitive verbs)."""
    if not payload.get("ok") or facet in ("", "full"):
        return payload
    base = {"ok": True, "schema": SCHEMA, "project": payload.get("project"), "source": payload.get("source"), "score": payload.get("score")}
    views = {
        "weakest": ("weakest_point", "logic_gaps", "friction_points"),
        "debate": ("debate_summary", "adversarial_alignment", "friction_points"),
        "trust": ("adversarial_alignment", "score_contract"),
        "constraints": ("constraints",),
        "contract": ("score_contract", "evidence_gap_count"),
        "dag": ("probability_dag",),
        "open-questions": ("open_questions",),
        "discriminators": ("discriminators",),
        "inverter": ("inverter",),
        "charter-drift": ("charter_drift",),
        "meta-audit": ("meta_audit",),
        "coherence": ("coherence",),
        "axioms": ("verified_axioms", "retired_axioms", "non_claims"),
    }
    for key in views.get(facet, ()):
        base[key] = payload.get(key)
    return base


def _repo_root() -> Path:
    # src/ztare/reports/eval_results.py → repo root is three parents up from this file's parent.
    return Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare autoresearch eval-results")
    parser.add_argument("--project", required=True, help="Project slug.")
    parser.add_argument("--champion", action="store_true", help="Use champion_eval_results.json instead of latest.")
    parser.add_argument("--facet", default="full", choices=FACETS,
                        help="Scope the output to one sub-view (default: full).")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default and only format).")
    args = parser.parse_args(argv)
    payload = apply_facet(build_eval_results(args.project, _repo_root(), champion=args.champion), args.facet)
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
