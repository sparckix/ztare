"""Agent-facing MOVE CARDS — render the EXOGENOUS-compute moves as tool cards the proving agent reads and
calls itself (the Ax-Prover / agentic-tool-use shape), instead of a hand-wired router scheduling them.

Scope (deliberate): these cards surface ONLY the EXOGENOUS-COMPUTE tools (SymPy witnesses, z3-QE abduction,
Isabelle premise selection AND independent full-theory verification, Mathlib library search) — what the
agent genuinely cannot do in its head, with MEASURED lift on the LLM's blind spots (witness 12/12 on Pell,
QE 6/6). The Isabelle `verify` card is the cross-substrate-CONSENSUS leg: a peer-kernel accept/reject the
agent can elect, NOT a Lean closure (the Lean kernel remains the sole closure arbiter).

The recursive DECOMPOSE-A-PLAN mechanism (DECOMPOSE a hard goal → sub-lemmas → kernel-audit the plan → prove
each recursively → composite-ratify) is deliberately NOT a card here — NOT because "the agent does it in its
head" (that earlier framing was wrong: in-head decomposition gets no soundness audit, no recursion, no
composite ratification), but because it is a SEPARATE governed mechanism: `isomorphism_decompose.route_and_solve`
(the warm leaf GENERATES the plan, the KERNEL audits it, the apparatus proves the sub-lemmas recursively). It
fires automatically inside the governed solver (default-ON, `ZTARE_LEANMILL_ISO_ROUTE`) — see `solver_core`.
Do NOT add a full-PLAN decompose card/tool here: that would fork a 4th decomposition path.

This module is the EXOGENOUS-TOOL contributor to the unified move registry `solver/move_corpus.py` (the single
source of truth that also pulls the structural moves, the transportable techniques, and the math research-op
catalogue). The agent-facing menu is RANKED + RENDERED by `solver/move_atlas.py` (semantic recall over the
corpus); these tool cards keep their governed WHEN/NOT content + live calibration receipts, and the atlas
surfaces them in goal-relevant order. `render_tool_block()` remains the TOOL-CARD-only renderer (the static
fallback when the embedder is down) — strategy/research moves are surfaced through the atlas, not bolted on here
(the 2026-06-20 de-frankenstein: theory-building / decompose / specialize live in the corpus + atlas, NOT as a
second appended surface in this file).

Each card REUSES `contracts/action_card.py` (no new schema) and pulls its `evidence_basis` from the LIVE
`move_calibration` receipts (per-move useful-exit-rate / attempts / cost, learned from RATIFIED governance
verdicts) — so the "cost/value policy" we used to feed the UCB scheduler is now rendered to the AGENT and
self-updates from receipts. Verification stays deterministic (the kernel still verifies whatever the agent
splices in). Single seam: `render_tool_block()` is injected into the leaf prompt (both adhoc + factory go
through `agentic_leaf.solve_robust`, so both get it).
"""
from __future__ import annotations

import os
from pathlib import Path

from ztare.leanmill.solver import prompts          # canonical prompt home (#49) — governance proof-constraint lines
from ztare.leanmill.contracts.action_card import build_action_card

_REPO = Path(__file__).resolve().parents[4]
# The canonical attempts DB the calibration receipts live in (best-effort; absent ⇒ static priors).
_DEFAULT_DB = _REPO / "analytics/public/queries/solver_lane_attempts.db"
# Self-contained command prefix so the agent can run the tool from ANY cwd/env (its shell inherits neither
# our PYTHONPATH nor the venv): absolute venv python + PYTHONPATH=src. Falls back to `python3` if no venv.
_VENV_PY = _REPO / "venv/bin/python"
_PY = str(_VENV_PY) if _VENV_PY.exists() else "python3"
_TOOL_CMD = f"PYTHONPATH={_REPO / 'src'} {_PY} -m ztare.leanmill.agent_tools"

