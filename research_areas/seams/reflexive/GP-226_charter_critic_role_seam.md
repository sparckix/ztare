# GP-226 — Charter-Critic Role (Closed-Loop Charter Tuning Against Operator Value-Vector)

> **Seam metadata** · `seam_id:` GP-226 · `track:` reflexive · `status:` open · `last_updated:` 2026-05-09


**Status:** open
**Cabinet:** `reflexive/` (meta-loop on the apparatus's own framing layer)
**Authored:** 2026-05-06
**Trigger:** session running `human_ai_interaction_primitive` qualitative-thesis
substrate where operator (Claude as Director) manually authored two evidence-
section reframe injections (§6, §7) plus a charter-clause amendment (UI-affordance
gate) to escape a score plateau at 65 → 88 in 5 iters with gpt-5.5.

## 1. The empirical observation

The session above produced a position-paper-grade qualitative thesis at score 88,
AND surfaced a missing role. The score-jumping labor was not in the apparatus.
It was in the operator who:

1. Read recent debate logs and identified the panel's repeated weakest-point
   fingerprint (Path B critique recurring; UI specification missing;
   velocity-vs-level under-engaged).
2. Mapped each fingerprint to a known reframe type — named-historical-precedent
   forcing, Path-B-honest framing, level-bound disclosure, UI-affordance
   specification.
3. Authored a durable patch — appended §6/§7 to evidence.txt + amended a rubric
   dimension + added a charter clause.
4. Validated against `scripts/public/validators/validate_rubric.py` pre-flight.
5. Restarted with model upgrade (gpt-4.1 → gpt-5.5).

The implicit operator objective function was **novelty + structural-rigor +
UI-affordance-concreteness**, weighted by feel. The operator made it explicit
mid-session ("novel for me") — confirming that the value-vector is a real
artifact that should be a first-class input, not implicit operator intuition.

## 2. The gap in existing apparatus

Three pieces of in-loop machinery already exist for evidence and prompting; none
operate on the charter:

| Module | Layer | When it fires |
|---|---|---|
| `src/ztare/workspace/compile_evidence.py` | Evidence compilation from `raw/` sources | Pre-iter-1, manual `make compile` |
| `src/ztare/orchestrator/qualitative_evidence_cold_shot.py` | Cold-shot LLM evidence seed | Pre-iter-1 only |
| `src/ztare/orchestrator/cold_llm_seed_requery.py` | Cold-shot RE-query for new evidence seeds | Mid-run on stagnation |
| `src/ztare/orchestrator/forced_reframe.py` | One-iter prompt nudge (REFRAME flag) | Mid-run on stagnation |

`forced_reframe.py` is the closest existing piece: stagnation-triggered, in-loop,
designed for de-anchoring. But it nudges the **mutator briefing for one iter**,
not the **durable charter or rubric**. The reframe pressure dissolves at the next
iter and the apparatus drifts back into the same local optimum.

The "generate-charter" the operator remembers is startup-only scaffold (see
`scripts/public/utilities/scaffold_rubric.py` pattern + manual charter authoring). There is no
charter-critic role.

## 3. Proposed architecture

**Module:** `src/ztare/orchestrator/charter_critic.py` (new).

**V1 scope: POST-RUN dispatch only.** In-iter / mid-run firing is deferred
to V3 (see §3.5). V1 fires once at run completion, emits patches that take
effect on the NEXT run via persisted evidence/charter/rubric edits. This
eliminates failure modes 4d (ping-pong) and most of 4f (three-body
collusion) for the first ship and aligns the trigger model with
`--auto-evolve` (also post-run, mutually-exclusive condition — see §3.5).

**Inputs:**
- Current `project_charter.md`
- Current rubric JSON
- Current `evidence.txt`
- Full debate-log trail for the just-completed run (post-run has full info)
- Score trajectory: champion + per-iter score series + champion-iter index
- `operator_value_spec.yaml` — substrate-specific artifact at project init.

**operator_value_spec.yaml — substrate-specific schema:**

```yaml
# projects/<slug>/operator_value_spec.yaml
substrate_class: qualitative_thesis   # gates which reframe-type taxonomy applies
                                       # (qualitative_thesis | proof_target |
                                       #  nd_features | closed_form_constant | audit)

weights:
  novelty: 0.45                # apparatus-output structural surprise
  falsifiability: 0.25         # observable-design discipline
  operationalizability: 0.20   # concrete-control-taxonomy completeness
  cross_domain_transfer: 0.10

constraints:
  novelty_must_not_dominate_falsifiability: true   # anti-Goodhart
  min_substitution_survival_engagement: 0.6        # Path A/B/C must be honest
  max_charter_patches_per_run: 3
  patch_expiry_runs: 5                             # 4h mitigation — see §4h

mode: advisory   # advisory | auto
                 # default advisory for first 3 substrates per §4-discipline;
                 # promote to auto only after ≥3 substrates with ≥80% operator
                 # approval rate AND zero contamination incidents
```

**CLI override (quick-experiment surface):** environment variables override
the YAML for a single run, logged in run telemetry:

```bash
make loop PROJECT=<p> RUBRIC=<r> \
  VALUE_NOVELTY=0.6 VALUE_FALSIFIABILITY=0.3 VALUE_MODE=advisory \
  ...
```

**Why no natural-language input.** A `--value "natural language"` mode would
require an LLM parse step → silently-wrong semantics surface. The marginal
operator-friction saving (~10 seconds of YAML editing) does not justify
the parse-error blast radius. Defer to V4 if a real need appears.

**Why substrate-specific.** "Novel" means different things per substrate:
qualitative_thesis novel = structural primitive not in published literature;
nd_features novel = new feature decomposition; proof_target novel = new
proof tactic. The reframe-type taxonomy (the 6 buckets in the table below)
is itself qualitative_thesis-biased; numeric substrates need different
buckets. Cross-project taxonomy contamination (4k) is mitigated at the
schema level by requiring `substrate_class` declaration.

**Trigger:** rubric flag `enable_charter_critic: true`. Fires
**post-run** (after the autoresearch_loop's outer for-loop exits, before
final telemetry write). Mutually exclusive with `--auto-evolve` per
the dispatch table in §3.5 — never both in the same run-end.

**Diagnosis:** classify the panel's stuck-on critique into reframe-type buckets.
Initial taxonomy (extensible):

| Fingerprint pattern | Reframe-type | Patch shape |
|---|---|---|
| "regression to labor-economics / tool discourse" | `path_b_honest_engagement` | Append evidence section forcing Path-B/C verdict |
| "empirically fragile / no historical precedent" | `named_historical_retrodiction` | Append evidence section listing N adversarial historical cases requiring retrodiction |
| "level-bound / does not engage capability shift" | `velocity_vs_level_disclosure` | Charter clause requiring level-invariance proof OR scope admission |
| "vague affordance / no concrete UI" | `ui_affordance_specification` | Rubric dimension amendment requiring concrete output spec |
| "vocabulary importation / smuggled primitive" | `vocabulary_neutral_restate` | Charter clause banning specific vocabulary class |
| "single-mode dogma / no task-class typology" | `path_c_decomposition_forcing` | Evidence section listing adversarial task-classes |

Fingerprint matching: bigram-Jaccard against a curated weakest-point corpus,
plus regex on canonical phrasings. Cheap and deterministic; no LLM call needed
for diagnosis.

**Action:** emit a structured patch — typed, sized, sanitation-checked:

```python
@dataclass
class CharterPatch:
    target: Literal["evidence", "charter", "rubric_dimension"]
    section_id: str           # e.g., "§7", "Mode-Fit Gate"
    operation: Literal["append", "replace", "amend"]
    body: str                 # the actual patch content
    reframe_type: str         # for telemetry + dampening
    sticky_until_iter: int    # min iter before re-evaluation
    sanitation_checks: list[str]  # passed gates
```

**Sanitation discipline (mandatory):**
- Charter-contamination check: no GT mentions, no derivations, no oracle
  knowledge (re-uses existing `_preflight_leak_audit` logic from `Makefile`).
- Path-A/B/C distinction preserved: patches cannot collapse the trichotomy.
- Vocabulary check: patches must use the same class of vocabulary the rubric
  declares admissible (info-theory / control-theory / economics / cognitive
  science for human-AI; Bayesian / weak-signal-detection for Fermi).
- Size bound: patch body ≤ 2KB (forces concision).

**Convergence (V1 post-run):**
- Max N patches emitted per run-end dispatch (default N=3).
- Each patch carries `expiry_runs: K` (default K=5; per 4h charter-rot
  mitigation). After K runs without re-attestation by another fingerprint
  match, the patch is auto-flagged for operator review and removed.
- "Frame-failure" telemetry: if 3 consecutive run-ends produce patches and
  champion score has not improved by ≥3 points across them, emit a
  frame-failure signal and halt critic dispatch until operator inspects.
- (V3 only) In-iter mode adds patch-stickiness K iters within a run +
  damping coefficient on patch frequency. V1 does not need these.

## 3.5. Dispatch table — interaction with `--auto-evolve`

Both `--auto-evolve` and the V1 charter-critic fire **post-run**. They are
mutually exclusive at run-end based on the championship score:

| Condition at run-end | Dispatch | Action | Direction |
|---|---|---|---|
| `best_score >= 85` AND `--auto-evolve` enabled | `evolve_rubric()` | Tighten rubric in-place; reset best_score=20 | Anti-Goodhart on the win |
| `best_score < 85` AND `enable_charter_critic` enabled | `charter_critic.dispatch()` | Reframe charter/evidence/rubric-dimension | Escape local optimum |
| `best_score >= 85` AND `enable_charter_critic` AND NOT `--auto-evolve` | `charter_critic.dispatch()` | Same as above; the critic CAN fire on a win when auto-evolve is off (e.g., to mature the framing past the win) | Optional sharpening |
| Neither flag set | no-op | — | — |

The chain that emerges: critic gets you to ≥85 → auto-evolve tightens →
next run climbs harder under tighter rubric → critic kicks in again as the
apparatus stalls on the new rubric → repeat. This is the productive
recursion the operator's "wow" insight pointed at.

## 4. Failure modes (decisive design constraints)

### 4a. Goodhart on the value-vector

If `novelty: 1.0` is the sole utility, the critic chases ever-more-exotic frames;
falsifiability collapses. The thesis becomes a creative-writing exercise that
the judge happens to score well because the judge is also reading the same
weakest-point patterns.

**Mitigation:** mandatory anti-Goodhart constraints in `operator_value_spec.yaml`
(novelty must not dominate falsifiability; substitution-survival floor;
empirical-grounding floor). Default constraints prevent novelty-only operation
even if operator declares novelty-only weights.

### 4b. Rubric-as-eval at the META level

The critic optimizes against the judge's repeated stuck-on patterns. If the
judge is wrong, the critic makes the apparatus more wrong, faster. The
`project_rubric_as_eval` failure mode reproduced one level up.

**Mitigation:** the critic's diagnosis is fingerprint-based (deterministic
pattern match), not judge-utility-based. The critic does not optimize
"satisfy the judge"; it optimizes "force the apparatus to engage a
reframe-type the panel keeps requesting." This is structurally different
from rubric-gaming because the patches are operator-authored taxonomies,
not learned-from-judge-rewards. Caveat: if the panel's repeated complaint
is itself wrong (e.g., the substrate genuinely doesn't admit a Path-B
answer and the judge is mis-reading), the critic will inject pressure
that makes the thesis worse. Mitigated by: max-3-patches cap + frame-failure
telemetry that escalates to operator review.

