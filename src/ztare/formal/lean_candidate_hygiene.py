"""Shared hygiene checks for generated Lean candidate files.

These helpers are intentionally syntax-level. They are not a substitute for
Lean elaboration, but they remove common low-value failure modes before proof
search scripts count a candidate as useful:

* filesystem-style imports emitted by LLMs,
* previews that truncate identifiers into fake names,
* decorative wrappers that re-export an endpoint field,
* duplicate top-level declarations.
"""
from __future__ import annotations

import re


def safe_preview(text: str, max_chars: int) -> str:
    """Return a prompt preview without cutting through identifiers."""
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    cut = stripped.rfind("\n", 0, max_chars)
    if cut < max_chars // 2:
        cut = -1
        for i in range(min(max_chars, len(stripped)) - 1, -1, -1):
            ch = stripped[i]
            if not (ch.isalnum() or ch in "_'"):
                cut = i
                break
    if cut < max_chars // 2:
        cut = max_chars
        while cut > 0 and (stripped[cut - 1].isalnum() or stripped[cut - 1] in "_'"):
            cut -= 1
        if cut < max_chars // 2:
            cut = max_chars
    return stripped[:cut].rstrip() + "\n-- [truncated preview; full declaration omitted]"


def normalize_candidate_source(src: str) -> str:
    """Normalize common generated Lean hygiene mistakes before compile.

    This is intentionally narrow: repair only module import spelling, not
    theorem statements or proof terms.
    """
    return re.sub(
        r"^import\s+ztare_proofs\.ZtareProofs\.",
        "import ZtareProofs.",
        src,
        flags=re.MULTILINE,
    )


def extract_lean_blocks(text: str) -> list[str]:
    return [
        m.group(1).strip()
        for m in re.finditer(r"```lean\s*\n([\s\S]*?)\n\s*```", text)
    ]


def extract_lean_block(text: str) -> str | None:
    m = re.search(r"```lean\s*\n([\s\S]*?)\n\s*```", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"```lean\s*\n([\s\S]*)\Z", text)
    return m.group(1).strip() if m else None


def extract_top_level_decl_names(lean_src: str) -> list[str]:
    decl_re = re.compile(
        r"^(?:private\s+)?"
        r"(theorem|lemma|def|structure|class|instance|abbrev|inductive)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)",
        re.MULTILINE,
    )
    return [m.group(2) for m in decl_re.finditer(lean_src)]


def duplicate_decl_names(lean_src: str, decl_index: dict) -> list[str]:
    decls = decl_index.get("decls", {})
    return [
        name
        for name in extract_top_level_decl_names(lean_src)
        if name in decls
    ]


def decorative_negation_wrapper(lean_src: str) -> bool:
    normalized = re.sub(r"\s+", " ", lean_src)
    return bool(
        re.search(r"\(\s*h\s*:\s*¬", normalized)
        and re.search(r":\s*False\s*:?=\s*(by\s*)?h\s*\(", normalized)
    )


def candidate_degeneracy_reason(
    src: str,
    *,
    target: str,
    field: str,
    allow_target_field_reference: bool = False,
    require_source_witness: bool = False,
) -> str | None:
    """Return a reason when a compiled candidate is only bookkeeping.

    Lake can verify wrappers that merely restate an existing structure field:

        theorem t (R : Target) : ... := by
          exact R.someField

    Those are sometimes useful local API conveniences, but they are not
    source-witness or closure progress.
    """
    if not re.search(r"\b(theorem|lemma|def|structure|instance)\s+\w", src):
        return "no_declaration"

    if (
        require_source_witness
        and re.search(rf"\([^)]*:\s*{re.escape(target)}\)", src)
    ):
        return "target_record_argument_in_source_witness_mode"

    if not re.search(rf"\([^)]*:\s*{re.escape(target)}\)", src):
        return None

    proof_match = re.search(r":=\s*by\s*\n(?P<body>[\s\S]+)$", src)
    if not proof_match:
        return None

    proof_body = proof_match.group("body")
    if (
        not allow_target_field_reference
        and re.search(rf"\b\w+\.{re.escape(field)}\b", proof_body)
    ):
        return "target_field_self_reference"

    body_lines = [
        line.strip()
        for line in proof_body.splitlines()
        if line.strip()
        and not line.strip().startswith("--")
        and line.strip() not in {"end ZtareProofs.NS", "end"}
    ]
    if len(body_lines) != 1:
        return None

    field_accessor = rf"\b\w+\.{re.escape(field)}(?:\.symm)?\b"
    direct_exact = rf"^exact\s+\(?{field_accessor}\)?$"
    direct_simpa = rf"^simpa(?:\s+\[[^\]]*\])?\s+using\s+\(?{field_accessor}\)?$"
    if re.search(direct_exact, body_lines[0]) or re.search(direct_simpa, body_lines[0]):
        return "direct_target_field_accessor"
    return None