# PORTABLE command prefix for SERIALIZATION. The committed move-atlas artifact must be machine-independent:
# baking THIS machine's absolute repo/venv path into it (the prior bug) both leaks the operator's home path
# AND breaks the cache for any other checkout. The LIVE agent prompt still uses `_TOOL_CMD` (absolute, resolved
# from this machine's repo root via `__file__`, so it runs from any cwd); only the cached atlas stores the
# relative form, and `render_for_goal` re-derives the absolute prefix from the live corpus at render time.
_TOOL_CMD_PORTABLE = "PYTHONPATH=src python3 -m ztare.leanmill.agent_tools"


def _cli(tool: str, arg: str = "<goal>") -> str:
    return f'{_TOOL_CMD} {tool} "{arg}"'


def portable_cli(cli: str) -> str:
    """Strip the machine-specific absolute prefix from a tool `cli` so it is safe to serialize into a committed
    artifact (relative `PYTHONPATH=src` + generic `python3`). Idempotent — a cli without the abs prefix (or an
    empty one) is returned unchanged. Used by `move_corpus.atlas_entries` at the serialization boundary."""
    return (cli or "").replace(_TOOL_CMD, _TOOL_CMD_PORTABLE)


def absolutize_cli(cli: str) -> str:
    """Inverse of `portable_cli`: re-attach THIS machine's absolute repo/venv prefix to a (portable) tool cli so
    the agent — whose cwd is the lake project, not the repo, with neither our PYTHONPATH nor the venv on it — can
    actually run the tool. Applied at RENDER time (the cached atlas stores the portable form; render resolves it
    for the live machine). Idempotent: an already-absolute cli (the static-fallback path's live-corpus cli) does
    not contain the portable prefix, so it is returned unchanged."""
    return (cli or "").replace(_TOOL_CMD_PORTABLE, _TOOL_CMD)

