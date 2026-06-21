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

import re
from pathlib import Path

# Canonical comment-stripping sorry/admit check (the ONE primitive — never substring-match raw Lean for a
# consequential decision; a `sorry` in a comment/identifier must not false-positive). 2026-06-13 audit.
from ztare.leanmill.lean_source import has_sorry as _has_sorry, strip_comments as _strip_comments, signature_before_proof

_CONJECTURE_PROMPT = (
    "You are a Lean 4 prover reasoning BACKWARD. The goal below is hard to prove directly. INVENT "
    "exactly ONE genuinely-useful intermediate lemma that, if true, makes the goal provable, then "
    "prove the ORIGINAL goal USING it. Self-contained against `import Mathlib`. Output EXACTLY:\n"
    "LEMMA:\n```lean\ntheorem {lname} : <your lemma statement> := by sorry\n```\n"
    "PROOF:\n```lean\n{goal_head} := by\n  <tactics that REFERENCE {lname}>\n```\n"
    "Rules: the lemma must NOT be trivially true; the PROOF must cite `{lname}` and contain NO `sorry`.\n"
    "GOAL:\n{goal}\n"
)


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
    goal_head = signature_before_proof(goal_text or "").strip() or (goal_text or "")
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


def _top_level_colon(sig: str) -> int:
    """Index of the binder/type-separating `:` at bracket depth 0 (binder colons are nested → ignored).
    `sig` is a signature WITHOUT the `:=` body (use statement_integrity._signature first)."""
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩", "⦃": "⦄"}
    closes = set(pairs.values())
    for i, c in enumerate(sig):
        if c in pairs:
            depth += 1
        elif c in closes:
            depth = max(0, depth - 1)
        elif depth == 0 and c == ":":
            return i
    return -1


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
    _pre = (preamble.strip() + "\n\n") if preamble.strip() else ""
    snippet = _pre + lemma.strip() + "\n\n" + proof.strip()
    if not snippet.lstrip().startswith("import"):
        snippet = "import Mathlib\n\n" + snippet
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
        _snip2 = _pre + _useless + "\n\n" + proof.strip()
        if not _snip2.lstrip().startswith("import"):
            _snip2 = "import Mathlib\n\n" + _snip2
        if _compile_probe(_snip2, lean_root, "ConjLoadBearing", timeout_s) is True:
            return False, "conjectured lemma is NOT load-bearing (goal-proof compiles with L:=True — cited but unused)"
    return True, "compiled — goal follows from the conjectured lemma (load-bearing)"


