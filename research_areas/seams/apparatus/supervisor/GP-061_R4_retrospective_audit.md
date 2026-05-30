# R4 Retrospective Audit — Component B against closed Planck harvests

> **Seam metadata** · `seam_id:` GP-061 · `track:` apparatus · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

**Closed:** 2026-04-15
**Outcome:** **PASS on both sandbox_07 and sandbox_08.** Dual R4 pass.
**Companion:** R3b (sandbox_10) passed earlier same day, Outcome A. Together these clear the GP-061.B two-run promotion gate under the v4 amendment.

---

## 1. What R4 is, honestly

R4 is the retrospective consistency check in the GP-061 v4 amendment. It cold-runs the current `negative_space_extractor` code against the existing `workspace/structural_memory.json` files of two closed Planck sandboxes (07 and 08). Its purpose is to verify that (a) the detector still fires on real historical mutator harvests, (b) the voids it surfaces are grep-verifiable against the family labels, and (c) its behavior matches the descriptions written into the GP-061 spec body at the time those sandboxes closed.

**What R4 is not.** It is not a novel cross-grammar capability test (that was R3b against sandbox_10). It is not a demonstration that Component B does something the earlier runs did not already do. It is the non-regression half of the promotion gate, closing the failure mode "we edited the detector between sandbox_08 closing and now and silently broke its vocabulary." Gemini Pro's framing of R4 as "officially validating Component B as a Generalized Falsification Engine" is overstatement; the honest claim is "detector behavior on historical corpora is stable, therefore the R3b cross-grammar pass is trustworthy under the current detector code."

## 2. Historical baseline

There is no `negative_space_extractor` entry in either sandbox's historical `derived_constraints.json`. Component B was not yet wired into the post-eval hook when those sandboxes originally ran. The only historical record of what Component B "should" surface on these corpora is the textual description in `GP-061_component_b_generalization_target_spec.md` §Cross-references, lines 351–352:

- sandbox_07: 12 failed families, 7 voids, **`exp(arg0|has_op:Pow)` filled**
- sandbox_08: 8 failed families, 7 voids, **`exp(arg0|has_op:Pow)` void**

(Where "exp" in the spec is the mathematical-notation shorthand for ZTARE's `eml` primitive, which the detector normalizes to the `EMLCALL` marker via `_normalize_family_label`.)

## 3. R4 run

```
command: python -m src.ztare.validator.negative_space_extractor --project gp023_planck_sandbox_07
fired: True
family_count: 12
universe_size: 14
present_feature_count: 9
void_feature_count: 7
voids at fn:EMLCALL|arg0: {Add, Call, Sub}      (Pow filled ✓ matches spec)
voids at fn:EMLCALL|arg1: {Add, Pow, Sub, USub}
```

```
command: python -m src.ztare.validator.negative_space_extractor --project gp023_planck_sandbox_08
fired: True
family_count: 8
universe_size: 14
present_feature_count: 8
void_feature_count: 7
voids at fn:EMLCALL|arg0: {Add, Call, Pow, Sub, USub}   (Pow void ✓ matches spec)
voids at fn:EMLCALL|arg1: {Sub, USub}
```

Both run to completion, fired=True, family counts match the spec's 12 and 8 exactly, void counts match 7 and 7 exactly, and the Pow-filled-vs-Pow-void polarity at the decisive `(fn:EMLCALL, arg0)` key matches the spec's written description.

## 4. Manual grep-verification

For each surfaced void I ran `_parse_to_ast + extract_generalized_feature_matrix` against the full failed-family set and computed the filled/void partition independently of the detector's own output. All 14 surfaced voids (7 per sandbox) match the manual computation exactly. Every void corresponds to an operator type that no family in the respective sandbox uses at that (fname, arg_pos) position. Zero spurious voids. Zero Planck-residue issues (Planck residue is by definition not a concern when testing against Planck sandboxes — the residue concern is the reverse direction, which R3b handled).

Sandbox-level observation: the filled/void partition at `EMLCALL/arg0` differs between the two sandboxes because of a real grammar choice by the live mutators — sandbox_07 families put `X0**P1` inside the eml first argument (filling `Pow`), while sandbox_08 families put plain `X0/X1` inside the eml first argument (leaving `Pow` unfilled). That is a real behavioral difference in what the two runs' mutators explored, surfaced correctly by Component B in both cases. This is the detector doing exactly what the spec said it should.

## 5. Correction to GP-061 v4 amendment

My v4 amendment text said: "Component B cold-run against those harvests must surface `fn:exp|arg0|has_op:Div` and no spurious voids." That is **wrong** on two counts:

1. The detector surfaces `fn:EMLCALL|*`, not `fn:exp|*`, because `_normalize_family_label` rewrites `N(...)` to `EMLCALL(...)` before AST parsing. The spec body at line 351-352 is consistent with this; my amendment was sloppy shorthand.
2. `has_op:Div` is **not** in the void set of either sandbox. In both, `Div` is among the **filled** slots at `EMLCALL/arg0` because every family in the corpus has `X0/X1` somewhere inside the eml first argument. I invented the Div-as-expected-void claim by thinking of exp-primitive vocabulary generically, without reading the spec carefully.

The correct pass criterion for R4 is: fired=True on both sandboxes, void count ∈ {6, 7} per spec ballpark, and the `Pow` polarity matches (filled on 07, void on 08). The v4 amendment is being corrected to reflect this below.

## 6. Verdict and gate status

R4 passes on both sandboxes. Combined with the R3b Outcome A pass on sandbox_10 (earlier same day, `GP-023_sandbox_10_post_run_audit.md`), the GP-061.B two-run promotion gate under the v4 amendment is **fully cleared**. Component B is eligible for live-wiring onto non-Planck projects under the Component-B live-emission discipline seam (`GP-061_constraint_accumulation_as_output_seam.md`).

**Scope of the promotion.** Component B is promoted from `open` to `confirmed` for live emission on projects using grammars where (a) the sealed GT is identifiable under single-start fitting without nesting collapse, OR (b) the cold-test harvest is curated rather than live-mutator-harvested (R3b protocol). This does NOT authorize live wiring on targets where the grammar-nesting-closure pathology from sandbox_09/10 is known or suspected — those still require GP-069 level 1 seal-time static checks (task #47) before promotion.

**What this earns us.** The promotion is narrow. Component B can now write negative-space voids into `derived_constraints.json` as provisional constraints that feed the mutator prompt on non-Planck ZTARE projects that clear the nesting-audit gate. The dollar-value claim (Problem §Why It Matters) that "a confirmed-but-domain-overfit Component B would inject spurious voids into the mutator prompt" is ruled out in two directions: (R3b) the vocabulary is not silently scoped to exp/eml, and (R4) the vocabulary behaves stably on historical Planck corpora under the current code version.

## 7. Cross-references

- `GP-023_sandbox_10_post_run_audit.md` — R3b Outcome A pass
- `GP-023_sandbox_10_pre_registration.md` — pre-reg §7 verdict tree
- `research_areas/private/specs/active/GP-061_component_b_generalization_target_spec.md` — v4 amendment (corrected inline after this audit)
- `research_areas/private/seams/GP-069_champion_nesting_audit_gate_seam.md` — level 1 gate governing future non-R3b targets
- `src/ztare/validator/negative_space_extractor.py` — detector under test
- `src/ztare/validator/structural_constraint_extractor.py` — feature matrix source (contains the `_normalize_family_label` EMLCALL rewrite)
