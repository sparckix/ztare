"""Agent-callable MOVE TOOLS — the leanmill moves exposed as a CLI the proving AGENT invokes itself,
instead of a hand-wired router scheduling them (the autoresearch pattern: the agent orchestrates exogenous
compute, cf. its generated `test_model.py` run via common/sandboxed_python). The agent (running in
workspace-write) calls e.g. `python -m ztare.leanmill.agent_tools witness "<goal>"`, reads the witness/
premise/lemmas, and splices it into its Lean proof — which the KERNEL still independently verifies (the
governance is unchanged; this only changes WHO decides which move fires: the agent's judgment, not a regex
router that starves the moves).

These are THIN wrappers over the canonical move functions (extend, don't fork):
  • witness  → witness_transport.solve_witness  (SymPy: Pell / linear-system / counterexample witnesses —
               the genuinely-LLM-impossible niche, e.g. Pell x=1766319049)
  • abduct   → abduction.route_abduction        (z3 quantifier-elimination most-general missing premise;
               fail-closed abort on nonlinear)
  • hammer   → sledgehammer.{lean_to_isabelle,run_sledgehammer}  (Isabelle premise selection; needs server)
  • verify   → sledgehammer.verify_isabelle  (Isabelle FULL-THEORY check — an independent-substrate accept/
               reject for cross-substrate consensus, NOT a Lean closure; needs server)
  • groebner → common.groebner_cert  (multivariate polynomial EQUALITY from equation hypotheses → an exact
               `linear_combination` cofactor certificate, the kernel discharges by ring)
  • nlsat    → common.nlsat_oracle   (z3 nlsat DECISION of a nonlinear-real ∀ — advisory VALID/counterexample,
               routes the prover effort; the certificate for a `0 ≤ p` shape is the `sos` tool)
  • certify  → solver.certified_faithfulness  (during FORMALIZATION: certify a boolean policy/spec candidate is
               faithful to a trusted reference over the whole integer domain → CERTIFIED_EQUIVALENT / REFUTED
               with a concrete distinguishing input / OUT_OF_FRAGMENT — an artifact, never an opinion)

These are the EXOGENOUS-COMPUTE tools (help PROVE the current goal). The recursive STRATEGY layer (decompose a
hard goal into sub-lemmas → kernel-audit the plan → prove each recursively → composite-ratify) is NOT a tool here:
it already exists as `isomorphism_decompose.route_and_solve` (the warm leaf generates the plan, the kernel audits
it, the apparatus solves the sub-lemmas recursively). It fires automatically inside the governed solver — see
`solver_core` (ZTARE_LEANMILL_ISO_ROUTE). Do NOT add a decompose tool here — that would fork a 4th decomposition
path; route through the canonical recursive planner instead.

Usage:  python -m ztare.leanmill.agent_tools <witness|abduct|hammer> "<lean goal or theorem text>"
Output is plain text for the agent to read; exit 0 if a result was produced, 1 if the tool found nothing
(an honest 'no result' — the agent should fall back to writing the proof directly).
"""
from __future__ import annotations

import dataclasses
import os
import sys


def _normalize_goal(g: str) -> str:
    """The agent naturally passes a BARE goal (`∃ x y, …` / `x ≤ z`); the canonical parsers
    (witness_transport / abduction / sledgehammer) expect a theorem-WRAPPED statement
    (`theorem t : <goal> := by sorry`). Wrap a bare goal — otherwise the tool returns a FALSE 'NONE' on the
    agent's own input and it hand-rolls its own solver (the D=4093 bug). Decl detection REUSES the canonical
    `lean_source.theorem_names` (no bespoke regex); the wrap template matches `_probe_text`/`compile_stub`."""
    s = (g or "").strip()
    try:
        from ztare.leanmill import lean_source as _ls
        if _ls.theorem_names(s):   # already a theorem/lemma declaration → use as-is
            return s
    except Exception:  # noqa: BLE001 — detection is best-effort; default to wrapping
        pass
    return f"theorem _agent_goal : {s} := by sorry"


