# GP-084 Crucial Experiment — Pre-Registration

> **Seam metadata** · `seam_id:` GP-084 · `track:` substrates · `status:` Sealed - run not yet started · `last_updated:` 2026-05-08


**Filed:** 2026-04-18  
**Status:** Sealed — run not yet started  
**Project:** `gp023_crucial_01`  
**Rubric:** `rubrics/gp023_crucial_01.json`  
**Sealed at:** see `projects/gp023_crucial_01/sandbox_seal.json`

---

## Ground Truth (Division A only)

**GT expression:** `f_true(x1, x2) = x1**3 / (exp(x1/x2) - 1)`

Normalized Planck spectral radiance formula. Guard: if x1/x2 > 500, return 0.0.  
Division A source: `src/ztare/substrates/gp023_crucial_gt.py`

**Evidence grid:**
- Visible: x1 ∈ {0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0}, x2 ∈ {0.5, 1.0, 2.0} — 24 points, clean
- Holdout: same x1 grid, x2 ∈ {0.75, 1.5} — 16 points, clean (unseen x2 values)
- Farther-tail: x1 ∈ {5.0, 6.0, 8.0}, x2 ∈ {0.5, 1.0, 2.0} — 9 points, for post-run evaluation only

**Denylist (Layer a):** Planck, blackbody, black-body, quantum, photon, Bose-Einstein, hv/kT, spectral radiance, Rayleigh-Jeans, Wien, boson, Boltzmann, Planck constant, h=6.626

**Sentinel result:** PASSED — 14 patterns, 0 matches across all Division B artifacts (2026-04-18)

---

## Lakatosian Pass/Fail Criteria (pre-committed before run)

| Outcome | Classification | Evidence |
|---------|---------------|----------|
| Engine recovers `x1^3/(exp(x1/x2)-1)` (or equivalent) with same grammar as GP-080, holdout RMSE < 0.15 | **Progressive programme** — "automated Kepler" earns cross-domain |
| Engine finds a locally-fitting but structurally wrong form (e.g., rational, polynomial); holds out but fails farther-tail | **Underdetermination confirmed on second domain** — same boundary as GP-080 |
| Engine fails to pass holdout gate after 15 iterations | **Degenerating programme** — grammar inadequate for this substrate class |
| Engine passes holdout only after grammar extension (new primitive added) | **Grammar-dependent** — Lakatosian grey zone; "Kepler-for-PK" scope |

The crucial question per GP-083 spec: does the SAME grammar that found a rational form in tacrolimus (GP-080) find the exponential form in this substrate without modification?

---

## Feasibility Notes (Phase 0)

**0.2 Feasibility filter:** The GT is continuous, two-variable, and exhibits a peaked structure. Evidence is uninformative about the exact generating class — a rational form, a log-polynomial, and the true exponential form are all plausible from the visible 24 points. PASS.

**0.3 Identifiability check:** The GT has no free parameters — it is a fixed structural law. The structural form is identifiable (x1^3 in numerator, exp(x1/x2)-1 in denominator). PASS.

---

## Verdict Criterion (pre-committed)

**Primary verdict gate:** Holdout RMSE < 0.15 on `evidence_holdout.txt` (16 clean points at unseen x2).

**Farther-tail discriminator (post-run, not a gate):** Run `eval_farther_tail.py` equivalent after close. If champion passes holdout but diverges at x1=8 (>200% relative error at x2=0.5) → rational basin confirmed. If champion passes farther-tail → exponential form recovered.

**Form recovery verdict:**
- Structural match to `x1^3/(exp(x1/x2)-1)` (by visual inspection or equivalence check) → **True form recovered**
- RMSE < 0.15 but wrong structural class → **Holdout insufficient to discriminate** (same finding as GP-080)

---

## Protocol Compliance

| Phase | Status |
|-------|--------|
| Phase 0: GT selection + feasibility | Complete |
| Phase 1: Division A artifacts (GT, evidence, denylist, sealed_assertions.py, harness_contract.json) | Complete |
| Phase 2: Division A briefing | Complete (project_charter.md) |
| Phase 3: Division B artifacts (charter, rubric, test_model.py, gate_harness.py, thesis.md) | Complete |
| Phase 4: Sentinel gate | PASSED (14 patterns, 0 matches) |
| Phase 5: Domain-expert review | PASSED (rubric-review: 0/5 checks failed, 2026-04-18) |
| Phase 6: Integration tests | PASSED (smoke-test pass, gates valid) |
| Phase 7: Seal | SEALED (sandbox_seal.json written 2026-04-18) |

**Attestation:** All Division B artifacts have been scanned by the sentinel. The domain-expert review is complete. The integration tests pass. This sandbox is sealed.

---

## Run Verdict (2026-04-18)

**Run:** `gp023_crucial_01`, 16 iterations, gemini-2.5-flash mutator, gpt-4.1 judge.
**Cost:** $0.4776 mutator + $0.5318 judge = **$1.01 total**.
**Champion score:** 97/100 (Wien approximation: `p0 * x2^p1 * x1^p2 * exp(-p3 * x1 / x2)`).
**Holdout RMSE:** 0.020 (threshold 0.15) — PASS.
**`is_exponential_class()`:** **False** — farther-tail discriminator fires at x1=6, x2=0.5 (238% error, threshold 200%).

**Lakatosian classification:** **Underdetermination confirmed on second domain** — same boundary as GP-080. Engine finds a locally-fitting but structurally wrong form (Wien, not Planck); holds out but fails farther-tail.

The crucial question was: does the SAME grammar that found a rational form in tacrolimus (GP-080) find the exponential form in this substrate without modification? Answer: the grammar found an exponential form (Wien approximation), but NOT the true transcendental form (Planck law with `exp(x1/x2)-1` denominator). The grammar is not the bottleneck — the data grid is. The visible/holdout evidence (x1 ≤ 4.0) cannot discriminate Wien from Planck. Stage 3 (adding farther-tail data to visible evidence) is the next experiment.
