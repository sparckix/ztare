# GP-061 Constraint Accumulation as Scientific Output — Seam

> **Seam metadata** · `seam_id:` GP-061 · `track:` apparatus · `status:` unrecorded · `last_updated:` 2026-05-08


Status: open
Opened: 2026-04-14
Revised: 2026-04-14 (after Gemini framing + sandbox_07 retroactive test)
Hypothesis family: H-ARCH-02 (output semantics)

---

## Problem Statement

ZTARE treats failure modes as routing signals. The mutator consumes the weakest-point critique, the debate log accumulates adversarial pressure, the structural_misfit hint captures one class of residual pattern, the structural_memory records per-family fit diagnostics. In every case the failure information is used *instrumentally* — as input to the next mutation — and discarded after.

The primary output of a run is a single champion thesis plus a score trajectory. Eliminated hypothesis classes are not surfaced as findings.

The scientific value claim this seam tests: **the epistemic output of a ZTARE run is more faithfully captured by the set of hypotheses it has certified as inconsistent with the evidence than by the single thesis it has promoted.** If true, current output format is underselling the apparatus. If false, GP-061 is re-presentation and should not be built.

---

## Retroactive Test Against sandbox_07 (2026-04-14)

Before designing the architecture, a discriminating experiment was run against sandbox_07's closed artifacts to check whether the premise holds.

**What exists:** sandbox_07's workspace already contains a harvesting layer. `workspace/derived_constraints.json` holds 17 provisional constraints extracted by the meta_judge and committee during the run. `workspace/structural_memory.json` records every structural family that was tried, with fingerprints, residuals, and diagnostic classifications.

**What the existing harvester captured:** all 17 constraints are **process / charter-compliance constraints**. Examples:

- PC-001 "all components must be derived through step-by-step reasoning"
- PC-002 "avoid importing named models from external domains"
- PC-005 "every term must have physical or empirical justification"
- PC-008 "model must accurately predict empirically observed peak locations"
- PC-011 "models must maintain numerical stability"
- PC-014 "functional form for hazard rate must be derived from first principles"

Every constraint is a statement about *how* a thesis should be built, not about *what mathematical structure* the evidence requires. The derived_constraints.json layer is a rubric-compliance harvester, not a structural-lesson harvester.

**What the existing harvester missed:** `structural_memory.json` contains the raw signal for the structural lesson in machine-readable form. Every family tried in sandbox_07 had the shape `A * phi^α * psi^δ * [eml-wrapped inner expression] + c`, with `latest_diagnostic_classification: structural_misfit` on every row. The inner eml arguments varied (`-(α·phi)/(γ·psi)`, `(α·phi)/(γ·psi)`, `-(α/γ)·(phi/psi)^γ`, etc.) but the outer multiplicative skeleton was invariant across all ten iterations. No family that broke this multiplicatively-separable skeleton was ever tried.

The structural lesson — "every member of the family `A·φ^α·ψ^δ·f(combined-φ,ψ)+c` produces structured residuals; the solution must differ at the outer skeleton, not at the inner composition" — is latent across all ten iterations of structural_memory but does not appear in any derived_constraints entry, any debate log, or the closure document.

**What this means for GP-061:**

1. The harvesting infrastructure exists and works at the process layer.
2. It does not extract structural/mathematical lessons because no component is looking at structural_memory with the instruction "find the invariant property shared by every failed family and emit it as a have-to-believe constraint on the next candidate."
3. The missing piece is not a new pipeline. It is **one function** that reads structural_memory, identifies the cross-family invariant, and emits it as a constraint into derived_constraints.json alongside the existing process-layer entries.

This is the discriminating experiment the seam needed. The premise holds: a structural constraint was retrievable from sandbox_07 alone and would have short-circuited the need for the sandbox_08 structural_misfit hint at the cost of one function call per run.

---

## What "Constraint" Means Here

A constraint, for purposes of this seam, is a three-part object:

