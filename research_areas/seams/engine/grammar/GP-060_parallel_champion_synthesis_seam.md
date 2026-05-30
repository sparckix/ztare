# GP-060 Parallel Champion Synthesis — Seam

> **Seam metadata** · `seam_id:` GP-060 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: open
Opened: 2026-04-15
Hypothesis family: H-ARCH-01 (search architecture)

---

## Problem Statement

The autoresearch loop is a **sequential hill-climber on a single path**. At each iteration the mutator receives the current champion thesis, the weakest-point critique, and the accumulated failure log, and produces one mutation. The champion advances if the mutation scores higher.

This architecture has two structural failure modes that are not addressed by any current apparatus:

**1. Basin trapping.** The mutator descends into one framing early (e.g., coordination-threshold-dominant for Hungary) and all subsequent mutations are local refinements within that basin. Orthogonal framings — equally valid structural models that score similarly on the rubric — are never reached because no mutation step has sufficient incentive to cross the basin boundary. High-stagnation pivots (GP-034 loop control) partially address this but are reactive and late.

**2. Dimensional blindness under multi-criterion rubrics.** For rubrics with 4–6 independent criteria, the mutator naturally optimizes toward the 2–3 easiest to satisfy and patches the remaining ones superficially. The linear chain cannot simultaneously hold pressure on all dimensions because each mutation step is a single-direction move. This is structurally analogous to coordinate-descent on a function where the axes are not aligned with the natural gradient — it converges but to a suboptimal point.

The evidence that this is real: sandbox_07 ran 10 iterations in the EML grammar space and never crossed from the "5-parameter decoupled Planck family" basin to the "compound substitution chi = gamma*phi/psi" basin, even though the latter was reachable at depth-1 (confirmed by GP-059 expressibility probe). The structural_misfit diagnostic was the missing signal that sandbox_08 is now testing. But the seed-dependence problem is orthogonal to the feedback-signal problem — even with a perfect hint, a single-path search can get trapped.

---

## Proposed Architecture: 3-Stage Parallel Champion Synthesis

The intervention has three stages. The key novelty is Stage 2 (the combiner). Stages 1 and 3 require only configuration changes; Stage 2 requires a new component.

### Stage 1 — Parallel Divergent Workers

Run K workers (K = 2–4) in parallel from the **same starting thesis and evidence**, each seeded with a different **mutation bias instruction** injected into the mutator persona. Each worker runs a short budget (2–4 iters). Workers do not share state.

The mutation bias instruction is a single paragraph appended to the persona that directs the worker's attack vector:

- **Worker A (structural axis):** "Your primary attack is the structural condition identification — push to operationalize each condition as a measurable variable with a threshold and a data source. Do not accept vague proxies."
- **Worker B (comparative axis):** "Your primary attack is the cross-case prediction — force the thesis to make a specific falsifiable claim about why Turkey 2023 or Georgia 2024 failed, using the same structural variables."
- **Worker C (discriminator axis):** "Your primary attack is the discriminator — the thesis must name a single observable that would definitively separate the structural model from the charisma/campaign rival. Operationalize it at the county or constituency level."
- **Worker D (durability axis):** "Your primary attack is the durability forecast — the thesis must name specific precursors of incumbency restoration risk and a 12-month early check event."

Each worker produces a champion thesis that is strong on its assigned dimension and potentially weak on others.

**What Stage 1 is not:** naive parallel restart. Workers do not start from random seeds. They start from the same seed with directed divergence. The goal is not to cover the space randomly but to generate one strong candidate per rubric dimension.

### Stage 2 — Combiner (the decisive new component)

A single LLM call reads all K worker champions, the rubric criteria, and the shared evidence surface, and produces one combined thesis.

The combiner's contract:

```
combine_champions(
    champions: list[ThesisText],   # K worker outputs
    rubric: RubricDict,            # criterion definitions with point allocations
    evidence: str,                 # shared evidence surface
    attribution: bool = True,      # whether to annotate which worker each section draws from
) -> ThesisText
```

The combiner's instruction is explicit about what it is doing: *"Each champion below handles one dimension of the rubric well and the others weakly. Your job is to write a single thesis that takes the strongest structural argument from the champion that best handles criterion X, the strongest discriminator from the champion that best handles criterion Y, and so on. Do not average — select and integrate. The combined thesis must not be weaker on any dimension than the weakest of its sources."*

The combiner is **not** a judge — it does not score. It does not modify evidence claims. It does not introduce new claims not present in any champion. It is a structured synthesis under criterion pressure.

**Critical constraint:** the combiner must fail-safe. If it introduces a claim not anchored in any source champion, that claim is ungrounded. The combiner instruction must explicitly prohibit this: "Do not introduce any structural claim, observable, or prediction not present in at least one of the input champions."

### Stage 3 — Linear Refinement

