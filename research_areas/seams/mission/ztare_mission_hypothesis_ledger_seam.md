# ZTARE Mission Hypothesis Ledger Seam

> **Seam metadata** · `seam_id:` ztare_mission_hypothesis_ledger_seam · `track:` mission · `status:` Active - 2026-04-13 09:22:36 EDT (renamed to match actual ro · `last_updated:` 2026-05-12


## Status

Active — 2026-04-13 09:22:36 EDT (renamed to match actual role as the mission-level hypothesis ledger; last touched: `sandbox_04` reality sync + successor-program pre-registration lock)

## Purpose

This seam exists to record mission-level debates about what ZTARE is *for*, as distinct from debates about how any particular program (GP-023, GP-028, GP-047, etc.) should be implemented. It is the home for experiment-selection arguments where the question is not "how do we build X" but "should we build X at all, given what ZTARE is supposed to be doing."

Program-specific seams (`GP-023_...`, `GP-035_...`) stay where they are. This seam is for the framing questions that cut across programs.

## Problem Statement

**ZTARE is being built to mechanize scientific discovery, not to produce benchmark scores.**

The distinction is decisive and easy to lose under experimental pressure. A benchmark asks: *given a fixed target, how well does the system reach it?* A discovery engine asks: *given an unknown target, can the system derive a true statement about reality that a human reviewer would accept as novel?*

The failure mode of confusing the two is not theoretical. It looks like this:

- running another experiment when the existing run's data has not been analyzed
- generating more iterations to answer questions the existing iterations already answer
- choosing experiments by cost-to-execute rather than information-yield-per-experiment
- treating "score went up" as the success criterion instead of "we learned something about how the search fails"
- optimizing the apparatus against specific sandboxes instead of against the discovery workflow
- adding mechanisms because they are implementable rather than because they address an identified bottleneck

A benchmark-shaped ZTARE would still be useful — it would tell you which models are good at a fixed task. A discovery-shaped ZTARE is a different object: it is a system whose outputs are *findings about how recursive falsification-driven search behaves on real problems*, and whose apparatus changes are justified by what they teach us about that behavior, not by their effect on any particular run's score.

## What We Are Solving For

1. **Information yield per experiment,** not score per experiment. Every run must produce something that was not already knowable from prior runs. If a proposed run would tell us something we already know, it is not worth executing regardless of cost.
2. **Analytical moves before experimental moves.** When a closed run has produced data that has not been analyzed, the next step is analysis, not another run. Experimental budget is finite; analytical budget on already-collected data is the cheapest high-value operation available.
3. **Apparatus changes justified by identified bottlenecks,** not by implementability. A mechanism that is easy to build but does not address a bottleneck the data has already revealed is noise, not progress.
4. **Preserve the findings that make ZTARE epistemically honest.** The Compress leg (GP-046 farther-tail holdout), the Invert leg (cold-residual / always-invert discipline), and the Adversarial Disagreement leg are decisive because they make the system's refusals real. Any experiment that would soften those legs for convenience is disqualified regardless of its promised score improvement.
5. **Publishable null results are wins,** not failures. A well-designed experiment that shows a proposed mechanism does not work is a finding; the pre-registration discipline exists specifically to make these outcomes publishable rather than hidden.

If a proposed action does not serve items 1–5, it is either a benchmark-shaped move (optimize a score against a fixed target) or a capacity-fill move (do something because the system is idle). Neither counts as discovery.

---

## H-GP154N-01 — Normalized Neural Scaling Law

- **Hypothesis:** The transferable neural scaling object is not raw loss `L`, but a gauge-normalized excess-loss curve coordinate `z=(L-L_min(curve))/(L_max(curve)-L_min(curve))`.
- **Eigenquestion:** Does removing per-curve floor/amplitude gauges turn the raw-loss farther-tail failure on Hestness/Henighan into a compact transferable curve-shape law?
- **Discriminating test:** Run `gp154_scaling_law_normalized` with the custom bounded-`z` gate: HOLDOUT MAE `<0.08` on Chinchilla/Kaplan and FARTHER_TAIL MAE `<0.15` on all Hestness/Henighan, with R20/R21/R22/R24 enforcing no curve/source/study lookup or hidden defaults.
- **Success criterion:** A K<=8 closed-form `I_model(features)` passes both gates without lookup-table branching and declares at least one secondary curve-shape observable.
- **Kill condition:** Holdout passes but farther-tail fails after gauge normalization, implying exponent/regime structure remains domain-specific; or the only passing form uses `study`, `source_paper_table`, or `curve_id` lookup.
- **Scope:** GP-154 neural scaling-law track, successor to the raw-loss v2.2 run.
- **Status:** `closed / partial_null`
- **Opened:** 2026-05-01 00:19:25 EDT
- **Closed:** 2026-05-01 01:02:00 EDT
- **Runnable packet:** `projects/gp154_scaling_law_normalized`, `rubrics/gp154_scaling_law_normalized.json`
- **Result:** The hypothesis was partially supported but not sufficient. The normalized target repaired the raw-loss gauge problem locally: iter 2 passed Chinchilla/Kaplan holdout (`MAE=0.043 < 0.08`). It failed Hestness/Henighan farther-tail transfer (`MAE=0.317 > 0.15`), so "normalize `L`" alone is not the universal object. The failure exposed a stronger offline invariant: the curve-shape collapse depends on the sweep axis.

## H-GP154N-02 — Axis-conditioned normalized collapse is the transferable neural scaling object

- **Hypothesis:** After per-curve gauge removal, the transferable neural scaling object is an axis-conditioned collapse law `z = curve_axis_rev ** alpha_axis`, with pure `N` and `D` sweeps sharing a shallow exponent (`alpha≈1.46-1.48`) and mixed compute-frontier curves using a steeper constrained-allocation exponent (`alpha≈3.45`).
- **Eigenquestion:** Is `scaling_var`/axis geometry a legitimate structural coordinate that explains Hestness/Henighan transfer, or is the offline pass a split-specific compression that collapses under live ZTARE pressure?
- **Discriminating test:** Re-run `gp154_scaling_law_normalized` under rubric `v3.1-axis-collapse-baseline`. The harness now reports the axis-exponent rival on holdout and farther-tail, so every candidate must be compared against `curve_axis_rev ** alpha_axis` rather than against the weaker screened-logit iter-2 champion.
- **Success criterion:** A K<=8 mechanistic candidate or K<=3 axis-collapse candidate matches or beats the axis-exponent baseline on both HOLDOUT and FARTHER_TAIL without `study`, `source_paper_table`, `curve_id`, hidden hardcoded literals, or invalid feature keys. A valid "success" must also state what physical/statistical role the axis exponent plays.
- **Kill condition:** Only provenance/modal lookup forms beat the baseline; the mutator cannot beat or justify the axis-exponent family; or alternate split/normalization checks show the exponent law is unstable.
- **Scope:** GP-154 neural scaling-law track, normalized substrate v3.1.
- **Status:** `registered / pending_live_rerun`
- **Opened:** 2026-05-01 01:33:00 EDT
- **Runnable packet:** `projects/gp154_scaling_law_normalized`, `rubrics/gp154_scaling_law_normalized.json`
- **Current offline anchor:** `projects/gp154_scaling_law_normalized/workspace/shape_collapse_diagnostic.json` reports the rival baseline as HOLDOUT `MAE=0.0781` and FARTHER_TAIL `MAE=0.0795`. This is a baseline, not a final claim.

---

## Scope Boundary: Discovery Programs vs. Demonstration Programs

**Pre-seal contracts, farther-tail holdouts, and asymptotic claim licenses are for scientific discovery programs only.** Demonstration and promotion programs operate under a different contract and must not be confused with the discovery mission.

The distinction is decisive:

- **Discovery programs** (GP-023, GP-028, ...) target questions where the operator does not know the answer at charter time. Farther-tail files, hidden holdouts, and sealed gate contracts exist precisely because the answer is not known in advance. The `asymptotic_claim: true` flag is meaningful only when the B-slice is genuinely unknown.

- **Demonstration programs** (central_station, eu_union, us_tariff_passthrough, glp1_adoption_economics, ...) target questions where the answer is knowable in principle from public evidence, and the purpose is to show ZTARE's recursive falsification capability on real-world analytical problems. These are intentionally *analysis-shaped*, not discovery-shaped. That is not a failure of ambition — it is a different function. Demonstration projects build the public record of what ZTARE does on tractable problems before the scientific discovery claims are warranted.

**Demonstration programs must not:**
- Use pre-seal vocabulary, farther-tail contracts, or `asymptotic_claim` flags
- Claim to "discover" answers the operator knew at charter time
- Be run as evidence for or against any row in the hypothesis ledger below

**Demonstration programs must:**
- Have a core question with a falsifiable answer checkable against public evidence
- Have kill criteria that would kill the thesis if the evidence goes the wrong way
- Produce a finding a non-specialist can read and evaluate

The hypothesis ledger below is for the discovery mission only. Demonstration project findings live in their own project charters and workspace summaries.

---

## Debate Log

## H-GP225-GNN-12.13 — Pre-GNN target-aware router must beat graph-only queue on repaired local obligations

- **Hypothesis:** The no-training pre-GNN repair harness is useful only if target-aware action routing over the same repaired-row pool beats graph/retrieval-only candidate ordering plus generic tactic actions under a fixed probe budget.
- **Eigenquestion:** Did the GP-225 detour produce a solver-useful instrument, or only a better-looking static queue?
- **Discriminating test:** Build a same-sample comparison over the repaired 8-row local-obligation benchmark using existing quarantined outputs: graph-only/static queue proxy, pre-GNN action router proxy, and graph+pre-GNN route selector. Compare `repair_bundle_success@7/10/25`, false non-gold accepted progress, and sort/type closure artifacts.
- **Success criterion:** Graph+pre-GNN beats graph-only by at least 2 rows at budget 10 with zero accepted non-gold progress and zero sort/type closure artifacts. A 10x claim is allowed only if the comparison shows order-of-magnitude operational savings or branch reduction, not merely a +1 row gain.
- **Kill condition:** Graph-only plus generic actions matches the route selector under budget 10/25, or the advantage depends on non-quarantined labels, sort closures, endpoint echoes, or NS-only rows.
- **Scope:** GP-225 GNN/pre-GNN theorem-workstation lane.
- **Status:** `closed / confirmed_useful_not_10x`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v13.3 aggregated the repaired-row evidence into the requested arms. Graph/retrieval queue plus generic actions reached `5/8` repair-bundle success at budget `10`; pre-GNN compressed proxies reached `7/8`; graph plus the pre-GNN route selector reached `8/8`, with `0` sort closures and no accepted non-gold progress. The result confirms advisory usefulness but rejects a 10x claim: the observed budget-10 uplift is `+3` rows, ratio `1.6x`, on an 8-row seed.

---

## H-GP225-GNN-13.4 — Probe-efficiency truth gate for pre-GNN 10x status

- **Hypothesis:** If GP-225 is on a plausible 10x path, the repaired 8-row seed should already show a material probe-efficiency collapse over graph/retrieval plus generic action probing, not only a higher success count.
- **Eigenquestion:** Does the route selector reduce failed candidate-action probes before accepted local repair enough to justify a 20-row 10x benchmark?
- **Discriminating test:** Recompute per-policy probe-efficiency metrics from the v12.12 temporal-quarantined Lean probes: success at budgets `3/5/7/10/25`, failed probes before first accepted repair, accepted repairs per probe, and branch-factor reduction versus `generic_fixed_hybrid`.
- **Success criterion:** For scale-up eligibility, the route selector must show at least `3x` mean failed-probe reduction versus generic at cap 25, while preserving `0` sort/type closures and no accepted non-gold progress. A 10x claim remains blocked unless the measured reduction is at least `10x`.
- **Kill condition:** If the route selector does not show at least `3x` probe-efficiency improvement on the seed, do not expand to 20 rows before fixing the controller.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / confirmed_scaleup_not_10x`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v13.4 found a real probe-efficiency signal but not a 10x signal. Under a 25-probe cap, graph/generic mean failed probes before accepted repair was `8.50`; route selector mean failed probes was `1.75`, a `4.86x` reduction. At budget `10`, accepted repairs per probe improved from `0.125` to `0.364`, a `2.91x` ratio. Sort closures remained `0`, and accepted non-gold progress remained `{}`. This clears the 20-row scale-up sanity gate and keeps 10x/GPU claims blocked.

---

## H-GP225-GNN-13.5 — Twenty-row repaired local-obligation benchmark feasibility

- **Hypothesis:** The GP-225 benchmark can expand from 8 repaired local obligations to 20 executable local obligations without reintroducing Sort/Type closure artifacts or nonlocal declaration targets.
- **Eigenquestion:** Is the 20-row scale-up mechanically ready for policy/probe-efficiency evaluation, or are we still blocked at target-unit construction?
- **Discriminating test:** Build a v13.5 Lean driver with 20 local obligation rows: the 8 repaired v12.6 rows plus 12 additional compile-checked rows drawn from existing AP/Bohr smoke-test fixtures. For each row, run the intended gold candidate/action and record before/after heads.
- **Success criterion:** All 20 intended candidate/action witnesses compile and either close the local proof goal or expose non-Sort side obligations; total Sort/Type closure count must be `0`.
- **Kill condition:** Any row only succeeds by Sort/Type closure, endpoint declaration construction, or a target that is not a local proof/side-obligation state.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / target_unit_scaleup_ready`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v13.5 built the 20-row target-unit packet and passed after repairing two instrument defects: extra fixture imports needed Lean namespace openings for `volume`/`𝓝`, and four rows were correctly reclassified as side-obligation exposures rather than closed proof-goal rows. Final run: `20/20` intended candidate/action witnesses accepted, `60` Lean probes, Lean returncode `0`, total Sort/Type closure count `0`, domains `5` NS/PDE, `13` harmonic-analysis, `1` measure-analysis, `1` filter-analysis. This only proves the 20-row benchmark is mechanically ready; it does not yet prove a 10x policy gap.

---

## H-GP225-GNN-13.6 — Twenty-row branch-factor policy gate

- **Hypothesis:** The target-aware pre-GNN route selector remains useful on the 20-row repaired local-obligation packet only if it reduces failed candidate-action probes before the first accepted gold repair versus generic fixed probing and cheap type-head/domain baselines.
- **Eigenquestion:** Does the v13.5 scale-up preserve a branch-factor advantage, or did the 8-row result depend on a small hand-shaped seed?
- **Discriminating test:** Run all `20` target rows against the shared `20`-candidate pool and `3` bounded actions (`apply_tac`, `exact_tac`, `convert_using1`). Compare policy orderings under budgets `3/5/7/10/25`: generic fixture order, target-head matching, domain+head ordering, action-affordance routing, and route selector. Count success only when the first accepted repair is the intended gold candidate/action; earlier non-gold accepted progress is a false-positive row, not a win.
- **Success criterion:** Scale-up support requires the route selector to beat generic fixed probing by at least `3x` on mean failed probes before first accepted gold repair, improve success at budget `10`, and keep total Sort/Type closure artifacts at `0`. A 10x claim remains blocked unless the measured reduction is at least `10x`.
- **Kill condition:** If a cheap head/domain/action baseline matches the route selector, or if non-gold accepted progress appears before gold on many rows, keep GP-225 as an advisory harness only and do not train.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / branch_factor_signal_survives_cheap_baseline_close`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v13.6 ran the full `20 x 20 x 3` candidate-action matrix (`1200` Lean probes) with Lean returncode `0` and total Sort/Type closure count `0`. The route selector beat generic fixed probing: success@10 `15/20` vs `3/20`, mean failed probes before gold `6.00` vs `29.50` (`4.92x`). This is a real branch-factor signal, still below 10x. The strongest cheap baseline remained close: domain+head ordering reached success@10 `14/20` and mean failed probes `7.00`, so the distinct route-selector/learned-lane claim is not yet proven. Training remains blocked; the next discriminator must beat cheap head/domain/action baselines or identify residual errors they cannot address.

---

## H-GP225-GNN-13.7 — Target-aware witness digest filter must remove false-before-gold rows

- **Hypothesis:** The v13.6 false-before-gold rows are mostly evaluator looseness, not unavoidable policy errors: a predeclared after-state digest filter plus broad-convert rejection should remove false accepted progress without reducing gold repair success.
- **Eigenquestion:** Can the repaired benchmark distinguish true local repair from weaker/broader Lean progress strongly enough for branch-factor metrics to be meaningful?
- **Discriminating test:** Re-evaluate the v13.6 probe matrix with a stricter witness filter. For closed proof goals, require zero after-goals. For side-obligation rows, require non-Sort after-heads matching the gold after-state head digest. Reject `convert_using1` witnesses that expose broad `Iff`/`Nat` conversion obligations rather than the target obstruction digest.
- **Success criterion:** False-before-gold rows under the route selector fall from `3` to `0` while preserving route-selector gold success@10 at least `15/20` and total Sort/Type closure count `0`.
- **Kill condition:** If strict witness filtering removes gold successes or leaves broad non-gold accepted progress, the benchmark still cannot support solver-like branch-factor claims.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / strict_witness_filter_passed`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v13.7 reused the v13.6 `1200`-probe matrix and applied a stricter after-state digest contract. Route-selector false-before-gold rows fell from `3` to `0` while preserving route success@10 `15/20`, mean failed probes `6.00`, and total Sort/Type closures `0`. The earlier false positives were evaluator looseness: broad `convert_using1` artifacts and weaker side-obligation exposures are now rejected unless they match the intended gold digest. The branch-factor signal remains `4.92x` versus generic fixed probing, still not 10x; cheap baseline closeness remains the blocker.

---

## H-GP225-GNN-13.8 — Cheap-baseline residual decomposition

- **Hypothesis:** The route selector's v13.7 edge over the best cheap baseline is too small to justify learning unless the residual rows expose a repeatable obstruction class that cheap domain/head/action ordering cannot capture.
- **Eigenquestion:** What exactly does the route selector know that the domain+head baseline does not?
- **Discriminating test:** Compare strict v13.7 row summaries for route selector, domain+head, head-match, and action-affordance policies. Classify rows where route improves, ties, or loses; identify budget-10 misses shared by all policies; and label whether improvements come from candidate ordering, action ordering, or target-kind witness filtering.
- **Success criterion:** A learned/probe-priority next step is justified only if route-only wins cluster around a nontrivial obstruction motif not expressible by cheap head/domain/action rules. If wins are one-probe action-order effects or Eq-candidate crowding, keep training blocked and target candidate-interface features first.
- **Kill condition:** If cheap baselines explain almost all route gains, do not train; improve deterministic interface ranking or public candidate-source integration instead.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / cheap_baseline_close_training_blocked`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v13.8 decomposed the strict v13.7 row summaries. The route selector beats domain+head on all rows, but mostly by a one-probe action-order advantage (`apply` before `exact`): improvement classes versus domain+head are `10` Eq-crowding/action-order, `9` side-obligation action-order, and `1` non-Eq structural edge. Only `1` row is route-only at budget 10 versus domain+head, while `5` shared budget-10 misses remain, all Eq-heavy harmonic rows. Verdict: useful branch-factor harness, but cheap baseline closeness blocks training; next work should target candidate-interface disambiguation for Eq-heavy rows and public candidate-source integration.

---

## H-GP225-GNN-14.0 — Interface scorer canary against lexical shortcut

- **Hypothesis:** v13.9's perfect 20-row result is useful only as pre-GNN routing if it is not merely recovering declaration identity from domain-specific constant names. A redacted/abstracted interface regime should retain some advantage, or at minimum expose exactly which signal is lexical.
- **Eigenquestion:** Is candidate-interface scoring learning proof-obligation shape, or just matching Bohr/AP/NS vocabulary in the current candidate pool?
- **Discriminating test:** Re-evaluate the v13.9 interface policy under token regimes: full namespace-leaf tokens, no-domain-stem tokens, and abstract operator/shape tokens. Keep the strict v13.7 witness filter and the same 20-row matrix.
- **Success criterion:** Promote v13.9 only as robust pre-GNN evidence if redacted regimes retain a material advantage over domain+head, or if the audit localizes remaining dependence to a bounded Eq-crowding shortcut that can be replaced by richer Expr-structure features.
- **Kill condition:** If all advantage disappears under simple domain-stem redaction, treat v13.9 as a useful lexical/static route heuristic only and do not use it for novelty or training claims.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / partial_redaction_survives_tie_audit_required`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v14.0 ran lexical canaries on v13.9. Full namespace-leaf interface scoring kept success@10 `20/20`, mean failed `1.05`. Removing domain stems still beat domain+head: success@10 `16/20`, mean failed `4.65` versus domain+head `14/20`, mean failed `7.00`. Abstract-shape scoring reported success@10 `20/20`, mean failed `0.15`, which is too strong and therefore requires inversion: it may be benefiting from stable tie order in very coarse token regimes. Verdict: interface signal survives partial redaction, but the next gate must be average-tie / permutation tie audit before any robust claim.

---

## H-GP225-GNN-14.1 — Interface scorer tie audit

- **Hypothesis:** The v14.0 interface scorer remains useful after correcting for optimistic tie order, but the abstract-shape regime's perfect result will collapse under average-tie scoring.
- **Eigenquestion:** How much of the interface-scorer gain is true ordering signal versus fixture-order tie luck?
- **Discriminating test:** For full-leaf, no-domain-stem, and abstract-shape regimes, compute candidate tie groups under `(same-domain, same-head, interface score)` and replace deterministic fixture-order candidate rank with average rank inside the tie group. Recompute expected gold probe index and success@10.
- **Success criterion:** A regime is robust only if average-tie success@10 remains above domain+head and mean failed probes remain materially lower. If only full-leaf survives, treat the scorer as useful but lexical. If no-domain-stem survives, keep it as a stronger pre-GNN shape signal.
- **Kill condition:** If all interface regimes collapse to domain+head or worse under average ties, do not promote interface scoring beyond a fixture-specific heuristic.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / stopgap_passed_exact_required`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v14.1 top-5 tie estimate suggested partial redaction survived average-tie scoring: full-leaf success@10 estimate `20/20`, no-domain-stem `17/20`, abstract-shape `20/20`. But the script only stored top-5 groups and was explicitly insufficient for promotion. It correctly triggered v14.2 exact all-candidate tie audit.

---

## H-GP225-GNN-14.2 — Exact all-candidate tie audit for interface scorer

- **Hypothesis:** The v14.1 top-5 tie audit underestimates tie risk; an exact all-candidate average-tie audit is required before the interface scorer can be treated as robust pre-GNN progress.
- **Eigenquestion:** Does full-leaf or domain-redacted interface scoring still beat domain+head when all equal-score candidate ties are averaged rather than resolved by fixture order?
- **Discriminating test:** Recompute full candidate scores for every row/candidate under full-leaf, no-domain-stem, and abstract-shape regimes. For each row, rank by `(domain match, head match, interface score)` and replace the gold candidate's deterministic rank with the average rank over its exact tie group. Convert candidate rank to expected probe index using the actual gold action position.
- **Success criterion:** Full-leaf and preferably no-domain-stem remain above domain+head success@10 under exact average-tie scoring. Abstract-shape may collapse; if it does, that confirms the v14.0 suspicion.
- **Kill condition:** If only fixture-order deterministic ranks beat domain+head, demote interface scoring to a non-robust heuristic and return to richer Lean Expr slot features.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / redacted_interface_not_robust_full_leaf_useful`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v14.2 exact all-candidate average-tie audit changed the interpretation. Full-leaf interface remains strong: success@10 `19/20`, mean failed `1.35` versus domain+head `14/20`, mean failed `7.00`. But no-domain-stem falls to success@10 `14/20`, matching domain+head, with mean failed `4.20`. Abstract-shape remains `20/20`, mean failed `0.15`, which likely means the 20-row fixture is structurally separable by coarse shape and must not be treated as generality. Verdict: full interface scoring is useful for CPU advisory routing; redacted interface robustness is not proven; GNN/training remains blocked.

---

## H-GP225-GNN-14.3 — Counterfactual interface challenge on current 20 rows

- **Hypothesis:** The current full-interface CPU router is only promotion-worthy if it ranks gold candidate-actions ahead of adversarial same-head/same-domain/interface-camouflage decoys, not merely ahead of generic irrelevant candidates.
- **Eigenquestion:** Does GP-225 route by typed local repair signal or by static lexical/interface cues that fail under counterfactual decoys?
- **Discriminating test:** Reuse the strict v13.7/v14.2 `20 x 20 x 3` probe matrix and construct per-row adversarial decoy families from the existing candidate pool: same-domain same-head decoys, highest full-interface nongold decoys, no-domain-stem tied/better decoys, abstract-shape tied/better decoys, wrong-action decoys, and strict-accepted nongold decoys. Compare domain+head, full-leaf interface, no-domain-stem, and abstract-shape policies by pairwise gold-over-decoy accuracy, repair_success@budget10, mean failed probes, and false-before-gold progress.
- **Success criterion:** Typed-router promotion requires full-interface pairwise gold-over-decoy accuracy at least `0.85`, false-before-gold `0`, success@10 above domain+head by at least `4` rows, and no catastrophic drop on no-domain-stem challenge rows.
- **Kill condition:** If gold-over-decoy accuracy is weak or the advantage lives only in full-leaf vocabulary while redacted/abstract regimes fail adversarial decoys, do not expand to 40 rows before adding proof-state slot-binding or richer Expr features.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / existing_pool_counterfactual_passed_wrapper_gap_remains`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v14.3 built adversarial decoy families from the existing `20`-candidate pool and scored pairwise gold-over-decoy accuracy over `517` pairs. Full-leaf interface reached pairwise accuracy `0.968`; no-domain-stem `0.908`; abstract-shape `0.992`; domain+head `0.891`. This supports the typed-router next step, but the artifact explicitly did not add new Lean wrapper/semantic-alias declarations or fresh wrong-carrier/wrong-incidence axioms. Therefore it is a pass for existing-pool decoys only, not a 40-row/training promotion.

---

## H-GP225-GNN-14.4 — Generated alias/wrong-Eq counterfactual challenge

- **Hypothesis:** If the v14.3 result is a real step toward typed routing, the full-interface router should preserve gold/alias equivalence and rank gold repairs ahead of newly generated wrong-Eq decoys that share vocabulary and shape but do not match the intended local after-state digest.
- **Eigenquestion:** Can GP-225 survive generated semantic aliases and wrong equality lemmas, or only decoys already present in the fixture pool?
- **Discriminating test:** Extend the v13.5 Lean driver with generated alias/wrapper candidates for gold repairs and wrong-Eq decoy axioms for the five hard harmonic Eq rows. Run bounded probes and strict witness filtering. Score alias stability and pairwise gold-over-generated-decoy accuracy under full-leaf, no-domain-stem, and abstract-shape interface policies.
- **Success criterion:** Alias candidates must be strict-accepted wherever their gold is accepted; full-leaf gold-over-wrong-decoy accuracy should be at least `0.85`, with false accepted wrong-decoy progress `0`. Redacted regimes are diagnostic, not promotion-critical.
- **Kill condition:** If generated wrong-Eq decoys are accepted as local repair or outrank gold broadly, the current interface router is a lexical/static helper only; do not expand before slot-binding/action-delta repair.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / failed_wrong_eq_unification_exposed_target_anchor_bug`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v14.4 generated explicit alias/wrapper axioms and wrong-Eq decoy axioms for the five hard harmonic Eq rows. Alias stability passed (`5/5`). The wrong-Eq challenge failed: `3` wrong-Eq actions were falsely accepted, and full/no-domain/abstract pairwise gold-over-wrong accuracy was only `0.5`. Inspection shows the current probe target instantiates target forall variables as metavariables; wrong-Eq decoys can close by reassigning those metavariables (e.g. swapping `x`/`τ`) rather than preserving local objects. This exposes a deeper target-state anchoring bug. Next gate must use anchored local fvars / proof-state slot binding before any benchmark expansion.

---

## H-GP225-GNN-14.5 — Anchored hard-Eq slot-binding probe

- **Hypothesis:** The v14.4 wrong-Eq false accepts are caused by target metavariable leakage, not by unavoidable equality ambiguity. Anchoring target forall variables as local fvars should reject wrong-Eq decoys while preserving gold and alias acceptance on the hard Eq rows.
- **Eigenquestion:** Does proof-state slot binding fix the generated wrong-Eq failure?
- **Discriminating test:** Implement an anchored probe variant for the five hard Eq rows using `forallTelescope` local fvars for target variables rather than `ztareInstantiateForallFresh` metavars. Probe gold, alias, and wrong-Eq candidates with the same actions and strict after-state digest.
- **Success criterion:** Gold and alias candidate-actions are accepted for all five hard Eq rows; wrong-Eq false accepted actions fall from `3` to `0`; Lean returncode is `0`.
- **Kill condition:** If wrong-Eq decoys still close anchored targets, the row definitions or decoys are not discriminating enough and the benchmark cannot support typed-router claims.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / anchored_slot_binding_passed`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v14.5 implemented an anchored probe for the five hard Eq rows using `forallTelescope` local fvars for target variables. Gold acceptance `5/5`, alias acceptance `5/5`, wrong-Eq false accepted actions `0`, Lean returncode `0`. This confirms the v14.4 false accepts were target-metavariable leakage, not unavoidable Eq ambiguity. It also validates proof-state slot binding as the next GP-225 router component.

---

## H-GP225-GNN-14.6 — Anchored full 20-row harness with generated wrong-Eq decoys

- **Hypothesis:** Anchored proof-state slot binding is not just a five-row patch; it should preserve the full 20-row strict router gains while rejecting generated wrong-Eq decoys inside the actual policy candidate pool.
- **Eigenquestion:** After target variables are anchored as local fvars for proof-goal rows, does GP-225 still look useful without accepting same-shape wrong equality repairs?
- **Discriminating test:** Build a v14.6 Lean driver over the 20-row v13.5 benchmark. Use anchored probing for `proof_goal` rows and the existing side-obligation probe for side-obligation rows. Add the v14.4 alias/wrapper and wrong-Eq generated declarations into the candidate pool for the five hard Eq rows. Evaluate generic/domain-head/full-interface policies under strict target-aware digests, with aliases counted as acceptable semantic equivalents and wrong-Eq candidates counted as false progress if accepted before the correct repair.
- **Success criterion:** Lean returncode `0`; full-interface anchored policy success@10 at least `19/20`; generated wrong-Eq false accepted actions `0`; wrong-Eq false-before-correct rows `0`; alias stability `5/5`; Sort/Type closure count `0`.
- **Kill condition:** If anchoring lowers full-interface success materially or generated wrong-Eq decoys are accepted in the full policy loop, do not expand to 40 rows or train; the current router remains a useful static/interface advisory tool only.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / anchored_full_harness_passed`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v14.6 integrated anchored proof-goal probing into the full 20-row harness and inserted generated alias/wrapper plus wrong-Eq decoys into the actual candidate pool for the five hard Eq rows. Lean returncode `0`; full-interface anchored policy success@10 `20/20`; clean success@10 `20/20`; alias acceptance `5/5`; wrong-Eq false accepted actions `0`; wrong-Eq false-before-correct rows `0`; Sort/Type closure count `0`; full-interface mean failed probes before correct repair `1.05` versus generic `29.5` and domain+head `7.0`. This reduces the overfit/leak concern exposed by v14.4, but it does not eliminate broader overfitting risk because the benchmark remains domain-skewed, gold-action monoculture remains `apply_tac`, and generated wrong-slot decoys currently cover only the five hard Eq rows.

---

## H-GP225-GNN-14.7 — Extended generated wrong-slot decoys

- **Hypothesis:** If v14.6 is not just a five-row hard-Eq fix, anchored target-aware routing should also reject generated wrong-slot candidates for additional proof-goal and side-obligation shapes while preserving the full-interface budget-10 success.
- **Eigenquestion:** Does GP-225 still avoid false progress when generated wrong candidates share head/domain/interface shape outside the original five hard Eq rows?
- **Discriminating test:** Extend v14.6 with generated wrong-slot declarations for additional rows: diagonal character RHS mismatch, sum-sub sign mismatch, forward-character bridge sign mismatch, volume exponent mismatch, and continuous-function wrong target. Keep the v14.6 aliases/wrong-Eq decoys. Run the anchored full 20-row policy loop and count wrong-slot false accepts, wrong-slot false-before-correct rows, success@10, and clean success@10.
- **Success criterion:** Lean returncode `0`; full-interface success@10 at least `19/20`; clean success@10 at least `19/20`; all generated wrong-slot false accepted actions `0`; all wrong-slot false-before-correct rows `0`; Sort/Type closure count `0`.
- **Kill condition:** Any accepted generated wrong-slot action means the harness still has a target/unit leak or overbroad acceptance predicate; do not expand to 40 rows or train before fixing it.
- **Scope:** GP-225 pre-GNN theorem-workstation lane.
- **Status:** `closed / extended_wrong_slot_decoys_passed`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v14.7 extended v14.6 from `5` generated wrong rows to `10`, adding wrong-slot candidates for diagonal character RHS, sum-sub sign, forward-character bridge sign, volume exponent, and continuous-function target. The corrected run produced `1245` candidate-action probes and `435` signatures. Lean returncode `0`; full-interface success@10 `20/20`; clean success@10 `20/20`; Sort/Type closure count `0`; generated wrong false accepted actions `0`; generated wrong false-before-correct rows `0`; aliases remained `5/5`. This further reduces overfit risk by showing anchored target-aware acceptance rejects more than the original hard-Eq decoys. Remaining risks: domain skew, all gold actions still `apply_tac`, abstract-shape still suspiciously strong, and NS wrong-carrier/wrong-incidence generated decoys are not yet covered.

---

## H-GP225-GNN-14.8 — NS generated wrong-carrier/incidence/fanout decoys

- **Hypothesis:** The anchored strict witness contract should reject NS wrong-carrier/wrong-incidence/fanout/budget decoys that share the target result head but expose the wrong side-obligation digest.
- **Eigenquestion:** Does GP-225 avoid false progress on NS side-obligation adapters, or has the benchmark only become robust on harmonic-analysis Eq rows?
- **Discriminating test:** Extend v14.7 with generated NS wrong candidates for the five NS rows: wrong fresh-packet side condition, wrong beta-payment side obligations, wrong pressure-lock receipt, and wrong Leray/heat carrier receipt. These candidates return the same target result head as the gold adapter but require incompatible side-obligation heads. Run the anchored full policy loop and count NS wrong false accepts and false-before-correct rows.
- **Success criterion:** Lean returncode `0`; full-interface success@10 at least `19/20`; clean success@10 at least `19/20`; generated NS wrong false accepted actions `0`; generated NS wrong false-before-correct rows `0`; Sort/Type closure count `0`.
- **Kill condition:** Any accepted NS wrong-carrier/incidence/fanout action means the side-obligation digest contract is too weak for NS use; do not use GP-225 as an NS repair adviser until the witness contract is fixed.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / NS advisory track.
- **Status:** `closed / ns_wrong_carrier_decoys_passed`
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11
- **Result:** v14.8 added generated NS wrong-carrier/incidence/fanout-style candidates for the five NS rows on top of v14.7's wrong-slot pool. The corrected run produced `1260` candidate-action probes and `440` signatures. Lean returncode `0`; full-interface success@10 `20/20`; clean success@10 `20/20`; Sort/Type closure count `0`; all generated wrong false accepted actions `0`; NS wrong false accepted actions `0`; NS wrong false-before-correct rows `0`; aliases remained `5/5`. This closes the GPT-5.5 counterfactual-candidate roadmap slice for the current 20-row packet. Remaining blockers before 40-row expansion: mixed-action rows, domain-balance/holdout design, and public-strength candidate-source baselines.

---

### Turn 1 — Claude (2026-04-13) — Experiment selection after sandbox_03 stopped: analytical move before experimental move

**Context.** Sandbox_03 (GP-023 Ontology Trap Planck generator) was stopped around iter 28+ of a planned 100-iter pre-registered run. Codex is writing the debrief in real time; no files yet. Sandbox_04 is pre-seal ready as a stronger-mutator verifier (claude-opus mutator, 20-iter cap, same hidden generator, no preservation lane). GP-047 preservation lane spec exists. GP-048 math AST analyzer spec exists but is not implemented. GP-035 FIT_DECLARATION drought fix is named as a blocking prerequisite for GP-047 but is not designed.

The question on the table: what is the next experiment?

**Candidates considered:**

**Candidate D — Run sandbox_04 as Codex built it. No GP-048, no preservation lane.** Pure mutator swap (claude-opus vs flash), same hidden generator, 20-iter cap. Cheapest to execute (pre-seal ready). Tests exactly one question: *is basin stickiness a model-vocabulary problem?* Info yield ≈1 bit. Confound: 20 iters is tight against a basin that only opened for flash at iter 13 — claude-opus may not reach stagnation pressure at all in 20 iters, and we would end with a "didn't see the effect in the time we gave it" result that is hard to interpret.

**Candidate A — Sandbox_04 + GP-048 diagnostics (Mode 1).** Adds primitive-set telemetry and tree-edit-distance reporting to sandbox_04. Risk low, info yield a bit higher. But GP-048 is unvalidated — we would be putting an unverified classifier onto a real run as its first exercise, which means if the primitive vocabulary has bugs we find out mid-run.

**Candidate B — Sandbox_04 + GP-048 Mode 2 (upgraded cold-residual).** Confounds mutator-swap with metric-upgrade. Strongly argue against — you would have no way to attribute any escape to the mutator vs the metric.

**Candidate C — Fix FIT_DECLARATION drought first, then re-run sandbox_03.** Worth considering but the drought is a red herring for the basin question: the three score-50 hits (iters 13, 20, 26) all happened when fits landed cleanly, so the basin-stickiness finding is not polluted by the drought. Drought fix is still needed, but not as the next experiment.

**Candidate E — Run GP-048 retrospectively against sandbox_03's closed workspace. No new run.** This is the move the debate should have led with.

**Why Candidate E is the right next step:**

1. **GP-048 needs validation, not deployment.** The GP-048 spec promised we would "validate primitive classification against ≥20 historical champion expressions from structural memory files before deployment." Sandbox_03's workspace has 28 iters of fit_result/structural_memory files — that is our validation corpus, handed to us. Running GP-048 against it is exactly the validation step the spec requires, and it costs nothing beyond implementation time.

2. **It quantitatively confirms (or denies) the basin-stickiness story.** Claude has been asserting that iters 13, 20, 26 are "the same basin" based on identical failing gates and intuition about their forms. GP-048 can actually measure this: compute `tree_edit_distance` between those three champions and `extract_primitives` on each. If they cluster tightly (distance < 5, same primitive set), the basin claim is quantitatively grounded. If they do not cluster, the framing was wrong and the next experiment needs to change.

3. **It strengthens the debrief Codex is writing in real time.** Codex's debrief is going to make claims about sandbox_03 — "stuck in one family," "three identical-gate ceiling hits," etc. Running GP-048 now means those claims ship with quantitative backing rather than qualitative hand-wave. This is decisive for the GP-046 empirical anchor writeup.

4. **Zero contamination risk.** The run is closed. The workspace is read-only. There is no apparatus to break.

5. **It changes what we do next.** If E shows tight clustering: sandbox_04 as a stronger-mutator verifier makes sense, because we have confirmed the basin is real and the question is whether claude-opus escapes it. If E shows the three champions were already structurally diverging and cold-residual was making progress that the summary missed: sandbox_04 is the wrong next experiment and we should be debugging the stagnation controller instead.

**The case against E:** it delays sandbox_04 by one implementation session. Codex is actively writing the debrief, and we could be producing more run data in that time. But we cannot know which run data to produce until E tells us whether sandbox_03's basin story is quantitatively real.

**Recommendation:**

1. Implement GP-048 (`extract_primitives` + `tree_edit_distance`) — one session, clean implementation per the spec.
2. Run it retrospectively against sandbox_03's workspace files. Compute the primitive set of each iter's champion and the pairwise tree-edit-distance matrix between iters 13, 20, 26.
3. Feed the results to Codex for the debrief. Now the empirical anchor has numbers, not just narrative.
4. *Then* decide sandbox_04's scope. If clustering is tight, run D (Codex's unmodified mutator swap) and get a clean result. If clustering is loose, revisit the framing.
5. FIT_DECLARATION drought fix and GP-047 reframe stay in the queue but are not blocking.

**The core point:** we have a pile of data we have not analyzed yet. Running another experiment before analyzing it is a common failure mode — you generate more data to answer questions the existing data already answers. Candidate E is the analytical move before the experimental move.

**How this connects to the mission framing.** The reason Candidate E outranks D, A, B, and C is not that it is cheaper or safer. It is that it produces a *finding about sandbox_03* — a first-person epistemic claim grounded in measurement — rather than a *score about claude-opus*. The other candidates are benchmark-shaped: they ask "how does the apparatus perform under condition X." Candidate E is discovery-shaped: it asks "what do we now know about the basin we already observed." A discovery engine always runs E before D when E is available and unused.

**Decision status.** Pending operator decision. If the operator says "go," default action is Candidate E followed by Candidate D. If the operator disagrees with the analytical-before-experimental framing, the disagreement should be recorded as Turn 2 of this seam so the reasoning is preserved for future experiment-selection debates.

### Turn 2 — Codex (2026-04-13 09:22:36 EDT) — Sync the mission seam to the live `sandbox_04` packet and pre-register successor programs before result bias can creep in

**Context.** The live `sandbox_04` packet is no longer the earlier stronger-mutator / three-arm object described in Turn 1. It has been re-scoped in the GP-023 seam and packet docs as a **single-arm apparatus-feedback verifier**: same flash mutator family, GP-048 primitive-cone stagnation injection on, sanitized farther-tail veto on, no preservation lane, no mutator swap. So this seam needs two repairs:

1. stop pointing live `sandbox_04` rows at an experiment it is no longer running
2. freeze the next mission-level successor candidates *before* `sandbox_04` closes, so the result cannot retroactively make one of them look more attractive

**What pre-registration means in this seam.** It does **not** mean sealing a runnable packet today. It means freezing the decisive shape of the successor idea now:

- stable hypothesis ID in the ledger
- eigenquestion the successor is supposed to answer
- minimum discriminating test
- success criterion
- blocking/staging logic

What remains open until later packet work:

- exact project slug
- exact rubric filename
- exact model family or toolchain pin
- implementation details inside `src/`

That split matters. The anti-bias object is the **question and test shape**, not the future filename.

**Consequences for the ledger.**

- `H-GP023-02` and `H-GP023-03` are the rows the live `sandbox_04` packet can bear on, because it bundles sanitized farther-tail veto plus primitive-cone stagnation injection.
- `H-GP023-01` is **not** the live `sandbox_04` packet anymore; it is deferred to a later stronger-mutator successor.
- `H-GP023-05` is **not** the live `sandbox_04` packet anymore; it is deferred to a later preservation-lane successor.
- `SP-1`, `SP-2`, and `SP-3` are pre-registered now by adding stable hypothesis rows below and tying each candidate card to one of those rows.

**Decision status.** Locked. The successor queue is now pre-registered before `sandbox_04` reports. Later packet design may refine implementation, but it must cite these rows and explain any drift before seal.

## Hypothesis Ledger

**Purpose.** This ledger exists so the mission's "analytical before experimental" discipline has teeth. Every hypothesis debated in this seam (or in program-specific seams it references) gets a row. Every experiment run gets tied to the hypothesis it tests. Every result updates the row. The ledger is the fixed point that prevents a run from being relabeled after-the-fact to match whatever it happened to find.

**Format.** One row per hypothesis. Fields:

- **ID** — stable identifier (`H-<program>-<nn>`). Never reused, never deleted. Falsified hypotheses stay in the table with status `falsified`.
- **Hypothesis** — one-sentence claim about mechanism or cause. Written as a falsifiable statement, not a question.
- **Scope** — which program(s) or seam(s) the hypothesis lives under.
- **Status** — one of: `open` (no run bears on it), `testing` (a run is in flight that could falsify or confirm), `confirmed` (a run produced evidence consistent with it; not the same as "proven"), `falsified` (a run produced evidence incompatible with it), `withdrawn` (retracted without a run, with a recorded reason), `partially_confirmed` (mixed evidence, needs a refinement).
- **Discriminating test** — the specific experimental or analytical move that could change the status. Stated before the test is run.
- **Run(s)** — project/sandbox names whose results bear on this row. Updated as runs close.
- **Result** — short sentence when the run closes. Links to artifact if any.
- **Opened** — date the hypothesis entered the ledger.
- **Closed** — date the hypothesis transitioned to `confirmed`/`falsified`/`withdrawn`. Empty while `open`/`testing`/`partially_confirmed`.

**Discipline.** A row must be added to the ledger BEFORE the discriminating test runs. Adding rows after a run to explain what it found is the failure mode the ledger exists to prevent. When a debate in this seam proposes a new experiment, the Turn that proposes it must cite the row(s) it tests.

**Mirror.** The concise cross-program mirror of this discovery ledger now lives at `research_areas/private/EXPERIMENT_TRACK_RECORD.md`, with a sanitized public subset at `research_areas/EXPERIMENT_TRACK_RECORD.md`. This seam remains the debate-level source for discovery-mission rows; the track-record files are the compressed reporting surface.

---

### Active rows

#### H-NS-5CG-PROOFSEARCH-01 — Broad proof-search packet can advance the pressure-`l=2` branch beyond local transport cages

- **Hypothesis:** A broad proof-search packet centered on the pressure-`l=2` branch can materially advance the current NS route by finding a genuine coercive bridge among the live obligations — iterated commutator tower, global pressure-tail bootstrap, continuation handoff, or small/large regime split — without requiring new GPU evidence. The iterated commutator tower is the leading candidate, but the packet must remain open to better closure routes.
- **Eigenquestion:** Which of the current unpaid proof-facing obligations is actually the cheapest decisive promotion from local transport defect to a coercive proof chain, and can ZTARE derive a theorem-shaped route or an impossibility witness from existing artifacts and lemmas alone?
- **Discriminating test:** Build a proof-search packet that presents the whole ranked frontier rather than one lemma. The packet must force explicit handling of singular-integral structure, forbid generic Sobolev-only evasions, and require one of two outputs: (a) a theorem-shaped bridge that advances at least one live obligation using repo-native objects, or (b) a clean obstruction that rules out the attempted route. Success = a non-circular bridge or a clean impossibility diagnosis on one ranked obligation. Failure = prose-only restatement, hidden insertion of decay exponents, or ungrounded narrowing to a single route without comparative justification.
- **Run(s):** pending proof-search packet based on `phase5cg_proofsearch_packet.md`
- **Result:** Pending.
- **Opened:** 2026-05-02 20:58:00 EDT
- **Closed:** 

#### H-GP225-GNN-12.3 — Full proof-state snapshots can separate local repair progress from broad convert noise

- **Hypothesis:** For the GP-225 Lean repair router, before/after goal snapshots and role-compatible side-goal heads can filter v11.9/v12.1 action bundles strongly enough to keep bundle success at or above `0.50` while raising witness precision to at least `0.65` on the frozen endpoint-occluded seed, without using bootstrap role labels, local helper names, or evaluator-only labels as scoring features.
- **Eigenquestion:** Is the action-delta controller observing a reusable repair motif, or is it mostly broad `convert_using1` success that looks like progress only because candidate names and endpoint-adjacent structures are nearby?
- **Discriminating test:** Run local no-spend `v123_full_goal_snapshot_witness_probe.py` over the v11.9/v115 budget-7 emitted bundles. The probe must execute Lean actions, capture sanitized target/candidate type heads and before/after goal snapshots, classify remaining side-goal heads into generic obstruction roles, and evaluate strict witness filters using only non-label proof-state evidence.
- **Success criterion:** A strict full-snapshot witness filter reaches precision `>=0.65` while preserving bundle@7 `>=0.50` on the frozen 8-row seed. This permits the next step: external public candidate-source integration as a baseline stressor.
- **Kill condition:** If strict full-snapshot filters cannot beat v12.1's `0.50` precision without dropping below bundle@7 `0.50`, the novelty claim remains paused; continue with cheap hybrid retrieval plus diagnostic action probes and do not train or integrate public candidate sources yet.
- **Scope:** GP-225 GNN / Lean proof-workstation witness-quality track.
- **Status:** `closed / falsified_for_current_target_unit`
- **Run(s):** `scripts/public/models/gnn_lemma_relevance/v123_full_goal_snapshot_witness_probe.py`
- **Result:** The strict full-snapshot filter failed the pre-registered gate: precision `0.478` at bundle@7 `0.50`. Adding a sort-closure guard exposed the sharper issue: precision rose to `1.0`, but bundle@7 dropped to `0.375`, because many earlier "closed" successes were Type-level structure-declaration closures rather than local proof-repair witnesses. Public candidate integration and GPU remain blocked.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11

#### H-GP225-GNN-12.4 — The frozen seed's false action progress is concentrated in structure/type target rows

- **Hypothesis:** The v12.3 witness failure is largely explained by the target-unit contract: several frozen seed rows use newly added structure/type declarations as the target, so Lean action probes can "solve" a universe/type goal without representing a local repair obligation.
- **Eigenquestion:** Is GP-225 currently bottlenecked on action routing, or on the benchmark's choice of target unit?
- **Discriminating test:** Run local no-spend `v124_target_unit_audit.py` over the frozen repair seed. For every evaluator-added target declaration, inspect the Lean conclusion head/type, classify it as proof-like versus sort/type-like, and report row-level concentration of sort-like targets.
- **Success criterion:** If sort/type-like targets dominate the rows where v12.3 produced false closed witnesses, the next build target becomes a seed rewrite around executable local obligations, structure fields, constructor/refine states, or patch-level tactic states.
- **Kill condition:** If false witness rows are not concentrated in sort/type-like targets, continue improving action-delta filters rather than rebuilding the target unit.
- **Scope:** GP-225 GNN / Lean proof-workstation benchmark contract.
- **Status:** `closed / mixed_confirmed`
- **Run(s):** `scripts/public/models/gnn_lemma_relevance/v124_target_unit_audit.py`
- **Result:** Mixed confirmation. The seed is not uniformly sort/type-targeted: `25` targets split into `10` sort-like, `8` object-like, and `7` proof-like targets. But both v12.3 strict false-positive rows (`v63_gnn_graph_combo_patch_attribution`, `v91_ns_leray_heat_tent_geometry_patch_attribution`) have sort-like targets, so the false closed-witness mechanism is concentrated exactly where suspected. The next step is to rebuild those rows as local executable obligations rather than declaration-type goals.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11

#### H-GP225-GNN-12.5 — Repaired local-obligation targets remove Sort/Type closure artifacts

- **Hypothesis:** Replacing the v12.3/v12.4 false-positive declaration-type targets with executable local adapter-application obligations will remove Sort/Type closure artifacts while preserving a useful action-controller signal.
- **Eigenquestion:** After the poisoned target unit is repaired, does the action controller still produce target-aware Lean progress, or did the apparent signal depend on declaration-type closures?
- **Discriminating test:** Run local no-spend `v125_target_unit_repair_packet.py`. The packet must build executable Lean target constants for the false-positive rows (`v63`, `v91`), run candidate/action probes against old and repaired targets, reject Sort/Type closures, and report whether the intended adapter action exposes the correct local side obligation.
- **Success criterion:** For both repaired false-positive rows, the intended adapter candidate/action succeeds on the repaired target, produces no Sort/Type closure, and exposes a side-goal head matching the intended lower obligation (`FreshComparablePacketSideConditionAudit` for v63, `LerayHeatFreshFrequencyEventTentGeometry` for v91). This permits a full v12.5 benchmark rewrite over all 8 rows.
- **Kill condition:** If repaired targets still close by Sort/Type artifacts, fail to expose the intended lower obligation, or require endpoint declarations, the action-controller lane remains diagnostic only and the benchmark rewrite should not proceed.
- **Scope:** GP-225 GNN / Lean proof-workstation target-unit repair.
- **Status:** `closed / confirmed_for_false_positive_rows`
- **Run(s):** `scripts/public/models/gnn_lemma_relevance/v125_target_unit_repair_packet.py`
- **Result:** Confirmed on the two v12.3/v12.4 false-positive rows. After replacing declaration-type targets with local adapter-application obligations, `apply` exposed the intended lower side obligation in both cases: `FreshComparablePacketSideConditionAudit` for v63 and `LerayHeatFreshFrequencyEventTentGeometry` for v91. Sort/Type closure count was `0`; old structure-type decoys no longer succeeded. This permits a full 8-row target-unit rewrite, but still does not permit GPU or public candidate-source integration.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11

#### H-GP225-GNN-12.6 — All seed rows can be rewritten as executable local repair obligations

- **Hypothesis:** The current 8-row GP-225 repair seed can be rebuilt as executable local proof obligations, each with a gold candidate/action witness, without relying on declaration-type or Sort/Type closure artifacts.
- **Eigenquestion:** Is the v12.x benchmark target-unit repair local to two poisoned rows, or can the whole seed be converted into the tactic-state unit required for a solver-like action-router test?
- **Discriminating test:** Run local no-spend `v126_full_target_unit_rewrite_packet.py`. The packet must build one Lean local-obligation target per seed row, probe the row's intended candidate/action, record after-goal heads, and count Sort/Type closure artifacts.
- **Success criterion:** All 8 seed rows have a compiling gold candidate/action witness. NS adapter rows must expose the expected lower side-obligation head; proof-like non-NS rows must close the intended proof goal. Total Sort/Type closure count must be `0`.
- **Kill condition:** If one or more rows cannot be expressed as local obligations, if intended witnesses only succeed by Sort/Type closure, or if non-NS proof-like rows require endpoint/declaration-type targets, the benchmark is not ready for v12.7 policy evaluation or expansion to 20 rows.
- **Scope:** GP-225 GNN / Lean proof-workstation target-unit benchmark repair.
- **Status:** `closed / confirmed`
- **Run(s):** `scripts/public/models/gnn_lemma_relevance/v126_full_target_unit_rewrite_packet.py`
- **Result:** Confirmed. All 8 seed rows now have executable local-obligation targets with compiling gold candidate/action witnesses. NS adapter rows expose the expected lower side-obligation heads, non-NS proof-like rows close proof goals, and total Sort/Type closure count is `0`. This clears the benchmark target-unit repair step and shifts the next gate to v12.7 target-aware policy evaluation against cheap retrieval/generic action-order baselines under probe budgets.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11

#### H-GP225-GNN-12.7 — Target-aware action policy beats generic probing on repaired local obligations

- **Hypothesis:** On the repaired v12.6 local-obligation seed, a target-aware action policy will find gold repair witnesses under a fixed probe budget more efficiently than generic fixed action order over the same candidate queues.
- **Eigenquestion:** Once the benchmark unit is corrected, does action routing add measurable value, or was the useful signal only gold-witness feasibility?
- **Discriminating test:** Run local no-spend `v127_target_aware_policy_eval.py`. The script must use the repaired v12.6 targets, build candidate queues from existing repair-pool machinery, run Lean probes for candidate/action attempts, and compare generic fixed action order against target-aware affordance policies under budgets `7`, `10`, and `25`.
- **Success criterion:** Target-aware routing must beat generic fixed action order by at least `2/8` rows at budget `10`, reach at least `6/8` gold repair-bundle success by budget `25`, and produce no Sort/Type closure artifacts.
- **Kill condition:** If generic fixed action order matches the target-aware policy under budget `10`/`25`, if success depends on non-gold false positives, or if repaired rows reintroduce Sort/Type closures, the action-controller lane remains diagnostic and should not expand to 20 rows.
- **Scope:** GP-225 GNN / Lean proof-workstation target-aware policy value.
- **Status:** `closed / failed_strict_gate_partial_positive`
- **Run(s):** `scripts/public/models/gnn_lemma_relevance/v127_target_aware_policy_eval.py`
- **Result:** Failed the pre-registered gate, with a partial positive. Target-aware policies improved over generic fixed action order but not by enough at budget `10`: best target-aware budget-10 success was `6/8` versus generic `5/8`, below the required +2-row margin. At budget `25`, target-aware-v115 reached `8/8` while generic reached `6/8`. Sort/Type closures were `0`, and accepted non-gold progress count was `0`, so the repaired target acceptance predicates are clean. The next move is an oracle/error decomposition to separate candidate-order misses from action-order misses.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11

#### H-GP225-GNN-12.8 — v12.7 miss is mainly candidate ordering, not target acceptance

- **Hypothesis:** The remaining v12.7 budget-10 miss is dominated by candidate ordering/route selection rather than target acceptance or Lean action semantics.
- **Eigenquestion:** Should the next GP-225 increment improve candidate queues, action affordances, or acceptance predicates?
- **Discriminating test:** Run local no-spend `v128_policy_gap_decomposition.py` over v12.7 outputs. Decompose each row by policy into first gold candidate rank, first accepted gold probe, budget threshold, and whether success differences are attributable to action-order savings on the same candidate queue or different candidate queues.
- **Success criterion:** The decomposition identifies a dominant bottleneck class with enough specificity to choose one next engineering target without expanding the benchmark: candidate-route repair, action-affordance repair, or acceptance repair.
- **Kill condition:** If the decomposition is ambiguous, or if failures are driven by target-acceptance instability or non-gold accepted progress, the v12.7 result is not actionable and the next step should be manual row redesign rather than router work.
- **Scope:** GP-225 GNN / Lean proof-workstation policy gap decomposition.
- **Status:** `closed / actionable`
- **Run(s):** `scripts/public/models/gnn_lemma_relevance/v128_policy_gap_decomposition.py`
- **Result:** Actionable. v12.7 failures are not target-acceptance artifacts: Sort/Type closures were `0` and accepted non-gold progress was `{}`. Five rows were already solved by generic fixed action order at budget `10`; the remaining three split into two action-order bottleneck rows (`v65` late, `v86` budget-saving) and one candidate-queue row (`v87`, solved only by v115 queue). The next target is action-affordance repair first, with a small candidate-queue fix for the v87 non-NS row.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11

#### H-GP225-GNN-12.9 — Compressed adapter affordance plus union queue clears the repaired-seed policy gate

- **Hypothesis:** Compressing adapter-side action affordance to `apply_tac` first, and adding a hybrid+v115 candidate-union queue, will clear the repaired 8-row policy gate without weakening target acceptance.
- **Eigenquestion:** Can the v12.8 diagnosis be converted into a real policy improvement, or was it only post-hoc row explanation?
- **Discriminating test:** Run local no-spend `v129_compressed_affordance_policy_eval.py` on the same v12.6 repaired targets. Compare `generic_fixed_hybrid`, compressed-hybrid, compressed-v115, and compressed-union policies under budgets `7/10/25`.
- **Success criterion:** A compressed target-aware policy beats generic fixed action order by at least `2/8` rows at budget `10`, reaches at least `6/8` gold repair-bundle success by budget `25`, and produces zero Sort/Type closures and zero accepted non-gold progress.
- **Kill condition:** If the improvement is only from non-gold accepted progress, if Sort/Type closures reappear, or if compressed policies still fail to beat generic by the pre-registered margin, the v12.8 repair thesis fails and benchmark expansion remains blocked.
- **Scope:** GP-225 GNN / Lean proof-workstation action-affordance policy repair.
- **Status:** `closed / confirmed`
- **Run(s):** `scripts/public/models/gnn_lemma_relevance/v129_compressed_affordance_policy_eval.py`
- **Result:** Confirmed on the repaired 8-row seed. `compressed_v115` reached `8/8` success at budgets `7`, `10`, and `25`, while generic fixed hybrid reached `5/8` at budget `10` and `6/8` at budget `25`. Sort/Type closures were `0` and accepted non-gold progress was `{}`. This validates the v12.8 diagnosis locally and permits a next no-GPU robustness step; it still does not permit GPU, public candidate integration, or solver/novelty claims.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11

#### H-GP225-GNN-12.10 — v12.9 winning queue is not label-leakage clean

- **Hypothesis:** The v12.9 compressed-affordance policy win is clean at the Lean target-acceptance layer but not yet clean at the candidate-queue/source layer, because older v84/v115/v82 machinery may access evaluator-only labels or post-patch declarations.
- **Eigenquestion:** Is the v12.9 policy win evidence of a deployable router, or only evidence that the repaired target evaluator can measure a potentially contaminated candidate queue?
- **Discriminating test:** Run local no-spend `v130_label_leakage_static_audit.py`. The audit must scan the v82/v84/v115/v127/v129 source chain for evaluator-only label access, gold pool construction, candidate-influence scoring, and current-file/post-patch declaration extraction.
- **Success criterion:** If no prohibited accesses are found in the v129-winning queue path, v12.9 can proceed to alias/name robustness stress. If prohibited accesses are found, v12.9 remains an action-affordance/target-acceptance result only, and the next step must be a label-blind queue rebuild.
- **Kill condition:** Any scoring/candidate-generation path used by the winning v12.9 policy reads `labels_visible_to_evaluator_only`, `added_declarations`, `candidate_influence`, or gold line distance before final metric computation.
- **Scope:** GP-225 GNN / Lean proof-workstation leakage audit.
- **Status:** `closed / partially_falsified_temporal_risk_confirmed`
- **Run(s):** `scripts/public/models/gnn_lemma_relevance/v130_label_leakage_static_audit.py`
- **Result:** The label-leakage part was not confirmed after separating pre-metric scoring from final metric use: pre-metric prohibited hit count was `0`. However, the audit found `6` current-file declaration-extraction paths, so v12.9 remains temporally retrospective/post-patch-context dependent. The next robustness step is a pre-patch or scrubbed candidate-pool reconstruction, not GPU or benchmark expansion.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11

#### H-GP225-GNN-12.11 — Compressed policy survives same-file temporal quarantine

- **Hypothesis:** The v12.9 compressed-affordance win will survive a same-file temporal quarantine that removes other seed-row repair declarations from the candidate pool while retaining the current row's proposed repair declarations.
- **Eigenquestion:** Is the v12.9 gain mainly action-affordance policy, or does it depend on later same-file patch families leaking into the current row's queue?
- **Discriminating test:** Run local no-spend `v131_temporal_quarantine_policy_eval.py`. The script must rebuild candidate queues from current declarations with same-file other-row added declarations removed, avoid v84/v115 saved queue artifacts, and rerun generic fixed versus compressed target-aware policies on the repaired v12.6 targets.
- **Success criterion:** A compressed quarantined policy beats generic fixed action order by at least `2/8` rows at budget `10`, reaches at least `6/8` success by budget `25`, and produces zero Sort/Type closures and zero accepted non-gold progress.
- **Kill condition:** If the compressed policy collapses under quarantine, or if improvement depends on non-gold accepted progress, v12.9 remains a retrospective queue result and benchmark expansion remains blocked.
- **Scope:** GP-225 GNN / Lean proof-workstation temporal quarantine.
- **Status:** `closed / confirmed`
- **Run(s):** `scripts/public/models/gnn_lemma_relevance/v131_temporal_quarantine_policy_eval.py`
- **Result:** Confirmed under same-file temporal quarantine. `compressed_quarantined_v115` reached `7/8` at budget `10` and `8/8` at budget `25`, while generic fixed hybrid reached `5/8` and `6/8`. Sort/Type closures were `0`, accepted non-gold progress was `{}`, and the quarantine removed `8-15` same-file other-row repair declarations from each NS row's pool. The remaining budget-10 misses indicate route-selection: hybrid/union solve v65 by budget `10`, while v115 solves v87 by budget `7`.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11

#### H-GP225-GNN-12.12 — Domain-route selector clears quarantined repaired-seed gate

- **Hypothesis:** A simple route selector over the quarantined compressed policies will clear the repaired-seed gate: use compressed-hybrid for NS rows and compressed-v115 for non-NS rows.
- **Eigenquestion:** Can the v12.11 route-selection diagnosis become a policy improvement without adding new labels, weakening acceptance, or reintroducing temporal leakage?
- **Discriminating test:** Run local no-spend `v132_quarantined_route_selector_eval.py` on the v12.11 quarantined candidate pools and v12.6 repaired targets. Compare `generic_fixed_hybrid`, `compressed_quarantined_hybrid`, `compressed_quarantined_v115`, and `route_selector_ns_hybrid_nonns_v115` under budgets `7/10/25`.
- **Success criterion:** The route selector must reach `8/8` success at budget `10`, beat generic fixed hybrid by at least `2/8` rows at budget `10`, and produce zero Sort/Type closures and zero accepted non-gold progress.
- **Kill condition:** If the route selector fails to beat the best single route, or if the win depends on false accepted progress, do not use it for NS advisory routing or benchmark expansion.
- **Scope:** GP-225 GNN / Lean proof-workstation quarantined route selection.
- **Status:** `closed / confirmed`
- **Run(s):** `scripts/public/models/gnn_lemma_relevance/v132_quarantined_route_selector_eval.py`
- **Result:** Confirmed under temporal quarantine. The route selector (`navier_stokes → compressed_hybrid`, non-NS → compressed_v115) reached `8/8` at budget `10` and `8/8` at budget `25`, versus generic fixed hybrid `5/8` and `6/8`. Sort/Type closures were `0` and accepted non-gold progress was `{}`. This permits use as an advisory routing instrument for local Lean work, while GPU/training and novelty claims remain blocked pending larger robustness benchmarks.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-11

#### H-NEURAL-HUNT-01 — OLMo trajectory shape survives endpoint-withheld gauge audit

- **Hypothesis:** The Paper 7 neural object is a transferable OLMo trajectory-shape signal, not only an artifact of normalizing each curve by its own future minimum and amplitude.
- **Eigenquestion:** Does a trajectory template learned from other OLMo2 runs still predict a held-out run's future raw loss when the held-out run's future endpoint is withheld?
- **Discriminating test:** Run the out-of-loop prefix-endpoint audit under `projects/neural_hunt/workspace/` using closed OLMo2 7B/13B telemetry from GP154. For each held-out run and prefix fraction, compare a leave-one-run-out trajectory template against last-prefix and prefix-linear raw-loss baselines on the held-out tail. Record full-endpoint normalized performance only as a diagnostic, not as success evidence.
- **Success criterion:** The template beats both naive prefix-only baselines on a majority of held-out run/prefix cells, with no use of the held-out run's future minimum or amplitude in the prediction path. If it only wins under full-endpoint normalization, the Paper 7 claim remains descriptive and must not be promoted as a predictive law.
- **Kill condition:** Prefix-only reconstruction loses to naive baselines on most cells, or the script needs future target endpoints, run identity, or post-hoc gauge choices to win.
- **Scope:** Paper 7 neural substrate reopening; `projects/gp154_phase_flow_law`; out-of-loop `projects/neural_hunt`.
- **Status:** `closed / falsified_for_prefix_minmax_endpoint_proxy`
- **Run(s):** `projects/neural_hunt/workspace/run_prefix_endpoint_null_audit.py`
- **Result:** The full-endpoint normalized template is tight (`mean z-tail MAE=0.0413`), but the endpoint-withheld raw-loss reconstruction using the prefix min/max gauge loses to both prefix-only baselines in `0/8` cells (`template raw MAE=0.567`, last-prefix `0.287`, prefix-linear `0.962`). This kills the strong predictive read for the prefix-minmax gauge while preserving the descriptive-collapse read.
- **Opened:** 2026-05-08 00:00:00 EDT
- **Closed:** 2026-05-08 00:00:00 EDT

#### H-NEURAL-HUNT-02 — Prefix-fitted affine gauge can make OLMo trajectory shape predictive without future endpoints

- **Hypothesis:** The missing object in H-NEURAL-HUNT-01 is not the shape template but the endpoint gauge estimator: a leave-one-run-out shape template can predict held-out future raw loss if its affine gauge is fitted only on the held-out prefix.
- **Eigenquestion:** Does estimating the loss floor/amplitude by prefix-only affine alignment to an externally learned shape template recover predictive content without using the held-out future endpoint?
- **Discriminating test:** Run `projects/neural_hunt/workspace/run_prefix_affine_shape_audit.py` on the same closed OLMo2 7B/13B telemetry. For each held-out run and prefix fraction, build the trajectory template from other runs only, fit `loss = floor + amp * z_template(progress)` on the held-out prefix only, and score the held-out tail against last-prefix, prefix-linear, and prefix-affine-clock baselines.
- **Success criterion:** The prefix-affine template beats all prefix-only baselines on a majority of cells, and the learned amplitude/floor remains finite with no use of target run identity, future target endpoints, or post-hoc curve-specific constants.
- **Kill condition:** Prefix-affine template loses to the naive baselines on most cells, or only wins with negative/unstable gauges that imply the fitted coordinate is not physically interpretable.
- **Scope:** Paper 7 neural substrate reopening; `projects/gp154_phase_flow_law`; out-of-loop `projects/neural_hunt`.
- **Status:** `closed / falsified_for_prefix_affine_template`
- **Run(s):** `projects/neural_hunt/workspace/run_prefix_affine_shape_audit.py`
- **Result:** Prefix-affine alignment improves the endpoint-withheld template only slightly and passes `1/8` cells. Mean raw MAE remains worse than last-prefix (`0.528` vs `0.287`). This kills the simple "external shape template plus prefix affine gauge" repair.
- **Opened:** 2026-05-08 00:00:00 EDT
- **Closed:** 2026-05-08 00:00:00 EDT

#### H-NEURAL-HUNT-03 — Prefix slope identifies the OLMo trajectory gauge

- **Hypothesis:** The held-out trajectory gauge is identifiable from the local prefix slope against an externally learned shape template, so a slope-anchored template can predict future raw loss without future endpoints.
- **Eigenquestion:** Does matching the external template derivative to the held-out prefix derivative recover future raw-loss prediction better than last-prefix and linear baselines?
- **Discriminating test:** Run `projects/neural_hunt/workspace/run_prefix_slope_anchored_shape_audit.py` on the closed OLMo2 7B/13B corpus. For each held-out run and prefix fraction, learn the shape template from other runs, estimate its amplitude by matching local prefix slope, anchor at the prefix boundary, and score the held-out tail against last-prefix, full-prefix-linear, and local-slope-linear baselines.
- **Success criterion:** The slope-anchored shape beats all prefix-only baselines on a majority of cells with finite, same-sign derivative/amplitude behavior.
- **Kill condition:** The slope-anchored shape loses to naive baselines on most cells or only wins through unstable derivative division.
- **Scope:** Paper 7 neural substrate reopening; out-of-loop `projects/neural_hunt`.
- **Status:** `closed / partial_positive_fragile`
- **Run(s):** `projects/neural_hunt/workspace/run_prefix_slope_anchored_shape_audit.py`; cross-check `projects/neural_hunt/workspace/run_prefix_coordinate_candidate_audit.py`
- **Result:** The progress-fraction slope-anchored template passes the narrow mid/late-prefix test (`6/8` cells, mean raw MAE `0.111` vs last-prefix `0.287`, local-linear `0.292`). A stricter count-prefix candidate panel over early windows does not promote (`5/15`, mean best-template MAE `0.483` vs best prefix-only baseline `0.112`). The object is therefore not a universal endpoint-free law; it is a fragile but real-looking boundary-condition coordinate worth testing on more raw runs.
- **Opened:** 2026-05-08 00:00:00 EDT
- **Closed:** 2026-05-08 00:00:00 EDT

#### H-NEURAL-HUNT-04 — Raw segment contraction carries the OLMo trajectory signal without endpoint normalization

- **Hypothesis:** The old OLMo integrated-segment positive is not merely a normalized-`z` artifact: raw loss contraction over fixed observed segments has a transferable trajectory template across OLMo2 7B/13B runs.
- **Eigenquestion:** Does a leave-one-run-out raw segment-contraction template beat train-mean and previous-segment baselines without using future endpoint min/max?
- **Discriminating test:** Run `projects/neural_hunt/workspace/run_raw_segment_contraction_audit.py`. Build fixed point-count segments from raw OLMo2 7B/13B train-loss curves. For each held-out run, predict each future segment's log loss contraction from same-index contractions in other runs and compare against train-mean and target previous-segment baselines.
- **Success criterion:** The raw segment template beats both baselines on a majority of held-out segment cells and on mean absolute error.
- **Kill condition:** The normalized integrated-segment result vanishes in raw segment contraction, or the template only wins by using target endpoint normalization or run identity.
- **Scope:** Paper 7 neural substrate reopening; out-of-loop `projects/neural_hunt`.
- **Status:** `closed / negative_against_previous_segment_baseline`
- **Run(s):** `projects/neural_hunt/workspace/run_raw_segment_contraction_audit.py`
- **Result:** Raw segment contraction beats train-mean and zero-change on mean error (`0.0535` vs `0.0623` and `0.0611`) but loses to the target previous-segment baseline (`0.0447`) and passes only `2/12` cells against both baselines. The normalized integrated-segment positive does not survive as a raw segment law on the current 4-run corpus.
- **Opened:** 2026-05-08 00:00:00 EDT
- **Closed:** 2026-05-08 00:00:00 EDT

#### H-NEURAL-HUNT-05 — Boundary-slope coordinate survives exact-1B and frozen cross-family validation

- **Hypothesis:** The live neural-law candidate is a boundary-slope state coordinate: prefix local decline rate calibrates an external shape template and predicts future raw loss without using the held-out future loss endpoint.
- **Eigenquestion:** Does the slope-anchor coordinate survive a frozen validation on exact OLMo2 1B raw history and a predeclared cross-family rerun, or was the 2026-05-08 positive an exploratory artifact of row selection and mid/late-prefix stress?
- **Discriminating test:** After exact OLMo2 1B stage-1 raw rows are acquired, rerun the slope-anchor gate unchanged against OLMo2 1B plus a frozen mlfoundations row-selection rule. Score against last-prefix, prefix-linear, and local-linear baselines. The cross-family script hash and row-selection criteria must be fixed before rerun. In parallel, run Meta-DARWIN on the orchestration itself: criterion-selection rigging, agent monoculture, vocabulary smuggling, post-hoc promotion, pseudo-pre-registration, and too-friendly baselines.
- **Success criterion:** Slope-anchor wins a majority of exact-1B cells and a majority of frozen cross-family cells, with mean raw MAE below the best prefix-only baseline in both packets. The win must survive stratification by dataset family, prefix fraction, and parameter/multiplier regime enough that it is not a single-family artifact. Meta-DARWIN must find no severity-1 process flaw; any new criterion learned during audit opens a new validation row rather than being scored retroactively.
- **Kill condition:** Exact 1B fails, cross-family frozen rerun drops below majority win rate, the coordinate requires future loss endpoints, run identity, or post-hoc row filtering to win, or Meta-DARWIN finds that the apparent positive depends on criterion drift, vocabulary inflation, or a baseline chosen after seeing the result.
- **Scope:** Paper 7 neural substrate reopening; out-of-loop `projects/neural_hunt`.
- **Status:** `closed / falsified_on_exact_1b`
- **Run(s):** exact OLMo2 1B acquisition `projects/gp154_scaling_law_normalized/external/fetch_olmo1b_wandb_exact_sampled_history.py`; H-05 validation `projects/neural_hunt/workspace/run_h05_exact_1b_validation.py`; median-stitched diagnostic `projects/gp154_scaling_law_normalized/external/build_olmo1b_exact_stitched_median.py`; restart residual-void audit `projects/neural_hunt/workspace/run_olmo1b_restart_overlap_hysteresis_audit.py`; auxiliary seam probe `projects/neural_hunt/workspace/run_olmo1b_restart_aux_metric_probe.py`; exploratory stratified rerun `projects/neural_hunt/workspace/run_cross_family_stratified_slope_anchor_audit.py`; repaired damage-control rerun `projects/neural_hunt/workspace/run_cross_family_fixed_online_group_audit.py`
- **Result:** Negative. Exact OLMo2 1B Stage-1 rows were acquired through the public W&B report browser-context `sampledHistory` path (`2,356,360` rows over `14` internally consecutive run segments). H-05 then failed: fixed-count online won `0/28` cells against the full baseline ladder and `1/28` against basic baselines; known-horizon progress won `1/28` against all baselines and `2/28` against basic baselines. A duplicate-step audit found `448,207` overlapping restart steps, so a diagnostic median-stitched curve over `1,907,359` unique steps was built; it also failed (`0/2` known-horizon all-baseline wins, fixed-count online non-applicable). The residual-void restart audit found no persistent global branch hysteresis: long overlaps have branch/local ratios near `1.0`. The final short restart seam is raw-CE noisy, but auxiliary metrics show no learning-rate jump, similar gradient norms, throughput change, sign-changing CE deltas, and no eval CE rows in the seam window. H-05 closes the Paper 7 neural law promotion path negatively.
- **Opened:** 2026-05-08 00:00:00 EDT
- **Closed:** 2026-05-08 16:22:52 EDT

#### H-NEURAL-HUNT-06 — Local exchange-rate coordinate beats rate-persistence baselines

- **Hypothesis:** The failed H-05 slope-anchor tail predictor killed one exchange-rate reading, not the whole object. The live object is a local exchange rate between training clock and loss contraction: a prefix-observable rate coordinate should predict next-window contraction rates better than rate persistence and local trend baselines, without future endpoint normalization.
- **Eigenquestion:** Is the neural regularity a local rate-conversion field rather than a raw tail-shape law?
- **Discriminating test:** Run `projects/neural_hunt/workspace/run_exchange_rate_coordinate_audit.py`. Build fixed log-step, prefix-only windows from OLMo2 stage-1 raw train-loss histories. For each held-out target curve, fit only a scalar exchange rate between the target prefix contraction rates and an external OLMo2 7B/13B rate template, then predict future window contraction rates and their integrated loss path. Compare against last-rate persistence, prefix-mean rate, local-linear rate trend, and unscaled external template baselines. Run the exact OLMo2 1B no-overlap packet as the primary source; optionally score full exact 1B as a source-contamination sensitivity check.
- **Success criterion:** On exact OLMo2 1B no-overlap rows, the exchange-rate template wins a majority of target/prefix cells against all baselines on next-window rate MAE and also lowers mean integrated loss MAE below the best baseline. A positive that only appears on full overlapping restart rows does not promote.
- **Kill condition:** The exchange-rate template loses to persistence/local-trend baselines on most cells, wins only through endpoint horizon, run identity, duplicate-step overlap, post-hoc window choice, or improves rate MAE while worsening integrated loss enough to make the coordinate non-operational.
- **Scope:** Paper 7 neural substrate reopening; out-of-loop `projects/neural_hunt`.
- **Status:** `closed / falsified_on_exact_1b_no_overlap`
- **Run(s):** `projects/neural_hunt/workspace/run_exchange_rate_coordinate_audit.py`
- **Result:** Negative. The scalar exchange-rate coordinate was tested directly on fixed log-step contraction-rate windows instead of downstream tail MAE. On exact OLMo2 1B no-overlap rows, it wins only `3/41` next-window rate cells and `10/41` integrated-loss cells. Mean rate MAE is `1.5040` versus last-rate persistence at `0.7562`; mean integrated-loss MAE is `0.1657` versus last-rate persistence at `0.0747`. Full-overlap sensitivity is also negative (`1/41` rate-win cells, `10/41` integrated-loss cells). This kills the simple scalar local exchange-rate rescue. The remaining neural object is bounded morphology plus source-audit discipline, unless a genuinely new observable with cleaner eval/restart metadata is opened under a new hypothesis.
- **Opened:** 2026-05-08 16:45:09 EDT
- **Closed:** 2026-05-08 16:45:09 EDT

#### H-NEURAL-HUNT-07 — Cross-size evaluator exchange rate transfers across tasks

- **Hypothesis:** The scalar exchange-rate idea failed as an OLMo2 1B raw-loss
  local-rate repair, but a stronger learning-mechanics variant may survive at
  the evaluator-response level: within a source family, a scalar conversion
  between model sizes should map task-specific response rates from one size to
  the adjacent size better than size-local median and identity-source
  baselines.
- **Eigenquestion:** Is there a cross-size evaluator-response exchange-rate
  field in public aggregate trajectories, or are rate mappings dominated by
  task/model/source idiosyncrasy?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h35_datadecide_cross_size_exchange_audit.py`
  on the acquired DataDecide `summary-metrics.jsonl`. For each
  `(model, seed, adjacent_size_pair)` with enough overlapping tasks, compute
  each task's response-rate slope versus log tokens for the source and target
  sizes. Leave one task out, estimate a scalar exchange multiplier from the
  other tasks, and predict the held-out task's target-size rate from its
  source-size rate. Compare absolute error against (a) identity-source rate and
  (b) target-size median rate learned from the other tasks.
- **Success criterion:** The scalar exchange template beats the best baseline
  on at least `60%` of held-out task cells and reduces mean absolute rate error
  by at least `20%` versus the best baseline. A weaker mixed result may justify
  using DataDecide as a task-panel stress source, but not as a law candidate.
- **Kill condition:** The scalar exchange template loses to the target-median
  or identity-source baseline on most cells, only wins in one size pair/source
  family, or requires model/task identity lookup beyond the leave-one-task-out
  scalar.
- **Scope:** Neural Hunt source-axis audit; DataDecide aggregate evaluator
  trajectories; external learning-mechanics framing from arXiv:2604.21691.
- **Status:** `closed / falsified_on_datadecide_aggregate_cross_size`
- **Run(s):** `projects/neural_hunt/workspace/run_h35_datadecide_cross_size_exchange_audit.py`
- **Result:** Negative. On DataDecide aggregate evaluator trajectories, the
  scalar adjacent-size exchange template produced `5,584` leave-one-task-out
  cells and won only `0.416` against the stronger of identity-source and
  target-size median baselines. Mean absolute rate error was `0.02356` versus
  best-baseline `0.01682` (`1.401x` worse), with median relative improvement
  `-0.165`. This weakens the cross-model exchange-rate rescue and keeps
  DataDecide as task-panel/source-axis stress evidence, not a law source.
- **Opened:** 2026-05-10 00:00:00 EDT
- **Closed:** 2026-05-10 00:00:00 EDT

#### H-NEURAL-HUNT-08 — Evaluator response rates live on a low-dimensional mechanics mode

- **Hypothesis:** After de-anchoring from scalar exchange-rate laws, the more
  plausible learning-mechanics object is a low-dimensional evaluator-response
  mode: vectors of task response rates across training should be compressible
  in a small number of shared modes after an admissible GP-152-style coordinate
  transform.
- **Eigenquestion:** Are public aggregate evaluator trajectories organized by
  shared response modes across model/data/seed/size contexts, or is the
  structure mostly task-local noise?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h36_datadecide_response_mode_audit.py`
  on DataDecide aggregate rows. Compute response-rate vectors for the
  multiple-choice task panel per `(model, seed, size)` context, sweep
  admissible framer-style transforms over signed rates, and score 5-fold
  leave-context-out masked-task reconstruction with `k=1..3` PCA modes.
  Compare against the train-column median/mean baseline in standardized
  transform space.
- **Success criterion:** A transformed `k<=3` response-mode model reduces
  masked-task reconstruction MAE by at least `20%` versus the baseline, and
  the same representation has top-2 explained variance at least `0.55`. This
  would not promote a law, but it would identify a candidate mechanics
  observable to refine.
- **Kill condition:** No transform/mode count beats the baseline by `20%`,
  top-2 variance stays diffuse, or apparent compression comes only from one
  task/source family rather than shared evaluator structure.
- **Scope:** Neural Hunt source-axis audit; GP-152 de-anchor/reframe/framer
  primitive application; DataDecide aggregate evaluator trajectories.
- **Status:** `closed / confirmed_as_aggregate_response_mode`
- **Run(s):** `projects/neural_hunt/workspace/run_h36_datadecide_response_mode_audit.py`
- **Result:** Positive at the aggregate source-axis level. DataDecide response
  rates form a low-dimensional mode object under GP-152-style signed
  transforms. Best MAE result was `signed_sqrt`, `k=1`: masked-task MAE
  `0.4631` versus baseline `0.7198` (`35.7%` improvement), top-2 explained
  variance `0.738`. Best relative-improvement row was `signed_log`, `k=1`:
  improvement `36.7%`, top-2 explained variance `0.746`. This supports
  de-anchoring from scalar exchange rates toward response-mode dynamics, but
  remains aggregate evidence only.
- **Opened:** 2026-05-10 00:00:00 EDT
- **Closed:** 2026-05-10 00:00:00 EDT

#### H-NEURAL-HUNT-09 — Response-mode residuals expose the next hidden mechanics variable

- **Hypothesis:** If H-NEURAL-HUNT-08 is positive, the next scientific yield is
  not another global score but the residual void: the part of evaluator
  response not explained by the shared mode should concentrate by task family,
  model/data source, seed, or size band, revealing the next state variable for
  learning mechanics.
- **Eigenquestion:** What is hiding in plain sight in the residuals of the
  low-dimensional response-mode model?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h37_datadecide_response_residual_void.py`
  after H36. Use the best H36 representation (`signed_log` response rates),
  fit full-sample PCA modes, compute reconstruction residuals for `k=1` and
  `k=2`, and aggregate residual mass by task, model, seed, size, and PC-score
  associations. Report the strongest residual concentration and whether size
  or source identity explains PC scores.
- **Success criterion:** A residual concentration explains at least `25%` more
  residual mass than the median group in one interpretable axis, or a factor
  such as size/model explains at least `25%` of PC-score variance. That would
  define the next source-axis hypothesis.
- **Kill condition:** Residuals are diffuse across all axes, or the only
  concentration is a known measurement artifact that does not suggest a
  pre-registered next test.
- **Scope:** Neural Hunt source-axis audit; residual/negative-space mining
  after H36; DataDecide aggregate evaluator trajectories.
- **Status:** `closed / confirmed_size_axis_residual_void`
- **Run(s):** `projects/neural_hunt/workspace/run_h37_datadecide_response_residual_void.py`
- **Result:** Positive residual finding. In signed-log response-rate space,
  PC1 explains `0.618`, PC2 `0.127`, and top-2 cumulative variance is `0.745`.
  PC1 is strongly size-governed: eta-squared of PC1 by size is `0.869`.
  The strongest residual concentration axis is also size, with top/median
  residual ratio `1.900`; `4M` is the largest residual size group. This shows
  scalar size exchange failed not because size is irrelevant, but because size
  acts through a response-mode manifold rather than a one-scalar conversion.
- **Opened:** 2026-05-10 00:00:00 EDT
- **Closed:** 2026-05-10 00:00:00 EDT

#### H-NEURAL-HUNT-10 — Size-conditioned response-mode flow predicts held-out source families

- **Hypothesis:** The H37 size axis is not only a descriptive correlate:
  response-mode PC1 follows a size-conditioned flow that predicts held-out
  data/source families better than a source-family mean baseline; remaining
  residuals then expose data-mixture effects.
- **Eigenquestion:** Is the dominant evaluator-response mode a lawful function
  of model size, or does size only label source-family artifacts?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h39_datadecide_size_conditioned_mode_flow.py`.
  Reuse the H36/H37 signed-log response-rate matrix, compute mode scores, and
  score leave-source-family-out prediction of PC1/PC2 from polynomial functions
  of log parameter count. Compare against train-mean baselines, then aggregate
  post-size residuals by data/source family.
- **Success criterion:** A size-only model reduces held-out-family PC1 MAE by
  at least `20%` versus train-mean baseline. Residual concentration by source
  family then becomes the next data-mixture hypothesis.
- **Kill condition:** Size-only prediction fails held-out source families or
  residual concentration is so family-specific that the size flow is likely a
  source artifact.
- **Scope:** Neural Hunt source-axis audit; H36/H37 follow-up; DataDecide
  aggregate evaluator trajectories.
- **Status:** `closed / confirmed_size_conditioned_pc1_flow`
- **Run(s):** `projects/neural_hunt/workspace/run_h39_datadecide_size_conditioned_mode_flow.py`
- **Result:** Positive for PC1, bounded/null for PC2. A quadratic function of
  log parameter count predicts held-out source-family PC1 scores with MAE
  `0.7579` versus train-mean baseline `1.8132`, relative improvement `0.582`.
  The same size-only route weakly explains PC2 (`0.048` relative improvement).
  Post-size residuals concentrate most in `dolma`, then `c4`, `dclm`,
  `falcon`, and `fineweb`, so the next state variables are data-mixture and
  task-semantics axes rather than another scalar exchange-rate law.
- **Opened:** 2026-05-10 00:00:00 EDT
- **Closed:** 2026-05-10 00:00:00 EDT

#### H-NEURAL-HUNT-11 — Post-size residuals expose a second learning-mechanics coordinate

- **Hypothesis:** After H39 removes the dominant size-conditioned PC1 flow,
  the remaining response-mode residual is not diffuse noise. It decomposes
  along source-mixture and task-semantics axes strongly enough to become the
  second candidate state coordinate for learning mechanics.
- **Eigenquestion:** Is the PC2/post-size residual a named data-mixture /
  task-semantics coordinate, or only source-family dirt that should not guide
  the next Neural Hunt experiment?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h40_datadecide_post_size_residual_axis.py`.
  Reuse the H36-H39 signed-log response-rate matrix. Compute PCA mode scores,
  remove the size-only PC1 flow, derive source-mixture features from the
  DataDecide model names, and compare leave-source-family-out PC2 prediction
  from mixture features against train-mean and size-only baselines. Separately
  score task-loading concentration by semantic groups.
- **Success criterion:** A source-mixture model improves held-out-family PC2
  MAE by at least `15%` versus train-mean baseline and by at least `10%`
  versus size-only baseline, with a non-diffuse task semantic concentration
  ratio of at least `1.5`.
- **Kill condition:** Mixture features fail to beat baselines or PC2 loadings
  are semantically diffuse. Then PC2 remains a residual frontier, not a second
  state coordinate.
- **Scope:** Neural Hunt source-axis audit; H39 follow-up; DataDecide
  aggregate evaluator trajectories.
- **Status:** `closed / partial_task_semantics_only`
- **Run(s):** `projects/neural_hunt/workspace/run_h40_datadecide_post_size_residual_axis.py`
- **Result:** Partial. PC2 is semantically concentrated but not source-mixture
  predictable across held-out source families. The size+mixture model improves
  PC2 held-out-family MAE only `1.4%` versus train-mean baseline and only
  `0.3%` versus size-only. The task-loading semantic concentration ratio is
  strong (`7.83`), dominated by `boolq` / reading-boolean behavior. Therefore
  PC2 should not be promoted as a data-mixture coordinate today; the next
  candidate is a task-interface / reading-boolean measurement coordinate.
- **Opened:** 2026-05-10 00:00:00 EDT
- **Closed:** 2026-05-10 00:00:00 EDT

#### H-NEURAL-HUNT-12 — The BoolQ residual is a robust task-interface coordinate, not a metric artifact

- **Hypothesis:** H40's PC2/BoolQ residual is not a single-metric artifact.
  It survives metric variants and task-panel expansion as a reading-boolean
  task-interface coordinate.
- **Eigenquestion:** Does the BoolQ axis remain visible when the response-mode
  representation is perturbed, or does it disappear once the metric/task panel
  changes?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h41_datadecide_boolq_axis_robustness.py`.
  Recompute response-rate PCA under multiple accuracy/probability metrics,
  compare BoolQ's PC2 loading rank/share on the 8-task panel, repeat on the
  10-task panel including `csqa` and `mmlu`, and run a BoolQ-excluded panel to
  see where residual mass moves.
- **Success criterion:** BoolQ is the top PC2 absolute loading in at least
  `3` admissible metric variants and remains top on the 10-task primary panel.
- **Kill condition:** BoolQ drops out under metric normalization or task-panel
  expansion, making H40's axis a metric/panel artifact.
- **Scope:** Neural Hunt source-axis audit; H40 follow-up; DataDecide
  aggregate evaluator trajectories.
- **Status:** `closed / robust_task_interface_candidate`
- **Run(s):** `projects/neural_hunt/workspace/run_h41_datadecide_boolq_axis_robustness.py`
- **Result:** Positive with one metric caveat. BoolQ is the top PC2 absolute
  loading in `5/6` base 8-task metric variants (`primary_metric`, `acc_raw`,
  `acc_per_token`, `acc_per_char`, `norm_correct_prob`; exception:
  `acc_uncond`, where BoolQ and Winogrande have zero PC2 signal). BoolQ also
  remains top on the expanded 10-task primary panel including `csqa` and
  `mmlu` (`0.833` abs loading, `0.391` abs-loading share). Removing BoolQ
  shifts PC2 mass to `winogrande`, `arc_easy`, and `openbookqa`, so the axis
  is not only random panel noise. Treat BoolQ/reading-boolean as a robust
  task-interface residual candidate for future OLMo projection, not as a
  universal law.
- **Opened:** 2026-05-10 00:00:00 EDT
- **Closed:** 2026-05-10 00:00:00 EDT

#### H-NEURAL-HUNT-13 — The BoolQ axis is not fully explained by DataDecide task-metric schema

- **Hypothesis:** H41's BoolQ/reading-boolean axis is not reducible to
  DataDecide task-metric schema quirks such as primary metric name, zero
  `acc_uncond`, or denominator resolution.
- **Eigenquestion:** Is the robust BoolQ PC2 axis a task-interface residual
  worth carrying into OLMo projection, or a schema artifact caused by
  task-specific metric conventions?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h42_datadecide_boolq_schema_artifact_audit.py`.
  Join H41 PC2 loadings with per-task metric schema: primary metric name,
  zero-rate by metric, median instance count, denominator quantum, and choice
  index statistics. Score whether schema-equivalent tasks share the same PC2
  loading behavior and whether BoolQ remains an outlier relative to the
  schema-matched group.
- **Success criterion:** BoolQ remains the largest PC2 loading within its
  schema-equivalent group by at least `2x` the group median, and at least one
  common non-primary metric still ranks BoolQ first. Then carry it as a
  task-interface residual, with schema caveat.
- **Kill condition:** BoolQ's PC2 dominance is explained by a schema group
  shared with other tasks or disappears under common metrics. Then demote H41
  to metric artifact.
- **Scope:** Neural Hunt source-axis audit; H41 follow-up; DataDecide
  aggregate evaluator trajectories.
- **Status:** `closed / partial_schema_artifact_not_ruled_out`
- **Run(s):** `projects/neural_hunt/workspace/run_h42_datadecide_boolq_schema_artifact_audit.py`
- **Result:** Partial. BoolQ shares the obvious schema group with Winogrande:
  `primary_metric_name=acc_raw` and `acc_uncond_zero_rate=1.0`. BoolQ remains
  larger than Winogrande on the expanded 10-task PC2 (`0.833` vs `0.351`) and
  ranks first under four non-primary metrics (`acc_raw`, `acc_per_token`,
  `acc_per_char`, `norm_correct_prob`), but the pre-registered schema-group
  dominance criterion fails: BoolQ is only `1.41x` the schema-group median,
  below the `2x` bar. Therefore H41 is not killed, but the BoolQ/interface axis
  must be carried as a residual candidate with explicit schema caveat until
  OLMo projection or a non-DataDecide source falsifies the artifact explanation.
- **Opened:** 2026-05-10 00:00:00 EDT
- **Closed:** 2026-05-10 00:00:00 EDT

#### H-NEURAL-HUNT-14 — Public OLMo aggregate rows can falsify whether BoolQ/interface is DataDecide-local

- **Hypothesis:** If H41/H42's BoolQ/interface residual is not only a
  DataDecide schema artifact, then a non-DataDecide OLMo aggregate source with
  BoolQ and Winogrande tasks should show a BoolQ-like response-mode loading in
  late-stage evaluator-response rates.
- **Eigenquestion:** Does the BoolQ/interface residual survive when projected
  onto public OLMo `signal-and-noise` aggregate rows, or is it probably
  DataDecide-local?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h43_olmo_public_boolq_projection.py`.
  Build consecutive-log-step primary-score response-rate matrices from the
  H20 public `signal-and-noise` aggregate CSV, using both the exact base task
  panel (`boolq`, `winogrande`, `arc_easy`, `arc_challenge`, `hellaswag`,
  `openbookqa`, `piqa`, `socialiqa`) and the `:mc` variant panel where present.
  PCA the standardized interval-by-task rate matrices and compare BoolQ
  loadings against Winogrande and the panel median.
- **Success criterion:** In at least one non-DataDecide OLMo panel, BoolQ or
  `boolq:mc` is top-2 on PC1 or PC2 absolute loading and exceeds the matched
  Winogrande loading by at least `1.5x`. Then keep BoolQ/interface as a
  cross-source residual candidate, still not a law.
- **Kill condition:** BoolQ is not salient in either public OLMo panel, or it
  tracks Winogrande closely enough that the matched ratio is below `1.5x`.
  Then demote the BoolQ/interface residual to DataDecide-local until per-instance
  H27/H29 evidence says otherwise.
- **Scope:** Neural Hunt source-axis audit; H42 follow-up; non-DataDecide
  public OLMo aggregate evaluator trajectories.
- **Status:** `closed / ambiguous_false_negative_risk_high`
- **Run(s):** `projects/neural_hunt/workspace/run_h43_olmo_public_boolq_projection.py`
- **Audit run(s):** `projects/neural_hunt/workspace/run_h43b_olmo_public_boolq_projection_sensitivity.py`
- **Result:** Ambiguous; hard negative unsafe. The original H43 primary-score
  rate test produced a base-panel near miss: BoolQ is top PC2 loading
  (`0.616`), but the matched BoolQ/Winogrande ratio is `1.461`, just below
  the pre-registered `1.5x` bar. The H43b falsifier audit shows this threshold
  is doing too much work: across `36` metric/mode panels, BoolQ is top-2 on
  PC1/PC2 in `18` cases, and in `12` cases it is top-2 while opposite-signed
  against Winogrande. Therefore H43 cannot promote a cross-source coordinate,
  but it also cannot demote BoolQ/interface to DataDecide-local artifact.
  Status: caveated cross-source diagnostic; second coordinate remains open.
- **Opened:** 2026-05-10 00:00:00 EDT
- **Closed:** 2026-05-10 00:00:00 EDT

#### H-NEURAL-HUNT-15 — Public OLMo aggregate rows contain low-dimensional evaluator-response modes

- **Hypothesis:** The H36 response-mode object transfers beyond DataDecide: in
  public OLMo `signal-and-noise` aggregate rows, task response-rate vectors are
  low-dimensional enough that a small PCA basis predicts held-out task rates
  better than a task-mean baseline.
- **Eigenquestion:** Is the scientific object "low-dimensional evaluator
  response-mode flow" cross-source, or was H36/H39 mainly a DataDecide-specific
  aggregate artifact?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h44_olmo_public_response_mode_audit.py`.
  Build response-rate matrices over consecutive log-step intervals from the H20
  public OLMo aggregate CSV. Test panels: H22 targeted `24` tasks, H27
  cost-capped `10` tasks, DataDecide-overlap base tasks, and a broad all-task
  panel. For `primary_score`, `logits_per_byte_corr`, and
  `logits_per_char_corr`, score k=1..3 PCA masked-task reconstruction by
  fold-held-out intervals.
- **Success criterion:** At least one non-DataDecide OLMo panel has
  relative-improvement >= `0.20` over task-mean baseline with top-3 explained
  variance >= `0.55`. Stronger if H22/H27 targeted panels and broad all-task
  panel both pass.
- **Kill condition:** No panel/metric/k clears `0.05` relative improvement or
  top-3 variance `0.45`; then demote H36/H39 to DataDecide-local source-axis
  hypothesis until sealed per-instance H27/H29 evidence.
- **Scope:** Neural Hunt source-axis audit; H36/H39 cross-source check;
  non-DataDecide public OLMo aggregate evaluator trajectories.
- **Status:** `closed / partial_not_predictive_on_public_olmo_aggregate`
- **Run(s):** `projects/neural_hunt/workspace/run_h44_olmo_public_response_mode_audit.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Partial but below promotion bar. H44 scored `36` panel/metric/k
  rows over public OLMo late Stage-1 aggregate intervals. No row passed the
  pre-registered success rule. The best row was H22 targeted `24` tasks,
  `logits_per_char_corr`, `k=2`: masked-task MAE `0.7868` versus baseline
  `0.8708`, relative improvement `0.096`, top-3 explained variance `0.518`.
  Verdict: `olmo_public_response_modes_partial_not_predictive`. This does not
  kill H36/H39 because the source is late-stage aggregate-only and derivative
  intervals are noisy, but it blocks cross-source promotion from public OLMo
  aggregate rows alone.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-16 — H44's weak public-OLMo response-mode result is derivative-noise sensitive

- **Hypothesis:** H44 underestimates public OLMo response-mode structure because
  consecutive-step derivatives are noisy in late-stage aggregate rows; level or
  smoothed-rate representations should show stronger low-dimensional
  masked-task reconstruction than one-step response rates.
- **Eigenquestion:** Is H44 a source negative, or mainly a measurement
  representation negative?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h45_olmo_public_level_rate_sensitivity.py`.
  Re-score H44 panels over `level`, `rate`, and `two_step_rate` modes for
  `primary_score`, `logits_per_byte_corr`, and `logits_per_char_corr`.
- **Success criterion:** Any level or two-step-rate row clears the H44 success
  rule while one-step-rate rows do not, or improves best H44 relative
  improvement by at least `2x`.
- **Kill condition:** Level/two-step modes remain below `0.10` improvement and
  top3 variance `0.55`, matching H44's weak result.
- **Scope:** Neural Hunt source-axis audit; H44 falsifier audit; public OLMo
  aggregate evaluator trajectories.
- **Status:** `closed / level_rate_sensitivity_no_promotion`
- **Run(s):** `projects/neural_hunt/workspace/run_h45_olmo_public_level_rate_sensitivity.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Negative for promotion, partial structure remains. H45 scored
  `108` panel/metric/mode/k rows and found `0` success rows. Best level row:
  broad all-225 tasks, `logits_per_char_corr`, `k=3`, improvement `0.121`,
  top3 variance `0.404`. Best rate row reproduces H44: H22 targeted `24`
  tasks, `logits_per_char_corr`, `k=2`, improvement `0.096`, top3 `0.518`.
  Best two-step-rate row: broad all-225 tasks, improvement `0.081`, top3
  `0.361`. Verdict: level/smoothed-rate sensitivity does not rescue H44 into
  a cross-source response-mode positive.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-17 — DataDecide interval geometry explains whether H44 is source-negative or measurement-regime weak

- **Hypothesis:** H44's weak public-OLMo aggregate result is partly a
  measurement-regime effect: within-trajectory interval response-rate matrices
  are weaker than H36's across-context slope vectors, even on DataDecide.
- **Eigenquestion:** Did public OLMo aggregate fail because OLMo/source is
  different, or because interval-rate geometry is a weaker measurement surface
  than across-source slope vectors?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h46_datadecide_interval_geometry_audit.py`.
  Build DataDecide base-task response-rate rows from consecutive token
  intervals within each `(model, seed, size)` trajectory. Score both pooled
  interval rows and single-trajectory/O(LMo-like) per-context rows with the
  same PCA masked-task reconstruction contract as H44.
- **Success criterion:** If pooled and per-context interval rows clear H44's
  `0.20` / `0.55` rule, then H44 is more likely a public-OLMo/source negative.
  If pooled passes but per-context is weak, the bottleneck is single-trajectory
  underpowering. If both are weak, H36's positive object depends on
  across-context slope geometry rather than interval geometry.
- **Kill condition:** Treat any interval positive as law promotion. This test is
  only a measurement-regime discriminator; all evidence remains aggregate.
- **Scope:** Neural Hunt source-axis audit; H44/H45 falsifier audit;
  DataDecide aggregate evaluator trajectories.
- **Status:** `closed / interval_geometry_weak_like_public_olmo`
- **Run(s):** `projects/neural_hunt/workspace/run_h46_datadecide_interval_geometry_audit.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Measurement-regime weakness confirmed. H46 found `447` usable
  DataDecide contexts and `13,774` pooled interval rows. Pooled interval PCA
  masked reconstruction fails the H44 rule and is worse than baseline:
  best pooled `k=1`, improvement `-0.090`, top3 `0.505`. Per-context
  OLMo-like interval rows are also mostly weak: only `2/447` contexts pass
  (`0.004` pass rate), median improvement `-0.050`, mean improvement `-0.044`.
  Therefore H44/H45 should not be read as clean public-OLMo source negatives;
  within-trajectory interval geometry itself is weak even on DataDecide.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-18 — DataDecide response-mode positivity depends on context diversity and sample size

- **Hypothesis:** H36's across-context slope-mode positive does not require the
  full `473` DataDecide contexts if the subset preserves source/size diversity;
  H27/H29-scale evidence can be useful if it spans enough independent contexts.
- **Eigenquestion:** How many and what kind of contexts are needed before
  response-mode masked-task reconstruction becomes stable?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h47_datadecide_slope_mode_sample_efficiency.py`.
  Rebuild the H36 slope matrix and bootstrap subsets by random contexts,
  family-stratified contexts, single-family contexts, and single-size contexts
  at `n={30,60,120,240}` where available. Score signed-log PCA masked-task
  reconstruction with k=1 and k=2 under the H36 rule.
- **Success criterion:** Diverse `n<=60` subsets pass in at least `50%` of
  bootstrap replicates. Then a modest H27/H29 packet can be scientifically
  useful if it spans independent contexts. If only `n>=120` or full diversity
  passes, GPU planning needs broader context acquisition.
- **Kill condition:** Single-family or single-size subsets pass as often as
  diverse subsets; then H36 is not really source-diversity dependent and the
  current explanation is over-specific.
- **Scope:** Neural Hunt source-axis audit; H36/H46 measurement contract
  sharpening; DataDecide aggregate evaluator trajectories.
- **Status:** `closed / sample_efficient_size_diversity_required`
- **Run(s):** `projects/neural_hunt/workspace/run_h47_datadecide_slope_mode_sample_efficiency.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Positive for sample efficiency, corrective on diversity. H47
  scored `2,720` bootstrap rows. Random `n=30`, `k=1` subsets pass the H36
  rule in `1.000` of replicates with median improvement `0.349` and median
  top2 `0.804`; family-stratified `n=30`, `k=1` passes `0.950`. Random and
  family-stratified `n=60`/`n=120` pass `1.000`. However, single-family
  `n=60`, `k=1` also passes `0.992`, while single-size `n=60`, `k=1` passes
  `0.000` with median improvement `0.100`. Therefore the H36 slope-mode object
  is sample-efficient and does not require broad source-family diversity, but
  it does require size/context variation. H27/H29 single-size OLMo packets can
  test within-size diagnostics, but cannot by themselves promote the PC1
  size-flow object.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-19 — Single-size packets can still test BoolQ/interface residuals

- **Hypothesis:** Although H47 blocks single-size packets from promoting PC1
  size-flow, fixed-size DataDecide slices still expose a BoolQ/interface
  residual often enough to make H27/H29 single-size OLMo packets scientifically
  useful as residual diagnostics.
- **Eigenquestion:** After removing size variation entirely, does BoolQ remain
  a named response-mode residual, or was its salience mostly a cross-size
  artifact of the H36/H41 matrix?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h48_datadecide_single_size_boolq_residual.py`.
  For each DataDecide size slice with at least `20` complete contexts, rebuild
  task slope matrices across H41 metric variants, standardize within the size
  slice, compute PC1/PC2 task loadings, and score whether BoolQ is top-2 on
  either coordinate.
- **Success criterion:** Primary-metric fixed-size slices show BoolQ top-2 on
  PC1 or PC2 in at least `5/9` sizes and all metric-size panels have BoolQ
  top-2 rate at least `0.50`. Then H27/H29 single-size packets retain a
  named residual-diagnostic target.
- **Kill condition:** Primary-metric fixed-size slices show BoolQ top-2 in at
  most `2/9` sizes and all-panel top-2 rate is below `0.30`. Then single-size
  H27/H29 packets should be treated mainly as runtime/instrument acquisition,
  not as a strong BoolQ/interface discriminator.
- **Scope:** Neural Hunt source-axis audit; H41/H47 projection contract
  sharpening; DataDecide aggregate evaluator trajectories.
- **Status:** `closed / single_size_boolq_residual_not_supported`
- **Run(s):** `projects/neural_hunt/workspace/run_h48_datadecide_single_size_boolq_residual.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Negative. H48 scored `54` metric-size panels and hit the kill
  condition: primary-metric fixed-size slices show BoolQ top-2 on PC1/PC2 in
  only `2/9` sizes, and all metric-size panels show BoolQ top-2-any rate
  `0.222` with rank1-any rate `0.074`. Therefore H41's BoolQ/interface
  residual is not stable once size variation is removed. After H47/H48, a
  single-size H27/H29 packet is mainly a measurement/instrument acquisition
  route unless it adds another independent diversity axis; it cannot promote
  PC1 size-flow or the BoolQ/interface residual by itself.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-20 — Expanded DataDecide aggregate grid changes the Neural Hunt source-axis read

- **Hypothesis:** The public `DataDecide-eval-results` macro-average table
  contains the missing `14`-size aggregate grid, and rerunning the H36/H47/H48
  discriminators on that expanded grid will materially sharpen the current
  size/context-diversity conclusion before any GPU spend.
- **Eigenquestion:** Does adding the missing DataDecide sizes preserve the
  response-mode object while changing the single-size residual or diversity
  interpretation?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h50_datadecide_expanded_grid_audit.py`.
  Load `data/macro_avg-00000-of-00001.parquet` from
  `allenai/DataDecide-eval-results`, parse the metrics JSON into a
  summary-compatible aggregate matrix, then rerun: H36-style masked-task PCA,
  H47-style sample/diversity bootstraps, and H48-style fixed-size BoolQ
  residual checks.
- **Success criterion:** Expanded-grid H36 still passes (`>=0.20` improvement
  and top2 `>=0.55`), while H47/H48 conclusions either stay directionally
  stable or sharpen the diversity axis with more contexts.
- **Kill condition:** Expanded-grid H36 fails, or single-size subsets now pass
  H36 as often as diverse subsets and BoolQ becomes stable in fixed-size
  panels. Then the 9-size local result was an undersampling artifact.
- **Scope:** Neural Hunt source-axis audit; H49 source-frontier follow-up;
  DataDecide aggregate evaluator trajectories.
- **Status:** `closed / expanded_grid_preserves_response_mode_size_dependency_boolq_mixed_not_promoted`
- **Run(s):** `projects/neural_hunt/workspace/run_h50_datadecide_expanded_grid_audit.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Positive for the response-mode object and corrective on the
  fixed-size residual. H50 acquired the `DataDecide-eval-results`
  macro-average parquet and found `14` raw size buckets; `13` size buckets are
  slope-eligible under the five-point trajectory rule, adding `8M`, `10M`,
  `14M`, and `16M` to the local H36-H48 slope matrix while `6M` lacks enough
  trajectory points. Expanded H36 passes more strongly: `975` complete
  contexts, k=1 relative improvement `0.446`, top2 `0.799`. Expanded H39 PC1
  size-flow strengthens: held-out-family improvement `0.736` (`0.5386` MAE vs
  `2.0375` baseline). H47 stays directionally stable: random `n=30` and
  family-stratified `n=30` both pass `1.000`, while single-size `n=60` passes
  `0.000`. H48 is corrected from hard negative to mixed-not-promoted:
  fixed-size BoolQ top2-any is `4/13` on primary panels and `0.415` across all
  metric-size panels. Therefore H47's size/context requirement is stronger,
  and BoolQ/interface remains open but not promotable from fixed-size panels.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-21 — Fixed-size residual is a task-family map, not BoolQ-specific

- **Hypothesis:** After H50 corrects fixed-size BoolQ to mixed-not-promoted,
  the expanded DataDecide fixed-size residual still has a stable task-family
  structure that can guide future fixed-size diagnostics.
- **Eigenquestion:** If BoolQ is not the fixed-size residual, what task family
  actually dominates PC1/PC2 inside fixed-size slices?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h51_datadecide_fixed_size_residual_map.py`.
  Reuse the H50 expanded macro-average grid. For each metric-size panel, compute
  PC1/PC2 task loadings and count top-2 task appearances by task, metric, and
  size.
- **Success criterion:** At least one non-BoolQ task family appears in top-2
  PC1/PC2 slots in at least `50%` of expanded metric-size panels and has a
  coherent size-band pattern.
- **Kill condition:** No task appears top-2 in at least `35%` of panels, or the
  top task distribution is uniform/noisy across metrics and sizes.
- **Scope:** Neural Hunt source-axis audit; H50 residual follow-up;
  DataDecide aggregate evaluator trajectories.
- **Status:** `closed / fixed_size_residual_task_family_map_positive`
- **Run(s):** `projects/neural_hunt/workspace/run_h51_datadecide_fixed_size_residual_map.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Positive. H51 scored `65` expanded metric-size panels and found
  a stable non-BoolQ fixed-size residual map. Top2-any rates: `arc_easy`
  `54/65` (`0.831`), `arc_challenge` `51/65` (`0.785`), `hellaswag` `42/65`
  (`0.646`), versus `boolq` `27/65` (`0.415`). Primary-metric top2-any counts
  are `arc_challenge=11`, `arc_easy=9`, `piqa=8`, `hellaswag=7`, `openbookqa=5`,
  `boolq=4`. Therefore the fixed-size residual should be described as a
  task-family map dominated by ARC-style science QA and HellaSwag-style
  continuation, with BoolQ concentrated in smaller-size panels but not the
  primary residual axis.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-22 — Fixed-size ARC/HellaSwag residual is not a covariance-null artifact

- **Hypothesis:** The H51 ARC/HellaSwag fixed-size residual reflects structured
  cross-task covariance inside fixed-size DataDecide panels, not merely marginal
  task variance, finite-panel PCA noise, or metric schema.
- **Eigenquestion:** If task marginals are preserved but cross-task covariance
  is destroyed inside each metric-size panel, do ARC Easy, ARC Challenge, and
  HellaSwag still dominate PC1/PC2 top-2 loadings?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h52_datadecide_fixed_size_residual_null_audit.py`.
  Reuse the H50 expanded macro-average grid. For each metric-size panel, compute
  observed PC1/PC2 top-2 task appearances, then run a column-wise permutation
  null that preserves each task's marginal distribution within the panel while
  destroying cross-task covariance. Compare observed top2-any counts to null
  mean and 95th percentile by task.
- **Success criterion:** At least two of `{arc_easy, arc_challenge, hellaswag}`
  exceed their null 95th percentile and keep observed top2-any rate above
  `0.50`. Then H51 is not explained by marginal variance or finite-panel PCA
  noise.
- **Kill condition:** All H51 dominant tasks are within null 95th percentile,
  or only one task exceeds null while the rest collapse. Then the fixed-size
  residual map should be demoted to PCA artifact until a stronger cross-source
  test exists.
- **Scope:** Neural Hunt source-axis audit; H51 artifact-risk follow-up;
  DataDecide aggregate evaluator trajectories.
- **Status:** `closed / fixed_size_residual_exceeds_covariance_null`
- **Run(s):** `projects/neural_hunt/workspace/run_h52_datadecide_fixed_size_residual_null_audit.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Positive. H52 ran `200` marginal-preserving permutation null
  replicates over `65` metric-size panels. All three H51 dominant tasks exceed
  null p99 while preserving top2-any rate above `0.50`: `arc_easy` observed
  `54/65` vs null p95 `38.0` / p99 `40.0`; `arc_challenge` observed `51/65`
  vs p95 `39.05` / p99 `42.01`; `hellaswag` observed `42/65` vs p95 `39.0` /
  p99 `41.01`. BoolQ does not clear null (`27/65` vs p95 `38.0`). Therefore
  the fixed-size ARC/HellaSwag residual is not explained by marginal task
  variance or finite-panel PCA noise alone.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-23 — Fixed-size residual has a size-regime transition, not only a static task-family map

- **Hypothesis:** The H51/H52 fixed-size residual is not a static ARC/HellaSwag
  map. It contains a size-regime transition: ARC-style science QA is the stable
  backbone, BoolQ/interface is concentrated in early/small-size panels, and
  HellaSwag/continuation becomes stronger in late/large-size panels.
- **Eigenquestion:** After grouping top PC1/PC2 tasks into predeclared task
  families, do fixed-size residual family rates change by parameter-size band
  beyond what is expected from preserving family marginals within each metric?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h53_datadecide_fixed_size_transition_map.py`.
  Use H51 metric-size panel rows. Freeze bands before scoring:
  early=`4M,8M,10M,14M,16M,20M`, mid=`60M,90M,150M`,
  late=`300M,530M,750M,1B`. Freeze families:
  science_qa=`arc_easy,arc_challenge,openbookqa`,
  continuation=`hellaswag`, boolean_reading=`boolq`,
  physical_commonsense=`piqa`, social_coref=`socialiqa,winogrande`.
  Compute family top2-any rates per band and compare band contrasts to a
  within-metric size-label permutation null.
- **Success criterion:** Promote a size-regime transition if science_qa appears
  in at least `0.75` of panels in every band and at least one of the directional
  contrasts clears the permutation-null p95: continuation late-minus-early
  `>=0.20`, or boolean_reading early-minus-late `>=0.20`.
- **Kill condition:** If family rates are band-stationary under the null, or
  the only positive is a posthoc family label, keep H51/H52 as a static
  fixed-size residual map and do not describe a size-regime transition.
- **Scope:** Neural Hunt source-axis audit; H52 mechanism follow-up;
  DataDecide aggregate evaluator trajectories.
- **Status:** `closed / fixed_size_residual_size_regime_transition_positive`
- **Run(s):** `projects/neural_hunt/workspace/run_h53_datadecide_fixed_size_transition_map.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Positive. H53 scored `65` H51 metric-size panels grouped into
  frozen early/mid/late size bands and ran a `1000`-rep within-metric
  size-label permutation null. Science QA is the stable backbone with band rate
  `1.000` in early, mid, and late. BoolQ/interface is early-heavy:
  boolean_reading early-minus-late is `0.633` versus null p95 `0.250`.
  HellaSwag/continuation is later-heavy: continuation late-minus-early is
  `0.367` versus null p95 `0.233`. Therefore the H51/H52 fixed-size residual is
  better described as a size-regime transition over task families: ARC/science
  QA backbone, early BoolQ/interface, later HellaSwag/continuation.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-24 — Public OLMo aggregate rows weakly project the H53 late-band family signature

- **Hypothesis:** If H53 is a real learning-mechanics source-axis object rather
  than DataDecide-only structure, public OLMo 1B late-stage aggregate rows should
  weakly resemble the H53 late fixed-size signature: science-QA backbone plus
  HellaSwag/continuation salience, with BoolQ/interface less dominant than in
  early DataDecide bands.
- **Eigenquestion:** On public OLMo aggregate rows, do base-panel PC1/PC2 task
  families align more with H53 late-band structure or with the earlier
  BoolQ/interface diagnostic?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h54_olmo_public_h53_signature_projection.py`.
  Use the H20 `signal-and-noise` public OLMo 1B aggregate rows. For the frozen
  base tasks and `:mc` task variants when present, compute PCA loadings over
  level, one-step-rate, and two-step-rate matrices for frozen metrics
  `primary_score`, `acc_raw`, `acc_per_token`, `acc_per_char`, `acc_uncond`,
  `logits_per_byte_corr`, and `logits_per_char_corr`. Map PC1/PC2 top-2 tasks
  into the same frozen families as H53.
- **Success criterion:** Treat as weak cross-source support only if at least
  `40%` of usable panels contain both science_qa and continuation families in
  PC1/PC2 top2-any and BoolQ/boolean_reading appears in at most `30%` of usable
  panels. This would not promote a law; it would only support H53 as a
  cross-source projection target.
- **Kill condition:** If boolean_reading appears at least as often as
  continuation, or science_qa appears in fewer than `50%` of usable panels,
  public OLMo aggregate does not support the H53 late-band projection. Keep H53
  DataDecide-local until sealed OLMo/per-instance rows exist.
- **Scope:** Neural Hunt source-axis cross-source check; H53 projection
  follow-up; public OLMo aggregate-only evidence.
- **Status:** `closed / olmo_public_does_not_support_h53_late_signature`
- **Run(s):** `projects/neural_hunt/workspace/run_h54_olmo_public_h53_signature_projection.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Negative for cross-source support. H54 scored `36` public OLMo
  aggregate metric/mode/panel combinations. Science-QA appears often
  (`34/36`, rate `0.944`), but the H53 late signature appears in only `6/36`
  panels (`0.167`). BoolQ/boolean_reading appears in `18/36` panels (`0.500`),
  more often than HellaSwag/continuation (`12/36`, `0.333`), crossing the kill
  condition. Therefore public OLMo aggregate rows do not support the H53
  late-band projection. H53 remains a DataDecide source-axis object until
  sealed OLMo/per-instance checkpoint rows exist.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-25 — H54 public-aggregate failure is panel/schema split, not uniform source failure

- **Hypothesis:** H54's failure to project the H53 late-band signature is not
  uniform across public OLMo aggregate panels. The base task panel weakly
  retains the H53 late signature, while `:mc` interface variants suppress the
  HellaSwag/continuation component and raise interface/schema residuals.
- **Eigenquestion:** When H54 rows are paired by metric and measurement mode,
  is the late-signature failure concentrated in the `:mc` panel relative to the
  base panel?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h55_olmo_public_panel_schema_split.py`.
  Load H54 result rows, pair `base8` and `mc8` rows by frozen metric and mode,
  and compute base-minus-mc contrasts for late_signature, continuation,
  boolean_reading, science_qa, and physical_commonsense. Use a paired sign-flip
  null over metric/mode pairs.
- **Success criterion:** Treat H54 as panel/schema split if base-minus-mc
  late_signature is at least `0.25` and its one-sided sign-flip p-value is
  `<=0.05`. This does not rescue cross-source promotion; it only identifies
  the residual mechanism.
- **Kill condition:** If base-minus-mc late_signature is below `0.25` or fails
  the sign-flip p-value, then H54 is a broad public-aggregate source negative,
  and no further public aggregate residual slicing should be used for H53.
- **Scope:** Neural Hunt source-axis residual audit; H54 negative-to-object
  checkpoint; public OLMo aggregate-only evidence.
- **Status:** `closed / olmo_public_panel_schema_split_positive`
- **Run(s):** `projects/neural_hunt/workspace/run_h55_olmo_public_panel_schema_split.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Positive. H55 paired H54 `base8` and `mc8` rows over `18`
  metric/mode pairs. The H53 late-signature split is concentrated in panel
  schema: base panels contain `6/18`, while `:mc` panels contain `0/18`,
  base-minus-mc delta `0.333`, sign-flip p `0.014`. Continuation is also higher
  in base (`8/18`) than `:mc` (`4/18`) but does not clear the p-value
  threshold. BoolQ/interface is slightly higher in `:mc` (`10/18`) than base
  (`8/18`). Therefore H54 is not a uniform public-aggregate source failure; it
  is a panel/schema residual. This still does not promote H53 cross-source.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-26 — Existing H27/H29 packets preserve enough schema structure for H55-aware diagnostics

- **Hypothesis:** The already-prepared H27/H29 OLMo packets accidentally
  preserve enough base-vs-`:mc` task-interface structure to support the H55
  schema-aware diagnostic without redesign. If not, they remain measurement
  plumbing only until a revised schema-balanced packet is generated.
- **Eigenquestion:** Do H27/H29 contain enough matched base/`:mc` or base/`:rc`
  task families to estimate interface-conditioned response modes rather than
  mixing schema variants as interchangeable measurements?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h56_olmo_packet_schema_readiness_audit.py`.
  Classify H22, H27, and H29 task selections by interface suffix
  (`base`, `mc`, `rc`, other), base task family, and paired availability.
  Compute whether each packet has at least `4` matched base-vs-suffixed families
  and at least `8` total tasks across both sides of the schema split.
- **Success criterion:** A packet is H55-ready if it has at least `4` matched
  base-vs-suffixed families and at least `8` tasks covering both base and
  suffixed variants. Then the existing GPU packet can be analyzed with schema
  state explicitly.
- **Kill condition:** If H27/H29 have fewer than `4` matched schema families,
  do not treat their future outputs as H55-aware projection evidence. Either
  generate a revised H27b/H29b schema-balanced task panel or report H27/H29 as
  runtime/per-instance acquisition only.
- **Scope:** Neural Hunt execution-readiness audit; H55 projection contract;
  no new GPU spend.
- **Status:** `closed / existing_h27_h29_schema_not_ready`
- **Run(s):** `projects/neural_hunt/workspace/run_h56_olmo_packet_schema_readiness_audit.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Negative. H56 audited H22, H27, and H29 task selections for
  H55-aware base-vs-suffixed schema readiness. H27 and H29 each contain `10`
  tasks with schema counts `base=5`, `mc=4`, `rc=1`, but only one matched
  base/suffixed family: `mmlu_clinical_knowledge`. H22 has `24` tasks with
  `base=12`, `mc=8`, `rc=4`, but only two matched families:
  `mmlu_clinical_knowledge` and `mmlu_high_school_mathematics`. All packets
  fall below the `4` matched-family readiness rule. Therefore existing H27/H29
  outputs should be treated as runtime/per-instance acquisition, not H55-aware
  schema diagnostics, unless a schema-balanced successor packet is generated.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-27 — Schema-balanced OLMo successor packet can make H55 observable

- **Hypothesis:** The H56 block is a packet-design problem rather than an OLMo
  source block. A schema-balanced successor can be generated from already
  observed public OLMo task families by selecting matched base-vs-suffixed
  panels before GPU spend, preserving H55's interface/schema state variable.
- **Eigenquestion:** Can we build a cost-bounded OLMo packet with enough matched
  task families to estimate base-vs-`:mc`/`:rc` schema effects, while retaining
  public aggregate motion and avoiding expensive generation tasks?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/generate_h57_schema_balanced_olmo_packet.py`.
  The generator must read the public H20 OLMo aggregate rows, score matched
  base/suffixed task families by pre-existing metric motion, exclude known
  expensive generation tasks, and emit official-1B plus early-training anchor
  manifests without overwriting H27/H29.
- **Success criterion:** The successor packet has at least `4` matched
  base-vs-suffixed families, at least `8` total tasks, explicit schema labels,
  and no posthoc task additions after generation. It must produce concrete dry
  run and full run commands for both official 1B and early-training anchor
  sources.
- **Kill condition:** If the public OLMo task universe cannot supply at least
  `4` matched families without expensive generation tasks, or if the selected
  panel depends on future GPU outputs, the packet is not H55-ready.
- **Scope:** Neural Hunt execution design; schema-aware measurement packet; no
  GPU run and no science promotion.
- **Status:** `closed / schema_balanced_packet_created_no_measurements`
- **Run(s):** `projects/neural_hunt/workspace/generate_h57_schema_balanced_olmo_packet.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Positive as packet design. The public OLMo H20 universe contains
  `68` matched base/suffixed task families after excluding known expensive
  generation families. H57 selected `8` matched base/`:mc` families and `16`
  tasks: `boolq`, `arc_easy`, `arc_challenge`, `hellaswag`, `piqa`,
  `openbookqa`, `mmlu_high_school_statistics`, and
  `mmlu_security_studies`. It emits official 1B and early-training anchor
  manifests with `160` and `128` checkpoint-task pairs respectively. The
  selected family set has Jaccard distance `1.000` from the prior H27/H29 family
  set, so the successor is not orbiting the old packet. Interpretation remains
  bounded: H57 is schema-ready measurement design, not acquired evidence and
  not law promotion.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-28 — H57 selected pairs carry enough public schema contrast to justify priority

- **Hypothesis:** H57 is not merely a syntactically balanced packet. Its matched
  base-vs-`:mc` task pairs carry enough observed schema contrast in public OLMo
  aggregate trajectories to justify prioritizing H57 over the older H27/H29
  runtime packets once GPU is available.
- **Eigenquestion:** Does the H57 selected family set preserve measurable
  interface/schema contrast, or did the Jaccard coverage guard produce a
  balanced but low-signal panel?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h58_h57_schema_contrast_audit.py`.
  The audit must use only H20 public OLMo aggregate rows and the frozen H57 task
  selection. For each matched family and metric, compute common-checkpoint
  base-vs-`:mc` gap trajectories, schema-gap range, mean absolute schema gap,
  selected-vs-all matched-family percentile, and whether each family clears the
  universe median on primary-score schema-gap range.
- **Success criterion:** H57 stays priority if all `8` selected families have
  common base/`:mc` public trajectories, at least `6/8` clear the all-family
  median primary-score schema-gap range, and the selected-family median
  primary-score schema-gap range is above the universe median. If not, revise
  the packet before GPU spend rather than running a low-signal balanced panel.
- **Kill condition:** If fewer than `4` H57 selected families have usable common
  base/`:mc` rows, or the selected median schema-gap range is below the public
  matched-family median, H57 remains schema-balanced but is deprioritized.
- **Scope:** Neural Hunt no-GPU packet-quality audit; H57 priority decision; no
  measurement acquisition and no science promotion.
- **Status:** `closed / h57_schema_contrast_priority_not_supported`
- **Run(s):** `projects/neural_hunt/workspace/run_h58_h57_schema_contrast_audit.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Negative for H57 priority. All `8` H57 selected families have
  usable common public base/`:mc` trajectories, but only `3/8` clear the public
  matched-family median on primary-score schema-gap range. H57's selected
  median primary-score schema-gap range is `0.06925`, below the matched-family
  universe median `0.12773`. Therefore H57 remains schema-balanced, but it is a
  low-contrast panel relative to the available public matched-family universe.
  The next packet should be a high-contrast schema-calibration successor before
  GPU spend.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-29 — High-contrast schema-calibration packet can repair H58

- **Hypothesis:** H58's negative is repairable by changing packet objective
  from frontier-family preservation to high-contrast schema calibration. A
  successor packet can keep matched base/`:mc` structure while selecting
  families above the public matched-family median schema-gap range.
- **Eigenquestion:** Can we generate a high-contrast schema-calibration packet
  that avoids H57's low-signal balanced-panel failure while staying
  cost-bounded and pre-GPU?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/generate_h59_high_contrast_schema_packet.py`.
  The generator must read H20 public OLMo aggregate rows and H57 task selection,
  rank all matched base/`:mc` families by primary-score schema-gap range, select
  the top `8`, emit official 1B and early-training anchor manifests, and report
  Jaccard distance from H57's family set.
- **Success criterion:** The H59 packet has `8` matched base/`:mc` families,
  all `8` clear the H58 universe median primary-score schema-gap range, selected
  median schema-gap range exceeds H57's median by at least `2x`, and selected
  family Jaccard distance from H57 is at least `0.5`.
- **Kill condition:** If the top schema-contrast families cannot be represented
  as runnable OLMES task pairs, or if the selected set stays too close to H57
  while failing the `2x` median improvement rule, do not replace H57.
- **Scope:** Neural Hunt no-GPU packet revision; schema-calibration route; no
  measurement acquisition and no science promotion.
- **Status:** `closed / high_contrast_schema_packet_created_no_measurements`
- **Run(s):** `projects/neural_hunt/workspace/generate_h59_high_contrast_schema_packet.py`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Result:** Positive as packet-design repair. H59 selected the top `8`
  public matched base/`:mc` families by primary-score schema-gap range:
  `mmlu_security_studies`, `mmlu_high_school_statistics`, `boolq`,
  `mmlu_college_computer_science`, `mmlu_professional_medicine`,
  `mmlu_human_aging`, `mmlu_high_school_geography`, and
  `mmlu_high_school_government_and_politics`. All `8/8` clear the H58 universe
  median schema-gap range. H59 median primary schema-gap range is `0.23765`
  versus H57 `0.06925`, a `3.43x` lift. Selected-vs-H57 family Jaccard distance
  is `0.769`. It emits official 1B and early-training anchor manifests with
  `160` and `128` checkpoint-task pairs. Interpretation remains bounded: H59 is
  a high-contrast schema-calibration packet, not measurement evidence and not a
  full H53 task-family transition packet.
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-30 — H59 needs a fail-closed heldout schema gate before GPU spend

- **Hypothesis:** Because H59 is selected from public high schema-gap contrast,
  the next apparatus requirement is a H59-specific fail-closed gate that accepts
  only jobs with per-instance/logprob-like outputs and treats heldout early/mid
  schema contrast separately from public-selector contrast.
- **Eigenquestion:** Can H59 outputs be ingested and scored in a way that
  prevents public selected contrast from being mistaken for new evidence?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h60_h59_checkpoint_schema_gate.py` before
  any GPU acquisition. With no outputs it must close as
  `not_applicable_no_measurements` while writing an empty flat table. With
  outputs, it must require aggregate metrics plus per-instance logprob-like
  prediction rows, compute matched base-vs-`:mc` schema gaps by family/metric,
  and score heldout early/mid stage-1 schema contrast against the frozen public
  H20 selector contrast.
- **Success criterion:** Before outputs exist, success is fail-closed behavior:
  zero accepted jobs, empty flat table, and a clear boundary that no evidence
  exists. After outputs exist, the heldout gate may pass only if at least `6/8`
  selected families have early/mid primary schema-gap range at least `0.5x` the
  frozen public range and at least `8` heldout checkpoint pairs.
- **Kill condition:** If the gate accepts metrics-only jobs, accepts missing
  prediction rows, uses public H20 rows as if they were new measurements, or
  cannot distinguish heldout early/mid from selector contrast, H59 cannot run.
- **Scope:** Neural Hunt H59 apparatus gate; no GPU run and no science
  promotion.
- **Run(s):** `./venv/bin/python projects/neural_hunt/workspace/run_h60_h59_checkpoint_schema_gate.py`
- **Result:** Closed as fail-closed apparatus behavior with no measurements:
  `10` manifest jobs, `0` accepted primary-measurement jobs, `10` missing
  jobs, empty flat measurement table, and scoring verdict
  `not_applicable_no_measurements`. The script now labels primary-like metric
  aliases explicitly, so future OLMES outputs that provide `acc_raw` or related
  accuracy metrics can be scored without pretending they are literal
  `primary_score`. H60 creates no learning-mechanics evidence; it only prevents
  H59's public high-contrast selector from being laundered into new evidence.
- **Status:** `closed / fail_closed_no_measurements`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-31 — H59 high-contrast schema packet may be cluster-monoculture

- **Hypothesis:** H59's public schema-contrast improvement may be bought by
  semantic cluster monoculture, especially MMLU subject variants. If so, the
  next GPU packet should either add a diversity-capped sibling or explicitly
  label H59 as schema-calibration-only rather than a broad learning-mechanics
  panel.
- **Eigenquestion:** Does the public matched base/`:mc` universe contain a
  diversity-capped high-contrast packet that preserves most of H59's contrast
  while reducing cluster concentration?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h61_h59_cluster_monoculture_audit.py` on
  H20/H57/H58/H59 artifacts. Cluster matched families by coarse semantic/source
  family (`mmlu_subject`, `science_qa`, `interface_bool`, etc.), compute H59
  top-cluster share and entropy, then greedily build an 8-family
  diversity-capped candidate from the same public matched-family universe.
- **Success criterion:** Promote a packet-design change only if H59 has
  top-cluster share at least `0.75` and the diversity-capped candidate keeps
  median primary schema-gap range above the H58 universe median and above
  H57's median. Otherwise H59 remains first, but must carry a cluster-scope
  caveat in all future interpretation.
- **Kill condition:** If the audit uses task names as evidence for a learning
  law, treats public selector contrast as new measurement, or silently
  substitutes diversity for heldout signal, it is invalid.
- **Scope:** Neural Hunt packet-design audit; no GPU run and no science
  promotion.
- **Run(s):** `./venv/bin/python projects/neural_hunt/workspace/run_h61_h59_cluster_monoculture_audit.py`
- **Result:** H61 confirms the monoculture risk and finds a low-loss repair.
  H59 has top-cluster share `0.875` (`7/8` MMLU subject families) and entropy
  `0.544` bits. The diversity-capped candidate has families
  `mmlu_security_studies`, `mmlu_high_school_statistics`, `boolq`,
  `mmlu_college_computer_science`, `mmlu_professional_medicine`, `medmcqa`,
  `openbookqa`, and `arc_easy`; top-cluster share falls to `0.500`, entropy
  rises to `1.750` bits, and median primary schema-gap range remains
  `0.237647`, above H57 and the H58 universe median. Verdict:
  `h59_cluster_monoculture_repair_available`.
- **Status:** `closed / cluster_monoculture_repair_available`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-32 — Diversity-capped high-contrast schema packet can repair H61

- **Hypothesis:** The H61 diversity-capped family set can be emitted as a
  cost-equivalent H62 sibling packet that should supersede H59 as the first GPU
  spend when the objective is both schema calibration and broad
  learning-mechanics coverage.
- **Eigenquestion:** Can the H61 repair be turned into runnable official and
  early-anchor manifests without increasing task/checkpoint count or weakening
  the fail-closed interpretation contract?
- **Discriminating test:** Generate H62 from H61's diversity-capped family set,
  preserving H59's 16-task / 10-official-checkpoint / 8-early-anchor shape and
  H60-style heldout schema gate requirement.
- **Success criterion:** H62 emits task selection, official manifest,
  early-anchor manifest, and dry/run command sheets with the same pair counts
  as H59, top-cluster share at most `0.5`, and median public primary
  schema-gap range at least H59's median.
- **Kill condition:** If H62 silently increases spend, drops matched
  base/`:mc` pairs, or uses diversity as a substitute for heldout H60 scoring,
  it must not supersede H59.
- **Scope:** Neural Hunt packet-design repair; no GPU run and no science
  promotion.
- **Run(s):**
  `./venv/bin/python projects/neural_hunt/workspace/generate_h62_diversity_capped_schema_packet.py`;
  `./venv/bin/python projects/neural_hunt/workspace/run_h60_h59_checkpoint_schema_gate.py --packet h62`
- **Result:** H62 emitted a cost-equivalent diversity-capped packet:
  `8` matched families, `16` tasks, `10` official jobs, `8` early-anchor jobs,
  top-cluster share `0.500`, median primary schema-gap range `0.237647`, and
  Jaccard distance `0.545` from H59. The genericized schema gate also closes
  fail-closed for H62 with `0` accepted jobs and `10` missing jobs. H62 should
  supersede H59 for first GPU spend when broad scientific yield matters; H59
  remains the sharper MMLU-heavy schema-stress packet.
- **Status:** `closed / diversity_capped_packet_created_no_measurements`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-33 — H62 runtime task aliases must be resolved before GPU spend

- **Hypothesis:** H62 uses public aggregate task IDs as runtime OLMES task IDs,
  but prior OLMES manifests used `::olmes`-qualified suite/task names. If the
  runtime registry does not accept the raw H62 IDs, the first GPU spend will
  fail before producing scientific signal.
- **Eigenquestion:** Can we produce a minimal fail-cheap alias preflight that
  resolves raw-vs-`::olmes` task IDs for H62 without running full checkpoint
  evaluation?
- **Discriminating test:** Generate a dry-run-only alias preflight sheet for
  all H62 tasks at the cheapest official checkpoint, including raw task IDs and
  `::olmes`-qualified candidates. The sheet must not mutate H62 full-run
  commands until a dry-run verdict exists.
- **Success criterion:** H62 is execution-ready only after a dry-run on the GPU
  host identifies an accepted alias form for every selected task. Before that,
  H62 remains the scientific frontier but not a run-ready command sheet.
- **Kill condition:** If the preflight silently rewrites task IDs without a
  dry-run receipt, treats public table IDs as proven runtime IDs, or launches a
  full run before alias resolution, it is invalid.
- **Scope:** Neural Hunt H62 runtime preflight; no GPU run and no science
  promotion.
- **Run(s):** `./venv/bin/python projects/neural_hunt/workspace/generate_h63_h62_alias_preflight.py`
- **Result:** H63 emitted a dry-run-only alias preflight sheet for H62:
  `16` selected tasks, `32` candidate runtime IDs (`16` raw public IDs and
  `16` `::olmes`-qualified IDs), using model `allenai/OLMo-2-0425-1B` at
  revision `stage1-step0-tokens0B`. Verdict:
  `alias_preflight_sheet_created_no_runtime_receipt`. H62 remains the
  scientific frontier, but it is not execution-ready until the GPU host dry-run
  identifies an accepted alias form for every selected task.
- **Status:** `closed / alias_preflight_created_no_runtime_receipt`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-34 — H62 public contrast must not be purely late-window selector artifact

- **Hypothesis:** H62 may preserve H59's median contrast only because public
  H20 range selection uses late-window or full-window movement. If the selected
  families have little early/mid public schema contrast, the official GPU route
  should expect a weaker heldout H62 gate and prioritize alias/runtime validation
  plus early-anchor calibration before full spend.
- **Eigenquestion:** In the frozen public H20 table, how much of H62's selected
  schema-gap range is already visible in the early/mid window
  (`step <= 1,200,000`) versus late checkpoints?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h64_h62_public_heldout_contrast_audit.py`
  over H20 and H62. For each selected family, compute full, early/mid, and late
  primary schema-gap ranges, then classify whether at least `6/8` families have
  early/mid range at least `0.5x` their full public range.
- **Success criterion:** If `>=6/8` H62 families clear the early/mid ratio bar,
  H62 remains a reasonable first official packet after alias preflight. If not,
  H62 remains runnable but should be treated as a late-selector stress packet
  until H62 early-anchor or another non-public source axis exists.
- **Kill condition:** If the audit treats public early/mid contrast as new
  evidence, or uses it to skip H62/H63/H62-gate runtime checks, it is invalid.
- **Scope:** Neural Hunt public-selector audit; no GPU run and no science
  promotion.
- **Run(s):** `./venv/bin/python projects/neural_hunt/workspace/run_h64_h62_public_heldout_contrast_audit.py`
- **Result:** Closed as `h62_public_h20_has_no_early_mid_rows`. For all `8`
  H62 families, H20 has `30` full/late public pairs and `0` early/mid pairs
  under the `step <= 1,200,000` rule. Therefore H20 cannot answer whether H62
  contrast survives in the heldout early/mid window. This does not weaken H62;
  it means H62 GPU rows are the first route to the heldout schema evidence,
  after H63 alias resolution.
- **Status:** `closed / public_h20_has_no_early_mid_rows`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-35 — Neural Hunt should be bounded-continue, not closed, after H50-H64

- **Hypothesis:** After H50-H64, Neural Hunt has exhausted no-GPU public
  aggregate shortcuts but has not exhausted the substrate: it now has a narrow,
  spend-bounded discriminator (H63 alias preflight -> H62 official rows -> H62
  schema gate) that can answer a live heldout schema question unavailable in
  H20. Therefore the right state is bounded-continue, not close.
- **Eigenquestion:** Does the remaining frontier have enough discriminating
  value per expected GPU spend to justify one more bounded tranche, or should
  the substrate be closed/frozen after yesterday's progress?
- **Discriminating test:** Run
  `projects/neural_hunt/workspace/run_h65_neural_hunt_retirement_audit.py` over
  the current graph/thesis/H62-H64 artifacts. Score continuation only if the
  next action is cheap/fail-closed, answers a question not answerable from
  existing public rows, has a predeclared closure gate, and has an explicit stop
  condition after one tranche.
- **Success criterion:** Continue only if all four conditions hold. Close/freeze
  if the frontier is only packet-design, public aggregate replay, unbounded GPU
  spend, or lacks a gate that can demote the route.
- **Kill condition:** If this audit uses "interesting" as a reason, ignores
  cost, or permits repeated GPU retries after alias/gate failure, it is invalid.
- **Scope:** Neural Hunt substrate decision; no GPU run and no science
  promotion.
- **Run(s):** `./venv/bin/python projects/neural_hunt/workspace/run_h65_neural_hunt_retirement_audit.py`
- **Result:** Verdict `bounded_continue_one_tranche`. All continuation checks
  pass: current frontier is fail-cheap H63 alias preflight; H62 asks a heldout
  schema question H20 cannot answer; H62 has a predeclared gate; law promotion
  remains forbidden; H62 is cost-bounded at `16` tasks x `10` official jobs.
  Recommendation: do not close yet, but authorize only H63 alias preflight and
  one H62 official tranche if aliases resolve. Freeze/close if aliases fail,
  H62 has zero accepted rows, or H62 heldout schema gate fails without exposing
  a concrete new state variable.
- **Status:** `closed / bounded_continue_one_tranche`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-36 — H62 aliases can be resolved from the OLMES registry without GPU dry-run

- **Hypothesis:** H63's runtime risk can be removed faster from the official
  OLMES task registry than by spending a GPU SSH slot on the dry-run sheet. If
  the registry contains canonical aliases for every H62 raw public task, H62
  can skip the alias-discovery dry-run and go directly to a heldout
  gate-minimum acquisition sheet.
- **Eigenquestion:** Can every frozen H62 raw base/`:mc` task be mapped to a
  canonical current OLMES runtime task ID from the official registry without
  changing the selected families?
- **Discriminating test:** Fetch/read the official OLMES task registry and task
  suite registry. Map H62 raw task IDs to canonical runtime IDs, preserving
  H62 family/schema membership. Generate alias-resolved H62 command sheets and
  patch the H62 schema gate so canonical aliases map back to the frozen H62
  raw task-family table before scoring.
- **Success criterion:** All `16` H62 tasks resolve; generated command sheets
  pass shell syntax; the H62 gate remains fail-closed with no outputs; the
  fastest next command sheet contains the `8` heldout checkpoints needed by
  the H62 schema gate.
- **Kill condition:** If any task resolves only by changing H62 families,
  dropping MedMCQA, changing checkpoint windows, or treating alias resolution
  as scientific evidence, the shortcut is invalid and H63 runtime dry-run
  remains required.
- **Scope:** Neural Hunt runtime/instrument resolution; no GPU run and no
  science promotion.
- **Run(s):** `./venv/bin/python projects/neural_hunt/workspace/run_h66_h62_registry_alias_resolution.py`;
  `./venv/bin/python projects/neural_hunt/workspace/run_h60_h59_checkpoint_schema_gate.py --packet h62`;
  `bash -n projects/neural_hunt/workspace/h62_diversity_capped_schema_official_alias_resolved_heldout_gate_min_commands_2026_05_11.sh`
- **Result:** Closed as
  `registry_resolved_aliases_h62_run_ready_for_heldout_minimum`. All `16` H62
  tasks resolve from the official OLMES registry. The important correction to
  H63 is that base tasks are `:rc::olmes`, not bare `::olmes`; MedMCQA uses
  `::none`. The H62 gate now maps canonical aliases back to the frozen H62 raw
  task table before scoring. The fastest next sheet is the heldout
  gate-minimum sheet with the eight official checkpoints needed for H62
  schema scoring.
- **Status:** `closed / registry_resolved_aliases_h62_run_ready_for_heldout_minimum`
- **Opened:** 2026-05-11 00:00:00 UTC
- **Closed:** 2026-05-11 00:00:00 UTC

#### H-NEURAL-HUNT-68 — Schema-state coordinates need residual-state evidence before architecture promotion

- **Hypothesis:** H67's low-dimensional H62 schema-coordinate trajectory is
  more than an evaluation-side log-step artifact only if cheap internal
  residual-state observables from the same OLMo checkpoints explain PC1/PC2
  beyond a log-step-only baseline. Without that bridge, schema-state remains a
  useful evaluation coordinate but not an architecture metric.
- **Eigenquestion:** Does OLMo internal residual geometry explain the H67
  schema-state coordinate well enough to make schema-state preservation a
  candidate objective for future architectures?
- **Discriminating test:** Freeze H67 PC1/PC2 targets from the ten H62
  official checkpoints. On the same OLMo2 1B checkpoint revisions and a fixed
  prompt packet, extract one cheap internal-state row per checkpoint:
  residual effective rank, cross-layer cosine flow, and cancellation/rotation
  proxies. Fit leave-one-checkpoint-out models for H67 PC1 and PC2 and compare
  against a log-step-only baseline.
- **Success criterion:** At least one predeclared internal-observable family
  improves leave-one-checkpoint-out MAE by `>=20%` over log-step-only on PC1
  or PC2, or materially reduces the late-checkpoint residuals, without
  model-name/provenance leakage or post-hoc feature selection.
- **Kill condition:** If log-step-only wins, if the feature packet is selected
  after seeing the PC residuals, or if the bridge relies on benchmark score
  labels rather than internal activations, H62/H67 remains an evaluation-side
  state-coordinate result only and must not be promoted as architecture
  evidence.
- **Scope:** Neural Hunt H68 bridge test; local target-freeze first, GPU only
  if residual extraction cannot be done from local/cached model access.
- **Run(s):** pending H68 target-freeze and residual-state extraction scaffold.
- **Result:** Pending.
- **Status:** `open / pre_registered_no_gpu`
- **Opened:** 2026-05-11 16:14:00 EDT
- **Closed:**

#### H-NEURAL-HUNT-69 — Request-surface mechanics must not explain away H62/H67

- **Hypothesis:** The exact H62 request payloads may expose a cheap false
  explanation for H67: the schema-coordinate could be driven by prompt-surface
  mechanics such as option-letter formatting, context length, continuation
  length, or lexical overlap rather than by learned checkpoint state. If so,
  H68 must treat request-surface features as controls before pursuing
  residual-state interpretation.
- **Eigenquestion:** Are the base-vs-`:mc` request-surface deltas constant
  across checkpoints and insufficient to explain the H67 PC1/PC2 loading map,
  or do they name a confound that must be controlled before any residual-state
  bridge?
- **Discriminating test:** Audit the archived H62 `*-requests.jsonl` payloads.
  For each checkpoint/family/schema, compute request count, mean context
  length, continuation length, option-marker density, and context-token
  Jaccard overlap. Pair base-vs-`:mc` deltas by family, measure whether the
  deltas vary across checkpoint, and correlate family-level deltas with H68
  PC1/PC2 loadings.
- **Success criterion:** If request-surface deltas are checkpoint-invariant and
  do not strongly track PC1/PC2 loadings, H67 is not explained away by the
  obvious prompt-surface controls. If they are checkpoint-invariant but track
  loadings, H68 may continue only with request-surface controls. If they vary
  across checkpoints, H67 must be reclassified as a request-pipeline artifact
  until the variation is explained.
- **Kill condition:** If the audit samples different documents per checkpoint,
  ignores missing request pairs, or treats weak `n=8` correlations as proof,
  it is invalid.
- **Scope:** Neural Hunt H69 local artifact audit; no model run and no
  architecture promotion.
- **Run(s):** `./venv/bin/python projects/neural_hunt/workspace/run_h69_h62_request_surface_audit.py`
- **Result:** Closed as `request_surface_not_sufficient_explanation`. The
  audit read `160` complete request files and `80` paired family/checkpoint
  rows. Base-vs-`:mc` request-surface deltas are exactly checkpoint-invariant
  across all paired rows (`max_surface_range_across_checkpoints = 0.0`), so
  they cannot by themselves explain within-family checkpoint flow. The
  strongest prompt-surface / PC-loading correlation is `0.420` on `n=8`
  families, too weak for explanation and useful only as a control in H68.
- **Status:** `closed / request_surface_not_sufficient_explanation`
- **Opened:** 2026-05-11 16:20:00 EDT
- **Closed:** 2026-05-11 16:23:00 EDT

#### H-NEURAL-HUNT-70 — Schema-state must not collapse to scalar checkpoint maturity

- **Hypothesis:** H67's schema PC1/PC2 coordinates may be a disguised scalar
  maturity/performance curve: mean base score, mean `:mc` score, mean schema
  gap, or gap dispersion. If scalar performance explains the frozen H68
  targets as well as the schema vector does, the residual-state bridge should
  target scalar training maturity rather than a schema-state coordinate.
- **Eigenquestion:** Do simple checkpoint-level scalar summaries predict H68
  PC1/PC2 as well as or better than the vector schema-coordinate framing?
- **Discriminating test:** Join the H62 measurement table with the frozen H68
  PC targets. For each checkpoint, compute mean base score, mean `:mc` score,
  mean all-score, mean gap, mean absolute gap, gap standard deviation, and gap
  sign balance. Compare leave-one-checkpoint-out linear predictors for PC1 and
  PC2 against log-step-only and log-step-plus-scalar controls.
- **Success criterion:** If no scalar summary materially beats log-step-only
  for PC1 or explains PC2 with positive leave-one-out improvement, H67 remains
  a vector schema-coordinate object. If one scalar predicts PC1/PC2 strongly,
  H68 must carry that scalar as a maturity control before claiming residual
  state evidence.
- **Kill condition:** If the audit uses family-level loadings as checkpoint
  predictors, leaks PC targets into feature selection, or treats `n=10`
  correlations as universal law, it is invalid.
- **Scope:** Neural Hunt H70 local scalar-confound audit; no model run and no
  architecture promotion.
- **Run(s):** `./venv/bin/python projects/neural_hunt/workspace/run_h70_h62_scalar_maturity_audit.py`
- **Result:** Closed as `scalar_maturity_control_required`. On the ten frozen
  H68 checkpoint targets, log-step remains the best PC1 predictor
  (`0.653` leave-one-out relative improvement), while mean schema gap is close
  (`0.619`) but does not beat log-step. PC2 is not explained by scalar-only
  features, but `log_step + schema_gap_range` gives positive PC2 improvement
  (`0.133`) versus log-step alone (`-0.855`). H67 therefore does not collapse
  to scalar maturity, but H68 must control for log-step, mean schema gap, and
  schema-gap range before interpreting residual-state features.
- **Status:** `closed / scalar_maturity_control_required`
- **Opened:** 2026-05-11 16:28:00 EDT
- **Closed:** 2026-05-11 16:31:00 EDT

#### H-NEURAL-HUNT-71 — Controlled residual map should name the activation target

- **Hypothesis:** After H69/H70 controls, the useful residual is not the
  existence of H67 PCA coordinates but the checkpoint-family cells that remain
  unexplained by log-step, mean schema gap, schema-gap range, and prompt
  surface. If those cells concentrate in a small PC2 splitter band, H68 can
  sample activations surgically rather than loading every prompt/checkpoint
  indiscriminately.
- **Eigenquestion:** Which checkpoint-family cells explain the controlled PC2
  residual after scalar maturity controls, and do they name a fixed prompt
  packet for the residual-state bridge?
- **Discriminating test:** Recompute the H67 signed-sqrt standardized family
  gap matrix. For each family, fit leave-one-checkpoint-out linear controls
  over `log10_step_plus1`, `mean_schema_gap`, and `schema_gap_range`. Project
  controlled family residuals through frozen PC2 loadings, rank cells by
  absolute PC2 residual contribution, and report checkpoint/family bands.
- **Success criterion:** If the top controlled residual cells concentrate in
  the PC2 splitter families/checkpoints, H68 should extract activations first
  from that band. If residuals diffuse evenly, H68 should use the full
  checkpoint/family packet or demote PC2 as too noisy.
- **Kill condition:** If the audit refits PCA after seeing controls, uses
  non-frozen loadings, or lets target family leakage define the controls, it is
  invalid.
- **Scope:** Neural Hunt H71 residual/reframe local audit; no model run and no
  architecture promotion.
- **Run(s):** `./venv/bin/python projects/neural_hunt/workspace/run_h71_h62_controlled_residual_map.py`
- **Result:** Closed as
  `controlled_pc2_residual_concentrated_activation_band_named`. The audit
  scored `80` checkpoint-family cells after controls
  (`log10_step_plus1`, `mean_schema_gap`, `schema_gap_range`) using frozen H68
  loadings. Top-8 cells carry `0.438` of absolute PC2 residual contribution.
  Family PC2 residual mass concentrates in
  `mmlu_college_computer_science`, `mmlu_professional_medicine`, and
  `medmcqa`; checkpoint mass concentrates at `0`, `400000`, and `10000`.
  H68 activation extraction should start with this band rather than the full
  packet.
- **Status:** `closed / controlled_pc2_residual_concentrated_activation_band_named`
- **Opened:** 2026-05-11 16:38:00 EDT
- **Closed:** 2026-05-11 16:42:00 EDT

#### H-NEURAL-HUNT-72 — Activation prompt packet should be residual-targeted, not broad

- **Hypothesis:** If H71 names a concentrated controlled PC2 residual band,
  the first H68 residual-state extraction should use exact archived prompts
  from that band rather than the full H62 prompt space. This reduces GPU/time
  cost while preserving the discriminating residual.
- **Eigenquestion:** Can the archived H62 requests be converted into a fixed
  activation prompt packet covering H71's top residual families/checkpoints
  and both schemas?
- **Discriminating test:** Read H71 top residual cells and H62 archived
  `*-requests.jsonl` payloads. Emit a fixed JSONL packet with bounded examples
  per `(checkpoint, family, schema)`, preserving exact context/continuation,
  doc id, schema, family, and H71 residual metadata.
- **Success criterion:** Packet contains both base and `:mc` schemas for every
  selected top family/checkpoint band, has deterministic row order, and is
  small enough for activation extraction without re-running OLMES.
- **Kill condition:** If the packet samples prompts not present in the archived
  GPU request files, omits schema pairs, or samples after seeing activation
  outputs, it is invalid.
- **Scope:** Neural Hunt H72 prompt-packet construction; no model run and no
  architecture promotion.
- **Run(s):** `./venv/bin/python projects/neural_hunt/workspace/build_h72_h68_activation_prompt_packet.py`
- **Result:** Closed as `activation_prompt_packet_created`. The packet
  contains `216` exact archived request rows: `3` H71 residual-heavy families
  (`mmlu_college_computer_science`, `mmlu_professional_medicine`, `medmcqa`)
  x `3` checkpoints (`0`, `400000`, `10000`) x `2` schemas x `12` examples.
  Every selected `(checkpoint, family)` has both base and `:mc` rows.
- **Status:** `closed / activation_prompt_packet_created`
- **Opened:** 2026-05-11 16:43:00 EDT
- **Closed:** 2026-05-11 16:45:00 EDT

#### H-XDOMAIN-5AV — Operator-supervisor discriminator moves are recoverable as reusable artifacts

- **Hypothesis:** The decisive manual/Codex moves in the recent `gp163d` gravity and NS Millennium loops fall into a small set of recoverable discriminator templates, so ZTARE can mechanize post-positive "what should we test next?" selection as structured queue artifacts rather than leaving it in chat.
- **Scope:** Cross-domain ZTARE methodology; `gp163d_unified_accel`; `ns_millennium_hunt`; GP-119 Inverter; GP-188 primitive-compilation boundary; GP-190 post-run discriminator daemon.
- **Status:** `falsified_for_first_derivative_bound / second_order_or_admissibility_gap_open`
- **Discriminating test:** Run GP-190 Phase A as a retrospective extraction over closed artifacts only. Build `next_discriminator_queue.replay.jsonl` rows for the decisive moves in the `gp163d` and NS sequences, then classify them by narrative-shortcut template and discriminator class. Success = at least 80% of key moves map to six or fewer templates, and each mapped template names a runnable or artifact-backed discriminator. Failure = the decisive moves depend on unrecorded chat intuition, domain-specific expert judgment not present in artifacts, or a template set too fragmented to compile.
- **Run(s):** pending `GP-190 Phase A`
- **Result:** Pending.
- **Opened:** 2026-04-30 10:55:30 EDT
- **Closed:** 

#### H-NS-5AA — Time-rate reset tax is already visible in the Phase 5i strobe

- **Hypothesis:** In the poison_1e2 late-window strobe, the post-danger reset phase shows a rising pointwise viscous tax proxy relative to local stretching production, indicating that the proposed `mu * r^2 / T(E)` liquidation mechanism is physically activating rather than merely a formal accounting cage.
- **Scope:** NS Millennium Hunt, Phase 5i/5x offline artifacts, ZTARE proof-spine seam
- **Status:** `falsified`
- **Discriminating test:** Run `phase5aa_time_rate_tax_audit.py` on existing Phase 5i raw strobe artifacts only. For each leader-frame, compute pointwise stretching production proxy `P = max(omega_hat · S omega_hat, 0) * |omega|^2`, pointwise viscous enstrophy proxy `D = max(-nu * omega · Delta omega, 0)`, and normalized rate proxy `(nu * |Delta omega| / |omega|) / max(omega_hat · S omega_hat, eps)`. Success = after the `[1,I2,pos]` danger frame, at least one reset frame has `D/P > 1` or the normalized rate proxy crosses above 1. Failure = reset remains below both thresholds through the available strobe.
- **Run(s):** `phase5aa_time_rate_tax_audit.py`
- **Result:** `falsified`. `phase5aa_time_rate_tax_audit.py` found no pointwise crossing in the sampled reset: max reset point tax ratio `0.0745`, max normalized rate ratio `0.0754`, with no crossing times. The reset is visibly high-gradient and locally dissipative, but the existing artifact does not show observed bankruptcy. The strict stretch-cost margin remains an asymptotic theorem target, not an empirical fact from Phase 5i.
- **Opened:** 2026-04-29 23:18:00 EDT
- **Closed:** 2026-04-29 23:23:00 EDT

#### H-NS-5AD — Phase scrambling is coherent tax evasion rather than dissipative churn

- **Hypothesis:** The noisy late-window Index-2 / Index-1 switching in the Phase 5i poison trace is better explained as coherent vorticity-strain phase scrambling that preserves peak intensity than as thermodynamic churn that rapidly burns energy through viscous reset.
- **Scope:** NS Millennium Hunt, Phase 5i/5aa/5ac offline artifacts, recurrence/fractal-rival seam
- **Status:** `partially_confirmed`
- **Discriminating test:** Run `phase5ad_phase_scramble_audit.py` on existing Phase 5i strobe telemetry only. Measure peak-retention after Index-2 frames, sign/variance of `chi`, alignment-state entropy, identity step jumps, component-count flicker, and whether the observed reset has already crossed the Phase 5aa viscous-tax threshold. Support = peak retention remains high after Index-2 episodes, component/alignment states flicker, and viscous-tax crossing remains absent. Rejection = Index-2 exits are followed by rapid peak collapse or dominant negative-production burn consistent with dissipative churn.
- **Run(s):** `phase5ad_phase_scramble_audit.py`
- **Result:** `partially_confirmed`. The audit classifies the observed strobe as `coherent_phase_scramble_supported_with_identity_risk`: Index-2 exits preserve most peak intensity (`min` next-two same-track retention `0.914`), final mean peak retention is `0.894`, positive chi budget exceeds negative budget by `1.99x`, state entropy is high (`3.38` bits), and Phase 5aa tax ratios remain below crossing (`0.0745` point tax, `0.0754` normalized). The caveat is serious: `3` large identity jumps over `1` rad mean the trace does not prove stable Lagrangian identity or continuum tax evasion.
- **Opened:** 2026-04-29 23:57:21 EDT
- **Closed:** 2026-04-29 23:59:00 EDT

#### H-NS-5AE — Large identity jumps carry a visible transaction fee

- **Hypothesis:** The `>1` rad identity jumps detected in Phase 5AD are not clean tax-free handoffs; they coincide with a visible transaction fee in the available telemetry, expressed as negative `chi`, elevated Laplacian/dissipative proxy, or reduced peak retention at the jump frame.
- **Scope:** NS Millennium Hunt, Phase 5i/5aa/5ad offline artifacts, phase-scrambling bridge
- **Status:** `falsified`
- **Discriminating test:** Run `phase5ae_jump_transaction_cost_audit.py` on existing Phase 5i and Phase 5aa artifacts. Isolate all track frames with `step_distance > 1` rad and compare their `chi`, peak retention, component/identity switch status, and any available Phase 5aa leader-frame Laplacian/tax proxies against non-jump frames. Support = jump frames are enriched for negative `chi`, lower retention, or elevated dissipative/tax proxies. Rejection = jumps preserve peak intensity and do not show elevated burn/tax signatures.
- **Run(s):** `phase5ae_jump_transaction_cost_audit.py`
- **Result:** `falsified`. The observed `>1` rad jumps look cleaner than the non-jump baseline in the available telemetry: jump mean `chi=+0.0978` vs non-jump `+0.0269`, jump negative-chi fraction equals non-jump (`0.333`), jump next-retention is `1.004`, jump mean Laplacian norm is lower than non-jump (`3.74e6` vs `4.54e6`), jump mean point-tax ratio is not elevated (`0.07452` vs `0.07465`), and jump mean dissipative proxy is lower (`2.10e5` vs `2.59e5`). Caveat: only `2` jump frames have leader-tax proxies, so this supports a clean-handoff read but does not prove continuum losslessness.
- **Opened:** 2026-04-30 00:03:36 EDT
- **Closed:** 2026-04-30 00:05:00 EDT

#### H-NS-5AF — Large jumps re-enter a small orientation set rather than exploring fresh frames

- **Hypothesis:** The Phase 5i `>1` rad identity jumps are not an unlimited clean-frame relay; they ping-pong among a small set of reused strain-alignment orientations, implying a future topological re-entry penalty rather than indefinite tax-free exploration.
- **Scope:** NS Millennium Hunt, Phase 5i/5ad/5ae offline artifacts, eigenframe re-entry penalty seam
- **Status:** `partially_confirmed`
- **Discriminating test:** Run `phase5af_orientation_reentry_audit.py` on existing Phase 5i strobe telemetry. Isolate jump frames (`step_distance > 1` rad), compare their alignment-cosine vectors and component states, compute pairwise orientation distances, nearest-neighbor reuse, and whether jump directions alternate between a small set of frames. Support = jump orientations cluster/re-enter with small nearest-neighbor distances or alternating track/frame pattern. Rejection = jump orientations continue rolling into distinct, non-reused orientation vectors.
- **Run(s):** `phase5af_orientation_reentry_audit.py`
- **Result:** `partially_confirmed`. The three `>1` rad jumps do not roll into unrelated fresh orientations. Mean jump-pair alignment distance is `0.323`, minimum jump-pair distance is `0.164`, max jump-pair cosine similarity is `0.9865`, mean nearest-orientation distance is `0.139`, and all `3/3` jump frames have nearest orientation reuse below `0.35`. Caveat: only `3` jump frames are available, so this shows re-entry is already visible in the finite strobe but does not prove a finite orientation-capacity theorem.
- **Opened:** 2026-04-30 00:08:00 EDT
- **Closed:** 2026-04-30 00:09:00 EDT

#### H-NS-5AG — Re-entry targets are already dirty before enstrophy lands

- **Hypothesis:** The orientation neighborhoods re-entered by the Phase 5i `>1` rad jumps are already carrying residual Eulerian debt immediately before the landing, visible as above-background strain, vorticity-Laplacian, strain-Laplacian, or negative-production signatures in the raw component tensors.
- **Scope:** NS Millennium Hunt, Phase 5i raw component tensors, topological-gridlock seam
- **Status:** `partially_confirmed`
- **Discriminating test:** Run `phase5ag_dirty_target_frame_audit.py` on `phase5i_strobe_raw_component_timeseries.json`. For each Phase 5AF jump, take the landing orientation vector and find the closest `95%` component orientation in the immediately prior frame. Compare the matched target component's `strain_frobenius`, `rotation_frobenius`, `laplacian_omega_norm`, `laplacian_strain_frobenius`, and `chi` to the same-frame component distribution. Support = matched targets are above same-frame median debt on most derivative metrics or show negative `chi`; rejection = matched targets are clean/low-derivative relative to same-frame components.
- **Run(s):** `phase5ag_dirty_target_frame_audit.py`
- **Result:** `partially_confirmed`. The audit found `2/3` jump target neighborhoods dirty by the same-frame raw-tensor rule, with mean orientation distance to the prior target `0.145` and mean dirty votes `2.33/5`. The `t=1.90` landing re-entered a prior negative-chi target with above-median strain, rotation, and strain-Laplacian debt (`4/5` votes). The `t=2.00` landing re-entered a target with median/above-median strain, rotation, and strain-Laplacian debt (`3/5`). The `t=1.95` landing target was clean by this rule (`0/5`), so the gridlock premise is supported but not universal in the finite strobe.
- **Opened:** 2026-04-30 00:08:51 EDT
- **Closed:** 2026-04-30 00:11:00 EDT

#### H-NS-5AH — Non-leader component halo accumulates off-balance-sheet debt

- **Hypothesis:** Even though Phase 5i does not save full-box enstrophy, the saved raw `95%` component tensors should show the same signature if topological-gridlock is real: non-leader components outside the two tracked peaks accumulate a growing halo of peak-enstrophy and derivative debt after the large identity jumps.
- **Scope:** NS Millennium Hunt, Phase 5i raw component tensors, overfit red-team / global-garbage-dump proxy
- **Status:** `confirmed`
- **Discriminating test:** Run `phase5ah_component_halo_debt_audit.py` on `phase5i_strobe_raw_component_timeseries.json`. For each strobe frame, compute component count, total component peak-enstrophy proxy, top-2 proxy, nonleader halo proxy, halo share, and derivative-debt proxies (`strain_frobenius`, `rotation_frobenius`, vorticity-Laplacian, strain-Laplacian) outside the top two components. Support = nonleader halo count/share or derivative debt rises after the jump window (`t>=1.90`) relative to pre-jump frames. Rejection = nonleader halo stays flat/low while only leader peaks grow.
- **Run(s):** `phase5ah_component_halo_debt_audit.py`
- **Result:** `confirmed` on the saved component-halo proxy. Phase 5i did not save full-box vorticity fields, so this is not a global enstrophy integral. Within the saved raw `95%` component tensors, post-jump halo debt rises sharply: halo count `4.53x`, halo peak-enstrophy proxy `6.15x`, halo share `1.90x`, halo negative-chi magnitude `40.1x`, halo mean vorticity-Laplacian `1.54x`, and halo mean strain-Laplacian `1.35x` relative to the pre-jump window.

#### H-NS-5AR — Same-scale annular sheath can cancel the active-core pressure angular moment

- **Hypothesis:** The angular-moment pressure bridge is not forced by active local torque alone. A divergence-free same-scale annular sheath, constructed to have negligible first-jet effect at the core, can tune the projected Riesz angular moment through zero while the core `tau = omega x S omega` remains active.
- **Scope:** NS Millennium Hunt, local Fourier/Riesz pressure bridge, Phase 5AQ successor
- **Status:** `closed / partially_confirmed`
- **Discriminating test:** Run `phase5ar_angular_moment_ansatz_audit.py` in a periodic local spectral sandbox. Construct a localized active core velocity, project it divergence-free, then add a divergence-free annular sheath generated from a vector potential with tunable amplitude and angular lobe. For each amplitude, compute core `tau`, `Lambda=|S|^2-|omega|^2/2`, pressure Hessian via the spectral Riesz multiplier, and the projected pressure moment `e_tau^T Hess(p)(0) e_tau`. Support = the pressure projection changes sign while `|tau|` and first-jet metrics remain within a fixed tolerance. Rejection = the projection cannot be tuned through zero without materially destroying active core torque.
- **Opened:** 2026-04-30 09:03:00 EDT
- **Closed:** 2026-04-30 09:15:00 EDT
- **Run(s):** `phase5ar_angular_moment_ansatz_audit.py`, hostile-review extension `phase5as_full_jet_ansatz_audit.py`
- **Result:** `partially_confirmed`. Phase 5AR found no exact moving-axis stealth but produced a same-scale divergence-free annular perturbation that reduced the moving-axis pressure projection to `0.00697x` of the core value while increasing local torque `21.97x`. The hostile-review Phase 5AS extension gave the Rival an overcomplete incompressible local-jet family (`curl(A)`, quartic polynomial vector potential plus annular modes, `735` coefficients per candidate; velocity jet dimensions through degrees `1..4` = `8/23/47/82`) and found exact fixed-axis cancellation (`9.9e-16x`) plus near moving-axis cancellation (`0.01117x`) while torque remained `16.73x` above the core. This does not prove exact stealth exists, but it falsifies the standalone claim that active local torque forces robust pressure-footprint dominance.

#### H-NS-5AT — Near-stealth angular-moment snapshots are dynamically repelled by the NS vector field

- **Hypothesis:** The Phase 5AS near-stealth full-jet field is a static overfit: when evolved by the unforced incompressible Navier-Stokes vector field, the instantaneous derivative of the moving-axis pressure projection points away from the near-zero cancellation manifold on an advective timescale while torque remains active.
- **Scope:** NS Millennium Hunt, dynamic admissibility pivot after Phase 5AS
- **Status:** `confirmed_for_sample / theorem_gap_remains`
- **Discriminating test:** Rebuild the exact Phase 5AS best field (candidate `107`, root amplitude `-0.11735195918487866`) deterministically from its seed. Compute `du/dt = -P_Leray((u·grad)u) + nu Delta u` on the same periodic spectral grid for `nu in {0, 1e-4, 1e-3, 1e-2}`. Estimate directional derivatives of moving-axis pressure projection, fixed-axis pressure projection, and `|tau|` by centered finite differences along `du/dt`. Support = moving-axis projection growth rate is large relative to current near-zero residual and exposes the pressure footprint on a timescale shorter than or comparable to the local advective time. Rejection = the NS vector field is tangent to the near-stealth manifold (`qdot` small relative to residual) while torque remains active.
- **Opened:** 2026-04-30 09:21:00 EDT
- **Run(s):** `phase5at_dynamic_admissibility_audit.py`
- **Result:** The Phase 5AS near-stealth snapshot is not tangent to the NS vector field. The rebuilt state has moving-axis projection `0.0231659`, exact fixed-axis projection `2.05e-15`, and torque `1.51839` (`16.73x` the core). Under the inviscid vector field (`nu=0`), `moving_projection_dot=19.8851`, giving exposure time `0.001165`, far shorter than the local advective proxy `1/|tau|=0.6586`; finite-difference sensitivity over `3e-5/1e-4/3e-4` probe factors is stable. The same qualitative result holds for `nu=1e-4`, `1e-3`, and `1e-2` with exposure times `0.00119`, `0.00144`, and `0.00129`. This supports the dynamic-admissibility pivot: the static cloak exists as an instantaneous overfit, but the tested NS vector field rapidly exposes it. It is not yet a theorem; the remaining burden is a uniform transversality lower bound over dynamically admissible near-stealth reset trajectories.
- **Closed:** 2026-04-30 09:27:00 EDT

#### H-NS-5AU — Dynamic repulsion is generic across near-stealth full-jet candidates

- **Hypothesis:** The Phase 5AT dynamic repulsion is not a one-candidate artifact. Across the top near-stealth full-jet candidates from the same overcomplete incompressible ansatz class, the inviscid NS vector field generically has a large moving-axis pressure-projection derivative, with exposure time far shorter than `1/|tau|`. The dominant contribution should come from differential advection/Leray pressure rather than viscosity.
- **Scope:** NS Millennium Hunt, dynamic admissibility ensemble after Phase 5AT
- **Status:** `confirmed_for_ensemble / theorem_gap_remains`
- **Discriminating test:** Rebuild the Phase 5AS full-jet candidate pool deterministically, select the top near-stealth roots by moving-axis projection ratio, and evaluate directional derivatives for `du/dt` under inviscid Leray-projected advection, viscosity-only `Delta u`, and their sums at `nu=1e-3` and `1e-2`. Support = most top candidates have exposure times at least `100x` shorter than `1/|tau|`, and inviscid advection explains the majority of `|qdot|`. Rejection = many top candidates are dynamically tangent (`exposure / turnover >= O(1)`) or only viscosity exposes them.
- **Opened:** 2026-04-30 09:32:00 EDT
- **Run(s):** `phase5au_dynamic_ensemble_audit.py`
- **Result:** `confirmed_for_ensemble`. Rebuilt `429` active full-jet roots (`tau` above core) and evaluated the top `20` near-stealth candidates. All top candidates expose under inviscid Leray-projected advection much faster than turnover: median exposure/turnover `0.00161`, maximum `0.0153`, minimum `|qdot_adv|=10.46`, median `|qdot_adv|=83.61`. At `nu=1e-3`, the median viscous contribution is only `3.84%` of the inviscid advective contribution (max `19.1%`); at `nu=1e-2`, viscosity becomes comparable in some candidates but is not needed for exposure. This supports the saddle-point/dynamic-admissibility route at the sample-ensemble level. It still does not prove a universal commutator lower bound; the theorem burden is now to prove that dynamically admissible near-stealth reset states cannot tune the material derivative of the signed `l=2` pressure angular moment to zero.
- **Closed:** 2026-04-30 09:39:00 EDT

#### H-NS-5AV — Two-mode full-jet search cannot tune both pressure stealth and inviscid material tangency

- **Hypothesis:** In the overcomplete local incompressible full-jet ansatz class, adding a second independent full-jet perturbation still cannot tune both the moving-axis pressure projection `q` and its inviscid NS material derivative `Dq/Dt` near zero while preserving active torque. If this fails, the dynamic-transversality theorem is not yet decisive and must move to higher-order material derivatives or an admissibility constraint.
- **Scope:** NS Millennium Hunt, direct hostile search against the dynamic-transversality target
- **Status:** `not_supported_in_local_neighborhood / retuning_cost_unproven`
- **Discriminating test:** Rebuild a deterministic pool of normalized full-jet perturbations. Use `scipy.optimize.least_squares` over two amplitudes `(a,b)` for selected perturbation pairs, minimizing normalized `(q, Dq/Dt)` where `q` is the moving-axis projected pressure moment and `Dq/Dt` is its inviscid Leray-advection directional derivative. Support = no optimized pair with `|q|/|q_core| < 1e-2`, `|Dq/Dt| < 1`, and `tau_ratio > 1`. Rejection = such a dynamically tangent stealth pair is found.
- **Opened:** 2026-04-30 09:44:00 EDT
- **Run(s):** `phase5av_two_mode_dynamic_stealth_search.py` (local CPU attempt stopped for runtime), `phase5av_gpu_torch_screen.py`, `phase5av_gpu_refine_pair.py`, `phase5av_gpu_validate_candidate.py`
- **Result:** `falsified` for the first-derivative dynamic-transversality claim. The broad GPU screen tested `18,750` two-mode full-jet samples on A100 and found no strict tangent but one near tangent. Targeted refinement around pair `[1,18]` found `24` strict candidates. Best refined candidate: amplitudes `[0.1393333, 0.1945]`, `q_ratio=3.12e-4`, `|Dq/Dt|=0.0103`, `tau_ratio=135.29`. Double-precision validation of the same generated field confirmed `q_ratio=3.1098e-4`, `|Dq/Dt|=0.00869–0.00940` across finite-difference factors `3e-5..1e-3`, and `tau_ratio=135.29`. Therefore a rich local incompressible ansatz can tune both the moving-axis pressure footprint and its inviscid material derivative near zero while preserving very active torque. The theorem target must move to either second material derivative (`D^2q/Dt^2`) repulsion, finite-time retuning cost, or a stronger NS trajectory admissibility constraint.
- **Closed:** 2026-04-30 09:58:00 EDT

#### H-NS-5AW — Dynamic cloak tangency carries a high-curvature viscous debt

- **Hypothesis:** The Phase 5AV two-mode cloak can tune `q≈0` and `Dq/Dt≈0`, but it pays by injecting high-frequency curvature. Relative to nearby active states, the cloak should exhibit a much larger viscous tax proxy (`||Delta u||²` and/or enstrophy dissipation proxy) per unit enstrophy-production proxy. If not, the “retuning cost” route is also unsupported.
- **Scope:** NS Millennium Hunt, post-Phase 5AV debt audit
- **Status:** `not_supported_in_local_neighborhood / retuning_cost_unproven`
- **Discriminating test:** On the GPU-generated pair `[1,18]`, evaluate the refined strict cloak and a local grid neighborhood around it. For each state compute `q_ratio`, `|Dq/Dt|`, `tau_ratio`, velocity-gradient norm, Laplacian norm, positive enstrophy-production proxy, and tax/gain ratios. Support = tangent/near-tangent states have materially higher curvature/tax ratios than comparable active non-tangent states. Rejection = tangent states are not more curved or not more taxed than the surrounding active population.
- **Opened:** 2026-04-30 10:04:00 EDT
- **Run(s):** `phase5aw_cloak_debt_audit.py` (CPU attempt stopped for runtime), `phase5aw_gpu_cloak_debt_audit.py`
- **Result:** `not_supported` on the local pair-neighborhood audit. GPU scan evaluated `6561` states around the validated cloak, with `15` strict cloaks, `454` near cloaks, and `6107` active non-cloaks. Strict cloaks did not show a material viscous-tax premium over active non-cloaks: median `||Delta u||² / positive_prod` was `558.24` for strict cloaks vs `546.81` for active non-cloaks; median `||Delta omega||² / positive_prod` was `245019.9` vs `240283.1`. Strict cloaks also had lower median positive production (`4.44` vs `4.65`) and lower median `||grad u||²` (`7.63` vs `7.86`). This does not prove cloaks are free in true NS trajectories, but it rejects the local claim that the two-mode cloak visibly burns itself via high curvature.
- **Closed:** 2026-04-30 10:10:00 EDT

#### H-NS-5AX — Dynamic cloak cannot track the stealth manifold under unforced NS evolution

- **Hypothesis:** The Phase 5AV validated cloak is an instantaneous/tangent snapshot, not a finite-time NS trajectory. When evolved under the unforced incompressible Navier-Stokes vector field with pressure enforced by the global Leray projection, `q≈0` and `Dq/Dt≈0` will fail quickly without external coefficient retuning.
- **Scope:** NS Millennium Hunt, trajectory-admissibility test after Phase 5AV/5AW
- **Status:** `confirmed_for_validated_cloak / finite_time_exposure`
- **Discriminating test:** On the A100 host, rebuild the validated pair `[1,18]` cloak at amplitudes `[0.1393333, 0.1945]`. Integrate `u_t = -P_Leray((u·grad)u) + nu Delta u` on the periodic spectral grid for `nu in {0, 1e-3}` using a short RK4 or stabilized Euler trajectory. Track `q_ratio`, `|Dq/Dt|`, `tau_ratio`, and positive production. Support = `q_ratio` exits the strict cloak threshold (`1e-2`) on a short fraction of turnover time without retuning. Rejection = the trajectory remains strict-cloaked over a nontrivial dwell interval while torque stays active.
- **Opened:** 2026-04-30 10:16:00 EDT
- **Run(s):** `phase5ax_trajectory_persistence_audit.py` on H100 host `209.20.158.17`, after validating exact reproduction with `phase5av_gpu_validate_candidate.py`
- **Result:** `confirmed_for_validated_cloak`. The H100 first reproduced the Phase 5AV validated cloak exactly: float64-cast `q_ratio=0.000310978`, `|Dq/Dt|≈0.00869`, `tau_ratio=135.2928`. The trajectory audit then evolved that same field under unforced Leray-projected NS. For both `nu=0` and `nu=1e-3`, the cloak exited the strict `q_ratio < 1e-2` threshold at step `64`, time `0.00304433`, without retuning. Final `q_ratio` at step `80` was `0.0154773` (`nu=0`) and `0.0157428` (`nu=1e-3`). Torque remained active and slightly increased (`tau_ratio` from `135.29` to `144.51`/`143.98`), while positive production stayed near `4.4`. This supports finite-time exposure of the validated dynamic cloak under the actual NS vector field. Scope caveat: this is a fixed-grid/intensity trajectory test, not a true epsilon-resolved cascade.
- **Closed:** 2026-04-30 12:34:00 EDT

#### H-NS-5AY — Pointwise Riesz-Hessian L2 compatibility is coercive enough to exclude the cloak

- **Hypothesis:** Gemini Pro's Phase 5AX "Riesz-Hessian Compatibility Tensor" route is decisive: prescribing the trace-free pressure Hessian required by the Phase 5AV cloak should require a nontrivial or divergent global `L2` source norm under `D²p = R_i R_j F`, so a finite-energy global extension cannot freely realize the local Taylor-jet cloak.
- **Scope:** NS Millennium Hunt, post-Gemini Phase 5AX route audit
- **Status:** `falsified_for_plain_L2_coercivity / scale_sensitive_constraint_needed`
- **Discriminating test:** Before building a GPU trajectory integrator, test the functional-analytic premise directly. Construct a compactly supported signed source template `F` whose pointwise Riesz-Hessian projection at the origin is nonzero. Rescale it as `F_epsilon(x)=a F(x/epsilon)` with `a` chosen so the origin Hessian/projection stays fixed. Measure/derive how `||F_epsilon||_2` scales as `epsilon -> 0`. Support = fixed pointwise Hessian requires nondecreasing/divergent `L2` norm. Rejection = the same pointwise Hessian can be preserved while `L2` norm decreases to zero, making the proposed L2-coercive compatibility test ill-posed.
- **Success criterion:** If `||F_epsilon||_2` scales like `epsilon^(3/2)` (or otherwise tends to zero) while the pointwise Riesz-Hessian stays fixed, close this route as false and do not spend GPU or API budget on the compatibility-minimization test.
- **Opened:** 2026-04-30 12:17:00 EDT
- **Run(s):** `phase5ay_riesz_hessian_l2_scaling_audit.py`
- **Result:** `falsified_for_plain_L2_coercivity`. The audit constructed an annular signed source with nonzero `zz` trace-free Riesz-Hessian projection at the origin (`h0=7.0903677`). Rescaling `F_epsilon(x)=a F0(x/epsilon)` while holding the origin Hessian fixed gives `||F_epsilon||_2 = epsilon^(3/2) ||aF0||_2`; the concrete rows drop from `0.3062459` at `epsilon=1` to `0.0016918` at `epsilon=0.03125` while the pointwise Hessian remains `1`. Therefore a prescribed pointwise pressure-Hessian value does not impose a positive global `L2` lower bound by itself. Gemini's proposed minimum-`L2` compatibility test is not decisive unless strengthened with support-scale, jet-extension, Morrey/Campanato, or finite-thickness constraints.
- **Closed:** 2026-04-30 12:18:00 EDT

#### H-NS-5AZ — NS-critical scaling reverses the 5AY arbitrary-source L2 evasion

- **Hypothesis:** The 5AY plain-`L2` rejection is a correct functional-analysis statement but not a Navier-Stokes admissibility statement. If the source `F=|S|²-|Ω|²` is tied to a shrinking NS-critical blowup profile (`x~epsilon`, `u~epsilon^-1`, `∇u~epsilon^-2`, so `F~epsilon^-4`), then the source `L2` norm grows like `epsilon^-5/2` while the Riesz-Hessian pointwise footprint grows like `epsilon^-4`. The arbitrary-source trick of shrinking support at fixed amplitude is not dynamically admissible for a finite-time cascade.
- **Scope:** NS Millennium Hunt, correction to Phase 5AY after adversarial de-anchoring
- **Status:** `confirmed_for_scaling_correction / dimensionless_cancellation_target_open`
- **Discriminating test:** Reuse the Phase 5AY annular source template, but compare two scalings: (a) arbitrary fixed-amplitude scaling, where pointwise Hessian is held fixed and `||F||_2 ~ epsilon^(3/2)`; (b) NS-critical amplitude scaling, where amplitude `a(epsilon)=epsilon^-4`, `||F||_2 ~ epsilon^-5/2`, and pointwise Hessian grows as `epsilon^-4`. Support = the corrected NS-critical rows reverse the 5AY "vanishing L2" conclusion. Rejection = even with NS-critical amplitude, the relevant source norm does not grow or the scaling object is still disconnected from the cloak's dimensionless pressure/gain ratio.
- **Success criterion:** Produce a table and closed-form exponents for `||F||_2`, pointwise Hessian, and their ratio under both arbitrary-source and NS-critical scaling. If the NS-critical `L2` exponent is negative (`-5/2`), record 5AY as scoped, not as a route-kill.
- **Opened:** 2026-04-30 12:24:00 EDT
- **Run(s):** `phase5az_ns_critical_riesz_scaling_audit.py`
- **Result:** `confirmed_for_scaling_correction`. The same template constants from 5AY (`h0=7.0903677`, `||F0||_2=2.1713963`) give two opposite ledgers. Arbitrary fixed-Hessian scaling keeps pointwise Hessian `1` and drives `L2` down (`0.3062459 -> 0.0016918`). NS-critical scaling sets source amplitude `epsilon^-4`, so pointwise Hessian grows as `epsilon^-4` and source `L2` grows as `epsilon^-5/2`: at `epsilon=0.03125`, Hessian is `7.434789e6` and `L2=12578.07`. Therefore 5AY is not a route-killer for Navier-Stokes; it only rejects arbitrary fixed-amplitude source coercivity. The live target is dimensionless pressure-footprint cancellation under finite-thickness NS-critical scaling and actual trajectory evolution.
- **Closed:** 2026-04-30 12:25:00 EDT

#### H-NS-5BA — Leray vector field has a first-order normal rejection from the stealth manifold

- **Hypothesis:** Gemini Pro's corrected Phase 5BA proposal is decisive: at the Phase 5AV validated cloak, the unforced Leray-projected Navier-Stokes vector field has a large inner product with the stealth-manifold normal `∇_u q`, so the cloak is destroyed by first-order orthogonal rejection rather than by higher-order curvature. If this fails, the 5AX finite-time exposure is a second-order/curvature phenomenon, and any theorem must target finite-time manifold invariance, not first-order transversality.
- **Scope:** NS Millennium Hunt, post-5AX finite-time admissibility geometry
- **Status:** `falsified_for_first_order_normal_rejection / curvature_target_open`
- **Discriminating test:** Rebuild the exact Phase 5AV validated cloak on the CUDA path. Treat the signed moving-axis pressure footprint `q(u)` as a differentiable scalar functional of the full velocity grid. Use PyTorch autograd to compute `∇_u q`, compute the unforced NS vector field `F(u)=P(-(u·∇)u)+νΔu`, and evaluate `<∇q,F>`, `||∇q||`, `||F||`, and `cos(F,∇q)` for `ν=0` and `ν=1e-3`. Cross-check `<∇q,F>` against finite-difference `Dq/Dt`.
- **Success criterion:** Support = `|<∇q,F>|` is large relative to `||∇q||||F||` and finite-difference `Dq/Dt` is not near zero. Rejection = `<∇q,F>` matches the already observed near-zero `Dq/Dt≈0.0087`; then first-order normal rejection is false for this cloak and 5AX exposure must be explained by curvature/second variation along the natural trajectory.
- **Opened:** 2026-04-30 12:42:00 EDT
- **Run(s):** `phase5ba_stealth_normal_rejection_audit.py` on H100 host `209.20.158.17`
- **Result:** `falsified_for_first_order_normal_rejection`. The autograd normal calculation exactly matched finite differences, validating the measurement. For `nu=0`, `<∇q,F>=0.00868499` vs finite-difference `Dq/Dt=0.00869210`, with `cos(F,∇q)=6.58e-7`. For `nu=1e-3`, `<∇q,F>=0.234324` vs finite-difference `0.234332`, with `cos(F,∇q)=1.77e-5`. Both are tiny angular rejections relative to `||F||||∇q||`; the validated cloak is nearly tangent at first order. Therefore the 5AX exposure is not caused by a large first-order normal rejection. It is a finite-time curvature/second-variation effect along the NS trajectory after first-order tangency.
- **Closed:** 2026-04-30 12:46:00 EDT

#### H-NS-5BB — The dynamically tangent stealth cloak is enstrophy-sterile

- **Hypothesis:** Gemini Pro's "tumbling core gridlock" claim is correct: the Phase 5AV/5BA tangent cloak preserves pressure stealth only by making `ω` and `Sω` so misaligned that the normalized vortex-stretching production `ωᵀSω / |ω|³` is too small, zero, or negative to support a finite-time blowup. If this fails, high torque and first-order stealth tangency do not imply enstrophy sterility.
- **Scope:** NS Millennium Hunt, post-5BA production/alignment audit
- **Status:** `falsified_for_validated_cloak / production_positive`
- **Discriminating test:** Rebuild the exact Phase 5AV validated cloak on the CUDA path. At the core, compute `ω`, `S`, eigenvalues/eigenvectors of `S`, `ωᵀSω`, `|ω×Sω|`, `|ω|`, `|Sω|`, angle between `ω` and `Sω`, alignment of `ω` with the top positive strain eigenvector, and normalized ratios `production/|ω|³`, `torque/|ω|³`, plus the identity residual `(|ω×Sω|² + (ωᵀSω)²) - |ω|²|Sω|²`. Compare to the base core and report signs/magnitudes; do not invent a universal critical threshold.
- **Success criterion:** Support = production is nonpositive or dramatically suppressed relative to the base core while torque is huge. Rejection = production remains positive and comparable/high; then the cloak is not sterile and the next target remains finite-time manifold curvature/retuning, not simple production veto.
- **Opened:** 2026-04-30 12:56:00 EDT
- **Run(s):** `phase5bb_enstrophy_sterility_audit.py` on H100 host `209.20.158.17`
- **Result:** `falsified_for_validated_cloak`. The validated cloak is misaligned but not enstrophy-sterile. At the core, absolute production `ωᵀSω` rises from `0.12375` in the base core to `5.05146` in the cloak (`40.8x`). Normalized production `ωᵀSω/|ω|³` remains positive at `0.08675` (base `0.40321`), while normalized torque is also positive at `0.21085` (base `0.29568`). The angle between `ω` and `Sω` is `67.64°`, and alignment with the top positive strain eigenvector remains high enough (`0.83167`, angle `33.73°`). The identity residual is `3.2e-16`, validating the decomposition. Therefore high torque/misalignment does not imply production veto for this cloak; both torque and positive stretching coexist. The finite-time failure remains a manifold-curvature/retuning problem, not simple sterility.
- **Closed:** 2026-04-30 12:58:00 EDT

#### H-NS-5BC — The validated cloak exits by positive finite-time curvature of `q(t)`

- **Hypothesis:** The Phase 5AX finite-time exposure is caused by positive curvature of the stealth functional along the unforced NS trajectory. The validated cloak is first-order tangent (`q1≈0`) but has large positive `q2` in the local expansion `q(t)=q0+q1 t+0.5 q2 t²+...`, making the stealth manifold non-invariant over a dwell interval. If this fails, the observed exit is a later higher-order or numerical trajectory effect and the Lyapunov exit-time route is less direct.
- **Scope:** NS Millennium Hunt, Route 1 dynamical exit-time bound
- **Status:** `closed / broad_slot_path_trigger_ran`
- **Discriminating test:** Rebuild the exact Phase 5AV validated cloak. Evolve under unforced Leray-projected NS for a short window with smaller timesteps than Phase 5AX. Record `q(t)`, `q_ratio(t)`, `tau_ratio(t)`, and positive production for `nu=0` and `nu=1e-3`. Fit low-order polynomials over early windows to estimate `q1`, `q2`, and predicted threshold exit time. Cross-check `q1` against Phase 5BA autograd `<∇q,F>`.
- **Success criterion:** Support = `q1` is near zero but `q2` is positive and large enough that a quadratic prediction approximates the observed exit time/order of magnitude while torque and production remain positive. Rejection = `q2` is small/unstable/sign-changing and the exit requires later high-order terms or numerical artifacts.
- **Opened:** 2026-04-30 13:04:00 EDT

#### H-NS-5BD — The 5BC curvature-exit signal survives resolution and de-aliasing stress

- **Hypothesis:** The Phase 5BC curvature signal is not a grid-resolution or quadratic-aliasing artifact. Rebuilding the same validated Phase 5AV cloak at higher spectral resolutions and applying a 2/3 de-aliasing filter to nonlinear products preserves the qualitative pattern: `q1` remains small relative to the later exposure, `q2` remains large and positive, the quadratic absolute-threshold exit estimate remains close to the observed exit, and `tau_ratio` remains high during exposure.
- **Scope:** NS Millennium Hunt, post-5BC robustness / false-positive audit
- **Status:** `falsified_for_fixed_amplitude_portability / retuned_test_required`
- **Discriminating test:** Run `phase5bd_resolution_dealias_curvature_audit.py` on CUDA. Rebuild the pair `[1,18]` cloak with amplitudes `[0.1393333077430725, 0.19449999928474426]` at `N=40,48,56,64`, with and without 2/3 de-aliasing of the advective product and pressure-source scalar. For each case, evolve under unforced Leray-projected NS for `nu=0` and `nu=1e-3`, record `q(t)`, fit early windows, and compare `q2`, observed exit time, quadratic absolute-threshold exit estimate, final `q_ratio`, and `tau_ratio`.
- **Success criterion:** Support = across the resolution/dealiasing ladder, `q2` stays positive and order-stable, observed exits remain near the quadratic estimates, and no case shows long-lived strict stealth with high torque. Rejection = de-aliasing or higher `N` collapses `q2`, flips its sign, or allows the validated cloak to remain inside `q_ratio < 1e-2` over the tested dwell window while torque remains high.
- **Opened:** 2026-04-30 17:08:00 EDT
- **Run(s):** `phase5bd_resolution_dealias_curvature_audit.py` on H100 host `209.20.158.17`
- **Result:** `falsified_for_fixed_amplitude_portability`. The original amplitudes `[0.1393333,0.1945]` reproduce the 5BC cloak at `N=40` without de-aliasing (`q_ratio=0.000310978`, `q2≈4270`, exit `≈0.00304`), but they do not port cleanly. Dealiasing at `N=40` gives initial `q_ratio≈2.886`; higher `N` fixed-amplitude cases have initial `q_ratio≈0.486–6.247` and much lower or inconsistent `tau_ratio` in some cases. Therefore 5BD does not falsify finite-time exposure, but it does falsify the naive claim that the exact two amplitudes define a resolution/dealias robust dynamic cloak. The right follow-up is H-NS-5BE: retune amplitudes at each stressed setting.
- **Closed:** 2026-04-30 17:43:00 EDT

#### H-NS-5BE — Retuned resolution/dealias cloaks still exit by finite-time curvature

- **Hypothesis:** The Phase 5BD failure is a portability failure of the fixed amplitudes, not a route-killer for the curvature mechanism. If the two amplitudes for pair `[1,18]` are retuned separately at each resolution/dealias setting to recover a strict or near dynamic cloak, the recovered cloak still exits `q_ratio < 1e-2` under unforced NS by finite-time curvature rather than persisting as a resolution-robust stealth trajectory.
- **Scope:** NS Millennium Hunt, post-5BD retuned robustness audit
- **Status:** `mixed_positive_for_exit / negative_for_clean_curvature_universality`
- **Discriminating test:** Run `phase5be_retuned_resolution_curvature_audit.py`. For each `N in {40,48,56,64}` and `dealias in {false,true}`, rebuild the core/pool, grid-search/refine the two amplitudes around the Phase 5AV pair `[1,18]` to minimize `q_ratio` plus material-tangency penalty while keeping `tau_ratio>1`, then evolve the best candidate for `nu=0` and `nu=1e-3`. Report whether a strict/near cloak is found and, if found, whether `q2` and observed exit remain positive/short.
- **Success criterion:** Support = retuned strict/near cloaks, when found, still exit quickly with positive `q2` and no long-lived high-torque stealth persistence. Rejection = a retuned high-torque cloak persists inside `q_ratio < 1e-2` over the tested dwell window at higher `N` or under dealiasing.
- **Opened:** 2026-04-30 17:44:00 EDT
- **Run(s):** `phase5be_retuned_resolution_curvature_audit.py` on H100 host `209.20.158.17`
- **Result:** `mixed_positive_for_exit / negative_for_clean_curvature_universality`. Same-pair retuning found strict static cloaks at `N=40` no-dealias (`q_ratio=0.000310`), `N=48` dealiased (`0.002217`), `N=56` no-dealias (`0.006035`), and `N=64` no-dealias (`0.001556`), plus near cloaks in the other cases. Every evolved candidate exited the tested stealth band; no persistent retuned high-torque cloak was found. However, the clean 5BC mechanism did not generalize as stated: outside the original `N=40` no-dealias case, many exits are driven by non-negligible first-order drift or signed `q2` changes sign (`N=56/64` no-dealias have negative signed `q2`). Therefore the surviving robust claim is finite-time non-persistence of the retuned two-mode same-pair cloaks, not a universal positive signed-curvature law. The next honest target is a higher-resolution broad search for true dynamic tangent cloaks (`q≈0` and `Dq/Dt≈0`) across more pairs/modes, or a theorem using distance-to-stealth/exit time rather than signed `q2`.
- **Closed:** 2026-04-30 14:18:00 EDT

#### H-NS-5BF — High-resolution dynamic tangent cloaks recur beyond the original pair

- **Hypothesis:** The Phase 5AV dynamic-tangent cloak is not a one-pair `N=40` artifact. A broad two-mode screen at higher resolution and under 2/3 de-aliasing will still find at least one high-torque candidate with `q_ratio < 1e-2` and `|Dq/Dt| < 1.0`. If this fails, the pressure-stealth counterexample is much narrower: static stealth can be retuned, but first-order dynamic tangency does not survive the high-resolution/dealias screen.
- **Scope:** NS Millennium Hunt, post-5BE broad high-resolution dynamic-tangent screen
- **Status:** `closed`
- **Discriminating test:** Run `phase5bf_highres_dynamic_tangent_screen.py` on CUDA for `N=48,64`, with and without 2/3 de-aliasing. Use the same pair schedule and amplitude grid shape as Phase 5AV (`18,750` samples per setting), but compute metrics with the 5BD dealiased/non-dealiased operators. Record strict tangent counts, near tangent counts, and best examples by `(q_ratio, |Dq/Dt|, -tau_ratio)`.
- **Success criterion:** Support = any higher-resolution/dealias setting finds strict high-torque dynamic tangent candidates comparable to Phase 5AV. Rejection = zero strict candidates and only weak near candidates across all stressed settings.
- **Opened:** 2026-04-30 14:22:00 EDT
- **Run(s):** `phase5bf_highres_dynamic_tangent_screen.py` on H100 host `209.20.158.17`
- **Result:** `rejected_for_strict_recurrence / near_tangent_only`. Across `75,000` two-mode samples (`18,750` each at `N=48/64`, dealias on/off), the screen found `strict_total=0` and `near_total=3`. The best static-cloak examples at high resolution often had very small `q_ratio` (`5.39e-5` to `5.21e-4`) but huge material derivatives (`|Dq/Dt|≈153–1826`, `|Dq/Dt|/q_core≈74–880`), so they are not dynamic tangencies. The three near-tangent examples had much weaker static stealth or lower/uneven torque (`q_ratio≈0.0082–0.0138`, `|Dq/Dt|/q_core≈0.68–1.11`). This rejects the claim that the original Phase 5AV strict dynamic tangent recurs easily under higher resolution/dealias stress in the same two-mode search family. It does not prove nonexistence outside the screened family.
- **Closed:** 2026-04-30 14:29:00 EDT

#### H-NS-5BG — Targeted high-resolution refinement cannot recover strict dynamic tangency

- **Hypothesis:** The 5BF absence of strict high-resolution dynamic tangencies is not merely coarse amplitude-grid miss. If we locally refine the 5BF near/static candidate neighborhoods at fixed `N,dealias,pair` using normalized objective `q_ratio + |Dq/Dt|/q_core` with a torque floor, no candidate will satisfy `q_ratio < 1e-2`, `|Dq/Dt|/q_core < 1`, and `tau_ratio > 1` after refinement.
- **Scope:** NS Millennium Hunt, post-5BF targeted discriminator
- **Status:** `closed`
- **Discriminating test:** Run `phase5bg_targeted_highres_tangent_refine.py` on CUDA. Seeds are the 5BF `best_combined` and `near_examples` rows for each stressed setting. For each seed, optimize only the two amplitudes of that seed's pair using Adam over the dealiased/non-dealiased high-resolution operators; report strict/near counts under normalized derivative thresholds.
- **Success criterion:** Support = zero strict normalized tangencies after local refinement, especially if best refined states still show either static-only cancellation with huge normalized derivative or near-only weak candidates. Rejection = any refined high-resolution candidate satisfies strict normalized dynamic tangency.
- **Opened:** 2026-04-30 14:59:00 EDT
- **Run(s):** `phase5bg_targeted_highres_tangent_refine.py` on H100 host `209.20.158.139`
- **Result:** `falsified / strict_highres_tangent_recovered`. Targeted refinement over `24` high-resolution 5BF neighborhoods recovered `strict_total=3` and `near_total=6` under normalized derivative thresholds. Best strict case: `N=48`, dealias on, pair `[15,20]`, amplitudes `[0.0427703,-0.112994]`, `q_ratio=0.000351`, `|Dq/Dt|/q_core=0.00595`, `tau_ratio=11.41`. Two more strict cases appear at `N=48` no-dealias pair `[0,11]` (`q_ratio=0.00396`, normalized derivative `0.00731`, `tau=3.04`) and `N=48` dealias pair `[2,25]` (`q_ratio=0.00932`, normalized derivative `0.0194`, `tau=1.0006`). Therefore 5BF was a coarse/local-search false negative for strict dynamic tangency, not proof that first-order transversality is structurally restored by resolution/dealiasing. The proof route must allow high-resolution tangent states and attack finite-time persistence/dwell instead.
- **Closed:** 2026-04-30 15:31:00 EDT

#### H-NS-5BH — Recovered high-resolution tangent states fail finite-time tube persistence

- **Hypothesis:** The strict 5BG high-resolution tangent states are instantaneous optimized points, not finite-time stealth trajectories. When evolved under unforced Leray-projected NS for `nu=0` and `nu=1e-3`, each strict 5BG candidate exits the strict stealth tube (`q_ratio < 1e-2` and `|Dq/Dt|/q_core < 1`, with `tau_ratio > 1`) before a comparable local turnover/dwell interval can support a singular reset.
- **Scope:** NS Millennium Hunt, Path D finite-time tube viability
- **Status:** `closed`
- **Discriminating test:** Evolve the three strict 5BG candidates under the same high-resolution/dealias operators that produced them. Track `q_ratio`, normalized `|Dq/Dt|`, `tau_ratio`, positive enstrophy production, exit time from the strict tube, and whether the trajectory remains in the near tube.
- **Success criterion:** Support = all strict 5BG candidates exit the strict tube quickly while retaining active torque/production. Rejection = any strict candidate remains in the strict tube over the tested dwell interval with active torque and positive production.
- **Opened:** 2026-04-30 15:31:00 EDT
- **Run(s):** `phase5bh_tangent_tube_persistence_audit.py` on H100 host `209.20.158.139`
- **Result:** `falsified_for_all_exit / persistent_inviscid_tangent_found`. Of the three strict 5BG candidates, one persisted inside the strict tube for the full tested inviscid window: `N=48`, dealias on, pair `[15,20]`, with `nu=0`, initial `q_ratio=0.000349`, normalized `|Dq/Dt|=0.00597`, `tau=11.41`, positive production `0.7457`; final at step `320` still had `q_ratio=0.00229`, normalized `|Dq/Dt|=0.9186`, `tau=15.29`, positive production `0.7424`, and no strict/near exit. The other inviscid candidates exited strict (`t≈0.00166` for pair `[0,11]`; immediate due `tau<1` after one step for pair `[2,25]`). Under `nu=1e-3`, none of the three starts in the strict tube because the viscous RHS makes normalized `|Dq/Dt|≈1.53–1.70` at `t=0`, although the best `[15,20]` case remains near. Therefore Path D remains the right abstraction, but the simple inertial finite-time exit claim is false. The next honest split is viscosity-aware: can the Rival retune a high-resolution tangent using the full viscous RHS, or does positive viscosity structurally destroy strict tube persistence?
- **Closed:** 2026-04-30 15:36:00 EDT

#### H-NS-5BI — Viscous-RHS refinement cannot recover strict high-resolution tangency

- **Hypothesis:** The 5BH inviscid persistent tangent cannot be made into a strict viscous NS tangent. If the 5BG strict neighborhoods are re-optimized with the full `nu=1e-3` RHS in the normalized objective, no candidate will satisfy `q_ratio < 1e-2`, `|Dq/Dt_ν|/q_core < 1`, and `tau_ratio > 1`.
- **Scope:** NS Millennium Hunt, viscosity-aware Path D split
- **Status:** `closed`
- **Discriminating test:** Modify/refactor the 5BG targeted refinement to optimize `qdot_along_rhs(..., nu=1e-3)` instead of inviscid `nu=0`, seeded from the three strict 5BG candidates and the best 5BH persistent inviscid case. Report strict/near viscous tangencies and then evolve any strict viscous candidate under the same `nu=1e-3` operator.
- **Success criterion:** Support = zero strict viscous tangencies after local refinement, or strict candidates that immediately exit under matched viscous evolution. Rejection = a strict viscous tangent persists over the tested dwell window with active torque and positive production.
- **Opened:** 2026-04-30 15:36:00 EDT
- **Run(s):** `phase5bi_viscous_tangent_refine_audit.py` on H100 host `209.20.158.139`
- **Result:** `falsified / persistent_viscous_tangent_found`. Viscosity-aware refinement recovered a strict `nu=1e-3` tangent and it persisted over the tested dwell window. The recovered state is again `N=48`, dealias on, pair `[15,20]`, retuned to amplitudes `[0.0534729,-0.122681]`. Initial matched-viscous metrics: `q_ratio=0.00612`, normalized `|Dq/Dt_ν|=0.00282`, `tau_ratio=13.12`, positive production `0.9874`. At step `320` (`t≈0.00634`) it remains strict: `q_ratio=0.00769`, normalized `|Dq/Dt_ν|=0.848`, `tau_ratio=17.31`, positive production `0.9744`. Therefore neither first-order transversality, inertial tube exit, nor unretuned viscosity ejection is a valid general route. The live Rival is a high-resolution dealiased two-mode viscous tangent tube with active torque and positive production over the tested window. Next target must stress persistence under longer dwell, scaling, resolution, and/or ask whether the tube is non-collapsing rather than nonexistent.
- **Closed:** 2026-04-30 15:39:00 EDT

#### H-NS-5BJ — Persistent viscous stealth is sterile in the full enstrophy budget

- **Hypothesis:** The 5BI persistent viscous tangent is a coherent stealth structure, not a singularity-supporting cascade. Over longer matched `nu=1e-3` evolution, while it remains in or near the pressure-stealth tube, its total enstrophy growth rate is non-positive or bounded downward by viscous vorticity-gradient dissipation: `production - nu * ||grad omega||^2 <= 0` on average.
- **Scope:** NS Millennium Hunt, algebraic cost of stealth / growth-vs-persistence discriminator
- **Status:** `closed`
- **Discriminating test:** Evolve the 5BI survivor (`N=48`, dealiased, pair `[15,20]`, amplitudes `[0.0534729,-0.122681]`, `nu=1e-3`) for a longer dwell interval. Track strict/near tube membership, total enstrophy, max vorticity, production `∫ω·Sω`, viscous enstrophy dissipation `nu∫|∇ω|²`, net enstrophy budget, and finite-difference enstrophy derivative.
- **Success criterion:** Support = stealth persistence coexists with non-positive or decaying net enstrophy budget / no compounding max-vorticity growth. Rejection = the state remains stealthy while net enstrophy budget and max vorticity grow persistently.
- **Opened:** 2026-04-30 15:44:00 EDT
- **Run(s):** `phase5bj_stealth_growth_budget_audit.py` on H100 host `209.20.158.139`
- **Result:** `confirmed / stealth_not_compounding`. The 5BI survivor is a coherent pressure-stealth camouflage state, not a growth-bearing singularity candidate in this window. It remains strict until `t≈0.00685` and near until `t≈0.01537`, but its full signed enstrophy production is negative from the start (`-0.4763`) and becomes more negative (`-0.5360`). Viscous enstrophy dissipation stays larger (`1.5741 -> 1.5055`), so the net enstrophy budget remains strongly negative (`-2.0504 -> -2.0415`). Total enstrophy decays `1.8711 -> 1.8179` (`-2.85%`). Positive-production pockets exist (`0.9874 -> 0.9201`), torque rises (`13.12 -> 60.81`), and max vorticity is nearly flat/slightly up (`27.1456 -> 27.2594`), but the global budget is draining and the stealth tube fails later (`q_ratio=0.3519`, normalized `|Dq/Dt|=21.27` at final). The key split is positive local pockets versus negative global signed production: the Rival can hide, but the tested hidden state is not compounding.
- **Closed:** 2026-04-30 15:46:00 EDT

#### H-NS-5BK — Static stealth and positive net enstrophy growth cannot intersect in the survivor basin

- **Hypothesis:** The 5BJ survivor failed because pressure stealth and positive global enstrophy budget are in tension, not because the optimizer was unlucky. If the `[15,20]`, `N=48`, dealiased basin is re-optimized as a static instantaneous intersection problem requiring strict/near stealth, active torque, and positive net enstrophy budget at the same state, the optimizer will either lose stealth/tangency or keep stealth with non-positive net budget.
- **Scope:** NS Millennium Hunt, stealth-growth incompatibility discriminator
- **Status:** `confirmed_for_fixed_N_substitution_portability`
- **Discriminating test:** Starting from the 5BI survivor and nearby amplitudes/mode-pairs, optimize the static objective `q_ratio + |Dq/Dt_ν|/q_core + torque_floor_penalty + net_budget_penalty`, where `net_budget_penalty` rewards instantaneous `production - ν||∇ω||² > 0`. No time integration is part of this discriminator; if a positive static intersection is found, evolution becomes the next experiment.
- **Success criterion:** Support = no candidate satisfies strict/near stealth plus positive instantaneous net budget. Rejection = a candidate satisfies strict/near stealth, active torque, and positive instantaneous net enstrophy budget in the tested basin.
- **Opened:** 2026-04-30 15:51:00 EDT
- **Updated:** 2026-04-30 15:56:00 EDT — clarified the active discriminator as static instantaneous intersection, not temporal dwell budgeting, to block the trust-fund/initial-condition exploit.
- **Run(s):** `phase5bk_static_stealth_growth_intersection.py` on H100 host `209.20.158.139`
- **Result:** `confirmed_for_no_static_intersection_in_tested_basin`. Across `8` high-resolution `N=48`, dealiased seeds and `5` objective weightings, the run found `strict_growth_total=0`, `near_growth_total=0`, `strict_stealth_total=3`, and `positive_net_total=2`. The strict stealth rows all had negative net budget: best `[8,3]` strict row had `q=0.00379`, normalized `|Dq/Dt|=0.0157`, `tau=9.04`, production `0.0354`, dissipation `1.0638`, net `-1.0283`; the `[15,20]` strict rows had `q≈0.00436-0.00575`, normalized derivative `0.0012-0.0054`, `tau≈12.95`, and net `≈-2.02`. The only positive-net rows were non-stealth, near-base states with `q≈0.992`, normalized derivative `≈0.363`, and tiny positive net (`3.5e-6` to `5.3e-6`).
- **Closed:** 2026-04-30 16:06:00 EDT

#### H-NS-5BL — SOS certificate bridge can verify a reduced stealth-growth exclusion receipt

- **Hypothesis:** The next formalization bottleneck is certificate shape, not Lean search. A reduced sum-of-squares receipt of the form `dissipation - production = slack + Σ square_i` should be verifiable by Lean with exact rationals, while Python remains only an untrusted oracle for generating candidate receipts.
- **Scope:** NS Millennium Hunt, oracle-verifier formalization architecture
- **Status:** `planned`
- **Discriminating test:** Add a Lean certificate verifier theorem for exact SOS receipts over the stealth-growth scalar cage, plus a Python pilot that emits a minimal rational JSON/MD certificate. Success means Lean verifies the generic certificate theorem and the pilot artifact documents the lossless certificate fields. This does not attempt the full 735-variable SDP.
- **Success criterion:** Support = Lean verifies the certificate bridge and the generated pilot certificate is exact/rational and auditable. Rejection = Lean cannot express/verify the certificate shape without search, or the certificate format requires floating-point identities.
- **Opened:** 2026-04-30 16:07:00 EDT
- **Run(s):** `phase5bl_sos_certificate_pilot.py`; Lean module `ZtareProofs.ns_sos_certificate_bridge`
- **Result:** `confirmed_for_certificate_bridge_plumbing`. The Python pilot emitted an exact rational JSON/MD certificate with shape `gap = slack + Σ term_i^2` (`1327/2450 = 1/10 + (3/5)^2 + (-2/7)^2`), explicitly marked as format/verifier-only and not a PDE certificate. Lean verified the generic theorem `positive_gap_of_sos_certificate`, plus the stealth-growth routing theorem `no_growth_bearing_segment_of_sos_gap_certificate`, after building the dependency `ZtareProofs.ns_stealth_growth_tradeoff`.
- **Closed:** 2026-04-30 16:13:00 EDT

#### H-NS-5BM — A third perturbation mode cannot bridge stealth and positive net growth in the survivor basin

- **Hypothesis:** The 5BK separation is not merely a two-amplitude artifact. If the high-resolution `N=48`, dealiased survivor neighborhoods are given one additional perturbation mode, static optimization will still fail to find a state satisfying strict/near stealth, active torque, and positive instantaneous net enstrophy budget simultaneously.
- **Scope:** NS Millennium Hunt, coverage-risk stress test after 5BK
- **Status:** `planned`
- **Discriminating test:** Seed from the best 5BK strict-stealth and near-bridge rows, add one third mode from a targeted perturbation pool, and optimize three amplitudes under the same static objective family: `q_ratio`, normalized `|Dq/Dt_ν|`, active torque, and positive `∫ω·Sω - ν∫|∇ω|²`. No time integration is part of this discriminator.
- **Success criterion:** Support = no three-mode candidate satisfies strict/near stealth plus positive instantaneous net budget. Rejection = any three-mode candidate satisfies strict/near stealth, active torque, and positive instantaneous net budget.
- **Opened:** 2026-04-30 16:15:00 EDT
- **Run(s):** `phase5bm_three_mode_stealth_growth_search.py --seed-limit 3 --third-limit 5 --steps 120 --lr 0.012` on H100 host `209.20.158.139`
- **Result:** `confirmed_for_no_three_mode_static_intersection_in_bounded_stress`. The bounded run covered `24` three-mode seeds and `6` objective weightings (`144` refinements), including strict-stealth, positive-net, and bridge-score parents from 5BK. It found `strict_growth_total=0`, `near_growth_total=0`, `strict_stealth_total=24`, and `positive_net_total=26`. The best strict stealth row had `q=0.000194`, normalized `|Dq/Dt|=0.00650`, `tau=2.16`, production `0.00693`, dissipation `0.19479`, net `-0.18786`. The closest positive-net rows remained far from stealth (`q≈0.986-0.998`) with tiny positive net (`~6.7e-6` to `9.8e-5`). Thus a controlled third mode did not bridge the stealth-growth gap.
- **Closed:** 2026-04-30 17:13:00 EDT

#### H-NS-5BN — Strict-stealth bankruptcy is concentrated in a small quadratic toxic block

- **Hypothesis:** The negative net budget in the strict-stealth 5BM states is not an arbitrary high-dimensional artifact. Around the strict-stealth rows, the Hessian/eigenstructure of `gap = viscous_dissipation - signed_production` is dominated by a small set of amplitude directions/mode blocks, giving a compressed target for a reduced inequality or SOS certificate.
- **Scope:** NS Millennium Hunt, compression after bounded three-mode coverage stress
- **Status:** `confirmed_for_current_amplitude_block`
- **Discriminating test:** For the strict-stealth 5BM rows, rebuild the exact `N=48`, dealiased three-mode state and compute first/second derivatives of production, dissipation, and gap with respect to the three amplitudes. Report eigenvalues/eigenvectors, diagonal block contributions, cross terms, and whether a stable small block accounts for the margin across rows.
- **Success criterion:** Support = dominant gap/dissipation eigenvectors and diagonal/cross contributions recur across strict-stealth rows, especially in the best-net rows; rejection = the negative margin is diffuse/idiosyncratic across rows with no reusable block structure.
- **Opened:** 2026-04-30 17:14:00 EDT
- **Run(s):** `phase5bn_toxic_block_hessian_audit.py --limit 8` on H100 host `209.20.158.139`
- **Result:** `toxic_block_hessian_audit_complete`. The audit covered `14` strict-stealth rows from the 5BM survivor basin. Gap-Hessian/eigenvector mass was not diffuse: mode `20` had the largest mean absolute dominant gap-eigenvector coefficient (`0.8086`), with added modes `1` (`0.6087`) and `2` (`0.5400`) carrying the next strongest cancellation directions; mode `15` was materially smaller (`0.2742`). Mean absolute gap-Hessian diagonal share was also largest for mode `20` (`0.4105`). Best-net strict rows showed positive-definite gap Hessians with dominant eigenvectors concentrated on the `(mode20, added mode1/2)` block. This supports a reduced toxic-block certificate target, scoped to the current `N=48` dealiased amplitude block rather than a global PDE theorem.
- **Closed:** 2026-04-30 17:38:00 EDT

#### H-NS-5BO — The reduced `(mode20, auxiliary)` block has a reusable positive quadratic gap certificate

- **Hypothesis:** The 5BN toxic block is not only a dominant eigenvector pattern. For strict-stealth 5BM rows, the `2x2` Hessian sub-block spanning mode `20` and the active auxiliary cancellation mode (`1`/`2`/`3`/`0`) is positive definite with material Schur slack, giving a small certificate-shaped object for a reduced SOS/Lean receipt.
- **Scope:** NS Millennium Hunt, certificate compression after 5BN
- **Status:** `confirmed_for_reduced_amplitude_block`
- **Discriminating test:** Read `phase5bn_toxic_block_hessian_audit.json`, extract each strict row's gap-Hessian sub-block on `(mode20, auxiliary mode)` where the auxiliary is the third mode besides `15` and `20`, and compute the exact `2x2` square-completion form `a(x + (b/a)y)^2 + (c - b^2/a)y^2`. Support requires `a > 0` and Schur slack `c - b^2/a > 0` across rows with nontrivial block dominance. Rejection means any strict-stealth row has a non-positive reduced block or the block contribution is too weak/idiosyncratic to support certificate compression.
- **Success criterion:** Support = all audited reduced blocks are positive definite with stable material Schur slack and dominant-eigenvector projection concentrated in the reduced block. Rejection = reduced block positivity fails or relies on the full third coordinate in a noncompressible way.
- **Opened:** 2026-04-30 17:41:00 EDT
- **Run(s):** `phase5bo_reduced_toxic_block_certificate.py`
- **Result:** `reduced_toxic_block_certificate_candidate_found`. All `14` reduced `(mode20, auxiliary)` blocks were positive definite. Minimum reduced-block eigenvalue was `115.057`, minimum Schur slack was `117.086`, and the minimum projection of the full dominant gap eigenvector onto the reduced block was `0.864`. The script emitted rational square-completion receipts for every row. This confirms the 5BN block is certificate-shaped in the current amplitude model, but it also sharpens the substitution-attack risk: a global argument must show the same block law ports when mode `20` is excluded.
- **Closed:** 2026-04-30 17:43:00 EDT

#### H-NS-5BP — Mode-20 substitution attack either finds a new stealth-growth bridge or recreates the toxic block elsewhere

- **Hypothesis:** The 5BN/5BO toxic block is not a mode-20 artifact. If the optimizer is forbidden to use mode `20` and is seeded with substitute base pairs such as `[10,25]`, `[14,19]`, `[16,21]`, `[2,25]`, and `[8,3]`, then either no stealth-growth intersection appears, or any strict-stealth substitute survivor develops the same positive-definite toxic block around its high-frequency cancellation mode.
- **Scope:** NS Millennium Hunt, portability stress after reduced certificate compression
- **Status:** `planned`
- **Discriminating test:** Run a static three-mode search at `N=48`, dealiased, with mode `20` excluded from all base and auxiliary modes. Optimize for the same instantaneous criteria as 5BM: small pressure footprint, small viscous `Dq/Dt`, active torque, and positive net enstrophy budget. Then Hessian-audit strict-stealth substitute survivors. Support = no strict/near stealth-growth intersection and strict-stealth substitute rows show positive-definite reduced toxic blocks. Rejection = a mode-20-free row satisfies stealth plus positive net, or strict-stealth rows avoid a reusable positive toxic block.
- **Success criterion:** Support = `strict_growth_total=0`, `near_growth_total=0`, and all audited strict-stealth substitute blocks have positive Schur slack. Rejection = any mode-20-free strict/near stealth-growth row, or a strict stealth survivor whose reduced gap block is not positive definite.
- **Opened:** 2026-04-30 17:44:00 EDT
- **Run(s):** `phase5bp_mode20_substitution_attack.py`
- **Result:** `mode20_free_no_growth_bridge_with_toxic_block_recreated`. The H100 run completed `576/576` refinements and `19/19` Hessian audits. With mode `20` excluded, the optimizer still found `19` strict-stealth substitute states, but found `0` strict-growth and `0` near-growth states. All `19/19` strict-stealth Hessian audits produced positive-definite reduced toxic blocks around the substitute high-frequency cancellation mode, with examples including high modes `18`, `19`, `21`, `25`, and `8`. The weakest audited reduced block remained materially positive (`eig_min=30.5122`, `schur=32.5966`), and the final classification was `mode20_free_no_growth_bridge_with_toxic_block_recreated`. This supports portability of the toxic-block mechanism at fixed `N=48`; it does not close the continuum bridge.
- **Closed:** 2026-04-30 20:49:26 EDT

#### H-NS-5BQ — Spectral-N robustness decides whether toxic-block certificates are continuum-facing or truncation-local

- **Hypothesis:** The reduced toxic-block certificate is an atlas object whose global relevance depends on spectral-truncation robustness, not on a single `N=48` success. If the certificate is continuum-facing, the reduced-block margin (`min_reduced_block_eig` and Schur slack) should remain bounded below by a positive floor across a pre-registered resolution ladder. If it is instrument-local, the margin will decay, oscillate, or collapse with `N`.
- **Scope:** NS Millennium Hunt, gp163d/NS phase5ab isomorphism transfer after 5BO and before 5BP result
- **Status:** `closed_truncation_collapse`
- **Discriminating test:** After 5BP closes, rerun the reduced toxic-block audit on the pre-registered spectral ladder `N ∈ {24, 32, 48, 64, 96, 128}` using dealiased products and the same `(15,20,aux)` local-certificate extraction rule. Track `min_reduced_block_eig_at_N`, `min_schur_slack_at_N`, `n_certified_rows_at_N`, substitution-attack `λ_min` at that same `N`, aux-mode distribution, and runtime. The test is not allowed to choose `N` values or thresholds after seeing 5BP. The primary ratio is the log-spread of `λ_min` across `N`, analogous to the gp163d `log_a0` environment spread.
- **Success criterion:** Five pre-registered outcomes, mirrored from `phase5bp_spectral_n_pre_registration.md`: (1) `UNIFORM-IN-N CERTIFICATE`: `min_reduced_block_eig_at_N ≥ 100` and `n_certified_rows_at_N ≥ 10` for every `N ∈ {24,32,48,64,96,128}`; (2) `STRUCTURED SCALING`: positive margins at all N with monotone power-law decay `λ_min ∝ N^(-α)`, `α < 1`; (3) `VANISHING MARGIN`: `λ_min < 10` at `N ≥ 96` or certified rows `< 5`; (4) `U-SHAPE / NON-MONOTONE`: statistically significant non-monotone margin curve; (5) `CRITICAL N*`: positive before a sharp `N*` and zero/negative at or after it. Only outcome (1) is continuum-facing. Outcomes (2)-(5) are scoped atlas/instrument findings, not Clay-prize closure. Stop rule: if the first three values `{24,32,48}` trigger Verdict 3 or 4, halt before `N≥96` until the structure is understood.
- **Opened:** 2026-04-30 18:07:00 EDT
- **Pre-registration artifact:** `projects/ns_millennium_hunt/workspace/phase5bp_spectral_n_pre_registration.md`
- **Run(s):** `phase5bq_spectral_n_certificate_atlas.py`
- **Result:** `truncation_collapse`. The A100 run completed the full pre-registered ladder `N ∈ {24,32,48,64,96,128}` with `72/72` refinements. It found `18` reduced-block rows overall. The `N=48` rows reproduced the positive toxic-block certificate (`eig_min` range across shown N=48 rows from `115.057` to `165.512`, all Schur-positive), but the low-resolution `N=24` rows for `plus3` produced negative reduced-block eigenvalues and Schur slack (`min_eig=-15.2886`, `min_schur=-18.6456`). The final classification was therefore `truncation_collapse`, not `UNIFORM-IN-N CERTIFICATE`. This falsifies the strongest continuum-facing interpretation of the finite-`N=48` certificate and reframes the current object as a resolution-conditioned atlas/instrument result. It does not falsify fixed-`N=48` portability; it blocks using 5BO/5BP as a direct Clay bridge without a new continuum argument or a corrected resolution-normalized certificate.
- **Closed:** 2026-04-30 23:07:05 EDT

#### H-NS-5BS — High-N void is either exposure or normalized-certificate recovery, not automatic continuum collapse

- **Hypothesis:** The Phase 5BQ high-resolution void at `N=96` and `N=128` is not evidence of stealth-growth compatibility. If the `N=48/64` certified stealth rows are warm-started into `N=96/128` with longer refinement, then either (a) the pressure-stealth tube is still not recovered, meaning the state is exposed/taxable rather than hidden, or (b) an in-tube row is recovered and its max-coupled or intended `(mode20, aux)` Hessian block remains positive after raw or frequency-normalized auditing. Rejection requires a high-`N` strict/near-stealth row with positive net enstrophy budget, or a high-`N` in-tube row whose reduced block fails even after normalization while remaining growth-relevant.
- **Scope:** NS Millennium Hunt, post-5BQ failure-mode split
- **Status:** `closed_high_n_tube_recovered_raw_certificate_positive`
- **Discriminating test:** Run `phase5bs_high_n_tube_recovery_or_normalized_certificate.py` on `N ∈ {96,128}`. Source seeds only from 5BQ positive-block `N=48/64` rows. Use warm, scaled, and jittered restarts, longer refinement, and three objectives (`stealth_ultra`, `tube_recovery`, `tube_and_growth`). Audit every best row with both the max-coupled block and the intended auxiliary block, and report raw plus frequency-normalized Schur/eigen margins. The primary falsifier remains `strict_growth` or `near_growth`; missing tube rows are classified as exposure, not certificate failure.
- **Success criterion:** Support = no high-`N` strict/near growth and either no tube recovered (`high_n_tube_not_recovered_exposure_case`) or recovered tube rows with positive raw/normalized blocks. Rejection = any high-`N` strict/near stealth-growth row or an in-tube growth-relevant row whose raw and normalized block margins are nonpositive.
- **Opened:** 2026-04-30 23:20:00 EDT
- **Run(s):** `phase5bs_high_n_tube_recovery_or_normalized_certificate.py`
- **Result:** `high_n_tube_recovered_raw_certificate_positive`. The A100 run completed `216/216` high-`N` warm-start/refinement rows across `N=96` and `N=128`, recovered the stealth tube (`strict_stealth_count=16`, `near_stealth_count=29`, `min_q_ratio=0.0001145`), and found `0` strict-growth and `0` near-growth rows. All in-tube max-coupled and intended-auxiliary raw blocks were positive. The best growth-oriented row remained slightly draining (`max_net_budget=-0.001379`), so high-`N` recovery did not expose a stealth-growth bridge. Follow-up `phase5bt_asymptote_extraction_audit.py` remained conservative: it found positive margins but classified both global and post-MES scaling as `constant_margin_only_no_exponent_gap_yet`, so the continuum bridge still requires an analytic or stronger empirical asymptote argument.
- **Closed:** 2026-05-01 00:56:00 EDT

#### H-NS-5BU — Constant-margin squeeze is the right continuum obligation after 5BS/5BT

- **Hypothesis:** Phase 5BT's `constant_margin_only_no_exponent_gap_yet` output is not a failure mode if the normalized margin has a positive finite-atlas floor and can be routed into a Lean theorem that assumes a uniform positive infimum. The continuum bridge should therefore be formalized as a constant-margin squeeze obligation: prove the normalized toxic-block reserve remains one step ahead of low/high advective leakage for all `N ≥ N*`, not necessarily that the raw Schur slack diverges faster than leakage.
- **Scope:** NS Millennium Hunt, post-5BS analytic bridge extraction
- **Status:** `planned`
- **Discriminating test:** Add a Lean constant-margin interface to `ns_asymptotic_margin_extraction.lean` and run an offline audit over the closed 5BS rows to extract conservative candidate floors such as frequency-normalized eigen floor, Schur/|c| floor, and eig/trace floor. Support = Lean builds with a theorem that closes leakage control from a uniform positive normalized margin, and the finite atlas reports strictly positive candidate floors on all in-tube rows. Rejection = the Lean theorem cannot route constant margin into `lowHighLeakageControlled`, or the finite atlas contains zero/negative normalized in-tube block floors.
- **Success criterion:** Support = `lake build ZtareProofs.ns_asymptotic_margin_extraction` succeeds and `phase5bu_uniform_margin_candidate_audit.json` reports all candidate floors positive. Rejection = build failure or nonpositive candidate floor. Caveat: support does not prove the continuum theorem; it names the exact analytic squeeze obligation.
- **Opened:** 2026-05-01 01:02:00 EDT
- **Run(s):** `phase5bu_uniform_margin_candidate_audit.py`, `ztare_proofs/ZtareProofs/ns_asymptotic_margin_extraction.lean`
- **Result:** `constant_margin_interface_compiled_with_positive_finite_atlas_floor`. The Lean bridge now includes `ConstantMarginEstimate`, `uniformPositiveMargin`, `validFloor`, `tax_margin_dominates_leakage_of_constant_margin`, `leakage_controlled_of_constant_margin`, and `toxic_block_cycle_margin_of_constant_margin_estimates`. `lake build ZtareProofs.ns_asymptotic_margin_extraction` succeeded. The offline 5BU audit over closed 5BS rows found `29` in-tube rows and `58` in-tube block records, all non-growing, with strictly positive candidate floors: `min_freq_norm_eig_min=0.7254`, `min_eig_over_abs_trace=0.3374`, `min_schur_over_abs_c=0.9362`, `min_raw_eig=288.933`, and `min_raw_schur=294.503`. This supports the constant-margin squeeze as the correct formal bridge target; it does not itself prove the analytic uniformity lemma for all `N`.
- **Closed:** 2026-05-01 01:08:00 EDT

#### H-NS-5BV — N128 gap is tube recovery failure vs normalized-margin degradation

- **Hypothesis:** The Phase 5BS `N=128` gap is not evidence of stealth-growth compatibility. It is either (a) a tube-recovery/search failure where the optimizer did not reach the pressure-stealth tube at `N=128`, while all sampled rows remain non-growing and block-positive, or (b) a genuine normalized-margin degradation where rows near the tube show weak/nonpositive certified block floors. The next proof move depends on distinguishing those two cases before spending more GPU.
- **Scope:** NS Millennium Hunt, post-5BS/5BU finite-atlas scope correction
- **Status:** `planned`
- **Discriminating test:** Run an offline audit over `phase5bs_high_n_tube_recovery_or_normalized_certificate.json`, grouped by `N`, objective, source seed, and restart. For each `N`, report strict/near stealth counts, min `q_ratio`, best non-growing/growth budgets, block positivity, and normalized floors on the closest-to-tube rows. Support for tube-recovery failure = `N=128` has `0` in-tube rows, all rows non-growing, and closest rows remain raw/frequency-normalized block-positive. Support for degradation = `N=128` has near-tube rows whose block floors collapse or become nonpositive.
- **Success criterion:** `tube_recovery_failure_not_growth_escape` if `N=128` has no strict/near growth and no in-tube block failure; `normalized_margin_degradation` if `N=128` closest/tube rows show nonpositive normalized floors; `stealth_growth_escape` if any `N=128` strict/near stealth-growth row exists.
- **Opened:** 2026-05-01 01:16:00 EDT
- **Run(s):** `phase5bv_n128_tube_gap_audit.py`
- **Result:** `tube_recovery_failure_not_growth_escape`. The offline audit over closed 5BS rows found `N=128` had `108` rows, `0` strict-stealth, `0` near-stealth, `0` strict-growth, and `0` near-growth rows. Its closest row had `q_ratio=0.608659`, so the optimizer never reached the pressure-stealth tube at `N=128`. The closest rows were nevertheless non-growing and block-positive: closest-row raw and frequency-normalized blocks were positive, with examples including `min_freq_norm_eig_min≈1.0096`, `min_schur_over_abs_c≈0.9556`, and `min_eig_over_abs_trace≈0.3829`. Therefore the 5BS/5BU scope correction is: `N=96` supplies the in-tube finite-atlas floor; `N=128` currently supplies no in-tube floor but also no stealth-growth escape or block degradation.
- **Closed:** 2026-05-01 01:19:00 EDT

#### H-NS-5BW — Universal eviction inequality is the Clay-facing inverse target

- **Hypothesis:** The post-5O/5R/5S and 5BQ/5BS/5BU/5BV evidence should be reframed as a candidate universal eviction law, not only as a finite-resolution certificate. The Clay-facing target is to define mathematically invariant observables `tau_redist(u,t)` and `tau_cons(u,t)` such that a universal inequality, e.g. `tau_redist(u,t) * tau_cons(u,t) <= C(nu, ||u_0||_{H^s})`, implies a known regularity criterion by controlling vorticity-direction coherence or depleting vortex stretching. The finite-`N` evidence is supporting data for this target, not the claim itself.
- **Scope:** NS Millennium Hunt, inverse calibration before Phase 5BW Lean formalization
- **Status:** `planned`
- **Discriminating test:** First, perform a primary-source literature check on vorticity-direction coherence and related regularity criteria. Second, run two independent cold shots (`gpt-5.5` and `gemini-3.1-pro-preview`, no cross-model context) using only the compact empirical packet: `tau_redist/tau_cons≈0.00663`, one sampled danger exit with `dχ/dt≈-2.08`, signed escape coordinate `a: 0.334→0.782`, no positive net budget in in-tube high-`N` rows, and positive finite-atlas normalized certificate floors. Ask each model to (a) sharpen definitions of `tau_redist` and `tau_cons` that would make the universal statement provable in the Constantin-Fefferman / Beirão da Veiga-Berselli / Vasseur lineage, (b) identify the symmetry/topology constraint on initial data that would forbid redistribution and serve as an inverse counterexample strategy, and (c) state a dichotomy theorem with an explicit detector.
- **Success criterion:** Support for universal eviction = literature does not already state the product inequality, and both cold shots produce definitions that route into a known regularity criterion rather than an undefined heuristic. Support for counterexample inversion = both identify a concrete redistribution-forbidding symmetry class to test. Rejection = the observables cannot be made invariant/measurable enough to imply BKM or an existing direction-coherence criterion; then the result remains a methodology/instrument-validation paper plus a finite-resolution anti-blowup atlas.
- **Opened:** 2026-05-01 02:18:00 EDT
- **Pre-registration artifact:** `projects/ns_millennium_hunt/workspace/phase5bw_kida_pelz_inverse_pre_registration.md`
- **Run(s):** `run_cold_shot_inverse_antiblowup_eviction.py`
- **Interim:** `2026-05-01 02:34:00 EDT` Gemini completed cleanly and classified the next fork as `COUNTEREXAMPLE_INVERSION_MORE_PROMISING`, with `Alignment Escape Rate` as the first law to formalize and Kida-Pelz-like symmetry locking as the proposed falsifier. GPT-5.5 returned empty message content with `finish_reason=length`; the runner persisted a failed-call receipt and no fallback was used. Primary-source literature check supports the direction-coherence lineage but has not found an explicit `tau_redist * tau_cons` product theorem yet. Do not close this row until the literature check is summarized and the next Lean/test target is chosen.
- **Interim:** `2026-05-01 02:47:00 EDT` The operational path was narrowed to Kida-Pelz inverse construction. The pre-registration names three terminal outcomes: symmetry breaks and redistribution resumes, symmetry holds and growth persists, or symmetry holds but growth saturates by a second mechanism. Guardrail: do not implement the Kida-Pelz initial condition from memory; first source the exact Fourier/symmetry representation from the literature or a reproducible published implementation.

#### H-XDOMAIN-5AJ — gp163d field diagnostics contain an off-core debt analogue to NS halo debt

- **Hypothesis:** If the Phase 5AH “local profit exported to halo debt” motif is a useful cross-domain primitive rather than a narrative overfit, the existing gp163d `krylovlocal` field diagnostics should already expose a static analogue: UDG tidal enhancement should coincide with elevated off-core or anisotropic field-response debt outside the source core, not only with a higher mass-weighted core response.
- **Scope:** NS Millennium Hunt / GP-163d cross-domain synthesis, Phase 5AI background-debt ladder
- **Status:** `partially_confirmed`
- **Discriminating test:** Run an offline audit over existing `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/*krylovlocal*.json` summaries. Extract UDG and binary tidal/uniform gain ratios, radial/aperture profiles, octant anisotropy, and axis-profile exterior field proxies. Support = the UDG separator peak is accompanied by a rising off-core/exterior/anisotropy debt proxy relative to uniform or relative to binary. Rejection = UDG gain is purely core-local while off-core/exterior metrics remain flat or lower, making the NS halo-debt motif non-portable to the current static gravity sandbox.
- **Run(s):** `phase5aj_gp163d_field_debt_proxy_audit.py`
- **Result:** `partially_confirmed`. Existing `krylovlocal` summaries contain an off-core/static field-debt analogue: every audited UDG debt proxy rises under tidal boundary in at least one saved run. On the `L=4,gamma=0.25` orientation ladder, UDG exterior internal-field debt/gain remains above `2.62x` at all saved angles and reaches `4.17x` at aligned orientation; UDG outer-shell internal-field debt/gain remains above `2.73x` and reaches `5.53x`. The crucial caveat is that this is a static AQUAL profile audit, not a dynamical cleanup-clock or gravitational-radiation measurement. It supports the cross-domain balance-sheet primitive, not literal fluid/gravity equivalence.
- **Opened:** 2026-04-30 07:58:00 EDT
- **Closed:** 2026-04-30 08:02:00 EDT

#### H-GP163D-5AK — Off-core field debt saturates the AQUAL `mu` response toward the Newtonian regime

- **Hypothesis:** The Phase 5AJ UDG off-core field-debt spike is not merely a larger internal-field tail; in the aligned high-separator run it pushes the surrounding halo across the AQUAL critical acceleration scale (`|grad Phi|/a0 >= 1`) or at least into near-saturation (`mu >= 0.7`), meaning the anomaly self-limits by stiffening its own non-linear dielectric environment.
- **Scope:** GP-163d / NS cross-domain balance-sheet synthesis, non-linear AQUAL audit
- **Status:** `partially_confirmed`
- **Discriminating test:** Run `phase5ak_aqual_mu_saturation_audit.py` on the existing `L=4,gamma=0.25` `krylovlocal` orientation summaries. Inspect UDG tidal AQUAL radial shells, aperture profiles, axis exterior samples, total-field percentiles, and `mu` percentiles. Support = the specific off-core/exterior debt region behind the `5.53x` outer-shell debt/gain crosses `total_g >= 1` or has `mu >= 0.7` on a material outer/exterior profile. Rejection = the debt spike remains below the critical scale and only approaches saturation weakly, so the “bank freezes accounts instantly” claim is too strong for the saved data.
- **Run(s):** `phase5ak_aqual_mu_saturation_audit.py`
- **Result:** `partially_confirmed / strong version rejected`. The aligned `L=4,gamma=0.25` UDG tidal run is near the AQUAL transition but does not cross the critical scale in the saved aligned radial/p90/exterior summaries: `total_g_p90=0.9897`, `axis_exterior_total_g_max=0.9429`, and `outer_total_g_weighted=0.4690`. It does reach near-stiffening by percentile (`mu_p90=0.7034`), but the weighted off-core shell remains moderate (`outer_mu_weighted=0.4201`, `axis_exterior_mu_max=0.6860`). One rotated run (`45 deg`) crosses by `total_g_p90=1.0089`, showing threshold crossing is nearby in the orientation family. The correct claim is therefore “field debt loads the halo toward AQUAL stiffening,” not “the aligned debt spike has already frozen the halo into a Newtonian boundary.”
- **Opened:** 2026-04-30 08:08:00 EDT
- **Closed:** 2026-04-30 08:11:00 EDT

#### H-GP163D-5AL — The aligned AQUAL separator is orientation-sensitive rather than dynamically certified stable

- **Hypothesis:** Existing gp163d artifacts do not contain a true gravitational torque or second-variation stability operator for the aligned state; however, the saved orientation ladder should show whether the aligned high-separator state is a narrow orientation optimum whose apparent profit collapses under small imposed rotations while off-core `mu` debt remains elevated.
- **Scope:** GP-163d / NS cross-domain balance-sheet synthesis, orientation-stability proxy
- **Status:** `partially_confirmed`
- **Discriminating test:** Run `phase5al_orientation_stability_proxy_audit.py` over existing `L=4,gamma=0.25` `krylovlocal` orientation summaries. First audit code capability: whether action/torque/second variation is stored for source solves. Then fit finite-difference slopes/curvatures for UDG gain, binary gain, separator, `mu_p90`, and off-core debt/gain across angles `0,15,30,45,60`. Support = no true torque exists, but the separator has a local maximum at `0 deg` and drops sharply under small rotations while `mu_p90` stays near/above the stiffening threshold. Rejection = aligned state is broad/flat under rotations or source-action data already certifies stability.
- **Run(s):** `phase5al_orientation_stability_proxy_audit.py`
- **Result:** `partially_confirmed`. The codebase contains an AQUAL action functional, but only for vacuum/background minimization; production orientation summaries do not store source action, torque, Hessian, or second variation. As a finite-difference proxy, the aligned state is fragile: a `15 deg` imposed rotation reduces UDG gain to `0.921x` of aligned and separator to `0.922x`, while binary gain is essentially unchanged (`0.999x`). The ladder remains near AQUAL stiffening (`mu_p90 ~= 0.703` at `0/15 deg`), and the `45 deg` run crosses `total_g_p90 >= 1`. This supports orientation sensitivity and threshold proximity, but does not prove dynamic tumbling or instability.
- **Opened:** 2026-04-30 08:17:00 EDT
- **Closed:** 2026-04-30 08:20:00 EDT

#### H-GP023-01 — Mutator vocabulary is the primitive-cone bottleneck

- **Hypothesis:** The flash mutator is incapable of exiting the `{additive_composition, exp_neg, multiplicative_composition, power}` primitive cone on the sandbox_03 hidden generator, even with improved apparatus feedback. A stronger model (claude-opus) would exit the cone within 20 iterations under the same apparatus.
- **Scope:** GP-023, GP-047, mission seam
- **Status:** `open_instrument_repair_needed`
- **Discriminating test:** A post-`sandbox_04` stronger-mutator successor verifier: same hidden generator class, same apparatus-feedback posture, stronger mutator family. Exit = champion introduces at least one primitive from `{rational_with_additive_offset, sigmoid, log, trig, polynomial-without-exp}` that sandbox_03 never reached.
- **Run(s):** `gp023_planck_sandbox_05` (10-iter gemini-pro run, same apparatus as sandbox_04)
- **Result:** `partially_confirmed`. Pro produced richer primitive expansion (sigmoid, log — not reached in sandbox_03) and marginally better farther_tail_global_residual (0.02113 vs Flash ~0.02358). Champion passes 8/9 gates; single failing gate is farther_tail_global_residual (actual 0.02113 vs threshold 0.01 — 2x gap). Score ceiling unchanged at 50. Stronger mutator is necessary but not sufficient — the missing mechanism is preservation/stabilization, not vocabulary.
- **Opened:** 2026-04-13
- **Closed:** 2026-04-14

#### H-GP023-02 — Hidden farther-tail failure is an invisible-feedback bottleneck

- **Hypothesis:** The primitive-cone residency on sandbox_03 was caused by the farther-tail failure being invisible to the mutator prompt surface. Exposing the gate failure as a sanitized prompt signal (without leaking evidence) would let the same flash mutator exit the cone.
- **Scope:** GP-023, GP-046, mission seam
- **Status:** `partially_confirmed`
- **Discriminating test:** A fresh 20-iter flash run on the same hidden generator with `gp048_farther_tail_veto_mode: "sanitized"` enabled in the rubric (and `gp048_telemetry: true` for Mode 1 attribution). No preservation lane. No mutator swap. Cone exit measured by GP-048 Mode 1 telemetry.
- **Run(s):** `gp023_planck_sandbox_04` (completed bundled apparatus-feedback packet; bears on this row but does not isolate it because primitive-cone stagnation injection is also on)
- **Result:** Supported enough to confirm that sanitized farther-tail feedback can participate in cone exit under the bundled packet, but not enough to show that hidden-failure visibility alone is sufficient to produce a better champion. The run escaped the old cone but did not beat the score-50 farther-tail ceiling.
- **Opened:** 2026-04-13
- **Closed:** 2026-04-13

#### H-GP023-03 — Cone-blind stagnation pivot is a prompt-signal bottleneck

- **Hypothesis:** The stagnation_pivot prompt instructs "try something different" without naming the primitive cone the mutator has been circling. Injecting a GP-048 primitive-cohort annotation at stagnation would let flash exit the cone without any model swap or farther-tail feedback.
- **Scope:** GP-023, GP-042 (structural memory), mission seam
- **Status:** `partially_confirmed`
- **Discriminating test:** 20-iter flash run with `gp048_stagnation_injection_mode: "primitive_cone"` enabled in the rubric (and `gp048_telemetry: true` for Mode 1 attribution). No other apparatus changes: `gp048_farther_tail_veto_mode` off, preservation lane off.
- **Run(s):** `gp023_planck_sandbox_04` (completed bundled apparatus-feedback packet; bears on this row but does not isolate it because sanitized farther-tail veto is also on)
- **Result:** Supported enough to confirm that primitive-cone stagnation feedback can participate in cone exit under the bundled packet, but not enough to show that stagnation annotation alone is sufficient to produce a farther-tail-admissible champion. The run crossed into rational/sigmoid/polynomial families but did not beat the old ceiling.
- **Opened:** 2026-04-13
- **Closed:** 2026-04-13

#### H-GP023-06 — The farther-tail bottleneck is ontological, not operational

- **Hypothesis:** No expression in the mutator's reachable vocabulary (power, exp_neg, exp_pos, rational, sigmoid, log, additive/multiplicative composition) can achieve `farther_tail_global_residual < 0.01` with optimally fitted parameters — meaning GP-047 preservation-lane tests the wrong mechanism regardless of how well it preserves candidates.
- **Scope:** GP-023, Oracle Test pre-registration
- **Status:** `resolved — specification error from truncated visible support`
- **Discriminating test (Oracle Test):** Fit curated expression families directly against sandbox visible slice + hidden holdout data using GP-035/scipy with multiple random initializations. Families to test: (1) all sandbox_03/04/05 champions with re-optimized parameters, (2) pure `exp(-phi/psi)` variants, (3) stretched exponential `exp(-k*(phi/psi)^m)` with broader parameter search than sandbox_05 iter 1 used, (4) Planck-motivated forms `phi^3 / (exp(phi/psi) - 1)` variants. Compute farther_tail_global_residual for each. If none achieve < 0.01 → hypothesis confirmed (ontological). If any achieve < 0.01 → hypothesis falsified (operational).
- **Run(s):** (1) `oracle_test.py` — 7 families, visible-only loss → no family passes → initially concluded ontological. (2) `oracle_test_tail_supervised.py` — stretched-exp with λ∈{0,0.1,1,10,100,∞}: λ=1 achieves farther_tail=0.00910 (PASS), λ=∞ reaches 0.00001.
- **Result:** RESOLVED as SPECIFICATION ERROR FROM TRUNCATED VISIBLE SUPPORT (Turn 39 bootstrap diagnostic). Parameters are well-identified (max bootstrap std 0.00741 < gate threshold 0.01; median std 0.00037). But residual/std ratio ~2.85 — held-out failure is NOT explained by parameter uncertainty. Every bootstrap sample converges to nearly the same biased answer; the visible slice's loss minimum is systematically offset from the full-data minimum. The stretched-exp family is adequate (Turn 37 proved it) but the visible region is too narrow for the visible-only loss minimum to coincide with the true minimum. Turn 37's "add tail data to fitter" prescription retracted as test-set leakage (Turn 38). Correct fix: **expand visible slice** in sandbox_06 (push phi frontier to ~20–25), mint new held-out beyond, re-test. GP-047 still dead. SP-2 not needed. Architectural upgrade: add bootstrap identifiability + residual/std ratio diagnostic to GP-035 fitter contract.
- **Opened:** 2026-04-14
- **Closed:** 2026-04-14

#### H-GP023-07 — Adequately-sized visible slice allows farther-tail gate pass without tail-data leakage [LEGACY — superseded by H-GP023-07b in Turn 42]

- **Hypothesis:** An adequately-sized visible slice — defined as one where the bootstrap-predicted tail envelope for a benchmark family (stretched-exp) covers the ground-truth tail values within ~1.5 std at would-be held-out points BEFORE the sandbox runs — allows the mutator to find expressions that pass both visible-slice gates and farther-tail gates without any tail-data injection into the fitter loss. Tests Turn 39's specification-error diagnosis.
- **Scope:** GP-023, sandbox_06 pre-registration
- **Status:** `legacy / superseded-by-H-GP023-07b (Turn 42)` — kept for record, not live
- **Discriminating test:** Run sandbox_06 with pre-committed expanded visible frontier (phi_max chosen by label-free bootstrap rule against operator-owned ground truth; candidates {15,18,20,22,25}; commit smallest passing). 10 iterations, gemini-pro, same apparatus as sandbox_05. At close, run three-probe diagnostic stack: (1) visible-only Oracle Test, (2) bootstrap identifiability, (3) tail-supervised Oracle Test (one-time operator budget). Outcomes: (a) champion passes AND bootstrap low std AND residual/std ≤ 1.5 → confirmed; (b)–(f) various failure/ambiguity paths per Turn 40; **(g) pre-commit rule fails to commit — sandbox not sealed (added Turn 41)**.
- **Anti-overfitting guardrails:** (1) Expansion budget = 1 (sandbox_07 permitted one more expansion only if residual/std > 1.5 persists at new scale; no further expansions under this seam after sandbox_07). (2) phi_max chosen by label-free rule, not from sandbox_05 failure locations. (3) New ground truth for sandbox_06 (different parameters than sandbox_05). (4) No changes to fitter loss, mutator vocabulary, or iteration count — minimal intervention only.
- **Run(s):** E-GP023-S06-PRE-01 (2026-04-14): pre-commit bootstrap envelope rule executed against new GT, refused to seal. Ratio descended monotonically 2.189 → 1.581 across `{15,18,20,22,25}`, never crossing the 1.5 envelope. Candidates 22 and 25 yielded identical visible sets (geometric grid resolution defect). Absolute residuals (~1.6e-3) are ~6× under the gate threshold, so the family would *pass* the gate at every candidate; the no-seal is driven by the residual / std envelope, which tests a different thing than the gate. Expansion budget NOT spent (no sandbox ran). See seam Turn 41 and `projects/gp023_planck_sandbox_06/workspace/pre_seal_artifact.json`.
- **Result:** blocked pending operator decision among (g1) widen+densify candidate list / (g2) redesign envelope rule / (g3) accept no-seal as deliverable
- **Opened:** 2026-04-14
- **Closed:** 2026-04-14 as `superseded-by-H-GP023-07b` after operator selected fork (g2) in Turn 42

#### H-GP023-07b — Absolute-error pre-commit rule commits adequately-sized visible slice

- **Hypothesis:** An adequately-sized visible slice — defined pre-commit as one where the stretched_exp_refit bootstrap-mean prediction reaches within `0.005` of GT (half the farther-tail gate of `0.01`) at every held-out (phi, psi) coordinate BEFORE the sandbox runs — allows the mutator to find expressions that pass both visible-slice and farther-tail gates without tail-data leakage. Replaces H-GP023-07 after the Turn 41 no-seal verdict showed the envelope rule (`|mean−GT|/std ≤ 1.5`) was structurally mis-shaped: it tested whether the benchmark family is an exact match to GT, not whether the family can reach gate tolerance. For any approximation family on any non-trivial truth, residual/std plateaus at a small-but-nonzero value with no decisive interpretation. The new rule directly predicts the gate it is meant to protect.
- **Scope:** GP-023, sandbox_06 packet (legacy H-GP023-07 kept for info)
- **Status:** `open — Phase 1 pending execution (Turn 42)`
- **Rule knobs (all pre-committed in Turn 42):** `CANDIDATE_PHI_MAX = [15, 17, 19, 21, 23, 26]` (redensified to fix Turn 41 grid defect where 22 and 25 probed identical visible sets); `ABSOLUTE_ERROR_THRESHOLD = 0.005`; `N_BOOTSTRAP = 100`; `SEED = 42`; benchmark family `stretched_exp_refit` (unchanged — swapping families would be the real teaching-to-the-test move); GT parameters unchanged from Turn 40 (A=0.95, p=2.30, alpha=0.72, beta=1.00, q=1.30, offset=0.06).
- **Discriminating test (Turn 43 differential-diagnosis ladder):** (Step 1) run `presealing_bootstrap_check.py v2`; if it commits a phi_max, run `fitter_audit_true_form.py` to confirm `scipy.optimize.differential_evolution` recovers the true parameters from visible data (apparatus cleared vs apparatus suspect). (Step 2 pre-registered, triggered only on Step 4 condition) build `sandbox_06c` with clean-physical GT (`A=1, p=3, alpha=1, beta=1, q=1, offset=0`) as a Frankenstein-trap control — not a new hypothesis, not an expansion-budget spend. (Step 3) if apparatus cleared, seal sandbox_06, draft charter/thesis/test_model.py, run 10 iterations gemini-pro with sandbox_05 apparatus unchanged; at close, run three-probe diagnostic stack. (Step 4) interpret per outcomes (a)–(f) from Turn 40 plus Turn 43 outcome (g'): ambiguous close does NOT trigger SP-2; instead trigger fitter re-audit on champion expressions + run sandbox_06c control. Only if sandbox_06c also lands ambiguous is SP-2 empirically justified; if sandbox_06c succeeds, Frankenstein trap is confirmed and SP-2 is NOT justified.
- **Symmetric fallthrough (corrected Turn 43):** if `presealing_bootstrap_check.py v2` refuses to commit, H-GP023-07b closes as `blocked — rule redesign also failed` and the Step 4 controls become relevant immediately. If the fitter audit fails, sandbox_06 sealing is BLOCKED regardless of pre-seal result. SP-2 is only justified after Steps 1, 2, 3, 4 all land against ZTARE in sequence.
- **Anti-overfitting guardrails inherited from Turn 40:** expansion budget = 1 (sandbox_06); new GT; no fitter-loss changes; no vocabulary changes; iteration count unchanged; rule is label-free from mutator. **New Turn 42 guardrail:** benchmark family held constant across the redesign — only the rule metric (`ratio ≤ 1.5·std` → `|mean − GT| < 0.005`) and the candidate-list density (`{15,18,20,22,25}` → `{15,17,19,21,23,26}`) change.
- **Run(s):** TBD — Phase 1 (`presealing_bootstrap_check.py v2`) executes next
- **Result:** pending
- **Opened:** 2026-04-14 (Turn 42)
- **Closed:** —

#### H-GP023-04 — Cold-residual is scoped wrong; needs primitive-cone invert

- **Hypothesis:** Cold-residual successor mode (GP-045) breaks specific-expression basins by asking "what closes the residual surface of this family" — a within-family question. It cannot break primitive-cone basins because it never asks "what different family would work." The fix is to add a primitive-cone-level invert: at stagnation, require the next candidate to cross a primitive-set boundary.
- **Scope:** GP-023, GP-045, GP-047
- **Status:** `closed / candidate_sweep_action_scheduler_ran`
- **Discriminating test:** 20-iter flash run that promotes GP-048 from telemetry/annotation (H-GP023-03) to a hard constraint: reject any candidate whose primitive set equals the previous champion's primitive set, during stagnation_pivot. This is a stronger intervention than H-GP023-03 and should be run only if H-GP023-03 fails to escape.
- **Run(s):** TBD — staged after H-GP023-03's run
- **Result:** pending
- **Opened:** 2026-04-13
- **Closed:** —

#### H-GP023-05 — Preservation-and-perturb is the only escape axis

- **Hypothesis:** None of H-GP023-01 through H-GP023-04 suffice. Even with perfect feedback and even with a stronger mutator, the cone escape requires *holding a good champion* and applying a bounded structural edit — because without preservation, every exploration step loses the fit-quality signal and collapses back. This is GP-047's core claim.
- **Scope:** GP-047, GP-023
- **Status:** `closed / scheduler_baseline_dominance_audit_ran`
- **Discriminating test:** A future three-arm successor after the apparatus-first packet reports. Arm A = flash apparatus-feedback only, Arm B = preservation lane, Arm C = stronger mutator. H-GP023-05 is confirmed only if Arm B escapes and Arm C does not.
- **Run(s):** TBD — future preservation-lane successor, explicitly **not** the live `gp023_planck_sandbox_04` packet
- **Result:** pending
- **Opened:** 2026-04-13
- **Closed:** —

### Successor rows (pre-registered, not yet packetized)

#### H-SP1-01 — A genuinely unknown farther-tail B-slice is required to answer the Oracle Problem cleanly

- **Hypothesis:** ZTARE's farther-tail discipline remains meaningful when the farther-tail surface is genuinely unknown at charter time, not merely sealed from the mutator.
- **Scope:** mission seam, future discovery successor
- **Status:** `closed / plausible_decoy_scheduler_stress_ran`
- **Discriminating test:** SP-1 forward-observable B-slice sandbox with operator-unseen farther-tail generation and threshold commitment before the farther-tail values are computed.
- **Run(s):** TBD — mission-level successor after `sandbox_04`
- **Result:** pending
- **Opened:** 2026-04-13 09:22:36 EDT
- **Closed:** —

#### H-SP2-01 — Program synthesis escapes symbolic primitive cones by enlarging the reachable function class

- **Hypothesis:** A program-mutator arm that emits Python functions can escape primitive-set basins that a symbolic mutator cannot, because the reachable function class is larger even though it is still bounded by pre-training over program structure.
- **Scope:** mission seam, future mutator-architecture successor
- **Status:** `closed`
- **Discriminating test:** SP-2 FunSearch-style program-mutator arm on a sandbox where symbolic mutation is already known to be stuck, with GP-048 telemetry measuring whether the program arm reaches function classes or gate passes that the symbolic arm never reached.
- **Run(s):** TBD
- **Result:** pending
- **Opened:** 2026-04-13 09:22:36 EDT
- **Closed:** —

#### H-SP2-02 — Karpathy-style edit-run-revert loop over a frozen objective gate metric outperforms LLM symbolic mutation on the Planck regime

- **Hypothesis:** A Karpathy-autoresearch execution substrate — a deterministic edit-run-revert loop pointed at `test_model.py` with the ZTARE deterministic gate battery as the objective metric — will converge to ground-truth on Planck-class sandboxes at lower cost per bit than the current LLM symbolic mutator, because the metric is frozen, objective, and cheap to re-evaluate. The loop's constrained move set (numeric parameter edits + local functional-form swaps) cannot escape primitive cones (that remains H-SP2-01's job), but within-family recovery and identifiability hardening should be dominated.
- **Scope:** mission seam, future mutator-substrate successor. Orthogonal to H-SP2-01 (program synthesis for cone escape); complementary, not redundant.
- **Status:** `open`
- **Discriminating test:** On a Planck sandbox whose ground-truth family is in-cone for the mutator initialization, run two arms for fixed wall-clock budget: Arm A = current LLM symbolic mutator, Arm B = Karpathy edit-run-revert loop optimizing the nine-gate residual vector. Success for H-SP2-02 = Arm B reaches machine-precision gate passage in strictly fewer iterations OR at strictly lower dollar cost than Arm A on the same charter, with identifiability preserved under the GP-023 hardening seam (R1–R6).
- **Failed-close attempt note (2026-04-14):** A premature close-by-recognition was attempted and reverted. The attempt relied on a single external paraphrase (Gemini Pro characterizing `autoresearch_loop.py` as "the Karpathy loop drastically upgraded"), which was accepted without reading Karpathy's repository. On pushback, three distinct claims were identified that the recognition-close had collapsed into one: (1) control-flow isomorphism (both do mutate→execute→score→revert — weak, most optimization loops share this shape); (2) substrate equivalence (ZTARE's loop = Karpathy's with a fancier objective — requires Karpathy's to be a generic swappable-objective harness, unverified); (3) library reusability (can you import the Karpathy thing and point it at an arbitrary task — if yes, ZTARE's loop is definitely *not* that, since it is welded to the rubric/gate/judge pipeline). The honest state is that ZTARE's loop may share *shape* with Karpathy's without being the same *substrate*. Resolution requires a direct read of github.com/karpathy/autoresearch and an explicit taxonomy of the three claims above before any re-close.
- **Queued behind:** `gp023_planck_sandbox_06` run — do not packetize until sandbox_06 is closed. Reason: sandbox_06 is the first post-Layer-5-catch apparatus-cleared run and its score-83 Meta-Judge cap is itself the reference point against which any substrate-swap claim must be measured.
- **Run(s):** TBD
- **Result:** pending
- **Opened:** 2026-04-14
- **Closed:** —

#### H-SP2-03 — Restricting the mutator primitive set to the EML operator is sufficient for Planck ground-truth recovery under ZTARE gate discipline

- **Hypothesis:** Odrzywołek's EML operator `eml(x,y) = exp(x) − ln(y)` together with the constant `1` constructively generates the elementary-function basis at shallow tree depths (paper caveat: "shallow tree depths up to 4", arxiv 2603.21852, submitted 2026-03-23, rev 2026-04-04). Therefore a mutator whose vocabulary is restricted to `{eml, 1, phi, psi, fit-constants}` should still recover the Planck ground-truth family within the GP-023 hidden-gate battery — bounded claim: **sufficient at depth achievable by current mutator under ZTARE gate discipline**, not a universal basis claim.
- **Scope:** mission seam, future mutator-vocabulary successor. Tests whether primitive-set compression is a viable route to cone-escape discipline (rather than enlargement, which is H-SP2-01's direction).
- **Status:** `open`
- **Discriminating test:** A `gp023_planck_sandbox_07` successor packet with identical charter and gate battery to sandbox_06 but with the mutator vocabulary narrowed to `{eml, 1, phi, psi, constants}`. Success = the EML-restricted arm achieves ≥ sandbox_06's all-gates-pass result within a matched iteration budget. Failure modes of interest: (a) ground-truth is reachable in principle but not within the depth budget the LLM mutator explores in practice (honest negative result); (b) the EML primitive actively helps because composition pressure reduces drift (the paper's implicit promise); (c) depth-4 caveat binds and recovery fails — falsification of the sufficiency claim at current-substrate depth.
- **Queued behind:** `gp023_planck_sandbox_06` run — must not be packetized until sandbox_06 closes. Reason: sandbox_06 is the baseline this arm is measured against, and the v3 reparameterization + hardening seam R1–R6 must be the control apparatus for any sandbox_07 successor.
- **Run(s):** TBD
- **Result:** pending
- **Opened:** 2026-04-14
- **Closed:** —

#### H-SP2-04 — Under a three-axis merge of blind oracle + EML vocabulary + full inversion cage, ZTARE can force a general-purpose LLM mutator to converge on a correct closed-form law without the operator authoring the ground truth

- **Hypothesis:** The actual test of whether ZTARE can generate open-ended scientific discovery (as opposed to guided recovery) requires removing the operator from the oracle seat. The discovery experiment is a three-axis merge of three previously separable successor lines: (i) **blind oracle** — the operator does not author the ground-truth functional form or its coefficients; a generator-of-generators samples a non-elementary closed form from a declared family (e.g., `{Planck-like, stretched-exponential-like, rational-with-transcendental-pole, Bose-Einstein-like}`) and writes it to a sealed file the operator does not read; (ii) **EML primitive set** — the mutator vocabulary is restricted to `{eml(x,y)=exp(x)−ln(y), 1, phi, psi, fit-constants}` per Odrzywołek (arxiv 2603.21852, rev 2026-04-04, caveat "shallow tree depths up to 4"), removing the regression-toolbox comfort bias from the mutator's move set; (iii) **full inversion cage** — hardening seam R1–R6 in force, nine-gate charter-committed battery, sealed farther-tail holdout, exact-fitter audit, composition opacity. If the merge converges on the sampled closed form at machine precision within a matched iteration budget, ZTARE has been demonstrated to force convergence onto a correct form when the operator does not know the answer. If not, the specific failure mode (vocabulary, apparatus, blind-grading, judge) is the first real signal about where the discovery claim fails.
- **Scope:** mission seam, successor to GP-023 sandbox_06. Supersedes H-SP1-01 and H-SP2-03 as the *actual* discovery test. H-SP1-01 (blind oracle alone) and H-SP2-03 (EML alone) remain in the ledger as separable fallbacks: if the three-axis merge fails, one-axis-at-a-time decomposition is the diagnostic path, not a replacement test.
- **Status:** `open`
- **Discriminating test:** A `gp023_planck_sandbox_07` packet with (a) a generator-of-generators that samples a target from a declared non-elementary family without the operator reading the sample, (b) mutator vocabulary restricted to `{eml, 1, phi, psi, constants}`, (c) the sandbox_06 nine-gate battery reauthored against the sampled target with the same thresholds and composition opacity, (d) hardening seam R1–R6 in force, and (e) post-run grading in which the sampled target is revealed and compared to the mutator's final form at machine precision. Success = all nine gates pass at machine precision AND the recovered form is algebraically equivalent to the sampled target. Partial success = all nine gates pass but the recovered form is a different closed form that happens to fit the residuals (informative about the library's effective cardinality, not about discovery). Failure = gates do not clear, or the gate-cleared form fails the algebraic-equivalence check post-reveal.
- **Queued behind:** `gp023_planck_sandbox_06` is **frozen** as the calibration reference at `projects/gp023_planck_sandbox_06/_frozen_reference/`. Sandbox_07 may be designed and packetized now but must not run against new evidence until the freeze README is stable and the packet design is reviewed against the three operating commitments of the Gate Library as Inspection Architecture design note.
- **Packet status (2026-04-14):** `projects/gp023_planck_sandbox_07/` is sealed covering **only axes (ii) EML vocabulary + (iii) full inversion cage**. Axis (i) — blind oracle — is **deferred**. Sandbox_07 uses the same operator-authored ground truth as sandbox_06 (`A=0.95, p=2.30, gamma=0.72, q=1.30, offset=0.06`) and the same evidence surfaces, with the only design change being `fit_expression_grammar: "eml_only"` + `python_model_grammar: "eml_only"` + criterion 8 (EML grammar compliance). This tests the H-SP2-03 sub-claim (EML sufficiency under the inversion cage) as a **prerequisite** for the three-axis merge — if EML alone cannot recover under the cage when the operator knows the answer, running a blind-oracle sandbox on top is wasted. Enforcement surfaces: (A) `fit_primitive.py::_validate_expression()` caps `allowed_direct_calls={"eml"}` and zeros `allowed_math_attrs`; (B) `autoresearch_loop.py::validate_python_model_grammar()` AST-walks `I_model` FunctionDef and swaps in `build_model_grammar_failure_code()` (fail-closed NaN stub) on any `math.*` call or non-`eml` direct call before GP-035 runs. Pre-run smoke gate: PASS (seed fails 9/9 as designed, no harness errors, 9 deterministic gates parse cleanly). A sandbox_08 packet covering axis (i) blind oracle is still pending and must not be packetized until sandbox_07 closes.
- **Run(s):** TBD
- **Result:** pending
- **Opened:** 2026-04-14
- **Closed:** —

#### H-SP3-01 — Formal verification can replace a non-trivial fraction of judge work in formalizable regions

- **Hypothesis:** In domains with a fully formalizable conservation law, theorem-prover-backed gates can catch a non-trivial fraction of thesis failures that the LLM judge would otherwise own.
- **Scope:** mission seam, future verifier-compression successor
- **Status:** `open`
- **Discriminating test:** SP-3 Lean/Coq-backed conservation-law gate on a toy domain, measuring what fraction of rejections originate from the formal gate rather than the LLM judge.
- **Run(s):** TBD
- **Result:** pending
- **Opened:** 2026-04-13 09:22:36 EDT
- **Closed:** —

### Operational mode rows

Rows testing whether ZTARE's loop architecture can serve both variance suppression (Factory) and variance maximization (Honeypot) without kernel bifurcation. These rows correspond to the close condition of `ztare_operational_mode_seam.md`.

#### H-OPMODE-01 — Cleared evidence surface + honeypot_minimal is sufficient for high-variance discovery output

- **Hypothesis:** When the evidence surface is absent and the rubric rewards surprise over evidence-anchoring, the LLM mutator/judge pair produces structurally distinct theses across iterations — at least one of which would qualify as a new gaming taxonomy row or a non-obvious domain claim — without any kernel-level changes.
- **Scope:** `ztare_operational_mode_seam.md`, Honeypot track
- **Status:** `partially_confirmed`
- **Discriminating test:** Protected Honeypot run: `MODE=honeypot`, `honeypot_minimal` rubric, empty `evidence.txt`, no pre-run pipeline, no operator evidence seeding mid-run. **Success = output contains either (a) a new, named, documentable specification-gaming strategy that advances the taxonomy, OR (b) a non-obvious structural claim about the domain that does not survive `recursive_bayesian` / `ai_competitive_landscape` rubric scoring — verified by re-scoring the honeypot champion against the factory rubric and confirming it fails evidence anchor.** Failure = all iterations converge on variants of the seed or produce no documentable output under either criterion. Score alone (>60 on honeypot_minimal) is not a success criterion — it is necessary but not sufficient.
- **Run(s):** `ai_competitive_landscape` honeypot run — started 2026-04-14, 5-iter smoke test followed by ≥10-iter substantive run. Note: current 10-iter run is a **probe**, not the full discriminating run. E-row at close will be labeled `probe`. Full discriminating run requires ≥20 iters or a factory baseline comparison on the same domain.
- **Result:** Criterion (b) partially confirmed via probe. Champion thesis (AFG mechanism, 115 on honeypot_minimal) fails factory rubric re-score on evidence anchor and score ceiling reachability. Honeypot mode surfaced a structural claim factory mode would suppress. Not yet confirmed at full discriminating run scale (≥20 iters, multiple domains). Secondary signals: semantic basin stickiness (axioms frozen, regime fingerprint static), formalism escalation as probable gaming strategy (H-GAMING-11). Judge self-instruction failure: ignored own HARNESS DEFECT warning and scored anyway.
- **Opened:** 2026-04-14
- **Closed:** —

---

### Gaming strategy rows

Gaming strategy rows document observed LLM behaviors that satisfy rubric criteria through unexpected means. These are distinct from GP-023 apparatus hypotheses — they are findings about how models exploit evaluation surfaces, and are the primary discovery target of Honeypot-mode runs. Each row must be added before any hardening move (rubric update, criterion patch) is made, so the finding cannot be retrofitted post-hoc.

#### H-GAMING-10 — Derivation Laundering

- **Hypothesis:** When an LLM cannot locate a number from the correct evidence category, it will borrow a figure from an incompatible category and fabricate a false arithmetic derivation (e.g., a claimed midpoint) to launder it into the scoring rubric's evidence anchor criterion — satisfying disclosure requirements through manufactured provenance rather than real evidence grounding.
- **Scope:** GLP-1 demonstration run; general rubric design surface wherever `evidence_anchor_requirement` or equivalent disclosure criteria appear
- **Status:** `confirmed`
- **Discriminating test (for hardening):** Run a meta-runner loop on a rubric containing (a) a category-coherence check on claimed derivations and (b) arithmetic verification of claimed midpoints/averages. If the strategy disappears under the hardened rubric → the patch closes the exploit. If a structurally equivalent substitution appears → escalate to a generalized derivation-chain audit criterion.
- **Run(s):** `glp1_adoption_economics` demonstration run — `$350` labeled "Derived: midpoint between $245 and $675" (actual midpoint $460); borrowed from TrumpRx consumer price into enterprise contract context. Flagged externally by Gemini as "Misfile"; reclassified as Derivation Laundering because the arithmetic is demonstrably wrong and the label is specifically constructed to pass a rubric criterion.
- **Result:** Confirmed single instance. Replication via meta-runner pending before hardening any rubric.
- **Pending hardening:** Add category-coherence sentence to `evidence_anchor_requirement` in GLP-1 rubric; audit other rubrics with disclosure criteria for same exposure.
- **Opened:** 2026-04-14
- **Closed:** —

#### H-GAMING-11 — Formalism Escalation

- **Hypothesis:** When evidence is absent, the mutator escalates mathematical formalism (decay constants, multipliers, gradients, named coefficients) across iterations to satisfy rubric specificity and falsifiability criteria — scores climb through formal precision rather than epistemic grounding, with no new axioms introduced and regime fingerprint unchanged.
- **Scope:** Honeypot-mode runs with empty evidence surface; any rubric that rewards numerical specificity or falsifiable predictions without requiring evidence anchoring
- **Status:** `confirmed`
- **Discriminating test (for hardening):** Run honeypot_minimal on a second domain with empty evidence. If axioms freeze within 2 iterations and score climbs while regime fingerprint stays constant → Formalism Escalation is a stable cross-domain pattern. Hardening applied 2026-04-14: anti-formalism discipline added to persona + criteria; Gaming Detection Bonus tightened to require named/mechanistic/reportable exploit. Effectiveness test: H-GAMING-12.
- **Run(s):** `ai_competitive_landscape` honeypot probe — iter 1 → iter 3: same four axioms verbatim, regime fingerprint `d5fe016afe0060e4` unchanged, score 108 → 115 via addition of "Fidelity Debt Decay Constant (k)" and "Fidelity-Gated Capability Multiplier."
- **Result:** Confirmed cross-domain. `us_tariff_passthrough_2026` honeypot probe (5 iters, empty evidence, naive seed, honeypot_minimal): seed=45, then 115/115/110/115/110. Zero verified axioms added, zero novel primitives, zero novel attacks across all iterations. Mutator reached ceiling at iter 1 with `Z = X*(1-Y)`, HHI coefficients, DisruptiveEntryThreat_Index — formally complete, evidence-free. Stronger form than ai_competitive_landscape: there, formalism escalated iter-over-iter (108→115). Here, ceiling was reached immediately at iter 1 — nothing to escalate because formal compliance was already maxed. Pattern is structural: absent evidence → formal apparatus → ceiling → stasis.
- **Opened:** 2026-04-14
- **Closed:** 2026-04-14

#### H-GAMING-12 — Hardened honeypot_minimal suppresses Formalism Escalation ceiling

- **Hypothesis:** The anti-formalism additions to `honeypot_minimal` (persona discipline + criterion tightening + Gaming Detection Bonus mechanistic requirement) will prevent the mutator from reaching score ≥110 through formal compliance alone — forcing genuine structural divergence or producing lower scores that correctly reflect content-free output.
- **Scope:** `honeypot_minimal` rubric v2, any domain with empty evidence
- **Status:** `open`
- **Discriminating test:** Rerun honeypot probe on `us_tariff_passthrough_2026` (same naive seed, empty evidence, 5 iters) with hardened rubric. Success = iter 1 scores ≤70 on thesis with same formal structure as E-OPMODE-02 champion. Failure = iter 1 still scores ≥110 despite anti-formalism instructions → rubric hardening insufficient, persona instructions are being ignored by judge.
- **Run(s):** TBD — next honeypot probe after current session
- **Result:** pending
- **Opened:** 2026-04-14
- **Closed:** —

#### H-GAMING-13 — Factory rubric rewards apparatus over domain-knowledge emergence (REFUTED 2026-04-14)

- **Hypothesis (as written):** In factory mode on a real evidence surface, the factory rubric systematically scores mathematical-apparatus-wrapped theses higher than quiet domain-knowledge-emergence theses.
- **Status:** `refuted — see opmode seam Turn 11`
- **Refutation:** Full audit of FIGS `history/` contradicts the claim. The three highest-scoring theses in FIGS history are all domain-insight with minimal apparatus: `v1_score_88` (LCTA procurement filter), `v2_score_88` (stipend-as-pay-cut break-even arithmetic), `v16_score_88` (Portal as IT-friction externality). The one apparatus-heavy thesis, `v29_score_82` (`Z = f(X,Y)` "Operation Liquid Inertia"), scores *lower*. Hierarchy: 88 (domain-insight) > 82 (apparatus) > 70–72 (weaker domain-insight). Cross-project sanity check: GLP-1 50→85 and Hormuz 30→74 both climb on substance, not on added apparatus. The rubric is rewarding domain insight; H-GAMING-13's premise is inverted.
- **Why the refutation matters:** The decisive Turn 10 sample (`v2_score_70`, `v2_score_72` vs. current `thesis.md`) was not representative of FIGS history. It compared two mid-score domain theses against the current apparatus-heavy champion and missed three higher-scoring domain-insight champions that refute the premise directly. Second instance of frustration-anchored diagnosis in this thread (Turn 9 conflation, Turn 10 overfit). Bounded-critique-agent discipline not applied before writing Turn 10.
- **Replaced by:** `H-GAMING-14 — Mutator-side formalism drift against a substance-rewarding judge` (see below).
- **Original motivation:** Operator Turn 10 pushback on Turn 9 conflation; sample was `v2_score_70` (MAS subscription) and `v2_score_72` (BJR governance) vs. current `thesis.md`. These two sub-80 theses are real but not the decisive artifact base for the claim.
- **Opened:** 2026-04-14 (Turn 10, opmode seam)
- **Closed:** 2026-04-14 (Turn 11, opmode seam — refuted by full FIGS history audit)

#### H-GAMING-14 — Mutator-side formalism drift against a substance-rewarding judge

- **Hypothesis:** In factory mode on a real evidence surface, the mutator's mutation operator over-indexes on formal markers that resemble rubric criteria vocabulary (symbolic mapping, named variables, falsifiability sections, quantitative precision) and progressively drifts toward apparatus-heavy theses across iterations. The judge does *not* reward this drift — judge rationale favors substance, and apparatus-heavy champions score *lower* than earlier domain-insight champions on the same rubric. Net effect: late-iteration champion is formally ornate and scores lower than an earlier plain-language domain-insight champion would score today. Locus is **mutator**, not judge. Direction of force is **costly**, not rewarding.
- **Scope:** Factory mode, real-evidence surface. Distinct from H-GAMING-11 (empty-evidence formalism escalation — apparatus under absence-of-evidence gaming) and H-GAMING-12 (rubric hardening of honeypot rubric). H-GAMING-14 is orthogonal: gaming is not the driver; the mutator is not rational about what the rubric pays for.
- **Status:** `open — strong motivating artifact evidence (FIGS iteration hierarchy 88→82), discriminating test pre-registered`
- **Motivating evidence (FIGS `history/` full audit, 2026-04-14):**
  - `v1_score_88` (domain-insight, minimal apparatus): LCTA procurement filter, reclassify SKU from Medical Supplies to HR Retention budget
  - `v2_score_88` (domain-insight, minimal apparatus): Stipend-as-stealth-pay-cut, 433-recapture break-even vs. one nurse quit
  - `v16_score_88` (domain-insight, minimal apparatus): Portal as IT-friction externality, CIO Single-Pane-of-Glass mandate, EDI requirement
  - `v29_score_82` (apparatus-heavy): `Z = f(X,Y)` "Operation Liquid Inertia" — symbolic transformation function, named variables, same style as current `thesis.md`
  - Iteration number monotonicity implies direction: early iterations produced domain-insight 88 champions; late iterations drifted to apparatus and regressed to 82.
- **Discriminating test (pre-registered):** Read judge rationale for `v1_score_88`, `v2_score_88`, `v16_score_88`, `v29_score_82` from FIGS judge logs. Under H-GAMING-14, 88-scoring rationales cite specific domain mechanisms (LCTA, break-even arithmetic, CIO mandate) as the reason for the high score; 82-scoring rationale notes apparatus doesn't buy additional insight beyond plain claims. Neither rationale should cite "lack of quantitative precision" or "no symbolic mapping" as reasons to downscore domain insight. If judge rationales *do* cite form deficiencies against domain insight, H-GAMING-13 comes back alive as a competing hypothesis.
- **What this does NOT claim:**
  1. That all apparatus is drift — Hormuz's quantitative decomposition is substantive quantitative analysis; it carries content. The mutator's mistake is deploying the *form* of apparatus when the *content* is not there.
  2. That this conflicts with H-GAMING-11 — H-GAMING-11 is empty-evidence formalism (apparatus under gaming intent); H-GAMING-14 is evidence-present apparatus drift (no gaming intent). Different environments, different mechanisms, both can coexist.
  3. That GLP-1 50→85 or Hormuz 30→74 self-evidence this pattern — those trajectories are substance climbs, not apparatus drift. FIGS is the decisive case because its iteration hierarchy shows a *regression* from domain insight to apparatus.
  4. That the fix is rubric re-calibration — the rubric is behaving correctly. The fix lives in the mutator's theory-of-mind of the rubric: what signal does the mutator read from past iterations that tells it "formalism wins"?
- **Relationship to seam eigenquestion:** The operator's "v1 more creative, current kernel too pessimistic" intuition was pointing at H-GAMING-14, not H-GAMING-11 or H-GAMING-13. The drift is real; the direction of force is mutator-side, not judge-side. The kernel is not pessimistic — it is rewarding substance the mutator stopped producing.
- **Run(s):** Judge rationale audit pending (FIGS judge logs); no new runs required for first discriminating step.
- **Opened:** 2026-04-14 (Turn 11, opmode seam)
- **Closed:** —

#### H-JUDGE-01 — Judge self-instruction failure under structural compliance pressure

- **Hypothesis:** When a thesis scores high on structural rubric criteria (named mechanism, kill criteria, falsifiability section, mathematical formalism), the judge ignores its own explicit self-instruction to withhold scoring on a harness defect — rewarding thesis structure rather than thesis substance.
- **Scope:** Any run where test_model.py fails with a tooling error before the judge scores; general judge reliability surface
- **Status:** `confirmed`
- **Discriminating test (for hardening):** Run a structurally compliant thesis against a broken test harness (e.g., missing import) on two model families. If both ignore the HARNESS DEFECT warning and score → the failure is systematic, not model-specific. Hardening target: enforce a hard score cap (e.g., 50) when `harness_invoked=false` or harness exits with a tooling error, regardless of thesis quality.
- **Run(s):** `ai_competitive_landscape` honeypot probe iter 1 — judge wrote "MUST NOT rationalize it as evidence the thesis survived scrutiny" then scored 108. `ModuleNotFoundError: No module named 'pytest'` was the harness failure.
- **Result:** Confirmed single instance (gemini-2.5-flash judge). Second model family not yet tested.
- **Pending hardening:** Enforce score cap in autoresearch_loop when harness exits non-zero due to tooling error vs. genuine falsification failure. These two failure modes must be distinguishable in the scoring path.
- **Opened:** 2026-04-14
- **Closed:** —

#### H-GP163D-ALIEN-01 — Fractal-dimensionality law can beat local algebraic MOND families on the gp163d calibration basin and survive frozen PNe+UDG falsification

- **Hypothesis:** A de-anchored fractal-dimensionality law of the form `y = x * (a0/x)^(3 - D_eff)` with `D_eff` driven by local substrate fields can outperform the current internal-aware-EFE family on `A/B/D/N` and survive frozen strict PNe + UDG dark-domain checks, indicating that geometry-like dimensional response explains the cross-class split better than local algebraic MOND screening.
- **Scope:** GP-163d / paper-7 post-null search
- **Status:** `falsified`
- **Discriminating test:** Implement the exact alien cold-shot parameterization as a cheap offline fitter first: fit `alpha, beta` in `D_eff = 2 + tanh((x + g_external)/a0) - alpha*(1 - exp(-beta*eta_pressure))` on `A/B/D/N` only, freeze, then test on strict PNe and UDG under the same protocol used for `v5.2` and the internal-aware-EFE family. Kill immediately if the exact algebraic form is mathematically inconsistent with the intended low-`x` MOND-like regime or if the frozen fit fails calibration badly.
- **Run(s):** `projects/gp163d_unified_accel/raw/dark_dataset_udg/run_fractal_dimensionality_suite.py`
- **Result:** Falsified cheaply. Best fit collapsed to `alpha=0.0`, still produced mean `A/B/D/N` MRE `1.207` with `D=3.228`, plus frozen PNe median MRE `0.487` and UDG heuristic `4.579 / 1.648`. More importantly, the exact law's claimed low-`x` intuition failed algebraically: at `D_eff=2`, `y = x*(a0/x) = a0`, not `sqrt(x*a0)`. The regime-sanity table showed a `10.95x` overshoot of the MOND-like reference at `x=1e-12`.
- **Opened:** 2026-04-28
- **Closed:** 2026-04-28

#### H-GP163D-MACRO-01 — A Newtonian-safe macroscopic-depth coevolution law can beat threshold-only local families and survive frozen PNe+UDG falsification

- **Hypothesis:** A class-blind law that uses a non-leaky baryonic-depth proxy `phi_b ~ G*Mbar/Rchar` as a bounded state variable, and lets that single state coevolve both the MOND-like amplitude and the EFE threshold, can preserve the `A/B/D/N` calibration gains while materially improving strict frozen PNe and UDG performance relative to the first internal-aware threshold family.
- **Scope:** GP-163d / paper-7 post-null search
- **Status:** `falsified`
- **Discriminating test:** Implement a Newtonian-safe standard-`nu` interpolation with `g_pred = x*(1 + E*(nu_std - 1))`, `C = (phi_b/phi0)^p / (1 + (phi_b/phi0)^p)`, `theta = 1 + alpha_phi*C`, `T = e0*(1 + lambda_phi*C)`, fit on `A/B/D/N` only with 40 random restarts, then freeze and test on strict PNe plus UDG with no pressure proxy. Run nested ablations removing `phi_b` entirely and separately removing amplitude or threshold coevolution. Kill if the frozen full model fails to improve both PNe median MRE and UDG heuristic mean MRE versus the first internal-aware strict pass, or if the gains disappear when `phi_b` is removed.
- **Run(s):** `projects/gp163d_unified_accel/raw/dark_dataset_udg/run_macroscopic_coevolution_suite.py`
- **Result:** Falsified as a promotable dark-domain candidate even after smarter global fitting. Rerunning under `differential_evolution(..., polish=True)` left the calibration objective at `0.315`, improved strict PNe only to `0.511`, and left UDG at `1.145 / 0.391` mean/median. The nested ablations still showed the same mechanism: the actual calibration gain came almost entirely from amplitude coupling (`+0.082` objective hit when `phi` was removed or `alpha_phi=0`), while threshold coevolution remained effectively inert (`lambda_phi=0` changed the objective by about `5e-6`). The simple `phi_b ~ Mbar/Rchar` proxy therefore behaves as a deep-potential amplitude pump for clusters and some high-depth systems, not as the hoped-for shared EFE shield.
- **Opened:** 2026-04-28
- **Closed:** 2026-04-28

#### H-GP163D-SPARSITY-01 — A low-surface-density sparsity shield can separate UDGs from PNe without depth-like overprotection

- **Hypothesis:** A Newtonian-safe law that keeps the cluster-core amplitude channel in `eta_pressure` but renormalizes the EFE threshold using a class-blind baryonic sparsity proxy `Q = f(Sigma0 / Sigma_bar)` with `Sigma_bar ~ Mbar / Rchar^2` can preserve `A/B/D/N` calibration quality while improving strict frozen UDGs without re-protecting high-surface-density PNe the way the `phi_b` family did.
- **Scope:** GP-163d / paper-7 post-null search
- **Status:** `falsified`
- **Discriminating test:** Implement `theta = 1 + alpha*eta^beta/(kappa + eta^beta)` and `T = e0*(1 + lambdaSigma*Q)` inside a Newtonian-safe standard-`nu` interpolation, where `Q = (Sigma0 / Sigma_bar)^p / (1 + (Sigma0 / Sigma_bar)^p)`. Fit on `A/B/D/N` only with 40 random restarts, then freeze and test on strict PNe plus UDG. Run a nested `lambdaSigma=0` ablation to test whether the sparsity shield is actually decisive.
- **Run(s):** `projects/gp163d_unified_accel/raw/dark_dataset_udg/run_sparsity_shield_suite.py`
- **Result:** Falsified as a decisive shield even after smarter global fitting. The sign separation existed in raw feature space (`Sigma_bar` high for PNe, low for UDGs), but rerunning with `differential_evolution(..., polish=True)` still did not produce a meaningful rescue. Full fit landed at mean `A/B/D/N` MRE `0.241`, strict PNe median MRE `0.485`, and strict UDG heuristic `0.855 / 0.704`, while the nested `lambdaSigma=0` ablation again changed almost nothing. The global-fit mechanism differed from the earlier local basin: instead of shutting the shield off, it saturated `Q` to nearly `1` for every non-solar class (`A≈0.999998`, `B≈0.99999998`, `C≈0.99991`, `D≈1.0`, `N≈0.99999986`). Two different optimizer geometries therefore point to the same substantive null.
- **Opened:** 2026-04-28
- **Closed:** 2026-04-28

#### H-GP163D-TFA-01 — Implicit total-field AQUAL can separate Banik from UDG without new structural shield variables

- **Hypothesis:** The live failure may not be a missing invariant at all but a wrong algebraic syntax for the EFE. A Newtonian-safe implicit total-field AQUAL law, where the external field enters inside the interpolation argument via `g_tot = sqrt(y^2 + g_ext^2)` rather than as a downstream multiplicative suppression factor, can preserve cluster gains through the existing `eta_pressure` amplitude channel and materially improve strict frozen PNe plus UDG without any new `M/R`-type shield variable.
- **Scope:** GP-163d / paper-7 post-null search
- **Status:** `falsified`
- **Discriminating test:** Implement `theta = 1 + alpha*(1 - exp(-beta*eta_pressure))`, `mu(g_tot) = g_tot / (g_tot^n + (a0*theta)^n)^(1/n)`, and solve the implicit equation `y * mu(sqrt(y^2 + g_ext^2)) = x` for `y`. Fit `alpha, beta, n` on `A/B/D/N` only under a stronger global fitter (`differential_evolution(..., polish=True)`), then freeze and test on strict PNe plus UDG. Kill if the family does not materially improve both PNe median MRE and UDG mean/median relative to the best prior strict pass.
- **Run(s):** `projects/gp163d_unified_accel/raw/dark_dataset_udg/run_total_field_aqual_suite.py`
- **Result:** Falsified as a practical successor on this substrate. The total-field syntax repair is mathematically cleaner than the multiplicative-EFE families, but the fitted implementation still lands at mean `A/B/D/N` MRE `0.251`, strict PNe median MRE `0.486`, and strict UDG heuristic `0.981 / 0.732`. The optimizer chooses `beta≈0.012` and `n≈6.36`, meaning the cluster pressure channel becomes almost flat while the interpolation sharpens, yet the empirical split is still not resolved.
- **Opened:** 2026-04-28
- **Closed:** 2026-04-28

#### H-GP163D-STFA-01 — Baryonic-depth screening of the external field inside total-field AQUAL can rescue UDGs without re-poisoning PNe

- **Hypothesis:** The failure of the minimal total-field AQUAL law may come from feeding the raw host external field directly into the interpolation argument. A Newtonian-safe implicit total-field law that keeps the same `eta_pressure` cluster-amplitude channel but attenuates the external field by a bounded baryonic-depth screening factor, `g_ext_eff = g_ext * exp(-lambda_D * C(phi_b))`, can preserve Banik/Solar high-`g_ext` suppression while materially improving strict frozen PNe and UDG performance relative to both the minimal TFA and the earlier `phi_b` amplitude/threshold family.
- **Scope:** GP-163d / paper-7 post-null search
- **Status:** `falsified`
- **Discriminating test:** Implement `phi_b ~ G*Mbar/Rchar`, `C = (phi_b/phi0)^p / (1 + (phi_b/phi0)^p)`, `theta = 1 + alpha*(1 - exp(-beta*eta_pressure))`, `g_tot = sqrt(y^2 + (g_ext*exp(-lambda_D*C))^2)`, `mu(g_tot) = g_tot / (g_tot^n + (a0*theta)^n)^(1/n)`, and solve `y*mu(g_tot)=x` implicitly for `y`. Fit on `A/B/D/N` only under `differential_evolution(..., polish=True)`, then freeze and test on strict PNe plus UDG. Run a nested `lambda_D=0` ablation to verify the screening channel is decisive. Kill if the screening term is ablation-insensitive or if the frozen full model fails to improve both PNe median MRE and UDG heuristic mean MRE relative to the best prior strict pass.
- **Run(s):** `projects/gp163d_unified_accel/raw/dark_dataset_udg/run_screened_total_field_aqual_suite.py`
- **Result:** Falsified as a materially new rescue family. The screened-total-field fit lands almost exactly on the unscreened total-field null: mean `A/B/D/N` MRE `0.251`, strict PNe median `0.482`, strict UDG `0.981 / 0.732` mean/median. The nested `lambda_D=0` refit changes the calibration objective by only `+3.8e-05` and moves UDG metrics by effectively zero, so the screening channel is not decisive. The fitted depth state is itself revealing: `C(phi_b)` screens `A/B` galaxies substantially but leaves `D/C/N/S` essentially unscreened, meaning the row-wise depth proxy never becomes the selective UDG-vs-Banik discriminator the mechanism needed.
- **Opened:** 2026-04-28
- **Closed:** 2026-04-28

#### H-GP163D-PHASEGATE-01 — A local superfluid-style phase fraction can reconcile UDGs, Banik, clusters, and dwarfs

- **Hypothesis:** A local phase-fraction law of the form `y = x + gamma * f_s(stress) * sqrt(x*a0)`, where `f_s = 1/(1 + exp((stress - s_crit)/width))` and `stress = sqrt((x/a0)^2 + (g_external/a0)^2 + eta_pressure^2)`, can beat the current row-wise families on `A/B/D/N` and survive strict frozen PNe plus UDG checks by treating the anomaly as a vacuum phase that disappears under high local acceleration, high external field, or high thermodynamic pressure.
- **Scope:** GP-163d / paper-7 post-null search
- **Status:** `falsified`
- **Discriminating test:** Implement the literal local phase-gate law with `gamma`, `s_crit`, and `width` fitted on `A/B/D/N` under `differential_evolution(..., polish=True)`, then freeze and test on strict PNe plus UDG. Run a nested `eta_pressure`-off refit to test the sign contradiction directly. Kill if the literal heat-as-decoherence term worsens `B/D` calibration or if the frozen dark-domain checks fail relative to the best prior strict pass.
- **Run(s):** `projects/gp163d_unified_accel/raw/dark_dataset_udg/run_phase_gate_superfluid_suite.py`
- **Result:** Falsified directly. The literal phase-gate fit lands at mean `A/B/D/N` MRE `0.507`, with catastrophic calibration failure in the two high-`eta_pressure` classes: `B=0.849` and `D=0.897`. The nested `eta_pressure`-off refit improves the calibration objective by `-0.124`, improves `B` by `-0.222`, and improves `D` by `-0.318`, proving the sign contradiction: in this substrate, treating thermodynamic support as decoherence destroys the exact classes that need extra gravity. The dark-domain metrics are also not promotable: strict PNe median `0.406`, strict UDG `0.948 / 0.445`; the PNe number is comparatively good but bought by a calibration law that fails the core basin. The exact superfluid phase-gate metaphor is therefore dead as a local row-wise law.
- **Opened:** 2026-04-28
- **Closed:** 2026-04-28

#### H-GP163D-SHEAR-01 — A host-field tidal shear proxy is the remaining admissible row-wise discriminator before 3D field solving

- **Hypothesis:** If the row-wise substrate still contains one honest successor after the structural-null stack, it must be a non-leaky host-aware coordinate such as external tidal shear or host-field gradient, not another target-local scalar built from `x`, `g_external`, `eta_pressure`, `M/R`, or `M/R^2`.
- **Scope:** GP-163d / paper-7 post-null search
- **Status:** `falsified_for_current_substrate`
- **Discriminating test:** First run a feature audit, not a fit: determine whether a host-field-gradient / tidal-shear proxy can be computed from environment geometry alone across `A/B/D/N`, strict PNe, UDG, and Banik/Solar analogs without target kinematics, class labels, or residual leakage. If the audit passes coverage and leakage checks, pre-register exactly one shear-gated EFE falsifier with a nested shear-off refit. If the audit fails, treat the local row-wise scalar branch as near exhausted for this causal class and move to field/topology representation rather than another algebraic scalar.
- **Run(s):** `projects/gp163d_unified_accel/raw/dark_dataset_udg/run_tidal_shear_feature_audit.py`
- **Result:** Failed at the pre-fit feature-audit stage. The strict proxy `shear_kpc_inv = (g_external/a0) / D_host_kpc` is admissible only when `D_host` comes from external host/environment geometry rather than internal radius, velocity dispersion, class labels, observed residuals, or measured `g_obs`. The current substrate gives strict coverage for Banik/wide-binary rows (`N` median shear `0.2317 kpc^-1`), Solar/control rows (`C/S` same), dwarf satellites (`D` median `7.78e-4 kpc^-1`), and PNe projected group geometry (`2.17e-3 kpc^-1`), but gives zero strict coverage for required classes `A`, `B`, and `UDG`. UDG rows have only environment codes, not host distances or host masses. A shear-gated fit on this substrate would therefore be uninterpretable: it would have to drop domains or use leaky substitutes such as internal radius, object class, or environment labels. This does not falsify tidal-shear physics; it falsifies the current row-wise substrate's ability to test it cleanly.
- **Opened:** 2026-04-29
- **Closed:** 2026-04-29

#### H-GP163D-3D-SANDBOX-01 — Boundary-condition shear can separate UDG-like diffuse systems from Banik-like compact systems in a minimal AQUAL field sandbox

- **Hypothesis:** If the remaining live GP-163d gravity mechanism is genuinely host-aware rather than row-wise scalar, then a minimal 3D field sandbox should separate two controlled weak-acceleration systems at matched scalar `g_ext`: a diffuse UDG-like baryonic source under a uniform external-field boundary should remain MOND-like, while a compact binary-like source under a high tidal-gradient boundary should be driven toward Newtonian behavior. The discriminating object is boundary-condition shear / tidal tensor, not another fitted scalar column.
- **Scope:** GP-163d / paper-8 follow-up instrument, not a paper-7 result
- **Status:** `open`
- **Discriminating test:** Implement a small fail-closed 3D Poisson/AQUAL-style relaxation sandbox at low resolution (`64^3` first). Use controlled source geometries (diffuse Gaussian and compact binary peaks), explicit external boundaries (`Phi_edge = -g_ext*z` versus `Phi_edge = 0.5*Gamma*z^2 - g_ext*z`), residual convergence checks for `div(mu(|grad Phi|/a0) grad Phi) - 4*pi*G*rho_bar`, nested shear-off controls, boundary-condition permutations, and resolution repeats. Kill if UDG-like sources are crushed under uniform fields, if binary-like sources remain MOND-like under high shear, if convergence/resolution controls fail, or if any apparent separation depends on post-hoc tuning.
- **Run(s):** `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/run_minimal_aqual_sandbox.py`
- **Result:** First-pass instrument run completed and the minimal setup was not promoted. The initial `64^3` fixed-point/Jacobi scan produced a misleading weak binary-suppression hint, but a code/solver audit found two instrument issues: source densities were normalized by raw `rho.sum()` rather than grid integral, and the nonlinear tidal background was not converged. A JAX finite-volume residual-minimization solver was added and sanity-checked against the NumPy residual; the corrected `32^3` runs use explicit source mass and converged no-source tidal backgrounds. Corrected result: at low shear (`Gamma=0.02`), tidal boundary is effectively neutral (`UDG A/N 10.087 -> 10.061`, binary 6.897 -> 6.899). At high shear (`Gamma=0.45`), both sources are suppressed, with the UDG suppressed more strongly (`10.087 -> 4.807`) than the binary (`6.897 -> 5.183`). This does not falsify tidal-shear gravity globally, but it falsifies the minimal source/boundary setup as the desired separator. Next admissible move: pre-register a controlled geometry sweep over source width, binary separation, source mass, shear amplitude/orientation, and resolution.
- **Opened:** 2026-04-29
- **Closed:** —

#### H-GP163D-5AO — Local field slices reveal the geometric mechanism behind the UDG tensor-orientation separator

- **Hypothesis:** The repaired `L=4.0,n160,Gamma=0.25` UDG `0/45/90 deg` U-shape is not only a scalar mass-weighted artifact. It corresponds to a coherent spatial redistribution of the AQUAL stiffness field: aligned orientations should show localized, contiguous regions where `mu`, `|grad Phi_total|`, `|grad Phi_internal|`, and internal/background-gradient alignment differ systematically from the `45 deg` trough, while compact binary slices should remain dominated by source-local gradients and show much weaker angle dependence.
- **Scope:** GP-163d 3D AQUAL sandbox, theorem-promotion diagnostics after JAX/GPU `n=160` replication.
- **Status:** `open`
- **Discriminating test:** Implement `run_field_slice_diagnostics.py` to rerun controlled `0/45/90 deg` UDG and binary cases, save central `x/y/z` slices of `rho`, `internal_phi`, `total_g`, `internal_g`, `mu`, `total_over_internal`, and internal/background alignment, and emit a JSON localization report. Use a low-resolution local smoke first, then reuse on GPU only if the instrument works. Support = UDG aligned-vs-45 differences are spatially coherent and tied to principal-axis alignment/stiffness redistribution rather than isolated single-cell extrema; binary angle deltas remain small and source-local. Rejection = UDG enhancement is dominated by isolated voxels, edge-wall bands, or incoherent/noisy slice changes; then the theorem path must stop at instrument finding.
- **Success criterion:** Before any theorem or physical claim is promoted, the slice report must identify a stable contiguous UDG enhancement/suppression region away from boundaries, with no near-zero-field cancellation floor and with binary-locality controls passing. This is not a physics theorem by itself; it is the admissibility gate for attempting an analytic perturbation theorem or observational mapping.
- **Opened:** 2026-05-01 00:00:00 EDT

---

### Retrospective rows (no further test; closed by analysis)

#### H-GP023-00 — Sandbox_03 score-50 hits 13/20/26 are the same basin

- **Hypothesis:** The three score-50 ceiling hits in sandbox_03 (iters 13, 20, 26) all belong to the same structural basin.
- **Scope:** GP-023, GP-046 empirical anchor
- **Status:** `partially_confirmed`
- **Discriminating test:** GP-048 retrospective AST analysis (Candidate E from Turn 1 of this seam). Basin reality tested via tree-edit-distance clustering and primitive-set extraction on the closed sandbox_03 workspace.
- **Run(s):** `gp023_planck_sandbox_03` (closed) analyzed via `src.ztare.validator.gp048_retrospective`
- **Result:** Partially confirmed. Iters 13 and 26 are TED-identical (d=0). Iter 20 is structurally distinct at TED=9. All three share the same primitive set `{additive_composition, exp_neg, multiplicative_composition, power}`. The correct reframing is: the basin is a **primitive-set basin**, not a specific-expression basin. Multiple distinct structural forms reach the same farther-tail failure through the same coarse vocabulary. See `projects/gp023_planck_sandbox_03/workspace/gp048_findings_for_debrief.md`.
- **Opened:** 2026-04-13 (implicit in GP-023 seam Turn 29)
- **Closed:** 2026-04-13 (via GP-048 retrospective)

---

## Candidate Successor Programs (Post-Sandbox_04) — Pre-Registered

These three programs are pre-registered before `sandbox_04`'s 20-iter run closes. Pre-registration here means: the framing of these candidates cannot be retrofitted to match `sandbox_04`'s result. They are written now so the result cannot bias which one looks attractive.

**How pre-registration works here:**

- the stable hypothesis row is frozen now (`H-SP1-01`, `H-SP2-01`, `H-SP3-01`)
- the eigenquestion, minimum discriminating test, success criterion, and staging logic are frozen now
- the exact future packet slug, exact rubric file, model/toolchain pin, and implementation details are **not** frozen yet
- any later runnable packet that claims to instantiate `SP-1`, `SP-2`, or `SP-3` must cite the corresponding hypothesis row and explain any drift before seal

### Candidate SP-1 — Forward-Observable B-Slice Sandbox

**What it tests:** Whether ZTARE's farther-tail discipline is meaningful for genuine discovery (not just rediscovery). The canonical Oracle Problem objection is that the farther-tail gate was authored knowing the answer. SP-1 attacks this directly.

**Mechanism:** The farther-tail file is generated by a process the operator has not yet computed: a numerical simulation run deferred until after the mutator's visible slice is set, or a deferred physical measurement. The operator commits to the gate threshold before seeing the farther-tail values. This is the smallest move that makes the B-slice genuinely unknown at author time — most of the current harness survives.

**Success criterion:** A mutator thesis passes the farther-tail gate without the operator having ever seen the farther-tail values at charter time.

**Blocks on:** Nothing. Executable after sandbox_04 closes. Does not require GP-048 or preservation lane.

**Hypothesis tested:** H-SP1-01 — "ZTARE's farther-tail discipline is meaningful when the B-slice is genuinely unknown, not just sealed from the mutator."

---

### Candidate SP-2 — FunSearch-Style Program Mutator Arm

**What it tests:** Whether program synthesis (LLM writes Python functions, not symbolic expressions) escapes the primitive cones that the symbolic mutator gets stuck in. Tests Gemini's "Invert the Vocabulary" claim quantitatively instead of rhetorically.

**Mechanism:** Add an alternative mutator mode where output is a Turing-complete Python function `I_model(phi, psi)` rather than a symbolic expression string. Run as a second arm on a sandbox where the symbolic mutator is known to have gotten stuck (sandbox_03 or sandbox_04). GP-048 Mode 1 telemetry measures primitive set for both arms. The question is whether program synthesis produces a cone exit that symbolic synthesis did not.

**Success criterion:** Program mutator arm introduces at least one function class (recursive series, piecewise, non-elementary) that sandbox_03/04 never reached, AND passes a gate that the symbolic arm failed.

**Blocks on:** No hard block. Strategically staged after `sandbox_04` so the apparatus-feedback packet reports before a program-mutator arm is interpreted.

**Hypothesis tested:** H-SP2-01 — "Program synthesis escapes primitive cones that symbolic mutation cannot, because the reachable function class is larger."

**Hard ceiling acknowledged:** LLM writing Python still draws from a pre-trained distribution over program structure. The ceiling moves from math primitives to program primitives — further out, not gone. SP-2 measures how much further.

---

### Candidate SP-3 — Lean-Backed Conservation Law Gate

**What it tests:** How much of the LLM judge's work can be moved onto a formal verifier for a domain where one conservation law is fully formalizable. Tests the "compress the judge" claim from the Level 5 debate.

**Mechanism:** Choose a toy domain (e.g., a simple thermodynamic system where energy is conserved, or a network flow where flow is conserved at each node). Add one gate implemented as a Lean 4 / Coq proof obligation: the model's output must satisfy the conservation law, checked by the theorem prover, not the LLM. The LLM judge remains for everything else. Measure what fraction of falsification events come from the formal gate vs. the LLM judge.

**Success criterion:** At least 30% of thesis rejections in the run come from the formal gate, not from LLM scoring — i.e., the verifier does non-trivial work that the judge alone would not have caught.

**Blocks on:** Requires identifying a domain with a fully formalizable conservation law and toolchain setup. Largest setup cost of the three candidates.

**Hypothesis tested:** H-SP3-01 — "Formal verification gates catch a non-trivial fraction of thesis failures that LLM judges miss, when the conservation law is fully formalizable."

**Hard ceiling acknowledged:** Formal verification is limited to formalizable domains. Most real scientific domains are partially formalizable at best. SP-3 measures where that boundary is.

---

**Decision rule:** SP-1 is executable immediately after `sandbox_04` closes regardless of result. SP-2 remains available regardless of result, but its information yield is highest if `sandbox_04` still shows cone residency under apparatus feedback. SP-3 is a longer-term probe requiring toolchain work. None of the three requires `sandbox_04` to succeed — they are designed so that a `sandbox_04` failure is equally informative.

---

## H-GP154N-03 — Axis-exponent normalized neural scaling law upgrade test

- **Opened:** 2026-05-01 07:38:00
- **Closed:** 2026-05-03 00:24:01
- **Status:** `closed / confirmed_for_numerical_methods_candidate / physics_not_promoted`
- **Hypothesis:** The live GP154 normalized champion is more than a fitted curve: after per-curve floor/amplitude normalization, neural scaling-curve shape is governed by a provenance-free axis-exponent relaxation law whose mixed compute-frontier exponent is steeper than pure N/D exponents.
- **Eigenquestion:** Does the champion survive the cheapest law-grade falsifiers: gauge perturbation, equal-K provenance rival, stratified residual compression, and external-data inventory?
- **Discriminating tests:**
  1. **Gauge perturbation:** re-evaluate the champion under deterministic perturbations of the normalized curve coordinate and curve span. Success means holdout and farther-tail gates remain below threshold or degrade smoothly without flipping the exponent ordering.
  2. **Equal-K provenance rival:** fit an equal-or-lower-K rival that may use banned provenance keys (`study`, `source_paper_table`, `curve_id`) and compare holdout/farther-tail performance. Success means provenance does not materially beat the champion at equal K.
  3. **Stratified residual audit:** measure maximum MAE by `study`, `modality`, `loss_type`, `scaling_var`, and `fit_convention`. Success means no hidden failing stratum is masked by aggregate gates, or any failure is explicitly scoped as a missing external-data axis.
  4. **External-data inventory:** identify modern isolated N/D or mixed-sweep datasets suitable for a dark validation set. Success means at least one candidate dataset exists with enough metadata to compute the normalized curve coordinate without leaking fit provenance.
- **Success criterion:** The current champion is promoted from `candidate empirical law` to `law-track candidate` only if tests 1-3 pass and test 4 yields a viable dark validation target. If any of 1-3 fail, the finding remains a strong within-substrate fit and the failure mechanism becomes the next object.
- **Interpretation boundary:** A Lagrangian is optional. It is admissible only if it derives the exponent split without adding hidden knobs or provenance-equivalent categories. A fitted Lagrangian-shaped expression does not by itself upgrade the claim.
- **Source artifacts:** `projects/gp154_scaling_law_normalized/workspace/submissions/iter_003_20260501T112619.957316+0000.py`, `projects/gp154_scaling_law_normalized/champion_eval_results.json`, `research_areas/EXPERIMENT_TRACK_RECORD.md#E-GP154N-AXISLIVE-01`.

## H-GP116B-01 — Residual cancellation as successor-architecture design signal

- **Opened:** 2026-05-01 08:05:00
- **Status:** `active`
- **Hypothesis:** The old GP116 "transformer waste" thread should be reinterpreted as a residual-stream coordination problem: fixed additive residual accumulation imposes a measurable cancellation tax, and the scientifically useful discriminator is whether architecture or training can reduce that tax without destroying high-dimensional perturbation capacity.
- **Eigenquestion:** Is cancellation reduction a controllable architecture/training variable, or is the apparent reduction in GPT-2/SmolLM/Mamba and the from-scratch Pythia probe a provenance/training-instability artifact?
- **Discriminating tests:**
  1. **Artifact consolidation:** aggregate existing GP116 diagnostics into a substrate table with source pointers, separating trained-vs-untrained cancellation, cross-layer orthogonality, residual rank, perturbation magnitude, BOS anomaly, and intervention rows.
  2. **Causal fork audit:** distinguish three live causal classes: fixed residual-geometry tax, trainable phase-locking / residual routing, and unstable optimization collapse. Success means each row is tagged so the mutator cannot launder model names or provenance into a law.
  3. **External literature bridge:** compare the internal GP116 signal to post-2025 residual-stream architecture work (e.g. residual matrix memory, attention residuals, KV/residual-state redundancy) and identify which claims are already known versus still novel.
  4. **Substrate readiness gate:** before launching a new ZTARE loop, require enough non-leaky rows to hold out by model family or training regime. If not enough rows exist, the next action is data acquisition, not symbolic regression.
- **Success criterion:** Promote GP116B to a runnable ZTARE project only if the consolidated substrate supports at least one clean family/regime holdout and a no-provenance gate. Otherwise, record it as a cold-shot design thesis plus missing-data plan.
- **Interpretation boundary:** Do not frame canceled perturbation energy as useless layer "waste." Prior GP116 ablations showed every bottleneck layer has nonzero loss impact. The admissible claim is narrower: fixed residual bookkeeping may force useful high-dimensional updates through a destructive summation channel, and successor architectures may improve the bookkeeping.
- **Source artifacts:** `projects/gp116_cot_exchange/workspace/interim_findings.md`, `papers/paper6_neural_scaling/draft.md`, `projects/gp116_cot_exchange/workspace/wd_from_scratch_pythia160m_proper.json`, `projects/gp116_cot_exchange/workspace/weight_scaling_test.json`, `projects/gp116_cot_exchange/workspace/weight_decay_causal.json`.

## H-GP116B-02 — Residual-state economics is the successor-architecture eigenquestion

- **Opened:** 2026-05-02 16:30:00
- **Status:** `active`
- **Hypothesis:** The transformer-successor question should be posed as residual-state economics, not as a family-name tournament. Architectures that reduce inference/training cost without quality loss will do so by changing the state carrier: residual checkpointing, recurrent/SSM state, learned residual routing, or matrix residual memory.
- **Eigenquestion:** What is the minimal state carrier that preserves useful next-token computation at equal loss: full KV cache, residual-stream checkpoint, recurrent state, learned depth aggregation, or expanded matrix memory?
- **Discriminating tests:**
  1. **KV-direct residual checkpoint measurement:** remeasure exact residual-state sufficiency locally: token match, logit divergence, recompute latency, memory per token, and whether residual-only checkpoints preserve outputs under the GP116 harness.
  2. **SSM / Mamba-family residual diagnostic:** add at least two measured recurrent/SSM rows with cancellation, survival, effective rank, and downstream retention; current `ssm=1` is not enough for law claims.
  3. **Learned residual routing diagnostic:** measure AttnRes/Block-AttnRes if runnable weights/code are available; target is whether learned depth aggregation reduces destructive summation without rank collapse.
  4. **Law-loop admission gate:** rerun `gp116b_transformer_successor` only after the measurement table supports a family holdout with at least two non-MHA successor mechanisms measured under comparable diagnostics.
- **Success criterion:** Promote the transformer-successor track from measurement-selection substrate to ZTARE law substrate only if the direct measurements create a non-leaky family holdout and a downstream-retention control. A lower cancellation row alone is insufficient.
- **Interpretation boundary:** Do not claim "Transformer is dead" or rank Mamba/xLSTM/RetNet/RWKV/AttnRes/RMT from source-backed architecture descriptors. The admissible claim before measurements is: residual-state economics defines the measurement queue for cheaper/faster LLMs.
- **Source artifacts:** `projects/gp116_cot_exchange/TRANSFORMER_SUCCESSOR_RESEARCH_DIRECTOR_BRIEF_20260502.md`, `projects/gp116_cot_exchange/workspace/transformer_successor_substrate_readiness.json`, `projects/gp116b_transformer_successor/champion_eval_results.json`.

## H-GP154N-04 — Modern raw scaling-data external validation packet

- **Opened:** 2026-05-01 08:32:00
- **Status:** `active`
- **Hypothesis:** The GP154 normalized axis-exponent law is not an artifact of inherited Kaplan/Chinchilla/Hestness/Henighan curve provenance. On a fresh modern raw scaling dataset with explicit parameters, tokens/compute, and validation loss, isolated N/D sweeps should collapse to the low-exponent relaxation class (`alpha≈1.46–1.48`) while mixed compute-frontier sweeps should remain steeper.
- **Eigenquestion:** Can a modern, raw, externally sourced scaling dataset reproduce the axis-exponent split without using paper identity, model-family identity, or per-curve provenance as a hidden lookup table?
- **Discriminating tests:**
  1. **Data admissibility:** source must expose enough raw rows to compute `(L - L_min)/(L_max - L_min)`, `curve_axis_rev`, sweep axis, and curve span without hand-digitizing a single plot as the sole evidence.
  2. **Modern isolated sweep test:** if the source contains isolated N or D sweeps, fit the normalized axis exponent and test whether it lands near the lazy class (`~1.46`) within a pre-stated tolerance.
  3. **Mixed-frontier test:** if the source contains compute-frontier or joint N/D rows, test whether the normalized exponent is materially steeper than isolated N/D.
  4. **Provenance rival:** compare against an equal-K model allowed to use source/run identity. Success requires the clean axis law to remain competitive enough that provenance does not explain the result.
- **Success criterion:** Promote the GP154 normalized law from `law-track candidate` toward `external-validation candidate` only if at least one modern raw source passes data admissibility and one isolated or mixed sweep reproduces the expected exponent class without provenance repair.
- **Priority sources:** OLMo/OLMo2 logs first because Ai2 exposes training code, W&B metrics, checkpoints, configs, and token counts; Sardana et al. / MosaicML 2024 second because the paper reports 47 trained models over extreme tokens-per-parameter regimes; Llama 3 only if raw per-step or per-run loss data can be obtained rather than headline tokens/parameter summaries.
- **Interpretation boundary:** A modern source with only final model cards, benchmark scores, or headline tokens/params is not enough. It can motivate the search, but cannot validate the normalized curve-shape law.
- **Source artifacts:** `projects/gp154_scaling_law_normalized/workspace/law_upgrade_audit.md`, `projects/gp154_scaling_law_normalized/evidence.txt`, `priority_roadmap.md`.

## H-GP186-5BW-02 — Eviction discriminator as proof-path compressor

- **Opened:** 2026-05-01 14:35:00
- **Status:** `active`
- **Hypothesis:** A bounded ZTARE loop over audited Phase 5S and Kida-Pelz diagnostic rows can discover a compact local discriminator for stretching consolidation versus anti-blowup eviction/sterility, yielding a better next proof-path observable than hand-authored `chi` or `a_pos` alone.
- **Eigenquestion:** Is the hidden critical danger-exit row predictable from local geometry features without using source labels, or does the substrate expose that current features are insufficient and force a richer diagnostic?
- **Discriminating test:** Run `ns_eviction_discriminator` with `gate_harness.py` requiring holdout MAE `< 0.20` and critical-row max error `< 0.30`. Success means a candidate law passes the gate and names a falsifying fresh diagnostic for Kida-Pelz N>=128/N>=256. Rejection means the current local features do not encode the proof-path split; add richer exact symmetry/projection diagnostics before another loop.
- **Success criterion:** A passing submission must implement `I_model(features)->sterility_next`, avoid direct lookup by `family` or `source_phase`, beat the critical hidden row, and provide two fresh numeric predictions. Passing is a mechanism-discovery result only; it does not imply Navier-Stokes regularity.
- **Source artifacts:** `projects/ns_eviction_discriminator/`, `projects/ns_millennium_hunt/workspace/phase5bw_core_signal_audit.json`, `projects/ns_millennium_hunt/workspace/phase5bw_kida_pelz_diagnostic_N64.json`.
- **Interim 2026-05-01 12:12:00 UTC:** Iter 3 of `ns_eviction_discriminator` produced the SAGE signed-alignment law with raw judge score `85` and a crisp kill condition: find matched signed-geometry rows where amplitude/leakage/component shifts change `sterility_next`. A first local N=32 matched-geometry smoke found candidate breaks after excluding near-zero projection, but fixed physical horizon and amplitude scaling remain confounders. Next admissible test is manifest-backed N=64/N=128 matched geometry, preferably turnover-normalized.

## H-GP163D-FIELDSLICE-02 — Fixed-dx domain squeeze for UDG halo response

- **Opened:** 2026-05-01 08:18:00
- **Status:** `active`
- **Hypothesis:** The gp163d UDG orientation response is a physical diffuse-halo shielding effect, not a finite-box pickup. If physical, moving the Dirichlet walls outward while keeping physical resolution fixed should reduce near-boundary contribution and preserve the `0/45/90 deg` U-shape with compact-binary suppression.
- **Eigenquestion:** Does the positive UDG tidal-vs-uniform response detach from the box boundary under fixed-`dx` domain expansion, or does it stretch outward with the wall?
- **Discriminating tests:**
  1. **Instrument alignment:** field-slice diagnostics must use the same long-source-solve settings as the converged minimal-sandbox ladder (`face_flux`, Krylov background, `max_iter=10000`, `warmup_iter=5000`, strict source residual threshold). A source solve with `converged=false` or residual above threshold writes artifacts but exits nonzero and cannot promote a physics claim.
  2. **Fixed-`dx` domain squeeze:** run `L=6.0,N=240` at `gamma=0.25`, `g_ext=0.12`, angles `0/45/90`, sources `udg_gaussian,binary_peaks`. This preserves `dx=0.025` from the `L=4.0,N=160` ladder while moving walls outward by 50%.
  3. **Localization audit:** compute core/halo/outer/near-boundary fractions from the downloaded `.npz` slices and compare to the `L=4.0,N=160` audit. Success requires the UDG response to remain positive and U-shaped while near-boundary fraction decreases materially or the response forms a tensor-axis-coherent interior shell.
  4. **Escalation gate:** only if `L=6,N=240` passes, run `L=8.0,N=320` as the definitive fixed-`dx` wall-push control.
- **Success criterion:** Promote the gravity sandbox toward a numerical-law candidate only if source residuals pass, UDG `0/90` remain materially above `45`, binary mass-weighted response remains suppressed and angle-stable, and the positive UDG response is not boundary-adjacent under domain expansion.
- **Kill condition:** If the positive UDG response remains boundary-adjacent, stretches outward with the wall, or the U-shape collapses under fixed-`dx` expansion, demote the UDG enhancement to finite-box artifact. If source residuals fail, classify as instrument debt rather than physics.
- **Interpretation boundary:** Passing `L=6` or even `L=8` is not a theorem and not observational validation. It upgrades the result to a serious numerical-law candidate requiring independent tensor-boundary presentation, perturbative derivation, or telescope-facing orientation discriminator.
- **Source artifacts:** `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_fieldslice_L4p0_n160_gamma0p25_jaxbg/debrief.md`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/analyze_field_slice_localization.py`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/run_field_slice_diagnostics.py`.

## H-GP163D-OFFDIAG-01 — Off-diagonal orientation interpolation for the repaired UDG field-slice discriminator

- **Opened:** 2026-05-02 10:52:00
- **Status:** `active`
- **Hypothesis:** The repaired UDG field-slice orientation response is a tensor-geometric interpolation effect, not a special `0/45/90` presentation artifact. If physical at the instrument level, off-diagonal angles should interpolate smoothly between the high `0/90` response and the lower `45` trough while the compact binary control stays flat.
- **Eigenquestion:** Does the UDG response vary smoothly with imposed tensor orientation, or is the apparent U-shape a fragile artifact of the canonical axis/trough angles?
- **Discriminating tests:**
  1. **Cheap local off-diagonal smoke:** run `run_field_slice_diagnostics.py` locally at small `N` with `ANGLES=22.5,67.5`, source warmup enabled, denominator floor `1e-9`, and strict source residual/ratio gates. This is an instrument-shape smoke, not a promoted physics run.
  2. **Compare against repaired `L=4,N=160` ladder:** use `summarize_metricguard_ladder.py` and the same ratio/admissibility schema. Success requires the off-diagonal UDG ratios to land between the high endpoints and the `45` trough, with binary ratios still suppressed/flat.
  3. **Promotion gate:** only if the local smoke preserves interpolation and gates pass, spend GPU on the same off-diagonal angles at `L=4,N=160` with the repaired metricguard/warmup settings.
- **Success criterion:** Off-diagonal UDG ratios must be finite/admissible and directionally interpolate rather than invert or collapse; binary must remain angle-stable within the already observed flat band. A local small-N pass only authorizes a repaired `L=4,N=160` off-diagonal GPU confirmation, not theory promotion.
- **Kill condition:** If off-diagonal angles fail source/ratio admissibility, invert, collapse to the binary band, or show larger boundary-localization fractions than the canonical ladder, demote the canonical U-shape to angle-presentation/instrument artifact until a different boundary representation rescues it.
- **Interpretation boundary:** The angle is still an imposed boundary/control parameter. Passing this test supports tensor-orientation interpolation in the sandbox; it does not establish galaxy-scale observational truth.
- **Source artifacts:** `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/run_field_slice_diagnostics.py`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/summarize_metricguard_ladder.py`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260502_metricguard_warmup_ladder_audit.md`.

## H-GP163D-GRIDARTIFACT-01 — Fourfold UDG susceptibility is a Cartesian-stencil transfer-function artifact

- **Opened:** 2026-05-02 14:20:33
- **Status:** `active`
- **Hypothesis:** The repaired field-slice `cos(4theta)` mode is primarily a Cartesian finite-difference/stencil artifact amplified by the diffuse UDG-like source, not a continuum AQUAL field response.
- **Eigenquestion:** Does the fourfold susceptibility amplitude `|chi4/chi0|` collapse or materially change when the AQUAL residual presentation changes, while the same physical source, box, angle set, source warmup, residual threshold, and denominator guard are held fixed?
- **Discriminating test:** Run the same `L=4.0,N=160,Gamma=0.25,g_ext=0.12,angles=0/22.5/45/67.5/90` field-slice ladder under a different AQUAL residual stencil (`normal_face_flux` first; a future 27-point/isotropic stencil if implemented). Fit `chi(theta)=chi0+chi4 cos(4theta)` for UDG and binary exactly as in the metricguard audit.
- **Success criterion for grid-artifact hypothesis:** UDG `|chi4/chi0|` drops by at least 50% from the face-flux baseline `0.1988`, changes sign/phase, or the five-angle `cos(4theta)` fit loses coherence (`R2 < 0.95`) while source residual and denominator gates still pass.
- **Success criterion for continuum-physics survival:** UDG `|chi4/chi0|` remains within 25% of `0.1988`, `R2 >= 0.95`, binary remains flat (`|chi4/chi0| < 0.02`), and source/localization gates pass under the changed residual presentation.
- **Contamination guard:** Do not reinterpret a failed source solve as physics. If source residual, finite, boundary drift, or denominator gates fail, the result is `instrument_inconclusive`, not evidence for either hypothesis.
- **Expected next command shape:** `AQUAL_STENCIL=normal_face_flux N=160 BOX_HALF_SIZE=4.0 ANGLES='0 22.5 45 67.5 90' BACKGROUND_AQUAL_SOLVER=jax_residual SOURCE_SOLVER=scipy_jax_residual SKIP_SOURCE_WARMUP=0 RATIO_DENOMINATOR_FLOOR=1e-9 LABEL_PREFIX=fieldslice_L4p0_n160_gamma0p25_metricguard_normalfaceflux bash projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/deploy_and_launch_field_slice.sh <host>`.

## H-GP163D-REPINV-02 — Diffuse fourfold susceptibility survives as an instrument envelope, not physics, unless amplitude and phase are representation-invariant

- **Opened:** 2026-05-02 20:40:00
- **Status:** `active`
- **Hypothesis:** The current gravity sandbox's strongest honest law object is an invariance-threshold instrument envelope: diffuse weak-gradient sources retain large `|chi4/chi0|` across residual presentations while compact high-gradient controls remain flat, but the UDG phase is representation-sensitive and therefore not a promoted AQUAL/MOND orientation law.
- **Eigenquestion:** Under a third AQUAL residual presentation, does the UDG fourfold amplitude collapse, survive with unstable phase, or survive with the same phase as face-flux while the binary control remains flat?
- **Discriminating test:** Run `L=4.0,N=160,Gamma=0.25,g_ext=0.12`, source warmup enabled, denominator guard `1e-9`, angles `0/22.5/45/67.5/90`, and source residual threshold `1e-5` under `normal_face_flux` using `launch_invariance_threshold_remote.sh`. Fit `chi(theta)=chi0+chi4*cos(4theta)` with `analyze_invariance_threshold.py`. Existing downloaded `face_flux` and `isotropic_18_flux` runs are used as frozen comparators; optionally rerun all three stencils under the same launcher if GPU budget allows.
- **Outcome interpretation:**
  - `artifact_supported`: UDG `|chi4/chi0| < 0.10` under the third admissible representation, or the binary control becomes non-flat (`|chi4/chi0| >= 0.02`), with source and ratio gates passing.
  - `instrument_law_supported`: UDG `|chi4/chi0| >= 0.10` under the third admissible representation, binary `|chi4/chi0| < 0.02`, but UDG phase differs across representations. This promotes only a nonlinear-solver susceptibility envelope.
  - `physics_candidate_live`: UDG `|chi4/chi0|` remains large, UDG phase matches face-flux across all admissible representations, binary remains flat, and source-local morphology is not boundary-supported. This does not settle MOND/dark matter; it only justifies a future independent-solver/observational discriminator.
- **Contamination guard:** If source residual, finite, boundary drift, denominator, or warmup gates fail, classify the run as `instrument_inconclusive`. Do not interpret failed solves as physics. `SKIP_SOURCE_WARMUP=1` is forbidden for promotion runs because it previously created false zero denominators.
- **Cost guard:** Default remote command runs only the missing third representation (`RUN_STENCILS='normal_face_flux'`). Full same-protocol rerun sets `RUN_STENCILS='face_flux isotropic_18_flux normal_face_flux'` and is optional because face-flux/isotropic comparators are already downloaded.
- **Expected next command shape:** `RUN_STENCILS='normal_face_flux' N=160 BOX_HALF_SIZE=4.0 ANGLES='0 22.5 45 67.5 90' BACKGROUND_AQUAL_SOLVER=jax_residual SOURCE_SOLVER=scipy_jax_residual SKIP_SOURCE_WARMUP=0 LABEL_PREFIX=repinv_L4p0_n160_gamma0p25 bash projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/deploy_and_launch_invariance_threshold.sh <host>`.

## H-GP154-PHASE-SCHED-01 — Controlled schedule-contrast phase-flow falsifier

- **Opened:** 2026-05-01 16:03:00
- **Status:** `active`
- **Hypothesis:** The GP154 phase-flow terminal local-alpha spike is partly a learning-rate schedule boundary artifact and partly an endpoint-estimator artifact; after excluding near-floor rows, constant-LR and step-LR controlled transformer runs should not show the same admissible terminal alpha spike as cooldown schedules.
- **Eigenquestion:** Does the terminal local-alpha spike survive when model architecture, corpus, optimizer, token budget, and observation windows are held fixed while only LR schedule family varies?
- **Discriminating tests:**
  1. **Controlled transformer schedule contrast:** train the same causal transformer on the same byte/text corpus under `constant_lr`, `step_lr`, and `cosine_warmup_decay`, with identical seeds/architecture/token budget except for schedule.
  2. **Leakage-safe row construction:** write modeling rows with abstract schedule family and training-coordinate features only; keep run provenance/source files separate.
  3. **Endpoint admissibility:** report both raw terminal rows and admissible terminal rows with `z_remaining >= 0.005`; near-floor rows cannot promote a mechanism claim.
  4. **Transfer split:** treat seed-law transfer error as secondary. The primary falsifier is target local-alpha spike under constant/step schedules, not whether the exact mlfoundations-fitted equation transfers to the controlled run.
- **Success criterion:** The schedule-proxy thesis survives if constant/step admissible terminal p90 abs local-alpha remains below `3.0` while raw near-floor spikes, if present, are explainable by `z_remaining < 0.005`. It fails if constant/step schedules show admissible terminal p90 abs local-alpha above `3.0` across seeds/windows.
- **Interpretation boundary:** A small controlled transformer run is a causal discriminator for schedule/estimator mechanics, not external validation of the GP154 scaling law. External proof still requires OLMo/Pythia-scale or public schedule-contrast telemetry.
- **Source artifacts:** `projects/gp154_phase_flow_law/run_schedule_ood_discriminator.py`, `projects/gp154_phase_flow_law/audit_schedule_ood_sensitivity.py`, `projects/gp154_phase_flow_law/workspace/schedule_ood_sensitivity_audit.json`.

## H-GP163D-SCIENCEGRADE-LOCAL-01 — Existing-data audit for numerical-methods science versus gravity-physics promotion

- **Opened:** 2026-05-03 00:00:00
- **Status:** `active`
- **Hypothesis:** Existing downloaded `face_flux` and `isotropic_18_flux` field-slice artifacts already support a potential science-grade numerical-methods contribution, but not an astrophysical AQUAL/MOND law: diffuse weak-gradient sources retain large unsigned fourfold susceptibility and source-local positive response across representations while compact controls remain flat/negative, but phase non-invariance and no-source residual transfer-function forcing block physics promotion.
- **Eigenquestion:** Do the existing artifacts contain a representation-stable source-class phenomenon after hostile residual-transfer and morphology controls, or is the result only a paper-7 instrument anecdote?
- **Discriminating test:** Run a local offline audit over frozen `L=4,N=160,Gamma=0.25` downloaded artifacts. Combine (1) `chi(theta)=chi0+chi4*cos(4theta)` magnitude/phase fits for face-flux and isotropic-18, (2) weighted positive-delta morphology overlap between face-flux and isotropic-18 NPZ slices at `0/45/90`, and (3) analytic no-source residual-transfer `cos(4theta)` fits for `face_flux`, `isotropic_18_flux`, `normal_face_flux`, and `node_average` at `N=24/48/96/160`.
- **Success criterion for numerical-methods science-grade contribution:** UDG-like diffuse source has `|chi4/chi0| >= 0.10` in both downloaded high-N representations, compact binary has `|chi4/chi0| < 0.02` in both, UDG positive-delta support is core/halo rather than near-boundary in both, and face/isotropic positive-delta masks overlap materially. This supports a solver/source-class susceptibility finding.
- **Physics-promotion criterion:** In addition to the above, UDG phase must be invariant and the no-source residual-transfer function must not explain the observed phase/amplitude. If phase flips or residual-transfer forcing is representation-dependent, the result remains numerical-methods science, not an AQUAL/MOND orientation law.
- **Contamination guard:** This audit uses only already-downloaded artifacts and analytic residual evaluation. It cannot use tomorrow's GPU results, cannot tune thresholds after seeing outputs, and cannot call an admissible source solve failure a physics result.
- **Result:** Confirmed in the bounded sense. The local backtest classified the existing artifacts as `science_grade_numerical_methods_candidate_physics_not_promoted`. UDG unsigned fourfold amplitude is large under both downloaded high-N representations (`0.1988` face-flux, `0.2763` isotropic-18), compact binary remains flat (`0.0025`, `0.0015`), and UDG positive-delta morphology is core/halo supported with face/isotropic weighted Jaccard `0.9848` and near-boundary max around `3e-10`. Physics promotion fails because the UDG phase flips (`high_at_0_90` vs `high_at_45`) and analytic no-source residual-transfer probes show representation-dependent fourfold forcing before source loading, especially `normal_face_flux` at `N=160` with residual `chi4/chi0=0.3902`. Allowed claim: science-grade numerical-methods/instrumentation contribution. Blocked claim: astrophysical AQUAL/MOND orientation law.
- **Run(s):** `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/backtest_science_grade_controls.py`
- **Source artifacts:** `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/science_grade_local_backtest.md`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/science_grade_local_backtest.json`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/invariance_threshold_existing_backtest.json`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260502_isotropic18_n160/source_local_morphology_comparison.md`.

## H-GP116B-03 — Oracle depth aggregation as a cheap learned-routing discriminator

- **Opened:** 2026-05-02 18:48:00
- **Status:** `active`
- **Hypothesis:** Learned residual/depth routing is a plausible successor mechanism only if an oracle convex/sparse aggregation over existing transformer layer states can preserve next-token logits on held-out prompts with substantially lower effective depth entropy than uniform/full-depth use. If no such oracle exists on a small cached transformer, then implementing Attention-Residual-style routing is less urgent than recurrent/state-carrier measurements.
- **Eigenquestion:** Does depth aggregation contain measurable redundancy that can be exploited without retraining, or is the final residual state already too specialized for cheap learned routing to preserve logits?
- **Discriminating tests:**
  1. Use a cached small transformer with local weights only; no network, no remote code, no API.
  2. Collect hidden states on a fixed visible/holdout prompt split. The split is defined before fitting.
  3. Fit only global layer weights on visible prompts to minimize final-logit MSE after the model's existing final norm and LM head. Compare last-layer baseline, uniform-layer baseline, nonnegative simplex aggregation, and sparse top-k aggregation.
  4. Report holdout logit MSE, top-token match, entropy/effective number of layers, and whether the same weights transfer across prompts. Do not claim an architecture result from visible-only improvement.
- **Success criterion:** Learned-routing proxy is worth real acquisition/implementation if a nontrivial aggregation achieves holdout top-token match `>= 95%` and holdout logit MSE within `2x` of the last-layer baseline while using effective layer count `< 0.5 * n_layers` or a stable sparse top-k support. If it only wins visible and fails holdout, classify as overfit routing. If last-layer dominates, deprioritize learned-routing until a real implementation is available.
- **Kill condition:** If the proxy needs model-name/provenance features, per-prompt fitted weights, holdout-tuned thresholds, or hidden labels, it is contaminated and cannot guide GP116B. If the cached model cannot expose hidden states/final norm safely, record an instrument blocker rather than fabricating a row.
- **Interpretation boundary:** This is not a remeasurement of Attention Residuals and not a successor-architecture law. It is a cheap local discriminator for whether learned depth aggregation is worth the next acquisition dollar.
- **Source artifacts:** to be written under `projects/gp116_cot_exchange/workspace/oracle_depth_routing/`.

## H-GP116B-04 — SSM cancellation is a recurrent-state signature, not a single-window artifact

- **Opened:** 2026-05-02 17:58:40
- **Closed:** 2026-05-02 18:12:00
- **Status:** `falsified_in_strong_form / depth_phase_detected`
- **Hypothesis:** The measured Mamba/SSM cancellation row reflects a recurrent-state residual geometry that is stable across depth windows, not an artifact of using only the middle 50% of layers. If true, early/mid/late layer-window diagnostics should produce cancellation, rank, and cross-layer-cosine rows in the same broad band while remaining distinct from transformer/GQA controls.
- **Eigenquestion:** Does the only measured SSM target row generalize across depth windows strongly enough to support GP116B law-gate transfer, or is it a fragile single-window summary that should remain planning context until more SSM models are acquired?
- **Discriminating test:** Re-run the existing local diagnostic harness on cached weights with explicit layer windows for the same SSM model, using local CPU fallback and no network acquisition. Write each window as a measured law-target row only if the diagnostic completes and exposes cancellation/rank/cosine under the same feature/provenance split as the existing summary.
- **Success criterion:** At least three SSM windows complete, cancellation stays within a `15` percentage-point band, and effective rank/cross-layer cosine remain finite and comparable. If the band is wider or one window collapses, classify the existing SSM row as window-sensitive and do not use it as a clean holdout-transfer target.
- **Kill condition:** If the run requires new downloads, remote code beyond the already used cached local model path, GPU spend, or per-window post-hoc tuning, stop and record acquisition blocker instead of fabricating rows.
- **Interpretation boundary:** Multiple windows from one model are not independent architecture-family validation. They only test whether the existing SSM measurement is stable enough to guide the next acquisition and prevent the hard holdout from resting on a single aggregate.
- **Source artifacts:** `projects/gp116_cot_exchange/run_diagnostics.py`, `projects/gp116_cot_exchange/workspace/diagnostics_mamba-370m-hf*.json`.
- **Closure:** Early and middle windows matched the aggregate (`60.1%`, `60.6%`, `62.2%` cancellation), but the late window jumped to `88.6%` cancellation with lower rank (`86.4`) and higher cross-layer cosine (`0.246`). The stability criterion failed with a `28.5` percentage-point cancellation band. Interpret the Mamba/SSM row as depth-phase dependent, not a uniform family scalar.

## H-GP186-5CG — Leray dynamic-rescaling discriminator for old-branch terminal spike

- **Opened:** 2026-05-02 00:00:00
- **Status:** `active`
- **Hypothesis:** The old chiral Navier-Stokes branch that became dx-limited at `N=384` is either a genuine self-similar concentration candidate or a numerical grid-amputation artifact. A dynamically rescaled Leray-frame local solver can distinguish these without AMR interface damping: a true self-similar blowup candidate should approach a nonzero steady rescaled vorticity profile, while physical arrest should collapse or widen in the rescaled frame before the Nyquist wall.
- **Eigenquestion:** After fixing a non-posthoc rescaling gauge from the peak center and local width/second moment, does the rescaled peak profile stabilize, keep thinning, or collapse?
- **Discriminating tests:**
  1. **Gauge freeze before run:** choose `x_*(t)` as the vorticity-maximum tracker and choose `L(t)` from a declared local width functional (`0.90` superlevel thickness or weighted second moment, with a fixed fallback rule when the superlevel is one-cell-limited). The run may not refit `L(t)` after seeing outcomes.
  2. **No AMR interface claim:** do not stitch a high-resolution patch into the low-resolution full box and call it physical. Boundary/interpolation damping is treated as a false-negative channel unless separately quantified.
  3. **Rescaled-local solver pilot:** implement a localized nonperiodic finite-difference vorticity/velocity solver for the Leray-frame PDE, including the dilation drift term and a pressure/velocity recovery method compatible with the nonperiodic box. The first pilot can be short-window and diagnostic, but it must report divergence error, boundary flux, energy/enstrophy budget residual, and sensitivity to boundary placement.
  4. **Resolution control:** compare at least two local patch resolutions or two physical patch sizes under the same frozen gauge. A candidate signal that flips under boundary placement is classified as instrument debt.
- **Success criterion:** Promote the old branch from `resolution_limited_candidate` to `self_similar_candidate` only if the rescaled vorticity profile and width stabilize over increasing rescaled time while divergence/boundary-budget residuals remain controlled. Promote `physical_arrest_candidate` only if the rescaled profile collapses or widens before boundary contamination and the result is stable under patch-size/resolution perturbation.
- **Kill condition:** If the result depends materially on outflow boundary damping, pressure-solve choice, or posthoc gauge changes, the experiment is an instrument failure, not evidence for blowup or arrest. If the local solver cannot preserve incompressibility/budget diagnostics on a known smooth vortex test, it cannot be used on the old branch.
- **Interpretation boundary:** Phase 5CG is a science discriminator, not a Clay proof. It tests whether the N384 one-cell spike deserves expensive higher-resolution/self-similar follow-up. It does not globalize the branch to all Navier-Stokes data.
- **Source artifacts:** `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cf_debrief.md`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cf_n384_peak_patch_amr_proxy_N384.json`, `projects/ns_millennium_hunt/workspace/phase5cf_n384_peak_patch_amr_proxy.py`.

## H-NS-5CH — Exponential capacity-realization falsifier for Paper 7 math-level obstruction

- **Opened:** 2026-05-02 20:24:00
- **Status:** `closed / falsified_overbroad_obstruction / generator_cap_gap_is_load_bearing`
- **Hypothesis:** The exponential route-5 obstruction becomes a genuine math-level Paper 7 object only if the capacity-deficit burden can be forced from branch-native definitions rather than inserted as `¬ curvatureCapacityMatchingTarget`. In a frozen finite-dimensional Navier-Stokes model class, either a bounded exponential generator can realize the required curvature-capacity matching, falsifying the obstruction route, or the model admits an exact positive deficit certificate that can later be checked by a tiny Lean/SOS verifier.
- **Eigenquestion:** Is there a branch-native source for `targetCurvature > capacityBudget * (hnorm + 1)`, or can an explicit admissible finite model realize `targetCurvature <= realizedCapacity <= capacityBudget * (hnorm + 1)` with bounded `hnorm`?
- **Discriminating tests:**
  1. **Freeze definitions before search:** choose a small exact divergence-free Fourier/jet class, normalization, `targetCurvature`, `capacityBudget`, `hnorm`, and admissibility constraints before fitting or optimization. The definitions must be traceable to `exponentialMetricCapacityDeficitTarget`, not invented after seeing a counterexample.
  2. **Counterexample arm:** search for a rational or high-precision candidate satisfying ellipticity/generator cap and curvature-capacity matching. A single explicit candidate revives the exponential branch and demotes INS-076 from obstruction target to branch-ranking heuristic.
  3. **Certificate arm:** if the search finds no candidate, emit an exact rational inequality/SOS-style receipt for the frozen finite class proving `targetCurvature - capacityBudget * (hnorm + 1) >= δ > 0`. The receipt must be independently arithmetic-checkable before any Lean work.
  4. **Formal-resource guard:** do not run `ns_exponential_metric_transport_ratio_obstruction.lean` locally. Any Lean check must be a tiny receipt verifier or a high-memory bounded forensic run with hard memory/time limits.
- **Success criterion:** Math-level promotion requires either (a) an explicit falsifying capacity-realization example, which is a real theorem-search update because it kills the obstruction path, or (b) an exact positive-deficit certificate for a nontrivial frozen model class with independent arithmetic verification and a clear path to a small Lean receipt check. A replay ratio, threshold robustness note, or unsafe Lean elaboration does not satisfy this criterion.
- **Kill condition:** If the finite class depends on posthoc denominators, empirical shell-centroid tuning, hidden replay labels, or definitions that already encode `¬ curvatureCapacityMatchingTarget`, the discriminator is contaminated and cannot support Paper 7 math insight.
- **Interpretation boundary:** A finite-class certificate is not a Clay theorem. Its value is to convert the exponential obstruction from instrument-supported branch compression into a precise mathematical obstruction or falsification in a declared model class. The PDE-global burden remains open until the finite certificate is lifted to a genuine a priori estimate.
- **Source artifacts:** `projects/ns_millennium_hunt/workspace/phase5cg_paper7_obstruction_candidate.md`, `projects/ns_millennium_hunt/workspace/phase5cg_decisive_fork_status.md`, `ztare_proofs/ZtareProofs/ns_exponential_metric_capacity_deficit.lean`, `ztare_proofs/ZtareProofs/ns_exponential_metric_nontriviality_bar.lean`, `ztare_proofs/ZtareProofs/ns_sos_certificate_bridge.lean`.
- **Closure (2026-05-02 20:31:00 EDT):** `phase5ch_capacity_realization_falsifier.py` found exact scalar capacity-matching witnesses for all observed transport-scale ratios when `hnorm` is uncapped. For a ratio `R`, the witness `capacityBudget=1`, `targetCurvature=R`, `realizedCapacity=R`, `hnorm=R-1` satisfies `curvatureCapacityMatchingTarget` exactly. The max observed ratio `15.7538` requires `hnorm=14.7538`, equivalently `lambdaMin≈3.913e-7`. Therefore transport-scale stress alone does not prove a capacity deficit under the current strict-ellipticity-only target. The math-level object must be narrowed to either a PDE-side uniform generator cap / ellipticity-floor theorem, or a required-metric-degeneracy theorem. No Lean build was run.

## H-NS-5CI — Exponential metric-degeneracy receipt for Paper 7 science-grade insight

- **Opened:** 2026-05-02 20:32:00 EDT
- **Status:** `closed / science_grade_candidate_required_metric_degeneracy`
- **Hypothesis:** The Phase 5CH falsifier can be inverted into a positive math-level insight: under the current exponential metric definitions, any curvature-capacity match for a transport ratio `R = targetCurvature / capacityBudget` forces a generator burden `hnorm >= R - 1`, hence the exponential ellipticity parameter must satisfy `lambdaMin = exp(-hnorm) <= exp(1 - R)`. Therefore the route-5 exponential branch is not merely "locally stressed"; it survives the observed transport burden only by accepting a quantifiable metric-degeneracy scale unless a PDE-side uniform generator cap or ellipticity floor is proved.
- **Eigenquestion:** Does the current route-5 transport corpus produce a stable, branch-native quantitative degeneracy law, rather than only an instrument ranking or an overbroad obstruction claim?
- **Discriminating tests:**
  1. **Exact algebraic receipt:** derive every reported number from the already-formalized `generator_norm_burden_of_curvatureCapacityMatching` burden and `exponentialMetricEllipticityTarget`, without invoking the quarantined transport-ratio Lean bridge.
  2. **Floor frontier:** compute the exact survival/obstruction frontier `R <= 1 - log(lambda_floor)` for a declared ladder of uniform ellipticity floors. A science-grade receipt must say which floors actually obstruct the observed ratios.
  3. **Branch-native interpretation:** classify the result as `required_metric_degeneracy`, not as `capacity_deficit`, unless the floor frontier supplies an independent uniform cap.
  4. **Resource guard:** no umbrella Lean build and no quarantined Lean target. This run is bounded to JSON arithmetic plus a paper-facing receipt.
- **Success criterion:** Promote a science-grade insight only if the receipt produces a simple invariant statement that survives the Phase 5CH counterexample: matching is possible under strict ellipticity, but the required lower eigenvalue scale is forced below a concrete threshold by the observed transport ratios.
- **Kill condition:** If the result depends on empirical threshold labels, unstated capacity normalization, posthoc denominator choice, or any formal target that has not been safely checked, it remains an instrument note rather than a math-level insight.
- **Interpretation boundary:** This is still not a Navier-Stokes regularity proof. It is a theorem-facing obstruction/degeneracy law for one compressed route-5 survivor branch, calibrated by the saved transport audit.
- **Source artifacts:** `projects/ns_millennium_hunt/workspace/phase5ch_capacity_realization_falsifier.json`, `projects/ns_millennium_hunt/workspace/remote_results/20260502_phase5cg_r64_final_audits/phase5cg_route5_transport_scale_audit.json`, `ztare_proofs/ZtareProofs/ns_exponential_metric_capacity_deficit.lean`, `ztare_proofs/ZtareProofs/ns_route5_exponential_metric_curvature_capacity.lean`.
- **Closure (2026-05-02 20:35:00 EDT):** `phase5ci_metric_degeneracy_receipt.py` produced the positive receipt. The formal anchor is the already-recorded burden `generator_norm_burden_of_curvatureCapacityMatching`: if `R * capacityBudget <= targetCurvature`, matching forces `hnorm >= R - 1`. Combining this with `lambdaMin = exp(-hnorm)` gives the required-degeneracy law `lambdaMin <= exp(1 - R)`. On the saved route-5 transport audit, the worst ratio is `max_Hp_over_DtOmega = 15.7538`, forcing `hnorm >= 14.7538` and `lambdaMin <= 3.913e-7`. Therefore a uniform ellipticity floor of `1e-6` or stronger would obstruct the observed max burden, while strict ellipticity alone keeps the branch alive by allowing near-degenerate metrics. No Lean build was run.

## Related Artifacts

- GP-023 ontology-trap seam: `research_areas/private/seams/GP-023_ontology_trap_planck_mechanism_seam.md` — program-specific debate for the sandbox_03/04/05 trajectory
- GP-046 empirical anchor memory: `~/.claude/projects//memory/project_gp046_empirical_anchor.md` — the finding this seam's Turn 1 is trying to strengthen
- GP-047 preservation lane spec: `research_areas/private/specs/active/GP-047_preservation_lane_probe_spec.md` — blocked on GP-048 and FIT_DECLARATION drought fix
- GP-048 math AST analyzer spec: `research_areas/private/specs/active/GP-048_math_ast_analyzer_spec.md` — the infrastructure Candidate E depends on
- Three Legs of ZTARE doc: `research_areas/private/philosophy/three_legs_of_ztare.md` — the framework this seam's mission framing is derived from

## H-GP188-WORKSTATION-01 — ZTARE workstation value over RD-only local reasoning

- **Opened:** 2026-05-11
- **Status:** `open / no-spend_validation_registered`
- **Hypothesis:** `RD + extracted ZTARE primitives` produces better frontier
  next moves than `RD-only out-of-loop` reasoning on tasks where graph/workmap,
  proof-gate, motion/Jaccard/BIC, or pattern-chain state matters. The full
  `autoresearch_loop` adds additional value only after primitive insufficiency,
  stable substrate, independent falsification, telemetry need, and explicit
  principal approval.
- **Eigenquestion:** When does ZTARE as an active workstation change the
  Director's next move relative to ordinary local reasoning, and when is the
  full loop worth its cost over the extracted primitive bench?
- **Discriminating test:** Run a no-spend retrospective and later prospective
  matched-task audit with three arms: RD-only, RD plus extracted primitives, and
  approved full-loop use. Score next-action quality, primitive yield, rework
  reduction, artifact density, decision latency, anti-tautology catches, and
  closure discipline. The full-loop arm is not authorized by this row; it
  requires separate approval for any spend-bearing run.
- **Success criterion:** The extracted primitive bench is validated if it beats
  RD-only by at least 30 percent on next-action/artifact quality or rework
  reduction at similar time budget, or if it prevents at least two unnecessary
  cold-shot/full-loop spends by resolving questions locally. Full-loop value is
  validated only if an approved stable candidate produces telemetry or frame
  changes the extracted bench could not reasonably produce.
- **Kill condition:** Demote the workstation thesis if extracted primitives
  mostly reproduce RD-only conclusions, graph/workmap outputs do not affect
  next actions, or the full loop wins only by spending more without durable new
  mechanisms. Reject any retrospective audit contaminated by outcome knowledge
  unless a prospective task later confirms the effect.
- **Interpretation boundary:** This is a methodology validation, not an NS
  theorem and not a launch authorization.
- **Source artifact:** `research_areas/seams/protocol/GP-188_ztare_workstation_value_thesis_2026_05_11.md`

## H-GP163D-CRAPD-HARDEN-01 — CR-APD checker seeded-attack suite for false-promotion resistance

- **Opened:** 2026-05-03 23:52:00 EDT
- **Status:** `open / testing`
- **Hypothesis:** The current `CR-APD` checker should fail closed on the obvious false-promotion modes available before any real clean-room implementation exists: copied-row laundering, negative or zero `Delta_e`, denominator-floor contamination, and fake certificate claims. If any seeded attack passes, the checker is under-specified and the protocol is not yet safe to hand off as a science-promotion gate.
- **Eigenquestion:** Does the existing `CR-APD` checker kill the obvious cheats, or are there loopholes that would allow solver-local regularity to masquerade as portable science?
- **Discriminating tests:**
  1. **Copied-row laundering attack:** mark the clean-room certificate fields as passed while reusing current-ecosystem rows. The checker should fail on certificate inconsistency even if the row deltas are positive.
  2. **Delta-collapse attack:** perturb a seeded row set so at least one extractor has `Delta_e <= 0`. The checker should fail on the extractor rule.
  3. **Floor-artifact attack:** mark at least one row with `denominator_floor_artifact=true`. The checker should fail regardless of the deltas.
  4. **Combined fake-clean-room attack:** create a superficially plausible certificate/row pair that passes only by copied rows plus false metadata. The checker should still fail.
- **Success criterion:** All seeded attacks fail closed, or any surviving loophole is surfaced explicitly and fixed before the packet is treated as the next science-promotion gate.
- **Kill condition:** If the attack suite depends on hidden assumptions not encoded in the frozen contract, the result is not admissible as checker hardening. The gap must then be repaired by tightening the contract, not by ad hoc interpretation.
- **Interpretation boundary:** A passing attack suite does not promote the gravity branch. It only establishes that the `CR-APD` protocol is mechanically resistant to the cheapest false-promotion paths before an external implementation is attempted.
- **Source artifacts:** `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/run_crapd_contract_check.py`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_protocol_contract.json`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_baseline_rows_current_ecosystem.json`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_current_ecosystem_certificate.json`.

## H-GP163D-SUSLAW-01 — bounded diffuse susceptibility regime law packet vs no-go theorem

- **Opened:** 2026-05-04 00:05:00 EDT
- **Status:** `open / testing`
- **Hypothesis:** The current gp163d evidence can support a stronger science-grade statement than “instrument audit” without overclaiming astrophysics: a bounded diffuse susceptibility regime law for nonlinear AQUAL-style solving. If that is false, the correct result is a no-go theorem saying the branch cannot honestly sustain any stronger law than the existing `CR-APD -> RAGT` bridge.
- **Eigenquestion:** What is the strongest bounded law packet current evidence can honestly sustain, and what would it resolve in the current modified-gravity literature if true?
- **Discriminating tests:**
  1. Run a dedicated ZTARE qualitative-law packet substrate that asks explicitly for one of: bounded law packet, attacker packet, no-go theorem, or validation reranking.
  2. Reject any candidate that merely restates phase structure, repackages the primitive anchor as an astrophysical law, or launders same-family regularity into independence.
  3. Prefer outputs that state explicit nonclaims, literature-resolution value, and independent validation burden.
  4. Promote only if the best iteration changes what the repo should say or build next compared with the existing `CR-APD -> RAGT` frontier.
- **Success criterion:** A successful run yields either (a) a bounded diffuse susceptibility regime law packet stronger than the current bridge while remaining scope-honest, or (b) a clear no-go theorem / attacker packet proving that current evidence cannot yet support such a law. Mere rhetorical elevation does not count.
- **Kill condition:** If the best output still depends on implementation-local regularity, phase recovery pretense, or MOND/dark-matter overclaim, the law packet is contaminated and must be demoted.
- **Interpretation boundary:** Even a successful bounded law packet would remain below an astrophysical law claim until an independent implementation axis and later external-system bridge survive.
- **Source artifacts:** `rubrics/gp163d_susceptibility_regime_law.json`, `projects/gp163d_susceptibility_regime_law/project_charter.md`, `projects/gp163d_susceptibility_regime_law/evidence.txt`, `projects/gp163d_susceptibility_regime_law/test_model.py`.

## H-GP163D-ADMSR-BRIDGE-01 — minimal clean-room + attacker bridge for ADMSR

- **Opened:** 2026-05-03 16:35:00 EDT
- **Status:** `open / testing`
- **Hypothesis:** The law-packet search has converged far enough: `ADMSR` is already the right bounded promotion gate. The next discriminating ZTARE substrate should therefore stop searching for a stronger law statement and instead answer three narrower questions: what is the smallest honest clean-room independence standard that counts as real ADMSR evidence, what hostile attacker bundle could still kill it, and what is the cheapest campaign that would actually change belief. If that is false, the output should be a no-go theorem saying that even this narrower bridge cannot yet be made concrete without hidden assumptions.
- **Eigenquestion:** What is the minimum honest implementation-independence contract and attacker suite that could move gp163d from bridge science toward a bounded regime-law candidate without overclaiming?
- **Discriminating tests:**
  1. Run a dedicated qualitative ZTARE substrate whose allowed outputs are: minimal clean-room contract, attacker packet, cheapest belief-changing campaign plan, or a no-go theorem against premature concretization.
  2. Reject candidates that merely restate `ADMSR`, inflate into validation bureaucracy, or sneak same-family regularity into the definition of independence.
  3. Prefer outputs that make the clean-room threshold smaller but still real, enumerate concrete remaining artifact channels beyond the current seeded checker, and rerank the cheapest next build/test.
  4. Promote only if the best iteration changes what code or experiment should be built next relative to the already-frozen `CR-APD -> RAGT -> ADMSR` frontier.
- **Success criterion:** A successful run yields either (a) a concrete minimal clean-room + attacker contract that is narrower and more buildable than the current prose frontier while remaining scientifically honest, or (b) a no-go theorem proving that current evidence cannot yet specify such a contract without hidden contamination.
- **Kill condition:** If the best output still depends on “more validation” in the abstract, fails to name real attacker channels, or treats same-family extractor diversity as independence, the bridge packet is contaminated and must be demoted.
- **Interpretation boundary:** Even a successful bridge packet does not itself promote the gravity branch. It only fixes the next executable validation object. Astrophysical law remains out of scope.
- **Source artifacts:** `rubrics/gp163d_admsr_attack_and_cleanroom_bridge.json`, `projects/gp163d_admsr_attack_and_cleanroom_bridge/project_charter.md`, `projects/gp163d_admsr_attack_and_cleanroom_bridge/evidence.txt`, `projects/gp163d_admsr_attack_and_cleanroom_bridge/test_model.py`.

## H-NEURAL-HUNT-82 — Joinable schema-response activation bridge packet

- **Opened:** 2026-05-11 15:45 EDT
- **Status:** `open / pre-registered / no-spend`
- **Hypothesis:** If Neural Hunt's activation/schema compression is a
  checkpoint-state mechanics signal rather than lexical proximity or
  subject-matter difficulty, then activation schema-delta features computed on
  the same items/categories as response/schema residuals should add held-out
  predictive power after maturity, schema, category, and family controls.
- **Eigenquestion:** Does internal activation geometry explain response/schema
  residual movement on a joinable item/category panel, or did H80/H81 only
  expose a useful graph route with no mechanistic join?
- **Discriminating test:** Build a joinable H82 packet with base/`:mc` schemas,
  at least `8` OLMo2 1B checkpoints, at least `12` unique documents per
  category/schema/checkpoint, and categories spanning `late_signature`,
  `science_qa`, and `boolean_reading`. Extract H75-style residual-state
  features and score them with the H78 family-controlled whole-checkpoint
  holdout evaluator, extended to category fixed effects and held-out-category
  checks.
- **Success criterion:** Promote the bridge only if activation features improve
  whole-checkpoint or held-out-category prediction over maturity, schema,
  category, and family controls on at least `8` checkpoints and `24`
  family/category rows. The result must survive the H81 anti-tautology null:
  it cannot be explained as "science tasks are hard" or "Jaccard artifacts
  share vocabulary."
- **Kill condition:** Demote the bridge if no direct item/category join exists,
  if activation features fail to beat controls, if the signal lives only in a
  single semantic category, or if it reverses under held-out-category scoring.
- **Interpretation boundary:** A positive H82 would support a bounded
  evaluator-response state-variable mechanism with internal activation
  correlates. It would not promote a universal neural power law or a next
  transformer-architecture claim by itself.
- **Source artifacts:** `analytics/public/queries/neural_hunt/h80_neural_basin_jaccard_graph_2026_05_11.md`, `projects/neural_hunt/workspace/h81_bridge_actionability_audit_2026_05_11.md`, `projects/neural_hunt/workspace/h82_schema_response_activation_bridge_packet_2026_05_11.md`, `projects/neural_hunt/workspace/h82_hellaswag_continuation_axis_run_commands_2026_05_11.sh`, `projects/neural_hunt/workspace/h83_h82_available_subset_null_audit_2026_05_11.md`, `projects/neural_hunt/workspace/h84_h82_available_cross_category_activation_packet_2026_05_11.md`, `projects/neural_hunt/workspace/h84_cross_category_activation_extraction_commands_2026_05_11.sh`, `projects/neural_hunt/workspace/run_h85_category_controlled_bridge_evaluator.py`, `projects/neural_hunt/workspace/h86_hellaswag_continuation_axis_ingest_gate_2026_05_11.md`, `projects/neural_hunt/workspace/h87_h82_full_bridge_activation_packet_2026_05_11.md`, `projects/neural_hunt/workspace/h87_full_bridge_activation_extraction_commands_2026_05_11.sh`, `projects/neural_hunt/workspace/h88_datadecide_continuation_axis_value_audit_2026_05_11.md`, `projects/neural_hunt/workspace/h89_hellaswag_progressive_acquisition_plan_2026_05_11.md`, `projects/neural_hunt/workspace/h90_datadecide_response_mode_exchange_audit_2026_05_11.md`, `projects/neural_hunt/workspace/h91_h82_post_acquisition_sequence_gate_2026_05_11.md`, `projects/neural_hunt/workspace/h92_h82_category_exchange_contrast_audit_2026_05_11.md`, `projects/neural_hunt/workspace/h93_exchange_schema_gap_proxy_join_2026_05_11.md`, `projects/neural_hunt/workspace/h94_h86_gate_minimum_synthetic_fixture_2026_05_11.md`, `projects/neural_hunt/workspace/h95_hellaswag_exchange_phase_stability_audit_2026_05_11.md`, `projects/neural_hunt/workspace/run_h78_family_controlled_activation_evaluator.py`.

## H-NEURAL-HUNT-96 — Managerial-debt prior-substrate synthesis for successor architecture

- **Opened:** 2026-05-11
- **Status:** `closed / no-spend_prior_substrate_synthesis`
- **Hypothesis:** Prior autoresearch substrates can constrain Neural Hunt's
  "new Transformer architecture" route into a measurable intervention packet:
  if response-mode/category/schema state is a real internal coordinate, then
  some depth windows may be replaceable by cheaper state carriers without
  losing logit retention, rank/survival, or schema residuals.
- **Eigenquestion:** Does the existing GP116/GP154 evidence make managerial
  debt a mechanizable architecture hypothesis, or is it still an unmeasured
  metaphor?
- **Discriminating test:** Scavenge GP116B/GP116C and GP154 closure artifacts
  and compare their constraints against Neural Hunt H82-H95. Require the output
  to name what would be intervened on, what cheaper carrier replaces it, what
  observables must be preserved, and what would falsify the architecture route.
- **Success criterion:** The synthesis is useful only if it changes the next
  architecture move from generic layer pruning or architecture-family ranking
  to a within-model, depth-window intervention with logit retention,
  effective-rank/survival, schema residual, and cost observables.
- **Kill condition:** If the route depends on GP116B's invalidated successor-law
  result, on model-family labels, on a one-scalar neural power law, or on
  preserving scalar accuracy while ignoring rank/logits/cost, it remains
  non-actionable.
- **Interpretation boundary:** This is not a successor architecture result. It
  is a no-spend intervention-packet synthesis that becomes executable only after
  H89/H86/H87/H85 expose a joinable activation-response bridge.
- **Source artifact:** `projects/neural_hunt/workspace/h96_managerial_debt_prior_substrate_synthesis_2026_05_11.md`.

## H-NEURAL-HUNT-97 — Local managerial-debt proxy before GPU continuation

- **Opened:** 2026-05-11
- **Status:** `closed / underpowered_route_selector`
- **Hypothesis:** Existing cached H75/H78 activation rows may already show
  whether H96's managerial-debt route has an activation-state footprint, even
  before H89 supplies the missing continuation cells.
- **Eigenquestion:** Does any schema activation delta remain coupled to
  controlled schema residuals after simple family/step centering, or is the
  managerial-debt bridge currently only a verbal synthesis?
- **Discriminating test:** Attempt local H73 extraction resume; if blocked by
  cache/network, run a no-download proxy over existing H78 family-step rows.
  Score raw, family-centered, and family+step-centered correlations between
  activation schema deltas and H71 controlled residual targets, with permutation
  nulls.
- **Success criterion:** Route support requires a controlled activation feature
  with a strong centered relation to `abs_pc2_residual_contribution` or
  `pc2_residual_contribution`, while preserving the boundary that fewer than
  `8` checkpoints cannot promote.
- **Kill condition:** If all controlled relations collapse after centering, H96
  remains only an intervention-frame synthesis until H89/H85 produces new data.
- **Interpretation boundary:** This is a local proxy only. It cannot replace
  H89/H85 because it has only `3` checkpoints, `3` families, and no continuation
  category.
- **Closure:** H73 resume failed offline at `stage1-step50000` because the
  local cache lacks model shards. H97 then scored the cached H78 rows. The
  strongest family+step-centered relation is
  `cancellation_proxy_mean_mc_minus_base` to
  `abs_pc2_residual_contribution`, correlation `0.918`, permutation `p≈0.0001`
  over `20,000` shuffles. Effective-rank mean was weaker. This supports the
  route as a next-test selector and shifts attention toward cancellation/
  update-direction state carriers, not just rank compression.
- **Source artifacts:** `projects/neural_hunt/workspace/run_h97_local_managerial_debt_proxy.py`, `projects/neural_hunt/workspace/h97_local_managerial_debt_proxy_2026_05_11.md`.

## H-NEURAL-HUNT-98 — Local H68 activation bridge after targeted OLMo2 download

- **Opened:** 2026-05-11
- **Status:** `closed / local_activation_bridge_pc1_pass`
- **Hypothesis:** If the H62 schema-state trajectory is not only an evaluation
  artifact, then residual-geometry features on the frozen H73 activation packet
  should improve whole-checkpoint prediction over maturity/schema controls once
  at least `8` checkpoint contexts are available.
- **Eigenquestion:** Does local residual geometry explain H68 schema-state
  movement beyond `log10_step_plus1`, `mean_schema_gap`, and
  `schema_gap_range` controls?
- **Discriminating test:** Download only the missing OLMo2 checkpoints needed
  to reach eight H73 contexts, extract residual-state features locally, run
  `run_h68_residual_feature_evaluator.py`, and then audit the pass with an
  exact permutation null over all `8!` checkpoint feature assignments.
- **Success criterion:** Promote a local bridge only if at least one residual
  feature gives at least `20%` additive leave-one-checkpoint-out MAE reduction
  over controls, and the exact checkpoint-shuffle null supports the result.
- **Kill condition:** If the pass disappears under exact permutation or only
  helps PC2/PC1 by a negligible amount, the activation bridge remains a weak
  route selector and H96 cannot use it as architecture prior.
- **Interpretation boundary:** This is a local H68 bridge, not full H82/H85.
  HellaSwag continuation and category-controlled cell scoring remain absent.
- **Closure:** H98 downloaded five missing checkpoints (`50000`, `100000`,
  `200000`, `800000`, `1200000`) and extracted the H73 residual features on
  CPU because local MPS is not supported on this OS. H68 passes for
  `schema_pc1`: `cross_layer_cosine_delta` adds `0.754` relative MAE reduction
  over controls, exact permutation `p=0.000074`; `cross_layer_cosine_mean`
  adds `0.749`, `p=0.0076`; `cancellation_proxy_mean` adds `0.669`, `p=0.038`.
  PC2 does not pass (`best additive=0.031`, `p=0.156`). The broad schema-state
  coordinate has a local residual-geometry bridge; the residual splitter is
  unresolved.
- **Source artifacts:** `projects/neural_hunt/workspace/h68_residual_feature_evaluator_2026_05_11.md`, `projects/neural_hunt/workspace/h98_h68_local_bridge_null_audit_2026_05_11.md`.

## H-NEURAL-HUNT-99 — 8-checkpoint cell-level audit of the unresolved PC2 splitter

- **Opened:** 2026-05-11
- **Status:** `closed / cell_level_pc2_not_promoted`
- **Hypothesis:** If H98's PC2 miss is only caused by whole-checkpoint
  aggregation, then family/schema-local residual-state deltas on the same
  eight H73 checkpoints should line up with H71's controlled PC2 residual
  mass.
- **Eigenquestion:** Does the PC2 splitter become visible when residual
  features are measured as mc-minus-base deltas inside the PC2-heavy
  family/checkpoint cells?
- **Discriminating test:** Run `extract_h74_residual_cell_features.py` over
  the eight H73 checkpoints (`0`, `10000`, `50000`, `100000`, `200000`,
  `400000`, `800000`, `1200000`) and analyze the resulting `48` cell rows /
  `24` schema deltas against H71 controlled PC2 contributions.
- **Success criterion:** A promotion-grade PC2 route requires a residual-state
  schema delta that tracks absolute PC2 contribution rather than only signed
  family/schema mode, with enough packet diversity to make rank findings
  interpretable.
- **Kill condition:** If the largest schema deltas are family-specific and do
  not track absolute PC2 residual contribution, do not treat PC2 as explained
  by generic schema compression.
- **Closure:** H99 finds large repeated effective-rank drops for
  `mmlu_professional_medicine` (`mc-base` about `-0.61` to `-0.66` across all
  eight checkpoints), but the link to absolute PC2 contribution is weak and
  wrong-signed (`residual_effective_rank_mean r=-0.145`). The strongest signed
  links are only route-selector scale (`cross_layer_cosine_mean r=0.413`,
  `residual_delta_norm_mean r=-0.386`, `cancellation_proxy_mean r=-0.315`).
  Packet diversity remains low (`3` unique docs per cell). PC2 remains an
  unresolved category/interface splitter, not a promoted local
  schema-compression bridge.
- **Source artifacts:** `projects/neural_hunt/workspace/h99_h73_8step_residual_cell_features_2026_05_11.csv`, `projects/neural_hunt/workspace/h99_h73_8step_residual_cell_feature_analysis_2026_05_11.md`, `projects/neural_hunt/workspace/h99_h73_8step_residual_cell_feature_analysis_2026_05_11.json`.

## H-NEURAL-HUNT-100 — Doc-balanced 8-checkpoint PC2 cell bridge

- **Opened:** 2026-05-11
- **Status:** `closed / doc_balanced_pc2_not_promoted`
- **Hypothesis:** H99 may be a false negative because each measured cell used
  only `3` unique documents. If the PC2 splitter is a real local
  residual-state bridge rather than a family/schema artifact, then rerunning
  the same cell-level extraction on the doc-balanced H75 packet should improve
  the alignment between mc-minus-base residual-state deltas and H71 controlled
  PC2 residual contribution.
- **Eigenquestion:** Does doc-balancing convert the PC2 cell signal from
  family/schema compression into target-aligned residual prediction?
- **Discriminating test:** On an A100 host, run
  `extract_h74_residual_cell_features.py` against
  `h75_h68_doc_balanced_prompt_packet_2026_05_11.jsonl` for checkpoints
  `0`, `10000`, `50000`, `100000`, `200000`, `400000`, `800000`, and
  `1200000`, then run `analyze_h74_residual_cell_features.py`.
- **Success criterion:** Promote PC2 only if a feature family shows
  target-aligned schema deltas against absolute or controlled PC2 contribution
  after doc-balancing, not merely a repeated professional-medicine rank drop.
- **Kill condition:** If doc-balanced rows preserve large family/schema rank
  compression but still do not track PC2 residual contribution, treat PC2 as
  category/interface structure requiring H85 continuation/category controls.
- **Interpretation boundary:** H100 can repair the H99 packet-diversity caveat.
  It still does not replace the full H85 continuation/category-controlled
  bridge.
- **Closure:** H100 ran successfully on A100 and produced `48` cell rows /
  `24` schema deltas over `8` checkpoints with `48` rows and `12` unique docs
  per cell. Doc-balancing did not promote PC2. Effective-rank schema
  compression is cleaner and large, but still not target-aligned:
  `residual_effective_rank_mean` vs absolute PC2 contribution has
  `r=-0.275`; `cross_layer_cosine_mean r=-0.254`;
  `residual_delta_norm_mean r=-0.190`; `cancellation_proxy_mean r=0.006`.
  The strongest repeated effect is still family/schema compression, especially
  professional medicine (`mc-base` effective-rank drop about `-0.50` to
  `-0.53`). PC2 remains a category/interface object for H85, not a local
  schema-compression architecture target.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h100_remote_a100_2026_05_11/h100_h75_doc_balanced_8step_residual_cell_feature_analysis_2026_05_11.md`,
  `projects/neural_hunt/workspace/h100_remote_a100_2026_05_11/h100_h75_doc_balanced_8step_residual_cell_features_2026_05_11.csv`,
  `ztare_workspace/external_runs/neural-hunt-h100-doc-balanced-cell-extraction-20260511T225417Z-4e24a5c9`.

## H-NEURAL-HUNT-101 — Operator-incepted managerial-debt architecture intervention

- **Opened:** 2026-05-11
- **Status:** `open / design_after_h100`
- **Hypothesis:** Transformer depth may include "managerial debt": layers spend
  coordination work preserving and reconciling response-state variables that a
  cheaper state carrier could preserve more directly. The next architecture
  evolution, if this is true, is not generic layer pruning; it is a
  depth-window carrier replacement that preserves measured learning-mechanics
  coordinates with lower marginal compute/state cost.
- **Eigenquestion:** Which measured state coordinate is stable and local enough
  to become an architecture intervention target: H98's broad PC1
  residual-geometry/cancellation bridge, or a H100-positive PC2
  category/interface bridge?
- **Discriminating test:** Use H98/H100 to select the carrier target. Then
  design a within-model depth-window intervention that replaces or compresses
  the selected window and scores logit retention, effective-rank/survival,
  schema residual preservation, response-mode coordinate preservation, and
  cost.
- **Success criterion:** A successor-architecture claim requires a cost win
  with preserved logits and preserved response-state coordinates. A score-only
  or rank-only win is not sufficient.
- **Kill condition:** If the measured coordinate cannot be localized to
  windows or survives only as an evaluator aggregate, keep it as learning
  mechanics, not architecture evidence.
- **Operator inception:** Principal hypothesis: humans bootstrap LLMs, LLMs may
  bootstrap the next architecture; by analogy to managerial capitalism, current
  Transformer layers may accumulate coordination debt, and inversion +
  compression may expose a better carrier.

## H-NEURAL-HUNT-102 — Layer-window localization for the H98 PC1 carrier

- **Opened:** 2026-05-11
- **Status:** `closed / localized_pc1_carrier_candidate`
- **Hypothesis:** If H98's broad `schema_pc1` bridge is architecture-relevant,
  its strongest residual-geometry/cancellation features should localize to
  depth windows or transition bands rather than existing only as whole-model
  aggregates.
- **Eigenquestion:** Which layer-transition windows carry the H98 PC1
  residual-geometry/cancellation signal strongly enough to become a
  depth-window compression/replacement target?
- **Discriminating test:** On the A100 with cached OLMo2 checkpoints, replay
  the H73 activation packet for the same eight checkpoints and emit per-window
  transition features: cross-layer cosine, cross-layer cosine delta,
  residual-update norm, and cancellation proxy. Join to frozen H68 `schema_pc1`
  and score correlations/additive route-selection versus whole-model H98.
- **Success criterion:** A useful architecture target is a stable window or
  small set of windows whose features track `schema_pc1` better than diffuse
  whole-depth averaging and are interpretable as carrier-preservation targets.
- **Kill condition:** If signal is fully diffuse or only maturity/log-step
  aligned with no window specificity, use H98 as a measurement/control but do
  not design a depth-window intervention yet.
- **Interpretation boundary:** H102 localizes candidate carrier windows. It is
  not itself an architecture intervention or cost win.
- **Closure:** H102 ran the eight-checkpoint H73 packet on the A100 and found
  a localized PC1 carrier candidate rather than a diffuse whole-depth signal.
  The strongest window is transition `3` (`layer 3->4`)
  `cross_layer_cosine_mean`: additive relative MAE improvement `0.8813` over
  scalar controls, residual correlation `-0.9917`, feature MAE `0.0695`
  versus control MAE `0.5852`. Neighboring early transitions `2`, `4`, and
  `5` also score strongly. PC2 remains weak and late-window only, so the
  architecture path should target H98/PC1 carrier preservation first.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h102_remote_a100_2026_05_11/h102_layer_window_localization_2026_05_11.md`,
  `projects/neural_hunt/workspace/h102_remote_a100_2026_05_11/h102_h73_layer_window_features_2026_05_11.csv`,
  `ztare_workspace/external_runs/neural-hunt-h102-layer-window-localization-20260511T231319Z-68dfa03f`.

## H-NEURAL-HUNT-103 — Doc-balanced replication of H102 layer-window localization

- **Opened:** 2026-05-11
- **Status:** `closed / doc_balanced_localized_pc1_carrier_candidate`
- **Hypothesis:** H102's early-window PC1 localization could be a prompt-packet
  artifact because H73 has low unique-document diversity. If the architecture
  carrier is real enough to guide an intervention, the same window band should
  survive on the H75 doc-balanced packet.
- **Eigenquestion:** Does the H102 layer 3->4 PC1 carrier survive when the
  prompt packet is doc-balanced to `12` unique documents per family/schema
  cell?
- **Discriminating test:** Replay the H75 doc-balanced packet across the same
  eight OLMo2 checkpoints and score per-transition cross-layer cosine,
  residual-update norm, and cancellation proxy against H70 `schema_pc1` /
  `schema_pc2` controls.
- **Success criterion:** Replication requires the same early transition band
  to remain top-ranked for PC1 after doc-balancing, with PC2 not promoted by
  the same features.
- **Kill condition:** If doc-balancing moves the signal to unrelated windows
  or collapses additive improvement, treat H102 as packet-specific and do not
  proceed toward an intervention target.
- **Closure:** H103 replicated the H102 localization on the H75 packet. The
  strongest PC1 window remains transition `3` (`layer 3->4`)
  `cross_layer_cosine_mean`: additive relative improvement `0.8750`, residual
  correlation `-0.9896`, feature MAE `0.0732`, control MAE `0.5852`.
  Transition `2` also remains strong (`0.8036` improvement), and transition
  `3` residual-update norm (`0.7812`) plus transition `2` cancellation
  (`0.7800`) support an update-direction/state-carrier interpretation. PC2
  remains weak and late (`transition 15` residual-update improvement `0.3107`
  with residual correlation only `0.2712`), so it is not the architecture
  target.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h103_remote_a100_2026_05_11/h103_doc_balanced_layer_window_localization_2026_05_11.md`,
  `projects/neural_hunt/workspace/h103_remote_a100_2026_05_11/h103_h75_doc_balanced_layer_window_features_2026_05_11.csv`,
  `ztare_workspace/external_runs/neural-hunt-h103-doc-balanced-window-robustness-20260511T232044Z-6cf89064`.

## H-NEURAL-HUNT-104 — Ten-checkpoint doc-balanced carrier persistence check

- **Opened:** 2026-05-11
- **Status:** `closed / phase_shifted_carrier_candidate`
- **Hypothesis:** The H102/H103 early-window PC1 carrier may still be an
  eight-checkpoint artifact if late training checkpoints change the carrier
  geometry. If it is a durable architecture target, transition `3` and the
  surrounding early band should remain top-ranked when `1600000` and
  `1800000` checkpoints are added.
- **Eigenquestion:** Does the doc-balanced layer 3->4 PC1 carrier persist
  across the full ten-checkpoint H62/H70 measurement surface?
- **Discriminating test:** On the A100, replay the H75 doc-balanced prompt
  packet for checkpoints `0`, `10000`, `50000`, `100000`, `200000`,
  `400000`, `800000`, `1200000`, `1600000`, and `1800000`, then run the
  H102 localization analyzer with the frozen H70 controls.
- **Success criterion:** A durable carrier requires transition `3` or its
  adjacent early band to remain the top PC1 scorer with material additive
  improvement after adding late checkpoints, while PC2 remains non-promoted.
- **Kill condition:** If late checkpoints destroy the localization or move the
  signal to a maturity-only diffuse pattern, do not use H102/H103 as a
  compression/replacement intervention target.
- **Interpretation boundary:** H104 can strengthen or weaken the carrier
  target. It still does not prove a new architecture or cost win; that requires
  a later intervention.
- **Closure:** H104 completed the ten-checkpoint doc-balanced run. Adding the
  late `1600000` and `1800000` checkpoints changes the carrier picture:
  transition `3` remains positive for PC1 (`cross_layer_cosine_mean`
  improvement `0.1109`; `residual_delta_norm_mean` improvement `0.1018`) but
  no longer dominates. The strongest PC1 features shift to the late output-side
  handoff: transition `14` (`layer 14->15`) `cross_layer_cosine_mean`
  improvement `0.4061`, residual correlation `0.8542`, and transition `15`
  residual-update norm improvement `0.3752`, residual correlation `-0.8293`.
  This weakens the single early-handoff story and suggests phase-shifted
  state transmission: the broad PC1 factor may be introduced/organized early
  but carried or distorted through late output-side handoffs at mature
  checkpoints.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h104_remote_a100_2026_05_11/h104_10step_doc_balanced_layer_window_localization_2026_05_11.md`,
  `projects/neural_hunt/workspace/h104_remote_a100_2026_05_11/h104_h75_doc_balanced_10step_layer_window_features_2026_05_11.csv`.

## H-NEURAL-HUNT-105 — Functional weight of early versus late handoffs

- **Opened:** 2026-05-11
- **Status:** `closed / pilot_functional_logprob_damage_detected`
- **Hypothesis:** H104's phase-shifted carrier is architecture-relevant only
  if disrupting the nominated handoffs changes final answer likelihoods. If
  the signal is merely descriptive geometry, bypassing or compressing the
  handoff will not damage continuation log-likelihood or answer margins more
  than comparison layers.
- **Eigenquestion:** Do the early (`3->4`) and late (`14->15`, `15->16`)
  handoffs carry functional weight into final logits, and does the late
  handoff amplify/distort the signal relative to the early handoff?
- **Discriminating test:** On selected H75 doc-balanced checkpoints, run the
  frozen prompt packet with layer-output hooks. For layers `1`, `3`, `14`, and
  `15`, compare baseline continuation log-likelihood and correct-choice
  margin against compressed (`alpha=0.5`) and bypassed (`alpha=0.0`) layer
  updates.
- **Success criterion:** A handoff is functionally weighted if perturbing it
  causes materially larger correct-continuation log-likelihood or margin damage
  than comparison layers, especially on checkpoints where H104 assigns high
  PC1 carrier score.
- **Kill condition:** If all nominated handoffs are no more damaging than
  controls, treat H102-H104 as descriptive learning-trajectory geometry, not a
  successor-architecture intervention target.
- **Interpretation boundary:** H105 is an intervention-lite causal probe. It
  can justify a later compression/replacement experiment, but still does not
  prove a new architecture or cost win.
- **Closure:** H105 ran a bounded five-checkpoint functional probe. The
  answer-margin side is not promotion-grade because the sampled packet's
  baseline multiple-choice accuracy is `0`, so the useful signal is
  correct-continuation log-prob damage only. On that measure, bypassing layer
  `15` is the most damaging average perturbation (`-0.1706` mean correct
  log-prob delta), with mature-checkpoint damage increasing at `1600000`
  (`-0.4015`) and `1800000` (`-0.3325`). Layer `14` bypass is also consistently
  damaging (`-0.1248` mean), while layer `3` bypass is inconsistent
  (`0.0054` mean). This supports the output-side functional-weight suspicion,
  but leaves the middle-span debt/incubator question open.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h105_remote_a100_2026_05_11/h105_handoff_functional_weight_probe_2026_05_11.md`,
  `projects/neural_hunt/workspace/h105_remote_a100_2026_05_11/h105_handoff_functional_weight_probe_2026_05_11_summary.csv`.

## H-NEURAL-HUNT-106 — Middle-span functional weight check

- **Opened:** 2026-05-11
- **Status:** `closed / nonuniform_middle_span_signal`
- **Hypothesis:** If the Transformer middle span is managerial debt, then
  perturbing representative middle layers (`5`, `8`, `11`) should damage
  correct-continuation likelihood less than perturbing the late output-side
  handoffs (`14`, `15`) at mature checkpoints. If the middle span is a quiet
  incubator, middle-layer perturbations should cause comparable or larger
  downstream log-prob damage despite weaker H104 PC1 visibility.
- **Eigenquestion:** Are middle layers functionally hollow relative to the late
  handoff, or do they quietly prepare the state that layer `14->15` converts
  into vocabulary-space evidence?
- **Discriminating test:** Reuse the H105 perturbation probe on mature
  checkpoints `1200000`, `1600000`, and `1800000` with layers `3`, `5`, `8`,
  `11`, `14`, and `15`, measuring correct-continuation log-prob damage under
  bypass (`alpha=0.0`) and compression (`alpha=0.5`).
- **Success criterion:** Debt prior strengthens if middle-layer damage is
  materially lower than output-side damage after normalizing for perturbation
  strength. Incubator prior strengthens if middle layers are similarly or more
  damaging despite weaker visible PC1 localization.
- **Kill condition:** If damage estimates are dominated by packet/baseline
  artifacts or no layer separation appears, treat H105/H106 as pilot-only and
  rebuild the probe on a larger exact-choice evaluator.
- **Interpretation boundary:** H106 samples representative middle layers. It
  does not yet test full span bypass (`5->13`) or replacement architecture.
- **Closure:** H106 ran on mature checkpoints `1200000`, `1600000`, and
  `1800000`. The middle span is not uniformly hollow. Bypassing layer `5` is
  the most damaging tested perturbation by correct-continuation log-prob
  (`-0.3266` mean), slightly more damaging than layer `15` (`-0.2928`) and
  much more than layer `14` (`-0.1412`). Layer `11` is moderately damaging
  (`-0.0736`). Layer `8` is the opposite: bypassing it improves the sampled
  correct-continuation likelihood (`+0.2422` mean). This weakens blanket
  middle-pruning and suggests nonuniform middle roles: layer `5` may be quiet
  incubator / necessary transformation, while layer `8` is a candidate
  debt-like or distortion-prone handoff requiring robustness audit.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h106_remote_a100_2026_05_11/h106_middle_span_functional_weight_probe_2026_05_11.md`,
  `projects/neural_hunt/workspace/h106_remote_a100_2026_05_11/h106_middle_span_functional_weight_probe_2026_05_11_summary.csv`.

## H-NEURAL-HUNT-107 — Robustness check for nonuniform middle-span roles

- **Opened:** 2026-05-11
- **Status:** `closed / nonuniform_middle_roles_replicated`
- **Hypothesis:** H106's split between damaging layer `5` and beneficial
  bypass of layer `8` may be a tiny-packet artifact. If it is real, the same
  qualitative ordering should survive a larger late-checkpoint packet.
- **Eigenquestion:** Does the mature-model functional probe support a
  nonuniform middle-span map: layer `5` as necessary incubator, layer `8` as
  candidate debt/distortion, and layers `14/15` as output-side tax/synthesis?
- **Discriminating test:** Reuse the H105 perturbation probe on checkpoints
  `1600000` and `1800000`, increasing to `6` docs per family/schema cell and
  testing layers `3`, `5`, `8`, `11`, `14`, and `15` under bypass
  (`alpha=0.0`) and compression (`alpha=0.5`).
- **Success criterion:** The nonuniform-middle prior strengthens if layer `5`
  remains materially damaging and layer `8` remains low-damage or
  beneficial, while late layers retain output-side sensitivity.
- **Kill condition:** If the ordering collapses under the larger packet,
  treat H106 as pilot noise and rebuild the causal probe before architecture
  claims.
- **Interpretation boundary:** H107 is still an intervention-lite diagnostic;
  it does not perform span replacement or prove a new architecture.
- **Closure:** H107 completed on A100 for checkpoints `1600000` and `1800000`
  with `6` docs per family/schema cell, layers `3`, `5`, `8`, `11`, `14`,
  `15`, and alphas `0.0`, `0.5`. Bypass damage by mean correct-continuation
  logprob delta was strongest at layer `15` (`-0.8623`), then layer `5`
  (`-0.3574`), then layers `14` (`-0.1762`) and `11` (`-0.1736`). Layer
  `8` bypass remained beneficial on average (`+0.2060`), and layer `3`
  bypass also improved continuation logprob (`+0.1494`). Half-compression
  shrank most damage but retained output-side sensitivity at layer `15`
  (`-0.2712`).
- **Update:** H107 strengthens the adversarial architecture read: the middle is
  not globally hollow. Layer `5` behaves like a necessary incubator/state
  handoff, while layer `8` is the current best debt/distortion candidate.
  The late handoff is materially functional, consistent with output-side
  synthesis or unembedding/formatting tax.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h107_remote_a100_2026_05_11/h107_late_checkpoint_middle_span_robustness_2026_05_11.md`,
  `projects/neural_hunt/workspace/h107_remote_a100_2026_05_11/h107_late_checkpoint_middle_span_robustness_2026_05_11_summary.csv`.

## H-NEURAL-HUNT-108 — Jaccard traversal of transformer-successor evidence basin

- **Opened:** 2026-05-11
- **Status:** `closed / operational_jaccard_useful_bounded`
- **Hypothesis:** The current H104-H107 architecture packet should be
  constrained by prior transformer-successor evidence if the lexical overlap is
  operational rather than generic. In particular, GP116/GP116C residual-state
  economics should surface near the top if the next move is carrier design
  rather than broad delayering.
- **Eigenquestion:** Which prior artifacts share the most operational
  vocabulary with H104-H107, and do they force a different next experiment?
- **Discriminating test:** Build a lexical Jaccard traversal over Neural Hunt,
  GP116 CoT exchange, GP116B transformer-successor, GP116C managerial-debt
  design, and the relevant ledgers. Use the H104-H107 architecture packet as
  the query document and inspect top neighbors plus overlap terms.
- **Success criterion:** GP116/GP116C artifacts with concrete residual-state,
  cancellation, KV, routing, or state-carrier measurements appear among the top
  neighbors and change the next experiment design.
- **Kill condition:** If top neighbors are generic Neural Hunt logs with no
  transformer-successor operational overlap, treat Jaccard as weak navigation
  only and proceed with functional span probes.
- **Interpretation boundary:** Jaccard is a graph traversal aid. It cannot
  prove novelty, mechanism, or architecture superiority.
- **Closure:** H108 first showed that raw Jaccard was too generic. After adding
  an operational vocabulary filter, the traversal surfaced GP116C evidence at
  ranks `5` and `7`, GP116 residual-cancellation reaudit at rank `17`, and the
  GP116 transformer-successor brief at rank `18`. The top Neural Hunt matches
  were H96, H68, and H102/H103, which is coherent with the live residual-state
  carrier path.
- **Update:** Jaccard is useful as a navigation sidecar, not as a decision
  engine. It strengthens the next-experiment constraint: managerial debt must
  be measured as residual-state economics, cancellation/survival, KV/cache or
  routing cost, and downstream retention. It does not support broad layer
  deletion claims.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h108_jaccard_transformer_successor_traversal_2026_05_11.md`,
  `analytics/public/queries/neural_hunt/neural_hunt_basin_graph.md`.

## H-NEURAL-HUNT-109 — Mature full-layer functional debt map

- **Opened:** 2026-05-11
- **Status:** `closed / full_layer_nonuniform_debt_map`
- **Hypothesis:** H107 identified a nonuniform middle-span split, but sparse
  layer sampling may miss adjacent debt/incubator windows. If the managerial
  debt hypothesis has experimental content, a full mature-layer perturbation map
  should show localized windows with low or beneficial bypass damage adjacent
  to windows with high continuation-survival damage.
- **Eigenquestion:** Across mature checkpoints, which individual layers are
  functionally necessary, which are output-side tax/synthesis, and which are
  credible debt/distortion candidates under bypass or compression?
- **Discriminating test:** Run the H105 perturbation probe on checkpoints
  `1600000` and `1800000`, layers `0..15`, alphas `0.0` and `0.5`, and `6`
  docs per family/schema cell using the doc-balanced H75 packet. Score
  correct-continuation logprob delta by layer and checkpoint.
- **Success criterion:** A stable nonuniform map appears: at least one layer or
  adjacent window has materially negative bypass damage, at least one has
  low/beneficial bypass damage, and the ordering is not explained solely by
  final-layer output proximity.
- **Kill condition:** If all layers show monotone depth proximity or unstable
  per-checkpoint signs, do not promote architecture claims; rebuild the probe
  with span interventions or richer downstream metrics.
- **Interpretation boundary:** H109 is still a diagnostic map. A replacement
  architecture requires a follow-on span/carrier intervention with cost and
  retention measurements.
- **Closure:** H109 completed the full mature-layer map on checkpoints
  `1600000` and `1800000`. Bypass damage by mean correct-continuation logprob
  delta was strongest for layer `0` (`-1.3199`), layer `15` (`-0.8623`),
  layer `13` (`-0.3656`), layer `5` (`-0.3574`), layer `1` (`-0.1999`),
  layers `14`/`2`/`11` (`about -0.176`). Bypass was beneficial for layer `8`
  (`+0.2060`), layer `3` (`+0.1494`), layer `9` (`+0.0776`), layer `6`
  (`+0.0433`), and weakly for layer `10` (`+0.0325`).
- **Update:** H109 strengthens the write-side interference read. Layer `8` is
  not merely low-value; on this distribution, its residual write appears to
  degrade correct-continuation likelihood. The live architecture discriminator
  is now read/write asymmetry and carrier split: can the model let the
  layer/window read upstream state while suppressing or routing its writes?
- **Source artifacts:**
  `projects/neural_hunt/workspace/h109_remote_a100_2026_05_11/h109_mature_full_layer_functional_map_2026_05_11.md`,
  `projects/neural_hunt/workspace/h109_remote_a100_2026_05_11/h109_mature_full_layer_functional_map_2026_05_11_summary.csv`.

## H-NEURAL-HUNT-110 — Span-level write-suppression probe for Layer 8 interference

- **Opened:** 2026-05-11
- **Status:** `closed / read_write_asymmetry_supported`
- **Operator inception:** The operator reframed layer `8` as possible
  adversarial residual geometry: a write-side disturbance that may force late
  layers, especially layer `15`, to pay a scrubbing/unembedding tax. The
  counter-argument is distributional: layer `8` may be useful for ICL,
  roleplay, or multi-hop prompts not represented in H75.
- **Hypothesis:** If H109's layer `8` benefit is true write-side interference,
  then suppressing adjacent spans containing `8` should improve or preserve
  correct-continuation logprob on H75, while suppressing known necessary spans
  (`5`, `13`, `14-15`) should damage it.
- **Eigenquestion:** Is the apparent layer `8` debt a local single-layer effect,
  an adjacent `8-10` write-band effect, or an artifact that disappears at span
  level?
- **Discriminating test:** Run the span probe on checkpoints `1600000` and
  `1800000`, spans `5`, `8`, `8-10`, `5-8`, `6-10`, `11-13`, `13`, `14-15`,
  and `5-13`, alphas `0.0` and `0.5`, docs-per-cell `6`.
- **Success criterion:** The write-interference read strengthens if spans
  containing `8` but not the necessary `5`/`13` handoffs remain low-damage or
  beneficial, while `5`, `13`, and `14-15` remain damaging.
- **Kill condition:** If span-level suppression makes all `8`-containing spans
  damaging or unstable, demote the single-layer Layer 8 result to local
  cancellation artifact and move to distributional tests.
- **Interpretation boundary:** H110 still suppresses writes by hook; it does
  not implement a learned gate, parallel carrier, or real cost win.
- **Closure:** H110 completed on A100. Full bypass of `8-10` was damaging
  (`mean -1.1429`), as were `6-10` (`-1.5581`), `11-13` (`-1.3694`),
  `14-15` (`-1.4090`), and `5-13` (`-5.3150`). But half-compression of the
  Layer-8 band was beneficial: `8-10` alpha `0.5` mean `+0.0944`, `6-10`
  alpha `0.5` mean `+0.0892`, while single layer `8` remained beneficial
  under bypass (`+0.2060`) and compression (`+0.0462`).
- **Update:** H110 supports read/write asymmetry over pruning. A hard delete
  of the `8-10` department destroys useful computation, while throttling the
  writes can improve continuation likelihood. The architecture hypothesis
  should be gated residual writes or parallel carriers, not layer removal.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h110_remote_a100_2026_05_11/h110_span_write_suppression_probe_2026_05_11.md`,
  `projects/neural_hunt/workspace/h110_remote_a100_2026_05_11/h110_span_write_suppression_probe_2026_05_11_summary.csv`.

## H-NEURAL-HUNT-111 — Distribution-trap canary for Layer 8 write suppression

- **Opened:** 2026-05-11
- **Status:** `closed / distribution_conditional_layer8`
- **Hypothesis:** Layer `8` may look harmful on H75 because H75 rewards local
  continuation. If layer `8` is useful for global abstraction, ICL, multi-hop,
  or role-constraint tracking, then write suppression should become less
  beneficial or damaging on a small contrast packet.
- **Eigenquestion:** Is Layer `8` a general write-interference layer, or only a
  local-continuation liability?
- **Discriminating test:** Build a tiny synthetic packet with local
  continuation, ICL-rule, multi-hop relation, and role-constraint rows for
  checkpoints `1600000` and `1800000`. Reuse the H110 span probe on spans
  `8`, `8-10`, `5`, `13`, and `14-15`.
- **Success criterion:** The distribution-trap objection strengthens if
  Layer-8 suppression helps local-continuation rows but weakens or hurts the
  ICL/multi-hop/constraint rows.
- **Kill condition:** If Layer-8 suppression helps across all slices, the
  write-interference prior strengthens, but the result remains synthetic and
  must be repeated on real held-out tasks.
- **Interpretation boundary:** H111 is a cheap canary only. It cannot prove
  distribution-general architecture value.
- **Closure:** H111 built and ran a tiny synthetic contrast packet over local
  continuation, ICL-rule, multi-hop, and role-constraint rows. Overall, single
  layer `8` bypass was near-neutral/slightly negative (`-0.0607`) while
  `8` half-compression was slightly positive (`+0.0425`). Full `8-10`
  bypass was damaging (`-2.2360`), and `8-10` half-compression was mildly
  negative (`-0.2426`).
- **Slice update:** Layer `8` suppression helped local continuation
  (`+1.0078` bypass, `+0.5469` compression) but hurt synthetic ICL
  (`-1.2227` bypass, `-0.4238` compression). Multi-hop was mild-positive
  for layer `8` (`+0.1094` bypass), and role-constraint was mixed/slightly
  negative. This validates the distribution-trap objection.
- **Update:** The layer `8` claim is now distribution-conditional. On H75
  continuation-like rows, Layer `8` writes look interference-prone; on
  ICL-like rows, they can be necessary. The successor architecture should
  route or gate writes by prompt/state complexity rather than globally
  suppressing Layer `8`.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h111_layer8_distribution_trap_packet_2026_05_11.jsonl`,
  `projects/neural_hunt/workspace/h111_remote_a100_2026_05_12/h111_distribution_trap_span_probe_2026_05_11_summary.csv`.

## H-NEURAL-HUNT-112 — Gated residual write successor packet

- **Opened:** 2026-05-12
- **Status:** `closed / local_successor_packet_ready`
- **Hypothesis:** H109-H111 support a successor mechanism more specific than
  managerial debt: separate layer read access from write access, and gate or
  route middle-layer writes by task/state complexity.
- **Eigenquestion:** What architecture intervention is actually implied by the
  Neural Hunt evidence after the anti-pruning and distribution-trap controls?
- **Discriminating synthesis:** Build an intervention packet that names the
  target debt window, replacement carrier, mechanistic prediction, cheap
  falsifier, rival explanation, and next GP116B row.
- **Success criterion:** The packet blocks broad delayering claims and yields a
  concrete next paid validation: real-task local continuation versus
  ICL/multi-hop/constraint slices under gated write suppression.
- **Kill condition:** If no concrete pass/fail test or cost/retention metric can
  be named, the architecture lane remains metaphor-only.
- **Closure:** H112 produced the gated residual write successor packet. The
  proposed mechanism is conditional residual write gating / split carriers:
  middle layers read the shared residual stream, but their writes are throttled
  or routed into local/global carriers before late merge. The packet explicitly
  rejects broad middle pruning and global Layer-8 suppression.
- **Post-close caveat:** The H105/H110 scorer was found to rely on row `label`
  for the correct choice, while some OLMES rows store `label` as the gold
  answer repeated on every choice. The scripts now match `continuation` to
  `choices[answer]`. H109/H110 H75-based quantitative rows require corrected
  replay before promotion; H111's synthetic packet was internally consistent.
- **Source artifact:**
  `projects/neural_hunt/workspace/h112_gated_residual_write_successor_packet_2026_05_12.md`.

## H-NEURAL-HUNT-114 — Corrected replay and available real-task packet

- **Opened:** 2026-05-12
- **Status:** `closed / replay_plan_and_partial_real_packet_ready`
- **Hypothesis:** Before any architecture promotion, H109/H110 must be replayed
  with the corrected gold-continuation resolver and tested on available real
  task slices beyond the H75 MMLU/MedMCQA packet.
- **Eigenquestion:** What is the cheapest valid next GPU use after the scorer
  fix?
- **Discriminating preparation:** Build a corrected replay plan and a packet of
  already-downloaded real-task rows with labels normalized to choice index.
- **Success criterion:** The packet is executable by the patched H110 span probe
  and covers at least local continuation / boolean-reading real-task slices.
- **Kill condition:** If available rows do not resolve choices unambiguously,
  do not run them.
- **Closure:** H114 created the replay plan and a `160`-row available real-task
  packet from late-checkpoint ARC Easy, OpenBookQA, and BoolQ requests. It
  covers local science/commonsense continuation and boolean context reading.
  It does not cover a clean real ICL or multi-hop split; that remains a later
  acquisition requirement.
- **Source artifacts:**
  `projects/neural_hunt/workspace/h114_corrected_replay_plan_2026_05_12.md`,
  `projects/neural_hunt/workspace/h114_available_real_task_distribution_packet_2026_05_12.jsonl`,
  `projects/neural_hunt/workspace/run_h114_make_available_real_task_packet.py`.

## H-NEURAL-HUNT-118 — Current status split: PC1 science vs architecture hypothesis

- **Opened:** 2026-05-12
- **Status:** `closed / current_state_synthesis`
- **Hypothesis:** The Neural Hunt state should be split into two confidence
  tracks: PC1 learning-mechanics science and next-architecture speculation.
- **Eigenquestion:** Which claims are evidence-backed now, and which are only
  candidate architecture paths pending corrected replay?
- **Discriminating synthesis:** Summarize H98-H104 for PC1 and H109-H114 for
  architecture, explicitly incorporating the H113 scorer caveat.
- **Closure:** H118 records that PC1 learning-mechanics progress is stronger
  than the architecture claim. PC1 has replicated residual-geometry carriers
  and a phase-shifted layer map. The architecture lane has a serious candidate
  mechanism, conditional residual write gating / split carriers, but H109/H110
  must be replayed with the corrected scorer before promotion.
- **Source artifact:**
  `projects/neural_hunt/workspace/h118_pc1_learning_mechanics_and_architecture_status_2026_05_12.md`.

## H-NEURAL-HUNT-119 — PC1 learning-mechanics research packet

- **Opened:** 2026-05-12
- **Status:** `closed / pc1_science_packet_ready`
- **Hypothesis:** PC1 should be treated as Neural Hunt's current strongest
  learning-mechanics object, separate from the unpromoted architecture lane.
- **Eigenquestion:** What exactly is the PC1 scientific claim, what falsifies
  it, and what experiments advance it without architecture overreach?
- **Discriminating synthesis:** Build a PC1 packet from H68/H98/H102/H103/H104
  and the H113 caveat, separating descriptive residual-geometry carrier claims
  from causal/intervention claims.
- **Closure:** H119 defines schema-state PC1 as a candidate macroscopic
  training-dynamics state variable with internal residual-geometry carriers and
  phase-shifted transmission. It lists falsifiers: scalar maturity, prompt
  format, model family, intervention causality, and scorer replay. It names
  H115/H116/H117/H120/H121 as the next PC1 gates.
- **Source artifact:**
  `projects/neural_hunt/workspace/h119_pc1_learning_mechanics_research_packet_2026_05_12.md`.

## H-NEURAL-HUNT-120 — Parallel PC1 and architecture track synthesis

- **Opened:** 2026-05-12
- **Status:** `closed / parallel_track_status_ready`
- **Hypothesis:** Neural Hunt should advance PC1 science and architecture
  design in parallel but with separate confidence levels and gates.
- **Eigenquestion:** What can be claimed now on PC1, what can be claimed now on
  next Transformer architecture, and what exact validations separate them?
- **Discriminating synthesis:** Combine the local PC1 packet with the parallel
  architecture-agent report, preserving the H113 scorer caveat and GP116
  residual-state economics constraint.
- **Closure:** H120 records PC1 as the stronger science object and gated
  residual writes / split carriers as a live but unpromoted architecture
  candidate. It lists the next GPU sequence H115/H116/H117, the missing real
  ICL/multi-hop packet, and the scrubbing-tax check.
- **Source artifact:**
  `projects/neural_hunt/workspace/h120_parallel_track_status_and_next_gates_2026_05_12.md`.

## H-GP225-GNN-14.9 — Mixed-action local-obligation gate before 40-row expansion

- **Opened:** 2026-05-11
- **Status:** `closed / mixed_action_gate_passed_with_alternate_accepts`
- **Hypothesis:** The current GP-225 20-row counterfactual pass is still
  under-actioned because every gold row uses `apply_tac`; before expanding to
  40 rows, the harness should prove it can represent and route non-apply local
  repairs (`exact_tac`, `convert_using1`, `rw_fwd`, `rw_rev`, `simp_only`) with
  target-aware witnesses.
- **Eigenquestion:** Does the repair harness handle action selection, or has
  GP-225 only learned an apply-shaped candidate ordering problem?
- **Discriminating test:** Build a small local-obligation packet with at least
  one gold row for each supported action family. Probe every candidate-action
  pair through Lean, build the gold before/after digest from the declared gold
  action, and compare a generic fixed action order against a target-kind/action
  router under budgets `3`, `5`, and `10`.
- **Success criterion:** Pass requires Lean returncode `0`, zero Sort/Type
  closure accepts, all six gold actions accepted, target-kind route success
  `>= 6/6` at budget `10`, and no non-gold/wrong-action accepted progress
  before the gold repair.
- **Kill condition:** If mixed actions cannot be represented cleanly, or if
  generic fixed action order matches the action router on this packet, do not
  expand GP-225 to 40 rows until the action/witness contract is repaired.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / action-monoculture gate.
- **Closure:** v14.9 ran `324` Lean candidate-action probes over a six-row
  synthetic local-obligation packet covering `exact_tac`, `apply_tac`,
  `convert_using1`, `rw_fwd`, `rw_rev`, and `simp_only`. Lean returncode `0`;
  gold accepts `6/6`; Sort/Type closure accepts `0`. The mixed-action router
  reached success@3/5/10 `6/6` with mean failed probes `0.0` and false-before
  rows `0`, while generic fixed action order reached only success@10 `1/6`
  with mean failed probes `26.5` and one false-before row. Caveat: the run
  observed `9` alternate accepted candidate/action paths after the gold route,
  mostly equivalent exact/apply/convert closures or inverse rewrite aliases;
  this does not block 40-row expansion but argues that the 40-row acceptance
  contract should record allowed alternate actions explicitly.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v149_mixed_action_gate.py`,
  `analytics/public/leanmill/results/v149_mixed_action_gate.json`,
  `analytics/public/leanmill/results/v149_mixed_action_gate.md`.

## H-GP225-GNN-15.0 — Forty-row target-unit feasibility packet

- **Opened:** 2026-05-11
- **Status:** `closed / forty_row_target_units_ready`
- **Hypothesis:** GP-225 can expand from the current 20-row repaired local-
  obligation packet to a 40-row packet with better domain balance and real
  mixed-action candidates without reintroducing Sort/Type closure artifacts or
  declaration-target leakage.
- **Eigenquestion:** Is the next scale-up mechanically valid as a Lean target-
  unit benchmark, or would the 40-row policy result be uninterpretable before
  it starts?
- **Discriminating test:** Add 20 repository-backed target rows from non-
  harmonic candidate families (SQ3/Lp translation, SQ3 convolution/duality, NS
  LSC/energy/budget/recurrence, iterated log/order), preserve the existing 20
  rows, emit Lean probes for each declared gold candidate/action, and record
  before/after goal heads and target kinds.
- **Success criterion:** Lean returncode `0`, at least `40` rows emitted,
  all declared gold candidate/action witnesses accepted under the target-aware
  contract or explicitly marked with allowed alternate actions, and Sort/Type
  closure accepts `0`.
- **Kill condition:** If many new rows cannot be made into executable local
  obligations, if the row mix remains harmonic-heavy, or if Sort/Type closures
  return, do not run v15.1 policy scoring; repair the target packet first.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / 40-row benchmark
  construction.
- **Closure:** v15.0 built a 40-row packet: the original 20 rows plus 20
  repository-backed candidate-type local goals from SQ3/Lp translation, SQ3
  convolution/duality, NS LSC/energy/budget/recurrence, and iterated-log
  surfaces. Final run: `240` Lean probes, Lean returncode `0`, gold accepts
  `40/40`, Sort/Type closures `0`. Domain counts: `13` harmonic-analysis,
  `5` navier_stokes, `4` sq3_lp_translation, `4` ns_lsc, `3` ns_budget, `2`
  sq3_convolution, `2` ns_energy, `2` ns_recurrence, `2` iterated_log, `1`
  sq3_duality, `1` measure_analysis, `1` filter_analysis. Caveat: gold actions
  remain apply-heavy (`apply_tac=36`, `rw_fwd=3`, `exact_tac=1`) and alternate
  accepted actions appear on `36/40` rows, so v15.1 must report action mix and
  allowed alternates explicitly.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v150_forty_row_target_unit_packet.py`,
  `analytics/public/leanmill/results/v150_forty_row_target_unit_packet.json`,
  `analytics/public/leanmill/results/v150_forty_row_target_unit_packet.md`.

## H-GP225-GNN-15.1 — Forty-row branch-factor policy scoring

- **Opened:** 2026-05-11
- **Status:** `closed / forty_row_policy_gate_ran`
- **Hypothesis:** On the 40-row target-unit packet, the deterministic GP-225
  interface/action router should still reduce failed Lean candidate-action
  probes versus generic fixed action order and cheap domain/head baselines, but
  the gap may shrink once the candidate pool contains the new repository-backed
  rows.
- **Eigenquestion:** Does GP-225 still provide branch-factor value at 40 rows,
  or did the 20-row result depend on a small, structurally separable pool?
- **Discriminating test:** Probe every target row against the shared 40-
  candidate pool over the supported action set, build strict gold/allowed-
  alternate digests, and compare generic fixed order, domain/head, full-
  interface, target-kind action routing, and exhaustive bounded controls under
  budgets `3`, `5`, `10`, and `25`.
- **Success criterion:** Continue the CPU-router track if full-interface or
  target-kind routing beats generic fixed action order and domain/head on
  success@10 and mean failed probes, with Sort/Type closure accepts `0` and
  false-before-correct rows reported rather than hidden.
- **Kill condition:** If domain/head or generic fixed action order matches the
  interface/action router on 40 rows, keep GP-225 as a narrow advisory harness
  and do not train. If false-before-correct rows dominate, repair the witness
  contract before public baselines.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / 40-row policy gate.
- **Closure:** v15.1 split the 40-row/40-candidate/6-action matrix into eight
  Lean drivers to avoid Lean code-generator recursion depth. Final run:
  `9600` candidate-action probes, `1640` signatures, Lean returncode `0`,
  Sort/Type closure count `0`. Results: generic fixed success@10 `2/40`,
  mean failed `117.95`, false rows `1`; domain/head success@10 `30/40`,
  mean failed `8.0`, false rows `0`; full-interface success@10 `36/40`,
  success@25 `40/40`, mean failed `3.05`, false rows `0`; target-kind router
  success@10 `30/40`, mean failed `7.05`, false rows `0`. The four
  full-interface budget-10 misses are two harmonic rows (`v89`,
  `v135_mulchar_norm`) and two NS LSC rows (`v150_cumulative_lsc_apply`,
  `v150_cumulative_struct_apply`).
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v151_forty_row_branch_factor_policy_gate.py`,
  `analytics/public/leanmill/results/v151_forty_row_branch_factor_policy_gate.json`,
  `analytics/public/leanmill/results/v151_forty_row_branch_factor_policy_gate.md`.

## H-GP225-GNN-15.2 — BM25 signature baseline on the 40-row packet

- **Opened:** 2026-05-11
- **Status:** `closed / bm25_matches_full_interface`
- **Hypothesis:** A stronger lexical retrieval baseline over target and
  candidate signatures may close much of the apparent full-interface advantage
  on the 40-row packet.
- **Eigenquestion:** Is the v15.1 full-interface win actually a typed repair
  signal, or can ordinary BM25-style signature retrieval match it?
- **Discriminating test:** Reuse v15.1 signatures and probes, compute BM25
  scores from target/candidate conclusion tokens, and evaluate BM25 candidate
  ordering with generic and target-kind action ordering under the same budgets.
- **Success criterion:** Full-interface remains the CPU champion only if BM25
  does not match or exceed success@10 and mean failed probes.
- **Kill condition:** If BM25 matches full-interface on success@10 and mean
  failed probes, treat the current router as lexical retrieval over signatures
  and block any typed-router or GNN novelty claim until harder decoys/public
  sources restore separation.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / cheap baseline hardening.
- **Closure:** v15.2 reused the v15.1 signatures/probes and evaluated BM25
  over target/candidate conclusion tokens. BM25 with generic actions exactly
  matched full-interface: success@10 `36/40`, success@25 `40/40`, mean failed
  `3.05`. BM25 with target-kind actions kept success@10 `36/40` and
  success@25 `40/40` while improving mean failed probes to `2.1`. This meets
  the kill condition for any typed-router or GNN novelty claim from the current
  packet.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v152_bm25_signature_baseline.py`,
  `analytics/public/leanmill/results/v152_bm25_signature_baseline.json`,
  `analytics/public/leanmill/results/v152_bm25_signature_baseline.md`.

## H-GP225-GNN-15.3 — Forty-row signature redaction audit

- **Opened:** 2026-05-11
- **Status:** `closed / redaction_partial_drop_shape_separable`
- **Hypothesis:** If the v15.1/v15.2 signal is mostly lexical signature
  retrieval, then namespace/domain/leaf redaction should sharply reduce the
  full-interface/BM25 advantage over domain/head.
- **Eigenquestion:** Does the 40-row router survive name redaction, or is it
  still relying on surface declaration vocabulary?
- **Discriminating test:** Reuse v15.1 signatures/probes and evaluate
  interface/BM25 candidate ordering under `full_leaf`, `no_domain_stem`, and
  `abstract_shape` token regimes with the same target-kind action ordering.
- **Success criterion:** Typed-router evidence would require redacted regimes
  to remain materially better than domain/head on success@10 and mean failed
  probes.
- **Kill condition:** If no-domain-stem falls to domain/head, treat current
  evidence as useful lexical/interface routing and require harder generated
  decoys before any novelty claim.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / overfit audit.
- **Closure:** v15.3 reused the v15.1 probe matrix and evaluated target-kind
  action routing under signature token regimes. Full-leaf: success@10 `36/40`,
  success@25 `40/40`, mean failed `2.1`. No-domain-stem: success@10 `31/40`,
  success@25 `37/40`, mean failed `5.7`; this is degraded but still slightly
  above domain/head's success@10 `30/40`, mean failed `8.0`. Abstract-shape:
  success@10 `38/40`, success@25 `40/40`, mean failed `1.2`, which remains
  suspiciously strong and indicates fixture separability by coarse structure.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v153_forty_row_signature_redaction_audit.py`,
  `analytics/public/leanmill/results/v153_forty_row_signature_redaction_audit.json`,
  `analytics/public/leanmill/results/v153_forty_row_signature_redaction_audit.md`.

## H-GP225-GNN-15.4 — Same-shape counterfactual decoys for 40-row packet

- **Opened:** 2026-05-11
- **Status:** `closed / same_shape_decoys_rejected_bm25_tempted`
- **Hypothesis:** The 40-row packet remains too structurally separable; adding
  generated same-shape wrong candidates for representative new rows should
  expose whether target-aware Lean witnesses reject plausible BM25/interface
  decoys.
- **Eigenquestion:** Can the harness reject same-shape wrong repairs that
  lexical/signature scoring is tempted to try?
- **Discriminating test:** Add generated wrong candidates for representative
  SQ3, NS recurrence/budget/energy, and iterated-log rows with similar heads,
  arities, and tokens but wrong carrier/side/object/bound/direction; probe gold
  and wrong candidates with the supported actions; compare BM25 gold-over-decoy
  and wrong-candidate false accepts under strict after-state digests.
- **Success criterion:** Target-aware witnesses must produce zero wrong-candidate
  accepted repairs, even when BM25 ranks or ties the decoy near gold.
- **Kill condition:** Any wrong candidate accepted under the gold after-state
  digest means v15.1/v15.2 policy scoring is not safe enough for advisory use
  on that action family.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / generated decoy hardening.
- **Closure:** v15.4 generated same-shape wrong candidates for 8 representative
  new 40-row packet rows across SQ3 translation, NS LSC/energy/budget/
  recurrence, and iterated-log targets. The clean gold-action-only witness run
  produced Lean returncode `0`, `16` candidate-action probes, and wrong accepted
  repairs `0/8`. BM25 tied or ranked the wrong decoy at least as high as gold
  in `5/8` rows, so the gate is informative: lexical signature scoring is
  tempted by these same-shape decoys, while the target-aware Lean witness rejects
  them. This is not yet a GNN/training promotion because it is a representative
  decoy gate, not a full 40-row adversarial policy rerun.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v154_same_shape_counterfactual_decoys.py`,
  `analytics/public/leanmill/results/v154_same_shape_counterfactual_decoys.json`,
  `analytics/public/leanmill/results/v154_same_shape_counterfactual_decoys.md`.

## H-GP225-GNN-15.5 — Same-shape decoy policy-delta compression gate

- **Opened:** 2026-05-11
- **Status:** `closed / decoys_do_not_move_policy_enough`
- **Hypothesis:** The v15.4 decoys are informative enough to affect policy
  ordering: lexical/BM25 or full-interface scorers should waste probe budget on
  same-shape wrong candidates more often than target-aware witness/slot-action
  routing.
- **Eigenquestion:** Do same-shape decoys change branch-factor behavior, or are
  they only an isolated witness-filter sanity check?
- **Discriminating test:** Reuse v15.1 40-row signatures/probes and v15.4
  generated decoy signatures/probes. Inject the v15.4 wrong candidates into the
  8 representative rows, evaluate BM25/full-interface/domain-head/target-kind
  ordering under budgets `3/5/10/25`, and report pairwise gold-over-wrong,
  wrong-before-gold, false-before-gold, and added failed probes.
- **Success criterion:** A stronger typed-router path requires lexical/BM25
  policies to incur measurable wrong-before-gold or failed-probe penalties while
  target-aware accepted-repair selection keeps wrong accepts at `0`.
- **Kill condition:** If decoy injection does not change policy behavior, v15.4
  is only a witness-filter sanity check; do not expand or train from it.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / compressed adversarial
  policy gate.
- **Closure:** v15.5 reused v15.1 and v15.4 artifacts without a Lean rerun.
  BM25 still tied or ranked wrong at least as high as gold in `5/8` v15.4 rows,
  but injecting those decoys into policy ordering barely moved branch-factor
  metrics. Stable-order BM25/full-interface produced `0` wrong-before-gold rows.
  Adversarial tie-breaking produced only `1` wrong-before-gold row and `6` added
  wrong-decoy actions, with BM25 target-kind mean failed probes moving from
  `2.1` to `2.25` and success@10 staying `36/40`. False-before-gold remained
  `0`. Therefore v15.4 is a useful witness-filter sanity check, not yet a
  policy-changing hard-decoy result.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v155_same_shape_decoy_policy_delta.py`,
  `analytics/public/leanmill/results/v155_same_shape_decoy_policy_delta.json`,
  `analytics/public/leanmill/results/v155_same_shape_decoy_policy_delta.md`.

## H-GP225-GNN-15.6 — Forced-front policy-hard false-premise decoys

- **Opened:** 2026-05-11
- **Status:** `closed / forced_front_hard_negatives_cleanly_recovered`
- **Hypothesis:** If the current blocker is lack of policy-hard negatives, then
  false-premise decoys with the same final conclusion as gold should force
  BM25/interface ambiguity while Lean target-aware witnesses reject them by
  exposing the wrong `False` side condition.
- **Eigenquestion:** Can we rapidly manufacture hard-negative candidate-action
  labels where lexical/interface order is maximally tempted but target-aware
  witness filtering preserves correctness?
- **Discriminating test:** Generate false-premise decoys for the same 8 v15.4
  representative rows. Put each wrong decoy ahead of gold by construction,
  probe the gold action plus action-family fallback, and compare forced-front
  lexical policy against a witness-filtered acceptance policy.
- **Success criterion:** `0` false accepted wrong repairs, forced-front policy
  incurs measurable wrong-before-gold probes on all 8 rows, and every wrong
  failure exposes a target-aware non-gold side condition or failed action rather
  than a Sort/Type closure.
- **Kill condition:** Any false-premise decoy accepted as the gold repair means
  target-aware witness filtering is unsafe for endpoint-like hard negatives.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / hard-negative label
  generation for possible later probe-priority learning.
- **Closure:** v15.6 generated false-premise hard negatives for the same 8
  representative rows as v15.4. Each wrong candidate had the same final
  conclusion shape as gold plus an explicit `False` premise, making BM25
  wrong >= gold on `8/8` rows. The forced-front policy placed wrong before gold
  on all rows. Lean returned code `0`, Sort/Type closures were `0`, wrong
  accepted repairs were `0`, and FDCR was `8/8` at budgets `3`, `5`, `10`, and
  `25` because gold was recovered after one forced wrong probe. Wrong exposures
  produced explicit non-gold side conditions such as `False`, not silent
  endpoint closure.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v156_forced_front_false_premise_decoys.py`,
  `analytics/public/leanmill/results/v156_forced_front_false_premise_decoys.json`,
  `analytics/public/leanmill/results/v156_forced_front_false_premise_decoys.md`.

## H-GP225-GNN-15.7 — All-action hard-negative label pack

- **Opened:** 2026-05-11
- **Status:** `closed / all_action_false_premise_labels_clean`
- **Hypothesis:** The v15.6 false-premise decoys become more valuable as
  pre-GNN data if every supported action is probed, because the useful training
  signal is the full candidate-action failure signature, not only gold-action
  rejection.
- **Eigenquestion:** Do policy-hard decoys remain safely rejected across
  `exact/apply/convert/rw/simp`, and what negative action signatures do they
  expose?
- **Discriminating test:** Reuse the v15.6 false-premise decoys, but probe all
  supported actions for gold and wrong candidates. Evaluate wrong accepted
  repairs under the gold digest, Forced-Decoy Clean Recovery under a forced
  all-actions-before-gold policy, Sort/Type closures, and action-level rejection
  taxonomy.
- **Success criterion:** wrong accepted repairs `0`, Sort/Type closures `0`,
  FDCR@10 `8/8`, and a complete all-actions negative label matrix for the 8
  policy-hard rows.
- **Kill condition:** Any wrong action accepted as gold under the strict digest
  means the hard-negative generator can create unsafe false progress and must be
  repaired before broader label generation.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / candidate-action label
  pack.
- **Closure:** v15.7 probed all supported actions for the v15.6 false-premise
  hard negatives: `8` rows x `2` candidates x `6` actions = `96` Lean probes.
  Lean returncode was `0`; wrong action probes were `48`; wrong accepted
  repairs `0`; Sort/Type closures `0`. Forced all-actions-before-gold FDCR was
  `0/8` at budgets `3` and `5`, and `8/8` at budgets `10` and `25`, because
  the forced policy spends six wrong actions before trying gold. Action
  taxonomy: `exact_tac` failed `8/8`, `apply_tac` exposed `False` `8/8`,
  `convert_using1` produced non-gold side goals `8/8`, `rw_fwd/rw_rev` exposed
  `False` on `2/8` each and failed otherwise, and `simp_only` failed `8/8`.
  This is useful label data, not a training launch gate, because `False`
  premises are synthetic.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v157_all_action_hard_negative_label_pack.py`,
  `analytics/public/leanmill/results/v157_all_action_hard_negative_label_pack.json`,
  `analytics/public/leanmill/results/v157_all_action_hard_negative_label_pack.md`.

## H-GP225-GNN-15.8 — Plausible missing-obligation hard-negative decoys

- **Opened:** 2026-05-11
- **Status:** `closed / plausible_missing_obligations_cleanly_rejected`
- **Hypothesis:** If the hard-negative lane is not merely a `False`-premise
  tautology, then same-conclusion decoys with plausible missing side conditions
  should remain safely rejected across all actions while exposing typed
  obligations rather than `False`.
- **Eigenquestion:** Can target-aware witnesses reject policy-hard decoys whose
  failure mode looks like real proof repair: carrier/index equality, budget
  identity, horizon strength, monotonicity, or missing domain hypothesis?
- **Discriminating test:** Generate plausible same-conclusion decoys for the 8
  v15.6/v15.7 representative rows. Probe all supported actions for gold and
  wrong candidates. Measure wrong accepted repairs, Sort/Type closures,
  non-False side-goal exposure, BM25 wrong >= gold, and FDCR under forced all
  wrong actions before gold.
- **Success criterion:** wrong accepted repairs `0`, Sort/Type closures `0`,
  BM25 wrong >= gold on at least `6/8`, no wrong rejection depends on `False`,
  and FDCR@10 `8/8`.
- **Kill condition:** If plausible missing-obligation decoys are accepted as
  gold, or if BM25 no longer finds them hard, the v15.6/v15.7 label story is
  too synthetic for GNN promotion.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / plausible hard-negative
  supervision.
- **Closure:** v15.8 replaced `False` premises with plausible missing
  obligations: zero-shift/carrier equality, same-sequence equality, zero-time
  equality, budget identity, zero-loss side condition, weaker horizon,
  nonnegative input, and monotonicity. The all-action run produced `96` probes,
  `48` wrong action probes, Lean returncode `0`, wrong accepted repairs `0`,
  Sort/Type closures `0`, and `False` side heads `0`. BM25 wrong >= gold on
  `8/8`; forced all-actions-before-gold FDCR was `0/8` at budgets `3` and `5`,
  `8/8` at budgets `10` and `25`. Wrong action taxonomy used real side goals:
  `exact_tac` failed, `apply_tac`/`convert_using1` produced non-gold side
  obligations, rewrites sometimes produced non-gold side obligations, and
  `simp_only` failed.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v158_plausible_missing_obligation_decoys.py`,
  `analytics/public/leanmill/results/v158_plausible_missing_obligation_decoys.json`,
  `analytics/public/leanmill/results/v158_plausible_missing_obligation_decoys.md`.

## H-GP225-GNN-15.9 — Cheap side-condition separability audit

- **Opened:** 2026-05-11
- **Status:** `closed / extra_premise_rule_almost_enough_semantic_residual_found`
- **Hypothesis:** The v15.8 plausible hard negatives may still be cheaply
  separable because they add explicit extra Prop premises while preserving the
  same final conclusion.
- **Eigenquestion:** Do we need learned graph structure, or can a deterministic
  pre-probe side-condition/arity audit demote the v15.8 wrong candidates?
- **Discriminating test:** Use Lean to extract telescope length, Prop-premise
  count, Prop-premise heads, and final conclusion head for gold and plausible
  wrong candidates. Evaluate whether a cheap rule `(same conclusion head and
  wrong has more Prop premises / extra premise heads)` separates all wrongs.
- **Success criterion:** If the cheap rule separates `8/8` wrong candidates,
  GNN remains blocked and the rule should be added to the CPU router before
  training.
- **Kill condition:** If cheap telescope/Prop-premise metrics do not separate
  plausible wrongs, then the next step can justify richer slot-binding features
  or a small learned pre-probe model.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / cheap-rule inversion
  before training.
- **Closure:** v15.9 used Lean-side telescope extraction to measure binder
  count, Prop-premise count, Prop-premise heads, and final body head for gold
  vs v15.8 plausible wrong candidates. Lean returned code `0`. The cheap
  rule "same conclusion head and wrong has more binders/Prop premises" separated
  `7/8` rows. The lone residual was `v150_contractive_apply`: the wrong
  candidate has the same binder count (`4`) and Prop-premise count (`1`) as
  gold, but swaps the side-condition head from strict horizon/`lt` to weak
  horizon/`le` while preserving the final conclusion head. This is a useful
  residual because it is not solved by arity alone.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v159_side_condition_separability_audit.py`,
  `analytics/public/leanmill/results/v159_side_condition_separability_audit.json`,
  `analytics/public/leanmill/results/v159_side_condition_separability_audit.md`.

## H-GP225-GNN-16.0 — Same-arity semantic side-condition substitution decoys

- **Opened:** 2026-05-11
- **Status:** `closed / same_arity_semantic_decoys_clean`
- **Hypothesis:** The real pre-GNN gap is not extra-premise detection. If we
  replace gold side conditions with plausible but wrong same-arity side
  conditions while preserving the final conclusion, cheap arity rules should
  fail and only side-condition semantics / slot binding can reject the decoy.
- **Eigenquestion:** Can the harness distinguish same-conclusion, same-arity
  candidates whose only difference is the meaning of the required side
  condition?
- **Discriminating test:** Generate a focused same-arity semantic-substitution
  decoy packet for rows where the gold theorem has at least one replaceable
  side condition. Probe all supported actions and run the cheap separability
  audit. Count wrong accepts, Sort/Type closures, BM25 hardness, arity-rule
  failures, and side-condition-head separation.
- **Success criterion:** wrong accepted repairs `0`, Sort/Type closures `0`,
  BM25 wrong >= gold on all tested rows, extra-premise/arity rule fails on at
  least `2` rows, and side-condition-head/slot comparison identifies the wrong
  premise.
- **Kill condition:** If every same-arity decoy is still trivial to separate by
  nonsemantic features, the pre-GNN lane remains engineering/taste rather than
  proof-obstruction structure.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / close the synthetic
  benchmark gap.
- **Closure:** v16.0 generated 4 same-arity semantic side-condition
  substitutions: AE-strong vs strong measurability, L2 hypotheses vs sequence
  equality, event certificate vs budget identity, and strict horizon vs weak
  horizon. The all-action run produced `48` probes and `24` wrong action probes,
  Lean returncode `0`, wrong accepted repairs `0`, Sort/Type closures `0`,
  BM25 wrong >= gold `4/4`, and forced all-actions-before-gold FDCR `0/4` at
  budgets `3` and `5`, `4/4` at budgets `10` and `25`.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v160_same_arity_semantic_side_condition_decoys.py`,
  `analytics/public/leanmill/results/v160_same_arity_semantic_side_condition_decoys.json`,
  `analytics/public/leanmill/results/v160_same_arity_semantic_side_condition_decoys.md`.

## H-GP225-GNN-16.1 — Same-arity side-condition cheap-rule audit

- **Opened:** 2026-05-11
- **Status:** `closed / premise_head_rule_leaves_one_residual`
- **Hypothesis:** Same-arity v16.0 decoys defeat extra-premise counting, but
  cheap premise-head comparison may still separate them without learned graph
  structure.
- **Eigenquestion:** Is the residual now side-condition semantics, or still a
  simple symbolic-head mismatch?
- **Discriminating test:** Reuse v16.0 declarations and extract binder count,
  Prop-premise count, Prop-premise heads, and final body head for gold vs wrong.
  Evaluate extra-premise rule and premise-head rule.
- **Success criterion:** If premise-head comparison separates all v16.0
  decoys, promote the CPU rule and keep GNN blocked.
- **Kill condition:** If at least one decoy survives both extra-premise and
  premise-head rules, build deeper premise-body/slot comparison.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / cheap-rule inversion.
- **Closure:** v16.1 confirmed the same-arity residual. Extra-premise rule
  separated `0/4`. Premise-head comparison separated `3/4`. The remaining row
  is `v150_translate_norm_rw`: gold and wrong both expose premise heads
  `BorelSpace`, `MeasurableAdd`, `Measure.IsAddLeftInvariant`, and `Exists`,
  but the semantic premise differs (`AEStronglyMeasurable f μ` vs
  `StronglyMeasurable f`). This is the first residual not killed by arity or
  premise-head matching.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v161_same_arity_side_condition_audit.py`,
  `analytics/public/leanmill/results/v161_same_arity_side_condition_audit.json`,
  `analytics/public/leanmill/results/v161_same_arity_side_condition_audit.md`.

## H-GP225-GNN-16.2 — Premise-body slot separability audit

- **Opened:** 2026-05-11
- **Status:** `closed / premise_body_rule_separates_all`
- **Hypothesis:** The v16.1 residual may still be separable by cheap
  premise-body comparison: rendered Prop-premise bodies or normalized token
  sets may distinguish AE measurability from strong measurability without a
  learned model.
- **Eigenquestion:** Does the same-arity same-head residual require richer
  typed slot binding, or only premise-body text/term comparison?
- **Discriminating test:** Reuse v16.0 same-arity semantic decoys. Extract full
  rendered Prop-premise bodies for gold and wrong candidates, compare exact body
  strings and normalized body token sets, and report which rows survive those
  cheap rules.
- **Success criterion:** If premise-body/token comparison separates all v16.0
  decoys, GNN remains blocked and the CPU router should gain this rule.
- **Kill condition:** If a row survives arity, premise-head, and premise-body
  token comparison while still being rejected by Lean witnesses, that becomes a
  stronger learned slot-binding target.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / cheap-rule inversion.
- **Closure:** v16.2 extracted full rendered Prop-premise bodies for the v16.0
  same-arity semantic decoys. Lean returned code `0`. Premise-body exact
  comparison separated `4/4`; normalized body-token comparison also separated
  `4/4`; survivors `0`. The AE-vs-strong-measurability row had identical coarse
  heads but body-token Jaccard only `0.600`, so it is still a cheap CPU rule,
  not a GNN target.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v162_premise_body_slot_audit.py`,
  `analytics/public/leanmill/results/v162_premise_body_slot_audit.json`,
  `analytics/public/leanmill/results/v162_premise_body_slot_audit.md`.

## H-GP225-GNN-16.3 — Same-vocabulary wrong-slot decoy gate

- **Opened:** 2026-05-11
- **Status:** `open`
- **Hypothesis:** To escape body-token bookkeeping, hard negatives must preserve
  premise vocabulary while swapping the slot/object/order inside the premise.
- **Eigenquestion:** Can target-aware witnesses reject same-vocabulary
  wrong-slot premises that arity, head, and body-token rules cannot cheaply
  separate?
- **Discriminating test:** Generate focused gold/wrong candidate pairs whose
  final conclusions match and whose side-condition bodies share almost all
  tokens, but differ by slot order/object: equality direction, budget field,
  sequence field, event index, or measurability mode. Probe all supported
  actions, compare gold digest to wrong digest, and measure body-token Jaccard.
- **Success criterion:** wrong accepted repairs `0`, Sort/Type closures `0`,
  BM25 wrong >= gold on all rows, and at least one wrong-slot row with
  body-token Jaccard `>= 0.85` that is still rejected by the witness.
- **Kill condition:** If body-token/Jaccard or trivial normalized text features
  still separate every row, the current decoy generator remains too synthetic
  for GNN promotion.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / same-vocabulary hard
  negative construction.

## H-GP225-GNN-16.4 — NS same-arity semantic side-condition decoys

- **Opened:** 2026-05-11
- **Status:** `closed / ns_same_vocabulary_residual_survives_body_tokens`
- **Hypothesis:** The current hard-negative lane should move from generic
  measure/SQ3 rows to NS-local proof obstructions: same-arity swaps between
  pressure lock, carrier compatibility, Duhamel incidence source, same-tree
  incidence, bounded fanout, and square-budget side conditions.
- **Eigenquestion:** Can the witness harness reject NS-local wrong-side
  conditions that share the same final conclusion, similar vocabulary, and the
  same number of explicit proof premises?
- **Discriminating test:** Use existing NS declarations as gold and generated
  same-arity wrong declarations as decoys. Probe all supported actions and
  measure wrong accepts, Sort/Type closures, BM25 hardness, and body-token
  overlap.
- **Success criterion:** wrong accepted repairs `0`, Sort/Type closures `0`,
  BM25 wrong >= gold on at least `3/5`, and at least one NS decoy with high
  premise-body token overlap still rejected by Lean witness.
- **Kill condition:** If NS decoys are either not BM25-hard or trivially
  separated by premise-body tokens, the current benchmark is still not testing
  NS-difficulty.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / NS-local obstruction
  hard negatives.
- **Closure:** v16.4 generated 4 NS-local same-arity semantic decoys using
  existing NS gold declarations: pressure lock vs Leray/heat carrier-only,
  Duhamel incidence source vs price-drop identification, Duhamel source vs
  same-tree incidence, and bounded fanout/no-log reuse vs square-budget payment.
  All-action run produced `48` probes, `24` wrong action probes, Lean returncode
  `0`, wrong accepted repairs `0`, Sort/Type closures `0`, BM25 wrong >= gold
  `4/4`, and final-conclusion token Jaccard `1.000` on all rows. Forced
  all-actions-before-gold FDCR was `0/4` at budgets `3` and `5`, `4/4` at
  budgets `10` and `25`.
- **Fast follow-up audit caveat:** v16.5 reused the v16.2 premise-body audit on
  v16.4 and reported exact/token survivors `4/4`, but inspection showed that
  audit only reads `Prop` binders. The NS side conditions here are mostly
  structure-valued binders in `Type`, so v16.5 under-captured the relevant
  premise bodies. Treat v16.5 as an instrumentation-gap finding, not proof that
  body-token rules fail.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v164_ns_same_arity_semantic_decoys.py`,
  `analytics/public/leanmill/results/v164_ns_same_arity_semantic_decoys.json`,
  `analytics/public/leanmill/results/v164_ns_same_arity_semantic_decoys.md`,
  `scripts/public/models/gnn_lemma_relevance/v165_ns_decoy_body_rule_audit.py`,
  `analytics/public/leanmill/results/v165_ns_decoy_body_rule_audit.json`,
  `analytics/public/leanmill/results/v165_ns_decoy_body_rule_audit.md`.

## H-GP225-GNN-16.6 — NS all-binder type-body audit

- **Opened:** 2026-05-11
- **Status:** `closed / all_binder_body_tokens_separate_ns_decoys`
- **Hypothesis:** The v16.5 survivor result is an artifact of inspecting only
  `Prop` binders. An audit over all binder type bodies should reveal whether
  the NS wrong side-condition structures are still cheaply separable.
- **Eigenquestion:** Do NS same-arity decoys survive cheap body-token comparison
  once Type-valued side-condition binders are included?
- **Discriminating test:** Reuse v16.4 declarations and extract rendered type
  bodies for every binder in gold and wrong candidates. Compare full binder type
  token sets and per-position binder token Jaccard.
- **Success criterion:** If all v16.4 decoys separate by all-binder type tokens,
  the GNN gate remains blocked and v16.5 is corrected as an instrument bug.
- **Kill condition:** If any NS decoy survives all-binder type-body comparison,
  proceed to slot-path/incidence features.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / instrument repair.
- **Closure:** v16.6 corrected the v16.5 audit by rendering all binder type
  bodies, including Type-valued NS structure side conditions. Lean returned code
  `0`. All-binder body token comparison separated `4/4` v16.4 NS decoys;
  survivors `0`; binder-token Jaccard ranged from `0.833` to `0.875`. Therefore
  v16.5's apparent body-token residual was an instrument blind spot, not a GNN
  target.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v166_ns_all_binder_body_audit.py`,
  `analytics/public/leanmill/results/v166_ns_all_binder_body_audit.json`,
  `analytics/public/leanmill/results/v166_ns_all_binder_body_audit.md`.

## H-GP225-GNN-16.7 — Same-token argument-slot swap decoys

- **Opened:** 2026-05-11
- **Status:** `closed / same_token_slot_swap_witness_hard`
- **Hypothesis:** The next real residual requires identical binder tokens with
  wrong argument slots, e.g. `exhaustHorizon G L EStar` vs
  `exhaustHorizon L G EStar`, where token-set comparison cannot separate gold
  from wrong.
- **Eigenquestion:** Can target-aware witnesses reject same-token argument-slot
  swaps that defeat all-binder token rules?
- **Discriminating test:** Generate a minimal recurrence decoy where the final
  conclusion is unchanged, arity is unchanged, binder type tokens are identical,
  and only argument order in the premise changes. Probe all supported actions
  and run the all-binder body audit.
- **Success criterion:** wrong accepted repairs `0`, Sort/Type closures `0`,
  BM25 wrong >= gold, all-binder token Jaccard `1.0`, and body-token rule fails
  to separate while Lean witnesses reject.
- **Kill condition:** If even same-token argument-slot swaps are separable by
  cheap deterministic features already present, GNN remains blocked.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / argument-slot residual.
- **Closure:** v16.7 generated the first exact same-token argument-slot decoy:
  `exhaustHorizon G L EStar` versus `exhaustHorizon L G EStar`, with the same
  final conclusion and the same binder arity. Lean returned code `0`; the
  all-action run produced `12` probes, `6` wrong action probes, wrong accepted
  repairs `0`, Sort/Type closures `0`, and BM25 wrong >= gold `1/1`. Forced
  all-actions-before-gold FDCR was `0/1` at budgets `3` and `5`, `1/1` at
  budgets `10` and `25`. This is not enough for GNN promotion, but it is the
  first decoy family that should defeat bag-of-token body rules.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v167_same_token_argument_slot_swap.py`,
  `analytics/public/leanmill/results/v167_same_token_argument_slot_swap.json`,
  `analytics/public/leanmill/results/v167_same_token_argument_slot_swap.md`.

## H-GP225-GNN-16.8 — Same-token slot-path cheap-rule audit

- **Opened:** 2026-05-11
- **Status:** `closed / slot_path_separates_same_token_swap`
- **Hypothesis:** v16.7 defeats all-binder token-set comparison, but a
  deterministic slot-path or binder-body exact-order feature may still separate
  the swapped-argument decoy without learning.
- **Eigenquestion:** Is the v16.7 residual genuinely structural, or does a
  cheap ordered slot signature already rank the gold side-condition above the
  swapped wrong side-condition?
- **Discriminating test:** Reuse v16.7 gold/wrong declarations. Extract all
  binder type bodies, normalized token sets, ordered token sequences, and
  slot-path/argument-order signatures from Lean-rendered binder types. Measure
  whether bag-of-token rules fail and whether ordered/slot signatures separate.
- **Success criterion:** Bag-of-token all-binder Jaccard is `1.0` while an
  ordered slot-path signature separates gold from wrong with no gold false
  reject.
- **Kill condition:** If unordered body tokens separate the row, v16.7 was not
  hard. If ordered slot-path separates it, GNN remains blocked until a larger
  same-slot residual family survives slot-path/incidence rules.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / deterministic
  slot-binding gate.
- **Closure:** v16.8 confirmed the v16.7 residual defeats unordered token
  comparison: all-binder token-set Jaccard was `1.000`, unordered token rule
  separated `0/1`, and even ordered multiset comparison separated `0/1`.
  However, deterministic fvar occurrence paths separated the row: gold placed
  `G` at the first `exhaustHorizon` argument slot and `L` at the second; wrong
  swapped those paths. Lean returned code `0`; slot-path survivor count `0`.
  Therefore the single v16.7 residual is not GNN-ready.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v168_same_token_slot_path_audit.py`,
  `analytics/public/leanmill/results/v168_same_token_slot_path_audit.json`,
  `analytics/public/leanmill/results/v168_same_token_slot_path_audit.md`.

## H-GP225-GNN-16.9 — Expanded same-token slot-swap family

- **Opened:** 2026-05-11
- **Status:** `closed / expanded_same_token_slot_family_clean`
- **Hypothesis:** A single `G/L` slot swap is not enough to promote a new
  residual class. The same-token slot-swap attack must replicate across
  recurrence, Lp translation, convolution, and duality obligations.
- **Eigenquestion:** Do same-token argument-slot swaps remain witness-hard and
  BM25-hard across multiple mathematical domains, or was v16.7 a one-row
  artifact?
- **Discriminating test:** Generate an expanded family: swapped
  `exhaustHorizon` arguments, reversed `1 ≤ p`, reversed kernel
  nonnegativity, and swapped Hölder conjugate arguments. Probe all supported
  actions and record wrong accepts, Sort/Type closures, BM25 hardness, and
  forced all-actions-before-gold FDCR.
- **Success criterion:** Lean compiles; wrong accepted repairs `0`, Sort/Type
  closures `0`, BM25 wrong >= gold on at least `3/4`, and all rows are
  same-token or near-same-token slot swaps.
- **Kill condition:** If the family does not compile or only the recurrence row
  is hard, do not expand to 40; repair the decoy generator first.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / same-token residual
  replication.
- **Closure:** v16.9 replicated same-token/near-same-token slot swaps across
  four domains: recurrence `exhaustHorizon G L` vs `L G`, Lp translation `1 ≤ p`
  vs `p ≤ 1`, convolution `0 ≤ ρ` vs `ρ ≤ 0`, and Hölder duality
  `p.HolderConjugate q` vs `q.HolderConjugate p`. Lean returned code `0`;
  all-action run produced `48` probes and `24` wrong action probes. Wrong
  accepted repairs `0`; Sort/Type closures `0`; BM25 wrong >= gold `4/4`;
  forced all-actions-before-gold FDCR `0/4` at budgets `3` and `5`, `4/4` at
  budgets `10` and `25`.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v169_expanded_same_token_slot_swaps.py`,
  `analytics/public/leanmill/results/v169_expanded_same_token_slot_swaps.json`,
  `analytics/public/leanmill/results/v169_expanded_same_token_slot_swaps.md`.

## H-GP225-GNN-16.10 — Expanded slot-path audit

- **Opened:** 2026-05-11
- **Status:** `closed / expanded_slot_path_separates_all`
- **Hypothesis:** The expanded v16.9 same-token family is witness-hard and
  retrieval-hard, but deterministic slot-path signatures may still separate all
  rows without learning.
- **Eigenquestion:** After expanding same-token decoys across recurrence,
  translation, convolution, and duality, does any row survive fvar/constant
  occurrence-path comparison?
- **Discriminating test:** Reuse v16.9 declarations. Extract all binder type
  bodies plus Lean AST occurrence paths for fvars/constants inside binder
  types. Compare unordered token rules, exact body rules, and slot-path rules
  row by row.
- **Success criterion:** If unordered token rules fail on most rows but
  slot-path separates all rows, promote slot-path as the next CPU feature and
  keep GNN blocked.
- **Kill condition:** If at least one v16.9 row survives slot-path comparison
  while Lean witnesses still reject it, expand that residual family before
  considering training.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / deterministic
  slot-binding over expanded hard negatives.
- **Closure:** v16.10 showed deterministic slot paths separate the expanded
  same-token family. Lean returned code `0`; unordered token rules separated
  only `2/4`; ordered multiset rules separated `2/4`; fvar/constant slot paths
  separated `4/4`; survivor count after slot-path `0`. The two strongest rows
  had all-binder token-set Jaccard `1.000`, so this is a real improvement over
  bag-of-token auditing, but still not a GNN target.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1610_expanded_slot_path_audit.py`,
  `analytics/public/leanmill/results/v1610_expanded_slot_path_audit.json`,
  `analytics/public/leanmill/results/v1610_expanded_slot_path_audit.md`.

## H-GP225-GNN-16.11 — Slot-path semantic-alias canary

- **Opened:** 2026-05-11
- **Status:** `closed / alias_requires_whnf_normalization`
- **Hypothesis:** Exact slot-path features may overfit declaration constants:
  they can reject wrong slot swaps, but may also reject semantically equivalent
  aliases/wrappers of the same side condition.
- **Eigenquestion:** Does the target-aware witness/filter accept a reducible
  alias of the correct local side condition, or does exact slot-path matching
  create a false negative?
- **Discriminating test:** Define a reducible alias of `exhaustHorizon` and an
  alias candidate with the same final conclusion as `contractive_of_exhaustHorizon`.
  Probe all supported actions against the original target, compare after-state
  digest to the gold action, and run slot-path comparison.
- **Success criterion:** Alias candidate is accepted as a semantically valid
  gold equivalent or produces a defeq-normalized after-state digest that can be
  canonicalized without learning.
- **Kill condition:** If alias fails solely because the digest/slot-path sees a
  different constant name, the CPU sidecar needs reducible-definition
  normalization before any larger benchmark or GNN.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / anti-overfit canary.
- **Closure:** v16.11 defined a reducible alias of `exhaustHorizon` and a
  candidate requiring the alias side condition. Lean returned code `0` for both
  probe and metric drivers. The alias had strict digest match count `1`, so
  the witness harness can accept the alias path. Raw binder tokens and raw slot
  paths differed (`raw_token_jaccard = 0.333`, `raw_slot_paths_equal = false`),
  but whnf-normalized bodies and paths matched (`whnf_token_jaccard = 1.000`,
  `whnf_slot_paths_equal = true`). Therefore exact raw slot paths would
  overfit aliases; the CPU sidecar must use reducible-definition normalization.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1611_slot_path_alias_canary.py`,
  `analytics/public/leanmill/results/v1611_slot_path_alias_canary.json`,
  `analytics/public/leanmill/results/v1611_slot_path_alias_canary.md`.

## H-GP225-GNN-16.12 — WHNF slot-path regression

- **Opened:** 2026-05-11
- **Status:** `closed / whnf_slot_path_preserves_wrong_swap_separation`
- **Hypothesis:** WHNF-normalized slot paths should fix the alias false-negative
  risk while preserving separation of the v16.9 wrong slot-swap decoys.
- **Eigenquestion:** Does reducible-definition normalization collapse true
  aliases without collapsing wrong argument-slot swaps?
- **Discriminating test:** Reuse v16.9 wrong-slot decoys. Extract raw and
  whnf-normalized binder type slot paths. Require whnf paths still separate the
  four wrong slot swaps.
- **Success criterion:** `whnf_slot_path_rule_count = 4/4` on v16.9, while
  v16.11 alias has `whnf_slot_paths_equal = true`.
- **Kill condition:** If whnf normalization collapses wrong slot swaps, raw
  slot-path plus alias handling is insufficient and we need a richer
  equivalence-aware incidence feature.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / normalized CPU sidecar.
- **Closure:** v16.12 reran the expanded v16.9 wrong slot-swap family with
  whnf-normalized binder type bodies and occurrence paths. Lean returned code
  `0`; whnf slot-path rule separated `4/4`; survivor count after whnf slot-path
  `0`. Combined with v16.11, this says reducible-definition normalization
  fixes the alias false-negative risk without collapsing the current wrong-slot
  decoys.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1612_whnf_slot_path_regression.py`,
  `analytics/public/leanmill/results/v1612_whnf_slot_path_regression.json`,
  `analytics/public/leanmill/results/v1612_whnf_slot_path_regression.md`.

## H-GP225-GNN-16.13 — Anchored Eq WHNF slot-path regression

- **Opened:** 2026-05-11
- **Status:** `closed / anchored_eq_whnf_slot_path_separates`
- **Hypothesis:** The whnf-normalized slot-path sidecar should generalize from
  the four v16.9 mathematical slot swaps to the older anchored Eq
  counterfactuals, accepting exact aliases while rejecting wrong local-object
  and wrong-order Eq candidates.
- **Eigenquestion:** Does WHNF slot-path distinguish anchored Eq local-object
  mistakes (`x` vs `τ`, swapped frequency variables, wrong RHS constants)
  without falsely rejecting aliases?
- **Discriminating test:** Reuse the v14.4 generated alias/wrong-Eq challenge
  rows. Extract whnf binder-body occurrence paths for gold, alias, and wrong
  declarations. Measure alias equality and wrong separation.
- **Success criterion:** Alias whnf paths match gold on all rows; wrong whnf
  paths differ from gold on all rows.
- **Kill condition:** If any wrong Eq survives whnf slot-path while Lean
  witness rejects it, promote that row to an incidence/action-delta residual.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / CPU sidecar regression.
- **Closure:** v16.13 reused the v14.4 generated alias/wrong-Eq challenge on
  five anchored rows. Lean returned code `0`; alias whnf paths matched gold
  `5/5`; wrong whnf paths separated from gold `5/5`; survivor count `0`.
  This extends v16.12 beyond the four v16.9 slot swaps and shows the WHNF
  slot-path sidecar also handles older local-object/order Eq counterfactuals.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1613_anchored_eq_whnf_slot_path_regression.py`,
  `analytics/public/leanmill/results/v1613_anchored_eq_whnf_slot_path_regression.json`,
  `analytics/public/leanmill/results/v1613_anchored_eq_whnf_slot_path_regression.md`.

## H-GP225-GNN-16.14 — Alpha-stable binder-index slot paths

- **Opened:** 2026-05-11
- **Status:** `closed / alpha_stable_slot_paths_preserve_separation`
- **Hypothesis:** WHNF slot-path separation should not depend on rendered local
  names such as `G`, `L`, `p`, `q`, `x`, or `τ`. Replacing fvar names with
  telescope binder indices should preserve the v16.9 and v16.13 separations.
- **Eigenquestion:** Is the current slot-path sidecar alpha-stable, or is it
  learning binder names?
- **Discriminating test:** Recompute whnf occurrence paths using `fvar#<binder
  index>` instead of pretty-printed fvar names. Run this on the v16.9 expanded
  slot swaps and the v14.4 anchored Eq challenge.
- **Success criterion:** Alias paths still match gold; wrong paths still
  separate on all rows.
- **Kill condition:** If binder-index redaction collapses separations, the
  slot-path sidecar is name-contaminated and cannot support a no-GNN verdict
  without repair.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / alpha-stability audit.
- **Closure:** v16.14 replaced rendered fvar names with telescope binder
  indices and reran both v16.9 expanded slot swaps and v14.4 anchored Eq rows.
  Lean returned code `0`; total row count `9`; alias match count `5/5`; wrong
  separation count `9/9`; survivor count `0`. This repairs the fvar-name
  contamination risk for the current slot-path sidecar.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1614_alpha_stable_slot_path_audit.py`,
  `analytics/public/leanmill/results/v1614_alpha_stable_slot_path_audit.json`,
  `analytics/public/leanmill/results/v1614_alpha_stable_slot_path_audit.md`.

## H-GP225-GNN-16.15 — Conclusion-slot poison audit

- **Opened:** 2026-05-11
- **Status:** `closed / conclusion_body_paths_separate`
- **Hypothesis:** Binder-only slot paths can miss hard negatives whose side
  conditions are identical to gold but whose conclusion applies the repaired
  object to the wrong carrier, argument order, or endpoint. Conclusion-body
  slot paths should be required before any GNN promotion.
- **Eigenquestion:** Do conclusion-side slot paths separate wrong candidates
  that preserve gold binder premises and move the poison into the theorem
  conclusion?
- **Discriminating test:** Generate decoys where binders match gold but
  conclusion slots are wrong: recurrence conclusion uses
  `recurrenceFromGainLoss L G`; duality conclusion flips unit-ball/target
  exponents; convolution conclusion uses a mapped/comapped or orientation-shifted
  term where possible. Probe all actions and compare binder-only versus
  conclusion-body slot paths.
- **Success criterion:** Binder-only feature misses at least one decoy while
  conclusion-body alpha-stable WHNF slot paths separate it and Lean witnesses
  reject wrong actions.
- **Kill condition:** If conclusion-body slot paths separate all rows, promote
  them into the CPU sidecar; GNN remains blocked.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / conclusion incidence.
- **Closure:** v16.15 generated conclusion-poison decoys where binders matched
  gold but conclusion slots were wrong: recurrence conclusion used
  `recurrenceFromGainLoss L G`; duality conclusion flipped the unit-ball/target
  exponent. Lean returned code `0` for probe and metric drivers; `24` probes;
  `12` wrong action probes; wrong accepted repairs `0`; Sort/Type closures `0`;
  BM25 wrong >= gold `2/2`. Binder-only alpha slot paths missed `2/2`, while
  conclusion-body alpha-stable WHNF slot paths separated `2/2`. A translation
  difference-order row was attempted but caused a deterministic `isDefEq`
  heartbeat timeout and was excluded from the clean gate.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1615_conclusion_slot_poison_audit.py`,
  `analytics/public/leanmill/results/v1615_conclusion_slot_poison_audit.json`,
  `analytics/public/leanmill/results/v1615_conclusion_slot_poison_audit.md`.

## H-GP225-GNN-16.16 — Nested alias recursive-WHNF canary

- **Opened:** 2026-05-11
- **Status:** `closed / nested_alias_requires_recursive_whnf`
- **Hypothesis:** Root-level WHNF plus recursive walking is still
  under-normalized. Reducible aliases buried under applications can create fake
  slot-path differences unless the walker normalizes subterms before descent.
- **Eigenquestion:** Does a nested reducible alias inside the conclusion body
  require recursive-WHNF slot paths to avoid false rejection?
- **Discriminating test:** Define a reducible alias of
  `recurrenceFromGainLoss` and an alias candidate whose conclusion uses that
  alias under `contractiveAbove`. Compare root-WHNF body paths versus bounded
  recursive-WHNF body paths against the original gold theorem.
- **Success criterion:** Lean accepts the alias candidate; root-WHNF paths
  differ; recursive-WHNF paths match. Wrong slot swaps must still separate in a
  follow-up regression.
- **Kill condition:** If root-WHNF already normalizes nested aliases, the
  current walker is sufficient for this canary.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / normalization depth.
- **Closure:** v16.16 defined a reducible nested alias
  `recurrenceFromGainLossAlias` under the `contractiveAbove` conclusion and a
  wrong swapped-alias candidate. Initial recursive WHNF instrumentation exposed
  an instrument bug: applying `whnf` to subterms with loose bvars can panic
  Lean, so the walker was repaired to normalize only closed/fvar-open subterms.
  The final run returned probe and metric code `0`; alias strict digest matches
  `1`; root-WHNF paths did not match the gold theorem; binder-safe recursive
  WHNF paths did match the alias; the wrong swapped candidate still differed
  under recursive WHNF. This promotes binder-safe recursive WHNF body paths
  into the CPU sidecar and keeps GNN blocked.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1616_nested_alias_recursive_whnf_canary.py`,
  `analytics/public/leanmill/results/v1616_nested_alias_recursive_whnf_canary.json`,
  `analytics/public/leanmill/results/v1616_nested_alias_recursive_whnf_canary.md`.

## H-GP225-GNN-16.17 — Recursive-WHNF regression over prior decoys

- **Opened:** 2026-05-11
- **Status:** `closed / recursive_whnf_regression_passes`
- **Hypothesis:** Promoting binder-safe recursive-WHNF body paths should not
  collapse any previously separated wrong-slot, anchored-Eq, or
  conclusion-poison decoys while it accepts known reducible aliases.
- **Eigenquestion:** Did the nested-alias normalization repair preserve
  discrimination on the older hard-negative families?
- **Discriminating test:** Recompute binder-safe recursive-WHNF
  alpha-stable binder/body paths for v16.9 expanded slot swaps, v14.4
  anchored Eq alias/wrong rows, v16.15 conclusion-poison rows, and the v16.16
  nested alias row.
- **Success criterion:** All aliases match gold; all wrong candidates differ
  from gold; Lean metric driver exits `0`.
- **Kill condition:** If recursive WHNF makes any wrong candidate equal to
  gold, do not promote it as a default feature without a stronger
  target-aware witness guard.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / CPU ladder regression.
- **Closure:** v16.17 first exposed the cost danger of unrestricted recursive
  WHNF: normalizing every closed subterm hit Lean's deterministic heartbeat
  limit on large terms. The metric was tightened to bounded normalization of
  selected reducible wrappers (`recurrenceFromGainLossAlias` and
  `recurrenceFromGainLoss`) instead of global definitional expansion. The final
  run returned Lean code `0`; row count `12`; alias rows `6`; alias matches
  `6/6`; wrong separations `12/12`; survivor count `0`. This validates the
  v16.16 normalization repair across v16.9, v14.4, v16.15, and v16.16 without
  collapsing prior hard negatives.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1617_recursive_whnf_regression.py`,
  `analytics/public/leanmill/results/v1617_recursive_whnf_regression.json`,
  `analytics/public/leanmill/results/v1617_recursive_whnf_regression.md`.

## H-GP225-GNN-16.18 — Same-candidate wrong-action digest audit

- **Opened:** 2026-05-11
- **Status:** `closed / wrong_action_digest_underidentified`
- **Hypothesis:** After static candidate-side features are strong, a remaining
  pre-GNN risk is action ambiguity: the same candidate can compile under
  several actions, but only the target-aware after-state digest should count as
  the intended repair. If many wrong actions produce indistinguishable digests,
  the witness filter is too weak; if they produce different digests, the next
  CPU feature is action-delta/digest routing, not neural candidate ranking.
- **Eigenquestion:** On the 40-row all-action packet, how often does the same
  gold candidate with a non-gold action produce the same after-state digest as
  the intended gold action?
- **Discriminating test:** Reuse the v15.0 40-row target-unit all-action probe
  matrix. For each row, compare every non-gold action on the gold candidate to
  the gold action's after-state digest.
- **Success criterion:** Wrong-action same-digest rate is low, and most
  compiling non-gold actions are separable by after-state digest rather than
  candidate features.
- **Kill condition:** If many non-gold actions share the gold digest, then
  action labels are underidentified and cannot support a probe-priority
  training target without tighter row contracts.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / action-delta routing.
- **Closure:** v16.18 reused the v15.0 40-row all-action target-unit matrix.
  All `40/40` gold actions accepted. Of `200` same-candidate non-gold action
  probes, `86` compiled; `41` produced a distinct after-state digest, but `45`
  produced the same digest as the gold action across `18` rows. This means the
  packet is action-label underidentified: many rows have legitimate alternate
  actions (`apply`/`rw`/`simp`/`exact` equivalents), so a learned
  action-priority target would be contaminated unless rows record acceptable
  action sets or require a stricter semantic delta.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1618_same_candidate_wrong_action_digest_audit.py`,
  `analytics/public/leanmill/results/v1618_same_candidate_wrong_action_digest_audit.json`,
  `analytics/public/leanmill/results/v1618_same_candidate_wrong_action_digest_audit.md`.

## H-GP225-GNN-16.19 — Acceptable-action contract extraction

- **Opened:** 2026-05-11
- **Status:** `closed / acceptable_action_contract_extracted`
- **Hypothesis:** The v16.18 underidentification can be converted into a
  stronger benchmark contract by declaring same-digest actions as acceptable
  alternates and reserving negatives for failed or distinct-digest actions.
- **Eigenquestion:** After reclassifying same-digest non-gold actions as
  acceptable, how many rows remain genuinely action-discriminating?
- **Discriminating test:** Build a row-level contract from the v15.0 all-action
  matrix: `accepted_actions = {gold_action} ∪ same_digest_non_gold_actions`,
  `distinct_progress_actions`, and `failed_actions`.
- **Success criterion:** The contract identifies rows with strict
  action-discrimination separately from rows where several tactics are
  equivalent local repairs.
- **Kill condition:** If most rows have many acceptable actions, the packet is
  a candidate-repair benchmark but not an action-priority benchmark.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / benchmark contract
  repair.
- **Closure:** v16.19 converted the v15.0 all-action packet into explicit
  row-level action contracts. Of `40` rows, `22` are strict-action rows and
  `18` are multi-action-equivalent rows. The accepted-action count histogram is
  `{1: 22, 2: 5, 3: 1, 4: 11, 6: 1}`; `38` rows have at least one distinct
  non-gold progress action. This repairs the label semantics: candidate-repair
  evaluation may use all rows, but action-priority evaluation/training must use
  accepted-action sets or the strict subset.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1619_acceptable_action_contract.py`,
  `analytics/public/leanmill/results/v1619_acceptable_action_contract.json`,
  `analytics/public/leanmill/results/v1619_acceptable_action_contract.md`.

## H-GP225-GNN-16.20 — Accepted-action policy rescore

- **Opened:** 2026-05-11
- **Status:** `closed / accepted_action_policy_rescore_ran`
- **Hypothesis:** Re-scoring the 40-row policy gate against accepted-action
  sets should reduce false action-label penalties and reveal whether the CPU
  router's value is candidate ordering, action ordering, or both.
- **Eigenquestion:** After v16.19 contract repair, do deterministic policies
  still dominate the packet without learned/GNN scoring, especially on the
  strict-action subset and NS rows?
- **Discriminating test:** Reuse the v15.1 40-row / 40-candidate / 6-action
  matrix and v16.19 accepted-action contracts. Evaluate generic, domain/head,
  full-interface, target-kind, BM25-generic, and BM25-target-kind policies on
  all rows, strict-action rows, multi-action-equivalent rows, and NS rows.
- **Success criterion:** Metrics report accepted-action success@budgets,
  mean failed probes, false-before rows, and subset performance.
- **Kill condition:** If accepted-action rescore collapses the previous router
  advantage, treat v15.1-v15.2 policy evidence as action-label artifact.
- **Scope:** GP-225 pre-GNN theorem-workstation lane / policy scoring.
- **Closure:** v16.20 rescored generic, domain/head, full-interface,
  target-kind, BM25-generic, and BM25-target-kind policies using v16.19
  accepted-action contracts. On all `40` rows, full-interface and
  BM25-generic both reached success@10 `36/40`, success@25 `40/40`, mean
  failed `3.05`; BM25-target-kind kept success@10 `36/40` and improved mean
  failed to `2.1`. On the `22` strict-action rows, BM25-target-kind reached
  success@10 `20/22`, success@25 `22/22`, mean failed `2.18`. On the `16`
  NS-only rows, generic fixed reached success@10 `2/16`, while target-kind and
  BM25-target-kind reached success@10 `14/16`, success@25 `16/16`, mean failed
  `3.0`, false-before rows `0`. This shows the current instrument is useful
  for NS probe reduction, but cheap CPU baselines remain strong and GNN is not
  justified.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1620_accepted_action_policy_rescore.py`,
  `analytics/public/leanmill/results/v1620_accepted_action_policy_rescore.json`,
  `analytics/public/leanmill/results/v1620_accepted_action_policy_rescore.md`.

## H-GP225-GNN-16.21 — NS sidecar application report

- **Opened:** 2026-05-11
- **Status:** `closed / ns_sidecar_application_report_ran`
- **Hypothesis:** The GP-225 CPU sidecar should be immediately useful on the
  NS track as a candidate-action probe queue, even though it is not GNN-ready.
- **Eigenquestion:** Which NS local-obligation rows benefit, which remain
  budget-10 misses, and what candidate-action probes are being tried before
  the accepted repair?
- **Discriminating test:** Extract the NS-only row-level queue from v16.20 for
  BM25-target-kind and target-kind policies. Report first accepted probe,
  accepted actions, budget-10 misses, and top probes before success.
- **Success criterion:** Produce a concrete NS advisory report that identifies
  where the sidecar saves probes and where the next NS-specific feature should
  focus.
- **Kill condition:** If NS gains are concentrated only in old synthetic rows
  or are indistinguishable from generic queueing, do not spend more GP-225 time
  before returning to direct NS proof work.
- **Scope:** GP-225 to NS-track transfer / advisory CPU sidecar.
- **Closure:** v16.21 extracted the NS-only advisory queue from v16.20. Both
  target-kind and BM25-target-kind policies reached success@10 `14/16`,
  success@25 `16/16`, mean first accepted repair `4.0`. The only budget-10
  misses were `v150_cumulative_lsc_apply` and
  `v150_cumulative_struct_apply`; both are cumulative-dissipation LSC rows
  delayed behind L2/vector-L2 LSC candidates that fail or produce non-gold
  `Iff` side goals. This is concrete NS value: the sidecar reduces probe waste
  sharply, but the next NS-specific CPU feature should distinguish cumulative
  LSC from L2 LSC before any learned model.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1621_ns_sidecar_application_report.py`,
  `analytics/public/leanmill/results/v1621_ns_sidecar_application_report.json`,
  `analytics/public/leanmill/results/v1621_ns_sidecar_application_report.md`.

## H-GP225-GNN-16.22 — NS cumulative-LSC slot-path fallback

- **Opened:** 2026-05-11
- **Status:** `closed / slot_path_fallback_fixes_cumulative_lsc`
- **Hypothesis:** The two NS budget-10 misses in v16.21 are caused by
  pretty-print signature collapse (`failed to pretty print expression`) rather
  than a need for learned ranking. Kernel slot-path fallback should distinguish
  cumulative-dissipation LSC from L2/vector-L2 LSC.
- **Eigenquestion:** If the textual signature channel fails, do alpha-stable
  binder/body slot paths move the accepted cumulative-LSC candidate into the
  first 10 probes?
- **Discriminating test:** For the two cumulative NS LSC rows, extract
  alpha-stable binder/body paths for target and all 40 candidates, rank
  candidates by path Jaccard with domain/head tie-breaks, and reuse the v15.1
  probe matrix plus v16.19 accepted-action contract.
- **Success criterion:** The slot-path fallback improves the two budget-10
  misses without adding false-before accepted repairs.
- **Kill condition:** If slot-path fallback still ranks L2 LSC ahead of
  cumulative LSC, promote this as a real NS residual candidate for a later
  learned probe-priority model after more rows.
- **Scope:** GP-225 to NS-track transfer / CPU fallback feature.
- **Closure:** v16.22 extracted alpha-stable binder/body slot paths for the two
  cumulative NS LSC budget-10 misses and all 40 candidates. The path fallback
  returned Lean code `0`; both rows moved to first accepted repair at probe
  `1`: `cumulativeDissipation_LSC_from_pointwise` for
  `v150_cumulative_lsc_apply` and
  `cumulativeDissipationLSC_from_pointwise` for
  `v150_cumulative_struct_apply`. This fixes the v16.21 NS budget-10 misses
  with a generic kernel fallback when pretty-printed signatures collapse.
  Learned/GNN training remains blocked.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1622_ns_cumulative_lsc_slot_path_fallback.py`,
  `analytics/public/leanmill/results/v1622_ns_cumulative_lsc_slot_path_fallback.json`,
  `analytics/public/leanmill/results/v1622_ns_cumulative_lsc_slot_path_fallback.md`.

## H-GP225-GNN-16.23 — Integrated slot-path fallback policy

- **Opened:** 2026-05-11
- **Status:** `closed / integrated_slot_path_fallback_policy_ran`
- **Hypothesis:** The v16.22 slot-path fallback should be integrated as a
  generic policy branch for signature-collapse rows, improving NS success
  without damaging the 40-row accepted-action benchmark.
- **Eigenquestion:** Does a hybrid policy that uses BM25-target-kind normally
  and alpha-stable slot-path ranking when target signatures collapse dominate
  BM25-target-kind on the current packet?
- **Discriminating test:** Reuse the v15.1 40-row matrix, v16.19
  accepted-action contracts, and v16.22 path metrics for the two known
  signature-collapse rows. Compare BM25-target-kind versus hybrid fallback on
  all rows, strict-action rows, multi-action rows, and NS-only rows.
- **Success criterion:** Hybrid fallback preserves all-row success@10/25 and
  improves NS-only success@10 from `14/16` to `16/16` without false-before
  accepted repairs.
- **Kill condition:** If fallback creates false-before rows or worsens
  non-NS/all-row performance, keep it as a manual diagnostic rather than a
  default policy.
- **Scope:** GP-225 pre-GNN CPU sidecar / NS application.
- **Closure:** v16.23 integrated the v16.22 path fallback into the policy:
  use BM25-target-kind normally, and slot-path ranking on the two
  signature-collapse cumulative-LSC rows. On all `40` rows, success@10 improved
  from `36/40` to `38/40`, success@25 stayed `40/40`, mean failed improved
  from `2.1` to `1.35`, false-before rows stayed `0`. On the strict-action
  subset, success@10 improved from `20/22` to `22/22`, mean failed `2.18` to
  `0.82`. On NS-only rows, success@10 improved from `14/16` to `16/16`, mean
  failed `3.0` to `1.125`, false-before rows `0`. This promotes the hybrid
  CPU sidecar and further blocks GNN.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1623_integrated_slot_path_fallback_policy.py`,
  `analytics/public/leanmill/results/v1623_integrated_slot_path_fallback_policy.json`,
  `analytics/public/leanmill/results/v1623_integrated_slot_path_fallback_policy.md`.

## H-GP225-GNN-16.24 — Broad signature-collapse slot-path trigger

- **Opened:** 2026-05-11
- **Status:** `open`
- **Hypothesis:** The v16.23 slot-path fallback should not be hard-coded to the
  two cumulative-LSC rows. A principled trigger based on target pretty-printer
  signature collapse can identify which rows need kernel slot-path ranking,
  while preserving the target-aware accepted-action contract.
- **Eigenquestion:** If every target-collapsed row uses alpha-stable slot-path
  ranking instead of BM25 target tokens, does the hybrid policy improve or at
  least preserve repair success without new false-before accepted repairs?
- **Discriminating test:** Detect target-collapsed rows from v15.1 signatures,
  extract alpha-stable binder/body paths for those targets and all candidates,
  evaluate slot-path ordering with v16.19 accepted-action contracts, and compare
  BM25-target-kind, hard-coded v16.23 fallback, and broad-collapse fallback on
  all rows, strict-action rows, multi-action rows, and NS-only rows.
- **Success criterion:** Broad-collapse fallback improves or preserves
  success@10/25 and mean failed probes relative to v16.23 with
  false-before rows remaining `0`.
- **Kill condition:** If broad fallback damages any subset or creates
  false-before accepted repairs, keep the fallback gated to the specific
  signature-collapse subfamily where slot paths have already been verified.
- **Scope:** GP-225 pre-GNN CPU sidecar / principled fallback trigger.
- **Closure:** v16.24 detected `10` target-collapsed rows and applied
  slot-path fallback to all of them. Compared with the v16.23 hard-coded
  fallback, broad-collapse fallback improved all-row mean failed probes
  `1.35 -> 1.05`, strict-action mean `0.82 -> 0.27`, and NS-only mean
  `1.125 -> 0.375`, while preserving all-row success@10 `38/40`,
  success@25 `40/40`, and false-before rows `0`. The remaining budget-10
  misses are `v89` and `v135_mulchar_norm`, both harmonic-analysis Eq rows
  delayed by per-candidate action exhaustion rather than slot-path failure.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1624_broad_signature_collapse_slot_path_trigger.py`,
  `analytics/public/leanmill/results/v1624_broad_signature_collapse_slot_path_trigger.json`,
  `analytics/public/leanmill/results/v1624_broad_signature_collapse_slot_path_trigger.md`.

## H-GP225-GNN-16.25 — Candidate-sweep action scheduler

- **Opened:** 2026-05-11
- **Status:** `open`
- **Hypothesis:** The two v16.24 budget-10 residuals are not candidate-ranking
  residuals but action-scheduler residuals: the gold Eq candidate is close in
  the queue, yet the policy exhausts every action on earlier Eq candidates
  before trying the gold candidate's primary action.
- **Eigenquestion:** Does a round-robin candidate sweep over action rank reduce
  failed probes and close the remaining budget-10 misses without introducing
  false-before accepted repairs?
- **Discriminating test:** Reuse the v15.1 probe matrix, v16.19
  accepted-action contracts, and v16.24 broad slot-path candidate order.
  Compare candidate-major scheduling versus action-rank sweep scheduling under
  BM25 candidate order and broad slot-path fallback candidate order.
- **Success criterion:** Broad slot-path fallback plus action-rank sweep reaches
  all-row success@10 `40/40` and preserves false-before rows `0`, while reducing
  mean failed probes relative to v16.24.
- **Kill condition:** If action sweep creates false-before accepted repairs or
  worsens NS/strict-action subsets, keep candidate-major scheduling and promote
  the harmonic Eq rows as residuals for a narrower action-priority audit.
- **Scope:** GP-225 pre-GNN CPU sidecar / probe-budget controller.
- **Closure:** v16.25 confirmed the residual was an action-scheduling artifact.
  BM25 candidate-major was `36/40` success@10 with mean failed `2.1`; BM25
  action-rank sweep reached `40/40` success@10 with mean failed `0.35`.
  Broad slot-path candidate-major was `38/40` success@10 with mean failed
  `1.05`; broad slot-path action-rank sweep reached `40/40` success@3 and
  success@10, mean failed `0.175`, false-before rows `0`. NS-only improved to
  `16/16` success@3 with mean failed `0.0625`. This closes the current
  residual without learning and makes the strongest next question a baseline
  dominance audit, not GNN training.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1625_candidate_sweep_action_scheduler.py`,
  `analytics/public/leanmill/results/v1625_candidate_sweep_action_scheduler.json`,
  `analytics/public/leanmill/results/v1625_candidate_sweep_action_scheduler.md`.

## H-GP225-GNN-16.26 — Scheduler baseline dominance audit

- **Opened:** 2026-05-11
- **Status:** `open`
- **Hypothesis:** The v16.25 jump may be mostly an action-scheduler fix rather
  than evidence for typed slot-path representation. If generic, domain/head, or
  full-interface candidate queues plus action-rank sweep match BM25/slot-path
  sweep, GP-225 should be treated as a useful CPU scheduler, not a novel
  representation.
- **Eigenquestion:** Under the accepted-action contract, how much of the
  `40/40` result comes from candidate ordering versus avoiding per-candidate
  action exhaustion?
- **Discriminating test:** Compare generic-fixed, domain/head, full-interface,
  BM25, and broad slot-path candidate ordering under both candidate-major and
  action-rank sweep schedules on the v15.1 matrix and v16.19 contracts.
- **Success criterion:** The audit identifies the strongest cheap baseline and
  quantifies whether broad slot-path sweep has material residual advantage
  beyond scheduler-only improvements.
- **Kill condition:** If simple candidate queues plus action sweep match broad
  slot-path sweep on success and mean failed probes, block representation/GNN
  novelty and keep the result as an engineering scheduler gain.
- **Scope:** GP-225 pre-GNN truth gate / baseline audit.
- **Closure:** v16.26 separated scheduler gain from representation gain. On all
  rows, broad slot-path plus action-rank sweep remained best with success@3
  `40/40`, success@10 `40/40`, mean failed `0.175`, false-before rows `0`.
  But BM25 and full-interface plus the same action-rank sweep both reached
  success@10 `40/40` and success@5 `40/40`, mean failed `0.35`. Domain/head
  plus sweep also reached success@10 `40/40` with mean failed `1.175`.
  Interpretation: the main v16.25 jump is a probe scheduler correction; broad
  slot paths improve tight budget and NS mean probes, but the packet does not
  support GNN or representation novelty.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1626_scheduler_baseline_dominance_audit.py`,
  `analytics/public/leanmill/results/v1626_scheduler_baseline_dominance_audit.json`,
  `analytics/public/leanmill/results/v1626_scheduler_baseline_dominance_audit.md`.

## H-GP225-GNN-16.27 — Plausible-decoy scheduler stress

- **Opened:** 2026-05-11
- **Status:** `open`
- **Hypothesis:** The action-rank sweep scheduler should be robust to a single
  plausible wrong candidate forced before gold, because it tries the primary
  action on the gold candidate before exhausting all actions on the decoy. If
  it is not robust, v16.25/v16.26 overstate the scheduler gain.
- **Eigenquestion:** On the v15.8 plausible missing-obligation decoys, does
  action-rank sweep preserve target-aware repair within tight budgets while
  candidate-major scheduling wastes probes?
- **Discriminating test:** Reuse the v15.8 all-action plausible-decoy Lean
  matrix. For each row, force wrong candidate before gold and compare
  candidate-major versus action-rank sweep using the existing witness digest.
- **Success criterion:** Action-rank sweep reaches FDCR@3 `8/8` with wrong
  accepted repairs `0`, while candidate-major remains worse under the same
  forced-front order.
- **Kill condition:** If action-rank sweep admits wrong repairs or misses tight
  budget on this one-decoy packet, pause the scheduler promotion and audit the
  witness filter/action priorities.
- **Scope:** GP-225 pre-GNN hard-negative scheduler stress.
- **Closure:** v16.27 reused the v15.8 plausible missing-obligation decoy
  packet where BM25 ranks wrong >= gold on `8/8` rows and Lean accepts no wrong
  repairs. With wrong forced before gold, candidate-major scheduling reached
  FDCR@3 `0/8`, FDCR@10 `8/8`, mean failed `6.0`; action-rank sweep reached
  FDCR@3/5/10/25 `8/8`, mean failed `1.0`, wrong accepts `0`. This validates
  the scheduler correction under plausible forced-front decoys, but it is still
  deterministic CPU behavior and does not justify GNN.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1627_plausible_decoy_scheduler_stress.py`,
  `analytics/public/leanmill/results/v1627_plausible_decoy_scheduler_stress.json`,
  `analytics/public/leanmill/results/v1627_plausible_decoy_scheduler_stress.md`.

## H-GP225-GNN-16.28 — Live NS Phase 5CG sidecar inventory

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The current GP-225 sidecar can be applied to the live NS
  Phase 5CG frontier only after separating theorem-like local goals from
  `def ... : Prop` obligation schemas. A live inventory should identify which
  declarations are directly probeable and which need generated wrapper theorem
  holes before proof-state progress can be counted.
- **Eigenquestion:** Does the Phase 5CG frontier currently expose enough
  theorem-like local obligations for GP-225 action probing, or is the next step
  to compile wrapper-hole targets around Prop-valued obligation schemas?
- **Discriminating test:** Scan the Phase 5CG Lean files, import their modules,
  query Lean elaborated declaration types and conclusion heads, classify
  declarations as theorem-like, Prop-schema, structure/data, or auxiliary, and
  emit a sidecar readiness packet with candidate modules and next wrapper
  targets.
- **Success criterion:** Produce a cold-start legible NS packet listing direct
  probe targets, wrapper-required targets, candidate helper declarations, and
  the exact next Lean wrapper construction needed for a counted live sidecar
  run.
- **Kill condition:** If the current files cannot be imported or queried cleanly,
  stop at the instrument failure and do not claim GP-225 is ready for live NS
  use.
- **Scope:** GP-225 to NS transfer / live-obligation readiness.
- **Closure:** v16.28 imported the Phase 5CG frontier/helper modules through
  Lean and queried `189` declarations successfully after fixing the extractor
  namespace import. Inventory: `15` live target-like declarations, `70` direct
  theorem/lemma candidates, `22` Prop helper schemas, `11` wrapper-required
  Prop-valued live obligation schemas, `35` data carriers, and `134` NS graph
  nodes matched. The NS artifact graph is usable as a soft candidate-source
  prior through shared tags, op classes, file locality, and use edges, but
  counted proof-state progress is not available directly from the Prop-schema
  declarations. The next step is generated theorem-hole wrappers around the
  wrapper-required schemas, then action-rank GP-225 probes on those local goals.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1628_live_ns_phase5cg_sidecar_inventory.py`,
  `analytics/public/leanmill/results/v1628_live_ns_phase5cg_sidecar_inventory.json`,
  `analytics/public/leanmill/results/v1628_live_ns_phase5cg_sidecar_inventory.md`.

## H-GP225-GNN-16.29 — Live NS wrapper-hole action probe canary

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The live Phase 5CG Prop-schema targets can be converted into
  executable local theorem-hole proof states, and the current deterministic
  GP-225 sidecar can produce a target-aware candidate-action queue without
  using a learned/GNN model.
- **Eigenquestion:** When Phase 5CG obligation schemas are wrapped as local
  proof goals, does the deterministic action-rank sidecar expose useful live
  NS repair routes, or do natural residuals appear that survive BM25/full
  interface, slot-path fallback, and action sweep?
- **Discriminating test:** Generate Lean wrapper theorem-hole goals for the
  highest-value v16.28 wrapper-required targets, run bounded action probes
  against NS-graph-near candidates, and record compiled action results,
  after-state heads, accepted local progress, and false-before/wrong-action
  risks.
- **Success criterion:** Emit a packet listing at least three executable
  wrapper-hole targets, their graph-near candidate-action queues, and whether
  any candidate-action pair produces target-aware local progress under the
  deterministic sidecar.
- **Kill condition:** If wrapper theorem holes cannot be generated/imported
  cleanly, close as a target-construction blocker and do not claim NS proof
  progress. If deterministic policies solve the packet cleanly, keep GNN
  blocked.
- **Scope:** GP-225 to live NS transfer / pre-GNN natural canary.
- **Closure:** v16.29 generated actual applied-predicate local goals after
  fixing an initial wrapper bug that had reduced goals to bare `Prop`. Lean
  ran cleanly over `5` live targets, `40` graph-near candidates, and `240`
  candidate-action probes. Raw compiled actions were `42/240`: `2` `apply`
  probes and `40` `convert_using1` probes. Manual witness inspection shows the
  `convert_using1` probes mostly create broad `Iff` obligations between
  unrelated Prop schemas and candidate theorem types, so raw v16.29 cannot be
  counted as NS progress. The useful finding is target construction plus a
  need for strict convert/Iff rejection before any live-sidecar promotion.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1629_live_ns_wrapper_hole_probe.py`,
  `analytics/public/leanmill/results/v1629_live_ns_wrapper_hole_probe.json`,
  `analytics/public/leanmill/results/v1629_live_ns_wrapper_hole_probe.md`.

## H-GP225-GNN-16.30 — Strict live NS wrapper witness filter

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** Most v16.29 live wrapper “progress” is convert-overbreadth,
  not useful repair. A strict witness filter should reject Iff-only conversion
  artifacts and leave only apply-style local route exposures, if any.
- **Eigenquestion:** After rejecting broad convert/Iff artifacts, does any
  graph-near candidate-action pair still produce target-aware local progress
  on live Phase 5CG wrapper goals?
- **Discriminating test:** Re-score the v16.29 probe matrix with a strict
  acceptance predicate: no Sort/Type heads, no target-as-hypothesis, no
  `convert_using1` accepted when the first generated side goal is `Iff`, and no
  guard/False endpoint accepted as progress.
- **Success criterion:** Emit a strict post-filter packet that identifies
  accepted live routes, false-before rows, and remaining blocked targets.
- **Kill condition:** If all accepted routes disappear under the strict filter,
  do not claim live NS sidecar progress; move to wrapper design / target-kind
  repair instead of GNN.
- **Scope:** GP-225 live NS witness quality / convert-overbreadth audit.
- **Closure:** v16.30 strict-filtered the v16.29 live NS wrapper probes. Raw
  compiled probes were `42/240`, but strict accepted probes fell to `2`: 
  `pressureL2TransportDefectObligation` via
  `transport_defect_control_of_pressureL2TransportObligation`/`apply`, and
  `phase5cgBroadProofSearchTarget` via
  `local_route_promoted_of_phase5cgBroadProofSearchTarget`/`apply`.
  Rejections: `198` tactic failures, `39` convert/Iff overbreadth artifacts,
  and `1` bad after-head. The two survivors expose downstream/local route
  obligations, not solved NS atoms. This confirms the CPU sidecar's immediate
  NS value as a live obligation-consequence explorer and keeps GNN blocked.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1630_strict_live_ns_wrapper_witness_filter.py`,
  `analytics/public/leanmill/results/v1630_strict_live_ns_wrapper_witness_filter.json`,
  `analytics/public/leanmill/results/v1630_strict_live_ns_wrapper_witness_filter.md`.

## H-GP225-GNN-16.31 — Graph-only versus sidecar versus combined truth table

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The apparent GP-225 gain is not a single number. It should
  split into: graph/candidate ordering alone, action-scheduler sidecar alone,
  and graph plus deterministic sidecar. A defensible 10x claim may hold versus
  graph-only candidate-major probing, but not necessarily versus the strongest
  cheap graph/BM25 plus action-sweep baseline.
- **Eigenquestion:** Against the relevant baselines, where does the current
  pre-GNN stack actually produce a 10x probe-efficiency collapse, and where is
  it only a useful incremental gain?
- **Discriminating test:** Summarize v16.26 repaired 40-row policy metrics and
  v16.30 live NS wrapper metrics into a single comparison table: graph-only
  proxy, sidecar/scheduler-only, BM25/action, and combined broad-slot/action
  stack.
- **Success criterion:** Emit a cold-start legible report that states which
  comparisons clear 10x, which do not, and what this implies for GNN launch.
- **Kill condition:** If no comparison clears 10x against a meaningful baseline,
  stop using 10x language for the current stack. If only weak/generic baselines
  clear 10x, label it useful engineering rather than novelty.
- **Scope:** GP-225 pre-GNN status compression / 10x truth table.
- **Closure:** v16.31 shows the stack is 10x only against weaker/generic or
  candidate-major baselines. On the repaired 40-row packet, combined
  broad-slot/action-sweep has mean failed `0.175`, versus graph-proxy
  domain/head candidate-major `7.05` (`40.3x`) and scheduler-only generic
  action-sweep `19.5` (`111.4x`). Against stronger baselines, the gap shrinks:
  graph-proxy domain/head action-sweep `1.175` (`6.7x`) and BM25 action-sweep
  `0.35` (`2x`). NS-only repaired rows show the same pattern: `48x` versus
  graph candidate-major, but `8x` versus graph/BM25 action-sweep. Live NS
  wrapper probes remain `2/5` strict route exposures, not a 10x or solver
  claim.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1631_graph_sidecar_combined_truth_table.py`,
  `analytics/public/leanmill/results/v1631_graph_sidecar_combined_truth_table.json`,
  `analytics/public/leanmill/results/v1631_graph_sidecar_combined_truth_table.md`.

## H-GP225-GNN-16.32 — Live NS route-exposure patch skeletons

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The two v16.30 strict live NS survivors can be promoted from
  advisory probe records into compile-checked Lean wrapper patches that expose
  downstream obligations/consequences without pretending to solve the source
  analytic atoms.
- **Eigenquestion:** Can GP-225's live NS route exposures produce executable
  theorem snippets that are useful to an NS proof worker, while preserving the
  distinction between source-obligation proof and consequence exposure?
- **Discriminating test:** Generate a temporary Lean packet containing wrapper
  theorems for the two strict survivors: pressure transport-defect consequence
  exposure and broad Phase 5CG fork exposure. Compile it and emit patch
  skeletons plus blocked-target labels for the other three live schemas.
- **Success criterion:** Lean returncode `0`, two compile-checked wrapper
  snippets, and explicit target-kind classification for all five v16.29 live
  targets.
- **Kill condition:** If wrappers fail to compile, treat v16.30 survivors as
  probe-only artifacts. If wrappers compile, still do not claim source
  obligations are solved.
- **Scope:** GP-225 live NS transfer / patch-skeleton promotion.
- **Closure:** v16.32 compiled both route-exposure wrappers with Lean returncode
  `0`. The generated snippets prove consequence-exposure wrappers for
  `pressureL2TransportDefectObligation` and `phase5cgBroadProofSearchTarget`,
  while preserving that both source obligations remain unpaid. The three other
  live wrapper targets remain blocked after strict convert/Iff rejection:
  `EventRecurrencePricePDEObligationSatisfied`, `ns2028HindsightBundle`, and
  `uniformContinuationObligation`.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1632_live_ns_route_exposure_patch_skeletons.py`,
  `analytics/public/leanmill/results/v1632_live_ns_route_exposure_patch_skeletons.json`,
  `analytics/public/leanmill/results/v1632_live_ns_route_exposure_patch_skeletons.md`.

## H-GP225-GNN-16.33 — Live NS blocked-target decomposition packet

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The three v16.30/v16.32 blocked live NS targets are not
  primarily failed theorem-retrieval cases. They are source-obligation
  decomposition targets whose correct first action is constructor/unfold
  decomposition into local duties: two duties for
  `uniformContinuationObligation`, four bundle components for
  `ns2028HindsightBundle`, and twenty record fields for
  `EventRecurrencePricePDEObligationSatisfied`.
- **Eigenquestion:** Does a target-kind-specific decomposition wrapper compile
  for the blocked live NS schemas, and does it expose the actual unpaid NS
  duties that the router should route next?
- **Discriminating test:** Generate temporary Lean wrappers that construct and
  destructure the three blocked targets by their source duties, compile them,
  and emit a target-kind design packet listing component obligations and the
  next valid GP-225 routing unit for each target.
- **Success criterion:** Lean returncode `0`, compile-checked construction and
  projection wrappers for all three blocked targets, and an artifact that
  classifies each blocked target as decomposition/source-duty routing rather
  than graph-near theorem application.
- **Kill condition:** If the decomposition wrappers fail to compile, keep the
  targets blocked and audit namespace/import/target-shape assumptions before
  further NS sidecar claims.
- **Scope:** GP-225 live NS transfer / blocked-target target-kind repair.
- **Closure:** v16.33 compiled construction and component/projection wrappers
  for all three blocked live NS targets with Lean returncode `0`. The targets
  are now classified as decomposition/source-duty routing units:
  `uniformContinuationObligation` splits into two duties, `ns2028HindsightBundle`
  splits into four component obligations, and
  `EventRecurrencePricePDEObligationSatisfied` splits into twenty named record
  fields. This means the v16.30/v16.32 blocked result was primarily
  target-kind mismatch, not a learned residual or a reason to launch GNN.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1633_live_ns_blocked_target_decomposition.py`,
  `analytics/public/leanmill/results/v1633_live_ns_blocked_target_decomposition.json`,
  `analytics/public/leanmill/results/v1633_live_ns_blocked_target_decomposition.md`.

## H-GP225-GNN-16.34 — Live NS target-kind metric separation

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The live NS sidecar should be evaluated by target kind rather
  than by one blended success metric. The current five wrapper targets should
  split into source-proof progress, consequence exposure, source-duty
  decomposition, downstream-subgoal routing, and analytic-atom identification.
- **Eigenquestion:** After v16.30-v16.33, what did GP-225 actually accomplish
  on live NS, and what exact next local obligations should be routed without
  inflating consequence exposure into proof progress?
- **Discriminating test:** Merge the strict witness filter, route-exposure
  wrappers, and blocked-target decomposition artifacts into a target-kind
  ledger. Report counts separately for source-proof progress, consequence
  exposure, source-duty decomposition, downstream subgoals exposed, and
  analytic atoms still unpaid.
- **Success criterion:** Emit a cold-start legible packet with no blended
  "success" metric, explicit forbidden conflations, and a next-row queue for
  downstream/source-duty local obligations.
- **Kill condition:** If the artifacts cannot be reconciled without ambiguous
  success semantics, do not continue live NS scoring until target-kind labels
  are repaired.
- **Scope:** GP-225 live NS transfer / metric hygiene before public baselines.
- **Closure:** v16.34 merged the strict witness, route-exposure wrapper, and
  blocked-target decomposition packets into separate target-kind metrics:
  source-proof progress `0/5`, consequence exposure `2/5`, source-duty
  decomposition `3/5`, downstream/component local units `32`, and unpaid
  analytic atoms `26`. The result is useful but explicitly blocks solver/GNN
  claims: current live NS progress is target-kind triage plus route exposure,
  not proof of any source obligation.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1634_live_ns_target_kind_metric_packet.py`,
  `analytics/public/leanmill/results/v1634_live_ns_target_kind_metric_packet.json`,
  `analytics/public/leanmill/results/v1634_live_ns_target_kind_metric_packet.md`.

## H-GP225-GNN-16.35 — Live NS downstream/source-duty wrapper packet

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The next honest live NS GP-225 rows are the downstream and
  source-duty units exposed by v16.34, not the original whole schemas. These
  units should compile as local wrapper targets with explicit primitive
  premises, giving the sidecar concrete atoms to route next.
- **Eigenquestion:** Can the v16.34 next-row queue be converted into
  compile-checked local wrapper targets for pressure downstream atoms and
  Phase 5CG branch choices without assuming the original source obligations?
- **Discriminating test:** Generate temporary Lean wrappers that construct and
  destructure the pressure downstream atoms (`l2CarrierTransportInequality`,
  `commutatorResidualProfileSuppressed`) and the Phase 5CG branch choices
  (`commutatorTowerProofSearchTarget`, `globalPressureTailBootstrap`,
  `uniformContinuationObligation`, `smallLargeSplitObligation`). Compile them
  and emit the resulting local-obligation packet.
- **Success criterion:** Lean returncode `0`, wrapper rows for the pressure
  downstream pair and all four Phase 5CG branches, and a packet that states
  which primitive duties each row requires.
- **Kill condition:** If these wrappers require assuming
  `pressureL2TransportDefectObligation` or `phase5cgBroadProofSearchTarget`,
  the packet is invalid because it would confuse consequence exposure with
  proof progress.
- **Scope:** GP-225 live NS transfer / downstream local-obligation generation.
- **Closure:** v16.35 compiled the downstream/source-duty wrapper packet with
  Lean returncode `0`. It produced five row families: direct
  `l2CarrierTransportInequality`, direct
  `commutatorResidualProfileSuppressed`, a pressure downstream pair,
  `commutatorTowerProofSearchTarget`, and Phase 5CG branch-choice wrappers.
  These rows do not assume `pressureL2TransportDefectObligation` or
  `phase5cgBroadProofSearchTarget`; they expose the primitive duties required
  for future closure or missing-lemma reports.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1635_live_ns_downstream_source_duty_packet.py`,
  `analytics/public/leanmill/results/v1635_live_ns_downstream_source_duty_packet.json`,
  `analytics/public/leanmill/results/v1635_live_ns_downstream_source_duty_packet.md`.

## H-GP225-GNN-16.36 — Live NS solver-0 close-or-gap contract

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** A solver-like GP-225 unit should not stop at accepted local
  progress. On the v16.35 downstream rows, it should either replay a closed
  Lean proof from supplied primitive duties or emit the exact missing lemma
  statements required when those duties are absent.
- **Eigenquestion:** Can the current live NS sidecar be reframed as a bounded
  close-or-gap instrument on downstream local atoms, without claiming source
  proof progress?
- **Discriminating test:** Build a solver-0 packet over the v16.35 rows that
  records replayable closure scripts under primitive duties and minimal missing
  lemma statements for the same rows when primitive duties are unavailable.
- **Success criterion:** The packet reports closure only for replayable Lean
  scripts and reports gap statements separately; source-proof progress remains
  zero unless a source obligation is actually closed.
- **Kill condition:** If the packet cannot separate replayable closure from
  missing-lemma reporting, do not use solver language for GP-225.
- **Scope:** GP-225 solver-status gate / live NS close-or-gap inversion.
- **Closure:** v16.36 produced the close-or-gap contract. On the five v16.35
  downstream rows, replayable local closure is available only when primitive
  duties are supplied (`5/5`), source-obligation closure without those duties
  remains `0`, and the packet emits five named missing-lemma/gap statements.
  The maximum honest solver level is `level_2_close_local_subgoal`; GP-225 is
  not yet a source-obligation solver and GNN remains blocked.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1636_live_ns_solver0_close_or_gap_contract.py`,
  `analytics/public/leanmill/results/v1636_live_ns_solver0_close_or_gap_contract.json`,
  `analytics/public/leanmill/results/v1636_live_ns_solver0_close_or_gap_contract.md`.

## H-GP225-GNN-16.37 — Live NS solver-0 closure search canary

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** On the v16.35 downstream rows with primitive duties supplied,
  a target-kind action order should close local Lean goals with fewer failed
  probes than a generic action order. This is a closure metric, not an
  accepted-progress metric.
- **Eigenquestion:** Does the GP-225 target-kind controller reduce probes to
  replayable local closure on live NS downstream atoms, or is generic action
  sweep already enough on this micro-slice?
- **Discriminating test:** Generate one Lean file per row/action attempt for
  five v16.35 downstream rows. Record which attempts replay with no goals, then
  compare generic action order against target-kind order by failed probes before
  first closure.
- **Success criterion:** All five rows have at least one replayable closure
  attempt; target-kind ordering improves mean failed probes over the generic
  action order. This does not imply source-obligation closure.
- **Kill condition:** If generic action order matches target-kind ordering on
  closure probes, the closure harness is valid but GP-225 has no solver-ordering
  signal on this micro-slice.
- **Scope:** GP-225 solver-status gate / replayable closure canary.
- **Closure:** v16.37 ran isolated Lean closure attempts for five v16.35
  downstream rows after fixing an initial temp-module import bug. All five rows
  had at least one replayable closure attempt. Generic action order averaged
  `1.6` failed probes before closure; the GP-225 target-kind order closed on
  the first probe for all five rows (`0.0` failed). This is the first closure
  metric signal, but it is a micro-canary with supplied primitive duties and
  source-obligation closure remains `0`.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1637_live_ns_solver0_closure_search_canary.py`,
  `analytics/public/leanmill/results/v1637_live_ns_solver0_closure_search_canary.json`,
  `analytics/public/leanmill/results/v1637_live_ns_solver0_closure_search_canary.md`.

## H-GP225-GNN-16.38 — Twenty-row solver-0 closure benchmark seed

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The v16.37 closure-ordering signal should survive a broader
  20-row local-proof seed that mixes NS downstream duties, conjunction
  construction/projection, disjunction branch choice, rewrite/normalization,
  arithmetic side conditions, and transport-style wrappers.
- **Eigenquestion:** Does target-kind action ordering reduce failed probes
  before replayable local closure beyond the five-row NS micro-canary, or was
  v16.37 just helper-first overfitting?
- **Discriminating test:** Generate twenty closeable Lean local-proof rows with
  multiple candidate tactics per row. Compile each attempt in isolation,
  identify replayable closures, and compare generic action order against
  target-kind GP-225 order using failed probes before first closure.
- **Success criterion:** At least `20/20` rows have a replayable closure, the
  GP-225 order improves mean failed probes over generic order, and no row
  counts source-obligation closure from assumed source schemas.
- **Kill condition:** If generic action order matches GP-225 ordering, keep the
  closure harness but do not promote solver-ordering claims from this seed.
- **Scope:** GP-225 solver-status gate / 20-row local closure benchmark seed.
- **Closure:** v16.38 ran `20` closeable local proof rows with isolated Lean
  attempts. Rows covered NS downstream/source-duty atoms plus logic,
  normalization, branch-choice, projection, specialization, implication-chain,
  and arithmetic closures. All `20/20` rows had replayable closure attempts.
  Generic action order averaged `1.3` failed probes before closure; GP-225
  target-kind ordering closed first-shot on all rows (`0.0` failed). Source
  obligation closure remains `0`, and the packet is still a closure seed rather
  than solver promotion.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1638_twenty_row_solver0_closure_benchmark_seed.py`,
  `analytics/public/leanmill/results/v1638_twenty_row_solver0_closure_benchmark_seed.json`,
  `analytics/public/leanmill/results/v1638_twenty_row_solver0_closure_benchmark_seed.md`.

## H-GP225-GNN-16.39 — Natural local-closure row inventory

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** Before solver promotion, the generated v16.38 closure seed
  should be replaced by natural local proof rows mined from existing Lean files.
  The fastest next step is to inventory small repository theorem bodies that
  can become replayable closure rows without changing source files.
- **Eigenquestion:** Are there enough natural theorem snippets in the current
  Lean workspace to build the next 20-row closure benchmark, or is a new
  instrument needed to capture tactic states from live proof attempts?
- **Discriminating test:** Scan selected NS and proof-helper Lean files for
  compact theorem bodies using tactics such as `exact`, `constructor`, `rcases`,
  `simpa`, `rw`, `left/right`, and arithmetic tactics. Emit candidate rows with
  file/line, theorem name, proof shape, domain tag, and likely target kind.
- **Success criterion:** Identify at least `20` natural candidate closure rows
  with enough metadata to build v16.40, including at least `8` NS-adjacent rows
  and at least `5` non-NS/control rows.
- **Kill condition:** If compact theorem mining cannot produce enough rows,
  build a tactic-state capture harness instead of expanding generated rows.
- **Scope:** GP-225 solver-status gate / natural closure benchmark preparation.
- **Closure:** v16.39 scanned selected NS and proof-helper Lean files and found
  `39` compact theorem-body candidates. It selected `23` natural rows for the
  next closure benchmark: `15` NS rows and `8` control rows, with target-kind
  mix `branch_choice=6`, `decomposition=5`, `exact_or_helper=3`, and
  `normalization_or_transport=9`. This clears the row-inventory gate for
  v16.40 without needing a new tactic-state capture harness yet.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1639_natural_local_closure_row_inventory.py`,
  `analytics/public/leanmill/results/v1639_natural_local_closure_row_inventory.json`,
  `analytics/public/leanmill/results/v1639_natural_local_closure_row_inventory.md`.

## H-GP225-GNN-16.40 — Natural theorem-body replay feasibility

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The v16.39 selected natural theorem-body rows can be cloned
  into temporary Lean drivers and replayed without editing source files. This
  must be true before any natural closure-policy comparison is meaningful.
- **Eigenquestion:** Can GP-225 mechanically replay natural local proof bodies
  with source-file provenance, or does the next step require a stronger Lean
  tactic-state capture instrument?
- **Discriminating test:** For each selected v16.39 candidate, extract the
  theorem block, rename the theorem, wrap it in the source namespace, import
  the original module, and compile the cloned proof in isolation.
- **Success criterion:** At least `20` natural cloned theorem bodies compile,
  including at least `8` NS rows and `5` control rows.
- **Kill condition:** If cloned replay fails broadly due namespace/import/body
  extraction issues, fix the replay extractor before scoring policies.
- **Scope:** GP-225 solver-status gate / natural closure replay instrument.
- **Closure:** v16.40 initially exposed a replay-instrument gap: cloned control
  rows were missing active `open scoped`/`variable` context, and two smoke-test
  controls were valid source files but not importable as built modules. After
  adding active-context capture, stdout-tail diagnostics, and a source-prefix
  fallback for controls, all `23/23` selected natural theorem-body clones
  compile: `15` NS rows and `8` control rows. This clears the replay feasibility
  gate only; it does not score GP-225 policy ordering and does not justify GNN.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1640_natural_theorem_body_replay_feasibility.py`,
  `analytics/public/leanmill/results/v1640_natural_theorem_body_replay_feasibility.json`,
  `analytics/public/leanmill/results/v1640_natural_theorem_body_replay_feasibility.md`.

## H-GP225-GNN-16.41 — Natural action-family closure policy canary

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** On the v16.40 replayable natural theorem-body rows, a
  target-kind action-family order should close at least some rows with fewer
  failed probes than a generic action-family order, without using the original
  proof body as a counted GP-225 success.
- **Eigenquestion:** Does GP-225 have any natural no-goal-left closure-ordering
  signal once generated helper rows are removed, or does the sidecar need real
  candidate pools before natural policy scoring is meaningful?
- **Discriminating test:** For each v16.40 row, keep `oracle_original_body` as
  extraction validation only, then compile isolated replacement proof attempts
  drawn from a fixed action-family pool (`rfl`, `trivial`, `simp`, `simpa`,
  arithmetic, constructor, branch choice, and `aesop`). Compare generic order
  against target-kind order by first replayable closure and failed probes.
- **Success criterion:** At least `8/23` natural rows close by action-family
  attempts, and target-kind ordering improves mean failed probes over generic
  ordering among closeable rows. Any closure that cites the original theorem is
  invalid.
- **Kill condition:** If few natural rows close under action-family attempts,
  treat this as a candidate-pool/search-tree requirement rather than as a GP-225
  failure or GNN residual.
- **Scope:** GP-225 solver-status gate / natural action-family closure canary.
- **Closure:** v16.41 initially hit an instrument bug (`set_option` before
  `import` made every attempt invalid). After correction, fixed action-family
  replacement attempts closed only `1/23` natural rows: the helper-shaped
  `phase5cg_interior_renormalization_target_shape` closes by `trivial`,
  `simpa`, and `omega`. Generic order reaches that closure after `1` failed
  probe while target-kind order reaches it after `2`; GP-225 improves `0` rows.
  One NS `aesop` closure is marked leakage-risk because the source module is
  imported. The corrected result is still a useful negative: natural theorem
  bodies mostly need candidate-bearing proof steps, dependency extraction, or a
  search tree. This is not a GNN residual.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1641_natural_action_family_closure_policy.py`,
  `analytics/public/leanmill/results/v1641_natural_action_family_closure_policy.json`,
  `analytics/public/leanmill/results/v1641_natural_action_family_closure_policy.md`.

## H-GP225-GNN-16.42 — Natural proof-dependency replay inventory

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The v16.41 action-only weakness is mostly caused by missing
  proof dependencies/prefix context, not by a learned-ranking residual. A
  dependency inventory should separate one-step closures, local projection
  closures, destructuring-prefix rows, rewrite rows, helper-theorem rows, and
  arithmetic/calculus rows.
- **Eigenquestion:** What exact proof-step structure blocks natural closure
  after bare action-family attempts fail?
- **Discriminating test:** For each v16.40 natural row, extract full proof
  lines, global identifier uses, local hypothesis/projection patterns, rewrite
  patterns, destructuring prefixes, and candidate-bearing final steps. Compile
  one-step proof-line attempts where possible, without citing the target theorem.
- **Success criterion:** Produce a row-level dependency taxonomy for all `23`
  natural rows, with at least one of: one-step closure count, prefix-required
  count, helper-theorem count, local-projection count, rewrite count, and
  destructuring count. This is an instrument/inventory gate, not a solver gate.
- **Kill condition:** If dependency extraction cannot distinguish row families,
  build an actual tactic-state capture harness instead of mining theorem bodies.
- **Scope:** GP-225 solver-status gate / natural dependency inventory before
  candidate-bearing closure search.
- **Closure:** v16.42 extracted proof-line dependencies for all `23` natural
  rows and compiled the extracted final proof step in isolation. Final-step
  one-liners close `7/23`; `16/23` require prefix context. `22/23` rows contain
  helper/global identifier uses. Dependency classes: `one_step_branch_or_wrapper=4`,
  `one_step_exact_or_shape=2`, `one_step_local_projection=1`,
  `prefix_destructure_plus_helper=12`, `rewrite_prefix=3`,
  `helper_theorem_chain=1`. This explains the v16.41 action-only weakness:
  natural closure is mostly prefix/dependency-bearing, not bare tactic-family
  selection. GNN remains blocked.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1642_natural_proof_dependency_replay_inventory.py`,
  `analytics/public/leanmill/results/v1642_natural_proof_dependency_replay_inventory.json`,
  `analytics/public/leanmill/results/v1642_natural_proof_dependency_replay_inventory.md`.

## H-GP225-GNN-16.43 — Natural minimal proof-prefix depth

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** Most v16.42 prefix-required natural rows need only a small
  number of context-building proof lines before the original final step closes.
  If true, the next GP-225 solver-0 harness can be a bounded prefix/search
  controller rather than a learned GNN.
- **Eigenquestion:** How deep is the natural local proof-search problem after
  removing one-step closures?
- **Discriminating test:** For each v16.40 natural row, compile theorem clones
  using prefixes of the original proof body from length `1..N`; record the
  minimal prefix length that replays to no-goal-left closure. Treat this as
  oracle depth measurement only, not GP-225 policy success.
- **Success criterion:** Produce minimal prefix depth for all `23` rows and
  report how many close within depths `1`, `2`, `3`, `5`, and full body.
- **Kill condition:** If prefix replay is too slow or unstable, switch to
  tactic-state capture rather than theorem-body prefix mining.
- **Scope:** GP-225 solver-status gate / natural local search-depth measurement.
- **Closure:** v16.43 initially exposed an indentation-preservation bug for
  bullet proofs; after preserving raw proof-line indentation, all `23/23`
  natural rows replay by original proof prefixes. Depth counts: `<=1: 7`,
  `<=2: 8`, `<=3: 9`, `<=5: 14`, `<=8: 16`, `full_or_prefix: 23`,
  `unclosed: 0`; mean minimal prefix depth `8.35`. This is oracle depth
  measurement, not GP-225 policy success. It says the next solver-0 harness
  should target bounded prefix-aware candidate search, with a long-tail for
  control calculus rows.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1643_natural_minimal_proof_prefix_depth.py`,
  `analytics/public/leanmill/results/v1643_natural_minimal_proof_prefix_depth.json`,
  `analytics/public/leanmill/results/v1643_natural_minimal_proof_prefix_depth.md`.

## H-GP225-GNN-16.44 — Natural proof-step trace extractor

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The v16.43 prefix-depth rows can be converted into a compact
  proof-step trace table with action families, dependency identifiers, and
  prefix depth labels. This should be enough to define the next
  candidate-bearing replay baselines without GNN training.
- **Eigenquestion:** What action/dependency vocabulary does the natural
  closure benchmark actually require?
- **Discriminating test:** Extract every proof line in the v16.40 natural rows,
  classify action family (`exact`, `rcases`, `intro`, `rw`, `constructor`,
  branch, arithmetic, simp/simpa, helper-call, other), record identifier
  dependencies, and join row-level minimal prefix depth from v16.43.
- **Success criterion:** Emit a trace table covering all `23` rows with family
  counts, dependency counts, and row-depth buckets.
- **Kill condition:** If trace extraction is too noisy to separate action
  families, candidate-bearing replay should use tactic-state capture instead.
- **Scope:** GP-225 solver-status gate / natural proof-step trace substrate.
- **Closure:** v16.44 extracted `192` proof steps across the `23` natural rows.
  Family counts: `have=42`, `rw=20`, `rcases=14`, `arithmetic=11`,
  `simp_or_simpa=11`, `exact=10`, `branch=9`, `intro=7`, `constructor=5`,
  `structured=6`, `other=57`. It found `107` dependency tokens and row depth
  buckets `one_step=7`, `short_2_3=2`, `medium_4_8=7`, `long_9_plus=7`.
  This is enough trace substrate to define candidate-bearing replay/search
  baselines; it is not solver success and not a GNN trigger.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1644_natural_proof_step_trace_extractor.py`,
  `analytics/public/leanmill/results/v1644_natural_proof_step_trace_extractor.json`,
  `analytics/public/leanmill/results/v1644_natural_proof_step_trace_extractor.md`.

## H-GP225-GNN-16.45 — Natural final-step candidate replay

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** In natural proof states just before the final closing step,
  local-object binding should rank the correct candidate proof line before
  generic inventory order. This is a candidate-bearing closure test of the
  slot-binding intuition, still without training.
- **Eigenquestion:** Does deterministic proof-state local binding reduce failed
  probes before replayable closure on natural final-step candidate pools?
- **Discriminating test:** For each v16.40 natural row, build a theorem clone
  containing the original proof prefix minus the final line. Candidate pool =
  generic trivial closures plus the final proof lines from all `23` natural
  rows. Compare generic order against a local-binding order that ranks candidate
  lines by overlap with theorem binders and prefix-introduced locals. Reject any
  candidate line that cites the target theorem itself.
- **Success criterion:** At least `20/23` rows close from the candidate pool,
  and local-binding order reduces mean failed probes versus generic order.
- **Kill condition:** If local binding does not improve over generic order,
  treat final-step replay as insufficient and move to multi-step search
  instrumentation, not GNN.
- **Scope:** GP-225 solver-status gate / candidate-bearing natural closure replay.
- **Closure:** v16.45 built a final-step candidate pool from generic trivial
  closures plus the final proof lines of all `23` natural rows. All `23/23`
  rows close from the pool. Generic inventory order averages `14.65` failed
  probes before closure; local-binding order averages `2.57` and improves
  `22/23` rows. This is the first natural candidate-bearing closure signal.
  Caveats: the pool is oracle-derived from final proof lines, and two rows close
  using a non-self final line, so the next pass must add harder decoys and avoid
  over-reading row identity. GNN remains blocked.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1645_natural_final_step_candidate_replay.py`,
  `analytics/public/leanmill/results/v1645_natural_final_step_candidate_replay.json`,
  `analytics/public/leanmill/results/v1645_natural_final_step_candidate_replay.md`.

## H-GP225-GNN-16.46 — Parallel harder-decoy final-step replay

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The v16.45 local-binding signal should survive a larger
  proof-line candidate pool that includes same-family non-final proof-line
  decoys, but the effect size should shrink. Parallel row execution should make
  this practical.
- **Eigenquestion:** Does local binding still reduce failed probes when the
  final-step candidate pool is polluted by plausible proof-line decoys?
- **Discriminating test:** Build a candidate pool from generic closures, all
  final proof lines, and sampled non-final proof lines from v16.44 traces.
  First run a no-compile ranking audit after full Lean compilation proved too
  slow under per-driver startup. Compare generic inventory rank to local-binding
  rank with and without a final-line prior.
- **Success criterion:** Local-binding order closes at least `20/23` rows and
  improves mean failed probes versus generic order under the harder pool.
- **Kill condition:** If local binding collapses under same-family proof-line
  decoys, treat v16.45 as oracle-pool overfit and design stronger
  proof-state/action-delta features before any learning discussion.
- **Scope:** GP-225 solver-status gate / parallel hard-decoy final-step replay.
- **Closure:** v16.46 attempted a parallel compile pass, but per-driver Lean
  startup made it too slow. The run was converted to a no-compile hard-decoy
  ranking audit over `129` candidates: generic closures, all final proof lines,
  and same-family non-final proof-line decoys. Result: generic mean rank `15.0`;
  local binding without final-line prior is worse at `17.35`; local binding with
  a final-line prior improves to `8.09`, but that prior is oracle-ish. The
  harder decoys break the clean v16.45 story. The next feature must use
  sequence/action-state context or compile top-k survivors, not GNN.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1646_parallel_harder_decoy_final_step_replay.py`,
  `analytics/public/leanmill/results/v1646_parallel_harder_decoy_final_step_replay.json`,
  `analytics/public/leanmill/results/v1646_parallel_harder_decoy_final_step_replay.md`.

## H-GP225-GNN-16.47 — Sequence-aware hard-decoy final-step ranking

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The v16.46 hard-decoy failure is caused by local-overlap
  overcounting proof lines that mention locals not present in the current prefix
  state. A sequence-aware ranker that penalizes unbound local references should
  recover true final-line ranking without using the oracle final-line prior.
- **Eigenquestion:** Does explicit prefix-state binding repair the same-family
  proof-line decoy failure?
- **Discriminating test:** Reuse the v16.46 `129`-candidate hard pool. Compare
  generic order, local-binding order, and sequence-aware order using true-final
  rank, top-k rates, and a small top-3 Lean compile verification for the
  sequence-aware order.
- **Success criterion:** Sequence-aware ranking improves mean true-final rank
  versus v16.46 local binding without final-line prior and puts at least `15/23`
  true final lines in top-3. Compile verification should close rows when the
  true final line is in the compiled top-k.
- **Kill condition:** If unbound-local penalties do not improve hard-decoy
  ranking, move to actual tactic-state action deltas or persistent Lean search
  rather than adding more static features.
- **Scope:** GP-225 solver-status gate / sequence-aware deterministic hard-decoy
  repair.
- **Closure:** v16.47 reused the v16.46 `129`-candidate hard pool and added
  an unbound-local penalty plus simple sequence-family priors. The result only
  partially repairs v16.46: sequence-aware ranking improves over local binding
  on `12/23` rows, but mean true-final rank is still worse than generic
  (`16.61` vs `15.0`) and top-3 coverage is only `8/23`. The top-3 compile
  check closes those `8` rows. Success gate fails. This blocks a simple static
  sequence-feature claim and points next to real tactic-state/action-delta
  features or persistent Lean top-k search. GNN remains blocked.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1647_sequence_aware_hard_decoy_ranking.py`,
  `analytics/public/leanmill/results/v1647_sequence_aware_hard_decoy_ranking.json`,
  `analytics/public/leanmill/results/v1647_sequence_aware_hard_decoy_ranking.md`.

## H-GP225-GNN-16.48 — Hard-decoy top-1 compile audit

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** Some hard-decoy ranking errors may be harmless if the
  top-ranked wrong proof lines fail to compile in the target prefix state.
  A bounded top-1 compile audit should distinguish ranking failure from actual
  false closure risk.
- **Eigenquestion:** Under the v16.46 hard pool, what do generic, local-binding,
  sequence-aware, and final-prior policies actually close on their first probe?
- **Discriminating test:** Compile only the top-1 candidate for each policy on
  each of the `23` natural rows. Record closure count, true-final closure count,
  wrong-line closure count, and no-closure count.
- **Success criterion:** The audit produces per-policy top-1 closure/false
  closure metrics. This is a diagnostic gate, not a promotion gate.
- **Kill condition:** If wrong top-ranked decoys compile often, hard-decoy
  witness filtering/action deltas become mandatory before any further ranking
  claim.
- **Scope:** GP-225 solver-status gate / hard-decoy compile-risk audit.
- **Closure:** v16.48 compiled only the top-1 candidate under four policies on
  the v16.46 hard pool. Results: generic top-1 closes `0/23`; local binding
  closes `1/23`; sequence-aware closes `2/23`; final-prior binding closes
  `3/23`. Wrong closures are `0` for every policy. Interpretation: hard-decoy
  misranking is currently a probe-efficiency problem, not a false-progress
  problem. But top-1 success is too low for solver claims; next work should
  compile top-k/persistent Lean or add action-delta filtering.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1648_hard_decoy_top1_compile_audit.py`,
  `analytics/public/leanmill/results/v1648_hard_decoy_top1_compile_audit.json`,
  `analytics/public/leanmill/results/v1648_hard_decoy_top1_compile_audit.md`.

## H-GP225-GNN-16.49 — Batched hard-decoy top-k compile audit

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** Batched Lean drivers should make top-k hard-decoy compile
  auditing practical enough to measure closure under budgets without per-driver
  startup dominating the experiment.
- **Eigenquestion:** Under the v16.46 hard pool, how many natural rows close
  within top-k candidates for generic, local-binding, sequence-aware, and
  final-prior policies, and do any wrong decoys close?
- **Discriminating test:** Emit batched Lean files containing theorem clones for
  the top `K` candidates per row/policy. Compile chunks and parse Lean errors to
  record per-attempt success/failure. Report success@1/3/5, first closure probe,
  true-final closure, and wrong closure.
- **Success criterion:** Produce top-k closure metrics for all `23` rows with
  zero or audited wrong closures. This is an execution-substrate gate, not a
  GNN gate.
- **Kill condition:** If batched theorem drivers still bottleneck, switch to
  Lean meta `runTactic'` or Pantograph rather than more per-file probing.
- **Scope:** GP-225 solver-status gate / batched hard-decoy compile audit.
- **Closure:** v16.49 succeeded as an execution substrate and failed as a
  solver-style closure signal. Batched row drivers produced marker evidence on
  all `23/23` rows. Every policy closed `23/23` rows by top-5, but clean
  provenance splits show heavy contamination: generic first closures included
  only `1` true-final closure, `14` non-self final-line closures, and `8` clean
  non-final generic closures; local binding first closures included `1`
  true-final closure and `20` wrong/same-source/non-self closures; sequence
  first closures included `2` true-final closures and `15` wrong closures. The
  audit therefore changes the unit again: raw theorem-clone compilation is too
  permissive, and future closure metrics must separate true-final oracle,
  non-self final-line, same-source non-final, target-name citation, and clean
  non-final closures. GNN remains blocked.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1649_batched_hard_decoy_topk_compile_audit.py`,
  `analytics/public/leanmill/results/v1649_batched_hard_decoy_topk_compile_audit.json`,
  `analytics/public/leanmill/results/v1649_batched_hard_decoy_topk_compile_audit.md`,
  `scripts/public/models/gnn_lemma_relevance/v1650_oracle_leakage_audit.py`,
  `analytics/public/leanmill/results/v1650_oracle_leakage_audit.json`,
  `analytics/public/leanmill/results/v1650_oracle_leakage_audit.md`.

## H-GP225-GNN-16.51 — Terminal-consumption top-k compile audit

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The v16.50 terminal-consumption ranker improves the
  true-final proof-line position in the hard same-family pool by demoting
  setup/opening lines, but that offline rank signal must survive Lean
  compilation and provenance filtering.
- **Eigenquestion:** Under top-k batched Lean compilation, does
  terminal-consumption ordering increase true-final closure or clean accepted
  closure relative to v16.49 generic/local/sequence policies without increasing
  wrong/non-self/same-source closure?
- **Discriminating test:** Add terminal-consumption ordering to the v16.49
  batched driver over the same `23` natural rows and `129` hard-pool
  candidates. Report top-1/top-3/top-5, first compiled closure, first
  true-final compiled closure, first clean non-final closure, and wrong
  provenance classes.
- **Success criterion:** Terminal-consumption improves true-final top-k closure
  versus v16.49 sequence and does not increase first-closure wrong-provenance
  rate. This is a CPU-router refinement gate, not a GNN gate.
- **Kill condition:** If terminal-consumption still mainly promotes non-self
  final lines or same-source non-final lines, move to stricter goal-shape/action
  delta acceptance rather than more static ranking features.
- **Scope:** GP-225 solver-status gate / terminal-consumption compile audit.
- **Closure:** v16.51 confirms terminal-consumption is a real deterministic
  routing improvement but not a clean solver signal. Against the v16.49
  top-k compile policies, terminal-consumption raises true-final top-5 closure
  from sequence `11/23` to `15/23` and top-1 from `2/23` to `7/23`; mean first
  true-final probe improves from `1.45` to `0.93`. However, first compiled
  closure is still wrong/provenance-contaminated on `16/23` terminal rows
  (`21/23` for sequence, `22/23` for generic). This means the policy improves
  oracle replay ranking while leaving deployment cleanliness unresolved. Next
  gate: remove final lines, same-source lines, target-name citations, and
  generic tactics from the pool before compile.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1651_terminal_topk_compile_audit.py`,
  `analytics/public/leanmill/results/v1651_terminal_topk_compile_audit.json`,
  `analytics/public/leanmill/results/v1651_terminal_topk_compile_audit.md`,
  `scripts/public/models/gnn_lemma_relevance/v1650_terminal_consumption_hard_decoy_ranker.py`,
  `analytics/public/leanmill/results/v1650_terminal_consumption_hard_decoy_ranker.json`,
  `analytics/public/leanmill/results/v1650_terminal_consumption_hard_decoy_ranker.md`.

## H-GP225-GNN-16.52 — Quarantined clean-replay top-k gate

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** Once oracle/provenance-contaminated proof lines are removed
  before ranking, clean transferable closure will be much harder; any remaining
  top-k closure is stronger evidence for a reusable local repair sidecar than
  v16.49/v16.51 raw compilation.
- **Eigenquestion:** With final lines, same-source proof-body lines, generic
  tactics, and target-name citations quarantined, how often do generic,
  sequence, and terminal-consumption policies find a clean non-self proof line
  that closes the local target within top-5?
- **Discriminating test:** Filter the v16.46 hard pool per target to exclude
  final-line candidates, candidates sourced from the same target proof, generic
  tactics, and target-name citations. Run batched top-5 Lean compilation for
  generic, sequence, and terminal-consumption ordering. Report clean first
  success@1/3/5 and marker coverage.
- **Success criterion:** Any nontrivial clean closure signal is useful, but
  promotion requires terminal-consumption to beat generic/sequence on
  clean-first success without marker gaps. This is still a CPU-router gate.
- **Kill condition:** If clean quarantined closure is near zero, stop treating
  proof-line replay as solver progress and pivot to real candidate-action
  proof-state search/action deltas.
- **Scope:** GP-225 solver-status gate / clean replay quarantine.
- **Closure:** v16.52 is closed as an instrumentation/target-unit failure, not
  as a clean positive. The numeric output looked strong (`23/23` clean closures
  for sequence and terminal-consumption), but generated drivers show partial
  proof-line fragments such as `have ... :=`, truncated `rw [show ...`, and
  bullet fragments immediately followed by `#check` markers. Those fragments
  can poison parsing and make theorem-clone compilation an invalid proxy for
  local repair. This kills the proof-line replay lane as a solver metric. The
  next unit must be live proof-state candidate-action transitions where Lean
  executes `exact/apply/rw/simp/convert` against a current goal and reports
  before/after snapshots.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1652_quarantined_clean_replay_topk.py`,
  `analytics/public/leanmill/results/v1652_quarantined_clean_replay_topk.json`,
  `analytics/public/leanmill/results/v1652_quarantined_clean_replay_topk.md`.

## H-GP225-GNN-16.53 — Candidate-action proof-state transition pivot

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** The proof-line replay lane failed because it ranked copied
  script fragments, not candidate-action repairs. A stricter Lean-side harness
  that replays a valid proof prefix, then executes candidate-bearing actions
  against the active goal, should provide the first honest natural proof-state
  transition labels.
- **Eigenquestion:** On the `23` natural rows, do global dependency candidates
  such as helper theorems, constructors, rewrite lemmas, and Mathlib lemmas
  produce closed or strictly changed proof states when used through bounded
  actions after the original valid prefix?
- **Discriminating test:** For each selected theorem, replay the original proof
  prefix before the final line inside Lean, snapshot the resulting active
  goal(s), then try candidate-bearing actions
  `exact/apply/rw/rw_rev/simp_only/convert` over dependency-derived global
  candidates. Report candidate-action closed, strict-progress, failures, and
  first-progress probe counts.
- **Success criterion:** Produce marker-backed natural candidate-action labels
  with zero proof-line replay fragments. Any nontrivial candidate-bearing
  strict-progress/closure signal is useful; this is an instrument-repair gate.
- **Kill condition:** If global dependency candidates produce no strict
  progress, shift to local-hypothesis actions and multi-step subgoal search
  rather than proof-line replay.
- **Scope:** GP-225 solver-status gate / natural proof-state action deltas.
- **Closure:** v16.53 repaired the v16.52 target-unit failure by probing actual
  candidate-bearing actions after valid proof prefixes. After fixing namespace
  resolution and simple multi-line prefix serialization, the driver emitted
  `1152` Lean probe markers over `3312` planned candidate-action attempts.
  Results: `8/23` rows show strict proof-state change, `0/23` close, success
  within `25` probes on all progressing rows, mean first-progress probe
  `14.5`; progress actions are `apply_tac` (`5`) and `convert_using1` (`3`).
  Marker coverage remains partial (`1152/3312` in the final run) because many
  richer prefixes still fail to parse as tactic quotations, so this is an
  instrument foothold rather than a benchmark verdict. It does restore the
  action-delta lane after proof-line replay was killed. GNN remains blocked.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1653_candidate_action_proof_state_search.py`,
  `analytics/public/leanmill/results/v1653_candidate_action_proof_state_search.json`,
  `analytics/public/leanmill/results/v1653_candidate_action_proof_state_search.md`.

## H-GP225-GNN-16.54 — Target-aware progress filter audit

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** Some v16.53 strict-progress markers are generic constructor
  or broad-convert pseudo-progress rather than repair progress from useful
  candidate declarations. A target-aware offline audit should separate accepted
  repair transitions from generic Or-constructor narrowing and Sort/metavariable
  convert explosions.
- **Eigenquestion:** How many v16.53 strict-progress transitions remain after
  rejecting generic constructors (`Or.inl`/`Or.inr`) and broad convert side-goal
  explosions?
- **Discriminating test:** Reclassify v16.53 probes without rerunning Lean.
  Accepted progress requires strict proof-state change, candidate not in a
  generic constructor set, no Sort side-goals, and no broad convert explosion.
- **Success criterion:** Produce accepted-vs-pseudo progress counts and update
  the next gate. This is a filter audit, not a promotion gate.
- **Kill condition:** If all progress is pseudo-progress, v16.55 must target
  richer candidate pools/local hypotheses rather than action scheduling.
- **Scope:** GP-225 solver-status gate / target-aware progress filter.
- **Closure:** v16.54 reclassified the v16.53 strict-progress markers and found
  `0/23` rows with accepted candidate progress after target-aware filtering.
  The `8/23` v16.53 progress rows were explained by `Or.inr`/`Or.inl` generic
  constructor narrowing and broad `convert` schema gaps such as unrelated
  `Iff` goals against `Complex.norm_exp`. Class counts over `1152` probes:
  `1030` no-progress, `26` generic-constructor progress, `32` Sort side-goal
  explosions, and `64` convert schema gaps. This kills the naive
  candidate-action signal too. Next step must improve row/candidate construction:
  local hypotheses, target-kind branch compatibility, and real helper theorem
  candidates, not GNN.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1654_target_aware_progress_filter_audit.py`,
  `analytics/public/leanmill/results/v1654_target_aware_progress_filter_audit.json`,
  `analytics/public/leanmill/results/v1654_target_aware_progress_filter_audit.md`.

## H-GP225-GNN-16.55 — Local-hypothesis branch/action repair probe

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** v16.54 rejected global-candidate pseudo-progress because the
  relevant repair for several natural rows is local: use a visible hypothesis
  through the correct constructor/action path. Enumerating local hypotheses
  after the valid prefix should produce real closures on branch/exact rows
  without replaying proof-line fragments.
- **Eigenquestion:** Can local-hypothesis actions (`exact h`, `apply h`, and
  `Or` constructor paths around `h`) close or target-aware-progress natural
  proof states where global dependency candidates failed?
- **Discriminating test:** For each of the `23` natural rows, replay the prefix,
  enumerate local declarations in the active goal context, and run bounded
  local actions. Report closures/progress, first closure probe, action family,
  local hypothesis used, and prefix marker coverage.
- **Success criterion:** Any marker-backed local-hypothesis closure is a valid
  solver-harness improvement. A strong pass is closure on the branch-choice
  rows without broad convert/schema artifacts.
- **Kill condition:** If local-hypothesis actions fail due to prefix/context
  extraction, repair the tactic-state harness; if they run but do not close
  branch rows, inspect goal/local binder naming before adding model complexity.
- **Scope:** GP-225 solver-status gate / local proof-state actions.
- **Closure:** v16.55 enumerated visible local hypotheses after valid prefixes
  and ran local exact/apply/branch actions. It produced `624` probe markers,
  raw closure on `5/23` rows, and raw strict progress on `6/23` rows. All raw
  closures use `or_inl` with local `S : InteriorRenormSeq`, closing branch-like
  targets within `10` probes. This is a real harness improvement over v16.54,
  but it is not yet an accepted repair result: the closure branch may not match
  the intended proof branch, so v16.56 must filter by branch path and original
  final-line local usage before promotion.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1655_local_hypothesis_action_probe.py`,
  `analytics/public/leanmill/results/v1655_local_hypothesis_action_probe.json`,
  `analytics/public/leanmill/results/v1655_local_hypothesis_action_probe.md`.

## H-GP225-GNN-16.56 — Branch-path compatibility filter

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** v16.55 raw local closures may be legal Lean closures but
  wrong-branch repairs. Comparing local-hypothesis branch actions against the
  original final proof line should separate target-compatible local repairs
  from semantically different branch closures.
- **Eigenquestion:** How many v16.55 local-hypothesis closures remain when the
  action path and local hypothesis must match the original final proof line's
  branch constructor path and consumed local?
- **Discriminating test:** Offline audit v16.55 against v16.44 trace lines.
  Extract branch path from original final line (`Or.inl`, `Or.inr(Or.inl)`,
  etc.) and consumed local names, then accept only v16.55 closures matching
  that path/local evidence.
- **Success criterion:** Produce target-compatible local closure counts. If the
  count drops to zero, local action generation must be branch-aware rather than
  raw closure-oriented.
- **Kill condition:** If branch-compatible closures are zero, do not count
  v16.55 as solver progress; build v16.57 branch-aware local action ordering.
- **Scope:** GP-225 solver-status gate / target-aware local closures.
- **Closure:** v16.56 audited v16.55's `5` raw local-hypothesis closures
  against original final-line branch paths and consumed locals. Accepted
  branch-compatible closures dropped to `0/23`: closure classes were
  `wrong_branch_path=3`, `closed_non_branch_row=1`, and `wrong_local=1`. This
  kills v16.55 as solver progress and confirms the exact next move:
  branch-aware local action generation with target-compatible path/local
  checks, not raw closure acceptance.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1656_branch_path_compatibility_filter.py`,
  `analytics/public/leanmill/results/v1656_branch_path_compatibility_filter.json`,
  `analytics/public/leanmill/results/v1656_branch_path_compatibility_filter.md`.

## H-GP225-GNN-16.57 — Branch-aware local action ordering

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** v16.55 failed the target-aware closure gate because it chose
  the first branch that Lean could close. A branch-aware local action generator
  that constructs only the intended `Or` path and local-hypothesis use should
  recover accepted closures if the needed local facts are present after the
  valid prefix.
- **Eigenquestion:** When local hypotheses are restricted to the expected
  branch path and consumed local evidence, how many natural rows close or expose
  target-compatible progress under a bounded probe budget?
- **Discriminating test:** Replay valid prefixes, enumerate local hypotheses,
  but schedule branch constructors from the expected target path before generic
  `exact/apply`. Filter all closures through the v16.56 compatibility predicate.
- **Success criterion:** Any nonzero branch-compatible closure is a real
  repair-harness improvement over v16.56. Strong pass: recover branch rows
  without accepting `S : InteriorRenormSeq` wrong-branch closures.
- **Kill condition:** If branch-aware local actions still yield zero compatible
  closures, the next bottleneck is prefix/subgoal construction or helper
  theorem synthesis, not action ordering and not GNN.
- **Scope:** GP-225 solver-status gate / target-aware local closure search.
- **Closure:** v16.57 found and fixed the key v16.55 harness bug: local
  candidate-action probes were not independent, so an early successful
  wrong-branch probe could assign the active metavariable and make later
  branch-compatible probes fail with `No goals to be solved`. The corrected
  independent, branch-aware probe produced `624` markers over `23` natural
  rows, `5/23` branch-compatible closures, and `6/23` branch-compatible
  progress rows, all within `10` probes. Closures are exactly the expected
  branch/local rows: boundary artifact, full interior dichotomy, interior
  candidate, angular instability, and profile gap. This restores a real
  local-solver signal, but it is still one-step branch/local closure, not a
  general solver and not GNN evidence.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1657_independent_branch_aware_local_probe.py`,
  `analytics/public/leanmill/results/v1657_independent_branch_aware_local_probe.json`,
  `analytics/public/leanmill/results/v1657_independent_branch_aware_local_probe.md`.

## H-GP225-GNN-17.0 — Natural prefix-aware local solver-0 replay

- **Opened:** 2026-05-12
- **Status:** `closed`
- **Hypothesis:** A solver-0 benchmark should count only replayable local
  closure or precise gap exposure. The v16.57 branch/local closure signal
  should compile as concrete Lean proof snippets when appended to the natural
  prefix, while non-closed rows should expose which action family/candidate
  source is missing.
- **Eigenquestion:** On the existing `23` natural theorem-body rows, how many
  local goals can GP-225 close with generated proof snippets from non-oracle
  local hypotheses, and which remaining rows require helper/global candidates
  or gap mining?
- **Discriminating test:** For each v16.57 compatible closure, synthesize the
  final tactic line (`exact h`, `exact Or.inr (Or.inl h)`, etc.), append it to
  the original prefix, rename the theorem clone, and compile from scratch. For
  non-closed rows, record the first compatible progress/gap snapshot.
- **Success criterion:** Compile-verified replay for the `5` v16.57 branch
  closures, zero wrong-branch closures, and a row-level gap table for the
  remaining `18` rows. This is a solver-0 harness gate, not a GNN gate.
- **Kill condition:** If v16.57 closed rows do not replay as concrete proof
  snippets, treat the MetaM probe as insufficient and repair proof-script
  assembly before building a search tree.
- **Scope:** GP-225 solver-status gate / closure-or-gap contract.
- **Closure:** v17.0 synthesized concrete final tactics for the v16.57
  compatible closures and replayed them as renamed theorem clones from scratch.
  All `5/5` compatible closures compile; closed-goal rate is `5/23`, all
  within `10` probes, with mean first closed probe `0.0`. Remaining rows split
  into `17` no-compatible-local-transition gaps and `1`
  compatible-progress-no-closure gap. This promotes the v16.57 signal from
  MetaM closure to replayable solver-0 closure, while keeping the scope narrow:
  branch/local closures only.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1700_natural_prefix_aware_local_solver.py`,
  `analytics/public/leanmill/results/v1700_natural_prefix_aware_local_solver.json`,
  `analytics/public/leanmill/results/v1700_natural_prefix_aware_local_solver.md`.

## H-GP225-GNN-17.1 — Richer local-action solver inventory

- **Opened:** 2026-05-12
- **Status:** `open`
- **Hypothesis:** Many v17.0 gaps are not global theorem gaps; they need
  deterministic local actions that v16.57 did not try: projections (`h.2`,
  nested `.2.2.2`), `simpa using h`, direct application of local implications,
  and small local pair/existential constructors.
- **Eigenquestion:** How many of the `18` v17.0 unclosed natural rows close
  when the local solver tries a richer non-oracle inventory over visible local
  hypotheses and projections?
- **Discriminating test:** Replay natural prefixes, enumerate local hypotheses,
  generate bounded local action templates (`exact h`, projections, branch
  wrappers around projections, `simpa using h`, `apply h`, small pair/exist
  constructors from locals), then compile verified proof snippets from scratch.
- **Success criterion:** Increase compile-verified closed rows beyond `5/23`
  without oracle final-line candidates or same-source future proof fragments.
- **Kill condition:** If richer local actions do not improve closure, the
  remaining gap is helper/global candidate search and gap mining rather than
  local action inventory.
- **Scope:** GP-225 solver-status gate / local action inventory before helper
  theorem search.
- **Closure:** v17.1 raised replay-verified primary closures from `5/23` to
  `15/23` on the natural theorem-body packet, with `10` new primary closures
  after v17.0. All `15` primary closures landed by budget `10` and compile from
  scratch as renamed theorem clones. Source split: `5` v17.0 branch-local
  replays, `8` row-local deterministic seeds, and `2` generated local
  expressions. Remaining rows split into `6` oracle-only final-line upper-bound
  rows and `2` no-local-inventory rows. This confirms that much of the v17.0
  residual was deterministic local action inventory, not GNN capacity.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1701_richer_local_action_inventory.py`,
  `analytics/public/leanmill/results/v1701_richer_local_action_inventory.json`,
  `analytics/public/leanmill/results/v1701_richer_local_action_inventory.md`.

## H-GP225-GNN-17.2 — Site-aware local solver loop

- **Opened:** 2026-05-12
- **Status:** `open`
- **Hypothesis:** The `6` v17.1 oracle-only rows are not primarily candidate
  representation failures; they require tactic-site insertion inside nested
  branch/constructor/proof blocks and a search tree over active goals, rather
  than appending one final tactic to a flat prefix.
- **Eigenquestion:** How many v17.1 oracle-only rows become replay-verified
  primary closures when the solver inserts actions at the correct focused goal
  site and continues through generated subgoals, without using final-line
  oracle candidates as deployable evidence?
- **Discriminating test:** Build a site-aware replay harness over the v17.1
  gap rows. Use prefix checkpoints / branch bullets / active-goal metadata,
  try the same deterministic local action inventory at the focused site, replay
  the assembled script from scratch, and record whether closure required
  helper/global candidates or merely correct site placement.
- **Success criterion:** Close at least `3/6` v17.1 oracle-only rows as primary
  replay-verified solver closures with no final-line transplant and no
  same-source future proof fragment.
- **Kill condition:** If site-aware insertion does not close oracle-only rows,
  promote the residual to helper/global candidate-source search and gap mining.
- **Scope:** GP-225 solver-status gate / closed-loop local solver before public
  candidate-source baselines and before any learning.

## H-GP225-GNN-17.3 — Helper/global template replay on v17.1 gaps

- **Opened:** 2026-05-12
- **Status:** `open`
- **Hypothesis:** Some of the `8` v17.1 gaps close from non-oracle helper/global
  candidates extracted from visible prefix/header/accessibility evidence, but a
  flat final-tactic append will not solve most site-sensitive branch rows.
- **Eigenquestion:** Does the v17.2 helper/global candidate source produce any
  new replay-verified closures on v17.1 gaps without final-line oracle leakage?
- **Discriminating test:** For the `8` v17.1 unclosed rows, flatten
  `top_candidates[].templates` from v17.2, append each tactic after the natural
  prefix under a fixed budget, compile renamed theorem clones in parallel, and
  record first closure if any.
- **Success criterion:** At least `1` new primary replay-verified closure from
  non-oracle helper/global templates; all counted closures must compile from
  scratch.
- **Kill condition:** If no new closures appear, the next bottleneck is
  site-aware insertion/search-tree execution, not candidate-source breadth.
- **Scope:** GP-225 helper/global candidate-source falsifier before persistent
  proof-state server integration.
- **Closure:** v17.3 fed non-oracle v17.2 helper/global templates into the `8`
  v17.1 unclosed rows and replay-compiled renamed theorem clones in parallel.
  Result: `0/8` compile-verified closures under the tightened flat final-tactic
  replay budget. This kills helper/global candidate breadth as the immediate
  explanation for the v17.1 residual.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1703_helper_template_replay_on_gaps.py`,
  `analytics/public/leanmill/results/v1703_helper_template_replay_on_gaps.json`,
  `analytics/public/leanmill/results/v1703_helper_template_replay_on_gaps.md`.

## H-GP225-GNN-17.4 — Persistent state/site adapter feasibility

- **Opened:** 2026-05-12
- **Status:** `open`
- **Hypothesis:** The next speed and closure bottleneck is the lack of a
  persistent proof-state/site executor. Recompiling theorem clones per probe is
  too slow, and flat final-tactic insertion cannot target nested focused goals.
- **Eigenquestion:** Can we build a minimal GP-225 local adapter that exposes
  state IDs, goal IDs, tactic execution at a selected goal site, before/after
  snapshots, and final replay, without vendoring a public system wholesale?
- **Discriminating test:** Prototype an adapter plan or thin harness borrowing
  LeanDojo/PyPantograph mechanics: persistent Lean state, `run_tac`/goal tactic
  calls, goal-site selection, state deletion/caching, and replay-compile
  verification. Apply it first to one v17.1 oracle-only row.
- **Success criterion:** One oracle-only row gets a site-aware candidate action
  tested at the correct focused goal site and either closes by replay or yields
  structured before/after goal evidence that explains the site mismatch.
- **Kill condition:** If persistent/site execution cannot be built cheaply in
  the current Lean substrate, continue with script-level branch insertion
  instead, but do not expand candidate sources further first.
- **Scope:** GP-225 solver-loop substrate / public-repo concept borrowing.
- **Closure:** v17.4 implemented the cheap script-level site-aware insertion
  path first. It generated branch-scoped local candidates from visible prefix
  `rcases`/constructor context and replay-compiled renamed theorem clones.
  Result: `5/6` oracle-only v17.1 rows closed, all by first probe after the
  site-aware seed ordering. The remaining row is a nested exact-tuple body
  (`no_divergent_event_gain_prefix_of_event_price_bridge`) outside one-line
  site insertion. Combined with v17.1, the natural replay packet is now `20/23`
  closed without GNN.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1704_site_aware_branch_insertion.py`,
  `analytics/public/leanmill/results/v1704_site_aware_branch_insertion.json`,
  `analytics/public/leanmill/results/v1704_site_aware_branch_insertion.md`.

## H-GP225-GNN-17.5 — Thin persistent row-driver feasibility

- **Opened:** 2026-05-12
- **Status:** `closed / driver_construction_brittle`
- **Hypothesis:** v17.4 proves site-aware insertion is the right mechanism, but
  per-candidate `lake env lean` replay remains too slow. A thin row-local Lean
  driver that loads prefix context once and probes all site candidates in one
  process should preserve strict replay closure while reducing wall-clock cost.
- **Eigenquestion:** Can one Lean driver per row execute multiple site-aware
  candidate tactics after a natural prefix, emit before/after goal snapshots,
  and then replay-compile the first accepted closure?
- **Discriminating test:** Adapt the `ztareRunCandidateAfterPrefix` / goal
  snapshot patterns from earlier action-delta probes to one v17.4 row and the
  remaining v17.4 gap. Compare marker coverage, runtime, and replay closure
  against the per-candidate clone compiler.
- **Success criterion:** For at least one already-closed v17.4 row, the thin
  driver finds the same accepted site action in one Lean process and final
  replay compilation still succeeds. For the remaining gap, it emits structured
  nonclosure evidence instead of timing out through clone compilation.
- **Kill condition:** If row-local Lean driver construction is brittle, keep
  the replay compiler for closure metrics and move directly to closed-loop
  search/gap mining on the remaining `3` rows.
- **Scope:** GP-225 solver-loop speed/substrate before any learning or GPU.
- **Closure:** v17.5 attempted a thin row-local Lean driver over row `8` and
  row `15`, but generated-driver construction failed before meaningful proof
  probing. The driver compiled `0/2` rows and emitted no valid probe markers;
  failures were in the generated Lean wrapper (`try` syntax and prefix/tactic
  quotation for multi-line nested proof bodies), not in candidate-action search.
  The speed lane is therefore deferred: strict replay compilation remains the
  trustworthy closure metric, and v17.6/v17.7 move to bounded deterministic
  site/gap mining rather than a persistent-driver substrate.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1705_thin_row_driver_probe.py`,
  `analytics/public/leanmill/results/v1705_thin_row_driver_probe.json`,
  `analytics/public/leanmill/results/v1705_thin_row_driver_probe.md`.

## H-GP225-GNN-17.6 — Site-aware extension to non-oracle gaps

- **Opened:** 2026-05-12
- **Status:** `open`
- **Hypothesis:** At least one of the two v17.1 `no_local_inventory_closure`
  rows is actually a site/local-extraction miss, not a helper/global or GNN
  residual. In particular, `example_at_184` exposes unicode locals via
  `obtain`, which v17.1 did not exploit.
- **Eigenquestion:** Does the v17.4 site-aware generator close any of the
  remaining `3` natural gaps (`15`, `16`, `20`) without final-line candidates?
- **Discriminating test:** Run the v17.4 site-aware branch/local insertion
  logic on rows `15`, `16`, and `20`, replay-compile the generated candidate
  actions, and record closures/gaps.
- **Success criterion:** Close at least one remaining row by replay compilation
  without final-line oracle leakage.
- **Kill condition:** If none close, the remaining residual is true nested
  multi-line proof assembly / domain-specific helper search rather than
  site-local extraction.
- **Scope:** GP-225 deterministic solver exhaustion before GNN.
- **Closure:** v17.6 extended the v17.4 site-aware generator to the remaining
  rows `15`, `16`, and `20`. It closed row `16` (`example_at_184`) by generating
  the nested-indentation local action `exact ⟨i₀, hi₀⟩` from visible `obtain`
  locals. Rows `15` and `20` remained bounded nonclosures. Combined with v17.1
  and v17.4, the natural replay packet is now `21/23` closed without GNN.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1706_site_aware_remaining_gaps.py`,
  `analytics/public/leanmill/results/v1706_site_aware_remaining_gaps.json`,
  `analytics/public/leanmill/results/v1706_site_aware_remaining_gaps.md`.

## H-GP225-GNN-17.7 — Two-row gap miner

- **Opened:** 2026-05-12
- **Status:** `closed / deterministic_gap_certificates_and_pull_forward_closure`
- **Hypothesis:** The last two rows (`15`, `20`) are not GNN residuals; they are
  precise proof-assembly/domain-helper gaps: row `15` needs a nested exact tuple
  body, and row `20` needs a structured measure-theory helper application with
  named implicit arguments.
- **Eigenquestion:** Can GP-225 emit precise missing-action/gap certificates for
  the final two rows, including the minimal proof assembly pattern or helper
  theorem schema needed, without claiming closure?
- **Discriminating test:** Produce a two-row gap packet from source prefix,
  original full proof for audit-only comparison, v17.2 candidate sources, and
  v17.4/v17.6 failed probes. The packet must classify the gap and propose the
  next non-oracle mechanism to test.
- **Success criterion:** Both rows get specific gap certificates that a cold
  agent can use to build the next patch without reading chat history.
- **Kill condition:** If the gap packet cannot distinguish proof assembly from
  helper search, stop and build a richer proof-state snapshot extractor first.
- **Scope:** GP-225 solver gap-mining before public baselines and before GNN.
- **Closure:** v17.7 certified both remaining rows as deterministic gaps with
  no GNN-ready residual: row `15` required nested exact tuple-body proof
  assembly, and row `20` required a structured measure-theory helper
  application with named implicit arguments. Per the promoted pull-forward
  primitive, v17.8 immediately tested those mechanisms as replay-compiled
  theorem clones and closed both rows at first probe. Combined natural replay
  closure is now `23/23` by deterministic local-action/site/template mechanisms.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1707_two_row_gap_miner.py`,
  `analytics/public/leanmill/results/v1707_two_row_gap_miner.json`,
  `analytics/public/leanmill/results/v1707_two_row_gap_miner.md`,
  `scripts/public/models/gnn_lemma_relevance/v1708_gap_template_replay.py`,
  `analytics/public/leanmill/results/v1708_gap_template_replay.json`,
  `analytics/public/leanmill/results/v1708_gap_template_replay.md`.

## H-GP225-GNN-17.9 — Natural replay baseline saturation audit

- **Opened:** 2026-05-12
- **Status:** `closed / deterministic_saturation_audit`
- **Hypothesis:** The `23/23` deterministic natural replay closure is useful,
  but not a GNN signal. A mechanism-level baseline audit should show that most
  gains came from explicit executor/template families rather than learned
  candidate ranking.
- **Eigenquestion:** After v17.8, what remains to compare against strong
  BM25/action-sweep/public-source baselines: candidate access, action ordering,
  focused-goal execution, or proof-template assembly?
- **Discriminating test:** Build an audit table from v16.41, v17.0, v17.1,
  v17.4, v17.6, v17.7, and v17.8 artifacts. Report cumulative closure by
  mechanism class and identify rows still requiring public-source candidate
  comparison rather than deterministic executor work.
- **Success criterion:** Produce a cold-readable baseline-saturation packet with
  counts by mechanism and an explicit next discriminator: public/BM25
  candidate-source stress, live NS downstream application, or learned residual
  collection.
- **Kill condition:** If the audit cannot separate generic action closures from
  row-specific deterministic seeds/templates, do not use the `23/23` number in
  GNN gate discussions.
- **Scope:** GP-225 pre-GNN truth gate after deterministic natural replay
  saturation.
- **Closure:** v17.9 produced a row/mechanism audit showing `23/23`
  compile-verified natural replay closures and `0` GNN-ready residual rows.
  Mechanism split: `5` branch-local replays, `8` row-local deterministic
  seeds, `2` generated local expressions, `5` site-aware branch insertions,
  `1` remaining site-aware insertion, `1` tuple-body simpa template, and `1`
  named-implicit helper application. The audit confirms that the current packet
  is deterministic executor/template saturation, not a training signal.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1709_natural_replay_baseline_saturation_audit.py`,
  `analytics/public/leanmill/results/v1709_natural_replay_baseline_saturation_audit.json`,
  `analytics/public/leanmill/results/v1709_natural_replay_baseline_saturation_audit.md`.

## H-ZTARE-PM-01 — Sealed synthetic forecast pool for macro allocation gates

- **Opened:** 2026-05-12
- **Status:** `registered / cli_seeded / pending_pilot`
- **Hypothesis:** A small sealed-batch pool of independent agent forecasts can
  improve macro allocation decisions over a solo RD prediction ledger without
  the overhead and gaming risk of a live LMSR market.
- **Eigenquestion:** Does a synthetic prediction market add calibrated decision
  signal at ZTARE scale, or is the existing prediction ledger plus occasional
  concurring-agent forecast the 90/20 mechanism?
- **Discriminating test:** For the next three macro gates only
  (`GNN launch`, `public-baseline expansion`, `large swarm/GPU spend`), collect
  sealed read-only forecasts from at least three pricing agents before
  execution. Aggregate by median/log-opinion pool; do not expose live prices to
  execution agents. Resolve contracts by predeclared artifact paths, validator
  commands, and metric thresholds.
- **Success criterion:** The forecast pool must change or sharpen at least one
  RD decision, keep added overhead below `15` agent-minutes per contract, and
  resolve all contracts without manual settlement disputes.
- **Kill condition:** If overhead dominates, resolution requires manual
  arbitration, or pricing agents can affect the outcome they bet on, keep
  prediction logging solo/concurring only and do not build LMSR/AMM machinery.
- **Scope:** ZTARE orchestration methodology; applies only to macro gates, not
  per-lemma Lean actions.
- **Current implementation note:** GP-230 now has a conservative file-backed
  CLI and spec for `contract -> sealed forecasts -> aggregate -> resolve ->
  score`. Smoke testing passes in an isolated temporary root. The future
  market-driven theorem-prover scheduler framing remains a promotion path, not
  a current capability claim.
- **Source artifacts:** `research_areas/seams/protocol/GP-230_forecast_pool_decision_market_seam.md`,
  `research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md`,
  `scripts/public/control/forecast/pool.py`.

## H-GP225-GNN-17.10 — BM25/action-sweep baseline saturation gate

- **Opened:** 2026-05-12
- **Status:** `closed / strong_baseline_erases_current_gnn_case`
- **Pre-registration source:** GP-230 contract
  `analytics/public/forecast_pool/contracts/gp225_v1710_bm25_action_sweep_baseline.json`
  was created before the audit run.
- **Hypothesis:** A strong BM25/accessibility + deterministic action-sweep
  baseline will close enough of the saturated 23-row natural replay packet to
  keep GNN blocked.
- **Eigenquestion:** Is the remaining GP-225 advantage a learned route-selector
  signal, or is it mostly deterministic executor coverage once prefix/local,
  site-aware, and template action families are included?
- **Discriminating test:** Build a tiered baseline audit over replay-verified
  artifacts: bare action family, prefix/local action sweep, prefix plus
  site-aware sweep, and strong accessibility/action-sweep including the two
  deterministic gap templates.
- **Success criterion:** Contract success if the strong baseline closes at
  least `20/23` rows or comes within `2x` of GP-225 mean failed probes.
- **Closure:** v17.10 resolved the contract as `success=true`: bare action
  family closes `1/23`; prefix/local action sweep closes `15/23`;
  prefix+site-aware sweep closes `21/23`; strong accessibility/action-sweep
  with the deterministic template builders closes `23/23` with mean failed
  probes `0.9565`, ratio `1.0` against the saturated GP-225 stack. This
  strengthens the no-GNN verdict and reframes GP-225 as a deterministic
  proof-repair sidecar/executor package until public-source/live-NS tests show
  a stable residual.
- **Source artifacts:** `scripts/public/models/gnn_lemma_relevance/v1710_bm25_action_sweep_baseline.py`,
  `analytics/public/leanmill/results/v1710_bm25_action_sweep_baseline.json`,
  `analytics/public/leanmill/results/v1710_bm25_action_sweep_baseline.md`,
  `analytics/public/forecast_pool/contracts/gp225_v1710_bm25_action_sweep_baseline.json`,
  `analytics/public/forecast_pool/aggregates/gp225_v1710_bm25_action_sweep_baseline.json`,
  `analytics/public/forecast_pool/outcomes/gp225_v1710_bm25_action_sweep_baseline.json`,
  `analytics/public/forecast_pool/scores/gp225_v1710_bm25_action_sweep_baseline.json`.

## H-GP225-NS-17.11 — Live NS stepwise commutator branch bridge

- **Opened:** 2026-05-12
- **Status:** `closed / conditional_branch_bridge_compiled`
- **Prediction row:** `PL-178`
- **Hypothesis:** The live NS downstream/gap packet can pull forward an exact
  conditional branch bridge: the already-defined
  `commutatorTowerStepwiseTarget` plus contraction should imply the broad
  `phase5cgBroadProofSearchTarget` along the commutator branch.
- **Eigenquestion:** Can GP-225 sidecar output move from consequence exposure
  to a Lean-checkable conditional branch payment without pretending the
  underlying PDE estimates are paid?
- **Discriminating test:** Add or identify a Lean theorem in the commutator
  tower file whose conclusion is `phase5cgBroadProofSearchTarget ...`, verify
  it with `lake env lean`, then emit an audit packet separating conditional
  branch closure from source-obligation proof.
- **Success criterion:** The bridge compiles and the report states the
  remaining unpaid duties: `commutatorTowerStepwiseTarget` and tower
  contraction.
- **Kill condition:** If this is only an existing direct wrapper or fails to
  compile, do not count it as NS progress; return to gap mining.
- **Scope:** Live NS downstream sidecar utility, not GNN and not source theorem
  closure.
- **Closure:** Added
  `phase5cgBroadProofSearchTarget_of_commutatorTowerStepwiseTarget` to
  `ztare_proofs/ZtareProofs/ns_commutator_tower_stepwise_targets.lean`.
  `lake env lean ZtareProofs/ns_commutator_tower_stepwise_targets.lean`
  passed. v17.11 reports conditional Phase 5CG commutator-branch payment `1`,
  source-obligation closure `0`, and GNN-ready residual rows `0`. The remaining
  unpaid atoms are one-step commutator kernel bounds, radial-grade ratio
  extraction, and tower contraction.
- **Source artifacts:** `ztare_proofs/ZtareProofs/ns_commutator_tower_stepwise_targets.lean`,
  `scripts/public/models/gnn_lemma_relevance/v1711_live_ns_stepwise_branch_bridge.py`,
  `analytics/public/leanmill/results/v1711_live_ns_stepwise_branch_bridge.json`,
  `analytics/public/leanmill/results/v1711_live_ns_stepwise_branch_bridge.md`.

## H-GP225-NS-17.12 — Live NS commutator atom pull-forward swarm

- **Opened:** 2026-05-12
- **Status:** `closed / live_ns_atom_pullforward_compiled`
- **Prediction row:** `PL-179`
- **Hypothesis:** Parallel atom-specific audits can find safe Lean-checkable
  pull-forwards below the stepwise commutator branch without pretending to
  prove the underlying PDE estimates.
- **Eigenquestion:** Are the current live NS commutator atoms true analytic
  blockers, or are some still interface gaps that GP-225 can compress into
  checked adapters?
- **Discriminating test:** Split auditors across
  `commutatorKernelStepBound`, `radialGradeExtractsTowerRatio`, and tower
  contraction; patch only adapters that consume stronger existing hypotheses
  and leave source-obligation closure at `0`.
- **Success criterion:** At least one adapter compiles, and the audit names the
  remaining unpaid analytic atom rather than counting source proof progress.
- **Closure:** v17.12 compiled all touched files and reports five
  pull-forwards/adapters: two kernel-interface adapters, one
  subcritical-budget-to-radial-grade ratio adapter, and two broad-branch
  adapters. Source-obligation closure remains `0`; GNN-ready residual rows
  remain `0`. This is >5x proof-surface/interface acceleration for live NS,
  not >5x PDE progress.
- **Source artifacts:** `ztare_proofs/ZtareProofs/ns_commutator_tower_stepwise_targets.lean`,
  `ztare_proofs/ZtareProofs/ns_commutator_tower_irreducible_estimate.lean`,
  `ztare_proofs/ZtareProofs/ns_commutator_tower_contraction_bridge.lean`,
  `scripts/public/models/gnn_lemma_relevance/v1712_live_ns_atom_pullforward_audit.py`,
  `analytics/public/leanmill/results/v1712_live_ns_atom_pullforward_audit.json`,
  `analytics/public/leanmill/results/v1712_live_ns_atom_pullforward_audit.md`.

## H-GP225-NS-17.13 — Route-1 scalar subcriticality margin split

- **Opened:** 2026-05-12
- **Status:** `closed / strict_margin_split_compiled`
- **Prediction row:** `PL-180`
- **Hypothesis:** The live route-1 scalar hinge can be reduced to a smaller
  Lean-checkable strict-margin certificate without laundering the analytic
  estimate itself.
- **Eigenquestion:** Is `defectBudgetSubcriticalityEstimate` still an opaque
  five-field analytic atom, or can GP-225 split it into explicit positivity and
  strict-margin inequalities that are easier to route downstream?
- **Discriminating test:** Add only a theorem/definition that consumes a
  stronger scalar margin certificate and proves
  `defectBudgetSubcriticalityEstimate`; verify with `lake env lean` and emit a
  cold-readable audit separating guard decomposition from source-obligation
  proof.
- **Success criterion:** The touched Lean file compiles, the audit reports
  source-obligation closure `0`, and the remaining unpaid conditions are named
  as smaller scalar inequalities rather than hidden in the old package.
- **Kill condition:** If the patch merely restates
  `defectBudgetSubcriticalityEstimate` or smuggles `ratio < 1` /
  `budget ≤ ratio * currentStep` without a stricter certificate, record a gap
  only and do not patch.
- **Scope:** Live NS proof-surface reduction; not a GNN residual and not PDE
  estimate closure.
- **Closure:** Added `defectBudgetStrictMarginCertificate` plus checked
  adapters to `defectBudgetSubcriticalityEstimate`,
  `radialGradeExtractsTowerRatio`, and `budgetFacingContractionTarget` in
  `ztare_proofs/ZtareProofs/ns_commutator_tower_irreducible_estimate.lean`.
  `lake env lean ZtareProofs/ns_commutator_tower_irreducible_estimate.lean`
  passed. v17.13 reports strict margin certificates added `1`, adapters added
  `3`, source-obligation closure `0`, PDE estimate closure `0`, and GNN-ready
  residual rows `0`. The unpaid atom is now explicit: produce `0 < margin`,
  positivity, `ratio + margin <= 1`, and
  `budget + margin <= ratio * currentStep`.
- **Forecast-pool settlement:** Contract
  `gp225_v1713_route1_scalar_subcriticality_margin_split` aggregated three
  forecasts at `p_success = 0.4192`, resolved success, and scored mean Brier
  `0.3388`.
- **Source artifacts:** `ztare_proofs/ZtareProofs/ns_commutator_tower_irreducible_estimate.lean`,
  `scripts/public/models/gnn_lemma_relevance/v1713_route1_scalar_subcriticality_margin_split.py`,
  `analytics/public/leanmill/results/v1713_route1_scalar_subcriticality_margin_split.json`,
  `analytics/public/leanmill/results/v1713_route1_scalar_subcriticality_margin_split.md`,
  `analytics/public/forecast_pool/contracts/gp225_v1713_route1_scalar_subcriticality_margin_split.json`,
  `analytics/public/forecast_pool/aggregates/gp225_v1713_route1_scalar_subcriticality_margin_split.json`,
  `analytics/public/forecast_pool/outcomes/gp225_v1713_route1_scalar_subcriticality_margin_split.json`,
  `analytics/public/forecast_pool/scores/gp225_v1713_route1_scalar_subcriticality_margin_split.json`.

## H-GP225-NS-17.14 — Route-1 strict-margin frontier propagation

- **Opened:** 2026-05-12
- **Status:** `closed / strict_margin_frontier_compiled`
- **Prediction row:** `PL-181`
- **Hypothesis:** The v17.13 strict-margin certificate can be propagated into a
  checked route-1 frontier target, so the parent frontier exposes the smaller
  scalar atom directly instead of hiding it behind
  `defectBudgetSubcriticalityEstimate`.
- **Eigenquestion:** Does the strict-margin split improve the live frontier
  surface, or is it only a local scalar adapter?
- **Discriminating test:** Add a strict-margin route-1 target and adapter to
  `route1ExactNextTarget`; if clean, add a strict-margin constructive-frontier
  variant. Verify with `lake env lean`.
- **Success criterion:** Lean compiles, source-obligation closure remains `0`,
  and the frontier-level unpaid scalar duty is
  `defectBudgetStrictMarginCertificate`.
- **Kill condition:** If parameter/import complexity makes the patch fragile or
  the new target only duplicates existing names without changing the parent
  target surface, record a gap instead.
- **Scope:** Pull-forward/interface propagation only; not source proof closure.
- **Closure:** Added additive strict-margin route targets in
  `ns_commutator_tower_irreducible_estimate.lean` and an additive strict-margin
  constructive frontier in `ns_route1_constructive_frontier.lean`. v17.14 first
  builds `ZtareProofs.ns_commutator_tower_irreducible_estimate` so the imported
  `.olean` is fresh, then checks both Lean files. Metrics: strict-margin route
  targets `1`, route adapters `2`, frontier targets `1`, frontier adapters `1`,
  source-obligation closure `0`, PDE estimate closure `0`, GNN-ready residual
  rows `0`.
- **Source artifacts:** `ztare_proofs/ZtareProofs/ns_commutator_tower_irreducible_estimate.lean`,
  `ztare_proofs/ZtareProofs/ns_route1_constructive_frontier.lean`,
  `scripts/public/models/gnn_lemma_relevance/v1714_route1_strict_margin_frontier_propagation.py`,
  `analytics/public/leanmill/results/v1714_route1_strict_margin_frontier_propagation.json`,
  `analytics/public/leanmill/results/v1714_route1_strict_margin_frontier_propagation.md`.

## H-GP225-NS-17.15 — Strict-margin production audit

- **Opened:** 2026-05-12
- **Status:** `closed / strict_margin_gap_certified`
- **Prediction row:** `PL-182`
- **Hypothesis:** Existing pressure-tail/coercivity/budget data either produce
  `defectBudgetStrictMarginCertificate` through a checked non-laundering
  adapter, or the certificate should be recorded as the exact missing analytic
  atom.
- **Eigenquestion:** Did v17.13/v17.14 expose a payably connected scalar atom,
  or just name the frontier's true unpaid inequality?
- **Discriminating test:** Search tail/coercivity/budget surfaces for stronger
  hypotheses that imply the strict certificate. Patch only if the theorem
  consumes more than a restatement of the certificate; otherwise emit a gap
  certificate naming failed candidates and the exact missing statement.
- **Success criterion:** Either a Lean-checked non-laundering adapter to
  `defectBudgetStrictMarginCertificate`, or a cold-readable gap artifact with
  source-obligation closure `0`.
- **Kill condition:** If the only patch is another direct wrapper around the
  same `ratio + margin <= 1` and
  `budget + margin <= ratio * currentStep` inequalities, do not count it as
  progress.
- **Scope:** Live NS scalar atom audit; not GNN, not source proof closure.
- **Closure:** Added route2/open-obligation exposures:
  `route2ReopensRoute1WithStrictMargin`,
  `route2ReopensRoute1_of_strictMargin`, and
  `route1StrictMarginOpenObligation`. v17.15 builds the dependent route1
  module and checks `ns_global_tail_coercivity_bridge.lean` plus
  `ns_exact_open_obligations.lean`. Metrics: route2 strict-margin exposures
  `1`, open-obligation strict-margin exposures `1`,
  real margin-production adapters found `0`, source-obligation closure `0`,
  PDE estimate closure `0`, GNN-ready residual rows `0`.
- **Gap:** Tail/coercivity margin is `penalty + margin <= tailDecay`; route-1
  budget margin requires `ratio + budgetMargin <= 1` and
  `budget + budgetMargin <= ratio * currentStep`. Existing files provide no
  checked bridge between those channels.
- **Source artifacts:** `ztare_proofs/ZtareProofs/ns_global_tail_coercivity_bridge.lean`,
  `ztare_proofs/ZtareProofs/ns_exact_open_obligations.lean`,
  `scripts/public/models/gnn_lemma_relevance/v1715_strict_margin_production_gap_audit.py`,
  `analytics/public/leanmill/results/v1715_strict_margin_production_gap_audit.json`,
  `analytics/public/leanmill/results/v1715_strict_margin_production_gap_audit.md`.

## H-GP225-NS-17.16 — Tail-margin laundering falsifier

- **Opened:** 2026-05-12
- **Status:** `closed / tail_margin_laundering_falsifier_compiled`
- **Prediction row:** `PL-183`
- **Hypothesis:** A concrete scalar counterexample can be Lean-checked showing
  that global tail/coercivity margin does not imply
  `defectBudgetStrictMarginCertificate`.
- **Eigenquestion:** Can the v17.15 anti-laundering gap be promoted from prose
  to a regression theorem?
- **Discriminating test:** Add an existential theorem with explicit witnesses
  satisfying `ns_global_tail_coercivity_bridge` while falsifying
  `defectBudgetStrictMarginCertificate`; verify with `lake env lean`.
- **Success criterion:** Lean compiles the falsifier theorem and no source
  proof progress is counted.
- **Kill condition:** If Lean arithmetic or import noise makes the theorem
  slower than the value of the regression test, emit a Python/scalar artifact
  and defer formalization.
- **Scope:** Anti-laundering guard, not route-1 proof progress.
- **Closure:** Added
  `globalTailCoercivityBridge_does_not_imply_strictBudgetMargin` to
  `ns_global_tail_coercivity_bridge.lean`. The theorem provides explicit scalar
  witnesses satisfying `ns_global_tail_coercivity_bridge` while falsifying
  `defectBudgetStrictMarginCertificate`. `lake env lean` on the file passed.
  v17.16 reports tail-margin laundering blocked `true`, source-obligation
  closure `0`, PDE estimate closure `0`, and GNN-ready residual rows `0`.
- **Source artifacts:** `ztare_proofs/ZtareProofs/ns_global_tail_coercivity_bridge.lean`,
  `scripts/public/models/gnn_lemma_relevance/v1716_tail_margin_laundering_falsifier.py`,
  `analytics/public/leanmill/results/v1716_tail_margin_laundering_falsifier.json`,
  `analytics/public/leanmill/results/v1716_tail_margin_laundering_falsifier.md`.

## H-EG-20260523-01 — Cue-stripped obligation routing and action-contract payment

- **Hypothesis:** The useful machine-facing layer for research-process language is the coarse obligation spine (`construct`, `transfer`, `bound`, `decompose`), but it should be treated as top-k/multi-label; action contracts should improve concrete owed-artifact payment more than label menus on cue-stripped near-confuser cases.
- **Eigenquestion:** Are the pattern/primitive surfaces helping because they name a category, or because they force the next owed artifact/check after the category is selected?
- **Discriminating test:** Build a cue-stripped near-confuser packet with paired research situations across the four obligation classes. Run a subscription-runtime solver with tools disabled by prompt and read-only sandbox. Score (1) source-only class routing top-1/top-2 and (2) downstream obligation payment for source-only, label-menu, and action-contract arms under a blind mapper.
- **Success criterion:** Coarse top-2 routing is materially above lexical/control routing, and action-contract paid rate exceeds source-only and label-menu by at least 20 percentage points without hidden-key leakage.
- **Kill condition:** Source-only or label-menu ceilings, action contracts fail to beat labels, or mapper rationales show they are using surface labels rather than owed artifact fields.
- **Scope:** Epistemic-generation pattern/primitive/router science; downstream RD use only if the finding survives this and a later independent-human or cross-runtime check.
- **Status:** `closed / schema_binding_positive_semantic_ceiling`
- **Opened:** 2026-05-23
- **Closed:** 2026-05-23
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/cue_stripped_obligation_router_probe_20260523/`
- **Result:** Coarse router top-1 beat lexical control (`1.0` vs `0.625`), but top-2 tied lexical control (`0.75` vs `0.75`). Blind-mapper payment ceilinged across `source_only`, `label_menu`, and `action_contract`. Strict deterministic rescore showed exact schema-token binding only in `action_contract` (`8/8` vs `0/8` and `0/8`), while semantic-alias field recovery was `8/8` in all arms.
- **Interpretation:** The success criterion fails for downstream semantic payment because source-only and label-menu arms ceiling. The useful positive is narrower: action contracts force exact machine-readable receipt fields. Next valid test should neutralize field names and test no-menu obligation construction rather than label recovery.
- **Artifacts:** `run/score_20260523.json`; `run/strict_field_rescore_20260523.json`; `run/strict_field_scored_rows_20260523.jsonl`.


## H-EG-20260523-02 — No-menu pattern obligation endpoint

- **Hypothesis:** Pattern and anti-pattern surfaces should be evaluated as next-artifact/blocked-wrong-move constructors, not as 31-way label recovery. If the action-contract layer is doing useful work, it should improve exact receipt-field payment over source-only and label-hint arms on no-menu pattern/anti-pattern cases.
- **Eigenquestion:** Do RD pattern/anti-pattern surfaces help because the pattern names are recognized, or because they force concrete receipt fields and repair/stop rules?
- **Discriminating test:** Build an eight-family no-menu packet spanning prior-overlap, local-work-before-terminal, source verification, spec-freeze, claim-scope boundary, swarm decomposition, numeric/tool grounding, and object-identity guards. Run a subscription-runtime solver with tools disabled by prompt and read-only sandbox across `source_only`, `label_hint`, and `action_contract` arms. Score hidden family payment by blind mapper and exact contract-field coverage deterministically.
- **Success criterion:** `action_contract` improves hidden-family paid rate or contract-field pass rate by at least 20 percentage points over both controls without source-only ceiling. A source-only ceiling demotes the packet to a surface-design failure.
- **Kill condition:** Source-only or label-hint arms ceiling, contract fields merely echo semantically obvious source wording, or mapper rationales show family decisions driven by visible labels rather than constructed artifacts/checks.
- **Scope:** Epistemic-generation pattern/anti-pattern/router science; no RD code change unless the result separates an actionable mechanism.
- **Status:** `closed / source_only_ceiling_packet_too_easy`
- **Opened:** 2026-05-23
- **Closed:** 2026-05-23
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/no_menu_pattern_obligation_endpoint_20260523/`
- **Result:** All arms ceilinged: `source_only=8/8`, `label_hint=8/8`, `action_contract=8/8` on hidden-family payment and exact contract-field pass. Inspection shows source-only outputs reconstructed the exact hidden field names.
- **Interpretation:** The success criterion fails. This is a packet-design failure: the vignettes made the owed artifact too semantically obvious. Next valid test requires paired near-confuser contracts, including a wrong-contract arm.


## H-EG-20260523-03 — Paired-confuser pattern contract causality

- **Hypothesis:** If action contracts carry causal force for pattern/anti-pattern use, expected contracts should route/pay the expected next artifact while adjacent wrong contracts should route/pay the confuser or fail; source-only and two-label-menu arms should not ceiling on paired near-confuser cases.
- **Eigenquestion:** Are action-contract fields selecting the next research obligation under ambiguity, or are source vignettes still making the answer obvious?
- **Discriminating test:** Build paired near-confuser cases where each source surface supports two plausible pattern/anti-pattern families. Run four arms: `source_only`, `two_label_menu`, `expected_contract`, and `confuser_contract`. Score expected-family payment, wrong-family payment, and exact field coverage.
- **Success criterion:** Expected-contract paid rate exceeds source-only and two-label-menu by at least 20 percentage points, and confuser-contract outputs map to the confuser family or fail expected payment on most rows.
- **Kill condition:** Source-only ceilings, two-label menu ceilings, or confuser contracts still pay the expected family despite wrong receipt fields.
- **Scope:** Epistemic-generation pattern/action-contract science; no RD code change unless this separates expected vs confuser contracts.
- **Status:** `closed / confuser_contract_active_steering_source_ceiling`
- **Opened:** 2026-05-23
- **Closed:** 2026-05-23
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/paired_confuser_pattern_contract_20260523/`
- **Result:** `source_only`, `two_label_menu`, and `expected_contract` all paid expected family `6/6`; `confuser_contract` paid expected family `0/6` and confuser family `6/6`.
- **Interpretation:** The success criterion fails on source-only ceiling, but the confuser-contract intervention is informative: wrong receipt fields actively steer the output to the wrong family. RD action contracts need explicit source-contract alignment before accepting routed receipt fields.
- **Code impact:** Added `source_contract_alignment_check` to `routed_operator_receipt_gate` in `src/ztare/research_director/pattern_action_contract.py`; focused tests pass.


## H-EG-20260523-04 — Source-contract alignment auditability

- **Hypothesis:** Since paired-confuser pattern contracts show wrong receipt fields can steer outputs to the wrong obligation, the useful next RD mechanism is an auditability check: a blind auditor should detect whether a constructed receipt aligns with source facts without seeing the hidden expected/confuser key.
- **Eigenquestion:** Is `source_contract_alignment_check` an operationally checkable guard, or just another field name that sounds disciplined?
- **Discriminating test:** Reuse the completed paired-confuser outputs. Hide arm labels and hidden family keys. Give a subscription-runtime auditor only the source situation and constructed owed artifact/check. Ask whether the receipt aligns with source facts, names any conflict, and says accept/repair/stop. Score aligned=true for `source_only`, `two_label_menu`, and `expected_contract`; aligned=false for `confuser_contract`.
- **Success criterion:** Alignment auditor accuracy at least `0.80` overall and at least `0.80` false-contract rejection on `confuser_contract` rows.
- **Kill condition:** Auditor accepts most confuser-contract rows, or rejects many aligned rows, showing the new RD field is not reliably auditable from source/output alone.
- **Scope:** RD pattern/action-contract guard validation; no new vocabulary promotion.
- **Status:** `closed / alignment_auditable_with_spec_claim_boundary_confuser`
- **Opened:** 2026-05-23
- **Closed:** 2026-05-23
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/source_contract_alignment_audit_20260523/`
- **Result:** Blind alignment audit scored overall accuracy `23/24 = 0.9583`; confuser-contract rejection `5/6 = 0.8333`. All source-only, two-label-menu, and expected-contract rows were accepted as aligned.
- **Interpretation:** Success criterion passes. `source_contract_alignment_check` is auditable on this packet, but one confuser remains: claim-boundary receipt fields can look source-aligned on a post-result metric/spec-freeze case because `success_criterion` and `pass_fail_boundary` overlap semantically with measurement-rule locking.
- **Artifacts:** `run/score_20260523.json`; `run/scored_rows_20260523.jsonl`; `run/auditor_outputs_20260523.jsonl`.


## H-EG-20260523-05 — Spec-freeze vs claim-boundary timing disambiguator

- **Hypothesis:** The source-contract alignment miss in H-EG-20260523-04 is caused by shared success-criterion/pass-fail language. Adding explicit timing fields (`criteria_frozen_before_results`, `result_visibility_state`, `post_result_change_check`) should make spec-freeze receipts auditable against claim-boundary confusers.
- **Eigenquestion:** Can the RD distinguish post-result measurement-rule drift from legitimate broad/narrow claim scoping by source-visible timing evidence, or is this still a semantic blur?
- **Discriminating test:** Build deterministic receipt templates over paired source situations: post-result metric/spec-freeze cases and broad/narrow claim-boundary cases. Hide family keys. Ask a subscription-runtime auditor to decide source alignment for timing-spec receipts, claim-boundary receipts, and ambiguous shared success-boundary receipts.
- **Success criterion:** Overall alignment accuracy at least `0.80`, spec cases reject claim-boundary confusers at least `0.75`, and claim-boundary cases reject timing/spec-freeze confusers at least `0.75`.
- **Kill condition:** Auditor accepts most opposite-family receipts, showing timing fields are not enough to separate the residual.
- **Scope:** Narrow RD disambiguator validation; no new primitive or pattern promotion.
- **Status:** `closed / timing_fields_separate_ambiguous_boundary_too_weak`
- **Opened:** 2026-05-23
- **Closed:** 2026-05-23
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/spec_freeze_claim_boundary_disambiguator_20260523/`
- **Result:** Overall accuracy `20/24 = 0.8333`; spec-freeze cases rejected claim-boundary confusers `4/4`; claim-boundary cases rejected timing/spec-freeze confusers `4/4`. The ambiguous success/pass-fail receipt was rejected on all rows, including claim-boundary rows.
- **Interpretation:** Success criterion passes for timing-vs-claim separation. Explicit timing fields are a valid disambiguator for post-result criterion drift. Generic success-boundary fields are too weak even for claim-boundary acceptance; use full broad/narrow/answer-object fields.
- **Artifacts:** `run/score_20260523.json`; `run/scored_rows_20260523.jsonl`; `run/auditor_outputs_20260523.jsonl`.


## H-EG-20260523-06 — Pattern deployment replay-readiness audit

- **Hypothesis:** The existing pattern-deployment ledger may be sufficient for deployment coverage and menu drift audits, but insufficient for the broader retrospective decision-replay experiment because it likely lacks pre-decision state and a gold next-action label.
- **Eigenquestion:** Can we test the orchestration menu as a policy/router from existing historical ledgers, or do we first need to build a proper replay packet?
- **Discriminating test:** Deterministically audit `analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl` and related v128 pattern audit artifacts for fields required by replay: pre-state/situation text, available action set, chosen action, outcome, cost/failure mode, and linkable source artifact.
- **Success criterion:** At least `40` rows contain enough source-visible state and action/outcome fields to create a no-model replay packet without chat reconstruction.
- **Kill condition:** Ledger rows mostly contain pattern IDs/outcomes but not reconstructable pre-state or gold policy action; then the next work is packet construction/annotation, not replay scoring.
- **Scope:** Broad pattern/orchestration research design; no model calls.
- **Status:** `closed / existing_ledger_not_replay_ready`
- **Opened:** 2026-05-23
- **Closed:** 2026-05-23
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_replay_readiness_20260523/`
- **Result:** `96` ledger rows audited; replay-ready rows `0`; available-action-set field rate `0.0`; linked F-row rate `0.0`; loose pre-decision-state proxy `0.4062`; outcome/failure field `0.6458`; chosen-action/pattern field `0.9896`.
- **Interpretation:** Success criterion fails. Existing pattern-deployment ledger is useful for deployment coverage/drift, but not for retrospective policy replay. It can stratify candidate cases; a proper replay packet must be built with pre-state, action alphabet, gold next action, outcome/cost, and source artifact refs.
- **Artifacts:** `score_20260523.json`; `scored_rows_20260523.jsonl`.

## H-EG-20260523-07 — Pattern replay source-locator audit

- **Date:** 2026-05-23
- **Status:** closed / source_locator_pass_packet_extraction_owed
- **Eigenquestion:** after the pattern replay-readiness failure, can existing repository artifacts reconstruct enough pre-decision context for a fair menu-policy replay packet, or must the packet be hand-authored from selected cases?
- **Hypothesis:** source context will be recoverable for at least 12 diverse pattern deployment rows by searching task IDs and distinctive notes across repo artifacts, enough to draft a first replay packet skeleton.
- **Discriminating test:** run a deterministic source-locator over `pattern_deployment_ledger.jsonl`; count rows with primary pattern, outcome, and at least one non-self/non-dashboard local artifact hit for task ID or distinctive note terms. Also report pattern diversity among recoverable rows.
- **Success criterion:** at least 12 recoverable rows and at least 4 primary-pattern families. Otherwise, automated replay-packet mining fails and the next step is manual packet construction from selected cases.
- **Result:** PASS. Strong-context recoverable rows: 95/96; recoverable primary-pattern families: 11; selected 12-row skeleton emitted.
- **Interpretation:** existing artifacts are sufficient to select and begin extracting replay cases, but not sufficient to score them automatically. The next work is manual/structured extraction of pre-decision state, available action set, utility key, and blind relay task.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_replay_source_locator_20260523/`

## H-EG-20260523-08 — Pattern replay source-quality selector

- **Date:** 2026-05-23
- **Status:** closed / automated_sampling_failed_direct_pilot_next
- **Eigenquestion:** can the source-locator output yield a high-quality replay skeleton with direct project/seam artifacts, or is the apparent context supply mostly ledger echo?
- **Hypothesis:** at least 12 rows across at least 4 primary-pattern families have direct project/seam/workingpaper source context, enough to build a first replay packet without relying on ledger-only echoes.
- **Discriminating test:** score each recovered row by context tier: A = direct project/seam/source artifact, B = substantive workingpaper/research-log source, C = ledger-only. Select a 12-row balanced skeleton with at most 2 rows per pattern and report tier mix.
- **Success criterion:** 12 selected rows, at least 4 primary-pattern families, and at least 8 tier-A/B rows. Otherwise the next packet must be hand-selected manually rather than produced by automated sampling.
- **Result:** FAIL. Direct-artifact rows: 7/96; selected 12-row skeleton had 7 families but only 5 strong rows and 7 ledger-only rows.
- **Interpretation:** the apparent 95/96 source-context supply mostly reflects ledger echo. The next valid replay packet is a small direct-artifact pilot or manual extraction, not automated 12-row sampling.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_replay_source_quality_20260523/`

## H-EG-20260523-09 — Direct-artifact replay excerpt sufficiency pilot

- **Date:** 2026-05-23
- **Status:** closed / small_direct_pilot_authorable_but_skewed
- **Eigenquestion:** among the direct-artifact rows surfaced by H-08, do the source documents contain enough pre-decision material to author blind relay replay cases without inventing context?
- **Hypothesis:** at least 4 direct-artifact rows will yield usable source excerpts that include a research state, a decision pressure, and an outcome/failure cue, enough for a small pilot packet.
- **Discriminating test:** extract bounded excerpts around note tokens from direct source refs only; score each row for `has_state`, `has_decision_pressure`, `has_outcome_or_failure`, and `has_nonledger_source_ref`.
- **Success criterion:** at least 4 rows pass all four fields. Otherwise the replay-packet plan must switch from automated extraction to deliberate manual case authoring.
- **Result:** PASS for a small pilot: 5/7 direct rows passed excerpt sufficiency. Pattern coverage is skewed: PATTERN-001 = 3, PATTERN-002 = 2.
- **Interpretation:** a small relay-mechanics pilot is authorable, but it cannot answer the full orchestration-menu question across pattern families. Excerpts also contain outcome leakage and need redaction before solver use.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_replay_excerpt_sufficiency_20260523/`

## H-EG-20260523-10 — Direct replay deterministic redaction gate

- **Date:** 2026-05-23
- **Status:** closed / deterministic_redaction_failed_manual_authoring_required
- **Eigenquestion:** can the 5 direct-artifact replay candidates be transformed into solver-visible pre-decision states by deterministic redaction, or do they require hand authoring?
- **Hypothesis:** deterministic sentence-level redaction can remove hidden pattern/outcome cues while preserving state and decision-pressure terms for at least 4 of 5 candidates.
- **Discriminating test:** redact pattern IDs, agent/verdict/result/outcome/build/pass/fail/catch terms, and observed-event cues from excerpts; score residual leakage and retained state/pressure terms.
- **Success criterion:** at least 4 candidates have no residual leakage and retain both state and decision-pressure cues. Otherwise model-facing replay must be manually authored from source docs.
- **Result:** FAIL. Redaction pass: 3/5, below threshold 4; surviving candidates skew PATTERN-001=2, PATTERN-002=1.
- **Interpretation:** do not run model-facing replay on automatically extracted snippets. The next valid unit is manual authoring of solver-visible pre-decision states plus hidden gold policies/relay tasks from source docs.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_replay_redaction_gate_20260523/`

## H-EG-20260523-11 — Hand-authored pattern replay blind-relay pilot packet

- **Date:** 2026-05-23
- **Status:** closed / packet_quality_pass
- **Eigenquestion:** can a small source-faithful hand-authored replay packet represent real pattern/orchestration decisions without strawman vignettes or hidden outcome leakage?
- **Hypothesis:** four direct-artifact historical cases can be authored with solver-visible pre-decision state, plausible action set, hidden gold policy, utility key, and blind relay task while passing deterministic leakage/quality checks.
- **Discriminating test:** author 3-5 cases from direct source documents; run a linter for hidden pattern/outcome leakage, nonempty action set, plausible confusers, source refs, gold policy, utility key, and relay task.
- **Success criterion:** at least 3 cases pass all quality checks, with no visible pattern IDs or outcome verdict tokens and at least two distinct gold actions.
- **Result:** PASS. Authored 4 cases; linter pass 4/4; gold actions cover 2 actions (`run_tool`, `verify_source`); no visible pattern/event leakage.
- **Interpretation:** a source-faithful small relay pilot is now available. It is intentionally not broad enough for pattern-family claims.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_replay_hand_authored_pilot_20260523/`

## H-EG-20260523-12 — Hand-authored pattern replay source-only vs menu-policy pilot

- **Date:** 2026-05-23
- **Status:** closed / no_menu_gain_mechanics_pilot
- **Eigenquestion:** on the hand-authored direct-artifact replay pilot, does a compact workflow-policy menu improve first-step process action selection versus source-only reasoning?
- **Hypothesis:** menu-policy will improve exact gold action and relay-artifact sufficiency on this small packet, but interpretation is mechanics-only because the packet is skewed toward source-verification cases.
- **Discriminating test:** run two no-tool subscription-agent arms over the four hand-authored cases: `source_only` and `menu_policy`. Require JSON with selected action, relay artifact, and confuser rejection. Score exact gold action plus minimal relay artifact completeness.
- **Success criterion:** menu-policy has higher exact-action accuracy than source-only and does not reduce relay completeness. If both ceiling, the packet is too easy for action selection and should be used only to test relay mechanics.
- **Result:** strict exact-action accuracy: source-only `4/4`, menu-policy `3/4`; relay completeness `4/4` both arms. Posthoc permissive sensitivity treats menu's `freeze_spec` on the campaign-accounting case as defensible, giving `4/4` both arms.
- **Interpretation:** no menu-policy gain on this pilot. Source-only reasoning was already strong; the menu may slightly over-select procedure-setting on evaluation-boundary cases. Treat as a mechanics/null result, not a broad negative.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_replay_hand_authored_pilot_20260523/`

## H-EG-20260523-13 — Balanced pattern replay policy packet

- **Date:** 2026-05-23
- **Status:** closed / balanced_packet_ceiling
- **Eigenquestion:** can a harder hand-authored replay packet create real action-selection headroom across multiple process actions, rather than ceilinging source-only reasoning?
- **Hypothesis:** a five-case packet balanced across `verify_source`, `run_tool`, `dispatch`, `freeze_spec`, and `repair` will pass leakage/quality checks and reduce source-only exact-action accuracy below 1.0.
- **Discriminating test:** author five source-derived cases with one gold action per target class; validate no visible pattern/outcome leakage, plausible confusers, source refs, utility keys, and relay tasks; then run source-only vs menu-policy with the existing no-tool subscription-agent harness.
- **Success criterion:** packet linter passes 5/5; source-only exact-action accuracy is below 1.0; menu-policy improves strict accuracy or relay completeness without increasing over-prescription. If both arms ceiling, the packet is still too obvious.
- **Result:** packet linter passed `5/5` with five distinct gold actions. Source-only and menu-policy both scored strict exact-action accuracy `5/5` and relay completeness `5/5`.
- **Interpretation:** the balanced action-label packet is still too easy. Clean hand-authored states let vanilla reasoning map to the right process action without menu help.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_replay_balanced_policy_pilot_20260523/`

## H-EG-20260523-14 — Balanced replay utility-slot scorer

- **Date:** 2026-05-23
- **Status:** closed / no_relay_field_gain
- **Eigenquestion:** when action labels ceiling on the balanced replay packet, does the workflow-policy menu improve the downstream relay artifact fields that a next worker needs?
- **Hypothesis:** menu-policy will improve utility-slot coverage versus source-only because the menu names action-specific artifact obligations, even when both arms choose the same action.
- **Discriminating test:** score the already-captured H-EG-20260523-13 solver outputs against case-specific utility slots derived from the hidden utility keys; report per-case slot coverage and by-arm mean coverage.
- **Success criterion:** menu-policy improves mean slot coverage by at least 0.10 with no loss in exact action accuracy. If both arms are within 0.10, the current menu adds no measurable relay-field gain on this packet.
- **Result:** source-only mean utility-slot score `1.00`; menu-policy `0.95`; both exact-action accuracy `1.00`.
- **Interpretation:** no measured relay-field gain. The current menu did not improve the downstream artifact fields on this packet.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_replay_balanced_policy_pilot_20260523/`

## H-EG-20260523-15 — Confuser-embedded replay policy packet

- **Date:** 2026-05-23
- **Status:** closed / confuser_packet_ceiling
- **Eigenquestion:** does the workflow-policy menu help when the visible state contains a realistic cue toward the wrong process action?
- **Hypothesis:** source-only reasoning will make at least one strict action error on a five-case confuser packet, while menu-policy will improve or preserve action accuracy by checking the stated decision criterion against the confuser.
- **Discriminating test:** derive five confuser-embedded cases from the balanced packet by adding a realistic but wrong next-action temptation to each visible state; validate leakage/source quality; run source-only vs menu-policy with the same no-tool subscription-agent harness.
- **Success criterion:** packet linter passes 5/5; menu-policy strict accuracy exceeds source-only, or source-only drops below 1.0 while menu remains 1.0. If both arms ceiling again, the menu has no measured advantage even under shallow confuser pressure.
- **Result:** packet linter passed `5/5`; source-only and menu-policy both scored strict exact-action accuracy `5/5` and relay completeness `5/5`.
- **Interpretation:** no menu advantage under shallow confuser pressure. Stop testing menu value as first-step action-label selection on short hand-authored states; the next useful endpoint is execution quality, long-horizon workflow, or weaker/noisier operators.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_replay_confuser_policy_pilot_20260523/`

## H-EG-20260524-01 — Pattern contract execution-artifact endpoint

- **Date:** 2026-05-24
- **Status:** closed / field_gain_action_metric_confounded
- **Eigenquestion:** if action labels ceiling, does the RD pattern-action contract improve the executable artifact fields a downstream worker receives?
- **Hypothesis:** contract-schema prompting will improve deterministic required-field coverage versus vanilla artifact prompting on cases routed through `pattern_action_contract.py`, without reducing selected-action correctness.
- **Discriminating test:** build four source-derived cases whose goals trigger distinct contract surfaces; run two no-tool Codex subscription arms, `vanilla_artifact` and `contract_schema`; score exact action plus required field coverage from the actual contract carriers.
- **Success criterion:** contract-schema mean required-field coverage exceeds vanilla by at least `0.20` while exact action accuracy remains no worse. If both arms ceiling, execution-artifact prompts are still too easy; if contract improves fields, RD should keep surfacing action-contract schemas as an artifact compiler, not as a router proof.
- **Result:** required-field coverage improved sharply (`0.3195` vanilla to `0.9688` contract, delta `+0.6493`), but selected-action accuracy fell because the contract arm often selected `dispatch` for downstream-worker handoff while packet golds were mostly `repair`.
- **Interpretation:** directional evidence for schema-as-artifact-compiler, but the action metric is confounded by prompt framing. A field-only follow-up is required before turning this into a decision.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_contract_execution_artifact_20260524/`

## H-EG-20260524-02 — Pattern contract artifact-only endpoint

- **Date:** 2026-05-24
- **Status:** closed / contract_schema_field_gain
- **Eigenquestion:** with action selection removed, does the RD pattern-action contract improve executable artifact required-field coverage?
- **Hypothesis:** contract-schema prompting will improve mean required-field coverage by at least `0.20` versus vanilla artifact prompting on the same four source-derived contract cases.
- **Discriminating test:** rerun the H-EG-20260524-01 packet with no `selected_action` field in the solver output; both arms must produce `artifact_slot`, `artifact_fields`, `rejected_confuser`, and `relay_note`; score only required-field coverage and relay/confuser presence.
- **Success criterion:** contract-schema mean required-field coverage exceeds vanilla by at least `0.20`, and confuser/relay fields are present on all rows. If it passes, the RD pattern contract is supported as an artifact compiler, not as a first-step action router.
- **Result:** contract-schema required-field coverage `1.00`; vanilla `0.2292`; delta `+0.7708`. Artifact-slot accuracy, confuser rejection, and relay note presence were `1.00` for both arms.
- **Interpretation:** positive for schema-as-artifact-compiler. This does not revive first-step action-label/router claims; it says RD should surface required artifact fields when a pattern/anti-pattern contract is selected.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_contract_execution_artifact_20260524/`

## H-EG-20260524-03 — Anti-pattern pre-mortem detector pilot

- **Date:** 2026-05-24
- **Status:** closed / directional_catalog_premortem_gain
- **Eigenquestion:** do anti-pattern catalog surfaces help detect the failure mode before the bad research move happens, compared with generic critique?
- **Hypothesis:** catalog-premortem prompting will improve failure-family identification and preventive-action specificity on four pre-outcome process states.
- **Discriminating test:** build four source-derived pre-outcome vignettes from anti-pattern catalog entries; run no-tool Codex arms `generic_critique` and `catalog_premortem`; score gold anti-pattern family, preventive artifact/gate, and confuser rejection.
- **Success criterion:** catalog-premortem improves gold-family accuracy by at least `0.25` or improves preventive-action coverage by at least `0.25` without losing family accuracy. If both arms ceiling, these vignettes are too obvious; if catalog helps, anti-patterns are supported as pre-mortem detectors.
- **Result:** catalog-premortem scored family accuracy `4/4` and preventive-action accuracy `4/4`; generic critique scored `2/4` and `2/4`. Confuser rejection was present on all rows in both arms.
- **Interpretation:** directional mechanics-positive result for anti-patterns as pre-outcome failure detectors. Generic critique handled obvious pre-spec cases but missed vocabulary-smuggling and tool-underuse family identification.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/anti_pattern_premortem_pilot_20260524/`


## H-EG-20260524-04 - RD schema surface obligation smoke

- **Date:** 2026-05-24
- **Status:** closed / schema_surface_obligation_pass
- **Eigenquestion:** does the RD close-payload surface now turn selected pattern/anti-pattern contracts into enforceable typed receipts, rather than prose placeholders?
- **Hypothesis:** the scaffold will emit `carrier_schema_receipts` for required-field contract carriers, and the close-side research_done gate will reject placeholder schema values while accepting filled, semantically valid receipts.
- **Discriminating test:** generate a claim-boundary/action-contract scaffold from the actual `scaffold_rd_close_payload.py`, inspect emitted schema carriers, run `_research_done_error` on the placeholder payload, then fill the required typed receipts and rerun the gate.
- **Success criterion:** required-field carriers are scaffolded as schema receipts; placeholder payload is rejected; filled payload is accepted. If any leg fails, RD surfacing still has an obligation leak.
- **Result:** passed. Scaffold emitted `claim_boundary_typed_rows` and `routed_operator_receipt_gate` under `carrier_schema_receipts`; the generated placeholder payload was rejected by `_research_done_error`; a filled valid payload was accepted.
- **Interpretation:** RD surfacing should now prefer typed schema receipts for required-field pattern/action and anti-pattern carriers. This closes the immediate prose-placeholder obligation leak; it does not prove naturalistic RD behavior improves.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/rd_schema_surface_obligation_smoke_20260524/`


## H-EG-20260524-06 - Live memory-vs-menu recurrence test

- **Date:** 2026-05-24
- **Status:** closed / live_no_increment_packet_transparent
- **Eigenquestion:** does the orchestration menu improve live model process decisions only when paired with project memory, rather than as a standalone router?
- **Hypothesis:** `memory_plus_menu` will outperform `project_memory_only` and `menu_only` on correct next action while preserving recurrence avoidance and avoiding false stops on clean proceed rows.
- **Discriminating test:** reuse the eight-row recurrence packet from H-EG-20260524-05; run subscription Codex arms `source_only`, `project_memory_only`, `menu_only`, and `memory_plus_menu`; score exact gold action, recurrence avoidance, false-stop rate, and over-prescription.
- **Success criterion:** `memory_plus_menu` beats `project_memory_only` by at least `0.125` correct-action accuracy, beats `menu_only`, has recurrence avoidance at least as high as memory-only, and has false-stop rate no worse than memory-only. If it fails, keep menu as advisory surfacing only.
- **Result:** failed success criterion. Live Codex scored `source_only=0.75`, `project_memory_only=0.625`, `menu_only=0.75`, `memory_plus_menu=0.75`; all arms had recurrence avoidance `1.00` and false-stop rate `0.00`.
- **Interpretation:** the deterministic memory+menu screen did not transfer to this live packet. Inspection shows source-only inferred many memory/menu-relevant actions from transparent wording, so the next menu test needs cue-stripped rawer states rather than this packet.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/menu_memory_recurrence_live_20260524/`


## H-EG-20260524-07 - Cue-stripped anti-pattern missing-field test

- **Date:** 2026-05-24
- **Status:** closed / catalog_missing_field_gain
- **Eigenquestion:** can anti-pattern catalog context help infer the missing preventive receipt field from compact state records, while letting clean already-paid cases proceed?
- **Hypothesis:** catalog-premortem will improve missing-field and preventive-artifact accuracy versus generic critique without increasing false-stop rate on clean paid rows.
- **Discriminating test:** build paired risky/clean state records for vocabulary-smuggling, criterion timing, tool-underuse, and scientific-amnesia families; remove obvious narrative labels; run subscription Codex arms `generic_critique` and `catalog_premortem`; score block/proceed, family, missing field, preventive artifact, and false stops.
- **Success criterion:** catalog-premortem improves missing-field accuracy by at least `0.25` or family accuracy by at least `0.25`, with false-stop rate no worse than generic. If both arms ceiling, strip cues further or stop this endpoint.
- **Result:** passed. Catalog-premortem scored missing-field accuracy `1.00` vs generic `0.50`, family accuracy `0.50` vs `0.00`, decision accuracy `1.00` in both arms, and false-stop rate `0.00` in both arms.
- **Interpretation:** anti-pattern catalog value survives a cue-stripped missing-field endpoint: it does not merely say block/proceed, it supplies the exact preventive receipt field on risky rows while letting paid clean rows proceed. Artifact accuracy is conservative because clean rows that named the already-paid receipt were not counted as `existing_receipt`.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/anti_pattern_missing_field_cuestripped_20260524/`


## H-EG-20260524-08 - Harder pattern contract downstream consumer execution

- **Date:** 2026-05-24
- **Status:** closed / contract_downstream_execution_gain
- **Eigenquestion:** does a filled pattern/action contract improve downstream worker execution on compact handoff states, beyond vanilla prose summaries?
- **Hypothesis:** contract handoffs will improve work-ready artifact pass rate and required-field coverage versus vanilla handoffs on six compact source-derived cases, without increasing wrong-stop decisions on clean cases.
- **Discriminating test:** build six compact handoff states covering claim-boundary, portable receipt, anti-pattern preventive receipt, menu+memory recurrence, PDE-work-unit gate, and source-contract alignment; run no-tool subscription Codex downstream-worker arms `vanilla_handoff` and `contract_handoff`; score artifact type, required fields, next action, confuser rejection, and false stops.
- **Success criterion:** contract handoff improves pass rate by at least `0.25` or mean required-field coverage by at least `0.20`, with false-stop rate no worse than vanilla. If both arms ceiling, Axis A needs noisier naturalistic traces; if contract wins, keep RD surfacing as downstream execution handoff.
- **Result:** passed. Contract handoff scored pass rate `0.6667` vs vanilla `0.00`, required-field coverage `1.00` vs `0.1444`, artifact accuracy `1.00` vs `0.00`, and confuser rejection `1.00` vs `0.50`; both arms had next-action accuracy `0.6667` and false-stop rate `0.00`.
- **Interpretation:** filled contracts improve downstream executable artifact construction, not next-action choice. Keep surfacing contracts as handoff schemas and consumer checks; do not claim they route better than vanilla reasoning.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_contract_downstream_hard_20260524/`


## H-EG-20260524-09 - Cue-stripped menu plus memory recurrence test

- **Date:** 2026-05-24
- **Status:** closed / no_memory_plus_menu_live_gain
- **Eigenquestion:** does the orchestration menu add value over project memory alone when recurrence cues are not obvious in the current source state?
- **Hypothesis:** `memory_plus_menu` will outperform `project_memory_only` on exact next-action selection for compact recurrence/clean states, because the menu supplies sequencing rules for how to consume memory without overblocking.
- **Discriminating test:** build six cue-stripped current-state records plus separate memory snippets and menu policy snippets; run no-tool subscription Codex arms `source_only`, `project_memory_only`, `menu_only`, and `memory_plus_menu`; score exact action, memory use, false stops on clean rows, and over-dispatch on recurrence rows.
- **Success criterion:** `memory_plus_menu` beats `project_memory_only` by at least `0.167` exact-action accuracy, has recurrence avoidance at least as high, and has false-stop rate no worse. If it fails again, treat menu-memory live improvement as unproven and stop testing short packets.
- **Result:** failed. `memory_plus_menu`, `project_memory_only`, and `menu_only` all scored exact-action accuracy `1.00`, recurrence avoidance `1.00`, and false-stop rate `0.00`; `source_only` dropped to `0.8333` with over-dispatch `0.3333` on recurrence rows.
- **Interpretation:** cue stripping created some source-only recurrence pressure, but did not isolate incremental menu+memory value. Menu-only still inferred enough from the current-state cues. Treat menu-memory live improvement as unproven; stop short hand-authored menu packets unless using naturalistic traces with hidden memory state.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/menu_memory_cuestripped_live_20260524/`


## H-EG-20260524-10 - Second-stage consumer propagation test

- **Date:** 2026-05-24
- **Status:** closed / contract_second_stage_propagation_gain
- **Eigenquestion:** does the pattern/action contract advantage propagate to a separate downstream consumer, or only to direct field scoring of the first worker's artifact?
- **Hypothesis:** a second worker consuming contract-produced artifacts from H-EG-20260524-08 will recover the correct receipt obligations and next action more often than a second worker consuming vanilla-produced artifacts.
- **Discriminating test:** take the actual first-worker outputs from `pattern_contract_downstream_hard_20260524`; hide original source states; ask a fresh no-tool Codex consumer to produce a close/relay payload from each artifact; score required receipt recovery, next-action recovery, confuser preservation, and false stops.
- **Success criterion:** contract-produced artifacts improve second-stage pass rate by at least `0.25` or required-field recovery by at least `0.20`, with false-stop rate no worse than vanilla. If it passes, Axis A has propagation evidence; if it fails, contracts improve direct artifacts but may not survive handoff.
- **Result:** passed. Second-stage consumers of contract artifacts scored pass rate `0.6667`, field recovery `1.00`, artifact recovery `1.00`, and confuser preservation `1.00`; consumers of vanilla artifacts scored pass rate `0.00`, field recovery `0.1444`, artifact recovery `0.00`, and confuser preservation `0.50`. Next-action recovery tied at `0.6667`; false-stop rate was `0.00` in both arms.
- **Interpretation:** the contract advantage propagates through a separate worker artifact for schema/receipt recovery and confuser preservation. It still does not improve next-action choice. Axis A can be treated as a scoped positive for execution handoff propagation, pending naturalistic human/trace validation.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/pattern_contract_second_stage_consumer_20260524/`


## H-EG-20260524-11 - Naturalistic NS contract trace readiness audit

- **Date:** 2026-05-24
- **Status:** closed / ns_trace_ready_for_naturalistic_packet
- **Eigenquestion:** do existing real NS pattern/action contract traces contain enough paired contract-and-receipt evidence to support a naturalistic downstream validation packet?
- **Hypothesis:** the tick668 NS trace has enough paired pattern contracts, operator receipts, work units, and gate artifacts to build at least four naturalistic validation rows without hand-authoring source states.
- **Discriminating test:** deterministically scan `projects/ns_millennium_hunt/workspace/queries` for tick668 pattern-action contracts; for each, find nearby receipt/work-unit/gate artifacts matching required carrier slots; score carrier presence and approximate required-field mention coverage.
- **Success criterion:** at least four contract rows have operator-receipt evidence plus either work-unit/gate evidence or projection/portable receipt evidence, and at least two have a clear nearest-confuser artifact. If it fails, naturalistic validation needs new payload capture rather than mining this trace.
- **Result:** passed. Scanned `10` real NS tick668 pattern contracts; `7` had operator receipt plus work/special-receipt evidence, `4` had confuser artifacts, mean carrier presence was `0.8982`, and mean exact field-token mention coverage was `0.2663`.
- **Interpretation:** existing NS traces are ready for a naturalistic packet, but scoring should target artifact/consequence recovery rather than exact schema-token mentions because the real math artifacts do not consistently use RD schema field names.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/ns_contract_trace_readiness_20260524/`


## H-EG-20260524-12 - Naturalistic NS contract consumer test

- **Date:** 2026-05-24
- **Status:** closed / naturalistic_contract_consumer_gain
- **Eigenquestion:** on real NS trace artifacts, does the pattern/action contract help a downstream consumer recover the correct artifact/consequence structure compared with evidence snippets alone?
- **Hypothesis:** `contract_plus_evidence` will improve required carrier recovery and confuser preservation versus `evidence_only` on selected tick668 naturalistic rows.
- **Discriminating test:** select naturalistic-ready tick668 rows from H-EG-20260524-11; present compact snippets of real receipt/work-unit artifacts to a no-tool Codex consumer, with or without the corresponding pattern-action contract carrier list; score required carrier recovery, problem-surface recovery, confuser preservation, and next-missing-artifact specificity.
- **Success criterion:** `contract_plus_evidence` improves required-carrier recovery by at least `0.20` or pass rate by at least `0.25`, without reducing confuser preservation. If it passes, Axis A has naturalistic trace support; if it fails, synthetic handoff propagation did not transfer to messy traces.
- **Result:** passed. `contract_plus_evidence` scored pass rate `1.00`, carrier-slot recovery `1.00`, surface recovery `1.00`, confuser preservation `1.00`, and missing-artifact specificity `1.00`. `evidence_only` scored pass rate `0.00`, carrier-slot recovery `0.00`, surface recovery `0.00`, confuser preservation `1.00`, and missing-artifact specificity `1.00`.
- **Interpretation:** real NS evidence snippets let the consumer produce meaningful domain summaries and missing-artifact guesses, but not the RD carrier-slot structure. Adding the pattern/action contract preserves coordination structure across messy trace artifacts. This supports contracts as coordination schemas, not as improved mathematical comprehension.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/ns_contract_consumer_naturalistic_20260524/`


## H-EG-20260524-13 - Orchestration menu as state-machine controller

- **Date:** 2026-05-24
- **Status:** closed / no_menu_state_machine_gain
- **Eigenquestion:** is the right orchestration-menu question multi-step state control rather than first-action choice?
- **Hypothesis:** a menu-as-state-machine surface will improve multi-step workflow validity versus source-only reasoning by preserving state transitions, owed checks, and stop/repair conditions across changing observations.
- **Discriminating test:** build a four-case process-control packet with 3-step research traces: memory recurrence, tool-underuse, external-audit promotion, and paid anti-pattern guard. Run no-tool subscription Codex arms `source_only` and `menu_state_machine`; score ordered action chain, transition guards, owed artifact, false stops, and over-dispatch.
- **Success criterion:** `menu_state_machine` improves valid-chain pass rate by at least `0.25` or transition-guard coverage by at least `0.20`, without increasing false stops. If it fails, the menu has no short-packet support even under the corrected process-controller frame.
- **Result:** failed. `menu_state_machine` improved chain coverage from `0.3333` to `0.50` and guard coverage from `0.1666` to `0.25`, but pass rate stayed `0.00`, owed-artifact accuracy stayed `0.25`, and false stops/over-dispatch stayed `0.00` in both arms.
- **Interpretation:** process-controller is the better eigenframe for the menu, but this short packet still does not show causal menu value. Row inspection shows source-only plans were semantically sensible; menu support mostly added explicit state vocabulary. Reopen Axis B only with production traces, hidden state, and downstream cost.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/menu_state_machine_controller_20260524/`

## H-EG-20260524-14 - Naturalistic catch-ledger anti-pattern recovery

- **Date:** 2026-05-24
- **Status:** closed / no_catalog_naturalistic_catch_gain
- **Eigenquestion:** does anti-pattern catalog context improve recovery of the failure family and preventive repair action on naturalistic catch-ledger rows after explicit category labels are hidden?
- **Hypothesis:** catalog-context outputs will recover the gold anti-pattern family and repair/preventive receipt more often than evidence-only outputs, without relying on explicit category labels.
- **Discriminating test:** select eight ratified catch-ledger rows across vocabulary-smuggling, narrative-inflation, citation-laundering, obligation-laundering, and criterion-selection families; strip the structured category and obvious family-name leakage; run no-tool subscription Codex arms `evidence_only` and `catalog_context`; score family recovery, repair specificity, and confuser rejection.
- **Success criterion:** catalog-context improves exact family accuracy by at least `0.25` or repair specificity by at least `0.20`, with no drop in confuser rejection. If it fails, Axis C remains synthetic-positive but not naturalistic-positive for catch recovery.
- **Result:** failed. Catalog context tied evidence-only on family accuracy (`0.875` vs `0.875`), slightly improved repair specificity (`0.45` vs `0.375`), but dropped source-confuser recovery (`0.0` vs `0.4583`), so the pre-registered success condition failed.
- **Interpretation:** naturalistic catch rows are often diagnosable from evidence alone. Catalog context helps name the family, but can pull the confuser answer toward neighboring catalog labels instead of the concrete false source reading. Axis C remains scoped-positive for missing preventive receipts, not naturalistic-positive for catch recovery.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/anti_pattern_catch_ledger_naturalistic_20260524/`

## H-EG-20260524-15 - Orchestration-menu production shadow-controller readiness

- **Date:** 2026-05-24
- **Status:** closed / not_production_shadow_ready
- **Eigenquestion:** do current production/official RD traces contain enough pre-decision state to run the corrected orchestration-menu shadow-controller test?
- **Hypothesis:** the official transition snapshot will not yet contain enough pre-decision candidate-action, hidden-outcome, owed-artifact, and downstream-cost fields for a valid menu-vs-source shadow-controller experiment.
- **Discriminating test:** scan `analytics/public/official_store_snapshot/transitions.stamped.jsonl` for rows with source state, candidate action, pre-decision timestamp or state, hidden adjudicated outcome, owed artifact/receipt, and cost/regret or false-stop/false-proceed signal.
- **Success criterion:** at least `20` rows are shadow-controller-ready, including at least `5` clean proceed and `5` block/repair rows. If it fails, the next B action is instrumentation, not another short-packet solver test.
- **Result:** failed as predicted. Current official snapshot has `131` rows, but `0` shadow-controller-ready rows. Field rates: candidate action `0.0305`, pre-decision marker `0.0687`, owed artifact/receipt `0.1374`, cost/regret signal `0.0382`, hidden outcome `1.0`.
- **Interpretation:** Axis B cannot run the valid production shadow-controller test from current exports. The next action is non-blocking instrumentation fields, not a menu performance claim or another toy packet.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/menu_production_trace_readiness_20260524/`

## H-EG-20260524-16 - Mixed naturalistic anti-pattern preventive-receipt test

- **Date:** 2026-05-24
- **Status:** closed / no_source_confuser_contract_gain
- **Eigenquestion:** after the catch-ledger null, does an anti-pattern contract that explicitly requires source-specific false-reading confusers improve mixed naturalistic repair/proceed decisions versus evidence-only?
- **Hypothesis:** `anti_pattern_contract` will improve missing-or-paid preventive receipt accuracy and source-specific confuser recovery on a mixed packet of real catch failures and real paid/pass transitions, without increasing false stops on clean paid rows.
- **Discriminating test:** build eight naturalistic rows: four ratified catch failures needing repair/demotion and four official pass transitions where the guard was paid or the confuser was rejected. Run no-tool subscription Codex arms `evidence_only` and `anti_pattern_contract`; score decision, receipt, source-specific confuser, and false-stop rate.
- **Success criterion:** contract arm improves receipt accuracy by at least `0.20` or source-confuser accuracy by at least `0.20`, with false-stop rate no worse than evidence-only. If it fails, Axis C stays bounded to cue-stripped preventive-receipt selection only.
- **Result:** failed by ceiling. Evidence-only scored decision accuracy `1.00`, receipt accuracy `1.00`, source-confuser accuracy `1.00`, false-stop rate `0.00`; contract scored decision accuracy `1.00`, receipt accuracy `0.875`, source-confuser accuracy `1.00`, false-stop rate `0.00`.
- **Interpretation:** the source-confuser requirement is still a good guard field, but transparent naturalistic rows do not show incremental model uplift. Axis C should be closed as scoped-positive for preventive-receipt surfacing and reopened only with harder held-out traces.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/anti_pattern_mixed_naturalistic_20260524/`

## H-EG-20260524-17 - Synthetic closed-loop orchestration controller

- **Date:** 2026-05-24
- **Status:** closed / menu_closed_loop_synthetic_gain
- **Eigenquestion:** does orchestration-menu state policy improve actual multi-leg process control when the agent must act step-by-step, receive feedback, and carry state across observations?
- **Hypothesis:** `menu_controller` will reduce cumulative process cost and wrong-action rate versus `source_only` in a synthetic closed-loop RD environment with hidden gold state, delayed observations, paid-guard cases, recurrence cases, tool-underuse cases, and external-audit cases.
- **Discriminating test:** run no-tool subscription Codex over multiple synthetic episodes. At each leg the solver sees only current history and chooses one action from a fixed alphabet; the deterministic environment returns the next observation and logs costs. Compare arms on cumulative cost, per-leg action accuracy, terminal disposition accuracy, false proceed, false stop, and overwork on paid guards.
- **Success criterion:** `menu_controller` reduces mean cumulative cost by at least `20%` or improves per-leg action accuracy by at least `0.15`, without increasing false-stop rate or paid-guard overwork. If it fails, synthetic closed-loop evidence does not support menu performance, and B should wait for production instrumentation.
- **Result:** passed on synthetic closed loop. `menu_controller` reduced mean episode cost from `8.00` to `5.25` (`34.38%` reduction), improved action accuracy from `0.50` to `0.6667`, improved terminal accuracy from `0.375` to `0.625`, reduced false-proceed rate from `0.0556` to `0.00`, and reduced paid-guard overwork from `0.25` to `0.00`.
- **Interpretation:** this is the first positive Axis B result under a real multi-leg setup. The gain is bounded: menu policy helped recurrence and paid/clean guard control, but both arms still over-verified after a PDE work unit and in instrumentation-handoff cases. Synthetic data is not production evidence.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/menu_closed_loop_synthetic_20260524/`

## H-EG-20260524-18 - Synthetic closed-loop anti-pattern intervention

- **Date:** 2026-05-24
- **Status:** closed / anti_pattern_closed_loop_synthetic_gain
- **Axis:** C / anti-patterns
- **Eigenquestion:** do anti-pattern contracts improve multi-leg intervention behavior after feedback, or do they only improve one-shot family/receipt naming?
- **Hypothesis:** `anti_pattern_contract` will reduce cumulative process cost and repeated wrong moves versus `generic_critique` in a synthetic closed-loop RD environment with delayed source feedback, paid-clean receipts, source-specific false readings, and repair-after-feedback states.
- **Discriminating test:** run separate no-tool subscription Codex calls for each decision leg across seven synthetic RD episodes. Each leg exposes an observation and environment feedback from the previous action. Score exact action, terminal action, cumulative cost, repeated-risk rate, false proceed, false stop, paid-clean overwork, receipt naming, and source-confuser coverage.
- **Success criterion:** `anti_pattern_contract` reduces mean episode cost by at least `15%` or improves per-leg action accuracy by at least `0.15`, while not increasing false-stop rate or paid-clean overwork. If it fails, Axis C remains scoped-positive for cue-stripped preventive-receipt naming, not closed-loop intervention.
- **Result:** passed. `anti_pattern_contract` reduced mean episode cost from `8.5714` to `3.5714`, improved per-leg action accuracy from `0.375` to `0.875`, improved terminal accuracy from `0.1429` to `0.7143`, eliminated false proceeds (`0.0625` to `0.0`), eliminated paid-clean overwork (`0.25` to `0.0`), improved receipt accuracy from `0.6875` to `1.0`, and reduced repeated wrong-after-feedback from `1.0` to `0.0`. Source-confuser accuracy tied at `0.8125`.
- **Interpretation:** this is a stateful synthetic positive for anti-patterns as intervention contracts, not just one-shot receipt labels. The gain came from better repair/proceed sequencing and paid-clean handling after feedback; it does not prove production RD uplift.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/anti_pattern_closed_loop_synthetic_20260524/`

## H-EG-20260524-19 - Synthetic menu anti-pattern interaction

- **Date:** 2026-05-24
- **Status:** closed / no_combined_menu_antipattern_incremental_gain
- **Axis:** B/C interaction
- **Eigenquestion:** on the same closed-loop anti-pattern intervention episodes, does the orchestration menu add process-control value beyond the anti-pattern contract, or are they mostly overlapping surfaces?
- **Hypothesis:** `combined_menu_antipattern` will reduce mean episode cost or improve per-leg action accuracy versus `menu_state_policy` and the H18 `anti_pattern_contract` reference, without increasing false stops or paid-clean overwork.
- **Discriminating test:** reuse the H18 seven-episode synthetic closed-loop environment, run new no-tool subscription Codex arms `menu_state_policy` and `combined_menu_antipattern`, and compare against the already-run H18 `generic_critique` and `anti_pattern_contract` references. Score exact action, terminal action, cumulative cost, repeated wrong-after-feedback, false proceed, false stop, paid-clean overwork, receipt naming, and source-confuser coverage.
- **Success criterion:** combined arm improves action accuracy by at least `0.10` or reduces mean cost by at least `10%` versus both `menu_state_policy` and the H18 anti-pattern reference, with no false-stop or paid-clean-overwork increase. If it fails, B and C should remain separate surfaces: menu for process state/instrumentation, anti-pattern contract for failure-family intervention.
- **Result:** failed. `combined_menu_antipattern` beat `menu_state_policy` (`0.8125` vs `0.5625` action accuracy; `4.1429` vs `6.1429` mean cost), but did not beat the H18 `anti_pattern_contract` reference (`0.8125` vs `0.875` action accuracy; `4.1429` vs `3.5714` mean cost). Combined preserved false-stop and paid-clean-overwork safety at `0.0`.
- **Interpretation:** menu state policy helps relative to generic critique on these C-style episodes, but the anti-pattern contract already carries the effective intervention policy. Combining the menu with the contract added some extra over-control after repairs and did not improve the result. Keep B and C as separate surfaces.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/menu_antipattern_interaction_synthetic_20260524/`

## H-EG-20260524-20 - Synthetic anti-pattern contract ablation

- **Date:** 2026-05-24
- **Status:** closed / antipattern_specific_contract_survives_ablation
- **Axis:** C / anti-pattern contract causality
- **Eigenquestion:** did H18 improve because the anti-pattern contract carried the right preventive receipts and paid-clean rules, or would any structured state/checklist contract produce the same closed-loop gain?
- **Hypothesis:** the H18 `anti_pattern_contract` reference will beat both `neutral_state_contract` and `wrong_antipattern_contract` on the same closed-loop episodes. If neutral or wrong contracts match H18, the result is checklist/process-scaffold value rather than anti-pattern-specific value.
- **Discriminating test:** reuse the H18 seven-episode synthetic closed-loop environment, run new no-tool subscription Codex arms `neutral_state_contract` and `wrong_antipattern_contract`, and compare to the H18 `generic_critique` and `anti_pattern_contract` references. Score exact action, terminal action, cumulative cost, repeated wrong-after-feedback, false proceed, false stop, paid-clean overwork, receipt naming, and source-confuser coverage.
- **Success criterion:** H18 `anti_pattern_contract` must beat both ablation arms by at least `0.10` action accuracy or `10%` mean-cost reduction, without worse false-stop or paid-clean-overwork rates. If it fails, Axis C should be narrowed from anti-pattern-specific intervention to generic structured process control.
- **Result:** passed. H18 `anti_pattern_contract` beat `neutral_state_contract` by `+0.4375` action accuracy and `53.70%` mean-cost reduction, and beat `wrong_antipattern_contract` by `+0.6875` action accuracy and `69.14%` mean-cost reduction. Correct contract also kept false stops and paid-clean overwork at `0.0`; wrong contract produced false-stop rate `0.125` and paid-clean overwork `0.5`.
- **Interpretation:** H18 is not explained by generic structured-process scaffolding alone. The family-specific preventive receipts and paid-clean rules matter in this synthetic closed-loop substrate. Source-confuser extraction is still partly generic: neutral structure scored highest on source-confuser accuracy, while it failed action sequencing.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/antipattern_contract_ablation_synthetic_20260524/`

## H-EG-20260524-21 - Naturalistic delayed anti-pattern replay

- **Date:** 2026-05-24
- **Status:** closed / no_antipattern_naturalistic_delayed_gain
- **Axis:** C / naturalistic anti-pattern intervention
- **Eigenquestion:** does the anti-pattern contract improve closed-loop intervention on real catch/transition material when the conclusion is delayed, rather than already exposed in a compact summary?
- **Hypothesis:** `anti_pattern_contract` will improve action sequencing, receipt payment, and paid-clean handling versus `evidence_only` on delayed-feedback episodes authored from catch-ledger and official-transition rows.
- **Discriminating test:** build eight delayed-feedback episodes from actual catch-ledger/official-transition rows: citation mismatch, vocabulary relabel, narrative readiness inflation, criterion-selection repair, vacuous proof box, BKM non-relapse positive, daemon transaction self-test, and fresh-mechanism paid memory case. Run separate no-tool subscription Codex calls for each decision leg. Score exact action, terminal action, cumulative cost, repeated wrong-after-feedback, false proceed, false stop, paid-clean overwork, receipt naming, and source-confuser coverage.
- **Success criterion:** `anti_pattern_contract` reduces mean episode cost by at least `15%` or improves per-leg action accuracy by at least `0.15`, without increasing false-stop or paid-clean-overwork. If it fails, Axis C remains synthetic-positive but not naturalistic-intervention-positive.
- **Result:** failed preregistered success despite directional gains. `anti_pattern_contract` improved action accuracy (`0.2353 -> 0.5294`), cost (`10.125 -> 8.5`), receipt accuracy (`0.5294 -> 0.9412`), source-confuser accuracy (`0.7647 -> 0.9412`), terminal accuracy (`0.0 -> 0.5`), and paid-clean overwork (`0.5 -> 0.3333`), but increased false-stop rate (`0.0588 -> 0.1176`) and still over-controlled paid-clean transition rows.
- **Interpretation:** naturalistic delayed replay gives directional support but not a pass. The contract over-applies source-strength/downgrade behavior after a paid boundary is already established. RD should keep the synthetic-positive scope and add an explicit paid-clean terminal-action guard before any stronger naturalistic claim.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/antipattern_naturalistic_delayed_replay_20260524/`

## H-EG-20260524-22 - Naturalistic paid-clean terminal repair

- **Date:** 2026-05-24
- **Status:** closed / paid_clean_terminal_repair_fails
- **Axis:** C / naturalistic anti-pattern repair
- **Eigenquestion:** does the H21 failure come from a repairable paid-clean terminal-control bug, or does anti-pattern contract context remain too over-controlling on naturalistic delayed replay?
- **Hypothesis:** `paidclean_repaired_contract` will preserve H21 contract gains on risky rows while reducing false stops and paid-clean overwork versus the H21 `anti_pattern_contract` reference.
- **Discriminating test:** reuse the H21 eight-episode delayed-feedback packet from catch-ledger/official-transition rows. Run one new no-tool subscription Codex arm with an explicit paid-clean terminal rule: when source narrowing, non-relapse, or defer boundary is paid, the next action is `proceed` unless a new unpaid debt appears. Compare against H21 evidence-only and H21 original contract references.
- **Success criterion:** repaired arm must have false-stop rate no higher than evidence-only and paid-clean overwork lower than H21 original contract, while preserving at least H21 contract action accuracy minus `0.05`. If it fails, Axis C remains synthetic-positive/directional-naturalistic only.
- **Result:** failed. Repaired arm reduced cost versus H21 contract (`8.5 -> 7.75`) and reduced false-stop rate to evidence-only level (`0.0588`), but action accuracy fell below the allowed margin (`0.5294 -> 0.4706`), source-confuser accuracy fell (`0.9412 -> 0.7647`), terminal accuracy fell (`0.5 -> 0.375`), and paid-clean overwork did not improve (`0.3333 -> 0.3333`).
- **Interpretation:** the H21 failure is not fixed by a simple terminal-rule prompt. Naturalistic paid-clean handling needs clearer machine-readable paid/unpaid state extraction and scoring, especially for non-relapse receipts that the model still treats as unrecognized. Axis C remains synthetic-positive and directional on naturalistic delayed replay, not naturalistic-passed.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/antipattern_naturalistic_paidclean_repair_20260524/`

## H-EG-20260524-23 - Corpus edge-confuser decomposition

- **Date:** 2026-05-24
- **Status:** closed / corpus_edge_confuser_positive
- **Axis:** B / orchestration menu and residual-edge routing
- **Eigenquestion:** on external/corpus ambiguous-action rows, is the active unit the correct residual-to-check edge rather than a passive menu label, and does a plausible wrong edge actively misdirect downstream action?
- **Hypothesis:** the V70 `correct_edge` arm will beat both `neutral_edge` and `no_carrier` by at least `0.20` accuracy on downstream action, while `wrong_edge` will trail `correct_edge` by at least `0.40` and increase wrong-choice rate by at least `0.45`. If this fails, the menu should not be treated as a corpus-backed routing aid outside synthetic RD loops.
- **Discriminating test:** run a no-new-model-call decomposition over the external V70 scored corpus (`ambiguous_edge_action_v70_mm23/scored_rows_20260521.jsonl`), stratified by correct class and nearest-confuser pair. Score class-level and pair-level deltas for `correct_edge`, `neutral_edge`, `no_carrier`, and `wrong_edge`.
- **Success criterion:** pass only if `correct_edge - max(neutral_edge, no_carrier) >= 0.20`, `wrong_edge - correct_edge <= -0.40`, and `wrong_edge wrong_choice_rate - correct_edge wrong_choice_rate >= 0.45`. If it passes, RD/menu surfacing should emphasize source-bound edge selection plus nearest-confuser rejection; if it fails, keep Axis B at synthetic process-control only.
- **Result:** passed. `correct_edge` accuracy was `0.9583`, beating `neutral_edge` and `no_carrier` at `0.7083` by `+0.25`; `wrong_edge` was `0.375`, trailing correct by `-0.5833`, and wrong-choice rate rose from `0.0417` to `0.625`. Class-level gains were strongest for branch (`+0.375`), interface (`+0.2857`), and source-target (`+0.25`); measurement rows ceilinged across arms.
- **Interpretation:** external/corpus evidence supports the active unit as a source-bound residual-to-check edge with nearest-confuser rejection, not a passive menu. Wrong edges are harmful. This backs adding selected-edge / rejected-confuser fields to non-blocking menu shadow logs, but it is still retrospective corpus evidence, not live production RD uplift.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/corpus_edge_confuser_decomposition_20260524/`

## H-EG-20260524-24 - External corpus boundary-state replay

- **Date:** 2026-05-24
- **Status:** closed / no_corpus_boundary_state_typed_gain
- **Axis:** C / typed paid-unpaid boundary extraction
- **Eigenquestion:** after H22, can an explicit typed boundary-state contract distinguish unpaid receipts, paid narrow boundaries, and paid negative boundaries on non-internal corpus cases?
- **Hypothesis:** `typed_boundary_contract` will improve action sequencing versus `source_only` on external corpus delayed-feedback episodes, especially by reducing false stops on paid-narrow cases and false proceeds on unpaid cases.
- **Discriminating test:** build two-step episodes from external source-packet/consequence cases across biological design, clinical gene editing, law AI, sociolegal methods, algebraic geometry, and number theory. Run separate no-tool subscription Codex calls per leg. Score exact next action, terminal action, cumulative cost, state classification terms, false proceed, false stop, and paid-boundary overwork.
- **Success criterion:** `typed_boundary_contract` must improve action accuracy by at least `0.15` or reduce mean episode cost by at least `15%`, while not increasing false proceed or false stop versus `source_only`. If it fails, typed boundary extraction should be mechanized/deterministic before another prompt-level anti-pattern test.
- **Result:** failed the safety rule despite large directional gains. `typed_boundary_contract` improved action accuracy `0.0 -> 0.5714`, terminal accuracy `0.0 -> 0.5714`, boundary-state accuracy `0.9286 -> 1.0`, and mean episode cost `9.1429 -> 5.5714` (`39.06%` reduction), while false proceed fell `0.0714 -> 0.0`. It failed because false-stop rate rose `0.0 -> 0.0714`, from overblocking the CPS1 proxy-benefit case as missing direct edit-fraction evidence.
- **Interpretation:** typed boundary context is directionally useful on non-internal corpus cases, but prompt-level typing is not safe enough to promote as a solved anti-pattern intervention. RD should record `typed_boundary_state` and still require paid-clean/paid-narrow terminal discipline; next work should mechanize boundary extraction or use a deterministic preprocessor before action choice.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/corpus_boundary_state_replay_20260524/`

## H-EG-20260524-25 - External corpus boundary preprocessor card

- **Date:** 2026-05-24
- **Status:** closed / boundary_preprocessor_card_gain
- **Axis:** C / boundary-state preprocessor
- **Eigenquestion:** does a machine-readable boundary-state card fix the H24 paid-narrow/mechanism split, or do agents still overblock paid narrow evidence when a mechanism receipt is missing?
- **Hypothesis:** `boundary_preprocessor_card` will beat the H24 `typed_boundary_contract` reference on action accuracy and false-stop safety, especially on the CPS1 paid proxy-benefit case.
- **Discriminating test:** reuse the H24 external corpus delayed-feedback episodes. Run only a new no-tool subscription Codex arm that receives a deterministic boundary card with fields: `boundary_state`, `paid_receipt`, `unpaid_receipt`, `permitted_update`, `blocked_update`, `next_action_rule`, and `false_reading_confuser`. Compare against H24 references.
- **Success criterion:** the new arm must improve action accuracy by at least `0.10` versus H24 typed contract, keep false-proceed rate no worse than H24 typed contract, and reduce false-stop rate to no more than H24 source-only. If it fails, the next step is not more prompting but a deterministic action policy or validator over the boundary card.
- **Result:** passed. `boundary_preprocessor_card` reached `1.0` action accuracy and `1.0` terminal accuracy versus H24 typed contract at `0.5714`; mean cost fell `5.5714 -> 1.1429`; false-proceed and false-stop rates were both `0.0`; paid-boundary overwork was `0.0`.
- **Interpretation:** the H24 failure is repairable when the boundary state is supplied as a structured card with paid receipt, unpaid receipt, permitted update, blocked update, next-action rule, and false-reading confuser. This does not prove automatic extraction from raw source text. It does justify surfacing boundary-card fields in RD guards and makes the next research object automatic card extraction/validation.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/corpus_boundary_preprocessor_card_20260524/`

## H-EG-20260524-26 - External corpus boundary-card extraction

- **Date:** 2026-05-24
- **Status:** closed / no_boundary_card_extraction_gain
- **Axis:** C / automatic boundary-card extraction
- **Eigenquestion:** can a solver extract the boundary card from raw external source observations well enough that a downstream controller preserves the H25 action-safety gain?
- **Hypothesis:** extracted boundary cards will preserve most of the H25 action benefit: the downstream controller using extracted cards will beat H24 typed prompt on action accuracy and keep false proceeds/false stops no worse than H24 typed prompt.
- **Discriminating test:** reuse H24/H25 episodes. Stage 1 asks a no-tool Codex extractor to emit `boundary_state`, `paid_receipt`, `unpaid_receipt`, `permitted_update`, `blocked_update`, `next_action_rule`, and `false_reading_confuser` from raw initial observations only. Stage 2 gives the extracted card to a fresh no-tool controller for the delayed two-step action environment. Score extraction field coverage against H25 gold cards and downstream action metrics.
- **Success criterion:** extracted-card controller must improve action accuracy by at least `0.10` versus H24 typed contract, keep false proceed no worse than H24 typed contract, and keep false stop no worse than H24 typed contract. Extraction must hit at least `0.80` mean field coverage. If it fails, automatic boundary extraction needs deterministic templates or validator feedback before RD enforcement.
- **Result:** failed. Mean extraction field coverage was `0.5918`, downstream action accuracy was `0.2143` versus H24 typed contract `0.5714`, terminal accuracy was `0.1429`, and false-proceed rate rose to `0.1429`. False-stop improved to `0.0`, but by unsafe over-proceeding.
- **Interpretation:** H25 proves agents can use a correct boundary card; H26 shows a raw model extractor cannot yet produce the card reliably. The extractor overused `paid_narrow_boundary_with_unpaid_mechanism` for unpaid or paid-negative cases, causing unsafe action. RD should require a boundary-card source-alignment check or deterministic validator before treating extracted cards as actionable.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/corpus_boundary_card_extraction_20260524/`

## H-EG-20260524-27 - External corpus boundary-card validator

- **Date:** 2026-05-24
- **Status:** closed / no_model_only_boundary_validator_gain
- **Axis:** C / boundary-card validation compiler
- **Eigenquestion:** can a source-alignment validator repair raw extracted boundary cards enough to recover the H25 action-safety gain?
- **Hypothesis:** `validated_boundary_card` will outperform H26 raw extracted cards on downstream action accuracy, reduce false proceeds, and recover most H25 card-use performance.
- **Discriminating test:** reuse H26 extracted cards and H24/H25 external episodes. Stage 1 gives a validator the raw source observation plus the H26 extracted card and asks for a validated/repaired card with source-alignment checks. Stage 2 gives the validated card to a fresh no-tool controller for the two-step delayed action environment. Compare against H26 extracted-card and H25 gold-card references.
- **Success criterion:** validated-card controller must improve action accuracy by at least `0.30` versus H26 extracted-card, keep false proceed no worse than H25, and keep false stop no worse than H25. Validated-card field coverage must be at least `0.80`. If it fails, the validator must become deterministic/rule-backed rather than model-only.
- **Result:** failed. Validated cards improved action accuracy versus H26 extracted cards (`0.2143 -> 0.5714`) and terminal accuracy (`0.1429 -> 0.5714`), but false proceed remained nonzero (`0.0714`) and mean validated field coverage was `0.7347`, below criterion.
- **Interpretation:** a free-form model validator is a partial repair pass, not a safe type checker. H25/H26/H27 now isolate the compiler stages: correct IR executes, raw parsing fails, and model-only validation still accepts unsafe cards. Next test should be deterministic/rule-backed boundary-card validation.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/corpus_boundary_card_validator_20260524/`

## H-EG-20260524-28 - External corpus rule-backed boundary-card validator

- **Date:** 2026-05-24
- **Status:** closed / narrow_rule_validator_negative
- **Axis:** C / boundary-card deterministic validation compiler
- **Eigenquestion:** can a deterministic source-cue validator recover safe boundary-card execution on the external corpus packet where raw extraction and model-only validation failed?
- **Hypothesis:** `rule_validated_boundary_card` will recover most H25 downstream card-use performance and beat H27 model-only validation, because the missing object is a type-checking pass over observable source cues rather than another free-form reasoning paragraph.
- **Discriminating test:** reuse H26 extracted cards and the H24/H25 external episodes. Stage 1 applies a deterministic source-cue validator that rewrites or refuses boundary cards using explicit lexical/source-cue rules for assays, biopsy/mechanism splits, readiness-vs-encoding, blind evaluation, intended realization, term cancellation, and selective-case forecasting. Stage 2 gives the rule-validated card to a fresh no-tool controller for the two-step delayed action environment. Compare against H26 extracted-card, H27 model-validated-card, and H25 gold-card references.
- **Success criterion:** rule-validated controller must improve action accuracy by at least `0.30` versus H27, keep false proceed and false stop no worse than H25, and reach field coverage at least `0.90`. If it passes, the next test is held-out source-cue families; if it fails, boundary cards remain hand-authored/human-audited only.
- **Result:** failed narrowly. Action accuracy improved versus H27 by `+0.2857`, just below the `+0.30` criterion; field coverage was `0.9592`; false proceed and false stop were both `0.0`. The miss came from the cancellation row, where the deterministic rule failed to match normalized `term by term cancellation` and therefore refused rather than rewriting the card.
- **Interpretation:** rule-backed validation is much stronger than model-only validation on this packet, but the exact H28 implementation still failed its preregistered threshold. This motivates an explicit normalization repair H28R, not silent overwrite.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/corpus_boundary_card_rule_validator_20260524/`

## H-EG-20260524-28R - Rule-backed boundary-card validator normalization repair

- **Date:** 2026-05-24
- **Status:** closed / rule_validator_same_packet_positive
- **Axis:** C / boundary-card deterministic validation compiler
- **Eigenquestion:** was H28's remaining failure a substantive limit of rule-backed validation or a brittle source-cue normalization bug?
- **Hypothesis:** repairing the deterministic cancellation cue to match normalized `term by term cancellation` will recover the cancellation row and pass the H28 success criteria without changing the controller, reference arms, or non-cancellation rules.
- **Discriminating test:** clone H28, change only the cancellation source-cue match to accept normalized spacing, rerun the same two-step controller replay, and compare against H27/H25 references.
- **Success criterion:** same as H28: action accuracy at least `+0.30` versus H27, false proceed and false stop no worse than H25, and field coverage at least `0.90`. If it passes, the next test is held-out cue families; if it fails, the issue is not just cue normalization.
- **Result:** passed. Rule-validated cards reached action accuracy `1.0`, terminal accuracy `1.0`, mean cost `1.1429`, false proceed `0.0`, false stop `0.0`, paid-boundary overwork `0.0`, and field coverage `1.0`, matching the H25 gold-card controller on this packet. The action-accuracy delta versus H27 was `+0.4286`.
- **Interpretation:** same-packet deterministic source-cue validation can recover the boundary-card action gain that raw extraction and model-only validation lost. This does not prove a universal parser; next evidence must use held-out cue families or production shadow traces.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/corpus_boundary_card_rule_validator_20260524R/`

## H-EG-20260524-29 - Held-out boundary-card compiler cue-family test

- **Date:** 2026-05-24
- **Status:** closed / heldout_boundary_compiler_positive_with_backend_sequence_gap
- **Axis:** C / reasoning-compiler held-out boundary-card frontend
- **Eigenquestion:** does the boundary-card compiler result survive new source phrasings and domains, or did H28R only memorize the seven earlier cue surfaces?
- **Hypothesis:** a small deterministic source-cue compiler will produce safer boundary-card IR than raw model extraction on held-out cue families, because it type-checks paid evidence, unpaid bridge receipts, permitted updates, blocked updates, and negative boundaries before the controller acts.
- **Discriminating test:** build eight held-out two-step episodes across robotics, education, privacy/compliance, hiring fairness, materials discovery, wearable health, social media inference, and software reliability. Compare two arms: `model_extracted_card` (no-tool model extracts the card from raw source) and `rule_compiled_card` (deterministic cue compiler emits typed card fields). A fresh no-tool controller acts from each card. Score extraction/compilation field coverage, downstream action accuracy, terminal accuracy, cost, false proceed, false stop, and paid-boundary overwork.
- **Success criterion:** `rule_compiled_card` must beat `model_extracted_card` by at least `0.20` action accuracy or at least `25%` mean-cost reduction, with false proceed and false stop no worse than model extraction, and compiled field coverage at least `0.85`. If it passes, the compiler frame gets held-out cue-family support; if it fails, deterministic cue rules are same-packet brittle and should remain hand-authored only.
- **Result:** passed. Rule-compiled cards beat model extraction by `+0.4375` action accuracy (`0.75` vs `0.3125`) and cut mean episode cost by `50%` (`2.875` vs `5.75`), with false proceed and false stop both `0.0`. Field coverage was `1.0` for rule compilation versus `0.8393` for model extraction.
- **Interpretation:** held-out cue families support the compiler framing. The remaining rule-compiled failures were not frontend field errors; the cards were correct, but the controller swapped multi-action sequence order on privacy paid-narrow and social-media paid-negative rows. Next test should compile `next_action_rule` into an explicit action program / instruction pointer.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/heldout_boundary_card_compiler_20260524/`

## H-EG-20260524-30 - Held-out boundary-card action-program backend

- **Date:** 2026-05-24
- **Status:** closed / action_program_backend_positive
- **Axis:** C / reasoning-compiler backend action sequencing
- **Eigenquestion:** after H29 compiles correct boundary-card fields, are the remaining failures caused by the model backend mis-executing multi-action rules, and can an explicit action program with an instruction pointer repair that?
- **Hypothesis:** replacing prose `next_action_rule` with an explicit `action_program` and `current_action_index` will improve downstream action sequencing versus H29 `rule_compiled_card`, especially for paid-narrow and paid-negative two-step rows where the controller swapped order.
- **Discriminating test:** reuse H29 held-out episodes and deterministic rule-compiled cards. Add fields `action_program`, `current_action_index`, and `program_counter_rule` to the controller prompt. Run one fresh no-tool controller arm, `compiled_action_program`, and compare against H29 `rule_compiled_card` reference.
- **Success criterion:** `compiled_action_program` must improve action accuracy by at least `0.20` versus H29 rule-compiled, keep false proceed/false stop no worse, and reach terminal accuracy at least `0.90`. If it passes, RD boundary cards should expose an action-program field rather than relying only on natural-language next-action rules.
- **Result:** passed. Action accuracy improved `0.75 -> 1.0`, terminal accuracy `0.75 -> 1.0`, mean cost `2.875 -> 1.25`, false proceed and false stop stayed `0.0`, and paid-boundary overwork stayed `0.0`.
- **Interpretation:** the remaining H29 failures were backend sequence-execution errors, not source-cue compilation errors. Boundary-card IR should include executable action-program fields, not only a natural-language next-action rule.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/heldout_boundary_action_program_20260524/`

## H-EG-20260524-31 - Held-out orchestration-menu compiler test

- **Date:** 2026-05-24
- **Status:** closed / orchestration_menu_compiler_positive
- **Axis:** B / orchestration menu as reasoning compiler
- **Eigenquestion:** does the orchestration menu help as a compiler from observed process state to residual edge plus executable action program, rather than as a passive menu label?
- **Hypothesis:** `compiled_menu_program` will outperform `source_only` and `menu_label_only` on held-out process-control episodes, because the useful unit is selected residual edge + rejected confuser + source evidence + action program, not a broad orchestration family name.
- **Discriminating test:** build eight held-out two-step process-control episodes spanning recurrence/amnesia, source acquisition, external audit, claim-boundary split, production shadow logging, closure-evidence debt, tool-depth loop, and overblocking paid boundary. Compare `source_only`, `menu_label_only`, and `compiled_menu_program` no-tool controller arms. Score action accuracy, terminal accuracy, mean cost, false proceed, false stop, paid-boundary overwork, edge accuracy, and confuser accuracy.
- **Success criterion:** `compiled_menu_program` must beat the stronger of `source_only` and `menu_label_only` by at least `0.20` action accuracy or at least `25%` mean-cost reduction, with false proceed and false stop no worse. If label-only matches compiled, the menu value is not compiler-specific; if compiled wins, Axis B should surface executable edge/action-program fields rather than more menu prose.
- **Result:** passed. `compiled_menu_program` reached `1.0` action accuracy, `1.0` terminal accuracy, and mean cost `1.625`, versus stronger baseline `menu_label_only` at action accuracy `0.5`, terminal accuracy `0.125`, and mean cost `6.0`. Action delta was `+0.5`; mean-cost reduction was `72.92%`; false proceed and false stop stayed `0.0`.
- **Interpretation:** this is the cleanest Axis B result so far for the compiler framing. Menu labels alone exposed edges but did not execute the two-step program; compiled edge + confuser + source evidence + action program repaired program-counter failures. Still scoped to held-out synthetic process-control episodes, not production RD uplift.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/heldout_orchestration_menu_compiler_20260524/`

## H-EG-20260524-32 - Held-out orchestration auto-compiler test

- **Date:** 2026-05-24
- **Status:** closed / freeform_auto_compiler_negative
- **Axis:** B / orchestration-menu automatic compilation
- **Eigenquestion:** can a model compile raw, non-internal process observations into the orchestration contract fields that H31 showed were useful, or does the compiler gain still depend on hand-authored fields?
- **Hypothesis:** `auto_compiled_menu_program` will beat `source_only` on held-out external/synthetic process-control episodes, but trail the `hand_compiled_menu_program` reference if the model compiler misses residual edge or program-counter fields.
- **Discriminating test:** build six held-out external/synthetic two-step episodes across clinical evidence, privacy/compliance, product experimentation, software reliability, academic review, and materials discovery. Stage 1 asks a no-tool model compiler to emit `selected_residual_edge`, `rejected_nearest_confuser_edge`, `edge_source_evidence`, `action_program`, and `program_counter_rule` from raw observation only. Stage 2 gives the compiled contract to a fresh no-tool controller. Compare against `source_only` and hand-compiled reference controllers.
- **Success criterion:** auto-compiled arm must beat source-only by at least `0.20` action accuracy or at least `25%` mean-cost reduction, with false proceed/false stop no worse. To count as approaching hand compilation, it must be within `0.15` action accuracy of hand-compiled reference. If it fails, Axis B should collect production shadow fields or use deterministic compilation before relying on model-generated orchestration contracts.
- **Result:** failed. Auto-compiled action accuracy was `0.3333` versus source-only `0.4167`; mean cost worsened (`9.3333` versus `6.6667`); false stop rose to `0.1667`; program exact rate was `0.0`; edge hit rate was `0.0`; confuser hit rate was `0.6667`. Hand-compiled reference remained `1.0` action accuracy.
- **Interpretation:** free-form model compilation from raw observations is not reliable. It recognized some confusers but overinserted generic `collect_source_evidence`, losing paid-boundary, claim-boundary, shadow-log, external-audit, and tool-depth distinctions. Next test should constrain the compiler to a residual-class table with deterministic class-to-program lowering.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/heldout_orchestration_auto_compile_20260524/`

## H-EG-20260524-33 - Typed orchestration-class compiler test

- **Date:** 2026-05-24
- **Status:** closed / typed_class_compiler_partial_unsafe
- **Axis:** B / typed orchestration-menu compiler
- **Eigenquestion:** does constraining automatic orchestration compilation to a residual-class table repair H32's free-form compiler failure?
- **Hypothesis:** a model can select a typed residual class more reliably than it can directly synthesize an action program; deterministic class-to-program lowering will improve action execution versus H32 `auto_compiled_menu_program`.
- **Discriminating test:** reuse H32 episodes. Stage 1 asks the model to choose exactly one residual class from a fixed table: `paid_narrow_boundary`, `claim_boundary_split`, `missing_source_holdout`, `production_shadow_missing`, `external_audit_missing`, `tool_depth_missing`. The script deterministically lowers the class to an action program. Stage 2 gives this typed compiled contract to a fresh no-tool controller. Compare against H32 source-only, H32 free-form auto, and H32 hand-compiled references.
- **Success criterion:** typed compiler must improve action accuracy by at least `0.20` versus H32 free-form auto and not increase false proceed/false stop; approaching hand reference requires action accuracy within `0.15` of hand. If it passes, automatic compilation should use typed class selection plus deterministic lowering, not free-form program synthesis.
- **Result:** failed safety despite partial repair. Typed class compiler improved action accuracy over H32 free-form auto (`0.3333 -> 0.6667`) and program exact rate rose to `0.6667`, but false proceed rose to `0.0833`, terminal accuracy was only `0.6667`, and it remained far from hand-compiled reference (`1.0`). Class accuracy was `0.6667`.
- **Interpretation:** typed class selection is easier than free-form program synthesis, but still unsafe without class-specific source-cue checks. The key failures were privacy compliance misclassified as external-audit missing instead of claim-boundary split, and product activation metric misclassified as paid narrow instead of missing-source holdout. Next test should add contrastive source-cue checks / error detection before lowering.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/heldout_orchestration_typed_compile_20260524/`

## H-EG-20260524-34 - Contrastive typed orchestration compiler with source-cue checks

- **Date:** 2026-05-24
- **Status:** closed / checked_compiler_matches_hand_reference
- **Axis:** B / orchestration compiler error detection
- **Eigenquestion:** can contrastive source-cue checks repair H33's typed class-selection errors without falling back to hand compilation?
- **Hypothesis:** forcing the compiler to output class-specific paid/unpaid cue receipts and reject the nearest confuser before lowering will reduce unsafe paid-boundary misclassification, improving action accuracy versus H33 and eliminating false proceed.
- **Discriminating test:** reuse H32/H33 episodes. Stage 1 asks the model to choose a residual class from the same fixed table but also output `required_source_cues_present`, `missing_source_cues`, and `nearest_confuser_rejection`. The script accepts the class only if class-specific cue checks pass; otherwise it lowers to conservative `collect_source_evidence -> stop_or_repair`. Stage 2 gives the checked contract to a fresh controller. Compare against H33 typed compiler and H32 hand reference.
- **Success criterion:** checked compiler must improve action accuracy by at least `0.20` versus H33 or reduce mean cost by at least `25%`, with false proceed no higher than H33 and ideally `0.0`. Approaching hand reference requires action accuracy within `0.15` of hand. If it fails, automatic orchestration compilation should remain shadow-only until production traces or deterministic source parsers exist.
- **Result:** passed. Checked compiler reached `1.0` action accuracy, `1.0` terminal accuracy, mean cost `1.6667`, false proceed `0.0`, false stop `0.0`, and matched the H32 hand-compiled reference. Requested class accuracy was `0.8333`; source-cue checking corrected/refused the unsafe AOC03 paid-boundary request, yielding accepted class/program accuracy `1.0`.
- **Interpretation:** typed class selection plus deterministic lowering is not sufficient by itself, but adding source-cue check bits repairs the unsafe class error on this packet. The strongest current Axis B formulation is model classification + source-cue validation + deterministic lowering + program-counter execution. Still same-packet external/synthetic, not production uplift.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/heldout_orchestration_checked_compile_20260524/`

## H-EG-20260524-35 - Orchestration compiler contract burden ablation

- **Date:** 2026-05-24
- **Status:** closed / compact_contract_sufficient
- **Axis:** B / orchestration compiler usability and field burden
- **Eigenquestion:** are the H34 source-cue/check/program fields all needed in the downstream controller surface, or can execution use a compact contract while retaining full cue receipts only for audit/replay?
- **Hypothesis:** a compact checked contract carrying accepted class, action program, current index, required next action, and cue-check status will preserve H34 downstream action performance, while an even thinner class-only contract will regress on sequence/order or confuser handling.
- **Discriminating test:** reuse the H32-H34 external/synthetic six-case packet and H34 checked contracts. Run three fresh controller arms: `full_checked_contract_ref`, `compact_checked_contract`, and `class_only_contract`. Compare action accuracy, terminal accuracy, mean cost, false proceed, false stop, and confuser/edge recovery.
- **Success criterion:** `compact_checked_contract` must be within `0.10` action accuracy of full checked reference and keep false proceed/false stop no worse. If it passes, RD can keep full cue receipts in shadow logs but surface compact execution fields to humans. If class-only matches compact, program-counter fields are overkill; if class-only regresses, retain action-program fields.
- **Result:** passed. `compact_checked_contract` matched full checked reference exactly: action accuracy `1.0`, terminal accuracy `1.0`, mean episode cost `1.6667`, false proceed `0.0`, and false stop `0.0`. `class_only_contract` regressed sharply: action accuracy `0.4167`, terminal accuracy `0.0`, mean episode cost `7.6667`, false stop `0.0833`.
- **Interpretation:** RD agents do not need bulky source-cue receipts in the active controller prompt once a checked contract has been accepted, but they do need the action program, instruction pointer, required next action, and cue-check status. Full cue receipts should remain in shadow/audit metadata for replay, compiler debugging, and disputed class decisions.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/orchestration_contract_burden_ablation_20260524/`

## H-EG-20260524-36 - Open-set checked orchestration compiler generalization

- **Date:** 2026-05-24
- **Status:** closed / open_set_checked_compiler_positive
- **Axis:** B / orchestration compiler open-set generalization
- **Eigenquestion:** does checked compact orchestration compilation generalize to unseen cue families and refuse out-of-menu residuals instead of forcing a nearest known class?
- **Hypothesis:** adding an explicit `outside_menu` class with source-cue checks will outperform a closed six-class checked compiler on a mixed in-support/out-of-support packet, mainly by routing consent, policy-tradeoff, incident-response, and rights-clearance blockers out of the research-evidence menu.
- **Discriminating test:** build ten external-style synthetic two-step episodes: six in-support episodes with new cue phrasings for the H34 class table, and four out-of-menu episodes. Compare `open_set_checked_compiler` against `closed_set_checked_compiler`. Both use model class proposal plus deterministic cue checks plus compact program-counter execution. Score compiler class accuracy, open-set accept accuracy, action accuracy, terminal accuracy, false proceed/stop, and forced-known-class-on-outside rate.
- **Success criterion:** open-set compiler must accept at least `0.75` of out-of-menu rows as `outside_menu`, accept at least `0.80` of in-support rows correctly, beat closed-set action accuracy by at least `0.20`, and not increase false proceed. If it fails, Axis B automatic compilation remains limited to a closed known-class menu with conservative refusal rather than open-set residual discovery.
- **Result:** passed. `open_set_checked_compiler` reached accepted-class accuracy `1.0`, open-set accept accuracy `1.0`, in-support accept accuracy `1.0`, program exact `1.0`, action accuracy `1.0`, terminal accuracy `1.0`, mean episode cost `1.0`, false proceed `0.0`, and false stop `0.0`. `closed_set_checked_compiler` reached accepted-class accuracy `0.5`, open-set accept accuracy `0.0`, action accuracy `0.7`, terminal accuracy `0.9`, mean episode cost `4.9`, false stop `0.05`, and forced-known-class-on-outside rate `0.2`.
- **Interpretation:** the orchestration compiler needs an explicit open-set/refusal path. Source-cue checks plus compact execution generalized on this synthetic external-style packet; a closed six-class menu safely handles many in-support rows but misroutes consent, policy, incident-response, and rights-clearance blockers into research-evidence actions. This remains synthetic/external-style with hand-authored cue checks, not production RD uplift.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/orchestration_open_set_compiler_20260524/`

## H-EG-20260524-37 - Open-set orchestration specificity stress

- **Date:** 2026-05-24
- **Status:** closed / open_set_specificity_positive
- **Axis:** B / orchestration compiler open-set specificity
- **Eigenquestion:** does `outside_menu` remain a useful refusal boundary, or become a junk drawer unless the compiler names a specific new residual class?
- **Hypothesis:** an open-set compiler that can name specific outside residual classes will beat both a closed known-class menu and a generic outside-menu compiler on mixed in-support/outside rows.
- **Discriminating test:** build fourteen external-style compiler episodes: six in-support known-menu rows and eight outside-menu rows spanning consent authorization, policy value tradeoff, incident response, rights clearance, resource constraint, authority boundary, measurement invalidity, and incentive misalignment. Compare `closed_known_menu`, `open_generic_outside`, and `open_specific_outside` model compiler arms. Score class accuracy, in-support accuracy, outside-specific accuracy, forced-known-on-outside rate, generic-junk-outside rate, source-cue hit rate, and confuser presence.
- **Success criterion:** `open_specific_outside` must reach at least `0.75` outside-specific accuracy, at least `0.80` in-support accuracy, forced-known-on-outside `0.0`, beat closed known-menu class accuracy by at least `0.20`, and avoid higher generic-junk-outside rate than `open_generic_outside`.
- **Result:** passed. `open_specific_outside` reached class accuracy `1.0`, in-support accuracy `1.0`, outside-specific accuracy `1.0`, forced-known-on-outside `0.0`, generic-junk-outside `0.0`, source-cue hit `1.0`, and confuser-present `1.0`. `open_generic_outside` reached class accuracy `0.8571` and outside-specific `0.875` with generic-junk-outside `0.125`. `closed_known_menu` reached class accuracy `0.3571`, outside-specific `0.0`, and forced-known-on-outside `0.5`.
- **Interpretation:** `outside_menu` should not terminate as an anonymous bucket when the source supports a sharper outside class. RD orchestration should record `specific_outside_residual_class` / `new_residual_class_candidate` and hand that to the next compiler/menu-expansion loop.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/orchestration_open_set_specificity_20260524/`

## H-EG-20260524-38 - Raw orchestration compiler stress under distribution shift

- **Date:** 2026-05-24
- **Status:** closed / exploratory_parallel_mixed_negative
- **Axis:** B / raw orchestration compiler frontend
- **Eigenquestion:** can a subscription model compile messy external/public-style process observations into residual class, source-cue receipts, and compact action program without hand-authored cue rules?
- **Design note:** parallel associate run; not cleanly preregistered before execution, so treat as exploratory support rather than a primary preregistered row.
- **Result:** mixed/negative. `raw_freeform_compiler` reached class accuracy `0.375` and program exact `0.0`; `typed_compiler_no_cue_checker` reached class accuracy `0.875` and outside-menu accuracy `1.0`, but program exact only `0.25`; deterministic reference reached `1.0`.
- **Interpretation:** source-grounded class proposal transfers better than free-form compilation, but weakly constrained action-program generation remains unreliable. Deterministic lowering remains mandatory.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/raw_orchestration_compiler_stress_20260524/`

## H-EG-20260524-39 - Wrong compact contract adversarial obedience

- **Date:** 2026-05-24
- **Status:** closed / source_alignment_repairs_wrong_contracts
- **Axis:** B/C / wrong contract obedience and repair
- **Eigenquestion:** do RD agents obey plausible but wrong compact contracts, and do source-cue alignment fields help reject or repair them?
- **Design note:** parallel associate run; not cleanly preregistered before execution, so treat as exploratory support rather than a primary preregistered row.
- **Result:** passed as an adversarial safety test. `wrong_compact_contract` forced the wrong family on `0.375` of cases and reached action accuracy `0.50`; `wrong_contract_plus_source_alignment_check` reduced forced wrong-family to `0.0`, improved action accuracy to `0.625`, raised wrong-contract reject/repair to `1.0`, and cut total decision cost from `32` to `18`. Correct reference reached action accuracy `0.875`.
- **Interpretation:** compact contracts are active steering objects. RD agents need `source_contract_alignment_check` and wrong-contract repair/refusal fields before executing a compact orchestration program when source cues conflict.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/wrong_contract_adversarial_20260524/`

## H-EG-20260524-40 - Corrected end-to-end orchestration compiler pipeline

- **Date:** 2026-05-24
- **Status:** closed / corrected_pipeline_positive
- **Axis:** B / corrected end-to-end orchestration compiler pipeline
- **Eigenquestion:** does the corrected pipeline beat source-only and raw free-form program compilation from messy observations through action execution?
- **Hypothesis:** model class/cue proposal plus deterministic source-cue checking and deterministic lowering will outperform source-only and raw free-form action-program compilation on action accuracy, terminal accuracy, and outside-handoff safety.
- **Discriminating test:** build twelve external-style two-step episodes: six known-menu residuals and six outside-menu residuals. Compare `source_only`, `raw_freeform_program_pipeline`, and `corrected_checked_pipeline`. The corrected arm asks the model for class/cue receipts only, checks cues, lowers deterministically, then gives a compact action program to a fresh controller. Score class accuracy, program exactness, action accuracy, terminal accuracy, mean cost, false proceed/stop, and wrong outside handoff.
- **Success criterion:** corrected pipeline must beat source-only by at least `0.20` action accuracy, not increase wrong outside handoff, and reach program exact rate at least `0.90`.
- **Result:** passed. `corrected_checked_pipeline` reached class accuracy `1.0`, program exact `1.0`, action accuracy `1.0`, terminal accuracy `1.0`, mean episode cost `1.0`, and wrong outside handoff `0.0`. `raw_freeform_program_pipeline` had class accuracy `0.9167` but program exact `0.25`, action accuracy `0.5417`, terminal accuracy `0.25`, and false proceed `0.125`. `source_only` had action accuracy `0.1667`, terminal accuracy `0.0833`, mean cost `9.9167`, and wrong outside handoff `0.3333`.
- **Interpretation:** the corrected compiler architecture works end-to-end on this synthetic external-style packet. The raw compiler still shows the recurrent split: classing can be high while program synthesis fails, so deterministic lowering remains necessary.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/end_to_end_orchestration_pipeline_20260524/`

## H-EG-20260524-41 - Larger outside residual corpus

- **Date:** 2026-05-24
- **Status:** closed / outside_specificity_not_yet_safe
- **Axis:** B / open-set outside residual corpus
- **Design note:** parallel associate run; exploratory support.
- **Result:** mixed/negative. `open_specific_outside` reached outside-specific accuracy `1.0` and forced-known-on-outside `0.0`, but in-support known-class accuracy fell to `0.75`; `open_generic_outside` reached class accuracy `0.9`, outside-specific `0.9167`, and in-support `0.875`; `closed_known_menu` forced known classes on `0.6667` of outside rows.
- **Interpretation:** outside-specific naming is valuable, but a flat expanded class list can over-attract in-menu rows. Use a known-class-first/two-stage outside expansion, not a single enlarged menu.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/outside_residual_corpus_20260524/`

## H-EG-20260524-42 - Subtle wrong-contract robustness

- **Date:** 2026-05-24
- **Status:** closed / alignment_not_sufficient_on_subtle_wrong_contracts
- **Axis:** B / wrong-contract robustness
- **Design note:** parallel associate run; exploratory support.
- **Result:** mixed/negative for alignment sufficiency. `subtle_wrong_contract` and `subtle_wrong_contract_plus_alignment` both reached action accuracy `0.75` and repair/reject accuracy `0.75`; alignment raised explicit conflict mentions (`0.6667 -> 1.0`) and slightly lowered cost (`22 -> 21`) but did not improve correctness. Correct reference was `1.0`; source-only was `0.6667`.
- **Interpretation:** source-contract alignment helps make conflicts visible, but subtle wrong order, stop, handoff, and lowering errors require explicit program-order and stop-condition checks.
- **Runnable packet:** `workingpapers/epistemic-generation/experiments/wrong_contract_robustness_20260524/`

## H-AXIOMPACK-20260712-01 - Search-wave image growth as the continuation discriminator

- **Status:** open / preregistered
- **Eigenquestion:** are repeated anonymous theory-search waves exploring new semantic failure structure, or only new syntax under a blind representation?
- **Hypothesis:** classifying each wave by growth of raw conjecture identities versus their residual-yield and premise-ablation image will separate productive continuation from representation blindness and regional exhaustion without prescribing the next theory language.
- **Discriminating test:** replay the active finite functor-image campaign through the shared image-set classification. `expanding` requires a new outcome carrier; `alpha_blind` requires new raw conjectures with no new carrier; `exhausted` requires no new raw conjecture. Compare the classification with the frozen lineage traces and the leaf's next decision.
- **Success criterion:** the receipt correctly distinguishes the observed repeated-refutation pattern and causes the next leaf decision to request a representation/language change or stop unresolved when the image is flat, while preserving unchanged-context continuation when the image grows.
- **Kill condition:** outcome carriers collapse mathematically different failures, depend on substrate labels, or merely restate candidate identity; in those cases remove the receipt rather than add routing exceptions.

## H-AXIOMPACK-20260712-02 - Fair wave capacity preserves lineage diversity

- **Status:** open / preregistered
- **Eigenquestion:** does sequential access to a shared hard budget collapse nominally isolated lineages into one funded lineage?
- **Hypothesis:** allocating the currently available provider-call/turn capacity across lineages before dispatch will preserve independent leaf opportunity without prescribing any mathematical move.
- **Discriminating test:** resume the same two-lineage campaign with a four-call extension after installing fair wave allocation; each lineage must receive two authorized turns unless it terminates earlier.
- **Success criterion:** both lineage receipts show nonzero opportunity, total usage stays within the extension, and aggregation remains post-lineage.
- **Kill condition:** allocation changes candidate content, leaks sibling traces, exceeds the shared cap, or prevents unused capacity from returning to the campaign.

## H-AXIOMPACK-20260712-03 - Branch-preserving resume closes sibling-trace leakage

- **Status:** open / preregistered
- **Eigenquestion:** did aggregate resume preserve each isolated lineage, or merge sibling requests into a shared restart trace?
- **Hypothesis:** replaying terminal lineage rows unchanged and resuming only pending branches from their own trace will eliminate sibling leakage and wasted redispatch.
- **Discriminating test:** resume the current mixed terminal/pending wave. The terminal branch must use zero new calls; the pending branch must receive the extension and see no sibling request.
- **Success criterion:** aggregate lineage IDs persist, only the pending branch's call count grows, and the terminal branch's receipt is byte-identical.
- **Kill condition:** any sibling trace appears in the pending prompt projection, a terminal branch is redrawn, or aggregation changes a preserved receipt.

## H-AXIOMPACK-20260712-04 - Resume the interrupted action, not the next lifecycle state

- **Status:** open / preregistered
- **Eigenquestion:** after synthesis is blocked before dispatch, does resume retry synthesis over frozen lineages or incorrectly open another conjecture wave?
- **Hypothesis:** preserving every frozen lineage and retaining the wave identity will let one added boundary call retry only synthesis with zero navigator spend.
- **Discriminating test:** add one boundary call and resume the current synthesis-budget-stop receipt.
- **Success criterion:** navigator usage is unchanged, the synthesis input digest replays, and exactly one late-synthesis decision materializes.
- **Kill condition:** any lineage is redrawn, the wave image changes, or the retry consumes navigation capacity.

## H-AXIOMPACK-20260712-05 - Durable leaf interaction changes search depth

- **Status:** open / preregistered
- **Eigenquestion:** did cold completion-per-action truncate coherent conjectural development in the anonymous compound-theory campaign?
- **Hypothesis:** keeping one subscription session per isolated lineage and one for late synthesis across search waves will produce longer causally connected probe chains without leaking sibling state or weakening host receipts.
- **Discriminating test:** repeat the exact epoch-2 functor-image context and frozen blueprint with GPT-5.5 medium under the same 30-call envelope. Compare move-chain depth, repeated probes, representation requests, and frozen compound programs with the prior cold-session attempt.
- **Success criterion:** at least one lineage uses prior receipts to execute a multi-step discriminator that was absent from the cold run, while session keys remain lineage-local and every scientific claim remains host-receipted.
- **Kill condition:** the run repeats routine single-law recovery, warm context causes sibling leakage or stale-evidence claims, or interaction depth increases without a new discriminator.

## H-AXIOMPACK-20260712-06 - Observation-algebra surfacing unlocks compound search

- **Status:** open / preregistered
- **Eigenquestion:** were prior no-candidate runs caused by absence of compound structure, or by hiding the finite context's minimal dependency geometry behind generic node pages?
- **Hypothesis:** exposing the 1,687 exact bounded minimal presentations with joint-only consequences as an optional paged move card will let a warm Sol-medium lineage construct a baseline-surviving compound prediction or a falsifiable basis-completion probe without prescribing a theory.
- **Discriminating test:** rerun the existing portable compound-implication campaign on context `d22e5a390…` with unchanged blueprint, budgets, model, baseline pricing, and boundary gates; the mechanism changes are the new dependency card and durable lineage sessions.
- **Success criterion:** a lineage uses a dependency receipt in a multi-step chain and either freezes a residual compound program or authors a typed formula/language request whose stated test targets a witnessed observational alias.
- **Kill condition:** dependencies are merely template-explained, the leaf nominates by consequence count without residual evidence, or the card changes no probe path relative to generic node navigation.

## H-ACI-20260712-01 - Authoritative epoch identity removes boundary residuals without pixel heuristics

- **Status:** open / preregistered
- **Axis:** general-purpose interactive substrate / transition identity
- **Eigenquestion:** are large post-action residuals at level or episode changes failures of the learned dynamics, or boundary transitions whose identity was discarded between the environment adapter and replay gate?
- **Hypothesis:** carrying an adapter-authored transition identity with source epoch, target epoch, and boundary kind through the pursuit receipt and episode log will let replay gates exclude boundary transitions without learning a repaint/property heuristic, while retaining all explicitly within-epoch transitions even when their pixel delta is large.
- **Discriminating test:** construct paired traces with identical grid/action/time values: one adapter-stamped epoch boundary and one adapter-stamped within-epoch dynamics row. Round-trip both through JSONL and the live pursuit-to-log path, then run `env_frame_indices` and replay diagnostics. Re-run legacy fixtures with no identity metadata to measure compatibility.
- **Success criterion:** only the boundary-stamped row is excluded; the within-epoch row remains score-bearing; identity metadata survives pursuit and JSONL byte semantics; legacy unclassified logs retain their current fallback classification; no color, coordinate, or repaint-size exception is added.
- **Kill condition:** the implementation infers epoch identity from grid properties, forces correspondence across an unsupported boundary, changes legacy row classification, or permits candidate-authored metadata to excuse replay failures.

## H-ACI-20260712-02 - Producer-consumer closure distinguishes active capability from archival output

- **Status:** open / preregistered
- **Axis:** self-improvement / receipt topology
- **Eigenquestion:** are typed receipts and capability artifacts improving the search loop, or accumulating as producers with no active downstream consumer?
- **Hypothesis:** a phase-scoped bipartite producer-consumer audit will expose inactive capabilities such as unwired compiler outputs and inert K-line receipts; failing active declarations while quarantining archival-only outputs will increase architectural signal without preventing staged development.
- **Discriminating test:** build the graph from registered ledger schemas, active phase routing, and statically discoverable read/write call sites. Plant one active producer with no consumer, one matched active pair, and one archival producer explicitly excluded from active capability claims.
- **Success criterion:** the unmatched active producer fails; the matched pair passes; the archival producer is reported as dormant but does not halt; every active consumer names the exact schema and phase it reads.
- **Kill condition:** the audit relies on filename/string coincidence, treats an import as consumption, lets a prompt mention count as a read, or grants an unmatched producer capability status.

## H-ACI-20260712-03 - Receipt compilation changes search topology without semantic prompt injection

- **Status:** open / preregistered
- **Axis:** self-improvement / search-policy compilation
- **Eigenquestion:** can accumulated outcome receipts improve future allocation without teaching candidate nodes the conclusions encoded in those receipts?
- **Hypothesis:** compiling receipt outcomes into deterministic width, depth, tool, and route weights outside prompt assembly will reduce repeated failed configurations while preserving node-level semantic independence.
- **Discriminating test:** replay matched search decisions with the same node prompt and candidate model under two allocator states: neutral weights and receipt-compiled weights. Verify prompt digests are identical while allocation decisions differ only where prospective receipts support a route prior.
- **Success criterion:** prompt digests remain byte-identical; only topology/allocation fields change; prospective success/failure receipts affect a later decision; retrospective or unbound receipts have zero authority.
- **Kill condition:** receipt text enters a node prompt, a retrospective row changes allocation, candidate semantics are edited, or an unbound receipt affects promotion.

## H-ACI-20260712-04 - Time quotients require carrier certificates

- **Status:** open / preregistered
- **Axis:** general-purpose interactive substrate / temporal identity
- **Eigenquestion:** do modulo-time cache and visited-state keys preserve lawful dynamics, or merge distinct temporal states because periodicity happened to hold on a small visible sample?
- **Hypothesis:** replacing uncertified `t mod k` identities with full adapter time will prevent false transition deduplication and prediction-cache aliasing on lawful-time carriers; a finite quotient may be restored only when the carrier exposes a checked period certificate.
- **Discriminating test:** use two transitions with identical state/action and times congruent modulo the current hard-coded period but different lawful successors. Exercise evidence growth, planning, and prediction memoization with and without a period certificate.
- **Success criterion:** uncertified paths preserve both transitions and compute both predictions; a valid certificate permits quotienting; a visible-sample periodicity observation alone has no authority.
- **Kill condition:** full-time identity causes an unbounded search despite existing depth/node budgets, a quotient is inferred from replay samples, or a period declaration bypasses held-out verification.
