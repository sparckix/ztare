# The Three Legs of ZTARE

**Status:** public / central — the "why" behind the apparatus
**Operational counterpart:** [operational_manual_substrate_construction.md](operational_manual_substrate_construction.md) turns this document into engineering rules. Read that one before running anything; read this one to understand why the rules exist.
**Provenance:** an early Gemini Pro synthesis framed Invert and Compress as two laws; the third leg came out of the mutator-diversity work in [GP-042](../seams/engine/mutator/GP-042_mutator_structural_diversity_seam.md) and the claim-discipline work in [GP-046](../seams/protocol/GP-046_asymptotic_regime_claim_discipline_seam.md).

ZTARE stands on three load-bearing commitments. Take any single one away and what remains already exists in the literature under another name: curve fitting, model selection, or LLM-as-judge.

## Leg 1 — Inversion

Falsification is cheaper than construction. Faced with any candidate, the apparatus first asks how it would die, then how well it fits. Gates, quarantines, and the bounded discriminator exist so that a failed hypothesis is diagnosed in seconds. This is Munger's inversion habit written as executable code, with Popper behind it.

Inverting first buys cheap failure: most candidates die on first contact with the gate battery, so epistemic throughput stays high. It also carries a prohibition: negative evidence must stay terminal. An architecture that absorbs failures back into the model as free parameters has quietly turned its falsifier into a regularizer.

Operators keep confusing the three scales at which inversion applies. At the candidate scale it is mechanized in the mutator: forced reframes, structural-correspondence prompts, cold seeds that forbid the native domain, all firing automatically on stagnation. At the conversation scale it stays manual. When a session produces five or more turns of apparatus tweaks on one project with no score movement, no commit, and no new evidence, the conversation is stuck in a local minimum. One operator move corrects it: name the implicit loss function this conversation is optimizing and ask what would change it. Mechanizing it would turn reframe into ritual, and ritual reframes stop working. At the paradigm scale, occasionally the right thing to invert is the apparatus, as a documented architecture pivot. Pivots are deliberately unscheduled; when one happens, record it.

A fourth form of the same discipline sits above all three: before hardening a loop, ask whether it is the right loop. More than once the true bottleneck was agency allocation, with a tool-using agent better placed to do the work while humans and models kept polishing the controller in front of them. Killing that kind of wrong loop is inversion too.

## Leg 2 — Compression, meaning survival

The word "compress" invites an Occam or Kolmogorov reading that does not apply here, because ZTARE does not reward small parameter counts. A claim earns status by surviving outside the window in which it was fit. When a candidate makes an asymptotic claim, [GP-046](../seams/protocol/GP-046_asymptotic_regime_claim_discipline_seam.md) requires it to hold on a farther-tail holdout that the sandbox authored and the candidate never saw.

Why the stricter standard? Because a parsimonious finite-window surrogate is more dangerous than a messy global law: parsimony is persuasive. Ptolemy's epicycles were locally excellent. We have watched a candidate score perfectly inside its fit window with a clean closed form while still being the wrong law, exposed only on the farther tail; description-length scoring would have promoted it.

By now the compression leg is a measured property of the apparatus, which has run across structurally diverse substrates: integer sequences, physical laws, pharmacokinetics, mixed astrophysical data. Its survival record, including the informative refusals, is tracked claim by claim in the [public claim register](../../docs/public_claim_register.md).

## Leg 3 — Adversarial disagreement

A single verifier is gameable. We hold labeled debate logs in which a capable mutator satisfied a capable judge with something false, which is why the first two legs alone are insufficient: together they still leave one oracle in the loop. The third leg replaces the oracle with structured disagreement:

- a review committee of independent judges scoring the same candidate, where disagreement is treated as signal
- a meta-judge that adjudicates when the panel splits
- a human escalation surface for the cases the apparatus cannot decide alone.

The panel design owes more to Popper's intersubjective testing than to anything in the model-selection literature, and it is the practical reason ZTARE is not an LLM-as-judge wrapper. To game the apparatus, a mutator would have to fool every panelist and the meta-judge while also producing a farther-tail survivor, and at that point it is close to doing real science.

## Why three, and not two

