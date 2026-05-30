# Deep Audit Findings — 2026-04-25 night

> **Seam metadata** · `seam_id:` 2026_04_25_deep_audit_findings · `track:` audits · `status:` unrecorded · `last_updated:` 2026-05-08


**Scope:** Latent apparatus bugs in autoresearch_loop, test_thesis, fit primitives, prompt rendering, contract table, gates registry.
**Audit type:** Read-only triage. No code edits.
**Trigger:** gp163d_unified_accel postmortem; operator wants pre-flight check before next substrate run.
**Bottom line:** 4 confirmed bugs (1 blocking — cancels Bug B fix; 3 latent traps), plus 4 brittleness hotspots and 2 cross-layer contract gaps. Recommended top-3 fixes are surgical (5–30 lines each).

---

## 1. Bugs found

### B1 — BLOCKING — Bug B "fix" is dead code: ordering bug in test_thesis.py

**File:** `src/ztare/validator/test_thesis.py`
**Lines:** 2367 (call) vs 2393 (write site) vs 1885 (read site)

`finalize_deterministic_score(evaluation, main_rubric, test_suite_status)` runs at line 2367. Inside, line 1885 reads `evaluation["holdout_hard_gate_fired"]`:

    gate_harness_ran = "holdout_hard_gate_fired" in evaluation

But the holdout-hard-gate dispatch that SETS that key runs ~30 lines LATER, starting at line 2393 (`if main_rubric.get("holdout_hard_gate"):`). At evaluation time inside `finalize_deterministic_score`, the key has never been written.

Result: `gate_harness_ran` is always `False` in the deterministic path. The Bug B branch (line 1887) — "demote L3 in-test issue to soft cap when gate harness produced numeric signals" — NEVER fires. Every fail_runtime/fail_other still goes to `hard_fail_reasons` at line 1904, zeroing the score. **The substrate-level rubric persona patch is the only thing keeping Bug B at bay**, and it only works in the LLM-judged path, not the `--deterministic_score_gates` path.

**Trigger:** any substrate run with `--deterministic_score_gates` whose `if __name__ == "__main__":` block in test_model.py fails OR whose subprocess exits nonzero, AND where the gate harness produces real holdout numbers. Score → 0 even when gate values are inside the rubric thresholds.

**Severity:** blocking for any substrate using deterministic-score gates with a holdout_hard_gate. Likely affects gp163d-class repeats.

---

### B2 — LATENT — INIT_RANGE pathology hint emits a syntax the parser silently rejects

**Files:**
- `src/ztare/fit/fit_primitive_features.py:1200-1201` (writer of the message)
- `src/ztare/fit/fit_primitive_features.py:1517-1547` (`_resolve_init_range` parser)
- `src/ztare/validator/autoresearch_loop.py:2566-2578` (relays the message to next-iter mutator prompt)

The Bug A pathology message recommends:

    INIT_RANGE = {'<param>': (1e-10*1e-3, 1e-10*1e3)}

with `*` multiplication. But `_resolve_init_range._to_num` (line 1533) only accepts `ast.Constant` and `ast.UnaryOp(USub, Constant)` — it returns `None` for any `ast.BinOp`. When the mutator follows the hint verbatim, `init_range_value` is `None` for that param and `_range_for(pname)` falls back to default `(-2.0, 2.0)`. The init-range trap continues silently.

**Trigger:** any sub-physical-scale fit on iter ≥ 2 (when the prior diagnostic is in the prompt). The mutator that copies the hint exactly gets the SAME failure with no change in fitted-param magnitude.

**Severity:** latent; cancels Bug A's fix when the very pattern Bug A is supposed to detect recurs.

**Quick fix:** either (a) emit a literal-numeric example in the message (`(1e-13, 1e-7)`) instead of multiplied form, or (b) extend `_to_num` to evaluate `ast.BinOp(Mult|Div|Add|Sub)` over Constant operands.

---

### B3 — LATENT — Sub-physical-scale detector is naive about y-scale

**File:** `src/ztare/fit/fit_primitive_features.py:1187`

    if pval != 0 and abs(pval) > 0 and y_min_nonzero / abs(pval) > 1e5:
        sub_physical[pname] = pval