Run the main autoresearch loop normally from the combined thesis as the seed. The combined thesis starts with better dimensional coverage than any single seed, so the linear chain refines from a higher-quality starting position rather than spending its early iters discovering directions it should have known from initialization.

---

## Why the Combiner Is the Decisive Piece

ZTARE already has parallelism at the **evaluation layer** — the firing squad runs multiple judges, debate logs accumulate adversarial critique. What is missing is parallel structure at the **generation layer**.

The combiner is the mechanism that makes parallel generation useful. Without it, K workers produce K uncombined partial solutions and the operator must manually arbitrate. With it, the K workers' outputs become structured inputs to a single synthesis step that is itself checkable (did the combiner introduce ungrounded claims? did it drop a criterion? did it produce a thesis that scores lower than its best source on any dimension?).

The combiner is also the minimum viable new component. It is a single function call, architecturally clean, independent of the loop internals. It can be prototyped and validated without modifying autoresearch_loop.py at all — implemented as a pre-run seeding step that replaces `thesis.md` before the main loop starts.

---

## Scope Boundary

**In scope:**
- `combine_champions` function (Stage 2)
- Stage 1 mutation-bias injection (a new CLI flag `--mutation-bias` or rubric key `mutation_bias_profile`)
- A thin orchestration wrapper that runs K workers in parallel and calls the combiner
- Validation: does the combined thesis score higher at iter 0 than the solo seed?

**Out of scope:**
- Continuous parallelization mid-run (parallel workers at every iter — architecturally complex, context-deprivation problem)
- Genetic crossover between champions at arbitrary iters (requires redesigning the champion tracker)
- Beam search (keeping top-K champions at each iter — fundamentally different loop architecture, separate seam)
- Any change to the evaluation layer (firing squad, meta-judge, debate format)

---

## Failure Modes to Test

1. **Combiner hallucination:** The combiner introduces a structural claim not present in any source champion. Gate: automated diff check — any sentence in the combined thesis must have a provenance citation to at least one source champion.

2. **Combiner averaging:** The combiner produces a thesis that is mediocre on all dimensions rather than strong on all. Gate: score each source champion and the combined thesis independently; the combined must beat the *worst* source champion on every criterion and the *best* source champion on at least K-1 criteria.

3. **Worker homogeneity:** Despite different mutation-bias instructions, K workers converge on the same framing. If all K workers are in the same basin after 2–4 iters, Stage 2 is combining K versions of the same thesis and the diversity benefit is lost. Detection: pairwise semantic similarity between worker outputs before combining. If similarity > threshold, extend worker budgets or introduce a stronger divergence constraint.

4. **Context deprivation:** Workers run without the accumulated failure log from prior iters of the other workers. A combined thesis may therefore repeat a framing already found to be weak in sandbox_07 or in prior runs of the same project. Mitigation: inject the project's failure history (from `semantic_gate_observations.jsonl` or prior debate logs) into all workers at initialization.

---

## Discriminating Experiment

**H-ARCH-01:** A combined thesis (Stage 1 + Stage 2 seed) reaches a higher score at iteration 0 than the best solo seed from any single worker, and the linear chain from the combined seed reaches a higher final score within the same total iteration budget (K×M + N) than a solo chain of the same total budget.

**Control:** Run the same project with the same total iteration budget as a straight linear chain. Compare final champion scores.

**Empirical anchor:** Hungary reversal 2026 is the natural first test — 5-criterion rubric with a comparative transfer axis that is exactly the kind of orthogonal dimension a single linear worker is likely to underprioritize.

---

## Relationship to Existing Seams

- **GP-034 (loop control / latent distance)** — the pivot heuristic is the current mechanism for escaping basins. GP-060 is a complementary intervention at initialization rather than mid-run. They are not redundant — GP-034 fires reactively when stagnation is detected; GP-060 acts proactively before the first iter.
- **GP-042 (structural diversity)** — GP-042 addresses diversity of functional forms within a single run (fit-primitive context). GP-060 addresses diversity of thesis framings in bounded-discriminator runs. Complementary, different layers.
- **GP-058 (bug-bounty + factory integration)** — if GP-060 is validated, the combiner step would be a natural addition to the factory setup flow (`make setup-project` → fetch → compile → parallel seed → combine → loop).

## Open Questions Before Implementation

1. What is the right K? 2 workers (structural + comparative) is the minimum useful divergence. 4 workers is probably the practical ceiling before cost dominates.
2. Should the mutation-bias be a CLI flag, a rubric key, or a separate seed-generation config file? The rubric key is cleanest — it keeps the bias specification with the project definition.
3. Does the combiner need to be model-family-agnostic, or is it always the judge model (gemini-flash) since it's a synthesis task not a generation task?
4. What is the right budget split? 3 iters per worker + 7 linear refinement iters = 10 total per worker × K workers is expensive. The right frame may be: Stage 1 is 1 iter each (single mutation from seed with bias), Stage 2 is 1 combiner call, Stage 3 is the remaining budget.
