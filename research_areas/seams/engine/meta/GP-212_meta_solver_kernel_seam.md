# GP-212 — Meta-Solver Kernel (Seam)

> **Seam metadata** · `seam_id:` GP-212 · `track:` engine · `status:` active draft 2026-05-04; pre-spec debate. · `last_updated:` 2026-05-09


**Status:** active draft 2026-05-04; pre-spec debate.
**Owner:** generalization-of-substrate-discipline
**Depends on:** GP-148 (mining infrastructure), GP-149 (mining findings), GP-151 (classifier telemetry downgrade), GP-086 (gate harness / cage discipline), GP-053 (seam-spec invariant), GP-104 (rubric authoring), GP-133 R4 (rubric_mode governance), INV-10
**Visibility:** private (first-mover IP — the gate-package taxonomy is novel contribution)

---

## 1. Problem statement

ZTARE has accumulated substantial substrate-specific discipline: charters, rubrics, gates, cage_meta classes, anti-pattern catalogs. Each new substrate today is hand-tuned by the operator + research director. The mining infrastructure (GP-148/149) showed that the failure modes ZTARE catches are *epistemic-discipline classes, not domain-specific* — they cross many projects. Translation: the gates that catch them should be substrate-agnostic.

The kernel partially mechanizes this:

- `src/ztare/validator/weakest_link_classifier.py` runs a regex classifier at runtime (GP-149 I-2/I-3)
- `docs/concepts/anti_pattern_catalog.md` is canonical reference; injected via `inject_antipattern_catalog` rubric flag
- `src/ztare/validator/rubric_mode_resolver.py` applies defaults per rubric_mode (Newton/Kepler/calibration)
- `cage_meta.substrate_class` dispatches behavior per substrate type (`lean_proof` is a recent example)
- `scripts/public/mining/*` produce the falsification dictionary, pivot effectiveness, climb triggers, score ceilings

The cross-LLM audit (GP-151 §8) found: fine-grained LLM classifier labels disagree across providers (48% three-way agreement, fails 60%). Super-class collapse to 3 classes (`structural_blocker` / `ceiling_breaker` / `other`) jumps to 75%. **Verdict was PATH_C_ONLY: keep runtime classifier observability-only, do not adopt live class-based routing.**

This seam is the explicit recognition that:

1. The kernel HAS a partial meta-solver (anti-pattern injection + classifier + substrate_class dispatch + rubric_mode defaults)
2. The cross-LLM block constrains how aggressive class-based routing can be
3. The MISSING piece is a substrate-level (not iteration-level) generalization: given a charter, identify its problem class, and instantiate the gate package proven to work for that class

GP-212 articulates that missing piece. It is not a new layer; it is the formalization and cross-substrate generalization of existing kernel pieces.

---

## 2. The four-step path

### 2.1 Step 1 — refresh the mining corpus (Phase 2 of this work, in flight)

