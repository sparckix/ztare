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

from ztare.orchestrator.briefing_attention import render_attention_agenda
from ztare.orchestrator.briefing_projection import build_projection_receipt


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
    # Optional admitted project-intake metadata from autoresearch_loop
    # `--intake`. Providers may use this to consume the exact launch packet
    # rather than guessing a conventional project-local filename.
    project_packet: Optional[dict[str, Any]] = None
    # Rendering mode — "file" (workbench/agentic path, briefing staged as
    # CONTEXT.md / ATTENTION.md with no size constraint) vs "chat" (legacy
    # sealed-completion path where the briefing is injected inline into a
    # chat prompt). Budget trimming only applies in "chat" mode.
    # ponytail: default "file" so existing tests that omit the field keep
    # working (they don't exercise the chat budget path).
    rendering_mode: str = "file"

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
    #:   T1 = always (central structural directive)
    #:   T2 = always (lightweight per-iter feedback)
    #:   T3 = stagnation_count > 2 (regime-specific failure analysis)
    #:   T4 = stagnation_count > 4 (big-hammer reframings)
    #:   T5 = hibernate (kept in codebase for past-failure preservation;
    #:        only renders when explicit rubric flag toggles them on)
    #: Default T2 means "always render" so existing providers keep
    #: rendering until a maintainer reclassifies them.
    tier: int = 2

    #: Optional hard cap for provider markdown injected into the worker prompt.
    #: Providers that surface large persisted artifacts should set this and
    #: keep full detail in structured_records / workspace files. This is the
    #: prompt-side analogue of CEGAR/abstract interpretation: pass a compressed
    #: witness carrier to the proposer, keep the concrete artifact for the gate.
    max_fragment_chars: int | None = None

    #: Control-plane providers are NEVER trimmed by the chat-mode budget gate.
    #: A channel that trims the jump-forcer (forced_reframe) or the failure
    #: digest (tried_failed_digest) to fit advice cards has inverted priorities.
    #: Set True on any provider whose output governs the search trajectory
    #: rather than informing it. Tier-gate and per-provider max_fragment_chars
    #: still apply; only the cross-provider budget-spill trim is bypassed.
    control_plane: bool = False

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

    def structured_records(self, ctx: BriefingContext) -> list[dict[str, Any]]:
        """Optional machine-readable records behind a rendered fragment.

        Providers should keep this deterministic and read-only, just like
        ``fragment``. The renderer persists these records next to the briefing
        so downstream reports can consume the same evidence the mutator saw.
        """
        return []

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


_ELISION_MARKER = "\n\n[provider fragment elided to fit briefing budget; full artifact remains in workspace sidecars]\n\n"
_ATOMIC_STRUCTURED_MARKERS = (
    "LEAF_WORKBENCH_ACTION_REQUEST",
    "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
    "STRATEGY_CARD_DISCHARGE",
)


def _atomic_structured_line(line: str) -> bool:
    return any(marker in line for marker in _ATOMIC_STRUCTURED_MARKERS)


def _bracket_delta(line: str) -> int:
    depth = 0
    in_string = False
    quote = ""
    escape = False
    for ch in line:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_string = False
            continue
        if ch in ("'", '"'):
            in_string = True
            quote = ch
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
    return depth


