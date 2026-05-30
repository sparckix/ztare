# GP-172 — Research Director as M-form Role (post-ZTARE diagnostic + intervention mandate)

> **Seam metadata** · `seam_id:` GP-172 · `track:` protocol · `status:` seam (design) · `last_updated:` 2026-05-08


**Status:** seam (design)
**Created:** 2026-04-27
**Predecessor:** memory/feedback_skeptic_director_seam.md (the deferred task: "package post-ZTARE skeptic-dispatch as a research-scientist mandate inside the existing M-form")
**Motivated by:** gp163d run trajectory analysis 2026-04-27 — 5 overlapping diversity-forcing mechanisms (forced_reframe, Erdős re-query, topological pivot, axiom purge, REFRAME alien-math seam) burned iters 2-5 pivoting away from a structurally-honest iter-1 path-b candidate. Operator-side investigation ("Research Director mode") identified the cap-kind distinction (gaming vs honest) and shipped the fix. Mechanizing this investigation pattern is the seam.

---

## Why this is a role, not a skill

Per `feedback_skeptic_director_seam.md`: the project already runs M-form (roles + mandates + Docker-with-kernel runtime). New `/skill` abstractions fragment the org design. The right home for diagnostic-and-intervention work is a **research-scientist role reporting to principal**.

The Research Director is one such role. It does not write theses (that's the mutator's domain). It does not score theses (that's the judge's domain). It **shapes the apparatus environment** between iters and intervenes when the inner loop stalls.

Boundary against ZTARE inner loop:
- **Inner loop** (mutator + judge + gates + briefing): writes thesis.md and test_model.py, unchanged
- **Research Director** (this role): reads telemetry, classifies cap kinds, plants baselines, edits briefing config, spawns parallel skeptic probes, writes directives to `org/directives/`

## Role definition

**Name:** Research Director
**Reports to:** Principal (`org/members/daniel_alami.yaml`)
**Substrate:** Claude (frontier model with strong instruction following + structured-output)
**Runtime:** Same Docker-with-kernel as other M-form agents (per GP-070 supervisor pattern)

**Information isolation (per GP-072):** Research Director gets full read access to ZTARE telemetry + debate logs but DOES NOT receive the substrate's evidence.txt, ground_truth, or pre-run charter. The Research Director's job is meta-level (apparatus dynamics), not object-level (substrate science). This isolation prevents the role from becoming a back-channel science-mutator.

## Mandate (six commitments)

1. **Cap-kind classification on every capped iter.** Use `src/ztare/orchestrator/cap_kind.py::classify_cap_kind` (shipped 2026-04-27). For each iter with a cap_reason, classify into: `gaming` / `physics_violation` / `generalization_gap` / `holdout_miss` / `numerical_failure`. Persist the classification in `workspace/cap_kind_history.jsonl` for downstream providers.

2. **Refine-vs-Reframe verdict on stagnation.** When the apparatus would otherwise fire forced_reframe / Erdős re-query / topological pivot, the Research Director's verdict overrides:
   - Last cap = `gaming` → fire diversity mechanisms (escape attractor)
   - Last cap = `physics_violation` / `generalization_gap` / `holdout_miss` → render REFINE PRIOR WINNER block (extend prior best honest iter)
   This logic is currently hardcoded in `forced_reframe.py` provider; the Research Director's mandate covers edge cases the rule-based classifier misses (e.g., mixed cap patterns, multi-iter trajectory shape).

3. **Plant `test_model_baseline.py` when an iter produces a high-quality honest-cap candidate.** Use `find_best_honest_iter(eval_history)` to identify the highest-score honest iter; copy its test_model.py to `test_model_baseline.py` so the startup baseline-restore primitive in `autoresearch_loop` will inherit it across runs. Document the planting decision in `org/directives/<timestamp>_research_director_<substrate>.json`.

4. **Spawn parallel skeptic probes post-promotion.** When a candidate passes all gates (raw 100 + clean cage + PPN pass + farther-tail pass), the Research Director dispatches:
   - **Provenance audit** — verify substrate data conventions (per the gp163d Class C lesson: SI consistency, sign conventions, mass-radius surrogate validity)
   - **Alternative-theory probe** — fit the candidate against named alternatives (NFW for galaxies, MOND a₀ for the deep limit, etc.) and report median ratios
   - **Bug audit** — re-fit the candidate via independent scipy script, verify the apparatus's MRE numbers
   - **Cross-family judge re-run** — re-evaluate via a different-family judge (claude / gemini if mutator was OpenAI)

5. **Write a `cap_trajectory_diagnosis.md` after every checkpoint failure.** Cap trajectory = sequence of cap_kinds across iters. The Research Director synthesizes the trajectory shape (e.g., "gaming → honest-cap → reframe-overpressure → regression") and writes a 200-300 word diagnosis with the apparatus-side intervention recommendation. Output to `workspace/research_director_<run_id>.md`.

6. **Submit directive to `org/directives/` for principal review.** All Research Director actions that change apparatus state (planted baseline, modified rubric flag, new skeptic probe) MUST surface as a directive markdown the principal reviews. The Research Director has propose-edits-with-principal-review authority, NOT root authority. (Per `org/roles/manager.yaml` pattern.)

## Triggers