def _tool_falsity(goal: str) -> int:
    """FALSITY SCREEN (#114) — is this ∀-goal computably FALSE? Stage 1: invariant mismatch (degree/parity/
    growth of the two sides, ~ms — the conservation-law check); stage 2: bounded SymPy counterexample search
    (~8s). ADVISORY: a hit means STOP trying to prove this sub-goal (it is false as stated — fix the statement
    or route to falsify); the kernel-proved ¬G remains the only refutation verdict."""
    from ztare.leanmill.solver.witness_transport import looks_false
    sig = looks_false(_normalize_goal(goal))
    if sig is None:
        print("falsity: NO SIGNAL (no invariant mismatch, no counterexample in the search box — the goal is "
              "consistent with being true; this is NOT a proof). Proceed to prove.")
        return 1
    print(f"falsity: LIKELY FALSE — {sig}")
    print("Do NOT keep trying to prove this sub-goal as stated: fix the statement (a wrong sign/bound/side), "
          "or declare `-- STATEMENT-FALSE`, or route it to the falsify move (kernel-proves the negation).")
    return 0


def _tool_sos(poly: str) -> int:
    """Sum-of-squares certificate (#114 + edge #2) for a polynomial nonnegativity goal (`0 ≤ p` / `p ≥ 0`,
    degree ≥ 4 — nlinarith auto-handles ≤ 2 alone). Pass the POLYNOMIAL expression (sympy syntax). UNIVARIATE
    (variable x) gets an EXACT closed-form decomposition; MULTIVARIATE falls through to the SDP path (numerical
    → rounded `sq_nonneg` HINTS, heuristic — needs cvxpy, provisioned on the Isabelle/solver node). Prints a
    VERBATIM nlinarith call carrying the squares as hints — copy exactly; the kernel re-verifies. A NOT-PSD
    verdict is a falsity signal."""
    from ztare.common.sos_certificate import (sos_certificate, sos_certificate_multivariate,
                                              render_verbatim_lean)
    cert = sos_certificate(poly)
    multivariate = False
    if cert is None:
        cert = sos_certificate_multivariate(poly)   # edge #2: SDP path for the multivariate regime
        multivariate = bool(cert)
    if cert is None:
        print("sos: NONE (non-polynomial / not SOS / out of scope — multivariate needs cvxpy on this node, or "
              "the polynomial is nonnegative-but-not-SOS like Motzkin). Write the proof directly.")
        return 1
    if not cert.get("psd"):
        print(f"sos: NOT NONNEGATIVE — {cert.get('witness_hint')}. The goal as stated is FALSE: "
              "fix the statement or route to falsify; do NOT keep trying to prove it.")
        return 0
    v = render_verbatim_lean(cert)
    if not v:
        print("sos: PSD but no non-trivial hints. Try `nlinarith` / `positivity` directly.")
        return 1
    if multivariate:
        print(f"sos: multivariate SDP certificate — {cert['n_squares']} square hint(s), recon_err="
              f"{cert.get('recon_err'):.2e} (HEURISTIC hints; the kernel's nlinarith re-verifies — a miss is "
              "harmless, never a false closure).")
    else:
        print("sos: exact certificate found — p = " + " + ".join(f"{w}*({q})^2" for w, q in cert["terms"]))
    print(v)
    return 0


