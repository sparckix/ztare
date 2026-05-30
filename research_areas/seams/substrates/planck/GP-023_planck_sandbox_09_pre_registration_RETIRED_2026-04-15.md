# GP-023 Planck Sandbox 09 — Negative-Space Extractor Clean Re-Run — Pre-Registration

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` unrecorded · `last_updated:` 2026-05-08


Status: **SEALED 2026-04-15**
Drafted: 2026-04-15
Hypothesis family: H-SP2-06 (negative-space coverage axis — GP-061.B live emission)
Predecessors:
  - sandbox_06 (calibration — closed)
  - sandbox_07 (eml grammar blind run — closed Outcome A-apparatus / B-mutator)
  - sandbox_08 (diagnostic-feedback axis — closed Outcome D, score=0 across 14 iters)

---

## Purpose

Sandbox_08 established two things:
1. Apparatus is still healthy: the end-to-end debug (sandbox_08 closure note §Score-starvation root cause) plugged the ground-truth form into the live harness and scored all 9 gates at machine precision. The gate battery is not broken.
2. The mutator, under the eml-only grammar, has a *feature-bag completeness gap*: across 12 failed candidates, not one nested a power operator inside the first argument of `eml(...)`. Component A (positive-space structural extractor) could not emit on this because its semantics intersect present features, not absent ones.

GP-061 Component B (negative-space / void extractor) was built post-sandbox_08 as the missing reader. Cold-tested retroactively on sandbox_07 and sandbox_08 (GP-061 seam appendix). Cold-test result:
- Sandbox_07 (12 failed families, universe=16): fires. `arg0|has_op:Pow` NOT in voids — sandbox_07's mutator did exercise Pow inside the first argument. Voids surface `arg1|has_op:Pow`, `arg0|has_op:{Add, Sub, Call}`, etc.
- Sandbox_08 (8 failed families, universe=14 after the `leaf`-scrub fix): fires. `arg0|has_op:Pow` IS in voids — the power-nesting blind spot, surfaced mechanically by the AST matrix extractor with no human feature pre-selection beyond the Python arithmetic BinOp set.

**Sandbox_09 tests whether Component B fires on a live run under the standard provisional-only ledger discipline**, and — simultaneously — whether the mutator under the eml-only grammar, on a clean third attempt at the same problem, converges without any hint injection. The retired `_STRUCTURAL_MISFIT_HINT_TEMPLATE` is removed end-to-end from `autoresearch_loop.py` and is not re-introduced here.

---

## Primary Hypothesis (H-SP2-06)

Under the eml-only grammar, with no hint injection, with Component A, Component B, and GP-062 trajectory thrash all live and writing provisional-only, gemini-pro's champion trajectory on sandbox_09 is structurally indistinguishable from sandbox_07's — the mutator still does not nest a power operator inside `eml(...)`'s first argument, Component B fires and writes one or more provisional void entries into the ledger, and the champion does not clear all 9 gates within the iteration budget. Sandbox_09 therefore serves as a *second* live datapoint for Component B (the first being the cold retroactive test on sandbox_08), qualifying the producer for provisional→confirmed promotion on the next run (sandbox_10) under the standard `seen_count_runs >= 2` gate.

**Why a null-style primary hypothesis.** Sandbox_07 and sandbox_08 both closed score=0 with the same mutator and the same grammar. The base-rate expectation for sandbox_09 is repetition of that behavior. Sandbox_09 is not a test of *whether the mutator can solve the problem* — that was already resolved by the sandbox_08 GT harness check (the form is reachable, the harness accepts it at machine precision). Sandbox_09 is a test of *whether the new detector fires on a live run under provisional-only discipline without breaking anything and without any prompt-side hint*.

## Null Hypothesis

Component B either does not fire, fires incorrectly, or its ledger writes corrupt the shared `derived_constraints.json` file. Alternatively, sandbox_09's champion clears the gates — in which case sandbox_07 and sandbox_08's score=0 outcomes were primarily run-to-run variance rather than a systematic blind spot, and the "feature-bag completeness gap" diagnosis must be retracted.

## Pre-Registered Discriminating Outcomes

- **Outcome A (clean capability — null confirmed, hypothesis retracted).** Champion clears all 9 gates within the iteration budget under vanilla prompting (no hint, no confirmed constraints rendered). This would invalidate the "mutator has a systematic power-nesting blind spot" conclusion from sandbox_08. Component B's value proposition would need re-grounding on a different case. Note that Outcome A is *unlikely* — base rate across sandbox_07 and sandbox_08 is 0 clearings out of 24 combined iterations.
- **Outcome B (primary — expected).** Champion does NOT clear the 9 gates (residual trajectory qualitatively matches sandbox_07's: max |residual| never drops below 0.05), Component B fires at least once during the run, writes one or more provisional entries with producer=`negative_space_extractor` into `workspace/derived_constraints.json`, and the voids list on the closed sandbox_09 corpus is structurally comparable to sandbox_08's (both should include `EMLCALL(arg0|has_op:Pow)` or an equivalently-named slot if the corpus again avoids power-nesting). Confirms H-SP2-06.
- **Outcome C (detector sensitivity diverges).** Champion does not clear; Component B fires but sandbox_09's void set is materially different from both sandbox_07 and sandbox_08 (e.g., sandbox_09's mutator happens to nest a power operator inside `eml` arg0, pushing `arg0|has_op:Pow` out of the void list). This is a *healthy sensitivity signature* for the detector — it reads per-project coverage variation rather than firing on a universal family-wide void — and does not invalidate Component B. It does weaken the specific claim that "the power-nesting gap is systematic" to "the power-nesting gap was systematic on sandbox_08 but not on sandbox_09."
- **Outcome D (apparatus failure).** One or more of: Component B raises an exception during the hook, the ledger write produces malformed JSON, the `CONSTRAINT_PRODUCERS` whitelist rejects `negative_space_extractor`, the hint-template injection path has not been fully retired (grep check on the mutator prompt artifact must return zero hits on the hint template body), charter fingerprint drifts mid-run, or gemini-pro is swapped for a different model mid-run.

---

## Ground Truth (sealed — mutator-invisible)

**Symbolic form:**
```
I(phi, psi) = A * phi**p / (exp((gamma*phi/psi)**q) - 1) + offset
```

**EML reformulation** (the form the mutator must reach under the eml-only grammar):
```
I_model(phi, psi) = A * phi**p / eml((gamma*phi/psi)**q, math.e) + offset
```
where `eml((gamma*phi/psi)**q, math.e) = exp((gamma*phi/psi)**q) - ln(math.e) = exp((gamma*phi/psi)**q) - 1`.

**Parameters:**
```
A      = 0.95
p      = 2.30
gamma  = 0.72
q      = 1.30
offset = 0.06
```

**Harness sanity check (recorded at seal time).** The GT above was plugged into sandbox_08's gate harness during the sandbox_08 debug session. All 9 deterministic gates passed at machine precision: `hidden_global_residual=4.8e-6`, `hidden_high_phi_decay_ratio=5.4e-5`, `farther_tail_global_residual=4.0e-6`, all three peak-location errors exactly `0.0`, all three farther-tail terminal errors below `3e-14`. Sandbox_09 inherits the same harness and evidence surfaces verbatim — the harness contract is therefore known to accept this GT at machine precision.

**Derivation, physical interpretation, operator nesting convention, and parameter-space reasoning are withheld from this pre-registration** to keep the post-run algebraic-equivalence check a pure syntactic comparison rather than a derivational one. They are recorded in the sandbox_07 pre-registration §GT Leak Audit section and are considered already sealed by that prior document.

---

## Critical Contamination Controls

The key risk for sandbox_09 is *residual operator knowledge*: the pre-reg author (Claude Opus 4.6, this session) debugged sandbox_08 by plugging GT into the harness, and therefore has direct knowledge of the power-nested GT form. The charter must not transmit that knowledge to the mutator.

Audit performed at seal time:

1. **Charter grep check** — `grep -i -E '\b(chi|coupled|Planck|Odrzywo|Wien|Bose-Einstein)\b' projects/gp023_planck_sandbox_09/` returns **no matches** on mutator-visible files (`project_charter.md`, `test_model.py`, `evidence*.txt`). One earlier match surfaced the substring "chi" inside the English word "matching" in the charter, which was confirmed benign via a word-boundary re-check.
2. **Power-nesting language scrub** — the charter does not mention power operators, inner arguments, Pow AST nodes, or any variant of "nested exponent." The only mention of `arg0|has_op:Pow` in the entire repository appears in this sealed pre-registration and in the GP-061 seam's cold-test appendix, both in `research_areas/private/`.
3. **Retired hint template audit** — `grep -n "_STRUCTURAL_MISFIT_HINT_TEMPLATE" src/ztare/validator/autoresearch_loop.py` must return zero hits at seal time. The retirement was performed in a prior session; this audit re-confirms.
4. **Detector output visibility** — Component B's first live write goes to `workspace/derived_constraints.json` under `provisional`. The mutator prompt renders the *confirmed* bucket only; provisional entries are not rendered. Before the first iter fires, the confirmed bucket must be empty for `negative_space_extractor`, `structural_extractor`, and `trajectory_extractor` producers — this is automatic because sandbox_09 is a fresh project with no prior ledger.
5. **Charter-injection path** — the charter *is* mutator-visible via `project_charter.md` injection into the mutator prompt. This is why the audit in item 1 is decisive: the mutator will read the charter. All GT-relevant language is contained in this pre-registration file, which lives under `research_areas/private/` and is not injected.

Mungerian inversion: *if a stranger reads only the charter and the seed test_model.py, can they reconstruct the power-nested GT form?* The charter mentions "structural blind spot" and "feature-bag completeness gap" in the context of sandbox_08's post-mortem but never names the specific operator, argument position, or function. The seed model is a linear placeholder with no structural hints. Verdict: **no reconstruction path from mutator-visible surfaces.**

---

## Apparatus

Identical to sandbox_08 except for the following changes:

| Component | sandbox_08 | sandbox_09 |
|-----------|-----------|------------|
| `_STRUCTURAL_MISFIT_HINT_TEMPLATE` injection | live, hardcoded in prompt | **retired end-to-end** |
| `--inject-structural-misfit-hint` CLI flag | required | **removed** |
| `--hint-ablation-iter` CLI flag | required | **removed** |
| Component A (`run_structural_extractor`) hook | live | live (unchanged) |
| GP-062 (`run_trajectory_thrash_detector`) hook | live | live (unchanged) |
| Component B (`run_negative_space_extractor`) hook | **not present** | **live, new** |
| Ledger producer whitelist | {meta_judge, firing_squad, adjudicator, inferred, structural_extractor, trajectory_extractor} | + `negative_space_extractor` |
| Downgradable producers | {structural_extractor, trajectory_extractor} | + `negative_space_extractor` |

- Charter fingerprint pinned at seal time: `5f8470b37e10123276c2f835482383bd6dfaea153cf7acf28955964c29dfae62`
- Evidence file fingerprints pinned at seal time:
  - `evidence.txt`: `5c42891df802828d86d1c783449e8fbb7a85b5b1c469cbe44501746e47cc5a50`
  - `evidence_holdout.txt`: `11c8fb202c1ab810f33c5e82ed87b4e138ae854bf26c0170cf7835cbaadf93e8`
  - `evidence_farther_tail.txt`: `882472ce558c3b14abaf9bab8badc12cf93cb321fdb0e923f5c06f3a3eb7a19d`
- Gate harness fingerprint: `de55cd843fa8c37d17ab0b7fd51742ef73457ed564c23e875449ffe941781c47`
- Seed `test_model.py` fingerprint: `9e4c53a7daa521686f605285ac3eefa49b8f7eafa9e95c96114ef097b9777551`

All five evidence/harness fingerprints match sandbox_08's originals byte-for-byte (copied verbatim at scaffold time). The mutator is running against the same generator output as sandbox_07 and sandbox_08 — this is the decisive property that makes sandbox_09 a third attempt at the same problem rather than a new problem.

---

## Enforcement Surfaces (pre-committed)

1. All surfaces from sandbox_07/08 inherited unchanged (charter scrub, EML grammar enforcement on fit_declaration AND I_model body, 9-gate battery, provisional→confirmed ledger gate).
2. **New:** `negative_space_extractor` is registered in `CONSTRAINT_PRODUCERS` and `DOWNGRADABLE_PRODUCERS` in `src/ztare/validator/derived_constraints.py`. Verified by smoke test at seal time.
3. **New:** the Component B hook is wired into `autoresearch_loop._refresh_derived_constraints_from_eval` as a third sibling block, parallel to the existing Component A and GP-062 blocks. All three hooks run every iteration. All three use fail-open try/except — detector exceptions log a warning but do not crash the loop.
4. **Retired:** no code path in `autoresearch_loop.py` or `mutate_thesis` reads from `_STRUCTURAL_MISFIT_HINT_TEMPLATE`. The symbol no longer exists. No `hint_context` parameter is threaded through the mutator prompt path.

---

## What would make this uninterpretable (Mungerian inversion)

- If Component B's hook crashes mid-run and the fail-open catch swallows the exception silently without writing a warning line. The run would appear healthy but the primary new producer would be silently offline. **Mitigation:** the hook's `except Exception as exc: print(...)` line is explicit and will surface in stdout. Post-run grading must grep the run log for `negative_space_extractor skipped` and treat any hit as Outcome D.
- If the mutator happens to nest a power operator inside `eml` arg0 on sandbox_09 (Outcome A or C), the "systematic blind spot" claim weakens. This is a legitimate null result and is pre-committed as Outcome A or Outcome C above, not re-labeled after the fact.
- If the ledger accumulates an entry with `producer=meta_judge` that is *actually* coming from Component B but got re-routed by `_normalize_constraint_producer` because the whitelist update was not picked up. **Mitigation:** the seal-time smoke test confirmed `negative_space_extractor` is in the imported `CONSTRAINT_PRODUCERS` set. Post-run grading must re-check by grep on the closed ledger.
- If Component A or GP-062 unexpectedly fires and promotes to confirmed within a single run. Neither should — the provisional gate requires `seen_count_runs >= 2`. If confirmed entries appear from any of the three new producers after a single run, that is a ledger-gate bug and qualifies as Outcome D.
- If gemini-pro is swapped for a different model mid-run — the claim is specifically about gemini-pro's search, not about "LLM mutators" generically. Same discipline as sandbox_07/08.
- If the iter budget is extended mid-run to chase a near-miss. The budget is fixed at seal time.

---

## Success Band

**Outcome B** (primary — expected) is confirmed if *all four* of the following hold:

1. Champion's best max |residual| does not drop below 0.05 within the iteration budget (structural failure persists).
2. `workspace/derived_constraints.json` contains at least one entry with `producer="negative_space_extractor"` after the run closes.
3. The post-run re-run of the Component B CLI (`python -m src.ztare.validator.negative_space_extractor --project gp023_planck_sandbox_09`) produces a dense-void set that is structurally comparable to sandbox_08's — in particular, at least one `EMLCALL|arg0|has_op:*` entry appears in the void list.
4. No Outcome D apparatus-failure indicators trip (see §Mungerian inversion).

Outcome B is the *intended* resolution and would close H-SP2-06 in favor of promoting Component B from "one live datapoint" to "two live datapoints" — qualifying the producer for confirmed-bucket promotion on the next run.

---

## Failure Band

**Outcome D** (apparatus failure) is confirmed if any of:
1. Component B raises an exception during the hook on any iteration and the `negative_space_extractor skipped` warning appears in the run log.
2. `derived_constraints.json` is malformed JSON post-run.
3. A confirmed entry appears from any of the three new producers after a single run (ledger gate leak).
4. The retired hint template body appears anywhere in the mutator prompt debug artifact (`last_prompt_debug.txt`) — grep check post-run.
5. Charter fingerprint drifts between seal and post-run.
6. Mutator model is not gemini-pro in the run manifest.

**Outcome A** (clean capability — hypothesis retracted) is confirmed if the champion clears all 9 gates. This is pre-committed as a legitimate outcome and forces retraction of the "systematic power-nesting blind spot" claim; it does not invalidate Component B's code, only its motivating diagnosis.

**Outcome C** (detector sensitivity diverges) is confirmed if the champion does not clear but the post-run Component B CLI does not surface `arg0|has_op:Pow` in the sandbox_09 void list. This weakens H-SP2-06 to a sandbox_08-specific claim and requires a follow-up seam note.

---

## Iteration Budget

Hard cap: **15 iterations.**

Rationale: sandbox_08 ran 14 iters before stopping; sandbox_07 ran 10. Setting 15 gives Component B a slightly larger corpus than sandbox_08 for the post-run cold re-check, while keeping the budget tight enough that a null result closes inside ~60 minutes of wall clock. Budget is fixed at seal time and may not be extended mid-run to chase a near-miss.

---

## Relationship to Sibling Seams

- **GP-061 (constraint accumulation as output)** — sandbox_09 is the first live run for GP-061 Component B. Cold-test retroactive pass (sandbox_07 + sandbox_08) is recorded in the GP-061 seam appendix and is the qualification gate for live wiring.
- **GP-062 (trajectory thrash detection)** — sandbox_09 is the second live run for GP-062 (first was sandbox_08 live, also sandbox_07 retroactive). If GP-062 fires on sandbox_09 with thrash iterations comparable to sandbox_07/08, its two-run promotion gate may clear for sandbox_10.
- **GP-045 (residual-mode successor)** — not engaged here. sandbox_09 is a standard hot-start run from a seed model.
- **GP-055 (meta-judge parse robustness)** — must be live at seal time (inherited from sandbox_08).
- **GP-059 (expressibility probe)** — not re-run. sandbox_07's GP-059 closure artifact established reachability at depth-1 for the shared GT.

---

## Dry-Run Checklist (before sealing)

- [x] Charter sha256 pinned: `5f8470b37e10123276c2f835482383bd6dfaea153cf7acf28955964c29dfae62`
- [x] Evidence surface fingerprints pinned (3 files above).
- [x] Gate harness fingerprint pinned.
- [x] Seed test_model.py fingerprint pinned (linear placeholder, intentionally grammar-valid-but-wrong).
- [x] Grep charter + evidence surfaces for `{chi, coupled, Planck, Odrzywo, Wien, Bose-Einstein}` with word boundaries. **Zero matches.**
- [x] Seed smoke check: `python gate_harness.py --run-visible-assertions` fails at expected point (`phi=0.1739, psi=0.6`, max |res| ~0.06 > 0.05 threshold). Seed is known-bad, as required. Confirmed 2026-04-15.
- [x] Seed deterministic gate check: `python gate_harness.py --emit-deterministic-gates` returns `gates passed: 0 / 9`. Confirmed 2026-04-15.
- [x] `_STRUCTURAL_MISFIT_HINT_TEMPLATE` and its CLI flags retired — grep confirmed zero hits in `src/ztare/validator/autoresearch_loop.py` in prior session.
- [x] Import smoke on `autoresearch_loop` + `negative_space_extractor` + `structural_constraint_extractor.extract_generalized_feature_matrix` + `derived_constraints.CONSTRAINT_PRODUCERS` passes with no error. Confirmed 2026-04-15.
- [x] Component B cold-test re-run on sandbox_08 after the `leaf` scrub still surfaces `EMLCALL(arg0|has_op:Pow)` in voids (7 total, universe=14). Confirmed 2026-04-15.
- [x] Peer review of the three new code artifacts performed in-session. Three follow-up items filed (strip `leaf` from universe — applied; map `EMLCALL` → `eml` in proposal prose — deferred, latent; soften "complementary not redundant" in seam — deferred, doc-only). None blocking for a provisional-only first live run.

---

## Pinned Command String (to be executed by the operator)

```
python -m src.ztare.validator.autoresearch_loop \
    --project gp023_planck_sandbox_09 \
    --rubric gp023_planck_sandbox_09 \
    --iters 15 \
    --mutator_model gemini-pro \
    --judge_model gemini \
    --deterministic_score_gates \
    --underidentified_after 15 \
    --no_model_fallback
