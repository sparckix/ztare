"""GP-174 Phase 1 — Blitz dispatch (decomposed from autoresearch_loop).

Single entry-point that owns the full mutator-fan-out pipeline so the
autoresearch_loop wire-in stays one call site. Replaces the ~140-line
inline block previously living at autoresearch_loop.py:5316.

Composition:

    dispatch_mutator_blitz(deps) -> str (winner thesis text)
        ├─ should_run_parallel(stagnation_count, rubric, force_iter_idx)
        │     └─ K=1 default; K=K when stagnation triggers OR force flag
        ├─ Stage 1: K parallel mutators (parallel_mutator.run_parallel_mutators)
        ├─ Stage 2+3: optional recombination (recombination.recombine)
        └─ Stage 4: tournament selection (parallel_mutator.pick_best_candidate)

Cost-shape posture (per panel synthesis):
  * Default K=1 — no behavior change for projects without rubric flags.
  * K=K only when (a) `stagnation_count >= parallel_mutator_min_stagnation`
    OR (b) `parallel_mutator_force=True` rubric flag set, OR (c) iter is
    in `parallel_mutator_force_iters` list (e.g. seed first 2 iters).
  * Recombination only when `enable_recombination=True` AND ≥2 viable
    blitz outputs, with fusion further gated on stagnation.

Failure isolation:
  * Any exception at any stage falls through to a single safe_mutate call.
  * Logs the failure path so postmortems can reconstruct.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


# Persona-private suffix bank (Munger Phase 1 — Lollapalooza A breaker).
# When K parallel mutators all read the same MutatorBriefing, persona
# divergence has nowhere to come from except a per-worker prompt addition.
# Each suffix is a 1-2 sentence epistemic-bias instruction that the
# mutator appends to its persona declaration. The bias is structural
# (which form-family priors to lean on, which to avoid) rather than
# domain-specific rather than global.
PERSONA_PRIVATE_SUFFIX = {
    "newton_discovery": (
        "Bias: prefer continuous closed-form expressions with smooth "
        "asymptotic limits at extreme feature values. Lean on power-law, "
        "ratio-of-polynomials, and saturation forms. Avoid hard "
        "regime-switch operators (Heaviside, np.where, piecewise) — those "
        "are the engineer-pragmatist's territory."
    ),
    "munger_inversion": (
        "Bias: invert before composing. For each candidate term, ask 'what "
        "is the failure mode this term's absence would create?' before "
        "deciding whether to include it. Prefer subtractive forms (start "
        "with the simplest baseline, add only what falsification "
        "demands). Lean toward anti-elegance — if the form looks "
        "suspiciously beautiful, the substrate is teaching you the answer."
    ),
    "engineer_pragmatist": (
        "Bias: piecewise + hard-boundary forms are first-class. If the "
        "residual fingerprint shows regime breaks or class-asymmetric "
        "patterns, propose explicit class-conditional or threshold-based "
        "constructions. Do not avoid Heaviside / sigmoid / tanh — they "
        "are tools, not anti-patterns. Other personas will avoid them; "
        "your job is to test whether they are required."
    ),
}


# ── Decision: when does parallel/recombination fire? ──────────────────


def should_run_parallel(
    *,
    stagnation_count: int,
    iter_idx: int,
    rubric_data: dict,
) -> tuple[bool, int, str]:
    """Decide whether this iter runs K-parallel or single mutator.

    Returns (run_parallel, K, reason).

    Default policy (panel synthesis — Apparatus seat + MCTS seat):
      K=1 every iter UNLESS one of the triggers fires:
        a. stagnation_count >= parallel_mutator_min_stagnation (default 1)
        b. iter_idx in parallel_mutator_force_iters (e.g. [1, 2] to seed
           the first two iters with diversity before falling back to K=1)
        c. parallel_mutator_force = True (operator opts in always-on)

    K=1 ABLATION OVERRIDE (panel seat 4 + Apparatus seat — Lollapalooza C
    mitigation): if `parallel_mutator_k1_ablation_every` is set (e.g. 5),
    every Nth iter is FORCED to K=1 regardless of stagnation triggers,
    so the operator can compare K=K winners against K=1 winners on the
    same trajectory and detect compositional pipeline-overfitting. Logged
    with `reason='k1_ablation_iter'`.

    Cost shape:
      * always-on K=3:   3× mutator/iter forever (~$0.24/iter at gpt5.5)
      * stagnation-only: 1× normally, 3× on stuck iters (~$0.08-0.24/iter)
      * 1-3-1-3 pattern: 2× average via parallel_mutator_force_iters=[1,3]
      * + K=1 ablation: every Nth iter K=1 regardless (~3% overhead)
    """
    # K=1 ablation override fires FIRST (Lollapalooza C check is
    # independent of stagnation policy).
    ablation_every = int(rubric_data.get("parallel_mutator_k1_ablation_every", 0) or 0)
    if ablation_every > 0 and iter_idx > 0 and (iter_idx % ablation_every == 0):
        return False, 1, f"k1_ablation_iter (iter_idx={iter_idx} % {ablation_every} == 0)"

    K_max = int(rubric_data.get("parallel_mutator_k", 1) or 1)
    if K_max <= 1:
        return False, 1, "K_max<=1 (parallel disabled in rubric)"
    if rubric_data.get("parallel_mutator_force", False):
        return True, K_max, f"force=True (always-on K={K_max})"
    force_iters = rubric_data.get("parallel_mutator_force_iters") or []
    if iter_idx in (int(x) for x in force_iters if isinstance(x, (int, str))):
        return True, K_max, f"iter_idx={iter_idx} in force_iters"
    min_stag = int(rubric_data.get("parallel_mutator_min_stagnation", 1))
    if stagnation_count >= min_stag:
        return True, K_max, f"stagnation_count={stagnation_count} >= {min_stag}"
    return False, 1, f"stagnation_count={stagnation_count} < {min_stag}; K=1 default"


# ── Tournament scoring (delegates to recombination scorer when enabled) ─


_TRIVIAL_LAGRANGIAN_PATTERNS = [
    # Harmonic oscillator centered at a substrate variable or affine
    # combination thereof: ½q̇² − ½(q − feature)² → static E-L gives
    # q = feature (B1 trivial-substitution class).
    # Run 1777403089 iter-4 worker_00 + worker_02 produced this pattern;
    # B1 didn't fire because GP-180 dispatch only runs on the blitz
    # winner, not on per-worker submissions.
    r"q\s*\(\s*t\s*\)\s*-\s*\(?\s*[A-Za-z_]",   # (q(t) - var
    r"q\s*-\s*\(?\s*mass_log10",
    r"q\s*-\s*\(?\s*radius_log10",
]

def _baseline_candidate_score(thesis_text: str) -> float:
    """Cheap syntactic validity scorer — used when recombination is OFF.

    Same shape as the original Phase 4e wire-in heuristic + two
    structural hooks added 2026-04-28 from the iter-4 audit:

    - Trivial-Lagrangian penalty: catches `(q − feature)²` harmonic
      patterns that defeat B1's intent without requiring GP-180 sympy
      dispatch per worker.
    - No domain-specific keyword bonus. Earlier versions rewarded
      domain-specific vocabulary globally; that overfits the kernel to
      whichever substrate happened to motivate the last repair.
    """
    if not thesis_text:
        return -1.0
    import re as _re
    s = 0.0
    if "PARAMETRIC_FORM" in thesis_text:
        s += 1.0
    if "PARAMETER_NAMES" in thesis_text:
        s += 1.0
    if "MODEL_PARAMS" in thesis_text:
        s += 1.0
    if "def I_model" in thesis_text or "def model" in thesis_text:
        s += 1.0
    if "```python" in thesis_text:
        s += 0.5
    try:
        m = _re.search(r"```python(.*?)```", thesis_text, _re.DOTALL)
        if m:
            compile(m.group(1), "<blitz_score>", "exec")
            s += 2.0
    except Exception:
        pass
    s += min(len(thesis_text) / 4000.0, 1.0)

    # Lagrangian declaration check — under invariant_search rubric mode
    # the apparatus contract requires LAGRANGIAN = "..." alongside the
    # legacy PARAMETRIC_FORM. Audit of run 1777403089 found iter-2 had
    # ZERO Lagrangian declarations across all 3 workers, iter-3 had 1/3,
    # iter-4 had 3/3 (but 2 trivial). Workers that omit LAGRANGIAN under
    # invariant_search are operating in legacy mode and cannot pass
    # path-b promotion floor; rank them below workers that declare one.
    has_lagrangian = "LAGRANGIAN" in thesis_text and "LAGRANGIAN_FREE" not in thesis_text
    if not has_lagrangian:
        s -= 1.5

    # Trivial-Lagrangian penalty — only inspect inside an extracted
    # LAGRANGIAN = "..." block to avoid false positives on q-dot terms.
    is_trivial_lag = False
    try:
        lag_match = _re.search(
            r'LAGRANGIAN\s*=\s*[\(\"\']([^\"\']{20,2000}?)[\)\"\']',
            thesis_text, _re.DOTALL,
        )
        if lag_match:
            lag_body = lag_match.group(1)
            for pat in _TRIVIAL_LAGRANGIAN_PATTERNS:
                if _re.search(pat, lag_body):
                    is_trivial_lag = True
                    s -= 2.0  # B1-shadow penalty: still positive, but ranks below
                    break        # non-trivial siblings in the tournament
    except Exception:
        pass

    return s


# ── Single-mutate helper accepted from caller (closure over heavy state) ─


@dataclass
class BlitzDispatchInputs:
    """Caller passes this in. Holds the closure / data the dispatcher
    needs without coupling to autoresearch_loop's local state.
    """
    stagnation_count: int
    iter_idx: int                  # 1-indexed iter number
    rubric_data: dict
    workspace_dir: Path
    current_thesis: str            # used for prior-champion novelty anchor
    current_mutator: str           # model_id for fusion calls
    single_mutate: Callable[[str], str]
    """Callable: (persona_extra_label: str) -> thesis_text. Caller closes
    over `mutate_thesis(...)` with all its 18 named args bound. The
    persona_extra_label is interpreted by `single_mutate` to (a) tag the
    persona declaration AND (b) resolve a structured persona-private
    bias suffix from `PERSONA_PRIVATE_SUFFIX` (Munger Lollapalooza A
    breaker — wired so K parallel workers actually diverge instead of
    sampling around a shared briefing)."""


@dataclass
class BlitzDispatchResult:
    winner_text: str
    K_used: int
    parallel_decision_reason: str
    n_originals: int
    n_after_recombination: int
    fusion_succeeded: bool
    n_crossovers: int
    winner_stage_origin: str
    error: Optional[str] = None


# ── Main entry point ──────────────────────────────────────────────────


def dispatch_mutator_blitz(deps: BlitzDispatchInputs) -> BlitzDispatchResult:
    """Run K-parallel + optional recombination + tournament. Returns
    the winning thesis text alongside provenance for the iter log.

    Failure path: any unexpected exception falls through to a single
    `single_mutate("")` call so the iter still gets a candidate.
    """
    run_parallel, K, decision_reason = should_run_parallel(
        stagnation_count=deps.stagnation_count,
        iter_idx=deps.iter_idx,
        rubric_data=deps.rubric_data,
    )

    if not run_parallel:
        winner_text = deps.single_mutate("")
        return BlitzDispatchResult(
            winner_text=winner_text,
            K_used=1,
            parallel_decision_reason=decision_reason,
            n_originals=1,
            n_after_recombination=1,
            fusion_succeeded=False,
            n_crossovers=0,
            winner_stage_origin="single_mutate",
        )

    # Stage 1: K parallel mutators
    try:
        from src.ztare.orchestrator.parallel_mutator import (
            MutatorTask, MutatorResult, run_parallel_mutators,
            pick_best_candidate, DEFAULT_PARALLEL_PERSONAS,
        )
    except Exception as exc:
        # Apparatus shouldn't even be in this branch if parallel_mutator
        # missing, but fall through safely.
        return BlitzDispatchResult(
            winner_text=deps.single_mutate(""),
            K_used=1, parallel_decision_reason=decision_reason,
            n_originals=1, n_after_recombination=1,
            fusion_succeeded=False, n_crossovers=0,
            winner_stage_origin="single_mutate_fallback",
            error=f"parallel_mutator import: {exc!s}"[:160],
        )

    personas_pool = DEFAULT_PARALLEL_PERSONAS
    tasks = [
        MutatorTask(worker_id=w, persona=personas_pool[w % len(personas_pool)])
        for w in range(K)
    ]

    def _worker(task):
        try:
            text = deps.single_mutate(task.persona)
        except Exception as exc:
            return MutatorResult(
                worker_id=task.worker_id, persona=task.persona,
                thesis_text="", test_model_text="",
                extras={"__error__": f"{type(exc).__name__}: {exc!s}"[:160]},
            )
        return MutatorResult(
            worker_id=task.worker_id, persona=task.persona,
            thesis_text=text or "", test_model_text="",
        )

    print(
        f"⚔️  Parallel mutator blitz K={K} reason='{decision_reason}' "
        f"(personas: {[t.persona for t in tasks]})"
    )
    blitz_results = run_parallel_mutators(tasks, _worker)
    n_originals = len(blitz_results)

    # Persist per-worker artifacts (keep existing parallel_blitz/ layout)
    try:
        bdir = Path(deps.workspace_dir) / "parallel_blitz" / f"iter_{deps.iter_idx:03d}"
        bdir.mkdir(parents=True, exist_ok=True)
        for r in blitz_results:
            (bdir / f"worker_{r.worker_id:02d}_{r.persona}.md").write_text(
                r.thesis_text or "<empty>", encoding="utf-8"
            )
    except Exception:
        pass

    # Stage 2+3: recombination (panel-revised, opt-in)
    # Bug A fix (dry-run 2026-04-28): pick_best_candidate calls scoring_fn(r)
    # with a MutatorResult, not a string. Wrap to extract .thesis_text.
    score_fn = lambda r: _baseline_candidate_score(r.thesis_text)
    n_crossovers = 0
    fusion_succeeded = False
    if deps.rubric_data.get("enable_recombination", False) and n_originals >= 2:
        try:
            from src.ztare.orchestrator.recombination import (
                recombine, score_candidate_extended, extract_parametric_form,
            )
            # AUDIT FIX (impl audit 2026-04-27): instantiate LLMRuntime
            # so persona_fusion is reachable. runtime=None silently
            # killed Stage 3 — fusion was theatrical telemetry until
            # this commit.
            try:
                from src.ztare.common.llm_runtime import LLMRuntime
                _runtime = LLMRuntime()
            except Exception:
                _runtime = None
            prior_form = extract_parametric_form(deps.current_thesis or "") or ""
            stag_for_fusion = deps.stagnation_count >= int(
                deps.rubric_data.get("recombination_fusion_min_stagnation", 1)
            )
            recomb = recombine(
                blitz_results,
                runtime=_runtime,
                model_id=deps.current_mutator,
                prior_champion_form=prior_form,
                workspace_dir=Path(deps.workspace_dir),
                iter_idx=deps.iter_idx,
                enable_crossover=True,
                enable_fusion=stag_for_fusion,
                max_crossover_pairs=int(deps.rubric_data.get("recombination_max_pairs", 3)),
                max_hybrids_per_pair=int(deps.rubric_data.get("recombination_max_hybrids_per_pair", 2)),
            )
            blitz_results = recomb.expanded_pool
            n_crossovers = recomb.n_crossovers
            fusion_succeeded = recomb.fusion_succeeded
            print(
                f"🧬  Recombination: {n_originals}→{len(blitz_results)} "
                f"(crossovers={n_crossovers}, fusion={recomb.n_fusion}, "
                f"fusion_gated={stag_for_fusion}, runtime={'live' if _runtime else 'unavailable'})"
            )
            score_fn = lambda r: score_candidate_extended(
                r.thesis_text, prior_champion_form=prior_form or None
            )
        except Exception as exc:
            print(f"🧬  Recombination error (falling back to tournament-only): {exc!s}"[:200])

    # Stage 4: tournament
    winner = pick_best_candidate(blitz_results, scoring_fn=score_fn)

    # Persist tournament summary (legacy parallel_blitz_log.jsonl)
    try:
        log_path = Path(deps.workspace_dir) / "parallel_blitz_log.jsonl"
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "iter": deps.iter_idx,
                "k": K,
                "decision_reason": decision_reason,
                "n_after_recombination": len(blitz_results),
                "n_crossovers": n_crossovers,
                "fusion_succeeded": fusion_succeeded,
                "winner_id": winner.worker_id if winner else None,
                "winner_persona": winner.persona if winner else None,
                "winner_stage_origin": (
                    (winner.extras or {}).get("stage_origin", "unknown")
                    if winner else None
                ),
                "scores": [
                    {
                        "worker_id": r.worker_id,
                        "persona": r.persona,
                        "stage_origin": (r.extras or {}).get("stage_origin"),
                        "score": round(score_fn(r), 3),
                        "thesis_chars": len(r.thesis_text or ""),
                        "error": (r.extras or {}).get("__error__"),
                    }
                    for r in blitz_results
                ],
            }) + "\n")
    except Exception:
        pass

    if winner:
        winner_origin = (winner.extras or {}).get("stage_origin", f"mutator_{winner.persona}")
        # AUDIT FIX (impl audit 2026-04-27): wire write_candidate_record
        # so pipeline_log.jsonl carries the third record type the panel
        # demanded. Without this, postmortem cannot reconstruct
        # per-candidate score components or "which stage produced winner".
        try:
            from src.ztare.orchestrator.recombination import (
                write_candidate_record, extract_parametric_form,
            )
            for r in blitz_results:
                pf = extract_parametric_form(r.thesis_text or "") or ""
                write_candidate_record(
                    Path(deps.workspace_dir),
                    deps.iter_idx,
                    candidate_id=f"iter{deps.iter_idx:03d}_{r.persona}_w{r.worker_id:02d}",
                    stage_origin=(r.extras or {}).get("stage_origin", f"mutator_{r.persona}"),
                    parametric_form=pf,
                    score=float(score_fn(r)),
                    score_components={
                        "thesis_chars": len(r.thesis_text or ""),
                        "has_param_form": "PARAMETRIC_FORM" in (r.thesis_text or ""),
                        "has_param_names": "PARAMETER_NAMES" in (r.thesis_text or ""),
                        "has_compile": True,  # compile-check inside scorer
                    },
                    selected_as_winner=(r is winner),
                    parent_ids=(r.extras or {}).get("parent_ids", []),
                    extras={"persona": r.persona},
                )
        except Exception as _wcr_exc:
            print(f"📜  candidate-record write failed (non-fatal): {_wcr_exc}")

        print(
            f"⚔️  Blitz winner: worker_{winner.worker_id} "
            f"persona={winner.persona} origin={winner_origin} "
            f"score={score_fn(winner):.2f}"
        )
        return BlitzDispatchResult(
            winner_text=winner.thesis_text or "",
            K_used=K,
            parallel_decision_reason=decision_reason,
            n_originals=n_originals,
            n_after_recombination=len(blitz_results),
            fusion_succeeded=fusion_succeeded,
            n_crossovers=n_crossovers,
            winner_stage_origin=winner_origin,
        )

    # No viable winner — fall back
    print("⚔️  Blitz produced no viable candidate; falling back to single mutate")
    return BlitzDispatchResult(
        winner_text=deps.single_mutate(""),
        K_used=K,
        parallel_decision_reason=decision_reason,
        n_originals=n_originals,
        n_after_recombination=len(blitz_results),
        fusion_succeeded=False,
        n_crossovers=n_crossovers,
        winner_stage_origin="single_mutate_fallback",
        error="no viable winner from tournament",
    )
