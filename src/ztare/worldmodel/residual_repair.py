"""Strategy cards from current replay residual quotients.

This module is a receipt reader. It does not run abduction, replay, or live
environments. Given a persisted replay diagnostic, it keeps Strategy Office
repair cards aligned to the current counterexample quotient: stale repair
cards are rejected and the current top residual class is opened as a work
order.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.common.candidate_memory import admissible_candidate_memory_records
from ztare.common.operator_proposal_contract import (
    family_sha,
    open_cards,
    record_disposition,
)
from ztare.research_director.strategy_decision_policy import (
    STRATEGY_LEDGER,
    StrategyCardBatchSubmission,
    submit_strategy_card_batch,
)
from ztare.research_director.strategy_office import STRATEGY_SCHEMA


def _load_candidate_memory(project: Path) -> list[dict[str, Any]]:
    path = project / "workspace" / "candidate_memory.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    records = payload.get("records")
    return [rec for rec in records if isinstance(rec, dict)] if isinstance(records, list) else []


def _best_visible_candidate(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        rec for rec in records
        if rec.get("source_type") in {"deterministic_near_miss", "full_survivor"}
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda rec: (
            int(rec.get("visible_exact_rows") or 0),
            int(rec.get("holdout_depth") or 0),
            float(rec.get("gate_score") or 0.0),
            -int(rec.get("visible_wrong_cells") or 0),
        ),
    )


def _candidate_dominates_replay_diagnostics(
    candidate: dict[str, Any] | None,
    diagnostics: dict[str, Any],
) -> bool:
    if not isinstance(candidate, dict):
        return False
    checked = int(diagnostics.get("checked_rows") or 0)
    exact = int(diagnostics.get("exact_rows") or 0)
    wrong_cells = int(diagnostics.get("wrong_cell_count") or 0)
    cand_checked = int(candidate.get("visible_checked_rows") or 0)
    cand_exact = int(candidate.get("visible_exact_rows") or 0)
    cand_wrong = int(candidate.get("visible_wrong_cells") or 0)
    if cand_checked <= 0 or checked <= 0:
        return False
    if cand_checked < checked:
        return False
    return (
        (cand_exact, -cand_wrong)
        > (exact, -wrong_cells)
        and (exact < checked or wrong_cells > 0)
    )


def reject_cards_dominated_by_candidate_memory(
    project: str | Path,
    diagnostics: dict[str, Any],
    *,
    source_ref: str,
) -> list[dict[str, Any]]:
    """Reject replay-repair cards superseded by a stronger executable carrier.

    A replay diagnostic from project-root or abduction can be weaker than a
    persisted candidate-memory carrier. Strategy cards should follow the
    strongest executable receipt, not force the worker to repair an obsolete
    quotient. This rejects only replay-mismatch cards when candidate memory has
    strictly better visible replay coverage over the same checked window.
    Holdout failures remain live work; this function does not promote the
    candidate or claim transfer closure.
    """
    root = Path(project)
    best = _best_visible_candidate(admissible_candidate_memory_records(root))
    if not _candidate_dominates_replay_diagnostics(best, diagnostics):
        return []
    ledger = root / "workspace" / STRATEGY_LEDGER
    rejected: list[dict[str, Any]] = []
    for card in open_cards(ledger):
        if card.get("kind") != "compressed_counterexample_repair":
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        residue = plan.get("residue_quotient") if isinstance(plan.get("residue_quotient"), dict) else {}
        if residue.get("residue_class") != "replay_mismatch_quotient":
            continue
        out = dict(card)
        out["disposition"] = "rejected"
        out["counterexample"] = (
            "superseded by candidate memory: a stronger executable carrier is "
            "strictly better over the diagnostic window; route next work to "
            "holdout/local-transfer residuals instead of this replay quotient"
        )
        out["superseding_receipt"] = source_ref
        out["superseding_candidate"] = {
            "submission": best.get("submission"),
            "sha": best.get("sha"),
            "visible_exact_rows": best.get("visible_exact_rows"),
            "visible_checked_rows": best.get("visible_checked_rows"),
            "visible_wrong_cells": best.get("visible_wrong_cells"),
            "holdout_depth": best.get("holdout_depth"),
        }
        rejected.append(record_disposition(ledger, out))
    return rejected


def _bbox_from_signature(sig: dict[str, Any]) -> tuple[int, int, int, int] | None:
    bbox = sig.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        return None
    try:
        y0, x0, y1, x1 = (int(v) for v in bbox)
    except Exception:  # noqa: BLE001
        return None
    return y0, x0, y1, x1


def _card_cells(card: dict[str, Any]) -> set[tuple[int, int]]:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    out: set[tuple[int, int]] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if "y" in obj and "x" in obj:
                try:
                    out.add((int(obj["y"]), int(obj["x"])))
                except Exception:  # noqa: BLE001
                    pass
            for val in obj.values():
                walk(val)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(plan.get("residue_quotient") or {})
    walk(plan.get("local_residue_quotient") or {})
    return out


def _cells_overlap_bbox(cells: set[tuple[int, int]], bbox: tuple[int, int, int, int]) -> bool:
    y0, x0, y1, x1 = bbox
    return any(y0 <= y <= y1 and x0 <= x <= x1 for y, x in cells)


def _card_bboxes(card: dict[str, Any]) -> list[tuple[int, int, int, int]]:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    out: list[tuple[int, int, int, int]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            bbox = _bbox_from_signature(obj)
            if bbox is not None:
                out.append(bbox)
            for val in obj.values():
                walk(val)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(plan.get("residue_quotient") or {})
    walk(plan.get("local_residue_quotient") or {})
    return out


def _bboxes_overlap(
    a: tuple[int, int, int, int],
    b: tuple[int, int, int, int],
) -> bool:
    ay0, ax0, ay1, ax1 = a
    by0, bx0, by1, bx1 = b
    return not (ay1 < by0 or by1 < ay0 or ax1 < bx0 or bx1 < ax0)


def _pair_counts_key(sig: dict[str, Any]) -> tuple[tuple[int, int, int], ...]:
    pairs = sig.get("pair_counts")
    if not isinstance(pairs, list):
        return ()
    out: list[tuple[int, int, int]] = []
    for item in pairs:
        if not isinstance(item, dict):
            continue
        try:
            out.append((
                int(item.get("predicted")),
                int(item.get("real")),
                int(item.get("count")),
            ))
        except Exception:  # noqa: BLE001
            continue
    return tuple(sorted(out))


def _replay_quotient_key_from_parts(
    *,
    t: Any,
    action: Any,
    signature: dict[str, Any],
) -> tuple[Any, ...] | None:
    bbox = _bbox_from_signature(signature)
    if bbox is None:
        return None
    try:
        mismatch_cells = int(signature.get("mismatch_cells") or 0)
    except Exception:  # noqa: BLE001
        mismatch_cells = 0
    return (
        t,
        action,
        bbox,
        mismatch_cells,
        _pair_counts_key(signature),
    )


def _replay_quotient_key_from_class(cls: dict[str, Any]) -> tuple[Any, ...] | None:
    sig = cls.get("signature") if isinstance(cls.get("signature"), dict) else {}
    return _replay_quotient_key_from_parts(
        t=cls.get("t"),
        action=cls.get("action"),
        signature=sig,
    )


def _replay_quotient_key_from_card(card: dict[str, Any]) -> tuple[Any, ...] | None:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    residue = plan.get("residue_quotient") if isinstance(plan.get("residue_quotient"), dict) else {}
    sig = residue.get("signature") if isinstance(residue.get("signature"), dict) else {}
    return _replay_quotient_key_from_parts(
        t=residue.get("t"),
        action=residue.get("action"),
        signature=sig,
    )


def build_replay_residual_repair_card(
    diagnostics: dict[str, Any],
    *,
    source_ref: str,
) -> dict[str, Any] | None:
    """Build one Strategy Office card for the current top mismatch class."""
    classes = diagnostics.get("mismatch_classes")
    if not isinstance(classes, list) or not classes:
        return None
    top = classes[0]
    if not isinstance(top, dict):
        return None
    sig = top.get("signature") if isinstance(top.get("signature"), dict) else {}
    bbox = _bbox_from_signature(sig)
    if bbox is None:
        return None
    plan = {
        "source_receipt_schema": diagnostics.get("schema", "ztare-replay-diagnostics-v1"),
        "source_receipt": source_ref,
        "residue_quotient": {
            "residue_class": "replay_mismatch_quotient",
            "class_count": int(top.get("count") or 0),
            "first_row": top.get("first_row"),
            "t": top.get("t"),
            "action": top.get("action"),
            "signature": sig,
            "bbox": list(bbox),
        },
        "routing_class": "classify_existing_operator_or_emit_operator_proposal",
        "required_next_gate": {
            "command": "replay_diagnostics",
            "success_status": "residual_class_removed_or_operator_carded",
            "adoption_authority": (
                "diagnostic repair cards route work only; replay/holdout gates "
                "remain the candidate authority"
            ),
        },
    }
    family = f"replay_residual_repair|{json.dumps(plan['residue_quotient'], sort_keys=True)}"
    return {
        "schema": STRATEGY_SCHEMA,
        "lane": "skill_acquisition",
        "kind": "compressed_counterexample_repair",
        "failure_family": family,
        "failure_family_sha": family_sha(family),
        "rationale": "current replay diagnostics contain a compact residual quotient",
        "falsifiable_prediction": (
            "after repair, waiver, or operator-proposal routing, rerun replay "
            "diagnostics removes this quotient or records the operator card"
        ),
        "action_plan": plan,
        "kill_condition": "current replay diagnostics no longer contain this quotient",
        "disposition": "open",
    }


def reject_stale_repair_cards(
    project: str | Path,
    diagnostics: dict[str, Any],
    *,
    source_ref: str,
) -> list[dict[str, Any]]:
    """Reject replay-repair cards whose residue no longer overlaps current replay.

    A replay-diagnostics receipt can supersede stale replay-diagnostics cards.
    It must not reject cards whose authority is another producer clock, such as
    a level-transfer probe blocked on an external seed prerequisite.
    """
    root = Path(project)
    ledger = root / "workspace" / STRATEGY_LEDGER
    classes = diagnostics.get("mismatch_classes")
    current_boxes = []
    current_replay_keys: set[tuple[Any, ...]] = set()
    if isinstance(classes, list):
        for cls in classes[:12]:
            if isinstance(cls, dict) and isinstance(cls.get("signature"), dict):
                bbox = _bbox_from_signature(cls["signature"])
                if bbox is not None:
                    current_boxes.append(bbox)
                key = _replay_quotient_key_from_class(cls)
                if key is not None:
                    current_replay_keys.add(key)
    rejected: list[dict[str, Any]] = []
    for card in open_cards(ledger):
        if card.get("kind") != "compressed_counterexample_repair":
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        residue = plan.get("residue_quotient") if isinstance(plan.get("residue_quotient"), dict) else {}
        if residue.get("residue_class") != "replay_mismatch_quotient":
            continue
        card_key = _replay_quotient_key_from_card(card)
        if card_key is not None and current_replay_keys:
            still_current = card_key in current_replay_keys
            if still_current:
                continue
            out = dict(card)
            out["disposition"] = "rejected"
            out["counterexample"] = (
                "superseded by current replay diagnostics: the card's replay "
                "quotient signature is no longer present"
            )
            out["superseding_receipt"] = source_ref
            rejected.append(record_disposition(ledger, out))
            continue
        cells = _card_cells(card)
        bboxes = _card_bboxes(card)
        if cells:
            still_current = any(_cells_overlap_bbox(cells, bbox) for bbox in current_boxes)
        elif bboxes:
            still_current = any(
                _bboxes_overlap(card_box, current_box)
                for card_box in bboxes
                for current_box in current_boxes
            )
        else:
            continue
        if still_current:
            continue
        out = dict(card)
        out["disposition"] = "rejected"
        out["counterexample"] = (
            "superseded by current replay diagnostics: the card's residue cells "
            "do not overlap any current mismatch quotient"
        )
        out["superseding_receipt"] = source_ref
        rejected.append(record_disposition(ledger, out))
    return rejected


def reject_satisfied_seed_prerequisite_cards(
    project: str | Path,
    *,
    source_ref: str = "workspace/level2_seed.json",
) -> list[dict[str, Any]]:
    """Reject open repair cards whose replayable seed prerequisite is now met."""

    root = Path(project)
    ledger = root / "workspace" / STRATEGY_LEDGER
    rejected: list[dict[str, Any]] = []
    for card in open_cards(ledger):
        if card.get("kind") != "compressed_counterexample_repair":
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        seed = plan.get("seed_prerequisite") if isinstance(plan.get("seed_prerequisite"), dict) else {}
        if seed.get("status") != "replayable_seed_missing":
            continue
        raw_path = seed.get("seed_path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        seed_path = Path(raw_path)
        if not seed_path.is_absolute():
            seed_path = root / seed_path
        if not seed_path.exists():
            continue
        out = dict(card)
        out["disposition"] = "rejected"
        out["counterexample"] = (
            "superseded by satisfied seed prerequisite: the requested "
            "replayable boundary seed now exists, so the current obligation is "
            "the seed-bound transfer/repair gate"
        )
        out["superseding_receipt"] = source_ref
        rejected.append(record_disposition(ledger, out))
    return rejected


def sync_replay_residual_repair_card(
    project: str | Path,
    diagnostics: dict[str, Any],
    *,
    source_ref: str = "workspace/latest_replay_diagnostics.json",
) -> dict[str, Any]:
    """Update Strategy Office repair cards from current replay diagnostics."""
    root = Path(project)
    dominated = reject_cards_dominated_by_candidate_memory(
        root,
        diagnostics,
        source_ref=source_ref,
    )
    if dominated:
        return {
            "schema": "ztare-replay-residual-repair-sync-v1",
            "project": str(root),
            "source_ref": source_ref,
            "rejected_stale_cards": 0,
            "rejected_candidate_dominated_cards": len(dominated),
            "cards_written": 0,
            "written": [],
            "authority": (
                "candidate-memory dominance only suppresses stale replay-repair "
                "routing; replay/holdout/live gates still own candidate adoption"
            ),
        }
    rejected = reject_stale_repair_cards(root, diagnostics, source_ref=source_ref)
    card = build_replay_residual_repair_card(diagnostics, source_ref=source_ref)
    written = (
        list(submit_strategy_card_batch(StrategyCardBatchSubmission(
            project_dir=root,
            cards=[card],
            source_ref=f"{source_ref}:residual_repair",
        )).get("written_cards") or [])
        if card is not None else []
    )
    return {
        "schema": "ztare-replay-residual-repair-sync-v1",
        "project": str(root),
        "source_ref": source_ref,
        "rejected_stale_cards": len(rejected),
        "cards_written": len(written),
        "written": written,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--diagnostics", default="workspace/latest_replay_diagnostics.json")
    args = ap.parse_args(argv)
    root = Path(args.project)
    diag_path = root / args.diagnostics
    diagnostics = json.loads(diag_path.read_text(encoding="utf-8"))
    print(json.dumps(
        sync_replay_residual_repair_card(root, diagnostics, source_ref=args.diagnostics),
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