def _safe_elide_fragment(text: str, cap: int) -> str:
    """Elide on syntactic boundaries, never inside code or bracket blocks."""
    marker = _ELISION_MARKER
    if cap <= len(marker) + 40:
        return marker.strip()[:cap]
    budget = cap - len(marker)
    source_lines = [raw_line.rstrip() for raw_line in (text or "").splitlines()]
    out: list[str] = []
    used = 0
    in_fence = False
    bracket_depth = 0
    structured_omitted = False
    for line in source_lines:
        stripped = line.strip()
        if _atomic_structured_line(line):
            delta = _bracket_delta(line)
            if delta == 0 and used + len(line) + 1 <= budget:
                out.append(line)
                used += len(line) + 1
                continue
            bracket_depth = max(0, bracket_depth + delta)
            if not structured_omitted:
                replacement = "[structured code/json block omitted; full artifact remains in workspace sidecars]"
                if used + len(replacement) + 1 <= budget:
                    out.append(replacement)
                    used += len(replacement) + 1
                structured_omitted = True
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
            if not structured_omitted:
                replacement = "[structured code/json block omitted; full artifact remains in workspace sidecars]"
                if used + len(replacement) + 1 <= budget:
                    out.append(replacement)
                    used += len(replacement) + 1
                structured_omitted = True
            continue
        if in_fence:
            continue
        delta = _bracket_delta(line)
        if bracket_depth > 0 or "{" in line or "[" in line or "}" in line or "]" in line:
            bracket_depth = max(0, bracket_depth + delta)
            if not structured_omitted:
                replacement = "[structured code/json block omitted; full artifact remains in workspace sidecars]"
                if used + len(replacement) + 1 <= budget:
                    out.append(replacement)
                    used += len(replacement) + 1
                structured_omitted = True
            continue
        if not stripped:
            candidate = ""
        elif stripped.startswith(("#", "-", "*", ">")):
            candidate = line
        elif ":" in stripped:
            candidate = line
        else:
            continue
        if used + len(candidate) + 1 > budget:
            continue
        out.append(candidate)
        used += len(candidate) + 1
    summary = "\n".join(out).strip()
    if not summary:
        return marker.strip()
    return summary + marker


