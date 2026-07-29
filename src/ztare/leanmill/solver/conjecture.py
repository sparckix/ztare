"""MOVE_CONJECTURE generation + kernel-checked advance test — the solver-core primitive for backward
(invent-a-lemma) decomposition. Extracted from the `solver_lane_worker.py` monolith into `src/` (task
#42, first slice) because it is general-purpose solver logic with NO worker-internal dependencies: it
needs only `agentic_leaf.default_dispatch` (the shared warm dispatch) and the v33 `_compile_probe`
(kernel typecheck, sorry-OK). The worker's move_runner imports these; the control script keeps only the
operational shim. SOUNDNESS NOTE: `conjecture_advances` NEVER closes the goal G — it only decides whether
to SPAWN the lemma L as a child (the search proves L and re-checks G-via-L under the kernel+MNC gate).

KNOWN v1 limitation (adversarial review 2026-06-05): a conjecture only genuinely DECOMPOSES once the
move generators prove `node.goal_text` (=L) for spawned sub_goal nodes instead of re-proving the row
target G — until that move_runner change lands, the spawned child re-proves G (the move is inert as
decomposition). The cite-check below is comment-stripped but is NOT yet a full load-bearing probe
(replace-L-with-False); both are tracked under #35."""
from __future__ import annotations

import os
import re
from pathlib import Path

# Canonical comment-stripping sorry/admit check (the ONE primitive — never substring-match raw Lean for a
# consequential decision; a `sorry` in a comment/identifier must not false-positive). 2026-06-13 audit.
from ztare.leanmill.lean_source import (has_sorry as _has_sorry, strip_comments as _strip_comments,
                                         signature_before_proof, top_level_colon as _top_level_colon)

# Prompts live in the canonical registry (prompts.py); local names preserved for the call sites.
from ztare.leanmill.solver.prompts import CONJECTURE_PROMPT as _CONJECTURE_PROMPT


def _goal_head_for_exemplar(goal_text: str) -> str:
    """The head (signature, no proof `:=`) of the GOAL theorem, for the `{goal_head}` PROOF exemplar.
    `goal_text` is the FULL theory blob (preamble defs + the goal theorem). `signature_before_proof`
    cuts at the FIRST depth-0 `:=`, which for a preamble carrying a helper `abbrev/def := …` is the
    HELPER's `:=`, not the goal's — so the exemplar would restate a stray def as the goal (observed:
    CLOB's `abbrev betterPrice := _root_.betterPrice` preceding the target). The goal theorem is always
    the LAST decl; take its head. Falls back to the whole-blob behaviour if unparsable."""
    from ztare.leanmill.lean_source import decl_blocks
    blocks = decl_blocks(goal_text or "")
    tail = blocks[-1][1] if blocks else (goal_text or "")
    return (signature_before_proof(tail).strip()
            or signature_before_proof(goal_text or "").strip() or (goal_text or ""))