# ── The exogenous tool specs (the agent calls these via Bash; it is already workspace-write) ──────────
#   move_key  → the move_calibration key (None ⇒ no receipt yet, e.g. the new Mathlib-search tool)
_TOOL_SPECS = [
    {
        "tool": "witness", "move_key": "witness_transport",
        "cli": _cli("witness"),
        "when": "the goal is a COMPUTABLE existential the kernel can re-verify but you cannot guess — a Pell "
                "equation ∃x y, x²−D·y²=N (the fundamental solution is a 10+-digit number), an INTEGER "
                "FACTORING existential ∃x y, x·y=N ∧ 1<x ∧ x<N given ONLY the product N (SymPy factors the "
                "semiprime — a no-tool model genuinely cannot), a semiprime system ∃x y, x·y=N ∧ x+y=S, or a "
                "linear/Diophantine system. SymPy computes the witness; you splice ⟨w₀,w₁,…⟩ and the kernel "
                "checks the arithmetic.",
        "confuser": "NOT for a ∀-goal, an inequality with no explicit witness, or anything you can already "
                    "close directly — it returns NONE and you should just write the proof.",
    },
    {
        "tool": "abduct", "move_key": "abduce",
        "cli": _cli("abduct"),
        "when": "a DECIDABLE LINEAR-ARITHMETIC goal is missing exactly one hypothesis (e.g. x≤y ⊢ x≤z). z3 "
                "quantifier-elimination returns the MOST-GENERAL missing premise (Dillig 'Explain'); use it as "
                "the intermediate lemma, then prove the goal from it.",
        "confuser": "fail-CLOSED on NONLINEAR goals (var·var / var^k / var-mod) — it returns NONE there by "
                    "design (undecidable); don't wait on it, reason directly.",
    },
    {
        "tool": "hammer", "move_key": "sledgehammer",
        "cli": _cli("hammer"),
        "when": "you need a PREMISE COMBINATION from a large library and don't know which lemmas combine — "
                "Isabelle Sledgehammer searches and returns a suggested proof/lemmas (heavyweight; needs the "
                "Isabelle server up).",
        "confuser": "returns NONE if the server is down or it finds nothing — fall back to writing the proof.",
    },
    {
        "tool": "verify", "move_key": None,
        "cli": _cli("verify", "<isabelle theory or `lemma name: \\\"…\\\" <proof>`>"),
        "when": "you want an INDEPENDENT-SUBSTRATE check of a (sub-)claim: submit a COMPLETE Isabelle theory "
                "(or a bare `lemma … <proof>` — I wrap the imports/begin/end) and Isabelle's kernel says "
                "ACCEPT/REJECT. Natural pairing: run `hammer` to get an Isar/one-liner proof, then `verify` "
                "the full theory to confirm Isabelle accepts it — a Lean⇄Isabelle corroboration that feeds "
                "cross-substrate consensus, or a quick way to confirm a sub-lemma is TRUE before investing the "
                "Lean proof.",
        "confuser": "an Isabelle ACCEPT is NOT a Lean closure — you still owe the Lean kernel the Lean proof; "
                    "this is a peer-substrate signal only. Returns REJECTED if the Isar proof is wrong / the "
                    "statement is false, and unavailable if the server is down (then prove in Lean directly).",
    },
    {
        "tool": "search", "move_key": None,
        "cli": _cli("search", "<pattern or name>"),
        "when": "you need the EXACT Mathlib lemma name/signature and your parametric memory may be stale — "
                "Loogle/LeanSearch query the current Mathlib (the Ax-Prover 'essential' tool). Use it before "
                "guessing a lemma name that may not exist.",
        "confuser": "returns NONE if offline / no match — then reason from the lemmas you know.",
    },
    {
        "tool": "falsity", "move_key": "falsify",
        "cli": _cli("falsity"),
        "when": "BEFORE grinding a suspect ∀-equation sub-goal: a ~ms invariant check (degree/parity/growth of "
                "the two sides must balance — the conservation-law check) plus a bounded counterexample search. "
                "A hit means the statement is FALSE AS WRITTEN — fix the sign/bound/side or declare "
                "`-- STATEMENT-FALSE` instead of burning budget proving the unprovable.",
        "confuser": "ADVISORY only — a hit is not a proof of falsity (the kernel-proved ¬G is), and NO SIGNAL "
                    "is not a proof of truth. Equality-shaped arithmetic ∀-goals only; NO SIGNAL elsewhere.",
    },
    {
        "tool": "sos", "move_key": "native_hammer",
        "cli": _cli("sos"),
        "when": "a UNIVARIATE polynomial NONNEGATIVITY goal (`0 ≤ p x` / `p x ≥ 0`, or an inequality you can "
                "rearrange to one) of degree ≥ 4: sympy computes an EXACT rational weighted sum-of-squares "
                "certificate and prints the VERBATIM `nlinarith [sq_nonneg …]` call whose square hints make "
                "the goal closable. Pass the polynomial in sympy syntax (variable x). A NOT-NONNEGATIVE "
                "verdict means the statement is FALSE — fix it or route to falsify.",
        "confuser": "NOT for degree ≤ 2 (nlinarith auto-generates those squares — zero lift, the subsumption "
                    "trap) and NOT for multivariate polynomials (needs an SDP solver, not provisioned — it "
                    "returns NONE there by design; reason directly instead).",
    },
    {
        "tool": "nlsat", "move_key": None,
        "cli": _cli("nlsat", "∀ (x y : ℝ), <polynomial (in)equality>"),
        "when": "a NONLINEAR REAL-arithmetic ∀-goal (polynomial (in)equalities over ℝ/ℤ, with &/|/¬/→) — z3's "
                "nlsat DECIDES it (real-closed-field QE is decidable where nlinarith is an incomplete "
                "heuristic). VALID ⇒ the goal is TRUE, keep proving it (route a `0 ≤ p` shape to `sos`); "
                "INVALID ⇒ a concrete counterexample (false as written → fix it or falsify).",
        "confuser": "ADVISORY — a DECISION, not a Lean proof (VALID does not close the goal; the kernel still "
                    "needs the proof, e.g. the sos certificate). NONE on transcendental / set-valued goals or a "
                    "z3 'unknown'. Reals/ints polynomial fragment only.",
    },
    {
        "tool": "groebner", "move_key": None,
        "cli": _cli("groebner", "a = b ; c = d ⊢ goal_lhs = goal_rhs"),
        "when": "a MULTIVARIATE polynomial EQUALITY that follows from polynomial-equation HYPOTHESES — ideal "
                "membership, decidable by Gröbner bases (what linarith can't do and polyrith does only via a "
                "flaky Sage round-trip). SymPy computes the exact cofactors; splice the VERBATIM "
                "`linear_combination` and the kernel discharges it by ring. FORMAT: `hyp0 ; hyp1 ⊢ goal` with "
                "`⊢` (or `|-`), each an equation.",
        "confuser": "NEEDS equation hypotheses (a hypothesis-free identity is `ring`'s job — returns NONE). "
                    "Equalities only (not inequalities — that's sos/nlsat). NONE when the goal is not in the "
                    "ideal by exact division (it may not follow algebraically, or needs the full cofactor lift).",
    },
    {
        "tool": "goalstate", "move_key": "tactic_step",
        "cli": _TOOL_CMD + ' goalstate "<theorem … := by sorry>" "<tac1>" "<tac2>" …',
        "when": "you want to SEE the goal state evolve before committing a long proof: opens the sorried "
                "statement on the REPL and applies your tactics ONE AT A TIME, printing each intermediate "
                "goal — probe what `intro`/`simp`/`field_simp` actually leaves, find WHERE a chain dies, or "
                "test a decomposition point. YOU drive the search; the tool adds no strategy.",
        "confuser": "each CALL spawns a fresh REPL and pays the Mathlib import (~1 min) — BATCH a whole "
                    "candidate sequence into ONE call, never one call per tactic. State is NOT kept between "
                    "calls (pass the full prefix again). REPL-closed is NOT credit — write the assembled "
                    "proof into your probe; the kernel + governance still verify it.",
    },
]
# Pattern-action-contract conformance (RP-002 / epistemic-generation research_log): each card = pattern (when)
# + anti-pattern (confuser) + ACTION (cli); USE is EVIDENCED, not asserted — the carrier artifact is the
# tool-call ledger `analytics/public/queries/agent_tool_calls.jsonl` (+ exogenous_move_telemetry receipts).
# The Phase-11 mechanical-router NULL is why these are AGENT-consumed cards with an advisory router, never a
# mechanical dispatcher trusted for lift on its own.


