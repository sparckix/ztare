# GP-087 — Residual-Driven Primitive Generation

> **Seam metadata** · `seam_id:` GP-087 · `track:` engine · `status:` `note` - n=1 conceptual, no implementation yet · `last_updated:` 2026-05-08


**Track:** findings / future-work
**Status:** `note` — n=1 conceptual, no implementation yet
**Opened:** 2026-04-18
**Goal slug:** `residual_driven_primitive_generation`
**Origin:** Operator Turn 7 in GP-085 debate log (2026-04-18). Inversion of the alien math API argument: instead of using alien math as a translator of discovered laws, use the alien math's farther-tail failure residual as a diagnostic signal that proposes the next grammar primitive. Motivated by the observation that the operator's injection of UNIVERSAL_DENOMINATOR in crucial_03 was driven by intuition that could, in principle, be systematized.

---

## The Core Claim

**Static grammar expansion is the correct mechanism for breaking the grammar ceiling.** GCH-Planck confirms this. But the current mechanism for selecting the next primitive is operator intuition: the operator observes stagnation, hypothesizes what structural class the ground truth belongs to, and injects the corresponding primitive. This is not scalable.

**The residual-driven hypothesis:** When a static grammar's best form fails the farther-tail gate, the failure residual — the signed, structured discrepancy between the best static form and the observed data in the farther-tail region — encodes the mathematical shape of what the grammar is missing. An unconstrained model (neural network / alien math) that passes the farther-tail gate would, by construction, have implicitly learned that shape. The residual between the alien model's tail predictions and the static model's tail predictions is a direct proposal for the next primitive.

**The loop:**
1. Lock the static grammar G₀ and run the engine to the grammar ceiling C(G₀, P, budget).
2. Run an unconstrained model (alien math) on the same data. Check its farther-tail behavior.
3. If the alien model passes the farther-tail gate: compute the residual between the alien model's tail predictions and the best static form's tail predictions.
4. Feed the residual shape (not the raw values) to a secondary proposer: "What is the simplest mathematical primitive that captures this functional shape?"
5. Append the proposed primitive to G₀, producing G₁. Re-run from scratch under the new grammar.
6. The farther-tail gate on the new run determines whether the primitive was correct.

**What this is NOT:**
- Alien math as translator (the alien model does not write the law — it diagnoses the gap)
- Dynamic grammar (G₁ is still static — the expansion happens between runs, not within a run)
- Replacing the operator (step 4 is a proposer, not a solver — the gate in step 6 remains the arbiter)

---

## Relationship to Existing Architecture

| Concept | Current mechanism | What this seam adds |
|---|---|---|
| Grammar expansion | Operator intuition | Residual shape as structured proposal signal |
| Alien math role | Translator (fails distillation, §2.8a) | Diagnostic (identifies gap, proposes primitive) |
| UNIVERSAL_DENOMINATOR injection | Operator guessed Planck needed exp-in-denom | Residual of alien tail vs static tail would have pointed there |
| Feynman Wall | Detected by stagnation + latent distance | Residual tells you *what wall* you hit, not just *that* you hit it |

The §2.8a argument in paper5 (alien math as translator fails the farther-tail gate) is **not contradicted** — it becomes the setup. The translator fails → use the failure to diagnose → propose the primitive that would have succeeded. These are sequentially compatible.

---

## Empirical Pre-condition

This mechanism requires that the alien model can pass the farther-tail gate on the substrates where the static grammar fails. This is not guaranteed:

- If the alien model is also interpolating (fails tail), the residual diagnostic has no signal value — you cannot distinguish "grammar is missing a primitive" from "the data contains no recoverable structure."
- If the alien model passes tail by memorizing training data rather than capturing structure (overfitting to noise), the residual shape is noise-driven and will propose spurious primitives.

**The discriminator:** Run the alien model with strict train/test split. If the alien model passes the farther-tail gate (held-out tail, never seen during training), its tail behavior is structural, not memorization. The residual is then trustworthy.

