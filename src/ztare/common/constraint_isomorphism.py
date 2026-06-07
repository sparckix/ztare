"""Constraint-to-Isomorphism engine — the canonical "strange loop" for autonomously surfacing
cross-field structural matches (the next "Barrington") when a system hits a structural ceiling.

WHY THIS IS GENERAL (and an interface, not a per-domain rebuild). `fit/analogy.py` already does the
hard middle — query a frontier LLM with ONLY a domain-stripped structural fingerprint and let a
holdout oracle verify/kill the answer — but it is welded to curve-fit residuals. This module is the
uplevel: the SHARED engine (the contamination-disciplined isomorphism query + the verify-via-oracle
discipline) lives here once; each consumer (leanmill proof search, a research director, the
autoresearch fit loop) plugs in its own domain piece via the `StrangeLoopDomain` Strategy. Same
pattern as `ztare.fit.mdl.MDLLibrary`.

THE THREE STEPS (Step 2 is the engine's; 1 and 3 are the domain's):
  1. abstract_failure   — DOMAIN: turn a concrete failure (a degrading closure rate, a residual
                          surface, a stalled research seam) into a `ConstraintFingerprint`: pure
                          topology / complexity / algebra, ALL domain syntax stripped.
  2. isomorphism query  — ENGINE: ask an LLM, given ONLY that abstract constraint and a domain to
                          push AWAY from, to name established theorems/algorithms/laws from ANY
                          field that solve exactly those constraints. Stripping the semantic gravity
                          is the mechanism: "do barrington" fails because it is orthogonal; "what
                          solves O(1)-width O(log n)-depth composition?" can surface it.
  3. compile_to_test + oracle — DOMAIN: map a surfaced match onto the system's variables, compile it
                          to a testable gate, and score it on a HOLDOUT. A match that does not
                          improve the oracle metric (MDL / closure rate / MRE) is bullshit and is
                          discarded. The loop only "completes" (mutates the architecture) on a
                          holdout-verified improvement.

DISCIPLINE (inherited from the validated GP-164 analogy primitive): the LLM PROPOSES, the oracle
DISPOSES. The query is structural-only (no variable names / charter prose / domain axioms — those
contaminate by letting the model retrieve a known RESULT rather than a known FORM). Every surfaced
match and verdict is auditable. Nothing mutates the live system except via a holdout-verified gate.

CANONICAL INVARIANT (the engine/consumer pattern — same as ztare.fit.mdl.MDLLibrary):
  1. ONE engine per capability = `IsomorphismLoop`. That is the surfaced PRIMITIVE.
  2. A DOMAIN/CONSUMER (`StrangeLoopDomain`) is a Strategy PLUG — specialized by CONFIG/COMPOSITION
     (a query, an oracle_fn, a failure_state, a forbidden_domain), or at most by subclassing the
     GENERAL domain. NEVER a parallel per-subject reimplementation; a consumer is NOT a primitive
     and is not surfaced in the catalog.
  3. The SUBJECT (leanmill, a research seam) is config/INPUT to the general domain, not its own
     domain. There is exactly one level: research-direction / architecture. The strange loop is an
     RD tool that takes a SYSTEM ceiling as input — it does NOT run inside the solver per proof.
  4. The distance-from-home knob `forbidden_domain` UNIFIES the autoresearch family: None → ANALOGY
     (match any field, incl. adjacent); set → DEANCHOR (forbid home + adjacent → the orthogonal jump).
     `fit/analogy.py` (ANALOGY) and `fit/cold_llm_erdos_seed.py` (DEANCHOR) are two settings of this
     one engine, not two systems.

STATUS: apparatus only. Whether the autonomous loop actually surfaces USEFUL matches (vs. plausible
nonsense) is an open efficacy question — build-to-have-ready, prove it works before trusting it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol


# ─────────────────────────────────────────────────────────────────────────────
# Typed objects (the contract between the engine and a domain)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConstraintFingerprint:
    """A domain-STRIPPED statement of why the system is stuck — the search query for Step 2.
    Carries NO domain syntax (no Lean tactics, no variable names, no charter prose): only the
    abstract mathematical shape of the ceiling, so the LLM retrieves structure, not a memorized
    answer for the home domain."""
    constraint_class: str                  # e.g. "bounded-width sequential composition"
    abstract_form: str                     # pure-math statement (topology/complexity/algebra)
    invariants: dict = field(default_factory=dict)   # structural stats (depth, width, monotonicity…)
    forbidden_domain: Optional[str] = None  # the HOME field to push away from (the orthogonal jump)

    def is_contaminated(self, banned_terms: "list[str]") -> bool:
        """Guard: the fingerprint must not leak home-domain vocabulary (which would let the model
        retrieve a known result instead of a structural form). Caller supplies the banned terms."""
        blob = f"{self.constraint_class} {self.abstract_form} {self.invariants}".lower()
        return any(t.lower() in blob for t in banned_terms if t)


@dataclass
class SurfacedIsomorphism:
    """One cross-field candidate the engine surfaced for an abstract constraint."""
    theorem: str                   # the named theorem / algorithm / law
    field: str                     # the field it comes from
    mechanism: str                 # HOW it solves the abstract constraint
    mapping_hint: str = ""         # how its components map back to the system's variables
    raw: str = ""                  # raw LLM text (audit)


@dataclass
class IsomorphismVerdict:
    """The holdout-oracle's judgment on a surfaced match once compiled to a testable gate."""
    iso: SurfacedIsomorphism
    metric_before: float
    metric_after: float
    improves: bool
    detail: dict = field(default_factory=dict)

    @property
    def delta(self) -> float:
        return self.metric_after - self.metric_before