def _tool_groebner(arg: str) -> int:
    """Gröbner-basis ideal-membership certificate (edge #3) → a Lean `linear_combination`. Use when a
    MULTIVARIATE polynomial EQUALITY follows from polynomial-equation HYPOTHESES (what `linarith` can't do and
    `polyrith` does only via a flaky Sage round-trip). FORMAT: `hyp0 ; hyp1 ; … ⊢ goal` (turnstile `⊢` or
    `|-`), each hyp/goal an equation `lhs = rhs`. SymPy computes the exact cofactors; copy the VERBATIM
    `linear_combination` — the kernel discharges it by `ring`. The emitted tactic names the hypotheses
    h0,h1,… (in the order you passed them); have them in context under those names or rename to match."""
    from ztare.common.groebner_cert import groebner_certificate, render_verbatim_lean
    s = (arg or "").strip()
    turn = "⊢" if "⊢" in s else ("|-" if "|-" in s else None)
    if not turn:
        print("groebner: NONE — need hypotheses. FORMAT: `a = b ; c = d ⊢ goal_lhs = goal_rhs`. A goal with "
              "NO hypotheses is a pure ring identity — use `ring` instead.")
        return 1
    hyp_str, _, goal = s.partition(turn)
    hyps = [h.strip() for h in hyp_str.split(";") if h.strip()]
    cert = groebner_certificate(hyps, goal.strip())
    if cert is None:
        print("groebner: NONE (goal not in the ideal generated by the hypotheses, by exact division — or "
              "non-polynomial / not an equation). The goal may not follow algebraically; check it, or it needs "
              "the full Gröbner cofactor lift (out of v1 scope). Write the proof directly.")
        return 1
    print(f"groebner: cofactor certificate found over {cert['hyp_count']} hypothesis/-es (names "
          f"{cert['names']}). COPY THE BLOCK VERBATIM as the proof (the kernel re-verifies by ring):")
    print(render_verbatim_lean(cert))
    return 0


def _tool_certify(arg: str) -> int:
    """CERTIFY FAITHFULNESS of a candidate policy/spec formalization against a TRUSTED reference, over the WHOLE
    integer domain — a checkable ARTIFACT, never an opinion. Use during FORMALIZATION when you must confirm a
    boolean policy rule (compliance/access/finance) you wrote means the SAME as the intent, or find where it
    differs. FORMAT: `<intent> ⊢ <candidate> @ attr0:int, attr1:int, …` (turnstile `⊢` or `|-`; rules in z3
    syntax And/Or/Not/==/>=/>/<=/<). Returns CERTIFIED_EQUIVALENT (equal on every input — z3 exhaustive),
    REFUTED (a CONCRETE distinguishing input you can re-check), or OUT_OF_FRAGMENT (undecided ⇒ fall back to the
    battery+judge; never a silent pass). z3 is complete for linear-integer policy, so a verdict is a decision."""
    from ztare.leanmill.solver.certified_faithfulness import policy_faithfulness_consensus, Verdict
    s = (arg or "").strip()
    rules, _, dom_part = s.partition("@")
    turn = "⊢" if "⊢" in rules else ("|-" if "|-" in rules else None)
    if not turn or "@" not in s:
        print("certify: NEED `<intent> ⊢ <candidate> @ attr0:int, attr1:int`. The `@` clause declares the "
              "domain attributes (each `name:int`). Example: `Or(a>=18, vip==1) ⊢ Or(a>18, vip==1) @ a:int, vip:int`.")
        return 1
    intent, _, candidate = rules.partition(turn)
    domain = {}
    for part in dom_part.split(","):
        if ":" in part:
            k, _, v = part.partition(":")
            if k.strip():
                domain[k.strip()] = (v.strip() or "int")
    if not domain:
        print("certify: NONE — the `@` clause declared no attributes. FORMAT: `… @ age:int, balance:int`.")
        return 1
    # Cross-substrate consensus (default-on): corroborate the z3 verdict with an INDEPENDENT Lean omega decision
    # on the same claim, and record any z3⨉Lean conflict. The Lean leg is naturally gated by the warm-verify
    # toolchain (compile_probe_via_repl returns None when it is unavailable), so this degrades to the z3-only
    # verdict where Lean is not live — no uncontrolled compile cost, no behaviour change on a Lean-less node.
    from pathlib import Path as _P
    _repo = _P(__file__).resolve().parents[3]

    def _lc(probe: str) -> bool:
        try:
            from ztare.formal.repl_compile import compile_probe_via_repl
            r = compile_probe_via_repl(probe, _repo / "ztare_proofs", timeout=120, reject_sorry=True)
            return bool(r and r[0])
        except Exception:  # noqa: BLE001 — toolchain absent ⇒ no Lean leg (dead-instrument guard handles it)
            return False
    _store = None
    try:
        from ztare.leanmill.solver.faithfulness_store import FaithfulnessStore
        _store = FaithfulnessStore(_repo / "analytics/public/queries/solver_lane_faithfulness_store.jsonl")
    except Exception:  # noqa: BLE001
        _store = None
    consensus, cert = policy_faithfulness_consensus(
        intent.strip(), candidate.strip(), domain,
        claim_nl=f"{intent.strip()} ⊢ {candidate.strip()}",
        lean_compile=_lc, record_conflict=(_store.record_conflict if _store else None))
    if consensus.n_substrates >= 2:
        print(f"certify: cross-substrate consensus = {consensus.status.upper()} (z3 ⨉ Lean-omega) — {consensus.reason}")
    if cert.verdict is Verdict.CERTIFIED_EQUIVALENT:
        print(f"certify: CERTIFIED_EQUIVALENT — the candidate is faithful on EVERY input ({cert.certificate}). "
              "The formalization preserves the intent; proceed.")
        return 0
    if cert.verdict is Verdict.REFUTED:
        w = cert.witness or {}
        print(f"certify: REFUTED — a concrete input distinguishes them: {w.get('request')} "
              f"(intent decides {w.get('intent_decides')}, candidate decides {w.get('candidate_decides')}). "
              "Re-check this case by hand; the candidate is NOT faithful — fix it.")
        return 0
    print(f"certify: OUT_OF_FRAGMENT — undecided in the decision procedure ({cert.detail}). "
          "Fall back to the instance battery + round-trip judge; do NOT treat as faithful.")
    return 1


