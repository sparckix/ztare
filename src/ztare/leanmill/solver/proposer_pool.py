"""GOVERNED PROPOSER POOL — the isomorphism-surfaced "swarm, done tastefully" (2026-06-20).

NOT a swarm of provers. `research_isomorphism` on our own seam (diverse parallel proposers + ONE serial exact
verifier over a dependency DAG) returned an IMPOSSIBILITY pass that fences off the copy:
  • CVP P-completeness  → verification is inherently SERIAL (no speculative batching / parallel-validate).
  • Haldane's dilemma   → the serial verifier caps the closure RATE; swarm size past it is wasted.
  • No Free Lunch       → no STATIC budget split across proposers is optimal; allocation must be ADAPTIVE.
  • Graham's anomalies  → proposers firing greedily at max budget make the bottleneck WORSE.

So the edge is NOT parallelism — it is the GOVERNED COMPOSITION the SOLVE candidates converge on:

  out-of-order DIVERSE propose (Parallel-Tempering / Reorder-Buffer)
    → live ANTI-CORRELATION so the pool never redundantly attacks one (node, approach)
        (Pauli exclusion / CSMA backoff / Competitive-Exclusion / VOQ-iSLIP — FOUR fields agreed)
    → cheap EV CHAMPION-select, verify in EV order, commit the FIRST that closes
        (Multiple-Try-Metropolis / Branch-and-Price / BLAST seed-and-extend)
    → SINGLE SERIAL kernel COMMIT (CVP says it MUST stay serial; the soundness boundary is UNCHANGED)
    → verdict feedback → per-model priors (NFL: adaptive allocation, `move_calibration.calibrate_by_model`).

REUSE, not rebuild: this module is only the CONTROL STRUCTURE. The cheap gate reuses the forecast-EV shape
(`P·value − λ·cost`) with `P = per-model prior × the proposer's own est_p`; the per-model prior reuses
`move_calibration.calibrate_by_model`; the occupancy normaliser reuses the proof_cache key; the actual
proposing (warm per-tag sessions) and verifying (the kernel) are INJECTED — no new solving, no new soundness
surface. DEFAULT-ON (`ZTARE_LEANMILL_PROPOSER_POOL`, `=0` reverts to the single leaf, native-gated so trivial
goals never pay the k dispatches); the existing single-leaf path is byte-identical when off.
"""
from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

# NO HARDCODED PRIORS (architecture quasi-invariant): the per-model priors are MEASURED (calibrate_by_model,
# Beta posteriors from the attempts DB). The only scalars here are the cold-start fallback (for a model with
# ZERO history anywhere) and the EV cost-weight — both env-overridable, and the cold-start is DATA-DRIVEN
# (the empirical base rate of the measured models) whenever any data exists; the constant is a last resort
# only on a totally empty DB. So nothing in the live ranking is a magic number once the system has run once.
_COST_LAMBDA_FALLBACK = 0.10   # EV cost-aversion λ (env ZTARE_LEANMILL_PROPOSER_COST_LAMBDA); mirrors forecast_router
_MODEL_STUB_FALLBACK = 0.35    # cold-start prior ONLY when the DB is empty (env ZTARE_LEANMILL_PROPOSER_MODEL_STUB)


def _cost_lambda() -> float:
    try:
        return float(os.environ.get("ZTARE_LEANMILL_PROPOSER_COST_LAMBDA", "") or _COST_LAMBDA_FALLBACK)
    except ValueError:
        return _COST_LAMBDA_FALLBACK


def _model_stub(priors: "Optional[dict[str, float]]" = None) -> float:
    """Cold-start prior for an UNMEASURED model. Precedence: explicit env override > the EMPIRICAL base rate
    (mean of the MEASURED per-model priors — the empirical-Bayes shrink target, fully data-driven) > a neutral
    constant only when there is no measured data anywhere. Never a forced magic number once the system has run."""
    _env = os.environ.get("ZTARE_LEANMILL_PROPOSER_MODEL_STUB", "")
    if _env:
        try:
            return float(_env)
        except ValueError:
            pass
    if priors:
        _vals = [v for v in priors.values() if isinstance(v, (int, float))]
        if _vals:
            return sum(_vals) / len(_vals)
    return _MODEL_STUB_FALLBACK


