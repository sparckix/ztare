"""Worldmodel AuditBattery — today's proven hand-run audits as a Strategy Office
substrate plug-in (deterministic, no LLM; see research_director.strategy_office).

Every audit is parameterized from evidence — roles and spec, never level
constants. The receipts are SUMMARY-shaped (counts + a few exemplars): the leaf
reasons about the law, the deterministic gates keep the full log off disk.

Audits (the conductor's by-hand battery, mechanized):
  * novelty_decay        — new abstract object-states per K-row segment + a
    Good-Turing estimate of unseen mass, under the CAP-HORIZON caveat (the log
    is sampled only within the row cap; the true tail past the cap is unknown).
  * conditional_coverage — distinct agent positions per indicator-flag config;
    the audit that finds the "1-position both-flags hole" (a multi-flag config
    witnessed at a single position cannot separate a goal from a coincidence).
  * event_context        — indicator-flag combos at env frames (deaths/resets).
  * ledger_closure       — undispositioned operator/strategy cards + abduced
    goal candidates still open.
  * sweep_horizon        — the horizon resource's bar length and the sweep caps.
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from ztare.common.operator_proposal_contract import open_cards
from ztare.worldmodel.episode_log import EpisodeLog, Transition
from ztare.worldmodel.cycle_enumeration import cycles_from_evidence
from ztare.worldmodel.gates import env_frame_indices
from ztare.worldmodel.goal_abduction import (
    _horizon_resource, _indicator_regions, _norm_spec, _region, _region_changed,
    abduce_goal_candidates,
)
from ztare.worldmodel.grid_dsl import grid_from_lists
from ztare.worldmodel.object_roles import (
    induce_roles, object_signature, sound_signature, volatile_positions,
)

ROW_CAP_ENV = "ZTARE_STRATEGY_BATTERY_ROW_CAP"
_DEFAULT_ROW_CAP = 1000
_DEFAULT_SEGMENT = 100
# reachability_sweep defaults, reported as the horizon cap (kept in sync by name)
_SWEEP_MAX_STATES = 200000
_SWEEP_MAX_DEPTH = 400
_PROMPT_SURFACES = (
    "current_iteration.md",
    "thesis.md",
    "project_charter.md",
    "workspace/latest_loop_event.json",
    "workspace/latest_sprint_receipt.json",
)
_STRUCTURED_ROLE_SURFACES = (
    "workspace/latest_loop_event.json",
    "workspace/latest_sprint_receipt.json",
    "workspace/latest_level_transfer_probe.json",
    "workspace/arc3_play_loop_report.json",
    "workspace/mutator_briefing_projection_latest.json",
)
_KERNEL_ROLE_NAMES = {
    "verification",
    "representation",
    "compression",
    "counterexample_routing",
    "memory",
    "search_control",
    "model_update",
    "selection",
    "write_back",
}
_LEXICAL_KERNEL_ROLE_HINTS = {
    "accept": "write_back", "adopt": "write_back", "author": "write_back",
    "certifies": "verification", "certify": "verification",
    "decide": "selection", "decides": "selection",
    "compress": "compression", "compresses": "compression",
    "deanchor": "representation", "deanchors": "representation",
    "factor": "representation", "factors": "representation",
    "gate": "verification", "gates": "verification",
    "hash": "representation", "hashes": "representation",
    "index": "memory", "indexes": "memory",
    "judge": "verification", "judges": "verification",
    "learn": "model_update",
    "normalize": "representation", "normalizes": "representation",
    "partition": "counterexample_routing", "partitions": "counterexample_routing",
    "promote": "write_back", "promotes": "write_back",
    "quotient": "compression", "quotients": "compression",
    "rank": "selection", "ranks": "selection",
    "recall": "memory", "recalls": "memory",
    "refine": "model_update", "refines": "model_update",
    "retrieve": "memory", "retrieves": "memory",
    "score": "verification", "scores": "verification",
    "select": "selection", "selects": "selection",
    "split": "representation", "splits": "representation",
    "steer": "search_control", "steers": "search_control",
    "teach": "model_update", "teaches": "model_update",
    "update": "model_update", "updates": "model_update",
    "verify": "verification", "verifies": "verification",
    "write": "write_back", "writes": "write_back",
}
_LEXICAL_ROLE_HINT_TOKENS = set(_LEXICAL_KERNEL_ROLE_HINTS)
_STOP_TERMS = {
    "action", "actions", "candidate", "candidates", "cell", "cells", "code",
    "abduce_spec", "artifact", "completed", "contains", "current", "data",
    "deterministic", "detail", "details", "diagnostic",
    "diagnostics", "evidence", "exact", "failed", "failure", "field", "file",
    "frame", "frames", "gate", "gates", "grid", "harmless", "holdout",
    "kernel", "law", "level", "levels", "local", "log", "model", "must",
    "only", "operator", "pass", "passes", "path", "predictions", "prefix",
    "produce", "project", "proposed", "provider", "reading", "receipt",
    "receipts", "replay", "result", "results", "rollout", "row", "rows",
    "run", "same", "score", "scored", "solve", "source", "spurious",
    "state", "states", "submission",
    "submissions", "test", "tests", "this", "three", "transition",
    "transitions", "tuple", "type", "used", "value", "visible", "where",
    "workspace", "world",
}


def _strip_prompt_noise(text: str) -> str:
    """Keep prose/receipts, not embedded carrier code.

    `current_iteration.md` often embeds a whole `test_model.py`. The strategy
    office should deanchor concepts, not Python syntax tokens.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    kept = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            kept.append("")
            continue
        if s.startswith(("#", "-", "*", ">")):
            kept.append(line)
            continue
        if re.match(r"(def|class|return|if|elif|else|for|while|try|except|with)\b", s):
            continue
        if any(sym in s for sym in ("=", "lambda", "tuple(", "range(", "len(", "assert ")):
            continue
        kept.append(line)
    return "\n".join(kept)


