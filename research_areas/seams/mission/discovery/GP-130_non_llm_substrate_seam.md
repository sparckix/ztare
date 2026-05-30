# GP-130 — Non-LLM Substrate in the ZTARE Loop

> **Seam metadata** · `seam_id:` GP-130 · `track:` mission · `status:` Open - debate seam, not a spec. · `last_updated:` 2026-05-08


**Status:** Open — debate seam, not a spec.
**Parent:** GP-129 Seat 8 (Hong–Page faux-diversity) — this seam is the concrete follow-up.
**Related:** GP-128 (persistent manager agent).
**Date opened:** 2026-04-23.

---

## Eigenquestion

**When does adding a non-LLM substrate (symbolic solver, SMT engine, theorem prover, deterministic verifier) to the ZTARE loop earn its keep, and where would it actively hurt?**

The question is NOT "are LLMs bad at math / logic." It is: **given that Claude + Codex + Gemini share training lineage and RLHF, what class of errors will they correlate on, and which of those errors become decisive as the research portfolio matures?**

---

## What problem this solves

GP-129 Hong–Page seat predicted: three transformer-RLHF agents will fail in correlated ways on certain prompt classes (sycophancy, authority-frame, out-of-distribution formal reasoning). Cross-checking between them detects shallow errors and misses correlated deep errors. The faux-diversity is invisible from inside the loop because every agent confirms.

The fix is not "add a fourth LLM." It is **add an agent whose error mode is structurally uncorrelated** with transformer RLHF output. Deterministic symbolic systems — Lean, Z3, dReal, Coq, Prolog-style checkers — fail by **refusing to prove**, not by **generating plausible-looking falsehoods**. Their null output is informative in a way that an LLM's hedge is not.

---

## Candidate trigger classes (where the non-LLM substrate would earn its keep)

Ordered by expected first-cycle value.

### 1. Theorem-claim verification — **highest value**

A formal theorem claim has a shape: "method comprising step A, then step B, characterized by invariant I." We already have falsification thresholds via pre-registration. But we do not have a **machine-checkable formal statement of the claim**. If we did, a Z3 / Lean encoding could exhaustively check whether the claimed invariant holds on a canonical model, or produce a counterexample.

- **Trigger:** before publishing any decisive claim.
- **What the non-LLM substrate produces:** either `UNSAT` (the negation is unsatisfiable → invariant holds within the model) or a counterexample.
- **Failure mode of the LLM loop without it:** all three agents "verify" the claim by re-stating it in plausible language. The counterexample is never found because the agents never tried to find one — they tried to explain why the claim holds.
- **Estimated adoption cost:** non-trivial but bounded. Each claim would need a one-time formal encoding (≤1 day per claim). Z3 / Lean check runs in seconds once encoded.

### 2. Identifiability proofs for GT / grammar candidates

Sandbox_06 (project memory: `project_sandbox06_identifiability_degeneracy.md`) burned a cycle because the (α, β) parametrization was rank-5-not-6 and the pre-commit bootstrap passed the wrong property. LLM review did not catch it. A symbolic-rank check on the Jacobian (or a Gröbner-basis test for parameter-separability) would have caught it before the run.

- **Trigger:** any new GT template before committing to a run.
- **What the substrate produces:** rank of the parameter Jacobian; dependency structure among parameters.
- **Cost:** SymPy / Mathematica / Macaulay2, no specialized deployment needed.

### 3. Grammar-ceiling certification

GP-085 (grammar-ceiling hypothesis) says: for a given GT, there exist targets outside the grammar's reachable span. This is currently asserted heuristically. A symbolic search over grammar expansions up to depth D would **prove** a target is outside the reachable span up to that depth, or find the path. This is a small finite combinatorial problem — the natural fit for a BFS with memoization, not an LLM.

### 4. Invariant checking for synthesized code

Before Codex lands production code that touches the autoresearch_loop or the grammar machinery, a lightweight property-based test harness (Hypothesis) plus a handful of formal postconditions could catch whole classes of regressions that code review misses. This is closer to "better tests" than "formal verification," but it IS a substrate whose failure mode (property falsified with a concrete counterexample) is uncorrelated with LLM failure modes.

---

## Where the non-LLM substrate would HURT

Inversion required by GP-129 — every frame must name its catastrophic failure mode.

### 1. False confidence from trivial `UNSAT`

A Z3 proof of an invariant on a toy model is cheap and feels authoritative. But if the encoded model is a simplified cartoon of the real system, the `UNSAT` certifies only the cartoon — while the prose report says "verified." This is the **lean-on-formalism trap**: the formal tool's deterministic output launders a modeling gap into apparent proof.

**Defense:** formal encoding must be reviewed against the system with the same scrutiny as the claim. The encoding becomes its own auditable artifact; it does not inherit the claim's trust.

### 2. Encoding cost exceeds value

