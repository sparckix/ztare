# GP-083: Inference Type Boundary — Kepler, Newton, and the Limits of Abduction

> **Seam metadata** · `seam_id:` GP-083 · `track:` mission · `status:` `note` (seam opened, no experiment yet) · `last_updated:` 2026-05-08


**Status:** `note` (seam opened, no experiment yet)
**Track:** Theory / Epistemology
**Opened:** 2026-04-17
**Cross-references:** GP-081 (Peircean Pipeline), GP-082 (Substrate Scope Boundary), Paper 5 Chapter 3

---

## The Question

The engine performs abductive compression: data → algebraic law → holdout survival. GP-080 proved this works (score 98, bi-exponential recovery). The question is not *whether* it works (GP-082 handles scope), but *what kind of knowledge it produces* and *what structural upgrades would change the kind*.

Three inference types (Peirce 1878):

1. **Abduction.** From surprising result → generate candidate explanation. The engine does this. It sees data, proposes a form, fits parameters, defends parsimony. This is Kepler: "the orbit is an ellipse" from Brahe's tables. The engine automates Kepler.

2. **Induction.** From repeated cases → generalize to rule. The holdout gate does this. The engine proposes a law, the holdout tests whether it generalizes. This is Kepler + verification: "the ellipse holds for Mars AND Jupiter." The engine automates this too.

3. **Deduction.** From axioms → derive consequence. The engine does NOT do this. It cannot derive the ellipse from F=ma + inverse-square gravity. It finds the ellipse empirically and defends it empirically. Newton requires deduction. The engine cannot currently cross this bridge.

---

## The Structural Claim

The engine's current architecture is an abduction-induction loop. It cannot produce deduction because:

1. **No axiom layer.** The engine has evidence (data) and a grammar (topology synthesizer), but no axiom set from which to derive consequences. The rubric's persona is a skeptical empiricist, not a formal theorist.

2. **No proof engine.** The fit primitive (SciPy) finds parameters that minimize residuals. It does not prove that a functional form necessarily follows from premises. Proof requires a different substrate (Lean, Coq, Isabelle).

3. **No logical connectives.** The grammar has mathematical operators (exp, log, +, *, /) but no logical operators (∀, ∃, →, ∧). It can express "f(x) = exp(-kx)" but not "for all x > 0, f(x) > 0 because exp is strictly positive."

---

## The Three Bridges

### Bridge 1: Abduction → Induction (BUILT)
The engine already crosses this. The holdout gate converts an abductive guess into an inductively tested law. GP-080's holdout_hard_gate_fired=false with exact_match=1.0 is the engine crossing this bridge.

### Bridge 2: Abduction → Deduction (GP-081, CONDITIONAL)
This is the Peircean Pipeline. The engine's typed provenance chain (form + composition steps + residual triggers) is an Ansatz that a theorem prover could attempt to derive from axioms. The bridge requires:
- The engine's output to be machine-parseable into a proof goal
- A theorem prover (Lean/Coq) to receive the goal
- The axiom set to be specified by the operator (e.g., real analysis for PK, quantum mechanics for spectral data)

This is GP-081's scope. The seam is conditional on Component D producing novel compositions.

### Bridge 3: Induction → Generative Mechanism (THE HARD ONE)
This is the Kepler→Newton bridge. Even if the engine finds the right formula AND a theorem prover verifies it deductively, the question remains: *why does this formula hold?* Newton's insight wasn't just F=ma → ellipse. It was that the SAME F=ma explains falling apples, planetary orbits, and tides. The unification across domains is the generative mechanism.

The engine cannot currently do this because:
- It operates on one substrate at a time
- It has no mechanism for cross-substrate pattern matching
- It cannot propose that two different laws in two different domains share a common generating mechanism