def decomposition_dag_audit(lemmas: "list[str]", chain_proof: str, lnames: "list[str]",
                            lean_root: Path, timeout_s: int, preamble: str = "",
                            goal_conclusion: str = "") -> "tuple[bool, dict]":
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
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    _pre = (preamble.strip() + "\n\n") if preamble.strip() else ""
    body = "\n\n".join(L.strip() for L in lemmas) + "\n\n" + chain_proof.strip()
    snippet = _pre + body
    if not snippet.lstrip().startswith("import"):
        snippet = "import Mathlib\n\n" + snippet
    if _compile_probe(snippet, lean_root, "DagAudit", timeout_s) is not True:
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
    snip2 = _pre + "\n\n".join(useless) + "\n\n" + chain_proof.strip()
    if not snip2.lstrip().startswith("import"):
        snip2 = "import Mathlib\n\n" + snip2
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
_SPECIALIZE_PROMPT = (
    "You are a Lean 4 prover. The GOAL below may be HARD or OPEN — proving it in full may be infeasible. "
    "Do the mathematician's first move: produce a GENUINELY PROVABLE SPECIAL CASE G' — a real INSTANCE "
    "or RESTRICTION of the goal (fix a parameter to a concrete value; restrict to a small case like n=1; "
    "or add ONE simplifying hypothesis) that is STRICTLY EASIER but NOT vacuous (NOT `True`, not trivially "
    "satisfiable) — then PROVE G' COMPLETELY (NO sorry). G' must be a logical CONSEQUENCE of the original "
    "goal.\n"
    "CRITICAL — make it SUBSTANTIVE, not the TRIVIAL/DEGENERATE CORNER: do NOT set the main object to a "
    "trivial element (0, ∅, the empty/zero/identity/constant case) — that makes the goal's hypotheses "
    "VACUOUSLY true and the result shallow (the analogue of the u≡0 solution of a PDE, the all-zeros SAT "
    "witness, the degenerate fiber). The goal's CHARACTERISTIC HYPOTHESES must remain NON-VACUOUSLY in "
    "force — pick a genuinely easier but still MEANINGFUL instance (a specific NON-trivial parameter value, "
    "a non-empty restricted subclass) where the hard hypotheses still do real work. Output EXACTLY:\n"
    "SPECIAL:\n```lean\ntheorem {sname} : <the special-case statement> := by\n  <full proof, NO sorry>\n```\n"
    "IMPLIES:\n```lean\ntheorem {sname}_from_general (hG : <the original goal's conclusion>) : "
    "<the special case's conclusion> := by\n  <short proof deriving the special case FROM the general goal>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. Both theorems must be sorry-free.\n"
    "{ban}ORIGINAL GOAL to specialize FROM:\n{goal}\n"
)


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
    _pre = (preamble.strip() + "\n\n") if preamble.strip() else ""
    g_concl = _lemma_conclusion(special_block)
    if not g_concl:
        return False, "could not parse the special case's conclusion"
    if goal_conclusion and _norm_ws(g_concl) == _norm_ws(goal_conclusion):
        return False, "special case is IDENTICAL to the goal (not a specialization)"
    if _norm_ws(g_concl) in ("True", "(True)"):
        return False, "special case is vacuous (`True`)"
    # (a) G' closes sorry-free
    snip = _pre + special_block.strip()
    if not snip.lstrip().startswith("import"):
        snip = "import Mathlib\n\n" + snip
    if _compile_probe(snip, lean_root, "SpecClose", timeout_s) is not True:
        return False, "special case does NOT compile sorry-free (not a genuine closed instance)"
    # (b) G ⇒ G' : the implication must typecheck sorry-free (so G' is a genuine consequence of G)
    if not implies_block or _has_sorry(implies_block):
        return False, "missing/incomplete `G ⇒ G'` implication — cannot confirm G' is a genuine special case of G"
    snip2 = _pre + implies_block.strip()
    if not snip2.lstrip().startswith("import"):
        snip2 = "import Mathlib\n\n" + snip2
    if _compile_probe(snip2, lean_root, "SpecImplies", timeout_s) is not True:
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


_FALSIFY_PROMPT = (
    "You are a Lean 4 prover acting as a SKEPTIC (Popper inversion). The statement below is CONJECTURED "
    "and MIGHT BE FALSE. Your job is to try to REFUTE it: prove its NEGATION. Do not be diplomatic — if "
    "the statement is false, exhibit the disproof; if you cannot, say so.\n"
    "The refutation theorem's SIGNATURE is FIXED for you (you do NOT write it):\n"
    "    theorem {fname}_refute : ¬ ({gprop}) := <your proof>\n"
    "Typically: for a ∀-statement, supply a concrete COUNTEREXAMPLE witness and prove the predicate fails "
    "on it (`by intro h; ...`, `by push_neg`, `by simp`, `by omega`, `by decide`, or a proof TERM like "
    "`fun h => absurd (h 0) (by decide)`). Output EXACTLY:\n"
    "HELPERS:\n```lean\n<optional sorry-free helper lemmas/defs, or leave the block empty>\n```\n"
    "PROOF:\n```lean\n<the COMPLETE proof that goes after `:=` — a `by` tactic block OR a proof term; "
    "NO `theorem` line, NO sorry>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. If you genuinely cannot refute it, output an "
    "empty PROOF block (an honest non-refutation, NOT a sorry).\n"
    "{pre}CONJECTURED statement to REFUTE:\n{goal}\n"
)