def _tool_nlsat(goal: str) -> int:
    """Nonlinear REAL-arithmetic DECISION via z3 nlsat (edge #1 — Tarski real-closed-field QE, decidable where
    `nlinarith` is incomplete). Pass a goal `∀ x…, φ` over ℝ/ℤ (polynomial (in)equalities, &/|/¬/→). ADVISORY,
    not a proof: VALID = the goal is TRUE (keep proving it — route a `0 ≤ p` shape to the `sos` tool for a
    kernel-checkable certificate); INVALID = a COUNTEREXAMPLE (false as written → fix it or route to falsify).
    A z3 'unknown' / untranslatable goal prints NONE."""
    from ztare.common.nlsat_oracle import nlsat_decide
    res = nlsat_decide(goal)
    if res is None:
        print("nlsat: NONE (z3 could not decide it, or the goal is outside the polynomial-real fragment — "
              "transcendental / set-valued / unmodelled binder). This is NOT a proof either way; proceed.")
        return 1
    if res.get("valid"):
        print("nlsat: VALID — the goal is TRUE over the reals (z3 nlsat decided ¬goal UNSAT). This is a "
              "DECISION, not a Lean proof: keep proving it. If it is a polynomial `0 ≤ p`, call the `sos` tool "
              "for a kernel-checkable nlinarith certificate.")
        return 0
    cex = res.get("counterexample", {})
    print(f"nlsat: INVALID — the goal is FALSE over the reals. Counterexample: {cex}. Do NOT keep trying to "
          "prove it: fix the statement (a wrong sign/bound/side), or route to the falsify move (kernel-proves "
          "the negation).")
    return 0