1. **A have-to-believe statement** — the positive inversion of the observed failure mode. Not "power-law families fail" but "any valid model MUST introduce a compositional step outside the multiplicatively-separable skeleton `A·φ^α·ψ^δ·f(·)+c`." Inversion is decisive: a have-to-believe form is actionable by the next candidate, while a ruled-out form is merely archival.
2. **Provenance** — the specific artifact(s) that certified the constraint. For structural constraints: which structural_memory entries support it, with the cross-family invariant that all share. For process constraints: which debate log line and which iteration. No entry without citation.
3. **Version + confidence** — the evidence surface hash the constraint was certified against, a confidence tag (provisional / confirmed), and the number of independent failures that support it. Constraints are not immutable: they can be downgraded, retracted, or re-certified on a later evidence surface.

A constraint is **not** a failed draft, a score drop, or a paraphrase of a weakest-point critique. It is the structural or compliance lesson extracted from *why* those things happened.

---

## Proposed Architecture

Two layers inside Component A (deterministic skeleton extraction + taxonomic diagnostic classification), plus a deferred Component B for cross-run accumulation.

### Component A.1 — Deterministic Skeleton Extractor

A single function that runs at iteration close, reads `structural_memory.json`, and finds the mathematical skeleton shared by all failed families. No LLM in this layer — pure tree-pattern matching over the normalized `family_label` strings that structural_memory already produces.

Contract:

```
extract_shared_skeleton(
    structural_memory: dict,    # current state of structural_memory.json
    confidence_threshold: int = 3,  # min failed families sharing the skeleton
) -> SharedSkeleton | None
```

Logic:

1. Read every family in structural_memory with `latest_diagnostic_classification == "structural_misfit"` and a residual above the failure threshold.
2. Parse each `family_label` as a Python AST (after normalizing the `N(...)` primitive marker to a callable name, and substituting parameter placeholders `P0..Pk, X0..X1, CONST` with fresh identifiers).
3. Compute the pairwise AST intersection across all failed families: the maximal subtree shared from the root. Differing subtrees are replaced with a wildcard marker `?`.
4. If ≥ N families (N = 3 default) share a non-trivial skeleton (≥ K operator nodes, K = 4 default — vetoes "all families have `+c`" as a trivial invariant), return the skeleton plus the fingerprints of the supporting families.
5. Otherwise return None. Do not emit a constraint on weak evidence.

**Why deterministic:** for sandbox_07's family_label format (`P0 * X0 ** P1 * X1 ** P2 * N(...) + P4`), tree-pattern matching has zero hallucination surface. Every family is already serialized by the fit pipeline into a normalized form. The skeleton is recoverable by parsing.

**Why this alone is not enough:** the skeleton tells you *what* is invariant across failures. It does not tell you *why* the skeleton fails against the evidence. A constraint that says "differ from skeleton X" is correct but thin — the mutator needs to know in *what direction* to differ. That is Component A.2's job.

### Component A.2 — Taxonomic Diagnostic Classifier

A second layer — this one an LLM call, but rigidly constrained — that takes the skeleton from A.1 and classifies it against a fixed diagnostic schema, then emits the actionable have-to-believe constraint. The LLM does not discover the invariant (that's A.1's job, deterministically). The LLM's only job is classification against pre-specified axes.