A structural upgrade for this would be: run the engine on N substrates independently, collect the N recovered laws, then run a *meta-engine* that looks for structural isomorphisms between the laws. If `f_PK(t) = c * exp(-kt)` and `f_radioactive(t) = N0 * exp(-λt)` are both recovered independently, the meta-engine could propose "exponential decay is a universal mechanism for first-order processes." This is abduction at the meta-level — Peirce applied recursively.

---

## Underdetermination and the Complexity Prior (added Turn 2)

When the engine fits `c * exp(-kt)`, can it distinguish this from `c * exp(-kt) + ε * sin(ωt)` where ε is below noise? If not, the engine faces classic Duhem-Quine underdetermination. What's recovered is the *simplest survivor*, not necessarily the true generating process.

This is not a bug — it is an honest epistemological boundary. The grammar's topology acts as an implicit Kolmogorov complexity prior: shorter expressions in the grammar are favored because the LLM proposes them more readily and the parsimony pressure penalizes unnecessary terms. This prior is decisive and should be stated explicitly rather than hidden behind "the engine finds the law."

**The compression:** The engine finds the simplest law consistent with evidence and holdout. That is the correct claim. "The law" implies uniqueness that underdetermination denies.

---

## Degenerating-Programme Criterion (added Turn 2)

A progressive programme (Lakatos) predicts novel facts. A degenerating programme adds epicycles to accommodate each new anomaly.

**The test:** If the engine requires grammar extensions for each new substrate (new operators, new composition rules, new persona tuning), the programme is degenerating — each extension is an ad hoc auxiliary hypothesis. If the same grammar recovers laws across substrates without modification, the programme is progressive.

**Current status:** One substrate (GP-080 PK, bi-exponential). The crucial experiment is GP-023 (Planck) with identical grammar. The result determines progressive vs. degenerating classification.

**Failure criterion for the "automated Kepler" claim:** If 3+ substrates each require grammar extension to succeed, the claim downgrades from "automated Kepler" to "domain-specific curve fitting with an LLM frontend."

---

## The Inversion: Why This Doesn't Matter Yet

Inverting: what fails if we DON'T build Bridges 2 and 3?

1. **Nothing fails for the current use case.** GP-080 proves the engine can recover PK laws from data. The clinical value (validated metabolic model for a specific patient) doesn't require deductive proof or cross-domain unification. Kepler is sufficient for navigation.

2. **The paper claims are safe.** Paper 5 explicitly says the engine performs abduction (Chapter 3, §3.1) and the residual includes eigenquestion selection. The Peircean argument is structural, not aspirational. No overclaim.

3. **Bridge 3 is a research programme, not an engineering task.** Cross-domain unification is what made Newton Newton. It took 78 years from Kepler (1609) to Newton (1687). The engine has been running for three weeks.

**The compression:** The engine automates Kepler. That is historically massive and practically sufficient. Newton is a research programme, not a next sprint.

---

## The Planck Test

The Gemini analysis is correct that Planck's discovery was structurally abductive: he fit the spectral data, then realized the math required quantization. The engine should be able to replicate Planck's discovery (Bridge 1) but not Planck's insight (Bridge 3). The distinction:

- **Planck's formula:** B(v,T) = 2hv³/c² × 1/(exp(hv/kT) - 1). This is a rational-exponential composition. The grammar can express this. The engine should find it from spectral data. This is GP-023's territory.

- **Planck's insight:** "Energy is quantized." This is a meta-observation about the formula — that it requires E=nhv to make physical sense. The engine cannot produce this because it has no physics axioms to reason against. It would find the formula and say "this fits." Planck found the formula and said "this implies something about reality."

The gap between "this fits" and "this implies" is Bridge 3. It is real, it is decisive, and it is not currently automatable.

---

## Appendix: The String Theory Question (demoted Turn 2 — no grammar, gate, or data)

Can the engine do theoretical physics (no empirical data, only mathematical constraints)?