Re-run the miner on the ~2608-record archive (1621 new logs since GP-149's 2026-04-24 run). Identify which gates and which interventions correlate with score climb across substrate classes. Specifically: are the GP-149 findings (pivot effectiveness varies by cluster, tail-generalization is the central blindspot, persistence > cleverness) stable under the new corpus, or has the distribution shifted?

If stable, the meta-solver inherits a validated foundation. If shifted, the mining itself produces the next set of patterns to mechanize.

This step is currently in progress (Stage 1 archive refreshed: 2608 records). LLM sub-classifier patch to use Gemini 2.5 Flash-Lite is the open work item.

### 2.2 Step 2 — problem-class taxonomy (the new thing)

Today: substrate classes are documented per-rubric in `cage_meta.class` and `cage_meta.substrate_class`. Existing values: `theory`, `proof_target`, `1d`, `audit`, `closed_form_constant`, `literature`, `nd_features`, `lean_proof`. These are useful but ad hoc; new classes get added when a new substrate type appears.

The meta-solver upgrade: a documented taxonomy of problem classes with structured metadata. Each class has:
- A short name and one-paragraph definition
- A canonical example substrate (project that exemplifies the class)
- The gate package proven to work for this class (mined from past projects)
- Anti-pattern emphasis (which sub-classes of `anti_pattern_catalog.md` matter most for this class)
- Default rubric_mode and gate flags

Initial classes (extracted from existing substrate runs):
- `qualitative_thesis_governance` — gp169 AID-MCVP, gp117 soft-governance, paper8 consciousness
- `formal_proof_lean` — gp211 paper8 lean proofs, gp139 lean hardening
- `quantitative_law_discovery` — gp159–161 Discovery Engine, gp140 Chebyshev
- `numerical_obstruction_audit` — NS phase 5* work
- `structural_diagnostic` — gp154 distribution shift, gp163d gravity
- `cross_domain_methodology` — paper7 substrate-prober

The taxonomy lives at `docs/concepts/problem_class_taxonomy.md` (proposed) and is referenced by rubric authoring + meta-solver instantiation.

### 2.3 Step 3 — gate-package recommender

Given a charter, classify the problem class, then recommend the gate package. Concretely: a function `recommend_gate_package(charter_text) -> {rubric_mode, gates_to_enable, gates_to_disable, anti_pattern_inject_mode}` that runs in the rubric-authoring step (or in `make generate-gp`).

The recommender's source of truth is the problem-class taxonomy (Step 2) plus the mined hit rates per gate per class (Step 1).

**Anti-tautology guard.** The recommender must not auto-apply gates without operator review on a new substrate. Default behavior: produce the recommendation, surface it in the charter authoring flow, require operator confirmation before launch. This avoids the failure mode the cross-LLM audit named: routing decisions that depend on LLM-judgment-dependent class labels propagating through the kernel without scrutiny.

### 2.4 Step 4 — auto-instantiation with cross-LLM consistency check

Once Step 3 is operator-confirmed for a substrate, the gate package is instantiated automatically into the rubric. **But:** any class-based routing decision that used an LLM-classified label must pass the cross-LLM consistency check from GP-151. If the label disagrees across providers below the 90% gate, the recommender falls back to PATH_C (observe-only, no live routing) and surfaces the disagreement to the operator.

This is the discipline that prevents the meta-solver from baking in LLM-aesthetic preferences as if they were structural truth.

---

## 3. What this is and is not

**This IS:**
- An articulation of how to lift existing kernel discipline (substrate_class dispatch, anti_pattern injection, rubric_mode resolver) from per-substrate hand-tuning to substrate-class-aware auto-instantiation
- Grounded in already-mined empirical data (GP-149 findings) and already-validated discipline (GP-151 cross-LLM guard)
- A path to release Mini-ZTARE Flavor B as an open-source artifact backed by the meta-solver kernel

**This IS NOT:**
- A new gate layer. The gates that exist already cover most failure modes; the meta-solver is the *selection* of gates, not new gates.
- A replacement for charter pre-registration. The charter is still operator-written. The meta-solver suggests defaults; it does not override.
- A claim that meta-solving is a substrate-independent algorithm. The mining will tell us empirically which gate combos generalize and which don't. Where they don't generalize, that is itself a finding.
- A claim that LLM-derived problem-class labels are reliable. They are not (per GP-151). The taxonomy must be human-curated with cross-LLM consistency checks on automated routing.

---

## 4. Three uncomfortable truths

### 4.1 The mining we already did may be insufficient

GP-149 ran on 1825 records across 84 projects. The cross-LLM audit (GP-151) found fine-grained labels unstable. If problem-class labels are equally unstable, the meta-solver's classifier is unreliable and the entire Step 3 is suspect.

Mitigation: Step 1 (Phase 2 mining) must include a problem-class consistency check across providers before the taxonomy is treated as data. The 90% threshold from GP-151 super-class collapse should apply to problem-class labels too.

### 4.2 The meta-solver may collapse the operator's discretionary signal

Currently the operator picks gates by judgment. If the meta-solver auto-recommends, the operator's residual signal (which gates work for which problem in this specific case) gets erased. That signal IS data — the operator's ad hoc choices, made under pressure, are themselves a labeled corpus.

Mitigation: log every operator override of the recommender's suggestion. The override log becomes new mining input. The recommender stays operator-confirmable, never operator-bypassing.

### 4.3 The "release as open source" path could dilute the moat

Mini-ZTARE Flavor B (the open-source thesis-hardening loop) draws its move-set from the labeled corpus + the gate-package recommender. Releasing the code without the corpus is fine. Releasing the recommender's logic AND the gate-package taxonomy gives competitors the meta-discipline without giving them the labeled data.

Mitigation: open-source the recommender's INTERFACE (a function signature, a documented taxonomy schema) but require external users to supply their own corpus + their own labeled gate-package mappings. The toolkit is a framework; the operator's mined mappings remain proprietary.

---

## 5. Open questions

1. **Where does the problem-class classifier live?** Embedded in `make generate-gp`? A new `src/ztare/meta_solver/classify.py` module? The latter is cleaner but adds a kernel surface.

2. **Cold-start problem.** A new project has no debate logs yet. The classifier classifies based on charter text alone. Is charter text enough to distinguish `qualitative_thesis_governance` from `quantitative_law_discovery`? Yes, probably — the charter's evidence pointers + admissible outcomes are diagnostic. But this needs validation.

3. **Compositional substrates.** Some substrates straddle two classes (e.g., gp211 paper8 lean proofs is BOTH `formal_proof_lean` AND `qualitative_thesis_governance` since it links a Lean proof to a governance corollary). Does the recommender pick one class, or compose two? The composition path is more interesting.

4. **Refresh cadence.** When does the taxonomy + recommender refresh? Tied to mining cadence (every N new projects) or operator-triggered? The same question we answered for Falsify's corpus.

5. **Relation to Mini-ZTARE Flavor B.** The open-source product is the meta-solver kernel applied to one problem class (defending a thesis under iterative attack). Should the open-source artifact include the taxonomy, or only the loop? The taxonomy is operator IP per §4.3 mitigation.

---

## 6. Internal epistemic panel review (multi-perspective critique)

Five perspectives critique GP-212 §1–§5 inline. Each perspective gives one acceptance, one pushback, one proposed change.

### Perspective 1 — kernel maintainer (cares about backward compatibility, gate determinism, side-effect blast radius)

- **Accepts:** the recommender as operator-confirmable (not operator-bypassing). The cross-LLM consistency check from GP-151 is correctly applied to problem-class labels.
- **Pushes back:** the proposed `src/ztare/meta_solver/` directory is a new top-level kernel surface. Adding new kernel surfaces increases blast radius for changes. Prefer extending `src/ztare/validator/rubric_mode_resolver.py` with the recommender logic, since it is already in the gate-resolution path.
- **Proposed change:** keep the recommender logic in `rubric_mode_resolver.py` or a sibling file under `validator/`, not in a new `meta_solver/` directory. Match existing kernel conventions.

### Perspective 2 — research director (cares about substrate launch quality, charter authoring overhead, false-positive routing)

- **Accepts:** the taxonomy of problem classes is a useful artifact even without auto-instantiation. Documenting it would improve charter authoring even if Step 3 (recommender) is never built.
- **Pushes back:** Step 3 changes the operator's relationship to the gate-selection step. The operator currently learns the gate library by hand-picking; the recommender shortcuts that. Risk: the operator becomes worse at gate selection because they stop practicing it. (Same critique that the design panel made about case-method instructors and AI tutors.)
- **Proposed change:** the recommender surfaces its reasoning at confirm-time, not just its output. "I recommended `inject_antipattern_catalog: true` because this charter classifies as `qualitative_thesis_governance` and that flag has +14.4 mean Δ on this class per GP-149." Operator sees the why, not just the what.

### Perspective 3 — mining-derived-discipline owner (cares about empirical grounding, false generalizations, cross-LLM stability)

- **Accepts:** the explicit acknowledgment of GP-151's PATH_C_ONLY constraint. The seam does not pretend the cross-LLM block doesn't exist.
- **Pushes back:** the proposed problem-class taxonomy in §2.2 has six classes seeded from existing projects. Six is small. With six classes and ~84 projects, the average class population is 14 projects. That is below the threshold for stable per-class hit rates per the GP-149 N≥20 guidance.
- **Proposed change:** before instantiating the recommender (Step 3), the taxonomy must populate to ≥20 projects per class. That requires either (a) more substrate runs, or (b) re-classifying existing projects against the taxonomy. The second is cheap and immediately unblocks Step 3.

### Perspective 4 — Munger multi-disciplinary (cares about second-order effects, lollapalooza, inversion, what could make this fail)

- **Accepts:** the operator-override-as-data feedback loop in §4.2. That is correct second-order thinking — the override is not a bug, it is signal.
- **Pushes back:** the seam frames the meta-solver as a positive accumulation. Inversion: what makes the meta-solver fail spectacularly? Most likely: the recommender becomes a shortcut that operators rely on without reading; a new substrate gets the wrong class label; the gate package deployed is actively harmful (e.g., inject anti-pattern catalog when the substrate is a math-discovery substrate where catalog injection would constrain the solution space). The failure mode is "competent automation worsens novel-substrate quality."
- **Proposed change:** add a "novel-substrate detection" gate. If the charter's text-similarity to all existing problem classes is below a threshold, the recommender refuses to auto-suggest, marks the substrate as `novel`, and forces hand-tuning. Inversion-via-anomaly. Same idea as `honest_low_match` in Falsify.

### Perspective 5 — Falsify operator (cares about how meta-solver deliverables become user-facing artifacts)

- **Accepts:** the §4.3 mitigation that open-sources interface + framework but keeps mined gate-package mappings proprietary. That is the right moat structure.
- **Pushes back:** the open-source piece (Mini-ZTARE Flavor B, listed in §5 open question 5) is a substantial separate artifact. Coupling it to GP-212 kernel completion creates a dependency that might delay both. The two efforts can run in parallel.
- **Proposed change:** decouple. GP-212 kernel work (Steps 1–4) is a research direction with months of work. Mini-ZTARE Flavor B can ship without it, using the existing anti_pattern_catalog + weakest_link_classifier as its move-set. The kernel work upgrades Mini-ZTARE later.

---

## 7. Munger multi-disciplinary synthesis

The five perspectives above converge on a sharper, smaller GP-212 than the original §2 proposed. Synthesizing through Munger's lens (mental models, lollapalooza, inversion, second-order, circle of competence, checklist):

**Inversion:** the question is not "what makes the meta-solver work" but "what makes it fail in a way that destroys ZTARE's epistemic integrity." Three failure modes:

1. **Aesthetic capture** (Perspective 4): recommender entrenches whichever LLM-aesthetic is currently dominant. Mitigation: novel-substrate detection + cross-LLM consistency check (already in §2.4 and §6 P4).

2. **Skill atrophy** (Perspective 2): operator becomes worse at gate selection because they stop practicing. Mitigation: recommender surfaces reasoning at confirm-time, not just output (§6 P2).

3. **Insufficient sample** (Perspective 3): per-class N too small for stable hit rates. Mitigation: bootstrap by re-classifying existing projects before deploying the recommender (§6 P3).

**Lollapalooza:** what compounds positively here? When mining → taxonomy → recommender → operator-override-log → mining cycle closes, each iteration sharpens the recommender. **But** GP-149 already refuted Lollapalooza-style stacking for the failure-class catalog. Don't assume the same compounding holds for the gate-package recommender. Treat each interaction (mining ↔ taxonomy ↔ recommender ↔ override-log) as a separate empirical claim until validated.

**Circle of competence:** ZTARE is competent at adversarial verification of arguments and theses. Extending it to "any problem" overruns the circle. The meta-solver should generalize within ZTARE's class of problems (epistemic verification under structured pressure), not outside it. The seam should not claim more than this.

**Checklist (concrete pre-implementation gates):**

1. Phase 2 mining must complete and produce stability check on GP-149 findings under the bigger corpus
2. Cross-LLM consistency check must pass at the super-class level (≥75% three-way per GP-151) for problem-class labels
3. Each problem class must have ≥20 projects before its gate-package mapping is deployed
4. Recommender must surface its reasoning + cite the empirical source; never operator-bypass
5. Operator-override log must be wired into the mining input
6. Novel-substrate detection must default to "refuse to auto-suggest"

**Synthesized scope:** GP-212 covers Steps 1–3 (mining, taxonomy, recommender) and explicitly defers Step 4 (auto-instantiation) until the checklist passes. Step 4 may turn out never to be appropriate in its full form; the operator-confirmable recommender may be the right terminal state.

---

## 8. Decision and next moves

**Decided here (subject to operator confirmation):**

- **Scope of GP-212:** Steps 1–3, deferring Step 4 until the §7 checklist passes.
- **Code location:** extend `src/ztare/validator/rubric_mode_resolver.py` (or a sibling under `validator/`) rather than create a new `meta_solver/` directory. Match existing kernel conventions (Perspective 1).
- **Taxonomy artifact:** new file `docs/concepts/problem_class_taxonomy.md` listing the initial six classes with structured metadata.
- **Recommender behavior:** operator-confirmable, surfaces reasoning, never bypasses. Default for novel substrates is "refuse to auto-suggest."
- **Decoupling:** Mini-ZTARE Flavor B (open-source) ships independently of GP-212 completion using existing kernel surfaces. GP-212 upgrades it later.

**Pre-spec deliverables:**

1. Phase 2 mining completion (in flight; LLM classifier pending Gemini Flash-Lite patch)
2. Re-classify existing 84 projects against the proposed problem-class taxonomy
3. Per-class hit-rate population from the new mining corpus

**Spec stage entry conditions:** items 1–3 above must complete before the spec is written.

**Spec scope:** the recommender function signature, the taxonomy file format, the operator-confirmation UI surface, the override-log shape.

---

## 9. Cross-references

- `research_areas/private/seams/engine/GP-148_void_mining_seam.md` — mining infrastructure
- `research_areas/private/seams/engine/GP-149_mining_findings_and_interventions_seam.md` — first-pass findings
- `research_areas/private/seams/engine/GP-151_classifier_telemetry_downgrade_seam.md` — cross-LLM PATH_C constraint
- `docs/concepts/anti_pattern_catalog.md` — current cross-substrate pattern library
- `docs/internal/agent_workflow/rubric_authoring_map.md` — current rubric authoring discipline
- `src/ztare/validator/weakest_link_classifier.py` — runtime classifier (existing)
- `src/ztare/validator/rubric_mode_resolver.py` — existing rubric defaults dispatcher (likely host for the recommender)
- `src/ztare/validator/autoresearch_loop.py` — gate dispatch path

---

*Seam v0 written 2026-05-04 in auto mode. Refresh after Phase 2 mining completes and the checklist in §7 has been re-evaluated.*
