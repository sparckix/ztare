"""Forecast-pool POLICY router — the work-router the `analytics/public/forecast_pool/` prediction market was
built to power but was never wired into the solver (it has a live SCORING loop — Brier/Elo/Murphy + per-agent
`calibration_weights.json` — but the ROUTING half, "use the forecasts to choose what compute to spend next,"
was missing; the operator: "never got to do a/b testing of whether that adds actual lift / kind of like an
agent-based prediction market").

This is that missing half, scoped to the solver's inner loop. It does NOT spin up N LLM-forecaster agents per
routing decision (that market already exists at the coarse, agent-minutes grain and is too heavy to call per
move). Instead it treats the signals leanmill ALREADY produces as the FORECASTERS of one binary question —
"will attempting this candidate CLOSE?" — and lets the forecast pool's own calibration machinery (inverse-Brier
weights, per domain) decide which signal to trust:

  • MovePriorForecaster   — `move_calibration.selection_priors` (the historical per-move close-rate);
  • ProofCacheForecaster  — `proof_cache` hit ⇒ near-certain close (re-verify is ~free);
  • NoGoodForecaster      — `no_good_store` match ⇒ a learned conflict; DROP it (CDCL: never re-spend on a no-good);
  • FaithfulnessForecaster— `faithfulness_store` reference/conflict (a known mistranslation trap is riskier);
  • AgentVoteForecaster   — the planner's own est_p_close (#74 agent vote), if supplied — the ONE LLM input,
                            already produced, not a per-candidate call.

The ensemble prices each candidate `ev = P(close)·value − λ·cost`, routes compute high-EV first, then the KERNEL
outcome RESOLVES every forecast → per-signal Brier → `reweight()` (the calibration update, mirroring the pool's
`calibration_weights.json` schema) → a POLICY `KeyLearningUnit` deposited into the compounder
(`contracts/learning_unit.py`). Whether forecast-routing is allowed to actually REORDER the scheduler is gated by
`PolicyPromotion`: BLOCKED until enough ADMISSIBLE support, ADVISORY (rank + log only) once supported, and only
PROMOTABLE — flips routing live — once the ensemble's Brier BEATS the move-prior-only baseline (the A/B the
operator said was never run). So even with the flag on, an uncalibrated router never changes a routing decision
(the standing rule: a policy is inadmissible without calibration).

BOUNDARY: operates entirely on the internal analytics ledger — it reads `calibration_weights.json`, writes a
local signal-weight file + a Brier ledger, and never produces a commit, so it is OUTSIDE the GP-241 commit-
signing membrane (the operator: "we dont need the fucking membrane to cryptographically sign stuff"). Reuses the
forecasting module's Brier, the existing signal stores, and the learning_unit model — it is the seam that wires
them, not a parallel build. Parity-safe: `ZTARE_LEANMILL_FORECAST_ROUTER` default-off ⇒ `routing_mode()=="off"`
and the solver keeps its current ordering byte-for-byte.

  python -m ztare.leanmill.solver.forecast_router --selftest
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from ztare.leanmill.contracts.learning_unit import (
    KeyLearningUnit, LearningExit, LearningKind, admissible as _admissible,
    context_signature, evaluate_promotion, exit_deposits,
)

# ── tunables (documented, not magic) ────────────────────────────────────────────────────────────────────────
_DEFAULT_P = 0.30            # the move prior's fallback when a move has no calibration row yet
_CACHE_P = 0.98             # a proof_cache hit ⇒ near-certain close (only the re-verify can fail)
_NOGOOD_P = 0.02            # a no_good match ⇒ a learned conflict (kept for the Brier row; the candidate is DROPPED)
_COST_LAMBDA = 0.10         # cost-aversion in EV = P·value − λ·(cost/cost_scale); a tiebreaker, not a dominator
_COST_SCALE = 100.0         # budget-unit normalizer so cost and value live on comparable scales
_MIN_W = 0.10               # weight floor so a temporarily-bad signal is down-weighted, never silenced


# ── the work-item + the per-signal forecast ─────────────────────────────────────────────────────────────────
@dataclass
class WorkCandidate:
    """One unit of routable work — a {target × move × substrate} the solver COULD spend compute on next."""
    id: str
    target: str = ""                  # the goal / row identity
    move: str = ""                    # the move_calibration key (the prior signal's lookup)
    substrate: str = "lean"           # lean | smt_z3 | isabelle — the traversal choice (#76)
    statement: str = ""               # the formal statement (cache / no_good lookup); "" ⇒ those signals abstain
    nl: str = ""                      # the NL claim (faithfulness lookup); "" ⇒ that signal abstains
    value: float = 1.0                # value_if_success (a keystone sub-lemma is worth more than a leaf)
    base_cost: float = 10.0           # budget units this attempt would spend
    context_features: "dict" = field(default_factory=dict)  # for the POLICY recall key (context_signature)

    def domain(self) -> str:
        """The calibration domain a forecaster is weighted within — keep it coarse (per substrate) so weights
        accumulate support; the move identity already lives inside the move-prior signal itself."""
        return self.substrate or "lean"


@dataclass
class SignalForecast:
    signal: str
    p_close: float = 0.0
    cost: float = 0.0
    abstain: bool = True              # an abstaining signal contributes NO term to the ensemble (vs a 0.5 vote)
    drop: bool = False               # a hard KILL (no_good): never route compute here
    route_first: bool = False        # a hard PROMOTE (cache hit): confirm it before anything else
    rationale: str = ""


# ── the forecasters (each WRAPS a real signal store — none reimplements one) ─────────────────────────────────
class Forecaster:
    name = "base"

    def forecast(self, c: WorkCandidate) -> SignalForecast:  # pragma: no cover - overridden
        return SignalForecast(self.name)


class MovePriorForecaster(Forecaster):
    """The historical per-move close-rate from ratified governance receipts (`move_calibration.selection_priors`).
    Always votes (every move has at least the Beta prior); this is the baseline the ensemble must beat."""
    name = "move_prior"

    def __init__(self, db_path: "str | Path | None"):
        self.priors: "dict[str, float]" = {}
        try:
            from ztare.leanmill.solver.move_calibration import selection_priors
            if db_path and Path(db_path).exists():
                self.priors = selection_priors(db_path) or {}
        except Exception:  # noqa: BLE001 — absent/locked DB ⇒ the flat fallback prior (never crash routing)
            self.priors = {}

    def forecast(self, c: WorkCandidate) -> SignalForecast:
        p = float(self.priors.get(c.move, _DEFAULT_P))
        return SignalForecast(self.name, p_close=p, cost=c.base_cost, abstain=False,
                              rationale=f"prior[{c.move}]={p:.2f}")


class ProofCacheForecaster(Forecaster):
    """A verified proof already exists for this exact statement (`proof_cache`) ⇒ near-certain close; route it
    FIRST (re-verifying a cached proof is ~free relative to a fresh attempt)."""
    name = "proof_cache"

    def __init__(self, path: "str | Path | None"):
        self.cache = None
        try:
            if path:
                from ztare.leanmill.solver.proof_cache import ProofCache
                self.cache = ProofCache(path)
        except Exception:  # noqa: BLE001
            self.cache = None

    def forecast(self, c: WorkCandidate) -> SignalForecast:
        if self.cache is None or not c.statement or not self.cache.has(c.statement):
            return SignalForecast(self.name)  # abstain
        return SignalForecast(self.name, p_close=_CACHE_P, cost=1.0, abstain=False,
                              route_first=True, rationale="cache hit (re-verify)")


class NoGoodForecaster(Forecaster):
    """A confirmed dead-end for this statement (`no_good_store`) ⇒ DROP — the CDCL discipline: never re-spend
    compute on a learned conflict. Speaks ONLY to kill; abstains otherwise."""
    name = "no_good"

    def __init__(self, path: "str | Path | None"):
        self.store = None
        try:
            if path:
                from ztare.leanmill.solver.no_good_store import NoGoodStore
                self.store = NoGoodStore(path)
        except Exception:  # noqa: BLE001
            self.store = None

    def forecast(self, c: WorkCandidate) -> SignalForecast:
        if self.store is None or not c.statement or not self.store.matches(c.statement):
            return SignalForecast(self.name)  # abstain
        return SignalForecast(self.name, p_close=_NOGOOD_P, cost=c.base_cost, abstain=False,
                              drop=True, rationale="known no-good (dropped)")


class FaithfulnessForecaster(Forecaster):
    """The NL↔formal correspondence is well-understood or a known trap (`faithfulness_store`): a recorded
    cross-substrate CONFLICT means this NL has a mistranslation trap ⇒ a fresh attempt is riskier; a clean
    confirmed reference is mildly reassuring. Mild + calibratable; abstains when the NL is unseen."""
    name = "faithfulness"

    def __init__(self, path: "str | Path | None"):
        self.store = None
        try:
            if path:
                from ztare.leanmill.solver.faithfulness_store import FaithfulnessStore
                self.store = FaithfulnessStore(path)
        except Exception:  # noqa: BLE001
            self.store = None

    def forecast(self, c: WorkCandidate) -> SignalForecast:
        if self.store is None or not c.nl:
            return SignalForecast(self.name)
        if self.store.conflicts(c.nl):
            return SignalForecast(self.name, p_close=0.30, cost=c.base_cost, abstain=False,
                                  rationale="known mistranslation trap")
        if self.store.reference(c.nl):
            return SignalForecast(self.name, p_close=0.55, cost=c.base_cost, abstain=False,
                                  rationale="confirmed faithful reference")
        return SignalForecast(self.name)


class AgentVoteForecaster(Forecaster):
    """The planner's OWN est_p_close for each candidate (the #74 agent vote) — the one LLM-sourced forecaster,
    supplied as a {candidate_id: p} map already produced by the planner, NOT a per-candidate model call."""
    name = "agent_vote"

    def __init__(self, votes: "dict[str, float] | None"):
        self.votes = votes or {}

    def forecast(self, c: WorkCandidate) -> SignalForecast:
        if c.id not in self.votes:
            return SignalForecast(self.name)
        # CLAMP to [0,1] (2026-06-13 audit): this is the LLM-sourced forecaster — a model emitting `95`
        # ("95%") or a negative would corrupt the EV ranking AND the Brier ledger that drives the learned
        # per-signal weights. A probability is a probability.
        p = min(1.0, max(0.0, float(self.votes[c.id])))
        return SignalForecast(self.name, p_close=p, cost=c.base_cost, abstain=False, rationale=f"agent={p:.2f}")


class PoolForecaster(Forecaster):
    """The forecast POOL's diverse-forecaster CONSENSUS P(close) (aggregate.p_success), supplied as a
    {candidate_id: p} map read via the boundary-safe `forecast_pool_bridge`. This is the ROUTE-TO-THE-ACTUAL-CODE
    forecaster — the cross-agent diversity comes from the pool's CONFIGURED warm forecasters (its daemon), NOT a
    one-off self-forecast (own-agent is at most ONE pool forecaster: necessary, not sufficient). Abstains when the
    pool has no aggregate yet for the candidate (no forecasts have landed)."""
    name = "pool"

    def __init__(self, pool_forecasts: "dict[str, float] | None"):
        self.p = pool_forecasts or {}

    def forecast(self, c: WorkCandidate) -> SignalForecast:
        v = self.p.get(c.id)
        if v is None:
            return SignalForecast(self.name)
        v = min(1.0, max(0.0, float(v)))   # clamp to [0,1] (2026-06-13 audit) — a probability is a probability
        return SignalForecast(self.name, p_close=float(v), cost=c.base_cost, abstain=False,
                              rationale=f"pool consensus={float(v):.2f}")


def default_forecasters(*, db_path=None, cache_path=None, no_good_path=None, faithfulness_path=None,
                        agent_votes=None, pool_forecasts=None) -> "list[Forecaster]":
    """Assemble the standard signal panel; any path/map left None ⇒ that signal simply abstains (never crashes)."""
    return [
        MovePriorForecaster(db_path),
        ProofCacheForecaster(cache_path),
        NoGoodForecaster(no_good_path),
        FaithfulnessForecaster(faithfulness_path),
        AgentVoteForecaster(agent_votes),
        PoolForecaster(pool_forecasts),
    ]


# ── the calibration-weighted ensemble (mirrors the forecast pool's calibration_weights.json schema) ──────────
def load_signal_weights(path: "str | Path | None") -> dict:
    """Per-signal reliability weights {signal: {default_weight, domains:{domain: w}}} — the SAME shape the
    forecast pool's `calibration_weights.json` carries per agent, here per SIGNAL. Missing file ⇒ uniform 1.0."""
    if path and Path(path).exists():
        try:
            return json.loads(Path(path).read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _weight_of(signal: str, domain: str, weights: dict) -> float:
    w = weights.get(signal) or {}
    return float((w.get("domains") or {}).get(domain, w.get("default_weight", 1.0)))


@dataclass
class PricedCandidate:
    candidate: WorkCandidate
    p_close: float
    ev: float
    forecasts: "list[SignalForecast]"
    route_first: bool = False
    dropped: bool = False
    breakdown: str = ""


def aggregate(forecasts: "list[SignalForecast]", domain: str, weights: dict) -> "tuple[float, bool, bool, str]":
    """Calibration-weighted mean P(close) over the NON-abstaining signals → (p_ensemble, route_first, drop, why).
    A no_good DROP and a cache route_first are hard deterministic overrides the weights cannot wash out (soundness
    /efficiency short-circuits, not votes)."""
    drop = any(f.drop for f in forecasts)
    route_first = any(f.route_first for f in forecasts)
    # Hard, exogenous-confirmed overrides DOMINATE the calibrated mean — a confirmed no-good is ~0 regardless of
    # the move prior (the CDCL conflict is ground truth, not a vote to average), and drop beats a stale cache hit.
    if drop:
        return _NOGOOD_P, False, True, "confirmed no-good ⇒ p≈0 (dominates prior)"
    if route_first:
        return _CACHE_P, True, False, "cache hit ⇒ p≈1 (re-verify)"
    live = [f for f in forecasts if not f.abstain]
    if not live:
        return _DEFAULT_P, route_first, drop, "no live signal ⇒ flat prior"
    num = sum(_weight_of(f.signal, domain, weights) * f.p_close for f in live)
    den = sum(_weight_of(f.signal, domain, weights) for f in live) or 1.0
    p = num / den
    why = ", ".join(f"{f.signal}:{f.p_close:.2f}·w{_weight_of(f.signal, domain, weights):.2f}" for f in live)
    return p, route_first, drop, why


def price(candidates: "list[WorkCandidate]", forecasters: "list[Forecaster]", *,
          weights: "dict | None" = None) -> "list[PricedCandidate]":
    """Price + RANK the candidate pool: cache-hits first, then descending EV = P·value − λ·(cost/scale); no_goods
    are priced (for the audit) but sorted to the back AND flagged dropped (the scheduler skips them)."""
    weights = weights or {}
    out: "list[PricedCandidate]" = []
    for c in candidates:
        fs = [fc.forecast(c) for fc in forecasters]
        p, route_first, drop, why = aggregate(fs, c.domain(), weights)
        cost = min((f.cost for f in fs if not f.abstain), default=c.base_cost)
        ev = p * c.value - _COST_LAMBDA * (cost / _COST_SCALE)
        out.append(PricedCandidate(c, p, ev, fs, route_first=route_first, dropped=drop, breakdown=why))
    # sort key: live candidates by (route_first, ev) desc; dropped no-goods always last
    out.sort(key=lambda pc: (not pc.dropped, pc.route_first, pc.ev), reverse=True)
    return out


# ── resolution → Brier ledger → reweight (the calibration update), + the POLICY learning unit ────────────────
def _y_of(exit: LearningExit) -> "float | None":
    """The realized binary outcome for the forecast 'will this CLOSE?': 1 if the disposition deposited a PROOF
    (a real closure), 0 if it ran admissibly but did not close. None ⇒ inadmissible (no label — must not score)."""
    if exit is LearningExit.INADMISSIBLE:
        return None
    return 1.0 if LearningKind.PROOF in exit_deposits(exit) else 0.0


def resolve(priced: PricedCandidate, exit: LearningExit, *, kernel_confirmed: bool, carrier_live: bool = True,
            ledger_path: "str | Path | None" = None, run_tag: str = "", attempt_at: str = "",
            decision_changed: "bool | None" = None) -> KeyLearningUnit:
    """Resolve a routed candidate against the KERNEL outcome: append a per-signal Brier row for every live
    forecast (so `reweight` can recalibrate) and return a POLICY KeyLearningUnit. INADMISSIBLE / dead-carrier /
    unconfirmed ⇒ admissible=False, NO Brier rows written and NOTHING deposited (the certificate rule — a dead-
    instrument forecast must never poison the signal weights, the contaminated-DB lesson)."""
    adm = _admissible(exit, kernel_confirmed=kernel_confirmed, carrier_live=carrier_live)
    y = _y_of(exit)
    c = priced.candidate
    key = context_signature(c.context_features, sorted(c.context_features)) or c.id
    unit = KeyLearningUnit(
        kind=LearningKind.POLICY, key=key, exit=exit, admissible=adm,
        payload={"p_ensemble": priced.p_close, "ev": priced.ev, "move": c.move, "substrate": c.substrate},
        target=c.target, carrier=c.move, source="forecast_router", run_tag=run_tag, attempt_at=attempt_at,
        est_p_close=priced.p_close, realized_value=y, decision_changed=decision_changed,
        context_features=dict(c.context_features),
    )
    if not adm or y is None or ledger_path is None:
        return unit
    rows = [{"signal": f.signal, "domain": c.domain(), "p": f.p_close, "y": y, "run_tag": run_tag}
            for f in priced.forecasts if not f.abstain]
    p = Path(ledger_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return unit


def _brier_by_signal(ledger_path: "str | Path") -> "dict[tuple[str, str], list[float]]":
    acc: "dict[tuple[str, str], list[float]]" = {}
    p = Path(ledger_path)
    if not p.exists():
        return acc
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            acc.setdefault((r["signal"], r.get("domain", "lean")), []).append((float(r["p"]) - float(r["y"])) ** 2)
        except Exception:  # noqa: BLE001
            continue
    return acc


def reweight(ledger_path: "str | Path", weights_path: "str | Path | None" = None) -> dict:
    """Recompute per-(signal,domain) weights from the Brier ledger — w = max(_MIN_W, 1 − 2·mean_brier) (1.0 for a
    perfect signal, _MIN_W for a coin-flip/worse), the inverse-Brier reliability the forecast pool assigns its
    agents. Writes the `calibration_weights.json`-shaped file and returns it. This IS the calibration update."""
    acc = _brier_by_signal(ledger_path)
    weights: dict = {}
    for (signal, domain), briers in acc.items():
        mean_b = sum(briers) / len(briers) if briers else 0.25
        w = max(_MIN_W, 1.0 - 2.0 * mean_b)
        node = weights.setdefault(signal, {"default_weight": 1.0, "domains": {}, "evidence": {}})
        node["domains"][domain] = round(w, 4)
        node["evidence"][domain] = {"mean_brier": round(mean_b, 4), "score_rows": len(briers)}
    if weights_path is not None:
        Path(weights_path).parent.mkdir(parents=True, exist_ok=True)
        Path(weights_path).write_text(json.dumps(weights, indent=2, ensure_ascii=False), encoding="utf-8")
    return weights


def baseline_beaten(ledger_path: "str | Path") -> "bool | None":
    """Does the calibration-weighted ENSEMBLE beat the move-prior-only BASELINE on Brier over the ledger? (the
    A/B the operator said was never run). None if there is no move_prior row to compare against."""
    acc = _brier_by_signal(ledger_path)
    base = [b for (sig, _), bs in acc.items() if sig == "move_prior" for b in bs]
    allb = [b for bs in acc.values() for b in bs]
    if not base or not allb:
        return None
    return (sum(allb) / len(allb)) < (sum(base) / len(base))


def router_promotion(units: "list[KeyLearningUnit]", ledger_path: "str | Path | None" = None):
    """The deploy gate: PolicyPromotion over the routed units, with beats_baseline taken from the Brier ledger.
    BLOCKED ⇒ off; ADVISORY ⇒ rank+log only; PROMOTABLE ⇒ may reorder the scheduler live."""
    bb = baseline_beaten(ledger_path) if ledger_path else None
    return evaluate_promotion(units, beats_baseline=bb)


def routing_mode(units: "list[KeyLearningUnit] | None" = None, ledger_path: "str | Path | None" = None) -> str:
    """The single gate the solver consults. 'off' ONLY when ZTARE_LEANMILL_FORECAST_ROUTER=0 (the opt-out A/B
    baseline arm); DEFAULT-ON 2026-06-10 → 'advisory' (rank + log, current ordering UNCHANGED) until the
    PolicyPromotion gate says 'promotable', at which point 'active' (forecast-EV order). So default-on alone never
    changes a routing decision — only a calibrated, baseline-beating router does (inadmissible-without-
    calibration); it just starts gathering the lift data instead of staying dormant."""
    if os.environ.get("ZTARE_LEANMILL_FORECAST_ROUTER", "1") == "0":
        return "off"
    if units and router_promotion(units, ledger_path).ready:
        return "active"
    return "advisory"


def _pool_forecasts_for_rows(rows: list) -> "dict[str, float]":
    """ROUTE-TO-POOL producer: for each target EMIT a micro forecast contract + READ the diverse forecasters'
    consensus P(close) via the boundary-safe `forecast_pool_bridge` → {candidate_id: p_success}. The pool's warm
    DAEMON (its CONFIGURED diverse forecasters) does the forecasting async; this reads whatever consensus has
    LANDED (empty on the first pass → PoolForecaster abstains → falls back to the cheap signals). This is the
    "route the POLICY to the actual pool code" seam — NOT a one-off forecaster. Gated (ZTARE_LEANMILL_POOL_ROUTER
    =1; DEFAULT-OFF because it needs the warm daemon RUNNING to add value + costs a subprocess per row), bounded
    (ZTARE_LEANMILL_POOL_ROUTER_CAP), best-effort (never raises into the batch)."""
    out: "dict[str, float]" = {}
    if os.environ.get("ZTARE_LEANMILL_POOL_ROUTER", "0") != "1":
        return out
    try:
        from ztare.leanmill.solver import forecast_pool_bridge as _pb
        if not _pb.pool_available():
            return out
        cap = int(os.environ.get("ZTARE_LEANMILL_POOL_ROUTER_CAP", "16") or 16)
        for i, r in enumerate(rows[:cap]):
            rid = str(r.get("row_id", i))
            goal = r.get("goal") or r.get("target_theorem_name") or ""
            if not goal:
                continue
            cid = _pb.emit_micro_contract(rid, goal)
            if cid:
                p = _pb.read_aggregate(cid)
                if p is not None:
                    out[rid] = p
    except Exception:  # noqa: BLE001
        return out
    if out:
        print(f"[forecast] pool: diverse-forecaster consensus landed for {len(out)} target(s)", flush=True)
    return out


def rank_rows(rows: list, *, db_path=None, cache_path=None, no_good_path=None, faithfulness_path=None,
              units: "list | None" = None, ledger_path=None, agent_votes: "dict | None" = None) -> "tuple[list, str, dict]":
    """The forecast router's STRATEGIC seam: advisory ranking of a batch of solver target ROWS by forecast EV.
    Distinct target statements ⇒ the cache / no_good / faithfulness signals actually DIFFERENTIATE (unlike the
    tactical move loop, where they short-circuit earlier and the router would just duplicate UCB+priors). Returns
    (rows, log_line, priced_by_id) — `priced_by_id[row_id] -> PricedCandidate` so the caller can RESOLVE each
    target's kernel outcome back through `resolve()` (closing the learn loop). Parity no-op when
    ZTARE_LEANMILL_FORECAST_ROUTER!=1 (returns {} for priced). The order is REORDERED only when the
    PolicyPromotion gate says 'active' (earned by beating baseline on Brier); otherwise the original order is
    preserved and the EV ranking is just LOGGED. A known no_good target sinks to the back. Never raises."""
    mode = routing_mode(units, ledger_path)
    if mode == "off" or not rows:
        return rows, "", {}
    try:
        fcs = default_forecasters(db_path=db_path, cache_path=cache_path,
                                  no_good_path=no_good_path, faithfulness_path=faithfulness_path,
                                  agent_votes=agent_votes, pool_forecasts=_pool_forecasts_for_rows(rows))
        cands = [WorkCandidate(id=str(r.get("row_id", i)), target=str(r.get("row_id", i)),
                               move="solve", statement=(r.get("goal") or r.get("target_theorem_name") or ""))
                 for i, r in enumerate(rows)]
        priced = price(cands, fcs)
        by_id = {pc.candidate.id: pc for pc in priced}
        rank = {pc.candidate.id: k for k, pc in enumerate(priced)}
        top = ", ".join(f"{pc.candidate.id}(ev={pc.ev:.2f}{',DROP' if pc.dropped else ''})" for pc in priced[:8])
        if mode == "active":
            rows = sorted(rows, key=lambda r: rank.get(str(r.get("row_id", "")), 1e9))
        return rows, f"[{mode}] EV order (top): {top}", by_id
    except Exception as e:  # noqa: BLE001 — advisory; never break the batch
        return rows, f"(forecast rank skipped: {e!r})", {}


def resolve_batch(results: list, priced_by_id: dict, *, ledger_path, weights_path=None, run_tag: str = "") -> int:
    """Close the forecast learn loop over a finished batch: for each result, map its solver outcome → a
    LearningExit and RESOLVE the matching priced candidate (records per-signal Brier rows for admissible
    outcomes; INADMISSIBLE/dead-instrument deposit nothing — the certificate rule), then REWEIGHT the signals.
    Best-effort + never raises. Returns the count resolved. No-op when `priced_by_id` is empty (router off)."""
    if not priced_by_id:
        return 0
    from ztare.leanmill.contracts.learning_unit import exit_of
    n = 0
    for res in results or []:
        pc = priced_by_id.get(str(res.get("name", res.get("row_id", ""))))
        if pc is None:
            continue
        outcome = str(res.get("outcome", ""))
        ran = outcome not in ("skipped", "deferred_discovery_bound", "outside_menu_source_cues_missing")
        try:
            resolve(pc, exit_of(outcome), kernel_confirmed=ran,
                    carrier_live=outcome != "inadmissible_provider_dead", ledger_path=ledger_path, run_tag=run_tag)
            n += 1
        except Exception:  # noqa: BLE001
            continue
    # ROUTE-TO-POOL: resolve each target's pool contract with the KERNEL outcome → the pool SCORES its diverse
    # forecasters (calibration compounds). Best-effort; only when the pool router is on.
    if os.environ.get("ZTARE_LEANMILL_POOL_ROUTER", "0") == "1":
        try:
            from ztare.leanmill.solver import forecast_pool_bridge as _pb
            for res in results or []:
                rid = str(res.get("name", res.get("row_id", "")))
                outcome = str(res.get("outcome", ""))
                if not rid or outcome in ("skipped", "deferred_discovery_bound", "inadmissible_provider_dead",
                                          "outside_menu_source_cues_missing"):
                    continue
                _pb.resolve_contract(_pb.contract_id_for(rid), success=(outcome == "closed"),
                                     compile_status=outcome, note=f"leanmill kernel outcome: {outcome}")
        except Exception:  # noqa: BLE001
            pass
    try:
        reweight(ledger_path, weights_path)
    except Exception:  # noqa: BLE001
        pass
    return n


def forecast_campaign_p0(p_closes: "list[float]", *, domain: str = "",
                         domain_mean_ttc_s: "float | None" = None,
                         domain_mean_cost_s: "float | None" = None) -> dict:
    """Campaign-START P0 forecast (2026-06-25): aggregate per-lemma P(close) — each from the SAME Brier-calibrated
    `price()`/`aggregate()` ensemble this router already runs per candidate — with the DOMAIN's historical mean
    time/cost (from `phase_timing.summarize_campaign_cycle_time`, segmented by `record_campaign`'s domain tag)
    into expected YIELD + TIME-to-closure + COST. This is the prediction to PRE-REGISTER at campaign start
    (admissibility filtering + budget-allocation focus) and SCORE against the actual — the self-learning loop
    (`reweight` already recalibrates the per-signal weights from the realized Brier ledger). PURE + injectable
    (the caller supplies the priced p_closes + the domain history), so it is hermetically testable with no hidden
    DB/embedder dependency and never blocks a campaign. Time model: a lemma with P(close)=p needs ~1/p expected
    attempts (geometric), each ≈ the domain's mean time-to-closure; E[campaign] sums over the lemmas."""
    p = [max(0.0, min(1.0, float(x))) for x in (p_closes or [])]
    n = len(p)
    yld = round(sum(p), 2)
    exp_time = round(sum((domain_mean_ttc_s or 0.0) / max(0.05, pi) for pi in p), 1) if domain_mean_ttc_s else None
    exp_cost = round(sum((domain_mean_cost_s or 0.0) / max(0.05, pi) for pi in p), 1) if domain_mean_cost_s else None
    return {"schema": "leanmill-campaign-p0-forecast-v1", "n_candidates": n, "domain": domain,
            "p_close": [round(x, 3) for x in p],
            "expected_yield": yld, "expected_yield_frac": (round(yld / n, 2) if n else None),
            "expected_time_to_closure_s": exp_time, "expected_cost_s": exp_cost,
            "hardest_lemma_index": (min(range(n), key=lambda i: p[i]) if n else None),
            "min_p_close": (round(min(p), 3) if p else None),
            "model": "geometric-expected-attempts × domain-mean-time"}


def domain_p0_history(domain: str, attempt_rows: "list[dict] | None" = None) -> dict:
    """The domain's historical P0 priors — {mean_ttc_s, mean_cost_s, close_rate} — for the campaign-start
    forecast, read from `phase_timing.summarize_campaign_cycle_time` over the attempts (segmented by domain via
    `record_campaign`). `close_rate` (mean closed/attempts over the domain's campaigns) is the per-lemma prior
    when a full per-candidate `price()` isn't run. Empty dict-ish (None values) on cold start / read error;
    best-effort, never blocks the campaign."""
    try:
        from ztare.leanmill.phase_timing import summarize_campaign_cycle_time
        rows = attempt_rows
        if rows is None:
            import sqlite3
            from pathlib import Path as _P
            db = _P("analytics/public/queries/solver_lane_attempts.db")
            if not db.exists():
                return None, None
            cx = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                cols = ("run_tag", "attempt_at", "outcome", "ratified", "wallclock_s", "move", "provider")
                rows = [dict(zip(cols, r)) for r in cx.execute(
                    f"SELECT {','.join(cols)} FROM attempts").fetchall()]
            finally:
                cx.close()
        summ = summarize_campaign_cycle_time(rows)
        camps = [c for c in (summ.get("campaigns", {}) or {}).values() if (c.get("domain") or "") == domain]
        with_ttc = [c for c in camps if (c.get("time_to_closure_s", {}) or {}).get("mean")]
        out = {"mean_ttc_s": None, "mean_cost_s": None, "close_rate": None, "n_campaigns": len(camps)}
        if with_ttc:
            out["mean_ttc_s"] = round(sum(c["time_to_closure_s"]["mean"] for c in with_ttc) / len(with_ttc), 1)
            costs = [c.get("cost_to_closure_s", {}).get("mean") for c in with_ttc
                     if c.get("cost_to_closure_s", {}).get("mean")]
            out["mean_cost_s"] = round(sum(costs) / len(costs), 1) if costs else None
        rates = [(c["yield"]["closed"] / c["attempts"]) for c in camps
                 if c.get("attempts") and isinstance(c.get("yield"), dict) and c["yield"].get("closed") is not None]
        if rates:
            out["close_rate"] = round(sum(rates) / len(rates), 3)
        return out
    except Exception:  # noqa: BLE001 — history read is best-effort
        return {"mean_ttc_s": None, "mean_cost_s": None, "close_rate": None, "n_campaigns": 0}


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)
    # ── campaign-start P0 forecast (pure aggregator) ──
    f = forecast_campaign_p0([0.9, 0.5, 0.2], domain="formalization-nonmath", domain_mean_ttc_s=600.0)
    ok("p0 forecast: expected_yield = Σ p_close", f["expected_yield"] == 1.6)
    ok("p0 forecast: hardest lemma = min p_close index", f["hardest_lemma_index"] == 2 and f["min_p_close"] == 0.2)
    # time = Σ ttc/p = 600/0.9 + 600/0.5 + 600/0.2 = 666.7 + 1200 + 3000 = 4866.7
    ok("p0 forecast: geometric-attempts × mean-ttc", abs(f["expected_time_to_closure_s"] - 4866.7) < 1.0)
    ok("p0 forecast: no history ⇒ time omitted, yield still given",
       forecast_campaign_p0([0.8, 0.8], domain="x")["expected_time_to_closure_s"] is None
       and forecast_campaign_p0([0.8, 0.8], domain="x")["expected_yield"] == 1.6)
    ok("p0 forecast: empty candidates ⇒ safe zeros", forecast_campaign_p0([])["n_candidates"] == 0)

    # ── pricing: cache-first, no-good dropped, EV ranks value×P ──────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as d:
        from ztare.leanmill.solver.proof_cache import ProofCache
        from ztare.leanmill.solver.no_good_store import NoGoodStore
        cache = ProofCache(Path(d) / "pc.jsonl"); cache.put("theorem hit : True := trivial", "trivial", "t")
        ng = NoGoodStore(Path(d) / "ng.jsonl"); ng.record("theorem bad : False := by sorry", "other_error", "w", confirmed=True)
        fcs = default_forecasters(cache_path=Path(d) / "pc.jsonl", no_good_path=Path(d) / "ng.jsonl",
                                  agent_votes={"hi": 0.9, "lo": 0.2})
        cands = [
            WorkCandidate("cached", move="m", statement="theorem hit : True := trivial", value=1.0),
            WorkCandidate("nogood", move="m", statement="theorem bad : False := by sorry", value=5.0),
            WorkCandidate("hi", move="m", value=2.0, base_cost=10),
            WorkCandidate("lo", move="m", value=2.0, base_cost=10),
        ]
        ranked = price(cands, fcs)
        order = [pc.candidate.id for pc in ranked]
        ok("cache hit routes FIRST", order[0] == "cached")
        ok("no-good is DROPPED to the back + flagged", order[-1] == "nogood" and ranked[-1].dropped)
        ok("higher agent-vote ranks above lower (EV)", order.index("hi") < order.index("lo"))
        ok("nogood candidate priced ~0 despite value=5", next(pc.p_close for pc in ranked if pc.candidate.id == "nogood") < 0.1)

    # ── resolution + reweight: an accurate signal earns weight, a wrong one loses it ─────────────────────────
    with tempfile.TemporaryDirectory() as d:
        ledger = Path(d) / "brier.jsonl"
        # forge priced candidates whose forecasts we control: signal "good" always right, "bad" always wrong
        def mk(pid, p_good, p_bad):
            fs = [SignalForecast("good", p_close=p_good, abstain=False),
                  SignalForecast("bad", p_close=p_bad, abstain=False)]
            return PricedCandidate(WorkCandidate(pid, move="m"), (p_good + p_bad) / 2, 0.0, fs)
        units = []
        for i in range(10):
            # even i: it CLOSES (y=1); good said .9, bad said .1
            pc = mk(f"c{i}", 0.9 if i % 2 == 0 else 0.1, 0.1 if i % 2 == 0 else 0.9)
            ex = LearningExit.CLOSED if i % 2 == 0 else LearningExit.GAP
            units.append(resolve(pc, ex, kernel_confirmed=True, ledger_path=ledger))
        w = reweight(ledger, Path(d) / "w.json")
        ok("accurate signal out-weighs the wrong one", _weight_of("good", "lean", w) > _weight_of("bad", "lean", w))
        ok("the wrong signal is floored, not silenced", _weight_of("bad", "lean", w) >= _MIN_W)
        ok("ensemble beats the move-prior baseline check returns a verdict", baseline_beaten(ledger) in (True, False, None))

        # INADMISSIBLE never writes a Brier row / deposits nothing
        before = ledger.read_text().count("\n")
        u = resolve(mk("dead", 0.9, 0.9), LearningExit.INADMISSIBLE, kernel_confirmed=False, ledger_path=ledger)
        ok("INADMISSIBLE resolve is non-admissible", not u.admissible)
        ok("INADMISSIBLE writes NO Brier row (certificate rule)", ledger.read_text().count("\n") == before)
        # unconfirmed kernel ⇒ also inadmissible even on a CLOSED-looking exit
        u2 = resolve(mk("unconf", 0.9, 0.9), LearningExit.CLOSED, kernel_confirmed=False, ledger_path=ledger)
        ok("unconfirmed CLOSED is refused (kernel is the arbiter)", not u2.admissible
           and ledger.read_text().count("\n") == before)

    # ── the promotion gate: blocked → advisory → promotable ──────────────────────────────────────────────────
    def _u(adm, dc):
        return KeyLearningUnit(LearningKind.POLICY, "k", LearningExit.CLOSED, adm, decision_changed=dc)
    ok("BLOCKED under min support", evaluate_promotion([_u(True, True)] * 3).status == "blocked")
    ok("ADVISORY when supported but baseline unproven",
       evaluate_promotion([_u(True, False)] * 10, beats_baseline=None).status == "advisory")
    ok("PROMOTABLE when supported ∧ beats baseline ∧ a decision changed",
       evaluate_promotion([_u(True, True)] * 10, beats_baseline=True).ready)

    # ── opt-out parity: =0 ⇒ routing_mode()=="off" (the A/B baseline arm); DEFAULT-ON otherwise ────────────────
    os.environ["ZTARE_LEANMILL_FORECAST_ROUTER"] = "0"
    ok("opt-out (=0) ⇒ routing_mode 'off' (baseline arm)", routing_mode() == "off")
    os.environ.pop("ZTARE_LEANMILL_FORECAST_ROUTER", None)
    ok("DEFAULT-ON (absent) uncalibrated ⇒ 'advisory' (never reorders until promoted)", routing_mode([_u(True, True)] * 3) == "advisory")

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
