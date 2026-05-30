# GP-100 — Epistemic Decoupling: Separating Topology Generation from Thesis Writing

> **Seam metadata** · `seam_id:` GP-100 · `track:` engine · `status:` open - opened 2026-04-19 · `last_updated:` 2026-05-08


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

open — opened 2026-04-19

## ID

GP-100

## Eigenquestion

Should the primary mutation loop always decouple mathematical topology generation from logical thesis writing, or is the current tactical patch (GPT-4.1 alignment on Component D seed path only) sufficient?

## Problem Statement

Scientific discovery requires two contradictory cognitive modes:

1. **The Generator (Abducer):** Creative, pattern-focused, willing to leap. Needs to propose wild topologies and recognize geometric structure in data. Gemini excels here.

2. **The Critic (Epistemologist):** Conservative, Bayesian, pedantic. Must acknowledge what the data does NOT prove, frame claims as "consistent with" not "proven by." GPT-4.1 excels here.

The current architecture asks a single LLM (Gemini) to perform both roles in one `mutate_thesis()` call. When Gemini is the mutator without Component D, it proposes both the functional form AND the justification text. Its Generator bias bleeds into the Critic role, producing confident overclaims that the judge consistently scores at 50.

### Current tactical patch (implemented 2026-04-19)

When Component D injects a topology via seed queue, an epistemic alignment pass routes the thesis writing to GPT-4.1 via `safe_mutate()`. The fit_declaration is protected (immutable). GPT-4.1 rewrites only the prose. This covers the post-Feynman-Wall path.

The non-seed path (early iterations, before library exhaustion) is unchanged — Gemini still does both jobs.

### Why this matters for Phase C

For Phase B (recovering known laws), overclaiming is caught by the GT-backed farther-tail gate. For Phase C (discovering unknown laws), there is no GT. The holdout is the only safety net. An epistemically overclaiming thesis about an unknown law could pass a finite-window holdout through Padé-style overfitting. The decoupled architecture is the structural defense against false discoveries.

## Scope

**Covers:**
- Whether to split `mutate_thesis()` into `propose_topology()` + `write_thesis()` on ALL paths
- Cost/latency tradeoff of two LLM calls per iteration
- Whether the alignment pass (tactical patch) is sufficient for Phase B
- Whether full decoupling is required before Phase C
- Model selection for each role (could change as models improve)

**Does not cover:**
- Changes to Component D's composition loop
- Changes to the judge (GPT-4.1 stays as judge)
- Grammar constraints (GP-099 scope)

## Existing Codebase Evidence

### 1. Tactical patch is live

`autoresearch_loop.py` lines ~2951-2995: When `_comp_seed_injected = True`, the alignment pass fires via `safe_mutate()` with GPT-4.1. The fit_declaration is protected by a safety check (`_seed_expr[:40] in _aligned`).

### 2. Non-seed path unchanged

When `not _comp_seed_injected` (line ~2985), `mutate_thesis()` is called with `current_mutator` (Gemini). Both topology and prose come from one call.

### 3. Empirical evidence of failure

Langevin sandbox_16 iterations 2-5: Gemini consistently scored 50 due to "catastrophic overclaim of tail exclusivity." The topology was sound (passed all hard gates) but the prose was assertive beyond what finite-window data supports.

## Open Questions for Debate

**Q1: Is the tactical patch sufficient for Phase B?**
The alignment pass only fires on the Component D seed path. In early iterations (before Feynman Wall), Gemini still writes everything. If Gemini proposes a good topology in iteration 3 but overclaims in the prose, the score is capped. Is that acceptable for Phase B?

**Q2: Is full decoupling required before Phase C?**
Phase C has no GT. The holdout is finite. An overclaiming thesis that passes holdout could be published as a false discovery. Does this require structural prevention (always decouple) or is the alignment pass + strong judge sufficient?

**Q3: Cost/latency tradeoff**
Two LLM calls per iteration: Gemini for topology (~$3) + GPT-4.1 for prose (~$0.50). Total ~$3.50 vs current ~$3. The cost increase is marginal (~15%). The latency increase is sequential (wait for Gemini, then GPT-4.1). Is this acceptable?

**Q4: What happens when models improve?**
If a future model is both creative and epistemically conservative, the decoupling becomes unnecessary overhead. Should the architecture support falling back to a single model when model capabilities converge?

**Q5: Splitting `mutate_thesis()`**
The current function is ~600 lines with complex context assembly (constraints, evidence, charter, pivot profiles, etc.). Splitting it into `propose_topology()` + `write_thesis()` requires refactoring the context assembly to be shared. Is this worth the engineering cost, or is the alignment pass approach (separate targeted prompt, not a refactor of mutate_thesis) architecturally superior?

## Implementation (2026-04-19)

### What shipped

Tactical patch in `autoresearch_loop.py` lines ~2960-3011:

1. **Rubric flag**: `"epistemic_alignment": true` in rubric JSON opts in. Default false — general-purpose engine is unaffected.
2. **Alignment pass**: When a Component D seed is injected AND `epistemic_alignment` is true, `safe_mutate()` calls GPT-4.1 with a targeted prompt that rewrites ONLY the thesis prose. The `fit_declaration` block is protected.
3. **Context injection**: Persona, evidence (first 4000 chars), prior weakest point, confirmed constraints, and structural memory are injected so GPT-4.1 can write data-grounded prose.
4. **Prompt requirements**: Map 1:1 to the rubric's 8 scoring criteria (regime decomposition, discriminator, full-range fit, transition shape, anchor proxy, trace emergence, no external import, grammar compliance).
5. **Safety check**: If GPT-4.1's output doesn't contain the first 40 chars of the seed expression, falls back to unaligned injection with a warning.
6. **Langevin rubric**: `gp096_langevin_sandbox_16.json` has `"epistemic_alignment": true` set.

### What did NOT ship

- Non-seed path is unchanged — when `not _comp_seed_injected`, `mutate_thesis()` still calls the default mutator (Gemini) for both topology and prose.
- No `propose_topology()` / `write_thesis()` split of `mutate_thesis()`.
- No new CLI arg — controlled purely by rubric flag.

### Files modified

| File | Change |
|------|--------|
| `src/ztare/validator/autoresearch_loop.py` | GP-100 alignment pass block (~50 lines) inside seed injection path |
| `rubrics/gp096_langevin_sandbox_16.json` | Added `"epistemic_alignment": true` |

## Recommendation

Defer full decoupling. The tactical patch (alignment pass on seed path) addresses the immediate Langevin failure. Open the seam for debate when Phase C substrate selection begins. The cost of premature architecture is higher than the cost of a focused patch that demonstrably works.