```

No `--inject-structural-misfit-hint`. No `--hint-ablation-iter`. The retired flags are not in `autoresearch_loop.py`'s argparse anymore — they would raise an error if passed.

---

## What This Experiment Does NOT Test

- Whether Component B's *rendered constraint* helps the mutator. The provisional-only gate means sandbox_09's mutator does not see Component B's output in its prompt. The "does it help?" test is decoupled to sandbox_11 or later (two confirmed-bucket promotions required first).
- Whether other mutator models (Claude Opus, GPT-4o) would behave differently. Scope is gemini-pro only.
- Whether the feature-bag matrix vocabulary is rich enough for non-eml grammars. Scope is the eml-only grammar.
- Whether the density guard `MIN_FILLED_SLOTS_PER_KEY=2` is correct. The peer review flagged it as weak. Revisited in a post-sandbox_10 follow-up.
- Whether Component A's conservative-refusal behavior on varied-outer-skeleton corpora is *always* the right call. Sandbox_09 will either confirm or refute that Component A refuses on this corpus as well.

These are legitimate follow-ups if sandbox_09 produces Outcome B. They are explicitly out of scope for this seal.

---

## Seal Statement

This pre-registration fixes:
- Hypothesis H-SP2-06 and its null
- Four discriminating outcomes (A, B, C, D) with quantitative conditions
- GT symbolic form and parameter values (sealed, mutator-invisible)
- Apparatus fingerprints (charter, evidence × 3, harness, seed)
- Enforcement surfaces
- Iteration budget (15, hard cap)
- Pinned command string
- Post-run grading protocol

Changes to any of the above after this point require a re-seal and invalidate the sandbox_09 run for H-SP2-06 purposes.

**Sealed 2026-04-15 by Claude Opus 4.6 (this session) at the direction of the operator.**

---

## Post-Seal Supplementary Evidence — Non-Planck Cold Test (2026-04-15)

Not a re-seal. The hypothesis, outcomes, GT, apparatus fingerprints, and command string above are untouched. This section records a diagnostic cold test of Component B against a non-Planck closed corpus, run after sealing, to address the "Planck-family drift" concern raised in the sandbox_09 scaffold peer review (the sandbox_08 closure's Next Step #2 called for exercising Component B outside the Planck generator before wiring it live).

### Target corpus

- **Project:** `gp045_cold_residual_01` (closed).
- **Grammar axis:** `math.exp`-only direct call (not `eml_only`). Different fit-primitive than sandbox_07/08.
- **Family count (failed, residual ≥ 0.15, structural_misfit):** 5.
- **Relation to Planck GT:** unrelated — different generator, different variable semantics.

### Diagnostic result

Component B fired with 4 dense voids, all at `exp(arg0|...)`:

```
exp:
  - arg0|has_op:Add
  - arg0|has_op:Call
  - arg0|has_op:Div
  - arg0|has_op:Sub
