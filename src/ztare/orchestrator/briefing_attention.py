"""Attention agenda compiler for mutator briefings.

Providers are good local sensors, but a prompt should not be provider-order
driven. This module compiles provider ``structured_records`` into a small
front-of-prompt agenda ranked by artifact authority, actionability, and
recency. It is intentionally substrate-neutral: the inputs are records, gates,
hashes, source refs, summaries, and requested actions.

Semantic retrieval belongs behind this compiler, not inside individual
providers. The compiler is the stable insertion point for a cached atlas over
records/past failures, using ``ztare.common.embeddings`` when enabled.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


_AUTHORITY_BY_SOURCE_TYPE = {
    "strategy_experiment": 115,
    "full_survivor": 100,
    "residual_class_receipt": 96,
    "level_transfer_receipt": 95,
    "deterministic_near_miss": 95,
    "compressed_counterexample": 94,
    "planner_anomaly": 93,
    "scheduler_counterexample": 93,
    "kernel_role_binding": 92,
    "gate_failure": 90,
    "graph_focus_receipt": 86,
    "source_claim_gap": 82,
    "r1_rejection": 76,
    "contract_violation": 74,
    "fit_failure": 70,
    "eval_failure": 68,
    "projection_constraint": 64,
    "projection_frontier": 62,
    "analogy_candidate": 40,
}

_ACTION_BONUS_TERMS = (
    "patch",
    "change",
    "explain",
    "discrimin",
    "repair",
    "retry",
    "focus",
    "candidate",
    "mismatch",
    "residual",
    "gate",
)


@dataclass(frozen=True)
class AttentionItem:
    provider: str
    source_type: str
    score: float
    summary: str
    action: str
    source_ref: str


def compile_attention_agenda(
    records: list[dict[str, Any]],
    *,
    max_items: int = 6,
) -> list[AttentionItem]:
    """Rank machine-readable briefing records into a compact agenda."""
    items: list[AttentionItem] = []
    seen: set[tuple[str, str, str]] = set()
    for rec in records:
        if not isinstance(rec, dict):
            continue
        item = _item_from_record(rec)
        if item is None:
            continue
        key = (item.provider, item.source_type, item.summary[:120])
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    items.sort(key=lambda item: (item.score, item.provider, item.summary), reverse=True)
    return items[:max_items]


def render_attention_agenda(
    records: list[dict[str, Any]],
    *,
    max_items: int = 6,
) -> str:
    """Render a small front-of-prompt attention contract."""
    items = compile_attention_agenda(records, max_items=max_items)
    if not items:
        return ""
    lines = [
        "## Briefing Attention Agenda",
        "- Read these first. They are selected from structured provider records by artifact authority, actionability, and recency.",
        "- If this agenda conflicts with project-root prose, follow the higher-authority artifact named here.",
    ]
    for item in items:
        bits = [
            f"provider={item.provider}",
            f"type={item.source_type}",
            f"score={item.score:.1f}",
        ]
        if item.source_ref:
            bits.append(f"source={item.source_ref}")
        action = f" action={item.action}" if item.action else ""
        lines.append(f"- {'; '.join(bits)}: {item.summary}{action}")
    lines.append("")
    return "\n".join(lines)


def _item_from_record(rec: dict[str, Any]) -> AttentionItem | None:
    provider = _clean(rec.get("provider") or "unknown")
    source_type = _clean(rec.get("source_type") or rec.get("type") or rec.get("kind") or "record")
    summary = _summary(rec)
    if not summary:
        return None
    action = _clean(rec.get("action") or rec.get("next_action") or rec.get("recommendation") or "")
    source_ref = _clean(rec.get("source_ref") or rec.get("submission") or rec.get("path") or "")
    score = _record_score(rec, source_type, summary, action)
    return AttentionItem(
        provider=provider,
        source_type=source_type,
        score=score,
        summary=summary,
        action=action,
        source_ref=source_ref,
    )


def _record_score(rec: dict[str, Any], source_type: str, summary: str, action: str) -> float:
    score = float(_AUTHORITY_BY_SOURCE_TYPE.get(source_type, 50))
    text = f"{summary} {action}".lower()
    score += sum(1.5 for term in _ACTION_BONUS_TERMS if term in text)
    if rec.get("source_type") == "deterministic_near_miss":
        score += min(20.0, float(rec.get("visible_exact_rows") or 0) / 100.0)
        score += min(5.0, float(rec.get("holdout_depth") or 0))
    if rec.get("sha") or rec.get("source_ref") or rec.get("submission"):
        score += 2.0
    if rec.get("observed_at_utc") or rec.get("iteration") is not None:
        score += 1.0
    return score


def _summary(rec: dict[str, Any]) -> str:
    if rec.get("source_type") == "kernel_role_binding":
        term = _clean(rec.get("term") or rec.get("concept") or rec.get("local_term") or "?")
        roles = rec.get("kernel_roles") or rec.get("roles") or []
        if isinstance(roles, (list, tuple, set)):
            role_text = ", ".join(_clean(x) for x in roles if _clean(x))
        else:
            role_text = _clean(roles)
        return _clip(f"typed kernel-role binding: {term} -> [{role_text}]", 260)
    if rec.get("source_type") == "planner_anomaly":
        klass = _clean(rec.get("anomaly_class") or rec.get("kind") or "planner anomaly")
        observed = _clean(rec.get("observed_next_action") or rec.get("observed") or "")
        expected = _clean(rec.get("expected_next_kernel_action") or rec.get("expected") or "")
        return _clip(
            f"{klass}; expected={expected or '?'}; observed={observed or '?'}",
            300,
        )
    if rec.get("source_type") == "scheduler_counterexample":
        klass = _clean(rec.get("anomaly_class") or "scheduler counterexample")
        tags = rec.get("scheduler_tags") or []
        if isinstance(tags, (list, tuple, set)):
            tag_text = ",".join(_clean(x) for x in tags if _clean(x))
        else:
            tag_text = _clean(tags)
        decision = _clean(rec.get("decision_action") or "")
        expected = _clean(rec.get("expected_next_kernel_action") or "")
        return _clip(
            f"{klass}; tags={tag_text or '?'}; decision={decision or '?'}; expected={expected or '?'}",
            340,
        )
    if rec.get("source_type") == "compressed_counterexample":
        klass = _clean(rec.get("residue_class") or rec.get("counterexample_class") or "compact residue")
        count = rec.get("cell_count") or rec.get("witness_count") or rec.get("count") or "?"
        repair = _clean(rec.get("repair_class") or "")
        suffix = ""
        if repair:
            if rec.get("first_step_repair_generalizes_to_depth") is False:
                n = rec.get("exact_steps_after_first_step_repair") or 0
                d = rec.get("local_steps_tested") or "?"
                suff = f"first-step only; depth check {n}/{d}"
            else:
                suff = "sufficient" if rec.get("repair_sufficient_for_first_step") else "not certified"
            suffix = f"; repair={repair} ({suff})"
        return _clip(f"compressed counterexample class={klass}; witnesses={count}{suffix}", 300)
    if rec.get("source_type") == "residual_class_receipt":
        matched = rec.get("matched_transitions") or "?"
        total = rec.get("transitions") or "?"
        class_count = rec.get("residual_class_count") or "?"
        passed = rec.get("admissibility_passed")
        top = rec.get("top_residual_classes") or []
        top_bits = []
        if isinstance(top, list):
            for item in top[:2]:
                if isinstance(item, dict):
                    top_bits.append(
                        f"#{item.get('rank')}:count={item.get('count')},cells={item.get('cell_count')}"
                    )
        top_clause = f"; top={'; '.join(top_bits)}" if top_bits else ""
        return _clip(
            f"residual quotient receipt replay={matched}/{total}; classes={class_count}; "
            f"admissibility={passed}{top_clause}",
            340,
        )
    if rec.get("source_type") == "level_transfer_receipt":
        verdict = _clean(rec.get("verdict_numbers") or rec.get("verdict") or "?")
        hint = _clean(rec.get("refinement_hint") or "")
        bits = [f"verdict={verdict}"]
        if hint:
            bits.append(f"refinement_hint={hint}")
        return _clip("cross-level transfer receipt " + "; ".join(bits), 340)
    if rec.get("source_type") == "strategy_experiment":
        kind = _clean(rec.get("kind") or "strategy card")
        residue = _clean(rec.get("residue_class") or "")
        repair = _clean(rec.get("repair_class") or "")
        sha = _clean(rec.get("failure_family_sha") or rec.get("sha") or "")
        receipt = _clean(rec.get("required_receipt") or "STRATEGY_CARD_DISCHARGE")
        required_transform = _clean(rec.get("required_transform") or "")
        parts = [kind]
        if sha:
            parts.append(f"sha={sha[:16]}")
        if residue:
            parts.append(f"residue={residue}")
        if repair:
            parts.append(f"repair={repair}")
        parts.append(f"requires={receipt}")
        if required_transform:
            parts.append(f"obligation={required_transform}")
        return _clip("; ".join(parts), 320)
    for key in ("summary", "first_mismatch", "detail", "weakest_point", "title"):
        text = _clean(rec.get(key))
        if text:
            return _clip(text, 260)
    if rec.get("source_type") == "deterministic_near_miss":
        checked = rec.get("visible_checked_rows") or "?"
        return _clip(
            "near-miss carrier "
            f"{rec.get('submission') or '?'} visible={rec.get('visible_exact_rows', 0)}/{checked} "
            f"wrong_cells={rec.get('visible_wrong_cells', '?')} first={rec.get('first_mismatch') or '?'}",
            300,
        )
    return _clip(json.dumps(rec, sort_keys=True, default=str), 260)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _clip(text: str, n: int) -> str:
    text = _clean(text)
    return text if len(text) <= n else text[: n - 3].rstrip() + "..."