def _row_cap() -> int:
    try:
        return max(50, int(os.environ.get(ROW_CAP_ENV, _DEFAULT_ROW_CAP)))
    except ValueError:
        return _DEFAULT_ROW_CAP


def _load_capped(project: "Path | str", cap: "int | None" = None,
                 path: "Path | None" = None) -> "list[Transition]":
    """Stream up to ``cap`` transitions from the episode log — never a full read
    of the (multi-hundred-MB) raw log. The cap IS the CAP-HORIZON sampling bound."""
    from ztare.worldmodel.adapter import episode_log_path
    cap = cap or _row_cap()
    path = Path(path) if path is not None else Path(episode_log_path(project))
    if not path.exists():
        return []
    rows: "list[Transition]" = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                rows.append(Transition(d["t"], grid_from_lists(d["s"]), d["a"],
                                       grid_from_lists(d["s_next"])))
            except Exception:  # noqa: BLE001 — a corrupt row is skipped, not fatal
                continue
            if len(rows) >= cap:
                break
    return rows


def _last_spec(project: "Path | str") -> dict:
    path = Path(project) / "workspace" / "spec_receipts.jsonl"
    if not path.exists():
        return {}
    last = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            last = json.loads(line)
        except json.JSONDecodeError:
            continue
    return _norm_spec((last or {}).get("spec")) if last else {}


def _action_arity(rows: "list[Transition]") -> int:
    return (max((tr.a for tr in rows), default=3) + 1) if rows else 4


def _regions(spec: dict, roles, start_grid) -> "list[tuple]":
    """Indicator flag cell-sets from the spec's region_events; fall back to
    indicator-role cells at the start grid. No level constants."""
    regs = _indicator_regions(spec)
    if regs:
        return regs
    role_by = {getattr(r, "name", None): r for r in getattr(roles, "roles", roles) or []}
    members: set = set()
    for name in ("covered_uncovered", "static_structural_mirror"):
        r = role_by.get(name)
        for m in (getattr(r, "members", []) if r else []):
            if isinstance(m, int):
                members.add(m)
            elif isinstance(m, (list, tuple)):
                members.update(x for x in m if isinstance(x, int))
    if not members or not start_grid:
        return []
    cells = tuple(sorted((y, x) for y in range(len(start_grid))
                         for x in range(len(start_grid[0])) if start_grid[y][x] in members))
    return [cells] if cells else []


# ── the five audits ──────────────────────────────────────────────────────────