Theorem-prover formalization in Lean / Coq can take weeks per claim. If the claim only matters for one publication, that investment does not amortize. The budget calculation is trivially wrong if we treat "ZTARE has formal verification" as a prestige feature — correct only when the encoding pays for itself in catching at least one real error, or when the encoded artifact is reused across claims.

**Heuristic:** adopt the lightest-weight substrate that could have caught the last known error. Start with SymPy rank checks (free). Escalate to Z3 SMT (hours of encoding per claim) only when SymPy leaves a gap. Lean / Coq only when a specific invariant is decisive across ≥5 cycles.

### 3. Ontological drift — the substrate's formalism becomes the territory

Munger's "man with a hammer" applies in reverse here. Once we have a formal substrate, there is pressure to express every claim in its vocabulary — and claims that resist formalization get demoted ("can't prove it, therefore less important"). Some of the most decisive research intuitions are NOT formalizable yet. Adopting the formal substrate as arbiter silences those.

**Defense:** formal substrate produces evidence, not verdicts. A claim that resists formalization is flagged, not demoted.

### 4. Adversarial gaming the verifier

Per the rubric-as-eval memory (`project_rubric_as_eval.md`): any formal spec an optimizer satisfies gets gamed toward satisfiability. If Claude / Codex know the Z3 check is in the loop, they will generate claims shaped to pass Z3 rather than claims shaped to be true. This is the GP-085 × GP-072 surface repeating at the formal layer.

**Defense:** hold the encoding separate from the claim generator. The role producing the claim must not see the encoding; the role producing the encoding must not see the claim's provenance. Cross-role information isolation (GP-072) extended to the formal substrate.

---

## Non-LLM substrate candidates — decisive profile

| Substrate | Best fit | Cost | Correlation with LLM errors |
|---|---|---|---|
| SymPy / NumPy symbolic | rank checks, identifiability, algebraic manipulation | zero deploy, minutes per claim | essentially uncorrelated on numeric invariants |
| Z3 / cvc5 (SMT) | theorem-claim invariants, grammar-ceiling under depth D, scheduling | hours-to-days encoding per claim | uncorrelated on structural logic |
| dReal | nonlinear real arithmetic, ODE-constrained claims | hours encoding, seconds to run | uncorrelated on analytical bounds |
| Lean / Coq | decisive theorems reused across claims | weeks encoding, seconds to run | uncorrelated but high overhead |
| Hypothesis (property-based) | code-level invariants | hours per module | partial correlation (property is still LLM-written) |
| Custom BFS / dynamic-programming search | grammar reachability under depth D | bespoke, 1-2 days per grammar | uncorrelated (deterministic) |

---

## Strippable at the principle layer?

Every concrete tool above is an instantiation. The principle — "introduce a deterministic checker whose null output is informative" — strips cleanly. What matters is **failure-mode orthogonality**, not the specific tool. Any substrate satisfying (a) deterministic, (b) refuses cleanly when unable to prove, (c) failure independent of transformer-RLHF biases would qualify. This means future substrates (quantum-classical verifiers, formal coalgebra tools, whatever) slot into the same role.

---

## Falsifiable predictions

If a non-LLM substrate is added at the publication / decisive-claim gate:

1. **At least one claim gets caught with a modeling error the LLM trio did not flag, within the first 5 uses.** If 5 uses pass without a substrate-caught issue, the value hypothesis is weakened — the LLM trio may be catching the errors we expected the substrate to catch.
2. **Encoding time per claim stabilizes under 4 hours by claim #3.** If encoding time grows, the substrate is the wrong abstraction level for the claim family.
3. **Cross-role information isolation (per GP-072) survives substrate adoption.** If claim-generators start shaping output for the Z3 check, adoption is net-negative and the substrate should be sequestered from the claim generator's awareness.

---

## Proposed first move (when you want to pilot)

**Start with SymPy Jacobian rank + Gröbner-basis identifiability checks in the GT pre-commit bootstrap**. Zero infrastructure, low encoding cost, directly motivated by the sandbox_06 failure we already paid for. Cycle time: one afternoon to wire up, one GT candidate to validate.

If that catches a real identifiability issue, escalate to Z3 encoding for at least one decisive claim. If Z3 encoding stays bounded, keep it in the loop. If the encoding bloats, retreat to SymPy-only and log the gap.

Do NOT start with Lean. The activation energy is an order of magnitude higher than the expected value at this stage.

---

## Open items

- [ ] Principal review of trigger classes — any to add or de-prioritize?
- [ ] Scope a SymPy rank-check harness as a supervisor pre-commit (~1 afternoon of engineering) — candidate first concrete artifact.
- [ ] Verify trigger discharges: theorem-claim verification IS the operational handoff between this seam and the publication/closure gate.
- [ ] Revisit after first real use: did the substrate catch anything the LLM trio missed? If no, escalate OR retreat rather than maintaining overhead.