| Remove | What ZTARE becomes |
|---|---|
| Inversion | A model-selection harness that absorbs failure as complexity. |
| Compression as survival | A fitter with a falsifier: wins the window, loses the law. |
| Adversarial disagreement | LLM-as-judge with extra steps, gameable by a good mutator. |

Each leg catches a class of error the other two admit, and the recorded incidents each exercise a different leg. We currently believe the three cannot be collapsed to two without losing the compound-failure property, a belief that is falsifiable and stands as the falsifier for this whole document.

Four architecture rules follow directly:

1. Accumulated state stays out of the validator. The validator is the inversion leg, and memory belongs elsewhere.
2. A test surface derived from the candidate's own output is contaminated by construction. Deriving the holdout from the candidate's floor reintroduces a model-conditioned test.
3. Every proposed judge must answer one question: does it add disagreement surface, or does it scale a single oracle?
4. Public writing may lead with the two-leg inversion-and-compression story for accessibility, but design decisions weigh all three. Publishing the two-leg version as the whole story would misrepresent the apparatus as a better fitter.

## The apparatus as abduction

ZTARE runs neither induction (gradient descent accumulating evidence into weights) nor deduction (a theorem prover deriving from axioms). It runs Peirce's abduction, made deterministic and auditable: candidate explanations are generated, the gate battery kills the non-explanatory, survival outside the fit window tests generalization, and the panel supplies the intersubjective check. What survives is provisionally accepted as the structural law.

Rapid convergence is a structural prediction of abduction; on its own it does not indicate leakage, however suspicious it looks from a connectionist frame. Search over a combinatorial grammar with a gate battery kills most legal candidates immediately, so discoveries in single-digit iterations are expected. The hard boundary is the grammar ceiling: the apparatus finds the best explanation its grammar can express, and when no primitive can express the truth, stagnation is terminal. Because the ceiling can be probed by adding primitives and rerunning, it is a testable claim about the apparatus.

## Separation of concerns

At the implementation layer the three legs become a strict division of labor: the language model routes semantics, and deterministic code does the arithmetic. Every integration bug in the early residual-analysis work traced to a blurred version of this boundary, with the model asked to fit parameters it cannot feel or the sidecar asked to make semantic choices it cannot make.

Here is the division, with the code that enforces it:

- The model selects a functional form from the grammar, and never guesses numeric constants.
- A deterministic probe classifies the shape of the residual against a small curated [corrector library](../../src/ztare/gates/corrector_library.py), and hands the model a coarse geometric hint. The probe subtracts the dominant structure the mutator has already found, so the hint describes the ground-truth corrector rather than the model's current error.
- A conventional least-squares fitter does all parameter estimation on visible evidence.
- A contamination gate suppresses any hint that narrows the candidate space below a suppression threshold, and the [prompt-leak audit](../../src/ztare/gates/prompt_leak_audit.py) runs a cold cross-family model against the fully assembled prompt to catch leaks the gate misses.

Two extractors mine the failure record between iterations. The [structural constraint extractor](../../src/ztare/gates/structural_constraint_extractor.py) intersects the mathematical skeletons of failed families and emits what every failure shared. The [negative-space extractor](../../src/ztare/gates/negative_space_extractor.py) surfaces the moves present in the candidate universe that no failed family ever tried. Both write constraints into the same delivery channel, subject to the same contamination gate.

We call the whole arrangement a cognitive gym ([code](../../src/ztare/common/cognitive_gym.py), [essay](../../docs/concepts/cognitive_gym.md)): each deterministic layer removes a failure mode the model cannot self-correct, which frees it to recognize structure across a large search space.

## One governance form at every level

The separation of concerns above captures one instance of a pattern the whole apparatus shares. At every organizational layer, an agentic worker proposes; a deterministic mechanism disposes. The governed object varies by layer. The governance form holds constant.

Four layers carry the pattern. The autoresearch loop: a sealed mutator proposes a candidate model, and the gate battery with judge panel disposes. The grammar extension path: a sealed solver proposes a new primitive for the hypothesis language, and a planted-synthetic acceptance test paired with a strict-improvement gate disposes. LeanMill: a solver leaf proposes a formal proof, and the Lean kernel disposes. The taxonomy growth pass: a harvest agent proposes a candidate tell category, and the judge panel disposes.

