"""Statement/proof separation for Lean source files (substrate-generic kernel).

Pure transform — NO I/O, NO Lean toolchain, NO substrate (APN/NS/Clay) specifics.
Given a Lean source that bundles the proof-construction DAG (helper defs AND
lemmas) in the same file as the statement, extract a FAIR goal: the transitive
definitional closure of the target's statement vocabulary, with every
proof-introduced decl withheld so a solver must reconstruct the proof itself.

This is the kernel logic behind the `materialize_statement_goals.py` operator
script (which owns the CLI, slice I/O, and the Lean compile-validation
orchestration). Per the LeanMill kernel/script boundary
(docs/concepts/leanmill_architecture.md), durable substrate-generic logic lives
here; orchestration lives in scripts/public/control/.

Boundary rule (principled, not lexical): seed from the local decls named in the
target's TYPE signature (everything up to `:= by`), take the closure of decls
they reference transitively; decls NOT reachable from the statement are
proof-only and dropped. The target theorem is never pulled into its own closure.
"""
from __future__ import annotations
import re

# Top-level declaration headers we recognize. Captures (kind, name).
_DECL_RE = re.compile(
    r"(?m)^(?P<kind>(?:noncomputable\s+|private\s+|protected\s+|scoped\s+)*"
    r"(?:def|abbrev|theorem|lemma|structure|inductive|class|instance))\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_'\.]*)"
)
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'\.]*")
_PROOF_KINDS = {"theorem", "lemma"}


def _kind0(kind_str: str) -> str:
    return kind_str.split()[-1]


def parse_decls(src: str) -> list[dict]:
    """Split a Lean file into top-level decls: name, kind, span [start,end), text."""
    matches = list(_DECL_RE.finditer(src))
    decls = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(src)
        decls.append({
            "name": m.group("name"),
            "kind": _kind0(m.group("kind")),
            "start": start, "end": end,
            "text": src[start:end],
        })
    return decls


def local_refs(text: str, by_name: dict) -> set[str]:
    """Local decl names referenced in `text`, RESOLVING dotted access. A token like
    `mem_divisorsFinset_iff.2` (projection) or `Ns.foo` is matched against by_name by
    its longest dotted PREFIX — otherwise the base decl (`mem_divisorsFinset_iff`) is
    never linked and gets wrongly dropped, breaking the extracted context. This was a
    real closure-completeness bug (`_IDENT_RE` swallows the trailing `.field`)."""
    refs: set[str] = set()
    for tok in _IDENT_RE.findall(text):
        parts = tok.split(".")
        for i in range(len(parts), 0, -1):
            cand = ".".join(parts[:i])
            if cand in by_name:
                refs.add(cand)
                break
    return refs


def statement_closure(decls: list[dict], target_name: str, seeds: set[str]) -> set[str]:
    """Names transitively referenced by the statement's SEED names (the local
    decls appearing in the target's type signature), restricted to decls defined
    in this file. Resolves dotted access (see `local_refs`). Proof-only decls are
    those NOT in this closure. The target theorem itself is never pulled in."""
    by_name = {d["name"]: d for d in decls}
    seen: set[str] = set()
    stack = [s for s in seeds if s in by_name and s != target_name]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        d = by_name.get(n)
        if not d:
            continue
        for ref in local_refs(d["text"], by_name):
            if ref != n and ref != target_name and ref not in seen:
                stack.append(ref)
    return seen


def split_header(target_text: str) -> "tuple[str, str] | None":
    """Split a target decl into (statement header, proof body) at the proof
    intro `:= by`. Handles `theorem P1 : ProblemP1 := by`, `theorem P7 : ∀ r,
    ProblemP7 r := by`, and multi-line `theorem Conjecture2 <binders> := by`."""
    m = re.search(r":=\s*by\b", target_text)
    if not m:
        return None
    return target_text[:m.start()].rstrip(), target_text[m.start():]


