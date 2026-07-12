"""Definition/API contracts for LeanMill theory artifacts.

The Lean kernel can certify a theorem whose surrounding vocabulary is awkward
to reuse or slightly different from the blueprint's intended API. This module
emits a small, deterministic receipt for introduced definitions so campaigns
can expose that gap without turning it into a proof verdict.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ztare.leanmill.lean_source import (
    decl_blocks,
    decl_kind,
    extract_signature,
    identifier_token_mentions,
    signature_before_proof,
    strip_comments,
)


DEFINITION_KINDS = {"def", "abbrev", "structure", "inductive", "class"}
THEOREM_KINDS = {"theorem", "lemma"}


@dataclass(frozen=True)
class DefinitionContract:
    name: str
    kind: str
    computability: str
    source_hash: str
    name_signature_text: str = ""
    referenced_by_statements: tuple[str, ...] = ()
    api_surface: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DefinitionApiReceipt:
    schema: str
    target_name: str
    definitions: tuple[DefinitionContract, ...] = ()
    summary_flags: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "target_name": self.target_name,
            "definitions": [d.to_json() for d in self.definitions],
            "summary_flags": list(self.summary_flags),
            "notes": list(self.notes),
        }


def _hash_block(block: str) -> str:
    from ztare.leanmill.control_plane import source_fingerprint
    return source_fingerprint(block or "")


def _name_signature_text(name: str, block: str) -> str:
    sig = " ".join((signature_before_proof(block or "") or "").split())
    return f"{name} :: {sig}" if sig else name


def _computability(block: str) -> str:
    head = (block or "").splitlines()[0] if block else ""
    clean = strip_comments(block or "")
    if "noncomputable def " in head or "noncomputable " in head:
        return "noncomputable"
    if "Classical.choose" in clean or "Classical.choice" in clean:
        return "classical"
    return "computable_or_structural"


def emit_definition_api_receipt(source: str, *, target_name: str = "") -> DefinitionApiReceipt:
    """Return a deterministic receipt for introduced definitions and their API surface.

    This is intentionally syntactic. It does not prove a definition correct; it
    makes review-relevant modeling/API facts visible: noncomputable definitions,
    definitions used by the target statement, and whether each definition has
    named theorem/lemma surface around it.
    """
    blocks = [(name, block, decl_kind(block)) for name, block in decl_blocks(source or "") if name]
    def_blocks = [(n, b, k) for n, b, k in blocks if k in DEFINITION_KINDS]
    theorem_blocks = [(n, b) for n, b, k in blocks if k in THEOREM_KINDS]
    theorem_sigs = {n: extract_signature(source or "", n) for n, _ in theorem_blocks}
    target_sig = theorem_sigs.get(target_name, "") if target_name else ""

    contracts: list[DefinitionContract] = []
    summary_flags: set[str] = set()
    notes: list[str] = []
    for name, block, kind in def_blocks:
        mentioned = tuple(sorted(n for n, sig in theorem_sigs.items() if identifier_token_mentions(sig, name)))
        api = tuple(sorted(n for n, b in theorem_blocks if n != target_name and identifier_token_mentions(b, name)))
        flags: set[str] = set()
        comp = _computability(block)
        if comp in {"noncomputable", "classical"}:
            flags.add(comp)
            summary_flags.add(f"has_{comp}_definition")
        if target_sig and identifier_token_mentions(target_sig, name) and not api:
            flags.add("target_depends_without_named_api")
            summary_flags.add("target_definition_without_named_api")
        if kind == "structure" and "Prop" not in block and "NoDuplicate" not in block and "Injective" not in block:
            flags.add("structure_without_visible_invariant")
        contracts.append(DefinitionContract(
            name=name,
            kind=kind,
            computability=comp,
            source_hash=_hash_block(block),
            name_signature_text=_name_signature_text(name, block),
            referenced_by_statements=mentioned,
            api_surface=api,
            flags=tuple(sorted(flags)),
        ))
    if not contracts:
        notes.append("no local definitions detected")
    return DefinitionApiReceipt(
        schema="leanmill.definition_api_receipt.v1",
        target_name=target_name,
        definitions=tuple(contracts),
        summary_flags=tuple(sorted(summary_flags)),
        notes=tuple(notes),
    )
