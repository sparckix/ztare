"""Briefing provider for Strategy Office experiment cards.

``workspace/strategy_experiments.jsonl`` is the cross-cycle office ledger:
cards here are not grammar operators and not candidate claims. They are
falsifiable next experiments selected from receipts. This provider is
reader-only and keeps those cards visible to the mutator/leaf that must execute
or refine the next step.
"""
from __future__ import annotations

import json
from pathlib import Path

from ztare.common.operator_proposal_contract import family_sha
from ztare.common.strategy_card_roles import (
    META_HARDENING_LANE,
    active_strategy_cards,
    blocking_strategy_cards,
    strategy_card_role,
)
from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider
from ztare.validator.core.strategy_card_gate import admissible_no_attempt_blocker_kinds


class StrategyExperimentsProvider(BriefingProvider):
    name = "strategy_experiments"
    priority = 34

    def _cards(self, project: Path) -> list[dict]:
        try:
            path = project / "workspace" / "strategy_experiments.jsonl"
            return [_card_with_sha(card) for card in active_strategy_cards(path)]
        except Exception:  # noqa: BLE001
            return []

    def _selected_cards(self, project: Path, *, limit: int) -> list[dict]:
        cards = self._cards(project)
        frontier = blocking_strategy_cards(cards, project_dir=project)
        # An identity-bound workbench task is the active work order.  Unbound
        # Strategy rows remain ledger history; re-appending them here would
        # turn case memory back into current task references after
        # ``blocking_strategy_cards`` deliberately removed them.
        try:
            from ztare.common.leaf_workbench_executor import (
                active_workbench_task_capability_scope,
            )

            scope, _task = active_workbench_task_capability_scope(project)
        except (OSError, ValueError, TypeError):
            scope = set()
        if scope:
            return frontier[:limit]
        selected = frontier + [card for card in cards if card not in frontier]
        return selected[:limit]

    def applies(self, ctx: BriefingContext) -> bool:
        return bool(self._cards(Path(getattr(ctx, "project_dir", "") or "")))

    def fragment(self, ctx: BriefingContext) -> str:
        project = Path(ctx.project_dir)
        cards = self._selected_cards(project, limit=5)
        if not cards:
            return ""
        lines = [
            "## Strategy Office Experiment Cards",
            "- These are falsifiable cross-cycle work orders from deterministic receipts. "
            "They do not certify a model and do not override gates.",
            "- Cards are ordered newest-first. The first blocking card for the active "
            "run lane is the frontier work order; older rows remain nonblocking case memory.",
            "- Object-level cards are current skill-acquisition obligations. Meta-hardening "
            "cards are queued apparatus work and do not block an executable candidate.",
            "- For object-level cards, include one typed receipt using the exact full "
            "`failure_family_sha` shown below. SHA prefixes do not match.",
            "- Receipt form: `STRATEGY_CARD_DISCHARGE: {\"failure_family_sha\": \"...\", "
            "\"outcome\": \"satisfied|refuted|blocked\", \"observed_status\": \"...\", "
            "\"evidence_refs\": [\"...\"]}`.",
            "- `satisfied` requires observed_status or next_gate_status equal to the "
            "listed next_gate success_status. A local patch, thesis, or quotient "
            "hypothesis without that gate result is blocked or refuted.",
            "- Put receipt lines outside code fences / test_model.py. If using the "
            "typed JSON payload, put them in `control_receipts`.",
            "- For repair cards, `blocked` must carry routing value: add `blocker_kind`, "
            "`next_action`, and either `attempted_repair`/`attempted_probe`, "
            "`new_evidence_refs`, or one card-listed no-attempt blocker.",
            "- Repair discipline: patch the quotient class, not every same-color "
            "or same-row sibling. A local fix is only satisfied by full replay "
            "no-regression or by an explicit operator/proposal card explaining "
            "why the broader equivalence class is necessary.",
        ]
        for card in cards:
            plan = card.get("action_plan") or {}
            role = strategy_card_role(card)
            lane = role.lane
            if lane == META_HARDENING_LANE:
                stale = _meta_hardening_projection_status(card)
                gate = plan.get("required_next_gate") or {}
                if stale:
                    lines.append(
                        f"- lane=meta_hardening; status=stale_projection; "
                        f"kind={card.get('kind', '?')}; "
                        f"sha={str(card.get('failure_family_sha', '?'))}; "
                        f"capability={_proposed_capability_id(card) or '?'}; "
                        f"reason={stale}. Do not treat this as an object-level blocker."
                    )
                    continue
                lines.append(
                    f"- lane=meta_hardening; kind={card.get('kind', '?')}; "
                    f"sha={str(card.get('failure_family_sha', '?'))}; "
                    f"target_artifact={plan.get('target_artifact', '?')}; "
                    f"mutable_surface={plan.get('mutable_surface', '?')}; "
                    f"capability={((plan.get('capability_contract') or {}).get('proposed_capability_id') or '?')}; "
                    f"evaluator={plan.get('evaluator', '')}; "
                    f"next_gate={gate.get('command', '?')}:{gate.get('success_status', '?')}; "
                    f"rollback={plan.get('rollback_condition', '')}"
                )
                continue
            if lane != "skill_acquisition":
                lines.append(
                    f"- lane={lane}; kind={card.get('kind', '?')}; "
                    f"sha={str(card.get('failure_family_sha', '?'))}; "
                    "status=nonblocking_control_memory. This row cannot block "
                    "the active skill-acquisition candidate."
                )
                continue
            gate = plan.get("required_next_gate") or {}
            residue = plan.get("residue_quotient") or {}
            repair = plan.get("repair_certificate") or {}
            hint = _first_refinement_hint(plan)
            witness = _residue_witness_summary(residue)
            seed = plan.get("seed_prerequisite") or {}
            no_attempt = admissible_no_attempt_blocker_kinds(card)
            routing = plan.get("routing_class") or "?"
            discriminator = plan.get("discriminator_axis") or {}
            axis = discriminator.get("axis") or "?"
            seed_bits = ""
            if seed:
                seed_bits = (
                    f"seed={seed.get('status', '?')}"
                    f"; seed_path={seed.get('seed_path', '?')}; "
                )
            repair_name = (
                hint.get("candidate_class")
                or repair.get("repair_class")
                or routing
            )
            lines.append(
                f"- lane={lane}; kind={card.get('kind', '?')}; "
                f"sha={str(card.get('failure_family_sha', '?'))}; "
                f"residue={residue.get('residue_class', '?')}; "
                f"witness={witness}; "
                f"{seed_bits}"
                f"repair={repair_name}; "
                f"axis={axis}; "
                f"prediction={card.get('falsifiable_prediction', '')}; "
                f"next_gate={gate.get('command', '?')}:{gate.get('success_status', '?')}; "
                f"no_attempt_blockers={no_attempt}; "
                f"kill={card.get('kill_condition', '')}"
            )
        digest = self._digest(Path(ctx.project_dir))
        if digest:
            lines.append("## Strategy Office Case Law Digest")
            for row in digest[-5:]:
                lines.append(
                    f"- disposition={row.get('disposition', '?')}; "
                    f"signature={row.get('proposal_signature', '?')}; "
                    f"reason={row.get('reason', '')}"
                )
        return "\n".join(lines) + "\n"

    def structured_records(self, ctx: BriefingContext) -> list[dict]:
        records = []
        for card in self._selected_cards(Path(ctx.project_dir), limit=8):
            plan = card.get("action_plan") or {}
            role = strategy_card_role(card)
            stale_meta = _meta_hardening_projection_status(card) if role.lane == META_HARDENING_LANE else ""
            residue = plan.get("residue_quotient") or {}
            repair = plan.get("repair_certificate") or {}
            hint = _first_refinement_hint(plan)
            discriminator = plan.get("discriminator_axis") or {}
            seed = plan.get("seed_prerequisite") or {}
            witness = _residue_witness_summary(residue)
            summary = card.get("rationale") or card.get("falsifiable_prediction") or ""
            if witness != "?":
                summary = f"{summary}; witness={witness}"
            if discriminator.get("axis"):
                summary = f"{summary}; axis={discriminator.get('axis')}"
            if hint.get("candidate_class"):
                summary = f"{summary}; target={hint.get('candidate_class')}"
            if seed.get("status"):
                summary = f"{summary}; seed={seed.get('status')}"
            no_attempt = admissible_no_attempt_blocker_kinds(card)
            required_transform = ""
            if card.get("kind") == "compressed_counterexample_repair" and (
                repair.get("sufficient_for_first_step") or hint.get("candidate_class")
            ):
                required_transform = (
                    "lower_certificate_to_carrier_or_refute_or_propose_capability"
                )
            records.append({
                "provider": self.name,
                "source_type": "strategy_experiment",
                "kind": card.get("kind"),
                "lane": role.lane,
                "role": role.to_dict(),
                "record_role": (
                    "stale_meta_hardening"
                    if stale_meta
                    else "advisory_control"
                    if role.lane not in {"skill_acquisition", META_HARDENING_LANE}
                    else None
                ),
                "stale_reason": stale_meta or None,
                "summary": summary,
                "action": card.get("falsifiable_prediction") or "",
                "source_ref": "workspace/strategy_experiments.jsonl",
                "failure_family_sha": card.get("failure_family_sha"),
                "required_receipt": "STRATEGY_CARD_DISCHARGE",
                "residue_class": residue.get("residue_class"),
                "seed_prerequisite": seed or None,
                "required_next_gate": plan.get("required_next_gate") or None,
                "admissible_no_attempt_blockers": no_attempt,
                "target_artifact": plan.get("target_artifact") or None,
                "mutable_surface": plan.get("mutable_surface") or None,
                "required_transform": required_transform or None,
                "repair_class": (
                    hint.get("candidate_class")
                    or repair.get("repair_class")
                    or plan.get("routing_class")
                ),
            })
        return records

    def _digest(self, project: Path) -> list[dict]:
        path = project / "workspace" / "leaf_proposals_digest.json"
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(payload, dict):
            return []
        rows = payload.get("last_k")
        return rows if isinstance(rows, list) else []