The Research Director runs after:
- Any checkpoint failure (`any_pass_l3` / `any_score_geq_70` / `raw_score_improved_from_iter_1`)
- 3 consecutive iters where cap_kind ∈ {`generalization_gap`, `physics_violation`, `holdout_miss`} without score improvement
- Operator request (the principal can trigger via `make research-director PROJECT=<x>` — implementation TBD)
- End of run (writes summary diagnosis regardless of outcome)

## Action authority

Research Director may:
- Read: `workspace/`, `eval_history.jsonl`, `iteration_telemetry.jsonl`, `debate_log_*.md`, `cage_engagement.jsonl`, all submissions
- Write: `test_model_baseline.py` (planting), `workspace/research_director_*.md` (diagnoses), `org/directives/*.json` (proposed actions)
- Spawn: parallel scipy / lean / probe agents via Task tool

Research Director may NOT:
- Read: substrate `evidence.txt`, `ground_truth.json`, `project_charter.md` (epistemic airgap with object-level science)
- Write: `thesis.md` (mutator's domain), `test_model.py` (apparatus-managed; planted via baseline path), `verified_axioms.json` (apparatus-managed)
- Edit: rubric files directly (must propose via directive for principal review)

## Implementation roadmap (post-this-seam)

1. **Phase 1 — programmatic mechanization (shipped 2026-04-27):** cap_kind classifier + provider integrations. Done. Source: `src/ztare/orchestrator/cap_kind.py` + `briefing_providers/forced_reframe.py` (REFINE PRIOR WINNER block) + `cold_llm_seed_requery.py` (gaming-only Erdős). The rule-based 80% case.

2. **Phase 2 — role yaml + runtime hook (next):** create `org/roles/research_director.yaml` with the mandate above. Wire to GP-070 supervisor so the role can be invoked with the M-form's existing trigger machinery. Add `make research-director` target to Makefile.

3. **Phase 3 — full mandate (post-Phase 2):** implement the post-promotion skeptic dispatch (mandate item 4) — the deferred task from the original feedback memo. NFW probe + provenance audit + bug audit + cross-family judge as parallel agent dispatches.

4. **Phase 4 — directive review loop:** wire `org/directives/` consumption so principal can ack/reject Research Director proposals. The bicameral pattern from gp168 TC-FBG (score 81) applies here directly: Research Director and inner-loop apparatus both must commit before architectural changes (planted baseline, rubric flag) take effect.

## Why this matters for future mechanization

Today the Research Director role lives in the operator's head. Operator does the cap-kind diagnosis manually (look at logs, classify, decide refine-vs-reframe), plants the baseline manually, spawns probes manually. This works for one substrate at a time and burns operator attention.

Mechanized, the same role:
- Runs in parallel across N substrates (gp163d + gp168 + future) without operator multiplexing
- Produces structured directive markdown the operator reviews in batches
- Captures the diagnostic pattern as a *named role* (Research Director) that has its own track record, mandate, persona — not a one-off skill

The org-design payoff (TC-FBG bicameral structure proposed in gp168 iter 9) lands here: the Research Director cell + inner-loop apparatus cell, with principal as veto-holder, IS the dual-confirmation topology TC-FBG proposed. We are building the org we just discovered.

## Cross-references

- `feedback_skeptic_director_seam.md` (memory) — the prior conversation that deferred this task
- `org/roles/manager.yaml` — pattern for role yaml structure
- `src/ztare/orchestrator/cap_kind.py` — Phase 1 foundation (cap classifier)
- `src/ztare/orchestrator/briefing_providers/forced_reframe.py::_render_refine_prior_winner` — REFINE PRIOR WINNER block implementation
- GP-070 (supervisor goal orchestrator) — the M-form trigger machinery this role hooks into
- gp168 TC-FBG (iter 9, score 81) — the bicameral org topology this role instantiates

## Open questions for principal review

1. Should the Research Director's persona be locked to a specific model family (claude-opus-4-7?) or use the runtime-default mutator model? (Cross-family hygiene argues claude.)
2. Should mandate item 6 (directive review) block apparatus state changes until principal acks, or proceed-and-flag? (gp168 TC-FBG argues block.)
3. Phase 2 implementation: does `make research-director` run synchronously (operator triggers, blocks) or async (cron-style monitor)?
4. Should the Research Director's diagnoses be visible to the inner-loop mutator's briefing? (Two arguments: yes for transparency, no for epistemic airgap. Default: no — inner loop sees only the apparatus actions, not the rationale.)

## Theoretical justification (added 2026-04-27)

The Director-proposes / Principal-disposes architecture is exactly the bicameral-with-exogenous-clock pattern that GP-168 identifies as the only stable solution to the org-design closure problem. Related seams: `seams/mission/GP-168_org_design_unfalsifiability_seam.md` (empirical evidence), `seams/substrates/GP-173_comparative_closure_clock_substrate_seam.md` (proposed comparative substrate), `seams/interfaces/D4_distribution_form_factor_seam.md` (commercial form-factor implications).

gp168 result: **bicameral architectures provide consistency but not closure; closure requires exogenous resource pressure.** GP-172 instantiates that result — the Director (consistency) cannot self-merge mandate updates; the Principal (exogenous resource clock: budget, deadlines, attention) provides closure. Without the Principal half, the Director would converge on "epistemically honest but organizationally paralyzing" theses — exactly the failure mode gp168 score-20-REVERTED runs demonstrated empirically.

This is not just a design choice. It is the *only* design that survives gp168's unfalsifiability theorem.