# ─────────────────────────────────────────────────────────────────────────────
# The Strategy a consumer implements (the per-domain pieces: Steps 1 and 3)
# ─────────────────────────────────────────────────────────────────────────────

class StrangeLoopDomain(Protocol):
    def abstract_failure(self, failure_state: object) -> ConstraintFingerprint:
        """Step 1: fingerprint a concrete ceiling into a domain-stripped ConstraintFingerprint."""
        ...

    def compile_to_test(self, iso: SurfacedIsomorphism, context: object) -> object:
        """Step 3a: map a surfaced theorem onto this system's variables and return a GATE enforcing
        its mechanism. The gate is OPAQUE to the engine — its type is whatever this domain's `oracle`
        knows how to apply (a predicate, a policy/transform, a config delta…). Raise to reject an
        unmappable match."""
        ...

    def oracle(self, gate: "object | None", holdout: object) -> float:
        """Step 3b: score the system on a HOLDOUT under `gate` (None = baseline, no gate). Higher is
        better (closure rate, −MDL, −MRE — the domain's improvement metric). The deterministic judge;
        it owns how the gate is applied."""
        ...

    def banned_terms(self) -> "list[str]":
        """Home-domain vocabulary the fingerprint must NOT contain (contamination guard). Optional —
        a domain may return [] to skip the check."""
        ...


# The Step-2 query signature: (fingerprint, n) -> surfaced matches. Injected so the engine is
# testable with a mock and wired to the real LLM in production.
IsomorphismQuery = Callable[[ConstraintFingerprint, int], "list[SurfacedIsomorphism]"]


# ─────────────────────────────────────────────────────────────────────────────
# The engine
# ─────────────────────────────────────────────────────────────────────────────

