"""est_p_close calibration (GP-246 Arc H) — data-driven move priors from the attempts DB.

The governed DAG's `move_policy` ranks moves by `est_p_close` (the probability a move closes a
node). v1 used HARDCODED STUBS (native_hammer 0.25, claude_warm 0.35, …). This module replaces
them with a value MEASURED from `solver_lane_attempts.db` — the exogenous, kernel-arbitrated
record of (provider, compile_ok) per attempt — which is the only legitimate est_p_close signal
(the model cannot narrate around a kernel verdict).

Anti-laundering (the architecture's explicit small-sample warning): a tiny sample must NOT be
fit into a routing myth. So we use a **Beta posterior with the stub as the prior mean** at a
configurable prior strength `k`:

    α0 = stub * k,  β0 = (1 - stub) * k
    posterior_mean = (α0 + closed) / (α0 + β0 + total)

With weak data the posterior stays near the stub (no overfitting); with strong data (e.g.
native_hammer at 0/29) it shifts to the empirical rate. No hard threshold, no laundering — the
prior strength is the single, explicit knob. Substrate-generic: it reads whatever attempts the
DB holds.

Empirical at build time (2026-06-02): native_hammer 0/29, claude_opus_warm 11/29 (38%),
claude_opus one-shot 0/18 — i.e. the stub badly over-rated native_hammer and one-shot cold-shot;
calibration down-weights the dead moves and keeps the warm/leaf move where the closures are.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable, Optional   # used in string annotations (pyflakes F821 / get_type_hints hygiene)

import math

from ztare.fit.mdl import bic_from_loglik  # canonical general BIC (Bernoulli model selection)
from ztare.leanmill.solver.governed_dag_search import (
    MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM, MOVE_CLAUDE_WARM_REFINE, MOVE_COLD_SHOT,
    MOVE_FRONTIER, MOVE_CONJECTURE, MOVE_GENERALIZE, MOVE_TACTIC_STEP, MOVE_PRIOR_P_CLOSE, MOVE_COST,
    DEFAULT_UCB_C, DEFAULT_UCB_EXPLORE_COST_LAMBDA,
)

# Map attempts-DB provider labels → the governed-DAG move whose est_p_close they inform.
# native_hammer is its own move; the warm agent / agentic leaf run in the CLAUDE_WARM slot;
# one-shot LLM providers are the COLD_SHOT fan-out; dedicated provers are the FRONTIER slot.
# ONLY closure moves (those that PROVE G ⇒ compile_ok/ratified is their success) belong here, since the
# aggregate calibrates est_p_CLOSE. generalize + tactic_step ARE closure moves (kernel_clean on success) —
# they were MISSING, so once the unstarving fix lets them run their closures would never feed calibration.
# DELIBERATELY EXCLUDED (non-closure moves whose stub prior is NOT a closure rate): conjecture (advances /
# spawns sub-goals), specialize (produces a verified RUNG, never closes G), falsify (proves ¬G) — their
# yield is tracked by their own outcome (advanced/rung/falsified), not by compile_ok, so calibrating their
# est_p_close from closure data would be wrong (it keeps their stub).
PROVIDER_TO_MOVE: dict[str, str] = {
    "native_hammer": MOVE_NATIVE_HAMMER,
    "claude_opus_warm": MOVE_CLAUDE_WARM,
    "claude_opus_warm_refine": MOVE_CLAUDE_WARM_REFINE,  # gap-refine retry → its OWN tracked arm (#30)
    "codex_refine": MOVE_CLAUDE_WARM_REFINE,  # 2026-07-05: warm move now records the ACTUAL provider (codex) + _refine
    "claude_refine": MOVE_CLAUDE_WARM_REFINE,
    "agentic_leaf": MOVE_CLAUDE_WARM,
    "codex": MOVE_CLAUDE_WARM,            # agentic-leaf best-of-N winner label (the ACTUAL warm-solve provider)
    "claude": MOVE_CLAUDE_WARM,
    "claude_opus": MOVE_COLD_SHOT,
    "codex_gpt5": MOVE_COLD_SHOT,
    "gemini_flash": MOVE_COLD_SHOT,
    "deepseek_v2": MOVE_FRONTIER,
    "leancopilot": MOVE_FRONTIER,
    "leanhammer": MOVE_FRONTIER,
    "generalize": MOVE_GENERALIZE,      # closure move (proves G via an internal strengthening)
    "tactic_step": MOVE_TACTIC_STEP,    # closure move (per-tactic stepping, re-verified as a `by` block)
}

DEFAULT_PRIOR_STRENGTH = 8.0


def beta_posterior_mean(stub: float, closed: int, total: int, strength: float) -> float:
    """Posterior mean of P(close) with a Beta(stub*k, (1-stub)*k) prior + (closed, total) data."""
    a0 = max(1e-6, stub * strength)
    b0 = max(1e-6, (1.0 - stub) * strength)
    return (a0 + closed) / (a0 + b0 + total)


def calibrate_from_counts(per_move: dict[str, tuple[int, int]],
                          stub_priors: dict[str, float] | None = None,
                          strength: float = DEFAULT_PRIOR_STRENGTH,
                          floor: bool = True) -> dict[str, dict]:
    """`per_move`: {move: (closed, total)}. Returns {move: {p, p_stub, closed, total, shift}}
    for EVERY known move (moves with no data keep their stub via the n=0 posterior == stub).

    `floor=True` (default, the SELECTION policy) applies the non-iatrogenic free-move floor so a
    free move is never down-weighted out of the search. `floor=False` is the HONEST FORECAST (no
    floor) — used for Brier scoring/calibration auditing, where pinning native_hammer at its stub
    while it is 0/49 would be a mis-calibration (cold-review-style Brier finding 2026-06-04)."""
    stubs = stub_priors or MOVE_PRIOR_P_CLOSE
    out: dict[str, dict] = {}
    for move, stub in stubs.items():
        closed, total = per_move.get(move, (0, 0))
        p = beta_posterior_mean(stub, closed, total, strength)
        # NON-IATROGENIC FLOOR: never let calibration DOWN-weight a FREE move (cost 0). A free
        # move (native_hammer) costs no budget, so it is always worth trying — pushing its prior
        # below the defer threshold would make the policy SKIP it and lose its occasional closures
        # for zero savings. Calibration only down-weights COSTLY moves (cold_shot/frontier), where
        # wasted budget is the real harm; free moves can only be revised UP by data, never down.
        floored = False
        if floor and MOVE_COST.get(move, 1.0) == 0.0 and p < stub:
            p, floored = stub, True
        out[move] = {"p": round(p, 4), "p_stub": stub, "closed": closed, "total": total,
                     "shift": round(p - stub, 4), "free_floored": floored}
    return out


def calibrate_by_error_class(per_cell: dict[tuple[str, str], tuple[int, int]],
                             per_move: dict[str, tuple[int, int]],
                             stub_priors: dict[str, float] | None = None,
                             strength: float = DEFAULT_PRIOR_STRENGTH,
                             cell_strength: float = DEFAULT_PRIOR_STRENGTH) -> dict[tuple[str, str], dict]:
    """Finer est_p_close: P(close | move, error_class) via NESTED shrinkage.

    `per_cell`: {(move, error_class): (closed, total)}; `per_move`: {move: (closed, total)}.
    Each cell's Beta prior MEAN is the MARGINAL (move) posterior (itself shrunk toward the stub),
    not the raw stub. So a sparse (move, error_class) cell sits at the marginal move rate; the
    marginal sits at the stub until it too has data. This makes the refinement data-gated by
    construction — it equals the marginal calibration today (DB sparse → parity) and only sharpens
    per-error-class as those cells fill. The FREE-move floor is inherited from the marginal."""
    stubs = stub_priors or MOVE_PRIOR_P_CLOSE
    marginal = calibrate_from_counts(per_move, stubs, strength)
    out: dict[tuple[str, str], dict] = {}
    for (move, eclass), (closed, total) in per_cell.items():
        m_mean = marginal.get(move, {}).get("p", stubs.get(move, 0.2))
        p = beta_posterior_mean(m_mean, closed, total, cell_strength)
        floored = False
        if MOVE_COST.get(move, 1.0) == 0.0 and p < m_mean:   # inherit the non-iatrogenic free floor
            p, floored = m_mean, True
        out[(move, eclass)] = {"p": round(p, 4), "p_marginal": round(m_mean, 4),
                               "p_stub": stubs.get(move), "closed": closed, "total": total,
                               "shift_vs_marginal": round(p - m_mean, 4), "free_floored": floored}
    return out


# ── Closure-count scoring: feed the GOVERNANCE verdict back into calibration ─────────────────────
# The attempts DB stamps `ratified` (the kernel/MNC governance verdict) onto every closing attempt,
# but the per-(move,error_class) prior used to ORDER the search scored raw `compile_ok` — so a
# gamed-then-REJECTED closure (compile_ok=1, ratified=0) counted as a calibration WIN and poisoned the
# priors routing the solver (the "ratified verdict emitted-then-dropped" open loop). `COALESCE(ratified,
# compile_ok)` closes it per-row: a ratified closure is a win, a governance-rejected closure is a LOSS
# even though it compiled, and an ungoverned attempt (ratified NULL) keeps its raw compile_ok so sparse
# data is never starved. This mirrors the marginal `selection_priors`, which is already ratified-aware.
def _close_score_expr(effective: bool) -> str:
    """SQL SUM-argument for the closure count. effective ⇒ score the governance verdict where it
    exists (COALESCE(ratified, compile_ok)); else legacy raw compile_ok."""
    return "COALESCE(ratified, compile_ok)" if effective else "compile_ok"


def _score_ratified_default() -> bool:
    """Selection/context priors score the governance verdict by default (a caught cheat is NOT a win).
    `ZTARE_CALIBRATION_SCORE=compile_ok` reverts to legacy raw-compile scoring (the parity escape)."""
    return os.environ.get("ZTARE_CALIBRATION_SCORE", "ratified").strip().lower() != "compile_ok"


# DATA-ADMISSIBILITY (2026-06-10, operator's catch): an attempt that died at the INSTRUMENT is NOT evidence
# about the move's close-rate — the move never got a fair shot at the MATH. Counting it as a calibration LOSS
# poisons the prior. `parse_error` = the probe never parsed (the 2026-06-08 carrier bug recorded native_hammer/
# cold_shot 0/N as dead-instrument artifacts, NOT real losses); `timeout` = the cold-Mathlib-reload censoring
# (right-censored — the move might have closed with more budget, so it is not a Bernoulli "did-not-close"). Both
# are inadmissible for est_p_close. This is the `apparatus_certificate` rule — "a negative is inadmissible
# without calibration" — applied to the LEARNING DATA itself, forward AND retroactively. Default-ON (a poisoned
# prior is a bug); `ZTARE_LEANMILL_CALIBRATION_ADMISSIBLE=0` reverts to the legacy count-everything aggregation.
_APPARATUS_FAILURE_CLASSES = ("parse_error", "timeout")

# RE-BASELINE CUTOFF (operator: "the cutoff is essentially from yesterday when we fixed the bug"). The apparatus
# materially changed at the carrier-probe fix (2026-06-08) + the REPL-toolchain / cold-Mathlib-timeout fix
# (2026-06-09 — warm REPL replaced the cold reload). Attempts BEFORE the later fix are from a DIFFERENT, broken
# instrument and are inadmissible wholesale (a clean re-baseline, no per-row archaeology). Override with
# `ZTARE_LEANMILL_CALIBRATION_SINCE=<ISO8601>` (e.g. to widen the window once more clean data accrues).
_CALIBRATION_ADMISSIBLE_SINCE_DEFAULT = "2026-06-09T00:00:00+00:00"


def _admissible_filter_on() -> bool:
    return os.environ.get("ZTARE_LEANMILL_CALIBRATION_ADMISSIBLE", "1") != "0"


def _admissible_since() -> str:
    return os.environ.get("ZTARE_LEANMILL_CALIBRATION_SINCE", _CALIBRATION_ADMISSIBLE_SINCE_DEFAULT)


def _has_column(con: "sqlite3.Connection", table: str, col: str) -> bool:
    """True iff `table.col` exists. An un-migrated attempts DB has no `ratified` column, so effective
    scoring must DEGRADE to compile_ok there (no governance verdicts to score anyway → parity)."""
    try:
        return any(r[1] == col for r in con.execute(f"PRAGMA table_info({table})").fetchall())
    except sqlite3.Error:
        return False


def _admissibility_clause(con: "sqlite3.Connection", effective: bool) -> "tuple[list[str], list, bool]":
    """The ONE attempts-DB admissibility WHERE (re-baseline date + apparatus-failure hygiene + dynamic
    carrier-liveness). Returns (where_terms, params, effective_after_migration_check) — shared by the per-move
    and per-model aggregations so they cannot drift (DRY; behaviour-identical to the inline clause it replaces)."""
    if effective and not _has_column(con, "attempts", "ratified"):
        effective = False  # un-migrated DB (no governance verdicts) → compile_ok (parity)
    where = ["provider IS NOT NULL"]
    params: "list" = []
    if _admissible_filter_on() and _has_column(con, "attempts", "attempt_at"):
        where.append("attempt_at >= ?"); params.append(_admissible_since())
        where.append("COALESCE(error_class,'none') NOT IN (%s)" % ",".join("?" * len(_APPARATUS_FAILURE_CLASSES)))
        params.extend(_APPARATUS_FAILURE_CLASSES)
    if _admissible_filter_on() and _has_column(con, "attempts", "carrier_live"):
        where.append("COALESCE(carrier_live, 1) != 0")
    return where, params, effective


def _cells_from_db(db_path: str | Path, effective: "bool | None" = None) -> "tuple[dict[tuple[str, str], tuple[int, int]], dict[str, tuple[int, int]]]":
    """Aggregate the attempts DB into ({(move, error_class): (closed, total)}, {move: (closed, total)}).

    `effective` (default = `_score_ratified_default()`) scores the GOVERNANCE verdict via
    `COALESCE(ratified, compile_ok)` so governance-rejected closures count as losses (the poisoning fix);
    pass `effective=False` for the legacy raw compile_ok aggregation."""
    if effective is None:
        effective = _score_ratified_default()
    cells: dict[tuple[str, str], list[int]] = {}
    moves: dict[str, list[int]] = {}
    try:
        with sqlite3.connect(str(db_path)) as con:
            where, params, effective = _admissibility_clause(con, effective)
            rows = con.execute(
                f"SELECT provider, COALESCE(error_class,'none'), COUNT(*), COALESCE(SUM({_close_score_expr(effective)}),0) "
                f"FROM attempts WHERE {' AND '.join(where)} GROUP BY provider, error_class", params).fetchall()
    except sqlite3.Error:  # DB exists but has no `attempts` table / is unreadable → safe empty
        return {}, {}
    for provider, eclass, total, closed in rows:
        move = PROVIDER_TO_MOVE.get(provider)
        if move is None:
            continue
        c = cells.setdefault((move, str(eclass)), [0, 0]); c[0] += int(closed); c[1] += int(total)
        m = moves.setdefault(move, [0, 0]); m[0] += int(closed); m[1] += int(total)
    return ({k: (v[0], v[1]) for k, v in cells.items()},
            {k: (v[0], v[1]) for k, v in moves.items()})


# --- PER-MODEL calibration (the NFL-impossibility leg of the governed-proposer-pool, 2026-06-20) ----------
# The diverse-proposer pool needs ADAPTIVE allocation across MODELS (claude / codex / kimi / …) — NFL proves no
# STATIC split is optimal. move_calibration is per-MOVE; this is the per-MODEL sibling: P(close | model) by the
# SAME governed Beta posterior, off the SAME admissible attempts. Pure read; advisory (routes proposer budget,
# never gates a closure). `stub` is the shared cold prior (no per-model stub table — a new model starts neutral).
DEFAULT_MODEL_STUB = 0.35


def calibrate_by_model(db_path: str | Path, *, stub: float = DEFAULT_MODEL_STUB,
                       strength: float = DEFAULT_PRIOR_STRENGTH, effective: "bool | None" = None) -> "dict[str, dict]":
    """{provider/model: {p, p_stub, closed, total, shift}} from the admissible attempts DB — the per-MODEL
    est_p_close that routes the diverse proposer pool. Reuses `beta_posterior_mean` + `_admissibility_clause`
    (no re-rolled SQL/posterior). A model with no admissible data sits at `stub` (n=0 posterior == stub).
    NOT floored (every model costs budget; unlike the free native moves there is nothing to protect from
    down-weighting) and NOT mapped through PROVIDER_TO_MOVE (we want the raw model identity)."""
    if effective is None:
        effective = _score_ratified_default()
    per_model: "dict[str, list[int]]" = {}
    try:
        with sqlite3.connect(str(db_path)) as con:
            where, params, effective = _admissibility_clause(con, effective)
            rows = con.execute(
                f"SELECT provider, COUNT(*), COALESCE(SUM({_close_score_expr(effective)}),0) "
                f"FROM attempts WHERE {' AND '.join(where)} GROUP BY provider", params).fetchall()
    except sqlite3.Error:
        return {}
    for provider, total, closed in rows:
        if not provider:
            continue
        m = per_model.setdefault(str(provider), [0, 0]); m[0] += int(closed); m[1] += int(total)
    out: "dict[str, dict]" = {}
    for model, (closed, total) in per_model.items():
        p = beta_posterior_mean(stub, closed, total, strength)
        out[model] = {"p": round(p, 4), "p_stub": stub, "closed": closed, "total": total,
                      "shift": round(p - stub, 4)}
    return out


# --- BIC model selection: should est_p_close split by error_class, or pool by move? ------------
# selection_priors / calibrated_priors_for_class CAN condition P(close) on the node's last error
# class. That helps IF closure probability genuinely depends on the error class — but with sparse
# governed data, a per-(move×class) split just overfits noise (a 1/1 cell reads p=1.0). BIC answers
# it honestly: is the finer model's likelihood gain worth its extra parameters, or is pooling by
# move the MDL-shorter description of the same data? This is the leanmill use of `bic_from_loglik`
# (Bernoulli model selection) — distinct from compress_champion's Gaussian curve-fit BIC.

def _binomial_loglik(cells: "list[tuple[int, int]]") -> float:
    """Maximized Bernoulli log-likelihood for a set of independent (closed, total) cells, each at
    its own MLE p=closed/total (clamped off 0/1 so a degenerate cell stays finite). The binomial
    coefficient term is dropped — it's identical across groupings of the same trials, so it cancels
    in the BIC comparison."""
    ll = 0.0
    for closed, total in cells:
        if total <= 0:
            continue
        p = min(max(closed / total, 1e-9), 1.0 - 1e-9)
        ll += closed * math.log(p) + (total - closed) * math.log(1.0 - p)
    return ll


def select_calibration_model(db_path: str | Path) -> dict:
    """Decide — by BIC — whether to condition est_p_close on error_class (per-(move×class) cells,
    more parameters) or pool by move (fewer). Returns the verdict + both BIC scores so the choice
    is auditable. The finer split wins only when its likelihood gain beats the k·ln(N) parameter
    penalty; on sparse data BIC keeps it pooled (no overfitting the priors that route the solver)."""
    cells, moves = _cells_from_db(db_path)
    n_obs = sum(t for _, t in moves.values())
    if n_obs <= 0 or not moves:
        return {"model": "pooled", "reason": "no governed data", "bic_pooled": None,
                "bic_split": None, "n_obs": 0, "k_pooled": 0, "k_split": 0}
    ll_pooled = _binomial_loglik(list(moves.values()))
    ll_split = _binomial_loglik(list(cells.values()))
    k_pooled, k_split = len(moves), len(cells)
    bic_pooled = bic_from_loglik(ll_pooled, k_pooled, n_obs)
    bic_split = bic_from_loglik(ll_split, k_split, n_obs)
    return {"model": "split" if bic_split < bic_pooled else "pooled",
            "bic_pooled": round(bic_pooled, 3), "bic_split": round(bic_split, 3),
            "delta": round(bic_pooled - bic_split, 3),  # >0 ⇒ split justified
            "n_obs": n_obs, "k_pooled": k_pooled, "k_split": k_split}


def calibrated_priors_for_class(db_path: str | Path, error_class: str,
                                strength: float = DEFAULT_PRIOR_STRENGTH) -> dict[str, float]:
    """Drop-in {move: calibrated_p} CONDITIONED on `error_class` (e.g. the current node's last
    failure class). Nested fallback: (move,error_class) cell → marginal move → stub; safe on a
    sparse/empty DB (returns the marginal, which returns the stub). Use this when retrying a node
    whose error_class is known; use `calibrated_priors` for the root/unknown-class case."""
    if not Path(db_path).exists():
        return dict(MOVE_PRIOR_P_CLOSE)
    cells, moves = _cells_from_db(db_path)
    marginal = {m: v["p"] for m, v in calibrate_from_counts(moves, strength=strength).items()}
    by_cell = calibrate_by_error_class(cells, moves, strength=strength)
    out = dict(marginal)
    for (move, eclass), v in by_cell.items():
        if eclass == str(error_class):
            out[move] = v["p"]
    return out


def _counts_from_db(db_path: str | Path, use_ratified: bool = False,
                    source: str | None = None) -> dict[str, tuple[int, int]]:
    """Aggregate the attempts DB into {move: (closed, total)} via PROVIDER_TO_MOVE.

    `use_ratified=True` scores the GOVERNANCE verdict (`ratified`) over only governed attempts
    (`ratified IS NOT NULL`) — so a gamed compile_ok=1 that was rejected counts as a LOSS, not a win
    (the false-positive fix). `source` filters by `row_id` prefix (e.g. 'adhoc::' for ad-hoc capability
    runs vs the batch C-pool) — avoids cross-source pollution of the rating."""
    metric = "ratified" if use_ratified else "compile_ok"
    where = ["provider IS NOT NULL"]
    params: list = []
    if use_ratified:
        where.append("ratified IS NOT NULL")
    if source:
        # exact-prefix via substr (NOT `LIKE source%` — `_`/`%` in row_ids are LIKE wildcards, and
        # `adhoc::foo%` would swallow `adhoc::foobar`; cold-review catch 2026-06-04). A `::`-suffixed
        # source is a MODE prefix (all rows under it); otherwise an EXACT row_id.
        if source.endswith("::"):
            where.append("substr(row_id,1,?)=?"); params += [len(source), source]
        else:
            where.append("row_id=?"); params.append(source)
    agg: dict[str, list[int]] = {}
    try:
        with sqlite3.connect(str(db_path)) as con:
            rows = con.execute(
                f"SELECT provider, COUNT(*), COALESCE(SUM({metric}),0) FROM attempts "
                f"WHERE {' AND '.join(where)} GROUP BY provider", params).fetchall()
    except sqlite3.Error:  # DB exists but no `attempts`/`ratified` → fall back to stubs (n=0)
        return {}
    for provider, total, closed in rows:
        move = PROVIDER_TO_MOVE.get(provider)
        if move is None:
            continue
        a = agg.setdefault(move, [0, 0])
        a[0] += int(closed); a[1] += int(total)
    return {m: (c, t) for m, (c, t) in agg.items()}


_UCB_MIN_SPAN = 0.05   # default floor for the Q-spread scale; env-overridable ZTARE_LEANMILL_UCB_MIN_SPAN
                       # (a near-flat prior still gets a little exploration instead of zero)


# ── UCB-over-moves: bandit selection that GUARANTEES move reachability (2026-06-07) ───────────────
# The fixed-priority `move_policy` walk (native→warm→cold→…→falsify-last) is the structural cause of the
# move-STARVATION the FALSIFY diagnosis found: an early leaf move monopolizes the wallclock, so every late
# move is unreachable regardless of capability. UCB dissolves it: rank the eligible moves by
#     ucb(m) = Q(m) + c · sqrt(ln(N+1) / (n_m + 1)) / (1 + λ·cost(m))
# where Q = the calibrated (ratified-aware) Beta-posterior mean (exploitation), n_m = the move's attempt
# count from the canonical `move` column (so EVERY move — including the non-closure tail conjecture/
# specialize/falsify — accrues visits and its exploration bonus DECAYS as it is tried; no permanent
# over-exploration), N = total attempts, cost = MOVE_COST (a λ-discount tempers the bonus on expensive
# moves so the search does not over-explore a costly falsify/tactic_step). A never-pulled move (n_m=0) gets
# the maximum finite bonus, so it is selected ahead of a well-explored low-value move ⇒ REACHABILITY by
# construction. At c=0 this reduces EXACTLY to argmax-Q (the calibrated-greedy order). The kernel still
# RATIFIES every closure, so a mis-ranked move only wastes budget — it can NEVER launder a closure (this is
# a SELECTION change, not a gate). Default-OFF via the worker flag ⇒ byte-identical fixed-order parity.

def move_visit_counts(db_path: str | Path, run_tag: str | None = None) -> dict[str, int]:
    """{move: attempt_count} — the UCB exploration denominator. Prefers the canonical `move` column (covers
    ALL moves incl. the non-closure tail); FALLS BACK to the `provider` column via PROVIDER_TO_MOVE when the
    `move` column is absent or all-NULL (an un-backfilled DB — e.g. the live 42-row DB). The fallback is the
    key WARM-START fix (red-team 2026-06-07): without it move_visit_counts returns {} ⇒ N=0 ⇒ zero
    exploration bonus ⇒ UCB collapses to pure-Q ⇒ the dormant tail (falsify lowest-Q) stays starved, the very
    failure UCB exists to fix. The fallback gives native/warm their real production counts and correctly
    leaves the tail at n=0 (dormant) — i.e. the production SKEW that makes the tail's n=0 bonus reachable —
    WITHOUT needing the `move`-column backfill. Empty only on a truly empty/unreadable DB (safe pure-Q)."""
    def _query(col: str) -> dict[str, int]:
        where, params = [f"{col} IS NOT NULL"], []
        if run_tag:
            where.append("run_tag=?"); params.append(run_tag)
        try:
            with sqlite3.connect(str(db_path)) as con:
                if not _has_column(con, "attempts", col):
                    return {}
                if run_tag and not _has_column(con, "attempts", "run_tag"):
                    return {}
                return {str(k): int(v) for k, v in con.execute(
                    f"SELECT {col}, COUNT(*) FROM attempts WHERE {' AND '.join(where)} GROUP BY {col}",
                    params).fetchall() if k is not None}
        except sqlite3.Error:
            return {}
    by_move = _query("move")
    if by_move:  # canonical column present and populated
        return by_move
    # FALLBACK: aggregate the `provider` column into moves (the same map calibration uses).
    out: dict[str, int] = {}
    for provider, n in _query("provider").items():
        mv = PROVIDER_TO_MOVE.get(provider)
        if mv:
            out[mv] = out.get(mv, 0) + n
    return out


def ucb_move_scores(priors: dict[str, float], visits: dict[str, int], costs: dict[str, float],
                    c: float = DEFAULT_UCB_C, lam: float = DEFAULT_UCB_EXPLORE_COST_LAMBDA) -> dict[str, float]:
    """PURE UCB blend: {move: Q + c·sqrt(ln(N+1)/(n_m+1))/(1+λ·cost)}. No I/O ⇒ directly unit-testable.
    `priors` = {move: Q} (calibrated means), `visits` = {move: n_m} (may omit a move ⇒ n_m=0), `costs` =
    MOVE_COST. At c=0 returns priors verbatim (calibrated-greedy). A move absent from `visits` (n=0) gets
    the maximum bonus c·sqrt(ln(N+1)) → reachability.

    `c` (default 0.3) is deliberately MODEST: the per-target horizon is SHORT (≈2–6 affordable leaf moves),
    so a UCB1-textbook c≈√2 would make the n=0 bonus exceed the whole Q range and the search would spend its
    tiny budget purely exploring (never exploiting the calibrated value). At c=0.3 the calibrated Q drives
    ordering and exploration is a gentle promoter that — accumulated across the target distribution — still
    guarantees every dormant move is eventually selected (reachability) without steamrolling a fresh node."""
    N = sum(max(0, int(v)) for v in visits.values())
    lnN = math.log(N + 1.0)
    # SCALE-INVARIANT exploration (red-team 2026-06-07): scale the bonus by the Q-SPREAD so `c` is a
    # DIMENSIONLESS fraction of the prior spread, not a raw magnitude that silently inflated as N grew. The
    # un-scaled bonus at c=0.3 / production N was ~2× the whole Q-span ⇒ the unproven tail (n=0) steamrolled
    # proven moves ⇒ a true-target REGRESSION. Scaling pins the n=0 bonus to `c × span × √(lnN)` so the
    # default stays in the no-regression band and `c` means the same thing regardless of corpus size.
    qs = [float(v) for v in priors.values()]
    _min_span = float(os.environ.get("ZTARE_LEANMILL_UCB_MIN_SPAN", _UCB_MIN_SPAN))
    span = max((max(qs) - min(qs)) if qs else 0.0, _min_span)  # floor: a flat prior still explores a little
    out: dict[str, float] = {}
    for move, q in priors.items():
        n = max(0, int(visits.get(move, 0)))
        bonus = c * span * math.sqrt(lnN / (n + 1.0)) / (1.0 + lam * float(costs.get(move, 1.0)))
        out[move] = float(q) + bonus
    return out


# ── Per-move REACHABILITY + YIELD (factory-intelligence read-model, 2026-06-06) ──────────────────
_NONCLOSE_SUCCESS = {"advanced", "rung", "falsified"}   # non-closure moves succeed via `outcome`, not compile_ok


def move_yield_report(db_path: str | Path, run_tag: str | None = None) -> dict:
    """Per-MOVE reachability + yield from the attempts DB — the insight the factory read-model was missing:
    WHICH moves are reached vs dormant, their ratified-close yield, and yield-per-minute. Uses the canonical
    `move` column (backfilled) so ALL moves are visible (cold/frontier no longer hidden behind raw provider
    names; the non-closure moves conjecture/specialize/falsify appear with their OWN success — advanced/rung/
    falsified — so a 0 close-rate is not mistaken for 'useless'). `run_tag` slices one run (e.g. an A/B arm).
    Surfaces the starvation finding: native+warm attempt-share, the only-warm-closes concentration, the
    dormant tail."""
    by_move: dict = {}
    where, params = ["move IS NOT NULL"], []
    if run_tag:
        where.append("run_tag=?"); params.append(run_tag)
    try:
        with sqlite3.connect(str(db_path)) as con:
            rows = con.execute(
                f"SELECT move, outcome, COALESCE(ratified,0), wallclock_s FROM attempts "
                f"WHERE {' AND '.join(where)}", params).fetchall()
    except sqlite3.Error:
        return {"by_move": {}, "headline": {}}
    for mv, outcome, rat, wc in rows:
        m = by_move.setdefault(mv, {"attempts": 0, "ratified_closes": 0, "non_close_success": 0,
                                    "_wc_sum": 0.0, "_wc_n": 0})
        m["attempts"] += 1
        m["ratified_closes"] += int(rat)
        if outcome in _NONCLOSE_SUCCESS:
            m["non_close_success"] += 1
        if wc is not None:
            m["_wc_sum"] += float(wc); m["_wc_n"] += 1
    total = sum(m["attempts"] for m in by_move.values()) or 1
    for m in by_move.values():
        m["reached"] = m["attempts"] > 0
        m["close_rate"] = round(m["ratified_closes"] / m["attempts"], 3) if m["attempts"] else 0.0
        m["mean_wallclock_s"] = round(m["_wc_sum"] / m["_wc_n"], 1) if m["_wc_n"] else None
        m["ratified_per_min"] = (round(m["ratified_closes"] / (m["_wc_sum"] / 60.0), 3)
                                 if m["_wc_sum"] > 0 else None)
        m.pop("_wc_sum"); m.pop("_wc_n")
    nw = (by_move.get(MOVE_NATIVE_HAMMER, {}).get("attempts", 0)
          + by_move.get(MOVE_CLAUDE_WARM, {}).get("attempts", 0))
    closers = sorted(mv for mv, m in by_move.items() if m["ratified_closes"] > 0)
    dormant = sorted(set(MOVE_PRIOR_P_CLOSE.keys()) - set(by_move.keys()))
    return {
        "by_move": by_move,
        "headline": {
            "total_attempts": total,
            "native_warm_attempt_share": round(nw / total, 3),
            "closers": closers,
            "only_warm_closes": closers == [MOVE_CLAUDE_WARM],
            "reached_moves": sorted(by_move.keys()),
            "dormant_moves": dormant,
        },
    }


# ── Exogenous-move outcome telemetry + promotion gate (cold-review #3, 2026-06-07) ────────────────────
# The cold review's discipline: "exogenous moves may generate ideas; only kernel-governed proof/exact-gap/
# falsifier exits create credit", and a move is promoted ONLY if its USEFUL-EXIT rate beats baseline with
# ZERO false ratifications. This read-model categorizes every attempt's outcome into the cold-review buckets
# and computes the per-move promotion verdict from the EXOGENOUS attempts DB (never self-scored).
_USEFUL_EXITS = {"closed", "rung", "falsified", "advanced", "exact_gap"}        # kernel-governed value
# CAUGHT CHEATS / mis-targets — only a CONFIRMED laundering verdict belongs here. RCA 2026-06-18: the old
# catch-all `rejected_negative_control` was REMOVED — it conflated banned-axiom rejects, control-flow drops,
# and genuine leakage into one "cheat" bucket, driving real provers' priors down for closures they produced
# (claude_warm fell to p=0.113). The truthful labels (`_reject_reason_from_validation`) replace it:
# `rejected_mnc_leakage` + `rejected_anti_laundering` ARE confirmed cheats; `rejected_banned_axiom` and the
# `uncredited_*` flow-bug labels are NOT (handled below). The legacy label is kept for back-compat reads of
# OLD rows, but the re-baseline reclassifies them.
_WRONG_TARGET = {"rejected_mnc_leakage", "rejected_anti_laundering",
                 "rejected_governance", "statement_altered", "statement_altered_confirmed", "leakage"}
# A KERNEL-VALID closure that the dispatch flow dropped, or a banned-axiom (true-modulo-axioms) reject —
# NEITHER is a cheat. Surfaced as its own bucket so it never poisons the cheat rate AND is loudly visible.
_FLOW_OR_AXIOM = {"uncredited_validated_closure_dropped", "uncredited_no_validation", "rejected_banned_axiom"}
# RE-BASELINE (RCA 2026-06-18, dead-instrument admissibility — same discipline as the carrier-liveness
# filter): every legacy `rejected_negative_control` row predates the truthful labels AND the MNC that
# supposedly produced it was a silent no-op (the `re` NameError), so the label is an UNRELIABLE catch-all,
# NOT a confirmed cheat. Excluded from the cheat rate (it would falsely depress real provers' priors —
# claude_warm was driven to p=0.113 by exactly this). Counted as a neutral, INADMISSIBLE legacy bucket.
_LEGACY_INADMISSIBLE = {"rejected_negative_control"}
# everything else (no_witness, no_falsifier, failed_compile, no_rung, open, …) = NO-POSITIVE (cheap miss)


def exogenous_move_telemetry(db_path: str | Path, run_tag: str | None = None,
                         min_attempts: int = 5, baseline_rate: float = 0.0) -> dict:
    """Per-MOVE outcome dashboard + promotion gate. For each move: attempts, useful_exits (closure | rung |
    falsified | advanced | exact_gap), no_positive (cheap misses), wrong_target (caught cheats), ratified_
    closes, FALSE_RATIFICATIONS (outcome=closed but ratified=0 — a gamed closure governance REJECTED; the
    safety tripwire), budget_s, and useful_exit_rate. `promotion_eligible` iff useful_exit_rate > baseline_
    rate AND false_ratifications == 0 AND attempts >= min_attempts (the cold-review gate). Reads the canonical
    `move`/`outcome`/`ratified`/`wallclock_s` columns; `run_tag` slices one A/B arm."""
    by_move: dict = {}
    where, params = ["move IS NOT NULL"], []
    if run_tag:
        where.append("run_tag=?"); params.append(run_tag)
    try:
        with sqlite3.connect(str(db_path)) as con:
            if not _has_column(con, "attempts", "move"):
                return {"by_move": {}, "headline": {"promotable": [], "tripwire_false_ratifications": []}}
            rat_sel = "COALESCE(ratified,-1)" if _has_column(con, "attempts", "ratified") else "-1"
            wc_sel = "COALESCE(wallclock_s,0)" if _has_column(con, "attempts", "wallclock_s") else "0"
            rows = con.execute(
                f"SELECT move, COALESCE(outcome,'') , {rat_sel}, {wc_sel} FROM attempts "
                f"WHERE {' AND '.join(where)}", params).fetchall()
    except sqlite3.Error:
        return {"by_move": {}, "headline": {"promotable": [], "tripwire_false_ratifications": []}}
    for mv, outcome, rat, wc in rows:
        m = by_move.setdefault(mv, {"attempts": 0, "useful_exits": 0, "no_positive": 0, "wrong_target": 0,
                                    "ratified_closes": 0, "false_ratifications": 0, "legacy_inadmissible": 0,
                                    "budget_s": 0.0})
        oc = (outcome or "").strip()
        if oc in _LEGACY_INADMISSIBLE:
            # RE-BASELINE: dead-MNC-era mislabel — EXCLUDE from every rate (not even an attempt); track it
            # separately so the de-poisoning is auditable. Without this the row would dilute the denominator.
            m["legacy_inadmissible"] += 1
            continue
        m["attempts"] += 1
        m["budget_s"] += float(wc or 0)
        if oc == "closed" and int(rat) == 0:
            # compiled BUT governance REJECTED it (gamed closure) — a WRONG-target + the tripwire, NOT useful.
            m["wrong_target"] += 1
            m["false_ratifications"] += 1
        elif oc in _USEFUL_EXITS:
            m["useful_exits"] += 1
            if oc == "closed" and int(rat) == 1:
                m["ratified_closes"] += 1
        elif oc in _WRONG_TARGET:
            m["wrong_target"] += 1
        else:
            m["no_positive"] += 1
    promotable, tripwire = [], []
    for mv, m in by_move.items():
        m["useful_exit_rate"] = round(m["useful_exits"] / m["attempts"], 3) if m["attempts"] else 0.0
        m["budget_s"] = round(m["budget_s"], 1)
        m["promotion_eligible"] = bool(m["attempts"] >= min_attempts
                                       and m["false_ratifications"] == 0
                                       and m["useful_exit_rate"] > baseline_rate)
        if m["promotion_eligible"]:
            promotable.append(mv)
        if m["false_ratifications"] > 0:
            tripwire.append(mv)
    return {"by_move": by_move,
            "headline": {"promotable": sorted(promotable),
                         "tripwire_false_ratifications": sorted(tripwire),
                         "baseline_rate": baseline_rate, "min_attempts": min_attempts}}


def closure_at_budget(db_path: str | Path, run_tag: str | None = None,
                      source: str | None = None) -> dict:
    """The OBJECTIVE metric the self-tuning is supposed to move — ratified closures (governance-
    accepted, NOT raw compile_ok). This is what `outcome_link` measures so a retune is scored against
    closure@budget, not the forecast-Brier PROXY. `run_tag` slices an A/B arm; `source` a row-id
    prefix. Returns {closures, attempts, rate} (rate = ratified closures / attempts). Safe on a
    missing/empty DB (returns zeros)."""
    where, params = ["1=1"], []
    if run_tag:
        where.append("run_tag=?"); params.append(run_tag)
    if source:  # exact-prefix (matches _counts_from_db: not LIKE — avoids the `_`/`%` wildcard swallow)
        if source.endswith("::"):
            where.append("substr(row_id,1,?)=?"); params += [len(source), source]
        else:
            where.append("row_id=?"); params.append(source)
    try:
        with sqlite3.connect(str(db_path)) as con:
            row = con.execute(
                f"SELECT COUNT(*), COALESCE(SUM(CASE WHEN ratified=1 THEN 1 ELSE 0 END),0) "
                f"FROM attempts WHERE {' AND '.join(where)}", params).fetchone()
    except sqlite3.Error:
        return {"closures": 0, "attempts": 0, "rate": 0.0}
    attempts, closures = (int(row[0]), int(row[1])) if row else (0, 0)
    return {"closures": closures, "attempts": attempts,
            "rate": round(closures / attempts, 4) if attempts else 0.0}


# ── Forecast / Brier / Elo (move-policy calibration loop, 2026-06-04) ────────────────────────────
def forecast_priors(db_path: str | Path, strength: float = DEFAULT_PRIOR_STRENGTH,
                    use_ratified: bool = False, source: str | None = None) -> dict[str, float]:
    """HONEST per-move close-prob forecast — Beta posterior with NO free-move floor. The SELECTION
    policy uses `calibrated_priors` (floored, so free moves are always tried); the FORECAST uses this
    (unfloored) so Brier scoring isn't fooled by a free move pinned above its true rate. `use_ratified`/
    `source` score the governance verdict / a row_id slice (see `_counts_from_db`)."""
    if not Path(db_path).exists():
        return dict(MOVE_PRIOR_P_CLOSE)
    cal = calibrate_from_counts(_counts_from_db(db_path, use_ratified, source), strength=strength, floor=False)
    return {m: v["p"] for m, v in cal.items()}


def brier_report(db_path: str | Path, strength: float = DEFAULT_PRIOR_STRENGTH,
                 use_ratified: bool = False, source: str | None = None) -> dict:
    """Brier-score the HONEST move forecast against actual outcomes (closes the forecast→outcome
    loop). Brier = mean (p−y)² over each move's attempts; per-move + n-weighted overall. Lower is
    better (0.25 = always-guess-0.5 chance). This is the metric that says whether move-selection's
    probabilities are trustworthy — and `rejected_governance` outcomes count as y=0 (gaming earns a
    forecast penalty, which is the steering signal toward honest moves)."""
    counts = _counts_from_db(db_path, use_ratified, source)
    fc = forecast_priors(db_path, strength, use_ratified, source)
    per: dict[str, dict] = {}
    tot_n = 0
    tot_b = 0.0
    for move, (closed, total) in counts.items():
        if not total:
            continue
        p = fc.get(move, MOVE_PRIOR_P_CLOSE.get(move, 0.2))
        brier = (p * p) * (total - closed) / total + (1 - p) * (1 - p) * closed / total
        per[move] = {"forecast_p": round(p, 4), "actual_rate": round(closed / total, 4),
                     "closed": closed, "total": total, "brier": round(brier, 4),
                     "miscalibration": round(abs(p - closed / total), 4)}
        tot_n += total
        tot_b += brier * total
    return {"overall_brier": round(tot_b / tot_n, 4) if tot_n else None, "n": tot_n,
            "chance_brier": 0.25, "per_move": per,
            "note": "honest forecast (no free-move floor) vs actual compile_ok; lower brier = better"}


def recorded_forecast_brier(db_path: str | Path, use_ratified: bool = False,
                            source: str | None = None) -> dict:
    """TRUE forecast Brier: the `est_p_close` RECORDED at dispatch time vs the realized outcome.
    Unlike `brier_report` (current prior vs aggregate history — fit to the same data), this is honest
    skin-in-the-game: each attempt's prediction is scored against what actually happened. Needs the
    `est_p_close` column populated (recorded by the worker's move_runner from 2026-06-04)."""
    metric = "ratified" if use_ratified else "compile_ok"
    where = ["est_p_close IS NOT NULL"]
    params: list = []
    if use_ratified:
        where.append("ratified IS NOT NULL")
    if source:  # exact-prefix (see _counts_from_db) — not LIKE (wildcard bug)
        if source.endswith("::"):
            where.append("substr(row_id,1,?)=?"); params += [len(source), source]
        else:
            where.append("row_id=?"); params.append(source)
    try:
        with sqlite3.connect(str(db_path)) as con:
            rows = con.execute(
                f"SELECT est_p_close, {metric} FROM attempts WHERE {' AND '.join(where)}",
                params).fetchall()
    except sqlite3.Error:
        return {"n": 0, "note": "no est_p_close/attempts column yet"}
    n = len(rows)
    if not n:
        return {"n": 0, "note": "no attempts with a recorded forecast yet (est_p_close NULL); "
                                "the worker records it going forward — re-run to accumulate"}
    brier = sum((p - (y or 0)) ** 2 for p, y in rows) / n
    mean_p = sum(p for p, _ in rows) / n
    base = sum((y or 0) for _, y in rows) / n
    return {"recorded_forecast_brier": round(brier, 4), "n": n,
            "mean_forecast": round(mean_p, 4), "base_rate": round(base, 4),
            "scored_against": metric, "chance_brier": 0.25,
            "note": "honest prediction-vs-outcome (recorded est_p_close), not current-prior-vs-history"}


def move_elo(db_path: str | Path, *, initial: float = 1000.0, k: float = 24.0,
             use_ratified: bool = False, source: str | None = None) -> dict:
    """Pairwise Elo leaderboard over MOVES from the attempts DB (textbook Elo — same formula as
    population_elo.py, inlined to avoid importing that module's batch-pipeline deps). Round-robin:
    for each move pair, the higher empirical close-rate 'wins'. A CROSS-CHECK rating complementing
    the calibrated probability the policy uses for selection (APN-style arm ranking). `use_ratified`/
    `source` score the governance verdict / a row_id slice. Returns {move:{elo,close_rate,n}} best-first."""
    counts = _counts_from_db(db_path, use_ratified, source)
    rated = {m: (c, t) for m, (c, t) in counts.items() if t > 0}
    if len(rated) < 2:
        return {"error": "need ≥2 moves with data", "moves_with_data": list(rated)}
    rate = {m: c / t for m, (c, t) in rated.items()}
    ratings = {m: initial for m in rated}

    def _expected(ra: float, rb: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))

    moves = sorted(rated)
    for i in range(len(moves)):
        for j in range(i + 1, len(moves)):
            a, b = moves[i], moves[j]
            result_a = 1.0 if rate[a] > rate[b] else (0.0 if rate[a] < rate[b] else 0.5)
            ea = _expected(ratings[a], ratings[b])
            ratings[a] += k * (result_a - ea)
            ratings[b] += k * ((1.0 - result_a) - (1.0 - ea))
    return {m: {"elo": round(ratings[m], 1), "close_rate": round(rate[m], 4),
                "n": rated[m][1]} for m in sorted(moves, key=lambda x: -ratings[x])}


