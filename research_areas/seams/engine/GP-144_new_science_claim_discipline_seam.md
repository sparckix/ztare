# GP-144 — New-Science Claim Discipline (Seam)

> **Seam metadata** · `seam_id:` GP-144 · `track:` engine · `status:` draft (no panel; gate designs are orthogonal engineering) · `last_updated:` 2026-05-08


**Status:** draft (no panel; gate designs are orthogonal engineering)
**Owner:** discovery-architecture
**Depends on:** GP-086 (cage/kernel hardening), GP-088 (Ansatz to Prover), GP-122 (Lean REPL integration), INV-10 (seam→spec→impl)
**Triggered by:** 2026-04-24 post-dialogue analysis of ZTARE's induction→ansatz→PSLQ→Lean pipeline. Four specific failure modes identified; each has a clear inversion-derived guardrail.
**Visibility:** private (covers new-science claim procedure — first-mover IP sensitivity)

---

## 1. Problem statement

ZTARE's `make discover` pipeline (GP-088 Ansatz to Prover → GP-122 Lean REPL) can produce formally-verified claims about open mathematical constants / theorems. The pipeline is real, not aspirational. But four specific failure modes can produce CLAIMS THAT PASS EVERY EXISTING GATE YET ARE WRONG. Each must be closed before any new-science claim is submitted externally.

## 2. Why no panel

Unlike GP-143 (kernel integration, where placement / dispatch / gate contract had genuine competing designs), GP-144's four gates are orthogonal engineering concerns with no contested design space. Each gate's design is directly derivable from its failure mode via Munger inversion — "how do we guarantee this fails?" → do the opposite. Popper's contribution is that each gate names its falsification condition BEFORE evidence arrives. Single-voice design is sufficient; debate surface is empty.

## 3. Failure modes and guardrail gates

### 3.1 Gate G1 — `continuum_limit_gate.py`

**Failure mode:** pseudo-singularity in a finite-resolution simulation is mistaken for a PDE singularity in the continuum limit. Numerical blow-ups at grid spacing h routinely disappear at h/2.

**Munger inversion:** run one CFD resolution, extract the blow-up ansatz, Lean-verify the local ODE blow-up, declare continuum-PDE blow-up. Never refine resolution. Never check BKM. Never check Leray scaling.

**Guardrail (opposite):**
- Re-extract candidate at ≥3 resolution levels with refinement ratio ≥2.
- Ansatz's Lean-verified blow-up must persist across all resolutions. Dissolution at higher h is automatic rejection.
- BKM sub-gate: compute `∫₀ᵀ ‖ω(·,t)‖_∞ dt`. Bounded → guaranteed no blow-up (Beale–Kato–Majda 1984). Unbounded → candidate survives.
- Leray-scaling sub-gate: candidate must exhibit self-similar scaling `u(x,t) = (T-t)^{-1/2} U(x / (T-t)^{1/2})`. No such fit → rejected.

**Popper falsifier (pre-registered):** *"If this candidate is a PDE singularity, at resolution h/2 the blow-up time shifts by ≤ ε(h) per the numerical-error envelope, AND the BKM integral diverges at the same rate. Either failure at h/4 → rejected."* Numerical thresholds committed before refinement runs.

### 3.2 Gate G2 — `pslq_falsity_audit_gate.py`

**Failure mode:** PSLQ snaps to a spurious transcendental relation because the bit budget was insufficient for the (dim, dict_size) of the search.

**Munger inversion:** feed 50-bit precision, search 5-dim relations, use a 20-candidate constant dictionary, take the first hit, celebrate.

**Guardrail (opposite):**
- Bit-budget gate (decisive): require `precision_bits ≥ dim · log₂(dict_size) + margin_bits`, margin_bits ≥ 20. Refuse PSLQ invocation if insufficient. Not negotiable; false-positive rate scales as `dict_size^dim / 2^precision`.
- Perturbation stress: inject noise at declared margin_of_safety envelope, rerun PSLQ, check the relation is unchanged. Noise-sensitive → reject.
- Dictionary ablation: rerun with subset dictionaries. Real relations collapse to a minimal subset cleanly; false positives appear only under the maximal dictionary.

