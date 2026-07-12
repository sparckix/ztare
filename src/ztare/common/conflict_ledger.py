from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ConflictClause:
    signature: str
    receipts_refs: tuple[str, ...] = ()
    witness_summary: str = ""
    provenance: Any = None
    defeasible: bool = False


@runtime_checkable
class ConflictLedger(Protocol):
    def learn(self, conflict_receipt: Any) -> ConflictClause: ...

    def blocks(self, candidate_signature: str) -> ConflictClause | None: ...

    def revive(self, evidence_card: Any) -> Any: ...

    def open_clauses(self) -> list[ConflictClause]: ...
