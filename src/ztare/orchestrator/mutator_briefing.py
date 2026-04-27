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

    @abstractmethod
    def applies(self, ctx: BriefingContext) -> bool:
        """Return True if this provider has a fragment for this iter."""

    @abstractmethod
    def fragment(self, ctx: BriefingContext) -> str:
        """Return the markdown fragment to inject. Stable header, then
        body. Include a trailing newline. Empty string returned by
        a provider that thought it applied but had nothing to say."""


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

        Persists to `workspace/mutator_briefing_iter_NNN.md` for
        operator audit.
        """
        ordered = sorted(self.providers, key=lambda p: (p.priority, p.name))
        fragments: list[tuple[str, str]] = []
        for p in ordered:
            try:
                if p.applies(ctx):
                    frag = p.fragment(ctx)
                    if frag and frag.strip():
                        fragments.append((p.name, frag))
            except Exception as exc:
                # Provider exceptions are NEVER fatal to the mutator
                # prompt assembly. Best effort: skip the broken provider
                # and continue. The exception goes to a sidecar log so
                # the operator notices.
                fragments.append((
                    p.name,
                    f"\n    <!-- briefing provider {p.name!r} raised {type(exc).__name__}: {exc!r} — skipped -->\n",
                ))
        body = "\n".join(f for _, f in fragments)

        # Persist for operator audit. Best effort.
        try:
            ws = ctx.workspace_dir
            if ws is not None:
                ws.mkdir(parents=True, exist_ok=True)
                audit_path = ws / f"mutator_briefing_iter_{ctx.iter_index:03d}.md"
                header = (
                    f"# Mutator briefing — iter {ctx.iter_index}\n\n"
                    f"Active providers: {[n for n, _ in fragments]}\n\n"
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
    from src.ztare.orchestrator.briefing_providers.forced_reframe import (
        ForcedReframeBriefingProvider,
    )
    from src.ztare.orchestrator.briefing_providers.verified_axioms import (
        VerifiedAxiomsProvider,
    )

    b = MutatorBriefing()
    b.register(FitTelemetryProvider())
    # WAR-T5 (2026-04-27): Sacred-DNA / Successor-Lock — surfaces
    # verified_axioms.json entries with active successor_lock as
    # permanent constraints. Priority 50 — renders BEFORE forced_reframe
    # (130) and cold-LLM (150) so the mutator sees the locked form
    # before any framings or reframes.
    b.register(VerifiedAxiomsProvider())
    # GP-168 Forced REFRAME (task #141): when stagnation triggers fire,
    # injects MANDATORY-DISJOINT-ARCHITECTURE block ahead of the cold-LLM
    # seed. Priority 130 — renders before cold-LLM seed (150) so the
    # mutator sees the forcing-function context first.
    b.register(ForcedReframeBriefingProvider())
    # GP-169 Phase 1: Cold-LLM Erdős seed surfaces three cross-domain
    # candidate forms (computed pre-iter-1 by orchestrator/pre_iter1_dispatch)
    # as MANDATORY-CONSIDER alternatives in iter 1+. Priority 150 — render
    # early so the mutator sees the seed before downstream telemetry.
    b.register(ColdLlmSeedBriefingProvider())
    # GP-167 unified data-diagnostics view (replaces the standalone
    # NoiseProfileBriefingProvider + SubstrateCritiqueBriefingProvider).
    # Reads noise_profile.json + substrate_critique.json +
    # substrate_critique_suggestions.json from workspace and renders
    # one cohesive section with three sub-views (Noise profile,
    # Substrate structure, Operator-action-needed). Same backend modules.
    b.register(DataDiagnosticsBriefingProvider())
    b.register(ContaminationDefenseBriefingProvider())  # GP-166 Fix B: .denylist hit surfacing
    b.register(GateGapProvider())
    b.register(PerClassBreakdownProvider())  # GP-166: per-class MRE + U-vs-S diagnosis
    b.register(FramerRecommendationProvider())
    b.register(IterTrajectoryProvider())
    b.register(AnalogyCandidatesProvider())
    b.register(RowOutlierProvider())
    b.register(AsymptoteDeviationProvider())
    return b
