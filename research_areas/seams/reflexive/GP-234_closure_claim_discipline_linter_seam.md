# GP-234 — Closure-Claim Discipline Linter (Tier-1 deterministic + Tier-2 LLM-semantic)

> **Seam metadata** · `seam_id:` GP-234 · `track:` reflexive · `status:` open / experimental · `last_updated:` 2026-05-15


**Status:** open / experimental
**Cabinet:** `reflexive/` (meta-loop on the apparatus's own discipline layer)
**Authored:** 2026-05-15
**Trigger:** NS Clay closure session (ticks 495-512) produced 5 ANTI-PATTERN-012 catches (vocabulary-chain-laundering) at severity 7-9 caught only by external Meta-Darwin dispatch or operator-forwarded GPT-5.5 analysis. Operator surfaced the gap: discipline catches were not autonomous; the apparatus needed in-artifact / pre-tick automated discipline checks.

## 1. The empirical observation

Across ticks 495, 496, 498, 501, 504 the artifact author (me, Claude) committed five distinct laundering errors:
- typed `Prop := True` placeholders (tick495)
- quantifier inversion `∀n` vs `limsup` (tick496)
- Serrin LPS exponent miscalculation `5/4 > 1` (tick498)
- nested-not-disjoint laundering (tick501)
- vector-vs-1-form direction-flip (tick504)

Each was caught EXTERNALLY (Meta-Darwin dispatch or GPT-5.5 forward), not in-artifact. The discipline memory `feedback_be_meta_darwin_to_self_2026_05_14.md` explicitly says discipline must run IN-ARTIFACT; the empirical data shows this didn't happen autonomously.

Diagnosis (operator-mediated): two compounding gaps.
- **Tool-not-consulted laundering**: the universal-language catalog at `workingpapers/.../structural_language_catalog_20260514.json` existed but wasn't consulted during PDE chain construction.
- **Multi-scope discipline gap**: ANTI-PATTERN-012 6-point verification was applied at LOCAL step scope only; CHAIN, RECURSIVE, META scopes were skipped.

## 2. The mitigation built this seam

Three meta-pattern entries minted:
- **META-PATTERN-022** `gowers_first_with_content_layer_composition` — composes PATTERN-025 (workflow scaffold) + universal-language JSONL (mathematical content) + ANTI-PATTERN-012 (per-step failure check).
- **META-PATTERN-023** `multi_scope_pattern_application` — patterns must be applied at FOUR scopes: local / chain / recursive / meta.
- **ANTI-PATTERN-012** `vocabulary_chain_laundering` — already minted earlier in the session.

Plus two automated linters:
- **Tier-1 deterministic** at `scripts/public/control/closure_claim_discipline_linter.py` — token-matching catches gross failures (no enumeration block at all, no scope coverage section, no anti-pattern reference). Cheap, fast, runs locally without API. Integrated into `rd_tick_brief.py` §2b.
- **Tier-2 LLM-semantic** at `scripts/public/control/closure_claim_discipline_linter_tier2.py` — gpt-4.1-mini call catches subtle SEMANTIC gaps (artifact has the right tokens but the chain has direction/quantifier/inclusion flip). EXPERIMENTAL; should run only when Tier-1 plateaus.

## 3. Why both tiers exist

| Tier | Strength | Weakness |
|---|---|---|
| Tier-1 (deterministic, token-matching) | cheap, fast, no API cost | misses subtle semantic flips |
| Tier-2 (LLM, gpt-4.1-mini) | catches semantic flips Tier-1 misses | API cost, slower, noisier |

**Empirical evidence from initial test on tick510 audit note**:
- Tier-1 verdict: 3 of 4 checks pass, FAILS on universal-language op enumeration (only 1 op named with sufficient lexical match).
- Tier-2 verdict (gpt-4.1-mini): FAIL with 5 semantic issues at severity 6-9 (direction-flip in PATTERN-007 step, missing recursive-scope coverage, missing FORM/DIRECTION verification at chain composition).

Both produce useful but distinct signal. Tier-2 catches subtle issues Tier-1 misses; Tier-1 catches gross issues without API cost.

## 4. Test plan

**Tier-1 sustained-value test (3-5 sessions)**:
- Apply Tier-1 to every closure-claim artifact in the next 3-5 NS Clay sessions.
- Track: (a) artifacts that fail Tier-1 and turn out to have real issues; (b) artifacts that pass Tier-1 and still have issues caught externally.
- Promote to "validated cheap precondition" if Tier-1 catches ≥3 real issues with <1 false positive per session.

**Tier-2 plateau-trigger test**:
- After Tier-1 demonstrates sustained value: enable Tier-2 on every artifact Tier-1 passes.
- Compare Tier-2 catches vs external (operator/GPT-5.5) catches.
- Promote Tier-2 to default if it catches ≥80% of external catches at <10% false-positive rate.

**Cost ceiling**: Tier-2 should run at most once per closure-claim artifact (gpt-4.1-mini ~$0.001-0.005 per call). For 10 artifacts/session, ~$0.05 budget.

## 5. Pre-tick integration

`rd_tick_brief.py` §2b surfaces:
- 4 discipline checks available
- Run command for Tier-1 check
- Run command for status/summary

Operator/agent reads §2b at session start; should also read every closure-claim artifact for in-artifact discipline notes BEFORE running the linter (anti-laundering on the linter itself).

## 6. Cross-link

- `org/patterns/multi_scope_pattern_application.md` (META-PATTERN-023)
- `org/patterns/gowers_first_with_content_layer_composition.md` (META-PATTERN-022)
- `org/anti-patterns/vocabulary_chain_laundering.md` (ANTI-PATTERN-012)
- `docs/concepts/anti_pattern_catalog.md` SB-4 (parallel human-readable entry)
- `feedback_be_meta_darwin_to_self_2026_05_14.md` (decisive user-memory)
- AGENTS.md §6m (canonical surfacing route)

## 7. Decision needed

**Block**: do we trust Tier-1 enough to ship as default RD-agent gate, or does it need 3-5 sessions of empirical validation first?

**Operator's directive (2026-05-15)**: test Tier-1 sustainably before promoting Tier-2 to default. Tier-2 built but flagged EXPERIMENTAL until Tier-1 plateaus. This seam captures the test plan.

## 8. Risks

- **Tier-1 false negatives**: token-matching passes artifacts with subtle issues (caught in initial test: tick510 passes some checks despite Tier-2 finding severity-9 issues).
- **Tier-2 cost creep**: ~$0.001-0.005 per call, but at scale could exceed budget. Cap at 1 call per artifact.
- **Linter laundering**: an artifact could be written to GAME the linter (include all keywords without substantive content). Mitigate via Tier-2 semantic check + occasional human/external audit.
- **Catalog drift**: linter must be kept in sync with new patterns/meta-patterns; the architecture index helps but updates require explicit care.

## 9. Status hooks

- Tier-1 shipped: `scripts/public/control/closure_claim_discipline_linter.py`.
- Tier-2 shipped EXPERIMENTAL: `scripts/public/control/closure_claim_discipline_linter_tier2.py`.
- `rd_tick_brief.py` §2b integrated.
- Architecture index has META-PATTERN-022, META-PATTERN-023, ANTI-PATTERN-012.
- Pattern catalog YAML regenerated (27 patterns).

Next step gate: 3-5-session Tier-1 sustained-value test before Tier-2 promotion.
