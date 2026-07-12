"""Typed outbound requests for theory-language identity changes.

Conservative derived symbols expand inside the current signature.  A new sort,
primitive, observable, quotient, or abstraction changes the executable theory
language itself and therefore cannot be smuggled into a formula epoch.  This
module records that request for the blueprint compiler or AdapterForge without
granting it admission authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ztare.leanmill.theory_ir import content_hash


THEORY_LANGUAGE_CHANGE_KINDS = frozenset(
    {
        "new_sort",
        "new_operation",
        "new_relation",
        "new_observable",
        "abstraction_refinement",
        "quotient_or_coordinate_change",
    }
)


@dataclass(frozen=True)
class TheoryLanguageExpansionRequest:
    source_context_hash: str
    source_epoch: int
    change_kind: str
    blind_spot: str
    proposed_interface: str
    evidence_refs: tuple[str, ...]
    discriminating_test: str
    kill_condition: str
    schema: str = "leanmill.theory_language_expansion_request.v1"

    def __post_init__(self) -> None:
        if self.schema != "leanmill.theory_language_expansion_request.v1":
            raise ValueError("unsupported theory-language request schema")
        if not self.source_context_hash or self.source_epoch < 0:
            raise ValueError("language expansion requires source context identity")
        if self.change_kind not in THEORY_LANGUAGE_CHANGE_KINDS:
            raise ValueError("unsupported theory-language change kind")
        for field_name in (
            "blind_spot",
            "proposed_interface",
            "discriminating_test",
            "kill_condition",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"language expansion requires {field_name}")
        if not self.evidence_refs:
            raise ValueError("language expansion requires inspectable evidence refs")

    @property
    def request_id(self) -> str:
        return "theory-language-request:" + content_hash(
            self.to_json(include_id=False)
        )

    def to_json(self, *, include_id: bool = True) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "source_context_hash": self.source_context_hash,
            "source_epoch": self.source_epoch,
            "change_kind": self.change_kind,
            "blind_spot": self.blind_spot,
            "proposed_interface": self.proposed_interface,
            "evidence_refs": list(self.evidence_refs),
            "discriminating_test": self.discriminating_test,
            "kill_condition": self.kill_condition,
            "authority": "proposal_only",
            "required_transition": "new_reviewed_blueprint_or_adapter_capability",
        }
        return {**core, "request_id": self.request_id} if include_id else core

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "TheoryLanguageExpansionRequest":
        required = {
            "schema",
            "source_context_hash",
            "source_epoch",
            "change_kind",
            "blind_spot",
            "proposed_interface",
            "evidence_refs",
            "discriminating_test",
            "kill_condition",
            "authority",
            "required_transition",
            "request_id",
        }
        if set(value) != required:
            raise ValueError("theory-language request fields do not match its schema")
        if (
            value.get("authority") != "proposal_only"
            or value.get("required_transition")
            != "new_reviewed_blueprint_or_adapter_capability"
        ):
            raise ValueError("theory-language request claims unsupported authority")
        request = cls(
            schema=str(value["schema"]),
            source_context_hash=str(value["source_context_hash"]),
            source_epoch=int(value["source_epoch"]),
            change_kind=str(value["change_kind"]),
            blind_spot=str(value["blind_spot"]),
            proposed_interface=str(value["proposed_interface"]),
            evidence_refs=tuple(str(row) for row in value["evidence_refs"]),
            discriminating_test=str(value["discriminating_test"]),
            kill_condition=str(value["kill_condition"]),
        )
        if value["request_id"] != request.request_id:
            raise ValueError("theory-language request digest mismatch")
        return request


def build_theory_language_expansion_request(
    *,
    source_context_hash: str,
    source_epoch: int,
    change_kind: str,
    blind_spot: str,
    proposed_interface: str,
    evidence_refs: Sequence[str],
    discriminating_test: str,
    kill_condition: str,
) -> TheoryLanguageExpansionRequest:
    return TheoryLanguageExpansionRequest(
        source_context_hash=source_context_hash,
        source_epoch=source_epoch,
        change_kind=change_kind,
        blind_spot=blind_spot,
        proposed_interface=proposed_interface,
        evidence_refs=tuple(str(row) for row in evidence_refs if str(row)),
        discriminating_test=discriminating_test,
        kill_condition=kill_condition,
    )


__all__ = [
    "THEORY_LANGUAGE_CHANGE_KINDS",
    "TheoryLanguageExpansionRequest",
    "build_theory_language_expansion_request",
]