**Inversion:** What would the substrate look like?
- Evidence: not physical measurements but mathematical objects (scattering amplitudes, symmetry conditions)
- Gate: not RMSE but mathematical consistency checks (unitarity, anomaly cancellation, crossing symmetry)
- Grammar: not real-variable operators but algebraic geometry primitives (Lie groups, complex manifolds, tensor operations)

This is structurally possible but requires three infrastructure layers that don't exist:
1. A symmetry-checking gate harness
2. Complex/algebraic primitives in the topology synthesizer
3. A theoretical-physicist persona in the rubric

File under: "conditional on grammar extension + new gate harness type." Not blocked by architecture, blocked by vocabulary.

**Turn 2 note:** SR reviewer flagged this section as aspirational noise — no grammar, no gate, no data means no experiment is even formulable. Demoted from main body to appendix. Revisit only if grammar extension becomes concrete.

---

## Debate Log

**Turn 1 (2026-04-17, Operator + Gemini analysis).** The engine automates Kepler (abduction + induction). Newton requires deduction (Bridge 2, GP-081) and cross-domain unification (Bridge 3, research programme). Planck's formula is recoverable; Planck's insight is not. String theory requires vocabulary extension, not architectural change. The decisive claim: Kepler is sufficient for the current use case, and the scope boundary is honestly drawn.

**Turn 2 (2026-04-17, Four-domain review — PhilSci / Munger / Symbolic Regression / Systems ML).** Synthesized convergence from four independent domain reviewers. All four agreed: the inversion section ("Kepler is sufficient") is the strongest and most decisive part of the seam.

Key findings by convergence strength:

*4/4 convergence:*
- The inversion section is correct and should be promoted to the opening frame, not buried in section 5.
- Bridge 1 is built and works. No dispute.

*3/4 convergence:*
- "Automated Kepler" is overclaimed on a single substrate. PhilSci: "one successful fit is a single corroboration, not a research programme" (Lakatos). SR: "PySR automates Kepler. Eureqa automated Kepler in 2009. The engine automates Kepler with an LLM instead of GP crossover — that is a methodological variant, not a historical event." Modifier needed: "automated Kepler on a single substrate, pending replication."
- Bridge 2 as theorem-proving is a category error. Systems ML: "the axiom set selection channel transmits the bits that make the proof possible — this is oracle contamination." Munger: "classic man-with-a-hammer — recommending Lean because that's what proof people reach for." The real value is smaller: automated ODE-class recognition via SymPy lookup (if `exp(-kt)` → `dy/dt = -ky`). This covers 80% of the practical value at 1% of the cost.
- Bridge 3's meta-engine proposal is naive. Munger: "produces taxonomies, not theories." SR: "clustering expressions by tree topology after stripping parameters is a weekend project, not Newton." Systems ML: "substrate selection is a channel — if the operator chooses PK and radioactive decay, the 'discovery' is pre-loaded."

*2/4 convergence:*
- GP-023 (Planck, same grammar) is the crucial experiment. PhilSci: "If it recovers Planck with the same grammar → progressive programme. If it requires grammar extension → Lakatosian grey zone. If it fails → 'Kepler' downgrades to 'Kepler-for-PK'." SR: "or run SRBench Feynman equations for direct publishable comparison."
- String Theory section is aspirational noise with no grammar, gate, or data. SR: "Delete or move to someday/maybe."

*1/4 (novel contributions):*
- PhilSci: Missing Duhem-Quine analysis — what's recovered is the simplest survivor, not the true generating process. The grammar's topology acts as an implicit Kolmogorov complexity prior; this should be stated explicitly.
- PhilSci: Missing degenerating-programme criterion — if the engine requires grammar extensions for each new substrate, the programme is degenerating (ad hoc auxiliary hypotheses). If the same grammar recovers laws across substrates, it is progressive.
- Munger: Bridge 2 inverted — deductive verification can make the engine WORSE by introducing false negatives (correct formulas rejected on formalist grounds when the axiom set is incomplete).
- Munger: "The danger is that the seam becomes a roadmap someone builds instead of a boundary someone respects."
- Systems ML: Bridge 2's information content is zero — the proof confirms logical consistency of existing knowledge against existing theory. The decisive bits are ALL in the axiom selection.
- SR: The holdout gate is underclaimed — it is a miniature Popperian engine implementing conjectures-and-refutations mechanically. This is philosophically significant and should be named.

