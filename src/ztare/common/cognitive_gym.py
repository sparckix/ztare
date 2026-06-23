"""Constrained-validation hooks shared by the in-loop and RD layers.

This module keeps the historic ``cognitive_gym`` import path, but the current
public vocabulary is simpler: validation operators.

The three operators are:

  - invert: ask what would falsify the current frame or what opposite move
    should be tested.
  - compress: ask which invariant or smallest core survives perturbation.
  - disagree: ask for the strongest specific counter-frame.

The in-loop validator already has concrete implementations for common
champion-shaped artifacts:

  - ``inverter_agent.py`` for falsification tests.
  - ``compress_champion.py`` for simpler gate-passing forms.
  - ``margin_of_safety.py`` for the 5-test stress battery.
  - ``negative_space_extractor.py`` for missing structural moves.

This module is the shared router around those implementations. If a request has
an artifact shape that an existing primitive can handle, the router returns that
primitive's invocation. If the artifact is broader, such as a closure attempt,
F-row, mandate edit, paper draft, or cross-substrate synthesis, the router emits
a structured LLM request for the RD/reviewer to fill.

Use it for:

  - RD review of closure attempts across substrates.
  - skeptic review of mandate edits or paper drafts.
  - cross-substrate analysis where no single substrate primitive applies.
  - stagnation review in ``autoresearch_loop``.

Scope: the hooks are dispatch and prompt surfaces. They are not a replacement
for the inner primitives or for deterministic gates.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class CognitiveGymRequest:
    """Structured input to a constrained-validation hook."""
    leg: str  # "invert" | "compress" | "disagree"
    substrate: str
    state_summary: str
    context: dict


@dataclass
class CognitiveGymResponse:
    """Structured output from a constrained-validation hook."""
    leg: str
    suggestion: str
    rationale: str
    confidence: str
    reframed_state: Optional[str] = None


INVERT_PROMPT = """You are operating ZTARE's Invert validation operator.

Invert asks: given the CURRENT FRAME of analysis, what would FALSIFY it? What's the opposite move? What would the negative-result version of this attempt look like?

# Current state

  Substrate: {substrate}
  State summary: {state_summary}
  Context: {context}

# Your job

Produce ONE specific INVERSION of the current frame. Don't be diplomatic — be sharp. Examples:
  - If the apparatus is trying to PROVE X, suggest constructing a counterexample to X
  - If the metric is going up, ask what configuration would make it go DOWN
  - If the LLM has converged on a strategy, ask what's the dual / orthogonal strategy

Return JSON: {{"suggestion": "<one-sentence inversion>", "rationale": "<2 sentences why>", "confidence": "high|medium|low"}}"""


COMPRESS_PROMPT = """You are operating ZTARE's Compress validation operator.

Compress asks: given the current state, what features SURVIVE asymptotically? Strip everything contingent. What's the smallest invariant that must hold?

# Current state

  Substrate: {substrate}
  State summary: {state_summary}
  Context: {context}

# Your job

Produce ONE compression. Strip away everything that could vary across runs / regimes. Examples:
  - If the analysis depends on N parameters, identify the 1-2 that are dimensionally irreducible
  - If the rubric has 6 dimensions, identify the 1 that dominates the score
  - If the proof has 10 lemmas, identify the lemma whose absence would collapse the rest

Return JSON: {{"suggestion": "<the irreducible core>", "rationale": "<2 sentences why this is what survives>", "confidence": "high|medium|low"}}"""


DISAGREE_PROMPT = """You are operating ZTARE's Adversarial Disagreement validation operator.

Disagree asks: assume the current analysis is WRONG. What's the strongest counter-frame? Don't temper it.

# Current state

  Substrate: {substrate}
  State summary: {state_summary}
  Context: {context}

# Your job

Produce ONE adversarial counter-frame. Be specific about what's wrong, not just "could be better":
  - If the apparatus is closing in on a verdict, name a specific way the verdict could be premature
  - If the rubric is scoring high, name the thing the rubric is missing
  - If the LLM proposes a theorem, name the falsifier the LLM hasn't considered