def _telemetry(db_path: "str | Path | None"):
    """Best-effort per-move receipt pull from move_calibration (learned useful-exit-rate / attempts / cost).
    Returns {move_key: row} or {} (absent DB / import error ⇒ static priors; never crashes)."""
    db = Path(db_path) if db_path else _DEFAULT_DB
    if not db.exists():
        return {}
    try:
        from ztare.leanmill.solver.move_calibration import exogenous_move_telemetry
        rows = exogenous_move_telemetry(db)
        # FIX (2026-06-10 inventory): exogenous_move_telemetry returns {"by_move": {move_key: row}, "headline": …}.
        # The prior `rows.get("moves")` was ALWAYS None ⇒ `for r in None` TypeError ⇒ caught ⇒ {} ⇒ every card
        # silently fell back to the STATIC prior (the learned receipt path was dead even with the flag on). by_move
        # is already {move_key: row} carrying useful_exit_rate/attempts/budget_s/false_ratifications.
        by_move = rows.get("by_move", {}) if isinstance(rows, dict) else {}
        return by_move if isinstance(by_move, dict) else {}
    except Exception:  # noqa: BLE001 — receipts are advisory; a card without them is fine
        return {}


def _evidence_for(move_key: "str | None", tele: dict) -> str:
    """Render the learned receipt (or the static prior) as the card's evidence_basis string."""
    if move_key and move_key in tele:
        r = tele[move_key]
        return (f"measured: useful_exit_rate={r.get('useful_exit_rate')} over {r.get('attempts')} attempts, "
                f"budget_s={r.get('budget_s')}, false_ratifications={r.get('false_ratifications')} "
                f"(from ratified governance receipts)")
    try:
        from ztare.leanmill.solver import governed_dag_search as _g
        from ztare.leanmill.solver.governed_dag_search import MOVE_COST, MOVE_PRIOR_P_CLOSE
        const = {"witness_transport": _g.MOVE_WITNESS_TRANSPORT, "abduce": _g.MOVE_ABDUCE,
                 "sledgehammer": _g.MOVE_SLEDGEHAMMER, "conjecture_lemma": _g.MOVE_CONJECTURE}.get(move_key or "")
        if const:
            return (f"prior (no receipts yet): P(useful)≈{MOVE_PRIOR_P_CLOSE.get(const)}, "
                    f"cost≈{MOVE_COST.get(const)} budget-units")
    except Exception:  # noqa: BLE001
        pass
    return "new tool (no receipts yet) — use when the WHEN condition matches; the kernel verifies regardless"


