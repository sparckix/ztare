"""Cognitive gym runtime hooks — OUTER/META layer (strange-loop).

# Important framing (corrected 2026-05-06)

The Three Legs of ZTARE are ALREADY MECHANIZED at the INNER level:

  - Invert  → `src/ztare/validator/inverter_agent.py` (GP-119)
              Popper-style falsification tests post-champion
  - Compress → `src/ztare/fit/compress_champion.py` (GP-103)
               Template enumeration for simpler gate-passing form
  - Adversarial Disagreement → `src/ztare/fit/margin_of_safety.py` (GP-112)
                               Buffett/Popper/Tukey/Taleb 5-test battery
  - + `src/ztare/gates/negative_space_extractor.py` (GP-061.B)
        Voids in the candidate universe

  Mutator briefing has 19 stateless providers in
  `src/ztare/orchestrator/briefing_providers/`.

  v5 vocab as generative dispatcher already exists at the option-B
  stagnation-only integration point: `gap_to_op_class.py` +
  `gap_to_op_class_integration.py`.

# What THIS module is for (OUTER, not INNER)

The strange-loop / fractal application: **applying invert / compress /
disagree to WHOLE-SUBSTRATE artifacts that the inner primitives don't
touch** — closure attempts, F-rows, mandate edits, paper drafts,
cross-substrate findings. The inner primitives operate on per-iter
champions / theses; this module operates on the META level RD reviews.

# The hooks dispatch to inner primitives when applicable

Where there's an existing inner primitive that solves a sub-question
the OUTER hook needs, this module IMPORTS and DISPATCHES rather than
re-implementing. Concretely:
  - The "compress" hook on a closure-attempt artifact CAN call
    `compress_champion.find_simpler_form()` if the artifact is a
    champion-shaped object.
  - The "invert" hook on a verified theorem CAN call
    `inverter_agent.run_inverter()` to produce falsification tests.
  - The "disagree" hook on a finding CAN call
    `margin_of_safety.run_battery()` for the 5-test stress.

When the artifact ISN'T champion-shaped (e.g. it's a paper draft, an
F-row, or a cross-substrate synthesis), the hook produces a structured
LLM prompt instead — the meta-layer that doesn't yet have a learned
counterpart.

# When to use THIS module

  - RD reviewing a closure attempt across multiple substrates
  - RD applying skeptic-review to mandate edits or paper drafts
  - Cross-substrate analysis where no single substrate's inner primitive
    applies
  - The Director's per-closure-attempt review duty (see RD mandate v1.22+)

# Honest scope

  - This is a SCAFFOLD. v0.1 dispatches via LLM with structured prompt
    templates. Future versions could compute the inversion / compression /
    disagreement directly from a learned model (see ranker_checkpoint.pt
    for the start of the world-model layer).
  - Where inner primitives apply, USE THEM. This module is for the
    cases they don't reach.

# The three legs as runtime operators

  invert(state)     — invert the current frame: what would FALSIFY this?
                       what's the OPPOSITE move? returns reframed state
  compress(state)   — asymptotic-survival compression: which features
                       SURVIVE under perturbation? returns trimmed state
  disagree(state)   — adversarial disagreement: spawn an opposing-frame
                       analysis; returns disagreement report

# Honest scope

  - These are SCAFFOLDS, not solvers. Each hook produces a structured
    request the LLM (or a subagent) is asked to fill. The hook is a
    DISPATCHER not a generator.
  - First-class versions would compute the inversion / compression /
    disagreement directly from a learned model. v0.1 here delegates
    to LLM with a structured prompt template.

# When to use

  - Stagnation in autoresearch_loop (≥3 iters with no score movement)
  - RD skeptic-review of a closure attempt
  - Pre-commit review of a high-leverage F-row
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class CognitiveGymRequest:
    """Structured input to a cognitive-gym hook."""
    leg: str  # "invert" | "compress" | "disagree"
    substrate: str
    state_summary: str
    context: dict


@dataclass
class CognitiveGymResponse:
    """Structured output from a hook."""
    leg: str
    suggestion: str
    rationale: str
    confidence: str
    reframed_state: Optional[str] = None


INVERT_PROMPT = """You are operating the "Invert" leg of ZTARE's cognitive gym.

The Invert leg asks: given the CURRENT FRAME of analysis, what would FALSIFY it? What's the opposite move? What would the negative-result version of this attempt look like?

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