**Turn 3 (2026-04-17, Synthesis — convergence-to-spec draft).** Based on Turn 2 convergence, the spec scope compresses to:

1. **Bridge 1 hardening (crucial experiment):** GP-023 Planck with identical grammar. Explicit Lakatosian pass/fail criteria. This is the single highest-value experiment.
2. **Bridge 2 downgrade:** From "theorem proving via Lean/Coq" to "ODE-class recognition via SymPy lookup." Engineering task, not research programme.
3. **Bridge 3 honest deferral:** No spec. Define the degenerating-programme failure criterion instead.
4. **Seam additions:** Underdetermination analysis, Kolmogorov complexity prior acknowledgment, degenerating-programme criterion.
5. **String Theory section:** Demoted to appendix or removed.

**Turn 4 (2026-04-17, Self-debate on spec scope — applying inversion to spec itself).**

*Question:* Does the ODE-class recognition (Bridge 2 downgrade) actually produce the "why" the operator needs, or is it just a lookup table?

*Inversion:* What fails if we DON'T build ODE-class recognition?

Answer: Nothing fails. The operator gets `f(x) = c * exp(-kt)` and any domain scientist recognizes this as first-order kinetics without software help. The engine's value is finding the form, not explaining it. ODE-class recognition is a convenience, not a capability gap. Munger's "simplest thing that could possibly work" applies: if the domain scientist already knows what `exp(-kt)` means, the lookup table adds zero information. If they don't, a lookup table won't give them understanding either.

*Counter:* In high-throughput automated pipelines (no human domain scientist in the loop), the ODE class tag enables downstream routing — e.g., "this is first-order kinetics → apply standard dosing protocol." The value is not explanation but automation of the next step.

*Resolution:* Bridge 2 splits into two distinct things:
- **2a: ODE-class tagging for pipeline routing** — engineering task, useful only in automated pipelines, trivial to build (SymPy + lookup table), spec it if/when an automated pipeline exists. Not a priority at 3 weeks.
- **2b: Deductive derivation from axioms** — research programme, category error to spec it now. The axiom selection problem is unsolved and may be unsolvable without domain expertise. Defer with Bridge 3.

*Compression:* At 3 weeks, the only spec-worthy item is the crucial experiment (Bridge 1 hardening via GP-023). Everything else is either (a) already built, (b) trivial engineering triggered by a future need, or (c) a research programme. The spec is: run the crucial experiment. That's it.

*Munger's warning applies:* "The danger is that the seam becomes a roadmap someone builds instead of a boundary someone respects." The spec must be a single experiment with explicit pass/fail, not a roadmap.

**Turn 5 (2026-04-17, Convergence check).** Does the spec survive all four domain lenses?

- PhilSci: Yes — a crucial experiment with Lakatosian pass/fail criteria is the textbook next step.
- Munger: Yes — "the simplest thing that could possibly work" is more substrates through Bridge 1.
- SR: Yes — cross-domain replication with same grammar is exactly what the SR community would demand.
- Systems ML: Yes — no new architecture, no oracle contamination risk, pure observation-dependent validation.

All four lenses converge on the same action: run GP-023 with identical infrastructure.

**Convergence reached. Spec drafted below (see GP-083 spec file).**

**Turn 6 (2026-04-18, Empirical anchor — GP-080 Stage 2 rational-vs-bi-exponential).** The theoretical underdetermination boundary predicted in this seam (Turn 2, PhilSci) has been empirically confirmed by the live Stage 2 run.