def _middle_elide_fragment(text: str, cap: int) -> str:
    """Bound a provider fragment while preserving its authority head and action tail."""
    if len(text) <= cap:
        return text
    marker = _ELISION_MARKER
    if cap <= len(marker) + 40:
        return text[:cap]
    safe = _safe_elide_fragment(text, cap)
    if safe.strip() != marker.strip():
        return safe
    keep = cap - len(marker)
    head = max(1, int(keep * 0.58))
    tail = max(1, keep - head)
    return text[:head].rstrip() + marker + text[-tail:].lstrip()


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
        contract (T0/T1) and central always-on (T2) providers are
        never dropped by the budget.

        Persists to `workspace/mutator_briefing_iter_NNN.md` for
        operator audit. The audit log records which providers fired
        and which were tier-gated or budget-trimmed.
        """
        ordered = sorted(self.providers, key=lambda p: (p.priority, p.name))
        # ponytail: in file/workbench mode the briefing is staged as a file
        # (CONTEXT.md / ATTENTION.md) so there is no inline prompt size limit.
        # Budget trimming is a vestige of the sealed-completion/chat path where
        # the briefing was injected into a single chat string. Only apply it in
        # "chat" mode. Operator can force chat semantics via rubric.briefing_budget_chars.
        is_file_mode = (getattr(ctx, "rendering_mode", "file") == "file")
        # Soft budget cap — paper 7 §11.15 finding: 28k chars of briefing
        # collapsed gpt-5.5's structural reasoning. 12k is a midpoint
        # between the cold-shot's effective 4.5k and the legacy 28k.
        # Operator override via rubric.briefing_budget_chars.
        budget = int(ctx.rubric.get("briefing_budget_chars", 12000))
        # Operator escape hatch — disable tiering entirely (legacy mode)
        # by setting `briefing_tiered_disable: true` in the rubric.
        tiering_disabled = bool(ctx.rubric.get("briefing_tiered_disable", False))
        fragments: list[tuple[str, str]] = []
        structured_records: list[dict[str, Any]] = []
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
                        original_len = len(frag)
                        cap = getattr(p, "max_fragment_chars", None)
                        if isinstance(cap, int) and cap > 0 and original_len > cap:
                            frag = _middle_elide_fragment(frag, cap)
                            budget_trimmed.append(
                                f"{p.name}(provider_cap,{original_len}->{len(frag)}c)"
                            )
                        # Budget enforcement: only applies in chat/sealed-completion
                        # mode. In file/workbench mode every applies()=True provider
                        # renders in full — the staged file has no size constraint.
                        # Within chat mode: T0/T1/T2 are never dropped; control-plane
                        # providers are never dropped regardless of tier (a jump-forcer
                        # trimmed to fit advice cards has inverted priorities).
                        if (
                            not is_file_mode
                            and not tiering_disabled
                            and p.tier >= 3
                            and not getattr(p, "control_plane", False)
                            and running_chars + len(frag) > budget
                        ):
                            budget_trimmed.append(f"{p.name}(T{p.tier},{len(frag)}c)")
                            continue
                        fragments.append((p.name, frag))
                        for record in p.structured_records(ctx):
                            if isinstance(record, dict):
                                structured_records.append(
                                    {"provider": p.name, **record}
                                )
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
        provider_chars = len(body)
        attention_agenda = ""
        if bool(ctx.rubric.get("briefing_attention_agenda", True)):
            raw_attention_agenda = render_attention_agenda(
                structured_records,
                max_items=int(ctx.rubric.get("briefing_attention_agenda_items", 6)),
            )
            agenda_cap = int(ctx.rubric.get("briefing_attention_agenda_chars", 1200))
            if agenda_cap > 0:
                attention_agenda = raw_attention_agenda
                if len(attention_agenda) > agenda_cap:
                    attention_agenda = _middle_elide_fragment(
                        attention_agenda, agenda_cap
                    )
                    budget_trimmed.append(
                        f"attention_agenda(provider_cap,{len(raw_attention_agenda)}->{len(attention_agenda)}c)"
                    )
            if attention_agenda:
                body = attention_agenda + "\n" + body
        running_chars = len(body)
        projection_receipt = build_projection_receipt(
            body=body,
            records=structured_records,
            iter_index=ctx.iter_index,
        )
        # The synthesis caller retains the typed records separately from the
        # human-readable diagnostics and decides when a downstream endpoint
        # has actually consumed them.
        self._last_structured_records = list(structured_records)
        # Stash gate/trim diagnostics on self so the audit header can
        # show them. Best effort.
        self._last_render_diagnostics = {
            "tier_gated": tier_gated,
            "budget_trimmed": budget_trimmed,
            "active_providers": [name for name, _ in fragments],
            "budget_chars": budget,
            "running_chars": running_chars,
            "provider_chars": provider_chars,
            "stagnation_count": ctx.stagnation_count,
            "tiering_disabled": tiering_disabled,
            "rendering_mode": getattr(ctx, "rendering_mode", "file"),
            "budget_applied": not is_file_mode,
            "render_ms": round((time.perf_counter() - render_started) * 1000.0, 3),
            "provider_timings_ms": provider_timings_ms,
            "structured_record_count": len(structured_records),
            "attention_agenda_chars": len(attention_agenda),
            "projection_receipt": projection_receipt,
            "projection_receipt_status": projection_receipt.get("status"),
            "projection_receipt_failures": projection_receipt.get("failures", []),
            "projected_schema_route_count": sum(
                1
                for record in structured_records
                if isinstance(record.get("route_delivery"), dict)
            ),
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
                    f"Budget-trimmed (central but oversized): "
                    f"{diag.get('budget_trimmed', [])}\n"
                    f"Tiering disabled: {diag.get('tiering_disabled', False)}\n\n"
                    f"Render ms: {diag.get('render_ms', '?')}\n"
                    f"Provider timings ms: {diag.get('provider_timings_ms', {})}\n\n"
                    f"---\n"
                )
                audit_path.write_text(header + body, encoding="utf-8")
                records_path = ws / f"mutator_briefing_iter_{ctx.iter_index:03d}_records.json"
                records_path.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "iter_index": ctx.iter_index,
                            "records": structured_records,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                projection_payload = (
                    json.dumps(projection_receipt, indent=2, sort_keys=True) + "\n"
                )
                projection_path = (
                    ws
                    / f"mutator_briefing_iter_{ctx.iter_index:03d}_projection_receipt.json"
                )
                projection_path.write_text(projection_payload, encoding="utf-8")
                (ws / "mutator_briefing_projection_latest.json").write_text(
                    projection_payload,
                    encoding="utf-8",
                )
                # Render receipt — one JSONL row per render so silent trims are auditable.
                # Appended (not overwritten) so the full run history survives.
                # ponytail: wire next to the projection-latest writer; no separate sink.
                render_receipt = {
                    "schema": "ztare.briefing_render.v1",
                    "iter": ctx.iter_index,
                    "mode": getattr(ctx, "rendering_mode", "file"),
                    "providers_applied": [name for name, _ in fragments],
                    "providers_rendered": [name for name, _ in fragments if not any(
                        t.startswith(f"{name}(") for t in budget_trimmed
                        if "(T" in t and "(provider_cap" not in t
                    )],
                    "providers_trimmed": [
                        t for t in budget_trimmed
                        if "(T" in t and "(provider_cap" not in t
                    ],
                    "total_chars": running_chars,
                    "budget_applied": not is_file_mode,
                }
                receipts_path = ws / "briefing_render_receipts.jsonl"
                with receipts_path.open("a", encoding="utf-8") as _rf:
                    _rf.write(json.dumps(render_receipt, sort_keys=True) + "\n")
        except Exception:
            pass  # audit failure is non-fatal

        return body


def render_default_briefing_context(ctx: BriefingContext) -> dict[str, Any]:
    """Render the standard in-loop briefing and expose audit diagnostics.

    This is the integration surface used by ``autoresearch_loop`` and tests.
    Keeping the active-provider accounting here prevents drift between the
    prompt carrier and cheap no-model seam tests.
    """
    briefing = default_briefing()
    body = briefing.render(ctx)
    diagnostics = getattr(briefing, "_last_render_diagnostics", {}) or {}
    return {
        "body": body,
        "structured_records": list(
            getattr(briefing, "_last_structured_records", ()) or ()
        ),
        "active_providers": list(diagnostics.get("active_providers") or []),
        "diagnostics": diagnostics,
        "projection_receipt": diagnostics.get("projection_receipt") or {},
    }


# ── Convenience: default registry seeded with shipped providers ─────────


def default_briefing() -> MutatorBriefing:
    """Return a MutatorBriefing with the standard provider set wired in.

    Imported from briefing_providers.* so each provider lives in its
    own file. Adding a new provider to the default set is a 1-line
    edit here plus a new file under briefing_providers/.
    """
    from ztare.orchestrator.briefing_providers.fit_telemetry import (
        FitTelemetryProvider,
    )
    from ztare.orchestrator.briefing_providers.gate_gap import (
        GateGapProvider,
    )
    from ztare.orchestrator.briefing_providers.iter_trajectory import (
        IterTrajectoryProvider,
    )
    from ztare.orchestrator.briefing_providers.row_outliers import (
        RowOutlierProvider,
    )
    from ztare.orchestrator.briefing_providers.asymptote_deviation import (
        AsymptoteDeviationProvider,
    )
    from ztare.orchestrator.briefing_providers.analogy_candidates import (
        AnalogyCandidatesProvider,
    )
    from ztare.orchestrator.briefing_providers.framer_recommendation import (
        FramerRecommendationProvider,
    )
    from ztare.orchestrator.briefing_providers.per_class_breakdown import (
        PerClassBreakdownProvider,
    )
    from ztare.orchestrator.briefing_providers.noise_profile_brief import (
        NoiseProfileBriefingProvider,
    )
    from ztare.orchestrator.briefing_providers.contamination_defense import (
        ContaminationDefenseBriefingProvider,
    )
    from ztare.orchestrator.briefing_providers.data_diagnostics import (
        DataDiagnosticsBriefingProvider,
    )
    from ztare.orchestrator.briefing_providers.cold_llm_seed import (
        ColdLlmSeedBriefingProvider,
    )
    from ztare.orchestrator.briefing_providers.cold_shot_seed import (
        ColdShotSeedBriefingProvider,
    )
    from ztare.orchestrator.briefing_providers.qualitative_evidence_seed import (
        QualitativeEvidenceSeedProvider,
    )
    from ztare.orchestrator.briefing_providers.forced_reframe import (
        ForcedReframeBriefingProvider,
    )
    from ztare.orchestrator.briefing_providers.verified_axioms import (
        VerifiedAxiomsProvider,
    )
    from ztare.orchestrator.briefing_providers.variational_promotion_floor import (
        VariationalPromotionFloorProvider,
    )
    from ztare.orchestrator.briefing_providers.contract_rules import (
        ContractRulesProvider,
    )
    from ztare.orchestrator.briefing_providers.graph_focus_receipt import (
        GraphFocusReceiptProvider,
    )
    from ztare.orchestrator.briefing_providers.r1_pattern_warning import (
        R1PatternWarningProvider,
    )
    from ztare.orchestrator.briefing_providers.tried_failed_digest import (
        TriedFailedDigestProvider,
    )
    from ztare.orchestrator.briefing_providers.refuted_families import (
        RefutedFamiliesProvider,
    )
    from ztare.orchestrator.briefing_providers.lagrangian_worked_example import (
        LagrangianWorkedExampleProvider,
    )

    b = MutatorBriefing()

    # ── Tier classification (paper 7 §11.15 briefing-density fix) ──
    # T0/T1 = always (apparatus contract + central structural directive)
    # T2    = always (lightweight per-iter feedback)
    # T3    = stagnation_count > 2
    # T4    = stagnation_count > 4
    # T5    = hibernate (only via rubric.briefing_force_show_<name>)
    # Tiers set on instances below; modify here, not in provider files.

    # Live champion (patch base): identifies the promoted champion so the leaf
    # knows exactly what to patch. Priority 18 — before everything else, so the
    # patch base is the very first directive the leaf sees. Tier 0 (non-advisory).
    from ztare.orchestrator.briefing_providers.live_champion import (
        LiveChampionProvider,
    )
    _p = LiveChampionProvider(); _p.tier = 0
    b.register(_p)
    # Contract rules (2026-04-27): teaches apparatus contracts upfront so
    # the mutator's first attempt complies. Renders at priority 20 — first.
    # Solves the "every iter wastes 1-3 R1 strikes re-learning the same
    # rules" pattern seen across gp163d (denylist hits, numpy imports) and
    # gp168 (missing I_model on qualitative substrate). Per-iter cost: ~2k
    # briefing tokens; ROI: prevents ~$0.30-1.20/iter R1-thrash bills.
    _p = R1PatternWarningProvider(); _p.tier = 0
    b.register(_p)
    # World-model committee state for interactive-environment projects
    # (GP-250): committee size, MDL champion, witnessed guard contexts, and
    # the grammar-ceiling instruction that scopes the mutator to grammar
    # extensions. Applies only when the rubric declares grid_dsl.
    from ztare.orchestrator.briefing_providers.worldmodel_committee import (
        WorldmodelCommitteeProvider,
    )
    _p = WorldmodelCommitteeProvider(); _p.tier = 1
    b.register(_p)
    # Leaf workbench (ENGINE-level contract, substrate adapter): exposes the
    # bounded worldmodel observation/probe capabilities a sealed leaf may cite
    # via typed receipts. Missing instruments are reported as LOWERABILITY_BLOCKED
    # tool gaps; capability proposals are optional meta attachments.
    from ztare.orchestrator.briefing_providers.leaf_workbench import (
        LeafWorkbenchProvider,
    )
    _p = LeafWorkbenchProvider(); _p.tier = 1
    b.register(_p)
    # Surviving-candidates (ENGINE-level multiple hypotheses): prior gate-passing
    # submissions re-gated each iteration; multi-survivor state => the briefing
    # demands a DISCRIMINATING experiment instead of same-evidence variants.
    # General: any project with gate_harness.py + submission snapshots.
    from ztare.orchestrator.briefing_providers.surviving_candidates import (
        SurvivingCandidatesProvider,
    )
    _p = SurvivingCandidatesProvider(); _p.tier = 1
    b.register(_p)
    # Proven invariants (ENGINE-level, general): kernel-ratified theorems about
    # the law surface as a HARD constraint tier — the fix for proven facts not
    # reaching identification. Tier 0 (never gated out; a proof is not advisory).
    from ztare.orchestrator.briefing_providers.proven_invariants import (
        ProvenInvariantsProvider,
    )
    _p = ProvenInvariantsProvider(); _p.tier = 0
    b.register(_p)
    # LeanMill proof jobs (ENGINE-level, general): async proof-work receipts
    # and absorption commands. This keeps proof work visible to mutators without
    # running Lean or polling solver processes during prompt assembly.
    from ztare.orchestrator.briefing_providers.leanmill_proof_jobs import (
        LeanMillProofJobsProvider,
    )
    _p = LeanMillProofJobsProvider(); _p.tier = 1
    b.register(_p)
    # Structural transport (2026-07-03, ENGINE-level, general): LATERAL basin
    # escape — cross-domain structures whose SHAPE matches the current seam, the
    # horizontal complement to the vertical cold-deanchor. STAGNATION-GATED in
    # applies() (stagnation_count >= 2 — analogy is noise on a healthy iter) and
    # fingerprint-sha CACHED (the live cross-field query costs API money, so it
    # runs only when the seam's shape changes). Tier 2 (advisory).
    from ztare.orchestrator.briefing_providers.structural_transport import (
        StructuralTransportProvider,
    )
    _p = StructuralTransportProvider(); _p.tier = 2
    b.register(_p)
    # Operator proposals (GP-250, ENGINE-level): the AUTOMATED grammar-expansion
    # channel — undispositioned candidate operator cards in
    # workspace/operator_proposals.jsonl brief the mutator that the residual is
    # irreducible under the current catalog. Tier 1 (central structural
    # directive: scopes the mutator to the law shape of a new operator).
    from ztare.orchestrator.briefing_providers.operator_proposals import (
        OperatorProposalsProvider,
    )
    from ztare.orchestrator.briefing_providers.strategy_experiments import (
        StrategyExperimentsProvider,
    )
    _p = StrategyExperimentsProvider(); _p.tier = 1
    b.register(_p)
    _p = OperatorProposalsProvider(); _p.tier = 1
    b.register(_p)
    _p = TriedFailedDigestProvider(); _p.tier = 2
    b.register(_p)
    _p = RefutedFamiliesProvider(); _p.tier = 2
    b.register(_p)
    _p = ContractRulesProvider(); _p.tier = 0
    b.register(_p)
    _p = GraphFocusReceiptProvider(); _p.tier = 1
    b.register(_p)
    _p = FitTelemetryProvider(); _p.tier = 2
    b.register(_p)
    # Variational-promotion explainer (2026-04-27): when a substrate has
    # tier_3_universal_law_target.active=true AND a prior iter was capped
    # at 50 by R20-R24 or PPN gates, this provider renders an unambiguous
    # cap-mechanism explanation at the TOP of the briefing (priority 30 —
    # before VerifiedAxioms@50, ForcedReframe@130, ColdLLM@150). Solves the
    # gp163d gp-5.5 attractor problem where briefing density obscured the
    # Variational-promotion criteria; this provider surfaces them as a central signal.
    _p = VariationalPromotionFloorProvider(); _p.tier = 2
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
    # GP-168 Forced REFRAME: when stagnation triggers fire,
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
    _p = PerClassBreakdownProvider(); _p.tier = 2  # central per-iter signal
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
        from ztare.orchestrator.briefing_providers.embedding_history import (
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
        from ztare.orchestrator.briefing_providers.obligation_contract import (
            ObligationContractProvider,
        )
        _p = ObligationContractProvider()  # tier=0 set on the class
        b.register(_p)
    except Exception:
        pass
    return b