This is itself a testable hypothesis: on the gp023 Planck substrate, would an unconstrained neural network trained on the same 36 visible points pass the farther-tail gate (x1∈{10,12,15}, x2∈{0.5,1.0})? If yes, the mechanism is viable. If no, the alien model is also failing the tail and the diagnostic is moot.

---

## Why This Belongs in Paper5 as Future Work

The current empirical result (GCH-Planck, crucial_03) proves that grammar expansion breaks the ceiling. It does not prove that the expansion can be automated. The future work section of paper5 should:

1. State the binding constraint accurately: "The current mechanism for grammar expansion is operator-guided and requires domain expertise. The ceiling is broken by UNIVERSAL_DENOMINATOR in crucial_03 — the operator knew to add this primitive because they knew Planck's law involves an exponential in the denominator. This is not an automated capability."
2. Name the next architectural target: "The alien math residual is a candidate signal for automating primitive proposal. The empirically correct use of unconstrained models in this pipeline is not as law-writers but as gap-diagnosticians — their tail behavior reveals what the static grammar cannot express, and the residual shape is the input to an automated primitive proposer."
3. Do not claim this works. State it as a testable architectural hypothesis requiring a controlled experiment on a substrate where (a) the static grammar fails and (b) the alien model passes the tail.

---

## Questions for Debate

### Q1 — Does the alien model reliably pass the farther-tail gate on grammar-starved substrates?

This is the decisive empirical pre-condition. If no, the mechanism has no signal. The test is cheap: train a neural net on the gp023 Planck visible data and check its predictions at x1∈{10,12,15}. Expected result: it passes (Planck's law is smooth and its tail is learnable from the visible range). But this must be verified, not assumed.

### Q2 — What is the right secondary proposer for primitive extraction from residual shape?

The residual is a set of (x, Δ) pairs where Δ = alien_prediction − static_prediction at farther-tail points. The question is what the secondary proposer sees: the raw Δ values, the functional form of Δ as a function of x, or something richer (gradient, curvature). Different proposer designs have different failure modes.

Candidate: run symbolic regression on the residual itself — let the engine discover the primitive from the residual rather than hard-coding a proposer. This is recursive ZTARE: run ZTARE on the gap between alien math and static grammar.

### Q3 — Does this require the alien math model to be separate from the ZTARE engine?

The alien model could be the same LLM that proposes compositions (mutator), operating without grammar constraints. Or it could be a genuine neural function approximator (e.g., a small MLP trained on the evidence). These have different properties: the MLP is genuinely unconstrained; the LLM in free-form mode may still implicitly constrain to algebraic forms.

### Q4 — How does this interact with GP-082 (substrate scope boundary)?

GP-082 asks where abductive compression breaks. This seam assumes the alien model can always pass the farther-tail gate — which may not hold on substrates where the data contains no tail-recoverable structure (e.g., chaotic systems, high-dimensional phase transitions). The scope conditions for this mechanism are the same as GP-082's scope boundary.

---

## Promotion Criteria (to active)

- n=1 (this note): conceptual, no experiments
- Promotes to `active` when: controlled experiment demonstrates alien model passing farther-tail gate on at least one grammar-starved substrate, AND residual shape is used to propose a primitive that breaks the ceiling in a follow-on run

---

## Cross-references

- `research_areas/private/seams/GP-085_grammar_ceiling_hypothesis_seam.md` — parent finding; Turn 7 is the origin of this seam
- `research_areas/private/seams/GP-082_substrate_scope_boundary_seam.md` — scope pre-condition
- `research_areas/private/papers/paper5.md` §2.8a — alien math as translator (compatible, not contradicted)
- `projects/gp023_crucial_03/run_summary.json` — the UNIVERSAL_DENOMINATOR injection that this mechanism would automate

---

## Debate Log

*(to be filled)*