False positive: when `y_min_nonzero` is naturally large (e.g. row counts ~1e6) and a fitted parameter is order(1) (legit), `1e6 / 1.0 = 1e6 > 1e5` — sub-physical-scale fires, marks `pathological=True`, blocks the fit's `success=True` flag interpretation and emits a misleading INIT_RANGE remedy.

**Trigger:** any substrate where visible `y` values span a large numeric scale and a parameter sits near 1 (offset, intercept, fraction). The detector fires on substrates that have nothing to do with the dimensional-constant scenario.

**Severity:** latent; symptom is "false-pathological" telemetry. Mutator may then add a useless INIT_RANGE for a parameter that should stay default.

**Quick fix:** condition the trigger on the parameter being _near zero_ relative to `min(|y|)` AND _smaller than 1_ in absolute terms; or compare `abs(pval)` directly against an absolute scale floor (e.g. 1e-3).

---

### B4 — LATENT — Nelder-Mead "convergence" classification is scale-dependent

**File:** `src/ztare/fit/fit_primitive_features.py:1053`

    if res.success or res.fun < 1e-3:
        converged += 1

`res.fun < 1e-3` is an absolute SSE threshold. For substrates with y at scale 1e-10, ANY simplex landing in the y≈0 basin satisfies it trivially → `converged_clean` regardless of fit quality. For substrates with y at scale 1e6, even an excellent fit has SSE far above 1e-3 → counter rarely increments → `no_convergence` even when scipy actually succeeded.

The `convergence_classification` field is the decisive signal `display formatting for "FIT SUCCESS"` plus downstream prompt rendering depend on. A miscalibrated counter feeds bogus telemetry to the judge and operator.

**Severity:** latent display/telemetry corruption; not an immediate score bug, but the postmortem's `max|res|=0.00000` masking pattern compounds with this.

**Quick fix:** classify via `res.success` only, OR via a y-scale-relative threshold like `res.fun < 1e-6 * sse_baseline` where `sse_baseline = sum(y_i ** 2)`.

---

## 2. Brittleness hotspots

### H1 — `:.5f` display formatting masks tiny residuals

**Files:** `src/ztare/validator/autoresearch_loop.py:4960, 5098, 5099, 5108`

`max|res|={:.5f}` and `σ̂²={:.5f}` round residuals at scale 1e-11 to `0.00000`. The gp163d postmortem already named this. The fix is mechanical (`:.5g` or `:.3e`) and applies to BOTH the legacy 1D path (line 4960) and the feature-vector path (5098-5108). Currently neither is patched. Same risk recurs in the 1D pathology message at fit_primitive_features.py:1156-1157 (`{pathology_threshold:.1f}`, `{y_max:.2f}`) for substrates whose y is far from order(1).

### H2 — `substitute_fitted_model_params` regex rejects multi-line / nested-dict MODEL_PARAMS

**File:** `src/ztare/fit/fit_primitive_features.py:1444-1452`

Pattern: `r"^(\s*MODEL_PARAMS\s*(?::\s*[\w\.\[\], ]*)?\s*=\s*)\{[^{}]*\}"`. The `[^{}]*` body refuses any nested brace. If a mutator writes:

    MODEL_PARAMS = {'a': 1.0, 'b': {'sub': 2.0}}

…or any deferred-default pattern with nested literals, regex returns `n=0` and the unmodified `python_code` is returned. MODEL_PARAMS stays `{}`, gate harness sees empty dict, `.get(default)` paths fire silently. Returns `python_code` unchanged is the comment-documented "fallback to LLM-guessed params" — but in fact MODEL_PARAMS at iter 1 is `{}` so the substrate gets garbage.

### H3 — `auto_escalate` widens around midpoint, can't escape order-of-magnitude gap

**File:** `src/ztare/fit/fit_primitive_features.py:1042-1046`

`auto_escalate` widens by 5×, 25× around the original interval midpoint. For default `(-2, 2)` (mid=0, half=2), the 25× widening yields `(-50, 50)` — still nowhere near a 1e-10 physical optimum. The escalator is a comfort blanket for substrates already close to order(1); it does NOT defend against the dimensional-constant trap that Bug A targets.

### H4 — `holdout_hard_gate_fired` key only set when rubric flag is on AND files exist

**File:** `src/ztare/validator/test_thesis.py:2393-2396`

