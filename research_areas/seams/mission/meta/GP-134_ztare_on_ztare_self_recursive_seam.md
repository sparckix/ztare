# GP-134 — ZTARE-on-ZTARE: Self-Recursive Architectural Discovery

> **Seam metadata** · `seam_id:` GP-134 · `track:` mission · `status:` Active - live runs ongoing (iter 0-19 observed 2026-04-23). · `last_updated:` 2026-05-08


**Status:** Active — live runs ongoing (iter 0-19 observed 2026-04-23).
**Opened:** 2026-04-23
**Parent:** GP-131 (Level 2 daemon / work-discovery loop — this seam is a specialization: use ZTARE itself as the substrate for ZTARE-improvement discovery).
**Related:** GP-133 (discovery panel — Rounds 1-4 all inform this seam), GP-101 (executable validator — now enforces map discipline).

---

## Eigenquestion

**Can ZTARE, applied to the target substrate "the ZTARE apparatus itself," discover a small bounded set of architectural primitives whose addition converts the apparatus from a fitting instrument into a constructing engine — and does the rubric + charter + scoring discipline produce primitives that are algorithmically concrete AND generatively yield-bearing, or does the apparatus produce Kepler-class verbal layering dressed in novel vocabulary?**

---

## Substrate

- **Project slug:** `ztare_on_ztare`
- **Target:** architectural primitives for the ZTARE apparatus itself (the outer-loop autoresearch_loop + compress_champion + rubric discipline)
- **Observable:** thesis.md containing 2-5 primitives, each with required fields (Description, Code-level insertion point, Named mechanism, Secondary observable, Falsifiable claim, Derivation sketch)
- **Evaluation:** qualitative rubric (`rubrics/ztare_on_ztare.json`) scored by a Newton-mode judge persona (gpt4.1) against 6 dimensions summing to 100%
- **Mode:** `rubric_mode: "newton"` (Generative Yield required, weight 20)

---

## Why this is a substrate worth running

Three reasons each of which would justify it alone:

1. **Dog-fooding discipline.** If the apparatus cannot discover what it needs to improve, the claim "ZTARE is a discovery tool" is weakened. Apparatus that cannot look at itself is apparatus that cannot self-correct.

2. **Cheap adversarial pressure.** A qualitative architectural-primitives rubric against a well-scoped charter is a pure prompt-level experiment: $1-2 per 10-iter run, API-bound. The marginal cost of attempting this is negligible.

3. **Mechanistic diagnostic on the apparatus's own failure modes.** When the mutator gets stuck on registry-closure-style verbal proposals, that tells us something about HOW the mutator is prompted + evaluated — not just about the substrate. Iter-by-iter score trajectories on ztare_on_ztare are diagnostic of apparatus-level drift that other substrates can't reveal.

---

## Run history

### Run 1 — 2026-04-23 AM, original loose rubric

- ITERS 10, gemini-pro mutator + gpt4.1 judge, original rubric without Mechanism Algorithmic Concreteness or Generative Yield dimensions
- Trajectory: 10 → 27 → 17 → 26 → 9 → 21 → 21 → **51** → 21 → 23 → 23
- Peak at iter 8 (51) via topological pivot — mutator proposed primitives with forward-observable-gate
- But Gemini-Pro critique landed: the 51 was "perfectly compliant but structurally hollow" — primitives named no secondary observable, Primitive 1 reduced to symbolic-registry-extension (Kepler epicycle layering)

### Run 2 — 2026-04-23 PM, rubric hardened w/ Mechanism Algorithmic Concreteness

- ITERS 10, same model pair, rubric added 5th dimension (Mechanism Algorithmic Concreteness, 15%)
- Trajectory: 0 → 27 → 29 → 44 → 23 → 44 (in progress at time of writing)
- Rebaseline from 51 to 0 is EXPECTED — new dimension punishes verbal primitives that don't name libraries/algorithms
- Climb to 44 indicates mutator partially adapting (naming scipy / numpy functions) but not yet fully compliant

### Run 3 (planned) — 2026-04-23 evening, rubric under Newton-mode

