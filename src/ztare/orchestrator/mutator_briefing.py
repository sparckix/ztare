"""Mutator Briefing — structured pre-iteration working-memory packet.

The mutator's "researcher's desk." Each apparatus iteration produces
deterministic workspace artifacts (fit results, gate verdicts, evidence
gaps, derived constraints, cage engagement matrices). Without
structured surfacing, those artifacts stay in stdout/JSON files and
the mutator's next iter operates with partial memory.

This module defines a registry of `BriefingProvider`s. Each provider:

  * declares a stable `name`
  * decides when it `applies(context)`
  * reads workspace artifacts (idempotent, no side effects)
  * emits a markdown `fragment(context) -> str`

`MutatorBriefing.render(context)` walks the registered providers,
asks each whether it applies, collects fragments from those that do,
and concatenates them into a single ordered briefing block. The block
is also persisted to `workspace/mutator_briefing_iter_NNN.md` so
operators can audit *exactly what the mutator saw* on a given iter
without grepping through prompt logs.

Design invariants:

  1. Providers are STATELESS. No instance fields beyond config.
  2. Providers read ONLY deterministic workspace artifacts. No priors
     that could leak between iters.
  3. Provider fragments are MARKDOWN with stable headers. The mutator
     can pattern-match against headers; tests can assert presence.
  4. Adding a channel is `briefing.register(MyProvider)` — never an
     edit to autoresearch_loop's prompt-assembly code.
  5. Briefings are PERSISTED per iter to enable post-hoc operator
     audit ("what did the mutator know on iter 7?").

This is the structural answer to the frontier-researcher-memory
question: the mutator gets memory OF WHAT WAS OBSERVED, not memory of
intuitions. Workspace artifacts are the substrate of memory; providers
are the lenses; the briefing is the desk.
"""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ── Briefing context ────────────────────────────────────────────────────


@dataclass
class BriefingContext:
    """Read-only context handed to each provider. Providers must NOT
    mutate it. Providers may load additional workspace artifacts via
    the project_dir field."""
    project_dir: Path
    iter_index: int
    rubric: dict
    workspace_dir: Optional[Path] = None
    # Optional substrate classifier output (if pre-launch classifier ran)
    substrate_classifier: Optional[dict] = None
    # Optional charter parse (asymptotes, K_law max, etc.)
    charter_meta: Optional[dict] = None
    # Optional runtime mutator model id — used by GP-169 cold-LLM
    # re-query to default to the mutator's model when the rubric
    # leaves cold_llm_seed_model_id blank or set to the @mutator
    # sentinel. autoresearch_loop fills this from MUTATOR_MODEL_ID.
    mutator_model_id: Optional[str] = None
    # Stagnation count (consecutive iters without improvement). Used by
    # the tiered briefing budget (paper 7 §11.15) — providers in tier T3+
    # only render when stagnation_count exceeds their gate threshold.
    # autoresearch_loop sets this from the run's stagnation tracker;
    # callers that don't care about tiering can leave it at 0.
    stagnation_count: int = 0

    def __post_init__(self) -> None:
        if self.workspace_dir is None:
            self.workspace_dir = self.project_dir / "workspace"


# ── Base provider ───────────────────────────────────────────────────────


