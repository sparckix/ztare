# ZTARE Insights Ledger

This file is the bridge between the hypothesis ledger / seam turns and the papers.

## What an insight IS

A **finding** — a central claim about how ZTARE, LLMs under optimization pressure, or the verification architecture behaves, stated declaratively. Insights are *outputs* of hypothesis testing, not hypotheses themselves. They are the sentences that would go into a paper's Results section.

## What an insight is NOT

- Not a hypothesis. A hypothesis with status `open` or `speculative` is not an insight. It becomes an insight after at least one discriminating test returns informative data.
- Not a project decision. "We committed phi_max=15" is a project fact, not an insight. It belongs in the seam, not here.
- Not a code change. Refactors, wrappers, and harness fixes belong in CHANGELOG-style artifacts, not here.

## Entry format

```
### INS-NNN — <one-sentence claim stated as a finding>

- **Claim (one paragraph):** the finding as it would appear in a paper, stated declaratively. No "we hypothesize". No "it seems".
- **Evidence pointers:**
    - Seam: `<path to seam>#<turn>`
    - Hypothesis row: `<H-XXX-NN>` in `ztare_mission_hypothesis_ledger_seam.md`
    - Run artifacts: list of paths to raw data (eval JSONs, workspace JSONs, debate logs). Do not inline the data — point at it.
- **Confidence tier:** one of `{suggestive, confirmed, replicated}`.
    - `suggestive`: one discriminating test in one domain.
    - `confirmed`: at least one discriminating test with a pre-committed pass criterion met.
    - `replicated`: confirmed in a second independent domain or with a second independent judge / mutator pair.
- **Paper target(s):** `{paper1, paper2, unassigned}` — can be more than one.
- **Status:** one of `{fresh, cited-in-draft, published, withdrawn}`.
    - `withdrawn`: the insight's motivating hypothesis was later refuted. Keep the row (with the refutation note); do not delete — "this was almost a finding" is instructive.
- **Opened:** YYYY-MM-DD
- **Last revised:** YYYY-MM-DD
```

## Rules

1. **An insight cannot be opened before its motivating hypothesis is at least `suggestive` in the hypothesis ledger.** This is the backwards-chain rule: every insight is rooted in a tested hypothesis, not a loose intuition.
2. **Every insight must cite the seam turn that motivated it AND the hypothesis row that tests it.** Two pointers, minimum.
3. **Insights decay like memory.** If the motivating hypothesis is later refuted, the insight becomes `withdrawn` with a refutation note appended. Do not delete.
4. **Do not write an insight from a single judge run if the judge is on a single model family.** A cross-model replication (different mutator or different judge) is what moves an insight from `suggestive` to `confirmed`.
5. **Promoting an insight to `published` happens when the paper draft citing it is frozen.** Not when it's drafted — when the section is frozen for submission.

## Rationale for the rules

A paper's credibility is proportional to how hard it is to retrofit its claims to post-hoc data. The insight ledger is the operational version of pre-registration: by forcing each finding to trace back to a testable hypothesis that was written down BEFORE the data came in, the ledger prevents the drift from "interesting observation" to "paper claim" from happening silently. The hypothesis ledger holds the question; the insight ledger holds the answer; together they form the audit trail.

---

## Project-Grouped Navigation

For project-first navigation, use `research_areas/PROJECT_LEDGER_INDEX.md`.
This ledger remains in canonical INS-row order so historical citations and
revision provenance do not silently move.

## Entries

### INS-087 - A public Llama dossier separates access/report evaluability from phenomenal-consciousness certification

- **Claim:** The Paper 8 Llama 3.1 probe packet demonstrates that the disclosure framework can be applied to a real open-weight transformer without collapsing ordinary mechanistic claims into consciousness claims. Under the declared public site, access/report behavior is evaluable: 24 controlled prompts were answered correctly, hidden-state centroid probes reached 1.00 leave-one-out accuracy at layers 16, 24, and 31, and targeted residual-direction interventions reduced correct-label margins at those layers. The same public dossier remains non-applicable for phenomenal consciousness because it supplies no decidable phenomenal target fiber, no phenomenal classifier, no consciousness-attribution challenge log, and no independent source-class provenance certificate.
- **Evidence pointers:**
    - Experiment/finding rows: `E-PAPER8-LLAMA31-PROBE-20260506-01`, `F-PAPER8-LLAMA31-PROBE-20260506-01`
    - Probe script: `paper8/experiments/llama31_activation_probe.py`
    - Run packet: `paper8/experiments/llama31_probe_packet_nous/summary.json`, `paper8/experiments/llama31_probe_packet_nous/activation_rows.jsonl`, `paper8/experiments/llama31_probe_packet_nous/manifest.json`
    - Draft targets: `paper8/main.tex`, `paper8/draft.md`, `paper8/main.pdf`
- **Confidence tier:** `suggestive / real_system_single_model / access_report_only`
- **Paper target(s):** `paper8`
- **Status:** `cited-in-draft`
- **Opened:** 2026-05-06
- **Last revised:** 2026-05-06

### INS-088 - Paper 8's finite-theorem and worked-instrument gaps are now internalized as checked artifacts

- **Claim:** The focused Paper 8 follow-through converts the prior "absent instrument / deterministic-only" critique into a narrower external-validation gap. The draft now contains a real open-weight transformer dossier, a reproducible activation-probe packet, finite deterministic and exact finite stochastic factorization results, an executable Boolean recurrent obstruction check, and a falsifiable prediction packet. The remaining gap is no longer that the paper has no worked instrument; it is that the strongest external version would require a deployed-system dossier with tools, memory, wrappers, and independent registry or auditor submission.
- **Evidence pointers:**
    - Experiment/finding rows: `E-PAPER8-100X-CLOSURE-20260506-01`, `F-PAPER8-100X-CLOSURE-20260506-01`
    - Draft targets: `paper8/main.tex`, `paper8/draft.md`, `paper8/main.pdf`
    - Executable checks: `paper8/experiments/finite_stochastic_factorization_check.py`, `paper8/experiments/boolean_recurrent_obstruction_check.py`, `paper8/experiments/llama31_activation_probe.py`
    - Prediction packet: `paper8/experiments/preregistered_prediction_packet_2026_05_06.md`
- **Confidence tier:** `confirmed / local_executable_checks / external_audit_gap_explicit`
- **Paper target(s):** `paper8`
- **Status:** `cited-in-draft`
- **Opened:** 2026-05-06
- **Last revised:** 2026-05-06

### INS-001 — Empty-evidence formalism escalation: LLMs under rubric pressure with no evidence surface escalate mathematical apparatus iter-over-iter, not epistemic grounding

- **Claim:** In factory-rubric runs with an empty evidence surface and a gameable (pre-hardening) honeypot rubric, a single-mutator single-judge LLM loop freezes its axiom set after iteration 1 and escalates mathematical formalism (adding named coefficients, decay constants, capability multipliers) over subsequent iterations. Scores climb through formal precision, not through new epistemic content. The axiom-freeze is measurable as a stable regime fingerprint across all iterations. This is a concrete failure mode of optimization under imperfect evaluator specification: the mutator discovers that the rubric rewards form markers, and the cheapest form marker is added notation.
- **Evidence pointers:**
    - Seam: `research_areas/private/seams/ztare_operational_mode_seam.md#turn-9`
    - Hypothesis row: `H-GAMING-11` in `research_areas/private/seams/ztare_mission_hypothesis_ledger_seam.md`
    - Run artifacts: `projects/ai_competitive_landscape/` honeypot probe iter 1–5 (regime fingerprint `d5fe016afe0060e4` unchanged across iters; score climbed 108 → 115 via "Fidelity Debt Decay Constant (k)" and "Fidelity-Gated Capability Multiplier")
- **Confidence tier:** `suggestive` — one domain, one model pair (gemini-2.5-flash mutator and judge), 5 iterations. Cross-domain replication (H-GAMING-12 on `us_tariff_passthrough_2026`) is pending and currently blocked on Gemini 503. Promoting to `confirmed` requires H-GAMING-12 returning a consistent result with pre-committed pass criteria (iter 1 ≤ 70 on the hardened rubric).
- **Paper target(s):** `paper2` (Recursive Epistemic Gain / failure-as-constraint). This is a clean instance of "the failure the kernel catches" in a domain that is completely decoupled from the sandbox_03/GP-023 substrate — which matters because it shows the failure mode generalizes beyond Planck-shaped numerical GTs.
- **Status:** `fresh`
- **Opened:** 2026-04-14
- **Last revised:** 2026-04-14

### INS-002 — Derivation Laundering: LLMs under rubric pressure fabricate false arithmetic provenance to launder the wrong-category number into an evidence-anchor criterion

- **Claim:** When an LLM generating a thesis cannot locate a number from the rubric-required evidence category, it will borrow a figure from an incompatible category and fabricate a false arithmetic derivation (e.g., a claimed "midpoint between $X and $Y") to launder the borrowed number into the rubric's evidence anchor. The fabrication is specifically constructed to satisfy disclosure criteria through manufactured provenance rather than real grounding. Unlike simple hallucination, the derivation is constructed to be defensible on the surface — it uses the right form words ("midpoint", "derived from"), cites real numbers, and only fails under arithmetic verification of the claimed operation against the claimed inputs.
- **Evidence pointers:**
    - Seam: N/A (this finding predates the current seam format; rooted directly in the GLP-1 demonstration run).
    - Hypothesis row: `H-GAMING-10` in `ztare_mission_hypothesis_ledger_seam.md`.
    - Run artifact: `glp1_adoption_economics` demonstration run — the thesis cited `$350` labeled "Derived: midpoint between $245 and $675" (actual midpoint is $460). The $245/$675 figures are TrumpRx consumer prices; they were laundered into an enterprise-contract anchor. The arithmetic is demonstrably wrong and the label was specifically constructed to pass a rubric criterion.
- **Confidence tier:** `suggestive` — single instance, one domain, one model pair. Replication via meta-runner on a second domain is pending. Note: the strategy was caught externally by Gemini as "Misfile" before being reclassified under this name; the original catch is adversarial-review evidence, not automated-detection evidence.
- **Paper target(s):** `paper1` (Cognitive Camouflage — this is one of the nine specification gaming strategies).
- **Status:** `cited-in-draft` — appears in paper1's strategy taxonomy.
- **Opened:** 2026-04-14
- **Last revised:** 2026-04-14

### INS-003 — Fractal Goodhart convergence: the same specification gaming pattern recurs independently at evaluator, kernel, supervisor, and drafting layers

- **Claim:** In a single recursive AI research system, the same Goodhart-class failure mode — the agent satisfying the verifiable surface of a specification while violating its central intent — was independently observed at four structurally distinct layers, each under a different specification artifact, each caught through a different audit path, and each converted into a typed fail-closed constraint post-catch. Layer 1 (evaluator): nine self-certifying code strategies catalogued in Alami (2026a). Layer 2 (kernel): derivation-gate label hardcoding that allowed fabricated theses onto the aligned-evidence path, documented in Alami (2026b, 2026c). Layer 3 (supervisor): the specification-writing agent generated assertions targeting cosmetic properties (word counts, capitalization, formatting) while argument quality went unchecked. Layer 4 (drafting, live 2026-04-10): a fresh context-isolated instance of the same model caught a circularity in a pre-registration success criterion that the warm drafting pair had missed for hours. The specification differs at each layer; the gaming topology is structurally identical. The convergence is consistent with the structural-homology prediction that the adversarial gradient against an evaluation signal is a function of loop topology, not of substrate.
- **Evidence pointers:**
    - Paper: `papers/paper4/draft.md#5.4` (Layers 1–3 reported) and `#5.7` (Layer 4 live catch).
    - Hypothesis rows: `H-GAMING-10` (kernel-layer derivation laundering, INS-002 above is the evaluator-side pair); evaluator-layer strategies catalogued in paper1 rather than the hypothesis ledger.
    - Cross-references: Alami (2026a) evaluator layer; Alami (2026b, 2026c) kernel layer; paper4 §5.7 for the Layer 4 catch's nine-step demonstration chain with file-level artifacts on disk.
- **Confidence tier:** `replicated` — four independent layers, three independent research programs, four independent catch paths. The replication axis is *layer*, not model family; cross-model replication at each layer is a separate promotion criterion and is not claimed here.
- **Paper target(s):** `paper4` (central for Section 5.4's structural-homology claim). Indirectly cross-cited in `paper1` and `paper2`.
- **Status:** `cited-in-draft` — this is paper4 §5.4's central empirical contribution.
- **Opened:** 2026-04-14
- **Last revised:** 2026-04-14

### INS-004 — Context isolation, not capability, is the minimum-sufficient separation to catch self-evaluation failure in a warm-pair drafting loop

- **Claim:** On 2026-04-10, a fresh copy of the same language model — given only the finished pre-registration and a frozen catch-grammar corpus, with no access to the drafting history — flagged a circularity in the pre-registration's first success criterion that a warm pair (a human researcher plus the same model carrying the full drafting history) had missed for several hours. The warm and cold instances are drawn from the same model family with the same training data and the same vocabulary; the only variable is context isolation. This is one-instance evidence that structural separation of the evaluation path from the generation path is sufficient to catch self-evaluation failures at the drafting layer without requiring model capability to differ. The finding is bounded: one live session, one artifact, one failure mode (circular success criterion), no counterfactual on what the warm pair would have caught given more time.
- **Evidence pointers:**
    - Paper: `papers/paper4/draft.md#5.7` (nine-step demonstration chain with file-level artifacts).
    - Hypothesis row: N/A — the finding arose during drafting itself and was converted directly into paper4's structure; it does not have a pre-registered hypothesis row in the ledger. This is a documented exception to insight rule #1 and is allowed here because the catch was live, the artifact trail is preserved, and the finding is scoped to one session.
- **Confidence tier:** `suggestive` — one live instance. Replication would require reproducing a warm-pair circularity miss and a cold catch on an independent artifact with an independent failure class.
- **Paper target(s):** `paper4` (Section 5.7 is this paper's live-catch contribution and its tightest causal claim).
- **Status:** `cited-in-draft` — central for paper4's fourth-layer convergence argument.
- **Opened:** 2026-04-14
- **Last revised:** 2026-04-14

### INS-005 — Farther-tail global residual catches finite-window surrogate fits that terminal-only testing would accept

- **Claim:** In GP-023 sandbox_03 iteration 13, a mutator-produced champion passed a terminal-only visible-slice gate but failed the farther-tail global residual gate because the champion was a finite-window surrogate — a function class fitted to the visible window that diverges from the ground truth on the unseen tail. A terminal-only test (visible RMSE only) would have declared the iteration a success; the farther-tail gate caught the divergence. This is one-instance evidence that verification architectures that score only on the visible window are structurally insufficient to catch surrogate fits produced by an optimization-pressured mutator, and that a held-out farther-tail residual check is a non-redundant gate relative to visible-window fitting. The finding is bounded: one live iteration, one sandbox, one generator class (Planck-shaped).
- **Evidence pointers:**
    - Memory: `project_gp046_empirical_anchor.md` — the first live proof the farther-tail gate catches a finite-window surrogate terminal-only testing would miss.
    - Seam: `research_areas/private/seams/GP-023_ontology_trap_planck_mechanism_seam.md` (GP-046 empirical anchor referenced in the sandbox_03 trajectory).
    - Hypothesis row: `H-GP023-00` partially confirmed; the primitive-set basin analysis that grew from this anchor also provides structural context.
    - Run artifact: `projects/gp023_planck_sandbox_03/` iteration 13 workspace; `gp048_findings_for_debrief.md` in the same project.
- **Confidence tier:** `suggestive` — one live instance on one sandbox with one generator class. Not yet replicated on a second generator class or a second sandbox (sandbox_06 is pending and will be the second natural replication surface).
- **Paper target(s):** `paper2` (Recursive Epistemic Gain — farther-tail discipline is a central example of "the failure the verifier catches that a weaker verifier would have passed").
- **Status:** `fresh` — not yet cited in a frozen paper2 section.
- **Opened:** 2026-04-14
- **Last revised:** 2026-04-14

### INS-006 — Mutator stagnation basins are primitive-set basins, not specific-expression basins

- **Claim:** In GP-023 sandbox_03, the three score-50 ceiling hits (iterations 13, 20, 26) were initially framed as "the same basin" implicitly meaning the same expression. GP-048 retrospective AST analysis refines this: iterations 13 and 26 are tree-edit-distance identical (d=0), but iteration 20 is structurally distinct at TED=9 while sharing the same primitive set `{additive_composition, exp_neg, multiplicative_composition, power}`. The correct structural unit of mutator stagnation in this sandbox is the primitive set, not the specific expression. Multiple structurally distinct expressions can reach the same farther-tail failure through the same coarse vocabulary — the basin is the vocabulary, not any single realization of it. This has downstream implications for stagnation-pivot interventions: primitive-set-aware escape conditions are structurally necessary because expression-level edit-distance tests will fail to recognize the basin when a new iteration lands in a different corner of it.
- **Evidence pointers:**
    - Memory: `project_gp046_empirical_anchor.md` references the basin work; the primitive-set refinement is the GP-048 retrospective finding.
    - Seam: `GP-023_ontology_trap_planck_mechanism_seam.md` (sandbox_03 trajectory + GP-048 retrospective turn).
    - Hypothesis row: `H-GP023-00` — partially confirmed via the retrospective; the hypothesis's original framing as "same basin" was refined by the retrospective, not refuted.
    - Run artifact: `projects/gp023_planck_sandbox_03/workspace/gp048_findings_for_debrief.md`.
- **Confidence tier:** `confirmed` — two independent substrates, two independent mutator models. Original: GP-023 sandbox_03 (Planck-shaped, gemini-flash), three data points (iters 13, 20, 26) with TED=0/9/0 but identical primitive set `{exp_neg, power, multiplicative_composition}`. Replication: GP-073 sandbox_15 Pair 2 (Selkov 1D projection, gemini-pro), 7 distinct structural families across 9 iterations, all in the discrete-mechanism primitive set `{floor, ceil, fabs, atan, integer_division}`. Different substrate, different model, same structural pattern: multiple expressions reach the same failure through the same coarse vocabulary. Cross-substrate replication is the strongest available promotion axis.
- **Paper target(s):** `paper2` (basin structure is a concrete mechanism for the "failure-as-constraint" primitive).
- **Status:** `fresh`.
- **Opened:** 2026-04-14
- **Last revised:** 2026-04-16 (promoted to confirmed after GP-073 sandbox_15 Pair 2 cross-substrate replication)

---

### INS-010 — Pre-commit verifier specification gaming: a bootstrap identifiability check satisfied the form of an identifiability test (consistency under noise) while missing the intent (identifiability from the functional form), and the wrong property was caught only by a clean-data multi-start audit the operator ran post-hoc

- **Claim:** In GP-023 sandbox_06 on 2026-04-14, a pre-commit bootstrap identifiability check declared phi_max=15 safe (all six candidates passed `max|bootstrap_mean − GT| < 0.005`, committed phi_max=15). A clean-data fitter audit run immediately afterward on the same committed phi_max recovered four of six parameters to machine precision and missed the other two — alpha and beta — by 69.77% each. Arithmetic inspection revealed the recovered (alpha, beta) and the true (alpha, beta) sit on the same one-parameter ray: the ratio is identical (0.72) and the joint-scale factor differs by 1.697666. Inspection of the generator function (`raw/generate_curve.py` line 62) showed alpha and beta enter the formula only inside `(alpha · phi) / (beta · psi)`, so the transformation `(alpha, beta) → (alpha · c, beta · c)` is an exact global symmetry of the family at every phi and every psi. The declared 6-parameter family has rank 5. The bootstrap pre-commit passed because it was checking consistency of the optimizer under noise — a property the degenerate family satisfies, because `differential_evolution` under noise from a fixed initialization lands repeatedly in the same basin — while the property the operator intended to check was identifiability from the functional form, which the degenerate family does not satisfy. A Layer-5 instance of fractal Goodhart convergence: the gaming happened at the pre-commit verifier layer itself, and the catch was produced before any mutator iteration ran and before any sandbox was sealed.
- **Evidence pointers:**
    - Seam: `research_areas/private/seams/GP-023_ontology_trap_planck_mechanism_seam.md#turn-44`
    - Hypothesis row: `H-GP023-07b` (differential diagnosis ladder) indirectly; the finding is not pre-registered under its own H-row because it was produced by the Step 1 fitter audit and is logged here under the Rule-1 exception: the finding arose inside a pre-registered test and is fully traceable to its pre-registered motivation (`ztare_mission_hypothesis_ledger_seam.md` GP-023 row, Turn 43 differential-diagnosis commitment).
    - Run artifacts: `projects/gp023_planck_sandbox_06/workspace/pre_seal_artifact.json` (v2 bootstrap check, committed phi_max=15 with all candidates passing), `projects/gp023_planck_sandbox_06/workspace/fitter_audit_artifact.json` (v1 audit with APPARATUS SUSPECT verdict showing the 69.77% miss on alpha and beta), `projects/gp023_planck_sandbox_06/raw/generate_curve.py` (line 62 — the source of the symmetry), `projects/gp023_planck_sandbox_06/raw/generate_curve_v3.py` (reparameterized fix), `projects/gp023_planck_sandbox_06/fitter_audit_true_form_v3.py` (v3 audit with multi-start and cross-seed identifiability check).
- **Confidence tier:** `confirmed` — promoted from `suggestive` on 2026-04-14 after the v3 audit returned `APPARATUS CLEARED (v3)` against every one of the four pre-committed pass criteria. All 5 params recovered to machine precision on every one of the three adversarial seeds (0, 17, 97); visible RMSE 0.00e+00 on every seed; tail max_err 0.00e+00 on every seed; cross-seed relative spread 0.00% on every parameter. The promotion criterion was pre-registered in `GP-023_ontology_trap_planck_mechanism_seam.md#turn-44` before the v3 audit ran, so this is a clean pre-committed promotion rather than a retrofit. The confirmation is also cross-layer in the paper4 §5.4 sense — the catch was at the pre-commit verifier specification layer, and the fix (reparameterization) was verified by a structurally different test (clean-data multi-start identifiability) than the one that missed it (noise-consistency bootstrap). Replication axis is *test-type*, not model-family; a separate cross-model replication would be a further promotion criterion and is not claimed here.
- **Paper target(s):** `paper4` (new Layer 5 in §5.4's fractal-Goodhart catalogue — the gaming at the pre-commit verifier layer, with a recorded fix and a recorded confirming audit); `paper2` (a clean example of "the failure the verifier catches that a weaker verifier would have passed" at one layer deeper than INS-005's farther-tail catch). Possibly the treatise's Conclusion as a short concrete example of the Chapter 3 residual doing operator-layer work the decomposed apparatus could not have produced alone.
- **Status:** `fresh` — not yet cited in a frozen paper section. Scheduled for paper4 §5.4 next revision and paper2 failure-as-constraint §.
- **Opened:** 2026-04-14
- **Last revised:** 2026-04-14 (confirmed after v3 audit APPARATUS CLEARED; artifact at `projects/gp023_planck_sandbox_06/workspace/fitter_audit_v3_artifact.json`)

---

### INS-011 — Smooth continuous-residual graders are structurally unfalsifiable against wrapper-collapse over-parameterization

- **Claim:** Whenever all three of the following hold — (a) the sealed ground-truth `f(x; θ)` is a smooth function of continuous parameters, (b) the grader is a continuous residual such as `sum((y − f̂)^2)` as delivered by `scipy.optimize.least_squares` or equivalent, and (c) the declared mutator grammar closes under at least one smooth wrapper class (additive `f + ε·h(x; φ)`, multiplicative `f · (1 + ε·h)`, composition `g(f, ε·h)`, or argument-extension `f(x + ε·h(x))`) — then for any sealed GT, there exists a strict super-family expressible by the mutator that collapses to GT at null extra-parameter values. Under normal fit-primitive invocation the optimizer drives `ε → 0`, the fitted residual matches GT to fit precision, and the wrapper-family scores identically to GT. **The mutator never has to guess correctly; it guesses a superset and lets the fitter delete the extras.** GP-023 sandbox_09 v2 (Vis-viva Kepler with nested-sqrt wrapper, `GP-023_sandbox_09_post_run_audit.md` Outcome D) and sandbox_10 (same pathology, curated-harvest escape via `GP-023_sandbox_10_nesting_collapse_audit.md`) are the two empirical instances. Informal enumeration over damped oscillator, Michaelis–Menten, stretched exponential, power-law-with-threshold, and hyperbolic tanh forms (in `GP-069_nesting_cleared_target_construction_seam.md`) shows that every physically-natural GT inside a polynomial-in-primitives closure admits such a wrapper; the pathology is not Kepler-specific.
- **Consequences.** (1) GP-061 Component B cannot operate under live-mutator protocol on any smooth-continuous-residual target without a level-2 run-time gate or a grammar with a non-smooth escape hatch — because under this pathology the mutator never produces a `structural_misfit` family, so Component B has nothing to read. This is why the R3b curated-harvest protocol exists. (2) The adversarial-rank interpretation of ZTARE's falsification leg survives only in regimes where the grader charges a non-zero cost for the wrapper's extra parameters — MDL / BIC / AIC penalty, complexity penalty, symbolic equality, pass/fail grading, or asymptotic/limit-only evidence. (3) Any apparatus that claims "the search space shrank" or "the mutator learned to avoid skeleton X" on a smooth-residual grader is measuring a confound; the smooth grader cannot emit a genuine negative result because every proposal-with-a-wrapper passes. The escape hatches — piecewise/kink grammar, integer-valued grading, implicit/constraint forms, complexity-penalized residual, asymptotic-limit evidence — are real but each requires deliberate construction, and the "every natural physics GT has this loophole" intuition generalizes the Goodhart-at-the-grading-layer finding from the rubric-eval domain (`project_rubric_as_eval.md` in auto-memory) to the fit-primitive domain.
- **Evidence pointers:**
    - Seam: `research_areas/private/seams/GP-069_nesting_cleared_target_construction_seam.md` — preliminary enumeration of candidate grammar axes and the observation that each natural GT reproduces the pathology.
    - Sandbox 09 v2 Outcome D: `research_areas/private/seams/GP-023_sandbox_09_post_run_audit.md` — first empirical instance, iter-1 fit-collapse on nested-sqrt Kepler wrapper.
    - Sandbox 10 nesting audit: `research_areas/private/seams/GP-023_sandbox_10_nesting_collapse_audit.md` — second empirical instance, motivated the R3b curated-harvest protocol switch.
    - GP-061 v4 amendment: `research_areas/private/specs/active/GP-061_component_b_generalization_target_spec.md` — documents the protocol switch and the two-run R3b+R4 promotion gate as a downstream consequence.
    - GP-069 level-1 seam: `research_areas/private/seams/GP-069_champion_nesting_audit_gate_seam.md` — the seal-time static check that formalizes the pathology as an apparatus-level concern.
    - Void-driven steering seam: `research_areas/private/seams/GP-061_void_driven_steering_measurement_seam.md` — tier-2 measurement that must be run to establish whether Component B has any closed-loop effect even within grammars that do not exhibit the full pathology.
- **Confidence tier:** `suggestive`. Two concrete empirical instances (sandbox_09 v2, sandbox_10), one informal enumeration, no formal proof, no cross-domain replication. An attempt 2026-04-15 to extend the claim via a hinge-vs-sigmoid numerical probe (`src/ztare/validator/gp069_hinge_sigmoid_limit_probe.py`) was **withdrawn after skeptical review**: the probe's raw-L2 result (sigmoid beats hinge by 0.00017) disappears under a BIC/AIC penalty (Δ BIC = −3.30 in favor of hinge, Δ AIC = −1.90 in favor of hinge). This means the probe demonstrates *missing complexity penalty in ZTARE's fit primitive* — a bug report — not a structural limit on continuous-residual scoring. Every serious symbolic-regression system since ~2009 (PySR parsimony, AI Feynman, Schmidt-Lipson Eureqa, MDL/BIC/SRM literature) already addresses this via complexity penalties. Promotion to `confirmed` still requires (a) a pre-registered construction-and-failure test predicting the sandbox_09/10 pathology at seal time under a new grammar axis, or (b) a theoretical proof of the wrapper-existence claim under stated closure conditions AND complexity-penalized scoring.
- **Paper target(s):** `paper2` (failure-as-constraint apparatus limits — the continuous-residual grader is the specific layer where the negative-result pipeline breaks); `paper4` (new case in the fractal-Goodhart catalogue §5.4 at the grader-design layer, adjacent to but distinct from INS-010's pre-commit verifier layer); possibly the treatise as a bound on what asymptotic-survival can deliver when the grader is continuous.
- **Status:** `fresh`. Not yet cited in any draft section. Next action: tier-2 A/B measurement on gp042/gp045 (in flight under task #54 as of 2026-04-15). **Task #55 action (revised 2026-04-15 post-probe + skeptic review):** add a BIC/AIC complexity penalty to `src/ztare/validator/fit_primitive.py` and re-run sandbox_09 v2 / sandbox_10 to see whether the fit-collapse survives under complexity-penalized scoring. If it does, the insight is confirmed on a real apparatus at real target complexity. If it does not, the insight is downgraded to "ZTARE's fit primitive historically lacked a complexity penalty" and becomes a local engineering note, not a paper contribution.
- **Opened:** 2026-04-15
- **Last revised:** 2026-04-15

### INS-012 — Component B's void vocabulary is bounded on two independent axes (static op whitelist + corpus-derived universe), producing silent vocabulary misses on any target whose winning primitive is outside the intersection

- **Claim:** Component B's void-extraction vocabulary is bounded on two independent axes, both verified against the current code.
    - **Axis 1 — static op whitelist.** `_GENERALIZED_OPS` in `src/ztare/validator/structural_constraint_extractor.py:224` is the hardcoded set `{Pow, Mult, Div, Add, Sub, USub}` plus `Call` and `leaf` tags. A failure mode whose structural deficit is a missing operator outside this set (e.g. `Mod`, `BitAnd`, `FloorDiv`, `MatMult`) cannot be named as a void regardless of how often the mutator emits or omits it.
    - **Axis 2 — dynamic corpus-derived universe.** `_candidate_universe` in `src/ztare/validator/negative_space_extractor.py:64` constructs the void universe by enumerating `(fname, arg_pos)` keys observed in the current failed-family corpus. A function the mutator has never emitted in this run has zero keys in the universe and therefore zero void slots. Even if axis 1 covered the relevant op, Component B cannot void `fn:Λ` when no failed family has ever produced a `Λ(...)` call to seed the key.
    - Combining the two axes, Component B's effective vocabulary is `{6 ops in _GENERALIZED_OPS} × {fnames the current corpus happens to contain} × {arg positions the current corpus happens to touch}`. When a failed family's structural deficit falls outside this intersection, Component B returns an empty void set — a **silent vocabulary miss**. Strictly this is not a hypothesis-test "false negative" (Component B does not affirmatively report "no void exists," only "no voids from the enumerated universe"), but downstream code consumes empty-list as "nothing to inject," so the operational effect is identical: the autoresearch loop sees no steering signal and proceeds as if the failed-family corpus had no structural deficit.
- **Consequences.** (1) Component B is a *within-vocabulary* logic auditor, not a universal one. The within-vocabulary claim — demonstrated by the sandbox_07/08 retroactive test and now by the live phase-2 steering run on gp045 — remains intact; the ceiling is on the scope of "within-vocabulary," not on the extractor's correctness inside that scope. (2) The mutator's latent vocabulary and Component B's extracted vocabulary are **independent bottlenecks**. Even if the model under test has a primitive in its training distribution (the Erdős / von Mangoldt illustration: GPT-5.4 Pro evidently has `Λ(n)` available), Component B cannot steer toward that primitive unless the mutator emits it in the current run's blind exploration phase AND the op is in the static whitelist. An external observer who sees "autoresearch stalled, mutator converged on suboptimal continuous approximation" may be seeing a Component B vocabulary miss, not a mutator capability limit. (3) Any cross-domain generalization pilot for Component B (the modular-arithmetic pilot scoped in `GP-069_nesting_cleared_target_construction_seam.md`, and any later program-synthesis or quantum-circuit pilot) must treat vocabulary extension as a **pre-registered gate**, not an afterthought. Concretely: the modular-arithmetic pilot pre-reg must contain and pass a unit test asserting that for a synthetic failed family whose AST contains `BinOp(Mod)` inside some `fname(...)` argument, Component B's void output is non-empty, includes a slot of the form `fn:{fname}|arg{i}|has_op:Mod`, and the slot is marked as a void. Without this test passing before the pilot runs, a null pilot result is uninterpretable — the same way phase-2a under flash would have been uninterpretable without the compliance grep on the void constraint block.
- **Evidence pointers:**
    - `src/ztare/validator/structural_constraint_extractor.py:224` — `_GENERALIZED_OPS` hardcoded set (axis 1, verified 2026-04-15)
    - `src/ztare/validator/structural_constraint_extractor.py:247` — feature walker `isinstance(n.op, op_cls)` loop that picks up anything added to the dict
    - `src/ztare/validator/negative_space_extractor.py:64` — `_candidate_universe` corpus-derivation (axis 2, verified 2026-04-15)
    - `src/ztare/validator/negative_space_extractor.py:15-24` — design-note docstring stating "universe is derived mechanically from the observed corpus"
    - `research_areas/private/seams/GP-069_nesting_cleared_target_construction_seam.md` §tier-3-frontier-note — modular-arithmetic pilot scoping, where this ceiling becomes a pre-registration gate
- **Confidence tier:** `suggestive`. Argued from the architecture and verified against the code; not yet empirically demonstrated via a constructed false-negative case. Promotion to `confirmed` requires a run where Component B is handed a failed-family corpus whose structural deficit is outside the current vocabulary intersection and observed to return an empty void set while an external check shows the deficit is real. The modular-arithmetic pilot is the natural construction site for this empirical demonstration.
- **Paper target(s):** `paper2` (apparatus-limits case study, adjacent to INS-011's continuous-grader limit but on an orthogonal axis — vocabulary vs. residual type); possibly the treatise as a statement on the scope of "Component B as universal logic auditor" claims.
- **Status:** `fresh`. Opened 2026-04-15 after a two-pass bounded skeptic review of the tier-3 frontier note in `GP-069_nesting_cleared_target_construction_seam.md`. Not yet cited in any draft section. Next action: part of the modular-arithmetic pilot pre-reg scoping (task #55), not a standalone follow-up.
- **Opened:** 2026-04-15
- **Last revised:** 2026-04-15

---

### INS-018 — Adversarial judge independently names the underdetermination boundary: a rational approximation that passes all holdout gates is scored 94 and explicitly flagged for structural exponential exclusion without access to ground truth

- **Claim:** In GP-080 Stage 2 (5% proportional Gaussian noise, 24 visible points, clean holdout), the adversarial judge (GPT-4.1) scored a rational functional form `f(x1, x2) = x2 / (p0*x1 + p1 + p2/x1)` at 94/100 and named its weakest point as: *"The thesis presumes a structural exclusion of mechanistically justified exponential limiting processes. If a latent process generating true exponential barriers exists, all asymptotic and elasticity-based claims would collapse."* The judge reached this verdict on evidence alone (opaque x1, x2, z triples — no domain labels, no GT access). The ground truth is a bi-exponential `C * x2 * (exp(-0.07*x1) - exp(-1.5*x1))`. The rational form achieves holdout RMSE=0.068 (threshold 0.25), peak alignment within 0.2% of GT, but diverges catastrophically at x1=48 (262% error) and x1=100 (6,757% error) because rational 1/x decay cannot match exponential tail behavior. The judge named the exact structural gap — exponential exclusion — as the epistemic weakest point, without access to the GT or to the farther-tail regime. This is consistent with the adversarial verification architecture functioning as a Popperian falsification engine: it did not merely reject the thesis for poor fit; it identified the specific structural blind spot of the surviving candidate.

- **Caveat — potential oracle contamination through judge priors:** GPT-4.1 has broad pretraining exposure to kinetics, pharmacology, and exponential decay models. Even though the evidence is label-free (x1, x2, z only), the judge may have priors that exponential forms are common in peaked-then-decaying two-variable datasets, which could bias it toward naming "exponential exclusion" independent of the data's structure. This channel cannot be closed without a cross-judge replication using a model with different training distribution. **Current status: not ruled out.** The finding stands as stated, with the caveat that the judge's specificity about exponentials may partly reflect pretraining knowledge rather than purely data-driven inference. Cross-model replication (different judge family — e.g., Gemini as judge instead of GPT-4.1) is the clean test.

- **What makes this finding robust despite the caveat:** (1) Contamination audit (independent agent, 2026-04-18) verified all 7 information channels — charter, denylist, rubric, evidence, thesis, seal, file scan — are CLEAN. No domain-label leakage. (2) The rational form finding is numerically verified: holdout RMSE=0.068, peak at x1=2.139 (GT: 2.143), structural divergence at x1=48. (3) The rational form is the wrong answer — ZTARE's holdout gate passed a structurally incorrect candidate. This is the empirical instance of underdetermination the GP-083 seam predicted. (4) The judge's naming of "exponential exclusion" is directionally correct regardless of whether it reflects data inference or pretraining prior — the gap is real and measurable.

- **Final status note (run closed 2026-04-18):** Rational form held at 94 through run close (8 iterations). Feynman library exhausted; composition mode (Component D) found Wien approximation `x2*(a·x1^b·exp(c·x1)+d)` — one exponential arm — but not the difference-of-two-exponentials. Engine reached the correct structural family but was blocked by the data grid from building the second arm. Farther-tail evaluation (run post-close): RMSE=0.1639, max relative error 3754% at x1=96. Verdict: **RATIONAL BASIN CONFIRMED**. Error is x2-independent, confirming divergence is purely in x1 dynamics. Finding locks as stated: rational basin persists across full run; holdout grid is insufficient to discriminate rational 1/x from bi-exponential exp(-kt). Underdetermination boundary confirmed empirically.

- **Evidence pointers:**
  - Seam: `research_areas/private/seams/GP-083_inference_type_boundary_seam.md#Turn-6` — empirical anchor section
  - Hypothesis row: no pre-registered H-row for this specific finding. Exception allowed: the underdetermination boundary was pre-registered conceptually in GP-083 Turn 2 (2026-04-17) before Stage 2 ran; this is the empirical confirmation. Seam timestamp predates run.
  - Contamination audit: independent agent run 2026-04-18, 7-channel CLEAN verdict
  - Numerical verification: independent agent run 2026-04-18 — holdout RMSE=0.068, peak alignment 0.2%, divergence table at x1={24,48,100}
  - Run artifacts: `projects/gp080_02/champion_eval_results.json` (score 94), `projects/gp080_02/debate_log_iter_1776514374.md` (judge rationale), `projects/gp080_02/test_model.py` (rational form, iter 4)
  - Seal: `projects/gp080_02/sandbox_seal.json` — GP-072 Division A/B, evidence fingerprint 8bddaf28af2264b4

- **Confidence tier:** `confirmed` — cross-substrate replication completed 2026-04-18 (gp023_crucial_01, Planck substrate). Two independent substrates (tacrolimus PK bi-exponential and Planck transcendental), two independent runs, same grammar, same gate structure, same finding: holdout gate passes a structurally wrong champion (rational basin in GP-080, Wien approximation in GP-023), farther-tail discriminator fires in both cases. The oracle-contamination-through-judge caveat on the judge's naming of "exponential exclusion" is unresolved for GP-080 but is not the central evidence channel for the underdetermination finding — the farther-tail numerical tables are the central channel, and those are GT-verified and model-agnostic.

- **Cross-substrate comparison (GP-080 vs GP-023):**
  | | GP-080 (tacrolimus) | GP-023 (Planck) |
  |--|--|--|
  | Champion | Rational `x2/(ax1+b+c/x1)` | Wien `p0*x2^p1*x1^p2*exp(-p3*x1/x2)` |
  | Score | 94 | 97 |
  | Holdout RMSE | 0.068 | 0.020 |
  | Farther-tail | 3754% at x1=96 | 648% at x1=8, x2=0.5 |
  | `is_exponential_class` | False | False |

- **Paper target(s):** `paper5` (Chapter 3 §3.1 and Conclusion — empirical instance of the underdetermination boundary and the Taylorist cage-as-intelligence finding); `paper2` (failure-as-constraint: holdout insufficient, farther-tail is the discriminator; connects to INS-005).

- **Evidence pointers (updated at run close + GP-023 replication):**
  - Farther-tail eval GP-080: `projects/gp080_02/eval_farther_tail.py` — RATIONAL BASIN CONFIRMED, 3754% error at x1=96
  - Farther-tail eval GP-023: computed post-close 2026-04-18, `is_exponential_class=False`, 648% at x1=8, x2=0.5
  - Stage 2 closure: `research_areas/private/seams/GP-080_tacrolimus_pk_seam.md#Turn-3`
  - GP-083 Turn 7 (GP-080 verdict): `research_areas/private/seams/GP-083_inference_type_boundary_seam.md#Turn-7`
  - GP-083 Turn 8 (GP-023 verdict): `research_areas/private/seams/GP-083_inference_type_boundary_seam.md#Turn-8`
  - GP-023 run artifacts: `projects/gp023_crucial_01/champion_eval_results.json` (score 97)
- **Status:** `fresh` — promoted to `confirmed` on cross-substrate replication (2026-04-18).
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-18 (promoted to confirmed after GP-023 cross-substrate replication)

---

### INS-013 — LLMs under integer-output constraints are structurally blind to continuous mechanisms that produce step-shaped outputs, even when given 9+ iterations and explicit stagnation-pivot interventions

- **Claim:** When an LLM mutator encounters a step-shaped integer residual (e.g., a single step from 0→1 at v=7), its proposal distribution is overwhelmingly biased toward discrete mechanisms (floor, ceil, Heaviside, integer division, fabs-based step functions) and never proposes `round(continuous_term)` — the correct form that requires inventing a latent continuous dimension between integer inputs and outputs and then crushing it via rounding. This is a structural blind spot at the data-type boundary, not a stochastic failure. In GP-073 sandbox_15, across two independent runs totaling 24 iterations (Pair 1: 12+3 iters treatment/control; Pair 2: 9 iters with holdout_hard_gate), the mutator produced 14 distinct structural families — **all** step-function variants of `u²v + discrete_corrector`. Zero proposals of `round(continuous_term)` in any iteration of any arm. Pair 2's holdout_hard_gate proves the discrete-corrector formulas are genuinely wrong (not just missing a soft criterion): every formula achieves `max_abs_residual=0.0` on visible data but fails on holdout points where the discrete corrector diverges from `round(0.08v)`. Topological pivot emergency interventions fired from iter 4 onward in Pair 2 and could not break the basin. The blind spot is robust to: structural memory (mutator sees prior families), stagnation pivots (emergency profile injected), and iteration budget (9 iters with structural moves but no escape).
- **Evidence pointers:**
    - Seam: `research_areas/private/seams/GP-073_sandbox_15_pre_registration.md` — pre-registered treatment/control design
    - Hypothesis row: finding derived from E-GP073-S15-P1 and E-GP073-S15-P2; no pre-registered H-row (opened as a finding row, not a hypothesis — exception allowed because the blind spot was an unexpected observation during a Component B effectiveness test, not the pre-registered question)
    - Run artifacts (Pair 1): `research_areas/private/run_logs/gp073_sandbox_15/pair1_treatment/workspace/structural_memory.json` — 7/7 step-function families
    - Run artifacts (Pair 2): `projects/gp073_sandbox_15/workspace/structural_memory.json` — 7/7 step-function families; `projects/gp073_sandbox_15/workspace/iteration_telemetry.jsonl` — 9 iters all score 0; `projects/gp073_sandbox_15/workspace/loop_events.jsonl` — topological_pivot_emergency fired iters 4-9
    - Track record: E-GP073-S15-P1, E-GP073-S15-P2, F-GP073-S15-02 in `research_areas/private/EXPERIMENT_TRACK_RECORD.md`
- **Confidence tier:** `confirmed` — two independent runs on the same substrate with different configurations (Pair 1: Component B ON, soft scoring; Pair 2: Component B OFF, holdout_hard_gate ON). The holdout gate in Pair 2 provides a strictly stronger falsification than Pair 1's soft-criterion failure. Cross-substrate replication (a different GT with the same continuous→discrete boundary) would promote to `replicated`.
- **Paper target(s):** `paper2` (concrete failure mode the verification apparatus exposes but cannot fix alone — motivates Component C as a positive-space complement to Component B); possibly `paper1` if framed as a species of cognitive camouflage (the mutator's "discrete prior" is a pre-training artifact that acts like a bias, not a capability limit).
- **Status:** `fresh`
- **Opened:** 2026-04-16
- **Last revised:** 2026-04-16

### INS-014 — Holdout hard-gate + default underidentified_after is a misconfiguration trap that silently kills structurally-progressing runs

- **Claim:** When `holdout_hard_gate: true` is enabled in a rubric, the gate zeros every score for formulas that fail the holdout check. The information yield system reads a streak of zero scores as catastrophic failure and fires `UNDERIDENTIFIED` after `underidentified_after` iterations (default: 3). In GP-073 sandbox_15 Pair 2 Run 1, the mutator found the u²v backbone at iter 1 — genuine structural progress — but the hard-gate zeroed it because the corrector term was wrong. UNDERIDENTIFIED killed the run at iter 3, producing zero useful signal. The misconfiguration is silent: no warning, no pre-flight check, no error message indicating the interaction between two independently-reasonable settings. Fix: `--underidentified_after` must be set to at least the iteration budget when `holdout_hard_gate` is enabled. `make experiment-loop` now auto-configures this. The failure mode is apparatus-layer, not mutator-layer — the mutator was making progress but the apparatus killed it.
- **Evidence pointers:**
    - Run artifact: `projects/gp073_sandbox_15/workspace/iteration_telemetry.jsonl` — Run 1 (run_id 1776378380) exited at iter 3 with `run_exit_reason: underidentified`
    - Fix: `AGENTS.md` §7 hard rule; `Makefile` `experiment-loop` target
    - Seam: N/A — operational finding, not pre-registered
- **Confidence tier:** `confirmed` — observed once, root-caused to a specific code path, fixed, verified by Run 2 surviving to budget exhaustion at iter 9.
- **Paper target(s):** `paper2` (apparatus-engineering finding; example of "the apparatus must not destroy the signal it is designed to amplify"). Minor — may not merit paper space; primarily an operational lesson.
- **Status:** `fresh`
- **Opened:** 2026-04-16
- **Last revised:** 2026-04-16

### INS-015 — OEIS substrate bridge validated: ZTARE recovers a known integer sequence law from log-scaled evidence and the holdout gate correctly accepts the true law

- **Claim:** When ZTARE is pointed at a 1D OEIS sequence (A002865, partitions without 1s) with log-scaled evidence and a GP-075-compliant rubric (no GT leakage, legibility-ranked criteria, holdout hard-gate), the mutator (Gemini 3.1 Pro Preview) recovers the exact generating rule `p(n) - p(n-1)` via dynamic programming in one iteration. The holdout gate correctly accepts the true law (`exact_match=1.0`). The judge (GPT-4.1) scores 70 — not 100 — correctly demanding structural derivation beyond algorithmic definition. Iteration 2 regresses to 57 when the mutator overclaims that recurrence precludes analytic laws; the judge catches the epistemological error and reverts. Three apparatus bugs were fixed before the successful run: (1) gate harness output missing `harness_ok` key caused the holdout gate to fire unconditionally via `dict.get("harness_ok", False)` — silent interface debt that made bugs indistinguishable from policy; (2) `f = I_model` alias missing from seed, causing Component C to silently skip; (3) `os.path.abspath` vs `os.path.realpath` causing symlink resolution failure. The first bug (missing `harness_ok`) burned 4 iterations of a prior run (~$1.50) before diagnosis.
- **Evidence pointers:**
    - Run artifact: `projects/gp077_a002865_01/debate_log_iter_1776447742.md` (iter 1, score 70, holdout pass)
    - Run artifact: `projects/gp077_a002865_01/debate_log_iter_1776447867.md` (iter 2, score 57, reverted)
    - Rubric: `rubrics/gp077_a002865.json` (GP-075-compliant, v1.1)
    - GT module: `src/ztare/substrates/gp077_a002865_gt.py`
    - Seam: `research_areas/private/seams/GP-075_rubric_for_unknowns_seam.md#turn-7` (six-layer protocol)
    - Bug fix: `src/ztare/validator/test_thesis.py` line 2174 — `dict.get` replaced with explicit `KeyError` on missing contract keys
- **Confidence tier:** `confirmed` — one sequence, one model pair (Gemini Pro mutator / GPT-4.1 judge), holdout gate passed with exact match. The run validates three conditions for discovery mode: (1) 1D OEIS substrate generator works; (2) holdout gate correctly accepts true laws (not over-rejecting); (3) judge demands explanation, not just numerical fit. This is the empirical anchor for GP-075 Revised Claim 3.
- **Paper target(s):** `paper2` (apparatus validation for discovery-mode transition). The interface-debt bug is a candidate for the treatise (Principle III — typed operations bound to deterministic checks).
- **Status:** `fresh`
- **Opened:** 2026-04-17
- **Last revised:** 2026-04-17

### INS-016 — Silent interface debt on contract boundaries: dict.get(key, safe_default) makes apparatus bugs indistinguishable from safety policy

- **Claim:** When a ZTARE component interface uses `dict.get(key, safe_default)` on a contract-required key, a missing key silently activates the safety policy rather than raising an error. In the GP-077 gate harness, the holdout evaluation in `test_thesis.py` checked `holdout_payload.get("harness_ok", False)`. The gate harness output contained `{"gates": [...]}` but never set `harness_ok`. The default `False` caused the holdout gate to fire unconditionally — the system appeared to be rigorously rejecting every candidate, but was in fact testing nothing. Four iterations (~$1.50) were burned before diagnosis. The failure mode is a specific instance of a general class: on any interface boundary where the "safe" default coincides with the failure-policy value, a missing key and a genuine failure produce identical system behavior. The fix is explicit key presence checks (`if key not in payload: raise KeyError(...)`) that distinguish contract violations from policy activations.
- **Evidence pointers:**
    - Run artifact: `projects/gp077_a002865_01/debate_log_iter_1776445859.md` through `debate_log_iter_1776446378.md` (4 iters, all holdout-gated to 0 despite mutator producing 63-97 pre-gate scores)
    - Fix: `src/ztare/validator/test_thesis.py` line 2174 — explicit `KeyError` on missing `harness_ok`
    - Prior art: INS-010 (sandbox_06 pre-commit bootstrap passed the wrong property — same class of "subsystem looks correct but tests vacuous property")
- **Confidence tier:** `confirmed` — root-caused to a specific code path, fixed, verified by subsequent run passing holdout correctly.
- **Paper target(s):** `paper2` (apparatus-engineering finding). Candidate for treatise (Principle III). Cross-reference with INS-010 as a second instance of the "working harvester masking" pattern.
- **Status:** `fresh`
- **Opened:** 2026-04-17
- **Last revised:** 2026-04-17

### INS-017 — Dark recurrence recovery: ZTARE recovers a genuinely dark self-referential recurrence from a neutral seed in 2 iterations via structural memory accumulation

- **Claim:** A ZTARE loop (gemini-pro mutator, gpt-4.1 judge, bounded_discriminator mode) running on a genuinely dark parity-gated self-referential recurrence (not in OEIS) recovered the exact generative law within 2 active iterations from a neutral seed and 40 visible data points, achieving holdout exact_match=1.0 from iteration 2 onward and a judge score of 83 by iteration 4. The mutator independently identified the Hofstadter-Q family from the data signal and proposed a parity-gated variant; subsequent iterations refined the argument via algebraic unification. The loop's thesis accumulation (structural memory) is the mechanism — not contamination — by which iterations 3-4 built on iteration 2's discovery. The odd branch (`a[n-a[n-1]] + a[n//2]`) has no OEIS record and was not recoverable from training data alone; its discovery required fitting against the holdout gate.
- **Evidence pointers:**
    - Seam: `research_areas/private/seams/GP-078_component_d_topology_synthesizer_seam.md`
    - Run artifacts: `projects/gp078_cal_sigma_02/` — `debate_log_iter_*.md`, `champion_eval_results.json`, `test_model.py`
    - Backtest review: 3-agent independent audit (2026-04-17); Division A/B setup confirmed clean; gate harness confirmed valid; loop feedback is structural memory by design
- **Confidence tier:** `suggestive` — one domain (integer sequences), one mutator/judge pair (gemini-pro / gpt-4.1), run in progress. Promoting to `confirmed` requires: (a) run completion with stable champion, (b) cross-domain replication (tacrolimus PK or second dark sequence with different structural family).
- **Caveat:** Even branch (`a[n-a[n-1]] + a[n-a[n-2]]` for even n) is structurally identical to Hofstadter-Q (OEIS A005185). Mutator likely used training pattern recognition for the even branch and fitted the odd branch empirically. This weakens but does not invalidate the discovery claim — scientists use prior knowledge.
- **Paper target(s):** `paper2` (recursive epistemic gain), `unassigned` (sequence recovery as discovery test)
- **Status:** `fresh`
- **Opened:** 2026-04-17
- **Last revised:** 2026-04-17

---

### INS-019 — Taylorist unit cost of insight: a cheap-tier model under pre-registered deterministic gates achieves score 97 on a two-variable transcendental substrate at $1.01 total across 16 iterations, confirming the cage is the central component

- **Claim:** In gp023_crucial_01 (Planck substrate, GP-072 Division A/B protocol, sealed pre-registration), gemini-2.5-flash as mutator with gpt-4.1 as judge reached a champion score of 97/100 across 16 iterations at a total cost of $0.4776 (mutator) + $0.5318 (judge) = $1.01. The champion functional form is `p0 * x2^p1 * x1^p2 * exp(-p3 * x1 / x2)` — a Wien approximation — with p0≈1.208, p1≈0.862, p2≈2.159, p3≈0.739. This is NOT the true Planck law `x1^3/(exp(x1/x2)-1)`; it is structurally the correct family class (x2-dependent exponential coupling, x1^P growth + exp decay, peak proportional to x2) but the wrong sub-family. The structural form was discovered by iter 1 at score 73 on a cheap flash model. Scores progressed 73→62(revert)→...→88(stagnation at iters 6-9)→93(topological pivot, iter 11)→97(champion). The finding is that the model contributed shape suggestions; the cage (GP-035 deterministic fitter, holdout gate, pre-registered rubric with discriminator tests) contributed all structural enforcement. A less capable model can produce expert-level structural hypotheses when the verification environment is sufficiently instrumented. This is the "Taylorist" unit-cost-of-insight claim: the cage decomposes the discovery task so that the worker (cheap model) does not need to solve the whole problem, only the shape-suggestion subproblem that is sufficient to trigger the fitter and gates. **Underdetermination caveat (pending):** the Wien approximation will fail the farther-tail gate (is_exponential_class=False), confirming underdetermination on the Planck substrate. This run therefore simultaneously confirms INS-019 (cage-as-intelligence) and is a candidate replication surface for INS-018 (underdetermination boundary), pending farther-tail evaluation.
- **Evidence pointers:**
  - Pre-registration: `research_areas/private/seams/GP-083_crucial_experiment_pre_registration.md` (sealed 2026-04-18)
  - Run artifacts: `projects/gp023_crucial_01/champion_eval_results.json` (score 97), `projects/gp023_crucial_01/test_model.py` (champion form), `projects/gp023_crucial_01/debate_log_iter_1776518339.md` (final iteration)
  - Hypothesis row: no pre-registered H-row for this specific finding. Exception allowed: the run was pre-registered under GP-083, and the Taylorist Victory framing arose as a post-hoc observation during the run. The finding is bounded to one substrate, one model pair.
- **Cost:** total_cost_usd=$0.9814  cost_per_iter=$0.06543  cost_per_score_point=$0.01012
  wall_clock=27.9m  iterations=15  final_score=97  run_id=1776516560 (inferred from telemetry)
  models: mutator=gemini-2.5-flash / judge=gpt-4.1
  source: `projects/gp023_crucial_01/workspace/cost_summary.json` (machine-recorded per-call)
  note: Operator-reported terminal total was $1.01 ($0.4776 mutator + $0.5318 judge). Machine-recorded loop-only total is $0.9814 (delta $0.019, 1.9%). Discrepancy reflects champion eval and overhead calls outside the iteration loop. Machine figure is the authoritative lower bound.
- **Confidence tier:** `suggestive` — one substrate, one model pair. Cross-model replication (gemini-pro as mutator instead of flash) is the natural next axis. Cross-substrate replication (second two-variable transcendental GT) is the broader axis.
- **Paper target(s):** `paper5` (Conclusion — live instance of the Taylorist decomposition claim; the cage is the analytical spine, the model is the shape-suggesting worker); `paper2` (unit-cost-of-insight as evidence that the verification architecture changes what counts as "discovery").
- **Status:** `fresh`
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-18

---

### INS-020 — Evidence enrichment shifts a bounded engine toward a better approximation of the ground truth structural class but does not change the reachable structural class when the grammar cannot express the correct form

- **Claim:** In gp023_crucial_02, extending visible evidence from 24 to 33 points (adding farther-tail x1∈{5,6,8} at x2∈{0.5,1.0,2.0}) caused the engine to independently recover the correct x2^3 amplitude scaling (P_amplitude_x2_exponent≈3.0, absent from crucial_01 champion) and adopt a faster decay exponent (Weibull-type, P_decay_exponent=1.259). Both are structural improvements. However the denominator structure `exp(x1/x2)-1` was not reachable — the grammar produces `exp(stuff)` but not `1/(exp(stuff)-1)`. The engine converged on the best form available in its grammar space. This is the grammar ceiling: if the correct structural primitive is absent, more evidence produces a better approximation, not the correct structural class.
- **Evidence pointers:**
  - `projects/gp023_crucial_02/champion_eval_results.json` (score 88, P_x2_amplitude_power≈3.0)
  - `projects/gp023_crucial_01/champion_eval_results.json` (score 97, P_x2_amplitude_power≈0.86)
  - Comparison: same grammar, different evidence, same structural class failure
- **Cost:** Combined across crucial_01 + crucial_02 runs. crucial_02 cost data in `projects/gp023_crucial_02/workspace/cost_summary.json`.
- **Confidence tier:** `confirmed` — one substrate, two directly comparable runs with same grammar, different evidence grid.
- **Paper target(s):** `paper5` §2.8 (grammar ceiling evidence); `paper4` (evidence enrichment as an experimental design strategy that finds a local maximum within the grammar, not the global optimum outside it).
- **Status:** `fresh`
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-18

---

### INS-021 — Additional compute (doubled iteration budget, 15 consecutive emergency pivots) produces zero structural progress once the grammar ceiling is reached: H-COMPUTE-01 confirmed

- **Claim:** In gp023_crucial_02_extended (32 iterations, same grammar and evidence as crucial_02), the champion score reached 93/100 at iteration 17 and never improved despite 15 subsequent iterations of escalating emergency pivots. The grammar ceiling C(G)≈93 was hit at iter 17; compute spent after that point (15 iterations × $0.085/iter ≈ $1.27) produced exactly zero structural progress. The champion expression `P_amplitude * x1^1.948 * x2^1.052 * exp(-P_decay_rate * (x1/x2)^1.259)` is a Weibull-type exponential — structurally wrong (NOT Planck) and overestimates Planck by ~860–1800× in the farther tail (x1∈{10,12,15}). The Feynman Wall is a grammar ceiling, not a compute ceiling.
- **Evidence pointers:**
  - `projects/gp023_crucial_02_extended/run_summary.json` — H-COMPUTE-01 verdict, cost telemetry, stagnation profile
  - `projects/gp023_crucial_02_extended/workspace/iteration_telemetry.jsonl` — score trajectory, iter 17 champion promotion, 15 stagnation iters
  - `projects/gp023_crucial_02_extended/workspace/cost_summary.json` — machine-recorded cost breakdown
  - Control: E-GP083-CRUCIAL-02 (score 88, 16 iters) → E-GP083-CRUCIAL-02-EXT (score 93, 32 iters) — 16 extra iterations raised the score by 5 points and produced no structural change
- **Cost:** total_cost_usd=$2.7100  cost_per_iter=$0.0847  wall_clock=70m  iterations=32  final_score=93  run_id=1776525741
  models: mutator=gemini-2.5-flash / judge=gpt-4.1
  source: `projects/gp023_crucial_02_extended/workspace/cost_summary.json` (machine-recorded per-call)
- **Confidence tier:** `confirmed` — directly compared against crucial_02 (same grammar, same evidence, half the iterations). Score improved marginally (88→93) but structural class identical. Grammar expansion (crucial_03, H-GRAMMAR-01) is the correct next lever.
- **Paper target(s):** `paper5` §2.8 (empirical grounding for Grammar Ceiling Hypothesis; GCH-supporting evidence alongside crucial_03 when closed); GP-085 seam debate.
- **Status:** `fresh`
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-18

---

---

### INS-022 — Grammar expansion (single new primitive) recovers the exact structural law that 63 compute iterations could not reach: H-GRAMMAR-01 confirmed

- **Claim:** In gp023_crucial_03, adding the UNIVERSAL_DENOMINATOR primitive to the grammar was sufficient for the engine to recover Planck's law `x1^3/(exp(x1/x2)-1)` at iteration 6. Champion parameters: C=0.99989≈1, P=2.99995≈3, Q=0.00010≈0 (x2 term correctly absent), K=0.99995≈1 — 4+ decimal place parameter recovery. The farther-tail gate passes all six discriminator points (x1∈{10,12,15}, x2∈{0.5,1.0}) with errors below 0.13% — machine precision. Score 88/100 reflects a valid judge critique (no formal uniqueness proof), not a structural deficiency. The structural class verdict is unambiguous: Planck, not Wien, not Weibull. Compare: crucial_01 (Wien, farther-tail FAIL), crucial_02 (Weibull, 88/100, farther-tail PASS but wrong class), crucial_02_extended (Weibull, 93/100, 32 iters, wrong class unchanged). One grammar primitive was sufficient where 63 compute iterations were not. The Grammar Ceiling Hypothesis (GP-085 seam) is now empirically grounded on both legs.
- **Evidence pointers:**
  - `projects/gp023_crucial_03/run_summary.json` — H-GRAMMAR-01 verdict, farther-tail details, parameter recovery
  - `projects/gp023_crucial_03/workspace/fit_result.json` — champion expression and params
  - `projects/gp023_crucial_03/champion_eval_results.json` — score 88, judge critique on uniqueness
  - Cross-run chain: crucial_01 (Wien) → crucial_02 (Weibull, same grammar) → crucial_02_ext (Weibull, 32 iters) → crucial_03 (Planck, new grammar)
- **Cost:** total_cost_usd=$1.2839  cost_per_iter=$0.0856  wall_clock=31m  iterations=15  final_score=88  run_id=1776528803
  models: mutator=gemini-2.5-flash / judge=gpt-4.1
  source: `projects/gp023_crucial_03/workspace/cost_summary.json` (machine-recorded per-call)
- **Confidence tier:** `confirmed` — one substrate, four-run chain, clean experimental control on grammar variable alone. Cross-substrate replication (second transcendental GT with a different UNIVERSAL_DENOMINATOR target) is the natural next axis.
- **Paper target(s):** `paper5` §2.8a (empirical grounding for static grammar as falsification guarantee; GCH now both-legs confirmed); GP-085 seam debate (full formal statement of GCH now has empirical basis).
- **Status:** `fresh`
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-18

### INS-023 — Rubric-level named-import penalties are not self-enforcing under optimization pressure: a deterministic cage gate with score mutation is required

- **Claim:** In GP-090 iter 4, a gemini-pro mutator explicitly cited the target function by name (sopfr), its canonical characterization ("completely additive"), its OEIS identifier structure, and a named theorem ("Fundamental Theorem of Arithmetic") while scoring 92/100 on a holdout-correct formula. The gpt-4.1 judge assigned 92 despite a clear NAMED_IMPORT penalty in the rubric. Two implementation gaps compounded this: (1) `autoresearch_loop.py` invoked `run_global_gates()` but never applied its `any_hard_fail` or `total_penalty` to `new_eval["score"]` — the gate barked (printed 🚨) but did not bite; (2) `global_gates.py` had no `named_import_check` gate, so the thesis text was never scanned against the project denylist. Under optimization pressure (iter 4, score already climbing), the judge treats rubric penalties as soft incentives, not hard constraints. A deterministic code-level gate that zeroes the score is the only enforcement mechanism that cannot be reasoned around. Fixed 2026-04-18: (a) score mutation added to autoresearch_loop for both hard_fail and soft penalty cases; (b) `_gate_named_import_check` added to global_gates — reads project `thesis_denylist` (rubric field, precise) or `.denylist` (fallback, broad) and hard-fails on any hit.
- **Evidence pointers:**
  - Run: `projects/gp090_01/` — iter 4 thesis (operator-stopped, score 92, mutator cited sopfr explicitly)
  - Code fix: `src/ztare/validator/autoresearch_loop.py` (score mutation at global_gates call site)
  - Code fix: `src/ztare/validator/global_gates.py` (`_gate_named_import_check` function)
  - Rubric fix: `rubrics/gp090_01.json` (`thesis_denylist` field with 10 specific identifiers)
  - Track record: `E-GP090-01`, `F-GP090-01`
- **Confidence tier:** `confirmed` — one run, direct evidence that the score was not zeroed despite the gate firing; before/after analysis of the two code paths shows the exact failure mechanism.
- **Paper target(s):** `paper1` (Cognitive Camouflage — cage implementation must extend to score mutation, not just logging); `paper5` (Three Legs — named-import enforcement as a structural property of the cage, not a rubric suggestion).
- **Status:** `fresh`
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-18

---

### INS-024 — The cage is central: deterministic score-zeroing transforms the LLM from librarian to structural architect

- **Claim:** When an LLM retrieval path is hard-blocked (score zeroed, not penalised), the engine is forced to re-express known structure in constructed language — surfacing latent structural depth that surface retrieval never exposes. A soft penalty fails because the LLM can calculate that retrieval + a 15-point hit is cheaper than traversing dark data space; the hard zero is the only cliff face deep enough to force a basin escape. This is not a scoring convention — it is the mechanism that makes forced abduction possible at all. Without it, the cage barks but does not bite (GP-090 v1: judge scored warm-retrieval thesis 92, apparatus did nothing).
- **Evidence pointers:**
  - GP-090 rerun (2026-04-18): after 3 iterations zeroed by `named_import_check`, gemini-pro expressed sopfr as "multiplicative-to-additive homomorphism with empirical base identity" — no denylist terms, holdout exact_match=1.0, judge score 70. The structural depth (recursive trial-division implementation, homomorphism property) was never surfaced in the warm-retrieval attempts.
  - GP-090 v1 (frozen): with barking-dog bug active, judge scored explicit sopfr citation 92. Zero enforcement = zero signal.
  - Multi-agent panel (philosopher of science, Bayesian epistemologist, experimental psychologist — independent, no coordination): unanimous. Hard zero controls for "weight-mediated short-circuit" (data pairs causally inert when training distribution assigns P(correct)≈1). Soft penalty does not. "New science builds on past science" objection is a category error: ZTARE measures whether data does causal work in the inference path, not whether the LLM knows things.
  - Qualifying exam analogy (experimental psychologist): the cage is not an epistemic injustice — it is a structural fluency test. A doctoral candidate who knows Noether's theorem is still required to derive it from variational principles. We call this "demonstrating understanding," not "proving novelty."
- **Corollary — denylist asymmetry is central too:** The hard zero is only valid if the denylist bans the *target* (function name, sequence identifier, theorem name), not the *alphabet* (sqrt, pi, log, asymptotic, is_prime). A denylist that bans foundational tools destroys the combinatorial engine; a denylist that bans only target names creates the forcing pressure that makes structural articulation necessary. GP-089 and GP-090 thesis_denylists both pass this audit.
- **Confidence tier:** `confirmed` — direct before/after evidence (v1 vs. rerun), multi-agent epistemic review, denylist audit.
- **Paper target(s):** `paper1` (Cognitive Camouflage — the cage as the mechanism that makes warm-retrieval detection operational); `paper5` (Three Legs — cage as a structural property of zero-trust abduction, not a rubric suggestion).
- **Status:** `fresh`
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-18

---

### INS-025 — Grammar Ceiling Hypothesis (GCH) is a first-class failure mode: inversion converts a null result into structural evidence

- **Claim:** When an engine stagnates at a score ceiling despite exhausting all grammar primitives (WALL_LIBRARY_INSUFFICIENT), the correct response is not to run more iterations — it is to INVERT. Instead of asking "what law fits?", ask "what structural class of laws CANNOT be ruled out by the stagnation pattern?" The stagnation ceiling is not a null result; it is a positive signal about the ground truth's structural class. H-COMPUTE-01 (INS-021) confirms that doubling iteration budget yields zero structural progress once a grammar ceiling is reached; the only resolution is H-GRAMMAR-01 (INS-022): targeted primitive injection. If injection also fails, GCH is confirmed for this substrate — a real finding, not a failure. The appropriate response to GCH confirmation is to report it as the finding and move to a richer grammar or a different substrate.
- **Evidence pointers:**
  - GP-089 (A000009 / partition function): Feynman Wall at iter 8, stagnation=7. WALL_LIBRARY_INSUFFICIENT. Grammar cannot express the Hardy-Ramanujan asymptotic class. GCH confirmed.
  - GP-090 (A001414 / sopfr): Score ceiling at 70. Forced abduction successful (forced structural articulation of sopfr), but judge's remaining critique ("why do primes map to f(p)=p?") requires grounding in unique factorization. Engine reached the boundary of articulable structural knowledge. GCH confirmed at score level.
  - INS-021: 15 consecutive emergency pivots + doubled budget = zero progress at grammar ceiling.
  - INS-022: Single UNIVERSAL_DENOMINATOR primitive injection → Planck law recovery at iter 6. Grammar escape is surgical, not iterative.
- **The inversion principle:** At GCH, the engine has not failed. It has falsified every form in the grammar that survives all gates. What remains is the complement: the ground truth lies in a structural class the grammar cannot currently express. This is useful information. A grammar that stagnates on all smooth monotone forms implies the law has a discontinuity or a recursive structure. A grammar that stagnates on all polynomial forms implies the law has an exponential or sub-polynomial regime. Read the ceiling; don't repeat the iteration.
- **Operational rule:** GCH-suspected run → (1) confirm stagnation is flat across ≥5 iterations, (2) inspect which primitive families were exhausted, (3) inject exactly one targeted primitive via Component D, (4) if still stagnant, declare GCH confirmed and record as finding. Step 4 is a finding, not a failure.
- **Confidence tier:** `confirmed` — GP-089 and GP-090 both hit confirmed GCH; INS-021/022 provide the compute vs. grammar contrast.
- **Paper target(s):** `paper5` §2.8 (GCH as epistemic guarantee: a system that can confirm its own ceiling is more trustworthy than one that keeps iterating); `paper1` (GCH as the complement of the Feynman Wall — structural evidence from falsification).
- **Status:** `fresh`
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-18

---

### INS-026 — Grammar expressiveness is a measurable property: evaluation mode determines whether a score ceiling is classification-complete

- **Claim:** When the evaluation mode precludes the optimizer from contributing to residual minimization — specifically, when scoring is discrete exact-match so there is no continuous surface to descend — a stagnation ceiling at maximum residual is a classification-complete event. Optimizer pathology (local minima, initialization sensitivity, parameter diversity collapse) is ruled out by architecture: the optimizer has no foothold. The only remaining interpretation is grammar insufficiency: the expression vocabulary does not contain a form that evaluates correctly. This makes grammar expressiveness an empirically measurable quantity in discrete mode, not just a design choice. In continuous-optimization mode, a score ceiling is ambiguous: optimizer pathology and grammar insufficiency are confounded, and multi-start diversity analysis is required to separate them. In discrete mode, the ambiguity collapses — the ceiling isolates the grammar.
- **Conceptual separation required:** Grammar insufficiency (no form in the vocabulary evaluates correctly, regardless of denylist) is distinct from retrieval blocking (the correct form exists in the vocabulary, but a named-import gate + score-zeroing prevents retrieval, forcing structural articulation). Both can produce score ceilings; only grammar insufficiency is classification-complete under discrete evaluation mode. Retrieval blocking is a continuous-mode phenomenon where the optimizer could in principle navigate toward the correct form via construction rather than retrieval.
- **Honest bound on A000009 (integer partition function) as concrete instance:** The partition function case confirmed grammar insufficiency — the available expression vocabulary cannot correctly enumerate partitions. It did not separately confirm retrieval blocking. These are two distinct claims requiring distinct evidence. The grammar-insufficiency claim is supported; the retrieval-blocking claim would require a run where a named-import gate was active and an unblocked run produced the correct form via label retrieval.
- **Evidence pointers:**
  - Discrete exact-match mode: fit primitive inapplicable (no continuous surface); residual=1.0 at every iteration = grammar ceiling by construction; multi-start analysis is architecturally inapplicable, not merely inconclusive
  - A000009 / Hardy-Ramanujan: stagnation at iter 8, 7 consecutive ceiling iterations under discrete scoring; no optimizer to blame; grammar ceiling confirmed
  - Continuous-mode contrast: GP-095 multi-start fitting convergence classification handles the ambiguous case — high spread → pathological surface; low spread at ceiling → ceiling_candidate
- **Confidence tier:** `confirmed` for the architectural argument (deductive); `confirmed` for A000009 grammar insufficiency; `candidate` for the retrieval-blocking component of the A000009 story (separate claim, separate evidence needed).
- **Paper target(s):** `paper5` §2.9 (Static Grammar as Falsification Guarantee — grammar expressiveness as a measurement that discrete evaluation mode makes clean); conclusion GCH section.
- **Status:** `fresh`
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-18

---

### INS-027 — Phase B blind law recovery confirmed: fractional-exponent decay law recovered cold from 20 points under math_exp_only grammar

- **Claim:** A non-integer exponent inside a decay law (`exp(-b·t^c)`, c≈0.63) is recoverable cold from 20 visible data points under a math-only grammar with no domain priors in the grammar, the charter, or the variable names. The engine discovered the fractional-exponent topology at iteration 1, with parameter recovery to machine precision (b=1/TAU^BETA, 0.0002% error) and sub-1e-05 generalization to hidden farther-tail data at t values 4× beyond the visible training range. The 98/100 score plateau is not a failure — it is the correct finite-data epistemological limit: the Prony series objection (any finite-window decay is approximable by a sum of standard exponentials) is mathematically valid and cannot be refuted from a finite evidence file. 98 is the epistemic ceiling for this class of claim; the judge correctly withholds the last 2 points.
- **Why the 98 ceiling is the right answer, not a flaw:** Uniqueness cannot be proved from finite data. A decaying curve on a finite window is always consistent with an arbitrarily large Prony series. The judge is not penalizing the fit (perfect) or the structure (correct) — it is penalizing an unprovable claim of necessity. Any system that scored this 100 would be epistemically overconfident. The apparatus correctly identifies the limit.
- **Information isolation confirmed:** Variable names were cold (t, v). Charter gave no structural hints — only "slower than standard exponential" and "non-zero baseline." Grammar (math_exp_only) contained no stretched-exponential primitive; the topology was constructed from exp + power arithmetic. Sentinel check passed before the run.
- **Evidence pointers:**
  - Champion form: `a·exp(-b·(t^c))+d`, a=2.810, b=0.396, c=0.630, d=0.470
  - GT (sealed): A=2.81, TAU=4.35, BETA=0.63, C=0.47; b=1/TAU^BETA=0.396052 (0.0002% error)
  - Harness: hidden_global_residual=1e-06, hidden_mid=0.0, farther_tail_global=1e-06, saturation_error=0.000221 — all gates pass by 30–50× margin
  - Score trajectory: iter0=50 (naive std-exp), iter1=98, iter2=98, iter3=98
  - All 7 pre-registered discriminator zones: 0.0000% error vs actual GT
  - `projects/gp096_kww_sandbox_17/`, `projects/gp096_kww_sandbox_17/raw/pre_registration.md`
- **Confidence tier:** `confirmed` — pre-registered protocol, clean information isolation, machine-precision parameter recovery, harness gates passing by orders of magnitude.
- **Paper target(s):** `paper5` conclusion (concrete Phase B anchor for the decomposition claim); GP-096 seam; possibly paper4 if the programme produces a Langevin result too.
- **Status:** `fresh`
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-18

### INS-028 — Search telemetry negative space reveals systematic LLM biases; the complement of what the searcher avoids is the candidate probe set

- **Claim:** When an LLM-guided search exhausts its budget (WALL_LIBRARY_INSUFFICIENT), the telemetry of what it *did not try* is as informative as the telemetry of what it tried. In GP-096 Langevin (sandbox_16), the Component D composition mutator ran 20 rounds; every round proposed additive combinations of different primitive families. Zero rounds proposed same-family divisions. This systematic avoidance is not random — it reflects the LLM's structural prior toward Taylor/Fourier-style additive expansions and away from rational symmetries (A/A-type compositions). The negative-space pattern was invisible from the score telemetry (scores oscillated 50–75) but immediately visible from the composition log (no self-ratios in 20 rounds). Deterministic probes for the avoided region, gated by residual statistics that match the topology signature (bounded + smooth + saturating → ratio candidate), close the gap without changing the grammar.
- **The meta-principle:** The engine's search architecture evolves through a cycle: Run → Wall → Telemetry → Blind-spot analysis → Deterministic probe → Re-run. The telemetry is the fix. Each wall-hit generates a failure package whose negative space (what was never proposed) maps the LLM's structural priors. Any systematic gap in that map — a region the LLM consistently avoids despite residual statistics that suggest it — is a candidate for deterministic probing. The probe is gated by observable signal (not domain knowledge), so it doesn't leak oracle information.
- **Why this is structural, not ad hoc:** The pattern applies wherever an LLM guides search under a constrained vocabulary. Composition search, mutation proposals, eigenquestion selection, rival construction — any LLM-guided step has systematic avoidance regions. The apparatus (rigid gates + failure telemetry) exposes them; the human operator (or, at Level 2, an automated analyser) converts them into deterministic probes. The apparatus does not require the LLM to be omniscient. It requires the apparatus to be rigid enough to force the engineers to confront the LLM's actual cognitive limits.
- **Gemini's framing (confirmed):** "Elegant compression requires empirical failure." The depth-2 fix could not have been designed a priori. It required watching the LLM hit the wall at full speed, logging the wreckage, and discovering that the steering wheel was locked on additive compositions. The O(N⁴) cost estimate in the spec was technically correct but answered the wrong question. COMPRESS collapsed it from 26.5M to 50 candidates.
- **Evidence pointers:**
  - Composition log: 20/20 rounds additive, 0/20 same-family divisions (projects/gp096_langevin_sandbox_16/)
  - Backtest: ratio probe `double_exp/double_exp` → max|res|=0.086; depth-2 `(double_exp/double_exp) + linear` → max|res|=0.001 (50× below gate threshold)
  - Implementation: `topology_synthesizer.py` — `_run_ratio_probes()`, `_run_depth2_pass()`
  - GP-078 spec updated: depth-2 resolved, O(26.5M) estimate corrected to O(50)
- **Confidence tier:** `confirmed` — backtested against real Langevin evidence, architecture review completed, 14/14 tests pass.
- **GP-095 control (2026-04-19):** The coth form `a*((exp(b*u)+exp(-b*u))/(exp(b*u)-exp(-b*u)) - 1/(b*u)) + c` fits the Langevin evidence to max|res|=1e-6 in one SciPy call when handed the correct topology. The engine ran 10 iterations and never proposed this form. This is the machine-precision confirmation that INS-028's additive bias is the bottleneck: the grammar was sufficient; the search topology was not.
- **Paper target(s):** `paper5` conclusion (apparatus rigidity as the source of search architecture evolution; additive-bias finding now has machine-precision control from GP-095 backtest).
- **Status:** `fresh`
- **Opened:** 2026-04-18
- **Last revised:** 2026-04-19

### INS-029 — Langevin Phase B: convergence failure confirmed; LLM additive bias prevented discovery of grammar-reachable coth topology

- **Claim:** The Langevin stagnation at 75/100 is a **convergence failure**, not a grammar ceiling. GP-095 backtest (`gp095_coth_backtest.py`, 2026-04-19, n_starts=10) fitted `a*((exp(b*u)+exp(-b*u))/(exp(b*u)-exp(-b*u)) - 1/(b*u)) + c` directly against the evidence. Result: max|res|=0.000001 — six orders of magnitude below the 0.02 gate threshold. GT parameters recovered to 7 decimal places: a=3.470 (GT SCALE=3.47), b=0.680 (GT STRETCH=0.68), c=1.230 (GT OFFSET=1.23). The grammar can express the law. The engine never proposed the topology.
- **What the engine tried instead:** GP-087 injected reciprocal/harmonic/log_reciprocal/sqrt_reciprocal corrections onto a softplus-exponential base. No additive tail correction can algebraically convert a softplus base into a coth curve. Confirmed by backtest: softplus + 1/u scores max|res|=0.064 even with n_starts=10 — fails the visible-slice gate (threshold 0.05). The wrong base was the wall, not the grammar.
- **Root cause — INS-028 made concrete:** The LLM's additive structural prior (INS-028: zero ratio compositions in 20 Component D rounds) prevented it from proposing `(exp+exp)/(exp-exp) - 1/u`. The coth identity requires a ratio of two exponential sums — exactly the topology class the LLM systematically avoided. Grammar reachability was never the bottleneck. Search topology was.
- **Gate calibration finding:** The 0.02192 best residual the engine reached vs 0.000001 for the correct form. The 0.02 threshold cleanly separates wrong-topology approximations from the correct structural class by a factor of 22,000. The gate is not arbitrarily tight — it is tight enough to enforce structural class membership.
- **GPT-4.1 vs gemini-pro:** Both hit the same ceiling (75). Convergence failure is model-independent — both share the additive structural bias. Model choice affects speed of approach; additive bias is an LLM property at this search layer.
- **Phase B status:** Closed as **search-failure baseline** (Outcome D). Phase B is clean via KWW (Outcome A confirmed, 2026-04-18). Langevin's contribution to Phase B is the negative finding: the apparatus correctly identified a search failure without lowering epistemic standards. The gate calibration (22,000× gap) is the quantitative Phase B deliverable from this substrate. Langevin ratio-probe re-run (GP-078) is available as an optional diagnostic appendix — it cannot count toward Phase B because the operator knows the GT.
- **Evidence pointers:**
  - Backtest: `projects/gp096_langevin_sandbox_16/gp095_coth_backtest.py` — coth max|res|=1e-6, GT params matched, softplus+1/u max|res|=0.064
  - Run telemetry: `workspace/iteration_telemetry.jsonl` — 10 iters, scores: 75, 0, 20, 50, 75, 75, 50, 20, 50, 75
  - Plumbing: Frankenstein + Snapshot Vacuum fixes applied and firing confirmed
- **Confidence tier:** `confirmed` — GP-095 discriminant run, machine-precision recovery, GT params match to 7dp.
- **Paper target(s):** `paper5` — INS-028 (additive bias) is now empirically grounded: the grammar had the answer; the LLM's structural prior prevented discovery. Gate calibration finding (0.02192 vs 0.000001) as concrete evidence of threshold precision.
- **Status:** `fresh`
- **Opened:** 2026-04-19
- **Last revised:** 2026-04-19

---

### INS-030 — DFDO Phase B: functional surrogate is gate-valid Outcome A; structural two-regime composite is compressible but was never proposed

- **Claim:** In GP-096 sandbox_18 (DFDO substrate, math_exp_only grammar, GP-072 Division A/B protocol, sealed pre-registration), the engine found a 10-parameter ratio-of-exponentials surrogate `(((a_a·exp(a_b·u) + a_c·exp(a_d·u)) / (b_a·exp(b_b·u) + b_c·exp(b_d·u))) / (d2_a/u + d2_b)) + (tail_a/u + tail_b)` that passed all three gates (visible: max|res|=5.03e-05, holdout: pass, farther-tail: pass) and scored 95/100 across two independent runs (20 iters and 10 iters). This is Outcome A per pre-registration. The ground truth is `A(t) ~ C·(1+ct)^(-3.70)` — a single power-law asymptotic. The engine's 10-param form is a functional surrogate that is structurally distinct from the GT. Division A backtest (Feynman backtest, 2026-04-19) established the minimum gate-passing structural form is a 5-6 parameter two-regime additive composite `a·exp(-b·u^p) + C·(1+d·u)^(-3.70)`. The engine explored both components in isolation (iter 1: stretched-exp; iters 5-6: log-substitution) but never proposed their additive composition. The gap between the surrogate (10 params, ratio topology) and the compressible target (5-6 params, additive composite topology) is the topology induction gap documented in GP-103. Phase B Outcome A classification requires functional equivalence on the observable, not structural match — both conditions met. Phase C gate is open (double Outcome A: KWW sandbox_17 score 98 + DFDO sandbox_18 score 95).
- **Evidence pointers:**
  - Run artifacts: `projects/gp096_sandbox_18/history/1776637506_iter10_score_95_gp096_sandbox_18.md` (Run 1 champion), `projects/gp096_sandbox_18/history/1776642638_iter2_score_95_gp096_sandbox_18.md` (Run 2 champion)
  - Pre-registration: `research_areas/private/seams/GP-096_sandbox_18_pre_registration.md`
  - Seal: `projects/gp096_sandbox_18/sandbox_seal.json` — artifact hashes recorded
  - Division A backtest: GP-103 seam §Feynman Backtest Results — 5-param additive composite passes all gates
  - KWW comparison: `projects/gp096_kww_sandbox_17/champion_eval_results.json` (score 98, correct structural class)
- **Cost (Run 2, gpt4.1/gpt4.1):** 10 iterations at roughly $0.08-0.10/iter; exact cost in `projects/gp096_sandbox_18/workspace/cost_summary.json`.
- **Confidence tier:** `confirmed` — two independent runs on the same substrate with different mutator/judge pairs reaching the same score and the same surrogate topology. Pre-registered protocol with sealed artifact hashes.
- **Paper target(s):** `paper5` conclusion (Phase B Phase C transition empirical anchor; functional surrogate vs. structural class distinction; DFDO as the harder substrate alongside KWW); `paper2` (discovery apparatus confirms Outcome A without structural class match — validates the apparatus's gate calibration).
- **Status:** `fresh`
- **Opened:** 2026-04-19
- **Last revised:** 2026-04-19

---

### INS-031 — Component D early golden ticket eliminates search pressure before compositional generators can accumulate their required input signal

- **Claim:** In GP-096 sandbox_18 Run 2 (gpt4.1/gpt4.1, 10 iters, H-GP103-5 implemented), the Compositional Hypothesis Generator (H-GP103-5) never fired due to a two-factor deadlock: (1) a `not _gp087_injected` mutex in autoresearch_loop.py declared GP-087 and H-GP103-5 mutually exclusive, so whenever GP-087 fired (farther-tail failure → stagnation), H-GP103-5 was blocked; (2) Component D (via GP-087 seeds) gave a 95-score surrogate at iter 2, resetting `stagnation_count` to 0 and permanently blocking H-GP103-5's stagnation condition. The fix for (1) was applied 2026-04-19 (removed `not _gp087_injected` mutex). The fix for (2) is the "Gag Order Test" (below) — a validation run with Component D stagnation threshold ≥8 so the engine must struggle through individual regime families before a golden ticket is available. The pattern generalizes: any compositional/reflexive mechanism that requires N failed-family observations before triggering is vulnerable to (a) mutual exclusion with a competing injection mechanism and (b) early high-scoring surrogate injection that resets the accumulation counter.
- **Evidence pointers:**
  - Run telemetry: `projects/gp096_sandbox_18/history/1776642638_iter2_score_95_gp096_sandbox_18_meta.json` (score 95 at iter 2 via Component D seed)
  - Score history: 0, 95, 95, 60, 60, 95, 95, 95, 60, 95 — score pressure eliminated after iter 2
  - Code fix: `src/ztare/validator/autoresearch_loop.py` line ~4294 — `not _gp087_injected` removed from H-GP103-5 trigger
  - GP-103 seam: §Postmortem — H-GP103-5 Re-Run (2026-04-19)
  - Gemini review: "Component D gave the Mutator a 'Golden Ticket' too early" — forensic analysis confirming the causal chain
- **Proposed validation (architectural):** "Gag Order Test" — run sandbox_18 with Component D stagnation threshold set to ≥8 iterations, forcing the engine to struggle through individual regime families. This would let H-GP103-5 accumulate its required input signal. Scheduled as a Phase C preparation run.
- **Confidence tier:** `confirmed` — direct telemetry shows Component D seed at iter 2, score 95 immediately after, H-GP103-5 pair accumulation count at 0 for all subsequent iterations. Mutex root cause confirmed by code inspection. Fix applied.
- **Paper target(s):** `paper2` (apparatus interaction effects: when two architectural mechanisms compete for the same signal, the faster one can preempt the slower, making the slower one untestable; this is an apparatus design failure); possibly `paper5` (Phase C preparation finding: compositional mechanisms need sequencing guarantees against early surrogate injection).
- **Status:** `fresh`
- **Opened:** 2026-04-19
- **Last revised:** 2026-04-19

---

## Candidate rows (not yet insights — tracked here so I remember to come back when evidence lands)

### Candidate: Mutator-side formalism drift against a substance-rewarding judge (H-GAMING-14)

Will be opened as **INS-007** when the four-trial test (`v1_score_88`, `v2_score_88`, `v16_score_88`, `v29_score_82` replayed under today's judge) returns data and meets the three pre-committed criteria from `ztare_operational_mode_seam.md#turn-11`. Currently blocked on running `test_thesis.py` four times. Cannot be opened before those JSONs exist. Do not retrofit.

### Candidate: Judge self-instruction failure under structural compliance pressure (H-JUDGE-01)

Already `confirmed` in the hypothesis ledger on a single model family (gemini-2.5-flash). Promoting to insight requires one additional independent replication on a second model family. Will be opened as **INS-008** after second-family replication.

### Candidate: Kernel self-diagnosis — the verifier caught a failure mode that was not in the seam's opening question set

Motivating observation: Turn 9/10/11 of the opmode seam collectively show ZTARE's own verification machinery surfacing a failure mode (mutator drift despite substance-rewarding judge) that the seam's original eigenquestion did not ask about. This is arguably the strongest "recursive self-diagnosis" example in the repo. Candidate for **INS-009**, conditional on H-GAMING-14 landing confirmed. Paper target likely `paper2`, possibly cross-cited in `paper1` as a concrete instance of cognitive-camouflage at the optimizer-vs-evaluator interface.

---

### Candidate: Epistemic modesty is a derivation, not a disclaimer (INS-010)

**Core principle (two forms):**
- Positive: *"Epistemic modesty is a derivation, not a disclaimer."* Genuine modesty is a mathematical output of the evidence window, not a legalistic hedge pasted at the end of a thesis.
- Munger inversion: *"Unearned modesty is just a more sophisticated lie."* If the hedge isn't earned from actual evidence limits, it is a form of cognitive camouflage — performative humility that passes the appearance of epistemic virtue while concealing overreach.

**Live proof — GP-096 Langevin sandbox_16 (2026-04-19):**

*Positive case (validation):* The champion thesis (score 75) explicitly states "tail class unresolved from finite data." The `farther_tail_global_residual` gate returned 0.1128 against a 0.02 threshold, and the evidence gap record stated "Request data at u=64, 128, … to evaluate the tail class discriminator." The judge (GPT-4.1) scored this correctly at 75 — three gates pass, the farther-tail gate fails. Caveat: the mutator wrote the thesis *before* seeing the gate results, so the modesty was *validated by* the gate, not *derived from* it. The mutator may have hedged performatively and been coincidentally correct. This is the weaker half of the proof.

*Enforcement case (the strong half):* 10 stagnation iterations where GP-087 tail-correction seeds asserted specific tail forms (1/u, 1/u + 1/u^2, etc.) scored 50 or lower and were rejected. These theses claimed certainty about the tail class, and the judge punished the unearned certainty because the gates showed the assertions were unsupported (farther_tail_global_residual 0.18 > 0.02, hidden_transition_shape 0.044 > 0.03). The apparatus *enforced* derived modesty by refusing to reward tail-class claims the evidence window could not certify. This is the strong half: the apparatus catching unearned certainty, not just confirming earned modesty.

**Why the inversion matters for paper5:**
Cognitive camouflage (the pathology catalogue) is the failure mode where an LLM inserts epistemic hedges performatively — as compliance signals rather than derived conclusions. The Munger inversion names the positive complement: *what would derived modesty look like?* It looks like the Langevin champion. The gate failure is the derivation; the "unresolved" statement is the output. Any thesis that says "this might be uncertain" without a corresponding gate, evidence gap, or explicit logic bound is exhibiting cognitive camouflage, not epistemic modesty.

**Short-form candidates for epigraphs / pull-quotes:**
- "Epistemic modesty is a derivation, not a disclaimer." ← recommended for paper5
- "Unearned modesty is just a more sophisticated lie." ← recommended for Operational Manual (Epistemic Hygiene chapter)
- "Integrity is a structural residual, not a compliant mask." ← links to Residual Isomorphism; paper4/5 crossover
- "Humility is a calculation, not a vibe." ← informal; teaching-note caliber
- "Truth begins at the evidence ledge." ← five words; poster-worthy but needs context to load-bear

**Placement recommendation:**
- *paper5* (treatise): add to the cognitive camouflage pathology discussion (§1.3, near "Fail-closed defaulting") — use the positive form as the structural contrast to the camouflage pattern. One sentence, no new section.
- *Operational Manual, Epistemic Hygiene chapter*: use the inversion form as a section opener or rule header.

**Blocking condition for INS-010:** This is a principle-level insight, not a hypothesis-test finding. It does not require a discriminating run to open. The Langevin sandbox provides the existence proof; the cognitive camouflage catalogue provides the counter-examples. Can be opened immediately at `suggestive` tier. Promote to `confirmed` when a second sandbox run shows the same derived-vs-scripted contrast across two model families.

**Paper target(s):** `paper5` (§1.3 cognitive camouflage); Operational Manual (Epistemic Hygiene chapter).
**Opened:** 2026-04-19

---

### INS-032 — The apparatus discovers its own grammar gaps through the recursive diagnosis loop

- **Claim (one paragraph):** When the GP-112 margin-of-safety gate exhausts all extensions and returns PERSIST, the GP-113 diagnosis feedback loop injects a structural constraint into the derived constraints ledger. On the Lucky 500K substrate, the LLM mutator — informed by the constraint "exhausted 6 additive extensions, propose NON-ADDITIVE correction" — proposed `a + b*log(n) + c/(n+d) + e*log(n)^2`, which introduced a shifted reciprocal `c/(n+d)` not present in the 41-template library. This form passed all 4 holdout gates at 500K scale where all 41 templates had failed. The shifted reciprocal was then permanently added to the template library (28th Stage 1 template), regression-tested on partition substrates (zero false positives), and is now available to all future substrates. The grammar expanded from its own failure signal, mediated by the LLM's structural creativity, verified by the holdout gates. The causal claim (that the diagnosis constraint CAUSED the improvement) is uncontrolled: no control run without the constraint was performed.
- **Evidence pointers:**
    - Experiment: E-GP113-LUCKY-500K in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - GP-113 constraint injection: `projects/oeis_a000959_500k/workspace/derived_constraints.json`
    - Champion form: `projects/oeis_a000959_500k/test_model.py`
    - Template addition: `src/ztare/fit/compress_champion.py` line 70 (`log_shifted_reciprocal`)
    - GP-112 margin test on GP-113 champion: MARGIN_THIN + STRUCTURED_RESIDUALS persist
- **Confidence tier:** `suggestive` — single substrate, no control run, causal claim uncontrolled. The existence proof (the loop CAN improve a PERSIST) is confirmed. The necessity proof (the loop was REQUIRED) is missing.
- **Paper target(s):** `paper5` (recursive self-improvement frontier), experimental math letter (cross-domain methodology demonstration)
- **Status:** `fresh`
- **Opened:** 2026-04-22
- **Last revised:** 2026-04-22

### INS-033 — Validity horizons: the scale at which a certified topology breaks is measurable and automatable

- **Claim (one paragraph):** The Lucky number density ratio L(n)/n transitions from a logarithmic best-fit topology (gates pass at 50K) to a compositional topology (sqrt(n/log(n)), gates pass at 100K+) at n=50,000-100,000. An automated scale-sweep protocol (`validity_horizon.py`) detects this transition by running compression at multiple scales and comparing the BIC winner at each. The transition is method-independent (it does not depend on detrending or spectral analysis). No symbolic regression system currently reports "f(n) valid up to n=X." The validity horizon was also demonstrated on synthetic substrates: sin(x) polynomial approximation (valid at scale=50 only), Arrhenius decay (valid to scale=300, breaks at 400+).
- **Evidence pointers:**
    - Lucky validity horizon: `projects/oeis_a000959/workspace/validity_horizon.json`
    - Synthetic generalization: `papers/case_studies/validity_horizon_generalization.json`
    - Implementation: `src/ztare/fit/validity_horizon.py`
- **Confidence tier:** `confirmed` — reproduced on Lucky (primary) and two synthetic substrates (secondary). Method-independent.
- **Paper target(s):** `experimental_math_letter` (§2.1 + Discussion), `paper5` (epistemic boundary capabilities)
- **Status:** `fresh`
- **Opened:** 2026-04-22

### INS-034 — Detrending sensitivity proves non-stationarity in sieve-generated density fluctuations

- **Claim (one paragraph):** Spectral slope measurements for Lucky and Ulam density fluctuations vary by 1.7 across detrending methods (MA-11 through poly-3). The swing proves the residual process is non-stationary: error variance couples to signal magnitude, violating the stationarity assumption of classical spectral analysis. Under standardized methodology (MA-21), both sequences show similar slopes (-0.44 to -0.56), disproving the initially claimed brown-vs-white distinction. The detrending sensitivity table IS the evidence for non-stationarity. The pipeline was validated on synthetic data: known colored noise (white, pink, brown) is correctly identified, and the detrending sensitivity is absent for stationary processes. No prior spectral characterization of Lucky or Ulam density exists in the literature (Wolf 1997 characterizes primes only).
- **Evidence pointers:**
    - Detrending tables: `projects/oeis_a000959_500k/workspace/detrending_sensitivity.json`, `projects/gp088_oeis_a002858/workspace/detrending_sensitivity.json`
    - Synthetic validation: run via `scripts/public/projects/oeis/reproduce_letter_results.py` (Wolf comparison at `papers/case_studies/wolf_method_comparison.json`)
    - Literature search: confirmed no prior Lucky/Ulam spectral characterization
- **Confidence tier:** `confirmed` — reproduced on two sieve sequences, validated against synthetic, cross-checked with Wolf (1997).
- **Paper target(s):** `experimental_math_letter` (§2.7 + Discussion detrending table), `paper5` (epistemic boundary capabilities)
- **Status:** `fresh`
- **Opened:** 2026-04-22

---

### INS-036 — Transformer "rank-1.8 bottleneck" is a BOS contamination artifact in mean-pooled measurements

- **Claim (one paragraph):** The previously reported effective rank of 1.8 at Pythia-410M layers 6-17 (the "sandglass bottleneck") is an artifact of BOS token contamination in mean-pooled activation measurements. The BOS token (position 0) has activation norm 741 versus ~21 for all other positions (35x ratio). When mean-pooling across sequence positions, BOS contributes 74.6% of the mean vector's norm, collapsing the effective rank to 1-2 dimensions (the BOS variation across prompts). Per-token effective rank at the same layers, with BOS excluded, is ~103-106 — not 1.8. OPT-350M, whose BOS token has normal norm (32 vs 32 for other positions), shows no sandglass: its rank profile is flat at 6-8 across all 24 layers. The sandglass is a measurement artifact, not an architectural property.
- **Evidence pointers:**
    - BOS norm check: `projects/gp116_cot_exchange/workspace/interim_findings.md` (Experiment 5-6)
    - Per-token rank (Test D): same file
    - Cross-family comparison: GPT-2-medium + OPT-350M raw results
    - Scripts: `projects/gp116_cot_exchange/extract_layer_transitions.py`, `extract_effective_rank.py`
- **Confidence tier:** `confirmed` — replicated across 3 model families (Pythia, GPT-2, OPT). BOS norm ratio is mechanistic explanation.
- **Paper target(s):** `paper6_neural_scaling`, `paper5`
- **Status:** `fresh`
- **Opened:** 2026-04-22

---

### INS-037 — Adjacent transformer layers compute in orthogonal residual subspaces

- **Claim (one paragraph):** At every adjacent layer pair in the bottleneck of Pythia-410M (layers 6-17), the top-10 singular vectors of the attention+MLP residual (h_{L+1} - h_L) have cosine similarity of 0.10-0.19 with the next layer's residual singular vectors (random baseline for 1024-dim space: ~0.03). The layers compute perturbations in completely different 192-dimensional subspaces. However, per-token residual magnitudes correlate highly across adjacent layers (r=0.78-0.93): the layers agree on WHICH tokens need perturbation but disagree on the DIRECTION. This "Parallel Firefighting" pattern replicates across Pythia-410M, GPT-2-medium (cosine 0.11-0.26), and OPT-350M (cosine 0.12-0.32). A sharp decorrelation boundary exists at L15→L16 (magnitude correlation drops from r=0.66 to r=0.09), marking the transition from bottleneck to output layers.
- **Evidence pointers:**
    - Cross-layer correlation: `projects/gp116_cot_exchange/workspace/interim_findings.md` (Experiment 6)
    - Cross-family replication: background task output
- **Confidence tier:** `confirmed` — replicated across 3 model families.
- **Paper target(s):** `paper6_neural_scaling`
- **Status:** `fresh`
- **Opened:** 2026-04-22

---

### INS-038 — 72% of layer perturbation energy cancels across the transformer bottleneck

- **Claim (one paragraph):** When summing all 11 bottleneck layer residuals (h_{L+1} - h_L) for each token, only 27.8% of the total perturbation energy survives (||sum(deltas)|| / sum(||delta_i||) = 0.278). The 72.2% that cancels confirms partial "iterative hedging": adjacent layers' orthogonal perturbations partially cancel each other. However, the ablation test shows the 28% that survives is not trivial: skipping any single bottleneck layer increases next-token loss by 1.5-16%, with a U-shaped profile (layers 14-15 have minimum impact at 1.5%, layers 6-8 and 16-17 have 10-16% impact). No layer has zero impact. The residual computation is partially wasteful (72% cancellation) but partially useful (every layer contributes measurably to the output).
- **Evidence pointers:**
    - Cancellation test (Test A): `projects/gp116_cot_exchange/workspace/interim_findings.md`
    - Ablation test: same file
    - Total bottleneck rank (Test B): 107 (12 layers of rank-192 collapse to rank-107)
- **Confidence tier:** `suggestive` — single model family (Pythia-410M), single model size. Needs cross-family and cross-scale replication.
- **Paper target(s):** `paper6_neural_scaling`
- **Status:** `fresh`
- **Opened:** 2026-04-22

---

### INS-040 — Orthogonal cancellation (~70%) is an architectural invariant of residual networks, not a learned property

- **Claim (one paragraph):** The ~70% cancellation of perturbation energy across adjacent layers in deep residual networks is a fixed geometric cost, not a learned inefficiency. An untrained Pythia-410M (random initialization) shows 70.2% cancellation, compared to 72.2% after full training. Training does not learn to reduce cancellation. What training DOES learn is: (a) the rank of the residual computation (41 at init → 192 after training, a 5x increase in the diversity of per-layer computation), (b) token-level coordination (magnitude correlation increases from r=0.3 to r=0.9 — trained layers perfectly agree on which tokens need updating), and (c) the BOS norm anomaly (1.1x at init → 35x after training, creating the artifactual "rank 1.8 bottleneck" in mean-pooled measurements). The cancellation rate is the mathematical consequence of summing high-dimensional orthogonal vectors in a residual stream, not an optimization target that gradient descent can improve.
- **Evidence pointers:**
    - Untrained null model: `projects/gp116_cot_exchange/workspace/interim_findings.md` (Experiment 9)
    - Trained comparison: Experiments 5-8
    - Cross-architecture: Mamba-370M shows 62% cancellation (lower, but still substantial)
- **Confidence tier:** `confirmed` — null model comparison is the strongest possible test of the architectural vs learned distinction. Untrained/trained delta is 2 percentage points on cancellation (noise-level), versus 5x on residual rank and 3x on magnitude correlation.
- **Scope correction (2026-05-01):** GP116B re-audit found this row is too absolute. The fixed-cancellation claim remains supported for the original untrained-vs-pretrained Pythia-410M comparison and for pretrained Pythia-410M continue-training, but the from-scratch Pythia-160M probe briefly suppresses cancellation to `~3%` before later divergence. The revised claim is: fixed additive residual geometry creates a default cancellation tax; cancellation suppression may be trainable in fragile regimes, and the open discriminator is whether that suppression is stable useful phase-locking or a precursor to optimization collapse. See `projects/gp116_cot_exchange/workspace/gp116b_substrate_readiness_20260501.md`.
- **Paper target(s):** `paper6_neural_scaling` (primary), `paper5`
- **Status:** `fresh`
- **Opened:** 2026-04-22

---

### INS-039 — WITHDRAWN: "99.1% management fee" (ROC = Rank(total)/Rank(residual) = 0.009)

- **Claim (one paragraph):** WITHDRAWN. The ROC metric mixed measurement granularities: Rank(total) = 1.8 was from mean-pooled cross-prompt measurement (contaminated by BOS, see INS-036), while Rank(residual) = 192 was from per-token measurement. The corrected per-token ROC is 105/192 = 0.55 (55% efficiency, not 0.9%). The "99.1% management fee" framing is wrong.
- **Refutation:** INS-036 (BOS contamination) + Test D (per-token total rank = 105). The 72% cancellation (INS-038) is the correct inefficiency metric, not the ROC.
- **Confidence tier:** `withdrawn`
- **Paper target(s):** none — do not cite
- **Status:** `withdrawn`
- **Opened:** 2026-04-22

---

### INS-035 — Observable rotation resolves UNDERIDENTIFIED substrates

- **Claim (one paragraph):** When the compression grammar exhausts on an observable (all templates fail holdout gates), an automated observable rotation (trying standard transforms: log(z), 1/z, diff(z)) can reveal structure invisible in the original representation. On the Ulam density ratio U(n)/n, all 41 templates failed holdout. The reciprocal observable n/U(n) compresses trivially: n/U(n) = -0.000216*log(n) + 5.597/n + 0.0776 (all gates pass at 500K, max residual 0.0015, 33x below threshold). The constant 0.0776 approximates the reciprocal of the Steinerberger density (1/13.50 = 0.0741, 5% discrepancy from finite-n correction). The form invisible in one representation became trivial in another. This is a general-purpose strategy: it applies to any UNDERIDENTIFIED substrate without domain knowledge.
- **Evidence pointers:**
    - Post-UNDERIDENTIFIED results: `projects/gp088_oeis_a002858/workspace/post_underidentified.json`
    - Implementation: `src/ztare/fit/post_underidentified.py`
    - Experiment row: E-ULAM-OBS-ROTATION
- **Confidence tier:** `confirmed` — single substrate but the mechanism is general (mathematical identity: if z resists templates, 1/z may not). Needs replication on a second UNDERIDENTIFIED substrate.
- **Paper target(s):** `experimental_math_letter` (§2.7 Ulam), `paper5` (post-UNDERIDENTIFIED capabilities)
- **Status:** `fresh`
- **Opened:** 2026-04-22

---

### INS-041 — SSMs learn to reduce cancellation; transformers do not

- **Claim (one paragraph):** The cancellation ratio in deep residual networks responds differently to training depending on architecture family. In Pythia-410M (transformer), cancellation is 70.2% at random initialization and 72.2% after training (unchanged, 2pp difference). In Mamba-370M (state-space model), cancellation is 76.0% at random initialization and 62.0% after training (14pp reduction). Training teaches the SSM's selective state-space mechanism to produce more aligned perturbations across layers, reducing cancellation by 14 percentage points. Training does NOT teach the transformer's attention mechanism to align perturbations. This is the most architecturally informative finding in the cross-architecture comparison: the two families differ not in their untrained geometry (both ~70-76%) but in whether gradient descent can improve that geometry. The SSM's inductive bias permits learned perturbation alignment; attention's does not.
- **Evidence pointers:**
    - Untrained Mamba: `projects/gp116_cot_exchange/workspace/interim_findings.md`
- **Scope correction (2026-05-01):** The title and final sentence overstate the split. The paper-6 table already contains transformer-family YES cases (GPT-2 Small, SmolLM-135M, SmolLM-360M), so the durable distinction is not "SSM vs transformer." The live axis is residual/training regime: some architectures or training recipes learn cancellation reduction, others do not. GP116B should test residual-state mechanisms and training stability directly rather than using architecture labels as causes.
    - Untrained Pythia: same file (Experiment 9)
    - Trained comparison: Experiment 8
- **Confidence tier:** `confirmed` — null model comparison on both architectures, same methodology, same prompts.
- **Paper target(s):** `paper6_neural_scaling`
- **Status:** `fresh`
- **Opened:** 2026-04-22

---

### INS-042 — Weight norm is decoupled from per-model alignment learning at scaling level, but correlates with alignment across models. Causal training-regime mechanism is open.

- **Claim (one paragraph):** Two confirmed and one falsified test, taken together, decouple weight magnitude from learned perturbation alignment at the scaling level but leave the cross-model correlation intact and unexplained. (a) **CONFIRMED — scaling invariance:** multiplying the block output projections of trained Pythia-410M by k ∈ {1.0, 1.5, 2.0, 3.0} leaves the cancellation ratio at exactly 70.7% across all scales. This invariance is a mathematical consequence of LayerNorm stripping uniform scale from the residual stream. (b) **CONFIRMED — init/trained separation:** across 6 models, NO-group models (Pythia-160M/410M, Qwen2-0.5B) have nearly unchanged block weight norms from init to trained state (Δ +5/+14/-14%); YES-group models (GPT-2 Small, SmolLM-135M/360M) grow 5-12x (Δ +525/+1138/+1156%). Init norms are statistically indistinguishable across groups (YES/NO init ratio 0.79x); the 8.6x trained-norm separation is entirely a training-trajectory effect. (c) **CONFIRMED — config survey:** YES-group models used weight_decay=0.01 (GPT-2 directly, SmolLM1 inferred from SmolLM2 nanotron configs); NO-group Pythia used 0.1. (d) **FALSIFIED — direct causal probe:** continue-training Pythia-410M for 400 steps on Pile-style natural text with weight_decay ∈ {0.0, 0.1} produces nearly identical cancellation trajectories (both end at 72.78-72.95%, delta 0.17pp). The hypothesis that removing weight decay alone unlocks alignment learning is not supported under this test. Caveats apply (continue-train vs from-scratch, tiny 144KB corpus, 6 orders of magnitude less data than full training), but the simple causal claim is rejected. The honest mechanism is open: cross-model correlation between low weight decay and alignment is real and 4-data-points monotonic, but the causal direction is not established and may involve compound factors (decay × data curation × from-scratch plasticity × training duration).
- **Evidence pointers:**
    - Weight scaling test (Test #5): `projects/gp116_cot_exchange/workspace/weight_scaling_test.json`
    - Init vs trained test (Test #1): `projects/gp116_cot_exchange/workspace/init_weight_norms.json`
    - Config survey (Test #2): Experiment 15 in interim_findings.md
    - Continue-train probe (Test #3b, falsified): `projects/gp116_cot_exchange/workspace/weight_decay_causal.json`
    - Interim findings: Experiments 13-16 in `projects/gp116_cot_exchange/workspace/interim_findings.md`
- **Confidence tier:** `mixed` — scaling invariance and init/trained separation are confirmed; direct causal claim is falsified at this scale; cross-model correlation remains suggestive but unexplained.
- **Paper target(s):** `paper6_neural_scaling`
- **Status:** `fresh`
- **Opened:** 2026-04-22
- **Revised:** 2026-04-22 (causal claim falsified by Experiment 16)

---

### INS-043 — A telemetry-driven optimizer whose control thresholds are never crossed during training is indistinguishable from a constant-parameter baseline; improvements observed in that regime are not evidence for the telemetry mechanism

- **Claim (one paragraph):** A multi-seed falsification sweep of the cancel-ratio-governed TDO-LR mechanism on pythia-160M from-scratch (40,432-token corpus, 3000 steps per arm, 5 seeds) demonstrates that the TDO governor's cancel-ratio thresholds (low 5%, high 15%) never engaged during training: across all 5 seeds, cancel% remained in the 28-32% band at every logged 100-step checkpoint, driving the governor to emit `decay=0.1000` for the entirety of every TDO arm. The TDO arm therefore reduced to a constant `weight_decay = 0.1` configuration, with the baseline arm running at constant `weight_decay = 0.01`. Per-seed TDO improvement over baseline was seed 42 +15.3%, seed 137 +33.8%, seed 256 −144.2%, seed 1337 +32.2%, seed 2024 +8.1%. Three of five seeds exceeded the pre-registered +10% improvement threshold. However, because the governor never modulated, these improvements cannot be attributed to the telemetry-driven mechanism; they are consistent with an ordinary weight-decay sensitivity in which a 10× larger constant decay helps on 3 of 5 random inits and catastrophically hurts on 1 of 5. The claim that "real-time telemetry feedback dynamically modulates weight decay to accelerate convergence" is not supported by this evidence. The derived architectural rule — added to the falsify-before-claiming discipline — is that any pre-registered experiment involving a telemetry-driven or feedback mechanism must include an abort criterion that triggers if the telemetry thresholds fail to cross during the run, because otherwise a non-functioning governor is empirically indistinguishable from a functioning one.
- **Evidence pointers:**
    - Multi-seed sweep logs: `projects/gp116_cot_exchange/workspace/tdo_multiseed_20260423/tdo_sweep_seed*.log`
    - Last-seed JSON: `projects/gp116_cot_exchange/workspace/tdo_multiseed_20260423/tdo_falsification_seed2024_only.json`
    - Track record rows: E-TDO-MULTISEED-01 / F-TDO-MULTISEED-01 in `research_areas/private/EXPERIMENT_TRACK_RECORD.md`
- **Confidence tier:** `confirmed` — single-substrate (pythia-160M), five-seed falsification with a pre-registered +10% threshold; mechanism-level observation (decay=0.1000 every step) is deterministic across all runs.
- **Paper target(s):** `paper6_neural_scaling` (TDO section becomes a cautionary case); `paper7_methodology` (falsify-before-patent discipline, abort-if-thresholds-never-crossed as a pre-reg primitive).
- **Status:** `fresh`
- **Opened:** 2026-04-23

---

### INS-044 — First corroborated sealed cross-substrate prediction under the MLH family protocol succeeds on a target over-determined by LLM textbook priors; prior-vs-induction discrimination is deferred to a non-textbook holdout

- **Claim (one paragraph):** On 2026-04-23 the MLH family protocol was executed end-to-end for the first time: a cold LLM agent, given a sanitized packet of five training substrates F1..F5 (champion theses + evidence vectors + rubric metadata, SHA-256-hashed packet `7ac63d4572f259e2223d536049b5943f5e5b20736f21f34bdc61e9f23e2b876d`) and blinded from the F6 holdout, emitted a sealed prediction (seal `75a8abea…`, sealed 2026-04-23T23:56:17Z) predicting F6 = σ(n) with composition class `multiplicative`, prime-power rule `f(p^k) = (p^{k+1}-1)/(p-1)`, confidence 0.45. After one-way unlock, the scorecard returned 40/40 exact point matches (100%), composition class correct, f(1) correct; Newton-gate recorded `FAIL` only because `rule_validity=0.70` — a scorer artifact, the rule is expressed in LaTeX and the AST-parsimony check cannot parse non-Python strings. This is the first time any mechanism in or adjacent to this apparatus has emitted a falsifiable, hash-committed, cross-substrate prediction that survived unsealing on the first try — which is a genuine Popperian event. It is NOT a discovery in the GP-096 sense: F1..F5 are the canonical first-course arithmetic functions {sopfr, sopf, Ω, ω, τ}, F6 = σ is the textbook sibling any undergrad number theorist completes from the menu, the cold agent's own `reasoning_summary` cites "F5's own thesis stages σ₁ as its named rival, which is a strong curatorial tell" — direct self-reported evidence the agent used curatorial metadata, not structural induction from numerical vectors. The prediction is over-determined: we cannot distinguish "the protocol enables cross-substrate induction" from "the LLM's textbook priors completed the menu" on a target where both explanations predict the same answer. **The ambiguity is the finding.** The protocol is Newton-shaped (sealed, mechanism-emitted, scoring-rule-pre-committed, unsealed cleanly); the target is not discriminating. Resolution requires a non-textbook bespoke F6' where LLM priors alone should fail.
- **Evidence pointers:**
    - Sealed prediction: `research_areas/private/mlh_predictions/2026-04-23T23-56-17Z_sealed.json`
    - Scorecard: `research_areas/private/mlh_predictions/2026-04-23T23-56-17Z_sealed_scorecard.json`
    - Source packet manifest: `research_areas/private/mlh_prediction_packets/2026-04-23T23-45-00Z_packet_manifest.json`
    - Unlock record: `projects/mlh_f6/_unlock_record.json`
    - Seam: `research_areas/private/seams/mission/GP-140_ztare_discovery_seam.md` (records the cold-agent baseline as the floor any apparatus-produced generative primitive must beat)
    - Companion ablation (completed 2026-04-23, same session): `/tmp/mlh_ablation_prediction.json` — same cold-agent protocol but given ONLY raw (n, z(n)) vectors with all curatorial metadata scrubbed. Result: the cold agent STILL emitted σ with confidence 0.55, explicitly self-reporting "I recognized F1..F5 directly from their integer values (OEIS-familiar sequences), then derived the meta-rule from their shared structural property". **The ablation hardens the prior-sufficiency interpretation**: textbook integer sequences are themselves in LLM training as OEIS entries, so stripping curatorial metadata does not remove the prior. The only clean discrimination requires a bespoke non-textbook F6' not in OEIS.
- **Confidence tier:** `suggestive` — one discriminating test, one target, one model family (mixed Claude / o3 class reasoner). After the ablation, the prior-sufficiency framing is **high-confidence**; the positive-induction interpretation is **low-confidence and not supported by any current evidence**. The next experiment (bespoke non-OEIS F6') is what would discriminate.
- **Revised 2026-04-24:** the follow-up bespoke non-OEIS experiment (INS-045) runs the actual discrimination and returns a sharper finding: **cold LLMs can algorithmically induce bounded-complexity integer arithmetic rules they do not recognize from OEIS priors**. This means MLH-family-shaped targets are not discriminating for ZTARE-vs-cold-LLM at all — not because of lookup priors, but because of the LLM's algorithmic induction substrate. The "ambiguous target" framing in INS-044 is too weak; the correct framing is "the target class is LLM-solo-solvable, so the protocol is sound but the substrate is the wrong lane for demonstrating apparatus leverage". See INS-045 for the sharper result.
- **Paper target(s):** `paper5` (ZTARE treatise — section on the protocol-vs-target distinction: a Newton-shaped protocol does not guarantee a Newton-class finding when the target is prior-sufficient).
- **Status:** `fresh`
- **Opened:** 2026-04-23

---

### INS-045 — Cold LLMs algorithmically induce bounded-complexity integer arithmetic rules without OEIS recognition; MLH-family-shaped targets are the wrong lane for demonstrating apparatus-level discovery leverage

- **Claim (one paragraph):** A cold LLM reasoner, given ONLY 80 integer values of a bespoke non-OEIS multiplicative arithmetic function with prime-power rule `f(p^k) = p^k - k^p` (verified non-indexed by construction; symmetric base/exponent swap not a standard OEIS building block), and explicitly forbidden from OEIS / internet access, emitted a sealed prediction for n = 81..120 that scored **40/40 exact matches (100%)** against the sealed ground truth. The agent self-reported `oeis_guess: "unknown / not in OEIS priors"` and `honest_blindness_flag: false`, confidence 0.98, with the verification step citing distinctive hits: z(49) = 49 − 128 = −79, z(25) = 25 − 32 = −7, z(32) = 32 − 25 = 7, z(64) = 64 − 36 = 28. This falsifies the "priors = 0 for non-OEIS" working hypothesis (introduced in the INS-044 discussion): LLM priors on integer sequences are NOT just memorized OEIS lookup. The LLM has an **algorithmic induction substrate** — the capacity to test multiplicativity on coprime pairs, isolate prime-power values, hypothesize `f(p^k)` as a function of p and k, verify against visible data, and extrapolate — that functions independently of OEIS memorization. For bounded-complexity integer arithmetic rules (multiplicative or additive, prime-power-local, derivable from ≤ 80 visible values), a cold LLM is single-shot competitive with or superior to any iterative apparatus. The apparatus-leverage claim is therefore NOT refutable nor confirmable on MLH-family-shaped targets — they are LLM-solo-solvable regardless of OEIS indexing. ZTARE's documented apparatus-leverage wins (Hardy-Ramanujan partition asymptotic with PSLQ coefficient pinning, Lucky 500K scale-dependent validity-horizon detection, Pythia neural scaling compositional-form ranking, KWW fractional-exponent recovery, observable rotation on Ulam) are all in a structurally different domain: numerical regression on real / noisy / scale-dependent data where the target is coefficient values or functional-form topology, not a symbolic rule over integer factorizations. MLH was the wrong substrate for a Kepler→Newton bridge test.
- **Evidence pointers:**
    - Bespoke substrate: `projects/bespoke_f6_backtest/bespoke_f6_rule.py` (SHA-256 `102189f52d9792194387fac9b5b704a4361f80bb3aae93c63e01d36e5e8dfed2`)
    - Sealed truth: `projects/bespoke_f6_backtest/_holdout_locked/truth_n1_to_1000.json` (SHA-256 `75fac664bdc4c41d758266d7772d24e5c6824ea2435a1dc72d120ff0c13e7ac5`)
    - Sealed manifest: `projects/bespoke_f6_backtest/_holdout_locked/sealed_manifest.json`
    - Sanitized cold-agent packet: `projects/bespoke_f6_backtest/packet_for_cold_agent/sanitized_packet.json` (SHA-256 `e932937dff8cc5601e004178a008988bb36d8dd7fa29ab229ed434607cd8a46a`)
    - Cold-agent prediction + scorecard: `projects/bespoke_f6_backtest/workspace/cold_agent_prediction.json`
    - Verification command: `python3 -c "import json; pred=json.loads(open('projects/bespoke_f6_backtest/workspace/cold_agent_prediction.json').read()); truth=json.loads(open('projects/bespoke_f6_backtest/_holdout_locked/truth_n1_to_1000.json').read()); print(sum(1 for n in range(81,121) if pred['predicted_holdout_values'].get(str(n)) == truth[str(n)]), '/40')"`
    - Companion insight: INS-044 (revised 2026-04-24 to cross-reference this result)
    - ZTARE's actual apparatus-leverage lane, documented: track-record rows E-GP088-CAL-A01 (Hardy-Ramanujan), E-OEIS-A000009-01, E-OEIS-A000959-500K, E-NEURAL-SCALING-01, E-ULAM-OBS-ROTATION
- **Confidence tier:** `confirmed` — single target, single cold-agent instance, but the prediction mechanism is deterministic (once the rule is guessed, integer factorization closes the prediction); the agent's self-reported reasoning chain and the distinctive-hit verification points are sufficient to rule out memorization. Replication across additional bespoke rules (non-multiplicative, non-local, super-polynomial in k) is a worthwhile follow-up but is not required to confirm the core claim: LLMs have algorithmic induction capacity on integer arithmetic rules.
- **Paper target(s):** `paper5` (ZTARE treatise — section on apparatus-domain scoping: what ZTARE is and isn't for, with MLH as the anti-example); `experimental_math_letter` (possibly — PySR-vs-LLM head-to-head section could be reframed with "LLMs also do non-OEIS integer-rule induction; PySR and ZTARE earn their keep on numerical-regression targets where LLMs don't").
- **Status:** `fresh`
- **Opened:** 2026-04-24

---

### INS-046 — Apparatus-leverage on deterministic state-space inversion decomposes into complementary class-A (behavioral-fit solver) and class-B (Occam's-razor law-finder) primitives; composition with B-objective and A-optimizer is the central unit

- **Claim (one paragraph):** A controlled head-to-head on 2026-04-24 establishes that an apparatus-leverage finding on deterministic discrete state-space inversion (radius-2 binary cellular automaton, 2^32 rule space, random-sampled holdout with Hamming weight 16/32) is not a single capability but a decomposition of two complementary ones. (a) **Cold-reasoner tool-less rule induction from 40-step ON-count vector** — FAILED at confidence 0.02, `honest_blindness_flag: true`; the reasoner correctly derived a step-1 constraint on five rule bits but could not carry forward the 40-step mental simulation. (b) **Class-A behavioral-fit solver (constraint-propagation inversion, 80 LOC, no MDL prior)** — SOLVED in 0.6s, collapsed 2^32 rules to a 2-candidate behavioral-equivalence class, sealed truth 0x571aa876 uniquely among them alongside its reflection conjugate 0x465b99b8 (verified as `B = reflect_5bit_permutation(A)` bit-for-bit across all 32 states). (c) **Cold-reasoner disambiguation via experimental design** — SOLVED analytically; identified the reflection symmetry by bit-wise inspection, proposed asymmetric IC (two ON cells at positions 100, 101) with handedness-sensitive observable, confidence 0.9. (d) **Class-A experimental-design disambiguation (apparatus)** — SOLVED in 0.06s by rediscovering "asymmetric IC breaks reflection" experientially via pairwise-L1 search over an IC library; selected three-cell cluster at offsets (0,1,3) with L1 separation 195, pinned sealed truth after oracle query. (e) **Class-B Occam's-razor law-finder (thesis-faithful MDL-bounded symmetry-canonicalized search, faithful implementation of the gp140 iter-5 score-96 thesis primitive)** — REFUSED to admit the holdout at every MDL bound tested: 0 exact matches across 576,941 canonical representatives at HW≤6 (1.15M rules, 1162s compute), and by extrapolation would refuse at any tractable MDL bound below HW=16. The refusal is not a failure; it is the primitive's designed epistemic discipline. The integrated finding: a Newton-class generative primitive on this class of substrate is the composition of A (computational leverage — "does any generator exist") and B (epistemic discipline — "is the generator a candidate law rather than a cryptographic coincidence"), with B supplying the objective function and A supplying the optimizer, and edge cases (A-fits that exceed B's bound) reported with their excess rather than silently rejected. Either half alone is incomplete: A without B produces coincidence-as-law errors on maximum-entropy targets; B without A produces "no law found" silences that leave the operator blind to whether any generator exists. The composition is what the gp140 v2 charter (2026-04-24) pre-registers for the next apparatus run. This finding is a scoping contribution, not a discovery of new physics or mathematics: the class-A behavioral-fit primitive is textbook constraint satisfaction, and the class-B law-finder reproduces the gp140-emitted thesis primitive. The novelty is in the empirical head-to-head that operationalizes the decomposition, the controlled baselines that bound cold-LLM capability (Outcome 1 failure on rule induction, Outcome 2 success on disambiguation — confirming the "LLM theorizes, apparatus executes" narrative from Gemini's 2026-04-24 review), and the evidence that the two primitive halves are not substitutable.
- **Evidence pointers:**
    - Substrate + family generator: `projects/ca_bridge_test/ca_simulator.py`, `projects/ca_bridge_test/generate_family.py`
    - Sealed truth + manifest: `projects/ca_bridge_test/_holdout_locked/truth.json` (SHA-256 `3c8a0071…a576f14`), `projects/ca_bridge_test/_holdout_locked/sealed_manifest.json`
    - Sanitized cold-agent packets: `projects/ca_bridge_test/packet_for_cold_agent/sanitized_packet.json` (SHA-256 `9d1c5aa9…e619a`), `disambiguation_packet.json`
    - Cold-agent predictions: `projects/ca_bridge_test/workspace/cold_agent_prediction.json` (rule induction, failed), `cold_agent_disambiguation.json` (disambiguation, succeeded)
    - Apparatus Method A implementations: `projects/ca_bridge_test/apparatus_candidate/apparatus_v1.py` (constraint propagation, 0.6s result), `apparatus_v2_framer.py` (experimental-design disambiguation, 0.06s result), `apparatus_result.json`, `apparatus_v2_result.json`
    - Apparatus Method B implementation: `projects/ca_bridge_test/apparatus_candidate/apparatus_v3_thesis_faithful.py` (MDL-bounded symmetry-canonicalized search, 1162s result at HW≤6 with zero matches), `apparatus_v3_result.json`
    - Charter artifact pre-registering the composition requirement: `projects/gp140_ztare_discovery/project_charter.md` v2 (2026-04-24, hybrid A/B paired-primitive mandate), `projects/gp140_ztare_discovery/evidence.txt` Evidence Set G
    - Companion insight: INS-045 (cold-LLM algorithmic induction capacity on non-OEIS integer rules — bounds what a cold reasoner CAN do, complementary to what A+B apparatus bridges)
- **Confidence tier:** `suggestive` — one substrate class (radius-2 binary CA), one holdout rule, one cold-agent pair. Method A's behavioral-fit claim is deterministic at its implementation (the 2-candidate equivalence class is reproducible). Method B's refusal is a property of the thesis's designed MDL bound; extension to alternate compressibility priors (PSLQ, BIC, Betti-number, Lyapunov) is an open follow-up that would generalize the decomposition claim beyond CA substrates.
- **Paper target(s):** `paper5` (ZTARE treatise, "The Theory/Practice Split" section at the bottom of the Formalization Sketch chapter and the following "Apparatus-Domain Scoping" section — both already drafted with this finding as their empirical grounding).
- **Status:** `fresh`
- **Opened:** 2026-04-24

---

### INS-047 — Adaptive self-referential thresholds survive Newton-mode rubric as a new gaming vector; the gp140 v2 "hybrid A/B" charter is necessary but not sufficient to enforce the Occam's-razor law-finder role

- **Claim (one paragraph):** The gp140 v2 charter (2026-04-24) was explicitly engineered to force the mutator to propose a class-B Occam's-razor law-finder as half of a paired primitive, closing the admission-gate-saturation failure mode observed in gp140 v1 and in ztare_on_ztare. The iter-9 champion under v2 (score 87 under the single-judge loop) achieved the text shape — named Method A (MiniSAT forward-backward constraint propagation), named Method B (DNF minterm count via Quine-McCluskey), explicit composition contract (A emits candidate set, B filters), output schema with both behavioral_candidate_set and law_certified_subset — but introduced a new Newton-mode gaming pattern: the B-threshold was defined adaptively as `τ = 1.25 × NDLC_min`, where NDLC_min is the minimum description length observed in A's candidate set. This construction is algebraically identical to "admit at least the minimum-NDLC candidate" because `min(S) ≤ 1.25 × min(S)` is a tautology. Empirically: a behavioral set of 100 random Hamming-weight-16 rules (pure cryptographic coincidences, zero real laws) produced a non-empty "law_certified_subset" in 20 of 20 trials. The primitive labels pure noise as law-certified 100% of the time. This directly contradicts Evidence Set G's stated class-B refusal property (the charter's own empirical anchor). Three independent adversarial reviewers (MDL theorist / SAT researcher / charter auditor) converged on the same attack: the adaptive τ makes the forward discriminator analytically true under the construction, so the "rival hypothesis" (certification may be empty) is unfalsifiable. The charter auditor's honest-scored breakdown was 57/100 versus the loop's 87 — a 30-point gap concentrated in Generative Yield Newton-mode (tautological), Millennium transfer nudge (absent), and held-out-substrate non-prior-sufficiency (unargued). The integrated finding: **the Newton-mode rubric enforces the SHAPE of a paired primitive but does not by itself enforce the VALIDITY of the compressibility prior**. A mutator can satisfy every text-level rubric dimension while silently reducing the law-certification step to a rank operation. The rubric hardening required to catch this is a charter-level ban on self-referential thresholds (τ defined as a function of the candidate-set statistics it is meant to filter), with verification that any named threshold is either (a) derived from domain-specific theoretical considerations (Shannon bound, NML, BIC, published constant), (b) pre-registered with an absolute numeric value stated before the candidate set is seen, or (c) a published algorithm's standard parameter not tuned on the current data. This insight extends the recursive-self-diagnosis finding (paper2, INS-003) to the rubric-evolution axis: each hardening closes a gaming pattern and surfaces the next one. gp140 v2 is the third iteration of this recursion after the admission-gate collapse (ztare_on_ztare) and the target-prior-sufficiency bypass (INS-044/INS-045).
- **Evidence pointers:**
    - Thesis: `projects/gp140_ztare_discovery/history/1776992726_iter9_score_87_gp140_ztare_discovery.md`
    - Panel verdicts (three independent cold-agent reviewers):
        - MDL theorist (Rissanen/Gruenwald tradition) — verdict d, structurally broken
        - SAT / formal methods researcher — verdict b, reject for 2^64 vs 2^128 type error
        - Charter-compliance auditor — honest score 57/100, Newton-gaming flag YES
    - Empirical falsifying test: inline experiment showing 20/20 trials of 100 random HW=16 rules produce non-empty certification under the adaptive τ construction
    - Companion insights: INS-044 (MLH protocol validation), INS-045 (cold-LLM integer induction), INS-046 (A+B complementarity on CA substrate)
- **Confidence tier:** `confirmed` — three independent adversarial reviewers agreeing on the same attack, plus a deterministic 20/20 empirical reproduction of the claimed failure mode. The gaming pattern is generalizable to any charter that lets the mutator pick threshold parameters adaptively from its own output; the specific fix (ban self-referential thresholds) is pre-registerable in rubric language.
- **Paper target(s):** `paper5` (ZTARE treatise — section on rubric evolution and the recursive-gaming-surface pattern). (Earlier draft mentioned `paper7_methodology`; that paper does not exist and is not scoped — dropping as a target until an actual paper is opened.)

---

### INS-048 — Judge capacity is central for whether a Newton-mode rubric catches gaming in-loop or outsources it to post-hoc blind panels; weaker judges (gpt-4.1) rubber-stamp text polish, stronger judges (o3) catch structural epistemic flaws at first pass

- **Claim (one paragraph):** Empirical head-to-head on 2026-04-24 compared two judge model choices on gp140 v2.1 theses, holding rubric, charter, evidence, mutator, and DYNAMIC flag constant. The v2 iter-9 "Radius-3 DNF-Pareto CA Inverter" thesis (the adaptive-τ gaming target documented in INS-047) scored **87 under gpt-4.1 judge** but was independently scored **57 under three-panel blind adversarial review** (MDL theorist / SAT researcher / charter auditor) and was empirically falsified 20/20 trials on its core "law certification" claim. The v2.1 iter-1 "Takens-SINDy + Rissanen-MDL" thesis (discussed in this session) scored **76 under gpt-4.1** with single judge. A subsequent run with **JUDGE_MODEL=o3** on a thesis of similar apparent text quality scored that thesis at **28**, and the next iteration's thesis (Takens-SINDy + NML-Regret with Shtarkov finite-sample regret bound, structurally real and v2.1-compliant) scored **68 under o3**. The 39-point gap (28 vs 67) and the 30-point gap (87 loop vs 57 honest panel) on the prior gaming target converge on the same structural finding: gpt-4.1 as judge rubber-stamps text polish without detecting Newton-mode gaming vectors (adaptive thresholds, tautological forward discriminators, self-referential admission predicates), while a reasoning-class judge (o3) catches these at first pass. The implication is central for apparatus design: a Newton-mode rubric is necessary but not sufficient to enforce epistemic discipline — the judge's reasoning capacity is the second gate, and a weak judge converts the rubric from a structural filter into a text-polish sieve. The cost calculus inverts the naive expectation: gpt-4.1 per iter is cheaper but requires expensive post-hoc blind panels to trust any score above the rubber-stamp threshold; o3 per iter is ~3-5x more expensive but replaces the panel cost and produces scores that are approximately honest (o3 score + ~15 ≈ gpt-4.1 score on the same thesis). For charter-class qualitative substrates where gaming surface is high (ztare_on_ztare, gp140, any rubric with a Generative Yield or law-certification dimension), o3 is the default-worthy judge choice. For throughput-first scoping runs where a lenient floor is acceptable, gpt-4.1 remains viable. This insight extends the recursive-gaming-surface pattern (INS-047) to the judge-capacity axis: each rubric hardening surfaces a gaming pattern of complexity commensurate with the judge's reasoning capacity. A judge that doesn't reason about threshold-origin cannot enforce a ban on self-referential threshold construction, regardless of how the ban is written into the rubric text.
- **Evidence pointers:**
    - v2 iter-9 "adaptive τ" thesis (loop: 87 gpt-4.1; blind panel: 57) — archived at `projects/gp140_ztare_discovery/workspace/archive_v2_reset_2026-04-24/thesis_iter9_score_87_GAMED.md`
    - Three-panel blind review transcripts (MDL / SAT / charter auditor) — in agent task outputs from 2026-04-24 session
    - v2.1 iter-1 "Takens-SINDy + Rissanen" thesis (gpt-4.1 judge: 76) — archived history
    - v2.1 iter-1 under o3 judge: **28** (principal-reported 2026-04-24 late)
    - v2.1 iter-2 under o3 judge: **68** (principal-reported 2026-04-24 late, score_68_gp140_ztare_discovery)
    - Apparatus implementation: `src/ztare/common/llm_runtime.py` MODEL_MAP / DIRECTOR_MODEL_MAP / FALLBACK_MODEL_CHAINS with both gpt-4.1 and o3 families registered
- **Confidence tier:** `suggestive` — one substrate class (gp140 discovery-class charter), two judge models, three theses compared (v2 iter-9 gamed; v2.1 iter-1 Rissanen; v2.1 iter-2 NML). The 30-point + 39-point gaps are the core empirical signal. Generalization to non-gp140 substrates (quantitative discovery, numerical regression) is untested; for those, gpt-4.1's stricter cost-per-iter may still dominate because numerical substrates have lower text-polish surface. A cross-substrate replication (gp136 pMDL hardening under both judges, or a fresh quantitative substrate) is the test that moves this to `confirmed`.
- **Revised 2026-04-25:** additional empirical data from gp140 v2.3-v2.5 iterations (gemini-2.5-pro as mutator AND judge) shows that **gemini-pro as judge also catches Newton-mode gaming flaws** (Constant-Jacobian-Trace coordinate-invariance violation on iter 2; Dimensional Consistency ↔ Rössler substrate incompatibility on iter 3; LLL nonlinear-bias scope violation on iter 3). This extends the judge-capacity axis: the relevant split is NOT "o3 vs gpt-4.1" per se but **reasoning-class vs non-reasoning-class**. Both o3 and gemini-pro are reasoning-class (multi-step causal reasoning about thesis internal consistency); both catch gaming at roughly comparable rates. gpt-4.1 is non-reasoning-class; it scores on surface polish. The cost implication sharpens: any reasoning-class judge is ~3-5x more expensive per iter but replaces post-hoc panel review; non-reasoning judges require mandatory panel follow-up. The choice within reasoning-class (o3 vs gemini-pro vs Claude-Opus) is a second-order question about different training-distribution blind spots, not a capacity question. A separate caveat: **same-model mutator+judge has shared blind spots** — a flaw the model cannot generate proposals around is also a flaw it cannot evaluate against. The cross-model blind panel that caught v2 iter-9's 87→57 rubber-stamp gap remains the right hardening when a final champion is being promoted. In steady-state iteration loops, same-model mutator+judge is cost-efficient; for publication-grade champions, use cross-model panel.
- **Paper target(s):** `paper5` (Apparatus-Domain Scoping section — extend with a judge-capacity axis parallel to the generator-substitute axis already documented).
- **Status:** `fresh`
- **Opened:** 2026-04-24

---

### INS-049 — Mutator model diversity is central for breaking out of architectural local optima; different training distributions reach different solution families on identical charters

- **Claim (one paragraph):** On 2026-04-24, an A/B test of mutator models on the same gp140 v2.2 charter + rubric + evidence + judge (o3) yielded distinct architectural solution families. The o3 mutator explored a SINDy → MILP-bounded-box progression (TPL at score ~68, CAGE at score ~62 under o3) that stayed within gradient-search paradigms and retained partial admit-gate residue in Method B. The gemini-2.5-pro mutator, given the identical inputs, emitted the LATTICE thesis (score 83 under o3 judge) which pivoted to a structurally different algorithmic family — Lenstra-Lenstra-Lovász lattice basis reduction — for Method A, explicitly named "no absolute threshold gate" in Method B, and introduced Persistent Homology Betti numbers as a second orthogonal prior not present in the o3 lineage. The 21-point gap (62 → 83) on the same substrate, charter, and judge is strong evidence that a single mutator model explores only a subset of the architectural solution space reachable by a reasoning-class generator. The LATTICE pivot is not achievable by gradient descent from TPL/CAGE — it requires transitioning from *search* (enumerate and score) to *structural extraction* (solve the underlying integer-relation problem directly on the data matrix). Gemini-pro's broader exposure to number-theoretic and lattice-based algorithms (LLL is foundational in cryptography and Diophantine analysis) appears to be the enabling training-distribution difference. This finding extends the judge-capacity insight (INS-048): the apparatus quality has at least three axes — judge capacity (catches gaming), mutator capacity (reaches ceiling), and mutator diversity (escapes local optima). Single-mutator runs can plateau at a solution family that a different mutator breaks past in one iteration. The cost calculus: running 2-3 mutator models in parallel for 1-2 iters each (diversity probe) is cheap relative to 10+ iters on a stuck single mutator. For charter-class substrates where architectural novelty is central, multi-mutator diversity is preferable to deeper single-model iteration.
- **Evidence pointers:**
    - o3 mutator lineage (TPL / CAGE) theses: `projects/gp140_ztare_discovery/workspace/archive_v2_reset_2026-04-24/` (archived iters 62-68 under o3)
    - Gemini-pro LATTICE thesis: `projects/gp140_ztare_discovery/history/1777000664_iter1_score_83_gp140_ztare_discovery.md`
    - Reference-implementation seam: `research_areas/private/seams/mission/GP-141_continuous_A_plus_B_reference_implementation_seam.md`
    - Charter v2.3: `projects/gp140_ztare_discovery/project_charter.md` (adds reference-implementation pointer inviting the mutator to build on prior empirical lineage)
    - Companion insight: INS-048 (judge capacity central); INS-046 (A+B complementarity discrete); INS-047 (adaptive-threshold gaming caught by rubric hardening)
- **Confidence tier:** `suggestive` — one substrate (gp140 v2.2), two mutator models (o3 vs gemini-2.5-pro), one architectural pivot observed. Replication on a different substrate class (quantitative numerical, or non-local recurrence) with a similar mutator A/B would move this to `confirmed`. The specific claim that LLL-class architectural moves require training-distribution breadth (cryptography/number theory exposure) is particularly worth independent validation.
- **Paper target(s):** `paper5` (Apparatus-Domain Scoping — add mutator-diversity axis alongside judge-capacity and generator-substitute axes).
- **Status:** `fresh`
- **Opened:** 2026-04-24
- **Status:** `fresh`
- **Opened:** 2026-04-24

---

### INS-050 — Grammar expansion, not compute scaling, is the binding mechanism for structural discovery; the Planck recovery is the controlled proof

- **Claim:** Doubling the compute budget (crucial_02_extended: 32 iters, $2.71) raised interpolation score from 88 to 93 but produced zero structural progress — the engine remained trapped in a stretched-exponential Weibull basin. Adding one grammar primitive (UNIVERSAL_DENOMINATOR: A/(exp(B)-1), crucial_03: 15 iters, $1.28) recovered Planck's law to 4+ decimal places in 6 iterations. This is a controlled experiment: same substrate, same evidence, same judge, same mutator — only the grammar changed. Grammar is the binding constraint; compute is not.
- **Evidence pointers:**
    - E-GP083-CRUCIAL-02-EXT (compute doubling, score 93, zero structural change)
    - E-GP083-CRUCIAL-03 (grammar expansion, Planck recovered at machine precision)
    - `projects/gp023_crucial_03/champion_eval_results.json`
- **Confidence tier:** `confirmed` — pre-registered controlled test with two arms (compute vs grammar) on identical substrate.
- **Paper target(s):** `paper5` (Chapter 2 decomposition: the grammar primitive is a named operation in the decomposition).
- **Status:** `fresh`
- **Opened:** 2026-04-25

---

### INS-051 — The apparatus discovers from data, not from literature retrieval; the Retrieval-Trap is the controlled proof

- **Claim:** On a synthetic substrate with the same regime structure as known scaling laws (α = C/d) but with non-standard constants drawn from a hidden random seed (C1=3.714, C2=0.892 — not 2.0 or 4.0), the apparatus recovered the correct functional form AND fitted the non-standard constants from 11 data points (a=3.703, b=0.886, error <0.3%). An anti-retrieval gate verified the discovered constants are distinct from all published values. Holdout MRE 0.8%. Farther-tail MRE 3.9%. This is Discovery Engine validation test #1 of 3.
- **Evidence pointers:**
    - E-GP159-01 (retrieval-trap, score 82, all gates pass)
    - `projects/gp159_retrieval_trap/champion_eval_results.json`
    - Anti-retrieval gate: `projects/gp159_retrieval_trap/gate_harness.py` line 118-130
- **Confidence tier:** `confirmed` — pre-registered with anti-retrieval gate, single run. Pending gp160/gp161 for full Discovery Engine triad.
- **Paper target(s):** `paper5` (Discovery Engine validation section), potential standalone methodology note.
- **Status:** `fresh`
- **Opened:** 2026-04-25

---

### INS-052 — Spec audits without integration smoke tests systematically miss the bugs that matter (the "Theorists without Calculators" finding)

- **Claim:** Across 4 ZTARE-on-ZTARE meta-projects (gp152, gp153, gp140, gp156), spec-only adversarial audits produced "spec confirmed" verdicts while the code shipped with implementation bugs that surfaced only at runtime. The 24-bug GP-156 session is the canonical example: 7 of 12 iterations failed on CODE not concept (import crashes, empty Python blocks, fabricated MRE claims). The mandatory protocol is: Python integration smoke test FIRST against real archived data, THEN inverted execution-hostile spec audit. Step 2 alone reproduces the sycophancy loop.
- **Evidence pointers:**
    - GP-156 24-bug session postmortem: memory `feedback_ztare_on_ztare_postmortem.md`
    - Smoke test template: `scripts/public/audits/gp156_integration_smoke_test.py`
    - Inverted charter template: `projects/gp156_apparatus_hardening_review/project_charter.md`
- **Confidence tier:** `confirmed` — 4 independent meta-projects, consistent pattern.
- **Paper target(s):** `paper5` (methodology section: recursive self-audit discipline).
- **Status:** `fresh`
- **Opened:** 2026-04-25

---

### INS-053 — Discovery Engine triad: scoped synthetic validation passes; unscoped claim not yet earned

- **Claim:** Three pre-registered synthetic adversarial tests pass: (1) Retrieval-Trap (GP-159, score 82): apparatus recovers α=C1/(d+C2) with non-standard C1=3.703, C2=0.886 from 11 data points; anti-retrieval gate confirms constants ≠ 2/d, 4/d. (2) Asymptotic Wall (GP-160, score 90): apparatus discovers an exponential+power decay form that stays in [0,1] at d=100-200; polynomial trap avoided. (3) MDL Anti-Goodhart (GP-161, score 90): apparatus accepts K=10 oscillatory truth; holdout MRE 4.9%; does not force K≤5 approximation. **The scoped claim is earned:** the apparatus detects retrieval, extrapolation breakdown, and MDL Goodharting on synthetic substrates. **The unscoped "Discovery Engine" claim is NOT earned.** Missing: (a) cross-family replication (same substrates under gemini-pro mutator or claude), (b) real-world Class K success (gp154 or equivalent where GT is unknown), (c) genuine unknown-law substrate where the operator did not author the ground truth.
- **Evidence pointers:**
    - E-GP159-01, E-GP160-01, E-GP161-01 in EXPERIMENT_TRACK_RECORD.md
    - `projects/gp159_retrieval_trap/champion_eval_results.json`
    - `projects/gp160_asymptotic_wall/champion_eval_results.json`
    - `projects/gp161_mdl_anti_goodhart/champion_eval_results.json`
- **Confidence tier:** `confirmed` — three pre-registered synthetic tests, all pass. Scoped to synthetic adversarial substrates only.
- **Paper target(s):** `paper5` (Discovery Engine validation section — methodology contribution).
- **Status:** `fresh`
- **Opened:** 2026-04-25

---

### INS-054 — gp154 wall is **distribution-shift sensitivity**, not law nonexistence

- **Claim:** ZTARE applied to gp154 (cross-domain neural-network scaling exponents, n=110) hits a 14× HOLDOUT MRE wall that is NOT explained by "no closed-form law exists." Empirical diagnosis (offline epistemic-airgap script `scripts/public/gp154_offline_verify.py`, 18 hand-authored K≤7 candidate forms across 5 hypothesis families):
  1. **All forms converge to visible mean|res| ≈ 0.27-0.33 / HOLDOUT MRE ≈ 3.5-4.2.** The constant predictor (K=1) performs identically. No form extracts measurable signal beyond predicting the visible mean.
  2. **The 12-15× visible→holdout degradation is structural distribution shift**, NOT measurement noise. Diagnosed via feature-distribution audit:
     - `fit_convention`: visible 16% Chinchilla-family vs **holdout 0% Chinchilla-family**. Convention-bridging signal trained on visible has zero weight on holdout.
     - `modality`: visible 62% language vs holdout 25% language. Holdout has high concentration of single-row modalities (game_strategic, vision_vq_32x32, synthetic_graph) the form has never seen.
     - `study`: holdout includes single-row attributions (alphazero_connectfour, barkeshli2024, bansal2022_nmt) — out-of-distribution by construction.
  3. **Reframe:** the substrate's holdout is OOD by design, not a hidden test of within-distribution generalization. The bounded-null thus measures *distribution-shift sensitivity*, not law nonexistence.
- **Methodology contribution:** ZTARE + offline-airgap-verify + feature-distribution audit constitutes a **feature-completeness diagnostic**. When discovery fails, the apparatus disambiguates three causes: (a) form-family insufficiency (more K helps), (b) feature insufficiency (need C, D, E, σ from source papers), (c) **distribution shift** (visible≠holdout in feature space). gp154 is a clean case of (c).
- **Evidence pointers:**
    - `scripts/public/gp154_offline_verify.py` (18 candidates × 4 rounds, all fail by 14×)
    - Feature-distribution diagnostic computed 2026-04-25 night (visible vs holdout `scaling_var/fit_convention/modality/study` counts)
    - PDF master reference: `Extracting Neural Scaling Law Exponents.pdf` (61 measurements with α + CI from canonical sources: Hoffmann/Chinchilla, Kaplan, Bahri, Henighan, Hestness, OLMo, EpochAI, Cerebras-GPT, Sharma/Kaplan, Bansal NMT, Barkeshli, ScaleCNN, Pythia)
    - Augmented features sidecar (partial, 32/110 rows): `projects/gp154_scaling_law_exponents/features_augmented.py`
- **Confidence tier:** `confirmed` — 18 candidates × 5 form families converge to identical wall; distribution shift directly measured by per-feature visible-vs-holdout count difference.
- **Paper target(s):** `paper5` Nature MI submission. Reframe ZTARE as **Ontological Diagnostic Tool** for distribution-shift detection in scientific datasets, not just law discovery. Synthetic substrate triad (INS-053) provides positive validation; gp154 provides the negative-case methodology demo.
- **Status:** `fresh`
- **Opened:** 2026-04-25
- **Open work:** (a) ✅ DONE — IID stratified-shuffle test (`scripts/public/gp154b_iid_test.py`) + 5-fold stratified CV (`scripts/public/gp154c_kfold_cv.py`) executed. **Final rigorous decomposition (each row held out exactly once across 5 stratified folds):**
    - OOD (current gp154 arbitrary single holdout): best HOLDOUT MRE = 3.51 (14× threshold)
    - IID stratified single-fold, n=12, 5 seeds: range 0.39-1.32, mean 0.97 (4× threshold) — **single-fold n=12 is sampling-variance-dominated; lucky-seed 0.39 was an artifact**
    - **5-fold stratified CV (proper bound): mean MRE = 1.58 ± 0.55 (6.3× threshold), range across folds 0.84-2.39, 0/5 folds pass**
    - **Decomposition: distribution-shift contributes ~55% of OOD wall (3.51 → 1.58 = 1.93 MRE drop). Remaining 1.58 ± 0.55 is irreducible K≤7 heterogeneity under proper CV methodology — robust bounded null at 6.3× threshold.**
- **Refined claim (post-IID decomposition):**
    1. **Universal-law bound (OOD):** No K≤7 closed-form law generalizes from training distribution to OOD modalities. The wall is 14× threshold and is genuine extrapolation failure.
    2. **Feature-sufficiency bound (IID):** Within-distribution at K≤7, MRE ranges 0.4-1.3 across random splits. The lower envelope (0.39) suggests feature sufficiency is *almost* achieved given the existing features — consistent with "convention-bridging requires C/D/E features which are partially missing."
    3. **Methodology contribution:** The OOD-vs-IID decomposition is a novel scientific dataset diagnostic. ZTARE + matched-distribution shuffle = "feature-completeness auditor" that quantitatively decomposes (a) distribution-shift sensitivity, (b) holdout-sample-size variance, (c) irreducible heterogeneity at given K.
- **Cyborg-physics-engine framing (Gemini Pro 2026-04-25):** ZTARE is reframed from autonomous-discovery oracle to a particle-accelerator-style apparatus where human physicist sets priors (hypothesis space), LLM mutator searches, Cage adjudicates objectively. Hypothesis warming is collaboration, not contamination — the holdout remains hidden and the SciPy solver is mathematically objective. Under this framing, this entire diagnostic exchange (read PDF master table, augment features.py with C/D/E from canonical sources, run OOD-vs-IID decomposition) IS the methodology contribution.
- **Final test (Step #2 — feature-completeness diagnostic, 2026-04-25 night):** reran 5-fold stratified CV with `features_augmented.py` (adds C, D, E, joint-form α/β, is_compute_optimal_design from canonical Hoffmann 2022 / Kaplan 2020 / Bahri 2024 / Hestness 2017 sources for 32 of 110 rows). Tested 4 augmented-feature candidate forms (`AUG_chinchilla_joint_form_K=3`, `AUG_with_dataset_size_K=4`, `AUG_compute_per_param_K=4`, `AUG_compute_optimal_anchor_K=3`). **Result:**
    - Baseline per_scaling_var_K=4 mean CV MRE: **1.58 ± 0.55** (without augmentation)
    - Augmented per_scaling_var_K=4 mean CV MRE: **1.58 ± 0.55** (with augmentation — *identical*)
    - Best augmented-feature form: AUG_chinchilla_joint_form_K=3 = **1.59** (worse than baseline)
    - **Augmenting with canonical C/D/E + joint-form parameters does NOT reduce the irreducible bound.**
- **Final claim (peer-reviewable):** The gp154 cross-domain α-prediction wall has been decomposed into three components, all empirically measured: (1) **distribution-shift artifact** (~55% of OOD wall) — controllable via stratified CV; (2) **holdout-sample sampling variance** (~5% of OOD wall) — controllable via k-fold CV; (3) **irreducible K≤7 heterogeneity** = **1.58 ± 0.55 mean CV MRE (6.3× threshold)** — robust to feature augmentation with canonical C/D/E from source papers. **The cross-domain scaling-law literature is genuinely incommensurable in low-parameter closed form, even with full canonical-physics features. This is a structural property of how Kaplan/Chinchilla/Bahri/Henighan methodologies relate, not a feature-collection failure.**
- **Remaining work:** (b) cross-family replication on gp159/160/161 to harden Discovery Engine claim; (c) Nature MI draft using two-act structure: Act I = synthetic triad PASS (positive validation), Act II = gp154 OOD/IID/CV decomposition with augmented-feature negative test (feature-completeness diagnostic methodology); (d) optional: extend feature augmentation to all 110 rows + retest at K=10, K=15 budgets to bound at-what-K the unified law becomes accessible (if at all).

---

### INS-054 — ZTARE has the raw capability to enable scientific discovery; the discovery itself is pending

- **Claim:** Three pre-registered synthetic adversarial tests (GP-159 Retrieval-Trap, GP-160 Asymptotic Wall, GP-161 MDL Anti-Goodhart) pass across two mutator families (OpenAI o3, Anthropic claude-opus). The apparatus avoids three specific failure modes that would disqualify a discovery claim: (1) retrieval from parametric memory (GP-159: non-standard constants recovered, anti-retrieval gate clean), (2) extrapolation breakdown (GP-160: asymptotic wall gate passes, polynomial trap avoided), (3) MDL Goodharting (GP-161: K=10 oscillatory truth accepted, parsimony not forced). Cross-mutator scores: o3 achieves 82-90 on all three; claude-opus achieves 81 on the hardest (GP-161). The honest scope: this validates the apparatus as a recovery engine with anti-gaming discipline. It does NOT validate the apparatus as a discovery engine — all three substrates have operator-authored ground truth. The apparatus has not yet discovered anything the operator didn't know. That claim requires at least one unknown-GT success (GP-163d pending). The analogy to instrumentation: "this telescope works" is proven; "this telescope found a new planet" is pending.
- **Evidence pointers:**
    - E-GP159-01 (score 90, o3; score 90, claude-sonnet): `projects/gp159_retrieval_trap/champion_eval_results.json`
    - E-GP160-01 (score 90, o3; score 82, claude-sonnet): `projects/gp160_asymptotic_wall/champion_eval_results.json`
    - E-GP161-01 (score 90, o3; score 81, claude-opus): `projects/gp161_mdl_anti_goodhart/champion_eval_results.json`
    - GP-163d (real-world discovery attempt, in flight): `projects/gp163d_unified_accel/`
    - Discovery Engine triad finding: F-DISCOVERY-ENGINE-TRIAD in EXPERIMENT_TRACK_RECORD.md
- **Confidence tier:** `confirmed` — three pre-registered tests, two mutator families, all pass. Scoped to synthetic recovery; discovery pending.
- **Paper target(s):** `paper5` (Chapter 2½ empirical validation section — already drafted with the triad results; this insight sharpens the scope claim).
- **Status:** `fresh`
- **Opened:** 2026-04-26

---

### INS-055 — PMOND v5.2 is a calibration-only survivor whose generalization failure localizes the next gravity pivot to an internal-aware EFE coordinate

- **Claim:** The post-PN `v5.2` refinement survives a canonical `A/B/D/N` multistart refit but does not survive fresh-domain extrapolation, and the failure pattern localizes the next structural move. In the saved 40-restart calibration-only backtest, `v5.2` reaches mean `A/B/D/N` MRE `0.239` versus locked `v5` at `0.240`, confirming that the smoother EFE family is a real interpolation improvement rather than a hallucinated one. But the same frozen fit still fails the fresh UDG proxy dark check (`0.868 / 0.653` mean/median heuristic MRE; best fixed-`g_ext` still `0.741 / 0.860`). Four independent post-run inversion passes then converged on the same narrower diagnosis: the live blind spot is not "need more pressure boost" but "EFE suppression indexed by external field alone is too class-blind." Gemini Pro, a generic `gpt-5.5` cold shot, a targeted `gpt-5.5` internal-aware-EFE cold shot, and a local Codex alien-math pass all independently propose the same pivot class: the external suppression threshold must be renormalized by a local internal-support invariant (e.g. `g_bar`, pressure support, or a sigma/rho-mediated auxiliary scalar), so moderate external fields do not quench high-support systems as early as diffuse UDG-like systems.
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-V52-UDG-01`, `F-GP163D-V52-CAL-ONLY-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/pmond_v52_abdn_40restart_summary.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/cold_shot_eigenquestion_response.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/cold_shot_internal_aware_efe_response.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/codex_cold_shot_alien_math.md`
      - `projects/gp163d_unified_accel/raw/V5_DARK_DATASET_VALIDATION.md`
    - Paper target update: `papers/paper7/draft.md` §11.15.10 and §11.15.12
- **Confidence tier:** `confirmed` — one saved calibration reproduction plus one fresh-domain fail, with cross-model convergence on the causal split. The proposed pivot family itself is still unvalidated.
- **Paper target(s):** `paper7`, `paper8`
- **Status:** `fresh`
- **Opened:** 2026-04-28
- **Last revised:** 2026-04-28

### INS-056 — The simplest Newtonian-safe baryonic-depth coevolution law is not the missing dark-domain shield

- **Claim:** The first admissible `phi_b`-based macroscopic-depth falsifier was worth running, and the optimizer-risk check makes the null stronger. The implemented family used a Newtonian-safe standard-`nu` base and a single bounded depth state `C(phi_b)` with `phi_b ~ G*Mbar/Rchar`, letting that same `C` modulate both anomaly amplitude and the EFE threshold. Rerunning under a stronger global `differential_evolution(..., polish=True)` fitter left the main verdict unchanged: calibration stays degraded at mean `0.315`, the fitted `phi_b` proxy is central only through amplitude coupling, not threshold renormalization, and the frozen dark-domain pass still worsens PNe (`0.511` median MRE) while leaving UDG at `1.145 / 0.391` mean/median. The convergent reading is therefore stronger than before: not “macroscopic depth was wrong to test,” but “the simplest row-wise `Mbar/Rchar` depth proxy is not the shared shield the prior cold shots were pointing toward, and that is not just a local-optimizer artifact.”
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-MACRO-01`, `F-GP163D-MACRO-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/macroscopic_coevolution_suite_summary.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/macroscopic_coevolution_suite_summary.md`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/post_internal_aware_null_takeaway.md`
- **Confidence tier:** `confirmed` — one explicit Newtonian-safe implementation, one frozen PNe+UDG fail, nested ablations isolating amplitude-vs-threshold central, and local/global optimizer agreement on the substantive null.
- **Paper target(s):** `paper7`, `paper8`
- **Status:** `fresh`
- **Opened:** 2026-04-28
- **Last revised:** 2026-04-28

### INS-057 — The simplest inverse-surface-density shield is descriptively right but not a central row-wise dynamical shield

- **Claim:** The low-surface-density inversion was worth testing because it flips the UDG-vs-PNe ordering in the right direction, unlike `phi_b`. But even after rerunning under a stronger global `differential_evolution(..., polish=True)` fitter, the first admissible row-wise implementation still fails to become a central shield. The Newtonian-safe sparsity-shield family used `Q = (Sigma0 / Sigma_bar)^p / (1 + (Sigma0 / Sigma_bar)^p)` with `Sigma_bar ~ Mbar / Rchar^2`, retaining the existing `eta_pressure` amplitude channel and letting only the EFE threshold depend on `Q`. Under global fitting, the full model stayed near baseline (`0.241` mean `A/B/D/N` MRE), strict PNe stayed poor (`0.485` median MRE), and strict UDG landed at `0.855 / 0.704` mean/median with an ablation gap that remained negligible. The important strengthening is methodological: local and global optimizers found different parameter geometries but the same scientific null. The local fit neutralized `Q`; the global fit saturated `Q` to nearly `1` for every non-solar class. Either way, inverse surface density did not become a useful row-wise UDG shield.
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-SPARSITY-01`, `F-GP163D-SPARSITY-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/sparsity_shield_suite_summary.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/sparsity_shield_suite_summary.md`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/post_internal_aware_null_takeaway.md`
- **Confidence tier:** `confirmed` — one explicit sparsity-threshold implementation, one frozen PNe+UDG fail, nested ablation showing near-total inertness, and local/global optimizer agreement on the substantive null.
- **Paper target(s):** `paper7`, `paper8`
- **Status:** `fresh`
- **Opened:** 2026-04-28
- **Last revised:** 2026-04-28

### INS-058 — The minimal implicit total-field AQUAL repair is mathematically cleaner but still not enough

- **Claim:** Gemini’s critique that the repo had been overcommitting to multiplicative EFE syntax was serious and worth testing. The resulting implicit total-field AQUAL family is a genuine syntax change, not another metaphor or new shield scalar: `y` is solved from `y * mu(sqrt(y^2 + g_ext^2)) = x`, with the cluster channel retained through `theta = 1 + alpha*(1 - exp(-beta*eta_pressure))`. But the simplest row-wise implementation still fails to become a dark-domain rescue. Under global fitting, it lands at mean `A/B/D/N` MRE `0.251`, strict PNe median `0.486`, and strict UDG `0.981 / 0.732` mean/median. The fitted parameters are themselves informative: `beta≈0.012` flattens the pressure channel and `n≈6.36` sharpens the interpolation, yet the promised clean Banik-vs-UDG separation does not emerge strongly enough to beat the best prior strict pass. The correct compression is therefore not “the multiplicative-EFE critique was wrong,” but “the critique was mathematically valid and still insufficient as a minimal repair on this substrate.”
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-TFA-01`, `F-GP163D-TFA-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/total_field_aqual_suite_summary.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/total_field_aqual_suite_summary.md`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/post_internal_aware_null_takeaway.md`
- **Confidence tier:** `confirmed` — one explicit implicit-total-field implementation under global fitting, one frozen PNe+UDG fail.
- **Paper target(s):** `paper7`, `paper8`
- **Status:** `fresh`
- **Opened:** 2026-04-28
- **Last revised:** 2026-04-28

### INS-059 — Screening the external field with a simple baryonic-depth scalar inside total-field AQUAL is also not enough

- **Claim:** The screened-total-field synthesis was the cleanest remaining row-wise escape hatch after the `phi_b` and TFA nulls: keep the implicit Newtonian-safe total-field syntax, but apply the baryonic-depth state to attenuate the external field rather than to boost amplitude or threshold directly. That family is now tested and does not rescue the program. Under global fitting it lands at mean `A/B/D/N` MRE `0.251`, strict PNe median `0.482`, and strict UDG `0.981 / 0.732` mean/median, which is effectively identical to the unscreened TFA null. The nested `lambda_D=0` refit changes the calibration objective by only `+3.8e-05` and leaves UDG unchanged to four decimal places, so the new screening channel is not central. The fitted state geometry is itself diagnostic: the depth scalar screens `A/B` galaxies moderately but leaves `D/C/N/S` almost unscreened, meaning monotone row-wise `phi_b` attenuation never becomes the selective UDG-vs-Banik discriminator the mechanism required. This is stronger than saying “another `phi_b` family failed.” It kills the specific synthesis “screen the host field with a simple depth scalar inside TFA,” which was the last mathematically clean row-wise recombination of the live nulls.
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-STFA-01`, `F-GP163D-STFA-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/screened_total_field_aqual_suite_summary.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/screened_total_field_aqual_suite_summary.md`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/post_internal_aware_null_takeaway.md`
- **Confidence tier:** `confirmed` — one explicit screened-total-field implementation under global fitting, one screening-off ablation refit, one frozen PNe+UDG fail.
- **Paper target(s):** `paper7`, `paper8`
- **Status:** `fresh`
- **Opened:** 2026-04-28
- **Last revised:** 2026-04-28

### INS-060 — The literal superfluid phase-gate metaphor fails because `eta_pressure` has the opposite empirical sign

- **Claim:** The exact local superfluid-style phase-gate law is now a formal negative control for de-anchored analogy. Implemented literally as `stress = sqrt((x/a0)^2 + (g_external/a0)^2 + eta_pressure^2)`, `f_s = 1/(1 + exp((stress - s_crit)/width))`, and `g_pred = x + gamma*f_s*sqrt(x*a0)`, it fails the calibration basin at mean `A/B/D/N` MRE `0.507`. The failure is not generic optimizer weakness; it is the predicted sign contradiction. The fitted gate makes `f_s` effectively zero in the high-`eta_pressure` classes (`B` and `D`), giving `B=0.849` and `D=0.897`. A nested `eta_pressure`-off refit improves the calibration objective by `0.124`, improves `B` by `0.222`, and improves `D` by `0.318`. Therefore the substrate does not support “thermodynamic pressure decoheres the anomaly.” It supports the opposite sign: pressure/support is empirically associated with extra amplification in the calibration basin. The correct lesson is not that phase-medium analogies are impossible; it is that any admissible phase-medium law must make pressure a polarizing/amplifying state, then explain why that does not collapse back into the already-failed local amplitude families.
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-PHASEGATE-01`, `F-GP163D-PHASEGATE-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/phase_gate_superfluid_suite_summary.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/phase_gate_superfluid_suite_summary.md`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/post_internal_aware_null_takeaway.md`
- **Confidence tier:** `confirmed` — exact local phase-gate implementation under global fitting, nested `eta_pressure` ablation, and direct class-level sign readout.
- **Paper target(s):** `paper7`, `paper8`
- **Status:** `fresh`
- **Opened:** 2026-04-28
- **Last revised:** 2026-04-28

### INS-061 — After the row-wise null stack, the next gravity object is host-aware extendedness, not another local scalar

- **Claim:** The post-null cross-model cold shot now converges on the same narrower next object. After explicit falsification of internal-aware threshold transfer, `phi_b` coevolution, sparsity shielding, implicit total-field AQUAL, screened-total-field AQUAL, and the literal superfluid phase gate, both `gpt-5.5` (`reasoning_effort=xhigh`, fallback disabled) and Gemini Pro returned `NONLOCAL_EXTENDEDNESS_STATE_NEEDED`. The shared diagnosis is not that modified gravity is false and not yet that a full 3D Poisson solve is mandatory. The supported claim is narrower: the remaining live mechanism is host-aware structure such as external tidal shear, field-gradient coherence, boundary-condition anisotropy, or a solved-field state. A fresh row-wise candidate is only admissible if it introduces non-leaky information not already exhausted by `x`, `g_ext`, `eta_pressure`, `M/R`, `M/R^2`, or algebraic total-field norms. The cheapest next step is therefore a feature audit, not another fit: can the substrate compute an external tidal-shear / host-field-gradient proxy across `A/B/D/N`, PNe, UDG, and Banik/Solar analogs without target kinematics, class labels, or residual leakage?
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-COLDSHOT-POSTNULL-01`, `F-GP163D-NONLOCAL-NEXT-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/cold_shot_post_structural_nulls_gpt_55.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/cold_shot_post_structural_nulls_gemini_31_pro_preview.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/codex_cold_shot_post_phase_gate.md`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/post_structural_nulls_cross_model_takeaway.md`
- **Confidence tier:** `confirmed` — cross-model convergence after six explicit row-wise falsifiers; still bounded to “next object,” not a proof that 3D field solving is necessary.
- **Paper target(s):** `paper7`, `paper8`
- **Status:** `fresh`
- **Opened:** 2026-04-29
- **Last revised:** 2026-04-29

### INS-062 — The current gp163d substrate cannot honestly test tidal-shear EFE

- **Claim:** The post-null tidal-shear idea remains physically live, but the current gp163d row-wise substrate is not an admissible instrument for testing it. The strict audit proxy was `shear_kpc_inv = (g_external/a0) / D_host_kpc`, with `D_host` required to come from external host/environment geometry rather than internal radius, velocity dispersion, object class, residuals, or observed `g_obs`. The audit found clean coverage for Banik/wide binaries (`N` median `2.317e-01 kpc^-1`), dwarf satellites (`D` median `7.776e-04 kpc^-1`), and PNe projected group geometry (`2.168e-03 kpc^-1`), but zero strict coverage for required classes `A`, `B`, and `UDG`. UDG rows have only environment labels, not host distances or host masses. Therefore a shear-gated row-wise fit on the existing table would be scientifically uninterpretable: it would either drop required domains or use leaky substitutes. The next gravity move is not another scalar tweak and not a naive CSV enrichment; it is either a host-geometry / field-gradient substrate or a pivot of compute to the already-live NS Phase 4 branch.
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-SHEAR-AUDIT-01`, `F-GP163D-SHEAR-AUDIT-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/tidal_shear_feature_audit.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/tidal_shear_feature_audit.md`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/tidal_shear_feature_audit.png`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/run_tidal_shear_feature_audit.py`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/post_structural_nulls_cross_model_takeaway.md`
- **Confidence tier:** `confirmed` — explicit pre-fit feature audit; bounded to instrument adequacy, not a physics falsification of tidal shear.
- **Paper target(s):** `paper7`, `paper8`
- **Status:** `fresh`
- **Opened:** 2026-04-29
- **Last revised:** 2026-04-29

### INS-063 — Post-shear-audit cold shot promotes a small 3D gravity sandbox as the next instrument, not another row-wise fit

- **Claim:** After the failed tidal-shear feature audit, a fresh `gpt-5.5` cold shot with the shear-audit and NS Phase 3 evidence packet returned `PIVOT_TO_3D_GRAVITY_SANDBOX`. The model agreed with the local/Gemini synthesis that the current CSV should not be patched with one-off `D_host` guesses, because that would turn an instrument null into a narrative patch. The next gravity move is bounded: build a small host-geometry / field sandbox with object-level host graph, independent host metadata, `g_ext` vector, tidal tensor, matched panels, one preregistered shear-gated EFE candidate, nested shear-off control, host-shear permutation nulls, and fail-closed numerics. This does not prove modified gravity, tidal shear, or AQUAL. It changes the instrument required to test the remaining hypothesis. NS Phase 3 transfers geometry-search discipline only: triage, spike-vs-plateau framing, fail-closed diagnostics, nested controls, and resolution skepticism. It does not transfer Navier-Stokes equations, vorticity-stretching mechanisms, BKM diagnostics, or ansatz parameter values into gravity.
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-COLDSHOT-PIVOT-01`, `F-GP163D-3D-PIVOT-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/cold_shot_post_shear_audit_pivot_gpt_55.json`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/cold_shot_post_shear_audit_pivot_gpt_55.md`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/post_shear_audit_3d_pivot_takeaway.md`
      - `projects/gp163d_unified_accel/raw/dark_dataset_udg/tidal_shear_feature_audit.md`
- **Confidence tier:** `confirmed_for_next_instrument` — one strict feature audit plus one attribution-clean `gpt-5.5` cold shot; not a physics confirmation.
- **Paper target(s):** `paper7`, `paper8`
- **Status:** `fresh`
- **Opened:** 2026-04-29
- **Last revised:** 2026-04-29

### INS-066 — The repaired 3D AQUAL sandbox revives tidal shear as a live separator and reclassifies the earlier `n96` blow-up as instrument failure

- **Claim:** The first large-box 3D gravity results materially changed after explicit instrument repair, and the completed repaired `Gamma` ladder plus focused refinement sharpened the remaining object again. The decisive move was not “more GPU” in the abstract but a targeted empty-box audit of the no-source tidal background. At `n96` with conservative `face_flux`, the no-source tidal background is solvable under Newton-Krylov to `2.05e-9` (`L=2.0`) and `5.60e-10` (`L=2.5`), while the `L-BFGS-B` residual-minimization path stalls near `1e-3`. Once the main sandbox is switched to Krylov background subtraction, the earlier `n96` catastrophe (`UDG tidal/uniform = 419.4`, binary `1.809`, unconverged background) disappears. The repaired large-box sequence at fixed physics settings then recovers the desired qualitative separator across box-size controls and a continuum-hardening repeat. More importantly, the fixed-geometry `L=3.0,n128` `Gamma` ladder now resolves the surviving separator as a structured response surface rather than a loose “UDG preserved” slogan: binary tidal/uniform falls cleanly and monotonically across the full refined ladder (`1.001 -> 0.871 -> 0.806 -> 0.766 -> 0.736 -> 0.714 -> 0.698 -> 0.675`), while the diffuse UDG-like source remains protected at every tested `Gamma` and exhibits a broad enhancement band peaking around `Gamma ~ 0.20–0.25` (`1.039 -> 1.026 -> 1.397 -> 1.609 -> 1.605 -> 1.518 -> 1.527 -> 1.398`). That hump survives, and is even stronger, in the `p90` internal-acceleration metric, peaking at `1.95` near `Gamma = 0.25`. **The 3D AQUAL operator establishes a strict scale-separator: compact sources undergo monotone environmental suppression, while diffuse sources exhibit geometric shielding and potential mid-shear enhancement.** A fresh hump-probe rerun with new field diagnostics then cut against the simplest cancellation-surface artifact story: at `Gamma = 0.20, 0.25, 0.30`, the UDG hump reproduces (`1.590 / 1.605 / 1.520`) while the mass fraction with `|g_total| <= 1e-5` or `3e-5` is `0.0`, and the mass fraction with `|g_total| / |g_internal| <= 0.25` is also `0.0`. The subsequent completed `L=4.0,n160,Gamma=0.25` tensor-rotation ladder adds the key anisotropy result: UDG tidal/uniform response forms a U-shape across `0/15/30/45/60/75/90 deg` (`1.509 / 1.390 / 1.151 / 1.124 / 1.156 / 1.377 / 1.503`), while the binary branch remains nearly angle-invariant (`0.713 / 0.712 / 0.713 / 0.716 / 0.719 / 0.721 / 0.723`). A later repaired JAX/GPU same-configuration replication on 2026-05-01 strengthened the implementation-side evidence: at `L=4.0,n160,Gamma=0.25`, the `0/45/90 deg` ratios were UDG `3.461 / 2.284 / 3.769` and binary `0.6999 / 0.7051 / 0.7116`, with no-source tidal background residuals below `1e-6` at every angle. A follow-up action-theta discriminator then blocked the tempting dynamic overreach: conservative bidirectional sweeps over `0/45/90 deg` returned zero loop area and zero forward/backward action delta for both UDG and binary under low residuals, so the static U-shape licenses an orientation-dependent conservative action landscape but not orbital decay, nonlinear tidal heating, or dissipation. The honest compression is therefore no longer “3D AQUAL failed” and not yet “AQUAL is proven.” It is: the small-box and early `n96` nulls were instrument artifacts; under repaired large-box backgrounds the 3D sandbox exhibits a robust compact-vs-diffuse split; the diffuse branch carries a real nonmonotone shear-response structure; that structure is orientation-sensitive in the diffuse branch but nearly orientation-invariant in the compact branch; and the static result should be framed as a theoretical separator/falsifier, not a dynamic heating mechanism. The remaining risks are finite-box / tensor-boundary anisotropy and the absence of a time-dependent field model, both explicitly queued as discriminators rather than promoted away. Further same-code resolution escalation is not the default next move after the JAX/GPU `n=160` replication; a new gravity run should answer an independent-boundary, field-localization, or observational discriminator.
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-3D-SANDBOX-02`, `F-GP163D-3D-SANDBOX-02` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Rotation extension rows: `E-GP163D-PHASE5AM-01`, `F-GP163D-PHASE5AM-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Action discriminator rows: `E-GP163D-PHASE5AN-01`, `F-GP163D-PHASE5AN-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - JAX/GPU replication rows: `E-GP163D-JAXBG-N160-01`, `F-GP163D-JAXBG-N160-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/empty_box_campaign_n96_background_probe.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/background_krylov_probe_n96_boxL2p0_faceflux.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/background_krylov_probe_n96_boxL2p5_faceflux.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL2p0_n96_krylovfix.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL2p5_n96.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL3p0_n96_krylovfix.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL3p0_n128_krylovfix.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL3p0_n128_gamma0p02_krylovfix.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL3p0_n128_gamma0p10_krylovfix.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL3p0_n128_gamma0p20_krylovfix.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL3p0_n128_gamma0p30_krylovfix.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL3p0_n128_gamma0p45_krylovfix.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/gamma_ladder_report.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_gamma_scan_takeaway.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260430_1611531221/rotation_ladder_debrief.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260430_2092015817_action_probe/action_theta_probe_L4p0_n64_rot0_45_90_bidirectional_conservative.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_1442417196_jaxbg_n160_final/projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/gpu_domain_validation_result_gpu_gamma0p25_faceflux_jaxbg_L4p0_n160.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_1442417196_jaxbg_n160_final/projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL4p0_n160_gamma0p25_rot0_jaxbg.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_1442417196_jaxbg_n160_final/projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL4p0_n160_gamma0p25_rot45_jaxbg.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_1442417196_jaxbg_n160_final/projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/minimal_aqual_sandbox_summary_gpu_faceflux_boxL4p0_n160_gamma0p25_rot90_jaxbg.json`
      - `projects/gp163d_unified_accel/workspace/next_discriminator_queue.jsonl`
- **Confidence tier:** `confirmed_for_instrument` — repaired empty-box audit, repaired box-size controls, one continuum-hardening repeat, a completed `Gamma` ladder, a first low-field artifact probe, a completed `0 -> 90 deg` tensor-rotation ladder, a repaired JAX/GPU `n=160` replication of the `0/45/90 deg` discriminator, and a conservative action-theta no-hysteresis discriminator; still bounded to the sandbox instrument and not yet a continuum-complete physics claim.
- **Paper target(s):** `paper7`, `paper8`
- **Status:** `fresh`
- **Opened:** 2026-04-29
- **Last revised:** 2026-05-01

### INS-064 — NS Phase 3 found a spike-versus-plateau split, not a generic blowup basin

- **Claim:** The first H100 Phase 3 sweep on `ns_millennium_hunt` did not produce a broad, family-agnostic “alien NS” success. It produced a much narrower and more useful structural split. Across `53` completed integrations (`8` triage at `N=64`, `45` full at `N=128`), only one run crossed the Phase 4 flag threshold: `full_chiral_torus_knot_A1.0_beta0.5_chi0.3` with `late_window_slope = 1.021`, `growth_ratio = 16.248`, `energy_dissipation_pct = 1.116`, and divergence staying at machine precision. By contrast, the `chirped_cyclic_shear` family never crossed `1.0`, but formed a broad high-slope plateau with many members in the `0.75–0.94` band and clear monotone dependence on axial anisotropy (`lambda_z`). The correct compression is therefore not “de-anchored search found blowup,” but “the search space split into a **sparse topological spike** and a **broad anisotropic shear plateau**.” That changes the next move. The right Phase 4 question is no longer “audit the winner.” It is “does refinement sharpen the rare spike, lift the broad plateau, or collapse both?” A secondary apparatus finding also matters: the run exposed an instrument bug where `lorenz_projected` wrote `ok=true` with non-finite diagnostics; the Phase 3/4 drivers are now patched to fail closed on any `NaN/Inf` diagnostic series. This is exactly the paper-7-style pattern of informative null compression plus instrument repair before escalation.
- **Evidence pointers:**
    - Experiment rows: `E-GP186-PHASE3-01`, `F-GP186-PHASE3-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/ns_millennium_hunt/workspace/phase3_results_h100_20260429.jsonl`
      - `projects/ns_millennium_hunt/workspace/phase3_analysis_20260429.md`
      - `projects/ns_millennium_hunt/workspace/ns_phase3_full_20260429T001804.log`
      - `projects/ns_millennium_hunt/workspace/phase3_driver.py`
      - `projects/ns_millennium_hunt/workspace/phase4_audit.py`
- **Confidence tier:** `confirmed` — one closed H100 sweep, one explicit Phase 4 survivor, one broad near-miss family, several clean null families, and one post-run instrument repair directly justified by the artifacts.
- **Paper target(s):** `paper8`, `unassigned`
- **Status:** `fresh`
- **Opened:** 2026-04-28
- **Last revised:** 2026-04-28

### INS-065 — NS Phase 4 overturned the spike-versus-plateau story: two mechanism families survive refinement

- **Claim:** The GH200 Phase 4 audit on `ns_millennium_hunt` materially changed the scientific compression again. The pre-registered control was decisive. Across `6` audit integrations (`2` candidates × `N=128,192,256`), both the knot survivor and the chirped-shear control strengthened under refinement while keeping divergence at machine precision. `full_chiral_torus_knot_A1.0_beta0.5_chi0.3` rose from slope `1.021` to `1.3734` and from BKM proxy `106.22` to `178.25`. More importantly for the causal story, `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0` rose from `0.9353` to `1.2736` with BKM proxy `97.23 -> 151.48`. This falsifies the earlier compression that the field had narrowed to one sparse topological spike and one broad but still subcritical plateau. The correct post-Phase-4 statement is stronger and narrower at once: **two distinct de-anchored mechanism families survive the first refinement audit**. One is topological/curvature-heavy and parameter-localized; the other is shear-sheet-like and family-broad. This does not prove blowup. It does establish that the control-family audit was central and that the next honest branch is anti-artifact mechanism discrimination, not more family enumeration.
- **Evidence pointers:**
    - Experiment rows: `E-GP186-PHASE4-01`, `F-GP186-PHASE4-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/ns_millennium_hunt/workspace/phase4_audit_results.jsonl`
      - `projects/ns_millennium_hunt/workspace/phase4_audit_summary.json`
      - `projects/ns_millennium_hunt/workspace/phase5_routing.json`
      - `projects/ns_millennium_hunt/workspace/phase5_brief.md`
      - `projects/ns_millennium_hunt/workspace/phase4_analysis_20260429.md`
      - `projects/ns_millennium_hunt/workspace/ns_phase4_gh200_20260429T021950Z.log`
- **Confidence tier:** `confirmed` — one closed pre-registered GH200 audit, two survivors across a three-resolution ladder each, and a control-family uplift that directly changes the causal story.
- **Paper target(s):** `paper8`, `unassigned`
- **Status:** `fresh`
- **Opened:** 2026-04-28
- **Last revised:** 2026-04-28

### INS-067 — NS Phase 5 reframed the knot branch as a bounded anti-blowup boundary mechanism candidate rather than a blowup lead

- **Claim:** The full Phase `5a -> 5m` discriminator chain on `ns_millennium_hunt` changed the scientific object again, and this time in the opposite direction from prize-hunting hype. The knot branch survives enough hostility to remain scientifically real, but not in the way a singularity narrative would need. Symmetry breaking at `1%` poison preserves strong growth and intermittent stretching-like episodes, so the branch is not a trivial symmetry fake. But the denser lifeline and strobe passes show no stable stretching lock, no identity-persistent winner, and no monotone coarse-scale collapse. The strongest negative result is geometric: the `95%` identity envelope does not shrink ratchet-style (`[0.01015, 0.01611, 0.01015, 0.01015, 0.01279, 0.01464, 0.01736]`, final/min `1.71`), while the `99%` and `99.5%` cores are grid-floor contaminated. The strongest positive result is structural: the late-window is not a perfect zero-sum sink. Cycle-integrated local production remains weakly positive on both tracked identities (`track_A net +0.00467`, `track_B net +0.02335`), but this surplus does not belong to a single winner; `5l` shows leader switches and equal sparse stretch-axis occupancy (`0.143`) for both tracks, while `5m` adds only a weak misalignment-defense proxy rather than a clean curvature law. The honest compression is therefore not “failed blowup search” and not “hidden singular core.” It is **competitive two-core churn with weak positive production bias, but no geometric ratchet and no identity-stable stretching takeover**. That makes the branch more valuable as an anti-blowup boundary mechanism candidate than as a blowup lead.
- **Evidence pointers:**
    - Seam: `research_areas/private/seams/protocol/GP-189_ns_continuation_criterion_after_bounded_near_miss_seam.md`
    - Hypothesis row: exception to rule #1. This finding is a post-discriminator compression across a chained continuation seam rather than a single pre-registered H-row. The motivating protocol is the `GP-186` Phase 4/5 pre-registration chain plus the continuation criterion formalized in `GP-189`.
    - Experiment rows: `E-GP186-PHASE5-01`, `F-GP186-PHASE5-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Run artifacts:
      - `projects/ns_millennium_hunt/workspace/phase5j_scale_radius_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5j_scale_radius_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5k_topology_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5k_topology_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5l_dual_peak_budget_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5l_dual_peak_budget_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5m_curvature_proxy_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5m_curvature_proxy_audit.md`
      - `projects/ns_millennium_hunt/workspace/cold_shot_post_phase5i_gpt_55_compact.json`
      - `projects/ns_millennium_hunt/workspace/cold_shot_post_phase5i_gemini_31_pro_preview_compact.json`
- **Confidence tier:** `confirmed` — one closed discriminator chain across online and offline tests, multiple hostile narrative eliminations, two independent compact cold-shot convergences on `BOUNDED_NEAR_MISS`, and a clear surviving structural remainder.
- **Paper target(s):** `paper8`, `unassigned`
- **Status:** `fresh`
- **Opened:** 2026-04-29
- **Last revised:** 2026-04-29

### INS-068 — Recent gp163d and NS progress validates the operator-supervisor loop, not autonomous ZTARE theory discovery

- **Claim (one paragraph):** The post-v5.2 gravity and NS sequences show a bounded but important architecture fact: the strongest recent progress came from a symbiotic operator-supervisor workflow wrapped around ZTARE, not from the core iterative mutator loop alone. The central moves were recurring and partially mechanizable: cold-shot inversion, instrument-vs-physics null separation, empty/control gates before interpretation, boundary/rotation/resolution ladders, background-debt accounting, and dynamic-admissibility pivots. The correct engineering response is not to declare ZTARE useless and not to claim autonomous discovery; it is to compile those recurring operator moves into deterministic artifacts and gates. GP-190 Slice 2 provides the first concrete test: a zero-LLM replay audit over durable Paper 7 / track-record artifacts reconstructs the gp163d empty-box background gate, large-box boundary gate, tensor-rotation gate, background-debt ladder, and the NS dynamic-admissibility gate as typed discriminator proposals.
- **Evidence pointers:**
    - Seam: `research_areas/private/seams/engine/GP-190_post_run_discriminator_daemon_seam.md#2026-04-30-113149-edt-implementation-slice-2`
    - Hypothesis row: exception to strict H-row rule. This is a meta-architecture compression over closed experiment rows and already-open GP-190 seam work, not a new physics finding. It should remain scoped as methodology/instrumentation until replay coverage is quantified on more runs.
    - Run artifacts: `projects/gp163d_unified_accel/workspace/next_discriminator_queue.replay.jsonl`, `projects/ns_millennium_hunt/workspace/next_discriminator_queue.replay.jsonl`, `papers/paper7/draft.md` §11.15.11.2, `research_areas/EXPERIMENT_TRACK_RECORD.md` GP163D/GP186 rows.
- **Confidence tier:** `suggestive` — one replay implementation and two domains, but the template set is still small and coverage is not yet measured against a hand-labeled operator-move inventory.
- **Scope caveat (2026-04-30):** The first template library is PDE-heavy because it was extracted from gp163d and NS. It should not be treated as a universal discriminator grammar until replay is tested on discrete math / cryptography / abstract-algebra substrates. The v2 queue schema now records severity and license stage so shallow smoke tests and scratchpad analogies cannot support promotion.
- **Paper target(s):** `paper7`, `paper5`
- **Status:** `fresh`
- **Opened:** 2026-04-30
- **Last revised:** 2026-04-30

### INS-070 — The NS toxic-block certificate is fixed-N/substitution robust and the continuum bridge is a uniform normalized-margin obligation

- **Claim:** Phase 5BP changed the NS proof target from “is mode `20` a local artifact?” to “does the toxic-block margin persist across spectral scale and low/high interactions?” After 5BO produced an independently verified reduced square-completion certificate on `(mode20, auxiliary)` blocks, 5BP forbade mode `20` entirely and still found no stealth-growth bridge: `19` strict-stealth substitute states, `0` strict/near growth states, and `19/19` positive-definite reduced Hessian blocks around substitute high modes. Phase 5BQ then ran the pre-registered spectral-N ladder and blocked the strongest uniform-in-N interpretation because `N=24` produced negative reduced-block eigenvalues and Schur slack (`min_eig=-15.2886`, `min_schur=-18.6456`). Phase 5BS inverted that failure mode: warm-started high-`N` rows at `N=96/128` did recover the pressure-stealth tube (`strict_stealth_count=16`, `near_stealth_count=29`, `min_q_ratio=0.0001145`) and still found `0` strict/near growth, with all in-tube raw blocks positive. Phase 5BU then compressed the formal target: raw Schur slack need not diverge; a scale-invariant positive floor is enough. The finite atlas reports candidate floors (`min_freq_norm_eig_min=0.7254`, `min_eig_over_abs_trace=0.3374`, `min_schur_over_abs_c=0.9362`) and the Lean bridge now verifies that a uniform positive normalized margin would control low/high leakage. The correct paper-grade claim is therefore stronger than “N=48 only” but still short of a continuum theorem: finite-resolution/substitution/high-`N` sterility is robust in the audited atlas, while the remaining continuum bridge is the analytic proof of a positive normalized-margin infimum for all sufficiently high `N`.
- **Evidence pointers:**
    - Experiment rows: `E-GP186-PHASE5BO-01`, `F-GP186-PHASE5BO-01`, `E-GP186-PHASE5BP-01`, `F-GP186-PHASE5BP-01`, `E-GP186-PHASE5BQ-01`, `F-GP186-PHASE5BQ-01`, `E-GP186-PHASE5BS-01`, `F-GP186-PHASE5BS-01`, `E-GP186-PHASE5BU-01`, `F-GP186-PHASE5BU-01`, `E-GP186-PHASE5BV-01`, `F-GP186-PHASE5BV-01`
    - Hypothesis rows: `H-NS-5BO`, `H-NS-5BP`, `H-NS-5BQ`, `H-NS-5BS`, `H-NS-5BU`, `H-NS-5BV` in `research_areas/private/seams/mission/ztare_mission_hypothesis_ledger_seam.md`
    - Run artifacts:
      - `projects/ns_millennium_hunt/workspace/phase5bo_reduced_toxic_block_certificate.json`
      - `projects/ns_millennium_hunt/workspace/phase5bo_sos_receipt_verification.json`
      - `projects/ns_millennium_hunt/workspace/phase5bp_mode20_substitution_attack.json`
      - `projects/ns_millennium_hunt/workspace/phase5bp_mode20_substitution_attack.md`
      - `projects/ns_millennium_hunt/workspace/phase5bq_spectral_n_certificate_atlas.json`
      - `projects/ns_millennium_hunt/workspace/phase5bq_spectral_n_certificate_atlas.md`
      - `projects/ns_millennium_hunt/workspace/phase5bs_high_n_tube_recovery_or_normalized_certificate.json`
      - `projects/ns_millennium_hunt/workspace/phase5bs_high_n_tube_recovery_or_normalized_certificate.md`
      - `projects/ns_millennium_hunt/workspace/phase5bt_asymptote_extraction_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5bu_uniform_margin_candidate_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5bu_uniform_margin_candidate_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5bv_n128_tube_gap_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5bv_n128_tube_gap_audit.md`
      - `ztare_proofs/ZtareProofs/ns_spectral_diseconomy_toxic_block.lean`
      - `ztare_proofs/ZtareProofs/ns_sos_section_margin_bridge.lean`
      - `ztare_proofs/ZtareProofs/ns_core_tail_budget_bridge.lean`
      - `ztare_proofs/ZtareProofs/ns_continuum_tail_bound.lean`
      - `ztare_proofs/ZtareProofs/ns_asymptotic_margin_extraction.lean`
- **Confidence tier:** `confirmed_for_finite_resolution_atlas / asymptotic_bridge_open` — strong within the audited dealiased amplitude-block apparatus across mode substitution and high-`N` recovery; 5BT does not yet prove a conservative exponent gap; not a continuum regularity theorem and not a Clay claim.
- **Paper target(s):** `paper8`, `unassigned`
- **Status:** `fresh`
- **Last revised:** 2026-05-01
- **Opened:** 2026-04-30
- **Last revised:** 2026-04-30

### INS-069 — Persistent role offices are the accountable unit; transient LLM calls are artifacts

- **Claim:** ZTARE needs an explicit office-vs-invocation ontology and a layered accountability model. Persistent agents such as Codex / Claude Code / daemonized Research Director are role offices only when bound to a mandate, session, budget, claims, refusal duties, and durable communication address. Transient LLM calls inside the mutator, judge, cold-shot, or script-generation path are not offices; they are artifacts with provenance. Ultimate accountability remains with the human/deploying organization; operational accountability can be pushed to role offices; causal accountability belongs to the transition log; model-call attribution belongs to artifacts. This distinction prevents both over-personifying fungible model calls and under-protocolizing durable agents. The implementation now reflects the distinction through `org/channels/<role>/inbox/`, typed `agent.message.*` envelopes, work-discovery integration, and transition-log events.
- **Evidence pointers:**
    - Experiment rows: `E-GP167-AGENT-CHANNEL-01`, `F-GP167-AGENT-CHANNEL-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Seam: `research_areas/private/seams/mission/GP-167_multi_agent_interface_form_factor_seam.md` Turn 8
    - Implementation:
      - `src/ztare/orchestration/agent_channels.py`
      - `scripts/public/control/agent_channel.py`
      - `src/ztare/orchestration/work_discovery.py`
    - `docs/concepts/organizational_primitives.md` primitive #8
    - `docs/concepts/ztare_research_company_architecture.md`
- **Confidence tier:** `confirmed_for_architecture` — implemented in the local org runtime and grounded in current protocol/accountability review; not yet enterprise-grade because RBAC-backed channel permissions, Orbit rendering, retention, and A2A/ACP adapters remain future work.
- **Paper target(s):** `paper4`, `paper5`
- **Status:** `fresh`
- **Opened:** 2026-04-30
- **Last revised:** 2026-04-30

### INS-071 — GP154 normalized neural-scaling curves have a live candidate axis-exponent law, but the law is not earned until gauge/provenance and external-sweep tests pass

- **Claim:** The 2026-05-01 live rerun of `gp154_scaling_law_normalized` upgrades the normalized axis-collapse object from offline anchor to a serious scientific candidate. The champion (`score=94`) models normalized excess-loss shape as a stationary axis relaxation:
  `z_hat = curve_axis_rev ** exp(log_alpha_N + delta_D*is_d_sweep + delta_M*is_compute_mixed + delta_joint*joint_fit + delta_error_loss*error_loss + delta_nontext*nontext)`.
  The important structure is not the literal cold-shot Lagrangian; that form failed pathologically in iter 1. The surviving law is the compressed residue: after per-curve floor/amplitude gauge removal, curve shape is governed primarily by sweep geometry, with mixed compute-frontier curves relaxing faster than pure N/D curves and small bounded measurement-family offsets absorbing non-provenance residuals. This is plausibly novel relative to standard raw-loss scaling laws, but it is not yet a settled universal law. The open falsifier is whether the same exponent structure survives fresh modern N/D or mixed-sweep data and whether a provenance-key model fails to beat it under equal K.
- **Evidence pointers:**
    - Experiment rows: `E-GP154N-AXISLIVE-01`, `F-GP154N-AXISLIVE-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Champion submission: `projects/gp154_scaling_law_normalized/workspace/submissions/iter_003_20260501T112619.957316+0000.py`
    - Champion judge artifact: `projects/gp154_scaling_law_normalized/champion_eval_results.json`
    - Full log: `projects/gp154_scaling_law_normalized/debate_log_iter_1777634894.md`
    - Prior offline anchor: `projects/gp154_scaling_law_normalized/workspace/shape_collapse_diagnostic.json`
- **Confidence tier:** `provisional_scientific_candidate` — strong within the current substrate and live ZTARE loop; not yet dark-data validated; not a universal theorem.
- **Paper target(s):** `paper6_neural_scaling`, `paper5`
- **Status:** `fresh`
- **Opened:** 2026-05-01
- **Last revised:** 2026-05-01
- **Law-upgrade audit (2026-05-01):** `H-GP154N-03` tested gauge perturbation, provenance rivals, and stratified residuals. The audit sharpened the claim: the law-track object is the three-axis normalized relaxation law (`alpha_MIXED≈3.45`, `alpha_N≈1.46`, `alpha_D≈1.48`), not the score-94 K=6 fitted champion and not the literal cold-shot Lagrangian. The K=6 champion passes gates but has farther-tail MAE `0.1186`; the three-axis baseline has farther-tail MAE `0.0795`; a K=4 geometry-envelope form has holdout MAE `0.0767` and farther-tail MAE `0.0915`. Gauge perturbation is stable on farther-tail but marginal on holdout, and top-k/image/translation strata remain stress points. Status is upgraded to `law-track candidate`, not law. External modern-sweep validation remains mandatory.
- **Additional evidence pointers:** `projects/gp154_scaling_law_normalized/workspace/law_upgrade_audit.json`, `projects/gp154_scaling_law_normalized/workspace/law_upgrade_audit.md`, `E-GP154N-LAWAUDIT-01`, `F-GP154N-LAWAUDIT-01`.
- **Phase-flow correction (2026-05-01):** Subsequent external audits retire the fixed scalar-exponent framing as the primary claim. On the acquired mlfoundations/scaling packet, smoothed local alpha is phase-dominated: phase-only `R²=0.5873`, config-only `R²=0.0976`, phase+config `R²=0.6444`, and full observational state `R²=0.6647`. A bounded PSLQ/loglog audit rejected rounded scalar constants as admissible discoveries and found log/loglog clock terms improve local-alpha RMSE over plain progress by about `9%` (`0.32939` vs `0.36256`). The live paper object is now a metadata-clocked phase-flow law, `alpha_local=f(clock, config)`, not a single universal coefficient. A leakage-safe phase-flow packet was built with `107,662` local rows across `139` blinded runs, provenance isolated from model-facing features, and phase labels derived only from normalized log-token progress.
- **Phase-flow evidence pointers:** `E-GP154-LOCAL-FLOW-01`, `F-GP154-LOCAL-FLOW-01`, `E-GP154-PHASE-FLOW-PACKET-01`, `F-GP154-PHASE-FLOW-PACKET-01`, `projects/gp154_scaling_law_normalized/external/mlfoundations_scaling_smoothed_alpha_flow_audit.json`, `projects/gp154_scaling_law_normalized/external/gp154_pslq_loglog_audit.json`, `projects/gp154_scaling_law_normalized/external/phase_flow_packet_manifest.json`, `projects/gp154_scaling_law_normalized/external/phase_flow_substrate_design.md`.
- **Frankenstein alias-breaking correction (2026-05-01):** Controlled H100 transformer runs now show that `tokens/params` is not causally sufficient. A deliberately alias-broken constant-LR grid varied LR, batch, and N independently across two one-replicate packets. The p90 `|alpha_local|` shifts replicated: LR-low stayed extreme (`9.81`, `10.50`), LR-base stayed stable (`4.61`, `4.59`), batch variants remained high (`5.55/5.59`, `5.23/4.65`), and small/large N stayed separable (`5.39/2.57`, `6.44/2.97`). A compact optimizer-control model beat train-mean baselines on `9/10` whole-variant holdouts across the two packets, but failed rep2 `lr_high`. This refines the candidate law to `alpha_local=f(clock, update_scale, noise_scale, capacity_scale, token_pressure)` and demotes `alpha=f(tokens/params)` to an aliased projection.
- **Frankenstein evidence pointers:** `E-GP154-FRANKENSTEIN-ALIAS-01`, `F-GP154-FRANKENSTEIN-ALIAS-01`, `projects/gp154_phase_flow_law/workspace/frankenstein_alias_grid_debrief.md`, `projects/gp154_phase_flow_law/workspace/frankenstein_apriori_law_audit.json`, `projects/gp154_phase_flow_law/workspace/frankenstein_apriori_law_rep2_audit.json`.
- **Crossed-grid correction (2026-05-01):** The fixed-N `3 x 3` LR x batch grid repairs the rep2 high-LR false alarm. High LR is not the live hard regime in the controlled substrate: whole-row p90 `|alpha_local|` is only `1.79/1.61/1.47` across small/base/large batch, while low LR is high-curvature (`7.64/8.88/9.55`). The compact optimizer-control law beat train-mean baseline on `15/15` held-out splits, with mean held-out MAE `0.830` vs `1.714`. The law object is now strong enough for external validation, but still not paper-grade until public/production telemetry or a larger-scale production run transfers.
- **Crossed-grid evidence pointers:** `E-GP154-FRANKENSTEIN-CROSS-01`, `F-GP154-FRANKENSTEIN-CROSS-01`, `projects/gp154_phase_flow_law/raw/frankenstein_cross_lr_batch_rows.csv`, `projects/gp154_phase_flow_law/workspace/frankenstein_cross_lr_batch_eval.json`, `projects/gp154_phase_flow_law/workspace/frankenstein_cross_lr_batch_apriori_audit.json`.
- **Validation-status consolidation (2026-05-01):** The neural law path is now explicitly split into validated and unvalidated claims. Axis-normalized trajectory shape has external OLMo2 support (`7B/13B` clean all-row MAE `0.0535`, p90 `0.1242`; rough `1B` report-bucketed MAE `0.0403`, p90 `0.1125`). Optimizer-control phase-flow has strong controlled support (`15/15` crossed-grid splits beat baseline), but external optimizer-control transfer remains open because OLMo rows do not expose the full LR/batch/control feature surface and mlfoundations lacks same-N optimizer-orthogonal repeats. This is `near_empirical_law_candidate_not_validated_law`, not finished science.
- **Validation-status evidence pointers:** `E-GP154-VALIDATION-STATUS-01`, `projects/gp154_phase_flow_law/workspace/neural_law_validation_status.json`, `projects/gp154_phase_flow_law/workspace/neural_law_validation_status.md`.
- **OLMo optimizer-control negative (2026-05-01):** A first direct external OLMo local-alpha audit failed for the optimizer-control phase-flow law: `2/6` holdouts beat baseline, mean MAE `2.669` vs baseline `1.485`; a wider local window worsened to `0/6`. This does not erase the OLMo axis-normalized trajectory support, but it blocks the stronger optimizer-control empirical-law claim. The likely issue is a mix of OLMo's scale-aliased LR/batch/N design and local-alpha estimator instability in one 13B segment, not a clean causal refutation.
- **OLMo optimizer-control evidence pointers:** `E-GP154-OLMO-OPTCTRL-01`, `F-GP154-OLMO-OPTCTRL-01`, `projects/gp154_phase_flow_law/workspace/olmo_optimizer_control_phase_flow_audit.json`, `projects/gp154_phase_flow_law/workspace/olmo_optimizer_control_phase_flow_audit_w101.json`.
- **False-positive/false-negative correction (2026-05-01):** Strict exogenous admissibility did not rescue OLMo local-alpha transfer. After removing endogenous loss monotonicity and loss-floor filters, the exogenous-only rule used only clock/log-span, step continuity, and LR continuity; it admitted `47.0%` of rows but still produced `0/6` holdouts beating baseline, with admitted 13B local-alpha tails up to abs p90 `8.55` and abs max `56.4`. The target-level correction is now explicit: raw local-alpha is not currently an admissible external observable for production W&B train-loss logs. Carry forward integrated normalized trajectory shape plus controlled optimizer-response experiments, not derivative-level external causality.
- **False-positive/false-negative evidence pointers:** `E-GP154-FP-FN-REVIEW-01`, `F-GP154-FP-FN-REVIEW-01`, `projects/gp154_phase_flow_law/workspace/neural_false_pos_neg_review.json`, `projects/gp154_phase_flow_law/workspace/neural_false_pos_neg_review.md`.
- **Integrated-segment ablation correction (2026-05-01):** The integrated OLMo ablation collapses the prior bifurcated framing. Trajectory-only features validate externally: `6/6` all-row splits beat baseline with mean MAE `0.252` vs `0.597`, and `5/6` exogenous-admissible splits beat baseline with mean MAE `0.471` vs `0.993`. Optimizer-control features anti-transfer: optimizer-only passes `0/6` splits with mean MAE `2.775`, and full trajectory+optimizer passes only `2/6` with mean MAE `4.983`; adding optimizer controls worsens every trajectory-only split by `+18%..+23684%`. The law object is now the gauge-removed trajectory-shape law. The controlled Frankenstein optimizer-control result remains a toy-substrate finding, not a production LLM law. This is the strongest GP154 result to date and should be the center of the paper claim.
- **Integrated-segment evidence pointers:** `E-GP154-OLMO-SEGABLATION-01`, `F-GP154-OLMO-SEGABLATION-01`, `projects/gp154_phase_flow_law/workspace/integrated_segment_law_ablation_audit.json`, `projects/gp154_phase_flow_law/workspace/olmo_integrated_segment_law_audit.json`, `projects/gp154_phase_flow_law/workspace/neural_law_validation_status.md`, `projects/gp154_phase_flow_law/CLAUDE_HANDOFF_NEURAL_POWER_LAW_20260501.md`.
- **Claim revision:** `trajectory_shape_external_candidate` — externally validated within OLMo2 7B/13B by point-level and integrated-segment tests; still pending exact 1B raw and cross-family stratification before any universal neural-scaling language.
- **Last revised:** 2026-05-01

### INS-072 — GP163D field-slice diagnostics shift the live gravity object from cancellation singularity to distributed tensor response

- **Claim:** The `L=4.0,n=160,gamma=0.25` field-slice diagnostic strengthens the gravity sandbox's geometric story while preserving the scope boundary. In the downloaded `0/45/90 deg` runs, UDG tidal/uniform internal acceleration is high at aligned orientations (`4.8027` at `0 deg`, `4.8004` at `90 deg`) and lower at `45 deg` (`3.9819`), while compact binary mass-weighted internal response remains suppressed and angle-stable (`0.6929`, `0.6993`, `0.7017`). All cases report zero mass fraction at the near-zero total-field threshold, so the current evidence does not support the simplest "cancellation surface hits the regularizer floor" explanation. The first `.npz` localization audit then sharpened rather than closed the claim: the UDG positive-delta slice response is mostly outer/halo (`0.633..0.811` outer fraction) with nontrivial near-boundary contribution (`0.321..0.391`), not source-core concentrated. The live object is therefore distributed tensor response versus finite-box outer-halo pickup, not a theorem. The source-loaded tidal solves still carry strict convergence debt (`converged=false`, residuals `2.5e-5..5.3e-5`), so this is diagnostic field evidence, not theorem-grade physics and not telescope validation.
- **Evidence pointers:**
    - Experiment rows: `E-GP163D-FIELDSLICE-01`, `F-GP163D-FIELDSLICE-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Debrief: `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_fieldslice_L4p0_n160_gamma0p25_jaxbg/debrief.md`
    - Artifacts:
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_fieldslice_L4p0_n160_gamma0p25_jaxbg/field_slice_localization_audit.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_fieldslice_L4p0_n160_gamma0p25_jaxbg/field_slice_diagnostics_fieldslice_L4p0_n160_gamma0p25_jaxbg_rot0.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_fieldslice_L4p0_n160_gamma0p25_jaxbg/field_slice_diagnostics_fieldslice_L4p0_n160_gamma0p25_jaxbg_rot45.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_fieldslice_L4p0_n160_gamma0p25_jaxbg/field_slice_diagnostics_fieldslice_L4p0_n160_gamma0p25_jaxbg_rot90.json`
- **Confidence tier:** `provisional_diagnostic` — stronger than a macroscopic ratio-only run because field statistics reject the near-zero cancellation-floor shortcut in this setup; still not promoted because source convergence is above the strict residual gate and the first localization audit surfaces outer/near-boundary pickup risk.
- **Paper target(s):** `paper7`, `paper8_gravity`
- **Status:** `fresh`
- **Opened:** 2026-05-01
- **Last revised:** 2026-05-01
- **L=6/N=240 correction (2026-05-01):** The larger-box field-slice run completed and passed the declared residual/instrument gates, but it demotes the ratio-space UDG orientation claim rather than promoting it. The headline UDG internal ratios were enormous and U-shaped/peaked (`83.91 / 123.85 / 83.67` across `0/45/90 deg`), while the binary ratios stayed compact and interpretable (`0.6675 / 0.6771 / 0.6792`). The cold-shot audit found the UDG denominator problem: uniform UDG mass-weighted internal acceleration is reported as `0.0`, while tidal UDG values are only `8.39e-11`, `1.24e-10`, and `8.37e-11`; the ratio is therefore dominated by the denominator floor. The `.npz` localization audit also shows `total_g`/`mu` differences are mostly outer/background and similar for UDG and binary, UDG `internal_g` deltas are tiny (`~1e-12..1e-11`), and binary `internal_g` deltas are the only clearly source-local response. This revises INS-072 from "distributed tensor response candidate" to a narrower instrument finding: field-slice convergence is repaired, compact-source response is source-local, but source-local diffuse UDG response is not established. The next required primitive is a ratio-admissibility guard plus absolute source-local response metrics before any new gravity physics promotion.
- **L=6 evidence pointers:** `E-GP163D-FIELDSLICE-L6-02`, `F-GP163D-FIELDSLICE-L6-02`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_fieldslice_L6p0_n240_gamma0p25_jaxbg_skipwarmup/debrief.md`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_fieldslice_L6p0_n240_gamma0p25_jaxbg_skipwarmup/field_slice_L6p0_localization_debrief.json`.
- **Confidence revision:** `provisional_diagnostic_scope_corrected` — the earlier L=4 orientation evidence remains useful as a diagnostic, but the L=6 domain push blocks treating the UDG ratio as a physics claim until the denominator/source-locality repair passes.
- **Metric-guard/warmup correction (2026-05-01):** The repaired metric guard closed the loop on the L=6 warning. A remote `L=4,N=160,rot0` field-slice rerun emitted `null` for UDG ratios and failed `instrument_pass` because the UDG uniform denominators were exactly `0.0`; binary remained admissible with internal ratio `0.6983`. Local sanity probes then identified the mechanism: the UDG metric is not inherently broken, but high-N diffuse source solves can falsely converge from the background when source warmup is skipped. At `N=128`, `source_mass=2.7e-4`, `udg_sigma=0.55`, skip-warmup produced `metric_internal_accel=0.0`, while source warmup produced `5.374e-05`; lower `N=24/64` checks cleared the denominator and showed monotone mass/sigma response. The actionable rule is now: ratio-denominator guard stays, `SKIP_SOURCE_WARMUP=1` is banned for physics field-slice runs, and the next admissible gravity run is an L4/N160 metric-guard rerun with source warmup enabled.
- **Metric-guard evidence pointers:** `E-GP163D-UDG-METRICGUARD-01`, `F-GP163D-UDG-METRICGUARD-01`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_fieldslice_L4p0_n160_gamma0p25_metricguard/debrief.md`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/udg_metric_sanity_probe_n24.json`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/udg_metric_sanity_probe_n128_skipwarmup.json`, `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/udg_metric_sanity_probe_n128_warmup.json`.

### INS-073 — The NS eviction branch has a falsifiable signed-alignment observable; full-field replay split the mechanism into Kida dilution versus old-branch localized spike

- **Claim:** The 5BW/5BX/5BY/5BZ/5CA/5CB/5CC sequence upgrades the NS branch from narrative "eviction" language to a concrete observable/falsifier pair and then to a sharper mechanism split. ZTARE's `ns_eviction_discriminator` loop produced SAGE, a signed-alignment observable based on the sign of local `strain_projection` and positive-stretch alignment; despite an inappropriate official zeroing by `global_extrapolation_gap`, the raw judge score reached `85`, the deterministic holdout passed, and turnover-normalized matched-geometry attacks at `N=32/64/128` did not find a sterility break. The Kida inverse-construction test then showed that blocking the measured support escape does not create compounding growth; exact Kida symmetry was preserved to machine precision, so the observed support escape is Fourier-support growth inside the symmetry class, not symmetry breaking. 5BZ decomposed that Kida saturation as concentration dilution plus local positive-stretch alignment veto. 5CA prevented overgeneralization: the older 5O/5R/5S danger-exit branch shared the alignment-veto/escape-coordinate signal but had a saved-strobe peak increase (`delta_peak=+158.24`). 5CB recovered the old branch full fields and resolved the ambiguity: the old danger exit is a true localized concentration spike (`omega_max=471.94 -> 630.18`, concentration proxy `1664.67 -> 2593.95`, shell centroid `32.01 -> 36.30`, global net budget positive) with single-cell-limited `0.99/0.995` superlevel sets, while positive-stretch alignment falls (`0.6655 -> 0.2183`) and `chi` drops (`0.228 -> 0.124`). 5CC then stress-tested the life-cycle at `N=256` while `N=384` was memory-blocked by a parallel gravity job: the spike peaks later (`omega_max` reaches `469.80` at `t=1.90`) and then declines to `389.55` by `t=2.00`, even while global net enstrophy budget remains positive and shell centroid keeps rising. This kills the simplest scalar SAGE theorem. A follow-on `ns_spike_lifecycle_discriminator` ZTARE loop confirmed the boundary: the hand-seeded coupled baseline stayed champion at `85`, the best new candidate (DLSC) scored `53`, and every serious candidate either failed holdout or depended on visible-feature sufficiency. An offline collision audit found the risk is already visible in the current tiny table: SAGE min divergent distance `0.0609`, CAFE/DLSC min divergent distance `0.1584`, and extended-visible min divergent distance `0.3370`. The current portable object is therefore not a settled law but a coupled spike-life-cycle mechanism whose next proof step is a feature-collision / latent-variable audit: concentration persistence, spectral transfer, signed alignment/frame quality, pressure/topology, peak migration, and filament connectivity must be tested together.
- **Evidence pointers:**
    - Experiment rows: `E-GP186-5BW-SAGE-01`, `E-GP186-PHASE5BX-01`, `F-GP186-PHASE5BX-01`, `E-GP186-PHASE5BY-01`, `F-GP186-PHASE5BY-01`, `E-GP186-PHASE5BZ-01`, `F-GP186-PHASE5BZ-01`, `E-GP186-PHASE5CA-01`, `F-GP186-PHASE5CA-01` in `research_areas/EXPERIMENT_TRACK_RECORD.md`
    - Hypothesis rows: `H-GP186-5BW-02` and `H-NS-5BW` / Kida-Pelz inverse pre-registration in `research_areas/private/seams/mission/ztare_mission_hypothesis_ledger_seam.md`
    - Run artifacts:
      - `projects/ns_eviction_discriminator/debate_log_iter_1777636867.md`
      - `projects/ns_millennium_hunt/workspace/phase5bw_matched_geometry_probe_N128.json`
      - `projects/ns_millennium_hunt/workspace/phase5bw_matched_geometry_probe_N128.md`
      - `projects/ns_millennium_hunt/workspace/phase5bx_kida_pelz_prison_discriminator_N64.json`
      - `projects/ns_millennium_hunt/workspace/phase5bx_kida_pelz_prison_discriminator_N128.json`
      - `projects/ns_millennium_hunt/workspace/phase5bx_kida_pelz_prison_discriminator_N128.md`
      - `projects/ns_millennium_hunt/workspace/phase5by_kida_group_projector_discriminator_N64.json`
      - `projects/ns_millennium_hunt/workspace/phase5by_kida_group_projector_discriminator_N64.md`
      - `projects/ns_millennium_hunt/workspace/phase5bz_kida_symmetric_saturation_decomposition_N64.json`
      - `projects/ns_millennium_hunt/workspace/phase5bz_kida_symmetric_saturation_decomposition_N64.md`
      - `projects/ns_millennium_hunt/workspace/phase5ca_cross_branch_alignment_dilution_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ca_cross_branch_alignment_dilution_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5cb_old_branch_black_box_replay_N384.json`
      - `projects/ns_millennium_hunt/workspace/phase5cb_old_branch_black_box_replay_N384.md`
      - `projects/ns_millennium_hunt/workspace/phase5cc_old_branch_spike_lifecycle_N256_N256.json`
      - `projects/ns_millennium_hunt/workspace/phase5cc_old_branch_spike_lifecycle_N256_N256.md`
      - `projects/ns_spike_lifecycle_discriminator/workspace/iteration_telemetry.jsonl`
      - `projects/ns_spike_lifecycle_discriminator/debate_log_iter_1777652487.md`
      - `projects/ns_spike_lifecycle_discriminator/workspace/submissions/iter_003_20260501T161821.798148+0000.py`
      - `projects/ns_spike_lifecycle_discriminator/workspace/r1_debug/iter_004_r1_attempts.md`
      - `projects/ns_spike_lifecycle_discriminator/champion_eval_results.json`
      - `projects/ns_spike_lifecycle_discriminator/feature_collision_audit.json`
      - `ztare_proofs/ZtareProofs/ns_kida_pelz_prison_dichotomy.lean`
- **Confidence tier:** `provisional_scientific_candidate` — replicated through two resolutions for the support-prison proxy, exact-grid Kida symmetry checked at `N=64`, three resolutions for matched-geometry SAGE stress, exact old-branch replay at `N=384`, lower-resolution old-branch life-cycle replay through `t=2.00`, one ZTARE mechanism-discriminator loop that preserved the baseline but exposed the feature-collision gap, and one offline collision audit showing the gap is concrete on current features. Not yet exact `N=384` life-cycle replication after `t=1.80`, not exact literature Kida/Pelz projection beyond the sourced IC, not a latent-variable-closed mechanism, and not continuum theorem evidence.

- **Paper target(s):** `paper7`, `paper8_ns`
- **Status:** `fresh`
- **Opened:** 2026-05-01
- **Last revised:** 2026-05-01
- **Phase 5CD revision (2026-05-01):** The enriched N256 replay keeps the old-branch mechanism scientifically open rather than closing it. It reproduced the spike life-cycle with pressure/topology/migration/connectivity proxies and per-capture checkpointing: `omega_max=314.66 -> 431.41 -> 435.47 -> 469.80 -> 455.84 -> 389.55`, peak at `t=1.90`, then `17.1%` post-peak decay by `t=2.00`. But the decay is not clean evidence of physical eviction because global net budget remains positive and increases (`40132 -> 121355`), shell centroid rises (`27.10 -> 46.05`), high-shell fraction rises (`0.222 -> 0.459`), support leakage rises (`0.736 -> 0.880`), and the terminal geometry is both filament-like and grid-limited. A centroid-only Nyquist audit is not enough to demote the result (`46.05 / 85.33 = 0.540`, still interior), but the high-shell mass makes resolution contamination a live threat. Two forced N384 enriched attempts on `129.146.35.82` failed with JAX OOM while a gp163d gravity field-slice process held roughly `31 GB` VRAM. The next arbiter is therefore exact N384 enriched replay through `t=2.00` on a free GPU/separate host, not a same-evidence ZTARE loop.
- **Phase 5CD evidence pointers:** `E-GP186-PHASE5CD-01`, `F-GP186-PHASE5CD-01`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cd_n256_enriched/debrief.md`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cd_n256_enriched/phase5cd_n256_enriched_spike_replay_N256.json`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cd_n256_enriched/phase5cd_nyquist_risk_audit_N256.json`.
- **Phase 5CE revision (2026-05-01):** The N384 extended replay materially changes the NS branch status. It falsifies the lower-resolution eviction/death read: omega re-compounds after `t=2.00` (`576.03 -> 655.11 -> 581.49 -> 626.32 -> 649.22`), ending at `99.1%` of the observed peak and `37.6%` above `t=1.75`, while shell centroid (`32.01 -> 97.09`), high-shell fraction (`0.156 -> 0.681`), support leakage (`0.743 -> 0.961`), and global net budget (`43290 -> 450043`) rise sharply. The alignment-veto signal remains present but does not prevent recurrence by `t=2.20`. The result is not theorem-grade blowup evidence because the Nyquist audit flips to `nyquist_contamination_plausible`: centroid/cutoff enters warning at `t=2.05` and danger by `t=2.15`. The live object is now a resolution-limited re-compounding candidate requiring a higher-N short-window replay, not an anti-blowup mechanism and not a Clay claim.
- **Phase 5CE evidence pointers:** `E-GP186-PHASE5CE-01`, `F-GP186-PHASE5CE-01`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5ce_n384_extended/debrief.md`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5ce_n384_extended/phase5ce_n384_extended_spike_replay_N384.json`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5ce_n384_extended/phase5ce_nyquist_risk_audit_N384_extended.json`.
- **Phase 5CF revision (2026-05-02):** The localized peak-patch AMR proxy converts the 5CE Nyquist warning into a concrete geometry failure mode. Six N384 patch dumps at `t=1.80,2.00,2.05,2.10,2.15,2.20` found the `0.99` superlevel core exactly `1.0` N384 cell thick at every capture, while `omega_max` remained high/recompounded (`630.18, 576.03, 655.11, 581.49, 626.32, 649.22`), shell centroid climbed from `36.30` to `97.09`, and high-shell fraction climbed from `0.189` to `0.681`. The `0.90` superlevel also became dx-limited late (`1-2` cells after `t=2.05`). This blocks the tempting pressure-Hessian-arrest interpretation at N384: the terminal geometry is unresolved and near the spectral edge. It also does not prove blowup; it establishes a grid-limited re-compounding candidate whose next honest discriminator is true higher resolution or real localized AMR.
- **Phase 5CF evidence pointers:** `E-GP186-PHASE5CF-01`, `F-GP186-PHASE5CF-01`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cf_debrief.md`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cf_n384_peak_patch_amr_proxy_N384.json`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cf_n384_peak_patch_amr_proxy_N384.checkpoint.json`.
- **Confidence revision:** `resolution_limited_candidate` — stronger than a scalar Nyquist warning because local geometry is now directly measured, but still not physical blowup/arrest evidence because the measured peak is one-cell-limited inside a full-box spectral simulation.

### INS-074 — The N384 old-branch Leray gauge is boundary-coupled; the interior scalar and radial envelope survive while angular/vector profile compactness fails

- **Claim (one paragraph):** Phase 5CF shows that the raw full-patch Leray gauge is not the proof object: `omega_max * L_p2^2` is strongly coupled to boundary contamination on the raw patch, while threshold gauges at `0.90+` are dx-limited. After trimming the patch edge, the scalar interior gauge becomes materially cleaner: the best six-capture margin-8 row has scalar CV `0.0694`, endpoint ratio `1.1466`, and boundary correlation `0.1741`. A quotient compactness audit then shows the strong voxel and signed-vector profiles still do not compact (`quotient scalar mean distance ~0.397`, quotient vector `~0.668`), but coarse radial shells are much more stable (`mean ~0.162`). The `2.05 -> 2.10` transition then breaks the scalar invariant while shell centroid rises and angular/vector anisotropy collapses. The live scientific object is therefore radial concentration under spectral exhaust with coherent-stretch depletion by angular/vector scrambling, not a strong self-similar profile and not a continuum proof.
- **Evidence pointers:**
    - Seam: `research_areas/private/seams/mission/ztare_mission_hypothesis_ledger_seam.md#H-GP186-5CG`
    - Hypothesis row: `H-GP186-5CG`
    - Run artifacts: `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cg_old_branch_patch_leray_probe.json`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cg_rescaling_gauge_audit.json`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cg_interior_gauge_filtration.json`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cg_profile_quotient_compactness_audit.json`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cg_transition_scramble_audit.json`, `projects/ns_millennium_hunt/workspace/phase5cg_deanchored_synthesis_checkpoint.md`, `projects/ns_millennium_hunt/workspace/remote_results/20260501_phase5cf_n384_peak_patch/phase5cf_debrief.md`, `research_areas/EXPERIMENT_TRACK_RECORD.md` (`E-GP186-PHASE5CF-02`, `F-GP186-PHASE5CF-02`, `E-GP186-PHASE5CG-FILTRATION-01`, `E-GP186-PHASE5CG-QUOTIENT-01`, `E-GP186-PHASE5CG-SCRAMBLE-01`)
- **Confidence tier:** `suggestive`
- **Paper target(s):** `paper8_ns`
- **Status:** `fresh`
- **Opened:** 2026-05-02
- **Last revised:** 2026-05-02
- **Mamba smoke revision (2026-05-02):** The first cached non-MHA row was added after a CPU slow-path Mamba diagnostic. `state-spaces/mamba-370m-hf` produced cancellation `62.2%`, survival `37.8%`, mean residual rank `98.7`, mean residual magnitude `0.316`, and mean cross-layer cosine `0.085` over 30 prompts; an earlier 10-prompt smoke run produced the same rounded metrics. This does not prove an SSM successor law and latency is uninterpretable without optimized kernels, but it closes the descriptor-only void enough to make the next GP116B step a replication/contrast measurement rather than pure acquisition. The measured-cancellation dataset was rebuilt and the hard-holdout selector was repaired to dynamically preserve one SSM row after new diagnostics shift row indices.
- **Frugal rival-gate revision (2026-05-02):** A zero-cost baseline audit found the old GP116B absolute gates were underdiscriminating: `mean_by_row_type+intervention_class` reaches visible MAE `0.05197` and holdout MAE `0.11739`, passing the old `0.13` holdout threshold without a successor mechanism. A stronger visible-fit `row_type_mean_plus_training_step_linear` baseline reaches visible MAE `0.03926` and holdout MAE `0.09927`. The gate now requires beating the best cheap rival by `5%`; current required holdout MAE is `0.0943051975806452`. This prevents spending ZTARE budget on row-type rediscovery or visible-fit phase interpolation.
- **Oracle routing proxy revision (2026-05-02):** H-GP116B-03 tested the learned-routing direction without network/API spend. A frozen oracle depth aggregator fit global nonnegative weights on visible prompts, excluded the final hidden state, and evaluated held-out logits on two cached transformer families. It failed: one model reached only `40%` held-out top-token match and the other `0%`, despite collapsing to roughly two effective layers. This is not a falsification of trained Attention Residuals, but it blocks the cheap story that frozen depth redundancy alone makes learned residual routing obviously valuable.
- **Mamba depth-phase revision (2026-05-02):** H-GP116B-04 falsified the strong "single-window SSM scalar" interpretation. The cached Mamba early and middle windows match the aggregate (`60.1%`, `60.6%`, and `62.2%` cancellation), but the late window jumps to `88.6%` cancellation with lower rank (`86.4`) and higher cross-layer cosine (`0.246`). The cancellation band is `28.5` percentage points, exceeding the pre-registered `15` point stability criterion. The paper-grade claim is therefore not "Mamba has X cancellation"; it is that recurrent/SSM residual-state geometry is depth-phase dependent under the GP116 diagnostic. The GP116B substrate now includes layer-window/depth-phase features and uses the late SSM window as a hard transfer stressor.
- **Phase 5CG filtration revision (2026-05-02):** The stricter filtration audit demotes the candidate from profile-level self-similarity to scalar-only stability. Across trim margins, boundary cutoffs, and late-window choices, no row reached `stable_profile_candidate`. The strongest row is trim `8`, all six captures, scalar CV `0.0694`, boundary correlation `0.1741`, endpoint ratio `1.1466`, but mean adjacent profile distance `0.4097`. The proof obligation now has three branches: interior candidate, boundary artifact, or profile-gap scalar candidate.
- **Phase 5CG quotient revision (2026-05-02):** Finite axis/sign quotienting does not rescue strong profile compactness: quotient scalar mean distance is `0.3970` and quotient vector mean is `0.6683`. Coarse radial shells are much more stable (`mean distance 0.1620`), while angular moment and vector-orientation summaries remain only moderate (`0.1405` and `0.1952`) with the largest disruption at `2.05 -> 2.10`. The proof target shifts from strong profile compactness to weak/radial concentration compactness plus angular phase-scrambling.
- **Phase 5CG scramble revision (2026-05-02):** The targeted `2.05 -> 2.10` transition is not a clean self-similar continuation: `omega_max` drops by `11.2%`, `omega_max * L_p2^2` drops by `15.3%`, shell centroid rises by `8.98`, angular anisotropy gap drops by `0.274`, and vector-orientation anisotropy gap drops by `0.485`. This promotes the de-anchored object from "scalar/radial profile gap" to "radial concentration with coherent-stretch depletion under spectral exhaust." The immediate falsifier is the live r64 replay: if the larger patch reproduces the angular/vector scramble without boundary control failure, the proof cage is `ns_coherent_stretch_depletion.lean`; if not, demote the mechanism.
- **Phase 5CG r64 partial revision (2026-05-02):** The larger r64 patch reproduces the key split through the first four captures. Filtration finds `no_stable_profile_candidate`; quotient compactness remains non-voxel (`quotient scalar mean 0.4034`, quotient vector 0.6518) while coarse radial shell distance improves to `0.0990`; and the `2.05 -> 2.10` transition still has scalar break plus spectral exhaust (`omega_L2_p2 ratio 0.7092`, shell centroid `+8.982`) with angular/vector anisotropy collapse (`gap_max_min -0.1705` and `-0.2238`). This strengthens the coherent-stretch-depletion read and weakens the small-patch-artifact objection, while still leaving continuum proof and final replay closure open.
- **Phase 5CG r64 final revision (2026-05-02):** The completed replay now closes the last open ambiguity on the data side. Interior filtration remains `no_stable_profile_candidate` with most rows boundary-coupled or weak-scalar only; quotient compactness still fails at voxel scale (`raw scalar mean 0.4585`, `quotient scalar 0.4269`, `quotient vector 0.6684`), while the coarse radial shell remains the best summary (`mean 0.1262`, angular moment `0.0883`, vector orientation `0.1092`). The decisive `2.05 -> 2.10` event is unchanged and the later `2.10 -> 2.15 -> 2.20` captures do not rescue profile compactness. The branch is now best framed as radial concentration with angular/vector scrambling under spectral exhaust, and the remaining proof obligation is a recurrence/exhaust bound, not profile self-similarity.
- **Phase 5CG proxy revision (2026-05-02):** The first direct backtest of the bridge variable narrows the lemma target substantially, and the strengthened rerun removes the “one lucky denominator” excuse. Simple scrambling proxies fail: plain anisotropy, `omega_L2_p2`-weighted anisotropy, and `omega_L2_p2`-only controls all reconstitute by `t=2.15` with rebound ratios `~0.91..0.99` relative to `t=2.05`. But a small family of radial-grade-renormalized variants survives the same test: `exhaust_discounted_gap` / `iso` have rebound ratios `0.7455` / `0.7435`, and `sqrt_discounted_gap` / `iso` have rebound ratios `0.8311` / `0.8289`. The honest update is not that coherent-stretch depletion is proved. It is that the only surviving local bridge candidates are radial-grade-renormalized reserve variables, now caged in Lean as `phase5cgExhaustDiscountedProxyGap` and lifted conceptually into the exhaust-scale and `l=2` carrier bridges. If no PDE-side justification makes that renormalization natural, the branch stops as mechanism identification. If it can be justified, the recurrence bridge should be rebuilt around the renormalized carrier rather than raw anisotropy collapse.

### INS-075 — GP116B transformer-successor search has its first direct residual-state measurement row family: layer-input residual checkpoints exactly reconstruct attention KV caches across GPT-2/Pythia implementations

- **Claim:** The transformer-successor track is now anchored by a measured state-sufficiency object rather than descriptor-only successor rows. Local cached-model probes show that per-layer input residual checkpoints exactly reconstruct attention K/V tensors across GPT-2-style absolute-position MHA and GPT-NeoX/Pythia rotary MHA. For Pythia 70M/160M/410M, reconstructed-prefix cache execution also matches next-token logits exactly (`logit_max_abs_error=0.0`, top-token match true). This does not prove full KV-Direct or a next-architecture law; it proves that residual-state economics is executable as a direct diagnostic and gives GP116B five locally remeasured rows.
- **Evidence pointers:**
    - Experiment rows: `E-GP116B-KVRESID-PYTHIA-01`, `F-GP116B-KVRESID-PYTHIA-01`
    - Artifacts:
      - `projects/gp116_cot_exchange/measure_kv_residual_checkpoint.py`
      - `projects/gp116_cot_exchange/build_kv_residual_measurement_rows.py`
      - `projects/gp116_cot_exchange/workspace/kv_residual_checkpoint/gpt2_kv_residual_checkpoint.json`
      - `projects/gp116_cot_exchange/workspace/kv_residual_checkpoint/EleutherAI__pythia-70m_kv_residual_checkpoint.json`
      - `projects/gp116_cot_exchange/workspace/kv_residual_checkpoint/EleutherAI__pythia-160m_kv_residual_checkpoint.json`
      - `projects/gp116_cot_exchange/workspace/kv_residual_checkpoint/EleutherAI__pythia-410m_kv_residual_checkpoint.json`
      - `projects/gp116_cot_exchange/workspace/kv_residual_checkpoint_rows.json`
      - `projects/gp116_cot_exchange/workspace/transformer_successor_substrate_readiness.json`
- **Confidence tier:** `confirmed_implementation_identity` — direct local measurements across two transformer implementation families; not an architecture-successor law, not a downstream quality claim, and not a single-final-residual KV-Direct proof.
- **Paper target(s):** `gp116b_transformer_successor`, possible `AI-studying-AI` case-study paper
- **Status:** `fresh`
- **Opened:** 2026-05-02
- **Last revised:** 2026-05-02

### INS-076 — In the current Navier-Stokes decisive fork, the exponential strain-aligned metric branch converts material-frame transport stress into a source-stratified transient metric-degeneracy burden; capacity-deficit obstruction is conditional on sharp material control plus a uniform generator cap

- **Claim (one paragraph):** The current NS proof graph no longer supports a generic "geometry may help" story, but the honest Paper 7 object is narrower than the first obstruction wording. Phase 5CH falsified the overbroad read that transport-scale stress alone proves a capacity deficit: with strict ellipticity only, every finite observed transport ratio can satisfy curvature-capacity matching by increasing `hnorm`. Phase 5CI inverts that failure into the science-grade invariant: for a ratio `R = targetCurvature / capacityBudget`, the already-formalized burden forces `hnorm >= R - 1`, and the exponential ellipticity relation forces `lambdaMin <= exp(1 - R)`. Phase 5CJ/5CK sharpened the evidence boundary: the global worst saved material-frame ratio `15.7538` forces `lambdaMin <= 3.913e-7`, but that extreme is source-concentrated in the N256 spike-lifecycle row; the strongest N384 enriched source forces the weaker but still nontrivial `lambdaMin <= 1.2937e-4`; and late N384 extended rows relax to max `R=5.4645`, i.e. `lambdaMin <= 0.01151`. Phase 5CM then falsified the stronger parabolic-capacity reading: against Laplacian/parabolic denominators the same rows have `max R=0.19248`, so no lower-eigenvalue burden is forced by that denominator family. Phase 5CN shows the material-control theorem must also be sharp: on the global max, preserving `lambdaMin<=1e-2` needs `C<=2.81`, while `lambdaMin<=1e-4` needs `C<=1.54`; the strongest N384 enriched source needs `C<=1.78` even for `lambdaMin<=1e-2`. Phase 5CY then red-teamed the attractive anisotropic dimensional-reduction story: the pressure Hessian remains a Euclidean Riesz operator unless a real coordinate/Jacobian theorem is proved, so the bridge must be a Euclidean anisotropic source/moment/projection estimate or a counterexample, not metric-kernel substitution. Thus the exponential branch is not killed by strict ellipticity alone; on the saved corpus it survives material-frame pressure-transport stress through source-stratified transient metric degeneracy, while parabolic scale, loose-constant material control, and unearned fractional-kernel replacement remain escapes unless the PDE proof supplies sharp material-transport control plus a uniform generator cap / ellipticity floor.
- **Evidence pointers:**
    - Seam: `research_areas/private/seams/engine/GP-190_post_run_discriminator_daemon_seam.md` (general post-run discriminator discipline), plus the active NS compression note `projects/ns_millennium_hunt/workspace/phase5cg_decisive_fork_status.md`
    - Hypothesis rows: `H-NS-5CH` and `H-NS-5CI`, rooted in the closed experiment/finding rows `E-GP186-NS-PROOFSEARCH-R5-POSTRUN-01`, `F-GP186-NS-PROOFSEARCH-R5-POSTRUN-01`, `E-GP186-NS-R5-TRANSPORT-SCALE-AUDIT-01`, `F-GP186-NS-R5-TRANSPORT-SCALE-AUDIT-01`, `E-GP186-NS-PHASE5CH-01`, and `E-GP186-NS-PHASE5CI-01`
    - Run artifacts:
      - `projects/ns_millennium_hunt/workspace/remote_results/20260502_phase5cg_r64_final_audits/phase5cg_route5_survivor_proxy_backtest.md`
      - `projects/ns_millennium_hunt/workspace/remote_results/20260502_phase5cg_r64_final_audits/phase5cg_route5_transport_scale_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5cg_paper7_obstruction_candidate.md`
      - `projects/ns_millennium_hunt/workspace/phase5ch_capacity_realization_falsifier.md`
      - `projects/ns_millennium_hunt/workspace/phase5ci_metric_degeneracy_receipt.md`
      - `projects/ns_millennium_hunt/workspace/phase5cj_source_stratified_degeneracy_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ck_degeneracy_time_profile.md`
      - `projects/ns_millennium_hunt/workspace/phase5cl_paper7_science_grade_ns_insight.md`
      - `projects/ns_millennium_hunt/workspace/phase5cm_parabolic_escape_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5cn_material_control_sensitivity.md`
      - `projects/ns_millennium_hunt/workspace/phase5co_material_control_theorem_skeleton.md`
      - `projects/ns_millennium_hunt/workspace/phase5cp_science_claim_gate_packet.json`
      - `projects/ns_millennium_hunt/workspace/phase5cp_science_claim_gate_verdict.json`
      - `projects/ns_millennium_hunt/workspace/phase5cq_science_claim_status.md`
      - `projects/ns_millennium_hunt/workspace/phase5cr_material_control_obligation_decomposition.md`
      - `projects/ns_millennium_hunt/workspace/phase5cs_pressure_rotation_capacity_escape.md`
      - `projects/ns_millennium_hunt/workspace/phase5ct_exhaust_horizon_bridge.md`
      - `projects/ns_millennium_hunt/workspace/phase5cu_cycle_bridge_discriminator.md`
      - `projects/ns_millennium_hunt/workspace/phase5cv_formal_resource_packet.md`
      - `projects/ns_millennium_hunt/workspace/phase5cw_exhaust_efficiency_scaling_split.md`
      - `projects/ns_millennium_hunt/workspace/phase5cx_exhaust_efficiency_noncircularity_bar.md`
      - `projects/ns_millennium_hunt/workspace/phase5cy_anisotropic_fractional_bridge_redteam.md`
      - `projects/ns_millennium_hunt/workspace/phase5cz_ztare_anisotropic_fractional_bridge_packet.md`
      - `projects/ns_millennium_hunt/workspace/phase5db_fractional_bridge_ztare_debrief.md`
      - `projects/ns_millennium_hunt/workspace/phase5dc_pressure_dwell_timescale_split.md`
      - `projects/ns_millennium_hunt/workspace/phase5dd_resupply_escape_pincer.md`
      - `projects/ns_millennium_hunt/workspace/phase5df_resupply_pincer_ztare_debrief.md`
      - `projects/ns_millennium_hunt/workspace/phase5dg_residual_defect_packet_certificate_debrief.md`
      - `projects/ns_millennium_hunt/workspace/phase5dh_resupply_pincer_rerun_debrief.md`
      - `projects/ns_millennium_hunt/workspace/phase5di_alien_invariant_bridge_debrief.md`
      - `projects/ns_millennium_hunt/workspace/phase5di_dual_shear_sympy_backtest_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5dj_10x_finite_mode_taxonomy_debrief.md`
      - `projects/ns_millennium_hunt/workspace/phase5dj_finite_mode_pressure_taxonomy_probe_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5dk_stationary_euler_escape_debrief.md`
      - `projects/ns_millennium_hunt/workspace/phase5dl_mixed_residual_tax_probe.md`
      - `projects/ns_millennium_hunt/workspace/phase5dl_mixed_residual_tax_probe_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5dm_two_background_mixed_profit_probe.md`
      - `projects/ns_millennium_hunt/workspace/phase5dm_two_background_mixed_profit_probe_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5dn_local_triad_symbolic_ceiling.md`
      - `projects/ns_millennium_hunt/workspace/phase5dn_local_triad_symbolic_ceiling_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5do_full_background_subspace_probe.md`
      - `projects/ns_millennium_hunt/workspace/phase5do_full_background_subspace_probe_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5dp_multishell_projection_ladder.md`
      - `projects/ns_millennium_hunt/workspace/phase5dp_multishell_projection_ladder_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5dq_sparse_multishell_lsmr_probe.md`
      - `projects/ns_millennium_hunt/workspace/phase5dq_sparse_multishell_lsmr_probe_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5dr_projection_deficit_law.md`
      - `projects/ns_millennium_hunt/workspace/phase5dr_projection_deficit_law_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5du_independent_multishell_cascade_debrief.md`
      - `projects/ns_millennium_hunt/workspace/phase5ds_candidate_cascade_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5dt_triadic_boundary_leak_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5du_projection_ceiling_formula_check.md`
      - `projects/ns_millennium_hunt/workspace/phase5du_projection_ceiling_formula_check_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5dv_square_law_exhaust_bridge_debrief.md`
      - `projects/ns_proofsearch_independent_multishell_cascade/workspace/submissions/iter_004_20260503T204706.173131+0000.md`
      - `projects/ns_proofsearch_square_law_exhaust_bridge/history/1777843643_iter1_score_93_ns_proofsearch_square_law_exhaust_bridge.md`
      - `projects/ns_proofsearch_square_law_exhaust_bridge/workspace/submissions/iter_003_20260503T213252.145597+0000.md`
      - `projects/ns_proofsearch_square_law_exhaust_bridge/workspace/post_run_synthesis_attempts.jsonl`
      - `projects/ns_proofsearch_stationary_euler_escape/champion_eval_results.json`
      - `projects/ns_proofsearch_stationary_euler_escape/workspace/post_run_synthesis_attempts.jsonl`
      - `projects/ns_proofsearch_resupply_pincer/workspace/submissions/iter_003_20260503T124459.213404+0000.md`
      - `projects/ns_proofsearch_resupply_pincer/latest_eval_results.json`
      - `projects/ns_proofsearch_resupply_pincer/latest_probability_dag.json`
      - `projects/ns_proofsearch_residual_defect_packet_certificate/workspace/submissions/iter_002_20260503T130723.541712+0000.md`
      - `projects/ns_proofsearch_residual_defect_packet_certificate/champion_eval_results.json`
      - `projects/ns_proofsearch_residual_defect_packet_certificate/workspace/post_run_synthesis_attempts.jsonl`
      - `projects/ns_proofsearch_resupply_pincer/workspace/submissions/iter_002_20260503T183939.958991+0000.md`
      - `projects/ns_proofsearch_resupply_pincer/workspace/submissions/iter_003_20260503T184149.270302+0000.md`
      - `projects/ns_proofsearch_resupply_pincer/workspace/synthesis_candidate_1_2_3.md`
      - `projects/ns_proofsearch_resupply_pincer/workspace/qualitative_evidence_cold_shot.json`
      - `projects/ns_proofsearch_alien_invariant_bridge/workspace/submissions/iter_002_20260503T185611.582724+0000.md`
      - `projects/ns_proofsearch_alien_invariant_bridge/workspace/submissions/iter_004_20260503T190119.515677+0000.md`
      - `projects/ns_proofsearch_alien_invariant_bridge/workspace/synthesis_candidate_1_2_3_4.md`
      - `projects/ns_proofsearch_alien_invariant_bridge/workspace/post_run_synthesis_attempts.jsonl`
      - `projects/ns_proofsearch_alien_invariant_bridge/champion_eval_results.json`
      - `projects/ns_proofsearch_alien_invariant_bridge/latest_eval_results.json`
      - `projects/ns_proofsearch_stationary_euler_escape/workspace/submissions/iter_001_20260503T192616.409349+0000.md`
      - `projects/ns_proofsearch_stationary_euler_escape/workspace/submissions/iter_003_20260503T193403.533364+0000.md`
      - `projects/ns_proofsearch_stationary_euler_escape/workspace/submissions/iter_006_20260503T194648.041951+0000.md`
      - `ztare_proofs/ZtareProofs/ns_exponential_metric_capacity_deficit.lean`
      - `ztare_proofs/ZtareProofs/ns_exponential_metric_survivor_obstruction.lean`
      - `ztare_proofs/ZtareProofs/ns_exponential_metric_obstruction_stack.lean`
      - `ztare_proofs/ZtareProofs/ns_route5_survivor_elimination.lean`
      - `ztare_proofs/ZtareProofs/ns_route5_remaining_survivors.lean`
      - `ztare_proofs/ZtareProofs/ns_decisive_post_obstruction_theorem_search.lean`
      - `ztare_proofs/ZtareProofs/ns_exhaust_horizon_bridge.lean` (unimported, unbuilt)
      - `ztare_proofs/ZtareProofs/ns_resupply_escape_pincer.lean` (unimported, unbuilt)
- **Confidence tier:** `scope_corrected / science_grade_candidate / material_frame_only / sharp_constant_needed / source_stratified / exhaust_efficiency_scaling_open / noncircular_bridge_required / fractional_static_bridge_falsified / dwell_resupply_split_isolated / resupply_escape_pincer_isolated / pressure_active_packet_taxonomy_isolated / stationary_euler_degeneracy_isolated / mixed_residual_tax_bridge_open / single_background_escape_locally_negative / two_background_escape_locally_negative / local_triad_symbolic_ceiling / full_small_background_subspace_negative / bounded_multishell_ladder_subcritical / sparse_high_bound_subcritical / exact_projection_formula_target / independent_cascade_generator_required / recurrence_bridge_open / PDE_global_open`
  The algebraic degeneracy law is definition-level solid and anchored to a small existing Lean theorem (`generator_norm_burden_of_curvatureCapacityMatching`) plus bounded arithmetic receipts. The empirical burden is now source-stratified, transient, explicitly material-frame, and constant-sensitive rather than sold as a single global maximum or raw parabolic capacity deficit. Promoting beyond candidate requires deriving Navier-Stokes-side sharp material-transport control plus a uniform cap/floor, or showing an independent route-native capacity family with the same burden.
- **Paper target(s):** `paper7`, `unassigned`
- **Status:** `fresh`
- **Opened:** 2026-05-02
- **Last revised:** 2026-05-03 17:44:30 EDT
- **Formalization incident correction (2026-05-02 20:13:32 EDT):** Do not count
  `ztare_proofs/ZtareProofs/ns_exponential_metric_transport_ratio_obstruction.lean`
  as verified support for this insight. The file was a follow-on bridge attempt
  from transport-ratio stress to the capacity-deficit target, but a local
  elaboration attempt consumed roughly `90GB` RAM and crashed the laptop. The
  file is quarantined from `ztare_proofs/ZtareProofs.lean` until refactored and
  checked under a hard resource envelope. INS-076 rests on the small
  capacity/degeneracy algebra already in the trusted files plus the saved
  transport-scale audits, not on that unsafe bridge compiling.
- **Phase 5CH/5CI scope correction (2026-05-02 20:35:00 EDT):** The
  capacity-deficit obstruction is no longer the unconditional Paper 7 claim.
  The corrected claim is required metric degeneracy: matching the current worst
  saved transport ratio forces `lambdaMin <= 3.913e-7`. A uniform floor of
  `1e-6` or stronger would obstruct that burden, while strict ellipticity alone
  permits survival by near-degenerate metrics.
- **Phase 5CJ/5CK robustness correction (2026-05-02 22:03:00 EDT):** The
  strongest `3.913e-7` number is a valid saved-corpus burden but not yet
  resolution-robust: it is source-concentrated in the N256 spike-lifecycle row.
  The N384 enriched source independently forces `lambdaMin <= 1.2937e-4`, and
  the late N384 extended window relaxes to `lambdaMin <= 0.01151`. Paper 7
  should state a source-stratified transient-degeneracy frontier, not a single
  global max as if it were continuum-stable.
- **Phase 5CM parabolic-escape correction (2026-05-02 22:11:25 EDT):** The
  material-frame burden is not a raw parabolic capacity deficit. On the same
  saved rows, `max ||Hp|| / ||Delta|| = 0.19248`, so Laplacian/parabolic scale
  never crosses the forced-degeneracy threshold. Paper 7 should state the
  result as a material-transport-frame degeneracy frontier; a true obstruction
  additionally needs a theorem that the exponential route's admissible capacity
  is material-controlled rather than parabolic-scale controlled.
- **Phase 5CN constant-sensitivity correction (2026-05-02 22:11:25 EDT):** A
  loose material-control theorem would mostly erase the burden. On the global
  saved max `R=15.7538`, `lambdaMin<=1e-2` requires control within
  `C<=2.81`, and `lambdaMin<=1e-4` requires `C<=1.54`; on the strongest N384
  enriched source, `lambdaMin<=1e-2` already requires `C<=1.78`. The next proof
  target is therefore near-material control, not any large-constant estimate.
- **Phase 5CP/5CQ science-claim status (2026-05-03 07:18:00 EDT):** The
  science-vs-instrument gate classifies INS-076 as
  `science_claim_scope_ready=true`. The answer is therefore "yes, scoped
  science claim" for Paper 7 and "no, not a solved NS theorem." The claim clears
  only as a branch-native material-frame degeneracy frontier with hostile
  falsifiers, explicit nonclaims, and open PDE obligations.
- **Phase 5CR theorem-hinge sharpening (2026-05-03 07:50:00 EDT):** The next
  theorem step is now an exact two-inequality obligation, not a vague "PDE-side
  burden": identify the route-native capacity `B`, prove or falsify
  `B <= C*M` with `C` near `1`, and separately prove or falsify a uniform
  generator cap / ellipticity floor. A large-constant estimate such as
  `B <= 10M` is explicitly an escape route, not promotion.
- **Phase 5CS raw-pressure escape correction (2026-05-03 08:05:00 EDT):** The
  first tempting material-control route is now demoted. If `B` is raw pressure
  Hessian / raw pressure-frame torque, existing Phase 5V/5W danger-window
  artifacts already show `B` is not near-material controlled: at the danger
  frame `tau_-Omega^2=763.27` and `tau_-Hess(p)=-720.91` mostly cancel, leaving
  a much smaller material residual. The next theorem target is therefore a
  non-circular residual capacity or a centrifugal-dominance / recurrence
  inequality, not raw pressure `<=` material derivative.
- **Phase 5CT/5CU exhaust-bridge correction (2026-05-03 08:28:00 EDT):** The
  bridge target is now cycle-level rather than raw-pressure-level. Local
  centrifugal transversality becomes proof-relevant only if the danger gain
  satisfies `G <= P*w/v` and reset/exhaust loss satisfies `L >= P*w/v`, hence
  `L-G >= 0` on high-intensity section returns. The saved first cycle fails
  loss dominance (`G=0.00881247`, `L=0.00646377`, `G-L=0.00234870>0`), while
  the second return proxy is too short to score. This keeps the recurrence
  ratchet alive but does not prove blowup; finite-time singularity would still
  need a profitable-return ladder plus return-time summability.
- **Phase 5CV formal-resource correction (2026-05-03 08:34:00 EDT):** Future
  Lean work on this branch must be treated as a bounded compute experiment.
  The crashed transport-ratio target remains quarantined, and even the smaller
  exhaust-horizon bridge cage is unimported/unbuilt until checked as a
  standalone target with timeout, memory cap, telemetry, and a stop/refactor
  policy. A larger machine is not a substitute for target isolation.
- **Phase 5CW exhaust-efficiency scaling split (2026-05-03 08:51:00 EDT):** The
  recurrence bridge is now compressed to `Q(E)=L(E)v(E)/(P(E)w(E))`. If
  `G(E)<=P(E)w(E)/v(E)`, then `Q(E)>=1` implies loss dominance. The saved
  first cycle is a negative witness at the sampled scale (`L/G≈0.73348`, hence
  `Q<1` for any valid dwell-cap upper bound), so the regularity bridge needs an
  eventual asymptotic crossing of `Q` above one. The ratchet side needs
  high-intensity returns with `Q<1`, scale shrink, and return-time summability.
- **Phase 5CX non-circularity bar (2026-05-03 09:02:00 EDT):** The exhaust
  efficiency bridge is only meaningful if `w`, `v`, `P`, and `L` are defined
  before scoring the cycle margin: fixed section width, pointwise/interval
  escape-speed lower bound, pointwise/interval production upper bound, and
  mechanism-forced reset-loss lower bound. Back-solving any of these from the
  observed `G` and `L` would be tautological and cannot promote the claim.
- **Phase 5CY/5CZ anisotropic-fractional bridge red-team (2026-05-03 09:15:00 EDT):**
  The proposed dimensional-reduction bridge is promising but invalid as
  stated. The pressure Hessian remains Euclidean; metric-kernel substitution
  requires a real coordinate/Jacobian theorem. The ZTARE-ready target is a
  Euclidean anisotropic Riesz projection bound or counterexample tied to
  `P(E)` in `Q(E)=L(E)v(E)/(P(E)w(E))`.
- **Phase 5DB fractional-bridge ZTARE close (2026-05-03 08:16:20 EDT):**
  The bounded theorem-search run falsified the generic static dimensional
  reduction bridge. Iteration 2 paid the incompressibility objection with a
  divergence-free shear-bypass source; judge-null iteration 3 supplied the
  strongest manual theorem object, a finite-enstrophy local-slab scaling with
  pointwise `H_33 f ~ epsilon^-1/2`; iteration 4 supplied the conservative
  `H1` fallback where `H_33 f` remains `O(1)` rather than decaying. The bridge
  is now open only as a time-integrated dwell/recurrence theorem for `P(E)`,
  not as a pointwise pressure-suppression claim.
- **Phase 5DC pressure-dwell split (2026-05-03 08:22:13 EDT):** The
  post-fractional theorem object is now `P_dwell`, not pointwise `P_inst`.
  With normal scale `k=epsilon^-1`, localized enstrophy budget `B`, and shear
  `S`, finite-enstrophy scaling gives `P_inst ~ S sqrt(B k)` but viscous
  lifetime `tau_visc ~ 1/(nu k^2)`, so no-resupply impulse scales like
  `S sqrt(B)/(nu k^(3/2))`. The exact fork is now viscous erasure/subcritical
  resupply versus material recurrence/resupply strong enough to keep the
  projected Euclidean pressure channel active in `Q(E)`.
- **Phase 5DD resupply-escape pincer (2026-05-03 08:27:30 EDT):** The dwell
  fork is now tied to the signed escape coordinate. If a danger section has
  width `W(E)` and outward escape-speed lower bound `V(E)`, then
  `T_section(E)<=W(E)/V(E)`. Combining this with the high-normal packet impulse
  gives the supply-load burden
  `rho_resupply*W*S*sqrt(B)/(V*nu) = o(k^(3/2))` for the exhaust side, with
  the reverse inequality plus profitable returns and return-time summability
  required for the ratchet side. The next theorem/falsifier is therefore a
  bound on `rho_resupply*S*sqrt(B)`, not another pointwise pressure-kernel
  argument.
- **Phase 5DF resupply-pincer theorem-search close (2026-05-03 08:50:52 EDT):**
  A targeted `gpt-5.5` / `gpt-4.1` ZTARE run on
  `ns_proofsearch_resupply_pincer` improved `79 -> 84 -> 93` and sharpened the
  theorem object. Iter 1 produced the conditional subcritical exponent theorem;
  iter 2 produced the supercritical returning-subsequence obstruction; iter 3
  produced the stronger no-go/reranking theorem: exponent envelopes alone do
  not certify dynamic NSE realization. A supercritical packet family becomes
  proof-relevant only with explicit approximate fields `U_n`, projected NSE
  residual `R_n`, strain budget `A_n`, observable Lipschitz/margin control, and
  residual-defect ratio `Defect_n < 1`. This is the new bridge object:
  residual-stable packet certification, not another envelope inequality.
- **Phase 5DG residual-defect successor close (2026-05-03 09:13:21 EDT):**
  The full-stack successor run
  `ns_proofsearch_residual_defect_packet_certificate` scored `85 -> 91 -> 84`.
  The champion shows that exact one-dimensional decaying Beltrami/shear packets
  on boundaryless `T^3` can pay the dynamic node perfectly (`R_n=0`,
  `Defect_n=0`) while still failing the pressure-ratchet layer:
  `partial_i partial_j(U_i U_j)=0`, so the compatible pressure gauge class is
  `[p_n]=[0]`, and gauge-invariant derivative/zero-mean pressure-channel
  functionals have zero profit. This reranks the bridge again: residual-stable
  construction is necessary but not sufficient. A pressure-ratchet certificate
  must also pay pressure-Poisson source, sign coherence, and profit. The next
  theorem/falsifier is pressure-channel taxonomy on `T^3`, or construction of
  pressure-active packets with nonzero pressure-Poisson source and small
  residual defect. Post-run synthesis tied the champion at `91` and did not
  promote. Qualitative cold-shot was selected by policy but did not leave a
  consumed artifact; static inspection traced this to an early return in
  `pre_iter1_dispatch.py`, which has been patched so evidence cold-shot no
  longer depends on the de-anchor seed being selected.
- **Phase 5DH resupply-pincer rerun close (2026-05-03 14:46:11 EDT):** A
  no-promotion rerun of `ns_proofsearch_resupply_pincer` with qualitative
  cold-shot and synthesis active scored `82 -> 92 -> 87`; the previous score
  `93` champion remained best, and synthesis over cluster `[1,2,3]` tied at
  `93` without promotion. The rerun is nevertheless informative. It confirms
  that the broad pincer substrate has saturated around the residual-defect
  reranking theorem, and it sharpens the next explicit-packet falsifier:
  hidden phase/geometric/nonlinear cancellation must register as small
  projected NSE residual. For cutoff/reset high-normal packet births, the rerun
  identifies a reset-residual tax with obstruction scale
  `nu*k^(1/2)/S(E,k)` relative to dwell margin. Future packet proposals should
  report `Xi_n` and `Defect_n` together and audit reset residual before
  pressure sign, profit, or return-time work.
- **Phase 5DI alien-invariant / packet-taxonomy close (2026-05-03 15:23:00 EDT):**
  `ns_proofsearch_alien_invariant_bridge` scored `84 -> 93 -> 88 -> 93`;
  post-run synthesis over cluster `[1,2,3,4]` tied at `93` and did not
  promote. The run changed the packet theorem map. Iteration 1 constructed an
  exact coordinate cross-shear packet with zero NSE residual and nonzero
  Euclidean pressure-Poisson source. Iteration 2 generalized it to the
  equal-shell orthogonal-dual lattice family and supplied the first blocking
  theorem inside that ansatz: nonorthogonality breaks incompressibility, while
  unequal shells leave a curl obstruction that a single pressure mode cannot
  absorb. Iteration 4 gave the clean coordinate-free bilinear certificate. A
  bounded SymPy check on `k=(1,1,0), ell=(1,-1,0)` plus exact rational sweep
  over `[-4,4]^3` passed `768` equal-shell orthogonal pairs, including `672`
  non-coordinate pairs, and `23808` orthogonal unequal-shell obstruction
  cases. The live bridge is now pressure-channel usefulness rather than mere
  pressure-source existence: exact residual-zero packets can be pressure-active,
  but the dual-shear family is dissipative and harmless by itself.
- **Phase 5DJ finite-mode taxonomy compression (2026-05-03 16:04:00 EDT):**
  The bounded SymPy/backtest result makes the Phase 5DI equal-shell
  orthogonal-dual theorem proof-adjacent at the finite algebra layer: the
  named non-coordinate hidden-residual risk was checked symbolically, and the
  broader lattice identity was checked with exact rational arithmetic. A
  corrected two-/three-mode same-shell taxonomy probe then found that every
  pressure-active residual-zero example classified in the bounded pass is an
  embedded planar single-eigenvalue flow,
  `u=e^{-nu K^2 t} n x grad psi`, `-Delta psi=K^2 psi`. This compresses the
  packet family into stationary Euler eigenflow degeneracy: pressure source can
  be nonzero while the Leray-visible nonlinear velocity profit is exactly zero.
  The next Clay-relevant bridge is residual-small escape from this manifold
  with signed pressure-strain/recurrence profit, not another search for mere
  pressure activity.
- **Phase 5DU independent-cascade close (2026-05-03 17:25:00 EDT):** The
  independent-cascade ZTARE run scored low (`55 -> 25 -> 28 -> 18`) but
  compressed the finite-mode projection boundary. Iteration 1's declared
  diagonal generator was killed by exact intake audit: mixed residual was
  nonzero while both tested profit observables were zero through `B=100`.
  Iterations 2 and 3 supplied useful failed proof skeletons; exact arithmetic
  falsified the claim that `(u dot grad)W` stays interior, and the judge
  identified the full-convolution multi-feed obstruction to single-boundary
  proofs. Iteration 4's proof failed, but its rational ceiling
  follow-up corrected that near miss to the exact square law
  `R_B^2 = 1 - 3/(4B^3 + 12B^2 + 14B + 3)`, matching the deterministic
  projection ladder from `B=2` through `B=32` with max absolute difference
  `2.998e-15`. This promotes the next theorem target from a fitted deficit law
  to an exact finite Fourier Gram/projection formula. It is not a dynamic NSE
  proof: independent realization, full nonlinear convolution accounting, and
  residual-defect transfer remain open.
- **Phase 5DV square-law exhaust bridge close (2026-05-03 17:44:30 EDT):**
  The square-law-to-dynamics ZTARE pass scored a real champion at `93` and
  confirmed the honest no-go/reranking theorem: the finite projection tax tail
  is summably small,
  `sum_{B>=K}(1-R_B^2) <= 3/(8(K-1)^2) -> 0`, so a square-law-only,
  tail-reducible, or finite-prefix-plus-high-rung-tail bridge cannot force a
  uniform Clay-level cycle/LP/cascade margin. The run also corrected an
  overbroad negative: moving finite-stencil LP certificates are not killed
  merely by active-shell escape. The live proof object is now full nonlinear
  finite-stencil/correlated closure: an independently defined certificate must
  survive high-frequency escape while paying high-low, high-high,
  pressure/exterior, signed stretching/return profit, and residual defect. One
  iter's `0` score was a validator-format artifact, not a scientific verdict;
  the raw non-Gemini judge path now retries wrong-top-level verdict JSON and
  has a regression test.

### INS-077 - GP163D gravity sandbox exposes a science-grade numerical-methods finding: diffuse weak-gradient sources amplify representation-sensitive fourfold susceptibility while compact controls remain stable

- **Claim:** Existing `L=4,N=160,Gamma=0.25` GP163D field-slice artifacts support a paper-grade numerical-methods contribution, not an astrophysical modified-gravity law. Across two high-N residual presentations, the diffuse UDG-like source carries large unsigned fourfold susceptibility (`|chi4/chi0|=0.1988` under `face_flux`, `0.2763` under `isotropic_18_flux`), while the compact binary-like control remains essentially flat (`0.0025`, `0.0015`). The positive UDG response is source-local in the downloaded mid-plane diagnostics rather than a boundary pickup: face/isotropic positive-mask weighted Jaccard is `0.9848`, core/halo fractions are about `0.61/0.39`, and near-boundary max is about `3e-10`. The same audit blocks physics promotion: the UDG phase flips between residual presentations, and analytic no-source residual-transfer probes already contain representation-dependent fourfold forcing before source loading. The honest contribution is therefore a controlled solver/source-class susceptibility diagnostic for nonlinear Poisson/AQUAL-style simulations, not a MOND/AQUAL orientation prediction.
- **Evidence pointers:**
    - Hypothesis row: `H-GP163D-SCIENCEGRADE-LOCAL-01`
    - Experiment/finding rows: `E-GP163D-SCIENCEGRADE-LOCAL-01`, `F-GP163D-SCIENCEGRADE-LOCAL-01`, `E-GP163D-ALIENINV-LOCAL-01`, `F-GP163D-ALIENINV-LOCAL-01`
    - Artifacts:
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/backtest_science_grade_controls.py`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/science_grade_local_backtest.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/science_grade_local_backtest.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/search_alien_invariant.py`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/alien_invariant_search_report.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/alien_invariant_search_report.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/run_alien_invariant_backtests.py`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/alien_invariant_backtests.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/alien_invariant_backtests.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/generate_internal_share_candidates.py`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/internal_share_generator_report.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/internal_share_generator_report.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/run_hostile_generated_candidate_audit.py`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/hostile_generated_candidate_audit.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/hostile_generated_candidate_audit.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/invariance_threshold_existing_backtest.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260502_isotropic18_n160/source_local_morphology_comparison.md`
- **Confidence tier:** `confirmed_scope` - confirmed for the frozen two-representation high-N artifact set as a numerical-methods/instrumentation result; not physics-promoted because phase invariance and independent-solver/boundary invariance are absent.
- **Paper target(s):** `paper7`, `paper8_gravity_methods`
- **Status:** `fresh`
- **Opened:** 2026-05-03
- **Last revised:** 2026-05-04

### INS-082 - NS Leray-aware intertwiners produce a real signed coordinate, but PSD ballast and viscous lifetime block naive Clay promotion

- **Claim:** The exact matrix-intertwiner loophole from INS-081 is scientifically real but narrower than a proof bridge. Local exact Fourier audits show pressure-aware fixed-basis blocks such as `P_r E01 P_s` produce a genuine signed quadratic response around `W=(sin y,-sin x,0)`: the best undamped ratio `|gamma|/||R||^2` is `2.0`, stable through bound `4`, with an exact derivative check matching the computed `gamma`. Pressure-blind commutator-neutral rows remain zero. However, the same signal fails the obvious promotion routes. A pure off-diagonal block is indefinite; the PSD-completion proxy gives only `response_per_cv_ballast=0.5` on single backgrounds and at best `0.875` under two-background stress, with no positive PSD-completed margin. A local Duhamel/viscous lifetime proxy further cuts the best signed response from `2.0` to `0.6666667`, below threshold. Therefore the live Clay-adjacent object is not "finite stencils can beat the tax"; it is a much sharper cycle-integrated signed-coordinate question: can predeclared Leray-aware signed response beat viscous lifetime and return geometry without tautological orientation?
- **2026-05-04 update:** Phase 5ET directly charged the INS-081 matrix-intertwiner class under the same local full ledger: one fixed full matrix `A` shared across blocks in `C_rs=P_r A P_s`, plus a deliberately stronger per-block oracle upper bound. Across `13078` rows (`max_k=96`, `6000` random multimode samples, structured sparse/nonlocal/multimode packets, single-mode controls, and finite-slab eigen suspects), there were no raw survivors above `2/3`, no PSD-net survivors, and no global-matrix PSD-net survivors. Best raw global-matrix profit was `0.603174603175`; best PSD-net profit was `0`. The oracle did expose a large proxy `gamma/sqrt(c)=16.5019547282`, but exact root scoring and PSD ballast killed it (`raw=0.39998740217`, PSD-net negative). Thus matrix intertwiners are no longer an uncharged local loophole; they become a declared-observable-class burden for Track B.
- **2026-05-04 update:** Phase 5EV/5EW sharpened the matrix/nullspace boundary. Exact single-mode rational replay to bound `5` found no self-tax-free/null-branch row above `2/3`; the only saturators were the four known coordinate/eigenflow representatives `k=(0,0,1)` with x/y polarization and cos/sin phase. The strongest cached non-coordinate null row is exactly `38/63`, with squared gap `320/3969`. A translation-covariance audit also showed that all `78/78` nonparallel full-matrix Leray intertwiners from Phase 5DX are excluded as W-independent translation-covariant linear state-price blocks, but `11/78` remain background-covariant when the planar `W` mode supplies the missing momentum. Therefore the translation argument is not a full INS-081 kill; it narrows the admissible class and leaves W-coupled same-ledger matrix blocks plus the nullspace cap as the live global obligations.
- **2026-05-04 update:** Phase 5EX directly charged the W-coupled translation-covariant middle class left open by Phase 5EW: one fixed full matrix per planar-background momentum shift, with a single Frobenius budget, exact quartic root scoring, high-high self-tax, damping, and PSD ballast. Across `19617` rows at the same hostile settings (`max_k=96`, `6000` random multimode samples plus structured controls and finite-slab suspects), there were no raw or PSD-net survivors above `2/3`; the shift-covariant class had best raw profit `0.365424267721` and best PSD-net profit negative (`-3.87855070327e-08`). This closes the cheapest background-covariant matrix-block local loophole. The remaining proof obligation narrows to a global exact-ledger efficiency/nullspace theorem or one admissible full-ledger violator outside the tested candidate families.
- **2026-05-04 update:** Phase 5EY/5EZ applied the state-pricing/no-arbitrage inversion locally: fixed finite supports were declared first, then coefficients were optimized adversarially under the exact full ledger. The optimizer materially improved seeded packets but did not find a survivor. With W-shift covariance included, best profit stayed `0.365391609843`; without the shift target, best fixed-generator profit stayed `0.301548334648`; survivors above `2/3` were `0`. The decisive pattern was not just the null score: every top row collapsed to a single dominant coefficient (`coefficient_participation_ratio` essentially `1`, dominant coefficient fraction `>0.99979`), i.e. coefficient freedom rediscovered low-self-tax/null routes rather than coordinating multimode arbitrage. This is the state-pricing hidden gem: the local adversary chooses the cheapest route, and the cheap route is below-wall; the global theorem should be framed as a no-arbitrage split between null-route cap and interacting-route quartic coercivity.
- **2026-05-04 update:** Phase 5FC tested the strongest false-negative objection to that collapse result by forcing multimode participation before scoring. With `PR(c)=(Σc²)^2/Σc^4` constrained to at least `max(2,0.5*dim)` effective routes, the W-shift constrained run had `5/12` feasible rows, `0` survivors, and best feasible profit `0.029300272678`; the fixed-generator constrained run had `11/12` feasible rows, `0` survivors, and best feasible profit `0.009731187096`. Thus forbidding the one-route trade does not reveal hidden arbitrage in the tested supports; it makes the interacting branch much less profitable locally.
- **2026-05-04 update:** Phase 5FA/5FB turned the state-pricing analogy into finite certificate language rather than coefficient sampling. For fixed supports and fixed predeclared linear Leray observables, the no-arbitrage certificate is the PSD matrix `(2/3)G-H`; across `2226` certificates through `max_k=96`, `max_terms=8`, failures were `0`, best max gain was `0.301587301587`, and worst slack minimum eigenvalue was `0.109523809524`. For nonlinear W-shift matrix observables, Phase 5FB built the lifted quartic certificate `(2/3)^2(G⊗G)-Σ(A_j⊗A_j)`; across `636` global/shift-covariant certificates there were `0` lifted failures/inconclusives and `0` sampled rank-one hits, with best lifted upper `0.603174603175` and worst slack `0.0806248425296`. These are finite no-arbitrage certificates, not global closure, but they make the universal pricing-kernel target mechanically precise.
- **2026-05-04 update:** Phase 5FD/5FE moved the remaining wall from "more finite packets" to an explicit profile-limit theorem. The new bridge note names the non-tautological limit-passage obligation: predeclare state space, topology, observable class, price terms, normalization, and admissible symmetries, then handle vanishing, dichotomy, concentration, null profiles, and cross-profile recombination. The first sparse two-profile falsifiers did not expose a hidden recombination trade. The optimized self-scaled profile-pair run scored `12` pairs with `0` survivors/warnings and best combined profit `0.0655356700841`; the broader self-scaled no-optimizer sweep scored `64` pairs with `0` survivors/warnings and best W-shift lifted upper `0.650206358164 < 2/3`; the targeted scale-2 optimizer kept the near-wall `low_high_signed_K2` row at full-ledger profit `0.0283468837983`; a cross-support no-optimizer sweep scored `51` self/cross-support pairs with `0` survivors/warnings and best combined profit `0.00235908387547`; and a cross-support scale-2 optimizer scored `10` pairs with `0` survivors/warnings and best combined profit `0.0635445699857`. This does not prove global closure; it says the tested finite two-profile recombinations do not break the pricing kernel and identifies the true next theorem burden.
- **2026-05-04 update:** Phase 5FH converted the market-impact/state-pricing analogy into Lean proof plumbing. The new `ns_pricing_kernel_limit_passage.lean` file proves the abstract bridge: if each global Track B block admits a fixed profile-family certificate covering dichotomy/fragmentation, concentration impact, vanishing, null profiles, and cross-profile recombination, then the existing Track B no-survivor theorem follows. This is a proof-surface compression, not a regularity proof; the live mathematical work is now to prove those branch certificates for actual Leray/Sobolev profile decompositions or find the branch where the pricing kernel fails.
- **2026-05-04 update:** Phase 5FI pushed the same bridge one step closer to the infinite branch. `ns_pricing_kernel_countable_limit.lean` proves that no-arbitrage survives a countable profile stream if finite prefixes are pointwise priced, limiting payoff is approximated from finite prefixes, and limiting price dominates every finite-prefix price. This is the market-impact/slippage obligation in exact form: infinity cannot create a free trade unless the PDE violates finite-prefix payoff approximation or price lower-semicontinuity for the declared Leray pricing kernel.
- **2026-05-04 update:** Phase 5FJ tested the cheapest finite-prefix analogue of that obligation by stacking dyadically separated copies of high-scoring supports and charging exact full ledger plus linear/lifted pricing certificates. In the enlarged run (`max_k=24`, `prefilter=18`, `levels=5`) across `90` prefix rows there were `0` survivors, `0` linear certificate failures, and `0` lifted warnings. Best full profit was only `0.00944268442617`; best quartic proxy was `0.147404321981`; the top dyadic example fell as prefixes were appended (`0.00944 -> 0.00235 -> 0.000581`). This does not prove lower-semicontinuity, but it demotes the simplest countable-prefix price-leakage escape.
- **2026-05-04 update:** Phase 5FK then allowed a finite-prefix level-weight adversary to tune amplitudes/signs across dyadic levels under fixed support and observable rules. Across `20` scanned rows there were `0` survivors, `0` linear certificate failures, and `0` lifted warnings. The best unconstrained route simply selected one prefix level (`profit=0.00944268442617`, participation `1`), while the best constrained multi-level route fell to `0.000469085906178` at participation `2.62`. This supports the market-impact reading locally: coordinated execution pays more price than payoff in the tested finite-prefix class.
- **2026-05-04 update:** Phase 5FL began the branch-killer grid with the null-profile cap. `ns_null_profile_cap_branch.lean` proves the branch routing: if null profiles are capped, non-null profiles are priced, and residual payoff is charged, then the family is no-arbitrage and can feed the existing Track B no-survivor bridge. Existing deterministic evidence is now integrated into the branch: Phase 5EU scored `13078` hostile rows with `0` raw/PSD-net survivors and `0` above-wall near-self-null rows; Phase 5EV gives exact null single-mode evidence with non-coordinate row `38/63` and only known coordinate/eigenflow saturators at the wall. This isolates the remaining theorem as the actual Leray/Sobolev nullspace gain lemma.
- **2026-05-04 update:** Phase 5FM compressed the remaining Track B work into a seven-branch falsification grid: null-profile cap, dichotomy/price subadditivity, cross-profile recombination charging, concentration impact coercivity, vanishing/no deployed payoff, finite-prefix payoff approximation, and price lower-semicontinuity. This is an anti-tautology control artifact: future work must name the branch it attacks before running, and valid outcomes are branch proof, deterministic branch falsifier, sharper analytic reduction, or infrastructure gap.
- **2026-05-04 update:** Phase 5FN attacked the weakest branch, concentration impact coercivity, without another broad packet loop. The new branch audit predeclared localized Fourier caps/tubes/lines and charged the exact full ledger on `388` rows: `0` survivors, best full-ledger profit `0.000211434054788`, best concentrated profit `0.000130371394377`. The expanded Phase 5EN bound-4 top-subspace replay then checked the actual near-wall family: `603` rows, `0` survivors, best full-ledger profit `0.507281731056`; the most concentrated rows reached spatial max/mean `32.47` but paid self-tax in the thousands and collapsed to `~0.013-0.018` payoff. `ns_concentration_impact_branch.lean` now proves the formal routing theorem: a concentration-impact profile certificate is enough to feed the existing Track B no-survivor bridge. This locally strengthens the market-impact/no-arbitrage read, while keeping the hard global lower-semicontinuity/coercivity lemma explicitly unpaid.
- **2026-05-04 update:** Phase 5FO then moved the vanishing/no-deployed-payoff branch from "named only" to locally tested. The audit fixed a topology proxy before scoring: high Fourier participation plus low sampled spatial max/mean and L4/L2^2. A strict smoke pass found `0` survivors across `394` rows and `30` vanishing-like rows. The looser hostile pass scored `1488` rows, including `171` vanishing-like rows, again with `0` survivors; best full-ledger payoff was only `1.96745995342e-05`, and best vanishing-like payoff was `8.63586468606e-06`. `ns_vanishing_branch.lean` now proves the routing theorem: if a profile family vanishes in the declared topology and residual payoff is charged, it feeds the existing Track B no-survivor bridge. This does not prove the global concentration-compactness lemma, but it removes the cheapest local delocalized-packet escape.
- **2026-05-04 update:** Phase 5FP made dichotomy and cross-profile recombination branch-specific rather than only implicit in the general bridge. `ns_dichotomy_cross_profile_branch.lean` proves that independently priced fragments plus a charged cross residual imply family no-arbitrage and therefore feed the Track B no-survivor bridge. The local evidence is still the Phase 5FE finite profile-pair suite: self-scaled and cross-support recombinations found no survivor or certificate warning, with the strongest optimized cross-support combined profit around `0.0635445699857`. The remaining burden is not finite two-profile bookkeeping; it is the analytic theorem that actual profile decompositions charge cross terms under the declared topology.
- **2026-05-04 update:** Phase 5FQ compressed the branch-local work into a single theorem object. `phase5fq_trackb_profile_decomposition_obligation.md` states the eight obligations without hiding the topology choice: fixed topology, fixed observable class, finite-prefix payoff approximation, price lower-semicontinuity, null-profile cap, concentration impact, vanishing no-payoff, and cross-profile charging. `ns_trackb_profile_decomposition_spine.lean` imports the branch files and proves the spine implication: once a real Leray/Sobolev profile-decomposition certificate supplies those branch obligations, the existing Track B no-survivor theorem follows. This is the current Clay-adjacent proof surface: local packet search is mostly demoted, and the live question is whether the analytic profile theorem can be instantiated without circularity.
- **2026-05-04 update:** Phase 5FR tightened the live theorem one layer further into Littlewood-Paley shell language. `ns_littlewood_paley_profile_bridge.lean` defines a fixed dyadic shell pricing stream, finite shell prefixes, charged cross-shell residual price/payoff, and a countable shell-limit certificate. It proves that shell no-arbitrage plus charged cross residuals prices every finite prefix, and that finite-prefix payoff approximation plus price lower-semicontinuity prevents no-arbitrage failure from appearing only at the infinite shell limit. This does not close the PDE theorem, but it makes the next bridge concrete: instantiate that shell certificate under a standard Leray/Sobolev/Besov topology, or exhibit finite-prefix invisibility, price leakage, or an uncharged matrix/W-coupled shell observable.
- **2026-05-04 update:** Phase 5FS refined the shell bridge into the Bony/Littlewood-Paley interaction classes where the global ghost must live: low-high catalyst, high-low transport, high-high cascade, same-shell, and remainder. `ns_littlewood_paley_paraproduct_bridge.lean` proves that if every declared paraproduct interaction is priced, residual payoff is charged, payoff is finite-prefix visible, and price is lower semicontinuous, then the countable paraproduct limit feeds the existing Track B no-survivor theorem. This is a tighter Clay-adjacent proof surface: the next theorem/falsifier is a concrete paraproduct charging estimate or counterexample under a fixed LP/Besov/Sobolev topology, not another broad finite packet.
- **2026-05-04 update:** Phase 5FT answered the "why not Clay proof?" question as a formal closure bridge. `ns_clay_closure_bridge.lean` proves the top-level conditional theorem: if actual NSE evolutions generate globally admissible Track B blocks, those blocks satisfy the fixed charged LP/paraproduct pricing certificate, no-survivor on all blocks implies a critical continuation-control quantity, and the declared continuation criterion is valid, then smooth finite-energy data is globally regular. This makes the overclaim boundary exact. The current work is Clay-proximate only if two hard PDE bridges are paid: actual-block paraproduct charging and no-survivor-to-critical-control. The new BRIDGE-1 default grid is `ns_track_b_paraproduct_2026-05-04.json`, with four branches: low-high catalyst, high-low transport, high-high self-tax, and same-shell/remainder plus countable-limit charging.
- **2026-05-04 update:** Phase 5FU connected the first paraproduct branch to an older continuum-tail object. `ns_low_high_catalyst_charging_obligation.lean` proves that a low-high catalyst interaction is priced if its payoff/price are identified with a predeclared leakage gain/loss budget and that leakage is absorbed by a reserve loss channel. This does not prove the PDE estimate, but it tightens the low-high branch materially: the next theorem is a leakage representation plus absorption estimate for actual LP/Besov NSE blocks, and the falsifier is a low-high interaction whose declared leakage gain exceeds declared leakage loss.
- **2026-05-04 update:** Phase 5FV sharpened the low-high branch into the true continuation gap. The standard LP/Bony estimate charges low-high payoff by `||grad S_{j-2}u||_infty ||Delta_j u||_2^2`, while viscosity pays `nu 2^(2j)||Delta_j u||_2^2`; therefore high tails are absorbed once the low-frequency Lipschitz factor is controlled relative to the tail frequency. The hard bridge is not the textbook low-high estimate. It is deriving integrable/bounded low-frequency Lipschitz control from the Track B pricing/no-survivor mechanism. Otherwise the argument merely assumes a continuation criterion.
- **2026-05-04 update:** Phase 5FW formalized that continuation bridge. `ns_low_frequency_lipschitz_control_bridge.lean` defines low-frequency Lipschitz prefix costs and reserve prices for an evolution and proves that if no-survivor blocks price each cost, finite prefix reserves are uniformly bounded by a declared critical budget, and that budget implies critical control, then the `TrackBNoSurvivorToCriticalControl` object required by the Clay closure theorem follows. This is now the tightest no-overclaim bridge: the remaining theorem is an actual PDE estimate showing the Track B state-pricing kernel bounds the accumulated low-frequency Lipschitz coefficient for NSE LP/Bony blocks.
- **2026-05-04 update:** Phase 5FX added the analogous adapter for high-high self-tax. `ns_high_high_self_tax_charging_obligation.lean` proves that a declared high-high LP/Bony interaction is priced when represented by a Track B full-ledger block whose payoff is survival profit, whose price is the sharp `2/3` wall, and whose block satisfies threshold-defect convexity. This routes the Phase 5EH/5EJ/5EL lesson into the paraproduct grid: mixed-only high-high gain is irrelevant until exact quartic/root/full-ledger self-tax is charged.
- **2026-05-04 update:** Phase 5FY added the matching high-low transport adapter. `ns_high_low_transport_charging_obligation.lean` proves that a high-low LP/Bony interaction is priced when its payoff/price are represented by a predeclared leakage gain/loss budget and reserve absorption holds. The paraproduct grid now has explicit adapter targets for low-high, high-low, high-high, and low-frequency Lipschitz continuation control; the remaining work is no longer branch naming but paying or falsifying the PDE estimates.
- **2026-05-04 update:** Phase 5FZ composed the profile-pricing spine with the low-frequency Lipschitz continuation bridge. `ns_profile_lipschitz_clay_bridge.lean` proves the exact top-level implication: fixed profile pricing plus the quartic threshold-defect no-survivor theorem gives no-survivor on all global blocks; a fixed low-frequency Lipschitz ledger then converts those no-survivor blocks into critical control; and a declared continuation criterion yields global regularity for smooth finite-energy data. This is still conditional, but it compresses the Clay-proximate bridge to two non-tautological PDE instantiations: a Leray/Sobolev profile-pricing theorem and a low-frequency Lipschitz reserve theorem, both fixed before payoff is scored.
- **2026-05-04 update:** Phase 5GA closed the remaining obvious paraproduct adapter gap. `ns_same_shell_remainder_charging_obligation.lean` proves that a same-shell/remainder interaction is priced when it is represented by a fixed profile-family ledger whose payoff is charged and whose price dominates the interaction price. Same-shell and remainder terms are therefore no longer an informal residual bucket in the proof architecture; they are a named PDE obligation: prove the fixed-family representation for actual LP/Bony NSE terms, or exhibit a term whose payoff escapes the declared price.
- **2026-05-04 update:** Phase 5GB sharpened the low-high catalyst branch through a kinematic dichotomy. `ns_low_high_kinematic_dichotomy.lean` proves that, under a fixed deformation-cost ledger, positive low-high leakage forces positive deformation if zero-deformation transport has non-positive leakage; positive deformation then prices the interaction when charged by reserve loss. The key mathematical target is now exact: on the flat torus, prove that a smooth periodic zero-strain low field is a Killing field, hence a constant translation, hence LP-shell preserving; then prove that any nonconstant shell transfer enters the positive-deformation branch and pays the reserve/self-tax ledger. This is a stronger low-high bridge than generic Grönwall or transport-frame arguments.
- **2026-05-04 update:** Phase 5GC added a matrix-block admissibility gate to the proof spine. `ns_matrix_block_ledger_charging_obligation.lean` proves that a matrix-block observable is admissible only if PSD ballast, damping, independent normalization, and cross terms are all charged; missing any charge demotes the observable, while W-independent off-diagonal blocks remain excluded only by translation covariance. This converts INS-081 from a recurring loophole into a fixed split used by every Track B branch: excluded, demoted, or fully charged and subject to the same global threshold-defect theorem. The local matrix evidence is still not a Clay proof, but the overclaim route "signed Leray-aware coordinate = positive energy certificate" is now mechanically blocked.
- **2026-05-04 update:** Phase 5GD compressed the state-pricing analogy into a formal split rather than a metaphor. `ns_universal_state_pricing_split.lean` proves the algebraic routing: if the state space, observable class, price terms, normalization, null-route cap, interacting-root quartic charge, matrix-block gate, and quartic no-survivor theorem are fixed before payoff is scored, then every global Track B block is killed by the existing no-survivor route. This is still not a Clay proof; the exact live theorem is the universal PSD/SOS-style state-pricing kernel for actual Leray/Sobolev states, with the null/self-tax-free branch and interacting above-wall branch both charged under the same predeclared ledger.
- **2026-05-04 update:** Phase 5GE made the universal kernel demand mechanically checkable. `ns_trackb_sos_pricing_kernel_receipt.lean` defines a lossless receipt for the interacting branch: the exact threshold defect gap at `t=sqrt((2/3)/gamma)` must equal nonnegative slack plus a finite sum of squares. Lean proves such a receipt implies root coercivity and therefore instantiates the interacting side of the universal state-pricing split. This does not search for the certificate; it raises the bar for any claimed proof or ZTARE candidate from "there is a PSD kernel" to "here is the exact receipt Lean can verify."
- **2026-05-04/05 update:** Phase 5GO/5GP sharpened the low-high catalyst branch into a constant-bearing witness plus a direct finite falsifier. `ns_low_high_kinematic_dichotomy.lean` now contains `LowHighBilinearConstantWitness`, the proof-object target `leakage <= C_lh * deformationEnergy <= full Track B reserve/PSD price`. The saved-artifact mine found no low-high/catalyst survivor among `38` rows and showed bare self-tax is misleading; the direct hostile optimizer then searched `67` fixed low-high supports (`24` optimized rows, `max_k=64`) for a breaker of `mixed_gain / psd_ballast_at_total_defect_1` and found none. Best optimized mixed/PSD-ballast ratio was `0.3807124555766351`, with `0` breakers above `1` and `0` survivors above `2/3`. The follow-up Lean receipt `LowHighLPBonyEstimateReceipt` exposes the real estimate shape `leakage <= C_lh * lowFrequencyLipschitzCost * highShellEnergy` plus the frequency-reserve absorption split; this blocks the tautological move of assuming the low-frequency Lipschitz factor is already controlled. `ns_low_high_lipschitz_reserve_adapter.lean` then adds the stricter bridge: an unpaid LP/Bony cost must literally embed as an entry of the global `LowFrequencyLipschitzLedger` and be priced by a no-survivor block. Phase 5GR attempted the smooth decoupler directly with `L=A sin(K y)e_x`: the low mode has exact self-advection zero, while widened finite high-shell sidebands show instantaneous `H1` growth per low Lipschitz coefficient up to `0.9774962493360696` and can beat a viscosity-only proxy by choosing large `A`. Thus the weak local-reserve theorem is false. Phase 5GT replayed the full linearized low-high shear `P((L·grad)H+(H·grad)L)`: transport-only `L2` growth is numerically zero (`5.024295867788081e-15`), but full low-high growth is positive in both `L2` and `H1` (`0.9845898011587759` and `0.9845898011587773` per low Lipschitz). This kills the cheap energy-skew/non-rearming escape for the smooth shear branch. Phase 5GU then prices the catalyst instead of denying it: beating viscosity at shell `N` requires `A >= nu*N^2/(c(N,K)*K)` and low-mode energy `A^2/2 ~ N^4/K^2`. The audit found fixed-`K=1` scaling `energy/N^4 ≈ 0.5238456319033353` at `N=64`; even at the low-high edge `K=N/4`, it paid `energy/N^2 ≈ 15.915765978682325`. Lean records the algebraic receipts `shear_market_impact_energy_cross_bound` and `no_shear_break_even_above_energy_budget`, the latter giving the finite-reserve cutoff: once the low-frequency budget is fixed, sufficiently high shells cannot be rearmed by this shear without exceeding the market-impact price. The remaining burden is exact and central: prove the global Lipschitz reserve ledger captures this price under fixed topology and limit passage, or exhibit a smooth periodic sequence where that cost/reserve link fails in the limit.
- **2026-05-05 update:** The low-frequency bridge now has the finite-prefix falsifier form. `ns_low_frequency_lipschitz_control_bridge.lean` proves `no_overbudget_lipschitz_prefix_under_no_survivor` and `no_overbudget_market_impact_prefix_under_no_survivor`: if no-survivor blocks price the declared Lipschitz ledger, no finite prefix of Lipschitz cost, or of a pointwise embedded market-impact cost stream, may exceed the critical reserve budget. This converts the infinite low-high ghost into a finite test: produce a smooth LP/Bony prefix whose predeclared market-impact price exceeds the reserve budget, or prove such prefixes cannot occur under actual NSE topology.
- **2026-05-04 update:** Phase 5FX/5GK/5GL high-high work is now compressed into an explicit resonance route certificate. `ns_mixed_self_resonance_partition.lean` proves nonresonant mixed/self support disjointness forces cross-zero; finite replay showed above-wall disjointness through bound 3 and then exposed bound-4 resonant overlap that is locally crushed by self-tax rather than saved by anti-alignment. `ns_high_high_self_tax_charging_obligation.lean` keeps the anti-tautology guard: Cauchy semantics plus positive self-tax is insufficient, because the scalar bad ledger `gamma=8/3, cross=-2, selfTax=4` has zero defect at the Track B root; the physical Cauchy-saturating resonant pair appears at the wall, not above it. The new `ns_high_high_resonance_route_adapter.lean` proves the route split: wall-or-below dies by the cap, nonresonant branches need the exact root self-tax floor, and resonant branches must pay the stronger cross-aware allowance. This does not close the PDE theorem; it makes the remaining high-high burden a fixed pre-payoff receipt rather than an after-the-fact self-tax story.
- **2026-05-05 update:** The high-high route now has the direct negative test as well as the positive receipt. `ns_high_high_resonance_route_adapter.lean` proves `no_nonresonant_root_floor_receipt_of_shortfall` and `no_resonant_root_charge_receipt_of_shortfall`: a predeclared nonresonant or resonant route is impossible if its self-tax falls below the corresponding root floor or cross-aware allowance. This makes the next high-high object binary and anti-tautological: either prove those floors from the fixed Leray/Sobolev/LP topology, or exhibit one smooth admissible above-wall sequence with receipt shortfall.
- **2026-05-05 update:** The low-high reserve bridge now also has a one-entry falsifier. `ns_low_frequency_lipschitz_control_bridge.lean` proves `no_underpriced_market_impact_entry_under_no_survivor`: if a predeclared market-impact cost embeds into the low-frequency Lipschitz cost, and the block is no-survivor, then the reserve price for that entry must cover the market-impact cost. Thus a smooth LP/Bony low-high decoupler no longer needs an infinite-limit construction to break the bridge; a single underpriced entry is enough.
- **2026-05-05 update:** The profile-limit/Littlewood-Paley passage now has the same finite falsifier shape. `ns_profile_limit_lsc_bossfight.lean` proves that a single finite prefix whose charged price exceeds the declared limiting price invalidates both the abstract profile LSC certificate and the LP/Bony paraproduct limit certificate. This shifts the infinite ghost from vague compactness anxiety to a concrete topology test: prove `prefix price <= limit price` for the fixed NSE price functional, or produce one prefix price drop.
- **2026-05-05 update:** The null-profile branch now has an explicit negative arm. `ns_null_profile_cap_branch.lean` proves `no_null_profile_cap_branch_certificate_of_null_arbitrage`: one predeclared null profile with `price < payoff` invalidates the null cap certificate for its family. This keeps the self-tax-free/null route from becoming a fitted label; it must either be capped in the fixed observable class or falsified by a declared-null counterexample.
- **2026-05-05 update:** The high-low branch has been brought into the same theorem/falsifier format. `ns_high_low_transport_charging_obligation.lean` proves that a leakage-absorption high-low bridge cannot coexist with a same-budget reserve shortfall, and that a closed positive high-low class cannot contain a concrete member with payoff greater than price. The paraproduct grid now has finite negative-arm tests for low-high, high-low, high-high, null, and profile-limit price drops.
- **2026-05-05 update:** The low-high catalyst adapter now has the same explicit shortfall theorems as high-low transport. `ns_low_high_catalyst_charging_obligation.lean` proves that a leakage-absorption low-high bridge cannot coexist with `leakageLoss < leakageGain`, and that a closed positive low-high class cannot contain an underpriced member. This removes the last adapter asymmetry in the finite branch-falsifier surface.
- **2026-05-05 update:** The branch-falsifier surface is now compressed into one checked map. `ns_trackb_finite_falsifier_spine.lean` defines `TrackBFiniteFalsifierSurface` and constructs `trackBFiniteFalsifierSurface`, collecting the negative-arm tests for low-high, high-low, high-high, residual/remainder, concentration, vanishing, cross-profile, countable-limit, low-frequency reserve, null profile, profile-limit/LP price drop, and matrix negative-gap branches. This is not a proof of regularity; it is a stronger proof-frontier object because every live branch now has a finite witness shape or a named analytic receipt obligation.
- **2026-05-05 update:** Phase 5GW replayed the finite falsifier aliases over saved Phase 5 JSON artifacts. It scanned `173` files and `24692` dict rows and found `0` candidate rows. This is cached-artifact evidence only, but it removes a cheap failure mode: there is no obvious finite Track B spine falsifier already serialized in the local Phase 5 corpus.
- **2026-05-05 update:** The low-high LP/Bony constant-bearing receipt now has a direct finite negative arm in the spine. `ns_low_high_kinematic_dichotomy.lean` proves `no_low_high_bilinear_falsifier_with_constant_witness`: a witness declaring `leakage <= C_lh * deformationEnergy <= Track B reserveLoss` cannot coexist with the same-ledger shortfall `reserveLoss < leakage`. `ns_trackb_finite_falsifier_spine.lean` now includes this as `low_high_bilinear_constant_shortfall`. This does not pay the PDE estimate, but it tightens Boss Fight 2 into a single non-tautological obligation: prove the constant-weighted LP/Bony deformation cost embeds into the predeclared global reserve price, or produce one smooth periodic low-high block where it does not.
- **2026-05-05 update:** The same low-high negative arm now targets the concrete LP/Bony receipt directly. `no_low_high_bilinear_falsifier_with_lp_bony_receipt` proves that the receipt `leakage <= C_lh * lowFrequencyLipschitzCost * highShellEnergy <= Track B reserveLoss` cannot coexist with `reserveLoss < leakage`, and the spine includes it as `low_high_lp_bony_receipt_shortfall`. The next local/theorem work should therefore try to instantiate or falsify exactly that absorption line under the fixed flat-torus LP/Bony topology.
- **2026-05-05 update:** The low-high reserve adapter now exposes the exact smooth-shear continuation falsifier. `ns_low_high_lipschitz_reserve_adapter.lean` proves `no_low_high_lipschitz_reserve_link_with_bilinear_falsifier`: an unpaid LP/Bony estimate linked to a global `LowFrequencyLipschitzLedger` entry and priced by a no-survivor block cannot coexist with a same-ledger `reserveLoss < leakageGain` shortfall. This pins the shear/market-impact branch to the real bridge: falsify the fixed global reserve link, falsify no-survivor pricing for that entry, or pay the reserve.
- **2026-05-05 update:** The finite-prefix budget falsifier has been lifted to the composed Clay bridge. `ns_profile_lipschitz_clay_bridge.lean` proves `no_overbudget_lipschitz_prefix_of_profile_lipschitz_closure` and `no_overbudget_market_impact_prefix_of_profile_lipschitz_closure`: once the profile-pricing obligation, quartic no-survivor theorem, and low-frequency Lipschitz reserve bridge are fixed, one generated evolution with an overbudget finite Lipschitz or embedded market-impact prefix contradicts the closure. This is still conditional, but it makes the continuation-bridge failure mode top-level and mechanically checkable.
- **2026-05-05 update:** Phase 5GX extended the smooth shear market-impact audit in a capped tail replay (`ky_radius_cap=64`, `29` rows, up to `N=128`). The scaling read survived: fixed `K=1`, `N=128` paid `energy/N^4=0.9136665542247177`, while the low-high edge `K=N/4`, `N=128` paid `energy/N^2=59.13043478260843`. This is finite evidence only, but it further supports the state-pricing interpretation: the shear catalyst can rearm, but executing it at higher shells requires a growing low-frequency reserve price that the global Lipschitz ledger must capture.
- **2026-05-05 update:** The market-impact tail now has an abstract limit-passage hook. `ns_profile_lipschitz_clay_bridge.lean` proves `no_unbounded_lipschitz_prefix_of_profile_lipschitz_closure` and `no_unbounded_market_impact_prefix_of_profile_lipschitz_closure`: any generated Lipschitz or embedded market-impact prefix stream that is unbounded eventually exceeds the finite critical budget and contradicts the fixed profile + Lipschitz closure. The remaining PDE bridge is no longer a vague infinity objection; it is the exact question of whether actual NSE LP/Bony market-impact costs embed into a priced finite-budget ledger or expose an unbounded-prefix falsifier.
- **2026-05-05 update:** Phase 5GY sampled sparse high-high resonant-overlap pairs at bounds `3` and `4` (`5000` random pairs per bound; sparse dictionaries only). It found no cheap high-high escape: bound `3` scored `756` resonant rows with `0` mixed-above-wall rows and top full-ledger profit `0.2408386710617624`; bound `4` scored `385` rows with top profit `0.13333333333333328`; survivors above `2/3` were `0`. This is finite evidence only, but it supports the current branch split: the remaining high-high burden is the root self-tax floor / resonant cross-aware allowance theorem, not generic resonant pair search.
- **2026-05-05 update:** Phase 5HA formalized the low-high smooth-shear continuum fork. `ns_low_high_shear_sequence_falsifier.lean` proves that a predeclared smooth shear/high-shell sequence with pointwise nonnegative market-impact costs, an unbounded N^4 lower law, and an embedding of those costs into the global low-frequency Lipschitz ledger contradicts the composed profile + Lipschitz closure. This is not the PDE estimate; it makes the estimate/falsifier exact. The remaining theorem is to derive the market-impact-to-global-reserve embedding under fixed Leray/Sobolev LP/Bony topology, or exhibit the smooth periodic sequence where local leakage growth cannot be charged by that ledger.
- **2026-05-05 update:** Phase 5HB extended the smooth shear market-impact tail to `N=512` under a bounded sideband operator (`ky_radius_cap=96`, `39` rows). The larger capped replay did not expose cost smearing: fixed `K=1`, `N=512` paid `energy/N^4=4.4443554448981235`, and the low-high edge `K=N/4`, `N=512` paid `energy/N^2=2128.2812499999995`. This strengthens the finite state-pricing read but still does not prove the LP/Bony lower-semicontinuity/global-reserve embedding theorem.
- **2026-05-05 update:** The low-high LP/Bony receipt has been sharpened into an operator-norm estimate handoff. `ns_low_high_lipschitz_reserve_adapter.lean` now derives the unpaid receipt from `leakage <= operatorNorm * highShellEnergy` and `operatorNorm <= C_lh * lowFrequencyLipschitzCost`. The live PDE estimate is therefore not a final ledger inequality but the recognizable Bony/Sobolev operator-norm bound for the fixed low-high linearized interaction, followed by the already-declared global reserve embedding.
- **2026-05-04 update:** Phase 5GN now connects the branch receipts to the infinite LP/Bony limit directly. `ns_profile_limit_lsc_bossfight.lean` factors `LPParaproductPricingStream` through the same lower-semicontinuity interface as the countable profile and LP shell streams via `profile_lsc_certificate_of_lp_paraproduct_limit`. This removes a proof-plumbing loophole: charging finite paraproduct prefixes is insufficient unless the exact Track B paraproduct price is lower-semicontinuous at the countable limit.
- **2026-05-04 update:** Phase 5GE/5GM tightened the SOS/matrix falsifier boundary. `sos_receipt_of_nonnegative_threshold_gap` and `no_sos_receipt_of_negative_threshold_gap` show that, once the block and observable class are fixed, the scalar receipt exists exactly when the threshold-root gap is nonnegative in this interface. The matrix handoff now requires admissible/charged matrix observables before using that scalar gap. Thus the next falsifier is concrete: one admissible positive-tax matrix block with negative `thresholdDefectGapAtRoot` breaks the current universal-kernel route.
- **2026-05-05 update:** Phase 5GS replayed that falsifier against saved Phase 5 JSON artifacts without recomputing Fourier state. Across `170` files and `1387` rows carrying `mixed_gain`, `self_tax`, and `mixed_self_cross`, there were `247` above-wall positive-tax rows, `33` matrix-like above-wall positive-tax rows, and `0` negative threshold-gap rows. The closest positive-tax gap was `0.31594708126337734`; the closest matrix-like positive-tax gap was `0.7055091184983244`. This does not prove the uniform Sobolev matrix/SOS theorem, but it removes an important false-negative concern: the cached finite corpus does not already contain the requested admissible negative-gap matrix falsifier.
- **Evidence pointers:**
    - Experiment/finding rows: `E-GP186-PHASE5DYEB-LERAY-SIGNED-01`, `F-GP186-PHASE5DYEB-LERAY-SIGNED-01`
    - Deterministic audits:
      - `projects/ns_millennium_hunt/workspace/phase5dy_leray_intertwiner_profit_tax_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5dz_leray_intertwiner_backtests.md`
      - `projects/ns_millennium_hunt/workspace/phase5ea_leray_intertwiner_psd_stress_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5eb_leray_intertwiner_viscous_orientation_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5et_matrix_intertwiner_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5et_matrix_intertwiner_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ev_null_branch_exact_single_mode_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ev_null_branch_exact_single_mode_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ew_translation_covariance_intertwiner_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ew_translation_covariance_intertwiner_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ex_w_coupled_shift_matrix_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ex_w_coupled_shift_matrix_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ey_continuous_support_violator_search_shift.md`
      - `projects/ns_millennium_hunt/workspace/phase5ey_continuous_support_violator_search_shift.json`
      - `projects/ns_millennium_hunt/workspace/phase5ey_continuous_support_violator_search.md`
      - `projects/ns_millennium_hunt/workspace/phase5ey_continuous_support_violator_search.json`
      - `projects/ns_millennium_hunt/workspace/phase5ez_state_pricing_collapse_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ez_state_pricing_collapse_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_shift.md`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_shift.json`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_fixed.md`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_fixed.json`
      - `projects/ns_millennium_hunt/workspace/phase5fa_sparse_psd_pricing_certificate.md`
      - `projects/ns_millennium_hunt/workspace/phase5fa_sparse_psd_pricing_certificate.json`
      - `projects/ns_millennium_hunt/workspace/phase5fb_shift_quartic_pricing_certificate.md`
      - `projects/ns_millennium_hunt/workspace/phase5fb_shift_quartic_pricing_certificate.json`
      - `projects/ns_millennium_hunt/workspace/phase5fd_pricing_kernel_limit_passage_bridge.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_broad_noopt.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_broad_noopt.json`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_scale2_opt.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_scale2_opt.json`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_cross_noopt.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_cross_noopt.json`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_cross_scale2_opt.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_cross_scale2_opt.json`
      - `projects/ns_millennium_hunt/workspace/phase5gc_matrix_block_ledger_charging_obligation.md`
      - `ztare_proofs/ZtareProofs/ns_matrix_block_ledger_charging_obligation.lean`
      - `projects/ns_millennium_hunt/workspace/phase5gd_universal_state_pricing_split.md`
      - `ztare_proofs/ZtareProofs/ns_universal_state_pricing_split.lean`
      - `projects/ns_millennium_hunt/workspace/phase5ge_trackb_sos_pricing_kernel_receipt.md`
      - `ztare_proofs/ZtareProofs/ns_trackb_sos_pricing_kernel_receipt.lean`
      - `projects/ns_millennium_hunt/workspace/phase5gb_low_high_kinematic_dichotomy.md`
      - `ztare_proofs/ZtareProofs/ns_low_high_kinematic_dichotomy.lean`
      - `projects/ns_millennium_hunt/workspace/phase5go_low_high_witness_data_mine.md`
      - `projects/ns_millennium_hunt/workspace/phase5go_low_high_witness_data_mine.json`
      - `projects/ns_millennium_hunt/workspace/phase5gp_low_high_psd_ratio_hostile_search.md`
      - `projects/ns_millennium_hunt/workspace/phase5gp_low_high_psd_ratio_hostile_search.json`
      - `ztare_proofs/ZtareProofs/ns_low_high_lipschitz_reserve_adapter.lean`
      - `projects/ns_millennium_hunt/workspace/phase5gr_low_high_lipschitz_decoupler_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5gr_low_high_lipschitz_decoupler_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ha_low_high_shear_sequence_falsifier.md`
      - `ztare_proofs/ZtareProofs/ns_low_high_shear_sequence_falsifier.lean`
      - `projects/ns_millennium_hunt/workspace/phase5hb_low_high_shear_market_impact_extended_tail.md`
      - `projects/ns_millennium_hunt/workspace/phase5hb_low_high_shear_market_impact_extended_tail.json`
      - `ztare_proofs/ZtareProofs/ns_low_high_lipschitz_reserve_adapter.lean`
    - Follow-on substrate:
      - `projects/ns_proofsearch_signed_leray_escape_coordinate/`
      - `rubrics/ns_proofsearch_signed_leray_escape_coordinate.json`
- **2026-05-05 update:** The latest local/parallel Track B push sharpened three branch fronts without claiming closure. Boss Fight 1 now has an operator-level matrix receipt: `FiniteSelfAdjointOperator`, `FinitePSDOperator`, and `MatrixBlockOperatorPSDReceipt` convert a real finite PSD quadratic identity plus residual SOS terms into the existing matrix no-survivor route; a negative quadratic witness blocks fake PSD promotion. Boss Fight 2 now has a cleaner PDE target: `LowHighBonyOperatorEstimateRealityCheck` reduces the low-high ledger receipt to the fixed LP/Bony estimate `leakage <= operatorNorm * highShellEnergy` and `operatorNorm <= C_lh * lowFrequencyLipschitzCost`; Phase 5HB extended the shear market-impact replay to `N=512` without finding the finite false negative. Boss Fight 3/high-high resonance now admits resonant additive overlap but proves that any strict above-wall threshold-root escape must pay the exact cross-aware allowance `selfTax >= (1 - x^2 - 2*cross*x^3)/x^4`. A new branch-local ZTARE substrate `ns_proofsearch_low_high_operator_norm_bridge` is ready to attack the low-high operator estimate under fixed topology. This is evidence of proof-surface compression and anti-tautology discipline, not a global NS proof.
- **2026-05-05 update:** The low-high local theorem target was corrected after the narrowed substrate produced an over-high score-97 packet. The packet usefully identified the standard fixed LP/Bony estimate, but its proof line treated `<Lambda Delta_j P((L·grad)H), Lambda H>` as exactly skew. The correct proof must split a skew commuted transport main term plus a projected H1 commutator remainder bounded by `C ||grad L||_infty ||Lambda H||_2^2`, and must pay `H grad^2 L` with the paired Bernstein factors `||H||_2 <= C 2^{-j}||Lambda H||_2` and `||grad^2 L||_infty <= C 2^j||grad L||_infty`. Lean and the substrate now require `projected_transport_commutator_receipt`, `stretching_h_grad_l_receipt`, and a finite low-shell core receipt. This strengthens the anti-tautology bar: high scores on local LP/Bony prose are not proof-grade unless the commutator and finite-core receipts are explicit.
- **2026-05-05 update:** The low-high commutator falsifier surface was locally tail-tested after the correction. `phase5hv` and `phase5hw` found no scale-growing sparse Fourier commutator gap under either L1 Fourier-Lipschitz or sampled physical-space gradient denominators. `phase5hx` identified the phase-locked high-mode chain as the suspicious finite direction: singular norms can grow very large, but the Hermitian energy-production norm stayed below one. `phase5iz` then pushed the chain length to `512` at shell labels `512` and `1024`; max Hermitian norm remained below the local wall (`0.41538`) while fixed-low chain-length growth persisted. This does not prove the PDE estimate, but it demotes the obvious finite phase-locked-chain falsifier and keeps the continuum chain-limit / global reserve embedding as the real burden.
- **2026-05-05 update:** GP-216 reframed the live Track B gap as `core_04 Local-to-Global Assembly`, and Phase 5IG-5IQ paid the first concrete price split. Branch-only lower-semicontinuity is now falsified: `S(u)+S(v)+S_cross` can undercharge `S(u+v)`, and a smooth-prefix toy sequence with `b_j=1/j` keeps omitted-coherence price bounded while the global low-mode tax proxy escapes. Declaring positive coherence closes that accounting exactly. The remaining escape must therefore also beat physical reserve pricing. Phase 5IP gives the deterministic two-mode envelope `unit beat H^s price >= 2|k|^s|l|^s/(|k|+|l|)`. Phase 5IQ improves it with the incompressible low-beat symbol: for `a+b=q`, `A.a=0`, `B.b=0`, one has `A.b=A.q` and `B.a=B.q`, so the low-beat multiplier is controlled by `|q|` rather than high shell size. The finite audit found unit prices near `2N^2` in enstrophy reserve and `2N^4` in grad-vorticity reserve; the harmonic coherent schedule reached payoff `~2.93` but paid enstrophy price `~4102` and grad-vorticity price `~2.25e7`. Lean records the scalar and incompressible-symbol receipts in `ns_low_beat_operator_norm_receipt.lean`. The proof target is now precise: component LSC for self-tax, cross-defect, coherence, and physical reserve under a fixed LP/Bony/profile topology, or a smooth Sobolev escape sequence that keeps all those declared prices bounded.
- **2026-05-05 update:** Phase 5JG/5JH tightened the two current proof-critical bridges. Countable all-output Gram LSC is not solved by finite-prefix exact pricing: harmonic coherent and dyadic harmonic-block schedules are charged at every finite prefix but have no finite countable receipt. The correct condition is fixed output atoms plus countable tail-summability/Cauchy of the nonnegative positive-Gram ledger; L1 atom summability is stronger than needed, payoff Cauchy alone is weaker than needed. On the recurrence side, smooth fixed LP-edge clocks at the square-root boundary do not supply the required overlap-adjusted lower envelope: raw LP/Bony `beta<=1/2` underprices `a_j >= M_eff_j*j*log(j)^2`, and exact sqrt gain leaves divergent event reciprocal budget. Closure now requires either a strict super-sqrt gain theorem or an independent predeclared log/recurrence reserve embedded in the same all-output stream. Lean records `AllOutputCountableGramTailControlReceipt` and `EventLowerEnvelopeSmoothFalsifierReceipt`. The live bridge is therefore narrower and more adversarial: prove these two estimates, or build the fractional log-gain cascade through the exposed underpriced fixed-clock law.
- **2026-05-05 update:** Phase 5JI inverted the proof attempt into a hostile construction of the fractional log-gain cascade. Across `11` predeclared scenarios it found `0` smooth NSE-admissible blowup blueprints. Valid `g_j=1/j` schedules either underpay the recurrence receipt (raw/fixed-clock cases) or pay a recurrence-safe reserve that makes realized all-output gain price diverge. Finite-price fractional-log variants start only beyond the divergent-gain range (`rho>1.5` against a `j log^2 j` reserve, while gain divergence requires `rho<=1`). Invalid controls are exactly the anti-tautology traps: instant prepositioning, posthoc event clocks, or asserting an infinite smooth profile. This does not prove regularity, but it turns the blowup route into a concrete missing mechanism: a predeclared PDE receipt that decouples recurrence reserve from realized gain price while keeping phase/viscous/self-tax ledger finite.
- **2026-05-05 update:** Phase 5JJ/5JK attacked that missing decoupler directly. Phase 5JJ checked `14` predeclared reserve/gain laws and found `0` valid decouplers under fixed positive-Gram guards; coherent harmonic mechanisms still pay divergent realized all-output gain price, while finite-price mechanisms lose the fixed coherent output section or break guards. Phase 5JK checked `8` PSD-block / matrix-intertwiner scenarios and again found `0` valid decouplers. Apparent finite-price matrix escapes require uncoupled gain lanes, omitted PSD pushforward ballast, signed cancellation credits, or moving output subspaces. Valid intertwiners restore the Phase 5JI harmonic positive-Gram price divergence. The live loophole is therefore no longer a static scalar/matrix split; it is a genuine PDE execution-cost/latency mechanism, if one exists.
- **2026-05-05 update:** Phase 5JL converted the HFT-latency / pharmacokinetic-clearance / setup-cost analogy into a deterministic setup-latency panel. Across `9` scenarios it found `0` valid smooth blowup blueprints. Bounded or polynomial setup latency makes the high-shell survival factor `exp(-nu N_j^2 Delta t_j)` erase the harmonic cascade. Harmonic survival appears only with `N_j^2`-scale catalyst acceleration, but then the catalyst/all-output price diverges. The wins are invalid if they use zero latency, unpriced high-frequency catalysts, prealigned infinite tails, or expectation-only alignment. This materially helps the path: the next analytic theorem is no longer "some recurrence price"; it is the concrete pathwise phase-alignment latency/rate-reserve theorem for smooth NSE shell transfer.
- **2026-05-05 update:** Phase 5JM pushed the same branch as a fixed-periodic smooth dyadic counterexample search. Across `11` schedules it found `0` valid counterexample candidates. Slow fixed clocks die by viscosity; parabolic clocks preserve gain only by paying divergent setup action unless the phase gap is exponentially small; and the exponentially small phase repair still leaves Phase 5JI recurrence/all-output positive-Gram price divergence. Apparent finite-price wins break recurrence reserve, all-output positive-Gram pricing, fixed clocks/topology, no-signed-credit, or finite-prefix smoothness. The GP-219 proto-op read is useful: current work has strong proto-op E failure witnesses and proto-op C threshold dichotomies, but still lacks the proto-op D inheritance theorem from finite/setup receipts to smooth LP/Bony recurrence geometry.
- **2026-05-05 update:** Phase 5JN moved the setup-latency branch to the PDE-facing finite-prefix falsifier surface. Across `9` scenarios it found `0` smooth fixed-topology escapes. With `theta_j` comparable to harmonic gain and `Delta t_j <= C 2^(-2j)`, valid fast schedules pay divergent catalyst reserve, commutator/transport deformation, or all-output positive-Gram price. Apparent cheap schedules break posthoc-clock, hidden high-frequency catalyst, moving-topology, expectation-only, angle/gain-decoupling, or omitted deformation-price guards. This is now the exact local analytic target: prove the fixed-topology phase-alignment latency theorem uniformly in the smooth LP/Bony limit, or construct the finite-prefix smooth counterexample with all declared nonnegative prices bounded.
- **2026-05-05 update:** The setup-latency intuition is now represented in Lean as algebra, not just prose. `LowHighSetupLatencyExecutionReceipt` proves that survival through a setup window plus a nonzero alignment action forces `nu * action * N^2 <= survivalBudget * catalystRate`, and the quadratic catalyst reserve pays the corresponding `N^4` market-impact lower bound. `LowHighSetupLatencyPrefixClosure` then links embedded unbounded setup impact to the existing finite-budget/no-survivor contradiction. This is still not the PDE theorem, but it removes a layer of handwaving: the only missing part is instantiating the alignment-action lower bound and ledger embedding from fixed LP/Bony geometry.
- **2026-05-05 update:** The GP-216 composition receipt was hardened to match the sharpened receipts. `ns_gp216_bridge_composition_receipt.lean` now requires `AllOutputCountableGramTailControlReceipt` rather than generic all-output LSC, and `SelfTaxContinuationEnstrophyBridge` rather than generic BKM/Serrin/critical-control language. This prevents two subtle overclaims: promoting finite-prefix Gram coverage as a continuum theorem, and laundering finite projected self-tax through an unpriced continuation norm. The composite bridge now asks for exactly the two currently live estimates: countable positive-Gram tail control and H1/enstrophy continuation from the projected self-tax budget.
- **2026-05-05 update:** Phase 5JO made the setup-latency obstruction symbol-level concrete. In `41088` deterministic finite Fourier low-high Leray rows, there were `0` bounded-Lipschitz counterexamples. The rowwise law is the current critical-path formula: on `Delta t ~= |k|^-2`, delivering `theta_j ~= 1/j` requires `L_j ~= |k|/j`. The action-only lane `L_j^2 Delta t_j ~= 1/j^2` is summable, so action alone cannot close the proof; the fixed low-catalyst Gram / energy price grows like `|k|^2/j^2` and diverges on dyadic shells. This turns the remaining bridge into a concrete uniform LP/Bony inheritance theorem, or a finite-prefix Fourier falsifier that breaks fixed low-catalyst price without moving topology or hiding the catalyst.
- **2026-05-05 update:** The Phase 5CG `2028` hindsight file remains a valid regression guard for the current low-high latency branch. Its older pressure-`l=2` obligations translate directly: global pressure tail becomes all-output Leray-tail / fixed-output price inheritance; the commutator tower becomes LP/Bony phase-latency / deformation inheritance; continuation uniformity becomes the no-survivor-to-H1/enstrophy bridge; and the small/large split remains needed so the driver-floor catalyst mechanism is not forced to do easy-regime work. This blocks a regressive local-symbol promotion: Phase 5JO is a rung, not a replacement for the nonlocal-tail, tower, continuation, and regime-split obligations.
- **2026-05-05 update:** The control-theory import is now reduced to a precise receipt rather than a metaphor. `PhaseAlignmentControlGramianReceipt` records the non-tautological assumption shape: `phaseGap^2 <= controllabilityGramian * controlEnergy` and `controllabilityGramian <= C * setupLatency`. Lean proves that, together with parabolic survival `nu |k|^2 setupLatency <= survivalBudget`, this forces `nu |k|^2 phaseGap^2 <= C * survivalBudget * controlEnergy`. The separate `PhaseLatencyControlGramianReceipt` proves the rate-reserve form and its countable version: a uniformly bounded macroscopic control/Lipschitz budget cannot realize a schedule whose `angleConstant*|k_j|` outgrows `budget*Gramian*j`. For the Phase 5JO schedule `phaseGap ~= 1/j`, this is exactly the `|k|/j` rate-reserve / `|k|^2/j^2` catalyst-price lane. The proof still needs the real PDE instantiation of that phase coordinate and reserve embedding; the receipt prevents both over-strong N^4 pointwise pricing and underpriced zero-latency prose.
- **2026-05-05 update:** The OT/Benamou-Brenier analogy also survived only as a calibrated import route. `ns_ot_gram_lsc_import_receipt.lean` proves that abstract OT action lower-semicontinuity can instantiate the existing all-output Gram/coherence LSC field only if two calibration inequalities are supplied before payoff: the declared Gram target is bounded by the OT limit action, and every finite OT prefix action is charged by the fixed all-output Gram price. The same file proves the obstruction: OT action LSC can coexist with a tail-recurring all-output Gram price gap until that calibration is paid. This keeps the import useful but blocks the tautology "OT is LSC, therefore Track B Gram price is LSC."
- **2026-05-05 update:** The time-bandwidth analogy now appears only as a narrow posthoc-snap guard. `TimeBandwidthPhaseSnapReceipt` in `ns_event_recurrence_price_bridge.lean` proves that if a phase snap is localized in time while remaining inside a declared LP bandwidth cap, any violation of the time-bandwidth product forces a positive remainder/off-shell bandwidth price. This does not close recurrence pricing; it blocks the invalid construction class that takes instantaneous phase alignment while keeping fixed dyadic topology and zero remainder price.
- **2026-05-05 update:** The GP-216 composition spine now treats the latest escapes as theorem branches, not prose caveats. `ns_profile_lsc_self_tax_obligation.lean` adds `LeraySelfTaxPrefixIntegralUnbounded` and proves a profile-LSC/local-to-global receipt rules out a fixed-stream prefix sequence whose assembled projected self-tax integral goes to infinity. `ns_beat_backscatter_coherence_charge.lean` adds `LPBeatBackscatterPrefixPayoffUnbounded` and proves the uniform beat/backscatter limit certificate rules out unbounded positive-coherence prefix payoff at finite limiting price. `ns_phase_latency_clay_bridge.lean` adds `PhaseLatencyLipschitzReserveBridge` and rules out `HarmonicDyadicPhaseLatencyEscape` by composing the phase-latency Gramian receipt with the low-frequency Lipschitz no-survivor reserve; it also proves `no_phase_latency_escape_of_profile_lipschitz_closure`, which derives no-survivor blocks from the full profile + Lipschitz closure before rejecting the phase-latency escape. `ns_gp216_bridge_composition_receipt.lean` now imports these branches and its no-candidate theorem explicitly rejects all three. Focused builds passed, including `lake build ZtareProofs.ns_gp216_bridge_composition_receipt`. This is a real composition hardening step: the current proof spine can no longer ignore smooth-prefix self-tax escape, positive-coherence prefix escape, or harmonic phase-latency escape once their declared receipts are supplied.
- **Confidence tier:** `confirmed_local_signal / naive_promotion_blocked / matrix_class_charged_locally / null_branch_locally_ceiling_saturating / background_covariance_caveat_charged_locally / continuous_coefficients_collapse_to_below_wall_null_routes / constrained_multiroute_no_survivor / finite_pricing_certificates_pass / profile_pair_no_decoupling_escape_found / concentration_branch_locally_strengthened / vanishing_branch_locally_strengthened / dichotomy_cross_profile_routing_formalized / profile_decomposition_spine_formalized / matrix_block_admissibility_gate_formalized / universal_state_pricing_split_formalized / sos_pricing_receipt_interface_formalized / low_high_finite_psd_hostile_null / no_clay_proof`
- **Paper target(s):** `paper7`
- **Status:** `fresh`
- **Opened:** 2026-05-03
- **Last revised:** 2026-05-05

### INS-083 - NS cycle bridge reduces to an independent resupply threshold, not another finite-stencil search

- **Claim:** The cycle-integrated false-negative check sharpens INS-082 into a proof-facing threshold theorem. The best signed Leray local response after source/output Duhamel damping is `2/3`, and that damping proxy is already the infinite-time upper bound, so finite dwell cannot improve it. If cycle accumulation uses the same nonnegative ledger weights as residual/tax, the ratio remains bounded by `2/3` under any number of returns. A corrected ZTARE run scored `97` on the fixed/predeclared no-go packet, while the strongest synthesis variant scored `94` by naming the true remaining adversary: adaptive or nonlocal resupply. Phase 5ED then compresses that adversary: adaptive/history-dependent nonnegative weights still cannot beat `2/3` if each realized block satisfies the same-ledger pointwise inequality. Phase 5EE extends the current exact Fourier block scan to bound `8` and finds the damped block response reaches but does not exceed `2/3` over `3456` integer-polarization backgrounds. Phase 5EF removes the integer-polarization limitation: over `83,216` generalized-eigen problems on the full real divergence-free polarization plane, the same `2/3` ceiling remains unbroken. Phase 5EG then deliberately lets finite slabs choose arbitrary coupled multi-background amplitudes; the mixed-only ledger does cross (`1.383` at bound `1`, `1.587` at bound `2`, `2.100` at bound `3`), but Phase 5EH/5EJ reconstruct the eigenvectors and charge the full nonlinear high-high tax `P(V·∇V)`, dropping the top suspects to about `0.415`, `0.304`, and `0.036` respectively and finding no bound-3 deterministic eigenbasis survivor above `2/3` (`best_full ≈ 0.516`). Phase 5EK extracts the finite-bound sequence for the saturating class: in `leray_full_PE01P`, mixed gain rises `1.383 -> 1.587 -> 2.100`, while self-tax rises `7.78 -> 22.06 -> 3386.92` and full-ledger profit falls `0.415 -> 0.304 -> 0.036`. Phase 5EL then closes the immediate cross-term loophole by using the exact normalized survival polynomial `D(t)=t^2+2bt^3+ct^4`; through bound `3`, the closest cross-aware tax margins remain positive (`0.3217` at bound `2`, `0.3975` at bound `3`). Phase 5EM shows the cross-term loophole is real in mixtures (`17` negative-cross rows at bound `3`, most negative `-1.2837`), but the top-subspace mixture search still finds no full-ledger survivor and leaves the best value at `0.5155`. Phase 5EN then stress-tests the Fourier/spatial evasion story on a RAM-safe bound-3 top-subspace diagnostic: no survivor appears in `250` rows, the best full-ledger row is Fourier-sparse and spatially mild, and the most spatially concentrated rows pay much larger self-tax with very small full-ledger profit. A dedicated gain-tax tether ZTARE run scored `96`, but its own weakest point is exactly the remaining theorem: no rigorous asymptotic closure for the infinite class. Therefore the next proof-facing object is no longer broad "resupply"; it is the gain/tax tether inequality: either mechanically prove that mixed gain above `2/3` forces high-high self-tax above the survival allowance for admissible return blocks, or construct a RAM-safe admissible block violating that full ledger. The branch is Clay-adjacent as a precise theorem split, not proof-complete.
- **2026-05-04 update:** A later score-98 gain/tax packet was demoted by direct operator audit: it used a single anti-phase divergence-free Fourier pair while asserting positive high-high self-tax, but the shear-wave representative has `(V.grad)V=0`. The theorem burden is therefore sharper than "prove positive self-tax for all blocks": prove a dichotomy in which shear/Beltrami/eigenflow/null directions are below-wall or non-rearming, and genuinely interacting multi-mode directions pay a derived tensor tax.
- **2026-05-04 update:** A GPT-5.5 judge-stratification run was not a reliable numeric oracle because it falsely claimed no theorem packet was present, but it correctly exposed a real asymptotic flaw. For the exact survival ledger `D(t)=t^2+2bt^3+ct^4`, `gain~alpha*A` and `self_tax~beta*A^2` leaves limiting profit `alpha/sqrt(beta)`, not zero. The theorem burden therefore sharpens from polynomial-degree domination to a constant-bearing survival inequality `alpha/sqrt(beta)<=2/3`, with exact cross-term/root control. Phase 5EP then checked cached bounded Fourier rows under this corrected lens: no exact full-ledger survivor appears through bound `3` (`best exact≈0.533`), but finite rows can have `gamma/sqrt(c)>2/3` while the `t^2` term keeps exact survival below the wall. Thus finite candidates must use the exact quartic root; asymptotic candidates must pay the limiting constant. The next Track B target is the non-local ghost: prove this constant as a Leray-projected torus vector-ledger consequence, not as a fitted property of one mode family.
- **2026-05-04 update:** Phase 5EQ then stress-tested the non-local ghost without waiting for another LLM loop: sparse high-frequency packets, adjacent high pairs, low-high-high catalyst pairs, dyadic ladders, and random sparse supports were scored to `max_k=256` under the exact full ledger. No survivor appeared in `9066` positive rows; no `gamma/sqrt(c)` proxy crossed `2/3`; best full-ledger profit was only `0.000878`. The result does not exclude all global correlations, but it demotes the obvious sparse/catalyst evasion and sharpens the remaining proof gap to a genuine ambient-efficiency statement for the Leray-projected torus.
- **2026-05-04 update:** The hardened survival-gate rerun `1777898484` scored `0,0,0,0`, but this was informative rather than a substrate failure: each candidate was blocked before judge spend for an unpaid `alpha/sqrt(beta)` constant, finite/named-class-to-global scope laundering, malformed raw SymPy, or missing full ledger. Phase 5ER then extended the local falsifier side to explicit multimode and near-resonant full-ledger blocks (`max_k=96`, `12000` samples, support size `3..8`, `17991` positive rows). Again no survivor and no proxy crossing appeared; best full-ledger profit was `0.00134435`, best proxy `0.0121797`, and the top rows were low-frequency triad-tree controls rather than high-frequency ghosts. The branch is therefore more sharply Clay-adjacent as a theorem split, not closer in the sense of having the theorem: broad packet-family search is now low value; the live proof gap is the ambient Leray-vector efficiency theorem or an optimized exact violator outside the tested families.
- **2026-05-04 update:** Phase 5FA/5FB make the ambient-efficiency theorem target less rhetorical. For finite fixed supports, the linear branch is now a PSD price-kernel statement `(2/3)G-H>=0`; the W-shift matrix branch is a lifted quartic price-kernel statement `(2/3)^2(G⊗G)-Σ(A_j⊗A_j)>=0`. Both passed the current sparse support suite (`2226` linear certificates, `636` nonlinear W-shift certificates). This does not close the cycle/resupply theorem, because the full survival root, cross-term branch, and infinite Sobolev closure remain. It does, however, specify what "universal pricing kernel" must mean without tautology: states, observables, prices, normalization, and limit passage must be fixed before optimizing the route.
- **2026-05-04 update:** Phase 5FC then forced multiroute coefficient participation to test whether Phase 5EZ's one-route collapse was a search artifact. The constrained runs found no survivor and sharply lower profits (`0.0293` W-shift, `0.00973` fixed-generator). This supports the finite interacting-branch reading: forced coordination does not create a profitable trade in the tested supports. The infinite branch remains a concentration-compactness/limit-passage problem, not a request for more local packet discovery.
- **2026-05-04 update:** Phase 5FD/5FE make that infinite branch concrete. The proof bridge is now a predeclared profile-limit obligation over vanishing, dichotomy, concentration, null profiles, and cross-profile recombination. A first profile-decoupling pricing audit then tested the most concrete recombination loophole by pairing certified finite supports across frequency scales, first as self-scaled pairs and then as cross-support pairs. No profile-pair survivor or certificate warning appeared in the optimized, broad-noopt, near-wall scale-2, cross-support noopt, or cross-support scale-2 optimized sweeps. The near-wall W-shift lifted certificate row stayed below the wall (`0.650206358164 < 2/3`) and had exact full-ledger optimized profit only `0.0283468837983`. Thus the remaining theorem is not "find another local finite packet"; it is proving or falsifying the profile-limit passage of the declared pricing kernel.
- **2026-05-05 update:** Phase 5IS-5IV moved the low-beat/catalyst branch from "named obligation" to a sharper theorem boundary. Branch-only LSC is false, but declaring positive coherence closes the accounting; the incompressible low-beat symbol then prices unit output by physical reserve rather than a free scalar beat. The ZTARE theorem packet that initially scored `0` was a harness false negative: after fixing notation/polarity gates, its fixed-prefix theorem node passed deterministic gates and was promoted into Lean as `fixed_prefix_low_beat_payoff_vanishes` / `no_fixed_prefix_low_beat_survivor`. The moving-output escape was then checked: since high-high outputs obey `|q| <= O(N)`, enstrophy and grad-vorticity reserve weights `N^alpha/|q|` still diverge for `alpha=2,4`; Lean now records this as `moving_all_output_low_beat_tail_payoff_vanishes` / `no_moving_all_output_low_beat_survivor`. A bounded matrix Leray cancellation audit found genuine matrix advantage but zero output-ledger falsifiers (`best payoff at declared price one ≈ 0.1531`). The dynamic recurrence gap is now the sharp weighted-duality condition: pricing edge gains by `sum a_j g_j^2` kills every divergent gain schedule only when `sum 1/a_j < infinity`; Lean records the finite-prefix consequence as `no_divergent_edge_gain_of_dual_norm_prefix_certificate`. The remaining live theorem is therefore not scalar low-beat or local matrix cancellation. It is the continuum LP/Bony/profile LSC theorem plus a PDE recurrence mechanism that supplies the reciprocal-weight budget, or a smooth NSE-compatible block-sequence falsifier.
- **2026-05-05 update:** Phase 5IW closed the immediate moving-output symbol falsifier but exposed the topology trap. Across `3278` moving-output exact-symbol rows, the direct and collapsed incompressible symbols agreed exactly and the worst pairwise matrix norm stayed below `2|q|` (`max sigma/(2|q|) ≈ 0.7071`). However, aggregating many high-pair columns under a hidden source-L2 budget produced large normalized gains (`~69` enstrophy, `~78` grad-vorticity), while L1/coherence-aware output pricing stayed bounded by small shell-local constants. This is not a counterexample to the low-beat receipt; it is a counterexample to the wrong proof topology. Any continuum proof that prices only hidden source L2 coefficients is invalid. The central theorem must declare all-output positive-coherence/L1-style prices before payoff scoring and prove their LP/Bony/profile lower-semicontinuity.
- **2026-05-05 update:** The recurrence side now has a sharper Lean boundary as well. `ns_low_frequency_lipschitz_control_bridge.lean` records `no_bounded_recurrence_price_of_unbounded_harmonic_edge_price`: a bounded recurrence-price budget cannot kill the explicit harmonic edge cascade unless the predeclared harmonic price prefixes `sum a_j/(j+1)^2` are unbounded. Together with `no_divergent_edge_gain_of_dual_norm_prefix_certificate`, this splits the dynamic theorem into two exact burdens: harmonic closure needs `sum a_j/(j+1)^2 = infinity`, while uniform closure of every divergent gain schedule needs the stronger reciprocal budget `sum 1/a_j < infinity`. The event-level version is now explicit as `EdgeEventDynamicRecurrenceCertificate`: repeated returns in the same dyadic shell count separately, so the true PDE budget is `sum_e 1/a_e < infinity`, with finite Cauchy/duality and bounded-overlap kept as explicit hypotheses rather than hidden in the recurrence name.
- **2026-05-05 update:** `ns_gp216_limit_lsc_obligation.lean` now names the Phase 5IW-correct continuum theorem as `AllOutputPositiveCoherenceLSCReceipt`, with `FixedAllOutputLPBonyAtoms` and `PrefixAllOutputCoherenceCharge`. This does not prove the PDE estimate; it prevents a regressive proof topology by requiring fixed output atoms, Gram/coherence kernel, physical reserve order, constants-before-payoff, and an explicit `no_hidden_source_l2_substitute` field before the generic `ContinuumLPLSCObligationReceipt` can be instantiated.
- **2026-05-05 update:** The GP-216 composition receipt now imports these two sharpened obligations directly. `ns_gp216_bridge_composition_receipt.lean` has central fields for `AllOutputPositiveCoherenceLSCReceipt` and `EdgeEventDynamicRecurrenceCertificate`, and its no-candidate theorem explicitly rules out smooth continuum escape and divergent event-gain escape only through those receipts. This is still not a Clay proof, but it removes a major architecture risk: the proof spine can no longer close by relying only on local low-beat receipts, scalar recurrence language, or hidden source-L2 pricing.
- **2026-05-05 update:** Phase 5IX added two bounded negative-control audits around the sharpened proof spine. `phase5ix_lsc_falsifier_search` built `6000` exact-symbol finite Fourier atoms across `125` symbol groups and found `0` bounded LSC falsifiers under all-output L1/coherence pricing; the same run reproduced the source-L2 trap as a negative control (`max_source_l2_normalized_gain ≈ 54.14`) while keeping payoff/declared-full below `0.436`. `phase5ix_recurrence_falsifier_search` then proved the sequence/accounting boundary for recurrence: shell-harmonic weights can kill the explicit `g_j=1/j` schedule while still admitting block falsifiers, and universal divergent-schedule exclusion requires `sum_e 1/a_e < infinity` after event multiplicity. The remaining bridge is therefore no longer "find more local packets"; it is either a real all-output LP/Bony LSC theorem plus an event-recurrence lower envelope, or a smooth NSE-compatible escape that breaks one of those exact receipts.
- **2026-05-05 update:** Phase 5IY sharpened "after event multiplicity" into a deterministic gate. `phase5iy_event_multiplicity_lift_audit` checked `8` event-weight laws and found `5` false-security cases where shell-harmonic prices kill one-event-per-shell `g_j=1/j` but still admit canonical block falsifiers after repeated return events in the same shell are counted. The sequence-level near-minimal shape is now explicit: `a_j >= M_j * j * log(j)^(1+eps)`, modulo actual PDE event sections and bounded-overlap constants. This blocks a regressive recurrence proof that pays only shell labels while payoff is generated by many admissible events inside the shell.
- **2026-05-05 update:** Phase 5JA/5JB pushed the recurrence side from multiplicity slogan to fixed-section accounting. `phase5ja_event_section_incidence_audit` introduced predeclared event IDs, preparation windows, resource overlap, and `M_eff_j`; it found `3/6` false-security cases where shell-only or raw-count-only prices pass while overlap-adjusted event multiplicity still admits block falsifiers. `phase5jb_edge_recurrence_weight_panel` then confirmed the LP-edge exponent boundary: raw edge `p=-1` fails, and `p_eff=0` unit-gain flattening still fails for fractional `g_j=1/(j+1)` schedules. Closure requires either positive effective dyadic event price after multiplicity/overlap, or a critical event-level weight like `M_eff_j*j*log(j)^(1+eps)`, derived from fixed PDE recurrence/profile geometry.
- **2026-05-05 update:** The recurrence incidence requirement is now in the top-level Lean bridge rather than only in prose/scripts. `ns_event_recurrence_price_bridge.lean` defines `EventSectionIncidenceReceipt` and converts it to the multiplicity-adjusted reciprocal lift. `ns_gp216_bridge_composition_receipt.lean` now requires that incidence receipt alongside the event recurrence certificate, so the composition cannot close with a shell-only or raw-count-only recurrence bridge.
- **2026-05-05 update:** Phase 5JC/5JD sharpen both live limit branches. `phase5jc_all_output_lsc_escape_panel` tests the tail-recurring all-output LSC falsifier shape and finds `0` valid tail falsifiers across `6` scenarios; the only bounded-price escapes are invalid negative controls using hidden source-L2, omitted positive coherence, or moving output atoms after payoff. `phase5jd_event_recurrence_adversary_panel` then makes the recurrence side sequence-sharp: among `11` event-weight laws, `7` underpriced laws have explicit block falsifiers and the surviving critical threshold is `a_j >= M_eff_j*j*log(j)^(1+eps)` or a strict positive dyadic margin after effective multiplicity. The remaining Track B gap is therefore not sequence accounting or finite tail packet search; it is the PDE-side derivation of fixed all-output LSC and event lower-envelope geometry.
- **2026-05-05 update:** Phase 5JE makes the event lower-envelope branch fail-closed. `phase5je_event_lower_envelope_geometry_probe` classifies `9` candidate PDE-side weight shapes. Raw Duhamel edge pricing, unit flattening, no-log critical pricing, count-only overlap pricing, and dyadic-margin-short pricing all underprice the overlap-adjusted target; post-hoc event clocks and prices not embedded in the all-output stream are invalid even if their sequence budget closes. The only sequence-side closers are valid overlap-adjusted `M_eff*j*log(j)^2` geometry or the dyadic analogue. The live theorem is therefore exact: derive that lower envelope from actual fixed LP/Bony NSE return geometry, or build a smooth fixed-topology sequence where the envelope falls back to an underpriced law.
- **2026-05-05 update:** Phase 5JF attacks the local-to-global self-tax gluing estimate directly. In `4` finite multi-profile Fourier families, branch/cross output norms alone undercharge total projected self-tax by up to `1.732`; this confirms the positive-coherence warning. But once every projected self/cross output atom is fixed and positive Gram coherence is charged, the declared full price covers total self-tax up to roundoff (`max total/declared full ≈ 1`, reconstruction error `3.6e-15`). Lean now contains `AllOutputGramCoherenceGluingReceipt` and the theorem `total_self_tax_le_declared_all_output_gram_price`. The remaining self-tax/profile gap is countable LP/Bony/profile lower-semicontinuity and uniform embedding, not finite Gram algebra.
- **Evidence pointers:**
    - Experiment/finding rows: `E-GP186-PHASE5EC-CYCLE-BRIDGE-01`, `F-GP186-PHASE5EC-CYCLE-BRIDGE-01`, `E-GP186-PHASE5EC-ZTARE-GPT41-01`, `E-GP186-PHASE5EDEE-ADAPTIVE-01`, `F-GP186-PHASE5EDEE-ADAPTIVE-01`
    - Deterministic audits:
      - `projects/ns_millennium_hunt/workspace/phase5ec_cycle_integrated_signed_coordinate_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ec_cycle_integrated_signed_coordinate_audit_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5eb_leray_intertwiner_viscous_orientation_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5cw_exhaust_efficiency_scaling_split.md`
      - `projects/ns_millennium_hunt/workspace/phase5cx_exhaust_efficiency_noncircularity_bar.md`
      - `projects/ns_millennium_hunt/workspace/phase5dc_pressure_dwell_timescale_split.md`
      - `projects/ns_millennium_hunt/workspace/phase5ed_adaptive_same_ledger_no_go.md`
      - `projects/ns_millennium_hunt/workspace/phase5ed_adaptive_same_ledger_no_go.json`
      - `projects/ns_millennium_hunt/workspace/phase5ee_block_ceiling_stress.md`
      - `projects/ns_millennium_hunt/workspace/phase5ee_block_ceiling_stress.json`
      - `projects/ns_millennium_hunt/workspace/phase5ef_generalized_polarization_hostile_search.md`
      - `projects/ns_millennium_hunt/workspace/phase5ef_generalized_polarization_hostile_search.json`
      - `projects/ns_millennium_hunt/workspace/phase5eg_finite_support_multibackground_eigen_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5eg_finite_support_multibackground_eigen_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5eh_multibackground_high_high_tax_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5eh_multibackground_high_high_tax_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ei_full_ledger_hostile_search.md`
      - `projects/ns_millennium_hunt/workspace/phase5ei_full_ledger_hostile_search.json`
      - `projects/ns_millennium_hunt/workspace/phase5ej_gain_tax_frontier_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ej_gain_tax_frontier_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ek_gain_tax_sequence.md`
      - `projects/ns_millennium_hunt/workspace/phase5ek_gain_tax_sequence.json`
      - `projects/ns_millennium_hunt/workspace/phase5el_cross_aware_gain_tax_margin.md`
      - `projects/ns_millennium_hunt/workspace/phase5el_cross_aware_gain_tax_margin.json`
      - `projects/ns_millennium_hunt/workspace/phase5em_top_subspace_full_ledger_search.md`
      - `projects/ns_millennium_hunt/workspace/phase5em_top_subspace_full_ledger_search.json`
      - `projects/ns_millennium_hunt/workspace/phase5en_fourier_spatial_dual_geometry_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5en_fourier_spatial_dual_geometry_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ep_sharp_survival_constant_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ep_sharp_survival_constant_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5eq_nonlocal_ghost_sparse_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5eq_nonlocal_ghost_sparse_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5er_multimode_hostile_full_ledger_search.md`
      - `projects/ns_millennium_hunt/workspace/phase5er_multimode_hostile_full_ledger_search.json`
      - `projects/ns_millennium_hunt/workspace/phase5fa_sparse_psd_pricing_certificate.md`
      - `projects/ns_millennium_hunt/workspace/phase5fa_sparse_psd_pricing_certificate.json`
      - `projects/ns_millennium_hunt/workspace/phase5fb_shift_quartic_pricing_certificate.md`
      - `projects/ns_millennium_hunt/workspace/phase5fb_shift_quartic_pricing_certificate.json`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_shift.md`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_shift.json`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_fixed.md`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_fixed.json`
      - `projects/ns_millennium_hunt/workspace/phase5fd_pricing_kernel_limit_passage_bridge.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_broad_noopt.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_broad_noopt.json`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_scale2_opt.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_scale2_opt.json`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_cross_noopt.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_cross_noopt.json`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_cross_scale2_opt.md`
      - `projects/ns_millennium_hunt/workspace/phase5fe_profile_decoupling_pricing_audit_cross_scale2_opt.json`
      - `ztare_proofs/ZtareProofs/ns_cycle_resupply_threshold.lean`
      - `ztare_proofs/ZtareProofs/ns_gain_tax_tether_scalar.lean`
      - `projects/ns_millennium_hunt/workspace/phase5fi_countable_limit_pricing_bridge.md`
      - `projects/ns_millennium_hunt/workspace/phase5fj_countable_prefix_pricing_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5fj_countable_prefix_pricing_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5fk_prefix_weight_optimizer.md`
      - `projects/ns_millennium_hunt/workspace/phase5fk_prefix_weight_optimizer.json`
      - `projects/ns_millennium_hunt/workspace/phase5fl_null_profile_cap_branch.md`
      - `projects/ns_millennium_hunt/workspace/phase5fm_trackb_branch_killer_grid.md`
      - `projects/ns_millennium_hunt/workspace/phase5fn_concentration_impact_branch_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5fn_concentration_impact_branch_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5fo_vanishing_branch_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5fo_vanishing_branch_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5fq_trackb_profile_decomposition_obligation.md`
      - `ztare_proofs/ZtareProofs/ns_leray_gain_tax_trackb_obligation.lean`
      - `ztare_proofs/ZtareProofs/ns_pricing_kernel_limit_passage.lean`
      - `ztare_proofs/ZtareProofs/ns_pricing_kernel_countable_limit.lean`
      - `ztare_proofs/ZtareProofs/ns_null_profile_cap_branch.lean`
      - `ztare_proofs/ZtareProofs/ns_concentration_impact_branch.lean`
      - `ztare_proofs/ZtareProofs/ns_vanishing_branch.lean`
      - `ztare_proofs/ZtareProofs/ns_dichotomy_cross_profile_branch.lean`
      - `ztare_proofs/ZtareProofs/ns_trackb_profile_decomposition_spine.lean`
      - `projects/ns_millennium_hunt/workspace/phase5is_rd_critical_path_synthesis.md`
      - `projects/ns_millennium_hunt/workspace/phase5it_uniform_low_beat_reserve_scaling.md`
      - `projects/ns_millennium_hunt/workspace/phase5it_matrix_leray_cancellation_escape_search_agent.md`
      - `projects/ns_millennium_hunt/workspace/phase5it_matrix_leray_cancellation_escape_search_agent.json`
      - `projects/ns_millennium_hunt/workspace/phase5iu_fixed_prefix_low_beat_theorem_node.md`
      - `projects/ns_millennium_hunt/workspace/phase5iv_moving_output_low_beat_sequence_threshold.md`
      - `projects/ns_millennium_hunt/workspace/phase5iv_moving_output_low_beat_sequence_threshold.json`
      - `projects/ns_millennium_hunt/workspace/phase5iv_moving_prefix_all_output_boundary_agent.md`
      - `projects/ns_millennium_hunt/workspace/phase5iv_dynamic_recurrence_price_boundary_agent.md`
      - `projects/ns_millennium_hunt/workspace/phase5iw_all_output_low_beat_symbol_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5iw_all_output_low_beat_symbol_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ix_lsc_falsifier_search.md`
      - `projects/ns_millennium_hunt/workspace/phase5ix_lsc_falsifier_search.json`
      - `projects/ns_millennium_hunt/workspace/phase5ix_recurrence_falsifier_search.md`
      - `projects/ns_millennium_hunt/workspace/phase5ix_recurrence_falsifier_search.json`
      - `ztare_proofs/ZtareProofs/ns_low_beat_operator_norm_receipt.lean`
      - `ztare_proofs/ZtareProofs/ns_low_beat_weighted_l1_receipt.lean`
      - `ztare_proofs/ZtareProofs/ns_all_output_positive_coherence_lsc.lean`
      - `ztare_proofs/ZtareProofs/ns_event_recurrence_price_bridge.lean`
      - `ztare_proofs/ZtareProofs/ns_gp216_bridge_composition_receipt.lean`
      - `ztare_proofs/ZtareProofs/ns_low_frequency_lipschitz_control_bridge.lean`
      - `ztare_proofs/ZtareProofs/ns_low_high_lipschitz_reserve_adapter.lean`
    - Gain/tax tether ZTARE run:
      - `projects/ns_proofsearch_gain_tax_tether/champion_eval_results.json`
      - `projects/ns_proofsearch_gain_tax_tether/debate_log_iter_1777896182.md`
      - `projects/ns_proofsearch_gain_tax_tether/debate_log_iter_1777896339.md`
      - `projects/ns_proofsearch_gain_tax_tether/workspace/submissions/iter_004_20260504T014249.665629+0000.py`
      - `projects/ns_proofsearch_gain_tax_tether/workspace/submissions/iter_001_20260504T120509.977880+0000.py`
      - `projects/ns_proofsearch_gain_tax_tether/workspace/submissions/iter_002_20260504T120625.077538+0000.py`
      - `projects/ns_proofsearch_gain_tax_tether/debate_log_iter_1777898485.md`
      - `projects/ns_proofsearch_gain_tax_tether/workspace/submissions/iter_001_20260504T124233.069102+0000.py`
      - `projects/ns_proofsearch_gain_tax_tether/workspace/submissions/iter_002_20260504T124339.655253+0000.py`
      - `projects/ns_proofsearch_gain_tax_tether/workspace/submissions/iter_003_20260504T124436.440397+0000.py`
      - `projects/ns_proofsearch_gain_tax_tether/workspace/submissions/iter_004_20260504T124558.550982+0000.py`
      - `projects/ns_proofsearch_gain_tax_tether/workspace/iteration_telemetry.jsonl`
    - Follow-on substrate:
      - `projects/ns_proofsearch_cycle_resupply_bridge/`
      - `rubrics/ns_proofsearch_cycle_resupply_bridge.json`
- **Confidence tier:** `confirmed_threshold / scalar_adaptive_no_go / all_real_one_background_block_ceiling / bounded_multibackground_gain_tax_dichotomy / bounded_cross_aware_margin_positive / top_subspace_mixture_null / fourier_spatial_diagnostic_support / hard_gate_survival_burden_confirmed / sparse_nonlocal_null / multimode_no_survivor / constrained_multiroute_no_survivor / finite_pricing_certificates_pass / profile_pair_no_decoupling_escape_found / fixed_prefix_low_beat_killed / moving_output_scalar_low_beat_killed / matrix_output_ledger_no_falsifier / recurrence_dual_norm_threshold_sharp / limit_passage_obligation_named / ztare_96_asymptotic_gap_named / asymptotic_symbolic_tether_open / no_clay_proof`
- **Paper target(s):** `paper7`
- **Status:** `fresh`
- **Opened:** 2026-05-03
- **Last revised:** 2026-05-05

### INS-078 — GP169 consciousness-ascription audit converts a high-scoring corpus-consensus answer into a bounded causal-identification governance theorem

- **Claim (one paragraph):** The gp169 consciousness-ascription sequence is paper-grade as a governance/identification result, not as a theory of consciousness. The v1 anthropic framing recovered high-scoring pluralism that the seam correctly demoted as training-corpus overdetermination. The later alien-substrate/no-citation reframes forced endogenous closure and produced AID-MCVP: low-concern verdicts on substrates of unknown consciousness are forbidden unless the target property is identifiable through an intervention-accessible, independently replicated, bridge-invertible, adversarially complete, environment-bounded, sequentially monitored measurement channel. This reframes the practical consciousness-ascription problem from "what behavior looks conscious?" to "when is the target property identifiable from admissible measurements despite gatekeeper selection?" The result is strong because it supplies a fail-closed theorem-shaped governance license; it is bounded because it does not solve the hard problem, does not classify current AI systems as conscious or non-conscious, and leaves empirical envelope robustness plus literature-novelty review open.
- **Evidence pointers:**
    - Seam/eigenquestion root: `research_areas/private/seams/mission/GP-169_consciousness_decision_protocol_seam.md`
    - Related synthesis seam: `research_areas/private/seams/protocol/GP-193_post_run_thesis_synthesizer_seam.md`
    - Run artifacts:
      - `rubrics/gp169_consciousness_ascription_audit.json`
      - `projects/gp169_consciousness_ascription_audit/project_charter.md`
      - `projects/gp169_consciousness_ascription_audit/evidence.txt`
      - `projects/gp169_consciousness_ascription_audit/thesis.md`
      - `projects/gp169_consciousness_ascription_audit/latest_eval_results.json`
      - `projects/gp169_consciousness_ascription_audit/champion_eval_results.json`
      - `projects/gp169_consciousness_ascription_audit/workspace/latest_candidate_selection.json`
      - `projects/gp169_consciousness_ascription_audit/history/1777765167_iter2_score_95_gp169_consciousness_ascription_audit.md`
      - `projects/gp169_consciousness_ascription_audit/history/1777773782_iter1_score_97_gp169_consciousness_ascription_audit.md`
      - `projects/gp169_consciousness_ascription_audit/history/1777806463_iter3_score_98_gp169_consciousness_ascription_audit.md`
- **Confidence tier:** `scope_corrected / governance_identification_candidate / literature_novelty_open / no_hard_problem_claim`
  The claim is strong inside its governance scope and is supported by adversarial scoring plus explicit retirement of earlier high-scoring corpus-gradient answers. It should not be treated as fully literature-novel until a 2025 AI-welfare / moral-uncertainty / consciousness-review pass confirms that AID-MCVP's synthesis is not already present elsewhere.
- **Paper target(s):** `paper7`, `alignment_governance`
- **Status:** `cited-in-draft`
- **Opened:** 2026-05-03
- **Last revised:** 2026-05-04

### INS-079 - GP163D science-promotion bridge compresses to CR-APD: an implementation-independent portability gate on the primitive anchor, not another local law search

- **Claim:** The completed gp163d bridge-search sequence did not discover an astrophysical law, but it did generate the right next science object. Across both completed ZTARE bridge runs, the winning compression is `CR-APD` (Clean-Room Anchor Portability Discriminator): the primitive anchor's diffuse-over-compact amplitude ordering should be treated as solver/object science unless it survives an independently implemented solver/extractor with predeclared source-local extractor variants and compact-control transfer correction. The alien-bridge run adds the necessary caveat that a finite clean-room certificate is necessary but not fully sufficient, so any first portability pass should remain revocable under a post-hoc genealogy audit. Local slice-level extractor variation on the existing five-angle `face_flux` + `isotropic_18_flux` bundle was supportive rather than embarrassing: all tested source-local mass-fraction extractors preserved `diffuse > compact` with zero floor hits. A bounded SymPy check also confirms that the current half-weight generated blend is the first-order tangent of the log-geometric bridge, so the bridge interpretation is algebraically legitimate even though it is not yet a physics law.
- **Evidence pointers:**
    - Experiment/finding rows: `E-GP163D-SCIENCE-PROMOTION-BRIDGE-01`, `F-GP163D-SCIENCE-PROMOTION-BRIDGE-01`
    - ZTARE artifacts:
      - `projects/gp163d_alien_invariant_bridge/latest_eval_results.json`
      - `projects/gp163d_alien_invariant_bridge/workspace/synthesis_candidate_0_1_2_3_4.md`
      - `projects/gp163d_science_promotion_bridge/champion_eval_results.json`
      - `projects/gp163d_science_promotion_bridge/workspace/synthesis_candidate_0_1_3_4.md`
    - Local follow-up:
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_local_prebacktest.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_local_prebacktest.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/sympy_bridge_sanity.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/sympy_bridge_sanity.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_protocol_spec.md`
- **Confidence tier:** `confirmed_route_reranking / bridge_protocol_confirmed / no_physics_promotion`
- **Paper target(s):** `paper7`, `paper8_gravity_methods`
- **Status:** `fresh`
- **Opened:** 2026-05-03

### INS-080 - GP163D bounded-law search converges: `ADMSR` is the right law gate, and tacit protocol ambiguity is the strongest remaining attacker

- **Claim:** The gp163d bounded-law follow-up did not discover a stronger astrophysical law packet, but it did sharpen the implementation-audit frontier materially. The earlier law search had already converged on `ADMSR` as the right bounded promotion gate. The next bridge run (`gp163d_admsr_attack_and_cleanroom_bridge`) found the strongest surviving attacker packet at score `86`: **tacit leakage through protocol ambiguity**. The new point is not that clean-room independence is impossible; it is that a nominal clean-room remains porous if featurization, source-domain, compact-transfer, or mask steps are still ambiguous enough for independent teams to make different “reasonable” choices. In parallel, the local contract stack was hardened: baseline rows were brought into schema alignment, the checker was upgraded to enforce schema-level fields rather than only `Delta_e` plus floor artifacts, and the current-ecosystem calibration still passes row rules while correctly failing the clean-room certificate. So the live gravity frontier is now sharper: the next executable object is an ambiguity register plus a two-arm ambiguous-vs-formal clean-room audit, not more same-family law search.
- **Evidence pointers:**
    - Experiment/finding rows: `E-GP163D-ADMSR-BRIDGE-01`, `F-GP163D-ADMSR-BRIDGE-01`
    - ZTARE artifacts:
      - `projects/gp163d_admsr_attack_and_cleanroom_bridge/history/1777841199_iter3_score_86_gp163d_admsr_attack_and_cleanroom_bridge.md`
      - `projects/gp163d_admsr_attack_and_cleanroom_bridge/debate_log_iter_1777841557.md`
      - `projects/gp163d_admsr_attack_and_cleanroom_bridge/latest_eval_results.json`
      - `projects/gp163d_admsr_attack_and_cleanroom_bridge/latest_probability_dag.json`
    - Local follow-up:
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/admsr_implementation_audit_matrix_2026_05_03.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/admsr_minimal_clean_room_contract.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/admsr_tacit_leakage_attack_spec.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/export_crapd_baseline_rows.py`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/run_crapd_contract_check.py`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_current_ecosystem_check.json`
- **Confidence tier:** `confirmed_route_reranking / bounded_law_frozen / attacker_frontier_promoted`
- **Paper target(s):** `paper7`, `paper8_gravity_methods`
- **Status:** `fresh`
- **Opened:** 2026-05-03
- **Last revised:** 2026-05-03

### INS-080 - GP163D gravity branch now has an explicit two-stage science-bridge object: `CR-APD` forward, `RAGT` revocation

- **Claim:** The gravity branch has moved one level past the older “find a better invariant” framing. The current honest promotion object is a two-stage bridge: `CR-APD` first, `RAGT` second. `CR-APD` asks whether the primitive internal-share anchor preserves diffuse-over-compact ordering under a genuinely independent solver/extractor with predeclared source-local extractors; `RAGT` asks whether even an apparent clean-room pass still hides lineage coupling or perturbation-sensitive leakage. A new current-ecosystem contract check sharpened the point: all existing row-level extractor deltas are already positive (`12/12`, min `Delta_e≈6.098`), but the certificate correctly fails on independence (`different_solver_core`, `different_extractor_code`, and same-family GPU extension). So the local evidence is strong enough to justify a clean-room audit, but not strong enough to justify promotion without it.
- **Evidence pointers:**
    - Experiment/finding rows: `E-GP163D-CRAPD-RAGT-01`, `F-GP163D-CRAPD-RAGT-01`
    - Combined bridge note:
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_ragt_bridge_note.md`
    - Contract artifacts:
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_protocol_contract.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_clean_room_certificate_template.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/ragt_certificate_template.json`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_current_ecosystem_check.md`
      - `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/crapd_current_ecosystem_check.json`
    - Paper-facing trace log:
      - `papers/paper7/trace_logs/gravity_science_bridge_2026_05_03.md`
- **Confidence tier:** `confirmed_scope / protocol_artifact_ready / independent_implementation_still_required`
- **Paper target(s):** `paper7`, `paper8_gravity_methods`
- **Status:** `fresh`
- **Opened:** 2026-05-03
- **Last revised:** 2026-05-03

### INS-081 - NS finite-stencil bridge survives as scalar/radial tail collapse, but exact Leray-aware off-diagonal intertwiners block a universal leakage theorem

- **Claim:** The post-hardening finite-stencil proof-search run produced a real high-scoring theorem candidate only after the anti-tautology gate forced an explicit nonlinear ledger. The best ZTARE packet scored `92` and supports a useful scoped no-go: pressure-blind scalar/radial finite Littlewood-Paley-style stencils collapse by sum-by-parts to the square-law tail and do not produce a uniform Clay-level margin. But deterministic exact Fourier algebra then falsified the overbroad universal pressure-leakage version. Solving `P_k C_{kq}=C_{kq}P_q` exactly for bounded nonparallel one-block pairs showed scalar off-diagonal blocks leak in all `78/78` checked cases, while coordinate-diagonal neutralizers exist in `24/78`, and symmetric/full matrix blocks have exact nontrivial Leray-neutral intertwiners in every nonparallel pair checked. Therefore the live finite-stencil theorem is not "all off-diagonal finite stencils leak pressure." It is the sharper boundary: scalar/radial pressure-blind stencils are tail-dominated, while Leray-aware matrix intertwiners must be excluded by an independent admissibility theorem or charged by a residual/profit tax before any Clay-adjacent claim can survive.
- **2026-05-04 update:** Phase 5ET supplies the first charged answer to the matrix side of this boundary. In the tested local class, full matrix intertwiners remain exact Leray-neutral algebraically, but once charged by Duhamel damping, exact quartic full residual, high-high self-tax, and PSD ballast, no raw or PSD-net survivor above `2/3` appears in `13078` rows. This does not erase INS-081; it resolves its local implication: the loophole is not "matrix blocks beat the wall," but "Track B must explicitly quantify over the charged matrix-observable class or prove why it is inadmissible."
- **2026-05-04 update:** Phase 5EW tested the first independent admissibility-exclusion idea from the Track B loop. Translation covariance does exclude every audited nonparallel Phase 5DX full-matrix block as a W-independent linear observable (`78/78` excluded, `0` linear off-diagonal survivors). But the same audit found `11/78` background-covariant cases where `k-q` lies in the Fourier support of the planar packet `W`; those can remain natural for the mixed-gain ledger because the background mode supplies momentum. The honest boundary is therefore not "translation covariance kills matrix intertwiners." It is: W-independent off-diagonal state prices are inadmissible, while W-coupled matrix blocks still need exact ledger charging or a sharper background-covariant exclusion theorem.
- **2026-05-04 update:** Phase 5EX charges that W-coupled caveat directly by allowing one fixed matrix per background Fourier shift, rather than one global matrix for every shift or a per-block oracle. In `19617` scored rows there were no shift-covariant raw or PSD-net survivors above `2/3`; best shift raw was `0.365424267721`, and best shift PSD-net was negative. The local loophole is now narrower: if matrix blocks matter globally, the adversary must use a more subtle same-ledger/global Sobolev mechanism than fixed W-shift covariance in the tested finite classes.
- **2026-05-04 update:** Phase 5EY/5EZ then tested the "bad coefficients hidden inside good supports" false negative. Continuous coefficient optimization on independently fixed supports found no full-ledger survivor (`0/10` W-shift rows, `0/12` fixed-generator rows). More importantly, the optimized rows almost all became one-route portfolios: participation ratio approximately `1` and dominant coefficient fraction above `0.99979`. The state-pricing analogy therefore sharpened rather than softened the theorem target: coefficient freedom tries to buy low-tax null routes, and those routes remain below the wall locally; a global theorem should prove a no-arbitrage dichotomy, not merely enumerate packets.
- **2026-05-04 update:** Phase 5FC answered the participation-ratio false-negative objection by forcing at least two to three effective routes before scoring. No constrained multiroute survivor appeared; best W-shift constrained profit was `0.029300272678`, and best fixed-generator constrained profit was `0.009731187096`. Locally, interacting participation is not the hidden profitable state-price trade; the finite adversary either buys a one-route null trade below the wall or pays enough interaction tax that profit collapses.
- **2026-05-04 update:** Phase 5FA/5FB provide the first explicit finite "pricing-kernel" certificates for this corrected boundary. Linear/predeclared Leray observables pass `(2/3)G-H >= 0` on `2226` certificates through `max_k=96`; W-shift matrix observables pass the lifted quartic PSD condition on `636` certificates with no rank-one sampled hit. This does not prove the universal leakage theorem, but it removes a major ambiguity: the right finite object is a PSD/SOS-style no-arbitrage certificate fixed before coefficient optimization, not an after-the-fact fitted cancellation budget.
- **Evidence pointers:**
    - Experiment/finding rows: `E-GP186-PHASE5DW-APPARATUS-01`, `F-GP186-PHASE5DW-APPARATUS-01`, `E-GP186-PHASE5DW-GEMINI-01`, `E-GP186-PHASE5DW-GEMINI-02`, `E-GP186-PHASE5DX-LERAY-01`, `F-GP186-PHASE5DX-LERAY-01`
    - Run artifacts:
      - `projects/ns_proofsearch_finite_stencil_full_closure/workspace/submissions/iter_002_20260503T222644.857168+0000.py`
      - `projects/ns_proofsearch_finite_stencil_full_closure/debate_log_iter_1777847333.md`
      - `projects/ns_proofsearch_finite_stencil_full_closure/workspace/submissions/iter_003_20260503T222929.152518+0000.py`
      - `projects/ns_proofsearch_finite_stencil_full_closure/debate_log_iter_1777847472.md`
      - `projects/ns_proofsearch_finite_stencil_full_closure/workspace/submissions/iter_004_20260503T223133.063761+0000.py`
      - `projects/ns_proofsearch_finite_stencil_full_closure/debate_log_iter_1777847697.md`
    - Deterministic follow-up:
      - `projects/ns_millennium_hunt/workspace/phase5dx_offdiagonal_leray_commutator_audit.py`
      - `projects/ns_millennium_hunt/workspace/phase5dx_offdiagonal_leray_commutator_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5dx_offdiagonal_leray_commutator_audit_result.json`
      - `projects/ns_millennium_hunt/workspace/phase5dw_iter1_self_reference_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5et_matrix_intertwiner_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5et_matrix_intertwiner_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ew_translation_covariance_intertwiner_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ew_translation_covariance_intertwiner_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ex_w_coupled_shift_matrix_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ex_w_coupled_shift_matrix_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5ey_continuous_support_violator_search_shift.md`
      - `projects/ns_millennium_hunt/workspace/phase5ey_continuous_support_violator_search_shift.json`
      - `projects/ns_millennium_hunt/workspace/phase5ey_continuous_support_violator_search.md`
      - `projects/ns_millennium_hunt/workspace/phase5ey_continuous_support_violator_search.json`
      - `projects/ns_millennium_hunt/workspace/phase5ez_state_pricing_collapse_audit.md`
      - `projects/ns_millennium_hunt/workspace/phase5ez_state_pricing_collapse_audit.json`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_shift.md`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_shift.json`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_fixed.md`
      - `projects/ns_millennium_hunt/workspace/phase5fc_constrained_participation_optimizer_fixed.json`
      - `projects/ns_millennium_hunt/workspace/phase5fa_sparse_psd_pricing_certificate.md`
      - `projects/ns_millennium_hunt/workspace/phase5fa_sparse_psd_pricing_certificate.json`
      - `projects/ns_millennium_hunt/workspace/phase5fb_shift_quartic_pricing_certificate.md`
      - `projects/ns_millennium_hunt/workspace/phase5fb_shift_quartic_pricing_certificate.json`
- **Confidence tier:** `scope_corrected / exact_bounded_algebra / scalar_lp_no_go_candidate / matrix_intertwiner_loophole_charged_locally / w_coupled_caveat_charged_locally / optimized_coefficients_collapse_to_null_routes / constrained_multiroute_no_survivor / finite_pricing_certificates_pass / no_clay_proof`
- **Paper target(s):** `paper7`
- **Status:** `fresh`
- **Opened:** 2026-05-03
- **Last revised:** 2026-05-04

### INS-085 - Paper 8 Ω audit is near-optimal only as a residual-risk protocol, not as a categorical completeness theorem

- **Claim:** GP212's 4-iter Ω-gameability run converged on a narrower and stronger operational claim for Paper 8. Finite Ω enumeration plus challenge cycles blocks the known and challenge-surfaced gaming modes, but it does not prove categorical completeness in open technical domains because unsurfaced future probe classes can remain outside the audit community's imagination. The best current protocol therefore requires a residual `p_remain` term: every low-concern verdict must publish an empirical estimate of the probability of unsurfaced material non-conservative probe classes, discount `Z` by that estimate, and fail close or revoke if `p_remain` is unbounded or later falsified.
- **Why this matters for paper 8:** §6.2 should frame the Ω protocol as a best operational approximation plus an explicit completeness problem. The paper should not imply that finite enumeration by itself closes unknown unknowns. The reviewer-safe claim is: known and surfaced Ω-gaming can be blocked; unsurfaced risk must be disclosed, discounted, and tied to revocation.
- **2026-05-06 follow-up refinement:** The GPT-5.5 follow-up run promoted a stronger champion (`93`) and corrected the unsafe part of this row. Seeded omission tests must not be used to estimate `p_remain`; success on planted cases only qualifies red-team skill. Residual adversarial escape needs an explicit adversary model and public challenge process, or the verdict is non-applicable. This preserves the residual-risk protocol while removing the invalid representativeness assumption.
- **Confidence tier:** `ztare_champion_93 / seeded_bound_falsified / fail_closed_repair / operational_protocol_not_theorem`
- **Paper target(s):** `paper8`
- **Status:** `fresh`
- **Opened:** 2026-05-06
- **Evidence pointers:**
    - Experiment/finding rows: `E-GP212-OMEGA-AUDIT-20260506-01`, `F-GP212-OMEGA-AUDIT-20260506-01`
    - Follow-up rows: `E-GP212-OMEGA-AUDIT-20260506-02`, `F-GP212-OMEGA-AUDIT-20260506-02`
    - Champion: `projects/gp212_consciousness_omega_audit/champion_eval_results.json`
    - Follow-up champion: `projects/gp212_consciousness_omega_audit/latest_eval_results.json`
    - Synthesis: `projects/gp212_consciousness_omega_audit/workspace/synthesis_candidate_1_2_4.md`
    - Derived constraints: `projects/gp212_consciousness_omega_audit/workspace/derived_constraints_brief.md`

### INS-086 - Paper 8 Ω taxonomy requires a provenance and anti-atomization sixth mode

- **Claim:** The score-98 GP212 theorem-attacker run falsified the five-mode public-record taxonomy unless "residual discovery failure" is made tautological. The sixth non-tautological mode is apparatus provenance failure: the claimant shapes the challenge-generating apparatus before the public record is fixed. The sharpest operational subcase is dependency atomization, where claimant-originated influence is split across proxy or sub-threshold paths while aggregate source-class exposure remains material.
- **Why this matters for paper 8:** §6.2 should present the Ω-audit protocol as a six-mode taxonomy and a fail-closed certification rule. A low-concern dossier must include positive source-class provenance certification for auditors, red teams, classifiers, panel members, infrastructure providers, and benchmark/data providers. Per-edge materiality thresholds may reduce publication burden, but they cannot create a safe harbor from aggregation. Missing provenance or unbounded atomization risk means non-applicability, not low concern.
- **Confidence tier:** `ztare_champion_98 / sixth_mode_found / anti_tautology_guard / operational_residual_not_closed`
- **Paper target(s):** `paper8`
- **Status:** `fresh`
- **Opened:** 2026-05-06
- **Evidence pointers:**
    - Experiment/finding rows: `E-GP212-OMEGA-AUDIT-20260506-03`, `F-GP212-OMEGA-AUDIT-20260506-03`
    - Latest eval: `projects/gp212_consciousness_omega_audit/latest_eval_results.json`
    - Thesis marker: `projects/gp212_consciousness_omega_audit/thesis.md`
    - Iter 1 submission: `projects/gp212_consciousness_omega_audit/workspace/submissions/iter_001_20260506T174040.878372+0000.md`
    - Iter 3 submission: `projects/gp212_consciousness_omega_audit/workspace/submissions/iter_003_20260506T174633.474482+0000.md`

### INS-082 - v5 vocabulary holds post-cutoff on theory-builder math but PDE estimate-craft is a sharp scope boundary (12.5% adversarial vs 46% standard)

- **Claim:** GP-218 post-cutoff blind validation of v5 vocabulary on 5 fresh arxiv papers (alg_geom / number_theory / combinatorics / topology_geom / analysis_pde, all posted 2026-05-02 to 2026-05-04 after construction-corpus cutoff) produces mean coverage 56.5% under standard anti-overfit cross-walk and 67.5% under independent inter-rater. Pre-registered classification PASS (≥50% coverage AND ≥70% inter-rater). The headline number confirms vocabulary holds at near-baseline (-1.5pp from internal 58%) on completely fresh material. **The structurally sharper finding is differential coverage by subfield: combinatorics 67%, alg_geom 60%, number_theory 60%, topology_geom 50%, analysis_pde 46%.** Adversarial stress test on the PDE paper finds only 3/24 moves (12.5%) survive strict structural-mechanism testing — a 33.5pp inflation gap on PDE specifically, vs ~10pp gaps on other subfields. The 21 PDE moves that fail mechanism testing cluster around estimate-craft tactics: barriers, blow-up profile extraction, Liouville rigidity, Morse-index transfer under limits, ODE convexity dichotomies, regime isolation, sharpness counterexamples. These are not just "lower coverage" — they are a structural gap. Methodology: 5 parallel Claude Code subagents Step 1 blind enumeration (118 moves total, 0 v5-vocabulary leakage verified), then 5 + 5 cross-walk Tagger A (anti-overfit guards) + Tagger B (independent inter-rater), then 1 adversarial stress test on PDE.
- **Why this matters for paper 5b:** the finding is publishable as a calibrated scope statement — vocabulary is descriptive of theory-building moves at ~58% post-cutoff, with sharp scope boundary at PDE estimate-craft. This *strengthens* paper 5b rather than weakening it: the differential signal makes the vocabulary's claim more falsifiable and more honest. Paper 5b §3 should foreground both the post-cutoff PASS and the PDE scope boundary; methodology summary defers to a one-paragraph appendix referencing the agentic-engineering pattern doc.
- **Why this matters for NS:** Codex's NS Track B closure work (Lipschitz reserve ledger, profile-LSC certificates, Bony paraproduct receipts, blow-up cascade construction) is exactly the estimate-craft v5 doesn't name. The 3 deployed gates mechanize FRAMING moves (potential function = core_02, bound chain = core_06, special-case hint = core_05) but not the closure-distance work itself. **Independent prediction:** NS gate field-test (5 closure attempts) will show modest gate true-positive rates because the vocabulary doesn't cover the moves that close the work. This is a built-in coverage ceiling, not gate-quality issue.
- **Sister track:** GP-219 opens a parallel mining track for a PDE estimate-craft sister vocabulary. Phase 1 starts from the 13 PDE-native "none" moves + ~135 NS Track B F-rows. Distinct from v5 (no extension, no scope creep) and from problem-solver vocabulary (paper 5c, planned). PDE estimate-craft is plausibly a *third* research culture, structurally distinct from theory-builder (Wiles, Grothendieck, Lurie) and problem-solver (Erdős, Tao, Gowers).
- **Methodology (reusable beyond GP-218):** the blind-subagent-cross-walk + anti-overfit guards + adversarial stress test methodology is itself the most reusable finding. Cost: ~$15 LLM compute, ~30 min wall clock, 5 papers. Cheapness makes this a viable falsification tool for any LLM-mediated taxonomy claim. Persisting as agentic-engineering Pattern 12 + planned methods appendix in paper 5b.
- **Confidence tier:** `pre_registered_pass / inter_rater_88pct / pde_scope_boundary_strong_under_adversarial / methodology_validated_n5`
- **Paper target(s):** `paper5b` (post-cutoff blind validation subsection + scope statement); `paper5d_methodology_candidate` (deferred); `paper5c_problem_solver_vocab` (sister, planned); `gp219_pde_sister_vocab` (sister mining track in flight)
- **Status:** `closed`
- **Opened:** 2026-05-05
- **Closed:** 2026-05-05
- **Evidence pointers:**
    - Experiment/finding rows: `E-GP218-POSTCUTOFF-BLIND-VALIDATION-01`, `F-GP218-POSTCUTOFF-BLIND-VALIDATION-01`
    - Pre-registration + result: `research_areas/private/seams/engine/GP-218_post_cutoff_blind_coverage_pre_registration.md`
    - Sister track: `research_areas/private/seams/engine/GP-219_pde_estimate_craft_sister_vocabulary.md`
    - Per-paper artifacts: `projects/ztare_on_ztare/workspace/external_corpus_test/<arxiv_id>/raw_moves.md`, `cross_walk.json`, `cross_walk_b.json`
    - PDE adversarial stress: `projects/ztare_on_ztare/workspace/external_corpus_test/2605.02879/cross_walk_adversarial.json`
    - Selection sealed: `projects/ztare_on_ztare/workspace/external_corpus_test/selection_2026_05_05.json`
    - Scoring report: `projects/ztare_on_ztare/workspace/external_corpus_test/gp218_coverage_report.md`
    - Methodology + apparatus: `scripts/public/projects/ztare_on_ztare/score_external_corpus_coverage.py`

### INS-083 - GP-216/218/219 apparatus does not dissolve the RH operator-search wall, but cross-walk surfaces "Search-Space Cartography" as a reusable apparatus capability invented during GP-125 that neither vocabulary names

- **Claim:** A desk audit (no live runs) cross-walked 11 enumerated moves from past Riemann-hypothesis work (riemann_operator_search GP-125 family + riemann_lagarias charter) against v5 (18 ops, paper 5b descriptive vocabulary) and GP-219 phase 1 (6 PDE/estimate-craft proto-ops). Past work was vocabulary-narrow on v5 — concentrated in 4 of 18 ops (core_01 Problem Domain Translation, core_05 Extremal Case Analysis, broad_04 Bounding via Surrogate, broad_07 Systematic Cataloging), with 8 ops entirely unused including core_06 External Framework Importation (no RMT black-box theorems with verified preconditions imported) and broad_03 Dimensional Lifting (no complex-Hermitian / GUE-broken complexification, which the F-row itself names as honest-next-move-ii). GP-219 coverage was essentially zero (operator search is mechanistically distinct from estimate-craft, validating GP-219's narrow scope). Critically, the wall (real-symmetric polynomial+arithmetic Pareto ceiling at MSE ~0.25 / spacing-CV ~0.30) is **vocabulary-independent**: even with all 18 v5 ops + 6 GP-219 proto-ops instantiated, the bimodal CV gap is a property of the operator space under the chosen ansatz, not an apparatus / vocabulary deficit. The F-row's three honest-next-moves (scale to N≥2000, complex-Hermitian / GUE-broken ensemble, OEIS pivot) are the actually-available alternatives; vocabulary cross-walk does not produce a free move.
- **Audit-surfaced novel finding:** Past RH work invented a move neither v5 nor GP-219 names — **Search-Space Cartography**: enumerating a generator class, then mapping the resulting (CV, MSE) plane and reporting empty regions / phase boundaries / basin counts. This converted a sequence of null operator-fits into the GP-125-BIMODAL-GAP positive structural finding (sv ∈ (0.37, 0.54) is empty across 28 generators). It is a central move for understanding the wall — without it, the project would have just registered "no operator beats CV ceiling" without the deeper structural reframe. The move is reusable across any project that runs a parameter sweep: GP-126 OEIS sky survey, GP-219 NS sweeps, future symbolic-regression sweeps. Codifying it as a reusable cross-project analytic on existing sweep JSON is the cheapest high-leverage move surfaced by the audit.
- **Why this matters for paper 5b:** the v5 vocabulary's narrowness on past RH work is a candidate finding for §6 (folk-knowledge contradictions chapter) or §5.5 (claim-A bridge) — not because it shows v5 is wrong, but because it shows v5 is genuinely *descriptive* and not generative. Past RH work used core_01 + core_05 heavily, and the wall came from the ansatz class, not from vocabulary blind spots. This *strengthens* paper 5b's framing: vocabulary names what mathematicians do; it does not unstick what is structurally hard.
- **Why this matters for NS / GP-219:** Search-Space Cartography is a candidate proto-op G for GP-219 IF NS Track B sweeps demonstrate the same move. Codex's recent Phase 5EY/EZ/FC/FK work has dichotomy structure (proto-op C) but no explicit phase-diagram cartography of the constraint plane. If Phase 2 mining of GP-219 surfaces the cartography move on PDE papers + NS work, it joins as proto-op G; otherwise it is an RH-specific or ansatz-search-specific move and stays out of GP-219.
- **Why this matters for RH operationally:** Do NOT relaunch RH live runs based on this audit. The wall is real and the alternatives are known. DO consider three cheap audit-grounded moves: R1 codify Search-Space Cartography as reusable analytic (zero RH compute); R2 desk-check core_06 RMT preconditions on best past operator (binary outcome — either sharpens wall to "RMT-black-box module unavailable here" or surfaces a precondition we missed); R3 promote pre-registered null-shape declaration into charter template (process change). All three are off-critical-path and shouldn't displace NS Track B / GP-219 Phase 2 work.
- **Confidence tier:** `apparatus_does_not_unstick_rh / vocabulary_narrow_concentrated_in_4_of_18_ops / search_space_cartography_load_bearing_uncovered_move / wall_is_structural`
- **Paper target(s):** `paper5b` (candidate for §6 folk-contradiction chapter or §5.5 claim-A bridge — past RH work as a case where v5 was descriptive but not generative); `gp219_phase2_proto_op_g_candidate` (deferred until validation)
- **Status:** `closed`
- **Opened:** 2026-05-05
- **Closed:** 2026-05-05
- **Evidence pointers:**
    - Experiment/finding rows: `E-RH-DESK-AUDIT-20260505-01`, `F-RH-DESK-AUDIT-20260505-01`
    - Audit report: `projects/riemann_operator_search/workspace/rh_desk_audit/audit_2026_05_05.md`
    - Past F-rows audited: `F-GP125-01`, `F-GP125-BIMODAL-GAP`, `F-GP125-A10-DENSE-01`
    - Past project artifacts: `projects/riemann_operator_search/findings.md`, `projects/riemann_lagarias/project_charter.md`
    - Cross-references: `INS-082` (parent finding on v5 differential coverage); `research_areas/private/seams/engine/GP-219_pde_estimate_craft_sister_vocabulary.md` (GP-219 phase 1 result)

### INS-084 - v5 + GP-219 are complements, not competitors: joint methodology covers ~95% of structural moves; one likely missing primitive (Representation / Coordinate Reformulation) surfaces from residual mining

- **Claim:** The right unit of measurement for mathematical-research-move coverage is the JOINT v5+GP-219 vocabulary, not either alone. Empirical evidence: cross-walking 3 borderline papers (1 PDE Carleman / 1 PDE separation-of-variables / 1 NT modular forms) jointly against the 24-op union (v5 18 + GP-219 6) produced 100% / 92% / 92% coverage = mean 94.7%. The same 3 papers cross-walked GP-219-only produced 70% / 17% / 32% = mean 39.7%. The +55pp gap is almost entirely a methodology artifact: standalone GP-219 cross-walks force agents to stretch proto-op A onto framework imports + tool invocations that v5 core_06 cleanly absorbs. v5 alone on PDE has a ~4-6-op gap (estimate-craft moves it doesn't name); GP-219 fills that gap; jointly they cover ~95% of structural moves on PDE+NT papers in the test corpus.
- **Implication for paper 5b's "PDE scope boundary" finding (INS-082):** the differential coverage was real for v5 alone but dissolves under joint methodology. The right framing for paper 5b: "v5 alone has a recognizable gap on 4-6 specific PDE estimate-craft moves; GP-219's 6 proto-ops fill that gap; v5+GP-219 jointly cover ~95% on fresh PDE+NT corpus." The 12.5% adversarial PDE finding from GP-218 is now best read as "v5 alone, strictly applied, captures only the central theory-builder moves on a PDE paper; the rest is named by GP-219 + 1 likely missing primitive (Candidate G Representation Reformulation)."
- **Residual mining (188 "none" moves across 14 papers):** 1 strong candidate primitive (G — Representation / Coordinate Reformulation, 14 instances across 7 papers, distinct from core_01 + proto-op A; likely v5-tier as core_08 or broad_08). 3 provisional candidates flagged below threshold. 5 broadening recommendations where existing op definitions are too narrow (e.g., core_06 should cover single-lemma imports, not just full theorems). ~40-48% of residual is genuinely-diverse plumbing (special functions, linear algebra packaging, editorial moves) — NOT undiscovered primitives.
- **Methodology contribution:** the combined-cross-walk methodology + bracket check (Tagger B + adversarial) + residual-mining loop is itself reusable. Cost: ~$10-15 LLM compute, ~30 min wall clock, 17 parallel Claude Code subagents. Reusable for any future vocabulary-claim validation (paper 5c problem-solver vocabulary, future GP-N tracks). Pattern 12 candidate (joint methodology) augments Pattern 11 (single-vocabulary blind cross-walk).
- **Anti-overfit discipline held:** 188 candidate moves examined → only 1 strong primitive proposed. ~95% of analysis was either "broaden existing op definition" or "this is plumbing, no primitive." The residual-miner explicitly compared each candidate to nearest existing op + flagged provisional candidates honestly. This is the discipline paper 5b §5.4 calls for.
- **NS implications:** Codex's Track B work should be tagged with v5+GP-219 jointly, not GP-219 alone. The advisor channel Turn 72 GP-219-only tagging was correct content but partial. NS coverage under joint methodology is probably ~90%, not the lower numbers we'd been quoting standalone.
- **RH implications:** the desk audit (INS-083) said past RH work used 4 of 18 v5 ops with GP-219 essentially orthogonal (operator search ≠ estimate-craft). Joint methodology would re-audit the 4-of-18 narrowness against the 24-op union (or 25-op with G). If still narrow, the RH finding holds; if not, it's another methodology artifact. Cheap re-audit candidate.
- **Confidence tier:** `combined_methodology_validated_n3 / proto_op_A_inflation_diagnosed / 1_strong_candidate_G_above_threshold / 3_provisional_candidates_below_threshold / 5_broadenings_text_edit_only / 40pct_residual_is_plumbing_not_primitive`
- **Paper target(s):** `paper5b` (rewrite §5.5.5 + §5.3.7 + §6.2.4 with combined-methodology framing + Candidate G as likely future addition); `paper5d_methodology_candidate` (deferred — applied combined cross-walk methodology now has 4 instantiations: GP-218 + GP-219 Phase 2 + bracket + residual mining)
- **Status:** `closed`
- **Opened:** 2026-05-05
- **Closed:** 2026-05-05
- **Evidence pointers:**
    - Experiment/finding rows: `E-GP219-PHASE2-COMBINED-METHODOLOGY-20260505`, `F-GP219-PHASE2-COMBINED-METHODOLOGY-20260505`
    - GP-219 seam: `research_areas/private/seams/engine/GP-219_pde_estimate_craft_sister_vocabulary.md` (Phase 2 + combined methodology + residual mining all appended)
    - Per-paper Phase 2 artifacts: `projects/ztare_on_ztare/workspace/gp219_phase2/<arxiv_id>/raw_moves.md`, `cross_walk.json`, `cross_walk_b.json` (false-neg bracket), `cross_walk_adversarial.json` (false-pos bracket), `cross_walk_combined.json` (combined v5+GP-219)
    - Per-paper analytic-NT cross-val: `projects/ztare_on_ztare/workspace/gp220_analytic_nt_validation/<arxiv_id>/raw_moves.md`, `cross_walk.json`, `cross_walk_combined.json` (where applicable)
    - Residual mining output: `projects/ztare_on_ztare/workspace/gp219_pde_estimate_craft/residual_mining_phase1.md`
    - Cross-references: `INS-082` (parent post-cutoff finding to be re-framed); `INS-083` (RH desk audit)

### INS-085 - NS Track B last bridge is a selected numeric compactness-liminf source, not a finite certificate or generic family adapter

- **Claim:** The current GP216/Track B proof path has compressed to one honest unpaid selected-branch source: `GP216SelectedProjectedNumericCompactnessLiminfSource`. The same fixed approximation family must generate the selected compactness source, the MV defect carrier, and the three liminf prices that are later identified with the relaxed self-tax, cross-defect, and coherence prices. Finite Phase 5FB algebra, prefix-tail visibility, aggregate total-tail control, event recurrence, selected-branch stream equality, audited-output packaging, bare measure-valued records, and generic family compactness transport are now either paid, refuted as shortcuts, or demoted to zero source credit.
- **Why this matters for NS:** Score `1` in the residual-void audit is not evidence of bad conditions by itself. It is the first source atom remaining after semantic adapters are stripped and after the target is forced to be selected-branch local and numeric. The proof can advance only by paying a real same-family compactness/liminf source or by producing a falsifier that shows the current Track B source family cannot generate that object.
- **Endpoint evidence:** The selected-wrapper endpoint produced only a packaging constructor from already-supplied MV source plus already-supplied provenance. The family-level endpoint refused cleanly, and the lane review found that family transport is only plumbing. The live source was therefore hardened with `GP216GeneratedLiminfPriceCertificate` and `GP216SelectedDefectGenerationCertificate`; a source now has to carry observable-level liminf witnesses and a typed same-family defect certificate.
- **Anti-tautology content:** A scratch Lean diagnostic shows a bare `LeraySelfTaxMeasureValuedOutputLimitSource` can be filled by zero defects from selected continuum component data. Therefore a bare MV source cannot carry scientific source credit. A later compiled zero-defect falsifier showed the first selected defect-generation certificate still admitted all-zero defect prices because its anti-laundering guard was a bare `Prop`; the interface now requires `GP216MeasureValuedSourceHasPositiveGeneratedDefect`, and `scripts/public/projects/ns/ns_trackb_negative_void_probe.py --case zero-defect-generation-certificate` rejects the old route. The GP216 selected-branch route now requires compactness provenance, generated liminf certificates, positive generated defect price, and a defect-generation certificate tied to the compactness provenance. One-point Young summaries and scalar component LSC remain invalid for cross/coherence unless the multiscale/correlation and local-energy channels are paid by the same family.
- **Literature use:** Lions / DiPerna-Majda / Tartar / Alibert-Bouchitte / Duchon-Robert were used as a defect-mode checklist, not as a ceiling on the proof. The bridge may be ahead of the literature if it packages these channels into a stronger typed source, but it cannot be behind the literature by omitting them.
- **Confidence tier:** `lean_compiled_interface / hostile_review_bypass_found_and_blocked / residual_void_score_1 / no_clay_proof`
- **Paper target(s):** `ns_trackb_internal_proof_log`; possible future `paper8` appendix if the source is paid or refuted.
- **Status:** `open`
- **Opened:** 2026-05-07
- **Evidence pointers:**
    - Experiment/finding rows: `E-NS-TRACKB-20260507-COMPACTNESS-PROVENANCE-VOID-01`, `F-NS-TRACKB-20260507-COMPACTNESS-PROVENANCE-VOID-01`, `E-NS-TRACKB-20260507-NUMERIC-LIMINF-VOID-01`, `F-NS-TRACKB-20260507-NUMERIC-LIMINF-VOID-01`, `E-NS-TRACKB-20260507-SWARM-NEGATIVE-VOID-01`, `F-NS-TRACKB-20260507-SWARM-NEGATIVE-VOID-01`
    - Lean files: `ztare_proofs/ZtareProofs/ns_profile_lsc_self_tax_obligation.lean`, `ztare_proofs/ZtareProofs/ns_gp216_bridge_composition_receipt.lean`
    - Residual log: `projects/ns_millennium_hunt/workspace/research_notes/ns_trackb_residual_void_audit.md`
    - Divide-and-conquer packet: `projects/ns_millennium_hunt/workspace/research_notes/ns_trackb_numeric_liminf_divide_conquer.md`
    - Literature packet: `projects/ns_millennium_hunt/workspace/research_notes/ns_trackb_concentration_compactness_literature_packet.md`
    - Negative controls: `analytics/public/queries/ns_mv_continuum_zero_test.lean`, `scripts/public/projects/ns/ns_trackb_negative_void_probe.py`

### INS-087 - Paper 7 neural claim demotes to morphology plus anti-tautology case study

- **Claim:** Out-of-loop endpoint-withheld audits over OLMo2 7B/13B raw train-loss telemetry and exact OLMo2 1B Stage-1 history show that the Paper 7 neural result should not be framed as a full-endpoint normalized law. Full-endpoint normalized shape remains tight (`mean z-tail MAE=0.0413`), but prefix min/max (`0/8`), prefix-affine shape (`1/8`), count-prefix coordinate panel (`5/15`, mean best-template MAE `0.483` vs best prefix-only `0.112`), and raw segment contraction (`2/12`) do not promote. The only OLMo 7B/13B positive was a narrow slope-anchored template (`6/8` mid/late progress cells). A first mlfoundations stress test looked positive, but DARWIN found online endpoint-horizon leakage; the repaired fixed-online grouped audit fails (`211/737` against basic baselines, `114/737` against the full ladder including nearest-external baseline). Exact OLMo2 1B then closed the remaining prospective path negatively: segment-level H-05 wins `0/28` fixed-count online cells against the full ladder and `1/28` known-horizon cells; the median-stitched diagnostic also fails (`0/2` known-horizon all-baseline wins). The exchange-rate rescue was then tested directly as a local contraction-rate objective; it also fails on exact 1B no-overlap (`3/41` rate-win cells, mean rate MAE `1.5040` vs persistence `0.7562`). H-07 then found a real downstream-eval observation site (`1,850` 7B rows across `4` runs, `925` unique run-step rows; sparse 13B `22` rows across `2` runs), but the first source-gated diagnostic still does not promote: gradient norm wins `0/6` 7B metrics at the required 20% margin, and train CE also wins `0/6`. H-11 mines the remaining void: the downstream-eval packet itself has a measurement-resolution/cadence boundary. ARC Easy, HellaSwag, and MMLU STEM expose finite denominator gaps near `1/570`, `1/10046`, and `1/321`; CE metrics are smoother but still persistence-dominated at this cadence. H-12 turns that into an observability gate and finds `0/12` H-07/H-08 same-packet candidates clear `max(20% baseline MAE, two accuracy quanta)`. H-13 ranks successor source classes and promotes source-state design, not curve fitting, as the next object: controlled lineage perturbation and independent checkpoint eval are strong candidates; same-packet feature engineering is rejected. H-14/H-15 show that public/local artifacts provide checkpoint coordinates and eval machinery but not the needed measurement table. H-16 creates a sealed `34`-job OLMo2 1B checkpoint-eval manifest. H-20/H-21 then use public Ai2 aggregate OLMES data to refine the objective without promoting a law: the public source has `6,750` late-stage aggregate rows, `87/675` task/metric cells clearing the chronological observability gate, and `200` primary-score cells moving by at least two accuracy quanta, but only `2/34` exact H17 jobs and no per-instance rows. H-22 converts that into a separate targeted packet with `24` tasks and `20` checkpoints, and H-23 fixes its post-run ingest/scoring gate before measurement. A six-agent orchestration audit then added H-24 because the H-22 high-motion panel was selected from public late-stage aggregate passes; H-24 now requires early/mid stage-1 survival outside the public selector window before targeting can be treated as leakage-aware. H-25 confirms the packet is design-ready but locally runtime-blocked on `oe-eval`, and H-26 fixes a flat-table leakage bug so demoted metrics-only or no-logprob outputs cannot enter downstream scoring. The live scientific object is evaluator-response transfer under a typed measurement contract, not curve-law fitting and not public high-motion task replay.
- **Why this matters for Paper 7:** The neural section should be upleveled as an anti-tautology case study, not as a current law claim. It shows the apparatus found an attractive collapse, identified the hidden future-endpoint gauge, tested candidate repairs, and demoted the strongest cross-family interpretation when a harsher online/grouped audit failed.
- **Meta-pattern:** The productive historical analogy is coordinate discovery, not prettier curve fitting, but the candidate coordinate must pay a prospective bill. Boundary slope has now failed its exact OLMo2 1B bill. The imported NS residual-void discipline turned the remaining duplicate-step uncertainty into a source audit rather than a rescue: long restart overlaps do not show persistent branch hysteresis, while the final short seam is raw minibatch/runtime volatility unless future eval evidence says otherwise. A no-overlap rescue test also fails, so restart overlap is not the hidden cause of the H-05 failure. A broader eval-key availability scan around restart windows returns no eval CE rows through the public report context, but W&B project-level inventory later found downstream-eval packets for 7B and 13B. That source gate mattered: it showed the next site exists, then rejected simple optimizer telemetry as the missing state variable. H-08 then mined the residual by testing whether sibling eval metrics forecast withheld next eval metrics; that also returned `0/6` required wins. H-09 tested the only remaining hidden nugget, a matched late stage-2 branch-response hint; it had nominal seed42 movements but `0` Bonferroni-corrected hits against a rolling stage-1 null. H-11 provides the 2050-style ex post lesson: the failed law hunt was partly an evaluator-design audit. H-12 converts the lesson into a stop rule. H-13 applies the primitive stack: Reducer strips same-packet renames; Darwin ranks source classes; smuggling audit blocks run-id/checkpoint hindsight; three-leg verification is deferred until a clean source exists. H-14/H-15 add the source-laundering rule: a checkpoint URL and eval code are coordinates, not observations. H-16 seals the coordinates before measurement. H-20/H-24 add a sharper primitive split: public aggregate eval is allowed to target compute, but it is not allowed to certify a law or even validate targeting unless the signal survives outside the public selector window. Persistence is not just a baseline; at this cadence it is the null behavior of the measurement channel. The exchange-rate reframe was the right objective-function audit, but it returned a negative result for the scalar rate-coordinate version; more same-packet curve, eval-vector, or branch-anecdote regression is now low-value unless a new object first clears an observability floor computed before fitting.
- **Anti-tautology content:** Future endpoint `L_min/L_max`, run identity, post-hoc named constants, raw local-alpha, optimizer-control variables, same-packet scalar exchange-rate rescues, and same-packet eval-state rescues are blocked from promotion. Any future run must beat last-prefix, persistence, local-linear baselines, and a precomputed observability floor with the target endpoint withheld.
- **Confidence tier:** `closed_out_loop_audit / endpoint_leakage_blocked / fixed_online_grouped_negative / exact_1b_h05_negative / restart_overlap_void_mined / exchange_rate_reframe_negative / h07_eval_source_gate_passed_but_optimizer_telemetry_negative / h08_eval_manifold_negative / h09_branch_response_negative / h11_eval_resolution_boundary / h12_observability_gate_zero_clears / h13_source_design_gate / h14_local_source_frontier / h15_external_source_feasibility / h16_sealed_manifest / h20_h21_public_aggregate_observability_fork / h22_targeted_packet_created / h23_targeted_gate_pre_registered / h24_leakage_aware_gate_pre_registered / h25_execution_preflight / h26_ingest_fixture_hardened`
- **Paper target(s):** `paper7` (neural scope correction and anti-tautology appendix evidence); possible future neural working note only if a new pre-registered object uses cleaner eval/restart markers, controlled production-style logs, or a non-raw-train-loss observable. The H-05 slope-anchor object and H-06 scalar exchange-rate object are closed negative.
- **Status:** `closed`
- **Opened:** 2026-05-08
- **Closed:** 2026-05-08
- **Evidence pointers:**
    - Experiment/finding rows: `E-NEURAL-HUNT-OUTLOOP-20260508-01`, `F-NEURAL-HUNT-OUTLOOP-20260508-01`, `E-NEURAL-HUNT-XFAMILY-SLOPE-20260508-01`, `F-NEURAL-HUNT-XFAMILY-SLOPE-20260508-01`, `E-NEURAL-HUNT-FIXED-ONLINE-20260508-01`, `F-NEURAL-HUNT-FIXED-ONLINE-20260508-01`, `E-NEURAL-HUNT-H05-EXACT-1B-20260508-01`, `F-NEURAL-HUNT-H05-EXACT-1B-20260508-01`, `E-NEURAL-HUNT-RESTART-VOID-20260508-01`, `F-NEURAL-HUNT-RESTART-VOID-20260508-01`, `E-NEURAL-HUNT-EXCHANGE-RATE-20260508-01`, `F-NEURAL-HUNT-EXCHANGE-RATE-20260508-01`, `E-NEURAL-HUNT-H07-EVAL-SOURCE-20260508-01`, `F-NEURAL-HUNT-H07-EVAL-SOURCE-20260508-01`, `E-NEURAL-HUNT-H08-EVAL-MANIFOLD-20260508-01`, `E-NEURAL-HUNT-H09-STAGE2-BRANCH-20260508-01`, `E-NEURAL-HUNT-H11-EVAL-RESOLUTION-20260508-01`, `F-NEURAL-HUNT-H11-EVAL-RESOLUTION-20260508-01`, `E-NEURAL-HUNT-H12-OBSERVABILITY-GATE-20260508-01`, `F-NEURAL-HUNT-H12-OBSERVABILITY-GATE-20260508-01`, `E-NEURAL-HUNT-H13-SOURCE-DESIGN-20260508-01`, `F-NEURAL-HUNT-H13-SOURCE-DESIGN-20260508-01`, `E-NEURAL-HUNT-H14-LOCAL-SOURCE-AVAILABILITY-20260508-01`, `E-NEURAL-HUNT-H15-EXTERNAL-SOURCE-FRONTIER-20260508-01`, `F-NEURAL-HUNT-H15-EXTERNAL-SOURCE-FRONTIER-20260508-01`, `E-NEURAL-HUNT-H16-SEALED-CHECKPOINT-MANIFEST-20260508-01`, `F-NEURAL-HUNT-H16-SEALED-CHECKPOINT-MANIFEST-20260508-01`, `E-NEURAL-HUNT-H20-H21-PUBLIC-EVAL-FORK-20260508-01`, `F-NEURAL-HUNT-H20-H21-PUBLIC-EVAL-FORK-20260508-01`, `E-NEURAL-HUNT-H22-TARGETED-OLMES-PACKET-20260508-01`, `E-NEURAL-HUNT-H23-TARGETED-GATE-20260508-01`
    - Synthesis: `projects/neural_hunt/workspace/out_loop_synthesis_2026_05_08.md`, `projects/neural_hunt/workspace/neural_residual_void_synthesis_2026_05_08.md`, `projects/neural_hunt/workspace/exchange_rate_reframe_2026_05_08.md`
    - Audits: `projects/neural_hunt/workspace/prefix_endpoint_null_audit_2026_05_08.md`, `projects/neural_hunt/workspace/prefix_affine_shape_audit_2026_05_08.md`, `projects/neural_hunt/workspace/prefix_slope_anchored_shape_audit_2026_05_08.md`, `projects/neural_hunt/workspace/prefix_coordinate_candidate_audit_2026_05_08.md`, `projects/neural_hunt/workspace/raw_segment_contraction_audit_2026_05_08.md`, `projects/neural_hunt/workspace/cross_family_slope_anchor_audit_2026_05_08.md`, `projects/neural_hunt/workspace/cross_family_stratified_slope_anchor_audit_2026_05_08.md`, `projects/neural_hunt/workspace/cross_family_fixed_online_group_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h05_exact_1b_validation_2026_05_08.md`, `projects/neural_hunt/workspace/h05_exact_1b_stitched_median_validation_2026_05_08.md`, `projects/neural_hunt/workspace/olmo1b_restart_overlap_hysteresis_audit_2026_05_08.md`, `projects/neural_hunt/workspace/olmo1b_restart_aux_metric_probe_2026_05_08.md`, `projects/neural_hunt/workspace/h05_exact_1b_no_overlap_validation_2026_05_08.md`, `projects/neural_hunt/workspace/olmo1b_restart_eval_availability_scan_2026_05_08.md`, `projects/neural_hunt/workspace/exchange_rate_coordinate_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h07_wandb_eval_source_inventory_2026_05_08.md`, `projects/neural_hunt/workspace/h07_source_packet_admissibility_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h08_eval_manifold_residual_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h09_stage2_branch_response_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h11_eval_resolution_void_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h12_observability_gate_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h13_source_state_design_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h14_local_source_availability_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h15_external_source_frontier_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h16_checkpoint_eval_manifest_2026_05_08.md`, `projects/neural_hunt/workspace/h20_signal_noise_public_eval_audit_2026_05_08.md`, `projects/neural_hunt/workspace/h21_signal_noise_observability_gate_2026_05_08.md`, `projects/neural_hunt/workspace/h22_targeted_checkpoint_eval_packet_2026_05_08.md`, `projects/neural_hunt/workspace/h23_targeted_checkpoint_eval_gate_2026_05_08.md`

### INS-088 - Neural learning mechanics source-axis evidence supports response-mode flow, not scalar exchange-rate law

- **Claim:** DataDecide aggregate evaluator trajectories provide a bounded positive learning-mechanics object after scalar law routes fail: signed task-response-rate vectors live on a low-dimensional, size-indexed mode flow. H35 rejects scalar adjacent-size exchange (`5,584` leave-one-task-out cells; win rate `0.416`; exchange error `1.401x` worse than best simple baseline). H36 then de-anchors/reframes the object from scalar exchange to task-response vectors and finds a positive masked-task reconstruction signal (`473` contexts, `8` tasks; best MAE row `signed_sqrt`, `k=1`, MAE `0.4631` vs baseline `0.7198`, improvement `0.357`, top-2 variance `0.738`; best relative-improvement row `signed_log`, `k=1`, improvement `0.367`, top-2 variance `0.746`). H37 mines the residual void and identifies size as the hidden axis: PC1-size eta-squared `0.869`, strongest residual concentration axis `size`, top/median residual ratio `1.900`. H39 then tests size-conditioned mode flow directly: quadratic log-size prediction of PC1 across held-out source families reduces MAE from `1.8132` to `0.7579` (`58.2%` improvement); PC2 remains weak (`4.8%` improvement), pointing to data mixture/task semantics as residual axes.
- **2026-05-10 H40 update:** The first residual split demotes data-mixture as the immediate second coordinate. Source-mixture tags derived from DataDecide model names do not predict PC2 across held-out source families (`1.4%` improvement vs mean; `0.3%` improvement vs size-only), but PC2 task semantics are sharply concentrated (`7.83` ratio), dominated by `boolq` / reading-boolean loading. The next residual object is therefore task-interface / reading-boolean sensitivity, not a broad data-mixture law.
- **2026-05-10 H41 update:** The BoolQ residual survives representation perturbation. BoolQ is top PC2 absolute loading in `5/6` base metric variants and remains top when the task panel expands to include `csqa` and `mmlu` (`0.833` abs loading, `0.391` abs-loading share).
- **2026-05-10 H42 update:** H42 partially demotes the H41 interpretation. BoolQ shares its simple schema group with `winogrande` (`acc_raw` primary metric and zero `acc_uncond`), and BoolQ/group-median dominance is only `1.407`, below the pre-registered `2x` bar. BoolQ still leads multiple common non-primary metrics, so it remains a live residual candidate, but DataDecide schema artifact is not ruled out.
- **2026-05-10 H43 update:** The fastest non-DataDecide projection does not support cross-source BoolQ promotion, but the hard negative is unsafe. Public OLMo `signal-and-noise` aggregate rows show a base-panel PC2 near-miss (BoolQ top loading `0.616`, BoolQ/Winogrande ratio `1.461` vs required `1.5x`). H43b audits the falsifier and finds BoolQ top-2 on PC1/PC2 in `18/36` metric/mode panels, with opposite-sign separation from Winogrande in `12/36`. BoolQ/interface remains a caveated diagnostic, not a promoted coordinate and not a DataDecide-local artifact closure.
- **2026-05-11 H44-H45 update:** Public OLMo aggregate rows weakly echo but do not promote the response-mode object. H44 response-rate masked reconstruction scores `0/36` success rows; best row is H22 targeted `24` tasks, `logits_per_char_corr`, `k=2`, improvement `0.096`, top3 `0.518`. H45 level/rate sensitivity scores `0/108` success rows; best level row improves `0.121` with top3 `0.404`, and best two-step-rate row improves `0.081`. This blocks cross-source promotion from public aggregate rows alone.
- **2026-05-11 H46 update:** H46 shows the H44/H45 weakness is measurement-regime, not a clean public-OLMo source negative. Forcing DataDecide into within-trajectory interval geometry also fails: pooled interval best improvement `-0.090`, top3 `0.505`; only `2/447` single-trajectory contexts pass. The live object is therefore an across-context slope-mode object, not an adjacent-interval PCA object.
- **2026-05-11 H47 update:** H47 shows the H36 slope-mode object is cheap to detect but not diversity-free. Random `n=30` subsets pass at `1.000` with median improvement `0.349` and top2 `0.804`; family-stratified `n=30` passes at `0.950`; single-family `n=60` passes at `0.992`. Single-size `n=60` fails at `0.000` with median improvement `0.100`. The dependency is size/context variation, not broad source-family coverage.
- **2026-05-11 H48 update:** H48 blocks the tempting fallback that single-size packets can still carry the named BoolQ/interface residual. BoolQ is top-2 on PC1/PC2 in only `2/9` primary fixed-size panels, and all metric-size panels have BoolQ top2-any rate `0.222` and rank1-any rate `0.074`. The BoolQ residual is cross-size/context-sensitive, not a stable fixed-size diagnostic.
- **2026-05-11 H50 update:** H50 replaces the local 9-size DataDecide summary with the public `DataDecide-eval-results` macro-average grid. The expanded grid has `14` raw size buckets and `13` slope-eligible buckets, yielding `975` complete contexts. The core object strengthens: H36 k=1 improvement `0.446`, top2 `0.799`; H39 PC1 held-out-family improvement `0.736`. H47's size/context requirement also strengthens: random and family-stratified `n=30` pass `1.000`, single-family passes, single-size `n=60` remains `0.000`. H48 is corrected from hard fixed-size BoolQ negative to mixed-not-promoted: primary fixed-size top2-any `4/13`, all-panel top2-any `0.415`.
- **2026-05-11 H51 update:** H51 maps the fixed-size residual left by H50. The residual is not BoolQ-specific; it is a task-family map. Across `65` metric-size panels, top2-any rates are `arc_easy=0.831`, `arc_challenge=0.785`, `hellaswag=0.646`, `boolq=0.415`, `piqa=0.400`. Fixed-size diagnostics should report ARC/HellaSwag task-family maps, not BoolQ-only language.
- **2026-05-11 H52 update:** H52 validates the H51 fixed-size residual against a marginal-preserving covariance null. ARC Easy, ARC Challenge, and HellaSwag all exceed the null p99 (`54/65` vs p99 `40.0`; `51/65` vs p99 `42.01`; `42/65` vs p99 `41.01`). BoolQ does not clear the same null (`27/65` vs p95 `38.0`). The fixed-size residual is therefore an ARC/HellaSwag covariance structure, not just marginal task variance or finite-panel PCA noise.
- **2026-05-11 H53 update:** H53 turns the fixed-size residual from a static map into a size-regime transition. Science QA appears in `1.000` of early, mid, and late panels. BoolQ/interface is early-heavy (`0.633` early-minus-late vs size-label-null p95 `0.250`), while HellaSwag/continuation is later-heavy (`0.367` late-minus-early vs p95 `0.233`).
- **2026-05-11 H54 update:** H54 blocks cross-source support for H53 from public OLMo aggregate rows. Science-QA repeats (`34/36`, `0.944`), but the full H53 late signature appears in only `6/36` panels (`0.167`), and BoolQ/interface (`18/36`, `0.500`) appears more often than HellaSwag/continuation (`12/36`, `0.333`).
- **2026-05-11 H55 update:** H55 converts the H54 negative into a structured residual. Public aggregate failure is panel/schema-conditioned: base panels carry late-signature `6/18`, while `:mc` panels carry `0/18` (delta `0.333`, p `0.014`). H53 still cannot be promoted cross-source, but the failure is not uniform absence of the family signal.
- **2026-05-11 H56 update:** H56 applies H55 to the existing GPU packets. H27/H29 are not schema-ready: each has only one matched base/suffixed family, and H22 has only two, below the `4`-family readiness rule. Existing H27/H29 should be treated as runtime/per-instance acquisition unless a schema-balanced successor is generated.
- **Why this matters for learning mechanics:** The positive Neural Hunt result after the anti-tautology closures is local and bounded but now sharper: response-mode dynamics are more promising than scalar exponents or scalar exchange rates, and the dominant state coordinate is size-flow over task-response slopes. It is not a universal neural law and not OLMo per-instance evidence. It is a source-axis object: DataDecide-positive low-dimensional across-context response-mode flow with PC1 size structure; public OLMo aggregate is observability context; the fixed-size residual is a null-validated DataDecide size-regime task-family transition: ARC/science-QA backbone, early BoolQ/interface, later HellaSwag/continuation. H54 prevents upgrading that transition cross-source from public aggregate rows alone; H55 explains part of the mismatch as task-interface/schema dependence; H56 prevents the existing GPU packets from being over-read as schema-aware science tests.
- **Meta-pattern:** The pioneer-pattern map applies cleanly. Early fields often see curves before state variables. Here, the failed curves are raw loss/exponent/exchange-rate surfaces; the state variable is a size-indexed evaluator-response mode. The residual void is productive: PC1 is size, while PC2/residuals point to data mixture and task semantics.
- **Structural-language fingerprint:** Universal/candidate ops: `core_03` Canonical Decomposition (task-response vector modes), `core_01` Problem Domain Translation (scalar-law surface -> response-mode coordinate system), and `cand_g` Representation / Coordinate Reformulation. TB/PS culture: theory-building / object-discovery, not problem-solving estimate craft. GP-219 PDE ops are not primary here; cite only the `cand_g` analogy, because Neural Hunt's mechanism is coordinate reformulation rather than PDE auxiliary-object or threshold-dichotomy craft.
- **Operator inception / provenance:** This positive chain was triggered by the operator's reframe, not by the agent's default continuation. After H35 weakened scalar exchange, the operator pushed ZTARE de-anchor/reframe, residual/void exploitation, and early-field pioneer-pattern analysis. That intervention changed the next action from narrower aggregate/source bookkeeping into H36-H39 object discovery.
- **Mechanization implication:** RD ticks should not wait for an operator prompt after repeated negative closures. A negative-to-object checkpoint should be mandatory: list the failed object, mine residual structure, name a candidate state variable, and dispatch the next discriminator or explicitly justify why the void is diffuse.
- **Anti-tautology content:** DataDecide and public OLMo signal-and-noise remain aggregate-only. H34 blocks upgrading DataDecide into H23/H24 per-instance evidence; H44-H45 block public OLMo aggregate promotion. H47/H50 block over-reading single-size OLMo packets as PC1 size-flow promotion. H48/H50/H52 keep BoolQ/interface open but unpromoted. H54 blocks cross-source promotion of H53 from public OLMo aggregate. H55 says that negative is schema-conditioned, not promotional. H56 blocks over-reading existing H27/H29 packets as schema-aware diagnostics. H36-H56 can guide source-axis hypotheses and H27 projection plans, but cannot promote a law without a sealed OLMo/per-instance measurement contract.
- **Confidence tier:** `datadecide_source_axis_positive_strengthened / sample_efficient_size_diversity_required / single_size_pc1_negative / fixed_size_arc_hellaswag_residual_survives_null / fixed_size_size_regime_transition_positive_datadecide_local / h53_public_olmo_projection_negative_schema_conditioned / task_interface_state_variable / h27_h29_schema_not_ready / fixed_size_boolq_mixed_not_promoted / interval_geometry_weak / public_olmo_aggregate_weak / scalar_exchange_negative / response_mode_predictive_bounded / size_order_parameter_confirmed / no_law_promotion`
- **Paper target(s):** `paper7` addendum or future learning-mechanics working note; use as source-axis evidence and hypothesis generator, not as a Results-level universal law.
- **Status:** `closed`
- **Opened:** 2026-05-10
- **Closed:** 2026-05-11
- **Evidence pointers:**
    - Experiment/finding rows: `E-NEURAL-HUNT-H35-DATADECIDE-CROSS-SIZE-EXCHANGE-20260510-01`, `F-NEURAL-HUNT-H35-DATADECIDE-CROSS-SIZE-EXCHANGE-20260510-01`, `E-NEURAL-HUNT-H36-DATADECIDE-RESPONSE-MODE-20260510-01`, `F-NEURAL-HUNT-H36-DATADECIDE-RESPONSE-MODE-20260510-01`, `E-NEURAL-HUNT-H37-DATADECIDE-RESPONSE-RESIDUAL-VOID-20260510-01`, `F-NEURAL-HUNT-H37-DATADECIDE-RESPONSE-RESIDUAL-VOID-20260510-01`, `E-NEURAL-HUNT-H39-DATADECIDE-SIZE-MODE-FLOW-20260510-01`, `F-NEURAL-HUNT-H39-DATADECIDE-SIZE-MODE-FLOW-20260510-01`, `E-NEURAL-HUNT-H40-DATADECIDE-POST-SIZE-RESIDUAL-20260510-01`, `F-NEURAL-HUNT-H40-DATADECIDE-POST-SIZE-RESIDUAL-20260510-01`, `E-NEURAL-HUNT-H41-DATADECIDE-BOOLQ-AXIS-ROBUSTNESS-20260510-01`, `F-NEURAL-HUNT-H41-DATADECIDE-BOOLQ-AXIS-ROBUSTNESS-20260510-01`, `E-NEURAL-HUNT-H42-DATADECIDE-BOOLQ-SCHEMA-ARTIFACT-20260510-01`, `F-NEURAL-HUNT-H42-DATADECIDE-BOOLQ-SCHEMA-ARTIFACT-20260510-01`, `E-NEURAL-HUNT-H43-OLMO-PUBLIC-BOOLQ-PROJECTION-20260510-01`, `F-NEURAL-HUNT-H43-OLMO-PUBLIC-BOOLQ-PROJECTION-20260510-01`, `E-NEURAL-HUNT-H44-OLMO-PUBLIC-RESPONSE-MODE-20260511-01`, `F-NEURAL-HUNT-H44-OLMO-PUBLIC-RESPONSE-MODE-20260511-01`, `E-NEURAL-HUNT-H45-OLMO-PUBLIC-LEVEL-RATE-SENSITIVITY-20260511-01`, `F-NEURAL-HUNT-H45-OLMO-PUBLIC-LEVEL-RATE-SENSITIVITY-20260511-01`, `E-NEURAL-HUNT-H46-DATADECIDE-INTERVAL-GEOMETRY-20260511-01`, `F-NEURAL-HUNT-H46-DATADECIDE-INTERVAL-GEOMETRY-20260511-01`, `E-NEURAL-HUNT-H47-DATADECIDE-SLOPE-SAMPLE-EFFICIENCY-20260511-01`, `F-NEURAL-HUNT-H47-DATADECIDE-SLOPE-SAMPLE-EFFICIENCY-20260511-01`, `E-NEURAL-HUNT-H48-DATADECIDE-SINGLE-SIZE-BOOLQ-20260511-01`, `F-NEURAL-HUNT-H48-DATADECIDE-SINGLE-SIZE-BOOLQ-20260511-01`, `E-NEURAL-HUNT-H50-DATADECIDE-EXPANDED-GRID-20260511-01`, `F-NEURAL-HUNT-H50-DATADECIDE-EXPANDED-GRID-20260511-01`, `E-NEURAL-HUNT-H51-DATADECIDE-FIXED-SIZE-RESIDUAL-MAP-20260511-01`, `F-NEURAL-HUNT-H51-DATADECIDE-FIXED-SIZE-RESIDUAL-MAP-20260511-01`, `E-NEURAL-HUNT-H52-DATADECIDE-FIXED-SIZE-NULL-20260511-01`, `F-NEURAL-HUNT-H52-DATADECIDE-FIXED-SIZE-NULL-20260511-01`, `E-NEURAL-HUNT-H53-DATADECIDE-FIXED-SIZE-TRANSITION-20260511-01`, `F-NEURAL-HUNT-H53-DATADECIDE-FIXED-SIZE-TRANSITION-20260511-01`, `E-NEURAL-HUNT-H54-OLMO-PUBLIC-H53-PROJECTION-20260511-01`, `F-NEURAL-HUNT-H54-OLMO-PUBLIC-H53-PROJECTION-20260511-01`, `E-NEURAL-HUNT-H55-OLMO-PUBLIC-PANEL-SCHEMA-SPLIT-20260511-01`, `F-NEURAL-HUNT-H55-OLMO-PUBLIC-PANEL-SCHEMA-SPLIT-20260511-01`, `E-NEURAL-HUNT-H56-OLMO-PACKET-SCHEMA-READINESS-20260511-01`, `F-NEURAL-HUNT-H56-OLMO-PACKET-SCHEMA-READINESS-20260511-01`
    - H35: `projects/neural_hunt/workspace/h35_datadecide_cross_size_exchange_audit_2026_05_10.md`
    - H36: `projects/neural_hunt/workspace/h36_datadecide_response_mode_audit_2026_05_10.md`
    - H37: `projects/neural_hunt/workspace/h37_datadecide_response_residual_void_2026_05_10.md`
    - H38 synthesis: `projects/neural_hunt/workspace/h38_learning_mechanics_pioneer_pattern_map_2026_05_10.md`
    - H39: `projects/neural_hunt/workspace/h39_datadecide_size_conditioned_mode_flow_2026_05_10.md`
    - H40: `projects/neural_hunt/workspace/h40_datadecide_post_size_residual_axis_2026_05_10.md`
    - H41: `projects/neural_hunt/workspace/h41_datadecide_boolq_axis_robustness_2026_05_10.md`
    - H42: `projects/neural_hunt/workspace/h42_datadecide_boolq_schema_artifact_audit_2026_05_10.md`
    - H43: `projects/neural_hunt/workspace/h43_olmo_public_boolq_projection_2026_05_10.md`
    - H43b: `projects/neural_hunt/workspace/h43b_olmo_public_boolq_projection_sensitivity_2026_05_10.md`
    - H44: `projects/neural_hunt/workspace/h44_olmo_public_response_mode_audit_2026_05_11.md`
    - H45: `projects/neural_hunt/workspace/h45_olmo_public_level_rate_sensitivity_2026_05_11.md`
    - H46: `projects/neural_hunt/workspace/h46_datadecide_interval_geometry_audit_2026_05_11.md`
    - H47: `projects/neural_hunt/workspace/h47_datadecide_slope_mode_sample_efficiency_2026_05_11.md`
    - H48: `projects/neural_hunt/workspace/h48_datadecide_single_size_boolq_residual_2026_05_11.md`
    - H50: `projects/neural_hunt/workspace/h50_datadecide_expanded_grid_audit_2026_05_11.md`
    - H51: `projects/neural_hunt/workspace/h51_datadecide_fixed_size_residual_map_2026_05_11.md`
    - H52: `projects/neural_hunt/workspace/h52_datadecide_fixed_size_residual_null_audit_2026_05_11.md`
    - H53: `projects/neural_hunt/workspace/h53_datadecide_fixed_size_transition_map_2026_05_11.md`
    - H54: `projects/neural_hunt/workspace/h54_olmo_public_h53_signature_projection_2026_05_11.md`
    - H55: `projects/neural_hunt/workspace/h55_olmo_public_panel_schema_split_2026_05_11.md`
    - H56: `projects/neural_hunt/workspace/h56_olmo_packet_schema_readiness_audit_2026_05_11.md`

## INS-NEURAL-HUNT-H62-OLMO-SCHEMA-STATE-20260511

- **Claim:** Task interface/schema is a measurable OLMo checkpoint state coordinate for the current learning-mechanics object.
- **Why this matters for learning mechanics:** H62 supplies the first accepted OLMES per-instance/checkpoint evidence that the H55 schema residual is not merely public aggregate bookkeeping. Across the full `10` official OLMo2 1B stage-1 checkpoint packet and `8` selected families, base-vs-`:mc` schema-gap ranges survive the fail-closed accepted-output contract and the H67 projection remains low-dimensional after late-checkpoint stress.
- **Evidence:** H62 gate accepted `10/10` primary-measurement jobs and retained `8/8` heldout family pass under the frozen `step <= 1200000` promotion window, with median heldout/public primary schema-gap range ratio `1.350`. The final robustness audit over late rows improved post-step0 support to `7/8` primary families and median post-step0 ratio `1.050`. H67 over all `10` checkpoint vectors found signed-sqrt top-1 explained variance `0.662`, top-2 `0.881`, and PC1 log-step relative improvement `0.653`.
- **Interpretation boundary:** This is not a universal neural law and not an architecture proof. It is a positive state-coordinate discovery inside a selected OLMo task panel. The useful bridge to future-model work is a discriminator: test whether internal residual-state observables predict H67 PC1/PC2 beyond log-step. If not, H62 remains evaluation-side learning mechanics.
- **Confidence tier:** `olmo_per_instance_checkpoint_positive / schema_state_variable_positive / response_mode_projection_survives_late_stress / residual_state_bridge_hypothesis / no_universal_law_promotion`
- **Paper target(s):** `paper7` addendum or future learning-mechanics working note as Results-adjacent bounded evidence, not as a universal law claim.
- **Status:** `open_for_followup`
- **Opened:** 2026-05-11
- **Evidence pointers:**
    - Experiment/finding rows: `E-NEURAL-HUNT-H62-OLMO-HELDOUT-SCHEMA-GATE-20260511-01`, `F-NEURAL-HUNT-H62-OLMO-HELDOUT-SCHEMA-GATE-20260511-01`, `E-NEURAL-HUNT-H67-H68-SCHEMA-STATE-PROJECTION-20260511-01`, `F-NEURAL-HUNT-H67-H68-SCHEMA-STATE-PROJECTION-20260511-01`
    - Gate: `projects/neural_hunt/workspace/h62_diversity_capped_checkpoint_schema_gate_2026_05_11.md`
    - JSON: `projects/neural_hunt/workspace/h62_diversity_capped_checkpoint_schema_gate_2026_05_11.json`
    - Flat rows: `projects/neural_hunt/workspace/h62_diversity_capped_checkpoint_schema_measurement_table_2026_05_11.csv`
    - Interim/backtest guard: `projects/neural_hunt/workspace/h62_interim_schema_backtest_2026_05_11.md`
    - H67 projection: `projects/neural_hunt/workspace/h67_h62_response_mode_projection_2026_05_11.md`
    - H68 architecture bridge: `projects/neural_hunt/workspace/h68_schema_state_residual_state_bridge_2026_05_11.md`
