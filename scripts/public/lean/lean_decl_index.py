#!/usr/bin/env python3
"""Stage 1: typed nomination filter — scan Lean spine for declarations.

Builds an index of every declaration in ztare_proofs/ZtareProofs/ for use
by the closed loop's pre-build validator. Each entry: name, kind (def /
structure / theorem / lemma / class / instance), source file, signature.

Pre-filter rejects LLM nominations that reference identifiers not in
the index and are not locally bound by the nominated theorem. It is a
cheap pre-build guard, not a replacement for Lean elaboration.

Usage:
    python scripts/public/lean/lean_decl_index.py --build
    python scripts/public/lean/lean_decl_index.py --check 'theorem foo : a ≤ b := ...'
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEAN_DIR = REPO / "ztare_proofs" / "ZtareProofs"
INDEX_PATH = REPO / "analytics" / "public" / "queries" / "lean" / "lean_decl_index.json"

DECL_KIND_RE = re.compile(
    r"^(theorem|lemma|def|structure|class|instance|abbrev|inductive)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)",
    re.MULTILINE,
)
FIELD_RE = re.compile(
    r"^\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\)\s*)*:\s+",
)
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
BINDER_RE = re.compile(r"[\(\{\[]\s*([A-Za-z_][A-Za-z0-9_]*(?:\s+[A-Za-z_][A-Za-z0-9_]*)*)\s*:")
FORALL_RE = re.compile(r"[∀]\s*([A-Za-z_][A-Za-z0-9_]*(?:\s+[A-Za-z_][A-Za-z0-9_]*)*)\s*:")

# Lean / mathlib things we don't need to resolve locally
GLOBAL_OK = {
    "theorem", "lemma", "def", "structure", "class", "instance", "abbrev",
    "import", "namespace", "end", "open", "section", "variable", "variables",
    "by", "exact", "apply", "intro", "intros", "refine", "use", "have",
    "show", "from", "rfl", "ring", "linarith", "omega", "simp", "Real",
    "Nat", "Int", "Rat", "Set", "List", "Option", "Prop", "Type", "Sort",
    "True", "False", "And", "Or", "Not", "Eq", "Iff", "ℝ", "ℕ", "ℤ", "ℚ",
    "Real.exp", "Real.log", "Real.sqrt", "Real.pi", "max", "min", "abs",
    "sup", "inf", "pow", "fun", "let", "in", "if", "then", "else",
    "with", "match", "where", "do", "this", "and", "or", "not",
    "Classical", "Decidable", "Finset", "Function", "Mathlib",
}

DEFAULT_EXCLUDE_GLOBS = (
    "*_iter.lean",
    "*_smoke*.lean",
    "closed_loop_*.lean",
    "*_axioms.lean",
)


def _split_names(group: str) -> list[str]:
    return [
        name for name in group.replace(",", " ").split()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
    ]


def local_names_in_snippet(text: str) -> set[str]:
    """Return names introduced by the nominated snippet itself.

    This intentionally covers only cheap syntactic binders. Lean elaboration
    remains the authoritative type checker.
    """
    return declared_names_in_snippet(text) | binder_names_in_snippet(text)


def declared_names_in_snippet(text: str) -> set[str]:
    """Return declaration names introduced by the nominated snippet."""
    return {m.group(2) for m in DECL_KIND_RE.finditer(text)}


def binder_names_in_snippet(text: str) -> set[str]:
    """Return binder names introduced by theorem/lemma parameters."""
    locals_: set[str] = set()
    for regex in (BINDER_RE, FORALL_RE):
        for m in regex.finditer(text):
            locals_.update(_split_names(m.group(1)))
    return locals_


def identifier_check_surface(text: str) -> str:
    """Return the part of a Lean snippet whose identifiers should be prechecked.

    Proof bodies routinely use Mathlib lemmas or local names that a regex index
    cannot resolve reliably. The cheap typed filter is intended to reject bad
    theorem statements before lake time, so it inspects only the declaration
    surface up to `:=` when present.
    """
    surface = text.split(":=", 1)[0]
    filtered_lines = []
    for line in surface.splitlines():
        stripped = line.strip()
        if re.match(r"^(import|open|namespace|end|section)\b", stripped):
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines)


def _index_field_decls(text: str, path: Path, index: dict[str, list[dict]]) -> None:
    """Index simple structure/class fields as locally resolvable identifiers."""
    lines = text.splitlines()
    current_container: str | None = None
    in_container = False
    for line_no, line in enumerate(lines, 1):
        decl = re.match(
            r"^(structure|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b.*\bwhere\b",
            line,
        )
        if decl:
            current_container = decl.group(2)
            in_container = True
            continue
        if in_container and re.match(
            r"^(theorem|lemma|def|structure|class|instance|abbrev|inductive)\s+",
            line,
        ):
            current_container = None
            in_container = False
        if not in_container or current_container is None:
            continue
        field = FIELD_RE.match(line)
        if not field:
            continue
        field_name = field.group(1)
        entry = {
            "kind": "field",
            "file": path.stem,
            "line": line_no,
            "parent": current_container,
        }
        index.setdefault(field_name, []).append(entry)
        index.setdefault(f"{current_container}.{field_name}", []).append(entry)


def should_index_file(path: Path, include_generated: bool = False) -> bool:
    if include_generated:
        return True
    if any(fnmatch.fnmatch(path.name, pattern)
           for pattern in DEFAULT_EXCLUDE_GLOBS):
        return False
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:600]
    except OSError:
        return False
    return "Generated by src/ztare/formal/lean_compiler.py" not in head


def _source_fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_index(lean_dir: Path, include_generated: bool = False) -> dict:
    index: dict[str, list[dict]] = {}
    paths = [
        path for path in sorted(lean_dir.glob("*.lean"))
        if should_index_file(path, include_generated=include_generated)
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in DECL_KIND_RE.finditer(text):
            kind = m.group(1)
            name = m.group(2)
            entry = {"kind": kind, "file": path.stem,
                     "line": text[:m.start()].count("\n") + 1}
            index.setdefault(name, []).append(entry)
        _index_field_decls(text, path, index)
    return {
        "n_files": len(paths),
        "n_declarations": len(index),
        "source_fingerprint": _source_fingerprint(paths),
        "excluded_globs": [] if include_generated else list(DEFAULT_EXCLUDE_GLOBS),
        "decls": index,
    }


def check_nomination(nomination_text: str, index: dict) -> dict:
    """Resolve every identifier in nomination against the index.

    Returns: {valid: bool, unresolved: [...], known: [...]}.
    Numeric literals, keywords, common stdlib names are ignored.
    """
    decls = index.get("decls", {})
    surface = identifier_check_surface(nomination_text)
    declared_names = declared_names_in_snippet(surface)
    binder_names = binder_names_in_snippet(surface)
    local_names = declared_names | binder_names
    unresolved = []
    known = []
    shadowed_globals = []

    def has_nonfield_decl(name: str) -> bool:
        return any(entry.get("kind") != "field" for entry in decls.get(name, []))

    def has_field_decl(name: str) -> bool:
        return any(entry.get("kind") == "field" for entry in decls.get(name, []))

    for tok in IDENT_RE.findall(surface):
        head = tok.split(".")[0]
        tail = tok.split(".")[-1]
        if "." in tok and head in local_names:
            if has_field_decl(tail) or has_nonfield_decl(tok):
                known.append(tok)
            else:
                unresolved.append(tok)
            continue
        if tok in local_names:
            known.append(tok)
            continue
        if tok in GLOBAL_OK or head in GLOBAL_OK:
            continue
        if tok[0].isdigit() or re.fullmatch(r"\d+", tok):
            continue
        # Single-letter local binders are usually fine
        if len(tok) <= 2:
            continue
        # Qualified field access requires the head object to be local/global.
        if (
            "." in tok
            and has_field_decl(tail)
            and not has_nonfield_decl(tok)
            and not has_nonfield_decl(head)
        ):
            unresolved.append(tok)
            continue
        # Strip qualified prefix; check both full and tail.
        if has_nonfield_decl(tok) or has_nonfield_decl(head) or has_nonfield_decl(tail):
            known.append(tok)
        else:
            unresolved.append(tok)
    for name in binder_names:
        if name not in declared_names and has_nonfield_decl(name):
            shadowed_globals.append(name)
    return {"valid": not unresolved and not shadowed_globals,
            "unresolved": list(set(unresolved)),
            "shadowed_globals": sorted(set(shadowed_globals)),
            "known_count": len(set(known)),
            "n_unique_unresolved": len(set(unresolved)),
            "n_shadowed_globals": len(set(shadowed_globals))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true",
                    help="(re)build the index from ztare_proofs/ZtareProofs/")
    ap.add_argument("--include-generated", action="store_true",
                    help="include *_iter/smoke/closed_loop Lean scratch files")
    ap.add_argument("--check", type=str,
                    help="check a Lean snippet against the index")
    ap.add_argument("--out", type=Path, default=INDEX_PATH)
    args = ap.parse_args()

    if args.build or not args.out.exists():
        print(f"building index from {LEAN_DIR}...")
        index = build_index(LEAN_DIR, include_generated=args.include_generated)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(index, indent=2))
        print(f"  scanned {index['n_files']} files; "
              f"{index['n_declarations']} unique declarations")
        print(f"  wrote {args.out}")
    else:
        index = json.loads(args.out.read_text())
        print(f"loaded {index['n_declarations']} declarations from {args.out}")

    if args.check:
        result = check_nomination(args.check, index)
        print(f"\n=== nomination check ===")
        print(f"  valid: {result['valid']}")
        print(f"  unresolved: {result['unresolved']}")
        print(f"  known: {result['known_count']} unique identifiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