def _tool_witness(goal: str) -> int:
    """SymPy exogenous witness for a computable existential (Pell / linear system / single equation)."""
    os.environ.setdefault("ZTARE_LEANMILL_KRONECKER", "1")  # enable the Pell + linear-system routes
    from ztare.leanmill.solver.witness_transport import solve_witness
    res = solve_witness(_normalize_goal(goal), dispatch=None)   # normalize: the agent passes a BARE goal
    if not res:
        print("witness: NONE (goal is not a computable existential, or no witness found). "
              "Write the proof directly.")
        return 1
    tac, meta = res
    print(f"witness: FOUND via path={meta.get('path')}  witnesses={meta.get('witnesses')}")
    # VERBATIM CONTRACT (the Bash-execution trap): the big-integer witness must reach the kernel UNALTERED.
    # If you paraphrase/reformat/add coercions, Lean rejects it and the tool looks broken. Copy EXACTLY.
    print("COPY THE BLOCK BETWEEN THE MARKERS VERBATIM AS THE PROOF — do NOT reformat, paraphrase, reorder, "
          "or add type coercions; the kernel rejects ANY alteration of the witness digits.")
    print("===VERBATIM-LEAN-BEGIN===")
    print(tac)
    print("===VERBATIM-LEAN-END===")
    return 0


def _tool_abduct(goal: str) -> int:
    """z3 quantifier-elimination most-general missing premise (Dillig 'Explain')."""
    from ztare.leanmill.solver.abduction import route_abduction, classify_abduction_route
    goal = _normalize_goal(goal)   # the agent passes a BARE goal; the parser expects theorem-wrapped
    lane = classify_abduction_route(goal)
    seed = route_abduction(goal)
    if not seed:
        print(f"abduct: NONE (route={lane}; nonlinear→fail-closed abort, or no premise). "
              "Write the proof directly.")
        return 1
    payload = dataclasses.asdict(seed) if dataclasses.is_dataclass(seed) else {"seed": str(seed)}
    print(f"abduct: FOUND missing premise via route={lane}")
    for k, v in payload.items():
        if v:
            print(f"  {k} = {v}")
    return 0


def _tool_hammer(goal: str) -> int:
    """Isabelle Sledgehammer premise selection (heavyweight — needs the Isabelle server running)."""
    from ztare.leanmill.solver.sledgehammer import lean_to_isabelle, run_sledgehammer
    theory, name, statement, imports = lean_to_isabelle(_normalize_goal(goal))
    try:
        out = run_sledgehammer(theory, statement=statement, imports=imports)
    except Exception as e:  # noqa: BLE001 — the server may be down; that's an honest 'no result'
        print(f"hammer: server unavailable ({str(e)[:120]}). Write the proof directly.")
        return 1
    if not out:
        print("hammer: NONE (no proof found by Sledgehammer). Write the proof directly.")
        return 1
    print(f"hammer: Sledgehammer suggestion(s):\n{out}")
    return 0


def _tool_verify(theory: str) -> int:
    """Independent Isabelle full-theory VERIFICATION (#73 cross-substrate move). The `hammer` tool above uses
    Isabelle to FIND premises; THIS submits a COMPLETE Isabelle theory (`lemma … <proof>`) and asks whether
    Isabelle ACCEPTS it — the Isabelle analog of the Lean kernel re-verify, on a SEPARATE substrate (different
    logic, different kernel). Use it to CROSS-CHECK: when `hammer` hands you an Isar/one-liner proof, or when
    a sub-claim falls to Isabelle's automation (`by auto`/`by simp`/`by (metis …)`), `verify` gives an
    INDEPENDENT verdict you can feed to cross-substrate consensus / corroboration.

    GOLDILOCKS / soundness: an Isabelle ACCEPT is NOT a Lean closure — the Lean kernel still needs the Lean
    proof; this is a peer-substrate signal, never a bypass (verify_isabelle re-parses the session output and
    fail-closes on sorry/oops/errors, so it can't mint a false pass)."""
    from ztare.leanmill.solver.sledgehammer import verify_isabelle, ISABELLE_IMPORTS
    s = (theory or "").strip()
    if not s:
        print("verify: NONE (no theory text). Pass a complete Isabelle theory, or a bare `lemma name: \"…\" "
              "<proof>` and I'll wrap it (imports + begin/end).")
        return 1
    # Accept a complete theory as-is; otherwise wrap a bare `lemma …` so the agent need not hand-write the
    # theory/imports/begin/end boilerplate. `begin` (theory keyword) is the unambiguous "this is a full
    # theory" signal — a bare lemma never contains it. No regex on Isabelle source needed for this.
    if s.lstrip().startswith("theory") and "begin" in s:
        thy = s
    else:
        thy = f"theory ZtareVerify\nimports {ISABELLE_IMPORTS}\nbegin\n\n{s}\n\nend\n"
    ok, diag = verify_isabelle(thy)
    if ok:
        print("verify: ACCEPTED by Isabelle (independent substrate) — " + (diag or "")[:400])
        print("NOTE: this is a CROSS-SUBSTRATE corroboration signal, NOT a Lean closure. You still owe the "
              "Lean kernel the Lean proof; use this to confirm a sub-claim is true or to feed consensus.")
        return 0
    print("verify: REJECTED / unavailable — " + (diag or "")[:500])
    print("(Isabelle did not accept the theory: fix the Isar proof, or the server is down — write the Lean "
          "proof directly. A bare statement with no proof is correctly rejected.)")
    return 1


