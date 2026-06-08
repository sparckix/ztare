#!/usr/bin/env python3
"""Synthesize F47 production-readiness gates from existing no-call audits.

No network, no model calls, no DB mutation.

F47 has a strong pairwise/ranking story, but production probability deployment
requires stronger evidence: held-out probability transfer, source safety,
market/equal-information controls, and prospective causal order. This tool
keeps those gates explicit so the paper can write F47 as a bounded ranking
phenomenon unless every production condition is satisfied.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_POLICY = WORKSPACE / "f47_translation_policy_control_2026_06_03.json"
DEFAULT_TRANSFER = WORKSPACE / "f47_cross_packet_transfer_audit_2026_06_03.json"
DEFAULT_EXTERNAL_BAR = WORKSPACE / "f47_external_bar_score_2026_06_03.json"
DEFAULT_PROSPECTIVE = (
    WORKSPACE
    / "f47_prospective_market_freeze_packet_2026_06_04"
    / "f47_prospective_market_freeze_score.json"
)
DEFAULT_OUT = WORKSPACE / "f47_production_readiness_audit_2026_06_05"


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def nested(obj: dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def p_value(row: dict[str, Any] | None) -> float | None:
    value = nested(row or {}, "paired_permutation", "p_value")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def delta(row: dict[str, Any] | None) -> float | None:
    value = (row or {}).get("delta_candidate_minus_baseline")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def n(row: dict[str, Any] | None) -> int:
    try:
        return int((row or {}).get("n") or 0)
    except (TypeError, ValueError):
        return 0


def pass_delta_p(row: dict[str, Any] | None, *, min_lift: float = -0.01, max_p: float = 0.05) -> bool:
    d = delta(row)
    p = p_value(row)
    return d is not None and p is not None and d <= min_lift and p <= max_p


def source_regressions(source_rows: dict[str, Any], comparison_key: str) -> list[dict[str, Any]]:
    out = []
    for source, comps in sorted(source_rows.items()):
        row = comps.get(comparison_key) if isinstance(comps, dict) else None
        d = delta(row)
        if d is not None and d > 0:
            out.append({"source": source, "delta": d, "n": n(row), "comparison": comparison_key})
    return out


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    policy = load_json(args.policy)
    transfer = load_json(args.transfer)
    external = load_json(args.external_bar)
    prospective = load_json(args.prospective)

    policy_vs_f100 = nested(policy, "panel_comparisons", "overall", "f100_mean_family_p") or {}
    policy_vs_raw = nested(policy, "panel_comparisons", "overall", "raw_panel_p") or {}
    policy_source = nested(policy, "panel_comparisons", "by_source") or {}
    transfer_verdict = str(transfer.get("verdict") or "")
    transfer_a = nested(transfer, "transfers", "source_balanced_to_translation_tournament", "panel_comparisons", "translated_vs_f100_mean_family") or {}
    transfer_b = nested(transfer, "transfers", "translation_tournament_to_source_balanced", "panel_comparisons", "translated_vs_f100_mean_family") or {}
    transfer_promotable = [
        bool(nested(transfer, "transfers", "source_balanced_to_translation_tournament", "promotable")),
        bool(nested(transfer, "transfers", "translation_tournament_to_source_balanced", "promotable")),
    ]
    external_vs_market = nested(external, "comparisons", "translated_vs_market") or {}
    external_vs_f100 = nested(external, "comparisons", "translated_vs_f100") or {}
    blend_vs_market = nested(external, "comparisons", "half_blend_vs_market") or {}
    prospective_resolution = prospective.get("resolution") if isinstance(prospective.get("resolution"), dict) else {}

    gates = [
        {
            "gate": "same_packet_policy_beats_f100",
            "required": "delta <= -0.01 and p <= 0.05",
            "passed": pass_delta_p(policy_vs_f100),
            "evidence": {
                "n": n(policy_vs_f100),
                "delta": delta(policy_vs_f100),
                "p": p_value(policy_vs_f100),
            },
            "failure_mode": "directional_but_p_above_gate" if delta(policy_vs_f100) is not None and delta(policy_vs_f100) <= -0.01 else "insufficient_lift",
        },
        {
            "gate": "same_packet_policy_beats_raw",
            "required": "delta <= -0.01 and p <= 0.05",
            "passed": pass_delta_p(policy_vs_raw),
            "evidence": {
                "n": n(policy_vs_raw),
                "delta": delta(policy_vs_raw),
                "p": p_value(policy_vs_raw),
            },
        },
        {
            "gate": "no_source_regression_vs_f100",
            "required": "all source-split translated-minus-F100 deltas <= 0",
            "passed": not source_regressions(policy_source, "f100_mean_family_p"),
            "evidence": {
                "regressions": source_regressions(policy_source, "f100_mean_family_p"),
                "sources": sorted(policy_source),
            },
        },
        {
            "gate": "cross_packet_bidirectional_transfer",
            "required": "both frozen packet transfer directions promotable",
            "passed": all(transfer_promotable),
            "evidence": {
                "verdict": transfer_verdict,
                "source_balanced_to_tournament": {
                    "promotable": transfer_promotable[0],
                    "n": n(transfer_a),
                    "delta": delta(transfer_a),
                    "p": p_value(transfer_a),
                },
                "tournament_to_source_balanced": {
                    "promotable": transfer_promotable[1],
                    "n": n(transfer_b),
                    "delta": delta(transfer_b),
                    "p": p_value(transfer_b),
                },
            },
        },
        {
            "gate": "joined_market_control",
            "required": "translated and predeclared blend beat market-only with p <= 0.05",
            "passed": pass_delta_p(external_vs_market) and pass_delta_p(blend_vs_market),
            "evidence": {
                "translated_vs_market": {
                    "n": n(external_vs_market),
                    "delta": delta(external_vs_market),
                    "p": p_value(external_vs_market),
                },
                "translated_vs_f100": {
                    "n": n(external_vs_f100),
                    "delta": delta(external_vs_f100),
                    "p": p_value(external_vs_f100),
                },
                "half_blend_vs_market": {
                    "n": n(blend_vs_market),
                    "delta": delta(blend_vs_market),
                    "p": p_value(blend_vs_market),
                },
            },
        },
        {
            "gate": "prospective_causal_order_resolved",
            "required": "resolved prospective packet with scoreable outcome rows",
            "passed": str(prospective.get("verdict")) != "not_ready_unresolved_markets"
            and int(prospective.get("valid_call_observations") or 0) > 0,
            "evidence": {
                "verdict": prospective.get("verdict"),
                "valid_call_observations": prospective.get("valid_call_observations"),
                "resolved_pairs": prospective_resolution.get("resolved_pairs"),
                "total_pairs": prospective_resolution.get("total_pairs"),
                "exclusion_reasons": prospective.get("exclusion_reasons"),
            },
        },
    ]
    failed = [gate for gate in gates if not gate["passed"]]
    verdict = "f47_pairwise_ranking_only_not_production_probability"
    if not failed:
        verdict = "f47_production_probability_ready"
    return {
        "schema": "gp245-f47-production-readiness-audit-v1",
        "inputs": {
            "policy": repo_rel(args.policy),
            "transfer": repo_rel(args.transfer),
            "external_bar": repo_rel(args.external_bar),
            "prospective": repo_rel(args.prospective),
        },
        "verdict": verdict,
        "production_ready": not failed,
        "gates": gates,
        "failed_gates": [gate["gate"] for gate in failed],
        "paper_claim_boundary": {
            "writeable_claim": (
                "F47 is a source-heldout pairwise/ranking primitive with promising "
                "translation evidence; it is not a deployed absolute-probability layer."
            ),
            "forbidden_overclaim": "F47 translated probabilities beat markets or should replace F100/raw in production.",
            "next_action": "Wait for prospective market-freeze outcomes and/or filled equal-information bars before new F47 probability calls.",
        },
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "f47_production_readiness_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# F47 Production Readiness Audit",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Production ready: `{report['production_ready']}`",
        f"- Failed gates: `{report['failed_gates']}`",
        "",
        "## Gates",
        "",
        "| gate | passed | evidence |",
        "|---|---:|---|",
    ]
    for gate in report["gates"]:
        lines.append(
            f"| `{gate['gate']}` | `{gate['passed']}` | `{json.dumps(gate['evidence'], sort_keys=True)}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Writeable: {report['paper_claim_boundary']['writeable_claim']}",
            f"- Forbidden: {report['paper_claim_boundary']['forbidden_overclaim']}",
            f"- Next: {report['paper_claim_boundary']['next_action']}",
            "",
        ]
    )
    (out_dir / "f47_production_readiness_audit.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--transfer", type=Path, default=DEFAULT_TRANSFER)
    parser.add_argument("--external-bar", type=Path, default=DEFAULT_EXTERNAL_BAR)
    parser.add_argument("--prospective", type=Path, default=DEFAULT_PROSPECTIVE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args)
    write_outputs(report, args.out_dir)
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "production_ready": report["production_ready"],
                "failed_gates": report["failed_gates"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
