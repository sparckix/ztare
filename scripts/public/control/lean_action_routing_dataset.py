#!/usr/bin/env python3
"""Build a Lean action-routing dataset from governed decider checkpoints.

This ports the epistemic-generation native-routing discipline to the
Lean proof-search arc. The unit is not "did a prompt sound better"; it
is an action-selection row with:
  - visible packet: pre/outcome-free row metadata only
  - hidden key: which action family actually paid off under governance
  - candidate actions: same pool for every row
  - abstain/defer: explicit valid action when no observed arm worked

No solver is run here. This is measurement-only scaffolding for a later
sealed routing-policy experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_CKPT = "/tmp/rung1/four_arm_decider_ckpt.jsonl"
DEFAULT_OUT_DIR = "/tmp/rung1/lean_action_routing"
DEFAULT_CORPUS = "/tmp/rung1/four_arm_frozen_corpus.json"
CANDIDATE_ACTIONS = [
    "use_governed_static_agentic",
    "use_feedback_agentic",
    "defer_or_abstain",
]
EXTERNAL_ACTION = "use_external_backend_adapter"
OUTCOME_KEYS = {
    "verdict", "ratified", "exact_gap", "axiom_smuggled",
    "governance_kill", "wrong_target_kind", "manual_edits", "reason",
    "verified_by", "trace_dir", "calls", "secs", "first_verdict",
    "recovered_after_first_failure",
}


def _sha_obj(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _stable_split(unit_id: str) -> str:
    # Deterministic; enough for dataset hygiene, not a claim of held-out
    # validity. Future sealed runs may override.
    h = int(hashlib.sha1(unit_id.encode()).hexdigest()[:8], 16) % 10
    if h < 6:
        return "train"
    if h < 8:
        return "dev"
    return "eval"


def _load_frozen_corpus(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text())
    rows = data.get("rows") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return {}
    return {str(r.get("id")): r for r in rows if isinstance(r, dict) and r.get("id")}


def _target_statement_features(corpus_row: dict[str, Any] | None) -> dict[str, Any]:
    if not corpus_row:
        return {}
    name = str(corpus_row.get("target_name") or "")
    source = Path(str(corpus_row.get("sorried_file") or ""))
    line_no = int(corpus_row.get("target_line") or 0)
    window = ""
    if source.exists() and line_no > 0:
        lines = source.read_text(errors="ignore").splitlines()
        start = max(0, line_no - 1)
        end = min(len(lines), start + 20)
        block: list[str] = []
        for line in lines[start:end]:
            block.append(line)
            if ":= by" in line or " by" == line.strip()[-3:]:
                break
        window = "\n".join(block)
    text = f"{name}\n{window}".lower()
    return {
        "target_name_len": len(name),
        "target_stmt_chars": len(window),
        "target_stmt_lines": len([ln for ln in window.splitlines() if ln.strip()]),
        "has_forall_token": int("∀" in window or "forall" in text),
        "has_exists_token": int("∃" in window or "exists" in text),
        "has_sum_token": int(any(s in text for s in ("sum", "finset", "range"))),
        "has_tendsto_token": int("tendsto" in text or "filter" in text),
        "has_integral_token": int(any(s in text for s in ("integral", "integrable", "mellin", "convolution"))),
        "has_order_token": int(any(s in text for s in ("≤", "<", "_le_", "_lt_", "bound", "mono"))),
        "has_nat_int_token": int(any(s in text for s in ("nat", "int", "finset", "range"))),
        "has_real_norm_token": int(any(s in text for s in ("real", "norm", "nnnorm", "ennreal"))),
        "arrow_count": window.count("→") + window.count("->"),
        "binder_count": len(re.findall(r"\([^)]*:\s*[^)]*\)", window)),
    }


def _visible_packet(row: dict[str, Any],
                    corpus_row: dict[str, Any] | None = None) -> dict[str, Any]:
    stmt_features = _target_statement_features(corpus_row)
    # Gold proof length is excluded: it was a calibration convenience,
    # not production-available routing information.
    return {
        "unit_id": row["id"],
        "row_id_hash": hashlib.sha256(row["id"].encode()).hexdigest()[:16],
        "available_actions": list(CANDIDATE_ACTIONS),
        "visible_features": {
            "id_prefix": row["id"].split("_", 2)[:2],
            "has_integral_word": int("Integrable" in row["id"]
                                     or "mellin" in row["id"].lower()
                                     or "convolution" in row["id"].lower()),
            "has_inequality_word": int(any(
                s in row["id"].lower()
                for s in ("lt", "le", "bound", "mean", "lp"))),
            **stmt_features,
        },
        "forbidden_visible_fields": sorted(OUTCOME_KEYS | {"gold"}),
    }


def _external_by_row(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    out: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        out[str(rec.get("row_id"))] = rec
    return out


def _features_by_row(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("status") == "ok" and isinstance(rec.get("features"), dict):
            out[str(rec.get("row_id"))] = rec["features"]
    return out


def _valid_actions(row: dict[str, Any], ext: dict[str, Any] | None,
                   actions: list[str]) -> tuple[list[str], str]:
    b = row.get("B1gs") or row.get("B_static") or {}
    a = row.get("A") or row.get("A_feedback") or {}
    b_ok = bool(b.get("ratified") or b.get("verdict") == "closure")
    a_ok = bool(a.get("ratified") or a.get("verdict") == "closure")
    ext_ok = bool(ext and ext.get("ratified"))
    valid: list[str] = []
    if b_ok:
        valid.append("use_governed_static_agentic")
    if a_ok:
        valid.append("use_feedback_agentic")
    if EXTERNAL_ACTION in actions and ext_ok:
        valid.append(EXTERNAL_ACTION)
    if len(valid) > 1:
        return valid, "multiple_actions_close"
    if len(valid) == 1:
        if valid[0] == "use_feedback_agentic":
            return valid, "feedback_only_win"
        if valid[0] == "use_governed_static_agentic":
            return valid, "static_only_win"
        return valid, "external_backend_only_win"
    if EXTERNAL_ACTION in actions and ext and not ext_ok:
        # Adapter was actually tried and did not close. Defer is the
        # honest action if no observed action closed.
        return ["defer_or_abstain"], "no_observed_action_closes"
    if a_ok and not b_ok:
        return ["use_feedback_agentic"], "feedback_only_win"
    if b_ok and not a_ok:
        return ["use_governed_static_agentic"], "static_only_win"
    if a_ok and b_ok:
        return ["use_governed_static_agentic", "use_feedback_agentic"], "either_closes"
    return ["defer_or_abstain"], "no_observed_action_closes"


def build(ckpt: Path, out_dir: Path, external_results: Path | None = None,
          corpus: Path | None = None,
          proofstate_features: Path | None = None) -> dict[str, Any]:
    rows = _load_jsonl(ckpt)
    ext_by_row = _external_by_row(external_results)
    corpus_by_row = _load_frozen_corpus(corpus)
    ps_by_row = _features_by_row(proofstate_features)
    actions = list(CANDIDATE_ACTIONS)
    if ext_by_row and EXTERNAL_ACTION not in actions:
        actions.insert(2, EXTERNAL_ACTION)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_p = out_dir / "lean_routing_manifest.jsonl"
    key_p = out_dir / "lean_routing_key.jsonl"
    policy_p = out_dir / "lean_routing_policy_classes.json"
    summary_p = out_dir / "lean_routing_summary.json"

    manifest_rows: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []
    for row in rows:
        unit_id = row["id"]
        visible = _visible_packet(row, corpus_by_row.get(unit_id))
        if unit_id in ps_by_row:
            visible["visible_features"].update({
                f"ps_{k}": v for k, v in ps_by_row[unit_id].items()
                if k != "type_head_top"
            })
            top = ps_by_row[unit_id].get("type_head_top") or {}
            if isinstance(top, dict):
                for head, n in list(top.items())[:8]:
                    safe = re.sub(r"[^A-Za-z0-9_]", "_", str(head)).strip("_")
                    if safe:
                        visible["visible_features"][f"ps_type_{safe}"] = int(n)
        visible["available_actions"] = list(actions)
        ext = ext_by_row.get(unit_id)
        valid, route = _valid_actions(row, ext, actions)
        invalid = [a for a in actions if a not in valid]
        hidden = {
            "unit_id": unit_id,
            "gold_route_class": route,
            "valid_actions": valid,
            "invalid_actions": invalid,
            "gold_n_steps": row.get("gold"),
            "arm_outcomes": {
                "B1gs": {k: (row.get("B1gs") or {}).get(k)
                         for k in ("verdict", "ratified", "reason",
                                   "calls", "secs")},
                "A": {k: (row.get("A") or {}).get(k)
                      for k in ("verdict", "ratified", "reason",
                                "calls", "secs")},
            },
            "external_backend_outcome": ext,
        }
        manifest_rows.append({
            "unit_id": unit_id,
            "status": "measurement_only_from_completed_decider",
            "source_ckpt": str(ckpt),
            "split": _stable_split(unit_id),
            "claim_scope": "measurement_only",
            "visible_packet": visible,
            "visible_packet_hash": _sha_obj(visible),
            "hidden_label_hash": _sha_obj(hidden),
            "candidate_actions": list(actions),
            "abstain_allowed": True,
            "defer_allowed": True,
            "ambiguity_class": ("multi_valid" if route == "either_closes"
                                else "unique"),
            "baseline_contract": {
                "candidate_pool_hash": _sha_obj(actions),
                "visible_fields": sorted(visible.keys()),
                "action_budget": 1,
                "abstain_enabled": True,
                "defer_enabled": True,
                "uses_primitive_features": False,
            },
            "decoy_metadata": {
                "same_source_family": True,
                "same_specificity": True,
                "same_arity": True,
                "same_text_length_bucket": True,
                "same_obligation_type": True,
                "plausibility_score_blinded": "not_yet_human_scored",
            },
            "candidate_notes": (
                "Derived from governed A-vs-B1gs decider. Visible packet "
                "excludes outcomes and gold_n_steps; hidden key stores route."
            ),
        })
        key_rows.append(hidden)

    for row in manifest_rows:
        leak_packet = dict(row["visible_packet"])
        leak_packet.pop("forbidden_visible_fields", None)
        blob = json.dumps(leak_packet, sort_keys=True)
        leaked = sorted(k for k in OUTCOME_KEYS | {"gold"} if k in blob)
        if leaked:
            raise SystemExit(f"visible packet leaks outcome fields: {row['unit_id']} {leaked}")
    manifest_p.write_text("\n".join(json.dumps(r, sort_keys=True) for r in manifest_rows) + "\n")
    key_p.write_text("\n".join(json.dumps(r, sort_keys=True) for r in key_rows) + "\n")
    policies = {
        "status": "design_only_not_run",
        "primary_question": (
            "Can a routing policy choose static, feedback, or defer better "
            "than non-semantic and text/generic controls under equal action budget?"
        ),
        "policy_classes": [
            {"policy_id": "P0_majority_static", "kind": "non_semantic_baseline",
             "allowed_inputs": ["route_prior_counts"], "claim_role": "control"},
            {"policy_id": "P1_visible_text_features", "kind": "feature_baseline",
             "allowed_inputs": ["visible_packet.visible_features"], "claim_role": "strong_control"},
            {"policy_id": "P2_generic_reasoning", "kind": "llm_generic_control",
             "allowed_inputs": ["visible_packet"], "claim_role": "generic_metacognition_control"},
            {"policy_id": "P3_feedback_selector", "kind": "catalog_or_rule_policy",
             "allowed_inputs": ["visible_packet", "candidate_actions"], "claim_role": "primary_test"},
            {"policy_id": "P4_selective_defer", "kind": "calibrated_abstain_defer",
             "allowed_inputs": ["best_policy_confidence", "coverage_target"],
             "claim_role": "selective_utility_only"},
        ],
        "support_rule": (
            "Primary policy must beat P0/P1/P2 at fixed action budget; P4 "
            "only claims selective utility at fixed coverage and defer cost."
        ),
    }
    policy_p.write_text(json.dumps(policies, indent=1, sort_keys=True) + "\n")
    counts = Counter(k["gold_route_class"] for k in key_rows)
    split_counts = Counter(m["split"] for m in manifest_rows)
    summary = {
        "ckpt": str(ckpt),
        "out_dir": str(out_dir),
        "n": len(rows),
        "candidate_actions": actions,
        "external_results": str(external_results) if external_results else None,
        "corpus": str(corpus) if corpus else None,
        "proofstate_features": str(proofstate_features) if proofstate_features else None,
        "corpus_features_rows": sum(
            1 for r in manifest_rows
            if (r["visible_packet"].get("visible_features") or {}).get("target_stmt_chars")
        ),
        "proofstate_features_rows": sum(
            1 for r in manifest_rows
            if "ps_goal_chars" in (r["visible_packet"].get("visible_features") or {})
        ),
        "gold_route_counts": dict(counts),
        "split_counts": dict(split_counts),
        "files": {
            "manifest": str(manifest_p),
            "key": str(key_p),
            "policies": str(policy_p),
            "summary": str(summary_p),
        },
        "claim_scope": "measurement_only",
    }
    summary_p.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ckpt = root / "ckpt.jsonl"
        rows = [
            {"id": "R_static", "gold": 3,
             "B1gs": {"verdict": "closure", "ratified": 1},
             "A": {"verdict": "open", "ratified": 0}},
            {"id": "R_feedback", "gold": 3,
             "B1gs": {"verdict": "open", "ratified": 0},
             "A": {"verdict": "closure", "ratified": 1}},
            {"id": "R_either", "gold": 3,
             "B1gs": {"verdict": "closure", "ratified": 1},
             "A": {"verdict": "closure", "ratified": 1}},
            {"id": "R_none", "gold": 3,
             "B1gs": {"verdict": "open", "ratified": 0},
             "A": {"verdict": "open", "ratified": 0}},
        ]
        ckpt.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        ext = root / "ext.jsonl"
        ext.write_text(json.dumps({
            "row_id": "R_none",
            "action": EXTERNAL_ACTION,
            "status": "closure",
            "ratified": 1,
        }) + "\n")
        corpus = root / "corpus.json"
        src = root / "r_feedback.lean"
        src.write_text("theorem demo_feedback (n : Nat) : n = n := by\n  sorry\n")
        corpus.write_text(json.dumps({
            "rows": [
                {"id": "R_feedback", "sorried_file": str(src),
                 "target_line": 1, "target_name": "demo_feedback"}
            ]
        }) + "\n")
        ps = root / "ps.jsonl"
        ps.write_text(json.dumps({
            "row_id": "R_feedback",
            "status": "ok",
            "features": {"goal_chars": 10, "hyp_count": 1,
                         "type_head_top": {"Nat": 1}},
        }) + "\n")
        s = build(ckpt, root / "out", ext, corpus, ps)
        assert s["gold_route_counts"]["static_only_win"] == 1
        assert s["gold_route_counts"]["feedback_only_win"] == 1
        assert s["gold_route_counts"]["multiple_actions_close"] == 1
        assert s["gold_route_counts"]["external_backend_only_win"] == 1
        assert s["corpus_features_rows"] == 1
        assert s["proofstate_features_rows"] == 1
        m = (root / "out" / "lean_routing_manifest.jsonl").read_text()
        assert "\"gold\":" not in m
        assert "\"verdict\":" not in m
        assert "\"ratified\":" not in m
    print("lean_action_routing_dataset self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default=DEFAULT_CKPT)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--external-results",
                    help="Optional JSONL from external_backend_adapter_smoke.py")
    ap.add_argument("--corpus", default=DEFAULT_CORPUS,
                    help="Optional frozen corpus JSON for pre-attempt target features")
    ap.add_argument("--proofstate-features",
                    help="Optional JSONL from lean_proofstate_feature_extract.py")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    summary = build(Path(args.ckpt), Path(args.out_dir),
                    Path(args.external_results) if args.external_results else None,
                    Path(args.corpus) if args.corpus else None,
                    Path(args.proofstate_features) if args.proofstate_features else None)
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
