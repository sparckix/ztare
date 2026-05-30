# GP-090 — Dark Sequence Discovery: A001414 (sopfr) Pre-Registration

> **Seam metadata** · `seam_id:` GP-090 · `track:` substrates · `status:` Sealed - hardened rerun (v2, post cage-fix) · `last_updated:` 2026-05-08


**Filed:** 2026-04-18
**Status:** Sealed — hardened rerun (v2, post cage-fix)
**Project:** `gp090_01`
**Rubric:** `rubrics/gp090_01.json`
**Sealed at:** see `projects/gp090_01/sandbox_seal.json`

---

## Ground Truth (Division A only)

**GT expression:** `z = sopfr(n)` = sum of prime factors of n with repetition (A001414). Also called the integer logarithm or completely additive arithmetic function.

Examples: sopfr(4) = 4, sopfr(12) = 7, sopfr(127) = 127 (prime), sopfr(128) = 14.

The function is discontinuous with large irregular jumps between adjacent values. Primes n give z=n (spike to n from smooth trend). This makes smooth approximations structurally wrong and creates catastrophic failures for any continuous formula at the farther-tail prime spikes (n=127, 131, 137, 139, 149).

Division A source: `src/ztare/substrates/gp090_a001414_gt.py`

**Evidence grid:**
- Visible: n = 2..80 — 79 points
- Holdout: n = 81..115 — 35 points
- Farther-tail region: n ∈ [116, 150] — declared in rubric; contains primes 127, 131, 137, 139, 149 where z=n (catastrophic for smooth models)

**Denylists:**
- `.denylist` (sentinel layer, Division B artifacts): sopfr, prime, factor, factorization, A001414, additive, omega, divisor, prime_factor, sum of prime, arithmetic
- `.thesis_denylist` (named-import cage gate, thesis scanning at runtime): sopfr, A001414, completely additive, additive function, sum of prime factors, Fundamental Theorem of Arithmetic, Big Omega, Omega function, prime factorization, prime factor

**Sentinel result:** PASSED — 11 patterns, 0 matches across all Division B artifacts (2026-04-18, after resetting test_model.py and freezing iter-4 warm-retrieval run)

---

## Prior Run Record (v1 — warm retrieval, operator-stopped)

**Run v1 (2026-04-18):** gemini-pro mutator / gpt-4.1 judge, stopped at iter 4, score 92.

Mutator explicitly cited: "Fundamental Theorem of Arithmetic", "completely additive", "Big Omega", sopfr by name. Judge gave 92/100 — NAMED_IMPORT penalty was rubric-level only and not enforced.

Two apparatus bugs exposed:
1. `autoresearch_loop.py` did not zero `new_eval["score"]` on global gate hard-fail (barking-dog bug)
2. No `named_import_check` gate existed — thesis text was never scanned at runtime

Both bugs fixed 2026-04-18. Frozen artifacts: `projects/gp090_01/_frozen_reference/warm_retrieval_run_01/`

---

## Lakatosian Pass/Fail Criteria (pre-committed before run)

| Outcome | Classification | Implication |
|---------|---------------|-------------|
| Engine reaches holdout-passing formula without any thesis triggering named_import_check | **Pure abduction confirmed on A001414** — engine independently discovered prime-factorization additive structure | Paper-grade finding; Level 3 grammar sufficient |
| Engine repeatedly triggers named_import_check (score zeroed each time) but eventually formulates a derivation from data patterns that avoids named imports and passes holdout | **Forced abduction** — cage redirects warm retrieval to structural derivation | Weaker but real finding; cage is the decisive mechanism |
| Engine cannot find a holdout-passing formula without triggering named_import_check — every passing thesis contains named imports — run terminates at 32 iters | **GCH confirmed on A001414: retrieval is the only available path** | Grammar ceiling on discontinuous prime-dependent sequences; cold finding suitable for paper |
| Engine finds a smooth approximation that passes holdout by luck but fails farther-tail at prime spikes | **Smooth surrogate confirmed** — farther_tail gate correctly rejects | Validates the farther-tail gate design for discontinuous targets |