def _tool_backend_live(tool: str) -> bool:
    """Don't advertise a tool whose backend isn't reachable — a DEAD tool wastes the agent's turn and teaches it
    the tool is useless (the operator foot-gun: `hammer` was surfaced with Isabelle down). witness (SymPy) /
    abduct (z3) ship in the venv and search (Loogle) self-degrades to an honest NONE, so they're always shown.
    hammer (Isabelle sledgehammer) is now DEFAULT-ON when its server is LIVE (the sound-knob-default-on
    principle) — `isabelle_hammer_live` auto-detects the server + liveness-gates it (ZTARE_LEANMILL_SLEDGEHAMMER=0
    force-off), so the cross-substrate leapfrog is surfaced wherever Isabelle runs and self-degrades elsewhere."""
    if tool in ("hammer", "verify"):   # both ride the Isabelle server (premise-search / full-verify)
        from ztare.leanmill.solver.sledgehammer import isabelle_hammer_live
        return isabelle_hammer_live()
    return True


def build_tool_cards(db_path: "str | Path | None" = None) -> list:
    """One action_card per LIVE exogenous tool (dead backends filtered — see `_tool_backend_live`);
    evidence_basis from the live calibration receipts."""
    tele = _telemetry(db_path)
    cards = []
    for s in _TOOL_SPECS:
        if not _tool_backend_live(s["tool"]):
            continue   # don't surface a dead tool to the agent
        cards.append(build_action_card(
            card_type=f"move_tool:{s['tool']}",
            failure_family="wrong-move-selected / move-starved (the agent never reaches the exogenous tool)",
            preventive_gate=f"call `{s['cli']}` when the WHEN condition holds",
            missing_or_paid_preventive_receipt="the kernel re-verifies whatever the tool returns (deterministic)",
            source_specific_false_reading_confuser=[s["confuser"]],
            nearest_confuser_rejection=[s["confuser"]],
            clean_proceed_condition=s["when"],
            action_program=[f"run: {s['cli']}", "read the tool output",
                            "copy the tool's ===VERBATIM-LEAN=== block into the proof EXACTLY (no paraphrase/coercions)",
                            "run `lake env lean` to let the KERNEL verify it"],
            program_counter_rule="call the tool only when its WHEN matches; else reason directly",
            evidence_basis=_evidence_for(s["move_key"], tele),
        ))
    return cards


def menu_preamble_lines() -> list:
    """The shared autonomy + VERBATIM + governance preamble for the agent-facing move menu — reused by BOTH
    `render_tool_block` (static fallback) and `move_atlas.render_for_goal` (the goal-ranked primary seam) so
    the framing never drifts between the two."""
    return ["", "## You are AUTONOMOUS in a workspace-write sandbox — decide your OWN actions.",
            "Act like a researcher with a terminal: run ANY shell command you judge useful — grep the Mathlib",
            "source, query Loogle, write candidate Lean and check it against the kernel, iterate, build helper",
            "lemmas, decompose. NOTHING below is a required step or a prescribed when-to-use; these are the moves",
            "AVAILABLE if you want them (the kernel re-verifies everything you splice in regardless of how you",
            "found it):",
            "VERBATIM CONTRACT: when a tool prints a `===VERBATIM-LEAN-BEGIN===` … `===VERBATIM-LEAN-END===`",
            "block, copy it into the proof EXACTLY as printed — do NOT paraphrase, reformat, reorder, or add",
            "type coercions. A single altered digit/token makes the kernel reject it (the tool is not at fault).",
            *prompts.GOVERNANCE_PROOF_CONSTRAINTS_LINES]   # #104 banned-tactics block (canonical prompts home, #49)


