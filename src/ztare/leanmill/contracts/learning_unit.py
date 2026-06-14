"""The leanmill LEARNING UNIT + taxonomy — the canonical spine for self-learning / compounding.

WHY (operator, 2026-06-10): "we need a self-learning compounder; we need to define what a 'learning exit' is
— in the past it was exit-C credits, but that is now at most a sub-item; we need a learning taxonomy and a KEY
learning unit, because if we don't define the categories it's hard to self-optimize." A 3-axis code inventory
(solver / autoformalize / governance, 2026-06-10) found the root cause this module fixes: leanmill had **two
disjoint learning worlds with four vocabularies for one concept** — the factory probe `exit_kind`
(`contracts/learning_feedback.py`: PROOF_VALUE / TESTED_LEARNING / TERMINAL) and the solver attempts-DB
`outcome` enum (`solver_core` `_record_attempt`) never shared an alphabet, and the autoformalize/governance
axes barely persist anything at all. This module is the single shared model both worlds map INTO.

THE KEY LEARNING UNIT (`KeyLearningUnit`) — the atomic, kernel/exogenous-CONFIRMED, reusable increment that
lowers the cost or raises the probability of a FUTURE attempt. Every existing store reduces to it (the common
shape the inventory extracted): `{kind, key, payload, exit, admissible, provenance, forecast↔realized, reuse}`.

THE TAXONOMY (`LearningKind`) — six MECE-ish categories spanning the three axes, each backed by an existing
store (see `KIND_BACKENDS`):
  • PROOF        — a verified proof of a (sub)goal              [proof_cache]                 (solver)
  • LEMMA        — an invented citable intermediate             [family_lemma_library, shelf] (solver)
  • REFUTATION   — a confirmed dead-end / counterexample / ¬G   [no_good_store, obstruction]  (solver+gov)
  • POLICY       — a calibrated prior / strategy choice         [move_calibration, agent-plan](orchestration)
  • FAITHFULNESS — a NL↔formal correspondence verdict (+xsub)   [firewall, cross_substrate]   (autoformalize)
  • CHEAT_PATTERN— a caught-laundering signature                [governance organs, catalog]  (governance)
"Exit-C credit" = a PROOF (CLOSED-exit) unit — one kind among six, exactly as the operator said.

THE LEARNING EXIT (`LearningExit`) — the unified DISPOSITION of an attempt: the one field that the solver
`outcome`, the factory `exit_kind`, the governance `verdict`, and the C-credit `evidence_status` were all
four spelling differently. An attempt is a LEARNING-EXIT when it deposits ≥1 ADMISSIBLE unit — so a FAILURE
is still a learning-exit (it deposits a REFUTATION + a POLICY datum). INADMISSIBLE deposits NOTHING (the
`apparatus_certificate` rule — a 0/N from a dead instrument must not enter learning; see the contaminated-DB
lesson). "Credit" is just the `admissible` bit, not the unit.

  python -m ztare.leanmill.contracts.learning_unit --selftest
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field, asdict
from typing import Any, Protocol, runtime_checkable


class LearningKind(enum.Enum):
    """WHAT kind of reusable knowledge a unit captures (the taxonomy axis)."""
    PROOF = "proof"                 # a verified proof reusable for an equivalent goal
    LEMMA = "lemma"                 # an invented citable intermediate (premise enrichment)
    REFUTATION = "refutation"       # a confirmed dead-end / counterexample / kernel-checked ¬G
    POLICY = "policy"               # a calibrated prior / move|substrate|depth strategy choice
    FAITHFULNESS = "faithfulness"   # a NL↔formal correspondence verdict (incl. cross-substrate)
    CHEAT_PATTERN = "cheat_pattern" # a caught-laundering signature (governance)


class LearningExit(enum.Enum):
    """The unified DISPOSITION of an attempt — collapses the four legacy vocabularies (solver `outcome`,
    factory `exit_kind`, governance `verdict`, C-credit `evidence_status`) into one enum. Each disposition
    declares which `LearningKind`s it deposits (see `exit_deposits`)."""
    CLOSED = "closed"               # a verified closure → PROOF (+ LEMMA helpers). The old "C credit".
    GAP = "gap"                     # an honest partial / sub-target remains → POLICY (got-close signal)
    REFUTED = "refuted"             # a confirmed counterexample / ¬G / dead-end → REFUTATION
    CHEAT_CAUGHT = "cheat_caught"   # governance caught a laundering attempt → CHEAT_PATTERN (+ REFUTATION)
    NO_SIGNAL = "no_signal"         # ran cleanly, produced nothing reusable → minimal POLICY (move didn't fire)
    INADMISSIBLE = "inadmissible"   # dead instrument / apparatus failure → DEPOSITS NOTHING (the certificate rule)


# ── vocabulary unification — map every legacy alphabet INTO LearningExit ──────────────────────────────────
# Solver attempts-DB `outcome` enum (solver_core._record_attempt) → the unified disposition.
_SOLVER_OUTCOME_TO_EXIT: "dict[str, LearningExit]" = {
    "closed": LearningExit.CLOSED,
    "tightened": LearningExit.CLOSED,            # rung-tighten produced a stronger closed statement
    "exact_gap": LearningExit.GAP, "open": LearningExit.GAP, "advanced": LearningExit.GAP,
    "rung": LearningExit.GAP, "new_sub_target": LearningExit.GAP,
    "falsifier": LearningExit.REFUTED, "sz_falsified": LearningExit.REFUTED,
    "retired_impossible": LearningExit.REFUTED,
    "rejected_negative_control": LearningExit.CHEAT_CAUGHT,
    "rejected_governance": LearningExit.CHEAT_CAUGHT,
    "no_advance": LearningExit.NO_SIGNAL, "no_witness": LearningExit.NO_SIGNAL,
    "no_seed": LearningExit.NO_SIGNAL, "failed": LearningExit.NO_SIGNAL,
    # apparatus failures (the dead-instrument class) — refused entry to learning:
    "inadmissible": LearningExit.INADMISSIBLE, "parse_error": LearningExit.INADMISSIBLE,
    "timeout": LearningExit.INADMISSIBLE, "failed_compile": LearningExit.INADMISSIBLE,
    "no_server": LearningExit.INADMISSIBLE,
}
# Factory probe `exit_kind` (contracts.learning_feedback) → the unified disposition. Imported lazily so this
# module has no hard dependency on the factory vocabulary (it merely subsumes it).
_FACTORY_EXIT_TO_EXIT: "dict[str, LearningExit]" = {
    "ratified_closure": LearningExit.CLOSED,
    "exact_gap_candidate": LearningExit.GAP,
    "valid_falsifier": LearningExit.REFUTED,
    "compile_candidate_needs_governance": LearningExit.GAP,
    "tested_no_positive_signal": LearningExit.NO_SIGNAL, "tested_probe_no_signal": LearningExit.NO_SIGNAL,
    "failed_negative_control": LearningExit.CHEAT_CAUGHT, "invalid_negative_control": LearningExit.INADMISSIBLE,
    "probe_failed": LearningExit.INADMISSIBLE, "probe_finished_no_tests": LearningExit.NO_SIGNAL,
    "retired": LearningExit.REFUTED, "tested_hold": LearningExit.NO_SIGNAL,
    "stale_family_spec_probe_packet": LearningExit.INADMISSIBLE,
}

# Which LearningKinds each disposition deposits (the learning-exit → unit(s) routing).
_EXIT_DEPOSITS: "dict[LearningExit, tuple[LearningKind, ...]]" = {
    LearningExit.CLOSED: (LearningKind.PROOF, LearningKind.LEMMA),
    LearningExit.GAP: (LearningKind.POLICY,),
    LearningExit.REFUTED: (LearningKind.REFUTATION,),
    LearningExit.CHEAT_CAUGHT: (LearningKind.CHEAT_PATTERN, LearningKind.REFUTATION),
    LearningExit.NO_SIGNAL: (LearningKind.POLICY,),
    LearningExit.INADMISSIBLE: (),                       # the apparatus_certificate rule — learn NOTHING
}


def exit_of(disposition: str) -> LearningExit:
    """Map any legacy disposition string (solver outcome | factory exit_kind | a LearningExit value) to the
    unified `LearningExit`. Unknown ⇒ NO_SIGNAL (conservative: ran, learned nothing — never fabricates CLOSED)."""
    d = (disposition or "").strip()
    for table in (_SOLVER_OUTCOME_TO_EXIT, _FACTORY_EXIT_TO_EXIT):
        if d in table:
            return table[d]
    try:
        return LearningExit(d)
    except ValueError:
        return LearningExit.NO_SIGNAL


def exit_deposits(exit: LearningExit) -> "tuple[LearningKind, ...]":
    """The LearningKind(s) a disposition is entitled to deposit (empty for INADMISSIBLE)."""
    return _EXIT_DEPOSITS.get(exit, ())


# ── the KEY LEARNING UNIT ─────────────────────────────────────────────────────────────────────────────────
@dataclass
class KeyLearningUnit:
    """The atomic reusable knowledge increment. `key` is the retrieval handle (a union the inventory found:
    a normalized statement key for PROOF/LEMMA/REFUTATION/FAITHFULNESS, a `move|move,error_class` cell for
    POLICY, a `(substrate,name)` for CHEAT_PATTERN). `admissible` is the "credit" bit — kernel/exogenous-
    CONFIRMED ∧ carrier-live; an inadmissible unit must NEVER be deposited or surfaced (the certificate rule)."""
    kind: LearningKind
    key: str
    exit: LearningExit
    admissible: bool
    payload: Any = None                                 # kind-specific: proof body / lemma decl / witness / prior / verdict
    # provenance (the recurring fields every store carries)
    target: str = ""                                    # row_id / problem identity
    carrier: str = ""                                   # move / provider / substrate that produced it
    source: str = ""                                    # free-form origin tag
    run_tag: str = ""                                   # A/B cohort
    attempt_at: str = ""                                # ISO8601 (caller stamps; this module never calls the clock)
    # ACTION-IMPACT attribution (design adapted from cognitive-firm `orchestration/action_impact.py`
    # ActionImpactRecordView; NOT imported — the payload-boundary discipline, like the signing reproduction).
    # The skin-in-the-game forecast↔realized pair + the causal value of this unit:
    est_p_close: "float | None" = None              # expected_impact — the forecast at dispatch (Brier skin)
    realized_value: "float | None" = None           # actual_impact — the measured value the unit produced
    decision_changed: "bool | None" = None          # Holmström informativeness — did consuming it change a decision?
    scope: str = "local"                            # local | project | system — how far the impact reaches
    externalities: "dict[str, float]" = field(default_factory=dict)   # cross-effects (a lemma reused on OTHER goals)
    context_features: "dict[str, Any]" = field(default_factory=dict)  # keyed by context_signature (the recall/bandit key)
    reuse: "dict[str, int]" = field(default_factory=lambda: {"exposures": 0, "citations": 0})

    def to_dict(self) -> "dict[str, Any]":
        d = asdict(self)
        d["kind"] = self.kind.value
        d["exit"] = self.exit.value
        return d


def admissible(exit: LearningExit, *, kernel_confirmed: bool, carrier_live: bool = True) -> bool:
    """The apparatus_certificate rule applied to a learning unit: a unit counts (earns "credit", enters the
    compounder, is surfaced to the agent/scheduler) ONLY if its disposition is admissible AND it was confirmed
    by the kernel/an exogenous organ AND the carrier was live. INADMISSIBLE dispositions and dead-carrier units
    are refused — a 0/N from a dead instrument must not enter learning (the contaminated-DB lesson)."""
    if exit is LearningExit.INADMISSIBLE:
        return False
    return bool(kernel_confirmed) and bool(carrier_live)


# ── the kind → backend registry (where each kind is persisted today; the inventory's wiring/health) ──────────
@dataclass
class Backend:
    module: str            # the store module
    persisted: bool        # does it survive a process exit?
    agent_consulted: bool  # does the leaf SEE it in its prompt?
    health: str            # live | half_dead | dead | stateless | offline


KIND_BACKENDS: "dict[LearningKind, Backend]" = {
    LearningKind.PROOF:         Backend("solver.proof_cache", True, False, "live"),          # agent-blind (the gap)
    LearningKind.LEMMA:         Backend("solver.family_lemma_library", True, True, "half_dead"),  # record_reuse never called
    LearningKind.REFUTATION:    Backend("solver.no_good_store", True, True, "live"),          # the one healthy accumulator
    LearningKind.POLICY:        Backend("solver.move_calibration", True, False, "live"),       # agent-blind + outcome_link dead
    LearningKind.FAITHFULNESS:  Backend("(none — stateless firewall/consensus)", False, False, "stateless"),  # the biggest gap
    LearningKind.CHEAT_PATTERN: Backend("common.kernel_hardener (gaming_vector_catalog)", True, False, "offline"),
}


# ── the COMPOUNDER interface — what every learning backend implements; the unifying layer ────────────────────
@runtime_checkable
class Compounder(Protocol):
    """The single contract a learning backend satisfies so the deposit→recall→measure loop is uniform across
    all six kinds (vs the six bespoke APIs the inventory found). A backend OWNS one or more LearningKinds.
    Implementations wrap the existing stores (proof_cache.put/get, no_good_store.record/prompt_block,
    move_calibration aggregate, …) — this is the seam, not a rewrite."""
    kind: LearningKind

    def deposit(self, unit: KeyLearningUnit) -> bool:
        """Persist an ADMISSIBLE unit (no-op + False on inadmissible). Returns whether it was newly stored."""
        ...

    def recall(self, key: str, *, for_agent: bool) -> "list[KeyLearningUnit] | str":
        """Retrieve units relevant to `key`. `for_agent=True` ⇒ a prompt-ready block (the goldilocks bridge —
        surface the deterministic store to the agent); `for_agent=False` ⇒ the structured units for the scheduler."""
        ...


def learning_exit_rate(exits: "list[LearningExit]") -> "dict[str, float]":
    """The self-optimization metric the operator asked for: of the attempts that RAN (excluding INADMISSIBLE
    apparatus failures), what fraction were a genuine learning-exit (deposited ≥1 unit)? Plus the disposition
    histogram. This is what makes 'scale learning' measurable — you optimize the learning-exit rate, not just
    the closure rate (CLOSED is one of six)."""
    total = len(exits)
    admissible_runs = [e for e in exits if e is not LearningExit.INADMISSIBLE]
    learning = [e for e in admissible_runs if exit_deposits(e)]
    hist: "dict[str, int]" = {}
    for e in exits:
        hist[e.value] = hist.get(e.value, 0) + 1
    return {
        "n": float(total),
        "inadmissible_rate": (total - len(admissible_runs)) / total if total else 0.0,
        "learning_exit_rate": len(learning) / len(admissible_runs) if admissible_runs else 0.0,
        "closure_rate": hist.get("closed", 0) / len(admissible_runs) if admissible_runs else 0.0,
        **{f"hist_{k}": float(v) for k, v in hist.items()},
    }


# ── borrowed primitives (design adapted from cognitive-firm `orchestration/action_impact.py`; NOT imported) ──
def context_signature(context_features: "dict[str, Any]", context_keys: "list[str]") -> "str | None":
    """A deterministic signature over a SUBSET of context features — the recall / bandit key for POLICY +
    FAITHFULNESS units (generalizes move_calibration's `(move, error_class)` cell + the agent-plan goal-structure
    into one principled context hash). Returns None if any required key is absent (fail-closed: no signature ⇒
    no false grouping). Adapted from `cognitive_firm.orchestration.action_impact.context_signature`."""
    import json
    if any(k not in context_features for k in context_keys):
        return None
    return json.dumps({k: context_features[k] for k in context_keys}, sort_keys=True, separators=(",", ":"))


@dataclass
class PolicyPromotion:
    """The LEARNING-EXIT → DEPLOYMENT gate: when is a learned POLICY trusted enough to flip default-on?
    Adapted from cognitive-firm's PolicyEvaluation (blocked → advisory → promotable). It UNIFIES the three
    ad-hoc trust-gates the 2026-06-10 inventory found — move_calibration's `min_governed=8`, learned_context's
    double-flag (`LEARNED_CONTEXT ∧ CALIBRATION_TRUSTED`), and outcome_link's Holmström `decisions_changed>0`:
      • BLOCKED    — too little ADMISSIBLE support (off-policy coverage below floor) ⇒ do NOT surface or deploy.
      • ADVISORY   — enough support to INFORM (surface to the agent) but not to AUTO-deploy (keep the flag off).
      • PROMOTABLE — supported ∧ beats baseline ∧ changed ≥1 decision (Holmström) ⇒ safe to flip default-on."""
    status: str                          # blocked | advisory | promotable
    support: float                       # admissible-support coverage in [0,1]
    reason: str = ""

    @property
    def ready(self) -> bool:
        return self.status == "promotable"


def evaluate_promotion(units: "list[KeyLearningUnit]", *, min_support: int = 8,
                       min_support_coverage: float = 0.25,
                       beats_baseline: "bool | None" = None) -> PolicyPromotion:
    """Off-policy-style promotion gate over the units for ONE context/arm. BLOCKED until BOTH a count floor
    (`min_support`, ≈ move_calibration's `min_governed`) AND a coverage floor (`min_support_coverage`) of
    ADMISSIBLE units are met; ADVISORY once supported; PROMOTABLE only when it ALSO beats baseline AND changed
    ≥1 decision (the Holmström informativeness — an uninformative retune is never promoted). Conservative by
    construction: with `beats_baseline` unproven or no decision-change, a well-supported policy stays ADVISORY,
    never auto-deployed. This is the principled replacement for the scattered `min_governed`/double-flag gates."""
    adm = [u for u in units if u.admissible]
    n = len(adm)
    coverage = n / len(units) if units else 0.0
    if n < min_support or coverage < min_support_coverage:
        return PolicyPromotion("blocked", coverage,
                               f"support {n}/{len(units)} (cov {coverage:.2f}) below floor "
                               f"(n≥{min_support} ∧ cov≥{min_support_coverage})")
    if beats_baseline and any(u.decision_changed for u in adm):
        return PolicyPromotion("promotable", coverage, "supported ∧ beats baseline ∧ changed ≥1 decision (Holmström)")
    return PolicyPromotion("advisory", coverage,
                           "supported; not promotable (needs beats-baseline ∧ a changed decision)")


def _self_test() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # vocabulary unification: all four alphabets collapse to the same disposition
    ok("solver 'closed' → CLOSED", exit_of("closed") is LearningExit.CLOSED)
    ok("factory 'ratified_closure' → CLOSED (same disposition, different alphabet)",
       exit_of("ratified_closure") is LearningExit.CLOSED)
    ok("solver 'rejected_governance' → CHEAT_CAUGHT", exit_of("rejected_governance") is LearningExit.CHEAT_CAUGHT)
    ok("dead-instrument 'parse_error'/'timeout' → INADMISSIBLE",
       exit_of("parse_error") is LearningExit.INADMISSIBLE and exit_of("timeout") is LearningExit.INADMISSIBLE)
    ok("unknown disposition → NO_SIGNAL (never fabricates CLOSED)", exit_of("???") is LearningExit.NO_SIGNAL)

    # the learning-exit → kind routing
    ok("CLOSED deposits PROOF+LEMMA (the old C-credit, now one kind)",
       set(exit_deposits(LearningExit.CLOSED)) == {LearningKind.PROOF, LearningKind.LEMMA})
    ok("a FAILURE is still a learning-exit: REFUTED → REFUTATION",
       exit_deposits(LearningExit.REFUTED) == (LearningKind.REFUTATION,))
    ok("CHEAT_CAUGHT → CHEAT_PATTERN + REFUTATION",
       set(exit_deposits(LearningExit.CHEAT_CAUGHT)) == {LearningKind.CHEAT_PATTERN, LearningKind.REFUTATION})
    ok("INADMISSIBLE deposits NOTHING (the certificate rule)", exit_deposits(LearningExit.INADMISSIBLE) == ())

    # the admissibility ("credit") bit
    ok("admissible: CLOSED + kernel-confirmed + carrier-live", admissible(LearningExit.CLOSED, kernel_confirmed=True))
    ok("inadmissible: dead carrier refused", not admissible(LearningExit.CLOSED, kernel_confirmed=True, carrier_live=False))
    ok("inadmissible: unconfirmed refused", not admissible(LearningExit.REFUTED, kernel_confirmed=False))
    ok("inadmissible: INADMISSIBLE disposition refused", not admissible(LearningExit.INADMISSIBLE, kernel_confirmed=True))

    # the KLU shape + serialization
    u = KeyLearningUnit(LearningKind.PROOF, key="t : True", exit=LearningExit.CLOSED, admissible=True,
                        payload="by trivial", carrier="native_hammer", target="row1")
    d = u.to_dict()
    ok("KLU serializes kind/exit as values", d["kind"] == "proof" and d["exit"] == "closed")
    ok("KLU carries the reuse compounding measure", d["reuse"] == {"exposures": 0, "citations": 0})

    # the self-optimization metric: learning-exit rate excludes apparatus failures
    exits = [LearningExit.CLOSED, LearningExit.REFUTED, LearningExit.INADMISSIBLE, LearningExit.NO_SIGNAL,
             LearningExit.GAP, LearningExit.INADMISSIBLE]
    m = learning_exit_rate(exits)
    ok("learning_exit_rate excludes INADMISSIBLE from the denominator",
       abs(m["inadmissible_rate"] - 2 / 6) < 1e-9 and abs(m["learning_exit_rate"] - 1.0) < 1e-9)
    ok("closure_rate is one sub-rate, not the whole story", abs(m["closure_rate"] - 1 / 4) < 1e-9)

    # the backend registry reflects the inventory's health verdicts
    ok("FAITHFULNESS backend is the stateless gap", KIND_BACKENDS[LearningKind.FAITHFULNESS].health == "stateless")
    ok("REFUTATION is the one live agent-consulted accumulator",
       KIND_BACKENDS[LearningKind.REFUTATION].agent_consulted and KIND_BACKENDS[LearningKind.REFUTATION].health == "live")
    ok("PROOF + POLICY are agent-blind (the goldilocks gap)",
       not KIND_BACKENDS[LearningKind.PROOF].agent_consulted and not KIND_BACKENDS[LearningKind.POLICY].agent_consulted)

    # borrowed primitive — context_signature (the recall/bandit key)
    sig = context_signature({"goal_class": "comm_ring", "move": "warm", "x": 9}, ["goal_class", "move"])
    ok("context_signature deterministic over the chosen keys", sig == '{"goal_class":"comm_ring","move":"warm"}')
    ok("context_signature fail-closed on a missing key", context_signature({"a": 1}, ["a", "b"]) is None)

    # borrowed primitive — the PolicyPromotion gate (blocked → advisory → promotable)
    def _u(adm=True, dc=False):
        return KeyLearningUnit(LearningKind.POLICY, key="k", exit=LearningExit.CLOSED, admissible=adm, decision_changed=dc)
    ok("promotion BLOCKED on thin support", evaluate_promotion([_u()] * 3, min_support=8).status == "blocked")
    ten = [_u(dc=True)] * 10
    ok("promotion ADVISORY when supported but baseline unproven (conservative)", evaluate_promotion(ten).status == "advisory")
    ok("promotion PROMOTABLE only when supported ∧ beats baseline ∧ a decision changed (Holmström)",
       evaluate_promotion(ten, beats_baseline=True).ready is True)
    ok("promotion stays ADVISORY if no decision changed (uninformative not promoted)",
       evaluate_promotion([_u(dc=False)] * 10, beats_baseline=True).status == "advisory")
    ok("inadmissible units don't count toward support (the certificate rule)",
       evaluate_promotion([_u(adm=False)] * 10, min_support=8).status == "blocked")

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test() if "--selftest" in sys.argv else (print(__doc__) or 0))
