"""Outcome links — bind a CALIBRATION RETUNE to a measured CLOSURE@BUDGET outcome.

The Holmström informativeness principle applied to the solver's self-tuning. `move_calibration`
RECORDS that priors shifted (a retune happened) and `recorded_forecast_brier` measures a PROXY
(forecast Brier). Neither records whether a retune actually moved the OBJECTIVE — closure@budget —
nor whether the retune was even INFORMATIVE (did it change a single move-selection DECISION?). That
makes the self-tuning's own validity claim — "tuning the priors closes more rows" — untestable from
the kernel's own records, and lets a retune that tuned a proxy masquerade as progress.

An :class:`OutcomeLink` is that missing record. It binds a *change* — a calibration retune (a
selection-prior shift, an autotune-k change) — to a *measured outcome* on ONE objective metric
(closure@budget), carrying the DECISION_CHANGED attribution. Lifecycle:

    open ── baseline ──▶ measuring ── post + decisions_changed ──▶ verdict_recorded
      │                                                                 │
      └──────────────────────────── void ───────────────────────────────┘

THE HOLMSTRÖM GATE (the exogenous, load-bearing piece): a retune that changed ZERO move-selection
decisions is NON-INFORMATIVE about the outcome and is recorded `inconclusive` — it can NEVER be
credited "improved" no matter how closure@budget moved, because the metric movement cannot be
attributed to it. Only a retune that changed ≥1 decision AND raised closure@budget earns `improved`.
This mechanizes the master discriminator (route the evidence to an exogenous carrier; distrust a
self-narrated win): the verdict is computed from exogenous numbers — the attempts-DB closure counts
and the DAG trace's changed-decision count — never narrated by the solver.

BOUNDARY (mirrors cognitive-firm `orchestration/outcome_links.py`, the borrow source): the harness
SUPPLIES the exogenous snapshot values + the decisions_changed count; this module owns the typed
record, the lifecycle, the deterministic verdict, and the `verdict_coverage` read model.

EXTENSION POINT (cited; not a parallel build): co-located with `proof_cache.py` (the wins store) and
`no_good_store.py` (the refutations store) in the solver package; the store file is
`OUT_DIR/solver_lane_outcome_links.jsonl` — the self-tuning dual that stores RETUNE→OUTCOME credit.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Canonical store home (same OUT_DIR the solver-lane stores use), resolved without importing
# solver_core (avoid an import cycle): src/ztare/leanmill/solver/outcome_link.py → repo root.
_REPO = Path(__file__).resolve().parents[4]
DEFAULT_OUTCOME_LINKS_LOG = _REPO / "analytics" / "public" / "queries" / "solver_lane_outcome_links.jsonl"

DEFAULT_OBJECTIVE_METRIC = "closure_at_budget"   # the OBJECTIVE, not the Brier proxy

VALID_STATUSES = {"open", "measuring", "verdict_recorded", "voided"}
VALID_VERDICTS = {"improved", "no_change", "regressed", "inconclusive"}
TERMINAL_STATES = {"verdict_recorded", "voided"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class OutcomeLink:
    """A durable link from a calibration retune to a measured closure@budget outcome."""

    link_id: str
    change_ref: str                     # what changed (e.g. a run_tag, a prior-shift fingerprint)
    change_kind: str                    # free label, e.g. "calibration_retune" / "autotune_k"
    metric_name: str
    created_at_utc: str
    updated_at_utc: str
    created_by: str = "solver.calibration"
    status: str = "open"
    baseline_value: float | None = None
    baseline_n: int | None = None       # sample size of the baseline measurement
    post_value: float | None = None
    post_n: int | None = None
    decisions_changed: int | None = None  # # move-selection decisions the retune flipped (the Holmström signal)
    verdict: str | None = None
    verdict_rationale: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATES


@dataclass
class OutcomeLinkSummary:
    """Read model: of N calibration retunes, how many demonstrably moved closure@budget."""

    total: int
    open: int
    measuring: int
    verdict_recorded: int
    voided: int
    improved: int
    no_change: int
    regressed: int
    inconclusive: int
    # of the retunes that earned a verdict, how many improved closure@budget AND were informative:
    credited_improvements: int
    # verdict_coverage = verdicts recorded / (links that are not voided) — how much of the self-tuning
    # we can actually speak to. Low coverage ⇒ the loop is open (we retune but never measure).
    verdict_coverage: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class OutcomeLinkStore:
    """Append-only JSONL store of outcome links (mirrors ProofCache/NoGoodStore load/append idiom)."""

    def __init__(self, path: "str | Path | None" = None):
        self.path = Path(path) if path is not None else DEFAULT_OUTCOME_LINKS_LOG
        self._mem: dict[str, OutcomeLink] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:  # noqa: BLE001 — a corrupt line never breaks the store
                    continue
                # last-write-wins on link_id (the JSONL is an append-only event log; latest state wins)
                try:
                    self._mem[rec["link_id"]] = OutcomeLink(**rec)
                except Exception:  # noqa: BLE001 — schema drift on an old row is skipped, not fatal
                    continue

    # ── lifecycle ────────────────────────────────────────────────────────────────────────────────
    def open_link(self, *, change_ref: str, baseline_value: float, baseline_n: int | None = None,
                  change_kind: str = "calibration_retune", metric_name: str = DEFAULT_OBJECTIVE_METRIC,
                  created_by: str = "solver.calibration", metadata: dict | None = None,
                  link_id: str | None = None) -> OutcomeLink:
        """Open a link with its baseline snapshot (closure@budget BEFORE the retune)."""
        now = _now_iso()
        link = OutcomeLink(
            link_id=link_id or uuid.uuid4().hex[:16], change_ref=str(change_ref),
            change_kind=str(change_kind), metric_name=str(metric_name),
            created_at_utc=now, updated_at_utc=now, created_by=str(created_by),
            status="measuring" if baseline_value is not None else "open",
            baseline_value=float(baseline_value), baseline_n=baseline_n,
            metadata=dict(metadata or {}))
        self._persist(link)
        return link

    def record_post(self, link_id: str, *, post_value: float, decisions_changed: int,
                    post_n: int | None = None) -> OutcomeLink:
        """Record the post-retune closure@budget + how many move-selection decisions the retune
        actually changed (the informativeness signal). Transitions to `measuring`."""
        link = self._get(link_id)
        if link.is_terminal():
            raise ValueError(f"link {link_id} is terminal ({link.status}); cannot record post")
        link.post_value = float(post_value)
        link.post_n = post_n
        link.decisions_changed = int(decisions_changed)
        link.status = "measuring"
        link.updated_at_utc = _now_iso()
        self._persist(link)
        return link

    def record_verdict(self, link_id: str, *, min_delta: float = 1e-9) -> OutcomeLink:
        """DETERMINISTICALLY compute the verdict from the exogenous snapshots + the Holmström gate.

        - decisions_changed == 0  → `inconclusive` (NON-INFORMATIVE: the retune changed no decision,
          so closure movement cannot be attributed to it — it is NEVER credited, the master-
          discriminator gate).
        - post > baseline + min_delta  AND decisions_changed > 0 → `improved`
        - post < baseline - min_delta  → `regressed`
        - otherwise → `no_change`."""
        link = self._get(link_id)
        if link.is_terminal():
            return link
        if link.baseline_value is None or link.post_value is None or link.decisions_changed is None:
            raise ValueError(f"link {link_id} missing baseline/post/decisions_changed; cannot verdict")
        delta = link.post_value - link.baseline_value
        if link.decisions_changed == 0:
            link.verdict = "inconclusive"
            link.verdict_rationale = (
                f"retune changed 0 move-selection decisions → non-informative; closure delta "
                f"{delta:+.3f} cannot be attributed to it (Holmström gate)")
        elif delta > min_delta:
            link.verdict = "improved"
            link.verdict_rationale = (
                f"closure@budget {link.baseline_value:.3f}→{link.post_value:.3f} ({delta:+.3f}) "
                f"with {link.decisions_changed} decision(s) changed → informative improvement")
        elif delta < -min_delta:
            link.verdict = "regressed"
            link.verdict_rationale = (
                f"closure@budget {link.baseline_value:.3f}→{link.post_value:.3f} ({delta:+.3f}) → regressed")
        else:
            link.verdict = "no_change"
            link.verdict_rationale = (
                f"closure@budget flat ({delta:+.3f}) despite {link.decisions_changed} decision(s) changed")
        link.status = "verdict_recorded"
        link.updated_at_utc = _now_iso()
        self._persist(link)
        return link

    def void(self, link_id: str, *, reason: str) -> OutcomeLink:
        link = self._get(link_id)
        if link.is_terminal():
            return link
        link.status = "voided"
        link.verdict_rationale = f"voided: {reason}"
        link.updated_at_utc = _now_iso()
        self._persist(link)
        return link

    # ── read model ───────────────────────────────────────────────────────────────────────────────
    def all_links(self) -> list[OutcomeLink]:
        return list(self._mem.values())

    def summary(self) -> OutcomeLinkSummary:
        links = self.all_links()
        by_status: dict[str, int] = {s: 0 for s in VALID_STATUSES}
        by_verdict: dict[str, int] = {v: 0 for v in VALID_VERDICTS}
        for ln in links:
            by_status[ln.status] = by_status.get(ln.status, 0) + 1
            if ln.verdict:
                by_verdict[ln.verdict] = by_verdict.get(ln.verdict, 0) + 1
        non_voided = len(links) - by_status["voided"]
        coverage = (by_status["verdict_recorded"] / non_voided) if non_voided else 0.0
        return OutcomeLinkSummary(
            total=len(links), open=by_status["open"], measuring=by_status["measuring"],
            verdict_recorded=by_status["verdict_recorded"], voided=by_status["voided"],
            improved=by_verdict["improved"], no_change=by_verdict["no_change"],
            regressed=by_verdict["regressed"], inconclusive=by_verdict["inconclusive"],
            credited_improvements=by_verdict["improved"], verdict_coverage=round(coverage, 4))

    # ── persistence ──────────────────────────────────────────────────────────────────────────────
    def _persist(self, link: OutcomeLink) -> None:
        self._mem[link.link_id] = link
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(link.as_dict(), sort_keys=True) + "\n")

    def _get(self, link_id: str) -> OutcomeLink:
        if link_id not in self._mem:
            raise KeyError(f"outcome link not found: {link_id}")
        return self._mem[link_id]


def ranking_decisions_changed(old_priors: dict[str, float], new_priors: dict[str, float]) -> int:
    """Exogenous attribution proxy: how many move-SELECTION decisions a prior retune could have
    flipped, measured as the number of moves whose RANK changed in the prior ordering. A best-first
    search selects by prior order, so a retune that preserves the ordering changes ZERO selections by
    construction (decisions_changed=0 → the Holmström gate fires → it cannot be credited). Cheap,
    deterministic, computable at retune time without running the solver. Moves present in only one
    map are treated as rank-changed (appeared/disappeared from the ranking)."""
    def _rank(priors: dict[str, float]) -> dict[str, int]:
        # higher prior = better = lower rank index; tie-break by move name for determinism.
        order = sorted(priors.items(), key=lambda kv: (-kv[1], kv[0]))
        return {m: i for i, (m, _) in enumerate(order)}
    ro, rn = _rank(old_priors), _rank(new_priors)
    moves = set(old_priors) | set(new_priors)
    return sum(1 for m in moves if ro.get(m) != rn.get(m))


def record_calibration_retune(*, change_ref: str, old_priors: dict[str, float],
                              new_priors: dict[str, float], baseline_closure: float,
                              post_closure: float, baseline_n: int | None = None,
                              post_n: int | None = None, store_path: "str | Path | None" = None,
                              min_delta: float = 1e-9) -> OutcomeLink:
    """Bind a prior retune (old→new priors) to its closure@budget outcome, deriving the
    decisions_changed attribution from the ordering change. The convenience the autotune calls."""
    return record_retune_outcome(
        change_ref=change_ref, baseline_closure=baseline_closure, post_closure=post_closure,
        decisions_changed=ranking_decisions_changed(old_priors, new_priors),
        baseline_n=baseline_n, post_n=post_n, change_kind="calibration_retune",
        store_path=store_path, min_delta=min_delta)


def record_retune_outcome(*, change_ref: str, baseline_closure: float, post_closure: float,
                          decisions_changed: int, baseline_n: int | None = None,
                          post_n: int | None = None, change_kind: str = "calibration_retune",
                          metric_name: str = DEFAULT_OBJECTIVE_METRIC,
                          store_path: "str | Path | None" = None, min_delta: float = 1e-9) -> OutcomeLink:
    """One-shot convenience for the batch case (both arms measured): open → baseline → post → verdict.
    Returns the verdict-recorded link. Fail-safe to compute; the caller persists via the store."""
    store = OutcomeLinkStore(store_path)
    link = store.open_link(change_ref=change_ref, baseline_value=baseline_closure,
                           baseline_n=baseline_n, change_kind=change_kind, metric_name=metric_name)
    store.record_post(link.link_id, post_value=post_closure, decisions_changed=decisions_changed,
                      post_n=post_n)
    return store.record_verdict(link.link_id, min_delta=min_delta)


def _selftest() -> int:
    import tempfile
    fails: list[str] = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    p = Path(tempfile.mktemp(suffix=".jsonl"))
    store = OutcomeLinkStore(p)

    # POSITIVE: a retune that changed 3 decisions AND raised closure 2→4 → improved + credited.
    pos = record_retune_outcome(change_ref="run_tag=A", baseline_closure=2, post_closure=4,
                                decisions_changed=3, store_path=p)
    ok("positive_informative_improvement_is_credited", pos.verdict == "improved")

    # NEGATIVE (the Holmström gate): a retune that RAISED closure 2→5 but changed 0 decisions is
    # NON-INFORMATIVE → inconclusive, NEVER credited (the improvement cannot be attributed to it).
    neg = record_retune_outcome(change_ref="run_tag=B", baseline_closure=2, post_closure=5,
                                decisions_changed=0, store_path=p)
    ok("zero_decision_change_is_inconclusive_not_credited", neg.verdict == "inconclusive")

    # NEGATIVE (regression): changed decisions but closure dropped 4→2 → regressed (steer away).
    reg = record_retune_outcome(change_ref="run_tag=C", baseline_closure=4, post_closure=2,
                                decisions_changed=2, store_path=p)
    ok("informative_regression_flagged", reg.verdict == "regressed")

    # NO-CHANGE: changed decisions but closure flat → no_change.
    flat = record_retune_outcome(change_ref="run_tag=D", baseline_closure=3, post_closure=3,
                                 decisions_changed=1, store_path=p)
    ok("flat_metric_is_no_change", flat.verdict == "no_change")

    # COVERAGE: 4 verdicts recorded, 0 voided → coverage 1.0; exactly 1 credited improvement.
    s = OutcomeLinkStore(p).summary()
    ok("verdict_coverage_full", s.verdict_coverage == 1.0 and s.verdict_recorded == 4)
    ok("exactly_one_credited_improvement", s.credited_improvements == 1)

    # PERSISTENCE: reopen from disk preserves the verdicts (the loop is auditable across runs).
    reopened = OutcomeLinkStore(p)
    ok("persisted_across_reopen", len(reopened.all_links()) == 4
       and reopened._get(pos.link_id).verdict == "improved")

    # INCREMENTAL API: open with a baseline, leave it measuring → counts toward awaiting/coverage<1.
    store2_path = Path(tempfile.mktemp(suffix=".jsonl"))
    st2 = OutcomeLinkStore(store2_path)
    lk = st2.open_link(change_ref="run_tag=E", baseline_value=1)
    ok("open_link_is_measuring", lk.status == "measuring" and lk.baseline_value == 1)
    ok("coverage_below_one_when_unmeasured", st2.summary().verdict_coverage == 0.0)

    # RANKING attribution proxy: a rescale that PRESERVES order changes 0 decisions; a reorder >0.
    ok("rank_preserving_retune_changes_no_decision",
       ranking_decisions_changed({"a": 0.9, "b": 0.5, "c": 0.1}, {"a": 0.8, "b": 0.4, "c": 0.05}) == 0)
    ok("rank_flip_changes_decisions",
       ranking_decisions_changed({"a": 0.9, "b": 0.5}, {"a": 0.4, "b": 0.7}) == 2)
    # end-to-end: a rank-preserving "improvement" is INCONCLUSIVE via the ordering proxy (Holmström).
    rc = record_calibration_retune(change_ref="k=8->16", old_priors={"a": 0.9, "b": 0.5},
                                   new_priors={"a": 0.8, "b": 0.45}, baseline_closure=2, post_closure=4,
                                   store_path=Path(tempfile.mktemp(suffix=".jsonl")))
    ok("rank_preserving_retune_outcome_inconclusive", rc.verdict == "inconclusive")

    p.exists() and p.unlink()
    store2_path.exists() and store2_path.unlink()
    print("OUTCOME-LINK SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