def falsify_generate(row: dict, goal_text: str, lean_root: Path, timeout_s: int,
                     preamble: str = "") -> "tuple[str, str, str, str]":
    """Ask the leaf for a proof of ¬G (a falsifying witness). Returns (refute_block, fname, gprop,
    raw_tail) where refute_block is the FULLY-ASSEMBLED `[helpers]\\n\\ntheorem <fname>_refute : ¬ (G)
    := by <body>` (statement owned by US, not the leaf). ('', fname, gprop, err) on failure / no
    refutation (⇒ no falsifier, never a false 'it's false')."""
    base = re.sub(r"[^A-Za-z0-9_]", "", (row.get("target_theorem_name") or "tgt"))[:24] or "tgt"
    fname = f"fls_{base}"
    gprop = _closed_goal_prop(goal_text)
    if not gprop:
        return "", fname, "", "could not build a closed Prop from the goal signature"
    pre = ("\nPREAMBLE:\n" + preamble.strip() + "\n") if preamble.strip() else ""
    prompt = _FALSIFY_PROMPT.format(fname=fname, gprop=gprop, goal=goal_text, pre=pre)
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
    _pre = (preamble.strip() + "\n\n") if preamble.strip() else ""
    snip = _pre + refute_block.strip()
    if not snip.lstrip().startswith("import"):
        snip = "import Mathlib\n\n" + snip
    if _compile_probe(snip, lean_root, "FalsifyRefute", timeout_s) is not True:
        return False, "¬G does NOT compile sorry-free — not a genuine refutation"
    return True, "genuine falsifier — a kernel-checked sorry-free proof of ¬(the verbatim goal Prop)"


def verify_statement_false_claim(target_name: str, source_text: str, goal: str,
                                 lean_root: Path, timeout_s: int) -> "tuple[bool, str, str]":
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
    # GOAL RECOVERY: the decomposition path (`solve_decomposition`) calls `solve_adhoc(lname, src, "")` with an
    # EMPTY goal — the statement lives only in `source_text`. Without this, `falsify_generate` would build ¬G
    # from "" and bail, so a confirmed-false PLANNER sub-lemma (iso_lemma1: the bare ∀ that DROPPED the parent's
    # denominator-unit hypothesis) would never verify. Recover the verbatim signature for the named target.
    goal = (goal or "").strip()
    if not goal and source_text and target_name:
        try:
            from ztare.leanmill.lean_source import extract_signature as _exsig
            goal = (_exsig(source_text, target_name) or "").strip()
        except Exception:  # noqa: BLE001
            goal = ""
        if not goal:
            return False, "could not recover the target signature from source (empty goal)", ""
    # cold-path preamble: the source up to (but excluding) the target decl — the defs/structures the ¬G needs.
    # Match `theorem|lemma|example <name>` (not just `theorem`), so a `lemma`-declared target still gets its
    # prelude on the cold path (the warm campaign env already holds the defs, so this only matters cold).
    preamble = ""
    if source_text and target_name:
        _m = re.search(r"(?m)^\s*(?:noncomputable\s+|private\s+|scoped\s+|@\[[^\]]*\]\s*)*"
                       r"(?:theorem|lemma|example)\s+" + re.escape(target_name) + r"\b", source_text)
        if _m:
            preamble = source_text[:_m.start()].strip()
    refute_block, fname, gprop, tail = falsify_generate(row, goal, lean_root, timeout_s, preamble=preamble)
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
                    return bool(ok), f"warm-¬G: {diag}", (refute_block if ok else "")
    except Exception:  # noqa: BLE001 — warm verify is best-effort; fall through to the cold kernel gate
        pass
    genuine, why = falsification_is_genuine(refute_block, fname, gprop, lean_root, timeout_s, preamble=preamble)
    return bool(genuine), f"cold-¬G: {why}", (refute_block if genuine else "")


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
        self._kernel_check = kernel_check   # optional (refute_source)->(passed, detail); runner injects organs
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
            passed, detail = self._kernel_check(test.candidate)
            if not passed:
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
_CORROBORATE_PROMPT = (
    "You are a Lean 4 prover acting as a SKEPTIC (Popper inversion via a CONSEQUENCE). The statement G below "
    "is CONJECTURED and MIGHT BE FALSE. Instead of refuting G directly, find a CONSEQUENCE K of G that is "
    "EASIER to decide — typically a concrete INSTANCE or a decidable corollary — and try to REFUTE that "
    "consequence. If `G → K` holds and `¬K` holds, then G is false (modus tollens).\n"
    "Choose K so that: (1) `G → K` is EASY to prove (K is a weakening/instance of G — apply G to a specific "
    "witness, project a conjunct, etc.), and (2) `¬K` is provable (K is a decidably/constructively FALSE "
    "consequence — e.g. evaluate at a counterexample with `by decide`/`by omega`/`by simp`).\n"
    "Output EXACTLY:\n"
    "CONSEQUENCE:\n```lean\n<the Prop K — JUST the type expression, e.g. `P 7` or `∀ n, n ≤ f n`; it may "
    "reference G's binders>\n```\n"
    "IMPLIES:\n```lean\n<the proof body after `:=` for `({G}) → (K)` — a `by` block or a term; NO theorem "
    "line, NO sorry>\n```\n"
    "REFUTE:\n```lean\n<the proof body after `:=` for `¬ (K)` — a `by` block or a term; NO sorry>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. If you cannot find a refutable consequence, "
    "output an empty REFUTE block (an honest non-refutation, NOT a sorry).\n"
    "{pre}CONJECTURED statement G:\n{goal}\n"
)


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
_TACTIC_STEP_PROMPT = (
    "You are proving a Lean 4 goal ONE TACTIC AT A TIME. Below is the CURRENT proof state (hypotheses and "
    "the goal remaining after the tactics applied so far). Emit the SINGLE next tactic that makes the most "
    "progress — JUST the tactic on one line: NO `by`, NO commentary, NO code fences. If the goal closes in "
    "one step, emit that closing tactic.{err}\n\nCURRENT PROOF STATE:\n{goal}\n"
)


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