class BriefingProvider(ABC):
    """Base class for all mutator-briefing providers."""

    #: stable identifier; used for ordering, audit trails, and tests
    name: str = "abstract"

    #: optional priority — providers render in ascending priority order;
    #: ties broken by name. Convention: 100 = critical, 500 = standard,
    #: 900 = nice-to-have.
    priority: int = 500

    #: tier — paper 7 §11.15 fix for the briefing-density bottleneck
    #: identified in run 1777403089 audit (28k chars input → mutator
    #: produces apparatus-feature nests; cold-shot at 4.5k chars same
    #: model produces clean Lagrangians). Tier defines when the provider
    #: renders:
    #:   T0 = always (apparatus contract — non-negotiable)
    #:   T1 = always (load-bearing structural directive)
    #:   T2 = always (lightweight per-iter feedback)
    #:   T3 = stagnation_count > 2 (regime-specific failure analysis)
    #:   T4 = stagnation_count > 4 (big-hammer reframings)
    #:   T5 = hibernate (kept in codebase for past-failure preservation;
    #:        only renders when explicit rubric flag toggles them on)
    #: Default T2 means "always render" so existing providers keep
    #: rendering until a maintainer reclassifies them.
    tier: int = 2

    #: explicit per-class rubric override key — when rubric has
    #: `briefing_force_show_<name>: true`, the provider renders even
    #: if its tier is gated out. For operator debugging.
    @property
    def force_show_key(self) -> str:
        return f"briefing_force_show_{self.name}"

    @abstractmethod
    def applies(self, ctx: BriefingContext) -> bool:
        """Return True if this provider has a fragment for this iter."""

    @abstractmethod
    def fragment(self, ctx: BriefingContext) -> str:
        """Return the markdown fragment to inject. Stable header, then
        body. Include a trailing newline. Empty string returned by
        a provider that thought it applied but had nothing to say."""

    def passes_tier_gate(self, ctx: BriefingContext) -> bool:
        """Tier-based stagnation gate. Returns True if the provider's
        tier is satisfied by ctx.stagnation_count, OR if the rubric
        forces it shown. Called BEFORE applies() so a provider gated
        out by tier never even gets to evaluate its own applies()."""
        if bool(ctx.rubric.get(self.force_show_key, False)):
            return True
        if self.tier <= 2:
            return True
        if self.tier == 3:
            return ctx.stagnation_count > 2
        if self.tier == 4:
            return ctx.stagnation_count > 4
        # T5 hibernate: only renders when explicitly forced via rubric
        return False


# ── Registry + entry point ──────────────────────────────────────────────


@dataclass
class MutatorBriefing:
    """Provider registry + render entry point."""
    providers: list[BriefingProvider] = field(default_factory=list)

    def register(self, provider: BriefingProvider) -> None:
        self.providers.append(provider)

    def render(self, ctx: BriefingContext) -> str:
        """Walk registered providers in priority order, collect
        fragments from those that apply, return concatenated markdown.

        Tiered fade-in (paper 7 §11.15): providers with tier ≥ 3 only
        render when ctx.stagnation_count exceeds their gate threshold.
        T5 providers hibernate unless explicitly forced via rubric.
        Plus a soft budget cap (`briefing_budget_chars`, default 12000)
        beyond which lower-priority T3+ providers are dropped — apparatus
        contract (T0/T1) and load-bearing always-on (T2) providers are
        never dropped by the budget.

        Persists to `workspace/mutator_briefing_iter_NNN.md` for
        operator audit. The audit log records which providers fired
        and which were tier-gated or budget-trimmed.
        """
        ordered = sorted(self.providers, key=lambda p: (p.priority, p.name))
        # Soft budget cap — paper 7 §11.15 finding: 28k chars of briefing
        # collapsed gpt-5.5's structural reasoning. 12k is a midpoint
        # between the cold-shot's effective 4.5k and the legacy 28k.
        # Operator override via rubric.briefing_budget_chars.
        budget = int(ctx.rubric.get("briefing_budget_chars", 12000))
        # Operator escape hatch — disable tiering entirely (legacy mode)
        # by setting `briefing_tiered_disable: true` in the rubric.
        tiering_disabled = bool(ctx.rubric.get("briefing_tiered_disable", False))
        fragments: list[tuple[str, str]] = []
        tier_gated: list[str] = []
        budget_trimmed: list[str] = []
        provider_timings_ms: dict[str, float] = {}
        render_started = time.perf_counter()
        running_chars = 0
        for p in ordered:
            provider_started = time.perf_counter()
            try:
                if not tiering_disabled and not p.passes_tier_gate(ctx):
                    tier_gated.append(f"{p.name}(T{p.tier})")
                    continue
                if p.applies(ctx):
                    frag = p.fragment(ctx)
                    if frag and frag.strip():
                        # Budget enforcement: T0/T1/T2 are never dropped.
                        # T3+ providers that would push past budget are
                        # trimmed (their content is logged to the audit
                        # but not injected into the prompt).
                        if (
                            not tiering_disabled
                            and p.tier >= 3
                            and running_chars + len(frag) > budget
                        ):
                            budget_trimmed.append(f"{p.name}(T{p.tier},{len(frag)}c)")
                            continue
                        fragments.append((p.name, frag))
                        running_chars += len(frag)
            except Exception as exc:
                # Provider exceptions are NEVER fatal to the mutator
                # prompt assembly. Best effort: skip the broken provider
                # and continue. The exception goes to a sidecar log so
                # the operator notices.
                fragments.append((
                    p.name,
                    f"\n    <!-- briefing provider {p.name!r} raised {type(exc).__name__}: {exc!r} — skipped -->\n",
                ))
            finally:
                provider_timings_ms[p.name] = round((time.perf_counter() - provider_started) * 1000.0, 3)
        body = "\n".join(f for _, f in fragments)
        # Stash gate/trim diagnostics on self so the audit header can
        # show them. Best effort.
        self._last_render_diagnostics = {
            "tier_gated": tier_gated,
            "budget_trimmed": budget_trimmed,
            "budget_chars": budget,
            "running_chars": running_chars,
            "stagnation_count": ctx.stagnation_count,
            "tiering_disabled": tiering_disabled,
            "render_ms": round((time.perf_counter() - render_started) * 1000.0, 3),
            "provider_timings_ms": provider_timings_ms,
        }

        # Persist for operator audit. Best effort.
        try:
            ws = ctx.workspace_dir
            if ws is not None:
                ws.mkdir(parents=True, exist_ok=True)
                audit_path = ws / f"mutator_briefing_iter_{ctx.iter_index:03d}.md"
                diag = getattr(self, "_last_render_diagnostics", {}) or {}
                header = (
                    f"# Mutator briefing — iter {ctx.iter_index}\n\n"
                    f"Active providers: {[n for n, _ in fragments]}\n"
                    f"Briefing chars: {diag.get('running_chars', '?')} "
                    f"(budget {diag.get('budget_chars', '?')}; "
                    f"stagnation_count={diag.get('stagnation_count', '?')})\n"
                    f"Tier-gated (silent this iter): {diag.get('tier_gated', [])}\n"
                    f"Budget-trimmed (load-bearing but oversized): "
                    f"{diag.get('budget_trimmed', [])}\n"
                    f"Tiering disabled: {diag.get('tiering_disabled', False)}\n\n"
                    f"Render ms: {diag.get('render_ms', '?')}\n"
                    f"Provider timings ms: {diag.get('provider_timings_ms', {})}\n\n"
                    f"---\n"
                )
                audit_path.write_text(header + body, encoding="utf-8")
        except Exception:
            pass  # audit failure is non-fatal

        return body