If `holdout_hard_gate=True` in rubric but `evidence_holdout.txt` or `gate_harness.py` is absent, the entire dispatch is skipped silently and `holdout_hard_gate_fired` is never written. Downstream consumers reading the key fall through to the "no gate ran" path. The configuration-drift case (rubric flag set on a substrate that hasn't been scaffolded for it) is a silent no-op — a sharp `KeyError` or warning would help.

---

## 3. Cross-layer contract gaps

### G1 — `cage.validate_substrate_meta` claims required keys but `check_min_rows_per_category` defaults silently

**Files:**
- `src/ztare/gates/cage.py:45` declares `min_rows_per_category` as `REQUIRED_SUBSTRATE_META_KEYS`
- `src/ztare/gates/cage.py:279` reads `meta.get("min_rows_per_category", 3)`

If validation is run, missing key → diagnostic. But if a downstream gate calls `check_min_rows_per_category` without first running `validate_substrate_meta` (e.g., legacy substrate or a non-Cage call path), the silent default of 3 fires. Two layers, two semantics, no shared single-source enforcement.

### G2 — `MODEL_PARAMS` substitution shape unspecified

**Files:**
- `fit_primitive_features.py:1416-1453` (writer)
- `fit_primitive.py:1208-1235` (1D writer, different regex)
- All `gate_harness.py` substrate files (readers; arbitrary code)

There is no formal schema for what `MODEL_PARAMS` should look like in test_model.py or what failure modes the gate harness must tolerate. The 1D and ND writers use DIFFERENT regexes with different tolerances. Mutator output that satisfies one writer's regex but trips the other's is possible. This is the bug class that B1/Bug-#34 keep surfacing.

### G3 — Gate registry's `_make_run_callback` returns engagement sentinels, not results

**File:** `src/ztare/gates/registry.py:63-85`

Every gate's `run` callback today returns `{"_gate_engagement_recorded": True, "_module": ..., ...}` — a placeholder, not the gate's actual verdict. Comment at line 76 acknowledges "Defer full integration to Phase 3b." Anything reading `cage.dispatch_and_run`'s `run_results` and treating the sentinel as a real verdict will silently see "engaged & no error" regardless of whether the gate would have passed. **Cage is not yet decisive for verdicts.** If autoresearch_loop ever wires Cage into the score path before Phase 3b lands, every gate "passes."

---

## 4. Top 3 priority fixes (by expected impact on next 5 runs)

**P1 — Fix B1 ordering bug (test_thesis.py).**
Move the `holdout_hard_gate` dispatch (line 2393) to BEFORE `finalize_deterministic_score` (line 2367), OR have `finalize_deterministic_score` defer the hard_fail / soft_cap decision until after the holdout dispatch sets `holdout_hard_gate_fired`. Without this, the gp163d pattern (judge writes "harness defect" when gate harness has real numbers) recurs in the deterministic-score path even though the rubric persona patch shipped. **30 minutes; highest-leverage fix.**

**P2 — Make the Bug A pathology hint parser-compatible (fit_primitive_features.py).**
Either rewrite the message at lines 1200-1201 to use literal numeric tuples like `(1e-13, 1e-7)` (no multiplication), OR extend `_to_num` (lines 1533-1539) to fold `ast.BinOp(Mult|Div|Add|Sub)` over Constant operands. As-is, mutators following the diagnostic verbatim get silently re-trapped. **15 minutes once the pattern decision is made.**

**P3 — Replace `:.5f` with `:.5g` in fit-primitive telemetry (autoresearch_loop.py + fit_primitive_features.py).**
Lines 4960, 5098, 5099, 5108 plus pathology messages at fit_primitive_features.py:1156-1157. The postmortem already documented the masking. Mechanical, low-risk. Closes the "max|res|=0.00000" cognitive trap that the operator specifically called out. **10 minutes.**

---

## 5. What I checked and found clean

- All 12 `f"""..."""` blocks in `autoresearch_loop.py` compile (Bug-D-class regressions absent today).
- All target files (autoresearch_loop, test_thesis, both fit primitives, prompt.py, contract_table.py, cage.py, registry.py) parse via `ast.parse` without syntax errors.
- `.format()` callsites I inspected (mform_alignment_audit, fit_declaration_retry, cognitive_camouflage_experiment) take user content only as the VALUE, not the template — Python `.format()` does not recursively interpret values, so user braces in `thesis_excerpt` / `previous_tail` are safe text. (Earlier in the audit I flagged these as bugs; that was wrong — keeping the note here for the operator's record.)
- `inject_gate_time_primitives` is idempotent (sentinel-checked) and docstring-aware.
- `extract_form_declaration` correctly handles negative-number `(-2.0, 2.0)` via UnaryOp(USub).

---

## 6. Followups worth opening (lower priority)

- F1: enforce `validate_substrate_meta` at every Cage entry point so silent-default semantics in `check_min_rows_per_category` go away (G1).
- F2: harden `substitute_fitted_model_params` regex to permit at least one nested `{}` level OR explicitly validate the mutator's MODEL_PARAMS literal at submission time (H2).
- F3: replace `auto_escalate` arithmetic widening with logarithmic widening (multiplicative span instead of additive midpoint), so 5× / 25× actually crosses decades (H3).
- F4: rewrite `convergence_classification` to be y-scale-relative (B4).
- F5: when Cage Phase 3b lands, ensure no autoresearch_loop call site reads `run_results` from the registry's stub callbacks as if they were verdicts (G3).

---

## Turn note — 2026-04-26 morning

Status of audit findings as of this morning:

**Top-3 priority fixes — all shipped:**
- ✅ **P1** (reorder `finalize_deterministic_score`): the call now
  defers via `_defer_deterministic_finalize` flag and runs AFTER the
  holdout-hard-gate dispatch, so `evaluation["holdout_hard_gate_fired"]`
  is set when `finalize` reads it. Bug B's `gate_harness_ran` branch is
  now LIVE code, not dead. `finalize` also adds
  `holdout_hard_gate_fired` as a hard-fail reason so the gate's
  score=0 is preserved (won't be undone by the demote-to-soft-cap path).
  Edits at `src/ztare/validator/test_thesis.py` lines 1869-1880, 2365-2378,
  2580-2592.
- ✅ **P2** (Bug A hint parser-compatibility): hint now uses plain
  numeric literals; warns explicitly that `*` `/` etc. are rejected by
  the INIT_RANGE parser. Edits at `src/ztare/fit/fit_primitive_features.py`
  lines 1198-1212 and `src/ztare/validator/autoresearch_loop.py`
  pattern #5.
- ✅ **P3** (`%.5f` → `%.5g` display): residuals at scale ~1e-11 no
  longer round to "0.00000". Edits at
  `src/ztare/validator/autoresearch_loop.py` lines 5102-5113.

**Latent bugs from audit — partially shipped:**
- ✅ **B3** (sub-physical-scale detector false positives): tightened
  with residual-quality guard. Detector now requires `mean|res| / max|y| > 0.05`
  in addition to the original signal. Verified gp163d still fires;
  large-y order(1) param substrate does NOT false-positive.
- (deferred) **B2/B4** logged but not fixed (lower priority).

**Lower-priority follow-ups F1-F5 — logged for future passes:**
- F1, F5 → appended to `GP-157_cage_orchestrator_substrate_agnostic_dispatch.md`
- F2, F3, F4 → appended to `GP-156_apparatus_hardening_proposal.md`

These are not blocking for the next gp163d relaunch.


---

## Addendum — 2026-04-25 night, post-v2.1 session

The session that began with the gp163d weighted-χ² wiring grew into the v2.1 meta-architecture build (REFRAME + ANALOGY + wMDL + GP-166 noise_profile + GP-167 substrate_critic + pathology enforcement + contamination defense + per-class breakdown + self-falsification reclassifier + R1 contract-collision fix + framer N-D scope fix). The session-final audit pass surfaced four additional latent bugs in the same harness/score-zero class as B1–B4 above. All four shipped this session.

### B5 — BLOCKING — gate-harness exit-1 + JSON in stdout misclassified as harness defect

**File:** `src/ztare/validator/utilities/harness_failure_mode.py`
**Lines:** 60–95 (classify_harness_failure)

The apparatus invokes `python gate_harness.py --run-visible-assertions` for L3. When gates fail, the harness exits 1 with **empty stderr and a JSON envelope in stdout** reporting `all_gates_pass: false`. The classifier inspected only stderr → empty → returned `FAIL_OTHER` → label "harness defect" → `harness_defect_cap` capped score at 50.

This was the structural cause of the dominant gp163d false-positive: legitimate gate failures (Class B/C farther-tail MRE > threshold) labeled as tooling defects, score zeroed by the cap, mutator pushed toward "fix the harness" instead of "fix the form." Roughly 50%+ of the prior 16-iter run history fell into this trap.

**Fix shipped:** `classify_harness_failure(stderr, stdout)` now also parses stdout JSON when stderr is empty and returncode is non-zero. If the JSON contains `all_gates_pass: false` (or any sub-gate's `passed: false`), returns `(FAIL_ASSERT, "GateFailure")` — a legitimate falsification, score-eligible per the rubric, no cap applied. Verified on the actual gp163d gate_harness output post-fix.

### B6 — HIGH — Holdout near-miss "floor" expression always evaluated to 30

**File:** `src/ztare/validator/test_thesis.py`
**Line:** 2525

The expression `min(pre_cap_score, _floor) if pre_cap_score >= _floor else _floor` always evaluates to `_floor=30` regardless of input. A judge-rated 70 near-miss collapsed to 30; a judge-rated 15 near-miss also raised to 30. The variable name said "floor" but the operator's expected gradient signal was destroyed — the mutator could not distinguish a strong near-miss from a weak one.

**Fix shipped:** replaced with `max(pre_cap_score, _floor)` — true floor semantics. Judge's score preserved when above floor; raised to floor only when below. Comment in code documents the previous bug and the reasoning.

### B7 — HIGH — Regime-mismatch silently zeroed saved baseline

**File:** `src/ztare/validator/autoresearch_loop.py`
**Lines:** 827–833 (`_saved_best_comparison_anchor`) + 3974–3980 (caller)

When the saved best candidate's regime fingerprint did not match the current eval's regime — a routine outcome of any rubric edit, judge model swap, or substrate flag change mid-run — `_saved_best_comparison_anchor` returned `compare_score=None`. The caller treated `None` as "no previous baseline" and silently promoted any new score (even 0) over the previously-saved 50. The operator saw `BASELINE PROMOTED: regime_mismatch:50 -> 0` on every rubric tweak, with no chance to inspect or override.

**Fix shipped:** when fingerprints diverge, `compare_score` is now set to `raw_saved_score` (not `None`), and the caller's print warns explicitly that the saved score is preserved despite regime mismatch. New candidates must beat the prior best to be promoted; rubric edits do not silently discard accumulated work.

### B8 — MEDIUM — Pathology detector flagged log-space parameters as exceeding 10×max(|y|)

**File:** `src/ztare/fit/fit_primitive_features.py`
**Lines:** 1261–1277

The Bug-#26 pathology detector compared `|fitted_param|` against `10×max(|y_observed|)`. For substrates with y at acceleration scales (gp163d's `y ≈ 1e-9`), the threshold was `1e-8`. A perfectly physical fitted parameter `log10_c0 = -10` (meaning `c0 = 1e-10`) was flagged as pathological because `|−10| > 1e-8`. Magnitude comparison is meaningless when the parameter lives in log space.

**Fix shipped:** added `_is_log_space_param()` helper that detects the convention prefixes `log_*`, `log10_*`, `log2_*`, `ln_*`. Log-space params are checked against the operator-declared `init_range` (with 2× widening) instead of against y-magnitude. Linear params still use the original `10×max(|y|)` threshold. Verified: `log10_c0 = -10.0` in declared range → not pathological; `log10_c0 = -50` outside `init_range=(-2, 2)` → correctly pathological; linear `k = 1.5` → not pathological.

### Bugs surfaced by the audit but NOT shipped (lower priority)

- **B9** (low): empty-stdout + empty-stderr + exit-1 case still returns `FAIL_OTHER`. This is the correct behavior for a true crash signature; documenting only.
- **B10** (low): pathology substitution does not re-verify that the init-range midpoint passes the gate harness. Corner case where the midpoint itself is degenerate.
- **B11** (low): `--run-visible-assertions` flag has no special handling in any project's gate_harness.py. Latent until someone defines its semantics.

### What this session changes for the next gp163d run

The four shipped fixes (B5–B8) eliminate the dominant harness-defect false-positive class. The next-iter score band is no longer floored by structural mis-classification of legitimate gate failures or fit pathology. Calibration target (60–80) is reachable as soon as the mutator pivots away from the radius-only S form, which the SubstrateCritic + per-class breakdown briefings should push it to do. Restart of the apparatus process is required for the fixes to take effect (Python imports are per-process; the running apparatus has the pre-fix code cached).