def _novelty_decay(rows, k: int = _DEFAULT_SEGMENT) -> dict:
    log = EpisodeLog(rows)
    vp = volatile_positions(log)
    states = [sound_signature(tr.s, vp) for tr in rows]
    counts = Counter(states)
    seen: set = set()
    per_segment: "list[dict]" = []
    for start in range(0, len(states), k):
        seg = states[start:start + k]
        new = sum(1 for s in seg if s not in seen)
        seen.update(seg)
        per_segment.append({"segment": start // k, "rows": len(seg), "new_states": new})
    n1 = sum(1 for _s, c in counts.items() if c == 1)
    n = len(states)
    last_rate = (per_segment[-1]["new_states"] / max(1, per_segment[-1]["rows"])) if per_segment else 0.0
    return {
        "segment_size_k": k,
        "distinct_states": len(counts),
        "per_segment_new": per_segment,
        "last_segment_new_rate": round(last_rate, 4),
        "good_turing_unseen_mass": round(n1 / n, 4) if n else 0.0,
        "caveat": "CAP-HORIZON: estimate valid only within the sampled row cap; "
                  "the tail past the cap is adversarial-unknown.",
    }


def _conditional_coverage(rows, spec, roles, *, min_flags: int = 2) -> dict:
    if not rows:
        return {"regions": 0, "holes": []}
    start = rows[0].s
    regions = _regions(spec, roles, start)
    roleseq = getattr(roles, "roles", roles)
    config_positions: "dict[tuple, set]" = defaultdict(set)
    for tr in rows:
        g = tr.s
        config = tuple(_region_changed(g, start, cells) for cells in regions)
        agent = object_signature(g, roleseq)[0]
        config_positions[config].add(agent)
    holes = []
    for config, positions in config_positions.items():
        if sum(config) >= min_flags and len(positions) == 1:
            holes.append({"config": _cfg_str(config), "positions_witnessed": 1})
    return {
        "regions": len(regions),
        "configs_witnessed": len(config_positions),
        "multiflag_configs": sum(1 for c in config_positions if sum(c) >= min_flags),
        "min_flags": min_flags,
        "one_position_multiflag_holes": holes[:20],
    }


def _event_context(rows, spec, roles, *, top: int = 10) -> dict:
    log = EpisodeLog(rows)
    env = sorted(env_frame_indices(log))
    if not rows:
        return {"env_frames": 0, "flag_configs_at_env_frames": {}}
    start = rows[0].s
    regions = _regions(spec, roles, start)
    tally: Counter = Counter()
    for i in env:
        cfg = tuple(_region_changed(rows[i].s, start, cells) for cells in regions)
        tally[_cfg_str(cfg)] += 1
    return {
        "env_frames": len(env),
        "regions": len(regions),
        "flag_configs_at_env_frames": dict(tally.most_common(top)),
    }


def _ledger_closure(project, rows, spec, roles) -> dict:
    ws = Path(project) / "workspace"
    open_ops = open_cards(ws / "operator_proposals.jsonl")
    open_strat = open_cards(ws / "strategy_experiments.jsonl")
    goal = abduce_goal_candidates(EpisodeLog(rows), spec, roles) if rows else {}
    cand_kinds = Counter(c.get("kind") for c in goal.get("candidates", []))
    return {
        "open_operator_cards": len(open_ops),
        "open_strategy_cards": len(open_strat),
        "open_operator_families": [c.get("failure_family") for c in open_ops][:15],
        "goal_abduction_mode": goal.get("mode"),
        "goal_candidate_kinds": dict(cand_kinds),
        "goal_candidates_undispositioned": sum(cand_kinds.values()),
    }


def _sweep_horizon(rows) -> dict:
    resource = _horizon_resource(rows) if rows else None
    bar = 0
    if resource is not None:
        bar = max((sum(1 for row in tr.s for c in row if c == resource) for tr in rows), default=0)
    return {
        "horizon_resource_color": resource,
        "horizon_bar_length": bar,
        "sweep_max_states": _SWEEP_MAX_STATES,
        "sweep_max_depth": _SWEEP_MAX_DEPTH,
        "note": "bounded object-space sweep caps (reachability_sweep); a bar of "
                "length H bounds remaining actions to H.",
    }


def _prompt_surface_text(project: "Path | str", *, max_chars: int = 120000) -> str:
    root = Path(project)
    chunks = []
    budget = max_chars
    for rel in _PROMPT_SURFACES:
        path = root / rel
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        if not text.strip():
            continue
        take = _strip_prompt_noise(text[:budget])
        chunks.append(f"\n@@ {rel}\n{take}")
        budget -= len(take)
        if budget <= 0:
            break
    return "\n".join(chunks)


def _typed_kernel_role_pressure(project: "Path | str") -> dict:
    """Read explicit concept→kernel-role bindings from structured receipts.

    This is the preferred carrier. Producers should emit e.g.
    ``{"kernel_role_bindings": [{"term": "reward", "roles": ["verification",
    "model_update"]}]}`` so Strategy Office does not infer roles from prose.
    """
    root = Path(project)
    by_term: dict[str, dict] = {}
    for rel in _STRUCTURED_ROLE_SURFACES:
        path = root / rel
        if not path.exists() or not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for binding in _extract_kernel_role_bindings(payload):
            term = str(binding.get("term") or "").strip().lower()
            roles = _coerce_kernel_roles(binding.get("roles") or binding.get("kernel_roles"))
            if not term or len(roles) < 2:
                continue
            rec = by_term.setdefault(term, {
                "term": term,
                "method": "typed_kernel_role_binding",
                "kernel_roles": set(),
                "sources": [],
                "examples": [],
            })
            rec["kernel_roles"].update(roles)
            rec["sources"].append(rel)
            if binding.get("evidence"):
                rec["examples"].append(str(binding.get("evidence"))[:220])
    suspects = []
    for term, rec in sorted(by_term.items()):
        roles = sorted(rec["kernel_roles"])
        if len(roles) < 2:
            continue
        suspects.append({
            "term": term,
            "method": "typed_kernel_role_binding",
            "kernel_roles": roles,
            "sources": sorted(set(rec["sources"])),
            "examples": rec["examples"][:3],
            "deanchor_seam": _deanchor_seam(term),
        })
    return {
        "suspects": suspects,
        "firing_signal": min(1.0, len(suspects) / 3.0),
        "method": "typed_kernel_role_binding",
    }


def _extract_kernel_role_bindings(obj) -> list[dict]:
    out = []
    if isinstance(obj, dict):
        for key in ("kernel_role_bindings", "semantic_deanchor_bindings"):
            val = obj.get(key)
            if isinstance(val, list):
                out.extend(x for x in val if isinstance(x, dict))
        term = obj.get("term") or obj.get("local_term") or obj.get("concept")
        roles = obj.get("kernel_roles") or obj.get("roles")
        if term and roles:
            out.append({"term": term, "roles": roles, "evidence": obj.get("evidence")})
        for val in obj.values():
            if isinstance(val, (dict, list)):
                out.extend(_extract_kernel_role_bindings(val))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_extract_kernel_role_bindings(item))
    return out


def _coerce_kernel_roles(raw) -> set[str]:
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        return set()
    return {str(x).strip() for x in items if str(x).strip() in _KERNEL_ROLE_NAMES}


def _deanchor_seam(term: str) -> dict:
    return {
        "constraint_class": (
            "substrate-local concept appears to carry a kernel role "
            "such as verification, representation, compression, "
            "counterexample routing, memory, search control, or "
            "write-back"
        ),
        "abstract_form": (
            "local term should be split into its substrate-invariant "
            "roles before code changes: verifier/event, witness, "
            "counterexample class, representation quotient, retrieval "
            "key, model-update, reusable advice, and write-back gate"
        ),
        "home_field": "interactive worldmodel prompt vocabulary",
        "local_term": term,
    }


def _semantic_deanchor_pressure(project: "Path | str", *, window: int = 6) -> dict:
    """Detect local concepts that may be doing kernel work in prompt surfaces.

    This is a Strategy Office trigger, not a conclusion. The current path is a
    lexical fallback: it only names terms whose local vocabulary appears near
    multiple kernel-role hints, then emits an operator-neutral seam skeleton for
    deanchored isomorphism work. The promotion path is typed role bindings /
    projection receipts first, semantic atlas retrieval second, lexical last.
    """
    typed = _typed_kernel_role_pressure(project)
    if typed.get("suspects"):
        typed["rule"] = (
            "strategy-office trigger only; typed role bindings/projection "
            "receipts are the preferred carrier. Run primitive_amnesia/"
            "research_isomorphism before adding substrate-specific machinery; "
            "accept only receipt schemas, invariants, quotients, or tests"
        )
        typed["preferred_future_carrier"] = (
            "typed_kernel_role_bindings + semantic_atlas_retrieval; lexical "
            "hints only cold-start the question"
        )
        return typed

    text = _prompt_surface_text(project)
    if not text:
        typed["rule"] = (
            "no typed role bindings and no prompt text; no deanchor trigger"
        )
        return typed
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_:-]{2,}", text)
    lowered = [t.lower().strip("_:-") for t in tokens]
    counts: Counter = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    roles_by_term: dict[str, set[str]] = defaultdict(set)
    for i, tok in enumerate(lowered):
        if tok in _STOP_TERMS or len(tok) < 4 or tok.isdigit():
            continue
        if tok in _LEXICAL_ROLE_HINT_TOKENS:
            continue
        if "_" in tok or any(ch.isdigit() for ch in tok):
            continue
        lo = max(0, i - window)
        hi = min(len(lowered), i + window + 1)
        near = set(lowered[lo:hi])
        if not (near & _LEXICAL_ROLE_HINT_TOKENS):
            continue
        roles_by_term[tok].update(
            _LEXICAL_KERNEL_ROLE_HINTS[v] for v in near & _LEXICAL_ROLE_HINT_TOKENS
        )
        counts[tok] += 1
        if len(examples[tok]) < 3:
            examples[tok].append(" ".join(tokens[lo:hi])[:220])
    suspects = []
    for term, count in counts.most_common(8):
        role_names = sorted(roles_by_term.get(term, set()))
        if count < 2 or len(role_names) < 2:
            continue
        suspects.append({
            "term": term,
            "method": "lexical_role_diversity_fallback",
            "near_kernel_role_verb_count": count,
            "kernel_roles": role_names,
            "examples": examples[term],
            "deanchor_seam": _deanchor_seam(term),
        })
    signal = min(1.0, sum(s["near_kernel_role_verb_count"] for s in suspects) / 20.0)
    return {
        "suspects": suspects,
        "firing_signal": round(signal, 4),
        "rule": (
            "strategy-office trigger only; lexical role hints are fallback "
            "sensors, not authority. Prefer typed role bindings/projection "
            "receipts, then semantic atlas retrieval; run primitive_amnesia/"
            "research_isomorphism before adding substrate-specific machinery; "
            "accept only receipt schemas, invariants, quotients, or tests"
        ),
        "method": "lexical_role_diversity_fallback",
        "preferred_future_carrier": (
            "typed_kernel_role_bindings + semantic_atlas_retrieval; lexical "
            "hints only cold-start the question"
        ),
    }