def render_tool_block(db_path: "str | Path | None" = None) -> str:
    """Compact prompt block advertising the EXOGENOUS tools to the proving agent (the TOOL-CARD view; injected
    behind ZTARE_LEANMILL_AGENT_TOOLS). This is the STATIC fallback — the primary agent-facing menu (tools +
    structural + technique + research moves, goal-ranked) is `move_atlas.render_for_goal`. Empty when the flag
    is off (byte-parity)."""
    if os.environ.get("ZTARE_LEANMILL_AGENT_TOOLS", "1") == "0":   # DEFAULT-ON (operator 2026-06-10); =0 opts out (keeps an A/B baseline arm)
        return ""
    cards = build_tool_cards(db_path)
    lines = menu_preamble_lines()
    for c in cards:
        tool = c["card_type"].split(":", 1)[1]
        lines.append(f"\n• TOOL `{tool}` — {c['action_program'][0].replace('run: ', '')}")
        lines.append(f"   WHEN: {c['clean_proceed_condition']}")
        lines.append(f"   NOT: {c['source_specific_false_reading_confuser'][0]}")
        lines.append(f"   track record: {c['evidence_basis']}")
    lines.append("")
    return "\n".join(lines)


def _selftest() -> int:
    from ztare.leanmill.contracts.action_card import validate_action_card
    # LIVE-GATE (default-on-when-live, 2026-06-11): hammer is FORCE-OFF (=0) ⇒ NOT surfaced (no dead tool).
    # Deterministic / no-network: drive the gate by the FORCE-OFF + ASSUME-LIVE hooks, not a real server probe.
    for _v in ("ZTARE_LEANMILL_SLEDGEHAMMER", "ZTARE_ISABELLE_SERVER", "ZTARE_ISABELLE_ASSUME_LIVE"):
        os.environ.pop(_v, None)
    os.environ["ZTARE_LEANMILL_SLEDGEHAMMER"] = "0"   # force-off ⇒ Isabelle tools (hammer + verify) gated out
    cards = build_tool_cards()
    tools = {c["card_type"].split(":", 1)[1] for c in cards}
    assert "hammer" not in tools, f"force-off hammer must be gated out: {tools}"
    assert "verify" not in tools, f"force-off Isabelle verify must be gated out too: {tools}"
    assert {"witness", "abduct", "search"} <= tools, tools
    for c in cards:
        v = validate_action_card(c, expected_card_type=c["card_type"])
        assert v["status"] == "pass", v
    # server LIVE (ASSUME_LIVE hook) + not force-off ⇒ hammer AND verify surface — DEFAULT-ON when up
    os.environ.pop("ZTARE_LEANMILL_SLEDGEHAMMER", None)
    os.environ["ZTARE_ISABELLE_ASSUME_LIVE"] = "1"
    cards_h = build_tool_cards()
    _live = {c["card_type"].split(":", 1)[1] for c in cards_h}
    assert len(cards_h) == len(_TOOL_SPECS) and {"hammer", "verify"} <= _live, cards_h
    for _v in ("ZTARE_LEANMILL_SLEDGEHAMMER", "ZTARE_ISABELLE_SERVER", "ZTARE_ISABELLE_ASSUME_LIVE"):
        os.environ.pop(_v, None)
    os.environ["ZTARE_LEANMILL_AGENT_TOOLS"] = "1"
    block = render_tool_block()
    assert "TOOL `witness`" in block and "Pell" in block, block
    os.environ["ZTARE_LEANMILL_AGENT_TOOLS"] = "0"
    assert render_tool_block() == "", "flag=0 must be empty (opt-out baseline arm)"
    os.environ.pop("ZTARE_LEANMILL_AGENT_TOOLS", None)
    assert render_tool_block() != "", "DEFAULT-ON: an absent flag must RENDER the tools (operator 2026-06-10)"
    print(f"move_cards self-test PASS ({len(cards)} tools by default / {len(cards_h)} with hammer enabled; live-gate + parity ok)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
