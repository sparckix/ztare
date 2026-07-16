"""Typed LeanMill control-plane carriers.

This module is intentionally free of solver imports. It gives proof-search,
falsification, cache, and diagnostics paths one vocabulary for the concepts
that kept drifting across the Gale/CLOB campaigns:

* statement identity,
* consequential verdicts,
* cache authority class.

The first adoption layer is diagnostics-only. Callers can attach these carriers
to manifests, logs, and tests before proof-credit paths migrate to them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
import re
from typing import Any, Mapping


def _norm_ws(text: str) -> str:
    return " ".join((text or "").split())


def _sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _sha256_file(path: str | Path | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_fingerprint(source_text: str) -> str:
    return _sha256_text(source_text or "")


def prop_fingerprint(prop_text: str) -> str:
    return _sha256_text(_norm_ws(prop_text))


def nl_fingerprint(nl_text: str) -> str:
    return _sha256_text(_norm_ws(nl_text))


def substrate_fingerprint(path: str | Path | None = None, *, text: str = "") -> str:
    if text:
        return _sha256_text(text)
    return _sha256_file(path)


@dataclass(frozen=True)
class StatementId:
    """Identity of the proposition a proof-bearing path is adjudicating."""

    target_name: str
    target_source_hash: str
    closed_prop_hash: str
    nl_exact_hash: str = ""
    substrate_fingerprint: str = ""
    closed_prop_norm: str = ""

    @classmethod
    def from_parts(
        cls,
        *,
        target_name: str,
        source_text: str = "",
        closed_prop: str = "",
        nl_exact: str = "",
        substrate_path: str | Path | None = None,
        substrate_text: str = "",
    ) -> "StatementId":
        prop_norm = _norm_ws(closed_prop)
        return cls(
            target_name=target_name or "",
            target_source_hash=source_fingerprint(source_text),
            closed_prop_hash=prop_fingerprint(prop_norm),
            nl_exact_hash=nl_fingerprint(nl_exact),
            substrate_fingerprint=substrate_fingerprint(substrate_path, text=substrate_text),
            closed_prop_norm=prop_norm,
        )

    def cache_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.target_name,
            self.target_source_hash,
            self.closed_prop_hash,
            self.nl_exact_hash,
            self.substrate_fingerprint,
        )

    def to_json(self, *, include_prop: bool = False) -> dict[str, Any]:
        obj = asdict(self)
        if not include_prop:
            obj.pop("closed_prop_norm", None)
        return obj

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "StatementId":
        return cls(
            target_name=str(value.get("target_name") or ""),
            target_source_hash=str(value.get("target_source_hash") or ""),
            closed_prop_hash=str(value.get("closed_prop_hash") or ""),
            nl_exact_hash=str(value.get("nl_exact_hash") or ""),
            substrate_fingerprint=str(value.get("substrate_fingerprint") or ""),
            closed_prop_norm=str(value.get("closed_prop_norm") or ""),
        )


class VerdictKind(str, Enum):
    CLOSED = "closed"
    REFUTED = "refuted"
    UNVERIFIED = "unverified"
    REJECTED_BY_GOVERNANCE = "rejected_by_governance"
    SUBSTRATE_UNAVAILABLE = "substrate_unavailable"
    SUBSTRATE_BROKEN = "substrate_broken"


@dataclass(frozen=True)
class Verdict:
    kind: VerdictKind
    statement_id: StatementId
    provenance: str
    detail: str = ""
    artifacts: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "statement_id": self.statement_id.to_json(),
            "provenance": self.provenance,
            "detail": self.detail,
            "artifacts": dict(self.artifacts),
        }

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "Verdict":
        statement_id = value.get("statement_id")
        if not isinstance(statement_id, Mapping):
            raise ValueError("verdict requires statement identity")
        artifacts = value.get("artifacts")
        if artifacts is not None and not isinstance(artifacts, Mapping):
            raise ValueError("verdict artifacts must be an object")
        return cls(
            kind=VerdictKind(str(value.get("kind") or "")),
            statement_id=StatementId.from_json(statement_id),
            provenance=str(value.get("provenance") or ""),
            detail=str(value.get("detail") or ""),
            artifacts={str(key): str(item) for key, item in dict(artifacts or {}).items()},
        )

    def kernel_refutation_source(self) -> str:
        """Return content-bound Lean bytes only for a typed refutation verdict."""
        if self.kind is not VerdictKind.REFUTED:
            return ""
        source = str(self.artifacts.get("lean_source") or "")
        digest = str(self.artifacts.get("lean_source_sha256") or "")
        return source if source and digest == _sha256_text(source) else ""


class CacheAuthority(str, Enum):
    PROOF_CREDIT = "proof_credit"
    AFFORDANCE = "affordance"


class SubstrateMutationKind(str, Enum):
    BANK_DECL_TO_ENV = "bank_decl_to_env"
    FAMILY_BANK = "family_bank"
    REVERIFY = "reverify"


@dataclass(frozen=True)
class SubstrateMutationReceipt:
    kind: SubstrateMutationKind
    target_name: str
    context_path: str
    stage: str
    before_sha256: str
    after_sha256: str
    changed: bool
    result: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "target_name": self.target_name,
            "context_path": self.context_path,
            "stage": self.stage,
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "changed": bool(self.changed),
            "result": dict(self.result),
        }


_AFFORDANCE_CACHE_NAMES = {
    "semantic_shelf",
    "semantic_reference",
    "staged_reuse",
    "staged_proof",
    "wip_probe",
}

_PROOF_CREDIT_CACHE_NAMES = {
    "proof_cache",
    "banked_rung",
    "banked_lemma",
    "exact_reference_reuse",
    "decomposition_cache",
}


def cache_authority(name: str) -> CacheAuthority:
    key = re.sub(r"[^a-z0-9_]+", "_", (name or "").strip().lower())
    if key in _AFFORDANCE_CACHE_NAMES:
        return CacheAuthority.AFFORDANCE
    if key in _PROOF_CREDIT_CACHE_NAMES:
        return CacheAuthority.PROOF_CREDIT
    return CacheAuthority.AFFORDANCE