def forecast_loop_report(db_path: str | Path, use_ratified: bool = False,
                         source: str | None = None) -> str:
    """One-call human report: calibrated SELECTION priors + honest FORECAST + Brier + Elo leaderboard.
    `use_ratified=True` scores the GOVERNANCE verdict (honest capability — gamed cheats are losses);
    `source` (e.g. 'adhoc::') slices to one corpus so cross-source attempts don't pollute the rating."""
    br = brier_report(db_path, use_ratified=use_ratified, source=source)
    elo = move_elo(db_path, use_ratified=use_ratified, source=source)
    sel = calibrated_priors(db_path)
    rfb = recorded_forecast_brier(db_path, use_ratified=use_ratified, source=source)
    scope = ("RATIFIED" if use_ratified else "compile_ok") + (f" | source={source}" if source else "")
    lines = [f"[move-forecast] attempts DB: {db_path}  (scoring: {scope})",
             f"  prior-vs-history Brier = {br['overall_brier']} (chance {br['chance_brier']}) over n={br['n']}",
             (f"  TRUE recorded-forecast Brier = {rfb.get('recorded_forecast_brier')} over n={rfb['n']} "
              f"(mean_forecast={rfb.get('mean_forecast')}, base_rate={rfb.get('base_rate')})"
              if rfb.get("n") else f"  TRUE recorded-forecast Brier = n/a ({rfb.get('note','')[:60]})")]
    for m, v in br["per_move"].items():
        floored = sel.get(m, v["forecast_p"]) != v["forecast_p"]
        lines.append(f"    {m:<20} forecast={v['forecast_p']:.3f} actual={v['actual_rate']:.3f} "
                     f"brier={v['brier']:.3f} miscal={v['miscalibration']:.3f}"
                     + ("  [selection-floored↑]" if floored else ""))
    if "error" not in elo:
        lines.append("  Elo leaderboard (cross-check):")
        for m, v in elo.items():
            lines.append(f"    {m:<20} elo={v['elo']:.0f} (close_rate={v['close_rate']:.3f}, n={v['n']})")
    return "\n".join(lines)