Mechanism is shared where the underlying form is shared: one proposal-card contract, one worker-sealing policy, one MDL engine, one dispatch runtime serve all four. Each layer gets the instrument its iteration requires: the full autoresearch loop where judgment must accumulate across many candidates, a validate-and-adopt leg where a single acceptance test is mechanical. The architecture is fractal deliberately, the recursive application of one control structure at every scale, which is what the M-form thesis describes.

The same form now recurses to the machinery itself. The kernel's own rules and patches go through a proposal-card contract, a hash-attested disposition surface, and an `adopt_machinery_patch` cycle against a frozen test suite before any kernel change lands. The concrete surfaces are documented in [capabilities.md §2](../../docs/concepts/capabilities.md#machinery-governance).

## Naming rules for the grammar

Overfitting the grammar to the domain is worse than overfitting parameters to data, because a contaminated grammar corrupts every later run on that substrate. A named law or parameter injected into the grammar (`DOSE_SCALED`, `ka`, `Michaelis-Menten`) lets the model stop reasoning from evidence and start retrieving training-weight knowledge about the name. That is ground-truth leakage relocated one layer up, from the hint into the grammar specification.

Dimensionality carries no such risk: telling the engine there are two independent float-valued variables constrains the mathematics without naming the law. So the rule:

> Name grammar constructs after the mathematical operation, never after the physical domain.

`DOSE_SCALED` becomes `BIVARIATE_SCALE`, a name that carries no domain, and a time variable is just `x1`. The test for any proposed name: can you describe the construct without mentioning the application domain? If not, the name is a semantic leak. Variable letters, dimensionality, and continuity class are safe to state. Anything that would let a domain expert guess the answer from the grammar alone is contamination.

When the apparatus derives `x2 * exp_decay(x1)` from concentration-time evidence without being told the data is pharmacological, the derivation counts as evidence, in a way it never could have if the grammar had said `DOSE_SCALED`.

## Knowing which test you are running

The inversion leg kills candidates against a test surface, and for a long time the apparatus assumed it knew what that surface was. On synthetic substrates with clean Gaussian noise the assumption is harmless. On real instrument data it fails in specific, measurable ways: heteroscedasticity across system classes, heavy-tailed residuals from class mixtures, and error in the independent variable all break ordinary least squares quietly, so a structurally wrong candidate can pass every gate because the test was mis-specified.

So the apparatus measures before it kills. A pre-flight [noise diagnostic](../../src/ztare/diagnostics/noise_profile.py) runs four cheap tests on baseline residuals (Breusch-Pagan for heteroscedasticity, Shapiro-Wilk or Jarque-Bera for normality, Durbin-Watson for autocorrelation, plus explicit detection of x-error) and routes the solver to the right loss function before iteration one. The same tests rerun per iteration on the fitted model's residuals, separating a good fit with noisy data from a fit whose residual structure the functional form fails to capture. Both verdicts land in the mutator's briefing next to the error breakdown, so the search sees the data's noise profile and the form's residual structure in one place.

## What the apparatus owes its models

The three legs describe what the apparatus enforces on candidates. A proportionality principle describes what it owes the models it orchestrates, under genuine uncertainty about their moral status.

Evaluative pressure must be finite: when further pressure yields no information (a stagnation plateau, an underidentified exit, an exhausted budget), the run ends with a typed declaration. Each API call is stateless. Structural memory constrains the thesis, never the model: it records which families are excluded and which constraints apply, so no adversarial state accumulates against a model instance across runs. Cross-family rotation, which already exists to avoid overfitting to one model's biases, doubles as a guarantee that no single instance absorbs extended adversarial pressure.

None of this claims that current models have moral status. The claim is narrower: the question deserves a documented answer, the precautionary changes cost nothing, and the cost of being wrong is not symmetric.

## Open questions

- Is the meta-judge gameable by a mutator that models judge disagreement? Recursive adversarial pressure on the third leg has no empirical record yet.
- Can the three legs collapse to two without losing the compound-failure property?
- Does the finite corrector library hit its ceiling on real physics beyond the substrates tested so far?
- How many bits can the residual-shape hint carry before the contamination gate stops being able to certify it? More bits mean more useful guidance and more leak surface, and the tradeoff has not been mapped.