- Rubric now has `rubric_mode: "newton"` + Generative Yield dimension (20%) + charter Secondary-observable field requirement
- Expected behavior: iter 1 drops to 10-25 (Newton-mode penalty stacks with Mechanism-Concreteness penalty for hollow primitives). Iter 3-5 should recover if mutator names secondary observables. Iter 8-10 should exceed Run 2's peak if Newton-mode discipline works.
- Planned command: `make experiment-loop PROJECT=ztare_on_ztare RUBRIC=ztare_on_ztare ITERS=10 MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gpt4.1 DYNAMIC=1`

### Future run (after DAG steering ships)

- Add Bayesian DAG surgical insertion + steering (per Gemini Pro 2026-04-23 PM suggestion): parse `latest_probability_dag.json`, compute per-node urgency = edge_weight × (1 − node_probability), prepend highest-urgency node's watch_signal to mutator prompt each iter
- This converts the DAG from passive reflection into active inference (Friston-style)
- Expected additional effect: mutator's attention is ex-ante steered toward the weakest link in its own belief structure

---

## Decisive findings so far

1. **Rubric hardening works as a discipline.** The rebaseline from 51 to 0 between Run 1 and Run 2 proves that Mechanism Algorithmic Concreteness catches verbal primitives that loose rubrics silently admit. This is evidence that rubric-dimension design is a controllable lever on what the apparatus will accept.

2. **Producer-vs-critic capability asymmetry is real.** Both the mutator (gemini-pro) and critics (gpt4.1 judge, plus Gemini Pro in-session) have comparable model capability. Yet the mutator produces verbal primitives that the critics immediately identify as Kepler-epicycle-layering. The asymmetry is NOT capability-level; it is cognitive-task-framing (production under format pressure vs critique with format freedom). This finding generalizes beyond ztare_on_ztare to any agent-as-producer-plus-agent-as-critic architecture.

3. **Topological pivot (GP-021 primitive) fires on a re-runnable substrate.** Iter 8 of Run 1 hit 51 after 7 iterations of oscillation. The mechanism — when the mutator is scored-stuck, invert the prior output and try the opposite topology — is NOT ztare-on-ztare-specific; it is a general apparatus capability. Watching it fire on a self-referential substrate is clean evidence the primitive works.

4. **Newton-mode rubric is necessary but not yet validated.** Run 3 is the test. If Newton-mode pushes total score toward 60+ via Generative Yield, the rubric-level fix is sufficient. If Run 3 plateaus at 30-45 (same ceiling as Run 2), the mutator is structurally stuck in Kepler mode and the DAG steering patch (Gemini Pro proposal) becomes necessary.

---

## Falsifiable predictions