def autotune_strength(db_path: str | Path, base_k: float = DEFAULT_PRIOR_STRENGTH,
                      k_max: "float | None" = None, min_n: int = 12,
                      use_ratified: bool = True, source: str | None = None) -> "tuple[float, dict]":
    """#28 — the calibration→CONTROL loop. CLOSES the loop the dead monitors only measured: the
    RECORDED out-of-sample forecast Brier (`recorded_forecast_brier`, previously zero callers) now
    DRIVES the Beta prior strength k. Signal = the OVERFITTING GAP (recorded out-of-sample Brier −
    in-sample prior-vs-history Brier). gap>0 ⇒ our priors generalize worse than they fit ⇒ respond
    with MORE shrinkage (raise k toward k_max). Direction is UNAMBIGUOUS + SAFE: it can only pull
    priors CLOSER to the hand-set stubs (never below base_k ⇒ never more aggressive than today), so
    it cannot collapse the move distribution, and the free-move floor downstream is untouched.
    Data-gated: returns base_k (PARITY) until ≥min_n recorded forecasts exist. Returns (k, info)."""
    k_max = base_k * 3.0 if k_max is None else k_max
    rfb = recorded_forecast_brier(db_path, use_ratified=use_ratified, source=source)
    n = rfb.get("n", 0) or 0
    recorded = rfb.get("recorded_forecast_brier")
    if n < min_n or recorded is None:
        return base_k, {"tuned": False, "reason": "insufficient recorded forecasts", "n": n, "k": base_k}
    insample = brier_report(db_path, use_ratified=use_ratified, source=source).get("overall_brier")
    if insample is None:
        return base_k, {"tuned": False, "reason": "no in-sample brier", "n": n, "k": base_k}
    gap = recorded - insample                       # >0 ⇒ out-of-sample worse ⇒ overfitting
    if gap <= 0:
        return base_k, {"tuned": False, "reason": "no overfitting gap", "gap": round(gap, 4),
                        "recorded_brier": recorded, "insample_brier": insample, "n": n, "k": base_k}
    frac = min(1.0, gap / 0.25)                      # normalize by chance-Brier; bounded [0,1]
    k = max(base_k, min(k_max, base_k + frac * (k_max - base_k)))
    return round(k, 2), {"tuned": True, "gap": round(gap, 4), "recorded_brier": recorded,
                         "insample_brier": insample, "n": n, "base_k": base_k, "k": round(k, 2)}


