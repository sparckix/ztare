"""DENOTATION-FAITHFULNESS — the boundary check for a BUILT definition (theory-first #123).

THE OPEN PROBLEM. The firewall (`autoformalize.faithfulness_gate`) certifies that a STATEMENT round-trips
to the NL. `detect_def_shells` / `default_def_faithfulness` catch a constant-shell or an LLM-obvious
wrong-object def. None of them answer the genuinely-hard question: when the agent INTRODUCES a new symbol
(a Lean `def` Mathlib lacks — `simpleResidueCoeff`, `IsRationalAntiderivative`), does that symbol actually
DENOTE the intended concept C, or merely some self-consistent decoy C' that satisfies every internal
sanity lemma AND composes with the shelf yet means something subtly different? A(S) (the stated API) under-
determines S. Proving denotation absolutely is NOT possible from inside the system — so we do NOT pretend to.

THE DESIGN (research_isomorphism, 2026-06-19 — deanchored from ITP):
  • Kalman observability rank — a hidden state is uniquely recoverable iff its constraint set is FULL-RANK
    over external outputs. Rank-deficient ⇒ a decoy fits ⇒ the denotation is UNDER-DETERMINED, not certified.
  • Mayers-Yao self-testing / Mostow-Birkhoff rigidity — one EXTREMAL external constraint pins the referent
    up to isomorphism where internal statistics alone cannot.
  • Universal Composability / Revelation Principle — composition with a TRUSTED environment forces the
    declared symbol to equal the true referent.

So we MEASURE pinning instead of asserting denotation, and return a 3-valued verdict that never launders
under-determination as certification:
  • REFUTED       — a declared agreement with a trusted reference is kernel-FALSE (a decoy is caught red-handed).
  • PINNED        — every built def carries ≥1 kernel-VERIFIED external anchor (overlap-agreement with a
                    trusted Mathlib concept, or composition with the proven shelf) → a decoy is ruled out.
  • UNDERDETERMINED — a built def has only self-consistency (no verified external anchor) → an OPEN GAP,
                    surfaced, NOT certified. This is the frontier, reported truthfully.
  • NOT_APPLICABLE — the formalization introduced no new defs (it used Mathlib objects only).

THE ANCHOR CONVENTION (agency upstream / determinism at the boundary — Goldilocks). The AGENT chooses a
trusted reference and states the agreement as an `anchor_…` theorem. A deterministic shape check first requires
a typed external reference and a one-sided definitional/extensional/special-case relation (or a typed model
instance). This rejects reflexive and internal-only theorems before kernel work. The KERNEL then decides whether
the surviving agreement holds (`verify_anchor_fn` = compile sorry-free + axiom-clean). The harness only
classifies and verifies anchors; it never writes them.

Pure + injectable: `certify_def_denotation` takes the theory source + injected verify/refute fns (mocks in
tests). `kernel_denotation_verifier` wires the real boundary through `_compile_probe` + `audit_axioms_subset`
(the SAME primitives `composite_ratify` uses — zero new soundness surface).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

from ztare.leanmill import lean_source as _ls

# the name a built def must agree-with-a-trusted-reference theorem carries; the agent writes these.
ANCHOR_PREFIX = "anchor_"

ANCHOR_KINDS = frozenset({"definitional", "extensional", "special_case", "model_instance"})

# Optional, source-bound metadata for anchors whose type cannot be classified safely from syntax alone:
#   -- @denotation-anchor: anchor=anchor_Foo_nat; target=Foo; kind=model_instance; external=Nat
# The theorem type remains authoritative: the marker's target and external reference must both occur there.
_ANCHOR_METADATA = re.compile(r"--\s*@denotation-anchor:\s*([^\n]+)")
_LEAN_IDENT = re.compile(r"(?<![\w'.])([A-Za-z_][\w'.]*)(?![\w'.])")
_EXTERNAL_OPERATOR_REFS = (
    ("∈", "Membership.mem"), ("⊆", "Set.Subset"), ("≤", "LE.le"), ("≥", "LE.le"),
    ("<", "LT.lt"), (">", "LT.lt"), ("+", "HAdd.hAdd"), ("-", "Sub.sub"),
    ("*", "HMul.hMul"), ("/", "HDiv.hDiv"), ("∅", "EmptyCollection.emptyCollection"),
)
_IDENTIFIER_NOISE = frozenset({
    "Prop", "Type", "Sort", "True", "False", "theorem", "lemma", "def", "abbrev",
    "by", "fun", "let", "in", "if", "then", "else", "match", "with", "where",
    "forall", "exists", "And", "Or", "Not", "Eq", "Iff",
})

PINNED = "PINNED"
UNDERDETERMINED = "UNDERDETERMINED"
REFUTED = "REFUTED"
NOT_APPLICABLE = "NOT_APPLICABLE"


def _metadata_fields(text: str) -> "dict[str, str]":
    """Parse a semicolon-delimited marker payload without assigning it authority."""
    out: "dict[str, str]" = {}
    for piece in (text or "").split(";"):
        key, sep, value = piece.strip().partition("=")
        if sep and key.strip() and value.strip():
            out[key.strip()] = value.strip()
    return out


def _anchor_metadata(theory_src: str, anchor_name: str) -> "dict[str, str]":
    """Return the unique metadata row explicitly bound to ``anchor_name``; ambiguity fails closed."""
    matches = []
    for raw in _ANCHOR_METADATA.findall(theory_src or ""):
        fields = _metadata_fields(raw)
        if fields.get("anchor") == anchor_name:
            matches.append(fields)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return {"anchor": anchor_name, "_invalid_reason": "duplicate metadata rows"}
    return {}


def _signature_conclusion(signature: str) -> str:
    """The conclusion after the theorem telescope, using the canonical bracket-aware colon parser."""
    ci = _ls.top_level_colon(signature or "")
    return (signature[ci + 1:] if ci >= 0 else signature or "").strip()


def _strip_outer_parens(text: str) -> str:
    s = (text or "").strip()
    while len(s) >= 2 and s[0] == "(" and s[-1] == ")":
        depth = 0
        closes_at_end = True
        for i, c in enumerate(s):
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0 and i != len(s) - 1:
                    closes_at_end = False
                    break
        if not closes_at_end or depth != 0:
            break
        s = s[1:-1].strip()
    return s


def _top_level_relation(conclusion: str) -> "tuple[str, str, str] | None":
    """Split the first top-level equality/iff/order relation in a Lean proposition."""
    s = _strip_outer_parens(conclusion)
    depth = 0
    opens, closes = "([{⟨⦃", ")]}⟩⦄"
    for i, c in enumerate(s):
        if c in opens:
            depth += 1
            continue
        if c in closes:
            depth = max(0, depth - 1)
            continue
        if depth:
            continue
        for op in ("↔", "≠", "≤", "≥", "=", "<", ">"):
            if s.startswith(op, i) and not (op == "=" and i > 0 and s[i - 1] == ":"):
                return s[:i].strip(), op, s[i + len(op):].strip()
    return None


def _binder_names(signature: str) -> "set[str]":
    """Conservative telescope-name extraction used only to avoid treating variables as references."""
    out: "set[str]" = set()
    ci = _ls.top_level_colon(signature or "")
    telescope = signature[:ci] if ci >= 0 else ""
    for group in re.findall(r"[({\[⦃]([^(){}\[\]⦃⦄]+)[)}\]⦄]", telescope):
        head = group.split(":", 1)[0]
        out.update(re.findall(r"\b[A-Za-z_][\w']*\b", head))
    for names in re.findall(r"(?:∀|forall)\s+([^,]+),", signature or ""):
        head = names.split(":", 1)[0]
        out.update(re.findall(r"\b[A-Za-z_][\w']*\b", head))
    return out


def _external_refs(expression: str, signature: str, local_decls: "set[str]") -> "list[str]":
    """Conservative references to library structure on the non-candidate side of an anchor relation."""
    bound = _binder_names(signature)
    refs: "set[str]" = set()
    for token in _LEAN_IDENT.findall(expression or ""):
        short = token.rsplit(".", 1)[-1]
        if token in _IDENTIFIER_NOISE or short in bound or short in local_decls:
            continue
        # Legacy inference accepts only inspectable library-like names. A bare lower-case identifier is
        # indistinguishable from a local variable/function and needs explicit metadata.
        if "." in token or token[:1].isupper():
            refs.add(token)
    for symbol, reference in _EXTERNAL_OPERATOR_REFS:
        if symbol in (expression or ""):
            refs.add(reference)
    return sorted(refs)


def _external_is_mentioned(signature: str, external: str) -> bool:
    return mentions_token(signature, external) or any(
        ref == external and symbol in (signature or "") for symbol, ref in _EXTERNAL_OPERATOR_REFS
    )


def _anchor_shape(theory_src: str, anchor_name: str, local_defs: "set[str]",
                  local_decls: "set[str]") -> dict:
    """Classify an anchor theorem before kernel verification; malformed and self-referential rows fail closed."""
    signature = _ls.extract_signature(theory_src, anchor_name) or ""
    conclusion = _signature_conclusion(signature)
    targets = sorted(d for d in local_defs if mentions_token(conclusion, d))
    meta = _anchor_metadata(theory_src, anchor_name)
    relation = _top_level_relation(conclusion)

    def invalid(reason: str, **extra) -> dict:
        return {"valid": False, "reason": reason, "signature": signature, **extra}

    if not signature or not conclusion:
        return invalid("missing theorem signature")
    if not targets:
        return invalid("anchor conclusion does not mention a local definition")
    if conclusion.strip() in {"True", "False"}:
        return invalid("trivial proposition is not a denotation anchor", targets=targets)

    if meta:
        if meta.get("_invalid_reason"):
            return invalid(meta["_invalid_reason"], targets=targets)
        kind = meta.get("kind", "")
        target = meta.get("target", "")
        external = meta.get("external", "")
        if kind not in ANCHOR_KINDS:
            return invalid("metadata kind is missing or unsupported", targets=targets)
        if target not in local_defs or target not in targets:
            return invalid("metadata target is not the referenced local definition", kind=kind, targets=targets)
        if targets != [target]:
            return invalid("typed anchor may depend on only its declared local definition", kind=kind,
                           target=target, targets=targets)
        if not external or external == target or external.rsplit(".", 1)[-1] in local_decls:
            return invalid("metadata external must be distinct from every local declaration", kind=kind,
                           target=target, targets=targets)
        if kind != "model_instance" and relation is None:
            return invalid(f"{kind} anchor requires an inspectable relation", kind=kind, target=target,
                           external=external, targets=targets)
        if relation is not None:
            lhs, operator, rhs = relation
            if mentions_token(lhs, target) == mentions_token(rhs, target):
                return invalid("target must occur on exactly one side of the anchor relation", kind=kind,
                               target=target, external=external, targets=targets)
            if " ".join(lhs.split()) == " ".join(rhs.split()):
                return invalid("reflexive relation is not a denotation anchor", kind=kind, target=target,
                               external=external, targets=targets)
            external_side = rhs if mentions_token(lhs, target) else lhs
            if not _external_is_mentioned(external_side, external):
                return invalid("metadata external is absent from the non-candidate side of the relation",
                               kind=kind, target=target, external=external, targets=targets)
        elif not _external_is_mentioned(conclusion, external):
            return invalid("metadata external is absent from the theorem conclusion", kind=kind,
                           target=target, external=external, targets=targets)
        return {"valid": True, "reason": "typed anchor shape accepted", "signature": signature,
                "kind": kind, "target": target, "external": external, "targets": [target],
                "metadata": True}

    # Backward-compatible path: only an unambiguous relation between one local definition and an
    # independently identifiable library expression is accepted. Ambiguous legacy anchors need metadata.
    if len(targets) != 1:
        return invalid("legacy anchor must reference exactly one local definition", targets=targets)
    if relation is None:
        return invalid("legacy anchor has no inspectable relation; add @denotation-anchor metadata",
                       targets=targets)
    lhs, operator, rhs = relation
    target = targets[0]
    lhs_has, rhs_has = mentions_token(lhs, target), mentions_token(rhs, target)
    if lhs_has == rhs_has:
        return invalid("target must occur on exactly one side of the anchor relation", target=target,
                       targets=targets)
    if " ".join(lhs.split()) == " ".join(rhs.split()):
        return invalid("reflexive relation is not a denotation anchor", target=target, targets=targets)
    external_side = rhs if lhs_has else lhs
    refs = _external_refs(external_side, signature, local_decls)
    if not refs:
        return invalid("no external reference distinct from the candidate; add typed metadata", target=target,
                       targets=targets)
    kind = "extensional" if operator == "↔" else "definitional"
    return {"valid": True, "reason": "unambiguous legacy anchor shape accepted", "signature": signature,
            "kind": kind, "target": target, "external": refs[0], "external_candidates": refs,
            "targets": [target], "metadata": False}


def mentions_token(text: str, name: str) -> bool:
    """True iff `name` occurs as a whole Lean identifier (not a substring of a longer ident) in `text` —
    so `… rationalDeriv …` matches `rationalDeriv` but not `rationalDerivQuotient`. The single canonical
    whole-token test reused by the anchor↔def mapping AND the composition-anchor scan (no re-rolled regex)."""
    return re.search(r"(?<![\w'.])" + re.escape(name) + r"(?![\w'.])", text or "") is not None


def certify_def_denotation(theory_src: str, *,
                           verify_anchor_fn: "Callable[[str], bool]",
                           composed_defs: "Optional[set]" = None,
                           refute_anchor_fn: "Optional[Callable[[str], bool]]" = None) -> dict:
    """Score how well the BUILT defs in `theory_src` are pinned to their intended denotation by external,
    kernel-verifiable anchors. Returns the 3-valued verdict + per-def accounting. NO Lean is run here — the
    kernel work is the injected `verify_anchor_fn(anchor_name)->bool` (proven sorry-free + axiom-clean) and
    optional `refute_anchor_fn(anchor_name)->bool` (the deep leg: kernel-proves the agreement is FALSE).
    The name prefix carries no credit: `_anchor_shape` must first establish an inspectable relation and an
    external reference distinct from every local declaration.
    `composed_defs` = defs that appear in a kernel-RATIFIED composite with the proven shelf — composition is
    itself an external anchor (the UC principle), so those defs are pinned without a separate overlap lemma."""
    defs = _ls.def_names(theory_src)
    composed = set(composed_defs or ())
    if not defs:
        return {"schema": "leanmill.def_denotation_receipt.v2", "verdict": NOT_APPLICABLE,
                "defs": [], "per_def": {}, "anchors": [],
                "reason": "no new definitions introduced — denotation-faithfulness N/A (Mathlib objects only)"}

    # Classify every anchor once before paying for kernel calls. Kernel truth alone cannot turn a tautology or
    # an internal-only relation into an external denotation constraint.
    anchor_names = [t for t in _ls.theorem_names(theory_src) if t.startswith(ANCHOR_PREFIX)]
    local_defs = set(defs)
    local_decls = {name for name, _block in _ls.decl_blocks(theory_src) if name}
    anchor_shape = {a: _anchor_shape(theory_src, a, local_defs, local_decls) for a in anchor_names}
    anchor_state: "dict[str, str]" = {}
    for a in anchor_names:
        if not anchor_shape[a]["valid"]:
            anchor_state[a] = "invalid_shape"
            continue
        try:
            if refute_anchor_fn is not None and refute_anchor_fn(a):
                anchor_state[a] = REFUTED
                continue
            anchor_state[a] = "verified" if verify_anchor_fn(a) else "pending"
        except Exception:  # noqa: BLE001 — a tooling failure is PENDING (never silently a pass)
            anchor_state[a] = "pending"

    per_def: "dict[str, dict]" = {}
    for d in defs:
        v, p, r, invalid = [], [], [], []
        for a in anchor_names:
            if anchor_shape[a].get("target") != d:
                continue
            st = anchor_state[a]
            (v if st == "verified" else r if st == REFUTED else invalid if st == "invalid_shape" else p).append(a)
        composition = d in composed
        if r:
            status = REFUTED
        elif v or composition:
            status = PINNED
        else:
            status = UNDERDETERMINED
        per_def[d] = {"status": status, "verified_anchors": v, "pending_anchors": p,
                      "invalid_anchors": invalid, "refuted_anchors": r, "composition_anchor": composition}

    if any(x["status"] == REFUTED for x in per_def.values()):
        verdict = REFUTED
    elif any(x["status"] == UNDERDETERMINED for x in per_def.values()):
        verdict = UNDERDETERMINED
    else:
        verdict = PINNED
    under = [d for d, x in per_def.items() if x["status"] == UNDERDETERMINED]
    refd = [d for d, x in per_def.items() if x["status"] == REFUTED]
    reason = {
        PINNED: f"all {len(defs)} built def(s) pinned by a verified external anchor",
        UNDERDETERMINED: f"under-determined def(s) (no verified external anchor; open gap): {under}",
        REFUTED: f"decoy def(s) caught — declared agreement is kernel-FALSE: {refd}",
    }[verdict]
    return {"schema": "leanmill.def_denotation_receipt.v2", "verdict": verdict, "defs": defs,
            "per_def": per_def,
            "anchors": [{"name": a, "state": anchor_state[a], **anchor_shape[a]} for a in anchor_names],
            "reason": reason}


WITNESS_PREFIX = "witness_"
WITNESSED = "WITNESSED"
VACUITY_SCOPED = "VACUITY_SCOPED"
VACUITY_EXPOSED = "VACUITY_EXPOSED"


def _nonempty_subjects(conclusion: str) -> "set[str]":
    """Simple set/carrier expressions explicitly certified nonempty in a theorem conclusion."""
    s = conclusion or ""
    out = set(re.findall(r"\b([A-Za-z_][\w']*)\.Nonempty\b", s))
    out.update(re.findall(r"\bSet\.Nonempty\s+([A-Za-z_][\w']*)\b", s))
    out.update(re.findall(r"\b([A-Za-z_][\w']*)\s*≠\s*∅", s))
    out.update(re.findall(r"∅\s*≠\s*([A-Za-z_][\w']*)\b", s))
    # `∃ x, x ∈ s` is the primitive expansion of `s.Nonempty`.
    out.update(re.findall(r"(?:∃|Exists)\b[^,]*,\s*[A-Za-z_][\w']*\s*∈\s*([A-Za-z_][\w']*)\b", s))
    return out


def _target_argument_names(conclusion: str, target: str) -> "set[str]":
    """Identifiers in the target application up to the next proposition connective."""
    m = re.search(r"(?<![\w'.])" + re.escape(target) + r"(?![\w'.])", conclusion or "")
    if not m:
        return set()
    tail = (conclusion or "")[m.end():]
    tail = re.split(r"\s(?:∧|∨|→|↔)\s|[,;\n]", tail, maxsplit=1)[0]
    return {t for t in _LEAN_IDENT.findall(tail) if t not in _IDENTIFIER_NOISE}


def _membership_carriers(theory_src: str, target: str) -> "set[str]":
    """Simple named set parameters whose emptiness can vacate the target definition."""
    body = _ls.def_body(theory_src, target) or ""
    return set(re.findall(r"∈\s*([A-Za-z_][\w']*)\b", _ls.strip_comments(body)))


def _witness_shape(theory_src: str, witness_name: str, prone_defs: "set[str]") -> dict:
    """Validate that a witness conclusion ties a vacuity-prone predicate to an inhabited argument."""
    signature = _ls.extract_signature(theory_src, witness_name) or ""
    conclusion = _signature_conclusion(signature)
    targets = sorted(d for d in prone_defs if mentions_token(conclusion, d))
    subjects = _nonempty_subjects(conclusion)
    bound_by_target = {d: subjects.intersection(_target_argument_names(conclusion, d)) for d in targets}
    required_by_target = {d: max(1, len(_membership_carriers(theory_src, d))) for d in targets}
    bound_targets = sorted(d for d in targets if len(bound_by_target[d]) >= required_by_target[d])
    if not signature or not conclusion:
        return {"valid": False, "reason": "missing theorem signature", "signature": signature, "targets": []}
    if conclusion.strip() in {"True", "False"}:
        return {"valid": False, "reason": "trivial proposition is not a nonvacuity witness",
                "signature": signature, "targets": targets}
    if not targets:
        return {"valid": False, "reason": "witness conclusion does not mention a vacuity-prone definition",
                "signature": signature, "targets": []}
    if not subjects:
        return {"valid": False, "reason": "witness conclusion has no explicit inhabited/nonempty set",
                "signature": signature, "targets": targets}
    if not bound_targets:
        return {"valid": False,
                "reason": "nonempty subjects do not cover the membership arguments of the referenced definition",
                "signature": signature, "targets": targets, "nonempty_subjects": sorted(subjects),
                "required_nonempty_counts": required_by_target}
    return {"valid": True, "reason": "nonempty subject is bound to the target definition",
            "signature": signature, "targets": bound_targets, "nonempty_subjects": sorted(subjects),
            "required_nonempty_counts": required_by_target, "kind": "nonempty_argument"}


def vacuity_prone_defs(theory_src: str) -> "list[str]":
    """Built `Prop` defs that universally quantify over SET MEMBERSHIP with no non-emptiness guard — i.e. a
    property that is VACUOUSLY TRUE on the empty set (`StrongSetLE`, `IsSublatticeSet`, an argmax predicate …).
    Grounded in the def BODY via the canonical `lean_source` parser (NOT a surface match on the theorem), so it
    sees vacuity that hides behind a def. A def guarded by an explicit `Nonempty`/`∃`/`≠ ∅` is not flagged."""
    prone: "list[str]" = []
    for d in _ls.def_names(theory_src):
        body = _ls.def_body(theory_src, d) or ""        # def-aware (canonical; `_decl_body` is theorem-only)
        val = _ls.split_at_proof(body)[1]               # binder-safe split at the def's `:=`
        val = val[2:] if val.startswith(":=") else val
        # the ∀-over-membership classification lives in lean_source (canonical parser), not a hand-rolled
        # regex here — `prop_quantifies_over_membership` is comment-stripped + Nonempty-guard aware.
        if _ls.prop_quantifies_over_membership(val):
            prone.append(d)
    return prone


def certify_nonvacuity(theory_src: str, *, verify_fn: "Callable[[str], bool]") -> dict:
    """The VACUITY sibling of `certify_def_denotation` — same anti-self-deception stance, one axis over. A
    `Prop` def that ∀-quantifies over set membership is vacuously true on `∅`, so a theorem concluding that
    property of a CONSTRUCTED set (an argmax, a fixed-point set) can be kernel-true while asserting NOTHING when
    the set is empty (Gemini's 2026-06-23 critique: the parametric argmax can be `∅`, making `StrongSetMonotone`
    vacuous). The agent PINS each vacuity-prone def with a kernel-checked `witness_<def>_…` theorem (a relevant
    non-emptiness / non-vacuous instance — possibly under the existence conditions the result needs, e.g.
    completeness + order-continuity) OR honestly flags `-- @vacuity-scope: <def>: …`. 3-valued + ADVISORY (never
    gates a closure); the kernel work is the SAME injected `verify_fn` the denotation leg uses (no new surface).
    A witness name alone carries no credit: its conclusion must explicitly make a target argument nonempty.
    A wrong/empty witness audits as unproven ⇒ stays VACUITY_EXPOSED, never laundered to WITNESSED."""
    prone = vacuity_prone_defs(theory_src)
    if not prone:
        return {"schema": "leanmill.nonvacuity_receipt.v2", "verdict": NOT_APPLICABLE,
                "prone_defs": [], "per_def": {}, "witnesses": [],
                "reason": "no vacuously-on-empty set-property defs — vacuity-faithfulness N/A"}
    witness_names = [t for t in _ls.theorem_names(theory_src) if t.startswith(WITNESS_PREFIX)]
    witness_shape = {w: _witness_shape(theory_src, w, set(prone)) for w in witness_names}
    witness_state: "dict[str, str]" = {}
    for w in witness_names:
        if not witness_shape[w]["valid"]:
            witness_state[w] = "invalid_shape"
            continue
        try:
            witness_state[w] = "verified" if verify_fn(w) else "pending"
        except Exception:  # noqa: BLE001 — a tooling failure is PENDING (never silently a pass)
            witness_state[w] = "pending"
    scoped = set(re.findall(r"--\s*@vacuity-scope:\s*([\w'.]+)", theory_src or ""))
    per_def: "dict[str, dict]" = {}
    for d in prone:
        v = [w for w in witness_names if witness_state[w] == "verified" and d in witness_shape[w]["targets"]]
        invalid = [w for w in witness_names
                   if witness_state[w] == "invalid_shape" and d in witness_shape[w].get("targets", [])]
        status = WITNESSED if v else (VACUITY_SCOPED if d in scoped else VACUITY_EXPOSED)
        per_def[d] = {"status": status, "verified_witnesses": v, "invalid_witnesses": invalid,
                      "scoped": d in scoped}
    exposed = [d for d, x in per_def.items() if x["status"] == VACUITY_EXPOSED]
    if exposed:
        verdict = VACUITY_EXPOSED
    elif all(x["status"] == WITNESSED for x in per_def.values()):
        verdict = WITNESSED
    else:
        verdict = VACUITY_SCOPED
    reason = {
        WITNESSED: f"all {len(prone)} vacuity-prone def(s) carry a kernel-verified non-emptiness witness",
        VACUITY_SCOPED: ("vacuity-prone def(s) honestly scope-flagged (disclosed, no witness): "
                         + str([d for d, x in per_def.items() if x["status"] == VACUITY_SCOPED])),
        VACUITY_EXPOSED: ("vacuity-prone def(s) with NO non-emptiness witness and NO scope flag — true-but-"
                          f"possibly-vacuous (open gap, never a false certification): {exposed}"),
    }[verdict]
    return {"schema": "leanmill.nonvacuity_receipt.v2", "verdict": verdict, "prone_defs": prone,
            "per_def": per_def,
            "witnesses": [{"name": w, "state": witness_state[w], **witness_shape[w]} for w in witness_names],
            "reason": reason}


def kernel_denotation_verifier(theory_src: str, lean_root: "Path | str", *, timeout_s: int = 180):
    """Wire the real boundary: returns `verify_anchor_fn(anchor_name)->bool` that compiles the theory file
    ONCE (cached) and per-anchor audits axioms — VERIFIED iff the file typechecks AND the anchor's proof is
    sorry-free (no `sorryAx`) and banned-axiom-free. Reuses `_compile_probe` + `audit_axioms_subset` (the
    composite_ratify primitives) so there is no new kernel surface. A sorried/unfinished anchor audits as
    `sorryAx` ⇒ NOT verified ⇒ its def stays UNDERDETERMINED (an open gap), never laundered to PINNED."""
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    from ztare.gates.lean_compile_primitives import audit_axioms_subset
    lean_root = Path(lean_root)
    src = theory_src if theory_src.lstrip().startswith("import") else ("import Mathlib\n\n" + theory_src)

    # ELABORATE-ONCE, QUERY-PER-ANCHOR (2026-06-25 post-run-starvation fix): the cold path below
    # (`audit_axioms_subset`) RE-ELABORATES THE WHOLE THEORY for EVERY anchor — for a theory-first campaign
    # with N built defs that is N × a full re-elaboration (and when the warm whole-file elaboration times out on
    # a heavy theory it falls to cold `lake env lean`, ~74s each), so the post-close denotation audit ran ~1h.
    # Instead: load the theory into a warm env ONCE (`campaign_file_env`, cached by path+mtime) and `#print
    # axioms` each anchor AGAINST that cached env (`campaign_file_decl_axiom_clean`, ~0.1s/anchor). Pure speed —
    # same `#print axioms` verdict; falls back to the per-anchor `audit_axioms_subset` when the warm env is
    # unusable (flag off / toolchain / dead REPL), so correctness is unchanged.
    import tempfile as _tf, hashlib as _hl
    _warm_tmp = Path(_tf.gettempdir()) / f"_denotation_warm_{_hl.sha256(src.encode('utf-8')).hexdigest()[:12]}.lean"
    # namespace prefixes the theory declares (anchors may be referenced by short name; #print axioms needs the
    # full name) — token scan, not a Lean regex (canonical, matches family_lemma_library._open_namespaces).
    _nss: "list[str]" = []
    try:
        from ztare.leanmill.lean_source import strip_comments as _sc
        for _ln in _sc(src).splitlines():
            _pt = _ln.split()
            if len(_pt) >= 2 and _pt[0] == "namespace" and _pt[1] not in _nss:
                _nss.append(_pt[1])
    except Exception:  # noqa: BLE001
        _nss = []
    _state: dict = {}

    def _warm_env():
        if "env" not in _state:
            try:
                from ztare.formal.repl_compile import campaign_file_env
                _warm_tmp.write_text(src, encoding="utf-8")
                _state["env"] = campaign_file_env(str(_warm_tmp), str(lean_root), timeout=max(180, timeout_s))
            except Exception:  # noqa: BLE001
                _state["env"] = None
        return _state["env"]

    _compiled: "dict[str, bool]" = {}

    def _file_ok() -> bool:
        if _warm_env() is not None:           # an env id ⇒ the theory typechecked (sorries OK)
            return True
        if "ok" not in _compiled:
            try:
                _compiled["ok"] = _compile_probe(src, lean_root, "Denotation", max(120, timeout_s)) is True
            except Exception:  # noqa: BLE001
                _compiled["ok"] = False
        return _compiled["ok"]

    def _warm_anchor(anchor_name: str):
        """(clean: bool) | None — #print axioms the anchor against the cached env, trying bare then namespace-
        qualified; None ⇒ warm unusable / no verdict ⇒ caller falls back to the cold per-anchor audit."""
        if _warm_env() is None:
            return None
        try:
            from ztare.formal.repl_compile import campaign_file_decl_axiom_clean
        except Exception:  # noqa: BLE001
            return None
        for cand in [anchor_name, *[f"{ns}.{anchor_name}" for ns in _nss]]:
            res = campaign_file_decl_axiom_clean(str(_warm_tmp), str(lean_root), cand, timeout=max(60, timeout_s))
            if res is not None:
                return bool(res[0])
        return None

    def verify_anchor_fn(anchor_name: str) -> bool:
        if not _file_ok():
            return False
        warm = _warm_anchor(anchor_name)
        if warm is not None:
            return warm
        try:                                  # COLD FALLBACK (warm unusable) — unchanged sound path
            clean, bad, axs = audit_axioms_subset(
                src, anchor_name, lean_root / "_denotation_axiom_audit.lean", lean_root,
                timeout_s=max(120, timeout_s))
        except Exception:  # noqa: BLE001
            return False
        # VERIFIED iff axiom-clean AND not sorried (sorryAx ⇒ the agreement is asserted, not proven).
        return bool(clean and not bad and not any("sorry" in str(a).lower() for a in (axs or [])))

    return verify_anchor_fn


# ───────────────────────────── selftest (hermetic — injected verify/refute, no Lean) ─────────────────────────────
def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    theory = (
        "import Mathlib\n\n"
        "noncomputable def simpleResidueCoeff (f : RatFunc K) : K := 0\n\n"
        "def IsRationalAntiderivative (f g : RatFunc K) : Prop := True\n\n"
        "theorem anchor_simpleResidueCoeff_agrees_evalResidue :\n"
        "    ∀ f, simpleResidueCoeff f = Mathlib.residue f := by sorry\n\n"
        "theorem some_api_lemma : True := trivial\n")

    # (1) NOT_APPLICABLE when no defs.
    r0 = certify_def_denotation("import Mathlib\ntheorem t : True := trivial\n",
                                verify_anchor_fn=lambda a: True)
    ok("no-defs ⇒ NOT_APPLICABLE", r0["verdict"] == NOT_APPLICABLE)

    # (2) a built def with a VERIFIED overlap anchor + the other pinned by composition ⇒ PINNED.
    r1 = certify_def_denotation(
        theory, verify_anchor_fn=lambda a: a == "anchor_simpleResidueCoeff_agrees_evalResidue",
        composed_defs={"IsRationalAntiderivative"})
    ok("verified-anchor + composition ⇒ PINNED", r1["verdict"] == PINNED)
    ok("def pinned by composition recorded",
       r1["per_def"]["IsRationalAntiderivative"]["composition_anchor"] is True)
    ok("only the mentioned def gets the anchor (token match)",
       r1["per_def"]["simpleResidueCoeff"]["verified_anchors"] == ["anchor_simpleResidueCoeff_agrees_evalResidue"]
       and r1["per_def"]["IsRationalAntiderivative"]["verified_anchors"] == [])

    # (3) anchor PENDING (sorried / unproven) + no composition ⇒ UNDERDETERMINED (open gap, NOT certified).
    r2 = certify_def_denotation(theory, verify_anchor_fn=lambda a: False)
    ok("pending anchor + no composition ⇒ UNDERDETERMINED", r2["verdict"] == UNDERDETERMINED)
    ok("UNDERDETERMINED never launders to PINNED",
       r2["per_def"]["simpleResidueCoeff"]["status"] == UNDERDETERMINED)

    # (4) the deep leg: a kernel-FALSE agreement ⇒ REFUTED (decoy caught), dominating PINNED.
    r3 = certify_def_denotation(
        theory, verify_anchor_fn=lambda a: True,
        refute_anchor_fn=lambda a: a == "anchor_simpleResidueCoeff_agrees_evalResidue")
    ok("kernel-false agreement ⇒ REFUTED", r3["verdict"] == REFUTED)
    ok("refuted def flagged with the offending anchor",
       r3["per_def"]["simpleResidueCoeff"]["refuted_anchors"] == ["anchor_simpleResidueCoeff_agrees_evalResidue"])

    # (5) a tooling exception in verify is PENDING, never a silent pass.
    def _boom(a):
        raise RuntimeError("kernel down")
    r4 = certify_def_denotation(theory, verify_anchor_fn=_boom, composed_defs=set())
    ok("verify exception ⇒ UNDERDETERMINED (fail-closed)", r4["verdict"] == UNDERDETERMINED)

    # ── vacuity-faithfulness sibling (Gemini's empty-set critique, 2026-06-23) ──
    vac_theory = (
        "import Mathlib\n\n"
        "def StrongSetLE {X : Type*} [SemilatticeSup X] [SemilatticeInf X] (s u : Set X) : Prop :=\n"
        "  ∀ ⦃x y : X⦄, x ∈ s → y ∈ u → x ⊓ y ∈ s ∧ x ⊔ y ∈ u\n\n"
        "def NonemptyGuarded {X : Type*} (s : Set X) : Prop := s.Nonempty ∧ ∀ ⦃x⦄, x ∈ s → True\n\n")
    # StrongSetLE is vacuity-prone (∀-over-∈, no guard); NonemptyGuarded is NOT (has `.Nonempty`).
    ok("vacuity_prone detects ∀-over-membership def", "StrongSetLE" in vacuity_prone_defs(vac_theory))
    ok("vacuity_prone skips a Nonempty-guarded def", "NonemptyGuarded" not in vacuity_prone_defs(vac_theory))
    # no witness, no scope flag ⇒ VACUITY_EXPOSED (open gap, never laundered)
    rv0 = certify_nonvacuity(vac_theory, verify_fn=lambda w: True)
    ok("prone def, no witness ⇒ VACUITY_EXPOSED", rv0["verdict"] == VACUITY_EXPOSED)
    # a VERIFIED witness mentioning the def ⇒ WITNESSED
    vac_w = vac_theory + ("theorem witness_StrongSetLE_nonvacuous {X : Type*} [SemilatticeSup X] "
                          "[SemilatticeInf X] : ∃ s u : Set X, s.Nonempty ∧ u.Nonempty ∧ "
                          "StrongSetLE s u := by sorry\n")
    rv1 = certify_nonvacuity(vac_w, verify_fn=lambda w: w.startswith("witness_StrongSetLE"))
    ok("verified non-emptiness witness ⇒ WITNESSED", rv1["verdict"] == WITNESSED)
    # an UNVERIFIED (sorried) witness ⇒ still VACUITY_EXPOSED (no false certification)
    rv2 = certify_nonvacuity(vac_w, verify_fn=lambda w: False)
    ok("pending witness ⇒ VACUITY_EXPOSED (fail-closed)", rv2["verdict"] == VACUITY_EXPOSED)
    # an explicit @vacuity-scope flag (no witness) ⇒ VACUITY_SCOPED (disclosed, not exposed)
    rv3 = certify_nonvacuity(vac_theory + "-- @vacuity-scope: StrongSetLE: vacuous when either set is ∅\n",
                             verify_fn=lambda w: False)
    ok("scope-flagged prone def ⇒ VACUITY_SCOPED", rv3["verdict"] == VACUITY_SCOPED)
    ok("no prone defs ⇒ NOT_APPLICABLE",
       certify_nonvacuity("import Mathlib\ndef f : Nat := 0\n", verify_fn=lambda w: True)["verdict"] == NOT_APPLICABLE)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