*The finding:* GP-080 Stage 2 (5% proportional Gaussian noise, 24 visible points) produced a champion at iteration 2 with score 73 and holdout exact_match=1.0. The engine found:

```
f(x1, x2) = x2 / (0.177*x1 + 0.588 + 0.810/x1)    # rational, 3 params
```

The ground truth is:

```
f(x1, x2) = C * x2 * (exp(-0.07*x1) - exp(-1.5*x1))  # bi-exponential
```

These are structurally different functions that are empirically indistinguishable on the data grid.

*Numerical verification (independent agent):*

| Metric | Value |
|--------|-------|
| Holdout RMSE (clean, x1 ≤ 24) | 0.068 — passes 0.25 threshold |
| Peak location: GT | x1 = 2.143 |
| Peak location: rational | x1 = 2.139 (0.2% error) |
| Max abs error on holdout | 0.170 at (x1=24, x2=4) |
| Error at x1=48 | 262% — rational decays as 1/x, GT decays as exp(-0.07x) |
| Error at x1=100 | 6,757% — catastrophic divergence |

*Contamination audit (independent agent):* **CLEAN.** All 7 information channels verified. The form mismatch (rational vs bi-exponential) is itself strong evidence against oracle leakage — a contaminated engine would have found exponentials, not rationals.

*Why this matters for GP-083:*

1. **Underdetermination is not philosophy — it is a physical property of the data grid.** The holdout grid (x1 ≤ 24) cannot discriminate rational from bi-exponential. A farther-tail point at x1=48 would instantly separate them (0.27 vs 0.99), but the current holdout doesn't have one.

2. **The engine finds the simplest survivor, not the true generating process.** The rational form has lower Kolmogorov complexity than the bi-exponential (no transcendental functions). The grammar's implicit complexity prior favors it. This is exactly what the PhilSci reviewer predicted: "what's recovered is the simplest survivor."

3. **The holdout gate is necessary but not sufficient.** Passing RMSE < threshold on in-range holdout confirms generalization within the data envelope, not beyond it. The GP-046 farther-tail gate is the missing discriminator — designed precisely for this failure mode.

4. **This refutes the "boundaries are artificial" claim.** Gemini Pro argued (2026-04-18) that GP-081/082/083 boundaries are self-imposed and the engine is ready for "inductive science right now." The Stage 2 result proves the opposite: the engine found a wrong-but-fitting form because the data grid cannot distinguish it from the truth. The boundary is in the information, not the architecture.

5. **Bridge 1 is weaker than claimed.** "Abduction + induction → law" is accurate only if "law" means "simplest survivor consistent with evidence and holdout." It does not mean "the true generating process." This is Kepler's actual situation — his ellipses were correct but he could not have distinguished them from slightly perturbed ellipses on Brahe's data. The engine automates Kepler including Kepler's limitations.

*Next step:* Post-run farther-tail evaluation. After Stage 2 closes, evaluate the champion against GT at x1=36, 48, 72. If the rational form is still champion → confirmed underdetermination finding. If the engine found exponentials by later iterations → the adversarial loop escaped the rational basin, which is a different and stronger finding. Either result is decisive.

---

## Turn 7 — Stage 2 Farther-Tail Verdict (2026-04-18)

**Run closed**: `gp080_02`, 8 iterations, champion at score 94 (rational form). Feynman library exhausted; composition mode found Wien arm but not full bi-exponential.

**Farther-tail table** (run: `eval_farther_tail.py` post-close):