Return JSON: {{"suggestion": "<adversarial counter-frame>", "rationale": "<2 sentences>", "confidence": "high|medium|low"}}"""


PROMPT_BY_LEG = {
    "invert": INVERT_PROMPT,
    "compress": COMPRESS_PROMPT,
    "disagree": DISAGREE_PROMPT,
}


# Lean-substrate connectors name the proof-side move, environment flag, and
# entry point. The hook itself does not run Lake or an LLM; callers execute the
# returned command on the proof substrate.
_LEAN_LEG_PLUGS = {
    "compress": {
        "suggestion": ("Lean COMPRESS = leanmill GENERALIZE (MOVE_GENERALIZE, ZTARE_LEANMILL_GENERALIZE=1): "
                       "prove a STRONGER invariant G' with G'⇒G whose proof subsumes the goal; the "
                       "'irreducible core that survives' is the decision-critical lemma — `conjecture.conjecture_advances` "
                       "trivialize-to-True probe identifies the lemma whose removal collapses the chain. "
                       "Run via `solver_core.solve(mode='dag_search')`."),
        "rationale": "Lean-substrate Compress leg → leanmill generalize + decision-critical core (the isomorphism)."},
    "invert": {
        "suggestion": ("Lean INVERT = leanmill FALSIFY (the Invert leg): before spending proof budget on a "
                       "conjectured (sub)goal, probe for a counterexample — `governance_organs.randomized_differential_probe` "
                       "(Schwartz-Zippel literal perturbation) / the `governed_dag_search` MOVE_FALSIFY producer. "
                       "When a live Lean goal + root are in the request context, this connector EXECUTES the producer "
                       "(`conjecture.LeanFalsifier` via `common.inversion.run_inversion`) — the sink now has a real "
                       "producer; this string is the no-substrate fallback."),
        "rationale": "Lean-substrate Invert leg → leanmill falsify producer (shared common.inversion contract)."},
    "disagree": {
        "suggestion": ("Lean DISAGREE = leanmill matched-negative-control + statement_integrity: "
                       "`solver_core._verify_matched_negative_control` (is the proof just a Mathlib lookup?) + "
                       "`statement_integrity.check` (did the agent ALTER the statement to a provable variant?) + "
                       "a cold cross-provider adversary pass on the goal."),
        "rationale": "Lean-substrate Disagree leg → leanmill MNC + statement-integrity adversary."},
}


def call_gemini(prompt: str, max_tokens: int = 800) -> str:
    """Local LLM call. Returns text or empty string if no API key."""
    if not os.environ.get("GEMINI_API_KEY"):
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model="gemini-3-pro-preview", contents=prompt,
            config={"max_output_tokens": max_tokens},
        )
        parts = []
        for cand in response.candidates or []:
            if cand.content and cand.content.parts:
                for p in cand.content.parts:
                    if hasattr(p, "text") and p.text:
                        parts.append(p.text)
        return "\n".join(parts)
    except Exception:
        return ""


# Substrate-keyed connector registry. A connector recognizes one artifact shape
# and returns the existing primitive or command that should handle it. New
# substrates register connectors instead of editing the dispatcher.
LegConnector = Any  # Callable[[CognitiveGymRequest], Optional[CognitiveGymResponse]]
_LEG_CONNECTORS: "dict[str, list]" = {"invert": [], "compress": [], "disagree": []}


def register_leg_connector(leg: str, connector: "LegConnector") -> None:
    """Register a substrate's connector for a leg. Connectors are tried in registration order."""
    _LEG_CONNECTORS.setdefault(leg, []).append(connector)


def _lean_invert_producer(request: CognitiveGymRequest) -> Optional[CognitiveGymResponse]:
    """Lean Invert leg PRODUCER (2026-06-06): when the request carries a live Lean goal + root, ACTUALLY
    run the falsifier — `conjecture.LeanFalsifier` through the shared Popper contract
    `common.inversion.run_inversion` — instead of returning a reference suggestion. This is the producer
    the arch reserved (`_LEAN_LEG_PLUGS['invert']` was a sink). Returns None when no live goal/root is
    present (⇒ the dispatch-by-reference plug handles it) or on any error (fail-soft to the suggestion)."""
    ctx = request.context or {}
    goal, lean_root = ctx.get("lean_goal"), ctx.get("lean_root")
    if not (goal and lean_root):
        return None
    try:
        from pathlib import Path as _P
        from ztare.leanmill.solver.conjecture import LeanFalsifier
        from ztare.common.inversion import run_inversion
        row = ctx.get("row") or {"target_theorem_name": ctx.get("target_name", "tgt")}
        lf = LeanFalsifier(row, _P(lean_root), int(ctx.get("timeout_s", 120)),
                           preamble=ctx.get("preamble", ""))
        v = run_inversion(lf, goal, {"lean_goal": goal})
        outcome = ("FALSIFIED — kernel-checked ¬G (the target as stated is FALSE)"
                   if v.falsified is True else "no falsifier (goal stands / undecided)")
        return CognitiveGymResponse(
            leg="invert", suggestion=f"Lean falsify producer: {outcome}. {(v.detail or '')[:220]}",
            rationale="executed conjecture.LeanFalsifier via common.inversion.run_inversion (Invert-leg producer)",
            confidence="high", reframed_state=((v.witness or "")[:600] if v.falsified else None))
    except Exception:  # noqa: BLE001 — fall through to the reference plug
        return None


