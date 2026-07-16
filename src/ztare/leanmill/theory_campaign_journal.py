"""Append-only scientific state for frontier theory campaigns.

The journal is the reciprocal integration membrane: context construction,
navigation, countermodels, proofs, definitions, and promotion communicate by
immutable events rather than importing one another's internal state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.leanmill.common import append_jsonl_locked
from ztare.leanmill.theory_ir import content_hash


EVENT_SCHEMA = "leanmill.theory_campaign_event.v1"
ALLOWED_EVENT_TYPES = frozenset(
    {
        "model_added",
        "formula_added",
        "theory_presentation_submitted",
        "theory_presentation_rejected",
        "theory_program_refused",
        "bounded_closure_computed",
        "countermodel_found",
        "conditional_consequence_proved",
        "conditional_consequence_refuted",
        "proof_attempt_unresolved",
        "conflict_learned",
        "abstraction_refined",
        "definition_proposed",
        "definition_retained",
        "structural_transport_proposed",
        "finalist_frozen",
        "sealed_evaluation_completed",
        "evidence_promoted_to_next_epoch",
        "navigator_action_executed",
        "navigator_agent_turn_failed",
        "navigator_candidate_deduplicated",
        "navigator_reject_all",
        "boundary_query_completed",
        "theory_task_adjudicated",
        "context_epoch_proposed",
    }
)
EVIDENCE_STATUSES = frozenset(
    {"proposed", "bounded_exact", "witnessed", "proved", "unresolved", "frozen"}
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class TheoryCampaignEvent:
    attempt_id: str
    campaign_id: str
    epoch: int
    context_hash: str
    event_type: str
    subject_ids: tuple[str, ...]
    input_refs: tuple[str, ...] = ()
    output_refs: tuple[str, ...] = ()
    evidence_status: str = "proposed"
    authority: str = "host"
    parent_event_ids: tuple[str, ...] = ()
    created_at: str = field(default_factory=_utc_now)
    event_id: str = ""
    schema: str = EVENT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != EVENT_SCHEMA:
            raise ValueError(f"unsupported event schema: {self.schema!r}")
        for name in ("attempt_id", "campaign_id", "context_hash", "authority", "created_at"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        if type(self.epoch) is not int or self.epoch < 0:
            raise ValueError("epoch must be a nonnegative integer")
        if self.event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"unknown theory campaign event type: {self.event_type!r}")
        if self.evidence_status not in EVIDENCE_STATUSES:
            raise ValueError(f"unknown evidence status: {self.evidence_status!r}")
        if not self.subject_ids:
            raise ValueError("subject_ids must be non-empty")
        expected = content_hash(self._identity_payload())
        if self.event_id and self.event_id != expected:
            raise ValueError("event_id does not match immutable event payload")
        object.__setattr__(self, "event_id", expected)

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "attempt_id": self.attempt_id,
            "campaign_id": self.campaign_id,
            "epoch": self.epoch,
            "context_hash": self.context_hash,
            "event_type": self.event_type,
            "subject_ids": list(self.subject_ids),
            "input_refs": list(self.input_refs),
            "output_refs": list(self.output_refs),
            "evidence_status": self.evidence_status,
            "authority": self.authority,
            "parent_event_ids": list(self.parent_event_ids),
            "created_at": self.created_at,
        }

    def to_json(self) -> dict[str, Any]:
        return {**self._identity_payload(), "event_id": self.event_id}

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "TheoryCampaignEvent":
        required = {
            "schema", "event_id", "attempt_id", "campaign_id", "epoch",
            "context_hash", "event_type", "subject_ids", "input_refs",
            "output_refs", "evidence_status", "authority", "parent_event_ids",
            "created_at",
        }
        if set(value) != required:
            raise ValueError("event fields do not match the frozen schema")
        return cls(
            schema=str(value["schema"]),
            event_id=str(value["event_id"]),
            attempt_id=str(value["attempt_id"]),
            campaign_id=str(value["campaign_id"]),
            epoch=int(value["epoch"]),
            context_hash=str(value["context_hash"]),
            event_type=str(value["event_type"]),
            subject_ids=tuple(str(row) for row in value["subject_ids"]),
            input_refs=tuple(str(row) for row in value["input_refs"]),
            output_refs=tuple(str(row) for row in value["output_refs"]),
            evidence_status=str(value["evidence_status"]),
            authority=str(value["authority"]),
            parent_event_ids=tuple(str(row) for row in value["parent_event_ids"]),
            created_at=str(value["created_at"]),
        )


@dataclass(frozen=True)
class TheoryCampaignViews:
    campaign_id: str
    latest_epoch: int
    context_by_epoch: Mapping[int, str]
    theory_archive: Mapping[str, TheoryCampaignEvent]
    proof_panel: Mapping[str, TheoryCampaignEvent]
    conflict_memory: Mapping[str, TheoryCampaignEvent]
    definition_library: Mapping[str, TheoryCampaignEvent]
    finalists: Mapping[str, TheoryCampaignEvent]


def validate_event_sequence(events: Iterable[TheoryCampaignEvent]) -> tuple[TheoryCampaignEvent, ...]:
    rows = tuple(events)
    if not rows:
        return rows
    campaign_id = rows[0].campaign_id
    seen: set[str] = set()
    context_by_epoch: dict[int, str] = {}
    # A journal may be a lineage shard created after the campaign has already
    # advanced.  The campaign ledger owns genesis; this shard owns monotonicity
    # from its first observed epoch onward.
    previous_epoch = rows[0].epoch
    for event in rows:
        if event.campaign_id != campaign_id:
            raise ValueError("one journal cannot mix campaign IDs")
        if event.event_id in seen:
            raise ValueError(f"duplicate event_id: {event.event_id}")
        missing_parents = set(event.parent_event_ids) - seen
        if missing_parents:
            raise ValueError(f"event refers to unseen parents: {sorted(missing_parents)}")
        if event.epoch < previous_epoch or event.epoch > previous_epoch + 1:
            raise ValueError("epochs must be monotone and advance one step at a time")
        bound = context_by_epoch.setdefault(event.epoch, event.context_hash)
        if bound != event.context_hash:
            raise ValueError("one epoch cannot carry multiple context hashes")
        if event.epoch > previous_epoch and previous_epoch >= 0:
            if event.context_hash == context_by_epoch[previous_epoch]:
                raise ValueError("a new epoch requires a new context hash")
        previous_epoch = event.epoch
        seen.add(event.event_id)
    return rows


def materialize_campaign_views(events: Iterable[TheoryCampaignEvent]) -> TheoryCampaignViews:
    rows = validate_event_sequence(events)
    if not rows:
        raise ValueError("cannot materialize an empty campaign journal")
    contexts: dict[int, str] = {}
    theories: dict[str, TheoryCampaignEvent] = {}
    proofs: dict[str, TheoryCampaignEvent] = {}
    conflicts: dict[str, TheoryCampaignEvent] = {}
    definitions: dict[str, TheoryCampaignEvent] = {}
    finalists: dict[str, TheoryCampaignEvent] = {}
    for event in rows:
        contexts[event.epoch] = event.context_hash
        target = None
        if event.event_type in {"theory_presentation_submitted", "bounded_closure_computed"}:
            target = theories
        elif event.event_type in {
            "conditional_consequence_proved", "proof_attempt_unresolved",
            "sealed_evaluation_completed",
        }:
            target = proofs
        elif event.event_type in {
            "countermodel_found", "conditional_consequence_refuted", "conflict_learned"
        }:
            target = conflicts
        elif event.event_type in {"definition_proposed", "definition_retained"}:
            target = definitions
        elif event.event_type == "finalist_frozen":
            target = finalists
        if target is not None:
            for subject_id in event.subject_ids:
                target[subject_id] = event
    return TheoryCampaignViews(
        campaign_id=rows[0].campaign_id,
        latest_epoch=rows[-1].epoch,
        context_by_epoch=contexts,
        theory_archive=theories,
        proof_panel=proofs,
        conflict_memory=conflicts,
        definition_library=definitions,
        finalists=finalists,
    )


class TheoryCampaignJournal:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def replay(self) -> tuple[TheoryCampaignEvent, ...]:
        if not self.path.exists():
            return ()
        rows: list[TheoryCampaignEvent] = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("event must be a JSON object")
                rows.append(TheoryCampaignEvent.from_json(raw))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid campaign journal line {line_number}: {exc}") from exc
        return validate_event_sequence(rows)

    def append(self, event: TheoryCampaignEvent) -> bool:
        existing = self.replay()
        if any(row.event_id == event.event_id for row in existing):
            return False
        validate_event_sequence((*existing, event))
        if not append_jsonl_locked(self.path, event.to_json(), ensure_ascii=True):
            # The shared helper may have completed its plain-append fallback.
            # Replay decides whether durability produced a valid journal.
            replayed = self.replay()
            if not replayed or replayed[-1].event_id != event.event_id:
                raise OSError("campaign event append could not be verified")
        return True

    def views(self) -> TheoryCampaignViews:
        return materialize_campaign_views(self.replay())


class IdempotentReplayJournal:
    """Replay host actions without duplicating an event under a fresh timestamp."""

    def __init__(self, journal: TheoryCampaignJournal | str | Path) -> None:
        self.journal = (
            journal
            if isinstance(journal, TheoryCampaignJournal)
            else TheoryCampaignJournal(journal)
        )

    @staticmethod
    def _semantic_identity(event: TheoryCampaignEvent) -> tuple[Any, ...]:
        return (
            event.attempt_id,
            event.campaign_id,
            event.epoch,
            event.context_hash,
            event.event_type,
            event.subject_ids,
            event.input_refs,
            event.output_refs,
            event.evidence_status,
            event.authority,
            event.parent_event_ids,
        )

    def replay(self) -> tuple[TheoryCampaignEvent, ...]:
        return self.journal.replay()

    def append(self, event: TheoryCampaignEvent) -> bool:
        identity = self._semantic_identity(event)
        if any(
            self._semantic_identity(prior) == identity
            for prior in self.journal.replay()
        ):
            return False
        return self.journal.append(event)

    def views(self) -> TheoryCampaignViews:
        return self.journal.views()


__all__ = [
    "ALLOWED_EVENT_TYPES", "EVENT_SCHEMA", "EVIDENCE_STATUSES",
    "IdempotentReplayJournal", "TheoryCampaignEvent", "TheoryCampaignJournal",
    "TheoryCampaignViews",
    "materialize_campaign_views", "validate_event_sequence",
]