class IsomorphismLoop:
    """The shared strange-loop orchestrator. Construct with a domain (Steps 1 & 3) and a query
    (Step 2; defaults to the LLM query). `run` executes failure → fingerprint → cross-field query →
    compile → holdout-verify, returning the verdicts. Only matches that IMPROVE the oracle survive."""

    def __init__(self, domain: StrangeLoopDomain, query: "IsomorphismQuery | None" = None):
        self.domain = domain
        self._query = query  # None → resolve the default LLM query lazily on first run

    def query(self, fp: ConstraintFingerprint, n: int) -> "list[SurfacedIsomorphism]":
        if self._query is None:
            self._query = default_llm_query
        return self._query(fp, n)

    def run(self, failure_state: object, holdout: object, *,
            n_candidates: int = 5, context: object = None,
            strict_contamination: bool = True) -> "list[IsomorphismVerdict]":
        # Step 1 — abstract the failure (domain).
        fp = self.domain.abstract_failure(failure_state)
        banned = []
        try:
            banned = list(self.domain.banned_terms() or [])
        except Exception:
            banned = []
        if strict_contamination and banned and fp.is_contaminated(banned):
            raise ValueError(
                f"contaminated fingerprint: leaks home-domain term(s) {banned} — Step 2 would "
                "retrieve a memorized result, not a structural form. Strip the vocabulary.")
        # Step 2 — surface cross-field structural matches (engine).
        isos = self.query(fp, n_candidates) or []
        # Step 3 — compile each match to a gate and holdout-verify (domain).
        baseline = self.domain.oracle(None, holdout)
        verdicts: list[IsomorphismVerdict] = []
        for iso in isos:
            try:
                test = self.domain.compile_to_test(iso, context)
            except Exception as e:
                verdicts.append(IsomorphismVerdict(iso, baseline, baseline, False,
                                                   {"unmappable": repr(e)[:160]}))
                continue
            after = self.domain.oracle(test, holdout)
            verdicts.append(IsomorphismVerdict(iso, baseline, after, after > baseline,
                                               {"compiled": True}))
        verdicts.sort(key=lambda v: -v.delta)
        return verdicts

    def best(self, failure_state: object, holdout: object, **kw) -> "IsomorphismVerdict | None":
        """The single best holdout-verified mutation, or None if nothing improved the oracle."""
        v = [x for x in self.run(failure_state, holdout, **kw) if x.improves]
        return v[0] if v else None


# ─────────────────────────────────────────────────────────────────────────────
# Default Step-2 query — reuses the validated LLM runtime + contamination discipline
# ─────────────────────────────────────────────────────────────────────────────

def _build_query_prompt(fp: ConstraintFingerprint, n: int) -> str:
    # forbidden_domain is the distance-from-home knob that UNIFIES the autoresearch family:
    #   None  → ANALOGY direction (fit/analogy.py): match from ANY field, including adjacent.
    #   set   → DEANCHOR direction (fit/cold_llm_erdos_seed.py): forbid the home field AND directly
    #           adjacent fields to force a far, non-canonical match (the orthogonal jump).
    away = (f"\nDo NOT answer from {fp.forbidden_domain} OR any field directly adjacent to it — that "
            "is the home framing that produced this ceiling, and the point is to surface what the "
            "home discipline would not. Reach into structurally-distant fields." if fp.forbidden_domain else "")
    return (
        "You are given ONLY an abstract structural constraint — no domain, no variable names, no "
        "context about where it came from. This is deliberate: name the STRUCTURE, not a memorized "
        "answer for any particular application.\n\n"
        f"CONSTRAINT CLASS: {fp.constraint_class}\n"
        f"ABSTRACT FORM: {fp.abstract_form}\n"
        f"STRUCTURAL INVARIANTS: {fp.invariants}\n"
        f"{away}\n\n"
        f"Name up to {n} established THEOREMS, ALGORITHMS, or PHYSICAL LAWS from any field "
        "(group theory, complexity, cryptography, physics, information theory, topology, …) that "
        "SOLVE or OPTIMIZE exactly these constraints. For each, return strict JSON with keys: "
        "`theorem`, `field`, `mechanism` (how it resolves the abstract constraint), `mapping_hint` "
        "(how its components would map onto a generic system with these invariants). Return a JSON "
        "list. Retrieve the STRUCTURE that fits; do not invent, and do not return a result claimed "
        "to already solve the caller's specific problem.")