def _lean_connector(request: CognitiveGymRequest) -> Optional[CognitiveGymResponse]:
    """Lean-substrate plug for ALL three legs (REUSE-by-reference to the leanmill moves). Handles the
    request iff it carries a Lean proof artifact (substrate=='lean' or a 'lean_goal' in context). For the
    INVERT leg, if a live goal+root are present it dispatches to the real producer (_lean_invert_producer)
    first; otherwise (and for compress/disagree) it returns the dispatch-by-reference suggestion."""
    ctx = request.context or {}
    if not (ctx.get("substrate") == "lean" or "lean_goal" in ctx):
        return None
    if request.leg == "invert":
        produced = _lean_invert_producer(request)
        if produced is not None:
            return produced
    plug = _LEAN_LEG_PLUGS.get(request.leg)
    if not plug:
        return None
    return CognitiveGymResponse(leg=request.leg, suggestion=plug["suggestion"],
                                rationale=plug["rationale"], confidence="high")


def _regression_invert_connector(request: CognitiveGymRequest) -> Optional[CognitiveGymResponse]:
    """Regression substrate, Invert leg → REUSE validator.inverter_agent.run_inverter (GP-119)."""
    ctx = request.context or {}
    if not ("project_dir" in ctx and "champion_thesis" in ctx):
        return None
    try:
        from ztare.validator.inverter_agent import run_inverter
        result = run_inverter(Path(ctx["project_dir"]), ctx["champion_thesis"], ctx.get("champion_score", 0))
        return CognitiveGymResponse(leg=request.leg, suggestion=str(result.get("falsification_tests", ""))[:600],
                                    rationale="dispatched to inverter_agent (GP-119)", confidence="high")
    except Exception:  # noqa: BLE001 — inner primitive errored; fall back to LLM
        return None


def _regression_compress_connector(request: CognitiveGymRequest) -> Optional[CognitiveGymResponse]:
    """Regression substrate, Compress leg → REUSE fit.compress_champion (GP-103) via CLI suggestion."""
    ctx = request.context or {}
    if not ("project_dir" in ctx and ctx.get("artifact_kind") == "champion"):
        return None
    return CognitiveGymResponse(
        leg=request.leg,
        suggestion=("Inner primitive available: run "
                    f"`python -m src.ztare.fit.compress_champion --project {Path(ctx['project_dir']).name}` (GP-103). "
                    "This invokes template enumeration for the simplest gate-passing form."),
        rationale="dispatched to compress_champion (GP-103) — outer hook recommends inner CLI invocation",
        confidence="high")


def _regression_disagree_connector(request: CognitiveGymRequest) -> Optional[CognitiveGymResponse]:
    """Regression substrate, Disagree leg → REUSE fit.margin_of_safety (GP-112) via CLI suggestion."""
    ctx = request.context or {}
    if not ("project_dir" in ctx and ctx.get("artifact_kind") == "champion"):
        return None
    return CognitiveGymResponse(
        leg=request.leg,
        suggestion=("Inner primitive available: run "
                    f"`python -m src.ztare.fit.margin_of_safety --project {Path(ctx['project_dir']).name}` (GP-112). "
                    "Buffett/Popper/Tukey/Taleb 5-test battery on the champion."),
        rationale="dispatched to margin_of_safety (GP-112) — outer hook recommends inner CLI invocation",
        confidence="high")


# Default registrations: lean plug FIRST (substrate-flagged), then the regression shape-recognizers.
for _leg in ("invert", "compress", "disagree"):
    register_leg_connector(_leg, _lean_connector)
register_leg_connector("invert", _regression_invert_connector)
register_leg_connector("compress", _regression_compress_connector)
register_leg_connector("disagree", _regression_disagree_connector)


def maybe_dispatch_to_inner(request: CognitiveGymRequest) -> Optional[CognitiveGymResponse]:
    """Return the first registered connector that can handle this request."""
    for connector in _LEG_CONNECTORS.get(request.leg, []):
        resp = connector(request)
        if resp is not None:
            return resp
    return None