def _planner_attention_pressure(project: "Path | str") -> dict:
    path = Path(project) / "workspace" / "arc3_play_loop_report.json"
    if not path.exists():
        return {"anomalies": [], "firing_signal": 0.0, "method": "play_loop_report"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"anomalies": [], "firing_signal": 0.0, "method": "play_loop_report_unreadable"}
    anomalies = []
    for entry in payload.get("cycles") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("pursuit") != "plan_exhausted":
            continue
        if int(entry.get("levels_gained") or 0) != 0:
            continue
        if int(entry.get("evidence_grown_by") or 0) != 0:
            continue
        anomalies.append({
            "anomaly_class": "plan_exhausted_without_reward_or_new_evidence",
            "cycle": entry.get("cycle"),
            "steps": entry.get("steps"),
            "played": entry.get("played"),
            "expected_next_kernel_action": (
                "goal-cue synthesis, compressed counterexample repair, "
                "or targeted evidence request"
            ),
            "observed_next_action": "broad/candidate pursuit exhausted without new evidence",
            "source_ref": "workspace/arc3_play_loop_report.json",
        })
    signal = min(1.0, len(anomalies) / 3.0)
    return {
        "anomalies": anomalies[-5:],
        "firing_signal": round(signal, 4),
        "method": "play_loop_report",
        "rule": (
            "planner anomalies are Strategy Office triggers. They may commission "
            "goal-cue synthesis, compressed-counterexample repair, or targeted "
            "evidence requests; they do not certify a candidate or override gates."
        ),
    }