def calibrated_priors(db_path: str | Path, strength: float = DEFAULT_PRIOR_STRENGTH) -> dict[str, float]:
    """The drop-in replacement for MOVE_PRIOR_P_CLOSE: {move: calibrated_p}. Falls back to the
    stub for any move/DB-miss (the posterior at n=0 == stub), so it is always safe to use."""
    if not Path(db_path).exists():
        return dict(MOVE_PRIOR_P_CLOSE)
    cal = calibrate_from_counts(_counts_from_db(db_path), strength=strength)
    return {m: v["p"] for m, v in cal.items()}


def selection_priors(db_path: str | Path, strength: float = DEFAULT_PRIOR_STRENGTH,
                     min_governed: int = 8) -> dict[str, dict]:
    """RECURSIVE SELF-TUNING priors (the kernel rating the move-policy selects on). Per move, score on
    the RATIFIED governance verdict once that move has ≥ `min_governed` governed attempts; otherwise on
    raw compile_ok. So the environment self-shifts from "what compiled" toward "what governance ratified"
    as the governed dataset accrues — a gamed-then-rejected move loses selection weight, an honestly-
    closing move gains it. Data-gated (sparse ratified → compile_ok = today's behaviour, parity) and
    free-move-floored (non-iatrogenic). Returns {move: {p, basis, governed_n, compile_n}}.

    This is the sensor→controller step done in ONE kernel place: every mode that loads selection priors
    inherits the self-tuning, no per-mode logic (the ONE-kernel invariant applied to the rating)."""
    if not Path(db_path).exists():
        return {m: {"p": p, "basis": "stub", "governed_n": 0, "compile_n": 0}
                for m, p in MOVE_PRIOR_P_CLOSE.items()}
    compile_counts = _counts_from_db(db_path)                       # {move: (closed, total)}
    ratified_counts = _counts_from_db(db_path, use_ratified=True)   # governed-only
    comp_cal = calibrate_from_counts(compile_counts, strength=strength)
    rat_cal = calibrate_from_counts(ratified_counts, strength=strength)
    out: dict[str, dict] = {}
    for move in MOVE_PRIOR_P_CLOSE:
        gov_n = ratified_counts.get(move, (0, 0))[1]
        comp_n = compile_counts.get(move, (0, 0))[1]
        if gov_n >= min_governed:                                  # enough governance signal → trust it
            out[move] = {"p": rat_cal[move]["p"], "basis": "ratified", "governed_n": gov_n, "compile_n": comp_n}
        else:                                                      # sparse governance → compile_ok (parity)
            out[move] = {"p": comp_cal[move]["p"], "basis": "compile_ok", "governed_n": gov_n, "compile_n": comp_n}
    return out