def conjecture_generate(row: dict, goal_text: str, lean_root: Path,
                        timeout_s: int, prompt_override: "str | None" = None) -> "tuple[str, str, str, str]":
    """Ask the warm dispatch to INVENT one intermediate lemma L (named `lname`, so we can check the
    goal-proof actually cites it) and prove the ORIGINAL goal USING L. Returns
    (lemma_block, goal_proof_block, lname, raw_tail). Strict LEMMA:/PROOF: fenced parse with a
    two-theorem-block fallback. ('','',lname,err) on failure (⇒ no_advance, never a false closure).

    `prompt_override`: an alternate prompt (e.g. the obstruction-targeted prompt from
    `obstruction_to_conjecture`) — used by the targeted-vs-blind conjecture A/B. The unique `{lname}`
    token is substituted in (via str.replace, NOT .format — the prompt embeds raw Lean that may contain
    braces); `{goal}` / `{goal_head}` are substituted too if present. The LEMMA:/PROOF: fenced contract
    is unchanged, so both arms go through the IDENTICAL parse + `conjecture_advances` kernel gate."""
    base = re.sub(r"[^A-Za-z0-9_]", "", (row.get("target_theorem_name") or "lem"))[:28] or "lem"
    lname = f"conj_{base}"
    goal_head = _goal_head_for_exemplar(goal_text or "")
    if prompt_override:
        prompt = (prompt_override.replace("{lname}", lname)
                  .replace("{goal_head}", goal_head).replace("{goal}", goal_text or ""))
    else:
        prompt = _CONJECTURE_PROMPT.format(lname=lname, goal=goal_text, goal_head=goal_head)
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        raw = default_dispatch(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception as e:  # noqa: BLE001
        return "", "", lname, f"dispatch_error: {e!r}"

    from ztare.leanmill.solver.agent_output import fenced_block

    lemma, proof = fenced_block(raw,"LEMMA:"), fenced_block(raw,"PROOF:")
    if not (lemma and proof):                               # fallback: two theorem/lemma blocks
        thms = re.findall(r"(?s)((?:theorem|lemma)\s+\S+.*?:=\s*by\b.*?)(?=\n(?:theorem|lemma)\s|\Z)", raw)
        if len(thms) >= 2:
            sor = [t.strip() for t in thms if _has_sorry(t)]   # comment-robust: a `sorry` in a comment ≠ a sorried lemma
            lemma = (sor[0] if sor else thms[0].strip())
            proof = next((t.strip() for t in thms if t.strip() != lemma), thms[-1].strip())
    return lemma, proof, lname, (raw or "")[-200:]


# `_top_level_colon` is the canonical `lean_source.top_level_colon` (re-exported above). It used to be a
# byte-identical copy here AND in statement_integrity — the forgotten-sibling shape, now de-duplicated
# (2026-06-22). External callers (`abduction`, `reflection`, `proof_margin_of_safety`, `solver_core`) import it
# from here unchanged.


def _lemma_conclusion(block: str) -> str:
    """The conclusion/type of a decl (after the top-level `:`, before `:=`) — bracket-aware. '' if none."""
    from ztare.leanmill.solver.statement_integrity import _signature
    sig = _signature(block.strip())
    j = _top_level_colon(sig)
    return sig[j + 1:].strip() if j >= 0 else ""


def _useless_lemma(lemma: str) -> str:
    """L with its TYPE replaced by `True` (binders preserved) → the useless-lemma for the load-bearing
    probe. Bracket-depth-aware top-level `:` split (the old regex split on the FIRST `:`, i.e. a binder
    colon like `(n : ℕ)`, producing malformed Lean → the probe miscompiled → every binder-carrying lemma
    was auto-credited load-bearing; adversarial review 2026-06-05). '' if the signature can't be split."""
    from ztare.leanmill.solver.statement_integrity import _signature
    sig = _signature(lemma.strip())
    j = _top_level_colon(sig)
    if j < 0:
        return ""
    return sig[:j].rstrip() + " : True := by sorry"


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _campaign_probe(preamble: str, body: str) -> str:
    """THE one door for building an audit compile-snippet (2026-07-02 synthInstance RCA). When a single-namespace
    campaign substrate is registered, compile `body` against the REAL substrate — re-entering its namespace AND
    re-declaring its section `variable` context (the SAME restoration warm_verify_campaign uses, sourced from the
    ONE helper lean_source.section_variable_lines) — so a section-style theory's type/instance binders resolve.
    Without this, every audit here (decompose / conjecture-advance / specialize / falsify) compiled the flat
    deanchored `preamble`, which loses those section binders ⇒ `synthInstanceFailed` ⇒ a VALID move REJECTED ⇒
    the expensive agentic fallback (the median-voter token burn). Non-campaign / multi-namespace / flat theory ⇒
    the flat preamble (byte-parity — every prior campaign shape is unchanged). The target is posed EXTERNALLY
    (not in the substrate) so re-inlining the substrate never clashes with the probe's own decls."""
    try:
        # THE ONE cold-probe door (2026-07-06): substrate + scope + the PREAMBLE's OWN warm-only defs (an inline
        # `inductive ProposalRun` the substrate never banked) + the body. Dropping the preamble here used to make a
        # body citing `ProposalRun` fail `unknown identifier` cold ⇒ a FALSE `no_advance` (the gale thrash);
        # native_hammer shares this exact door now, so they can never drift again. None off-campaign ⇒ flat fallback.
        from ztare.formal.repl_compile import assemble_cold_probe
        _probe = assemble_cold_probe(preamble, body=body, keep="")
        if _probe is not None:
            return _probe
    except Exception:  # noqa: BLE001 — never let the campaign path break an audit; fall through to flat
        pass
    pre = (preamble.strip() + "\n\n") if preamble.strip() else ""
    s = pre + body
    return s if s.lstrip().startswith("import") else "import Mathlib\n\n" + s


def _typecheck_diag(snippet: str, lean_root: Path, timeout_s: int) -> str:
    """Best-effort SHORT diagnostic suffix for a failed advance probe — the FIRST Lean error, so a
    `did not typecheck` no_advance is self-classifying (vocabulary FALSE-negative vs genuine non-following).
    Re-compiles via the diag-returning `compile_probe_via_repl` (the bool `_compile_probe` discards the
    text). Returns '' when the REPL is unavailable / on any error (never raises into the gate)."""
    try:
        from ztare.formal.repl_compile import compile_probe_via_repl   # local import (best-effort writer rule)
        res = compile_probe_via_repl(snippet, lean_root, int(min(int(timeout_s), 120)))
        if res is None:
            return ""
        diag = (res[1] or "").strip()
        first = next((ln.strip() for ln in diag.splitlines() if "error" in ln.lower()), diag)
        return (" :: " + first[:140]) if first else ""
    except Exception:  # noqa: BLE001 — diagnostics never block the advance verdict
        return ""


def conjecture_advances(lemma: str, proof: str, lname: str, lean_root: Path,
                        timeout_s: int, preamble: str = "", goal_conclusion: str = "") -> "tuple[bool, str]":
    """Kernel-checked ADVANCE test: does the ORIGINAL goal follow from the conjectured lemma L?
    Compile `<L as sorry> + <goal proof citing L>` with the v33 probe (sorry-OK, error-free — L is
    DELIBERATELY unproven). Advances iff: (a) the goal-proof is sorry-free (G genuinely follows from L,
    not a hidden sorry), (b) it CITES `lname` in real tactic text (comments stripped — not a spurious
    direct proof), (c) the snippet typechecks. NO false-closure: this never closes G — it spawns L.

    `preamble`: the goal's DEFINITION context (the imports + depended-on defs/structures, WITHOUT the
    target theorem) — prepended so a goal that references local defs (e.g. `Good`, `algebraicFunctionPoint`)
    typechecks. Empty for self-contained goals (PutnamBench), where a bare `import Mathlib` suffices.

    `goal_conclusion`: the goal's conclusion (after its top-level `:`). If given, a conjecture whose OWN
    conclusion is the SAME statement is rejected as CIRCULAR — it merely RESTATES the goal rather than
    DECOMPOSING it (the load-bearing + typecheck legs PASS a verbatim restatement, so without this leg
    'advance' would credit a circular non-reduction; adversarial review 2026-06-05). Catches literal /
    α-restatement; definitional-unfolding equivalence is out of cheap reach (would need the kernel)."""
    if not lemma or not proof:
        return False, "no lemma/proof generated"
    if _has_sorry(proof):
        return False, "goal-proof not sorry-free (G must follow from L, not a hidden sorry)"
    proof_nc = _strip_comments(proof)   # canonical nested-aware strip (no ad-hoc regex)
    if lname not in proof_nc:
        return False, "goal-proof does not cite the conjectured lemma in tactic text (spurious / comment-only)"
    if goal_conclusion and _norm_ws(_lemma_conclusion(lemma)) == _norm_ws(goal_conclusion):
        return False, "conjectured lemma RESTATES the goal (circular — not a genuine sub-lemma reduction)"
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    snippet = _campaign_probe(preamble, lemma.strip() + "\n\n" + proof.strip())
    ok = _compile_probe(snippet, lean_root, "ConjAdvance", timeout_s)
    if ok is not True:
        # SELF-EXPLAINING no_advance (2026-06-21): surface the FIRST Lean error so a `did not typecheck`
        # is actionable — `unknown identifier`/`unknown constant` ⇒ a missing-vocabulary FALSE-negative
        # (the campaign def/banked-lemma was not in scope: check the `preamble` is threaded), whereas
        # `unsolved goals`/`type mismatch` ⇒ a GENUINE non-following decomposition. Best-effort; never blocks.
        return False, "did not typecheck (goal does not follow from L)" + _typecheck_diag(snippet, lean_root, timeout_s)
    # LOAD-BEARING check (deterministic, EXOGENOUS — stronger than the advisory LLM reviewer): replace L's
    # TYPE with `True` (a useless lemma) and re-compile the goal-proof. If it STILL compiles, the proof
    # didn't actually NEED L's content (cited-but-spurious — e.g. an unused `have _ := L`); if it now
    # FAILS, L is genuinely load-bearing. This catches the cosmetic-cite the substring check can't. Best-
    # effort: if L's signature can't be parsed to swap the type, skip this leg (keep the advance).
    _useless = _useless_lemma(lemma)
    if _useless and "True := by sorry" in _useless:
        _snip2 = _campaign_probe(preamble, _useless + "\n\n" + proof.strip())
        if _compile_probe(_snip2, lean_root, "ConjLoadBearing", timeout_s) is True:
            return False, "conjectured lemma is NOT load-bearing (goal-proof compiles with L:=True — cited but unused)"
    return True, "compiled — goal follows from the conjectured lemma (load-bearing)"


def decomposition_dag_audit(lemmas: "list[str]", chain_proof: str, lnames: "list[str]",
                            lean_root: Path, timeout_s: int, preamble: str = "",
                            goal_conclusion: str = "", goal_source: str = "",
                            goal_name: str = "") -> "tuple[bool, dict]":
    """Meta-Darwin FITNESS on a DECOMPOSITION — the operator's Step-4 gate (2026-06-05). Generalizes
    `conjecture_advances` from a single edge L⇒G to a multi-lemma DAG: given intermediate lemmas
    L1..Ln as SORRIED signatures (`theorem Lᵢ : … := by sorry`) + a `chain_proof` of the goal G that
    cites them, AUDIT — BEFORE the leaf spends ANY effort — whether the decomposition is SOUND and
    NON-CIRCULAR; KILL it otherwise. This is what makes the autonomous deanchor→isomorphism→decompose
    loop NON-IATROGENIC: it rejects the laundered / circular / vacuous decompositions that would
    otherwise manufacture fake lift (e.g. the 'n=1 closes unconditionally' restatement the adversary
    caught). All legs deterministic/kernel; fail-CLOSED on a confirmed defect, never closes G.

    Legs (returns (passed, verdict) with per-leg booleans + a `killed` reason on failure):
      (a) chain sorry-free — G genuinely follows from the Lᵢ, not a hidden sorry;
      (b) every Lᵢ cited in the chain (comments stripped) — no spurious lemma in the DAG;
      (c) NON-CIRCULAR — no Lᵢ's conclusion ≡ G's (a lemma must REDUCE, not RESTATE the goal);
      (d) COMPILES — preamble + all Lᵢ(sorried) + chain typechecks (well-typed DAG + G follows from the
          ASSUMED Lᵢ); this is the 'logically chains to the target' check;
      (e) LOAD-BEARING — replacing ALL Lᵢ types with `True` BREAKS the chain (the decomposition is
          genuinely used — not a direct proof of G that ignores the lemmas). `passed=True` ⇒ the Lᵢ are
          worth spawning as children for the existing solver to prove."""
    v: dict = {"n_lemmas": len(lemmas or [])}
    if not lemmas or not (chain_proof or "").strip():
        return False, {**v, "killed": "empty decomposition (no lemmas / no chain proof)"}
    if _has_sorry(chain_proof):
        return False, {**v, "killed": "chain proof not sorry-free (G must follow from the Lᵢ, not a hidden sorry)"}
    chain_nc = _strip_comments(chain_proof)   # canonical nested-aware strip (no ad-hoc regex)
    uncited = [ln for ln in (lnames or []) if ln and ln not in chain_nc]
    if uncited:
        return False, {**v, "killed": f"lemma(s) not cited in the chain (spurious): {uncited}"}
    if goal_conclusion:
        gc = _norm_ws(goal_conclusion)
        # CRITICAL (audit 2026-06-05): the chain must prove the GOAL G, not some unrelated statement.
        # Without this, a chain proving a trivial `2=2` passes every other leg (sorry-free, cites Lᵢ,
        # non-circular, typechecks, load-bearing) yet never reduces G — a spurious-success hole.
        if _norm_ws(_lemma_conclusion(chain_proof)) != gc:
            return False, {**v, "killed": "chain does NOT prove the goal G (chain concludes "
                           f"`{_lemma_conclusion(chain_proof)[:80]}`, not the goal)"}
        circ = [ln for L, ln in zip(lemmas, (lnames or [None] * len(lemmas)))
                if _norm_ws(_lemma_conclusion(L)) == gc]
        if circ:
            return False, {**v, "killed": f"CIRCULAR — lemma(s) restate the goal (no reduction): {circ}"}
    # KERNEL circularity (2026-06-22): the textual check above catches a LITERAL / same-name restatement,
    # but MISSES an α-renamed / definitionally-equal one — exactly the consciousness campaign's `iso_lemma1`,
    # which was the WHOLE target with `E→q, R→Q` renamed (textually different, the SAME Prop) and so sailed
    # through as a "sub-lemma," fragmenting a directly-provable goal. Complete the leg the docstring flagged as
    # "would need the kernel": for each Lᵢ, ask the ONE canonical statement-integrity oracle whether `@Lᵢ` is
    # the SAME Prop as `@G` (`@G = @Lᵢ := rfl`). Same-Prop ⇒ Lᵢ RESTATES G (no reduction) ⇒ circular → prove
    # G directly instead of "decomposing G into G". ENHANCEMENT-ONLY + fail-OPEN: `rfl` fires ONLY on a genuine
    # defeq, so it can NEVER reject a real (strictly-easier) sub-lemma; any oracle/compile error never rejects
    # (byte-parity with the no-leg path). SCOPE: active only when the caller threads the goal's full statement.
    if goal_source.strip() and goal_name.strip():
        try:
            from ztare.leanmill.solver.statement_integrity import kernel_type_equiv_fn
            from ztare.leanmill.lean_source import extract_signature as _exsig
            _eq = kernel_type_equiv_fn(goal_name, lean_root)
            if _eq is not None:
                for L, ln in zip(lemmas, (lnames or [None] * len(lemmas))):
                    _lsig = _exsig(L, ln) if ln else ""
                    if not _lsig.strip():
                        continue
                    # re-emit Lᵢ under the GOAL's name so the oracle (which keys on one name) compares @G vs @Lᵢ
                    _l_as_goal = f"theorem {goal_name} {_lsig} := by sorry"
                    if _eq(goal_source, _l_as_goal):
                        return False, {**v, "killed": f"CIRCULAR (kernel α/defeq) — lemma `{ln}` is the SAME "
                                       "Prop as the goal G (restates, does not reduce — prove G directly)"}
        except Exception:  # noqa: BLE001 — fail-OPEN: the kernel leg only ADDS catches; an error never rejects
            pass
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    _snip = lambda body: _campaign_probe(preamble, body)   # noqa: E731 — the ONE campaign-context door (see _campaign_probe)
    body = "\n\n".join(L.strip() for L in lemmas) + "\n\n" + chain_proof.strip()
    if _compile_probe(_snip(body), lean_root, "DagAudit", timeout_s) is not True:
        return False, {**v, "killed": "decomposition does NOT typecheck (G does not follow from the Lᵢ, or a Lᵢ is ill-typed)"}
    v["compiles"] = True
    # LOAD-BEARING: gut every lemma to `: True` and re-compile the chain. If it STILL compiles, the
    # chain proves G WITHOUT the lemmas' content — a fake decomposition (the leaf could prove G directly).
    useless = [_useless_lemma(L) for L in lemmas]
    # FAIL-CLOSED (audit 2026-06-05): if ANY lemma can't be gutted to `: True`, we CANNOT verify the
    # decomposition is load-bearing — do NOT silently skip the leg and pass (that exempted laundered
    # decompositions). An unverifiable load-bearing leg ⇒ kill.
    if not all(u and "True := by sorry" in u for u in useless):
        return False, {**v, "compiles": True,
                       "killed": "cannot verify load-bearing — a lemma signature is unparseable (fail-closed)"}
    snip2 = _snip("\n\n".join(useless) + "\n\n" + chain_proof.strip())
    if _compile_probe(snip2, lean_root, "DagLoadBearing", timeout_s) is True:
        return False, {**v, "compiles": True,
                       "killed": "NOT load-bearing (chain compiles with every Lᵢ:=True — decomposition unused)"}
    return True, {**v, "compiles": True, "load_bearing": True,
                  "passed": "sound, non-circular, load-bearing, proves-G decomposition — spawn the Lᵢ"}


# ── CAPABILITY B: SPECIALIZE — the "do the easy case first" move (2026-06-05) ────────────────────────
# The forward/downward dual of conjecture. conjecture splits a goal VERTICALLY (invent L, L⇒G).
# specialize moves DOWN to a tractable INSTANCE/RESTRICTION G' of G (fix a parameter, n=1, add a
# simplifying hypothesis) and PROVES G' fully — a verified special-case RUNG (real governed progress on
# a hard/open goal), NOT a closure of G. This is the move a human uses on an open problem and the
# variant-curriculum capability AlphaProof uses at scale; leanmill had it NAMED in the RD vocabulary
# (Polya specialize) but never wired into the solver. P1 head-to-head (2026-06-05) is the evidence:
# the leaf, told to close the full open goal, CHEATED; given the freedom to SPECIALIZE, it makes honest
# progress instead. SOUND by construction: G' must (a) close sorry-free, (b) be a genuine CONSEQUENCE of
# G (`G ⇒ G'` typechecks — so it's weaker, an instance/restriction, not a different/stronger claim),
# (c) be non-vacuous and ≠ G. The kernel gates all three — the leaf can't launder an unrelated easy
# theorem as "progress on G".
from ztare.leanmill.solver.prompts import SPECIALIZE_PROMPT as _SPECIALIZE_PROMPT


def specialize_generate(row: dict, goal_text: str, lean_root: Path, timeout_s: int,
                        preamble: str = "") -> "tuple[str, str, str, str]":
    """Ask the leaf for a PROVABLE SPECIAL CASE G' of a hard/open goal + its proof + the `G ⇒ G'`
    implication. Returns (special_block, implies_block, sname, raw_tail). ('','',sname,err) on failure
    (⇒ no genuine specialization, never a false rung)."""
    base = re.sub(r"[^A-Za-z0-9_]", "", (row.get("target_theorem_name") or "spec"))[:24] or "spec"
    sname = f"spec_{base}"
    ban = ""  # caller may inject banned-terms via prompt context; reserved
    prompt = _SPECIALIZE_PROMPT.format(sname=sname, ban=ban, goal=goal_text)
    if preamble.strip():
        prompt = prompt.replace("the PREAMBLE", "the PREAMBLE below") + "\nPREAMBLE:\n" + preamble.strip() + "\n"
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        raw = default_dispatch(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception as e:  # noqa: BLE001
        return "", "", sname, f"dispatch_error: {e!r}"

    from ztare.leanmill.solver.agent_output import fenced_block
    return fenced_block(raw,"SPECIAL:"), fenced_block(raw,"IMPLIES:"), sname, (raw or "")[-200:]


def specialization_is_genuine(special_block: str, implies_block: str, sname: str, goal_conclusion: str,
                              lean_root: Path, timeout_s: int, preamble: str = "") -> "tuple[bool, str]":
    """Kernel-gated GENUINENESS test for a proposed special case (the verified-rung gate). Genuine iff:
    (a) G' compiles SORRY-FREE (a real closed theorem); (b) the `G ⇒ G'` implication compiles SORRY-FREE
    (so G' is a genuine CONSEQUENCE of G — weaker, an instance/restriction, not a different claim);
    (c) G' is NON-vacuous and its conclusion ≠ G's (strictly easier, actually specialized). A genuine,
    closed G' is a verified special-case rung — real progress on a hard/open goal, never a closure of G."""
    if not special_block:
        return False, "no special case generated"
    if _has_sorry(special_block):
        return False, "special case not sorry-free (must be a genuinely PROVED instance)"
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    g_concl = _lemma_conclusion(special_block)
    if not g_concl:
        return False, "could not parse the special case's conclusion"
    if goal_conclusion and _norm_ws(g_concl) == _norm_ws(goal_conclusion):
        return False, "special case is IDENTICAL to the goal (not a specialization)"
    if _norm_ws(g_concl) in ("True", "(True)"):
        return False, "special case is vacuous (`True`)"
    # (a) G' closes sorry-free  [_campaign_probe = the ONE campaign-context door, see its docstring]
    if _compile_probe(_campaign_probe(preamble, special_block.strip()), lean_root, "SpecClose", timeout_s) is not True:
        return False, "special case does NOT compile sorry-free (not a genuine closed instance)"
    # (b) G ⇒ G' : the implication must typecheck sorry-free (so G' is a genuine consequence of G)
    if not implies_block or _has_sorry(implies_block):
        return False, "missing/incomplete `G ⇒ G'` implication — cannot confirm G' is a genuine special case of G"
    if _compile_probe(_campaign_probe(preamble, implies_block.strip()), lean_root, "SpecImplies", timeout_s) is not True:
        return False, "`G ⇒ G'` does not typecheck — G' is NOT a genuine consequence of the goal (possible laundered unrelated theorem)"
    return True, "genuine special-case rung — G' closes sorry-free AND is a kernel-checked consequence of G"


def specialization_substantive(goal_text: str, special_block: str) -> "tuple[bool, str]":
    """ADVISORY non-degeneracy signal (the cross-field 'substantive specialization' invariant, deanchored
    across PDE u≢0 / AG generic-point / model-theory non-vacuous / CEGIS non-trivial-witness / DOE
    discriminating-point: a special case is SUBSTANTIVE iff its truth stays CONTINGENT on the hard
    structure, DEGENERATE iff it collapses to a corner whose truth is unconditioned on it).

    STRUCTURAL, non-lexical (Leg 3a — parameter/object-variable retention; deliberately NOT a
    {0,1,∅,…} watch-list, which rots and false-positives on legit base cases): take the goal's binder
    variables that its CONCLUSION depends on, and check whether G''s conclusion still references ANY of
    them. The trivial corner (`f := 0`, or `f := const` however spelled — even via nested defs) DROPS
    those variables from the conclusion, so its truth no longer depends on the hard object; a substantive
    special case (restrict f to a non-empty subclass / fix an AUXILIARY parameter while keeping the
    object) retains at least one. Returns (substantive, reason). ADVISORY per §3b — used to MEASURE
    substantive-vs-trivial rungs and to drive a refine retry; promote to a hard gate only after a
    pos/neg/laundered-corner calibration shows 1.0 catch / 0.0 FP."""
    g_concl = _lemma_conclusion(special_block) if special_block else ""
    goal_concl = _lemma_conclusion(goal_text) if goal_text else ""
    if not g_concl or not goal_concl:
        return True, "no conclusions to compare — advisory pass"
    sig = goal_text[:_top_level_colon(goal_text)] if goal_text else ""
    # binder variable names: the identifiers before each top-level `:` inside (...)/{...}/⦃...⦄ groups
    names: set[str] = set()
    for grp in re.findall(r"[(\{⦃]([^(){}⦃⦄]*?):[^(){}⦃⦄]*[)\}⦄]", sig):
        for tok in grp.replace(",", " ").split():
            if re.fullmatch(r"[A-Za-z_][\w']*", tok):
                names.add(tok)
    # the subset the GOAL's conclusion actually depends on (the hard object/parametric vars)
    concl_vars = {v for v in names if re.search(rf"(?<![\w']){re.escape(v)}(?![\w'])", goal_concl)}
    if not concl_vars:
        return True, "goal conclusion has no bound variables to condition on — advisory pass"
    retained = {v for v in concl_vars if re.search(rf"(?<![\w']){re.escape(v)}(?![\w'])", g_concl)}
    if retained:
        return True, f"substantive: G' conclusion still conditioned on goal var(s) {sorted(retained)}"
    return False, (f"degenerate corner: G' conclusion dropped ALL goal conclusion-var(s) {sorted(concl_vars)} "
                   "— truth unconditioned on the hard structure (the f:=0 / u≡0 / degenerate-fiber corner)")


# ── GENERALIZE — the induction-strengthening move (the CLOSURE dual of specialize) ────────────────────
# Meta-language: a Construct/Transfer move ("Generalization & Abstraction", shared-core). Sometimes a
# goal is hard because it's TOO SPECIFIC — no inductive leverage. The fix is to prove a STRONGER, more
# general fact G' (a stronger inductive hypothesis) and close the goal as an INSTANCE of it.
#
# SOUNDNESS / no-frankenstein: generalize is a CLOSURE move, and a closure of G is — by definition — a
# proof OF G. So it emits a SINGLE self-contained tactic-block proof of the ORIGINAL goal that does the
# strengthening INTERNALLY (a `have`/`suffices` proving the stronger statement, then closing the goal
# from it). That proof routes through the EXACT SAME governance as every direct move
# (`_verify_compile` + `_validate_against_contract` = kernel-compile receipt + matched-negative-control +
# statement_integrity). There is therefore NO separate closure path and NO false-closure surface: the
# strengthening lives in a `have`, the theorem the kernel ratifies is G unaltered. The leaf can't launder
# (statement_integrity guards G's statement; MNC guards leakage). "Did it really generalize vs prove G
# directly" is a LIFT question (the A=B selection test), not a soundness one — so this ships default-OFF
# and is promoted only if signal-gated selection beats the plain menu.
# ── CAPABILITY (Invert leg): FALSIFY — the "is the target actually FALSE?" producer (2026-06-06) ──────
# The refutation dual of a closure, and the Lean instance of the shared Popper inversion
# (common/inversion.py): on the OPEN/untrusted-statement regime (the anti-laundering gate's whole reason to exist) the
# target may be FALSE, and a kernel-checked proof of ¬G is a first-class, high-value outcome (excluding a
# false conjectured (sub)goal before more budget is spent). leanmill had a falsifier SINK (NODE_KIND/status/MoveResult.falsifier
# + residual_to_lever) but NO producer — this feeds it. SOUND by construction: the refuted statement is
# OURS, not the leaf's. We build the closed Prop G from the goal's own signature, pin it into a refute
# theorem whose type is literally `¬ (G)`, and the leaf supplies ONLY the proof body — so "negate a
# strawman / weakened statement" (the warm-path statement-alteration laundering vector, MEMORY 2026-06-06)
# is structurally impossible. The kernel then gates it exactly like a closure: sorry-free + the ¬G proof
# genuinely typechecks + the anti-laundering organs pass. A falsifier and a closure of the SAME G cannot
# coexist under a consistent kernel, so this never manufactures a false "it's false" verdict.
def _closed_goal_prop(goal_text: str) -> str:
    """The goal's statement as a CLOSED Prop: `∀ <binders>, <conclusion>` (or just the conclusion when
    there are no binders) — i.e. the theorem's type, which is exactly what ¬(...) must negate. '' if the
    signature can't be cleanly split (⇒ caller bails: no falsify attempt rather than an unsound one)."""
    from ztare.leanmill.solver.statement_integrity import _signature
    sig = _signature((goal_text or "").strip())
    j = _top_level_colon(sig)
    if j < 0:
        return ""
    head, concl = sig[:j], sig[j + 1:].strip()
    if not concl:
        return ""
    # strip the leading `theorem|lemma|example <name>` to leave just the binder telescope
    from ztare.leanmill import lean_source as _ls   # canonical Lean parsing
    binders = _ls.strip_decl_prefix(head)
    cn = _norm_ws(concl)
    if cn in ("True", "(True)", "False", "(False)"):
        return ""   # degenerate literal — not a real open goal to refute
    return f"∀ {binders}, {concl}" if binders else concl


def _current_goal_prop(target_name: str, source_text: str, goal: str) -> str:
    """Closed Prop for the target currently under adjudication."""
    goal = (goal or "").strip()
    if not goal and source_text and target_name:
        try:
            from ztare.leanmill.lean_source import extract_signature as _exsig
            goal = (_exsig(source_text, target_name) or "").strip()
        except Exception:  # noqa: BLE001
            goal = ""
    return _closed_goal_prop(goal)


def _strip_wrapping_parens(s: str) -> str:
    s = (s or "").strip()
    changed = True
    while changed and s.startswith("(") and s.endswith(")"):
        changed, depth = False, 0
        for i, ch in enumerate(s):
            if ch in "([{⟨":
                depth += 1
            elif ch in ")]}⟩":
                depth -= 1
                if depth == 0 and i != len(s) - 1:
                    return s
        if depth == 0:
            s = s[1:-1].strip()
            changed = True
    return s


def _negated_prop(concl: str) -> str:
    concl = (concl or "").strip()
    if concl.startswith("¬"):
        return _strip_wrapping_parens(concl[1:].strip())
    if concl.startswith("Not "):
        return _strip_wrapping_parens(concl[4:].strip())
    return ""


def _matching_refutation_declaration(refute_source: str, current_gprop: str) -> str:
    """Return the declaration whose type is exactly the negation of ``current_gprop``."""
    if not (refute_source and current_gprop):
        return ""
    try:
        from ztare.leanmill.lean_source import decl_blocks, decl_kind
        for name, block in decl_blocks(refute_source):
            if not name or decl_kind(block) not in {"theorem", "lemma"}:
                continue
            neg = _negated_prop(_lemma_conclusion(block))
            if neg and _norm_ws(neg) == _norm_ws(_strip_wrapping_parens(current_gprop)):
                return name
    except Exception:  # noqa: BLE001
        return ""
    return ""


def _refutation_matches_current_goal(refute_source: str, target_name: str, current_gprop: str) -> bool:
    """A reusable refutation must negate the closed Prop for this exact target signature."""
    return bool(target_name and _matching_refutation_declaration(refute_source, current_gprop))


from ztare.leanmill.solver.prompts import FALSIFY_PROMPT as _FALSIFY_PROMPT


def falsify_generate(row: dict, goal_text: str, lean_root: Path, timeout_s: int,
                     preamble: str = "", nugget: str = "") -> "tuple[str, str, str, str]":
    """Ask the leaf for a proof of ¬G (a falsifying witness). Returns (refute_block, fname, gprop,
    raw_tail) where refute_block is the FULLY-ASSEMBLED `[helpers]\\n\\ntheorem <fname>_refute : ¬ (G)
    := by <body>` (statement owned by US, not the leaf). ('', fname, gprop, err) on failure / no
    refutation (⇒ no falsifier, never a false 'it's false').

    `nugget` (the CEGAR/proof-sketch reuse): a counterexample INSIGHT a prior skeptic/leaf already found
    for THIS statement (recycled from `no_good_store`'s `statement_false` witness, or the current leaf's own
    probe). Seeded as a HINT so the skeptic ADAPTS the known crux to OUR goal instead of re-deriving from a
    blank page (why CLOB looped: the leaf found a hard ULift counterexample the throwaway fresh skeptic could
    not reproduce). SOUND + un-launderable: the refutation theorem's signature (¬ of OUR goal) is still fixed
    and the kernel re-checks the proof — a wrong nugget merely fails to help. Goldilocks: nugget = affordance,
    kernel = the only determinism."""
    base = re.sub(r"[^A-Za-z0-9_]", "", (row.get("target_theorem_name") or "tgt"))[:24] or "tgt"
    fname = f"fls_{base}"
    gprop = _closed_goal_prop(goal_text)
    if not gprop:
        return "", fname, "", "could not build a closed Prop from the goal signature"
    pre = ("\nPREAMBLE:\n" + preamble.strip() + "\n") if preamble.strip() else ""
    _nug = ""
    if (nugget or "").strip():
        from ztare.leanmill.solver.prompts import FALSIFY_NUGGET_SEED as _NUG
        _nug = _NUG.format(nugget=nugget.strip()[:1600])
    prompt = _FALSIFY_PROMPT.format(fname=fname, gprop=gprop, goal=goal_text, pre=pre, nugget=_nug)
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        raw = default_dispatch(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception as e:  # noqa: BLE001
        return "", fname, gprop, f"dispatch_error: {e!r}"

    from ztare.leanmill.solver.agent_output import fenced_block
    helpers, proof = fenced_block(raw,"HELPERS:"), fenced_block(raw,"PROOF:")
    if not proof:
        return "", fname, gprop, (raw or "")[-200:]   # honest non-refutation
    # ASSEMBLE with OUR signature — the leaf supplies only the RHS proof (a `by` block OR a proof term),
    # never the statement. (Forcing `:= by` would reject the common ¬∀ disproof-by-term `fun h => …`.)
    theorem = f"theorem {fname}_refute : ¬ ({gprop}) := {proof.strip()}"
    refute_block = (helpers.strip() + "\n\n" + theorem) if helpers.strip() else theorem
    return refute_block, fname, gprop, (raw or "")[-200:]


def falsification_is_genuine(refute_block: str, fname: str, gprop: str,
                             lean_root: Path, timeout_s: int, preamble: str = "") -> "tuple[bool, str]":
    """Kernel-gated genuineness test for a falsifying witness (the verified-falsifier gate). Genuine iff:
    (a) refute_block is non-empty and SORRY-free/admit-free; (b) the negated Prop is non-degenerate
    (gprop is a real statement, not literal True/False); (c) the assembled `theorem <fname>_refute :
    ¬ (gprop) := by ...` COMPILES sorry-free against preamble+Mathlib (a genuine, kernel-checked proof
    of ¬G). Because WE assembled the signature, (c) passing means ¬ of the VERBATIM goal Prop is proved —
    no strawman possible. The runner additionally routes the source through run_anti_laundering_kernel
    (vacuity / leakage / consequence-exposure organs)."""
    if not refute_block:
        return False, "no refutation generated (honest non-falsification)"
    if _has_sorry(refute_block):
        return False, "refutation not sorry-free (must be a genuinely PROVED ¬G)"
    if not gprop or _norm_ws(gprop) in ("True", "(True)", "False", "(False)"):
        return False, "degenerate/empty negated Prop"
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    if _compile_probe(_campaign_probe(preamble, refute_block.strip()), lean_root, "FalsifyRefute", timeout_s) is not True:
        return False, "¬G does NOT compile sorry-free — not a genuine refutation"
    return True, "genuine falsifier — a kernel-checked sorry-free proof of ¬(the verbatim goal Prop)"


def _reverify_agent_refutation(target_name: str, lean_root: "Path", timeout_s: int,
                               source_text: str = "", goal: str = "") -> "tuple[bool, str, str]":
    """REUSE the agent's OWN kernel-checked counterexample instead of re-deriving ¬G — the fix for the recurring
    'FALSIFY recovery never fires' bug (CLOB v1/v2, EF1: the FRESH skeptic in `falsify_generate` could not reproduce
    the leaf's complex ULift/list counterexample, so `¬G NOT kernel-confirmed` → the reformulation re-entry never
    fired and the campaign GROUND A FALSE LEMMA forever). The leaf ALREADY proved the target false: a sorry-free
    `-- STATEMENT-FALSE:` probe carrying a proved negation. The host appends a theorem whose type is exactly
    ``¬G`` and whose proof cites the saved declaration; Lean, rather than a name/text heuristic, decides whether
    the saved theorem refutes this statement. ZTARE_LEANMILL_REUSE_AGENT_REFUTATION=0
    reverts to always-re-derive. Returns (confirmed, detail, refute_block) or (False, why, '')."""
    import os
    if os.environ.get("ZTARE_LEANMILL_REUSE_AGENT_REFUTATION", "1") == "0":
        return False, "reuse disabled", ""
    current_gprop = _current_goal_prop(target_name, source_text, goal)
    if not current_gprop:
        return False, "cannot compute current target proposition for refutation reuse", ""
    try:
        import glob as _glob
        from ztare.leanmill.solver.agentic_leaf import probe_dir as _pd, robust_probe_glob as _rpg
        from ztare.formal.repl_compile import warm_verify_campaign as _wvc
    except Exception:  # noqa: BLE001 — reuse is best-effort; fall through to the skeptic
        return False, "no probe infra", ""
    try:
        # ROBUST probe search (the run-scratch split-brain, RCA 2026-07-04): `probe_dir` returns the RUN-ISOLATED
        # subdir only when ZTARE_LEANMILL_RUN_SCRATCH is set in THIS process; a caller (or a differently-launched
        # run) may leave it flat while the probes sit in `.solver_scratch/<run_tag>/`. Search the resolver's dir
        # AND the flat base AND every run subdir (isolated-first + fallback) so the reuse never misses the probe.
        pdir = _pd(lean_root)
        base = Path(lean_root) / ".solver_scratch"
        search = [pdir, base] + (sorted(base.glob("*/"), key=lambda d: d.stat().st_mtime, reverse=True)[:12]
                                 if base.exists() else [])
        seen, cands = set(), []
        for d in search:
            # BOTH the broad name-substring glob AND the canonical `robust_probe_glob` — `robust_probe_name`
            # TRUNCATES the target segment (`_probe_target_seg`), so a long target's RobustProbe file
            # (`RobustProbe_quiescent…no_blockin_codex_0.lean`) is INVISIBLE to `*{full_target}*` and the agent's
            # kernel-VALID refutation is silently discarded → falsify falls to a fresh skeptic that fails → the
            # campaign grinds a FALSE statement. The forgotten-sibling class the canonical glob exists to kill
            # ("route every reader through here"). RCA 2026-07-06 (gale capstone, 46-char target).
            for _pat in (f"*{target_name}*.lean", _rpg(target_name)):
                for pf in _glob.glob(str(Path(d) / _pat)):
                    if pf not in seen:
                        seen.add(pf); cands.append(pf)
        cands = sorted(cands, key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0.0, reverse=True)
    except Exception:  # noqa: BLE001
        return False, "probe dir unreadable", ""
    for pf in cands[:8]:
        try:
            txt = Path(pf).read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        if _has_sorry(txt):
            continue
        from ztare.leanmill import lean_source as _lean_source

        refutation_names = [
            name
            for name, block in _lean_source.decl_blocks(txt)
            if name
            and _lean_source.decl_kind(block) in {"theorem", "lemma"}
            and _negated_prop(_lemma_conclusion(block))
        ]
        if not refutation_names:
            continue
        # ROOT FIX (2026-07-05, the recurring-ghost class ONCE AND FOR ALL): verify the counterexample against the
        # SUBSTRATE's REAL defs, NOT base Mathlib. A self-contained probe RE-DECLARES the theory (bestBid, Book,
        # Uncrossed …), and those re-declarations can DIVERGE from the substrate in ANY dimension — a weaker
        # typeclass ([LT K] vs [LinearOrder K] = the carrier ghost) OR a different def BODY (bestBid=head vs the
        # substrate's max = the def ghost). Compiled against base Mathlib (env=None), the ¬G is validated against
        # the PROBE's OWN (possibly weaker/wrong) defs → a counterexample that does NOT hold under the real theory
        # gets "confirmed" → a bogus reformulation forever. Every prior fix (carrier_order_weakened) patched ONE
        # divergence dimension; this closes the CLASS: STRIP the probe's re-declarations of substrate-provided
        # decls and re-verify the ¬G against the SUBSTRATE env (which supplies the REAL defs). A head-based
        # counterexample then FAILS (the substrate's max breaks its `Uncrossed initial` hypothesis) ⇒ not confirmed.
        # Falls back to base Mathlib ONLY when no substrate is registered (parity for non-campaign use).
        # DIVERGENCE GUARD (2026-07-05, the recurring falsify-ghost class, ONCE AND FOR ALL — NO env change, so the
        # universe-false-reject cure `env=None` for self-contained probes stays fully intact). A self-contained
        # probe RE-DECLARES the theory (to be checkable in base Mathlib). If it re-declares a SUBSTRATE def with a
        # DIFFERENT body/signature — `bestBid=head` vs the substrate's `max`, `[LT K]` vs `[LinearOrder K]` — its
        # counterexample is validated against a DIVERGENT theory, so a ghost that does NOT hold under the real
        # substrate gets "confirmed" (the CLOB head-ghost + the carrier ghost are two faces of THIS). Pure-text,
        # name-by-name: reject the reuse when the probe re-declares a shared def differently; an IDENTICAL
        # (universe-poly) re-statement is NOT flagged, so no regression. Subsumes `carrier_order_weakened`.
        try:
            from ztare.formal.repl_compile import get_campaign_substrate as _gcs2
            from ztare.leanmill.lean_source import substrate_infidelities as _sinf2
            _sub2 = _gcs2()
            if _sub2 and Path(_sub2).exists():
                _div = _sinf2(txt, Path(_sub2).read_text(encoding="utf-8", errors="replace"))
                if _div:
                    continue   # divergence ghost — probe's theory ≠ substrate's; its ¬G refutes a DIFFERENT theory
        except Exception:  # noqa: BLE001 — guard best-effort; a read failure must not suppress a genuine reuse
            pass
        # The positive-proof harness appends ``#print axioms <target>``.
        # A refutation omits that target. Audit a host-owned exact-identity
        # bridge; only a theorem that Lean can use to prove ``¬G`` survives.
        refutation_source = _lean_source.strip_print_axioms_commands(txt)
        bridge_name = "ztare_saved_refutation_bridge"
        for refutation_name in reversed(refutation_names):
            bridged_source = (
                refutation_source.rstrip()
                + f"\n\ntheorem {bridge_name} : ¬ ({current_gprop}) := by\n"
                + f"  exact {refutation_name}\n"
            )
            r = _wvc(
                bridged_source,
                bridge_name,
                str(lean_root),
                min(timeout_s, 180),
                env=None,
            )
            if r is None:
                from tempfile import TemporaryDirectory
                from ztare.gates.lean_compile_primitives import audit_axioms_subset

                with TemporaryDirectory(prefix="leanmill_saved_refutation_") as directory:
                    clean, _confirmed_bad, axioms = audit_axioms_subset(
                        bridged_source,
                        bridge_name,
                        Path(directory) / "Probe.lean",
                        Path(lean_root),
                        timeout_s=min(timeout_s, 180),
                    )
                r = (
                    clean,
                    "cold axiom audit: " + (", ".join(axioms) if axioms else "no extra axioms"),
                )
            if r is not None and bool(r[0]):
                return (
                    True,
                    f"reused agent's kernel-checked counterexample ({Path(pf).name}): {str(r[1])[:80]}",
                    bridged_source,
                )
    return False, "no reusable non-divergent agent refutation probe for this target", ""


def recover_saved_refutation(
    target_name: str,
    source_text: str,
    lean_root: "Path",
    timeout_s: int,
) -> "tuple[bool, str, str]":
    """Kernel-recheck a saved exact-statement refutation without dispatching an agent."""
    return _reverify_agent_refutation(
        target_name,
        lean_root,
        timeout_s,
        source_text=source_text,
    )


# ── SINGLE-DOOR refutation memo (2026-07-06, gale capstone — operator "single door, do it both"). The leaf can
# KERNEL-CONFIRM ¬G (the statement-integrity gate in agentic_leaf) but that verdict was flattened to a TEXT tail
# in `_agentic_leaf_warm_solve` and LOST — so solve_adhoc's epilogue rolled a FRESH re-verify that a carrier
# ghost / an overwritten probe defeats, and the reformulation never fired though the leaf ALREADY saw the target
# was false (gale: 3 verifiers gave 3 answers on the SAME target). Fix: `verify_statement_false_claim._gate` —
# the ONE funnel every ¬G verdict already passes through — now REMEMBERS each SURVIVING confirmed refutation for
# the run; every consumer reads the SAME memory instead of re-deriving it. Sound: we memoize only what `_gate`
# already kernel-confirmed AND carrier-ghost-passed (never a bare claim); keyed on the goal so a later
# STRENGTHENED statement (new goal, same name) never reuses the weak statement's ¬G.
_CONFIRMED_REFUTATIONS: "dict[tuple, object]" = {}


def _statement_identity(target_name: str, source_text: str, goal: str) -> str:
    """Canonical statement identity for the memo key. The leaf re-forms its goal into `∀`-shape
    (`_leaf_goal_from_source`) so the raw goal STRING differs between the leaf's verify and the epilogue's read —
    key on the target's SIGNATURE recovered from source instead (goal-form-independent, and it CHANGES when the
    statement is reformulated, so a strengthened statement never reuses the weak one's ¬G). Both sides read the
    SAME source for the SAME target ⇒ identical key. Falls back to the normalized goal when no signature."""
    try:
        from ztare.leanmill.lean_source import extract_signature as _exsig
        sig = (_exsig(source_text, target_name) or "").strip() if source_text else ""
        if sig:
            return " ".join(sig.split())
    except Exception:  # noqa: BLE001 — signature recovery is best-effort; fall back to the goal
        pass
    return " ".join((goal or "").split())


def current_statement_id(target_name: str, source_text: str, goal: str):
    """Diagnostics carrier for the exact statement currently being adjudicated."""
    from ztare.leanmill.control_plane import StatementId
    return StatementId.from_parts(
        target_name=target_name,
        source_text=source_text or "",
        closed_prop=_statement_identity(target_name, source_text, goal),
    )


def _refutation_key(target_name: str, source_text: str, goal: str) -> "tuple":
    import os as _os
    sid = current_statement_id(target_name, source_text, goal)
    return (_os.environ.get("ZTARE_SOLVER_RUN_TAG", ""), target_name or "",
            sid.closed_prop_norm, sid.closed_prop_hash)


def _remember_refutation(
    target_name: str,
    source_text: str,
    goal: str,
    block: str,
    *,
    provenance: str,
    detail: str,
):
    if not (target_name and block):
        return None
    try:
        import hashlib
        from ztare.leanmill.control_plane import Verdict, VerdictKind

        verdict = Verdict(
            kind=VerdictKind.REFUTED,
            statement_id=current_statement_id(target_name, source_text, goal),
            provenance=provenance,
            detail=detail,
            artifacts={
                "refutation_block_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
                "lean_source_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
                "lean_source": block,
            },
        )
        _CONFIRMED_REFUTATIONS[_refutation_key(target_name, source_text, goal)] = verdict
        return verdict
    except Exception:  # noqa: BLE001 — the memo is an optimization; never break a verdict
        return None


def confirmed_refutation(target_name: str, source_text: str, goal: str) -> str:
    """The kernel-confirmed ¬G refutation block for this statement recorded earlier THIS run by
    `verify_statement_false_claim` — or "" if none. Lets solve_adhoc's epilogue honor the leaf's already-
    kernel-checked verdict WITHOUT a fresh re-verify (which a carrier ghost or an overwritten probe defeats).
    ZTARE_LEANMILL_REFUTATION_MEMO=0 reverts to the re-verify-only path."""
    import os as _os
    if _os.environ.get("ZTARE_LEANMILL_REFUTATION_MEMO", "1") == "0":
        return ""
    verdict = _CONFIRMED_REFUTATIONS.get(_refutation_key(target_name, source_text, goal))
    try:
        return verdict.kernel_refutation_source() if verdict is not None else ""
    except Exception:  # noqa: BLE001 — compatibility read must fail closed
        return ""


def confirmed_refutation_verdict(
    target_name: str, source_text: str, goal: str
) -> "dict | None":
    """Operational typed verdict for the current statement, if kernel-confirmed."""
    verdict = _CONFIRMED_REFUTATIONS.get(_refutation_key(target_name, source_text, goal))
    try:
        return verdict.to_json() if verdict is not None and verdict.kernel_refutation_source() else None
    except Exception:  # noqa: BLE001 — invalid memo entries carry no authority
        return None


def adjudicate_statement_false_verdict(target_name: str, source_text: str, goal: str,
                                       confirmed: bool, detail: str, block: str,
                                       *, provenance: str = "verify_statement_false_claim",
                                       extra: "dict | None" = None) -> "tuple[bool, str, str]":
    """Shared admission point for an already-kernel-checked `¬G` candidate.

    Generation paths may differ, but the verdict side effects must not: apply the substrate-drift guard,
    populate the in-process refutation memo, and emit the typed verdict telemetry. This helper does not compile
    or prove anything; callers pass `confirmed=True` only after their own kernel gate has accepted the block."""
    verdict = (bool(confirmed), detail or "", block or "")
    if verdict[0] and verdict[2] and os.environ.get("ZTARE_LEANMILL_CARRIER_GHOST_GUARD", "1") != "0":
        try:
            from ztare.formal.repl_compile import get_campaign_substrate as _gcs
            from ztare.leanmill.lean_source import substrate_infidelities as _sinf
            _sub = _gcs()
            _sub_src = Path(_sub).read_text(encoding="utf-8", errors="replace") if _sub and Path(_sub).exists() else ""
            _weak = _sinf(verdict[2], _sub_src) if _sub_src else []
            if _weak:
                verdict = (False, f"substrate ghost — refutation drifts from the substrate ({_weak[0]}); it "
                                  f"refutes a DIFFERENT theory, not the committed one (no reformulation)", "")
        except Exception:  # noqa: BLE001 — the guard is best-effort; never suppress a refutation on a read error
            pass
    verdict_object = None
    if verdict[0] and verdict[2]:
        verdict_object = _remember_refutation(
            target_name,
            source_text,
            goal,
            verdict[2],
            provenance=provenance,
            detail=verdict[1],
        )
    try:
        from ztare.leanmill.control_plane import Verdict, VerdictKind
        from ztare.leanmill.verdict_store import emit_verdict
        emit_verdict(
            verdict_object or Verdict(
                kind=VerdictKind.UNVERIFIED,
                statement_id=current_statement_id(target_name, source_text, goal),
                provenance=provenance,
                detail=verdict[1],
            ),
            extra={"target_name": target_name or "", "has_refutation_block": bool(verdict[2]), **(extra or {})},
        )
    except Exception:  # noqa: BLE001 — telemetry must never affect the falsify verdict
        pass
    return verdict


def verify_statement_false_claim(target_name: str, source_text: str, goal: str,
                                 lean_root: Path, timeout_s: int, nugget: str = "") -> "tuple[bool, str, str]":
    """GATE a SOFT `-- STATEMENT-FALSE:` leaf CLAIM at the soundness boundary. The engine's rule is that ONLY
    a kernel-checked ¬G is a refutation verdict (a code comment is the agent's hypothesis, not a verdict);
    accepting a bare claim let the v7 leaf escape a TRUE, tractable lemma with a bogus counterexample (one
    that violates a structure-field hypothesis), deadlocking the reformulation re-entry on a provable target.

    This dispatches the SKEPTIC (`falsify_generate` — an INDEPENDENT attempt to PROVE ¬G, the same machinery
    MOVE_FALSIFY uses) and kernel-verifies the result. The verify routes through the WARM campaign env when a
    substrate is registered — so confirming a claim re-uses the amortized elaboration and does NOT re-introduce
    the verify-starvation that the inline path suffered. The negated goal's signature is OWNED by us (no
    strawman), and the `#print axioms` audit on the warm path rejects a ¬G that launders via a still-`sorry`
    decl in the env. Returns (confirmed, detail, refute_block): confirmed=True ONLY when ¬G genuinely compiles
    sorry-free with a clean axiom set ⇒ the target really is false; else (False, why, "") ⇒ the claim is
    UNVERIFIED and must NOT trigger reformulation.

    The PREAMBLE for the cold fallback is the source prelude up to the target (so a ¬G that needs the campaign
    defs can still elaborate when no warm env is available); on the warm path the env already holds them."""
    row = {"target_theorem_name": target_name}

    def _gate(confirmed: bool, detail: str, block: str) -> "tuple[bool, str, str]":
        """THE SINGLE DOOR for a ¬G verdict (2026-07-04, CLOB carrier-ghost). WHATEVER path confirmed the
        falsification — the reuse of the leaf's own probe, the warm skeptic, the cold skeptic, or any future
        producer — its refutation block flows through here before it counts as a refutation. Reject a CARRIER
        GHOST: a probe that re-declares a substrate carrier with a STRICTLY WEAKER order class (`[LT K][LE K]`
        where the substrate has `[LinearOrder K]`) refutes a WEAKER theory than the one committed to — its
        degenerate `≤` (e.g. always-false) is impossible under the real instance, so the 'counterexample' does
        NOT refute the substrate statement and must never drive a reformulation. One check, every path; a genuine
        counterexample keeping the real order passes clean. Fail-safe: a substrate/read error never suppresses a
        real refutation. ZTARE_LEANMILL_CARRIER_GHOST_GUARD=0 reverts.

        Every SURVIVING confirmed verdict is also REMEMBERED for the run (`_remember_refutation`), so a downstream
        consumer (solve_adhoc's epilogue) honors the leaf's kernel verdict without a fresh re-verify that a ghost
        or an overwritten probe would defeat — the single door from 'the leaf saw it's false' to reformulation."""
        return adjudicate_statement_false_verdict(
            target_name, source_text, goal, confirmed, detail, block,
            provenance="verify_statement_false_claim")
    # GOAL RECOVERY: every falsification path, including probe reuse, must adjudicate THIS statement.
    # A stale probe for an earlier same-name theorem is only reusable when it negates this closed Prop.
    goal = (goal or "").strip()
    if not goal and source_text and target_name:
        try:
            from ztare.leanmill.lean_source import extract_signature as _exsig
            goal = (_exsig(source_text, target_name) or "").strip()
        except Exception:  # noqa: BLE001
            goal = ""
        if not goal:
            return False, "could not recover the target signature from source (empty goal)", ""
    # REUSE-FIRST (the recovery-never-fires fix): before dispatching a FRESH skeptic that may fail to reproduce a
    # complex counterexample (the CLOB/EF1 deadlock), re-verify the agent's OWN sorry-free STATEMENT-FALSE probe —
    # it already PROVED ¬G. Kernel-checked reuse, no re-derivation ⇒ the recovery fires fast. Falls through to the
    # skeptic below when no reusable probe exists (behaviour-preserving for every prior shape).
    _reuse = _reverify_agent_refutation(target_name, lean_root, timeout_s, source_text=source_text, goal=goal)
    if _reuse[0]:
        return _gate(*_reuse)
    # cold-path preamble: the source up to (but excluding) the target decl — the defs/structures the ¬G needs.
    # Match `theorem|lemma|example <name>` (not just `theorem`), so a `lemma`-declared target still gets its
    # prelude on the cold path (the warm campaign env already holds the defs, so this only matters cold).
    preamble = ""
    if source_text and target_name:
        _m = re.search(r"(?m)^\s*(?:noncomputable\s+|private\s+|scoped\s+|@\[[^\]]*\]\s*)*"
                       r"(?:theorem|lemma|example)\s+" + re.escape(target_name) + r"\b", source_text)
        if _m:
            preamble = source_text[:_m.start()].strip()
    # NUGGET reuse (CEGAR): seed the skeptic with the counterexample INSIGHT so it ADAPTS the known crux to OUR
    # goal instead of re-deriving from scratch (the CLOB deadlock: the leaf found a hard ULift counterexample the
    # throwaway fresh skeptic could not reproduce → recovery never fired). Sources, in order: (a) the caller's
    # `nugget` (the CURRENT leaf's own probe insight — breaks the first-confirmation deadlock); (b) the RECYCLED
    # witness from `no_good_store`'s `statement_false` no-good for this exact statement (the CEGIS no-good clause
    # we already persist — reused across attempts/runs). Sound: the skeptic still proves ¬(OUR goal), kernel-checked.
    _seed = (nugget or "").strip()
    if not _seed:
        try:
            from ztare.leanmill.solver.no_good_store import NoGoodStore as _NGS
            from ztare.leanmill.solver.solver_core import OUT_DIR as _OUT
            _seed = (_NGS(_OUT / "solver_lane_no_good_store.jsonl").statement_false_witness(goal) or "").strip()
        except Exception:  # noqa: BLE001 — the nugget is advisory; never block the refutation on a store read
            _seed = ""
    refute_block, fname, gprop, tail = falsify_generate(row, goal, lean_root, timeout_s, preamble=preamble, nugget=_seed)
    if not refute_block:
        return False, f"no ¬G produced (honest non-refutation): {(tail or '')[:160]}", ""
    if _has_sorry(refute_block):
        return False, "skeptic's ¬G is not sorry-free (an unproved counterexample is not a refutation)", ""
    # WARM campaign env first (avoid re-starving verify); fall back to the cold genuineness gate.
    try:
        from ztare.formal.repl_compile import (get_campaign_substrate, campaign_file_env,
                                               warm_verify_campaign)
        from ztare.common.timeouts import timeout_s as _budget   # the ONE timeout home (no inline magic numbers)
        _sub = get_campaign_substrate()
        if _sub:
            # env build = a heavy substrate elaboration (use the cold-compile budget); warm probe = the warm-REPL ceiling.
            _env = campaign_file_env(_sub, lean_root, timeout=_budget("cold_compile"))
            if _env is not None:
                _wv = warm_verify_campaign(refute_block, f"{fname}_refute", lean_root,
                                           _budget("warm_repl_ceiling"), env=_env)
                if _wv is not None:
                    ok, diag = _wv
                    return _gate(bool(ok), f"warm-¬G: {diag}", (refute_block if ok else ""))
    except Exception:  # noqa: BLE001 — warm verify is best-effort; fall through to the cold kernel gate
        pass
    genuine, why = falsification_is_genuine(refute_block, fname, gprop, lean_root, timeout_s, preamble=preamble)
    return _gate(bool(genuine), f"cold-¬G: {why}", (refute_block if genuine else ""))


def statement_false_rejection_feedback(claim: str, why: str) -> str:
    """Corrective source-comment guidance fed back to the leaf when its STATEMENT-FALSE claim FAILED kernel
    verification: the negation did not compile, so the target is consistent-with-true — prove it as given, and
    re-check that the proposed counterexample actually satisfies every hypothesis (incl. each structure field)."""
    return ("\n\n-- ⚠ STATEMENT-FALSE claim was NOT kernel-confirmed: " + (why or "¬G did not compile").strip()[:240] +
            "\n-- Your counterexample is " + (claim or "").strip()[:160] +
            "\n-- A real counterexample must satisfy EVERY hypothesis (including each field of any structure the\n"
            "-- statement binds); the skeptic could not prove ¬(goal), so the statement is consistent-with-true.\n"
            "-- PROVE the statement EXACTLY AS GIVEN — do NOT re-flag it STATEMENT-FALSE without a compiling ¬G.\n")


class LeanFalsifier:
    """The Lean-substrate instance of the shared Popper Inverter (common/inversion.py). invert = build
    ¬G (the closed-Prop negation we OWN); specify = ask the leaf for the ¬G proof body (falsify_generate);
    adjudicate = the KERNEL decides (falsification_is_genuine + the anti-laundering organs) — synchronous,
    hard bool. Same mechanics the MOVE_FALSIFY runner uses; this conforms them to the protocol so the
    cognitive-gym Invert leg can dispatch to a real Lean producer (was a sink)."""

    def __init__(self, row: dict, lean_root: Path, timeout_s: int, preamble: str = "",
                 kernel_check=None):
        self.row, self.lean_root, self.timeout_s = row, lean_root, timeout_s
        self.preamble = preamble
        self._kernel_check = kernel_check   # optional (source, exact_target)->(passed, detail)
        self._fname = ""
        self._gprop = ""

    def invert(self, claim, context):
        from ztare.common.inversion import CounterHypothesis
        self._gprop = _closed_goal_prop(claim)
        return CounterHypothesis(statement=(f"¬ ({self._gprop})" if self._gprop else ""),
                                 rationale="negation of the goal's closed Prop (owned, not leaf-written)")

    def specify(self, counter, context):
        from ztare.common.inversion import FalsificationTest
        refute_block, fname, gprop, tail = falsify_generate(
            self.row, claim_of(context), self.lean_root, self.timeout_s, preamble=self.preamble)
        self._fname, self._gprop = fname, gprop
        return FalsificationTest(counter=counter, candidate=refute_block,
                                 pass_when="¬G fails to compile (goal stands)",
                                 fail_when="¬G compiles sorry-free + organs pass (goal is FALSE)",
                                 meta={"fname": fname, "gprop": gprop, "tail": tail})

    def adjudicate(self, test, context):
        from ztare.common.inversion import Verdict
        genuine, why = falsification_is_genuine(
            test.candidate, self._fname, self._gprop, self.lean_root, self.timeout_s, preamble=self.preamble)
        if genuine and self._kernel_check is not None:
            passed, detail = self._kernel_check(
                test.candidate,
                f"{self._fname}_refute",
            )
            if passed is not True:
                return Verdict(falsified=False, arbiter="lean_kernel", witness="",
                               detail=f"anti-laundering organ blocked: {detail}")
        return Verdict(falsified=bool(genuine), arbiter="lean_kernel",
                       witness=(test.candidate if genuine else ""), detail=why)


# ── Consequence-corroboration: the Popper DUAL of falsify (2026-06-07) ─────────────────────────────
# Falsify attacks G DIRECTLY (prove ¬G). Consequence-corroboration tests a CONSEQUENCE K of G:
#   * REFUTE leg (SOUND, kernel-gated, a first-class falsifier): prove `G → K` AND `¬K`; then
#     `¬G := fun hg => hnk (himpl hg)` follows by modus tollens. Often FAR easier than direct ¬G — K can be
#     a decidable instance / numerical corollary even when G is a hard ∀-statement. SOUNDNESS is automatic:
#     if G is TRUE then `G→K` true forces K true, contradicting `¬K`, so one leg CANNOT compile sorry-free —
#     the kernel can never mint a falsifier for a true G. We OWN the `¬G` signature (`_closed_goal_prop`);
#     the leaf supplies only K's Prop + the two proof bodies; the assembled block routes through the SAME
#     `falsification_is_genuine` + anti-laundering gate as MOVE_FALSIFY (zero new soundness surface).
#   * CORROBORATE leg (soft signal + banked lemma): prove K (a verified consequence of G that HOLDS) — never
#     closes G, but raises confidence + banks K as a reusable lemma toward proving G. (v1 emits the refute
#     leg as the kernel outcome; the corroborate leg is surfaced in the tail for the selection prior.)
from ztare.leanmill.solver.prompts import CORROBORATE_PROMPT as _CORROBORATE_PROMPT


def corroborate_generate(row: dict, goal_text: str, lean_root: Path, timeout_s: int,
                         preamble: str = "") -> "tuple[str, str, str, str]":
    """Popper-dual generator: ask the leaf for a CONSEQUENCE K of G + a `G→K` proof + a `¬K` proof, then
    ASSEMBLE the `¬G` refutation block by modus tollens (`fun hg => hnk (himpl hg)`). Returns the SAME tuple
    shape as `falsify_generate` — `(refute_block, fname, gprop, raw_tail)` — so it is a drop-in for the
    `falsification_is_genuine` gate (we OWN the `¬G` signature; the leaf never writes it). ('', fname, gprop,
    err) on failure / no refutable consequence (⇒ no falsifier, never a false 'it's false')."""
    base = re.sub(r"[^A-Za-z0-9_]", "", (row.get("target_theorem_name") or "tgt"))[:24] or "tgt"
    fname = f"cns_{base}"
    gprop = _closed_goal_prop(goal_text)
    if not gprop:
        return "", fname, "", "could not build a closed Prop from the goal signature"
    pre = ("\nPREAMBLE:\n" + preamble.strip() + "\n") if preamble.strip() else ""
    prompt = _CORROBORATE_PROMPT.format(G=gprop, goal=goal_text, pre=pre)
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        raw = default_dispatch(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception as e:  # noqa: BLE001
        return "", fname, gprop, f"dispatch_error: {e!r}"
    refute_block = assemble_consequence_refutation(raw, fname, gprop)
    return refute_block, fname, gprop, (raw or "")[-200:]


def assemble_consequence_refutation(raw: str, fname: str, gprop: str) -> str:
    """Parse the leaf's CONSEQUENCE / IMPLIES / REFUTE blocks and ASSEMBLE the `¬G` refutation by modus
    tollens. PURE (no dispatch/compile) ⇒ unit-testable. Returns '' if any block is missing or carries a
    sorry/admit (an honest non-refutation — never an unsound partial). The composition `fun hg => hnk
    (himpl hg)` is type-correct iff both leg theorems compile; the downstream kernel gate decides that."""
    from ztare.leanmill.solver.agent_output import fenced_block   # canonical (#80/#49); was a shadowing local _fenced def
    kprop = fenced_block(raw, "CONSEQUENCE:", lang="lean")
    implies_body = fenced_block(raw, "IMPLIES:", lang="lean")
    refute_body = fenced_block(raw, "REFUTE:", lang="lean")
    if not kprop or not implies_body or not refute_body:
        return ""   # honest non-refutation (missing a leg)
    blob = kprop + "\n" + implies_body + "\n" + refute_body
    if _has_sorry(blob):
        return ""   # never assemble an unsound partial
    himpl = f"theorem {fname}_himpl : ({gprop}) → ({kprop}) := {implies_body.strip()}"
    hnk = f"theorem {fname}_hnk : ¬ ({kprop}) := {refute_body.strip()}"
    refute = (f"theorem {fname}_refute : ¬ ({gprop}) := "
              f"fun hg => {fname}_hnk ({fname}_himpl hg)")
    return himpl + "\n\n" + hnk + "\n\n" + refute


class LeanConsequenceCorroborator(LeanFalsifier):
    """MOVE_CORROBORATE's Popper inverter — reuses LeanFalsifier's `invert` (own the ¬G signature) and
    `adjudicate` (the SAME `falsification_is_genuine` + organs gate); overrides ONLY `specify` to build the
    ¬G witness via a CONSEQUENCE (`corroborate_generate`) instead of a direct ¬G (`falsify_generate`). So the
    soundness surface is IDENTICAL to falsify; only the route to the witness differs."""

    def specify(self, counter, context):
        from ztare.common.inversion import FalsificationTest
        refute_block, fname, gprop, tail = corroborate_generate(
            self.row, claim_of(context), self.lean_root, self.timeout_s, preamble=self.preamble)
        self._fname, self._gprop = fname, gprop
        return FalsificationTest(counter=counter, candidate=refute_block,
                                 pass_when="¬G-via-consequence fails to compile (goal stands)",
                                 fail_when="¬G-via-consequence compiles sorry-free + organs pass (goal is FALSE)",
                                 meta={"fname": fname, "gprop": gprop, "tail": tail})


def claim_of(context: dict) -> str:
    """The goal text a LeanFalsifier inverts — read from the inversion context (`lean_goal`)."""
    return (context or {}).get("lean_goal", "")


# ── CAPABILITY (M3 v2): TACTIC-STEPPING — per-step agentic search vs a persistent proofState ──────────
# The leaf emits ONE tactic at a time against a PERSISTENT REPL proofState built from OUR decl (the goal +
# preamble) — REACTING to the live goal after each step, the genuinely-non-redundant value over whole-proof
# moves. The ANTI-LAUNDERING INVARIANT: a tactic applied to a fixed proofState CANNOT redefine a depended-on decl (no file write),
# so the file-edit laundering surface is removed by construction. REPL-`closed` is NEVER the verdict — the
# caller REASSEMBLES the accepted sequence and re-verifies it through the SAME governance (_verify_compile +
# kernel + MNC). CALIBRATION-FIRST: a dead/mismatched REPL ⇒ INADMISSIBLE, never a fake negative.
from ztare.leanmill.solver.prompts import TACTIC_STEP_PROMPT as _TACTIC_STEP_PROMPT


def _next_tactic(goal_pp: str, lean_root: Path, timeout_s: int, last_error: str = "") -> str:
    """Ask the leaf for the SINGLE next tactic given the live proof state (reacting per-step). '' if none."""
    err = (f"\nThe previous tactic FAILED: {last_error[:200]} — emit a DIFFERENT tactic." if last_error else "")
    prompt = _TACTIC_STEP_PROMPT.format(goal=goal_pp, err=err)
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        raw = default_dispatch(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception:  # noqa: BLE001
        return ""
    for ln in raw.strip().splitlines():
        s = ln.strip().strip("`").strip()
        if s and not s.startswith("```") and s.lower() != "by":
            return s[3:].strip() if s.lower().startswith("by ") else s
    return ""


def tactic_step_solve(row: dict, lean_root: Path, timeout_s: int, preamble: str = "",
                      max_steps: int = 8, step_retries: int = 1) -> "tuple[str, dict]":
    """Per-step agentic tactic search. Returns (proof_block, info): proof_block = `by\\n  <accepted
    tactics>` IFF the sequence CLOSED at the REPL (the caller MUST still re-verify it through governance —
    REPL-closed is NOT ratified), else ''. CALIBRATION-FIRST: a dead/mismatched substrate ⇒
    ('', {'inadmissible': ...}) — never a fake negative (the 2026-06-01 going-blind RCA)."""
    from ztare.formal.lean_persistent import PersistentLean
    from ztare.formal.substrate_liveness import calibrate, SubstrateDeadError
    stub = (row.get("goal") or "").rstrip()
    if not stub:
        return "", {"error": "no goal"}
    decl = ((preamble.strip() + "\n\n") if preamble.strip() else "") + stub + (
        "\n  sorry" if stub.endswith(":= by") else " := by sorry")
    if not decl.lstrip().startswith("import"):
        decl = "import Mathlib\n\n" + decl
    pl = PersistentLean(project_dir=str(lean_root))
    try:
        try:
            calibrate(pl)   # RAISES SubstrateDeadError on a dead/mismatched REPL (fail-loud)
        except SubstrateDeadError as e:
            return "", {"inadmissible": str(e)[:200]}
        opened = pl.start_tactic_proof(decl, timeout=min(120, timeout_s))
        if not opened.get("ok"):
            return "", {"error": "start_tactic_proof: " + str(opened.get("err"))[:120]}
        ps, goal_pp = opened["ps"], opened.get("goal", "")
        accepted: list[str] = []
        closed, last_err = False, ""
        per_step_to = max(20, timeout_s // max(2, max_steps))
        retries = step_retries
        for _ in range(max_steps):
            tac = _next_tactic(goal_pp, lean_root, per_step_to, last_error=last_err)
            if not tac:
                break
            sr = pl.step(ps, tac, timeout=per_step_to)
            if not sr.get("ok"):
                last_err = sr.get("err", "")
                if retries > 0:
                    retries -= 1
                    continue        # re-prompt with the error (the per-step reaction)
                break
            accepted.append(tac)
            last_err, retries = "", step_retries
            if sr.get("closed"):
                closed = True
                break
            ps, goal_pp = sr.get("ps"), "\n".join(sr.get("goals") or [])
            if ps is None:
                break
        proof_block = ("by\n" + "\n".join("  " + t for t in accepted)) if (closed and accepted) else ""
        return proof_block, {"closed_at_repl": closed, "steps": len(accepted)}
    finally:
        pl.close()


from ztare.leanmill.solver.prompts import GENERALIZE_PROMPT as _GENERALIZE_PROMPT


def generalize_generate(row: dict, goal_text: str, lean_root: Path, timeout_s: int,
                        preamble: str = "") -> "tuple[str, str, str]":
    """Ask the leaf to close the ORIGINAL goal via an internal induction-strengthening (`have` a stronger
    fact, then instantiate). Returns (proof_body, gname, raw_tail) — proof_body is the `by ...` tactic
    block that goes directly after the goal's `:=` and is GOVERNED identically to a direct move (the
    runner runs `_verify_compile` + `_validate_against_contract`). ('', gname, err) on failure."""
    base = re.sub(r"[^A-Za-z0-9_]", "", (row.get("target_theorem_name") or "gen"))[:24] or "gen"
    gname = f"gen_{base}"
    prompt = _GENERALIZE_PROMPT.format(gname=gname, goal=goal_text)
    if preamble.strip():
        prompt += "\nPREAMBLE:\n" + preamble.strip() + "\n"
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        raw = default_dispatch(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception as e:  # noqa: BLE001
        return "", gname, f"dispatch_error: {e!r}"
    from ztare.leanmill.solver.agent_output import fenced_block   # canonical (#80/#49); was a raw PROOF: fence regex
    body = fenced_block(raw, "PROOF:", lang="lean")
    # The body must be a tactic proof the runner folds after the goal's `:= by`. The verifier
    # (`_verify_compile`) only strips a leading `"by "` (with a SPACE) — a `by\n...` body would DOUBLE
    # the `by` and fail every compile. So normalize to the single `"by <tactics>"` form (the same shape
    # native/cold proof_text uses, so it routes through the SAME governance). A `sorry`/`admit` body is
    # dropped to '' (governance would reject it anyway; '' keeps the no-advance accounting honest).
    if body and "sorry" not in body and "admit" not in body:
        mb = re.match(r"^\s*by\b\s*", body)            # strip an existing leading `by` (+ its whitespace)
        body = "by " + (body[mb.end():] if mb else body)
        return body, gname, (raw or "")[-200:]
    return "", gname, (raw or "")[-200:]


from ztare.leanmill.solver.prompts import REVIEW_PROMPT as _REVIEW_PROMPT


def decomposition_review(goal: str, lemma: str, lean_root: Path, timeout_s: int = 90,
                         dispatch_fn=None) -> "tuple[bool, str]":
    """Borrow B (#39, LEAP §5.3 reviewer): a per-edge PRODUCTIVITY filter on a conjectured lemma L —
    is it STRICTLY EASIER than the goal G, NON-circular (not a grandparent restatement), a plausible
    route? Catches the 'subgoal restates the goal' failure that loops decomposition (LEAP ablation:
    2 rollouts with it vs failure-after-8 without). ADVISORY: the kernel + the L⇒G sorry-contract
    (`conjecture_advances`) gate SOUNDNESS; this only PRUNES search. FAIL-OPEN (worthy=True) on any
    dispatch/parse error — a tooling failure must NOT block a sound decomposition. Self-scored LLM
    judgement (monoculture risk) ⇒ ship advisory/default-off, validate with pos/neg controls first."""
    if not (goal and lemma):
        return True, "empty input — fail-open (advisory)"
    prompt = _REVIEW_PROMPT.format(goal=goal[:1500], lemma=lemma[:1500])
    try:
        if dispatch_fn is None:
            from ztare.leanmill.solver.agentic_leaf import default_dispatch as dispatch_fn
        raw = dispatch_fn(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception as e:  # noqa: BLE001
        return True, f"review dispatch error — fail-open (advisory): {e!r}"
    m = re.search(r"\b(NOT_WORTHY|WORTHY)\b", raw)
    if not m:
        return True, "no parseable verdict — fail-open (advisory)"
    worthy = (m.group(1) == "WORTHY")
    tail = raw[m.end():].strip()
    reason = (tail.splitlines()[0][:160] if tail else m.group(1))
    return worthy, reason


def _selftest() -> int:
    """Deterministic (no compile) checks for the two adversary-found fixes in `conjecture_advances`:
    the load-bearing useless-lemma builder + the circularity conclusion-compare."""
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # BUG2: a lemma WITH a binder must NOT split on the binder colon (the old regex did → malformed).
    u = _useless_lemma("theorem conj_x (n : ℕ) : 2 * n = n + n := by sorry")
    ok("useless: binder preserved (not split on '(n :')", "(n : ℕ)" in u and u.endswith(": True := by sorry"))
    ok("useless: implicit+inst binders preserved",
       "{m : ℕ}" in _useless_lemma("theorem c {m : ℕ} [DecidableEq ℕ] : m = m := by sorry"))
    ok("useless: no-binder lemma", _useless_lemma("theorem c : P := by sorry") == "theorem c : True := by sorry")
    # the OLD regex bug, asserted dead: it would have produced an unbalanced "(n : True := by sorry"
    ok("useless: no unbalanced paren (old bug dead)", "(n : True" not in u)

    # GOAL_HEAD: the PROOF exemplar must restate the GOAL theorem, not a helper `abbrev/def := …` that
    # precedes it (CLOB regression: first depth-0 `:=` landed on `abbrev betterPrice`, not the target).
    _blob = ("def betterPrice : Side → Prop\n  | .bid => True\n\n"
             "abbrev betterPrice2 : Prop := True\n\n"
             "theorem tgt : (∀ x ∈ ([] : List Nat), x = x) := by")
    _gh = _goal_head_for_exemplar(_blob)
    ok("goal_head: picks the goal theorem, not the preceding helper `:=`",
       _gh.startswith("theorem tgt") and ":=" not in _gh and "betterPrice" not in _gh)
    ok("goal_head: single-decl unchanged",
       _goal_head_for_exemplar("theorem t (n : ℕ) : P n := by").strip() == "theorem t (n : ℕ) : P n")

    # METRIC: circularity = L's conclusion equals the goal's conclusion (verbatim / α / whitespace).
    ok("conclusion extraction", _lemma_conclusion("theorem c (n : ℕ) : Good n := by sorry") == "Good n")
    goal_concl = "Good n"
    ok("circular: L restates the goal",
       _norm_ws(_lemma_conclusion("theorem conj (n : ℕ) : Good n := by sorry")) == _norm_ws(goal_concl))
    ok("non-circular: a genuine bridge differs",
       _norm_ws(_lemma_conclusion("theorem conj (n : ℕ) : 2 * (∑ i ∈ Finset.range n, i) = n * (n - 1) := by sorry"))
       != _norm_ws(goal_concl))

    # SPECIALIZE (capability B) — pure-logic gate rejections (compile-dependent legs covered by a lake
    # calibration script, like the dag-audit one). The genuineness gate must reject the laundered cases.
    ok("specialize: no special case → reject",
       specialization_is_genuine("", "", "spec_x", "Good n", Path("/tmp"), 5)[0] is False)
    ok("specialize: identical-to-goal → reject (not a specialization)",
       specialization_is_genuine("theorem spec_x : Good n := by rfl", "x", "spec_x", "Good n", Path("/tmp"), 5)[0] is False)
    ok("specialize: sorry in special → reject",
       specialization_is_genuine("theorem spec_x : Good 1 := by sorry", "x", "spec_x", "Good n", Path("/tmp"), 5)[0] is False)
    ok("specialize: vacuous True → reject",
       specialization_is_genuine("theorem spec_x : True := by trivial", "x", "spec_x", "Good n", Path("/tmp"), 5)[0] is False)

    # SUBSTANTIVENESS (cross-field non-degeneracy, Leg 3a — STRUCTURAL parameter retention, no watch-list).
    _goal = "theorem t (n : ℕ) (f : FormalPowerSeries ℚ) (hf : Good f) : Alg f := by"
    ok("substantive: degenerate corner (f dropped → Alg 0) flagged",
       specialization_substantive(_goal, "theorem s : Alg (0 : FormalPowerSeries ℚ) := by rfl")[0] is False)
    ok("substantive: retains the object var f → substantive",
       specialization_substantive(_goal, "theorem s (f : FormalPowerSeries ℚ) (h : Small f) : Alg f := by sorry")[0] is True)
    ok("substantive: const-other-than-0 corner (f→1, NOT in any watch-list) also flagged structurally",
       specialization_substantive(_goal, "theorem s : Alg (1 : FormalPowerSeries ℚ) := by rfl")[0] is False)
    ok("substantive: auxiliary-param fixed (n→3) but object f kept → substantive (no false-reject of base case)",
       specialization_substantive(_goal, "theorem s (f : FormalPowerSeries ℚ) : Alg f := by sorry")[0] is True)

    # FALSIFY (Invert leg) — pure-logic legs (the compile-dependent ¬G typecheck needs the live box, like
    # the specialize lake legs). The statement is OURS by construction, so the genuineness gate only has to
    # reject the obviously-bad refutations; "negate a strawman" is structurally impossible (we assemble the
    # signature, the leaf supplies only the proof body).
    ok("closed-prop: binders → ∀-wrapped",
       _closed_goal_prop("theorem t (n : ℕ) : n = n + 1 := by") == "∀ (n : ℕ), n = n + 1")
    ok("closed-prop: no binders → bare conclusion",
       _closed_goal_prop("theorem t : 2 + 2 = 5 := by") == "2 + 2 = 5")
    ok("closed-prop: literal True/False → '' (degenerate, no falsify)",
       _closed_goal_prop("theorem t : False := by") == "" and _closed_goal_prop("theorem t : True := by") == "")
    ok("falsify: no refutation → reject (honest non-falsification)",
       falsification_is_genuine("", "fls_x", "∀ (n:ℕ), n = n+1", Path("/tmp"), 5)[0] is False)
    ok("falsify: sorry in refutation → reject",
       falsification_is_genuine("theorem fls_x_refute : ¬ (P) := by sorry", "fls_x", "P", Path("/tmp"), 5)[0] is False)
    ok("falsify: degenerate negated Prop → reject",
       falsification_is_genuine("theorem fls_x_refute : ¬ (True) := by trivial", "fls_x", "True", Path("/tmp"), 5)[0] is False)
    # LeanFalsifier conforms to the shared Popper Inverter contract (common.inversion).
    try:
        from ztare.common.inversion import Inverter as _Inv
        ok("LeanFalsifier implements the Inverter protocol",
           isinstance(LeanFalsifier({"target_theorem_name": "t"}, Path("/tmp"), 5), _Inv))
    except Exception as _e:  # noqa: BLE001
        ok(f"LeanFalsifier protocol import ({_e!r})", False)

    # ── Consequence-corroboration (Popper dual): the modus-tollens ASSEMBLY ──────────────────────
    _raw = ("CONSEQUENCE:\n```lean\nP 7\n```\n"
            "IMPLIES:\n```lean\nfun hg => hg 7\n```\n"
            "REFUTE:\n```lean\nby decide\n```\n")
    _rb = assemble_consequence_refutation(_raw, "cns_x", "∀ n, P n")
    ok("corroborate: assembles himpl + hnk + ¬G-by-modus-tollens",
       "cns_x_himpl : (∀ n, P n) → (P 7)" in _rb and "cns_x_hnk : ¬ (P 7)" in _rb
       and "cns_x_refute : ¬ (∀ n, P n) := fun hg => cns_x_hnk (cns_x_himpl hg)" in _rb)
    ok("corroborate: missing REFUTE leg → '' (honest non-refutation)",
       assemble_consequence_refutation("CONSEQUENCE:\n```lean\nP 7\n```\nIMPLIES:\n```lean\nfun hg => hg 7\n```\n",
                                       "cns_x", "∀ n, P n") == "")
    ok("corroborate: sorry in any leg → '' (never assemble an unsound partial)",
       assemble_consequence_refutation(
           "CONSEQUENCE:\n```lean\nP 7\n```\nIMPLIES:\n```lean\nby sorry\n```\nREFUTE:\n```lean\nby decide\n```\n",
           "cns_x", "∀ n, P n") == "")
    # the assembled ¬G is OWNED by us (the leaf never writes the ¬G signature) ⇒ statement-alteration immune,
    # and it routes through the SAME falsification_is_genuine gate (a sorry'd leg is already rejected above).
    ok("corroborate: LeanConsequenceCorroborator IS-A LeanFalsifier (reuses invert+adjudicate gate)",
       issubclass(LeanConsequenceCorroborator, LeanFalsifier))

    # SINGLE-DOOR refutation memo (2026-07-06, gale): the leaf's kernel-confirmed ¬G must reach the epilogue
    # even though the leaf re-forms its goal to ∀-shape while the epilogue reads the base goal. Key on the
    # SIGNATURE recovered from source ⇒ both resolve to the SAME key for the SAME statement.
    import os as _os_st
    _os_st.environ["ZTARE_SOLVER_RUN_TAG"] = "memo_selftest"
    _CONFIRMED_REFUTATIONS.clear()
    _src_st = ("def BlockingPair (m w) : Prop := True\n\n"
               "theorem cap (m w : Nat) (h : P m) : ∀ x, ¬ BlockingPair m x := by sorry")
    _leaf_goal = "∀ (m w : Nat) (h : P m), ∀ x, ¬ BlockingPair m x"   # leaf's ∀-reconstructed form
    _epi_goal = "∀ x, ¬ BlockingPair m x"                             # epilogue's base (post-colon) form
    _remember_refutation("cap", _src_st, _leaf_goal, "theorem cap_cex : ¬ (…) := by decide")
    ok("memo: leaf ∀-goal write is READ under the epilogue's base goal (signature-keyed, not goal-string)",
       confirmed_refutation("cap", _src_st, _epi_goal).startswith("theorem cap_cex"))
    ok("memo: a DIFFERENT (reformulated) statement misses — no stale ¬G reuse",
       confirmed_refutation("cap", _src_st.replace("∀ x, ¬ BlockingPair m x",
                                                   "(hc : ∀ x, x ∈ full m) → ∀ x, ¬ BlockingPair m x"), _epi_goal) == "")
    _os_st.environ["ZTARE_LEANMILL_REFUTATION_MEMO"] = "0"
    ok("memo: kill-switch reverts to re-verify-only ('' regardless of a recorded verdict)",
       confirmed_refutation("cap", _src_st, _epi_goal) == "")
    _os_st.environ.pop("ZTARE_LEANMILL_REFUTATION_MEMO", None)
    _CONFIRMED_REFUTATIONS.clear()
    _os_st.environ.pop("ZTARE_SOLVER_RUN_TAG", None)

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