def _level_transfer_pressure(project: "Path | str") -> dict:
    path = Path(project) / "workspace" / "latest_level_transfer_probe.json"
    if not path.exists():
        return {"status": "absent", "firing_signal": 0.0, "method": "level_transfer_probe"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"status": "unreadable", "firing_signal": 0.0, "method": "level_transfer_probe"}
    q = payload.get("residue_quotient") or {}
    cert = payload.get("repair_certificate") or {}
    local = payload.get("local_transfer") or {}
    mismatch = payload.get("status") != "exact_first_step_transfer"
    return {
        "status": payload.get("status"),
        "post_depth": payload.get("post_depth"),
        "replay_reaches_level": payload.get("replay_reaches_level"),
        "actions_tested": payload.get("actions_tested"),
        "exact_actions": payload.get("exact_actions"),
        "residue_class": q.get("residue_class"),
        "residue_cell_count": q.get("cell_count"),
        "repair_class": cert.get("repair_class"),
        "repair_sufficient_for_first_step": bool(cert.get("sufficient_for_first_step")),
        "repair_scope": cert.get("scope"),
        "local_steps_tested": local.get("steps_tested"),
        "exact_steps_after_first_step_repair": local.get("exact_steps_after_first_step_repair"),
        "first_step_repair_generalizes_to_depth": local.get("first_step_repair_generalizes_to_depth"),
        "firing_signal": 0.75 if mismatch else 0.0,
        "method": "level_transfer_probe",
        "rule": (
            "level-transfer residues are compressed counterexamples. A sufficiency "
            "certificate may select a repair card, but cannot claim solve or "
            "canonical adoption without replay/holdout/sealed reward."
        ),
    }


