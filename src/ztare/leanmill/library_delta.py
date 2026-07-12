"""Library-delta receipts for LeanMill theory artifacts.

Kernel success answers whether declarations elaborate. Library review also
needs a compact view of the declaration API: public names, signatures, local
dependency edges, namespace placement, and concrete-vs-generic theorem shape.
This module emits that view deterministically for manifests and diagnostics.

The receipt is read-only telemetry. It does not decide proof credit, mutate the
substrate, or steer proof search.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import re
from typing import Any

from ztare.leanmill.control_plane import source_fingerprint
from ztare.leanmill.lean_source import (
    decl_blocks,
    decl_kind,
    decl_spans,
    identifier_token_mentions,
    signature_before_proof,
    strip_comments,
)


DEFINITION_KINDS = {"def", "abbrev", "structure", "inductive", "class"}
THEOREM_KINDS = {"theorem", "lemma"}
PUBLIC_KINDS = DEFINITION_KINDS | THEOREM_KINDS | {"instance", "opaque", "axiom"}


@dataclass(frozen=True)
class LibraryDecl:
    name: str
    kind: str
    namespace: str
    visibility: str
    signature_hash: str
    block_hash: str
    signature_text: str
    generality_flags: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LibraryEdge:
    source: str
    target: str
    target_kind: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LibraryDeltaReceipt:
    schema: str
    target_name: str
    public_decls: tuple[LibraryDecl, ...] = ()
    dependency_edges: tuple[LibraryEdge, ...] = ()
    summary: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "target_name": self.target_name,
            "public_decls": [d.to_json() for d in self.public_decls],
            "dependency_edges": [e.to_json() for e in self.dependency_edges],
            "summary": dict(self.summary),
            "warnings": list(self.warnings),
        }


def _decl_visibility(block: str) -> str:
    head = (block or "").splitlines()[0] if block else ""
    return "private" if re.match(r"\s*(?:noncomputable\s+)?private\b", head) else "public"


def _namespaces_by_decl_start(source: str) -> dict[int, str]:
    lines = (source or "").splitlines()
    spans = decl_spans(source or "")
    start_lines = {start for _, start, _ in spans}
    out: dict[int, str] = {}
    stack: list[tuple[str, str]] = []
    for idx, raw in enumerate(lines):
        s = strip_comments(raw).strip()
        if idx in start_lines:
            out[idx] = ".".join(name for kind, name in stack if kind == "namespace" and name)
        m_ns = re.match(r"namespace\s+([A-Za-z_][\w.']*)\s*$", s)
        if m_ns:
            stack.append(("namespace", m_ns.group(1)))
            continue
        m_section = re.match(r"section(?:\s+([A-Za-z_][\w.']*))?\s*$", s)
        if m_section:
            stack.append(("section", m_section.group(1) or ""))
            continue
        m_end = re.match(r"end(?:\s+([A-Za-z_][\w.']*))?\s*$", s)
        if m_end and stack:
            name = m_end.group(1) or ""
            if not name:
                stack.pop()
                continue
            for pos in range(len(stack) - 1, -1, -1):
                if stack[pos][1] == name:
                    del stack[pos:]
                    break
    return out


def _generality_flags(kind: str, sig: str) -> tuple[str, ...]:
    if kind not in THEOREM_KINDS:
        return ()
    flags: set[str] = set()
    if re.search(r"[:]\s*Type(?:\*|[ ]|$)", sig) or re.search(r"\{[^{}:]+:\s*Type", sig):
        flags.add("type_polymorphic")
    if "[" in sig and "]" in sig:
        flags.add("typeclass_parametric")
    if re.search(r"\b(Fintype|DecidableEq|LinearOrder|PartialOrder|Preorder)\b", sig):
        flags.add("structured_parametric")
    if re.search(r"\b(PUnit|Unit)\b", sig):
        flags.add("unit_or_punit_surface")
    if re.search(r"\bNat\b|\bInt\b|\bBool\b", sig) and "type_polymorphic" not in flags:
        flags.add("concrete_type_surface")
    if "type_polymorphic" not in flags and "typeclass_parametric" not in flags:
        flags.add("closed_or_concrete_surface")
    return tuple(sorted(flags))


def _decl_warnings(name: str, kind: str, sig: str, flags: tuple[str, ...]) -> tuple[str, ...]:
    warnings: set[str] = set()
    if kind in THEOREM_KINDS and "closed_or_concrete_surface" in flags and name and not name.startswith("anchor_"):
        warnings.add("theorem_surface_is_closed_or_concrete")
    if kind in THEOREM_KINDS and "unit_or_punit_surface" in flags and "counterexample" not in name.lower():
        warnings.add("unit_surface_outside_named_counterexample")
    if kind == "axiom":
        warnings.add("public_axiom")
    if kind == "opaque":
        warnings.add("opaque_public_decl")
    if kind in DEFINITION_KINDS and "Classical.choose" in sig:
        warnings.add("definition_signature_mentions_classical_choice")
    return tuple(sorted(warnings))


def emit_library_delta_receipt(source: str, *, target_name: str = "") -> LibraryDeltaReceipt:
    """Emit a deterministic declaration/API graph receipt for a Lean source file."""
    text = source or ""
    blocks = decl_blocks(text)
    spans = decl_spans(text)
    namespace_by_start = _namespaces_by_decl_start(text)
    rows: list[tuple[str, str, str, str, str, str]] = []
    for (name, block), (_, start, _) in zip(blocks, spans, strict=False):
        if not name:
            continue
        kind = decl_kind(block)
        if kind not in PUBLIC_KINDS:
            continue
        sig = " ".join((signature_before_proof(block) or block.splitlines()[0] if block else "").split())
        rows.append((name, kind, block, sig, namespace_by_start.get(start, ""), _decl_visibility(block)))

    kind_by_name = {name: kind for name, kind, *_ in rows}
    clean_blocks = {name: strip_comments(block) for name, _, block, *_ in rows}
    theorem_names = {name for name, kind, *_ in rows if kind in THEOREM_KINDS}
    definition_names = {name for name, kind, *_ in rows if kind in DEFINITION_KINDS}

    edges: list[LibraryEdge] = []
    for src_name, _kind, _block, _sig, _ns, _vis in rows:
        body = clean_blocks.get(src_name, "")
        for tgt_name, tgt_kind in kind_by_name.items():
            if tgt_name != src_name and identifier_token_mentions(body, tgt_name):
                edges.append(LibraryEdge(source=src_name, target=tgt_name, target_kind=tgt_kind))

    in_degree = Counter(e.target for e in edges)
    out_degree = Counter(e.source for e in edges)
    warnings: set[str] = set()
    decls: list[LibraryDecl] = []
    for name, kind, block, sig, ns, vis in rows:
        flags = _generality_flags(kind, sig)
        row_warnings = set(_decl_warnings(name, kind, sig, flags))
        if kind in DEFINITION_KINDS and not any(e.target == name and e.source in theorem_names for e in edges):
            row_warnings.add("definition_without_theorem_surface")
        if out_degree[name] >= 8:
            row_warnings.add("high_decl_fan_out")
        if in_degree[name] >= 8:
            row_warnings.add("high_decl_fan_in")
        warnings.update(row_warnings)
        decls.append(LibraryDecl(
            name=name,
            kind=kind,
            namespace=ns,
            visibility=vis,
            signature_hash=source_fingerprint(sig),
            block_hash=source_fingerprint(block),
            signature_text=sig,
            generality_flags=flags,
            warnings=tuple(sorted(row_warnings)),
        ))

    namespaces = sorted({d.namespace for d in decls})
    summary = {
        "public_decl_count": len(decls),
        "theorem_count": sum(1 for d in decls if d.kind in THEOREM_KINDS),
        "definition_count": sum(1 for d in decls if d.kind in DEFINITION_KINDS),
        "dependency_edge_count": len(edges),
        "namespace_count": len([n for n in namespaces if n]),
        "root_namespace_decl_count": sum(1 for d in decls if not d.namespace),
        "max_fan_in": max(in_degree.values(), default=0),
        "max_fan_out": max(out_degree.values(), default=0),
        "definition_without_theorem_surface_count": sum(
            1 for d in decls if "definition_without_theorem_surface" in d.warnings
        ),
        "closed_or_concrete_theorem_count": sum(
            1 for d in decls if "theorem_surface_is_closed_or_concrete" in d.warnings
        ),
        "target_present": bool(target_name and any(d.name == target_name for d in decls)),
        "warning_count": sum(1 for d in decls if d.warnings),
    }
    if target_name and not summary["target_present"]:
        warnings.add("target_decl_not_found")
    if decls and summary["namespace_count"] == 0 and len(decls) >= 12:
        warnings.add("many_public_decls_at_root_namespace")
    if definition_names and not theorem_names:
        warnings.add("definitions_without_theorem_layer")
    return LibraryDeltaReceipt(
        schema="leanmill.library_delta_receipt.v1",
        target_name=target_name,
        public_decls=tuple(decls),
        dependency_edges=tuple(edges),
        summary=summary,
        warnings=tuple(sorted(warnings)),
    )