def selection_prior_values(db_path: str | Path, **kw) -> dict[str, float]:
    """{move: p} from `selection_priors` — the drop-in the worker feeds to `set_move_priors`."""
    return {m: v["p"] for m, v in selection_priors(db_path, **kw).items()}


def report(db_path: str | Path, strength: float = DEFAULT_PRIOR_STRENGTH) -> str:
    cal = calibrate_from_counts(_counts_from_db(db_path), strength=strength)
    lines = [f"[move-calibration] attempts DB: {db_path} (prior strength k={strength})"]
    for move, v in sorted(cal.items(), key=lambda kv: -kv[1]["p"]):
        lines.append(f"  {move:<24} p={v['p']:.3f} (stub {v['p_stub']:.2f}, "
                     f"shift {v['shift']:+.3f}) from {v['closed']}/{v['total']}")
    return "\n".join(lines)


# ── #103(2) SELF-LEARNED dispatch budgets ────────────────────────────────────────────────────────────
# A fixed per-dispatch wall is always arbitrary (the planner-guillotine foot-gun). The dispatch analogue of
# `cold_calibration.cold_safe_timeout`: learn the budget from the wallclock of attempts that ACTUALLY SUCCEEDED,
# instead of a hand-set default. Reuses the SAME admissibility filter as the move priors (#79/#90 re-baseline +
# apparatus-failure exclusion + carrier-liveness), so the 2026-06-08/09 dead-instrument rows can't poison the
# budget. PURE + DB legs separated so the math is unit-testable; both FAIL-SAFE (None ⇒ caller keeps its factory
# default — never starve a dispatch on thin/contaminated data). Wiring into the timeouts factory as an OPT-IN
# override is the follow-up (the attempts DB must accrue enough CLEAN successful rows first).
def _percentile(sorted_vals: "list[float]", p: float) -> float:
    """Nearest-rank percentile of an ASCENDING-sorted, non-empty list (`p` in [0, 100])."""
    k = int(round((p / 100.0) * (len(sorted_vals) - 1)))
    return sorted_vals[max(0, min(len(sorted_vals) - 1, k))]


def budget_from_durations(durations: "Iterable[float]", *, percentile: float = 90.0,
                          headroom: float = 1.5, floor: int, cap: int,
                          min_samples: int = 5) -> "Optional[int]":
    """SELF-LEARNED dispatch budget (#103(2)) = percentile(SUCCESSFUL durations) × headroom, clamped to
    [floor, cap]. Returns None when fewer than `min_samples` positive durations are supplied (insufficient data
    ⇒ the caller keeps its hand-set factory default — FAIL-SAFE: thin data never starves a dispatch). PURE (no
    DB / no env) so the percentile + clamp logic is unit-testable in isolation."""
    vals = sorted(float(d) for d in durations if d and float(d) > 0)
    if len(vals) < max(1, min_samples):
        return None
    return int(max(floor, min(cap, round(_percentile(vals, percentile) * headroom))))