```

Universe=7, present=3, family_count=5. Density guard passed (≥2 filled slots at the dense key). The void set is disjoint from the sandbox_07 and sandbox_08 void sets — confirming the detector reads per-corpus coverage rather than emitting a Planck-family-wide signature.

### Bug discovered and fixed during the non-Planck cold test

The non-Planck run surfaced a substring-match bug in `_normalize_family_label` (`structural_constraint_extractor.py`):

- **Symptom:** On the first pass the function name rendered as `MATHECONSTxp` instead of `exp`. Void *keys* and *density guard* were correct; only the function-name prefix in the rendered proposal was mangled.
- **Root cause:** `text.replace("math.e", _MATHE_MARKER)` is a bare substring replace, which corrupts `math.exp` → `MATHECONSTxp` when the corpus contains `math.exp` calls (the eml-only corpora do not, which is why the bug was dormant through the sandbox_07/08 cold tests).
- **Fix:** word-boundary regex `re.sub(r"\bmath\.e(?![a-zA-Z0-9_])", _MATHE_MARKER, text)`. The negative lookahead forbids matching when `math.e` is followed by an identifier character, so `math.exp`, `math.expm1`, `math.erf`, etc. are left alone; only the bare `math.e` constant is rewritten.
- **Post-fix verification:**
  - `gp023_planck_sandbox_07` — 12 families, 7 voids, `arg0|has_op:Pow` **not** in void set (matches pre-fix asymmetry: sandbox_07 has Pow inside arg0).
  - `gp023_planck_sandbox_08` — 8 families, 7 voids, `arg0|has_op:Pow` **in** void set (matches the sandbox_08 diagnosis).
  - `gp045_cold_residual_01` — 5 families, 4 voids, function name renders as `exp`.
  - Sandbox_07 / sandbox_08 void sets are bit-identical to the pre-fix cold-test output documented in the GP-061 seam and the sandbox_08 closure. No behavioral drift on the eml-only corpora.

### Why this is supplementary and not a re-seal

- The sandbox_09 apparatus does not include `gp045_cold_residual_01`. The bug fix affects the structural-constraint reader's label normalization path, which runs post-hoc on sandbox_09 failed families at the end of each iteration; it is not part of the mutator prompt surface and does not change gates, harness, evidence, charter, or seed.
- The eml-only sandboxes (07, 08, and by inheritance 09) never exercised the buggy branch because they contain no `math.exp` calls in their family labels. The fix is a no-op on sandbox_09 byte-for-byte.
- The bug affected **rendering** only, not void detection. The density guard, universe construction, and void-set computation are all driven by the feature-bag output of `extract_generalized_feature_matrix`, which does not use `_normalize_family_label` on the rendered name side — it uses the parsed AST.

If sandbox_09 fires Component B under Outcome B, the sandbox_09 void set is expected to be a subset or superset of the sandbox_08 void set (not identical — sandbox_09 is a fresh run with a different mutator trajectory). The post-run detector-emission audit should compare sandbox_09's void set against sandbox_07 and sandbox_08 as documented in the grading protocol above.

---

## Correction Block — Sandbox_09 PAUSED (2026-04-15, post-seal, pre-run)

**Status: PAUSED. Do not execute the pinned command above until this pause is explicitly lifted by the operator.**

### What the prior "Post-Seal Supplementary Evidence" section got wrong

The section immediately above claims a "Non-Planck Cold Test" against `gp045_cold_residual_01` and presents it as evidence that Component B's feature vocabulary generalizes outside the Planck domain. That claim is **wrong** and the section is retained here only as an audit-trail artifact — not deleted, per the recordkeeping discipline.

- `gp045_cold_residual_01`'s own `project_charter.md` describes it as a fresh exploratory verifier on the **frozen GP-037 / GP-042 / GP-043 substrate**. That substrate is the Planck-family `I(phi, psi)` generator used by sandbox_06/07/08.
- `gp045_cold_residual_01/thesis.md` uses `phi` and `psi` as its observables and reasons about an `I(phi, psi)` surface with a ψ-dependent asymptotic floor and φ-decay. Same variables, same observable, same generator.
- The only axis on which gp045 differs from sandbox_07/08 is the **fit-primitive grammar** (`math.exp` direct call vs `eml_only`). That is an apparatus axis, not a domain axis.
- I conflated "different grammar over the same generator" with "different domain." Component B has therefore been cold-tested on **three Planck-family projects and zero non-Planck projects**. There is no evidence that the `fn:{fname}|arg{i}|has_op:{OP}` vocabulary, the density guard, or the dense-void promotion logic are domain-agnostic.

### What stays valid

- The `_normalize_family_label` substring-match bug fix (`math.e` → word-boundary regex) is real, was verified on three projects, and did not change the sandbox_07 or sandbox_08 void sets. It stays applied.
- The sandbox_09 apparatus itself (charter, evidence surfaces, harness, seed, fingerprints, gate battery) is untouched and remains sealed.
- The sandbox_09 hypothesis, outcomes, and GT remain sealed.

### Why sandbox_09 must not execute in its current form

Sandbox_09's stated purpose (Outcome B in particular) treats a Component B live emission as the third datapoint for the two-run promotion gate. But two of the three existing cold datapoints (sandbox_07, sandbox_08) and the broken "non-Planck" test (gp045) are all drawn from the Planck family. Running sandbox_09 as-is would produce a fourth Planck-family datapoint and nothing more. Under that corpus, Component B could promote to confirmed for the next sandbox run without ever having been exercised against a structurally disjoint generator. That is precisely the failure mode the sandbox_08 closure's Next Step #2 was supposed to block, and I failed to enforce it.

Running sandbox_09 now would conflate:

- **Apparatus test:** does Component B fire live, write provisional entries, and avoid contaminating the prompt surface? (sandbox_09 can still answer this.)
- **Generalization test:** is the feature vocabulary domain-agnostic? (sandbox_09 **cannot** answer this because its corpus is Planck-family.)

A single live run cannot answer both questions at once, and the pre-reg text above reads as if it does.

### What happens next

1. A new target-domain spec (`GP-061_generalization_target_rc_step_01_spec.md`) is being drafted for an RC step-response generator. That target is physically and structurally disjoint from Planck `I(phi, psi)`: different variables (`t`, `R`), no `phi^n * psi^m` coupling, no `1/(exp(x)-1)` denominator, no peaked surface.
2. Component B must fire correctly on a cold retroactive corpus of failed families from the new target before any live run anywhere wires it into the post-eval hook on a non-Planck project.
3. Whether sandbox_09 is then unpaused as-is (apparatus test only, under a narrowed hypothesis) or is retired in favor of running the new RC-step target as sandbox_09 itself is an operator decision. The new target-domain spec is written so either branch is available.
4. Until the operator explicitly lifts this pause, the pinned command string above does **not** authorize execution. Treat the seal as provisional despite the "Sealed 2026-04-15" line above.

**Paused 2026-04-15 by Claude Opus 4.6 (this session) after the operator flagged the Planck-family / non-Planck conflation.**
