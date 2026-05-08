---
id: PATTERN-001
name: friction_debate
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: [debate, dialectic, two-sides, conflict, ambiguous, contested]
  structural: [conflicting_evidence, decision_under_uncertainty, prior_verdicts_disagree]
  problem_classes: [hard_mathematical_residual, pre_category_emergence, apparatus_self_audit]
spawn:
  mode: sequential_friction
  rounds: 5
  subagents:
    - role: champion_exist
      description: Argues the proposition exists / construction succeeds / theorem holds
      tools: [read]
    - role: champion_nonexist
      description: Argues nothing exists / construction fails / theorem false
      tools: [read]
    - role: arbiter
      description: Synthesizes Round-5 joint verdict + tightens theorem statement
      tools: [read, write_verdict]
output_schema: friction_verdict_v1
fallback: PATTERN-002  # darwin_idea_killer
preconditions:
  - construction_freedom: at least one champion can attempt explicit construction
  - orthogonal_pressure_since_last_run: prior iteration was NOT another Pattern-1 on same residual
  - recursion_depth: 0_or_1  # max 2 consecutive Pattern-1 deployments before mandatory Reducer
deployment_rules:
  - rule_1_construction_freedom: verify at least one champion has freedom before spawning
  - rule_2_orthogonal_pressure: at least one orthogonal pattern between Pattern-1 iterations
  - rule_3_recursion_depth: ≤2 consecutive Pattern-1 on same residual
  - rule_4_10x_criteria: output must meet ≥1 of {compiled_constructor, compiled_falsifier, residual_split, executable_test, promotion_gate} or downgrade to review-note
  - rule_5_top_of_funnel: question must be FRESH, not residual-grinding
  - rule_6_pre_spec_locked_before_deployment: pre-registration file (criteria + verdict alphabet + scoring rule) MUST exist as a committed git artifact BEFORE the first agent dispatch. Operator must record `pre_spec_sha` (full commit hash) in the orchestration_state directory before round_1.json is written. If `pre_spec_sha` is empty, missing, or points to a commit timestamped AFTER the earliest agent dispatch log entry, the deployment is automatic INSUFFICIENT_EVIDENCE on all criteria. No retroactive pre-spec.
  - rule_7_verdict_alphabet_locked: verdicts MUST be drawn from the fixed alphabet `{PASS, FAIL, PARTIAL, INSUFFICIENT_EVIDENCE}`. Compound qualifiers ("STRONG WEAK PASS", "GENUINE PASS", "PROVISIONAL PARTIAL"), charity grades, and any new label coined during scoring are automatic INSUFFICIENT_EVIDENCE for the affected criterion AND a catalog-level catch under ANTI-PATTERN-007. The arbiter has no authority to extend the alphabet mid-debate.
  - rule_8_criteria_locked_before_dispatch: the criteria set (the list of disjoint questions the joint verdict will answer) MUST be enumerated, frozen, and committed inside the pre-spec file referenced by `pre_spec_sha`. Adding, removing, refining, or re-weighting criteria after the first agent dispatch is automatic INSUFFICIENT_EVIDENCE on the changed criteria AND requires a new pre_spec_sha + a new deployment id (the prior deployment is closed). Criterion drift is not "tightening".
chain_position: primary  # this pattern starts a chain typically
related_patterns:
  - PATTERN-002 (darwin_idea_killer — chained on output)
  - PATTERN-008 (three_leg_verification — chained on theorem output)
references:
  - https://arxiv.org/abs/2402.06782 (Khan et al. 2024 — closest published analog)
  - https://arxiv.org/html/2603.27404v1 (Heterogeneous Debate Engine, Mar 2026)
---

# Pattern 1 — Friction Debate

## Problem

Single-perspective LLM analysis converges on whichever frame the agent
defaults to. Parallel critics (existing `debate_orchestrator.py`) catch
position-level issues but don't surface STRUCTURAL conflict. When a
problem is genuinely contested between two frames, the LLM tends to
hedge ("both have merit") or fold to whichever frame the prompt
prejudices.

Friction-mode adversarial debate forces both frames to attempt their
strongest case, then forces each to identify the OPPONENT'S exact
failure step.

## Pattern

Five-round structure with friction enforced:

1. **ROUND 1 — CHAMPION_EXIST**: assume the proposition holds. Construct
   explicit candidate / proof / mechanism. Use construction freedom.
2. **ROUND 2 — CHAMPION_NONEXIST**: rebut. Identify the EXACT step where
   Round 1 fails. Use construction freedom.
3. **ROUND 3 — CHAMPION_EXIST**: respond. Either repair or concede a
   specific class.
4. **ROUND 4 — CHAMPION_NONEXIST**: tighten verdict.
5. **ROUND 5 — JOINT VERDICT**: synthesize. Final answer + precise
   theorem statement OR explicit counterexample.

State persistence: `projects/{project}/orchestration_state/{task_id}/round_{k}.json`
with structured rebuttal references.

## Why it works

- Friction forces EXIST agent to attempt actual constructions (not
  aesthetic speculation).
- Friction forces NONEXIST agent to produce concrete proofs (not vague
  "no such thing").
- Joint-verdict format eliminates ambiguity.
- The CHAMPION_EXIST role acts as natural antibody to laundering — agent
  self-rebuts when construction fails.