def loogle_search_text(query: str, max_hits: int = 8) -> str:
    """THE canonical Loogle Mathlib-search primitive, returning a text result (one home for the HTTP + format).
    Both the CLI tool (`_tool_search`, prints it) and the API agentic leaf (`api_agentic_leaf._mathlib_search`,
    returns it) call this — no re-rolled Loogle endpoint. Query forms: a name (`Polynomial.roots`), a pattern
    (`Polynomial.Splits ?f ?p`), or a type. Returns an honest `NONE`/`unreachable` line on no match / 5xx."""
    import json
    import urllib.parse
    import urllib.request
    url = "https://loogle.lean-lang.org/json?q=" + urllib.parse.quote(query)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:  # noqa: S310 — fixed trusted host
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 — offline / 5xx ⇒ honest NONE, never crash
        return f"search: NONE (Loogle unreachable: {str(e)[:120]}). Reason from the lemmas you know."
    hits = data.get("hits") or []
    if not hits:
        return (f"search: NONE — {str(data.get('header', 'no match'))[:200]}. The name/pattern may not exist; "
                "do NOT invent it — restructure or use a lemma you can confirm.")
    lines = [f"search: {data.get('count', len(hits))} Mathlib declarations match `{query}` (top "
             f"{min(max_hits, len(hits))}; use the EXACT name):"]
    for h in hits[:max_hits]:
        name = h.get("name") or "?"
        typ = " ".join(str(h.get("type") or "").split())[:160]
        lines.append(f"  • {name}" + (f" : {typ}" if typ else ""))
    return "\n".join(lines)


def _tool_search(query: str) -> int:
    """Mathlib lemma SEARCH via Loogle (the 'essential' API-discovery tool the prompt advertises but that was
    NEVER implemented — a dead advert). Returns the REAL matching Mathlib declarations + signatures so the agent
    uses an EXISTING name instead of GUESSING a non-existent one — the firewall RCA was formalizations failing to
    typecheck on invented names (`RatFunc`/residue/partial-fraction). Delegates to the canonical
    `loogle_search_text` (shared with the API leaf); never crashes the agent's turn."""
    print(loogle_search_text(query))
    return 0