def _proposed_capability_id(card: dict) -> str:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    contract = plan.get("capability_contract") if isinstance(plan.get("capability_contract"), dict) else {}
    return str(
        contract.get("proposed_capability_id")
        or plan.get("proposed_capability_id")
        or ""
    ).strip()


def _meta_hardening_projection_status(card: dict) -> str:
    """Return why a meta-hardening card is stale for the current projection."""

    proposed = _proposed_capability_id(card)
    if not proposed:
        return ""
    try:
        from ztare.worldmodel.strategy_gate_actions import registered_strategy_gate_actions

        if proposed in registered_strategy_gate_actions():
            return (
                "proposed capability id is a registered Strategy gate command; "
                "use capability_id=run_strategy_required_gate instead"
            )
    except Exception:  # noqa: BLE001
        pass
    try:
        from ztare.common.visible_workbench_actions import route_visible_workbench_action_request

        route = route_visible_workbench_action_request(
            {"type": "LEAF_WORKBENCH_ACTION_REQUEST", "payload": {"capability_id": proposed}}
        )
    except Exception:  # noqa: BLE001
        return ""
    if route.get("status") == "ok" and route.get("route") in {"in_turn_cli", "parent_kernel"}:
        return f"proposed capability is already registered as route={route.get('route')}"
    return ""


