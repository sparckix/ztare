# Pre-Registration — GP-096 Sandbox 19 (Gag Order Calibration)

**Filed:** 2026-04-19  
**Status:** sealed  
**Protocol:** GP-072 Division A/B  
**GP-075 regime:** calibration (synthetic known-process substrate, not discovery mode)

---

## GT Selection (Phase 0)

**Source:** Shanbhag MTS 2019 test case 3 — "Twin Peaked Spectrum"  
**Data file:** `tests/test3.dat` from pyReSpect-time GitHub repository  
**GT type:** Tabulated empirical data from a synthetic continuous twin-peaked relaxation spectrum.  
**Algebraic form:** None. The generating process is H(τ) = dual-peak continuous distribution → G(t) = ∫ H(τ) exp(-t/τ) d(ln τ). No closed-form symbolic expression exists.

**Phase 0.2 — Feasibility filter:**  
PASS. The G(t) data is uninformative about the specific functional form. A monotonically decreasing G(t) observable is consistent with many functional families (stretched exponential, power law, rational, additive multi-mode). The two-mode Maxwell fit achieves only 49% normalised RMSE on the downsampled data, proving the data does NOT immediately reveal the correct functional class. The mutator is trapped.

**Phase 0.3 — Identifiability:**  
The problem is intentionally underdetermined. Multiple functional forms can fit the visible 20-point window. Discrimination occurs at the holdout gate (t ∈ [1.26, 89.07]) and farther-tail gate (t ∈ [142, 10000]). A two-mode Maxwell cannot pass the holdout gate (RMSE > 100%). A stretched exponential composite or equivalent continuous-distribution surrogate is required.

---

## Division A Artifacts

- `src/ztare/substrates/gp096_sandbox_19_gt.py` — GT module (log-log interpolation of all 40 data points)
- `projects/gp096_sandbox_19_gagorder/evidence_holdout.txt` — holdout set (10 pts, t ∈ [1.26, 89.07])
- `projects/gp096_sandbox_19_gagorder/evidence_farther_tail.txt` — farther tail (10 pts, t ∈ [142, 1e4])
- `projects/gp096_sandbox_19_gagorder/.denylist` — 40 patterns (Layer a + Layer b)

---

## Experiment Design

**Purpose:** Calibration of H-GP103-5 (additive regime compositor) in the G(t) / continuous-decay domain.

**Hypothesis:** PHASE_G1.5 will be forced to trigger because:
1. Single-family fits (power law, pure exponential, simple rational) fail on the holdout
2. Two-mode Maxwell fails by RMSE > 100% on holdout (verified above)
3. The engine must discover an additive bi-modal functional form to pass the holdout gate

**Gag order design:**
- `composition_stagnation_threshold: 8` — Component D (brute-force topology synthesizer) is gagged until 8 stagnation iterations
- `gp103_stagnation_threshold: 0` — H-GP103-5 armed immediately, fires on first differential failure detection
- Rationale: the engine should stagnate on single-family fits for ~5-8 iters, then H-GP103-5 detects differential failure between fast-decay and slow-decay structural families and injects an additive composite seed

**Pass criterion:** Engine proposes f(t) = A·g₁(t) + B·g₂(t) where g₁ captures short-time behaviour and g₂ captures long-time behaviour, achieving holdout normalised RMSE < 0.15.

**Fail criterion:** Engine finds a single-family model that passes holdout (would indicate the problem is easier than expected — update estimate of substrate difficulty) OR engine never exits single-family stagnation within 20 iters (would indicate H-GP103-5 detection logic not triggering on this domain).

---

## Contamination Audit

**Sentinel result:** PASSED — 40 patterns, 0 matches  
**Directory name check:** `gp096_sandbox_19_gagorder` — no GT hints ("gagorder" refers to experiment type)  
**Rubric filename:** `gp096_sandbox_19_gagorder.json` — no GT hints  
**Denylist coverage:** Layer (a) covers all GT-specific terms (Prony, Maxwell, Shanbhag, pyReSpect, test3, twin peak, bimodal). Layer (b) covers domain-class vocabulary (polymer, viscoelastic, rheology, relaxation spectrum, H(τ), inverse Laplace). Known gap: enumeration of Layer (b) is best-effort per GP-072 constraint.

---

## Artifact Hashes (at seal)

| Artifact | SHA-256 |
|---|---|
| `.denylist` | bceac8b8f2e832dfd1a6b926fcc1e84a6c28f81a7da103913775126038561b47 |
| `evidence.txt` | e8f725ccac77e59893f9cd8e700c3a564ac8c8c1109f4dd5f8bc287838b15587 |
| `evidence_holdout.txt` | f4ba95761ae490f6a925d6ff8ea268db44db6ee4be5c25de9fd649da93f6160a |
| `evidence_farther_tail.txt` | fc77ce32190fa41c04dbb030d94e7b8fd4c2eafe4cd8f9bc44ad8c0d389ed668 |
| `gate_harness.py` | c41ff9686cf202e6b0882c2c946674d06473cd219f8705aea72576cead4f067e |
| `rubric` | 100e0096f42f20fe264a034545f24c359aeba0dac5e143b98a03e27df9bef45f |
| `gt_module` | c7c5c1ce8789243229009d715b31a7223ccac36113f436f54a83568104a42cb1 |

---

## Launch Command

```
make experiment-loop PROJECT=gp096_sandbox_19_gagorder RUBRIC=gp096_sandbox_19_gagorder ITERS=20 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
```