def _dispatch_text(prompt: str, *, provider: str = "gemini", model: "str | None" = None,
                   timeout_s: int = 180) -> str:
    """Provider-flexible text dispatch for the structural-only query. PROVIDER POLICY (repo rule):
    gemini / deepseek go via API (`LLMRuntime`, allowed); codex (OpenAI) / claude (Anthropic) go ONLY
    via the SUBSCRIPTION CLI (`subscription_agent_runtime`), never the metered API. The isomorphism loop
    legitimately needs this provider flexibility for its structural query; other consumers use the
    runtime they need directly (warm-agent architecture for agentic work, `LLMRuntime` for API
    completions) rather than reaching through this module. Returns "" (never raises) on any failure."""
    provider = (provider or "gemini").lower()
    if provider in ("codex", "claude"):
        from pathlib import Path as _P
        repo = _P(__file__).resolve().parents[3]
        try:
            from src.ztare.common.subscription_agent_runtime import run_subscription_agent_with_recovery
        except Exception:
            try:
                from ztare.common.subscription_agent_runtime import run_subscription_agent_with_recovery
            except Exception:
                return ""
        try:
            run = run_subscription_agent_with_recovery(
                runtime=provider, prompt=prompt, agent_id="constraint_isomorphism::query",
                repo=repo, session_state=None, timeout_seconds=timeout_s,
                claude_disallowed_tools=["WebSearch", "WebFetch"])
            return (getattr(getattr(run, "result", None), "stdout", "") or "") if run else ""
        except Exception:
            return ""
    # API providers (gemini/deepseek allowed). Fallback stays within the same family → never a
    # metered OpenAI/Anthropic call.
    try:
        from src.ztare.common.llm_runtime import LLMRuntime
    except Exception:
        try:
            from ztare.common.llm_runtime import LLMRuntime
        except Exception:
            return ""
    mid = model or ("deepseek-chat" if provider == "deepseek" else "gemini-3.1-pro-preview")
    fb = () if provider == "deepseek" else ("gemini-3.1-flash-lite-preview",)
    try:
        resp = LLMRuntime().call_text(prompt, model_id=mid, fallback_model_ids=fb,
                                      max_tokens=2000, request_label="constraint_isomorphism_query",
                                      timeout_seconds=timeout_s)
        return getattr(resp, "text", "") or ""
    except Exception:
        return ""


