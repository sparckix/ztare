from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ztare.common.candidate_memory import admissible_candidate_memory_records
from ztare.common.strategy_card_roles import (
    META_HARDENING_LANE,
    strategy_card_blocks_context,
    strategy_card_role,
)


def strategy_card_obligation_prompt(project_dir: str | Path) -> str:
    """Render a short obligation pointer for blocking Strategy Office cards."""
    try:
        from ztare.common.operator_proposal_contract import open_cards
        from ztare.validator.core.strategy_card_gate import (
            admissible_no_attempt_blocker_kinds,
        )

        all_cards = open_cards(Path(project_dir) / "workspace" / "strategy_experiments.jsonl")
        cards = [
            card for card in all_cards
            if strategy_card_blocks_context(card)
        ]
        meta_count = sum(
            1 for card in all_cards
            if strategy_card_role(card).lane == META_HARDENING_LANE
        )
    except Exception:  # noqa: BLE001
        cards = []
        meta_count = 0
    if not cards:
        if meta_count:
            return (
                "### ACTIVE STRATEGY OFFICE META BACKLOG\n"
                f"{meta_count} meta-hardening card(s) are queued; they do not block "
                "object-level candidate evaluation unless the task is explicitly meta-hardening.\n"
            )
        return ""
    lines = [
        "### ACTIVE STRATEGY OFFICE OBLIGATION",
        "Open skill-acquisition Strategy Office cards are active. Your submission must include "
        "one typed receipt for each listed skill card before judge review, "
        "using the exact full `failure_family_sha` shown below:",
        '`STRATEGY_CARD_DISCHARGE: {"failure_family_sha": "...", '
        '"outcome": "satisfied|refuted|blocked", "observed_status": "...", '
        '"evidence_refs": ["..."]}`',
        "Place the `STRATEGY_CARD_DISCHARGE:` line in markdown outside the Python "
        "code block. Never put this receipt inside a string literal, comment, "
        "docstring, or test_model.py carrier.",
        "If the worldmodel typed JSON contract is active, put receipts in "
        "`control_receipts`, not in `test_model_py`.",
        "SHA prefixes do not match; copy the full card SHA.",
        "A transition model alone does not discharge a search-control card.",
        "`satisfied` is only valid when `observed_status` or `next_gate_status` "
        "equals the card's listed `next_gate`; otherwise use `blocked` or "
        "`refuted`.",
        "For repair cards, `blocked` must also include `blocker_kind`, "
        "`next_action`, and either `attempted_repair`/`attempted_probe`, "
        "`new_evidence_refs`, or one of the no-attempt blocker kinds listed "
        "on that card.",
    ]
    for card in cards[:3]:
        role = strategy_card_role(card)
        plan = card.get("action_plan") or {}
        residue = plan.get("residue_quotient") or {}
        gate = plan.get("required_next_gate") or {}
        discriminator = plan.get("discriminator_axis") or {}
        no_attempt = admissible_no_attempt_blocker_kinds(card)
        lines.append(
            "- "
            f"sha={str(card.get('failure_family_sha', '?'))}; "
            f"lane={role.lane}; "
            f"kind={card.get('kind', '?')}; "
            f"residue={residue.get('residue_class', '?')}; "
            f"axis={discriminator.get('axis', '?')}; "
            f"next_gate={gate.get('success_status', '?')}; "
            f"no_attempt_blockers={no_attempt}; "
            f"prediction={card.get('falsifiable_prediction', '')}"
        )
    return "\n".join(lines) + "\n"


def deterministic_patch_base_document_context(
    *,
    project_dir: str | Path,
    current_content: str,
    current_test_model: str,
    include_root_excerpt: bool = False,
    max_root_excerpt_chars: int = 2400,
) -> str | None:
    """Demote stale root prose/code when gate receipts name a better carrier."""
    path = Path(project_dir) / "workspace" / "candidate_memory.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict) or payload.get("schema") != "ztare-candidate-memory-v1":
        return None
    records: list[dict[str, Any]] = [
        rec for rec in admissible_candidate_memory_records(
            project_dir,
            [row for row in (payload.get("records") or []) if isinstance(row, dict)],
            require_submission_source=True,
        )
        if str(rec.get("source_excerpt") or "").strip()
    ]
    if not records:
        return None

    def _rank(rec: dict[str, Any]) -> tuple[int, int, int, float, int]:
        return (
            1 if rec.get("source_type") == "full_survivor" else 0,
            int(rec.get("visible_exact_rows") or 0),
            int(rec.get("holdout_depth") or 0),
            float(rec.get("gate_score") or 0.0),
            -int(rec.get("visible_wrong_cells") or 0),
        )

    best = max(records, key=_rank)
    patch_base_sha = str(best.get("sha") or "")
    submission = str(best.get("submission") or "").strip()
    if submission:
        path = (Path(project_dir) / submission).resolve()
        root = Path(project_dir).resolve()
        try:
            if path.is_file() and (path == root or root in path.parents):
                patch_base_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            pass
    source = str(best.get("source_excerpt") or "").strip()
    anchor = source[:240]
    current_content = current_content or ""
    current_test_model = current_test_model or ""
    root_prose_matches_patch_base = bool(anchor and anchor in current_content)
    root_code_matches_patch_base = bool(anchor and anchor in current_test_model)
    root_note = (
        "Root prose omitted from mutation context because deterministic "
        "candidate memory is the higher-authority edit surface. Inspect the "
        "root files manually if auditing history; do not use them as the next "
        "edit target."
    )
    if include_root_excerpt:
        root_excerpt = current_content.strip()
        if len(root_excerpt) > max_root_excerpt_chars:
            root_excerpt = (
                root_excerpt[:max_root_excerpt_chars].rstrip()
                + "\n... [root prose truncated]"
            )
        root_note = "Root prose excerpt:\n" + root_excerpt
    return (
        "### CURRENT SYSTEM STATE (ROOT ARTIFACTS QUARANTINED)\n"
        "A deterministic candidate-memory patch base supersedes the project-root "
        "`current_iteration.md` / `test_model.py` surfaces for the next mutation. "
        "Use the `## Deterministic Candidate Memory` patch base as the edit target; "
        "do not infer the active mechanism from stale root prose.\n\n"
        f"- patch_base_submission: {best.get('submission')}\n"
        f"- patch_base_sha: {patch_base_sha}\n"
        f"- visible_exact_rows: {best.get('visible_exact_rows')}/{best.get('visible_checked_rows')}\n"
        f"- first_mismatch: {best.get('first_mismatch')}\n\n"
        f"- root_prose_matches_patch_base: {str(root_prose_matches_patch_base).lower()}\n"
        f"- root_test_model_matches_patch_base: {str(root_code_matches_patch_base).lower()}\n\n"
        f"{root_note}"
    )