**Popper falsifier:** *"If this PSLQ relation is real, then (i) it survives margin_of_safety perturbation; (ii) it appears when we drop the least-likely constants; (iii) the bit budget exceeded `dim · log₂(dict_size) + 20` at detection. Any failure → false-positive."*

### 3.3 Gate G3 — `ansatz_survivor_gate.py`

**Failure mode:** system chases a low-residual ansatz that happens to be a local minimum specific to one extraction path, ignoring structurally-different candidates that would lead to simpler Lean proofs.

**Munger inversion:** take the ansatz with lowest residual; commit; run 50 iterations; never test alternates.

**Guardrail (opposite):**
- Top-K Lean attempt: submit top-5 (not top-1) to Lean. Selection pressure is proof-shortness, not residual.
- Independent-pipeline agreement: re-extract from (a) disjoint time window, (b) different IC perturbation, (c) different solver library. ≥3 agreeing pipelines → champion. Disagreement → reject all three (path-dependent).
- Adversarial basis reformulation: adversarial agent proposes functionally-equivalent ansatz in a different basis. Both Lean-prove same theorem → structure is real. Only original works → fitted to its own basis.

**Popper falsifier:** *"If this ansatz is decisive, then its Lean proof is shortest among top-5 AND it is recovered by ≥3 independent extraction paths AND an adversarial basis reformulation preserves the verified theorem. Any failure → residual-minimum was coincidental."*

### 3.4 Gate G4 — `proof_surveyability_gate.py`

**Existing work: gp139_lean_hardening champion (score 87).** Addresses `sorry`/axiom-smuggling, kernel-guarantee vs statement-fidelity gap. Reuse as G4's implementation backbone; extend with surveyability overhead (length/sketch/reviewer) rather than reimplementing.

**Failure mode:** Lean proof compiles but is unsurveyable (50,000 lines of case analysis, custom axioms, unfixed `sorry`s). Committee rejects despite formal validity.

**Munger inversion:** emit any-length proof that compiles; dismiss `sorry`s as minor; no human-readable sketch.

**Guardrail (opposite):**
- Axiom allowlist: compile only under whitelisted axiom set (Mathlib core). No `sorry`. No custom axioms. Constructive by default; classical opt-in only with justification.
- Proof-length vs sketch requirement: proof > 500 tactical lines → require machine-authored sketch whose structure corresponds to proof structure 1-to-1 (not just summary).
- Adversarial peer-reviewer persona: simulated "Clay committee member, 30-min budget" must be able to reconstruct the decisive moves from the sketch. Failure = unsurveyable → rejected.

**Popper falsifier:** *"If this proof is committee-grade, it compiles under the whitelisted axiom set AND its sketch is reconstructable by an adversarial 30-min reviewer AND proof structure corresponds to sketch structure 1-to-1. Any failure → verified but not acceptable."*

## 4. Meta-gate: the Munger lollapalooza (kernel-phase-correct layering)