_MODEL_STUB = _MODEL_STUB_FALLBACK   # back-comat alias (cold-start constant; live code uses _model_stub(priors))

# Parallel-Tempering "temperatures": per-proposer explore↔exploit framing so the pool spreads across the
# obvious and the unusual instead of all converging on one tactic (replica-exchange MCMC, by proposer index).
_TEMPERATURE_FRAMINGS = (
    "Temperature LOW (exploit): use the single most standard, direct tactic that closes this.",
    "Temperature HIGH (explore): try a less-obvious or unconventional tactic; avoid the first thing that comes to mind.",
    "Temperature MID (decompose): break it into a few small steps and discharge each.",
)


# ─────────────────────────── anti-correlation occupancy (Pauli / CSMA / Competitive-Exclusion) ───────────────
class ApproachOccupancy:
    """Live, in-round registry of which (node, APPROACH) pairs the pool is already attacking, so concurrent
    proposers DIVERSIFY instead of collapsing onto one (often dead) approach — the failure mode the seam's
    third cut named. Thread-safe; lifetime is ONE attack round (cross-round refutations are `no_good_store`'s
    job, not this). An 'approach' is the structural angle a proposer declares (a tactic/lemma family); keys are
    whitespace/case-normalised. `claim` is greedy (first proposer to an approach owns it); `avoid_for` gives a
    later proposer the occupied set to steer AWAY from (CSMA character-displacement), the advisory we inject
    into its prompt so the parallel budget spreads across distinct angles."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._occupied: "set[tuple[str, str]]" = set()

    @staticmethod
    def _akey(approach: str) -> str:
        return re.sub(r"\s+", " ", (approach or "").strip().lower())[:80]

    def claim(self, node_key: str, approach: str) -> bool:
        """Reserve (node, approach). Returns False if already occupied (steer this proposer elsewhere)."""
        k = (node_key, self._akey(approach))
        with self._lock:
            if not k[1] or k in self._occupied:
                return False
            self._occupied.add(k)
            return True

    def avoid_for(self, node_key: str) -> "list[str]":
        """Approaches already being attacked on this node — feed to the next proposer as 'pick a DIFFERENT angle'."""
        with self._lock:
            return sorted(a for (n, a) in self._occupied if n == node_key)

    def release_round(self, node_key: str) -> None:
        with self._lock:
            self._occupied = {(n, a) for (n, a) in self._occupied if n != node_key}


# ─────────────────────────── proposals + the portfolio ───────────────────────────────────────────────────────
@dataclass
class Proposal:
    """One proposer's candidate for a node. `proof_text` is the thing the SERIAL kernel will check; `approach`
    is the declared structural angle (for occupancy/diversity); `est_p` is the proposer's own P(close) ∈ [0,1]
    (clamped on read — a bare/garbage est_p must not corrupt EV); `cost` is the relative budget it spent."""
    model: str
    approach: str
    proof_text: str
    est_p: float = 0.5
    cost: float = 1.0
    meta: dict = field(default_factory=dict)

    def clamped_est_p(self) -> float:
        try:
            return min(max(float(self.est_p), 0.0), 1.0)
        except (TypeError, ValueError):
            return 0.5


def pool_enabled() -> bool:
    """DEFAULT-ON; `=0` reverts to the single leaf. THE single gate (the solve_adhoc wiring calls this, so the
    default lives in exactly one place — the prior raw env-check in solver_core defaulted ON while this helper
    defaulted OFF: a split-brain, 2026-06-20)."""
    return os.environ.get("ZTARE_LEANMILL_PROPOSER_POOL", "1") != "0"


def default_portfolio() -> "list[str]":
    """The proposer models, in declared order. Subscription leaves (warm, tool-equipped) + API proposers
    (one-shot, diverse failure modes). `kimi` is `llm_runtime.MODEL_MAP['kimi']`. Override with
    ZTARE_LEANMILL_PROPOSER_MODELS=claude,codex,kimi. Membership is advisory — a dead/unconfigured model is
    skipped at dispatch; the per-model prior decides budget share."""
    # `kimi-code` = k2.7-code (code-tuned, a DIFFERENT failure mode than general k2.6 → diversifies the pool at
    # API cost; the SOTA Lean prover Kimina-Prover is NOT on the Moonshot API — open weights only — so this is
    # the best reachable kimi-family proposer, 2026-06-20). `deepseek` (deepseek-chat) = a distinct provider
    # FAMILY (the principal's #2 preference after kimi) → de-correlated failure modes from the kimi pair, cheap
    # API; the NFL prior-floor prune drops it automatically if it underperforms (2026-06-20).
    # FULL portfolio (2026-06-20): claude/codex (subscription warm) + kimi/kimi-code/deepseek/grok/gemini (API,
    # one-shot, diverse families). Every reachable family is in by default — the NFL prior-floor prune + token-
    # neutral realloc LEARN which families pull weight and drop the rest, so a wide portfolio costs no more than a
    # narrow one at steady state while maximizing failure-mode de-correlation. An unconfigured/dead family (e.g.
    # no XAI key for grok) is skipped at dispatch (advisory membership), never a crash.
    raw = os.environ.get("ZTARE_LEANMILL_PROPOSER_MODELS", "claude,codex,kimi,kimi-code,deepseek,grok,gemini")
    return [m.strip() for m in raw.split(",") if m.strip()]


def model_priors(db_path: "Optional[str]" = None) -> "dict[str, float]":
    """Per-model P(close) from the governed attempts DB (NFL-adaptive allocation). Reuses
    `move_calibration.calibrate_by_model`. Fail-open to the neutral stub (never crash the solve on a telemetry
    read)."""
    try:
        from ztare.leanmill.solver.move_calibration import calibrate_by_model
        if db_path is None:
            from ztare.leanmill.solver.solver_core import OUT_DIR
            db_path = str(OUT_DIR / "solver_lane_attempts.db")
        return {m: d.get("p", _MODEL_STUB) for m, d in calibrate_by_model(db_path).items()}
    except Exception:  # noqa: BLE001 — advisory; missing DB ⇒ all-stub
        return {}


# ─────────────────────────── the governed pool (the MTM champion-gate) ────────────────────────────────────────
def _ev(p: "Proposal", priors: "dict[str, float]") -> float:
    """The cheap champion-select score = P·value − λ·cost, with P = per-model prior × proposer est_p. This is
    the MTM/Branch-and-Price 'preliminary weight' — it never decides a closure (the kernel does), only the
    ORDER in which the serial verifier is offered candidates (Haldane: spend the scarce verify on the best first)."""
    prior = priors.get(p.model, _model_stub(priors))   # unmeasured ⇒ empirical base rate, not a magic constant
    return prior * p.clamped_est_p() - _cost_lambda() * max(0.0, p.cost)


@dataclass
class PoolOutcome:
    closed: bool
    committed: "Optional[Proposal]"
    verified_order: "list[str]"          # models, in the EV order the serial verifier actually tried
    agreement: "list[str]"               # models whose closing proof AGREES (diversity-as-governance corroboration)
    n_proposals: int


def governed_attack(node_key: str, proposals: "list[Proposal]", verify_fn: "Callable[[Proposal], bool]", *,
                    priors: "Optional[dict[str, float]]" = None,
                    max_verify: "Optional[int]" = None,
                    agree_key: "Optional[Callable[[Proposal], str]]" = None) -> PoolOutcome:
    """Run ONE governed round: EV-rank the (already-generated, anti-correlated) `proposals`, then offer them to
    the SERIAL `verify_fn` in EV order, COMMITTING the first that closes (MTM champion → runner-up). `verify_fn`
    is the kernel — called at most `max_verify` times (Haldane: the serial verifier is the scarce resource, so
    we do NOT blindly verify all k; we stop at the first close). Returns the commit + a corroboration read:
    DIVERSITY-AS-GOVERNANCE — distinct models that produced the SAME (agree_key) closing proof are an
    independent-agreement signal (the cross-substrate-consensus principle at the model layer). Pure control:
    no soundness surface (verify_fn IS the kernel; a non-closing champion is simply skipped)."""
    priors = priors if priors is not None else {}
    ranked = sorted(proposals, key=lambda p: _ev(p, priors), reverse=True)
    budget = max_verify if max_verify is not None else len(ranked)
    tried: "list[str]" = []
    committed: "Optional[Proposal]" = None
    for p in ranked[:max(0, budget)]:
        tried.append(p.model)
        if verify_fn(p):
            committed = p
            break
    # corroboration: which OTHER MODELS produced a proof equal (by agree_key) to the committed one. Keyed on
    # `p.model != committed.model` (NOT object identity) so a model that emitted two identical proofs cannot
    # self-corroborate — independent agreement means a DIFFERENT model reached the same proof.
    agreement: "list[str]" = []
    if committed is not None:
        ak = agree_key or (lambda q: re.sub(r"\s+", " ", (q.proof_text or "").strip()))
        ckey = ak(committed)
        agreement = sorted({p.model for p in proposals if p.model != committed.model and ak(p) == ckey})
    return PoolOutcome(closed=committed is not None, committed=committed,
                       verified_order=tried, agreement=agreement, n_proposals=len(proposals))


# ─────────────────────────── live model adapters (reuse default_dispatch + llm_runtime + fenced_block) ────────
# Each proposer is a model dispatched through an EXISTING path — subscription leaves (claude/codex) via the warm
# `agentic_leaf.default_dispatch` (per-tag session ⇒ concurrency-safe), API models (kimi/deepseek/gemini) via
# `llm_runtime.call_text`. The proof is extracted with the canonical `agent_output.fenced_block` — NO new parsing
# and NO hand-rolled regex over the Lean code. `est_p` is a uniform 0.5, so the champion ranking is driven by the
# per-MODEL prior (the NFL-adaptive signal), not a parsed self-score.
_SUBSCRIPTION = ("claude", "codex")


def _extract_proposal(model: str, raw: str, *, cost: float = 1.0) -> "Optional[Proposal]":
    """The proposer's proof = the CANONICAL fenced-block extraction (`agent_output.fenced_block`) — NO hand-rolled
    regex over the Lean code (the brittle-parser anti-pattern). No metadata protocol either: a model just emits a
    ```lean proof, so nothing can pollute the fence. `est_p` is a uniform 0.5 (the EV champion-rank is driven by
    the per-MODEL prior — the NFL-adaptive signal — not a parsed self-score); `approach` is the proof head, used
    only for the occupancy anti-correlation. Returns None on a non-answer (no fenced block)."""
    from ztare.leanmill.solver.agent_output import fenced_block
    proof = (fenced_block(raw or "", after="", lang="lean") or fenced_block(raw or "", after="")).strip()
    if not proof:
        return None
    approach = " ".join(proof.split()[:6])[:80]
    return Proposal(model=model, approach=approach, proof_text=proof, est_p=0.5, cost=cost)


def propose_with_model(model: str, prompt: str, *, repo: str, timeout: int, agent_tag: str = "",
                       dispatch_fn: "Optional[Callable]" = None) -> "Optional[Proposal]":
    """Dispatch one proposal from `model` through its EXISTING path; returns a Proposal or None (dead/empty).
    `dispatch_fn` (model, prompt) -> raw_text is injectable for tests; the default routes subscription leaves
    through `default_dispatch` and API models through `llm_runtime.call_text`."""
    try:
        if dispatch_fn is not None:
            raw = dispatch_fn(model, prompt)
        elif model in _SUBSCRIPTION:
            from ztare.leanmill.solver.agentic_leaf import default_dispatch, INADMISSIBLE_DISPATCH
            raw = default_dispatch(prompt, runtime=model, repo=repo, timeout=timeout,
                                   agent_tag=agent_tag or f"pool_{model}")
            if raw == INADMISSIBLE_DISPATCH:
                return None
        else:
            from ztare.common.llm_runtime import LLMRuntime, MODEL_MAP
            # SIBLING of the dead-API-leaf cache (2026-06-22): the pool's API proposers call llm_runtime
            # DIRECTLY, so the dead-API protection in `agentic_leaf.default_dispatch` never covered this path —
            # a dead/slow API model (kimi 429 / no-key grok) hung the whole proposer WAVE because `call_text`
            # defaults to timeout_seconds=300 WITH cross-model fallback (so it compounds). The exact dead-API
            # class, the forgotten sibling. Fix: (1) skip a known-dead model (shared process cache); (2) a HARD
            # short timeout; (3) NO cross-model fallback / retries — we want THIS model or nothing; (4) cache a
            # failure as dead for the process (a fresh run re-probes). The kernel re-verifies every closure, so
            # dropping a hung proposer only changes the producer route, never soundness.
            from ztare.leanmill.solver.agentic_leaf import _DEAD_API_RUNTIMES
            if model in _DEAD_API_RUNTIMES:
                return None
            _api_to = max(20, min(int(timeout),
                                  int(os.environ.get("ZTARE_LEANMILL_POOL_API_TIMEOUT_S", "90") or 90)))
            try:
                resp = LLMRuntime().call_text(prompt, model_id=MODEL_MAP.get(model, model),
                                              timeout_seconds=_api_to, retries=0, fallback_model_ids=())
                raw = getattr(resp, "text", None) or (resp if isinstance(resp, str) else "")
            except Exception:  # noqa: BLE001 — a hung/erroring API proposer is dead for this process round
                _DEAD_API_RUNTIMES.add(model)
                return None
    except Exception:  # noqa: BLE001 — a dead proposer is a miss, never a crash of the round
        return None
    return _extract_proposal(model, raw or "")


def attack_node(node_key: str, prompt: str, verify_fn: "Callable[[Proposal], bool]", *,
                repo: str, timeout: int, portfolio: "Optional[list[str]]" = None,
                priors: "Optional[dict[str, float]]" = None, db_path: "Optional[str]" = None,
                max_verify: "Optional[int]" = None, dispatch_fn: "Optional[Callable]" = None) -> PoolOutcome:
    """THE runnable governed pool (the A/B vehicle; default-OFF caller). Fan the portfolio in PARALLEL (each
    model gets the occupancy advisory so the angles diverge — anti-correlation), then `governed_attack`:
    EV-rank by per-model prior × est_p, verify in EV order through the SERIAL `verify_fn` (the kernel), commit
    the first close. Reuses the ThreadPool-per-tag concurrency pattern; verify stays serial (CVP). A dead model
    drops out (None) without sinking the round."""
    import concurrent.futures as _cf
    portfolio = portfolio or default_portfolio()
    priors = priors if priors is not None else model_priors(db_path)
    # NFL generation-adaptivity: drop proposers whose MEASURED prior is below a floor — don't spend a dispatch
    # on a demonstrably-dead model (the static-split-is-never-optimal arm of the impossibility pass; complements
    # the EV-rank that adapts the VERIFY budget). Unmeasured models keep the STUB (> floor) so a model is pruned
    # only on SUSTAINED bad calibration (Beta-posterior, not a single miss), never on absence-of-data; the floor
    # is conservative. Never empties the portfolio (keep the single best) and never silently truncates (logs the
    # drop). Default-on; ZTARE_LEANMILL_PROPOSER_PRIOR_FLOOR=0 keeps the full portfolio.
    _floor = float(os.environ.get("ZTARE_LEANMILL_PROPOSER_PRIOR_FLOOR", "0.12") or 0.0)
    _stub = _model_stub(priors)   # data-driven cold-start (empirical base rate), NOT a magic constant
    if _floor > 0 and len(portfolio) > 1:
        _orig_n = len(portfolio)
        kept = [m for m in portfolio if priors.get(m, _stub) >= _floor]
        if not kept:                                  # all measured-weak ⇒ keep the single best (never empty)
            kept = [max(portfolio, key=lambda m: priors.get(m, _stub))]
        _dropped = [m for m in portfolio if m not in kept]
        if _dropped and os.environ.get("ZTARE_LEANMILL_PROPOSER_REALLOC", "1") != "0":
            # NFL weighting, TOKEN-NEUTRAL: reallocate each pruned slot to a SURVIVING model (descending-prior
            # round-robin) so a measured-dead model's wasted dispatch becomes an extra Parallel-Tempering shot
            # from a calibrated-good one — SAME total dispatches, better allocation, diversity preserved (every
            # survivor keeps ≥1 slot, so the pool never collapses to one model). This is the *defensible* sense
            # of generation-weighting: it does NOT spend more budget chasing the best model (that would trade
            # against the diversity that IS the pool's edge); it only re-points budget already being spent.
            # =0 reverts to prune-only (a smaller portfolio).
            _ranked = sorted(kept, key=lambda m: priors.get(m, _stub), reverse=True)
            _extra = [_ranked[i % len(_ranked)] for i in range(_orig_n - len(kept))]
            portfolio = kept + _extra
            print(f"[proposer-pool] NFL realloc: dropped {_dropped} (prior < {_floor}); "
                  f"reallocated {len(_extra)} slot(s) → {_extra} (total {len(portfolio)} unchanged)", flush=True)
        else:
            if _dropped:
                print(f"[proposer-pool] NFL prune: dropped {_dropped} (prior < {_floor}); "
                      f"portfolio now {kept}", flush=True)
            portfolio = kept
    occ = ApproachOccupancy()

    def _one(model: str, idx: int) -> "Optional[Proposal]":
        avoid = occ.avoid_for(node_key)   # populated by EARLIER waves ⇒ this proposer steers to a fresh angle
        # PARALLEL TEMPERING: each proposer gets an explore/exploit "temperature" framing by index, so the pool
        # spreads across exploit (standard, low-temp) ↔ explore (unusual, high-temp) instead of all converging on
        # the obvious tactic — diversity BEYOND model-difference (the alien-move from replica-exchange MCMC).
        temper = _TEMPERATURE_FRAMINGS[idx % len(_TEMPERATURE_FRAMINGS)]
        p = prompt + f"\n\n-- {temper}" + (
            f"\n-- other proposers are already trying: {', '.join(avoid)}; take a DIFFERENT angle." if avoid else "")
        prop = propose_with_model(model, p, repo=repo, timeout=timeout, dispatch_fn=dispatch_fn)
        if prop is not None:
            occ.claim(node_key, prop.approach)   # record the angle so LATER waves diverge from it
        return prop

    # WAVE-BATCHED generation so the anti-correlation actually bites: within a wave the proposers run
    # concurrently (their `avoid_for` sees only PRIOR waves), but each wave updates the occupancy before the
    # next, so a portfolio larger than the worker slots (or with repeated models — Parallel-Tempering) genuinely
    # spreads across distinct angles instead of all launching blind to each other (the bug a one-shot parallel
    # map has). With portfolio ≤ workers it is a single wave and diversity comes from the models differing.
    parallel = len(portfolio) > 1 and os.environ.get("ZTARE_LEANMILL_PROPOSER_PARALLEL", "1") != "0"
    workers = max(1, min(len(portfolio), int(os.environ.get("ZTARE_LEANMILL_PROPOSER_WORKERS", "3") or 3)))
    proposals: "list[Proposal]" = []
    if parallel:
        with _cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for i in range(0, len(portfolio), workers):
                wave = portfolio[i:i + workers]
                idxs = range(i, i + len(wave))
                proposals.extend(p for p in ex.map(_one, wave, idxs) if p is not None)
    else:
        proposals = [p for p in (_one(m, i) for i, m in enumerate(portfolio)) if p is not None]
    return governed_attack(node_key, proposals, verify_fn, priors=priors, max_verify=max_verify)


# ───────────────────────────────────────── selftest (hermetic — injected verify, no Lean/LLM) ────────────────
def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # --- ApproachOccupancy: anti-correlation ---
    occ = ApproachOccupancy()
    ok("first claim of an approach succeeds", occ.claim("nodeA", "induction on n"))
    ok("second proposer on the SAME approach is steered away", not occ.claim("nodeA", "Induction on N  "))
    ok("a DIFFERENT approach on the same node is free", occ.claim("nodeA", "strong induction + WF"))
    ok("avoid_for lists the occupied approaches", len(occ.avoid_for("nodeA")) == 2)
    ok("other nodes are independent", occ.claim("nodeB", "induction on n"))
    occ.release_round("nodeA")
    ok("release frees the round", occ.avoid_for("nodeA") == [] and occ.claim("nodeA", "induction on n"))

    # --- governed_attack: EV champion order + serial commit + Haldane budget + corroboration ---
    priors = {"claude": 0.6, "codex": 0.27, "kimi": 0.56}
    props = [
        Proposal("codex", "a1", "PROOF_X", est_p=0.9, cost=1.0),    # high self-est but low model prior
        Proposal("claude", "a2", "PROOF_GOOD", est_p=0.7, cost=1.0),  # best EV (0.6*0.7)
        Proposal("kimi", "a3", "PROOF_GOOD", est_p=0.5, cost=1.0),
    ]
    # only PROOF_GOOD verifies; record the order the serial verifier was offered candidates
    seen = []
    def verify(p):
        seen.append(p.model)
        return p.proof_text == "PROOF_GOOD"
    out = governed_attack("nodeC", props, verify, priors=priors)
    ok("champion-first EV order (claude before codex)", out.verified_order[0] == "claude")
    ok("commits the first closing proposal", out.closed and out.committed.model == "claude")
    ok("corroboration: kimi produced the SAME closing proof → agreement", out.agreement == ["kimi"])

    # Haldane: max_verify caps how many times the serial verifier is called
    seen.clear()
    out2 = governed_attack("nodeD", [Proposal("codex", "z", "NO", est_p=0.9),
                                     Proposal("kimi", "z", "NO", est_p=0.9),
                                     Proposal("claude", "z", "NO", est_p=0.9)], verify, max_verify=1)
    ok("max_verify caps serial-verify calls (Haldane)", len(seen) == 1 and not out2.closed)

    # est_p garbage must not corrupt EV / crash
    ok("garbage est_p clamps, no crash",
       abs(_ev(Proposal("m", "a", "p", est_p="bad"), {"m": 0.5}) - (0.5 * 0.5 - _cost_lambda())) < 1e-9)

    # --- live adapters (injected dispatch — no LLM/Lean) ---
    pr = _extract_proposal("kimi", "Here is the proof.\n```lean\nby simp [foo]\n```")
    ok("proof = canonical fenced-block extraction (no code regex)", pr is not None and pr.proof_text == "by simp [foo]")
    ok("est_p is a uniform 0.5 (rank by model prior, not a parsed self-score)", pr.est_p == 0.5)
    ok("approach is the proof head (for occupancy)", pr.approach == "by simp [foo]")
    ok("no fenced block ⇒ None (a non-answer is a miss)", _extract_proposal("kimi", "no code here") is None)

    # attack_node end-to-end with injected dispatch: 3 models propose, only claude's proof verifies
    bank = {"claude": "x\n```lean\nGOODPROOF\n```", "codex": "y\n```lean\nBAD1\n```",
            "kimi": "z\n```lean\nBAD2\n```"}
    out3 = attack_node("nodeE", "prove it", lambda p: p.proof_text == "GOODPROOF",
                       repo=".", timeout=1, portfolio=["claude", "codex", "kimi"],
                       priors={"claude": 0.6, "codex": 0.27, "kimi": 0.56},
                       dispatch_fn=lambda model, prompt: bank[model])
    ok("attack_node: pool closes via the verifying proposal", out3.closed and out3.committed.model == "claude")
    ok("attack_node: all 3 models proposed", out3.n_proposals == 3)
    # a fully-dead portfolio (every dispatch empty) ⇒ no proposals, clean miss
    outd = attack_node("nodeF", "prove it", lambda p: True, repo=".", timeout=1,
                       portfolio=["claude", "kimi"], priors={}, dispatch_fn=lambda m, p: "")
    ok("attack_node: dead portfolio ⇒ clean miss (no crash)", not outd.closed and outd.n_proposals == 0)

    # --- INTEGRATION: anti-correlation actually STEERS later proposers (deterministic in SEQUENTIAL mode) ---
    seen_prompts: "dict[str, str]" = {}
    def rec_dispatch(model, prompt):
        seen_prompts[model] = prompt   # the approach (occupancy key) is the proof head, e.g. 'angle_m1 ...'
        return f"```lean\nangle_{model} by rfl\n```"
    os.environ["ZTARE_LEANMILL_PROPOSER_PARALLEL"] = "0"   # deterministic order: m1, then m2 (sees m1), …
    try:
        outw = attack_node("nodeW", "BASE", lambda p: False, repo=".", timeout=1,
                           portfolio=["m1", "m2", "m3", "m4"], priors={}, dispatch_fn=rec_dispatch)
    finally:
        del os.environ["ZTARE_LEANMILL_PROPOSER_PARALLEL"]
    ok("first proposer gets NO avoid advisory (nothing claimed yet)",
       "DIFFERENT angle" not in seen_prompts.get("m1", ""))
    ok("later proposers DO get the anti-correlation advisory (occupancy bit)",
       all("DIFFERENT angle" in seen_prompts.get(m, "") for m in ("m2", "m3", "m4")))
    ok("the advisory NAMES the earlier-claimed proof-head approaches (steering, not just a flag)",
       "angle_m1" in seen_prompts.get("m4", "") and "angle_m3" in seen_prompts.get("m4", ""))
    ok("all 4 models proposed", outw.n_proposals == 4)

    # corroboration must NOT count the committed model's OWN second identical proof as agreement.
    # claude#1 wins EV (0.6·0.9−λ=0.44 > claude#2 0.6·0.8−λ=0.38 > codex 0.5·0.3−λ=0.05) AND has a same-model
    # duplicate (claude#2, identical proof) — which must be EXCLUDED — while codex (the OTHER model) counts.
    same_model = [Proposal("claude", "a", "P", est_p=0.9), Proposal("claude", "b", "P", est_p=0.8),
                  Proposal("codex", "c", "P", est_p=0.3)]
    outs = governed_attack("nodeS", same_model, lambda p: p.proof_text == "P",
                           priors={"claude": 0.6, "codex": 0.5})
    ok("corroboration excludes the committed model's own duplicate, counts the OTHER model",
       outs.closed and outs.committed.model == "claude" and outs.agreement == ["codex"])

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