The schema (adapted from Gemini's follow-up and kept rigid to minimize hallucination surface):

```
class StructuralDiagnostic:
    variable_coupling: Literal[
        "separable",          # phi, psi appear in independent multiplicative factors
        "ratio_coupled",      # phi/psi or psi/phi coupling
        "product_coupled",    # phi*psi coupling in inner composition
        "compound_nonlinear", # phi, psi combined via a non-ratio non-product form
    ]
    asymptotic_behavior: Literal[
        "unbounded_growth",   # grows without limit as variables → large
        "exponential_decay",  # decays exponentially in a combined variable
        "polynomial_decay",   # decays polynomially in a combined variable
        "saturates",          # approaches a finite limit
    ]
    error_geometry: Literal[
        "tail_dominated",     # residuals concentrated at high values
        "origin_dominated",   # residuals concentrated at low values
        "midrange_dominated", # residuals concentrated in the interior
        "uniform_structured", # structured residual across the full domain
    ]
    have_to_believe: str      # the positive inversion, < 300 chars, must reference one of the three axes as the directional signal
```

Contract:

```
classify_skeleton(
    skeleton: SharedSkeleton,
    residual_diagnostics: list[dict],   # from fit_result.json residual_diagnostic fields
    evidence_summary: str,              # short description of where the evidence lives in the domain
    model: str = "gemini-flash",
) -> StructuralDiagnostic
```

The LLM prompt instructs the model to:
1. Look at the skeleton A.1 produced.
2. Look at the residual_diagnostics from the last N iterations (already stored per fit_result).
3. Choose one value per axis from the fixed enum. No free text for the classification fields.
4. Emit the `have_to_believe` as a positive requirement that names at least one of the three axes as the failure direction.

Example expected output for sandbox_07:
```
{
  "variable_coupling": "separable",
  "asymptotic_behavior": "exponential_decay",
  "error_geometry": "tail_dominated",
  "have_to_believe": "Any valid model MUST introduce compound (non-separable) coupling between phi and psi in the inner composition. Evidence: all failed families use separable multiplicative coupling and produce tail-dominated structured residuals."
}
```

**Why this is safer than "find the invariant":** the LLM is not generating the invariant and is not free-form characterizing the failure. The invariant is already determined by A.1. The LLM classifies against fixed axes with fixed enums. Hallucination surface is bounded to (a) picking the wrong enum, which is detectable by inspection, and (b) the final have_to_believe string, which must cite one of the chosen axes. If the have_to_believe does not name any of the three classified axes, it is rejected and regenerated.

**Why the enums are rigid:** if the classifier is allowed to invent taxonomy categories ("the model fails because of nonlinear growth asymmetry in the inner term"), it will drift toward plausible-sounding but unactionable statements. Fixed enums force the output into a shape the mutator can act on.

**Validation gate:** before the constraint is written to derived_constraints.json, run a consistency check: the `have_to_believe` string must contain lexical evidence of at least one of the three classified axes (e.g., if `variable_coupling = "separable"`, the string must mention coupling, separable, compound, or an equivalent). Fail-closed if the check fails — do not emit the constraint.

### Component A pipeline summary

```
1. extract_shared_skeleton(structural_memory)  →  SharedSkeleton | None   [deterministic]
2. if skeleton is None: return (no constraint emitted this iteration)
3. classify_skeleton(skeleton, residual_diagnostics, evidence_summary) → StructuralDiagnostic   [LLM, rigid schema]
4. validate_consistency(StructuralDiagnostic)  →  bool  [fail-closed]
5. if valid: write constraint into derived_constraints.json with producer=structural_extractor
6. mutator reads derived_constraints.json on next iteration and acts on the constraint as a have-to-believe prior
```

**Why this is minimal:** no new file, no new pipeline, no new prompt surface. Component A is two functions that read one existing artifact and write to another existing artifact. It uses the existing constraint flow into the mutator. It does not modify the judge, the adversarial review committee, or the loop.

**Why this is decisive:** the sandbox_07 retroactive test proved that the structural lesson is latent in structural_memory but never surfaces. Adding this two-layer extraction pass changes the mutator's input on the next iteration and unblocks search paths the sequential loop would otherwise never reach.

**Why Gemini's "have-to-believe" framing is kept:** the output is always in positive form ("must introduce compound coupling"), never in negative form ("this family was tried and failed"). This matches the mutator's natural instruction-following — it can act on a positive requirement while a ruled-out list is only a constraint by implication.

**Why Gemini's "immutable physical law" framing is rejected:** constraints can be wrong. A false skeleton extraction or a misclassification can produce a constraint that blocks valid search paths. Solution: constraints are versioned against evidence_hash, confidence-tagged, and auto-downgraded when a candidate that violates the constraint scores higher than the current champion. The mutator treats them as strong priors, not hard blocks.

### Component B — Cross-Run Constraint Accumulator (deferred)

A project-level or hypothesis-family-level accumulator that persists constraints across runs. Each new run writes new constraints, reads prior constraints as context, and the mutator does not re-propose hypotheses that violate high-confidence accumulated constraints.

This is where the architecture actually compounds across runs: the mutator's search space shrinks each run, and the operator sees cumulative progress in terms of hypothesis space reduction.

**Deferred because:** Component A must first prove it extracts real structural lessons and not noise. If Component A fires reliably across 3–5 projects without producing false-skeleton constraints, Component B becomes the natural next step. If Component A produces noisy or wrong constraints, Component B would compound the noise across runs.

### What is explicitly not in this seam

- **Judge/adversarial review committee constraint emission** (Gemini's original form). The existing process-constraint harvester already does this via meta_judge and committee paths into derived_constraints.json. Adding more to that layer is duplicative. The structural lesson is missed at the structural_memory layer, not at the judge layer — that is where GP-061 intervenes.
- **Full output inversion** (Component C from the prior seam draft). Champion thesis remains the primary run output. The accumulated constraint set is an additional artifact, not a replacement.
- **Cross-domain transfer** (constraints learned in Planck transferring to Hungary). Out of scope by structural difference between fit-primitive and bounded-discriminator projects.
- **Changes to the evaluation layer.** adversarial review committee, meta-judge, and debate format unchanged.

---

## Failure Modes to Test

1. **False skeleton extraction.** Component A fires on 3 families that share a trivial skeleton (e.g., "all have a `+c` additive constant") and emits a vacuous have-to-believe constraint. Gate: the shared skeleton must have non-trivial structure (≥ K operator nodes, configurable). A single additive constant is not a skeleton.

2. **Structural constraint that is actually correct but blocks the truth.** The extractor emits "models must differ from the shared skeleton at the outer composition" and the true ground-truth model *does* share that outer skeleton with a specific inner variant the mutator hasn't tried. Mitigation: the constraint is a strong prior, not a hard block. The mutator can violate it if the violation is justified and the judge accepts the justification. Any candidate that violates a structural_extractor constraint and scores higher than the current champion causes the constraint to be automatically downgraded from provisional to retracted.

3. **Provenance drift.** The extractor cites families F1..Fn, but a later structural_memory update invalidates one of the cited families (re-classification from structural_misfit to parametric_noise). Gate: constraints re-validate their provenance on each run close. Invalidated cited families get replaced or, if insufficient support remains, the constraint drops to provisional or is retracted.

4. **Constraint explosion.** Component A fires too often and floods derived_constraints.json. Gate: rate-limit — at most one structural_extractor constraint emitted per iteration, and only if it dominates the structural_memory (covers ≥ floor(n/2) of active failed families). Less-covered skeletons wait for additional evidence.

5. **Mutator ignores structural constraints.** The constraint is written correctly but the mutator prompt doesn't surface structural_extractor entries distinctly enough for the LLM to act on them as priors. Mitigation: structural_extractor constraints render at the top of the derived_constraints injection block with explicit framing ("the following are structural have-to-believe requirements based on the invariant failure mode of prior families").

---

## Discriminating Experiment

**H-ARCH-02 (revised after retroactive test):** Running Component A against sandbox_07's closed `workspace/structural_memory.json` surfaces a non-trivial have-to-believe constraint on the outer skeleton of the candidate expression family, and that constraint corresponds to the structural lesson that sandbox_08 is currently trying to surface via the hardcoded `_STRUCTURAL_MISFIT_HINT_TEMPLATE`.

**Success criteria:**

1. Component A, run against sandbox_07 closed artifacts, emits at least one structural_extractor constraint of the form "any valid model must differ from the multiplicatively-separable skeleton `A·φ^α·ψ^δ·f(·)+c` at the outer composition."
2. The emitted constraint cites ≥ 3 sandbox_07 families as provenance.
3. The constraint is stated as a have-to-believe (positive inversion), not as a ruled-out list.

**If H-ARCH-02 holds:** the structural_misfit hint in sandbox_08 is a workaround for a missing extraction pass. GP-061 Component A subsumes it by generalizing the extraction from one hardcoded skeleton to any skeleton that the extractor identifies as an invariant across failed families.

**If H-ARCH-02 fails:** Component A does not extract the intended constraint from sandbox_07. In that case either the extraction logic needs a different approach (e.g., LLM-based structural summarization instead of tree-pattern matching) or the signal is genuinely not retrievable from structural_memory alone and the sandbox_08 hint remains the correct intervention.

---

## Relationship to Existing Apparatus

- **derived_constraints.json (existing process harvester):** unchanged. Component A adds structural constraints to the same file under a new producer tag. Both layers coexist.
- **structural_memory.json (existing family tracker):** unchanged. Component A is a reader, not a writer.
- **structural_misfit hint (sandbox_08):** GP-061 subsumes this if H-ARCH-02 holds. The hardcoded template becomes unnecessary because the extractor emits the same constraint from the structural_memory directly.
- **GP-060 parallel champion synthesis:** complementary. GP-060 handles positive claim coverage (K workers explore thesis space). GP-061 handles negative claim coverage (structural invariant across failures → have-to-believe constraint). Together they bracket the search.
- **GP-031 findings bridge:** GP-061 is the negative-space analogue. Shared infrastructure where possible (both write into run closure; both versioned against evidence surface).
- **GP-042 structural memory:** this seam is the downstream reader that gives structural memory a linguistic output. GP-042 produces the data, GP-061 produces the findings.

---

## Open Questions Before Implementation

1. **Tree-pattern vs LLM for skeleton extraction.** Tree-pattern matching is deterministic and cheap but brittle if the structural_memory family_label format varies. LLM extraction is flexible but introduces hallucination risk. Default: tree-pattern first (the family_label format is already normalized — `P0 * X0 ** P1 * X1 ** P2 * ...`), with an LLM fallback path gated behind explicit invocation.
2. **Where does Component A run?** Post-iteration-close hook in autoresearch_loop, co-located with the existing derived_constraints writer. One function call per iteration close.
3. **Confidence threshold N.** Start at N=3 (three failed families sharing a skeleton before emission). Sandbox_07 had 10 families sharing the same outer skeleton, so N=3 is conservative for that dataset. Validate against other closed sandbox projects.
4. **How to format the constraint for mutator injection.** structural_extractor constraints should render distinctly from process constraints. Proposed: a separate section in the derived_constraints prompt block titled "structural requirements (inferred from repeated failure of this skeleton across N families)." Kept separate so the mutator does not confuse process compliance with structural necessity.
5. **When to downgrade a structural constraint.** If a candidate that violates the constraint scores higher than the current champion, the constraint is auto-downgraded to provisional and the violating candidate's outer skeleton replaces the prior structural prior. This is the automatic self-correction path that prevents immutable-law failure modes.

---

## Overfitting Defense Audit (added 2026-04-14)

Prompted by the legitimate concern: "if we use empirical failures to permanently prune the search space, aren't we overfitting to the apparatus's own incompetence?" This section names which guards actually fire in the shipped code and which were missing before this audit.

### Guards already in code before this audit

1. **Provisional → confirmed gate.** `derived_constraints.update_derived_constraints_ledger` requires `seen_count_runs ≥ 2` across **distinct runs** before a constraint promotes from provisional to confirmed. A single sandbox_07 run cannot by itself push a structural_extractor constraint into the mutator prompt.
2. **Advisory rendering.** `render_confirmed_constraints_prompt_section` only reads the `confirmed_constraints` bucket. Provisional constraints are logged to `derived_constraints.json` but never injected into the mutator prompt. The injected text explicitly says *"These are NOT primary evidence. Your thesis may comply with them directly or explicitly argue non-applicability with justification."* The prior is read-only, not a hard filter.
3. **Non-applicability clause.** Every proposal carries a `non_applicability_condition` string. For structural_extractor proposals this includes an explicit auto-downgrade escape hatch: *"If a candidate that violates this skeleton scores strictly higher than the current champion, the constraint is auto-downgraded."* The mutator is instructed it can argue its way out per-iteration. This is a softer, continuously-available version of retraction.
4. **Severity gradations.** structural_extractor proposals are emitted with `severity="blocking"` for the negative-inversion case, but the rendered prompt section does not distinguish severities — all confirmed constraints print with the same READ-ONLY framing. So severity is advisory-only at the mutator surface.

### Gap that existed before this audit

The non-applicability clause in §Guards 3 was documentation, not code. There was no enforcement path — nothing actually demoted a confirmed constraint if the loop kept stagnating under its prior. Gemini's "Retraction Protocol" framing is reasonable; the current code lacked the mechanism.

### New mechanism added 2026-04-14

`derived_constraints.downgrade_constraints_on_stagnation(...)` — narrow, opt-in retraction:

- Acts **only** on producers in `DOWNGRADABLE_PRODUCERS = {"structural_extractor", "trajectory_extractor"}`. Judge-produced constraints (meta_judge, committee, adjudicator) are never touched by stagnation downgrade; their provenance is human-debate-adjacent and not subject to incompetence-overfit risk.
- Fires only when `stagnation_count ≥ threshold` (default `6`, deliberately higher than Gemini's proposed `4` to avoid retracting too eagerly; the loop should be genuinely starved, not just slow).
- Demotes the most-recently confirmed entry back to provisional, records a `downgrade_history` entry with timestamp/stagnation_count/threshold/reason, and re-indexes `DC-???` / `PC-???` IDs.
- **Mechanism only — not auto-wired.** Deliberately not called from `_refresh_derived_constraints_from_eval`. The caller (loop control / emergency-pivot path) owns the trigger decision. This keeps stagnation-count semantics out of the ledger module and lets us ship the retraction mechanism without introducing a new automatic behavior in live runs.

### What is still not defended

- **Feature-selection bias** (applies to GP-062, not GP-061 directly). GP-061's skeleton extraction reads features that *emerge from the data*. GP-062's trajectory detector reads features the human chose. See GP-062 seam §Feature-Set Bias.
- **Cross-domain transfer.** A structural constraint confirmed on two fit-primitive runs has no defense against being injected into a non-fit-primitive run. Component B (cross-run accumulator) will need a domain fingerprint to gate this.
- **Prompt-budget amplification.** Every confirmed constraint costs mutator context. An unbounded ledger will eventually starve the primary thesis prompt. Not addressed here.

### Language discipline

The prompt-rendered framing must stay `"adversarially surfaced"` and `"NOT primary evidence"`, not `"immutable physical law"` or `"proven constraints"`. The Gemini framing `proven_constraints.json` was rejected on that ground and is not adopted.

---

## Sandbox_08 Live Observation (2026-04-15)

First live run of GP-061's hook. Results validated the conservative-refusal behavior:

- Hook fired every iteration (14 iters in `iteration_telemetry.jsonl`).
- `derived_constraints.json` shows `0` entries with `producer=structural_extractor`. Zero emissions across the run.
- Not a hook failure — a correct refusal. `structural_memory.json` had 12 families: 8 `structural_misfit`, 4 `outlier_dominated`. The feature-bag intersection across the 8 structural_misfit families collapsed below `min_operator_nodes=4` because sandbox_08's families genuinely varied the outer skeleton more than sandbox_07's.
- The overfitting-defense audit predicted exactly this shape: if the mutator actually varies the skeleton, the extractor refuses to emit a constraint it cannot support with ≥4 invariant features. Good conservatism.

The single-run provisional gate never had to engage because nothing was emitted to gate. Defense held at the upstream extractor layer instead of the downstream ledger layer. Both layers still in place for the next run.

---

## Component B — Negative-Space Extractor (GP-061.B)

Added 2026-04-15 as a sibling detector, not a modification of Component A.

### Why a second component

Sandbox_08's end-to-end debug (see `GP-023_planck_sandbox_08_closure.md` §Score-starvation root cause) identified a *feature-bag completeness gap*: the mutator systematically avoided nesting a power operator inside the first argument of `eml(...)`, across all 12 candidates. Component A could not emit on this because its semantics are positive-space (intersect features *present* across failed families). A missing feature is, by definition, not in any family's bag, and therefore not in the intersection.

Gemini's initial proposed fix — hand-add `eml_arg0_has_power` to `SKELETON_FEATURE_PREFIXES` — was rejected as a weaker form of the same leakage the prompt-hint fix was rejected for: if the human chooses which feature name to look for, the detector is not discovering the blind spot, it is confirming what the human already knew. The principled alternative is a **mechanical feature vocabulary** that enumerates features without human pre-selection, paired with a **negative-space reader** that fires on absence rather than presence.

### Architecture

Two additions:

1. `structural_constraint_extractor.extract_generalized_feature_matrix(tree)` — new function, additive. For every `Call` node in the AST, for every argument position, it walks the argument subtree and emits:
   - `fn:{fname}|arg{i}|has_op:{OP}` — operator `OP ∈ {Pow, Mult, Div, Add, Sub, USub, Call}` appears anywhere in that argument's subtree.
   - `fn:{fname}|arg{i}|depth:{d}` — max operator-chain depth bucket.
   - `fn:{fname}|arg{i}|leaf` — the argument is a bare `Name`/`Constant`.
   
   The legacy `_extract_feature_bag` (decisive for Component A on sandbox_07) is left untouched.

2. `src/ztare/validator/negative_space_extractor.py` — new module, sibling of `structural_constraint_extractor.py` and `trajectory_thrash_detector.py`. Pipeline:
   - Load `structural_memory.json`, filter to `structural_misfit` families with `latest_visible_max_abs_residual >= 0.15` (same filter as Component A).
   - Run `extract_generalized_feature_matrix` over each family's `family_label` AST.
   - **Candidate universe** = for each `(fname, arg_pos)` key observed in at least one family, enumerate the cartesian product with the full operator catalog + `leaf`. No human pre-selection of which slots matter.
   - **Voids** = universe − union of all observed feature bags.
   - **Density guard:** only report voids at keys where `≥ MIN_FILLED_SLOTS_PER_KEY=2` distinct slots are filled in the corpus. This is the defense against "features no one tried because they're gibberish" — if a key has only one filled slot, absence of others is not informative.
   - Emit a single `derived_constraints.json` proposal with `producer="negative_space_extractor"`, `failure_family="negative_space_blind_spot"`, `severity="degrading"`, listing all dense voids and requiring the next candidate to fill at least one unless ruled out by grammar/physics.

### Cold-test results on sandbox_07 and sandbox_08

Gating rule before live wiring (user directive): *"the Taxonomic LLM must natively synthesize the 'explore nested power' Have-to-Believe constraint based solely on the negative-space vector."* Interpreted as: the detector must surface the power-nesting blind spot on the sandbox_08 corpus **mechanically**, without any string I typed matching a feature I know is in GT.

**Sandbox_08 (family_count=8, universe_size=16):**
```
fired: True
void features:
  EMLCALL(arg0|has_op:Add)
  EMLCALL(arg0|has_op:Call)
  EMLCALL(arg0|has_op:Pow)    <-- the power-nesting blind spot, surfaced mechanically
  EMLCALL(arg0|has_op:Sub)
  EMLCALL(arg0|has_op:USub)
  EMLCALL(arg0|leaf)
  EMLCALL(arg1|has_op:Sub)
  EMLCALL(arg1|has_op:USub)
```
`arg0|has_op:Pow` is in the void list. The detector read the corpus and reported that across 8 failed families, not one nested a `Pow` operator inside `eml`'s first argument. This matches the power-nested GT shape `eml((gamma*phi/psi)**q, math.e)` without any human knowledge of GT flowing into the feature vocabulary — `_GENERALIZED_OPS` and the arg-position enumeration are mechanical.

**Sandbox_07 (family_count=12, universe_size=16):**
```
fired: True
void features:
  EMLCALL(arg0|has_op:Add)
  EMLCALL(arg0|has_op:Call)
  EMLCALL(arg0|has_op:Sub)
  EMLCALL(arg1|has_op:Add)
  EMLCALL(arg1|has_op:Pow)
  EMLCALL(arg1|has_op:Sub)
  EMLCALL(arg1|has_op:USub)
```
**`arg0|has_op:Pow` is NOT in the sandbox_07 void list.** Sandbox_07's mutator *did* exercise power operators inside `eml`'s first argument (sample label `N(P1 * X0 ** CONST / (P3 * X1 ** CONST), math.e)`). This is a material asymmetry — the detector is reading the two corpora as having genuinely different coverage gaps, not firing on a universal Planck-family void. This matches the closure-note observation that sandbox_08 varied its outer skeleton more and its inner `eml` argument less than sandbox_07.

### Why the asymmetry matters

- Component A (positive-space) fires on sandbox_07 because the shared-feature intersection is dense enough — outer skeleton invariants carry the signal.
- Component B (negative-space) fires on sandbox_08 because the shared-feature intersection is sparse but the coverage gap is concentrated at a single arg-position.
- Each sandbox is diagnosed by exactly one of the two components. **Complementary, not redundant.** That justifies keeping them as parallel siblings instead of collapsing them into one schema.

### Rollout discipline

Cold-retroactive test = passed, by the gating rule above.

**Status 2026-04-15: promoted `open → confirmed` for live emission on fit-primitive projects that clear the GP-069 level-1 nesting-audit gate.** Promotion gate cleared by: (a) R3b curated-harvest pass on sandbox_10 (Kepler vis-viva, `GP-023_sandbox_10_post_run_audit.md`, Outcome A); (b) R4 retrospective consistency check on sandbox_07 and sandbox_08 closed Planck harvests (`GP-061_R4_retrospective_audit.md`, dual pass). R4's v4-amendment Div claim was retracted mid-audit — the correct polarity criterion is the Pow-filled-on-07 / Pow-void-on-08 asymmetry at `EMLCALL|arg0`, which matched exactly.

The hook is wired unconditionally at `autoresearch_loop._refresh_derived_constraints_from_eval` lines 1013–1051, gated only by the opt-out flag `--disable-negative-space-extractor`. Cold-run verification 2026-04-15 on gp042_structural_memory_01 and gp045_cold_residual_01 confirms the detector fires correctly across distinct projects within the Planck grammar family (same `math.exp / X0 / X1` vocabulary as sandbox_07/08, different run contexts) — `fn:exp|arg0|has_op:{Add, Call, Div, Sub}` voids emitted cleanly, density guard respected. This is **within-grammar** portability evidence, not cross-grammar: gp042 and gp045 share the Planck primitive family. The only cross-grammar capability evidence remains sandbox_10's R3b curated-harvest pass on the `math_power_only` / `sqrt / pow` axis.

**Implication for live-mutator cross-grammar validation.** The repo currently has no live-mutator fit-primitive project outside the Planck grammar axis that clears GP-069 level 1. Such a target must be **constructed** (task #55) before live-mutator cross-grammar evidence can exist. Until then, cross-grammar claims route through the R3b curated-harvest protocol only.

**What promotion does not authorize:** (a) live wiring on grammar-nesting-closed targets (see GP-069 level-1 pre-seal checklist); (b) promotion to the `confirmed_constraints` bucket from a single run — the existing `seen_count_runs ≥ 2` distinct-run gate still governs prompt injection; (c) non-fit-primitive domains (hormuz, hungary, eu_union, etc.) — those projects have no `structural_memory.json` and the detector silently no-ops, which is correct behavior.

### What Component B does NOT defend against

- **Noise voids.** If a key is dense on the filled side (many slots filled) but one slot is absent, Component B will flag it even if the absence is physically meaningful (e.g., `arg1|has_op:USub` — negating the second argument of `eml` is syntactically legal but semantically rare). The Taxonomic LLM (or a human auditor, until the LLM path is wired) is the second filter that decides whether a surfaced void is actionable or coincidental.
- **Grammar-ruled-out voids.** Some voids are forbidden by the declared grammar (e.g., `arg1|has_op:Call` might be disallowed in a restricted primitive grammar). The `non_applicability_condition` clause explicitly routes these to the grammar spec and `project_charter.md` declarations.
- **Cross-run absence.** Component B reads a single project's corpus. A feature absent in one project but present in another is handled by the confirmed-bucket promotion gate (`seen_count_runs >= 2`), which is inherited from the existing ledger machinery — no new mechanism needed.

### Open questions deferred to post-sandbox_09

- Whether the density guard threshold (`MIN_FILLED_SLOTS_PER_KEY=2`) is right. Sandbox_07 and sandbox_08 both clear it comfortably; a sparser corpus might not.
- Whether to wire an LLM taxonomic step that converts the raw voids list into a prose have-to-believe. Currently the deterministic path emits a structured bullet list. Good enough for cold testing; may need LLM prose when injected into the mutator prompt.
- Whether `depth:{d}` features should be part of the void universe. Currently only `has_op:*` and `leaf` slots are in the universe; depth features are reported in the feature bag but not scanned for absence. That keeps the universe finite and interpretable but may miss "nobody ever built a depth-3 argument" blind spots.
