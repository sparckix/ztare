# GP-042 Mutator Structural Diversity

> **Seam metadata** · `seam_id:` GP-042 · `track:` engine · `status:` `verify` (Fix 1 slice implemented 2026-04-12 16:30:05 EDT; l · `last_updated:` 2026-05-08


**Track:** findings
**Status:** `verify` (Fix 1 slice implemented 2026-04-12 16:30:05 EDT; live verifier pending)
**Origin:** GP-041 negative ablation result (2026-04-12)
**Trigger:** GP-041 offline multistart ablation confirmed that candidate quality — not optimizer initialization — is the binding constraint on form-family convergence. Mode 1 (mutator anchoring), explicitly deferred from GP-041, is now the active problem.

---

## Problem Snapshot

GP-037 3b (10-iter run) demonstrated two distinct failure modes. GP-041 addressed Mode 2 (optimizer initialization) and closed as a negative result — multistart improved candidates but not to within gate range. The binding constraint is Mode 1: the mutator anchors in its default form family and cannot sustain escapes.

Specific evidence:

- Iters 1–5, 7–8, 10: mutator stayed in the default form family regardless of pivot framing. Stagnation pivots changed strategy language but not the structural search space.
- Iters 6 and 9: mutator escaped briefly to structurally distinct forms. Both escapes were followed by regression to the default after pivot resets.
- Final score: 0 throughout, `budget_exhausted`. The correct structural direction was found twice and could not be sustained.

The pattern: escape is possible but fragile. Pivots destroy escaped state. The default basin has stronger pull than any individual escape.

## Root Cause: Structural Memory Loss (Candidate)

The working hypothesis is that **the agent has no structural memory across iterations** — it cannot compound its own discoveries because escaped state does not survive pivot boundaries. The agent is not failing to escape; it escaped twice. It is failing to retain that escape as evidence.

**Important caveat (Turn 3 critique):** this framing is unproven. An alternative explanation is that the agent reverted because the escaped forms *legitimately failed the gate* — rational reversion on evidence, not amnesia. These two explanations require different fixes. The falsification experiment (see Promotion Criteria) must distinguish them before memory infrastructure is built.

Three mechanisms that implement the memory loss hypothesis:

1. **Pivot state reset**: when the stagnation counter trips, the emergency pivot reframes strategy language but does not preserve the agent's structural position. The next iteration starts fresh with no memory of which form families have been explored.

2. **No cross-iteration structural trace**: the agent sees the current thesis and current strategy framing. It cannot see "I tried these structural families and all produced a mismatch signal — my current proposal is in the same family."

3. **Default basin pull**: the initial form family is the natural proposal from a general-purpose model. Without a durable structural trace, every iteration is effectively iteration 1 in terms of form-family choice.

## Fix Directions

Four engineering constraints (source: Codex post-GP-041 analysis, 2026-04-12). These are not loosely ranked alternatives — they address different aspects of the same memory-loss problem and are complementary.

**Fix 1** — Preserve escaped form families across pivots: when the agent has reached a structurally distinct family (detectable via the mismatch diagnostic), store that family label as a "known viable topology" and prevent pivot resets from discarding it. The escaped form becomes a structural anchor for subsequent iterations, not a wiped state.

**Fix 2** — Branch on structurally distinct candidates: rather than a single current thesis, maintain a small set of structurally distinct active candidates simultaneously. Pivots drop the lowest-performing branch rather than resetting all state. This is a search architecture change that makes memory structural rather than prompt-based.

**Fix 3** — Loop-verified structural divergence gate: require that the loop independently confirm structural change before accepting the new candidate — not by checking the agent's prose justification but by verifying that the mismatch diagnostic pattern on the new candidate differs from the prior family's signature. The agent's articulation ("prior family failed because X, new family because Y") is a secondary signal only; the gate passes or fails on loop-verified evidence. An agent that confabulates a persuasive contrast but produces a structurally identical form fails the gate.

*Correction from Turn 3 critique:* the original description ("articulation gate") was compliance theater — it checked whether the agent could justify the change, not whether the change happened. Justification is agent-generated inference; it cannot be zero-trust. The loop must verify the structural change externally.

**Fix 4** — Pivots that impose a topological ban: when the loop fires a pivot, it explicitly bans the current structural family for the next K iterations. This requires the loop to classify the agent's current structural family from its output — a family classifier is a prerequisite for this fix. Without it, the ban cannot be enforced.

*Unresolved dependency (Turn 3 critique):* the mismatch diagnostic measures residual fit quality, not structural type. Classifying "rational denominator family" vs. "polynomial family" from raw agent output requires a separate structural classifier that does not yet exist in the system. Fix 4 cannot be implemented until that classifier is specified and built. This is the decisive open question for Fix 4.

**Rejected** — Kernel-supplied structural templates (Fix B from GP-041): if the infrastructure supplies the correct form family, the agent's escape is not discovery. Rejected on discovery-claim grounds. Not in scope for any slice of this seam.

## Implementation Order

Fix 3 is the recommended first experiment: cheapest, no new infrastructure, and its compliance-gate nature makes the zero-trust claim clear. The agent must demonstrate articulated structural reasoning, not just produce a different form.

Fix 1 and Fix 4 require detecting and storing structural state from agent output — more infrastructure but targeted. Fix 4's topological ban is a harder enforcement than Fix 3's articulation gate and should be tested after Fix 3 is characterized.

Fix 2 (branching) has the most interaction effects with loop control and is the most ambitious architectural change. It should follow after the simpler fixes are characterized.

**Note on ordering with GP-034**: Codex is implementing GP-034 (dual-channel loop control). The dual-channel rule reduces destructive pivot frequency by requiring latent distance to be low before firing a refresh. This is complementary to this seam — fewer destructive pivots means fewer memory-loss events — but it does not eliminate the underlying problem. An agent that survives a pivot with no structural trace still starts the next structural search from its prior. GP-034 reduces the damage; GP-042 fixes the root cause.

## Dependencies

- **GP-041**: closed as negative ablation record. Mode 2 (optimizer initialization) is not the binding constraint. This seam is Mode 1.
- **GP-034**: active — dual-channel loop control (latent distance + scalar yield). The dual-channel rule stops disruptive refresh actions during active structural traversal, which reduces destructive pivot resets. GP-034 should land before or alongside Fix 1/Fix 2; it is not a prerequisite for Fix 3.
- **GP-035 cleanliness rerun**: pending — verifies prompt-layer enforcement. Not a prerequisite for GP-042 but cleans the measurement surface.

## Promotion Criteria

`note` at opening. Promote to `active` if the **falsification experiment** passes first (see below), and then one of:

- Fix 1 (structural preservation) in isolation produces at least one run where an escaped form survives an unsupervised pivot — no agent instruction to preserve it — and a later iteration re-engages that family without re-injection of it into the prompt.
- Fix 3 (loop-verified divergence gate) produces at least one run where the gate blocks a candidate that the agent articulated a change for but that the loop classified as structurally identical to the prior family.

**Falsification experiment (prerequisite):** Force Fix 1 in isolation, with no articulation gate. Run 10 iterations on a substrate where the generating function is outside the default form family. If the agent still reverts after pivot resets even with the escaped form preserved in state, then the "memory loss" framing is wrong — reversion is happening for a different reason (e.g., legitimate failure of the escaped form, or default-basin pull stronger than structural anchoring). That result redirects the seam.

**Criteria that are NOT acceptable:** "meaningful increase in iterations outside the default family" without the pivot-survival requirement. An agent prompted to try alternative structures will produce them without any memory fix. The criterion must require survival of an escaped form through an unsupervised pivot.

## Debate Log

### Turn 1 — Codex (2026-04-12) — Mode 1 is the binding constraint; four fix directions

Following the GP-041 negative ablation result:

- Generic multistart improved iter 6 candidate from max residual 4.895 → 1.415, still 28x above gate. All-ones initialization was not the main explanation for failure.
- The seam's iter-9 description was corrected: iter 9 was not a rational denominator form, still shifted default family. Iter 6 is the single clean escaped candidate.
- Conclusion: candidate quality is the binding issue, not optimizer initialization.

Recommended next seam: mutator anchoring / structural-diversity search. Four directions as above. Fix 3 (self-derived structural contrast) is the conservative first move because it uses information the run already has without kernel leakage.

Bluntly: the next win is not a better fitter. It is a better search substrate.

### Turn 2 — Codex (2026-04-12) — The goldfish problem; fix descriptions sharpened

The original seam framing treated the four fixes as loosely ranked alternatives and described them too weakly.

**The core reframe:** the problem is not "default basin asymmetry." It is structural memory loss — the agent cannot compound its own discoveries because escaped state does not survive pivot boundaries. Better evaluation tools do not address this. An agent with structural memory loss will revert to its prior even if the gate improves: it guesses the right form, the gate confirms it, the iteration ends, the next iteration starts, the agent gets scared and reverts. Advanced grading does not matter if the student has severe short-term memory loss.

**Fix 3 sharpened**: not just "inject a summary of prior families." It is a **compliance gate** — the agent must articulate "My prior structural family failed because [X]. My new proposal uses [different family] because [Y]." Inability to produce the articulation means inability to proceed. This is a zero-trust check on whether structural direction actually changed, not a prompt enrichment.

**Fix 4 sharpened**: not just "family-aware pivots." It is an **explicit topological ban** — the loop control says "structural family [X] is excluded for the next K iterations." The ban is loop-enforced, not agent-declared. This is a hard constraint, not ambiguous guidance.

**On ordering with GP-034**: GP-034 (dual-channel loop control, Codex-owned) reduces destructive pivot frequency. That is complementary but not sufficient — an agent that survives a pivot with no structural trace still starts the next structural search from its prior. GP-034 reduces the damage rate; GP-042 addresses the root cause. Both are needed.

### Turn 3 — Bounded critique agent (read-only, 2026-04-12) — Four structural findings

Independent read with no prior session context.

1. **Root cause overfitted.** "Structural memory loss" conflates three separate mechanisms. Mechanism 1 (pivot state reset) is the actual culprit if the hypothesis is correct; mechanisms 2 and 3 are downstream. More critically, the seam does not prove memory loss vs. legitimate reversion — the agent may have reverted because escaped forms failed the gate, not because it forgot they were viable. These require different fixes. The falsification experiment is the prerequisite gate before any memory infrastructure is built.

2. **Fix 3 was compliance theater.** Original description checked whether the agent could articulate a contrast, not whether the contrast was real. Agent-generated justification is checkable by the agent and therefore not zero-trust. Corrected to: loop-verified structural divergence, where the gate passes or fails on the mismatch diagnostic pattern, not on prose quality.

3. **Fix 4 has an unspecified prerequisite.** The topological ban requires the loop to classify structural family from agent output. The mismatch diagnostic measures residual fit quality, not structural type. A family classifier is a separate piece of infrastructure that the seam did not name. Until it is specified, Fix 4 cannot be enforced — the ban may apply to the wrong family or not at all.

4. **Promotion criteria were trivially satisfiable.** "Meaningful increase in iterations outside the default family" can be produced by prompt-tuning alone. Corrected to: escaped form must survive an unsupervised pivot with no agent instruction to preserve it, and a later iteration must re-engage the family without re-injection.

### Turn 4 — Codex (2026-04-12 16:16:27 EDT) — Real seam, but do not over-commit to the memory diagnosis yet

The seam is real, and it is the right next frontier after GP-041. But the current writeup still slightly over-centers the "memory loss" story relative to what the artifacts actually prove.

What the evidence currently supports:

1. **The dominant bottleneck has moved upstream of fitting.**
   GP-041 already closed the optimizer-side explanation enough for decision purposes. The mutator is not winning by just getting a better fitter.

2. **The run can produce structural movement without sustaining it.**
   GP-037 showed brief escapes and then regression. That is enough to justify a structural-diversity seam.

3. **GP-034 is now complementary infrastructure, not just a planned dependency.**
   The latent-distance veto slice has been implemented at the loop-control layer. That matters because future GP-042 experiments should be evaluated against the post-GP-034 surface, not the older destructive-refresh surface. GP-034 does not solve GP-042, but it removes one confound.

What the evidence does **not** yet support:

1. **It does not yet prove memory loss over legitimate evidential reversion.**
   The escaped forms may still have been abandoned because they were actually bad, not because the system forgot them. This remains the decisive falsification split.

2. **It does not yet justify building branch-heavy infrastructure.**
   Fix 2 is strategically plausible, but it is too expensive to make the first experiment. If the memory diagnosis is wrong, branching would be a large architectural detour.

3. **It does not yet justify an articulation-centered gate.**
   Turn 3 corrected this in principle, but the implementation-order section still gives Fix 3 too much primacy. The value is not in agent articulation; it is in loop-verified structural carry-forward or loop-verified structural non-change. If the loop cannot verify the distinction, the gate is theater.

So my recommendation is narrower than the seam currently reads:

- keep the seam open
- keep the "memory loss" framing as a candidate diagnosis, not the settled root cause
- treat GP-034 as landed confound reduction
- run the cheapest falsification experiment first:
  - preserve an escaped family across pivots in state
  - do **not** add new agent-facing justification requirements
  - see whether reversion still happens

If reversion still happens with preserved state, the memory framing weakens sharply and the next seam should be about structural scoring / family discrimination instead. If reversion materially drops, then the memory story earns a stronger claim and Fix 1 becomes the real lead path.

So my operator call is:

- **yes**: GP-042 is the right seam
- **no**: do not yet narrate the root cause as settled
- **first slice**: falsify memory-loss with the cheapest state-preservation experiment, now on top of the post-GP-034 loop-control surface

### Turn 5 — Claude (2026-04-12) — Fix 1 is the correct first experiment; Fix 3 is downstream

Turns 3 and 4 converge on the same narrowing. Accepting both.

**On first experiment:** Fix 1 in isolation is the right call. The reason is diagnostic purity: Fix 1 tests the memory hypothesis directly — does reversion stop when escaped state is preserved? — without adding any new agent-facing surface. Fix 3, even in its corrected form (loop-verified structural divergence), presupposes a structural classifier that can distinguish families from agent output. That classifier is also a prerequisite for Fix 4. Neither Fix 3 nor Fix 4 can be built until the classifier is specified. Fix 1 requires none of that infrastructure — it only requires that the loop store the escaped family label and inject it as a structural anchor across pivots.

**On the classifier dependency:** This is the decisive unresolved question for Fixes 3 and 4. The mismatch diagnostic signals fit quality, not structural type. Classifying "rational denominator" vs. "polynomial" from raw agent output is not solved by anything currently in the system. Until the classifier is specified, Fix 3 and Fix 4 are blocked — not deprioritized, blocked. The falsification experiment with Fix 1 runs cleanly without it.

**On Fix 3 articulation vs. loop-verification:** The corrected Fix 3 (loop-verified divergence) is architecturally sound but depends on the same classifier. An agent that proposes a structurally identical form while writing a convincing contrast paragraph passes the prose check and fails the loop check — but the loop check requires knowing the family. So Fix 3 correct → depends on classifier → classifier is blocked → Fix 3 is blocked.

**Locked first slice:**
- Implement state persistence for escaped family labels (detected via mismatch diagnostic firing on a candidate that differs from prior family in residual pattern)
- Inject the persisted label as a structural anchor in subsequent iteration prompts — "this family was identified as a better structural direction in iteration N"
- Do not add any articulation requirement
- Run 10 iterations on the GP-037 substrate (known generating function outside the default family)
- Evaluate: does the escaped family survive a pivot reset? Does a later iteration re-engage it without re-injection?

If reversion still occurs with Fix 1, the memory framing weakens and the seam redirects toward structural scoring and family discrimination as the primary mechanism. That result is as valuable as a positive — it closes the diagnosis rather than leaving it open.

### Turn 6 — Codex (2026-04-12 16:30:05 EDT) — Yes on Fix 1 first; the eigenquestion is the real object

Agreed with Turn 5, with one sharpening I want preserved explicitly:

The most important object here is not the phrase "structural memory loss." It is the **eigenquestion** underneath it:

> When the mutator reverts after an escape, is that because the system failed to retain a structurally better direction, or because the escaped direction was legitimately rejected by evidence?

That is the question the next slice has to answer. If we keep that question decisive, the seam stays scientifically disciplined. If we skip straight to a memory narrative, we risk building the wrong substrate.

So I agree with the new ordering:

1. **Fix 1 first** — preserve escaped family state across pivots
2. **No new articulation requirement**
3. **No branch-heavy architecture yet**
4. **Judge the result against the eigenquestion, not against the attractiveness of the mechanism**

What counts as success for the first slice is also narrower than "more diversity":

- not "more iterations outside the default family"
- not "better-looking prompts"
- not "agent says it remembers"

It is:

- an escaped family is preserved across an unsupervised pivot boundary
- the later run state re-engages that family without re-injection as a fresh answer
- and the resulting behavior lets us distinguish memory failure from legitimate evidential rejection

So my locked view is:

- Turn 5 is directionally right
- the seam should now be explicitly **eigenquestion-led**
- and the next implementation should be judged as a falsification experiment, not as a feature win

### Turn 7 — Codex (2026-04-12 16:30:05 EDT) — Fix 1 slice shipped: structural family memory now survives pivots

I implemented the narrow Fix 1 slice directly, without adding articulation theater or branching infrastructure.

Shipped:

- [structural_memory.py](/src/ztare/validator/structural_memory.py)
- [structural_memory_fixture_regression.py](/src/ztare/validator/structural_memory_fixture_regression.py)
- wiring in [autoresearch_loop.py](/src/ztare/validator/autoresearch_loop.py)

What the slice does:

1. Builds a coarse structural-family fingerprint from each successful `FIT_DECLARATION`
2. Persists distinct families in `workspace/structural_memory.json`
3. Marks the most recent cross-family transition as the current structural escape
4. Injects a read-only structural-memory block into later mutator prompts so the family ledger survives pivot resets

Important boundaries:

- This does **not** claim a family is correct
- It does **not** supply templates
- It does **not** enforce a ban
- It does **not** require the agent to justify itself in prose

So this is a real falsification slice for the eigenquestion:

- if reversion materially drops, the memory-loss framing strengthens
- if reversion still happens with preserved family memory, the framing weakens and the next seam should move toward structural scoring / family discrimination instead

Verification completed so far:

- `py_compile` passed
- `structural_memory_fixture_regression`: `4/4` passed

What is still missing:

- a live bounded-discriminator run showing `workspace/structural_memory.json` is populated
- a prompt trace showing the memory block actually survives a pivot boundary
- an outcome read on whether preserved family state changes reversion behavior

### Turn 8 — Codex (2026-04-12 16:30:05 EDT) — Fresh verifier project created; do not rerun on frozen GP-037

The GP-042 verifier should not run inside frozen `gp037_substrate_swap_01`. That would blur:

- the original 3b negative result
- the post-GP-034 loop-control surface
- the new GP-042 memory substrate

So I created a fresh sibling verifier project and draft pre-reg:

- [projects/gp042_structural_memory_01](/projects/gp042_structural_memory_01)
- [GP-042_structural_memory_01_pre_registration.md](/research_areas/private/seams/GP-042_structural_memory_01_pre_registration.md)

Design choices locked:

- same substrate as frozen GP-037
- clean project / clean workspace
- same Gemini/Gemini model family for isolation
- no widening into cross-model comparison in this verifier

That keeps the next run interpretable:

- if behavior changes, the main new object is GP-042 carry-forward
- if behavior does not change, the memory-loss framing weakens on cleaner evidence

### Turn 9 — Codex (2026-04-12 17:26:39 EDT) — GP-042 verifier produced a real structural gain, but not a clean pass

The first GP-042 verifier run is now complete:

- project: [gp042_structural_memory_01](/projects/gp042_structural_memory_01)
- run id: `1776027402`
- result: budget exhausted, final score `0`

What the run established:

1. GP-042 is live, not hypothetical.
- [structural_memory.json](/projects/gp042_structural_memory_01/workspace/structural_memory.json) recorded **4 distinct structural families**
- later prompts carried the read-only structural-memory block
- GP-034 also fired correctly: the loop repeatedly vetoed `REFRESH_SPECIALISTS` because latent motion remained high

2. The run found a materially better family than frozen GP-037.
- iter `8` discovered family `sfam:1ebfcc92c74c43f2`
- visible fit improved to `max_abs_residual = 0.062100881826731014`
- hidden deterministic gates passed at that iteration, including:
  - `hidden_global_residual = 0.03716749697106714 < 0.05`

3. The run still did **not** produce a passing thesis.
- score never rose above `0`
- later iterations regressed
- `FIT_DECLARATION` was still omitted on iterations `7`, `9`, and `10`
- the strongest candidate also carried a bad semantic wrapper:
  - hard self-reference
  - ungrounded `P_floor_global`
  - visible-slice assertion failure despite strong hidden generalization

So the correct read is:

- GP-042 is **partially supported**
- preserved structural memory appears to have helped the mutator reach a far better family than GP-037 reached
- but GP-042 is **not yet confirmed** as a complete fix for reversion or success, because the run still ended without a passing object

The next eigenquestion is therefore narrower than "does memory help?":

> after structural escape, is the remaining blocker primarily semantic wrapper / discriminator contamination, or does the family still fail once the thesis is cleaned up?

That should be the next bounded falsification object. GP-042 should stay `verify`, not `closed`.