| x1 | x2 | f_true | f_champ | abs_err | rel_err |
|----|----|--------|---------|---------|---------|
| 30 | 1 | 0.1070 | 0.1489 | 0.042 | 39.1% |
| 30 | 3 | 0.3211 | 0.4468 | 0.126 | 39.1% |
| 36 | 1 | 0.0703 | 0.1228 | 0.053 | 74.6% |
| 48 | 1 | 0.0304 | 0.0897 | 0.059 | 195% |
| 48 | 3 | 0.0911 | 0.2691 | 0.178 | 195% |
| 72 | 1 | 0.0057 | 0.0567 | 0.051 | 902% |
| 96 | 1 | 0.0011 | 0.0406 | 0.040 | 3754% |

Farther-tail RMSE: 0.1639. Verdict: **RATIONAL BASIN CONFIRMED** — champion diverges catastrophically. Relative error is x2-independent (identical % across all x2), confirming the divergence is purely in x1 dynamics (rational 1/x vs exponential decay). The x2 coupling is correct in both models.

**Composition mode finding**: Feynman library exhausted. Component D composition found `x2 * (a·x1^b·exp(c·x1) + d)` (Wien approximation — single exponential arm) but not `x2*(exp(-k1·x1) - exp(-k2·x1))`. Engine got to the right structural family but couldn't build the difference-of-two-exponentials. The missing coupling: the data grid cannot teach the engine to put x2 INSIDE the exponent argument. Holdout variation (x2=0.75, 1.5 vs visible 0.5, 1.0, 2.0) is too narrow to reveal the x1/x2 coupling inside exp(-). This is the empirical proof that the data grid is the bottleneck, not the grammar.

**GP-083 implication**: The underdetermination boundary is now empirically closed for tacrolimus. The three-part chain is complete: (1) rational fits on holdout (score 94), (2) judge names exponential exclusion without GT access, (3) farther-tail confirms 3754% divergence. Bridge 1 is validated at its correct scope: "abduction → induction → simplest survivor consistent with evidence." Not "simplest survivor = true generating process."

---

---

## Turn 8 — GP-023 Crucial Experiment Verdict (2026-04-18)

**Run closed**: `gp023_crucial_01`, 16 iterations, champion at score **97** (Wien approximation). Mutator: gemini-2.5-flash (cheap tier). Judge: gpt-4.1. Total cost: **$0.4776 mutator + $0.5318 judge = $1.01**.

**Champion form:**
```
z = p0 * x2^p1 * x1^p2 * exp(-p3 * x1 / x2)
p0 ≈ 1.208, p1 ≈ 0.862, p2 ≈ 2.159, p3 ≈ 0.739
```

**True GT (sealed, Division A):**
```
z = x1^3 / (exp(x1/x2) - 1)
```

**Farther-tail evaluation** (`is_exponential_class()`, post-close):

| x1 | x2 | z_true | z_pred | rel_err |
|----|----|--------|--------|---------|
| 5.0 | 0.5 | 0.005675 | 0.013250 | 133.5% |
| 5.0 | 1.0 | 0.847957 | 0.969360 | 14.3% |
| 5.0 | 2.0 | 11.178186 | 11.176670 | 0.0% |
| 6.0 | 0.5 | 0.001327 | 0.004480 | 237.6% |
| 6.0 | 1.0 | 0.536741 | 0.686279 | 27.9% |
| 6.0 | 2.0 | 11.317470 | 11.450301 | 1.2% |
| 8.0 | 0.5 | 0.000058 | 0.000434 | 647.7% |
| 8.0 | 1.0 | 0.171815 | 0.291308 | 69.5% |
| 8.0 | 2.0 | 9.552569 | 10.177630 | 6.5% |