_GENERALIZE_PROMPT = (
    "You are a Lean 4 prover. The GOAL below is hard, likely because it is TOO SPECIFIC — proving it "
    "directly gives no inductive leverage. Use the INDUCTION-STRENGTHENING move: inside the proof, first "
    "establish a STRONGER, more general fact G' (via `have`/`suffices`) that is EASIER to prove because "
    "the stronger statement yields a stronger inductive hypothesis; then close the ORIGINAL goal as an "
    "INSTANCE of G'. Output EXACTLY one fenced block — the COMPLETE proof of the original goal AS STATED "
    "(do NOT change its statement), NO sorry, NO admit:\n"
    "PROOF:\n```lean\nby\n  -- strengthen: have {gname} : <stronger statement> := by <proof of the stronger fact>\n"
    "  -- then close the original goal from {gname}\n  <full tactic proof, NO sorry>\n```\n"
    "The proof body must be self-contained against `import Mathlib` + the PREAMBLE and must fit directly "
    "after the goal's `:=`.\nORIGINAL GOAL (prove EXACTLY this, do not weaken or restate):\n{goal}\n"
)


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


_REVIEW_PROMPT = (
    "You are reviewing a proposed proof DECOMPOSITION. The MAIN goal G is:\n{goal}\n\n"
    "A prover proposes proving G via this intermediate lemma L:\n{lemma}\n\n"
    "Judge whether L is a GOOD decomposition. YES only if ALL hold: (1) L is STRICTLY EASIER than G "
    "(a genuine reduction, not the same difficulty); (2) L is NOT a restatement of G or a trivial "
    "rephrasing (non-circular); (3) proving L plausibly makes G follow. Answer with EXACTLY one token "
    "on the first line: WORTHY or NOT_WORTHY, then a one-line reason."
)


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

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