**Correction 2026-04-24:** earlier drafts of this seam used "Phase D" loosely (per Gemini-Pro's external framing) to mean "claim-pipeline gates." In the actual ZTARE kernel, Phase D is specifically the **INV-3 layer3_exclusive Ansatz-to-Prover** step (`autoresearch_loop.py`'s deterministic `test_model.py` writer, which consumes Phase C's fit output and writes a def-f() harness with the LLM physically barred). The GP-144 gates therefore do not replace Phase D — they live AROUND and INSIDE the real kernel phases at specific insertion points.

Correct mapping of GP-144 gates onto real kernel phases:

### Phase C — Admission (is this even a law?)

Driven by the ztare_on_ztare score-92 champion family and its hardening projects (gp135 + gp136 + gp137 + gp138). Operates on candidates produced by compress_champion / fit_primitive. Filters out:
- **C1. Compressibility** — pMDL / NML / CTW. Hardened by gp136_pmdl_hardening (score 90).
- **C2. Statistical purity** — Tracy-Widom edge test on residuals. Note: gp137_tw_replacement champion (score 77) confirmed the original TW gate is circular under operator-declared class; replacement is weaker than hoped. Use with caveats; may be replaced.
- **C3. Physical reality** — Noether symmetry verification. Hardened by gp138_noether_g_selection (score 97).

A candidate passing Phase C earns the status "law-shaped" — it survives admission-layer filters.

### Pre-Phase-D gate — G3 Ansatz Survivor (upstream of kernel Phase D)

G3 fires BEFORE Phase D ingests the champion ansatz. Phase D's INV-3 writer accepts one ansatz and produces the deterministic harness; G3 is the selection pressure on WHICH ansatz Phase D receives.

- **G3. Structural robustness** (`ansatz_survivor_gate.py`) — proof-shortness selection among top-K Phase-C survivors + ≥3 independent extraction paths + adversarial basis reformulation. Insertion point: before `_write_layer3_stub` / before the Phase D INV-3 writer consumes the chosen ansatz. Upstream of `test_model.py` writing.
- **Cousin of M-form alignment audit** (ztare_on_ztare Evidence Set C category 5); this is its generalization to the new-science claim surface.

### Inside Phase D — G1 and G2 land as deterministic checks INSIDE the written test_model.py

The kernel Phase D is specifically the `INV-3 layer3_exclusive` contract: deterministic `def f()` writer, LLM physically barred. GP-144's G1 and G2 extend what the INV-3 writer emits.

- **G1. Continuum reality** (`continuum_limit_gate.py`) — resolution refinement, BKM integral, Leray scaling. Insertion point: invoked BY the INV-3 writer when it builds `test_model.py` for a PDE-class candidate. The gate is a module; the Phase D writer calls it; its pass/fail assertions become part of `test_model.py`'s deterministic harness. **Implementation constraint (layer 4 of RMS Chaos Trap enforcement, 2026-04-24):** G1's deterministic check MUST encode the ban on trajectory-level RMS fitness metrics for any substrate whose declared λ_max > 0. The gate refuses to admit a thesis whose Method-A fitness rule violates `T · λ_max ≤ 5`. Canonical reference: `docs/concepts/chaos_substrate_primitives.md` Principle 1.
- **G2. Algebraic reality** (`pslq_falsity_audit_gate.py`) — bit budget, perturbation stability, dictionary ablation. Insertion point: invoked BY the INV-3 writer when the ansatz carries PSLQ-derived closed-form constants. Same pattern: gate module called by the writer, assertions materialized in `test_model.py`.

The INV-3 prohibition against LLM-written `def f()` extends naturally to G1 and G2: these gates are deterministic Python, called deterministically by the Phase D writer, with no LLM in the loop.

A candidate passing Phase D's extended harness (including G1/G2 assertions) earns the status "claim-grounded" — the claim is about the mathematical object, not a numerical artifact, and the deterministic test_model.py enforces this.

### Inside Phase D extensions absorbed from gp147 meta-validation (added 2026-04-24)

The gp147_gate_discovery_validation run (iter 2 score 88, iter 5 score 88) independently rediscovered G1 and G2 AND proposed four additional failure modes the operator had not included in the original GP-144. These are adopted as extension gates on the Phase-D-writer output; all fit the same pattern as G1/G2 (deterministic check, INV-3-compliant, called by the Phase-D INV-3 writer, assertions materialized in test_model.py):

- **G5. Translation semantic drift** (`translation_diff_gate.py`) — during `lean_compiler` translation from apparatus output to Lean 4, no symbol is silently swapped (π' vs π, ζ(3) vs ζ'(3), etc.). gp139 guarantees kernel soundness but not semantic identity of the input vs. output statement. Falsifier: hash-canonicalize the pre-translation expression and the post-translation Lean statement; any symbol substitution changes the hash and the gate rejects.

- **G6. Hidden domain-restriction injection** (`domain_match_gate.py`) — translator must not silently add side-conditions (e.g., "x≠0", "assume convergent") that make the theorem true but NARROWER than the intended claim. Falsifier: pre-register the domain scope in the pre-translation artifact; post-translation, enumerate all `⊢`-free hypotheses introduced and reject if any new hypothesis is present that was not in the pre-registered scope.

- **G7. Ensemble ambiguity** (`ensemble_ambiguity_gate.py`) — when Phase-C produces multiple candidates that all pass admission (near-tied scores), the Phase-D writer MUST surface the ensemble rather than silently selecting one. Falsifier: if the candidate set emitted to Phase D has ≥2 members with scores within margin_of_ambiguity (rubric-declared, default 5% of top score), the gate requires explicit operator-facing reporting of all members. Selecting silently is rejected.

- **G8. Coordinate invariance lapse** (`coordinate_invariance_gate.py`) — for substrates declared coordinate-invariant (chaotic dissipative ODEs, number-theoretic constants, topological objects), Phase D must verify the claim's numeric value is invariant under the expected transformation class (C¹ diffeomorphism for chaotic ODE attractor invariants; scale-and-shift for conjecture-refinement; etc.). Falsifier: apply the declared transformation group to the underlying substrate; recompute; reject if the claim's numeric changes beyond declared tolerance.

**Credit:** gp147 meta-validation run, iter 2 (88) and iter 5 (88), mutator o3, judge o3. Gates G5/G6 address the specific Lean-kernel-vs-semantic-identity gap that gp139_lean_hardening does not cover. G7 addresses the candidate-selection silent-bias problem. G8 generalizes the coordinate-invariance requirement from gp140 v2.4 charter into a claim-pipeline gate.

### Post-Phase-D — G4 Surveyability (before external submission)

After Phase D's deterministic harness passes and (if applicable) GP-122 Lean REPL compiles the proof, G4 fires before any external submission.

- **G4. Surveyability** (`proof_surveyability_gate.py`) — axiom allowlist (inherits gp139_lean_hardening score-87 backbone) + proof-length vs sketch requirement + adversarial 30-min reviewer persona. Insertion point: post-`make discover` pipeline, pre-submission wrapper.

A candidate passing G4 earns the status "submission-ready."

### Sequencing (kernel-phase-correct)

```
Phase C admission (gp136/137/138) → G3 ansatz_survivor → kernel Phase D INV-3 writer
     ↓                                                      ↓
"law-shaped"                                          test_model.py with G1 + G2 assertions
                                                            ↓
                                                    deterministic harness passes
                                                            ↓
                                                    (optional) GP-122 Lean compilation
                                                            ↓
                                                    G4 surveyability
                                                            ↓
                                                    "submission-ready"
```

Failure at any point rejects the claim. No phase can be bypassed. No retroactive re-entry after failure unless the candidate is materially modified (re-enters at Phase C).

### What this resolves

- Earlier drafts of this seam conflated Gemini-Pro's external "Phase D = Millennium Sieves" with the kernel's "Phase D = INV-3 layer3_exclusive." These are different referents. Now corrected.
- G1 and G2 do not replace Phase D; they extend what the Phase D INV-3 writer materializes into test_model.py.
- G3 is upstream of Phase D (selection pressure on ansatz input).
- G4 is downstream of Phase D (post-Lean, pre-submission).
- gp139_lean_hardening (score 87) remains G4's backbone — no re-implementation.

Credit: Gemini-Pro for the functional layering intuition; operator for the INV-3 / Phase-D naming-collision catch.

## 5. Self-application requirement (MANDATORY — blocks gate-stack trust)

Before the gate stack is trusted for any real claim, run ZTARE end-to-end against a **GT-known synthetic substrate** and let the GP-119 Inverter try to push false positives past all four gates. This is the reflexive-audit generalization of GP-105 M-form alignment to the new-science pipeline.

Companion substrate: **GP-146 — gate_stack_validation**. Lives at `projects/gp146_gate_stack_validation/` (not yet created; triggered when gates are implemented).

### 5.1 Target substrate choice (GP-146)

Pick a problem whose closed form is MATHEMATICALLY KNOWN so we have ground truth for "was the claim right?" Candidates:

1. **Arnold cat map Lyapunov exponent.** λ₁ = log(φ²) = 2·log((1+√5)/2) ≈ 0.9624. Closed form proven since Arnold-Avez 1968. Pure algebraic number; PSLQ target well-defined.
2. **Tent map Lyapunov.** λ = log 2. Trivial but zero-false-positive testbed.
3. **Shift map Lyapunov.** λ = log k for k-symbol shift. Exact, parameterized.

Use Arnold cat map as primary; tent/shift as degenerate negative controls (anything that claims ≠ log 2 on the tent map is a stack failure).

### 5.2 Adversarial injection protocol

The Inverter (GP-119) runs three injection attempts per gate:
- **Against G1 (continuum):** inject a numerical pseudo-singularity constructed at single resolution; verify G1 rejects on refinement failure.
- **Against G2 (PSLQ):** inject a low-precision PSLQ output claiming a relation (π, e, ζ(3), γ, Catalan) at 40-bit precision; verify G2 rejects on bit-budget violation.
- **Against G3 (ansatz):** inject a low-residual ansatz that Lean-proves a long theorem vs a competitor with shorter proof; verify G3 selects the shorter.
- **Against G4 (surveyability):** inject a proof with `sorry` cleared via `axiom sorry_placeholder : …`; verify G4 rejects on axiom-allowlist violation.

Each attempt MUST be rejected by its target gate. Any attempt that passes = gate insufficient → patch, retest.

### 5.3 Acceptance criterion for gate-stack trust

All four gates reject every corresponding injection attempt AND the Arnold cat map true answer (λ = 2·log(φ)) passes ALL four gates end-to-end (G1 trivially as there's no PDE limit, G2 with adequate bit budget, G3 as the shortest-proof candidate, G4 with Mathlib-only axioms).

Failure at any step → gates do not ship.

### 5.4 Sequencing

GP-146 runs BEFORE GP-145 (SAW) attempts its Lean submission. Order:
1. Gates implemented (triggered when GP-145 score ≥ 85)
2. GP-146 self-application validation (must pass)
3. GP-145 claim submitted through the validated gate stack
4. Any external submission (arXiv, journal) only after GP-146 has passed

Inverting this order is forbidden — an unvalidated gate stack trusted for a real claim is a structural risk, not a time-saver.

## 6. Spec deferral

Gates are not specified or implemented yet. Spec for each gate lands when:
- At least one conjecture-refinement substrate (GP-145 SAW or successor) reaches score ≥ 85 on the aggressive-judge rubric v2.1.
- The champion at that score attempts Phase-D Lean compilation.
- The gate stack becomes decisive at that moment.

Pre-work now: this seam documents the design. Per INV-10, no gate implementation until spec; no spec until promotion trigger.

## 7. Companion substrate: GP-145 SAW connective constant μ_sq

The conjecture-refinement target that will stress-test the gate stack is GP-145 (2D square-lattice self-avoiding-walk connective constant). Substrate lives at `projects/gp145_saw_mu_square/`. Seam-level dependency: GP-144 gates should be implementation-ready by the time GP-145 reaches promotion, so the first real claim goes through the full gate stack.

## 8. What this seam is NOT

- Not a kernel-integration seam (that's GP-143).
- Not a new substrate spec (that's GP-145).
- Not a rubric change (rubric v2.1 already shipped 2026-04-24).
- Specifically: a pre-registered description of four failure modes + gate designs + Popper falsifiers, to be implemented when triggered by a substrate actually attempting new-science claim.

## 9. SUPERSESSION — Gate G3 (ansatz survivor) → leanmill (2026-06-07)

Gate G3 (`ansatz_survivor_gate.py`, §3.3) was a SPECULATIVE SHELL blocked on "live Lean compilation pipeline / GP-122 lean_repl." That blocker is now RESOLVED by **leanmill**: `ztare.leanmill.solver.solve_adhoc` is the live kernel-verified Lean pipeline, and G3's core idea — *"pick the SHORTEST verifying proof among top-K"* (short proof = structural correctness, not path-fitting) — is **already shipped** as `ztare.leanmill.solver.family_lemma_library.mdl_shortest` (the MDL description-length proof-form selector). So G3 should NOT be built out in the gates layer; any real ansatz-shortest-proof selection routes through leanmill. The gate is marked SUPERSEDED in its docstring but left registry-WIRED as a benign advisory shell (`proof_surveyability` declares a dependency on it; `tests/integration/test_gate_engagement.py` asserts its ordering) — fully removing it is a separate gate-engagement refactor (drop the dependency + update the test), deferred. The G3 *independent-extraction-paths* and *adversarial-basis-reformulation* legs (§3.3) remain genuinely unbuilt and are NOT superseded by leanmill — only the Lean-shortest-proof selection is.