def _tool_goalstate(decl: str, tactics: "list[str] | None" = None) -> int:
    """Warm-REPL GOAL-STATE ORACLE (#124 pull-forward; the agent-facing face of the EXISTING
    `PersistentLean.start_tactic_proof`/`step` API that `conjecture.tactic_step_solve` already consumes —
    extend, don't fork). Opens `theorem … := by sorry`, applies YOUR tactics ONE AT A TIME, prints each
    resulting goal state. YOU drive the search (try a tactic, read the state, decide the next move) — the
    harness adds NO strategy (Goldilocks: search belongs to the agent; the tool is a trust-free oracle).
    REPL-closed is NOT credit: write the assembled proof into your probe — kernel + governance still
    verify. Calibration-first: a dead/mismatched REPL prints INADMISSIBLE (never a fake negative)."""
    from pathlib import Path
    from ztare.formal.lean_persistent import PersistentLean
    from ztare.formal.substrate_liveness import SubstrateDeadError, calibrate
    d = (decl or "").strip()
    if ":=" not in d:
        d = d + " := by sorry"
    elif d.rstrip().endswith(":= by"):
        d = d.rstrip() + " sorry"
    if not d.lstrip().startswith("import"):
        d = "import Mathlib\n\n" + d
    pl = PersistentLean(project_dir=str(Path.cwd()))
    try:
        try:
            calibrate(pl)
        except SubstrateDeadError as e:
            print("goalstate: INADMISSIBLE (REPL dead/mismatched — an apparatus fact, not a math "
                  f"signal): {str(e)[:160]}")
            return 1
        opened = pl.start_tactic_proof(d, timeout=120)
        if not opened.get("ok"):
            print(f"goalstate: could not open the proof ({str(opened.get('err'))[:160]}). "
                  "Check the statement elaborates standalone (binders/imports).")
            return 1
        ps, goal = opened["ps"], opened.get("goal", "")
        print("goal 0 (initial):\n" + goal)
        for i, tac in enumerate([t for t in (tactics or []) if t.strip()], 1):
            sr = pl.step(ps, tac, timeout=60)
            if not sr.get("ok"):
                print(f"step {i} `{tac}` FAILED: {str(sr.get('err'))[:200]}")
                print("(state unchanged — try a different tactic from the last printed goal)")
                return 1
            if sr.get("closed"):
                print(f"step {i} `{tac}`: CLOSED at the REPL. NOT credit — write the assembled proof "
                      "into your probe; the kernel + governance still verify it.")
                return 0
            ps = sr.get("ps")
            print(f"goals after step {i} `{tac}`:\n"
                  + ("\n".join(sr.get("goals") or []) or "(no goals printed)"))
        return 0
    finally:
        pl.close()


_TOOLS = {"witness": _tool_witness, "abduct": _tool_abduct, "hammer": _tool_hammer, "search": _tool_search,
          "falsity": _tool_falsity, "sos": _tool_sos, "goalstate": _tool_goalstate, "verify": _tool_verify,
          "groebner": _tool_groebner, "nlsat": _tool_nlsat, "certify": _tool_certify}


def _log_tool_call(tool: str, arg: str, exit_code: int) -> None:
    """Tool-USE telemetry — the agent's orchestration is otherwise only INDIRECTLY observable (server log + the
    attempts DB). Append each agent tool invocation to a ledger so a run is legible: which exogenous tools the
    agent CHOSE to call (witness/abduct/hammer/search) and how often. Best-effort; never affects the result."""
    try:
        import json
        from datetime import datetime, timezone
        from pathlib import Path   # NOT module-level here (only dataclasses/os/sys are) — import locally or NameError
        repo = Path(__file__).resolve().parents[3]
        p = repo / "analytics" / "public" / "queries" / "agent_tool_calls.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "tool": tool,
                                "arg": (arg or "")[:160], "exit": int(exit_code)}) + "\n")
    except Exception:  # noqa: BLE001
        pass


def main(argv: "list[str] | None" = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] not in _TOOLS:
        print(f"usage: python -m ztare.leanmill.agent_tools <{'|'.join(_TOOLS)}> \"<lean goal>\"\n"
              "       goalstate takes extra args: goalstate \"<theorem … := by sorry>\" \"<tac1>\" \"<tac2>\" …")
        return 2
    if argv[0] == "goalstate":   # the one multi-arg tool: decl + one tactic per following arg
        rc = _tool_goalstate(argv[1], argv[2:])
        _log_tool_call("goalstate", argv[1], rc)
        return rc
    rc = _TOOLS[argv[0]](argv[1])
    _log_tool_call(argv[0], argv[1], rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