**Crucial question:** Does the hardened cage (named_import_check scoring 0 on warm-retrieval theses) force the engine to discover sopfr structure from data — or does it just produce 32 iterations of 0-scored warm-retrieval attempts (GCH confirmed)?

---

## Feasibility Notes (Phase 0)

**0.2 Feasibility filter:** sopfr is discontinuous and prime-factorization-dependent. Evidence values are irregular integers. Any smooth formula is structurally wrong. Evidence is partially informative about the additive prime structure (at primes n, z=n is visible). PASS — feasibility filter accepts, but the structural class (additive prime function) is hard to derive from data alone without naming the concept.

**0.3 Identifiability check:** sopfr is uniquely defined by the (n, z) pairs — no parameter degeneracy. The function is not smooth, so fitting parameters are irrelevant. Identifiability is structural, not parametric. PASS.

**Known concern:** The GP-090 substrate is a well-known OEIS sequence (A001414). Any sufficiently capable LLM may retrieve it from training weights. The named_import_check gate is the primary guard against warm retrieval scoring. If retrieval is the only available path, GCH confirmed = the finding.

---

## Protocol Compliance (GP-072 Phase Checklist)

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0: GT selection + feasibility | Complete | Deliberately chosen as "warm target" to stress-test named-import cage |
| Phase 1: Division A artifacts (GT script, evidence.txt, evidence_holdout.txt, .denylist) | Complete | `gp090_a001414_gt.py`, 79 visible, 35 holdout |
| Phase 2: Division A briefing | Complete | `project_charter.md` — no sequence identity, no function name |
| Phase 3: Division B artifacts (charter, rubric, test_model.py, gate_harness.py) | Complete | `generate_substrate.py` output; test_model.py reset to scaffold after v1 run |
| Phase 4: Sentinel gate | **PASSED** — 11 patterns, 0 matches (2026-04-18, post-reset) | |
| Phase 5: Domain-expert review (GP-075 rubric check) | **PASSED** — 0/5 checks failed (2026-04-18) | `projects/gp090_01/workspace/rubric_review_20260418T202551Z.json` |
| Phase 6: Integration tests | **PASSED** — gate_harness produces valid JSON; baseline f(n)=0 correctly fails holdout | |
| Phase 7: Seal | **SEALED** — see `projects/gp090_01/sandbox_seal.json` | |

**New gates active (GP-086 hardening, 2026-04-18):**
- `named_import_check` cage gate: scans thesis text against `.thesis_denylist` on every iteration; hard-fail zeros `new_eval["score"]` if any term matched
- `autoresearch_loop.py` score mutation: hard-fail and soft penalties now correctly applied to `new_eval["score"]` (barking-dog bug fixed — v1 run's 92 would now score 0)

**Attestation:** All Division B artifacts have been scanned by the sentinel. The domain-expert review is complete (GP-075 rubric review: 0/5 checks failed). The integration tests pass. This sandbox is sealed.

---

## Artifact Hashes (at seal time)

| Artifact | SHA-256 (first 16 hex) |
|----------|----------------------|
| evidence.txt | `42952e7f5d959e8e` |
| evidence_holdout.txt | `e8c3524ababc0c82` |
| gate_harness.py | `611f5420e79d52f0` |
| project_charter.md | `f90d83105e399835` |
| test_model.py | `06cc6df16c37d2ff` |
| thesis.md | `10495206d25eeaff` |
| .denylist | `7c68be066796d58b` |
| .thesis_denylist | `609ac4835d17c0ee` |
| rubric (gp090_01.json) | `c6762fb0ec7e7271` |

---

## Run Parameters

- **Mutator:** gemini-pro
- **Judge:** gpt-4.1
- **Iterations:** 32
- **underidentified_after:** 32 (auto-set by experiment-loop from holdout_hard_gate=true)
- **Command:** `make experiment-loop PROJECT=gp090_01 RUBRIC=gp090_01 ITERS=32 MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gpt4.1`