COMPRESS_PROMPT = """You are operating the "Compress" leg of ZTARE's cognitive gym.

The Compress leg asks: given the current state, what features SURVIVE asymptotically? Strip everything contingent. What's the smallest invariant that must hold?

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


DISAGREE_PROMPT = """You are operating the "Adversarial Disagreement" leg of ZTARE's cognitive gym.

The Disagree leg asks: assume the current analysis is WRONG. What's the strongest counter-frame? Don't temper it.

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


def maybe_dispatch_to_inner(request: CognitiveGymRequest) -> Optional[CognitiveGymResponse]:
    """If the artifact is shaped right for an inner primitive, route to it.

    Returns None if no inner primitive applies (caller falls back to LLM
    dispatch). This is the strange-loop join: outer caller, inner
    machinery where it fits.

    Recognized artifact shapes (in `request.context`):
      - "champion": dict with parametric form + score → routes to inner primitive
      - "project_dir": Path to a substrate workspace → margin_of_safety / inverter
      - else: no inner primitive applies; outer LLM dispatch
    """
    leg = request.leg
    ctx = request.context or {}

    # Only INVERT and COMPRESS have champion-shaped inner primitives.
    # ADVERSARIAL_DISAGREE has margin_of_safety but it operates on full project_dir.

    if leg == "invert":
        # inverter_agent.run_inverter expects (project_dir, champion_thesis, score)
        if "project_dir" in ctx and "champion_thesis" in ctx:
            try:
                from src.ztare.validator.inverter_agent import run_inverter
                result = run_inverter(
                    Path(ctx["project_dir"]),
                    ctx["champion_thesis"],
                    ctx.get("champion_score", 0),
                )
                # Adapt result to CognitiveGymResponse shape
                return CognitiveGymResponse(
                    leg=leg,
                    suggestion=str(result.get("falsification_tests", ""))[:600],
                    rationale="dispatched to inverter_agent (GP-119)",
                    confidence="high",
                )
            except Exception as e:
                # Inner primitive errored; fall back to LLM
                return None
        return None

    if leg == "compress":
        # compress_champion is project-dir based; routes to it when champion file exists
        if "project_dir" in ctx and ctx.get("artifact_kind") == "champion":
            return CognitiveGymResponse(
                leg=leg,
                suggestion=(
                    "Inner primitive available: run "
                    f"`python -m src.ztare.fit.compress_champion --project "
                    f"{Path(ctx['project_dir']).name}` (GP-103). "
                    "This invokes template enumeration for the simplest gate-passing form."
                ),
                rationale="dispatched to compress_champion (GP-103) — outer hook recommends inner CLI invocation",
                confidence="high",
            )
        return None

    if leg == "disagree":
        # margin_of_safety operates on project_dir
        if "project_dir" in ctx and ctx.get("artifact_kind") == "champion":
            return CognitiveGymResponse(
                leg=leg,
                suggestion=(
                    "Inner primitive available: run "
                    f"`python -m src.ztare.fit.margin_of_safety --project "
                    f"{Path(ctx['project_dir']).name}` (GP-112). "
                    "Buffett/Popper/Tukey/Taleb 5-test battery on the champion."
                ),
                rationale="dispatched to margin_of_safety (GP-112) — outer hook recommends inner CLI invocation",
                confidence="high",
            )
        return None

    return None


def dispatch(request: CognitiveGymRequest) -> CognitiveGymResponse:
    """Run a cognitive-gym hook on a state.

    Routing:
      1. If an inner primitive (inverter_agent / compress_champion /
         margin_of_safety) handles this artifact shape, dispatch there.
      2. Else fall back to LLM with structured prompt template.

    Honest scope: this is the OUTER/META layer. Inner primitives are
    the load-bearing implementations for champion-shaped artifacts;
    LLM dispatch handles the meta-artifacts (closure attempts, F-rows,
    mandate edits, paper drafts) the inner primitives don't reach.
    """
    # Try inner-primitive dispatch first
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


# Smoke test — verify the dispatcher imports and shape works without API
if __name__ == "__main__":
    import sys
    print("=== cognitive_gym_hooks dispatcher smoke test ===")
    response = dispatch(CognitiveGymRequest(
        leg="invert", substrate="ns_track_b",
        state_summary="apparatus is converging on instance_with_evidence patches",
        context={"prior_attempts": 3, "verified": 0},
    ))
    print(f"  leg={response.leg}")
    print(f"  suggestion={response.suggestion[:200]}")
    print(f"  rationale={response.rationale[:200]}")
    print(f"  confidence={response.confidence}")
    sys.exit(0)
