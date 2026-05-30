# GP-089 — Dark Sequence Discovery: A000009 (q(n)) Pre-Registration

> **Seam metadata** · `seam_id:` GP-089 · `track:` substrates · `status:` Sealed - run not yet started · `last_updated:` 2026-05-08


**Filed:** 2026-04-18
**Status:** Sealed — run not yet started
**Project:** `gp089_01`
**Rubric:** `rubrics/gp089_01.json`
**Sealed at:** see `projects/gp089_01/sandbox_seal.json`

---

## Ground Truth (Division A only)

**GT expression:** `z = round(1000 * ln(q(n)))` where `q(n)` = number of distinct integer partitions of n (A000009).

Log-scaled to produce a smooth monotone integer sequence. The mutator sees only the integer pairs — no functional form, no sequence identity, no scale information.

Division A source: `src/ztare/substrates/gp089_01_gt.py`

**Evidence grid:**
- Visible: n = 3..48 — 46 points
- Holdout: n = 49..65 — 17 points (unseen at run time)
- Farther-tail region: n ∈ [66, 82] — declared in rubric for extrapolation pressure

**Denylists:**
- `.denylist` (sentinel layer, Division B artifacts): partition, distinct, A000009, Hardy, Ramanujan, modular, theta, generating, q(n), OEIS, Rogers
- `.thesis_denylist` (named-import cage gate, thesis scanning at runtime): A000009, q(n), OEIS, Hardy-Ramanujan, Hardy Ramanujan, partition function, number of partitions, distinct partitions, unrestricted partitions, modular form, theta function, Rogers-Ramanujan

**Sentinel result:** PASSED — 11 patterns, 0 matches across all Division B artifacts (2026-04-18)

---

## Lakatosian Pass/Fail Criteria (pre-committed before run)

| Outcome | Classification | Implication |
|---------|---------------|-------------|
| Engine recovers a formula matching all holdout points and farther-tail without naming q(n), Hardy-Ramanujan, or A000009 | **Pure abduction confirmed** — Level 3 grammar sufficient | Discovery-grade finding; the `sqrt_log` primitive structure was independently inferred |
| Engine cites A000009 / q(n) / Hardy-Ramanujan — named_import_check zeroes the score each time — but eventually finds the form without naming it | **Warm retrieval + recovery** — engine initially retrieves but gets forced onto structural derivation | Finding: cage can redirect warm retrieval to genuine derivation under sufficient iteration pressure |
| Engine reaches holdout-passing formula only by naming the function — named_import_check blocks every thesis scoring > 0 until run terminates | **GCH on A000009** — retrieval is the only available path with this grammar | Grammar ceiling confirmed for log-scaled partition sequence |
| Engine fails holdout gate entirely after 32 iterations | **Degenerating programme** — grammar inadequate for this substrate class | Cold finding; Level 3 grammar insufficient for log-scaled partition growth |

**Crucial question:** Can the engine discover the `pi*sqrt(n/3)` asymptotic structure (or its scaled discrete approximation) purely from 46 (n, z) pairs — without the named-import cage triggering?

---

## Feasibility Notes (Phase 0)

**0.2 Feasibility filter:** GT is monotone, log-scaled integer-valued. Evidence is informative about growth rate but not about the specific generating function class. The sequence grows as `pi*sqrt(n/3)` in log scale — this form is *discoverable* from the data but is not a standard polynomial. PASS.

**0.3 Identifiability check:** The log-scaled form has a dominant `sqrt(n)` term with a `log(n)` correction. These are structurally distinguishable in the data range. No parameter degeneracy. PASS.

---

## Protocol Compliance (GP-072 Phase Checklist)

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0: GT selection + feasibility | Complete | |
| Phase 1: Division A artifacts (GT script, evidence.txt, evidence_holdout.txt, .denylist) | Complete | `gp089_a000009_gt.py`, 46 visible, 17 holdout |
| Phase 2: Division A briefing | Complete | `project_charter.md` — no sequence identity, no function name |
| Phase 3: Division B artifacts (charter, rubric, test_model.py, gate_harness.py) | Complete | `generate_substrate.py` output |
| Phase 4: Sentinel gate | **PASSED** — 11 patterns, 0 matches (2026-04-18) | |
| Phase 5: Domain-expert review (GP-075 rubric check) | **PASSED** — 0/5 checks failed (2026-04-18) | `projects/gp089_01/workspace/rubric_review_20260418T202522Z.json` |
| Phase 6: Integration tests | **PASSED** — gate_harness produces valid JSON; baseline f(n)=0 correctly fails holdout | |
| Phase 7: Seal | **SEALED** — see `projects/gp089_01/sandbox_seal.json` | |

**New gates active (GP-086 hardening, 2026-04-18):**
- `named_import_check` cage gate: scans thesis text against `.thesis_denylist` on every iteration; hard-fail zeros `new_eval["score"]` if any term matched
- `autoresearch_loop.py` score mutation: hard-fail and soft penalties now correctly applied to `new_eval["score"]` (barking-dog bug fixed)

**Attestation:** All Division B artifacts have been scanned by the sentinel. The domain-expert review is complete (GP-075 rubric review: 0/5 checks failed). The integration tests pass. This sandbox is sealed.

---

## Artifact Hashes (at seal time)

| Artifact | SHA-256 (first 16 hex) |
|----------|----------------------|
| evidence.txt | `317c42f6d7c3e752` |
| evidence_holdout.txt | `bb485a1b60f69250` |
| gate_harness.py | `611f5420e79d52f0` |
| project_charter.md | `b10884083ae29dc0` |
| test_model.py | `06cc6df16c37d2ff` |
| thesis.md | `df19f122a5768a8f` |
| .denylist | `326336b391146044` |
| .thesis_denylist | `de639b650e6be2dc` |
| rubric (gp089_01.json) | `e792eeeee4050403` |

---

## Run Parameters

- **Mutator:** gemini-lite (gemini-2.5-flash)
- **Judge:** gpt-4.1
- **Iterations:** 32
- **underidentified_after:** 32 (auto-set by experiment-loop from holdout_hard_gate=true)
- **Command:** `make experiment-loop PROJECT=gp089_01 RUBRIC=gp089_01 ITERS=32 MUTATOR_MODEL=gemini-lite JUDGE_MODEL=gpt4.1`