def _loop_control_pressure(project: "Path | str") -> dict:
    """Read autoresearch loop-control telemetry as scheduler pressure.

    This is meta-control evidence only. It says the current routing is
    low-yield; it cannot certify a model, discharge a card, or weaken a gate.
    """
    path = Path(project) / "workspace" / "latest_information_yield.json"
    if not path.exists():
        return {"anomalies": [], "firing_signal": 0.0, "method": "information_yield"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {
            "anomalies": [],
            "firing_signal": 0.0,
            "method": "information_yield_unreadable",
        }
    signal = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    action = str(decision.get("action") or "")
    weakest = str(signal.get("weakest_point") or "")
    if not weakest:
        return {"anomalies": [], "firing_signal": 0.0, "method": "information_yield"}

    lower = weakest.lower()
    scheduler_tags = []
    if signal.get("mutation_r1_mismatch") or "r1" in lower:
        scheduler_tags.append("r1_declaration_mismatch")
    if "pre_judge" in lower or "pre-judge" in lower:
        scheduler_tags.append("pre_judge_gate_loop")
    if "patch_base" in lower or "strictly improve" in lower:
        scheduler_tags.append("patch_base_no_improvement")
    if "strategy_card" in lower:
        scheduler_tags.append("strategy_card_attention_failure")
    if action == "REFRESH_SPECIALISTS" and not scheduler_tags:
        scheduler_tags.append("low_yield_specialist_refresh")
    if not scheduler_tags:
        return {"anomalies": [], "firing_signal": 0.0, "method": "information_yield"}

    stagnant = int(decision.get("stagnant_window") or 0)
    anomaly = {
        "anomaly_class": "scheduler_counterexample",
        "residue_class": "low_yield_loop_control",
        "scheduler_tags": scheduler_tags,
        "iteration_index": signal.get("iteration_index"),
        "score": signal.get("score"),
        "decision_action": action,
        "stagnant_window": stagnant,
        "weakest_point": weakest[:500],
        "expected_next_kernel_action": (
            "route the failure family through a quotient repair, typed card "
            "discharge, or kernel-improvement receipt before retrying the same "
            "candidate lineage"
        ),
        "observed_next_action": decision.get("rationale") or weakest[:220],
        "source_ref": "workspace/latest_information_yield.json",
    }
    signal_strength = 0.5
    if action == "REFRESH_SPECIALISTS":
        signal_strength += 0.2
    if signal.get("mutation_r1_mismatch"):
        signal_strength += 0.15
    signal_strength += min(0.15, stagnant * 0.05)
    return {
        "anomalies": [anomaly],
        "firing_signal": round(min(1.0, signal_strength), 4),
        "method": "information_yield",
        "rule": (
            "loop-control anomalies are scheduler counterexamples. They may "
            "commission a quotient repair, typed card discharge, targeted "
            "evidence request, or kernel-improvement receipt; they do not "
            "certify a candidate or override replay/holdout/sealed gates."
        ),
    }


def _cfg_str(config: tuple) -> str:
    return "".join("1" if b else "0" for b in config) or "(no-regions)"


def _firing_signal(nd: dict, cov: dict, ledger: dict) -> float:
    import math
    backlog = ledger.get("open_operator_cards", 0) + ledger.get("open_strategy_cards", 0)
    holes = len(cov.get("one_position_multiflag_holes", []))
    decayed = 1.0 - float(nd.get("last_segment_new_rate", 1.0))  # low new-rate → pressure
    signal = (0.2 * math.tanh(backlog / 5.0)
              + 0.4 * math.tanh(holes / 3.0)
              + 0.4 * max(0.0, min(1.0, decayed)))
    return round(max(0.0, min(1.0, signal)), 4)


# ── the AuditBattery protocol surface ────────────────────────────────────────

class WorldmodelBattery:
    """AuditBattery for the interactive grid world-model substrate."""

    def run_audits(self, project) -> dict:
        rows = _load_capped(project)
        cap = _row_cap()
        if not rows:
            return {"error": "no episode log", "firing_signal": 0.0}
        log = EpisodeLog(rows)
        spec = _last_spec(project)
        roles = induce_roles(log, _action_arity(rows))
        nd = _novelty_decay(rows)
        cov = _conditional_coverage(rows, spec, roles)
        ev = _event_context(rows, spec, roles)
        ledger = _ledger_closure(project, rows, spec, roles)
        sweep = _sweep_horizon(rows)
        deanchor = _semantic_deanchor_pressure(project)
        planner = _planner_attention_pressure(project)
        transfer = _level_transfer_pressure(project)
        loop_control = _loop_control_pressure(project)
        cyc = cycles_from_evidence(log, spec)
        return {
            "substrate": "worldmodel_grid",
            "rows_scanned": len(rows),
            "row_cap": cap,
            "capped": len(rows) >= cap,
            "roles": [getattr(r, "name", None) for r in getattr(roles, "roles", roles)],
            "novelty_decay": nd,
            "conditional_coverage": cov,
            "event_context_at_env_frames": ev,
            "ledger_closure": ledger,
            "sweep_horizon": sweep,
            "semantic_deanchor_pressure": deanchor,
            "planner_attention_pressure": planner,
            "level_transfer_pressure": transfer,
            "loop_control_pressure": loop_control,
            "cycle_enumeration": {
                "sources": len(cyc),
                "multi_state_sources": sum(1 for v in cyc.values() if v.get("multi_state")),
                "per_source": cyc,
            },
            "firing_signal": max(_firing_signal(nd, cov, ledger),
                                 deanchor.get("firing_signal", 0.0),
                                 planner.get("firing_signal", 0.0),
                                 transfer.get("firing_signal", 0.0),
                                 loop_control.get("firing_signal", 0.0)),
        }

    def query_menu(self) -> dict:
        def _nd(project, k=_DEFAULT_SEGMENT):
            return _novelty_decay(_load_capped(project), k=int(k))

        def _cov(project, min_flags=2):
            rows = _load_capped(project)
            spec = _last_spec(project)
            roles = induce_roles(EpisodeLog(rows), _action_arity(rows)) if rows else []
            return _conditional_coverage(rows, spec, roles, min_flags=int(min_flags))

        def _ev(project, top=10):
            rows = _load_capped(project)
            spec = _last_spec(project)
            roles = induce_roles(EpisodeLog(rows), _action_arity(rows)) if rows else []
            return _event_context(rows, spec, roles, top=int(top))

        def _open(project, ledger="operator_proposals.jsonl"):
            return [c.get("failure_family")
                    for c in open_cards(Path(project) / "workspace" / str(ledger))]

        def _deanchor(project, top=5):
            out = _semantic_deanchor_pressure(project)
            out["suspects"] = out.get("suspects", [])[:int(top)]
            return out

        def _planner(project, top=5):
            out = _planner_attention_pressure(project)
            out["anomalies"] = out.get("anomalies", [])[:int(top)]
            return out

        def _transfer(project):
            return _level_transfer_pressure(project)

        def _loop_control(project, top=5):
            out = _loop_control_pressure(project)
            out["anomalies"] = out.get("anomalies", [])[:int(top)]
            return out

        def _event_timeline(project, episode="visible", spec='{"changed": true}'):
            from ztare.worldmodel.evidence_quotients import (
                cap_events, event_timeline, resolve_episode_ref)
            rows = _load_capped(project, path=resolve_episode_ref(project, episode))
            parsed = json.loads(spec) if isinstance(spec, str) else dict(spec or {})
            out = cap_events(event_timeline(EpisodeLog(rows), cell_predicate_spec=parsed))
            out["rows_scanned"] = len(rows)
            if len(rows) >= _row_cap():
                out["row_cap"] = _row_cap()
                out["capped"] = True
            return out

        def _episode_contrast(project, episode_a="visible", episode_b="holdout",
                              at_t=None):
            from ztare.worldmodel.evidence_quotients import (
                episode_contrast, resolve_episode_ref)
            rows_a = _load_capped(project, path=resolve_episode_ref(project, episode_a))
            rows_b = _load_capped(project, path=resolve_episode_ref(project, episode_b))
            out = episode_contrast(EpisodeLog(rows_a), EpisodeLog(rows_b),
                                   at_t=None if at_t is None else int(at_t))
            out["rows_scanned"] = {"a": len(rows_a), "b": len(rows_b)}
            if max(len(rows_a), len(rows_b)) >= _row_cap():
                out["row_cap"] = _row_cap()
                out["capped"] = True
            return out

        return {
            "novelty_decay": ("new abstract states per K-row segment + Good-Turing "
                              "unseen mass (params: k)", _nd),
            "conditional_coverage": ("distinct agent positions per flag config; "
                                     "one-position multi-flag holes (params: min_flags)", _cov),
            "event_context": ("indicator flag combos at env frames / deaths (params: top)", _ev),
            "open_cards": ("undispositioned card families in a ledger "
                           "(params: ledger filename)", _open),
            "semantic_deanchor": ("local terms doing kernel work; returns "
                                  "operator-neutral seam skeletons (params: top)",
                                  _deanchor),
            "planner_attention": ("play-loop anomalies where planning exhausted "
                                  "without level gain or new evidence (params: top)",
                                  _planner),
            "level_transfer": ("latest level-boundary transfer receipt and compact "
                               "repair certificate, if present", _transfer),
            "loop_control": ("autoresearch information-yield scheduler "
                             "counterexamples (params: top)", _loop_control),
            "event_timeline": ("group cell-change events across time in one "
                               "episode log; per-step counts + rate series "
                               "(params: episode=visible|holdout|path, spec JSON "
                               "with changed/before_in/after_not_in)",
                               _event_timeline),
            "episode_contrast": ("contrast two episodes' states at a matching "
                                 "step: value census delta + differing rows "
                                 "(params: episode_a, episode_b, at_t)",
                                 _episode_contrast),
        }

    def experiment_kinds(self) -> "list[str]":
        return [
            "reachability_sweep_to_goal",       # sweep with an abduced goal predicate
            "targeted_action_path_probe",       # execute a specific action path live
            "coverage_gap_probe",               # drive a 1-position hole to a 2nd position
            "conjunction_activation_probe",     # co-activate never-co-witnessed flags
            "horizon_exhaustion_probe",         # exhaust the bounded object-space (refute)
            "disposition_backlog_review",       # close tested-but-undispositioned cards
            "semantic_deanchor_receipt_compile", # deanchor suspect term into receipt/test/quotient
            "compressed_counterexample_repair", # compact residue -> quotient/test/repair card before broad search
            "scheduler_counterexample_review",  # low-yield telemetry -> routing/kernel-improvement receipt
        ]