### 4c. Charter contamination automation

Auto-generated patches could leak GT structure if the critic has any oracle
access (e.g., reads `gate_harness.py`, `verified_axioms.json` from prior
substrates with known answers).

**Mitigation:** charter-critic operates ONLY on (charter, rubric, evidence,
debate logs, value-spec). It cannot read harness files, ground-truth
artifacts, or any project artifact whose contents constitute oracle
knowledge for the current substrate. Enforce by sandboxed file-read
allowlist.

### 4d. Ping-pong / oscillation

Critic and mutator disagree → repeated frame-flips. Score plateaus at
oscillating-mid-tier instead of climbing.

**Mitigation:** patch-stickiness (K iters minimum before re-evaluation).
Damping coefficient on patch frequency — second patch must be N iters
after first; third must be 2N iters after second.

### 4e. De-anchoring depth (knowledge-bound critic)

The §7 PRESSURE-4 H1-H6 retrodiction (algorithmic trading, autoland, FDA
AI/ML clearance, credit scoring, AML, autonomous vehicles) required real
domain knowledge. A critic without external retrieval would generate
vaguer pressures and gain less ground.

**Mitigation:** patch authoring is allowed to call the same cold-shot
LLM the existing `qualitative_evidence_cold_shot.py` uses, with the same
forbidden-domain discipline. Two-tier action:
1. **Light patch** (no LLM) — append a structural pressure from the
   reframe-type taxonomy (e.g., "name 5 historical precedents that
   retrodict the snapback question").
2. **Heavy patch** (LLM-assisted, gated by rubric flag
   `enable_heavy_charter_patches: true`) — call cold-shot to generate
   the actual H1-Hn precedent list with structural commitments stated
   neutrally. Operator-reviewed before commit on first usage; auto-
   commit on subsequent usages within the same project run.

### 4f. The judge-mutator-critic three-body problem

Three LLM-driven roles now optimizing toward partially-overlapping
objectives. Risk of converged collusion (mutator writes what critic
predicts judge wants).

**Mitigation:** critic uses the SAME judge model as scoring (so its
diagnosis matches what the judge will reward) but is briefed with an
adversarial mandate explicitly orthogonal to the mutator's. Periodic
cross-model audit: re-diagnose the last N patches with a different
judge-class model; flag divergences > threshold.

## 5. Why this is reflexive-cabinet, not apparatus-cabinet

`apparatus/` covers Cage / supervisor / instrumentation — the engine's
internal mechanics. This proposal modifies *what gets fed to the engine*
based on *what the engine produced*. That is the meta-loop layer:
self-modifying input under operator-declared utility.

Closest existing reflexive-cabinet seam: `seam_and_miner_review_2026_05_06.md`
(self-recursive improvement via telemetry). GP-226 is the next concrete
instance of that pattern, applied to the framing layer instead of the
primitive layer.

## 6. Test case (cheapest validation)

The session that motivated this seam IS the labeled training pair, BUT
per §8b 4j the validation must include an ablation arm — the original
session conflated patch effect with model upgrade (gpt-4.1 → gpt-5.5
at iter 16).

**Reference trajectory (the motivating session, both interventions present):**
- Project state at iter 5 with score-50s plateau (`human_ai_interaction_primitive`)
- Operator action 1: authored §6 PRESSURE-1/2/3 (task-class decomposition,
  Path-B engagement, velocity-vs-level)
- Resulting score: 65 → 67 over iters 6–15 (organic uptick on §6)
- Operator action 2: authored §7 PRESSURE-4/5/6 (H1-H6 retrodiction,
  Path-B explicit, velocity-vs-level depth) + UI-affordance gate amendment +
  evidence_reload_per_iter flag + model upgrade to gpt-5.5
- Resulting score: 88 in iter 1 of post-restart

**V1 validation protocol (three arms):**

- ARM A — REPLAY: re-run motivating session with critic dispatching post-run
  patches at iters 5, 15. Both interventions present (patches + model upgrade
  at iter 16). Expected: champion ≥85.
- ARM B — ABLATION (model held): same as ARM A but mutator + judge held
  at gpt-4.1 throughout. Isolates patch contribution from model contribution.
  If champion climbs significantly above the gpt-4.1 baseline plateau (~67),
  patches are decisive. If champion stalls at ~67, the original session's
  lift was mostly model-upgrade; critic value is unproven.
- ARM C — UNSEEN: dispatch on `fermi_paradox_discriminator` post-run with
  critic enabled. Out-of-sample test for cross-project taxonomy
  applicability (4k mitigation). Substrate-specific value-spec required;
  the qualitative_thesis taxonomy may apply but the substrate-class
  declaration gates this explicitly.

**Quantitative success criteria:**
- ARM A: champion ≥85; patch-type emission at run-1-end matches one of
  `path_c_decomposition_forcing` / `path_b_honest_engagement` (operator's
  iter-5 patch was primarily the former); patch-type emission at
  run-2-end matches `named_historical_retrodiction` +
  `ui_affordance_specification` + `velocity_vs_level_disclosure`.
- ARM B: ARM-B-champion − gpt4.1-baseline ≥ 10 points to claim
  patch-decisive-ness. <5 points means model upgrade dominated.
- ARM C: champion improvement ≥ 5 points vs no-critic baseline OR
  documented frame-failure with operator-reviewable patch trace.
- False-positive rate (patches emitted when score was climbing organically
  ≥3 points in last 5 iters): ≤10% across all three arms.
- Frame-failure rate: documented per-run; not a pass/fail criterion at V1.

**Sham-arm counterfactual (4l mitigation, deferred to V2):** every Kth
patch run an additional arm where the critic emits a deliberately wrong
reframe-type bucket. If sham arm and real arm produce similar Δscore,
the classifier isn't doing real work. V1 logs the sham-arm artifact
without dispatching it; V2 actually runs it.

## 7. Open questions

1. **Should the operator-value-spec live at project-init only, or be
   re-tunable mid-run?** Mid-run tunability is more flexible but adds another
   surface for operator labor. Default: project-init only; re-tune requires
   explicit `make charter-retune` (analog to `make compile`).

2. **Per-substrate critic variants vs single critic with per-substrate
   reframe-type taxonomy?** Per §8b 4k cross-project contamination critique,
   the V1 default is **substrate-specific from day 1**: single critic
   module, per-substrate-class taxonomy registry indexed by
   `operator_value_spec.yaml::substrate_class`. The 6 initial buckets
   in §3 are registered against `qualitative_thesis` only. Other substrate
   classes (proof_target, nd_features, closed_form_constant, audit) start
   with empty taxonomies; reframe-types are added as real sessions surface
   them. A reframe-type promotes to the "shared" cross-substrate pool only
   after firing productively across ≥2 substrates of different classes.
   This prevents qualitative_thesis-specific failure modes from propagating
   as taxonomy bias to numeric substrates.

3. **Should the critic emit patch CANDIDATES for operator approval, or
   auto-commit?** RESOLVED: two-mode flag in `operator_value_spec.yaml`
   (per the §3 schema). DECISION: **default `advisory` for first 3
   substrates with auto-promotion gate** of (a) ≥3 substrates run with
   advisory, (b) operator approval rate ≥80%, (c) zero contamination
   incidents. Even after promotion to `auto`, retain a kill-switch: an
   `OPERATOR_OVERRIDE_ADVISORY=1` env var the operator can set to force
   advisory mode mid-program if patches start drifting. Charter patches
   are durable + cross-run-persistent (high blast radius); the ~30s
   operator-review cost is cheap insurance against contamination.
   - `mode: advisory` — emits patch to
     `workspace/charter_patch_candidate_<run_id>.md`, operator commits
     via `make charter-commit RUN=<run_id>` (new target).
   - `mode: auto` — auto-commits to evidence/charter/rubric with full
     telemetry trail in `workspace/charter_patches.jsonl`.

4. **Interaction with `forced_reframe.py`?** V1 (post-run) and
   `forced_reframe` (in-iter mutator-briefing nudge) do not conflict —
   they operate on different cadences and surfaces. `forced_reframe`
   continues to fire mid-run as designed; charter-critic V1 fires
   post-run on top of the cumulative trajectory (which may include
   forced-reframe iters). Telemetry note: log forced-reframe firings
   in the run summary so the critic's diagnosis distinguishes
   "stagnation despite forced-reframe" (stronger signal for durable
   patch) from "stagnation without forced-reframe firing" (lighter
   signal). When V3 in-iter mode lands, the resolution rule from the
   prior version applies: forced-reframe fires FIRST one-iter; critic
   fires after +2 iters of persistent stagnation.

5. **Interaction with `enable_post_run_thesis_synthesis` and
   `--auto-evolve`?** All three are post-run dispatchers. Order at
   run-end: (1) thesis synthesis (read-only, produces summary), (2)
   charter-critic OR `--auto-evolve` per dispatch table in §3.5
   (mutually exclusive, score-gated), (3) telemetry write. Post-run
   thesis synthesis output is an INPUT to charter-critic diagnosis —
   the synthesis names the run's decisive claim, which the critic
   uses to disambiguate the panel's weakest-point fingerprints.

6. **Persistence across runs?** Charter patches authored in run N persist
   into the project's `evidence.txt` / `project_charter.md` for run N+1
   automatically. Patches with telemetry tag `experimental` may be reverted
   by operator before re-run.

## 8. Decision points pending operator review (updated 2026-05-06)

Operator decisions reached during 2026-05-06 design discussion are
marked RESOLVED; remaining decisions are open.

- **Cabinet placement** — RESOLVED: `reflexive/`. This is meta-loop,
  not engine internals.
- **Operator-value-spec schema** — RESOLVED: substrate-specific YAML
  (`projects/<slug>/operator_value_spec.yaml`) at project init, CLI
  override via `VALUE_*` env vars, no natural-language input for V1.
  Schema in §3. Cross-project contamination mitigated by mandatory
  `substrate_class` declaration (per 4k).
- **Mode default** — RESOLVED: `advisory` for first 3 substrates,
  promote to `auto` only after empirical patch-quality data clears the
  gate (≥3 substrates, ≥80% approval, 0 contamination). Kill-switch
  retained even in auto mode.
- **Timing** — RESOLVED: V1 post-run only. In-iter is V3. Shipping
  path: post-run advisory V1 → 3 substrates → post-run auto V2 →
  in-iter advisory V3 → in-iter auto V4. Eliminates failure modes
  4d (ping-pong) and most of 4f (three-body) for V1.
- **--auto-evolve interaction** — RESOLVED: mutually exclusive at
  run-end per dispatch table in §3.5. Score-gated (auto-evolve ≥85,
  critic <85; critic-on-win optional when auto-evolve is off).
- **Test-case validation plan** — RESOLVED: three-arm protocol in §6
  (REPLAY / ABLATION-model-held / UNSEEN). Ablation arm addresses
  4j N=1 confound by isolating patch effect from model upgrade.
- **Initial reframe-type taxonomy size** — RESOLVED: 6 buckets, only
  registered against `qualitative_thesis` substrate class. Other
  substrate classes start with empty taxonomies. Promotion to
  cross-substrate "shared pool" requires firing across ≥2 substrate
  classes (per 4k).
- **Patch expiry** — RESOLVED: each patch carries `expiry_runs: K`
  (default K=5); auto-flagged for operator review after K runs without
  re-attestation (per 4h charter-rot mitigation).
- **L2 active-pressures summary header** — SHIPPED 2026-05-06 PM:
  `src/ztare/orchestrator/briefing_compression.py::_build_active_pressures_summary`.
  At run-start, replaces accumulated REFRAME PRESSURE block content with a
  ~500–1100 byte summary of which primitives have active patches and at
  what cross-run counts; renders the PRIMITIVE-CEILING DIRECTIVE at the
  TOP of the briefing where mutator attention is highest. Rubric flag
  `enable_briefing_compression: true`. Non-destructive — disk artifacts
  unchanged.
- **L3 stale-pressure expiry** — SHIPPED 2026-05-06 PM:
  `briefing_compression.py::_select_blocks_to_keep`. REFRAME PRESSURE
  blocks whose source patches are older than `expiry_runs` (default 5)
  are suppressed from the mutator-visible view; ledger lookups identify
  which on-disk blocks correspond to expired ledger entries. Rubric flag
  `briefing_compression_expiry_runs: 5`.
- **Same-primitive supersession (BONUS)** — SHIPPED 2026-05-06 PM: when
  multiple committed patches in the same primitive exist (e.g., 4
  velocity_vs_level patches all in BOUND), only the latest is shown to
  the mutator; older same-primitive patches are tagged superseded. Rubric
  flag `briefing_compression_supersede_same_primitive: true`. First
  measured impact on real HAI state: 4 superseded blocks dropped from
  charter; total briefing reduced 49.5KB → 37.1KB (~25% reduction)
  before iter-1.
- **Bug fix in `_apply_patch`** — SHIPPED 2026-05-06 PM: charter patches
  were being written with a double-H2 (section_id wrapper + patch body
  H2) which broke briefing-compression block-matching signatures. Fixed
  to detect when body already starts with `## ` and skip the wrapper.
- **Taxonomy-extension proposer** — OPEN: 4g notes that the taxonomy
  is fixed-point — the critic only reapplies known reframes, doesn't
  discover new ones. Mitigation in 4g proposes a
  `taxonomy_extension_proposer` that emits proposal artifacts on
  fingerprint-no-match. Defer decision to spec phase: build the
  no-match-detection in V1 (cheap; emits artifact), build the
  proposer in V2.
- **Sham-arm counterfactual** — DEFERRED to V2: log the artifact in
  V1 without dispatching the sham arm (per 4l). Cost is small; V1
  collects the data, V2 actually runs the counterfactual.
- **Value-spec recursion (4i)** — OPEN: the value-spec is itself a
  one-shot. Mitigation in 4i defers a `value_spec_critic` until the
  first-order critic has a track record. V1 collects telemetry on
  patch effectiveness per weight regime (cheap); V2+ decides whether
  to build a value-spec critic.

## 8b. Failure-mode review (added 2026-05-06 PM, second-Claude pass)

The §4 failure modes are well-thought-through. The following six are
either underweighted or absent. Listed in decisive-first order.

### 4g. Taxonomy is fixed-point — critic only reapplies KNOWN reframes

The 6-bucket reframe-type taxonomy is operator-curated. The critic
classifies into buckets and emits a patch FROM that bucket. **It does
not discover new reframe types.** If the substrate exhibits a
weakest-point fingerprint that doesn't match any taxonomy bucket, the
critic either (a) classifies into the wrong bucket and emits a wrong
patch, or (b) hits the no-match path and falls through.

This is the same problem at the META level that the original "operator
labor" problem is at the OBJECT level. GP-226 mechanizes operator
*application* of reframes; it does NOT mechanize operator
*discovery* of new reframe types. The novel-reframe labor remains with
the operator.

**Mitigation:** add a `taxonomy_extension_proposer` to the critic. When
no bucket matches the fingerprint above a similarity threshold, emit a
proposal artifact (`workspace/reframe_proposal_<iter>.md`) with the
unmatched fingerprint + a "what reframe-type might this be?" prompt
seed for operator review. Don't auto-extend the taxonomy from
unmatched fingerprints — that's the rubric-as-eval failure mode at the
TAXONOMY level. But surfacing the unmatched cases is honest.

### 4h. Charter rot — patches accumulate and harden across runs

§7 question 6 says "charter patches authored in run N persist into run
N+1 automatically." Over many runs, charters become palimpsests of
patch decisions whose original triggering conditions may no longer
apply. The fingerprint that justified `path_b_honest_engagement` patch
in run-3 might not apply in run-15, but the patch is still on the
charter, biasing the mutator.

**Mitigation:** every patch carries an expiry condition, not just
`sticky_until_iter`. Options: (a) auto-expire after K runs unless
re-attested, (b) a periodic charter-cleanup pass that drops patches
whose triggering fingerprint hasn't recurred in last M iters, (c) a
charter-vintage telemetry that surfaces patches > N runs old for
operator review.

### 4i. operator_value_spec is itself a one-shot — meta-self-reference

GP-226 is "fix the charter's one-shot-ness by introducing a recursive
critic against operator-valued parameters." But the parameter spec
itself (`operator_value_spec.yaml`) is one-shot at project init. The
same logic that says "charter should be recursive" applies recursively
to the value-spec: as a project progresses, novelty tends to matter
less and falsifiability more (mature work prioritizes rigor over
exploration). The spec's weights should themselves drift.

The seam acknowledges this as a Q under "open questions" (§7 question
1) and defaults to project-init only. **That default exports the
recursion problem one level up — operator now has to manually
`make charter-retune`.** Worth flagging that the proposed solution
recreates the original problem at a finer scale.

**Mitigation:** at minimum, make the value-spec carry telemetry: which
patches the critic emitted under each weight regime, what Δscore each
produced. Operator's decision to retune is then data-driven, not
intuition-based. Stronger: add a `value_spec_critic` that proposes
weight adjustments based on patch effectiveness — but defer this until
the first-order critic has a track record.

### 4j. N=1 validation — patch effect confounded with model upgrade

§6 test case proposes validating against the
`human_ai_interaction_primitive` session that motivated the seam. That
session's score climb (50 → 88) had two confounded interventions:
(a) operator's §6/§7 charter patches, (b) gpt-4.1 → gpt-5.5 model
upgrade at iter 16. The seam's validation plan doesn't separate these.

If a critic emits structurally-similar patches and the test session is
re-run with the SAME model upgrade timing, the patch contribution
can't be isolated from the model upgrade contribution.

**Mitigation:** ablation arm. Re-run the test session with critic on
+ model held at gpt-4.1 throughout. If score climbs, patches are
decisive. If score stalls at the gpt-4.1 ceiling, the §6 test case
mostly measured model upgrade and the critic's lift is unknown.

### 4k. Cross-project taxonomy contamination

§7 question 2 defaults to "single critic, taxonomy indexed by
`cage_meta.type`." The 6 initial buckets came from one substrate
(`human_ai_interaction_primitive`). Their applicability to
`fermi_paradox_discriminator` or other future substrates is a research
question, not a default.

**Mitigation:** start with substrate-specific taxonomies from day 1.
Allow promotion of a reframe-type to a "shared" pool only after it
fires productively across ≥ 2 substrates. The shared-pool gating
prevents the first substrate's failure modes from propagating as
taxonomy bias to all future substrates.

### 4l. Patch attribution is unfalsifiable as designed

When a critic emits a patch and the next iter's score changes, the
seam attributes the delta to the patch. But: the mutator is also
drifting iter-over-iter; debate logs evolve; rubric flags may have
changed. Without a no-patch counterfactual, patch effect is
correlational, not causal.

§4b's mitigation ("structurally different from rubric-gaming because
the patches are operator-authored taxonomies") addresses one failure
mode but not this attribution one.

**Mitigation:** when the critic emits a patch, log a `patch_sham_arm`
counterfactual: what the iter would have looked like with the
WRONG patch type from the taxonomy (a random other bucket). Run the
sham counterfactual once every K patches. If the sham arm produces
similar score deltas to the real patch arm, the critic's
classification isn't doing real work.

### Summary table of additional failure modes

| # | Mode | Severity | Mitigation in seam? |
|---|---|---|---|
| 4g | Taxonomy fixed-point — no novel reframe discovery | high | absent — propose taxonomy_extension_proposer |
| 4h | Charter rot — patches accumulate across runs | high | absent — propose patch expiry |
| 4i | value_spec is itself a one-shot (meta-self-reference) | medium | acknowledged as Q, deferred |
| 4j | N=1 validation conflates patch + model upgrade | medium | absent — propose ablation arm |
| 4k | Cross-project taxonomy contamination | medium | acknowledged in §7 Q2, defaults wrong way |
| 4l | Patch attribution unfalsifiable | low-medium | absent — propose sham-arm counterfactual |

## 8c. Briefing-compression discovery (2026-05-06 PM)

After 8 buckets accumulated and unmatched fingerprints kept appearing
each run, operator surfaced the principle (per `feedback_invert_compress_primitives`):
the taxonomy itself needs compression. Two layers of compression shipped
in one session:

**Compression layer #1 — taxonomy → primitives.** 8 buckets compressed
to 3 epistemic primitives (DERIVE / BOUND / OBSERVE). Each bucket is now
annotated with `primitive: <DERIVE|BOUND|OBSERVE>`. Synthetic
`primitive_*` buckets handle fingerprints that match a primitive but no
specific bucket (the fallback that drove unmatched-count from 2 to 0 on
HAI). Cross-run patch counter now operates at TWO levels: per-bucket
(`_count_cross_run_patches_for_reframe`) and per-primitive
(`_count_cross_run_patches_for_primitive`). Primitive-level escalation
fires at count ≥5 — the PRIMITIVE-CEILING DIRECTIVE forces meta-argument
or scope-reduced eigenquestion.

**Compression layer #2 — briefing accumulation.** Per-project briefing
artifacts (evidence.txt + project_charter.md) accumulate REFRAME PRESSURE
blocks across runs. After 5+ runs they bloat to 50KB+, drowning signal.
The L2/L3 + supersession compression operates non-destructively at
read-time in autoresearch_loop, suppressing stale and superseded blocks
from the mutator-visible view while leaving disk artifacts intact. First
measured impact: 25% briefing reduction with PRIMITIVE-CEILING DIRECTIVE
surfaced at top.

The two compression layers compose: primitive taxonomy compresses
horizontally (8 buckets → 3 primitives); briefing compression compresses
vertically (history of patches → latest-per-primitive + summary header).
Together they address the operator's "the taxonomy keeps popping up,
universal language for compression" insight.

## 9. Forward links

- **Spec to author after seam approval:**
  `specs/active/reflexive/GP-226_charter_critic_role_spec.md` — implementation
  blueprint with file-paths, function signatures, telemetry schema.
- **Pre-registration:** none required (no novel scientific claim; this is
  apparatus mechanization).
- **Memory entry to add at scaffold time:**
  `feedback_charter_critic_loop.md` — once the critic is shipped and run
  on the Fermi project, capture lessons learned (false-positive rate,
  patch-quality distribution, frame-failure incidence).

## 10. ZTARE_BOARD entry

Add row in `research_areas/private/ZTARE_BOARD.md`:

```
| GP-226 | charter_critic_role | reflexive | open-seam | 2026-05-06 |
| | V1 = post-run-only closed-loop charter tuning against substrate-      |
| | specific operator value-vector. Mechanizes the operator labor         |
| | surfaced in human_ai_interaction_primitive run (score 50→88 via 2     |
| | manual reframe injections + UI gate amendment). Mutually exclusive    |
| | with --auto-evolve at run-end (score-gated dispatch). 6 initial       |
| | reframe-type buckets registered against qualitative_thesis only;      |
| | other substrate classes start empty (4k cross-project contamination   |
| | mitigation). Advisory mode default; auto promotion after ≥3           |
| | substrates with ≥80% approval + 0 contamination incidents. Each       |
| | patch carries expiry_runs (4h). Three-arm validation protocol         |
| | (REPLAY / ABLATION-model-held / UNSEEN) addresses 4j N=1 confound.    |
| | V3 = in-iter mode with stickiness + dampening; deferred until V1+V2   |
| | track record exists.                                                  |
```
