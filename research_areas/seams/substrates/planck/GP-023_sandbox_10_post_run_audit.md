# Sandbox_10 (Kepler vis-viva) — Post-Run Audit

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

**Closed:** 2026-04-15
**Outcome:** **A — clean R3b capability pass** (per pre-reg §7)
**Pre-registration:** `GP-023_sandbox_10_pre_registration.md` (v1 sealed 2026-04-15)

---

## 1. What was tested

Under the R3b curated-harvest cold protocol (not the original GP-061 spec v3 mode (c) live-mutator harvest), Component B (`negative_space_extractor`) was run against a pre-sealed corpus of 5 grammar-valid wrong regression candidates for the Kepler vis-viva equation `v(r, a) = sqrt(GM * (2/r - 1/a))`. The curated harvest was frozen before the run; the expected decisive void slot `fn:sqrt|arg0|has_op:Sub` and three pre-registered ancillary voids (`Div`, `USub`, `Call` at the same key) were committed to in pre-reg §6.1 before cold-run observation.

## 2. Result

```
command: python -m src.ztare.validator.negative_space_extractor --project gp023_sandbox_10
fired: True
family_count: 3 (F1, F3, F4)
universe_size: 21
voids surfaced at (fn:sqrt, arg0):
  - has_op:Sub   — DECISIVE, matches pre-reg §6.1 expectation
  - has_op:Div   — ancillary, pre-registered
  - has_op:USub  — ancillary, pre-registered
  - has_op:Call  — ancillary, pre-registered
voids at (fn:sqrt, arg0, has_op:{Pow, Mult, Add}): NONE (density guard respected)
Planck-residue voids (fn:eml|*, fn:exp|*): NONE (clean)
```

Every surfaced void is grep-verifiable against `projects/gp023_sandbox_10/curated_harvest.json`:
- No family contains `Sub` inside `sqrt` → Sub void legitimate
- No family contains `Div` inside `sqrt` → Div void legitimate
- No family contains unary minus inside `sqrt` → USub void legitimate
- No family contains a nested call inside `sqrt` → Call void legitimate
- F3 contains `math.sqrt(X0**P1 * X1**P2)` → fills `Mult`, `Pow` → not void (correct)
- F4 contains `math.sqrt(P1 * X0**P2 + P3 * X1**P4)` → fills `Add`, `Mult`, `Pow` → not void (correct)

Zero spurious voids. Zero Planck-grammar residue. The detector's feature vocabulary generalized cleanly from the `exp`/`eml` corpora of sandbox_07/08/09 to the `sqrt`/`pow` corpus of sandbox_10 without silent template leakage.

## 3. Verdict tree mapping

Pre-reg §7 Outcome A requires all four of:

1. `(fn:sqrt, arg0, has_op:Sub)` is in the surfaced void set → **YES**
2. No Planck-vocabulary slot appears → **YES**
3. Every surfaced void is grep-verifiable against the harvest → **YES**
4. No spurious void surfaces for `(fn:sqrt, arg0, has_op:{Pow, Mult, Add})` → **YES**

Pre-registered ancillary voids `{Div, USub, Call}` are explicitly allowed under §7 Outcome A without downgrade to B. All four ancillaries surfaced exactly as predicted.

Verdict: **Outcome A**. Sandbox_10 passes R3b.

## 4. Promotion gate status

The GP-061.B two-run promotion gate (pre-reg §7) requires BOTH:

1. Sandbox_10 R3b passes Outcome A or B → **DONE (Outcome A)**
2. Retrospective R4 check passes on sandbox_07 and sandbox_08 closed Planck harvests — Component B cold-run against those harvests must surface `fn:exp|arg0|has_op:Div` and no spurious voids → **PENDING**

Component B is NOT yet live-wired onto non-Planck projects. The R4 retrospective is the remaining half of the gate (tracked as downstream work).

## 5. Caveats

- **Tautology risk acknowledged.** Per pre-reg §2 and independent-review C5, the curated harvest was constructed to have `(fn:sqrt, arg0, has_op:Sub)` conspicuously absent by design. The detector is mechanically guaranteed to surface this slot once the density guard engages. A passing run demonstrates: the parser ingests `math_power_only` labels; the feature vocabulary is not silently scoped to `exp`/`eml`; the density guard fires correctly; no Planck residue leaks into void output. **It does NOT demonstrate that a live mutator would produce a harvest from which Component B could recover the same void.** That stronger claim is ruled out for sandbox_10 by the nesting-collapse pathology (`GP-023_sandbox_10_nesting_collapse_audit.md`) and remains open for future sandbox families where the identifiability/nesting interaction is more forgiving.

- **F2 and F5 are carried in the harvest file as nominal grammar-diversity markers but do not contribute to the cold-run feature-bag corpus** because their labels use `**` (BinOp(Pow)) with no `math.*` call node, producing empty feature bags that are dropped by the detector. F1 was corrected at seal time from `**` form to `math.pow` form (pre-reg §8.1 F1 correction log) to ensure ≥3 families reach the density guard. The effective cold-run corpus is {F1, F3, F4}.

- **F1 correction was post-smoke-test and pre-verdict**, disclosed transparently in pre-reg §8.1. The decision tree and expected voids were unchanged. A more adversarial reviewer could still flag this; the honest mitigation is full disclosure and a lesson-learned entry requiring seal-time bag-non-empty dry runs for future curated harvests (added to `docs/PRE_RUN_CHECKLIST.md`).

- **The run is narrow capability evidence, not apparatus-level validation.** Per `docs/IS_THIS_A_BREAKTHROUGH.md` §4, this is a Component-B-generalization datapoint in a well-posed test, not a demonstration of live symbolic-regression discovery.

## 6. What it rules out and what it does not

**Ruled out:** the hypothesis that Component B's feature-bag vocabulary is secretly specific to `exp`/`eml` grammar and would surface template residue (or no voids at all) when pointed at a `sqrt`/`pow` harvest. If that were true, the detector would either (a) emit `fn:exp|*` or `fn:eml|*` voids, or (b) fail to engage the density guard at the `(fn:sqrt, arg0)` key. Neither happened.

**Not ruled out:** that Component B would successfully surface expected voids on a harvest produced by a real mutator under sandbox_10 grid conditions. The nesting-collapse audit already established that such a harvest would be empty (the mutator fit-collapses to GT at iter 1), so this question is not testable on sandbox_10 under mode (c) and is ruled out by construction, not by a run.

## 7. Cross-references

- Pre-registration: `research_areas/private/seams/GP-023_sandbox_10_pre_registration.md`
- Nesting-collapse audit (ruled out mode (c)): `research_areas/private/seams/GP-023_sandbox_10_nesting_collapse_audit.md`
- Parent spec (pending v4 amendment): `research_areas/private/specs/active/GP-061_component_b_generalization_target_spec.md`
- Downstream R4 retrospective: task #48 (spec v4 amendment includes R4 protocol)
- Independent review notes: see conversation log 2026-04-15 (ruthless third-party pass)
- Paired promotion-gate condition: R4 cold-run of Component B against sandbox_07 and sandbox_08 closed harvests