Empirically validated 2026-05-08: 7 deployments produced 3 genuine clean
theorems (Bohr-Mean Enstrophy Identity finite-Σ, Conditional Infinite-Σ
Extension, Pressure-AP Dichotomy) + Time-Dependent Rank-1 Preservation +
Rank Dichotomy. 2 deployments caught as over-claims by post-hoc audit
(Pattern-1 #7 pressure-term-skipped; rabbit-hole catch in Pattern-1
recursive-on-own-residual).

## When to deploy

- Conflicting prior verdicts (single-perspective bias)
- Conjectured theorem needs sharpening to its sharpest form
- Pivot is contested between alien-math panels — adversarialize them
- Top-of-funnel SHARP question (NOT residual-grinding)

## Process preconditions (rules 6-8) — enforceable, not aspirational

Rules 1-5 (above) gate WHO and WHAT. Rules 6-8 gate the META-EPISTEMIC
shape of the deployment record. These were added 2026-05-08 after
catch #31 (substrate-visibility selection bias) found that META-DARWIN
catches with code outputs were addressed but META-DARWIN catches that
were process-only (charity-grade qualifier inflation, deployment-time
pre-spec laundering, cross-vocabulary criterion-selection rigging) were
left unaddressed.

**Rule 6 — `pre_spec_locked_before_deployment`**

The pre-registration file MUST be authored, committed, and its commit
hash recorded in `orchestration_state/{task_id}/pre_spec_sha.txt`
BEFORE any subagent receives a prompt. The operator (or wrapper) must
verify:

- the file at `pre_spec_sha` contains the criteria list, the verdict
  alphabet, and the scoring rule,
- the commit timestamp at `pre_spec_sha` is strictly earlier than the
  earliest dispatch log entry,
- the orchestration runner refuses to write `round_1.json` if
  `pre_spec_sha.txt` is absent or empty.

If any check fails, the entire deployment is INSUFFICIENT_EVIDENCE.
There is no retroactive pre-spec, no "the pre-reg captures what we
intended", no "the pre-reg was finalized while the agents were
warming up". The commit timestamp is the only honest signal.

**Rule 7 — `verdict_alphabet_locked`**

The verdict alphabet is fixed at `{PASS, FAIL, PARTIAL, INSUFFICIENT_EVIDENCE}`.
The arbiter (Round 5) selects exactly one from this set per criterion.

- No compound qualifiers ("STRONG WEAK PASS", "PARTIAL-PARTIAL",
  "GENUINE PARTIAL").
- No charity grades ("WEAK PASS with caveat", "PROVISIONAL PASS").
- No newly-coined mid-scoring labels.
- Any label outside the alphabet is automatic INSUFFICIENT_EVIDENCE
  for the affected criterion AND records a catalog-level catch under
  ANTI-PATTERN-007 (charity_grade_inflation).

If a verdict genuinely lies between PASS and FAIL, the answer is
PARTIAL. If the evidence does not support any of {PASS, FAIL, PARTIAL},
the answer is INSUFFICIENT_EVIDENCE. The alphabet is exhaustive by
design; "we needed a finer label" is the failure mode this rule
catches.

**Rule 8 — `criteria_locked_before_dispatch`**

The criteria set (disjoint questions the joint verdict answers) is
locked at `pre_spec_sha`. After the first agent dispatch:

- adding a new criterion is automatic INSUFFICIENT_EVIDENCE on that
  criterion AND closes the current deployment (a new deployment id +
  new pre_spec_sha is required to score the added criterion),
- removing a criterion is automatic INSUFFICIENT_EVIDENCE on the
  removed criterion (it is recorded as INSUFFICIENT_EVIDENCE in the
  verdict, not deleted),
- refining a criterion (changing wording in a way that changes which
  evidence counts) is treated as removal+addition.

The failure mode this rule catches: criterion drift after seeing
each agent's attack vector — a form of cross-vocabulary criterion-
selection rigging (ANTI-PATTERN-009).

## Anti-pattern

**RABBIT HOLE**: applying Pattern 1 recursively to its own residual
without orthogonal pressure between iterations. After 2 consecutive
Pattern-1 deployments on the same problem class, a META-META-META audit
is mandatory before any 3rd deployment.

**OVER-CONFIDENCE**: claiming "5/5 clean theorems" when honest score
(after audit) is ~1.5/5. Each output must pass 10x criteria gate.

**FRICTION COLLAPSE**: when residual class is exotic enough that EXIST
champion has no construction freedom, friction becomes ritual. Pivot
to (a) explicit construction agent, (b) literature sweep, or (c)
honest "open in 2026" call.

## Concrete example

2026-05-08 ~01:00 — question "does any non-constant bounded smooth
stationary 3D NS solution exist with finite Bohr-Fourier spectrum?".

- Round 1: ABC flow / Beltrami / multi-shell tilted shears tried;
  conceded mid-round (Beltrami P((u·∇)u) = 0 collapses to ν Δu = 0
  forcing constant)
- Round 2: Bohr-mean enstrophy identity ν M[|∇u|²] = 0 derived; transport
  + pressure terms vanish under div=0
- Rounds 3-5: convergent verdict u ≡ 0; Beltrami loophole closed;
  sharpness audit identified open frontier (infinite-Σ AP)

Result: clean rigorous theorem (Bohr-Mean Enstrophy Identity for finite
Σ) shipped as Lean file `ns_trackb_bohr_mean_enstrophy_identity.lean`.

## Cross-references

- `pattern1_failure_mode_inversion_2026_05_08.md` — 5 deployment rules
- `agent_orchestration_meta_patterns_2026_05_08.md` — full pattern catalog
- `pattern1_rabbit_hole_catch_2026_05_08.md` — anti-pattern catch
