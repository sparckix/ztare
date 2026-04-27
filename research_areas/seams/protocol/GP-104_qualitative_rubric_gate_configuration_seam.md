# GP-104 — Qualitative Rubric Gate Configuration Seam

## Status

`active` — n=3 observations (Seattle, paper5_self_review, gp096_sandbox_20 partial). Pattern is real. Fix is manual patch per project today. Debate converged on building `generate_general_purpose_project` (spec pending). See ## Debate Outcome section.

## ID

GP-104

## Eigenquestion

What is the minimum required rubric configuration for qualitative (non-numerical) projects to avoid silent gate misfires that zero valid scores?

## Problem Statement

ZTARE's global gates were designed for quantitative law-recovery substrates (curve-fit tasks with numerical evidence). Three of those gates fire on every project by default and produce hard fails or severe penalties on qualitative projects where they are structurally inapplicable:

| Gate | Default behavior when misconfigured | Effect on qualitative projects |
|------|--------------------------------------|-------------------------------|
| `global_evidence_fit` | Hard fail if evidence_text parses to zero numerical rows | Zeros every iteration; evidence is text, not numbers |
| `global_extrapolation_gap` | Hard fail if `farther_tail_region` key absent from rubric | Zeros every iteration; no holdout interpolation concept in qualitative work |
| `global_uniqueness_gap` | −40 penalty if no criterion key contains "rival" | Cuts scores by 40 pts; policy "rivals" are not mathematical structural forms |

**Observed instances:**

1. **gp096_sandbox_20 Division A (2026-04-20):** `farther_tail_region` absent → `global_extrapolation_gap` hard fail → 20/20 iterations scored 0. Fixed by adding `farther_tail_region: null`. (This was a quantitative project but the gate opt-out was not documented in the rubric setup checklist.)

2. **seattle_tech_housing (2026-04-20):** All three gates fired. `global_evidence_fit` and `global_extrapolation_gap` hard-failed at iteration 0; `global_uniqueness_gap` cut score from 60 → 20 at iteration 2. Fixed by adding all three opt-out keys.

3. **paper5_self_review (2026-04-20):** `farther_tail_region: null` was added during setup (lesson from gp096); `disable_evidence_fit_gate` was missing and would have hard-failed. Fixed before run started.

**Root cause:** The rubric construction process (manual JSON authoring) has no checklist that distinguishes project type and required gate opt-outs. The gates have disable/opt-out keys, but operators discover them only after observing a misfire.

## Project Type Taxonomy

### Type A — Quantitative Law Recovery
**Examples:** gp096_sandbox_20, gp023_planck, sandbox_17_KWW, sandbox_15_Selkov  
**Evidence format:** Numerical (x, y) pairs  
**Required gates:** All gates active. `farther_tail_region` must be declared (real value or null with reason).  
**Checklist:**
- `farther_tail_region`: declare with real [min, max] dict OR `null` + `disable_reason` if gate_harness already handles it
- `evidence_fit_threshold`: set (default 0.15 if omitted)
- `holdout_hard_gate`: true if gate_harness enforces holdout

### Type B — Qualitative Thesis (Policy, Philosophy, History, Social Science)
**Examples:** seattle_tech_housing, paper5_self_review, eu_union_stability, central_station  
**Evidence format:** Text documents, reports, academic papers  
**Required opt-outs:**
```json
{
  "farther_tail_region": null,
  "farther_tail_region_disable_reason": "<project type> — no numerical holdout gate",
  "disable_evidence_fit_gate": true,
  "disable_evidence_fit_gate_reason": "<project type> — evidence surface is text, not a numerical curve",
  "disable_uniqueness_gap_gate": true,
  "disable_uniqueness_gap_gate_reason": "<project type> — rival mechanisms scored by rubric criteria; keyword heuristic for mathematical forms does not apply"
}
```
**Exception:** If the rubric already contains a criterion key with "rival" in its name, `disable_uniqueness_gap_gate` is not needed (the gate auto-passes on criterion key detection).

### Type C — Mixed (Quantitative claim embedded in qualitative thesis)
**Examples:** eu_union_failure_probability_2035 (% forecast inside policy analysis)  
**Required:** Type B opt-outs PLUS `holdout_hard_gate: false` and forecast-typing flags.  
**Key risk:** `global_evidence_fit` may pass if evidence has parseable numbers even when those numbers aren't the fit target — audit carefully.

## Fix: Rubric Pre-Run Validator (Not Yet Built)

The structural fix is a pre-run validator (invoked at `make seal` time or as a GP-103-style auto-check) that:
1. Detects project type from evidence format and rubric structure
2. Warns if required opt-out keys are absent for the detected type
3. Blocks sealing if a Type B project has no `farther_tail_region` key and no `disable_evidence_fit_gate`

Until that validator is built, operators must apply the Type B checklist manually when authoring qualitative rubrics.

## Where to Document

**User/operator-facing:** Add a "Rubric Setup Checklist by Project Type" section to `docs/OPERATIONAL_MANUAL.md` (or equivalent) so the operator knows which keys to add before running.