| # | Prediction | Test | Kill level |
|---|---|---|---|
| P1 | Newton-mode rubric + Generative Yield dimension cause measurable shift: Run 3 peak score > Run 2 peak (44). | Observed peak across 10 iters. | Peak ≤ 44 → Newton-mode rubric alone is insufficient; ship DAG steering next. |
| P2 | Mutator at some iter names ≥1 secondary observable with evaluation method + expected value (satisfies Generative Yield dimension's full-credit criterion). | Inspect per-iter debate logs for the four-field primitive structure including Secondary observable field. | Zero iters produce a valid Secondary observable → charter + rubric nudge insufficient; need secondary-sub-prompt refactor (Item b). |
| P3 | Run 3 produces ≥1 iter with total score ≥60 that is not rebaselined away by iter 10. | Score trajectory. | If peak ≥60 but rebaselined back to ≤30 by iter 10, convergence is unstable; apparatus mode-switches rather than converges. |
| P4 | Across Runs 2 and 3, primitives proposed by the mutator accumulate a discovery_class taxonomy: mostly `recognition` (naming existing techniques), with 0-2 `synthesis` (novel combination with derivation), 0 `synthesis_incompressible`. | Post-run manual classification against discovery_class_classifier.py. | ≥3 `synthesis` across two runs → the apparatus IS generating architectural novelty; proceed to paper. Zero `synthesis` over both runs → apparatus is a sophisticated recognition engine, honest label. |

---

## Relationship to GP-131 and GP-133

- **GP-131 work-discovery loop:** ztare_on_ztare IS a GP-131 target case. If GP-131's daemon were running, ztare_on_ztare would be a candidate it surfaces as a proposal. This seam instantiates the work.
- **GP-133 discovery panel:** the Newton-mode rubric + Generative Yield dimension + discovery_class taxonomy + py_exec governance all emerged from GP-133 Rounds 1-4. This seam is where those rubric-level disciplines get tested operationally.
- **Feedback loop:** findings from ztare_on_ztare runs update the GP-133 panel. Run 2's rebaseline-from-51-to-0 on hardened rubric is the empirical validation that Round 4's Mechanism Algorithmic Concreteness dimension does what it claims.

---

## Open items

- [ ] Run 3 launch (Newton-mode) + analysis of trajectory vs P1-P4
- [ ] After Run 3, ship DAG steering patch (Gemini Pro proposal) and run it as Run 4
- [ ] Per-iter discovery_class classification of produced primitives (manual for now; automate once corpus is > 20 primitives)
- [ ] If a `synthesis` classified primitive appears, domain-expert review + spec draft
- [ ] Update F-row for ztare_on_ztare in `EXPERIMENT_TRACK_RECORD.md` after each run closure
- [ ] Paper methodology track reference: the producer-vs-critic asymmetry finding (point 2 above) belongs in the methodology paper as a distinct INS entry

---

## Meta

This seam is the concrete dog-food for the full GP-133 discovery discipline. It tests whether the apparatus's rubric-level, charter-level, and governance-level disciplines produce primitives that survive the apparatus's own Generative Yield criterion. If yes: strong validation that the discipline-stack works. If no across runs 3 and 4: the apparatus is a sophisticated recognition engine and the appropriate next-step is to reframe its external claims accordingly.

Not a failure either way — both outcomes are scientifically informative.

---

## 2026-04-23 16:10:00 EDT — Reality Sync After Newton-Mode Runs

The seam text above is now stale if read literally as a live-run summary. Run 3 was not merely "planned"; multiple Newton-mode runs have now executed under the same rubric fingerprint (`234b0de5b57e63a5`) and dynamic committee regime. The current project state is:

- **Run 3 (`run_id 1776963510`)** reached **79** at iteration 3 under Newton-mode, with a thesis centered on analytic/functional invariance hardening via symbolic global checks, unit audit, and provenance trace. Weakest point: ultra-deep / obfuscated provenance laundering remained unclosed.
- **Run 4 (`run_id 1776968076`)** reached **66** at iteration 5 with a three-primitive stack (sweep audit, forward observable/SFF gate, correctness-tax audit). Weakest point: all three primitives still relied on empirically selected thresholds (`±10%`, `7/9`, `40%`), leaving them vulnerable to adversarial tuning.
- **Run 5 (`run_id 1776969970`)** budget-exhausted at iteration 15 with **best score 55** and latest-iteration score 47. The live loop converged on a more concrete thesis (AST unit propagation, functional parameter audit, SFF config-lock, externalized audit), but the judge's repeated verdict was stable: **thresholds remain cooked, unit algebra is incomplete, and out-of-window robustness is asserted more than derived.**

### Hypothesis status against P1–P4

- **P1 (Run 3 peak > Run 2 peak 44): CONFIRMED.** Newton-mode plus DAG steering did produce materially higher peaks (79, then 66).
- **P2 (valid secondary observables appear): CONFIRMED in weak form.** The mutator now routinely names secondary observables with evaluation methods. This closes the "verbal-Kepler" failure mode.
- **P3 (peak ≥60 that is not rebaselined away): NOT CONFIRMED.** High peaks occurred, but they were not stable. The loop remains vulnerable to collapse back into threshold-heavy descriptive gating proposals.
- **P4 (0–2 synthesis-class primitives): UNRESOLVED but trending toward `recognition`, not `synthesis`.** The strongest candidates so far mainly recombine known audit/gate ideas (symbolic checking, unit algebra, SFF, external audit) into a sharper architecture. That is useful, but it is not yet clear architectural novelty in the strong sense.

### Updated interpretation

The loop has discovered something real, but narrower than the seam's original hope:

1. **It can escape pure registry-closure/verbal-layering basins.**
2. **It can generate Newton-mode-compliant primitives with named mechanisms and secondary observables.**
3. **It then falls into a new local optimum:** "discovery-class architecture" gets operationalized as an increasingly elaborate **adversarial gate stack** whose thresholds remain empirically hand-fit.

That is not null. It is evidence for a more precise claim:

> The first stable move beyond Kepler-class verbal proposals is not free-form architectural invention but the emergence of audit/externalization/forward-observable primitives. However, without first-principles threshold grounding, these proposals remain recognition-class hardening rather than a settled constructing-engine blueprint.

### Immediate next question

The discriminating next move is no longer "can the mutator name secondary observables?" It can. The next question is:

> **Can ZTARE propose a primitive whose acceptance boundary is derived from operator-internal invariance, ensemble theory, or external published constants rather than cooked pass bands?**

Until one such primitive appears and survives attack, the live best reading of `ztare_on_ztare` is:

- **positive on rubric/charter hardening**
- **positive on producer→critic asymmetry diagnosis**
- **negative / unresolved on full constructing-engine conversion**

---

## 2026-04-30 10:55:30 EDT — New Self-Recursive Target from `gp163d` / NS

The `gp163d` gravity and NS Millennium loops identify a better next
ZTARE-on-ZTARE target than another free-form primitive search:

> Can ZTARE recover and replay the operator-supervisor's post-positive
> discriminator choices from artifacts alone?

This is narrower and more testable than "can ZTARE invent architecture?" The
recent frontier work shows that the apparatus already has useful gates and
ledgers, but the next decisive experiment is still often selected in chat. The
candidate primitive is therefore not a new physics solver or a new mutator
persona. It is a structured discriminator queue plus a background-debt ladder:

```text
local mechanism -> exported/background debt audit -> control ladder
-> dynamic/admissibility bridge
```

This target avoids the cooked-threshold problem that weakened earlier
`ztare_on_ztare` primitives. The acceptance boundary is artifact recovery:

- Can the historical next move be reconstructed from saved outputs?
- Does it map to a small reusable template?
- Does the template name a concrete kill test and required artifacts?
- Does it preserve what remains human-gated?

This is now pre-registered as `H-XDOMAIN-5AV` and opened as
`GP-190_post_run_discriminator_daemon_seam.md`.

---

## Strange-loop expansion (2026-05-06 PM addendum)

### The realization

Original GP-134 (2026-04-23) framed ZTARE-on-ZTARE as: run the iter
loop on a self-referential substrate (architectural primitives for the
apparatus itself). That worked for one cycle, hit verbal-layering
limits (Run 1 peaked at 51 then judged "structurally hollow"), and
went mostly dormant as Research Director agents (Codex on NS Track B,
Claude as Director on consciousness/gravity, etc.) shifted most R&D
OUTSIDE the ZTARE evaluation surface.

The 2026-05-06 PM operator realization breaks the original framing:

> "It doesn't matter that RD and Claude agents are doing things outside
> ZTARE — as long as we mine insights from the apparatus's data
> ecosystem (F-rows, project workspaces, papers, seams), we can feed
> those mined signals back into ZTARE-on-ZTARE with **expanded scope**:
> the substrate becomes 'what happens outside the apparatus' itself."

This is a beautiful strange loop because:

  1. **Agents are interchangeable from the gain cycle's perspective.**
     RD agents, Claude agents, human-operator typing — all produce
     artifacts that hit the same data substrate. The mining layer
     doesn't care which agent did what.
  2. **Mining IS the recursive cell.** The cycle runs at week-scale
     not iter-scale, but it has the same shape: produce artifacts →
     mine signals → propose refinement → refinement reaches the
     apparatus. Today's `mine_*.py` scripts plus the GP-227 trajectory
     dashboard form one full revolution of this cycle.
  3. **The expanded-scope substrate inverts the original framing.**
     Original GP-134: "run ZTARE on ZTARE-as-substrate" (small,
     self-contained). Expanded GP-134: "run ZTARE on the apparatus's
     own corpus of work this week" (large, growing). The larger
     substrate gives the iter loop more material; the rubric scores
     "given everything produced this week, what refinement would have
     produced more / better?"

### Why this resolves the dormancy concern

Run-3+ of original GP-134 got harder to motivate as the apparatus's
useful work shifted to substrates (NS, gravity, consciousness) that
lived outside ZTARE iter loops. The expanded-scope framing makes that
shift IRRELEVANT: as long as the work hits the data ecosystem, the
mining harvests it, and ZTARE-on-ZTARE-with-expanded-scope ingests it
as substrate. The agent identity is decoupled from the gain cycle.

### Proposed substrate v2 (provisional spec)

**Project slug:** `ztare_on_ztare_v2_expanded_scope`

**Target:** apparatus refinements derived from this week's full output
corpus (mining outputs + F-rows + seams + project workspaces).

**Substrate construction:**
  - Inputs to substrate: the outputs of `mine_trajectory_curves.py`,
    `mine_reference_graph.py`, `sample_artifacts_for_taste.py` (after
    rating), `mine_recursive_gain_candidates.py`, plus the week's
    F-row diff + new seams + new project workspace artifacts.
  - Substrate.meta.class: `meta_apparatus_corpus` (new class — needs
    cage_meta entry).
  - Each "candidate" the mutator proposes is an apparatus refinement:
    a new primitive, a wired loop (one-shot → recursive), a retired
    decorative gate, a new ZTARE substrate, etc.
  - Each candidate must reference SPECIFIC mined evidence: "I propose
    primitive X because closure-pattern miner showed v5-op Y has Lane
    A density Z across N substrates" (not "I think apparatus needs X").

**Rubric (provisional v2):**
  - **Evidence-anchored** (25%): every claim cites a specific mined
    output line with verifiable JSON-path reference
  - **Cost-bounded** (15%): refinement cost-estimate falls in
    {trivial / day / week / month}; high-cost refinements need higher
    expected-gain justification
  - **Recursive-gain-mechanism named** (20%): refinement names which
    of the 6 mechanisms it instantiates (retire / wire-loop / promote-
    primitive / new-substrate / revive-stalled / self-skeptic)
  - **Anti-tautology** (15%): refinement must NOT just restate an
    existing primitive's behavior; must add structure
  - **Falsifiable** (15%): refinement must name a kill-criterion
    measurable in next week's mining output
  - **Generative yield** (10%): refinement must enable downstream work
    that cannot be done without it (else it's decorative)

**Cadence:**
  - Weekly run, Monday morning, ingesting the prior week's mining
    outputs.
  - Each iter is one candidate apparatus refinement; iters 1-10 per
    run.
  - Champion gets operator-reviewed before promotion (no auto-modify
    of apparatus state).

**Falsifier:** if 3 consecutive weekly runs produce zero champions
the operator agrees to ship, the substrate is wrong (either the rubric
is too tight or the mining isn't surfacing actionable evidence).
Diagnose and revise.

### Connection to GP-227 trajectory dashboard

GP-227's `mine_recursive_gain_candidates.py` already produces the
candidate stream this substrate would consume. The current behavior
is: operator reads the dashboard, hand-picks moves to ship. The v2
substrate replaces "hand-picks" with "ZTARE iter loop selects under
rubric discipline." The dashboard becomes the substrate for v2's
mutator.

### Risks

  1. **Goodhart on the rubric.** "Evidence-anchored" can be gamed by
     citing arbitrary mining lines. Mitigation: rubric requires
     verifiable JSON-path quotes that the validator pre-flight checks
     against the actual mined files.
  2. **Mining-output as substrate creates a meta-Goodhart.** If the
     substrate evaluates apparatus refinements that themselves change
     what the mining outputs, the substrate is moving. Mitigation:
     freeze the mining-output snapshot per run; refinements that
     change mining-script behavior produce next-week's substrate, not
     this week's.
  3. **Dormancy still possible if mining outputs are sparse.** If a
     week has thin mining signals (e.g., few F-row closures, low
     compounding ratio), the v2 substrate has nothing to chew on.
     Mitigation: that's a real signal — if the apparatus produces
     thin output, we should know that, not paper over it with
     synthetic candidates.

### Decision

**Promote this addendum from seam → spec when:**
  - Operator confirms expanded-scope framing (this addendum's purpose)
  - GP-227 dashboard has been used for 2+ weeks of operator-mediated
    refinement-shipping (so we have a baseline to compare ZTARE-loop-
    mediated shipping against)
  - At least one rubric draft survives a panel-review pass without
    "structurally hollow" critique

This addendum is an ARCHITECTURAL PROPOSAL, not a build commitment.
The build is gated on operator approval + the two confirmation tests
above.