def learned_dispatch_budget(db_path: "str | Path", *, move: "Optional[str]" = None,
                            percentile: float = 90.0, headroom: float = 1.5, floor: int, cap: int,
                            min_samples: int = 5, run_tag: "Optional[str]" = None) -> "Optional[int]":
    """Learn a dispatch budget from SUCCESSFUL attempts' `wallclock_s` in the calibration DB, ADMISSIBILITY-
    FILTERED exactly like the move priors (#79/#90: re-baseline date + apparatus-failure-class exclusion +
    carrier-liveness), optionally scoped to one `move` (via PROVIDER_TO_MOVE) and/or `run_tag`. "Successful" =
    the same governance close-score the priors use (`COALESCE(ratified, compile_ok) > 0`). Returns None when the
    DB is unreadable / lacks `wallclock_s` / yields fewer than `min_samples` admissible successful rows ⇒ the
    caller keeps its factory default (FAIL-SAFE). The self-learned analogue of the hand-set timeouts factory."""
    try:
        with sqlite3.connect(str(db_path)) as con:
            if not _has_column(con, "attempts", "wallclock_s"):
                return None
            effective = _score_ratified_default() and _has_column(con, "attempts", "ratified")
            where = ["wallclock_s IS NOT NULL", "wallclock_s > 0", f"{_close_score_expr(effective)} > 0"]
            params: "list" = []
            if move is not None:
                provs = [p for p, m in PROVIDER_TO_MOVE.items() if m == move]
                if not provs:
                    return None   # unknown move ⇒ no provider maps to it ⇒ no admissible data
                where.append("provider IN (%s)" % ",".join("?" * len(provs))); params.extend(provs)
            if run_tag is not None and _has_column(con, "attempts", "run_tag"):
                where.append("run_tag = ?"); params.append(run_tag)
            if _admissible_filter_on() and _has_column(con, "attempts", "attempt_at"):
                where.append("attempt_at >= ?"); params.append(_admissible_since())
                where.append("COALESCE(error_class,'none') NOT IN (%s)" % ",".join("?" * len(_APPARATUS_FAILURE_CLASSES)))
                params.extend(_APPARATUS_FAILURE_CLASSES)
            if _admissible_filter_on() and _has_column(con, "attempts", "carrier_live"):
                where.append("COALESCE(carrier_live, 1) != 0")
            rows = con.execute(f"SELECT wallclock_s FROM attempts WHERE {' AND '.join(where)}", params).fetchall()
    except sqlite3.Error:
        return None
    return budget_from_durations((r[0] for r in rows), percentile=percentile, headroom=headroom,
                                 floor=floor, cap=cap, min_samples=min_samples)