def build_goal(src: str, target_name: str) -> "dict | None":
    """Extract a fair goal for `target_name` from Lean source `src`.

    Returns {seeds, n_kept, n_dropped, dropped_names, goal, original_proof} or
    None if the target/proof-intro can't be parsed. `goal` is the kept statement
    vocabulary (original file order) followed by the target as `<header> := by`.
    """
    decls = parse_decls(src)
    target = next((d for d in decls if d["name"] == target_name and d["kind"] in _PROOF_KINDS), None)
    if not target:
        return None
    split = split_header(target["text"])
    if not split:
        return None
    header, proof_body = split
    by_name = {d["name"]: d for d in decls}
    sig_after_name = header.split(target_name, 1)[1] if target_name in header else header
    seeds = local_refs(sig_after_name, by_name) - {target_name}
    closure = statement_closure(decls, target_name, seeds)
    kept = [d for d in decls if d["name"] in closure]
    dropped = [d for d in decls if d["name"] not in closure and d["name"] != target_name]
    context = "\n\n".join(d["text"].rstrip() for d in kept)
    goal_full = (f"{context}\n\n{header} := by" if context else f"{header} := by")
    return {
        "seeds": sorted(seeds),
        "n_kept": len(kept), "n_dropped": len(dropped),
        "dropped_names": [d["name"] for d in dropped],
        "goal": goal_full,
        "original_proof": proof_body,
    }


def truncate_to_target_header(src: str, target_name: str) -> "str | None":
    """The VERBATIM file up to and including the target theorem's `:= by` (imports
    stripped — the caller adds `import Mathlib`). This is the k=all ablation context
    done by TRUNCATION, not reconstruction: every set_option / open / namespace /
    variable / helper stays in its exact original position and order, so the only
    thing the prover must supply is the final proof body. Reconstruction-from-decls
    drops directives and errors spuriously (the wrong primitive); this is the right one.
    Returns None if the target / `:= by` can't be located."""
    decls = parse_decls(src)
    target = next((d for d in decls if d["name"] == target_name and d["kind"] in _PROOF_KINDS), None)
    if not target:
        return None
    m = re.search(r":=\s*by\b", target["text"])
    if not m:
        return None
    cut = target["start"] + m.end()          # absolute offset of end of `:= by` in src
    head = src[:cut]
    return "\n".join(ln for ln in head.splitlines() if not ln.lstrip().startswith("import "))


def build_ablation_layers(src: str, target_name: str) -> "dict | None":
    """Layers for a controlled premise-injection ablation: the statement context
    (always kept) + the WITHHELD proof-helper decls in FILE (dependency) order, so
    a caller can reconstruct the goal with the first k helpers added back and
    measure closure vs k. NOT a leak — a deliberate ablation that characterizes how
    far above the frontier a row is (needs 1 key lemma vs the whole proof DAG).

    Returns {header, kept_text, dropped_decls: [{name, text}, …] in file order} or
    None if unparseable. Helpers keep their original proof bodies (from the file).
    """
    decls = parse_decls(src)
    target = next((d for d in decls if d["name"] == target_name and d["kind"] in _PROOF_KINDS), None)
    if not target:
        return None
    split = split_header(target["text"])
    if not split:
        return None
    header, _proof = split
    by_name = {d["name"]: d for d in decls}
    sig_after_name = header.split(target_name, 1)[1] if target_name in header else header
    seeds = local_refs(sig_after_name, by_name) - {target_name}
    closure = statement_closure(decls, target_name, seeds)
    kept = [d for d in decls if d["name"] in closure]
    # dropped (proof-only) decls in ORIGINAL FILE ORDER → adding the first k keeps
    # the source's topological dependency order (helpers precede their users).
    dropped = [d for d in decls if d["name"] not in closure and d["name"] != target_name]
    # PREAMBLE: everything before the first decl (set_option / open / namespace /
    # variable / local notation). Helpers compiled against the WRONG environment
    # (e.g. without `set_option autoImplicit false` or `open Classical`) error
    # spuriously — preserve it. Strip `import` lines (the caller adds `import Mathlib`).
    first_start = decls[0]["start"] if decls else 0
    preamble = "\n".join(ln for ln in src[:first_start].splitlines()
                         if not ln.lstrip().startswith("import "))
    return {
        "preamble": preamble.strip(),
        "header": header,
        "kept_text": "\n\n".join(d["text"].rstrip() for d in kept),
        "dropped_decls": [{"name": d["name"], "text": d["text"].rstrip()} for d in dropped],
    }