def _first_refinement_hint(obj) -> dict:
    if isinstance(obj, dict):
        hint = obj.get("refinement_hint")
        if isinstance(hint, dict):
            return hint
        for val in obj.values():
            found = _first_refinement_hint(val)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _first_refinement_hint(item)
            if found:
                return found
    return {}


def _card_with_sha(card: dict) -> dict:
    out = dict(card)
    if not out.get("failure_family_sha") and out.get("failure_family") is not None:
        out["failure_family_sha"] = family_sha(out.get("failure_family"))
    return out


def _residue_witness_summary(residue: dict) -> str:
    if not isinstance(residue, dict) or not residue:
        return "?"
    bits: list[str] = []
    for key in ("class_count", "cell_count", "t", "action", "bbox"):
        value = residue.get(key)
        if value not in (None, "", [], {}):
            bits.append(f"{key}={value}")
    signature = residue.get("signature")
    pair_counts = signature.get("pair_counts") if isinstance(signature, dict) else None
    if isinstance(pair_counts, list) and pair_counts:
        pairs = []
        for row in pair_counts[:3]:
            if not isinstance(row, dict):
                continue
            predicted = row.get("predicted")
            real = row.get("real")
            count = row.get("count")
            if predicted is not None and real is not None:
                pairs.append(f"{predicted}->{real}x{count}")
        if pairs:
            bits.append("pairs=" + ",".join(pairs))
    return ";".join(bits) if bits else "?"