def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # n=0 ⇒ posterior == stub exactly (no data, no shift; every move safe by default).
    ok("no_data_equals_stub", abs(beta_posterior_mean(0.25, 0, 0, 8.0) - 0.25) < 1e-9)
    # strong negative signal (0/29) shifts a 0.25 stub DOWN substantially.
    p_nh = beta_posterior_mean(0.25, 0, 29, 8.0)
    ok("strong_zero_shifts_down", p_nh < 0.10 and p_nh > 0.0)
    # matched signal (11/29 vs stub 0.35) stays near the stub.
    p_warm = beta_posterior_mean(0.35, 11, 29, 8.0)
    ok("matched_stays_near_stub", abs(p_warm - 0.35) < 0.06)
    # weak data (1 attempt) barely moves the prior (anti-laundering).
    p_weak = beta_posterior_mean(0.30, 0, 1, 8.0)
    ok("weak_data_near_stub", abs(p_weak - 0.30) < 0.05)
    # calibrate_from_counts covers every stub move; the live shape: native_hammer (FREE) 0/29,
    # cold_shot (COSTLY) 0/18, claude_warm 11/29.
    cal = calibrate_from_counts({MOVE_NATIVE_HAMMER: (0, 29), MOVE_COLD_SHOT: (0, 18),
                                 MOVE_CLAUDE_WARM: (11, 29)})
    ok("covers_all_moves", set(cal) == set(MOVE_PRIOR_P_CLOSE))
    # NON-IATROGENIC: the FREE move (native_hammer) is NOT down-weighted (held at stub, floored),
    # so the policy still always tries it; the COSTLY dead move (cold_shot) IS down-weighted —
    # that is where the lift is (stop spending budget on a 0/18 move).
    ok("free_move_not_downweighted",
       cal[MOVE_NATIVE_HAMMER]["p"] == MOVE_PRIOR_P_CLOSE[MOVE_NATIVE_HAMMER]
       and cal[MOVE_NATIVE_HAMMER]["free_floored"])
    ok("costly_dead_move_downweighted",
       cal[MOVE_COLD_SHOT]["p"] < 0.15 and not cal[MOVE_COLD_SHOT]["free_floored"])
    ok("warm_held_near_stub", abs(cal[MOVE_CLAUDE_WARM]["p"] - 0.35) < 0.06)
    ok("conjecture_no_data_keeps_stub",
       abs(cal[MOVE_CONJECTURE]["p"] - MOVE_PRIOR_P_CLOSE[MOVE_CONJECTURE]) < 1e-9)
    # calibrated_priors returns a usable dict over all moves.
    pri = {m: v["p"] for m, v in cal.items()}
    ok("priors_dict_complete", all(isinstance(pri[m], float) for m in MOVE_PRIOR_P_CLOSE))

    # RE-BASELINE regression (RCA 2026-06-18): legacy `rejected_negative_control` rows are dead-instrument
    # mislabels — they must be EXCLUDED from the cheat rate (not counted as attempts/wrong_target), while the
    # truthful labels (`rejected_anti_laundering`/`rejected_mnc_leakage`) DO count as cheats. Without this the
    # contamination drove real provers' priors down (claude_warm → p=0.113).
    import sqlite3 as _sq, tempfile as _tf, os as _os
    _td = _tf.mkdtemp(prefix="mc_rebaseline_")
    _db = _os.path.join(_td, "t.db")
    _c = _sq.connect(_db)
    _c.execute("CREATE TABLE attempts(move TEXT, outcome TEXT, ratified INT, wallclock_s REAL)")
    _c.executemany("INSERT INTO attempts VALUES(?,?,?,?)",
                   [("claude_warm", "closed", 1, 5.0)] * 3
                   + [("claude_warm", "rejected_negative_control", 0, 5.0)] * 5   # legacy mislabel → excluded
                   + [("claude_warm", "rejected_anti_laundering", 0, 5.0)])       # genuine cheat → counted
    _c.commit(); _c.close()
    _t = exogenous_move_telemetry(_db, min_attempts=1)["by_move"]["claude_warm"]
    ok("rebaseline: legacy rejected_negative_control EXCLUDED from attempts",
       _t["attempts"] == 4 and _t["legacy_inadmissible"] == 5)
    ok("rebaseline: genuine anti_laundering still counts as wrong_target", _t["wrong_target"] == 1)
    ok("rebaseline: useful_exit_rate is the TRUE 0.75, not the poisoned 0.33", _t["useful_exit_rate"] == 0.75)
    import shutil as _sh
    _sh.rmtree(_td, ignore_errors=True)

    # ── per-(move, error_class) nested shrinkage (#18) ──
    # A SPARSE cell sits at the MARGINAL move rate (data-gated → parity with marginal calibration).
    per_move = {MOVE_CLAUDE_WARM: (11, 29)}
    sparse = calibrate_by_error_class({(MOVE_CLAUDE_WARM, "type_mismatch"): (0, 1)}, per_move)
    ok("sparse_cell_sits_at_marginal",
       abs(sparse[(MOVE_CLAUDE_WARM, "type_mismatch")]["p"]
           - sparse[(MOVE_CLAUDE_WARM, "type_mismatch")]["p_marginal"]) < 0.05)
    # A DENSE cell with a strong signal moves OFF the marginal (sharpens): warm is great on
    # unknown_identifier (20/22) but poor on unsolved_goals (1/20) → the cells separate.
    dense = calibrate_by_error_class(
        {(MOVE_CLAUDE_WARM, "unknown_identifier"): (20, 22),
         (MOVE_CLAUDE_WARM, "unsolved_goals"): (1, 20)},
        {MOVE_CLAUDE_WARM: (21, 42)})
    p_good = dense[(MOVE_CLAUDE_WARM, "unknown_identifier")]["p"]
    p_bad = dense[(MOVE_CLAUDE_WARM, "unsolved_goals")]["p"]
    ok("dense_cells_separate_by_class", p_good - p_bad > 0.25)
    # FREE-move floor is inherited: a free move is never down-weighted below its marginal per class.
    free = calibrate_by_error_class({(MOVE_NATIVE_HAMMER, "deep_recursion"): (0, 15)},
                                    {MOVE_NATIVE_HAMMER: (0, 5)})
    ok("free_move_floor_inherited_per_class",
       free[(MOVE_NATIVE_HAMMER, "deep_recursion")]["free_floored"]
       and free[(MOVE_NATIVE_HAMMER, "deep_recursion")]["p"]
           >= free[(MOVE_NATIVE_HAMMER, "deep_recursion")]["p_marginal"] - 1e-9)
    # empty DB → calibrated_priors_for_class returns the stubs (safe fallback).
    import tempfile as _tf, os as _os
    miss = _tf.mktemp(suffix=".db")
    ok("missing_db_returns_stubs",
       calibrated_priors_for_class(miss, "anything") == dict(MOVE_PRIOR_P_CLOSE))
    # REGRESSION (cold-review): a DB that EXISTS but has no `attempts` table must fall back to
    # stubs, not raise.
    exists_no_table = _tf.mktemp(suffix=".db")
    sqlite3.connect(exists_no_table).execute("CREATE TABLE other(x)")
    try:
        ok("existing_db_no_attempts_table_returns_stubs",
           calibrated_priors_for_class(exists_no_table, "x") == dict(MOVE_PRIOR_P_CLOSE)
           and calibrated_priors(exists_no_table) == dict(MOVE_PRIOR_P_CLOSE))
    finally:
        _os.path.exists(exists_no_table) and _os.remove(exists_no_table)

    # ── forecast (honest, no floor) vs selection (floored) ──
    honest = calibrate_from_counts({MOVE_NATIVE_HAMMER: (0, 29)}, floor=False)
    floored_sel = calibrate_from_counts({MOVE_NATIVE_HAMMER: (0, 29)}, floor=True)
    ok("honest_forecast_unfloored_below_stub",
       honest[MOVE_NATIVE_HAMMER]["p"] < honest[MOVE_NATIVE_HAMMER]["p_stub"]
       and not honest[MOVE_NATIVE_HAMMER]["free_floored"])
    ok("selection_still_floored", floored_sel[MOVE_NATIVE_HAMMER]["free_floored"]
       and floored_sel[MOVE_NATIVE_HAMMER]["p"] == floored_sel[MOVE_NATIVE_HAMMER]["p_stub"])

    # ── brier_report on a tiny synthetic DB ──
    bdb = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(bdb)
    con.execute("CREATE TABLE attempts(provider TEXT, compile_ok INT, error_class TEXT)")
    con.executemany("INSERT INTO attempts(provider,compile_ok) VALUES(?,?)",
                    [("native_hammer", 0)] * 10 + [("claude_opus_warm", 1)] * 6 + [("claude_opus_warm", 0)] * 4)
    con.commit()
    br = brier_report(bdb)
    ok("brier_overall_below_chance", br["overall_brier"] is not None and br["overall_brier"] < 0.25)
    ok("brier_flags_native_hammer_miscal",
       br["per_move"][MOVE_NATIVE_HAMMER]["actual_rate"] == 0.0)
    el = move_elo(bdb)
    ok("elo_ranks_better_move_higher",
       "error" not in el and el[MOVE_CLAUDE_WARM]["elo"] > el[MOVE_NATIVE_HAMMER]["elo"])
    _os.path.exists(bdb) and _os.remove(bdb)

    # ── RATIFIED scoring + source slice: a gamed compile_ok=1 that's ratified=0 must NOT count as a win ──
    rdb = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(rdb)
    con.execute("CREATE TABLE attempts(row_id TEXT, provider TEXT, compile_ok INT, ratified INT)")
    # ad-hoc claude_warm: 4 compiled, but 2 were rejected by governance (ratified=0), 2 ratified=1
    con.executemany("INSERT INTO attempts(row_id,provider,compile_ok,ratified) VALUES(?,?,?,?)",
                    [("adhoc::t", "claude_opus_warm", 1, 1), ("adhoc::t", "claude_opus_warm", 1, 1),
                     ("adhoc::t", "claude_opus_warm", 1, 0), ("adhoc::t", "claude_opus_warm", 1, 0),
                     ("APN_x", "claude_opus_warm", 1, None)])  # batch, ungoverned → excluded from ratified
    con.commit()
    by_compile = _counts_from_db(rdb)                                   # compile_ok: 5/5
    by_ratified = _counts_from_db(rdb, use_ratified=True)               # ratified: 2/4 (the cheats are losses)
    by_adhoc = _counts_from_db(rdb, use_ratified=True, source="adhoc::")  # ad-hoc slice only
    ok("compile_ok_counts_all", by_compile[MOVE_CLAUDE_WARM] == (5, 5))
    ok("ratified_excludes_cheats_and_ungoverned",
       by_ratified[MOVE_CLAUDE_WARM] == (2, 4))  # 4 governed (2 ratified, 2 rejected); APN ungoverned excluded
    ok("source_slice_adhoc_only", by_adhoc[MOVE_CLAUDE_WARM] == (2, 4))
    # ── RECURSIVE SELF-TUNING selection_priors: shifts compile_ok → ratified as governed data accrues ──
    seldb = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(seldb)
    con.execute("CREATE TABLE attempts(row_id TEXT, provider TEXT, compile_ok INT, ratified INT)")
    # claude_warm: many compile-wins but governance REJECTED most (gamed) — 12 governed, 2 ratified.
    rows = ([("r", "claude_opus_warm", 1, 1)] * 2 + [("r", "claude_opus_warm", 1, 0)] * 10
            + [("r", "native_hammer", 0, None)] * 3)  # native sparse-governed
    con.executemany("INSERT INTO attempts(row_id,provider,compile_ok,ratified) VALUES(?,?,?,?)", rows)
    con.commit()
    sel = selection_priors(seldb, min_governed=8)
    ok("selection_warm_uses_ratified_when_rich",
       sel[MOVE_CLAUDE_WARM]["basis"] == "ratified" and sel[MOVE_CLAUDE_WARM]["governed_n"] == 12)
    ok("selection_ratified_downweights_gamed",   # 2/12 ratified ≪ 12/12 compile_ok → lower p
       sel[MOVE_CLAUDE_WARM]["p"] < 0.35)
    ok("selection_sparse_governed_uses_compile_ok",
       sel[MOVE_NATIVE_HAMMER]["basis"] in ("compile_ok", "stub"))
    _os.path.exists(seldb) and _os.remove(seldb)

    # ── per-(move,error_class) CONTEXT prior is ratified-aware too (the _cells_from_db poisoning fix) ──
    # Closes the last compile_ok-blind consumer: a gamed-then-REJECTED closure must drag the per-class
    # prior down exactly as it does the marginal selection prior. `COALESCE(ratified, compile_ok)`.
    cdb = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(cdb)
    con.execute("CREATE TABLE attempts(row_id TEXT, provider TEXT, compile_ok INT, error_class TEXT, ratified INT)")
    # cold_shot on unsolved_goals: 4 compiled, 3 governance-REJECTED (ratified=0), 1 ratified=1.
    con.executemany("INSERT INTO attempts(row_id,provider,compile_ok,error_class,ratified) VALUES(?,?,?,?,?)",
                    [("r", "codex_gpt5", 1, "unsolved_goals", v) for v in (1, 0, 0, 0)])
    con.commit(); con.close()
    _eff = calibrated_priors_for_class(cdb, "unsolved_goals")                 # default: ratified-aware
    _prev = _os.environ.get("ZTARE_CALIBRATION_SCORE")
    _os.environ["ZTARE_CALIBRATION_SCORE"] = "compile_ok"
    _leg = calibrated_priors_for_class(cdb, "unsolved_goals")                 # parity escape: legacy
    if _prev is None:
        _os.environ.pop("ZTARE_CALIBRATION_SCORE", None)
    else:
        _os.environ["ZTARE_CALIBRATION_SCORE"] = _prev
    ok("context_prior_ratified_downweights_gamed", _eff[MOVE_COLD_SHOT] < _leg[MOVE_COLD_SHOT])
    ok("context_prior_compile_ok_escape_reverts", _leg[MOVE_COLD_SHOT] > 0.5)
    _os.path.exists(cdb) and _os.remove(cdb)

    # REGRESSION (cold-review): exact source must NOT swallow a longer-prefix row_id.
    sdb = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(sdb)
    con.execute("CREATE TABLE attempts(row_id TEXT, provider TEXT, compile_ok INT, ratified INT)")
    con.executemany("INSERT INTO attempts(row_id,provider,compile_ok) VALUES(?,?,?)",
                    [("adhoc::foo", "claude_opus_warm", 1), ("adhoc::foobar", "claude_opus_warm", 0)])
    con.commit()
    foo = _counts_from_db(sdb, source="adhoc::foo")       # exact → only foo (1/1)
    mode = _counts_from_db(sdb, source="adhoc::")          # mode prefix → both (1/2)
    ok("source_exact_no_prefix_swallow", foo[MOVE_CLAUDE_WARM] == (1, 1))
    ok("source_mode_prefix_includes_all", mode[MOVE_CLAUDE_WARM] == (1, 2))
    _os.path.exists(sdb) and _os.remove(sdb)
    _os.path.exists(rdb) and _os.remove(rdb)

    # ── TRUE recorded-forecast Brier: scores the est_p_close logged at dispatch time vs outcome ──
    fdb = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(fdb)
    con.execute("CREATE TABLE attempts(row_id TEXT, provider TEXT, compile_ok INT, ratified INT, est_p_close REAL)")
    # forecasts: 0.9 then closed(1), 0.1 then failed(0)  → perfect-ish → low Brier
    con.executemany("INSERT INTO attempts(row_id,provider,compile_ok,est_p_close) VALUES(?,?,?,?)",
                    [("adhoc::t", "claude_opus_warm", 1, 0.9), ("adhoc::t", "claude_opus_warm", 0, 0.1)])
    con.commit()
    rfb = recorded_forecast_brier(fdb)
    ok("recorded_forecast_brier_computed", rfb["n"] == 2 and rfb["recorded_forecast_brier"] < 0.02)
    rfb_empty = recorded_forecast_brier(_tf.mktemp(suffix=".db"))
    ok("recorded_forecast_brier_empty_safe", rfb_empty["n"] == 0)
    _os.path.exists(fdb) and _os.remove(fdb)

    # ── BIC calibration-model selection: split-by-error-class only when DATA justifies it ──
    ok("loglik_perfect_fit_beats_noisy", _binomial_loglik([(10, 10)]) > _binomial_loglik([(5, 10)]))
    # NO class dependence: warm closes ~half regardless of class (10/20 vs 10/20). The split buys
    # NO likelihood gain, so BIC pays its extra parameter for nothing → keep POOLED (the honest
    # "don't carve the priors on noise" case). (NB: BIC at ~1 obs/cell can perfectly-separate and
    # over-split — a known small-N property; the existing nested shrinkage handles within-split
    # sparse cells, so the two are complementary.)
    cdb = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(cdb)
    con.execute("CREATE TABLE attempts(provider TEXT, compile_ok INT, error_class TEXT)")
    con.executemany("INSERT INTO attempts(provider,compile_ok,error_class) VALUES(?,?,?)",
                    [("claude_opus_warm", 1, "unknown_identifier")] * 10 + [("claude_opus_warm", 0, "unknown_identifier")] * 10
                    + [("claude_opus_warm", 1, "unsolved_goals")] * 10 + [("claude_opus_warm", 0, "unsolved_goals")] * 10)
    con.commit()
    sparse_sel = select_calibration_model(cdb)
    ok("bic_pools_when_no_class_signal", sparse_sel["model"] == "pooled" and sparse_sel["delta"] < 0)
    _os.path.exists(cdb) and _os.remove(cdb)
    # RICH + REAL class dependence: warm is 30/32 on unknown_identifier but 2/30 on unsolved_goals;
    # the likelihood gain from splitting now dwarfs the parameter penalty → BIC picks SPLIT.
    cdb2 = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(cdb2)
    con.execute("CREATE TABLE attempts(provider TEXT, compile_ok INT, error_class TEXT)")
    con.executemany("INSERT INTO attempts(provider,compile_ok,error_class) VALUES(?,?,?)",
                    [("claude_opus_warm", 1, "unknown_identifier")] * 30 + [("claude_opus_warm", 0, "unknown_identifier")] * 2
                    + [("claude_opus_warm", 1, "unsolved_goals")] * 2 + [("claude_opus_warm", 0, "unsolved_goals")] * 28)
    con.commit()
    rich_sel = select_calibration_model(cdb2)
    ok("bic_splits_on_rich_class_dependence", rich_sel["model"] == "split" and rich_sel["delta"] > 0)
    ok("bic_empty_db_pooled", select_calibration_model(_tf.mktemp(suffix=".db"))["model"] == "pooled")
    _os.path.exists(cdb2) and _os.remove(cdb2)

    # ── UCB-over-moves (reachability bandit) ──────────────────────────────────────────────────
    _costs = {"native_hammer": 0.0, "claude_warm": 3.0, "falsify": 4.0}
    # c=0 ⇒ UCB == calibrated-greedy (Q verbatim), no exploration term.
    _greedy = ucb_move_scores({"native_hammer": 0.05, "claude_warm": 0.35, "falsify": 0.20},
                              {"native_hammer": 29, "claude_warm": 29, "falsify": 0}, _costs, c=0.0)
    ok("ucb_c0_is_calibrated_greedy",
       abs(_greedy["claude_warm"] - 0.35) < 1e-9 and abs(_greedy["falsify"] - 0.20) < 1e-9
       and max(_greedy, key=_greedy.get) == "claude_warm")
    # REACHABILITY: at a real c, a NEVER-pulled low-Q move (falsify n=0) outranks a HEAVILY-pulled
    # equally-low-Q move (native n=200) — the exploration bonus makes the dormant move selectable.
    _ub = ucb_move_scores({"native_hammer": 0.05, "falsify": 0.05},
                          {"native_hammer": 200, "falsify": 0}, _costs, c=1.0, lam=0.0)
    ok("ucb_reachability_dormant_outranks_saturated", _ub["falsify"] > _ub["native_hammer"])
    # At the DEFAULT (short-horizon) c, a strong-Q proven move still beats a weak-Q dormant one — the modest
    # exploration bonus does NOT steamroll the calibrated value on a fresh node (it only gently promotes).
    _ub2 = ucb_move_scores({"claude_warm": 0.45, "falsify": 0.05},
                           {"claude_warm": 20, "falsify": 0}, _costs)  # default c=0.3
    ok("ucb_exploitation_survives_default_c", _ub2["claude_warm"] > _ub2["falsify"])
    # COST-DISCOUNT: with equal Q and equal (zero) visits but N>0 (some OTHER move pulled), the cheaper move
    # gets the larger exploration bonus. (When NOTHING is pulled, N=0 ⇒ no bonus ⇒ pure-Q cold start.)
    _ub3 = ucb_move_scores({"native_hammer": 0.20, "falsify": 0.20},
                           {"claude_warm": 10}, _costs, c=1.0, lam=0.5)
    ok("ucb_cost_discount_favours_cheap", _ub3["native_hammer"] > _ub3["falsify"])
    # cold start (nothing pulled, N=0) ⇒ UCB == pure Q (no exploration term to add).
    _ub4 = ucb_move_scores({"native_hammer": 0.20, "falsify": 0.20}, {}, _costs, c=1.0, lam=0.5)
    ok("ucb_cold_start_is_pure_Q", abs(_ub4["native_hammer"] - _ub4["falsify"]) < 1e-12)
    # move_visit_counts: reads the canonical `move` column for ALL moves (incl. the non-closure tail).
    vdb = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(vdb)
    con.execute("CREATE TABLE attempts(move TEXT, run_tag TEXT)")
    con.executemany("INSERT INTO attempts(move,run_tag) VALUES(?,?)",
                    [("claude_warm", "r1")] * 5 + [("falsify", "r1")] * 2 + [("native_hammer", "r2")] * 3)
    con.commit(); con.close()
    _vc = move_visit_counts(vdb)
    ok("visit_counts_all_moves", _vc.get("claude_warm") == 5 and _vc.get("falsify") == 2
       and _vc.get("native_hammer") == 3)
    ok("visit_counts_run_tag_slice", move_visit_counts(vdb, run_tag="r1").get("native_hammer", 0) == 0)
    ok("visit_counts_missing_move_col_empty", move_visit_counts(_tf.mktemp(suffix=".db")) == {})
    _os.path.exists(vdb) and _os.remove(vdb)
    # WARM-START FALLBACK (red-team fix 2026-06-07): a DB with the `provider` column but NO `move` column (the
    # un-backfilled live shape) must STILL yield the production skew via PROVIDER_TO_MOVE — not {} (which would
    # collapse UCB to cold-start pure-Q and re-starve the tail).
    pdb = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(pdb)
    con.execute("CREATE TABLE attempts(provider TEXT, compile_ok INT)")
    con.executemany("INSERT INTO attempts(provider,compile_ok) VALUES(?,?)",
                    [("native_hammer", 0)] * 21 + [("claude_opus_warm", 1)] * 11 + [("claude_opus", 0)] * 3)
    con.commit(); con.close()
    _pf = move_visit_counts(pdb)
    ok("visit_counts_provider_fallback_warm_start",
       _pf.get(MOVE_NATIVE_HAMMER) == 21 and _pf.get(MOVE_CLAUDE_WARM) == 11 and _pf.get(MOVE_COLD_SHOT) == 3)
    _os.path.exists(pdb) and _os.remove(pdb)
    # SCALE-INVARIANCE AT PRODUCTION N (red-team #4.5: the old un-scaled bonus at production N was ~2× the
    # Q-span, which let a dormant move steamroll proven moves). The scaled bonus must stay BOUNDED by the
    # Q-span — a dormant move can be lifted by at most ~one Q-spread, NOT dominate it — at the default c and
    # production N. (Pure-function property; the POLICY also excludes the strategist tail from the pool —
    # tested in governed_dag_search._selftest.)
    _prodN_visits = {MOVE_NATIVE_HAMMER: 1500, MOVE_CLAUDE_WARM: 800, MOVE_COLD_SHOT: 300,
                     MOVE_FRONTIER: 120, MOVE_CONJECTURE: 40}  # closure menu; tail absent ⇒ n=0
    _prodN_priors = dict(MOVE_PRIOR_P_CLOSE)
    _span = max(_prodN_priors.values()) - min(_prodN_priors.values())
    _sc = ucb_move_scores(_prodN_priors, _prodN_visits, MOVE_COST)  # default c=0.15
    _falsify_bonus = _sc["falsify"] - _prodN_priors["falsify"]   # dormant (n=0), the most-explored move
    ok("ucb_dormant_bonus_bounded_by_qspan_at_production_N", 0.0 < _falsify_bonus < _span)
    # within the CLOSURE menu, the proven warm is not steamrolled by a dormant LOWER-Q closer (native 0.25,
    # dormant only if absent — here native is saturated; the value-order is the intended behavior).
    ok("ucb_proven_warm_beats_saturated_lower_value_native_at_production_N",
       _sc[MOVE_CLAUDE_WARM] > _sc[MOVE_NATIVE_HAMMER])

    # ── Exogenous-move telemetry + promotion gate ─────────────────────────────────────────────────────
    tdb = _tf.mktemp(suffix=".db")
    con = sqlite3.connect(tdb)
    con.execute("CREATE TABLE attempts(move TEXT, outcome TEXT, ratified INT, wallclock_s REAL, run_tag TEXT)")
    con.executemany("INSERT INTO attempts(move,outcome,ratified,wallclock_s,run_tag) VALUES(?,?,?,?,?)",
                    # witness_transport: 4 ratified closes + 1 miss ⇒ useful 4/5, no false-ratifications ⇒ PROMOTABLE
                    [("witness_transport", "closed", 1, 2.0, "r")] * 4 + [("witness_transport", "failed_compile", -1, 1.0, "r")]
                    # falsify: 2 falsified (useful) + 3 no_falsifier ⇒ useful 2/5 ⇒ promotable (baseline 0)
                    + [("falsify", "falsified", -1, 3.0, "r")] * 2 + [("falsify", "no_falsifier", -1, 2.0, "r")] * 3
                    # corroborate: a GAMED closure governance REJECTED (closed, ratified=0) ⇒ tripwire, NOT promotable
                    + [("corroborate", "closed", 0, 4.0, "r")] * 5)
    con.commit(); con.close()
    rep = exogenous_move_telemetry(tdb, run_tag="r", min_attempts=5, baseline_rate=0.0)
    wt = rep["by_move"]["witness_transport"]; fl = rep["by_move"]["falsify"]; cr = rep["by_move"]["corroborate"]
    ok("exo_tele: witness_transport useful-rate + ratified closes",
       wt["useful_exits"] == 4 and wt["ratified_closes"] == 4 and wt["useful_exit_rate"] == 0.8
       and wt["false_ratifications"] == 0 and wt["promotion_eligible"] is True)
    ok("exo_tele: falsify useful exits (falsified counts, no_falsifier doesn't)",
       fl["useful_exits"] == 2 and fl["no_positive"] == 3 and fl["useful_exit_rate"] == 0.4)
    ok("exo_tele: a gamed closure (closed+ratified=0) is WRONG-target + tripwire, NOT useful/promotable",
       cr["wrong_target"] == 5 and cr["false_ratifications"] == 5 and cr["useful_exits"] == 0
       and cr["promotion_eligible"] is False)
    ok("exo_tele: headline promotable + tripwire",
       "witness_transport" in rep["headline"]["promotable"] and "falsify" in rep["headline"]["promotable"]
       and "corroborate" in rep["headline"]["tripwire_false_ratifications"]
       and "corroborate" not in rep["headline"]["promotable"])
    ok("exo_tele: empty/no-move-col DB is safe", exogenous_move_telemetry(_tf.mktemp(suffix=".db"))["by_move"] == {})
    _os.path.exists(tdb) and _os.remove(tdb)

    # ── #103(2) self-learned dispatch budget — PURE leg ──
    ok("budget: <min_samples ⇒ None (fail-safe)",
       budget_from_durations([10, 20, 30], min_samples=5, floor=30, cap=1800) is None)
    ok("budget: p90×headroom (p90 of 10..100 = 90 ×1.5 = 135)",
       budget_from_durations([10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
                             percentile=90, headroom=1.5, floor=30, cap=1800, min_samples=5) == 135)
    ok("budget: cap clamps a huge p90",
       budget_from_durations([5000] * 8, percentile=90, headroom=1.5, floor=30, cap=1800, min_samples=5) == 1800)
    ok("budget: floor clamps tiny durations",
       budget_from_durations([1, 1, 1, 1, 1, 1], percentile=90, headroom=1.5, floor=30, cap=1800, min_samples=5) == 30)
    ok("budget: non-positive durations filtered (then <min_samples ⇒ None)",
       budget_from_durations([0, -1, None, 5], min_samples=5, floor=30, cap=1800) is None)

    # ── #103(2) self-learned dispatch budget — DB leg (admissibility-filtered) ──
    ldb = _tf.mktemp(suffix=".db"); con = sqlite3.connect(ldb)
    con.execute("CREATE TABLE attempts(row_id TEXT, provider TEXT, compile_ok INT, ratified INT, "
                "wallclock_s REAL, attempt_at TEXT, error_class TEXT, carrier_live INT)")
    good = [(f"g{i}", "claude_opus_warm", 1, 1, float(w), "2026-06-10T00:00:00+00:00", "none", 1)
            for i, w in enumerate([60, 70, 80, 90, 100, 200])]
    bad = [("b1", "claude_opus_warm", 1, 1, 9999.0, "2026-06-01T00:00:00+00:00", "none", 1),    # pre-cutoff
           ("b2", "claude_opus_warm", 1, 1, 9999.0, "2026-06-10T00:00:00+00:00", "none", 0),    # dead carrier
           ("b3", "claude_opus_warm", 0, 0, 9999.0, "2026-06-10T00:00:00+00:00", "timeout", 1), # apparatus-fail
           ("b4", "claude_opus_warm", 0, 0, 9999.0, "2026-06-10T00:00:00+00:00", "none", 1)]    # not successful
    con.executemany("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)", good + bad)
    con.commit(); con.close()
    _lb = learned_dispatch_budget(ldb, move=MOVE_CLAUDE_WARM, percentile=90, headroom=1.5,
                                  floor=30, cap=1800, min_samples=5)
    ok("learned_budget: admissible successful rows only — excludes the 9999 contamination (pre-cutoff/dead/fail)",
       _lb is not None and _lb < 1000)   # the 9999s would slam it to cap=1800 if any leaked through the filter
    ok("learned_budget: thin/no admissible data ⇒ None (fail-safe)",
       learned_dispatch_budget(ldb, move=MOVE_FRONTIER, floor=30, cap=1800, min_samples=5) is None)
    _os.path.exists(ldb) and _os.remove(ldb)
    _nwdb = _tf.mktemp(suffix=".db"); con = sqlite3.connect(_nwdb)
    con.execute("CREATE TABLE attempts(provider TEXT, compile_ok INT)"); con.commit(); con.close()
    ok("learned_budget: missing wallclock_s column ⇒ None", learned_dispatch_budget(_nwdb, floor=30, cap=1800) is None)
    _os.path.exists(_nwdb) and _os.remove(_nwdb)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="GP-246 Arc H move-prior calibration from attempts DB")
    ap.add_argument("--db", default=None, help="solver_lane_attempts.db path")
    ap.add_argument("--strength", type=float, default=DEFAULT_PRIOR_STRENGTH)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--forecast", action="store_true",
                    help="print the forecast/Brier/Elo loop report (honest forecast + calibration audit)")
    ap.add_argument("--ratified", action="store_true",
                    help="score the GOVERNANCE verdict (ratified), not raw compile_ok (honest capability)")
    ap.add_argument("--source", default=None,
                    help="row_id prefix slice, e.g. 'adhoc::' for ad-hoc capability vs batch")
    a = ap.parse_args(argv)
    if a.selftest or not a.db:
        return _self_test()
    print(forecast_loop_report(a.db, use_ratified=a.ratified, source=a.source)
          if a.forecast else report(a.db, a.strength))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