def default_llm_query(fp: ConstraintFingerprint, n: int = 5, *, provider: str = "gemini",
                      model: "str | None" = None) -> "list[SurfacedIsomorphism]":
    """Production Step-2: query a frontier LLM with the structural-only prompt and parse the JSON.
    Provider-flexible (gemini API default `gemini-3.1-pro-preview`; codex/claude via subscription CLI;
    deepseek API) — see `_dispatch_text`. Returns [] (never raises) on any runtime/parse failure."""
    import json
    import re as _re
    prompt = _build_query_prompt(fp, n)
    text = _dispatch_text(prompt, provider=provider, model=model)
    if not text:
        return []
    m = _re.search(r"\[.*\]", text, _re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except Exception:
        return []
    out: list[SurfacedIsomorphism] = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        out.append(SurfacedIsomorphism(
            theorem=str(it.get("theorem", "")).strip(),
            field=str(it.get("field", "")).strip(),
            mechanism=str(it.get("mechanism", "")).strip(),
            mapping_hint=str(it.get("mapping_hint", "")).strip(),
            raw=json.dumps(it)[:400]))
    return [o for o in out if o.theorem]


# ─────────────────────────────────────────────────────────────────────────────
# Self-test — a MOCK domain + MOCK query prove the orchestration with no LLM / no Lean.
# It encodes the canonical worked example: a "context dilution as length grows" ceiling, whose
# abstract form is bounded-width sequential composition; the mock query surfaces Barrington-style
# bounded-width composition; compiling it to a "prune context to bound width" gate IMPROVES the
# oracle — i.e. the loop rediscovers the MDL-library lever from the failure. (A useless match does
# NOT improve the oracle and is dropped.)
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    class _MockDomain:
        """A toy proof-search-like domain: 'width' (context size) grows with build-up length and
        dilutes closure. A gate that BOUNDS width improves the holdout closure rate; an irrelevant
        gate does not."""
        def abstract_failure(self, fs):
            return ConstraintFingerprint(
                constraint_class="bounded-resource sequential composition",
                abstract_form="capability degrades as sequence length L grows while working width W "
                              "grows unbounded; need expressive composition at bounded W",
                invariants={"width_grows_with_length": True, "depth": "O(L)", "target_width": "O(1)"},
                forbidden_domain="theorem-proving")

        def compile_to_test(self, iso, context):
            # The gate is a POLICY this domain's oracle applies per item (opaque to the engine).
            mech = (iso.mechanism + " " + iso.theorem + " " + iso.mapping_hint).lower()
            if "width" in mech or "bound" in mech or "prune" in mech:
                # the useful match → a policy that PRUNES width to the target (the MDL-library action)
                return lambda item: dict(item, width=min(item["width"], item["target_width"]))
            if "unmappable" in mech:
                raise ValueError("cannot map this match onto the system")
            return lambda item: item  # irrelevant match → identity policy (changes nothing)

        def oracle(self, gate, holdout):
            # closure rate over holdout; only a gate that actually bounds width rescues long items.
            closed = 0
            for item in holdout:
                eff = item if gate is None else gate(item)
                closed += 1 if eff["width"] <= item["needs_width"] else 0
            return closed / max(1, len(holdout))

        def banned_terms(self):
            return ["lean", "tactic", "mathlib", "proof"]

    # holdout: short items close either way; long items only close once width is bounded.
    holdout = [{"width": 1, "needs_width": 1, "target_width": 1},
               {"width": 5, "needs_width": 1, "target_width": 1},
               {"width": 9, "needs_width": 1, "target_width": 1}]

    def mock_query(fp, n):
        return [
            SurfacedIsomorphism("Barrington's theorem", "complexity theory",
                                "bounded-width branching programs compute richly via composition; "
                                "bound the working width and compose in depth",
                                "width←provisioned context; prune to bound it"),
            SurfacedIsomorphism("Noether's theorem", "physics",
                                "a continuous symmetry yields a conserved quantity",
                                "maps to invariants under a group action"),
            SurfacedIsomorphism("Unmappable thing", "x", "unmappable", "x"),
        ]

    loop = IsomorphismLoop(_MockDomain(), query=mock_query)
    verdicts = loop.run(failure_state=None, holdout=holdout, n_candidates=3)
    ok("returns_a_verdict_per_candidate", len(verdicts) == 3)
    best = loop.best(failure_state=None, holdout=holdout, n_candidates=3)
    ok("best_is_the_width_bounding_match", best is not None and "Barrington" in best.iso.theorem)
    ok("best_improves_oracle", best is not None and best.improves and best.delta > 0)
    irrelevant = [v for v in verdicts if "Noether" in v.iso.theorem][0]
    ok("irrelevant_match_does_not_improve", not irrelevant.improves and irrelevant.delta == 0)
    unmappable = [v for v in verdicts if "Unmappable" in v.iso.theorem][0]
    ok("unmappable_match_flagged", "unmappable" in unmappable.detail and not unmappable.improves)

    # contamination guard fires on a leaked home-domain term
    class _LeakyDomain(_MockDomain):
        def abstract_failure(self, fs):
            fp = super().abstract_failure(fs)
            fp.abstract_form += " (this is a Lean tactic proof problem)"  # leaks 'lean'/'tactic'/'proof'
            return fp
    leaked = False
    try:
        IsomorphismLoop(_LeakyDomain(), query=mock_query).run(None, holdout)
    except ValueError:
        leaked = True
    ok("contamination_guard_fires_on_leak", leaked)

    # a domain with NO matches surfaced → best() is None (honest: nothing rediscovered)
    none_best = IsomorphismLoop(_MockDomain(), query=lambda fp, n: []).best(None, holdout)
    ok("no_matches_returns_none", none_best is None)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