def dispatch(request: CognitiveGymRequest) -> CognitiveGymResponse:
    """Run a validation operator on a state.

    Routing:
      1. If a registered primitive handles the artifact shape, return that
         primitive's invocation.
      2. Otherwise, fall back to the structured LLM prompt.

    Scope: champion-shaped artifacts should route to concrete primitives. Broad
    review artifacts use the LLM prompt surface.
    """
    # Try existing primitive dispatch first.
    inner_response = maybe_dispatch_to_inner(request)
    if inner_response is not None:
        return inner_response
    if request.leg not in PROMPT_BY_LEG:
        return CognitiveGymResponse(
            leg=request.leg, suggestion="",
            rationale=f"unknown leg {request.leg!r}",
            confidence="high",
        )
    prompt = PROMPT_BY_LEG[request.leg].format(
        substrate=request.substrate,
        state_summary=request.state_summary,
        context=json.dumps(request.context, default=str)[:1500],
    )
    raw = call_gemini(prompt)
    if not raw:
        return CognitiveGymResponse(
            leg=request.leg, suggestion="",
            rationale="LLM unavailable",
            confidence="low",
        )
    # Extract JSON
    import re
    m = re.search(r"\{[^{}]*\"suggestion\"[^{}]*\}", raw, re.DOTALL)
    if not m:
        return CognitiveGymResponse(
            leg=request.leg, suggestion=raw[:200],
            rationale="LLM returned no JSON",
            confidence="low",
        )
    try:
        parsed = json.loads(m.group(0))
        return CognitiveGymResponse(
            leg=request.leg,
            suggestion=parsed.get("suggestion", ""),
            rationale=parsed.get("rationale", ""),
            confidence=parsed.get("confidence", "low"),
        )
    except json.JSONDecodeError:
        return CognitiveGymResponse(
            leg=request.leg, suggestion=raw[:200],
            rationale="JSON parse failed",
            confidence="low",
        )


def invert(substrate: str, state_summary: str, context: dict) -> CognitiveGymResponse:
    """Convenience for the invert leg."""
    return dispatch(CognitiveGymRequest("invert", substrate, state_summary, context))


def compress(substrate: str, state_summary: str, context: dict) -> CognitiveGymResponse:
    """Convenience for the compress leg."""
    return dispatch(CognitiveGymRequest("compress", substrate, state_summary, context))


def disagree(substrate: str, state_summary: str, context: dict) -> CognitiveGymResponse:
    """Convenience for the adversarial disagreement leg."""
    return dispatch(CognitiveGymRequest("disagree", substrate, state_summary, context))


def all_three(substrate: str, state_summary: str, context: dict) -> dict[str, CognitiveGymResponse]:
    """Run all three legs. Useful for a full cognitive-gym workout."""
    return {
        "invert": invert(substrate, state_summary, context),
        "compress": compress(substrate, state_summary, context),
        "disagree": disagree(substrate, state_summary, context),
    }


# Smoke test — verify the connector registry routes per substrate without API
if __name__ == "__main__":
    import sys
    fails = []
    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"); fails.append(name) if not cond else None
    print("=== cognitive_gym_hooks connector-registry smoke test ===")
    # LEAN substrate → leanmill plug for each leg (the registered isomorphism)
    for leg, kw in (("compress", "GENERALIZE"), ("invert", "FALSIFY"), ("disagree", "matched-negative-control")):
        r = maybe_dispatch_to_inner(CognitiveGymRequest(leg, "P1", "open goal", {"substrate": "lean", "lean_goal": "theorem t : G := by"}))
        ok(f"lean {leg} → leanmill plug ({kw})", r is not None and kw in r.suggestion)
    # regression compress (champion shape) → compress_champion CLI suggestion (REUSE preserved)
    r = maybe_dispatch_to_inner(CognitiveGymRequest("compress", "sub", "x", {"project_dir": "/tmp/p", "artifact_kind": "champion"}))
    ok("regression compress → compress_champion (behaviour preserved)", r is not None and "compress_champion" in r.suggestion)
    # neither shape → None → caller falls back to LLM
    ok("unrecognized artifact → None (LLM fallback)",
       maybe_dispatch_to_inner(CognitiveGymRequest("invert", "s", "x", {"prior_attempts": 3})) is None)
    # a newly-registered substrate is reached without editing the dispatcher
    register_leg_connector("compress", lambda req: CognitiveGymResponse("compress", "NEWSUB", "test", "high")
                           if (req.context or {}).get("substrate") == "newsub" else None)
    r = maybe_dispatch_to_inner(CognitiveGymRequest("compress", "s", "x", {"substrate": "newsub"}))
    ok("register_leg_connector extends without editing dispatcher", r is not None and r.suggestion == "NEWSUB")
    print("SMOKE", "PASSED" if not fails else f"FAILED {fails}")
    sys.exit(1 if fails else 0)