**Internal:** This seam + the ZTARE board row.

## Closure Condition

Closed when a pre-run validator (at seal time) auto-checks for required type-specific gate configuration and warns/blocks on missing keys. Until then: `active`, manual checklist required.

## Debate Outcome (2026-04-20)

Three candidate fixes were debated:

**A — Field manual checklist:** Fixes documentation, not enforcement. Already failed — fix was known after gp096 and still missed on Seattle and paper5. Rejected as sole solution.

**B — Extend GP-103 seal checker:** Correct enforcement point (seal time), but type detection from rubric structure is fragile. Quantitative projects can also need `farther_tail_region: null`. The heuristic would have false positives/negatives. Viable as a belt-and-suspenders addition but not the primary fix.

**C — Build `generate_general_purpose_project`:** Adopted. Fixes the root cause (blank-slate authoring produces no opt-outs) rather than the symptom. MVP is narrow: ~100 lines of Python, one Makefile target, LLM-drafted persona/criteria from a brief, Type B opt-outs pre-filled in template. Composable with GP-072. Addresses GP-054 persona-weakness failure mode simultaneously (LLM drafts an adversarial persona rather than operator writing from scratch).

**Spec needed:** Yes. Generator touches rubric schema, project folder structure, Makefile, and optional LLM call.

## Next Action

1. Write `research_areas/specs/active/GP-104_general_purpose_project_generator_spec.md`
2. Implement `src/ztare/generator/generate_gp_project.py` per spec
3. Add `generate-gp` Makefile target
4. Add Type B opt-out template to `config/renderers/field_manual.md` as belt-and-suspenders documentation
5. Optionally extend GP-103 seal check to warn on absent Type B keys

---

## GP-104B — Charter-Rubric Spirit Gap (2026-04-20)

### New Eigenquestion

The original GP-104 eigenquestion (gate misfire prevention) is solved. A second failure mode is confirmed: **the LLM-drafted rubric captures the explicit content of the charter brief but systematically drops implicit requirements** (second-order effects, dynamic modeling, counterfactual discipline, capital stack). The mutator then optimizes for the rubric, not the charter, and produces a high-scoring thesis that is narrow and shallow relative to what the charter actually asked.

**Observed instance:** seattle_tech_housing. Charter asked "is tech destroying Seattle — model positive and negative externalities." Rubric produced four static criteria (causal attribution, mechanism pricing, Boeing comparator, falsifiable prediction). Mutator produced 94/100 thesis consisting of a static voucher-NPV vs. physical-replacement calculation. Top 10% executive synthesis; not 0.1% dynamic policy analysis.

**Root cause anatomy (three independent causes):**

| Layer | Failure | Observable |
|---|---|---|
| Rubric generation | LLM draft drops implicit charter requirements (dynamic modeling, second-order effects) | Rubric criteria match explicit brief language; no criterion penalizes static first-order analysis |
| Persona | LLM-drafted persona is too polite — scores surface rigor, not modeling adequacy | 94/100 on a static calculation that a real adversarial expert would penalize |
| Judge context | Charter is not live during judge scoring — judge sees rubric + thesis but not charter question | Judge cannot penalize failure to engage charter spirit that no criterion encodes |

### Three-Fix Solution

All three fixes are additive; none alone is sufficient.

**Fix 1 — Charter-rubric gap check (in `generate-gp`):**
After LLM drafts rubric, a second adversarial LLM call reads the charter and rubric and returns: "What does the charter implicitly require that no rubric dimension currently scores?" If the gap list is non-empty, a revision pass forces the rubric to add or modify dimensions to cover the gaps.

**Fix 2 — Persona hardening (in `generate-gp`, rubric prompt):**
The RUBRIC_SYSTEM_PROMPT must require the persona to name at least one specific modeling failure mode that will be penalized even absent an explicit criterion — e.g., "hostile to any cost calculation that treats a variable as fixed without a sensitivity range when second-order market effects are knowable." This creates implicit scoring pressure beyond what the criteria encode.

**Fix 3 — Charter preamble injection (in `autoresearch_loop.py`, judge prompt):**
Inject the charter's `## Core Question` field as a preamble into the judge's scoring context. The judge is then explicitly instructed: "The operator's original question was [X]. Score the thesis not only on rubric criteria but on whether it engages this question at the required level of rigor." Scope-limited to `## Core Question` only (not full charter) to avoid leaking mechanisms or methodology hints.

### Implementation Status

- Fix 1 and Fix 2: implement in `generate_gp_project.py` — requires a second LLM call for gap check and a revision pass, and an updated RUBRIC_SYSTEM_PROMPT requiring named modeling failure modes.
- Fix 3: implement in `autoresearch_loop.py` — inject `project_charter.md ## Core Question` into judge scoring prompt if file exists.

### Closure Condition for GP-104B

Closed when: (a) generate-gp includes gap check + persona hardening, (b) autoresearch_loop injects charter preamble into judge context, (c) a re-run of seattle_tech_housing with rewritten charter/rubric produces a thesis that engages dynamic modeling and second-order effects.