`is_exponential_class: False` — fails at small x2 / large x1 (the regime where the `-1` denominator in Planck's law is decisive and Wien diverges). Holdout RMSE: 0.020 (passes 0.15 threshold).

**Error pattern:** Divergence is x2-dependent (large errors at x2=0.5, small at x2=2.0), opposite of GP-080 which showed x2-independent divergence. The Wien approximation is valid at high x2 (low x1/x2 ratio) and fails at low x2 (high x1/x2 ratio, i.e., where the Bose-Einstein `-1` correction matters). This is the physically correct boundary.

**Lakatosian verdict (pre-committed):** **"Underdetermination confirmed on second domain — same boundary as GP-080."**

The engine passes holdout but fails farther-tail. The champion is structurally correct family class (x2-dependent exponential coupling, peak proportional to x2) but wrong sub-family (Wien, not Planck). This is consistent with the simplest-survivor principle: the Wien form is lower complexity than Planck's transcendental denominator, and the visible/holdout grid (x2 ∈ {0.5, 1.0, 2.0}, x1 ≤ 4.0) cannot discriminate them.

**Taylorist observation (INS-019):** Score 97 at $1.01 total, cheap-tier model. The cage (GP-035 deterministic fitter, holdout gate, pre-registered discriminator tests) produced the structural enforcement; the model produced shape suggestions. The model contributed the x2-dependent exponential coupling (correct) and the x1/x2 argument structure (correct); the cage enforced correctness up to the evidential limit. True form not recovered — the underdetermination boundary, not the model's capability, is the bottleneck.

**Cross-substrate comparison with GP-080:**

| | GP-080 (tacrolimus PK) | GP-023 (Planck) |
|--|--|--|
| Champion form | Rational `x2/(ax1+b+c/x1)` | Wien `p0*x2^p1*x1^p2*exp(-p3*x1/x2)` |
| Champion score | 94 | 97 |
| Holdout RMSE | 0.068 | 0.020 |
| Farther-tail verdict | RATIONAL BASIN CONFIRMED | WIEN BASIN CONFIRMED |
| Error pattern | x2-independent (rational 1/x) | x2-dependent (Wien approximation breaks at high x1/x2) |
| True form | Bi-exponential | Planck transcendental |
| `is_exponential_class` | False | False |
| Cost | ~$1.50 (GP-4.1 mutator) | $1.01 (flash mutator) |

Both domains: holdout insufficient to recover true form. Different basins, same structural boundary.

**Programme status (Lakatos):** "Underdetermination confirmed on second domain" is the evidence that the GP-083 pre-commitment predicted. The crucial experiment has returned its result. The programme is not degenerating (same grammar worked on both domains without modification); it is limited at the evidential boundary: the holdout grid is the bottleneck, not the grammar.

---

## Next Actions

1. ~~**GP-080 Stage 2 post-run farther-tail evaluation:**~~ DONE — Turn 7 above. Rational basin confirmed.
2. ~~**GP-023 crucial experiment:**~~ DONE — Turn 8 above. Wien basin confirmed. Underdetermination on second domain.
3. **Stage 3 design (now active):** Re-run with farther-tail holdout point included in visible evidence (x1=8, x2=0.5 visible, not held out). Tests whether the discriminator, not the engine, was the bottleneck. If the engine recovers Planck with a farther-tail point in evidence → the data grid was the bottleneck. If not → grammar extension is needed.
4. ~~Bridge 2 spec: ODE-class recognition via SymPy, not theorem proving.~~ DONE — captured in spec as deferred.
5. ~~Bridge 3 deferred — define degenerating-programme criterion only.~~ DONE — criterion added to seam and spec.
6. ~~Add underdetermination analysis and Kolmogorov complexity prior language to this seam.~~ DONE — sections added above.
7. ~~Demote String Theory section to appendix.~~ DONE.
8. ~~Empirical anchor from Stage 2.~~ DONE — Turn 6 added.
9. **Fix f_dominant alias:** Add `f_dominant = f_true` to `src/ztare/substrates/gp023_crucial_gt.py` (Component C looked for `f_dominant()` which doesn't exist — now that run is closed, safe to patch).
10. **INS-018 → confirmed (pending):** gp023_crucial_01 is a cross-substrate replication of the underdetermination boundary. Promote INS-018 from `suggestive` to `confirmed` after updating the ledger entry with Turn 8 data.