# ── Convenience: default registry seeded with shipped providers ─────────


def default_briefing() -> MutatorBriefing:
    """Return a MutatorBriefing with the standard provider set wired in.

    Imported from briefing_providers.* so each provider lives in its
    own file. Adding a new provider to the default set is a 1-line
    edit here plus a new file under briefing_providers/.
    """
    from src.ztare.orchestrator.briefing_providers.fit_telemetry import (
        FitTelemetryProvider,
    )
    from src.ztare.orchestrator.briefing_providers.gate_gap import (
        GateGapProvider,
    )
    from src.ztare.orchestrator.briefing_providers.iter_trajectory import (
        IterTrajectoryProvider,
    )
    from src.ztare.orchestrator.briefing_providers.row_outliers import (
        RowOutlierProvider,
    )
    from src.ztare.orchestrator.briefing_providers.asymptote_deviation import (
        AsymptoteDeviationProvider,
    )
    from src.ztare.orchestrator.briefing_providers.analogy_candidates import (
        AnalogyCandidatesProvider,
    )
    from src.ztare.orchestrator.briefing_providers.framer_recommendation import (
        FramerRecommendationProvider,
    )
    from src.ztare.orchestrator.briefing_providers.per_class_breakdown import (
        PerClassBreakdownProvider,
    )
    from src.ztare.orchestrator.briefing_providers.noise_profile_brief import (
        NoiseProfileBriefingProvider,
    )
    from src.ztare.orchestrator.briefing_providers.contamination_defense import (
        ContaminationDefenseBriefingProvider,
    )
    from src.ztare.orchestrator.briefing_providers.data_diagnostics import (
        DataDiagnosticsBriefingProvider,
    )
    from src.ztare.orchestrator.briefing_providers.cold_llm_seed import (
        ColdLlmSeedBriefingProvider,
    )
    from src.ztare.orchestrator.briefing_providers.cold_shot_seed import (
        ColdShotSeedBriefingProvider,
    )
    from src.ztare.orchestrator.briefing_providers.qualitative_evidence_seed import (
        QualitativeEvidenceSeedProvider,
    )
    from src.ztare.orchestrator.briefing_providers.forced_reframe import (
        ForcedReframeBriefingProvider,
    )
    from src.ztare.orchestrator.briefing_providers.verified_axioms import (
        VerifiedAxiomsProvider,
    )
    from src.ztare.orchestrator.briefing_providers.path_b_promotion_floor import (
        PathBPromotionFloorProvider,
    )
    from src.ztare.orchestrator.briefing_providers.contract_rules import (
        ContractRulesProvider,
    )
    from src.ztare.orchestrator.briefing_providers.r1_pattern_warning import (
        R1PatternWarningProvider,
    )
    from src.ztare.orchestrator.briefing_providers.lagrangian_worked_example import (
        LagrangianWorkedExampleProvider,
    )

    b = MutatorBriefing()

    # ── Tier classification (paper 7 §11.15 briefing-density fix) ──
    # T0/T1 = always (apparatus contract + load-bearing structural directive)
    # T2    = always (lightweight per-iter feedback)
    # T3    = stagnation_count > 2
    # T4    = stagnation_count > 4
    # T5    = hibernate (only via rubric.briefing_force_show_<name>)
    # Tiers set on instances below; modify here, not in provider files.

    # Contract rules (2026-04-27): teaches apparatus contracts upfront so
    # the mutator's first attempt complies. Renders at priority 20 — first.
    # Solves the "every iter wastes 1-3 R1 strikes re-learning the same
    # rules" pattern seen across gp163d (denylist hits, numpy imports) and
    # gp168 (missing I_model on qualitative substrate). Per-iter cost: ~2k
    # briefing tokens; ROI: prevents ~$0.30-1.20/iter R1-thrash bills.
    _p = R1PatternWarningProvider(); _p.tier = 0
    b.register(_p)
    _p = ContractRulesProvider(); _p.tier = 0
    b.register(_p)
    _p = FitTelemetryProvider(); _p.tier = 2
    b.register(_p)
    # Path-B promotion-floor explainer (2026-04-27): when a substrate has
    # tier_3_universal_law_target.active=true AND a prior iter was capped
    # at 50 by R20-R24 or PPN gates, this provider renders an unambiguous
    # cap-mechanism explanation at the TOP of the briefing (priority 30 —
    # before VerifiedAxioms@50, ForcedReframe@130, ColdLLM@150). Solves the
    # gp163d gp-5.5 attractor problem where briefing density obscured the
    # path-b promotion criteria; this provider surfaces them load-bearing.
    _p = PathBPromotionFloorProvider(); _p.tier = 2
    b.register(_p)
    # GP-180 Lagrangian worked-example (2026-04-28): when the rubric has
    # `enable_lagrangian_derivation: true` (or `rubric_modes` contains
    # `"invariant_search"`), render the action-principle contract + three
    # worked Lagrangians at priority 9999 — the LAST block in the
    # assembled briefing. Recency-bias rationale: the mutator's next
    # action must obey the GP-180 contract, and long-context LLMs attend
    # most strongly to the tail of the prompt (Liu et al. 2023,
    # "Lost in the Middle"). Stops the mutator from declaring bare-Newton
    # Lagrangians whose static E-L has no real solution.
    # Keep the action-principle worked example available, but do not let a
    # multi-kilobyte example crowd out the cold-shot seed on iter 1. It now
    # appears after stagnation or via briefing_force_show_lagrangian_worked_example.
    _p = LagrangianWorkedExampleProvider(); _p.tier = 3
    b.register(_p)
    # Axiom successor-lock briefing (2026-04-27) — Sacred-DNA — surfaces
    # verified_axioms.json entries with active successor_lock as
    # permanent constraints. Priority 50 — renders BEFORE forced_reframe
    # (130) and cold-LLM (150) so the mutator sees the locked form
    # before any framings or reframes.
    _p = VerifiedAxiomsProvider(); _p.tier = 2
    b.register(_p)
    # GP-168 Forced REFRAME (task #141): when stagnation triggers fire,
    # injects MANDATORY-DISJOINT-ARCHITECTURE block ahead of the cold-LLM
    # seed. Priority 130 — renders before cold-LLM seed (150) so the
    # mutator sees the forcing-function context first.
    _p = ForcedReframeBriefingProvider(); _p.tier = 4
    b.register(_p)
    # GP-184 cold-shot structural seed (2026-04-28): renders the
    # Lagrangian + PARAMETRIC_FORM proposed by the pre-iter-1 cold-shot
    # call as a HARD architectural directive. Priority 145 — renders
    # BEFORE ColdLlmSeed (150) because the cold-shot is a substrate-aware
    # structural prior (specific Lagrangian) while the cold-LLM seed is
    # a domain-de-anchor primitive (cross-domain shapes). The mutator
    # should anchor on the structural prior first. Live-finding routing
    # fix from run 1777403089 audit (2026-04-28) where the cold-shot
    # fired but the seed lived in a black hole.
    _p = ColdShotSeedBriefingProvider(); _p.tier = 1
    b.register(_p)
    # GP-169 Phase 1: Cold-LLM Erdős seed surfaces three cross-domain
    # candidate forms (computed pre-iter-1 by orchestrator/pre_iter1_dispatch)
    # as MANDATORY-CONSIDER alternatives in iter 1+. Priority 150 — render
    # early so the mutator sees the seed before downstream telemetry.
    _p = ColdLlmSeedBriefingProvider(); _p.tier = 4
    b.register(_p)
    # GP-193 evidence-grounded cold shot (priority 160 — just after Erdős
    # cross-domain seed at 150). Renders 3 evidence-brief-aware thesis families
    # as T2 mandatory-consider alternatives. Activates only for qualitative
    # substrates with enable_qualitative_evidence_cold_shot=true.
    _p = QualitativeEvidenceSeedProvider(); _p.tier = 2
    b.register(_p)
    # GP-167 unified data-diagnostics view (replaces the standalone
    # NoiseProfileBriefingProvider + SubstrateCritiqueBriefingProvider).
    # Reads noise_profile.json + substrate_critique.json +
    # substrate_critique_suggestions.json from workspace and renders
    # one cohesive section with three sub-views (Noise profile,
    # Substrate structure, Operator-action-needed). Same backend modules.
    _p = DataDiagnosticsBriefingProvider(); _p.tier = 3
    b.register(_p)
    _p = ContaminationDefenseBriefingProvider(); _p.tier = 3  # GP-166 Fix B: .denylist hit surfacing
    b.register(_p)
    _p = GateGapProvider(); _p.tier = 3
    b.register(_p)
    _p = PerClassBreakdownProvider(); _p.tier = 2  # load-bearing per-iter signal
    b.register(_p)
    _p = FramerRecommendationProvider(); _p.tier = 3
    b.register(_p)
    _p = IterTrajectoryProvider(); _p.tier = 5  # hibernate — opt-in only
    b.register(_p)
    _p = AnalogyCandidatesProvider(); _p.tier = 4
    b.register(_p)
    _p = RowOutlierProvider(); _p.tier = 5  # hibernate — opt-in only
    b.register(_p)
    _p = AsymptoteDeviationProvider(); _p.tier = 2
    b.register(_p)
    # Embedding-history retrieval (2026-05-06) — sister channel to
    # iter_trajectory. While iter_trajectory shows the LAST K iters by
    # ordinal, this provider surfaces the K iters whose telemetry-text
    # embedding is most similar to the current state. Useful when the
    # mutator is in a region the substrate has visited before.
    # Tier 3 (stagnation-only) so it doesn't burden the every-iter
    # briefing budget; iter_trajectory remains the always-on channel.
    try:
        from src.ztare.orchestrator.briefing_providers.embedding_history import (
            EmbeddingHistoryProvider,
        )
        _p = EmbeddingHistoryProvider(); _p.tier = 3
        b.register(_p)
    except ImportError:
        # sentence-transformers not available; skip this provider
        pass
    # GP-241 V4 second-consumer (out-of-loop→in-loop): the obligation
    # contract. T0 (always), substrate-specific v4_activation.yaml,
    # observe-mode (renders+persists; enforcing close-gate pending cold
    # review). Degrades safe (fragment→"" on any error).
    try:
        from src.ztare.orchestrator.briefing_providers.obligation_contract import (
            ObligationContractProvider,
        )
        _p = ObligationContractProvider()  # tier=0 set on the class
        b.register(_p)
    except Exception:
        pass
    return b
