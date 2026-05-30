# GP-168 Org Design Discovery — Unfalsifiability Without Exogenous Closure

> **Seam metadata** · `seam_id:` GP-168 · `track:` mission · `status:` active | done | abandoned · `last_updated:` 2026-05-09


**Status**: open seam, default private (first-mover IP, not shipped, contains operational findings)
**Opened**: 2026-04-27
**Substrate**: gp168_org_design_discovery
**Provenance**: 38 evaluations across multiple ZTARE runs on `org_topology` substrate; verified directly from `workspace/eval_history.jsonl`.

## TL;DR

Two-Channel Federated Bicameral Gating (TC-FBG) and its variants reach repeatable high scores on the gp168 substrate (peaks: 81, 82, 82, 79, with one outlier at 93). They consistently fail at the same axis:

> **Bicameral architectures provide consistency but not closure. Closure requires exogenous resource pressure.**

This is the org-design analogue to a Gödel-style limit: an internal-consistency framework cannot decide its own termination.

## What's verified empirically

### Repeated peaks (positive results)
The bicameral / dual-confirmation family scores consistently in the 60–93 range across many independent ZTARE iterations. Peaks at idx=13 (score 81), idx=20 (82), idx=24 (82), idx=16 (79), and one outlier at idx=34 (93). This is not a single lucky iteration — it's a robust attractor for the substrate.

### Consistent weakness (the limit)
Every peak gets cut down on the same decisive assumption:

- **Score 81 (TC-FBG, idx=13)** — judge weakest-point: *"Catastrophic reliance on persistent, enforceable independence between dual confirmation paths. If this independence is ever broken, the anti-drift guarantee fails instantly and undetectably."*
- **Score 93 (variant, idx=34)** — judge weakest-point: *"The thesis's assumption that physically, operationally, supply-chain, and lifecycle irreducible audit/confirmation path independence is never achievable — even in principle — is an extrapolation."*
- **Latest run (2026-04-27, REVERTED to score 20–22)** — judge terminal verdict: *"Catastrophic absence of any mechanism for pruning or prioritizing the organizational design space in light of persistent empirical negative evidence, combined with unfalsifiability (no threshold for when forward observables could close the hypothesis space); the thesis asserts eternal openness rather than defining when or how to focus resources, making it simultaneously untestable and paralyzing for actual design."*

The pattern across all three: **architectural consistency does not provide a stopping rule.** The decisive axiom (dual-confirmation independence, audit-path irreducibility) is itself open-textured — every iteration can refine it without ever closing it.

## The structural finding

Bicameral organizations can guarantee process-level consistency (no single principal can unilaterally write the substrate). They cannot guarantee:

1. **Termination**: when to stop searching the design space
2. **Resource allocation**: which open question to fund next
3. **Closure**: when accumulated negative evidence justifies abandoning a branch

These three are the same thing under different names. They are NOT properties an internal architecture can supply — they require **exogenous resource pressure** (a budget, a deadline, an investor's clock, a mortality timeline). The minute the organization is given infinite resources, the bicameral pattern produces "epistemically honest but organizationally paralyzing" theses (the judge's exact phrasing).

## Distinction from physics substrates

This is the inverse of gp163d (modified gravity). Physics substrates have *intrinsic* falsification gates:
- Mercury PPN: |y/g_bar − 1| < 4e-10 closes branches whether the operator wants them closed or not
- Holdout MRE: < 0.35 closes branches by data, not by decision

Org topology has no such gates. Whether dual-confirmation independence is "achievable in principle" is not a question data can settle — it depends on the operator's threat model, their resource clock, and their adversary's capabilities. All of those are exogenous to the substrate.

**Implication for ZTARE on org-topology substrates**: the loss function must include an exogenous-pressure term, not just internal consistency. Otherwise the apparatus correctly converges on "eternal openness" theses that are unfalsifiable by construction.

## Connection to the broader programme

- **gp163d (physics)** — substrate with intrinsic gates, ZTARE finds closed-form falsifications
- **gp168 (org)** — substrate without intrinsic gates, ZTARE finds an *unfalsifiability theorem*
- Both are valid science. The second is the more interesting epistemological result.

The pair together is a paper: *"Bicameral architectures provide consistency but not closure; closure requires exogenous resource pressure."* This is the org-design analogue to Gödel — an internal-consistency framework cannot decide its own termination.

## What to NOT do next

- **Don't relaunch** gp168 ZTARE expecting a closed-form winner. The substrate's ceiling is the unfalsifiability result itself — additional iters will keep finding TC-FBG variants and keep getting REVERTED on the same termination axis.
- **Don't conclude "TC-FBG failed"** — it's the strongest known stable thesis pattern. The failure is structural, not implementation-level.
- **Don't write up TC-FBG alone** — the paper-strength claim is the *pair* (TC-FBG + its termination limit), not either half.

## What to do next

1. **Write up the pair as a paper** — the cleanest framing is "Bicameral consistency without closure: an unfalsifiability theorem for self-governing organizations." Paper 7 has §11.5 already; this could be a second interim section in paper 7 or a new short paper.
2. **If pursuing further empirically**: design a substrate where exogenous resource pressure IS encoded (e.g., a budget-constrained variant where each open hypothesis carries a per-iter audit cost). That moves the closure problem inside the substrate and lets ZTARE find the optimal termination rule. This is a substrate redesign, not a model search.
3. **The Research Director M-form (GP-172) is the operational pattern that USES this finding** — Director proposes (consistency), Principal disposes (closure via budget). See `seams/protocol/GP-172_research_director_mform_role_seam.md`. The whole bicameral-with-exogenous-clock architecture this project runs on is itself the demonstration.

## Related seams (added 2026-04-27 reorg)

- `seams/protocol/GP-172_research_director_mform_role_seam.md` — operational instantiation (Director/Principal split)
- `seams/substrates/GP-173_comparative_closure_clock_substrate_seam.md` — proposed substrate to compare clock types empirically
- `seams/interfaces/D4_distribution_form_factor_seam.md` — commercial form-factor (distro vs SaaS) implications

This seam is the empirical mission finding (necessity of closure clocks). The other three address operational, comparative-empirical, and commercial dimensions respectively.

## Cost ledger

Latest run (10-iter, gpt4.1/gpt4.1, EVOLVE=1):
- Mutator: $0.4967 (113k input, 30k output)
- Judge: $0.5420 (150k input, 27k output)
- Total: $1.04, final score 20 REVERTED, but the REVERSION verdict IS the finding.

## Open questions (NOT to relaunch ZTARE on this substrate)

- Can we encode exogenous resource pressure as a substrate feature without making it a parameter the mutator can game? (Unclear; would need a substrate-redesign seam.)
- Is the unfalsifiability result formal-provable (Gödel-style), or only empirical-from-this-run? Worth a 1-page sketch before publishing.
- What's the relationship to Goodhart's Law at the org-design layer? gp168 may be Goodhart-on-bicameral-process — every metric the architecture tracks gets gamed by the architecture itself.

---

## Addendum 2026-04-27 — Operational Architecture Synthesis (Panels A + B)

This addendum records the decision that translates the GP-168 unfalsifiability finding into the actual file layout, schema, and runtime that runs in this repo. Two cross-domain expert panels were convened on 2026-04-27 to resolve overlapping infrastructure (Panel A) and the right primitive for principal-stated intent (Panel B). Their outputs are synthesized below into a single operational decision the principal will execute as a refactor.

### Why this addendum exists

The GP-168 finding ("bicameral architectures provide consistency but not closure; closure requires exogenous resource pressure") was first translated into code as a parallel tree at `org/clocks/`, `org/budgets/`, `org/escalations/` with a `closure_daemon.py`. The principal flagged two concerns:

1. **Spaghetti risk.** GP-132 lightweight goals (`org/goals/`) and GP-070 formal goal orchestrator already track deadlines, costs, escalations, and audit transitions. The new tree was *parallel* to these, not *integrated* with them. Panel A was convened to resolve this.
2. **Wrong primitive at the top.** The existing `org/goals/` is task-shaped and ZTARE-flavored (write a seam, draft a spec, run a sandbox). It has no Objective layer above it (the "why" was implicit) and no measurable Key Results alongside it (success was undefined). Panel B was convened to validate the proposed OKR-shaped uplift.

The two debates resolve into one architectural decision because they describe the same artifact stack at different vertical positions: Panel A is about *how the closure-pressure layer attaches to the work-item layer*; Panel B is about *what the work-item layer should look like above the task tier*. They compose without conflict.

### Panel A (closure-pressure tree collapse) — converged decision

Five seats (distributed-systems engineer, modern SaaS workflow architect, biologist, alien-AI futurist, organizational designer) converged on:

- **Single source of truth per fact.** Deadlines and budgets are *fields on the work item*, not separate objects. The parallel `org/clocks/` and `org/budgets/` trees are deleted.
- **Single escalation channel.** GP-070's executive inbox at `ztare_workspace/gates/pending/` wins; `org/escalations/` is deleted as persistence and becomes a *view* over gates.
- **Single write-ahead log.** GP-070's `transitions.jsonl` absorbs all clock and budget events; the parallel audit logs are deleted.
- **Daemon as stateless poller.** `closure_daemon.py` survives but rewrites: it scans the work-item tree, evaluates time and budget predicates, and submits state-transition *requests* through the GP-070 orchestrator API. The orchestrator owns mutation; the daemon owns scheduling.
- **What survives from GP-168 as code.** The daemon survives as poller; the Telegram bot survives as transport. What was decisive about GP-168 — *time-pressure auto-resolution, budget-pressure auto-resolution, exogenous-oracle escalation as the explicit escape valve* — is preserved as behaviors on the existing infrastructure rather than a parallel layer.

### Panel B (OKR uplift) — modified-and-validated decision

Six seats (OKR practitioner from the Doerr/Grove lineage, modern SaaS workflow architect, solo-operator skeptic, biologist on multi-level objective hierarchies, distributed-systems data engineer, alien-AI futurist) converged on:

- **Three-tier hierarchy is correct.** Objective → Key Result → Task. The timescale ratio between top intent (years) and atomic task (hours) is ~10⁴, which is one decade per tier — well-calibrated. Two tiers would be too coarse, four too ceremonial.
- **KRs as separate files, not as a YAML array on Objectives.** Files give clean git diffs, KR-level audit trail, reassignability, agent-friendly mutation, and zero migration cost if KRs ever need to become first-class. The "Objective as self-contained file" virtue is preserved by the dashboard (Orbit) joining the three trees on render — display layer's job, not storage layer's.
- **`measurement_locus: self | world` is decisive.** A KR scored by the principal himself drifts toward self-flattering scores ("Cells that measure their own success become tumors" — biologist seat). At least one `world`-measured KR per Objective; the daemon enforces this on Objective creation.
- **`kr_type: output | outcome | health_metric` is required.** Forces the principal to face that he wrote three outputs and zero outcomes for an Objective titled "strong cross-domain reception." The schema cannot make him write outcome KRs but can refuse to let him pretend output KRs are outcomes.
- **Continuous score 0.0–1.0 at closure, not pass/fail.** Real OKR practice scores KRs continuously; 0.7 on a stretch KR is a win; 1.0 across the board means sandbagging. Add `score: float | null` and `score_rationale: str` set at quarter close.
- **Append-only `check_ins:` log on each KR.** Captures confidence drift; daemon escalates on two consecutive declining check-ins with no task work toward the KR.
- **No `review_cadence: weekly` field.** The cadence is whatever the daemon enforces via Telegram nudges. Solo-scale practice cannot sustain a separate weekly ritual; it will be ignored within a month.
- **`horizon: target_date | open`** — replace quarter-bounded with target-date-when-real-deadline OR open-ended for durable rolling Objectives. Solo Objectives outlive quarters; quarter-binding forces fake Objectives.
- **Authoring mode hedge.** `authoring_mode: human | agent_proposed` field anticipates the alien-AI-futurist endpoint (in 5–10 years agents read principal chat and propose Objectives; the field marks provenance now and becomes decisive later).

### Composed decision (the actual refactor)

The two panels compose as:

```
org/objectives/<obj_id>.md           ← new: Panel B (Objective layer)
org/key_results/<kr_id>.md           ← new: Panel B (KR layer, files not array)
org/tasks/{pending,active,done}/     ← renamed from org/goals/ ; Panel B
   each task carries closure-pressure fields per Panel A
org/clocks/                          ← DELETE: Panel A
org/budgets/                         ← DELETE: Panel A
org/escalations/                     ← DELETE: Panel A (use ztare_workspace/gates/pending/)
ztare_workspace/gates/pending/       ← single escalation channel, GP-070 owns
research_areas/private/goals/.../transitions.jsonl  ← single write-ahead log, GP-070 owns
scripts/public/control/closure_daemon.py            ← REWRITE: stateless poller over org/tasks/, org/key_results/, org/objectives/
orbit/src/server/telegram-bot.ts     ← REWIRE: push from ztare_workspace/gates/pending/, render OKR tree
orbit/src/components/ClosureClockPane.tsx → ObjectiveTreePane.tsx ← REWIRE Panel A indicators onto Panel B tree
```

### Concrete schemas (canonical for implementation)

**`org/objectives/<obj_id>.md`** frontmatter:
```yaml
objective_id: <snake_case>
title: "<short title>"
horizon: target_date | open
target_date: 2026-06-30 | null
status: active | done | abandoned
created_by: daniel_alami
created_utc: <iso>
closure_deadline: <iso> | null
auto_resolution: archive_with_postmortem
authoring_mode: human | agent_proposed
```

**`org/key_results/<kr_id>.md`** frontmatter:
```yaml
kr_id: <snake_case>
objective_id: <parent_objective_id>
description: "<one sentence>"
measurement: "<how it's measured, concrete>"
measurement_source: daemon | principal
measurement_locus: self | world
kr_type: output | outcome | health_metric
target: "<numeric or boolean threshold>"
status: pending | on_track | at_risk | done | failed
score: float | null
score_rationale: "<one line>" | null
last_measured_utc: <iso> | null
review_overdue_threshold_days: 14
check_ins:
  - {utc: <iso>, confidence: 0.7, note: "<one line>"}
created_utc: <iso>
```

**`org/tasks/{pending,active,done}/<task_id>.md`** frontmatter (renamed from `goals/`):
```yaml
task_id: <snake_case>
objective_id: <parent_objective_id> | null
kr_id: <kr_id> | null
title: "<short>"
priority: low | medium | high | urgent
assigned_to: role.<role_id>
autonomous_scope_ok: true | false
status: pending | active | done | abandoned
closure_deadline: <iso> | null
warn_at_pct: 0.7
escalate_at_pct: 0.9
auto_resolution: deny | approve | escalate | archive | defer
budget_cap_usd: <float> | null
budget_spent_usd: <float>
budget_exhaust_action: close_partial | escalate | kill
created_by: <member_id>
created_utc: <iso>
```

### Closure-pressure cascade (who acts when)

**Objective expiry (`closure_deadline` reached, status still `active`):** Daemon posts Telegram alert with Objective title + KR statuses + scores; principal taps `done | abandon | extend` within 7 days; default on no response = `auto_resolution: archive_with_postmortem` with daemon-generated stub.

**KR measurement-overdue (`last_measured_utc` older than `review_overdue_threshold_days`):** If `measurement_source: daemon`, daemon attempts re-measurement; on success updates and appends check-in. On failure or `measurement_source: principal`, KR flagged `at_risk`, surfaced in Telegram digest. Second consecutive overdue cycle → `at_risk` permanent, surfaces in Objective closure prompt.

**Task expiry:** Daemon warns at `warn_at_pct`, escalates at `escalate_at_pct`, applies `auto_resolution` at deadline. Agents handle task-level auto-resolution where the mandate permits; principal can intervene any time.

All escalations route to `ztare_workspace/gates/pending/`. All transitions append to `transitions.jsonl`. Single write-ahead log; single escalation channel; daemon submits requests, orchestrator owns mutations.

### Telegram + Orbit role split

**Telegram (compressed, push):**
- Daily digest: "Q2 stance: 3 objectives active, 8 KRs (5 on-track, 2 at-risk, 1 overdue), 12 tasks active, 3 imminent." Counts only — tree structure stays in Orbit.
- Closure prompts: surfaced one at a time, Objective > KR > Task priority order.
- Check-in nudges: weekly per Objective, single message asking "confidence on these N KRs unchanged?" Principal taps thumbs-up to extend `last_measured_utc` without opening any file.
- Inline-button acks route to `ztare_workspace/gates/pending/` resolutions. Telegram owns no state.

**Orbit (full, pull):**
- Renders the OKR tree by joining `org/objectives/`, `org/key_results/`, `org/tasks/`.
- Pressure indicators at every level: time-to-deadline on Objectives, days-since-measurement on KRs, budget/deadline gauges on tasks.
- Postmortem view: closed Objectives show their KR scores, check-in trajectory, linked task outcomes in one page.

### Minimum viable practice (honest)

~5 minutes per week (in Telegram): respond to KR check-in nudges; respond to overdue-measurement prompts where `measurement_source: principal`; glance at digest counts.

~30 minutes per quarter (in Orbit): score each closing KR 0.0–1.0 with one-line rationale; read auto-generated postmortems and edit if wrong; author or refine 1–3 Objectives for next horizon.

If the principal finds himself spending 30 min/week on OKR maintenance, the system is being misused and should be pruned, not the principal's behavior.

### Theatre-detection signal

Daemon computes a per-Objective **honesty score** at closure: `(count of world-measured KRs with non-null last_measured_utc in the closure window) / (count of world-measured KRs)`. If this drops below 0.5 for two consecutive Objective closures, daemon posts: *"OKR honesty score declining. The system may have collapsed into theatre. Consider deleting or simplifying."* Defining the kill signal now is the only thing that keeps the architecture from outliving its honesty.

### Migration plan (each step independent and reversible)

1. Create empty `org/objectives/` and `org/key_results/` directories.
2. Rename `org/goals/{pending,active,done}/` → `org/tasks/{pending,active,done}/` via `git mv`. Update hardcoded paths in daemon and Telegram digest.
3. Add optional `objective_id:` and `kr_id:` fields to existing task frontmatter, default `null`. Existing daemon ignores them.
4. Author 1–3 initial Objectives. Backfill `objective_id` on currently-active tasks where the link is obvious; skip ambiguous tasks.
5. Author KRs as files in `org/key_results/`. Require at least one `measurement_locus: world` outcome KR per Objective.
6. Wire the daemon's measurement loop for `measurement_source: daemon` KRs — start with the easiest case (count of `done` tasks under the Objective).
7. Wire Telegram digest to compute and render the OKR tree summary.
8. Wire Orbit to render the full tree by joining the three directories.
9. Run for one cycle (4–6 weeks). Observe what rots. Adjust schema before adding more Objectives.

After step 1: delete the parallel GP-168 tree (`org/clocks/`, `org/budgets/`, `org/escalations/`).

### What this means for the GP-168 finding itself

The unfalsifiability theorem stands. Bicameral architectures still provide consistency but not closure. The operational answer is now wired into the substrate: closure pressure at every tier (Objective deadline, KR measurement cadence, Task clock+budget), executed by a stateless daemon over fields on existing artifacts, escalating through the existing executive inbox to the principal as exogenous oracle. The principal's Telegram surface is the *bounded-attention reflex* the panels diagnosed. The OKR honesty score is the *failure-detection signal* that prevents the architecture from outliving its honesty.

The GP-168 paper draft (Paper 7 §11.5) does not change. The implementation that demonstrates the finding now exists in `org/` with a clean schema instead of a spaghetti parallel tree.

### Open questions carried forward (Panel B)

- Should Objectives be NL-first with agent-derived frontmatter today, or human-authored YAML today with NL-first as a future migration? (`authoring_mode:` field hedges; revisit after first real Objective is authored.)
- Should Objectives outlive quarters or align to quarters? (`horizon: target_date | open` accommodates both; default `open` for solo scale.)
- Does the daemon's auto-postmortem produce useful postmortems, or noise? (Untested; first Objective closure tells us.)
- What happens to tasks whose Objective is archived mid-flight? (Recommended: cascade-archive with daemon listing affected tasks in the closure prompt so principal can rescue any that should survive.)
- File-vs-array at strict solo scale: weakest panel consensus; took files because asymmetry favors them.

### Provenance

- Panel A run 2026-04-27 ~13:00 UTC, 5 seats, ~1900 words.
- Panel B run 2026-04-27 ~14:00 UTC, 6 seats, ~3800 words.
- Both panels coordinated by general-purpose agent against the same operational briefing; no codebase access; converged independently on compatible structural conclusions.

---

## v3 META-HARDENING REFRAME (2026-05-02)

### What v3 is

v3 of `gp168_org_design_discovery` is launched not because the
unfalsifiability theorem is in doubt, but because the principal
flagged a substrate-prior bias concern in the v1/v2 candidate-family
vocabulary: "we drew on marine/ecological primitives for the org
design but I wonder if a meta hardening of org would make sense
across all potential angles."

The v2 charter's strip test caught apparatus-specific leakage
(proper-noun substitution, M-form vocabulary). It did NOT catch
substrate-prior leakage — the case where every family on the
hypothesis space comes from the same intellectual tradition (6 of 9
v2-suggested families inherited from marine/ecological/biological
priors). v3 closes this gap.

### What changed

1. **Substrate prior is now the sixth fingerprint axis.** v2 had 5
   axes (Principal authority, Coordination locus, Information flow,
   Death-spiral containment, Locus of priority decision). v3 adds:
   Marine/ecological | Corporate/industrial | Military/command |
   Religious/monastic | Market/economic | Legal/juridical |
   Open-source/commons | Cooperative/mutual |
   Performing-arts/improvisational | Computational/formal | Other.

2. **Two-substrate-prior rule.** The mandatory ≥3 disjoint families
   must span ≥2 distinct substrate priors. Three families all from
   the same prior fails meta-hardening, regardless of how disjoint
   their topologies look on the other 5 axes.

3. **Substrate-paraphrase test.** Each decisive primitive must
   be paraphraseable into ≥1 other substrate prior without losing
   its solve-the-invariant property. Primitives that survive the
   paraphrase are substrate-invariant; primitives that don't are
   substrate-leaked instantiations.

4. **Exogenous-pressure source naming.** Per paper7 §11.6, every
   family must name its concrete exogenous pressure source for
   closure. Internal-only mechanisms re-enact the v1 score-20
   paralysis attractor.

5. **Incumbent description refreshed.** v2 described "M-form +
   Orbit". The current incumbent is a 4-substrate-prior composition:
   - GP-168 OKR addendum (corporate/industrial)
   - RD-1.12 live co-drive (computational/formal)
   - agent_utilization caps (corporate/industrial)
   - paper7 §11.6 exogenous-pressure clock (market/economic)

   v3 theses that propose a single-prior alternative must defend
   why monoculture beats the existing multi-prior mix.

### Why this is a v3, not a new project (gp192 was the alternative)

The principal asked: "shall we run again ztare on ztare but for the
org/ design aspect?" and on the question of project reuse: "let's
reuse the project we had". The v2 substrate (charter, evidence,
rubric, raw/, debate logs) is preserved as audit and reused as the
v3 starting point. Specifically:

- v2 charter archived to `project_charter_v2_archive.md`.
- v2 evidence archived to `evidence_v2_archive.txt`.
- v2 debate logs (50+ files in `debate_log_iter_*.md`) preserved
  as audit history.
- v2 goodhart_log entries (2026-04-27 timestamps) referenced by v3
  evidence.txt §3b as the empirical anchor for "v2 collapse: deep-
  on-one-family, not collapse-onto-one-fingerprint."

The v3 reframe is in:
- `projects/gp168_org_design_discovery/project_charter.md` (rewritten)
- `projects/gp168_org_design_discovery/evidence.txt` (rewritten)
- `rubrics/gp168_org_design_discovery.json` (added 4 new criteria:
  Substrate-Prior Disjointness, Substrate-Paraphrase Survival,
  Exogenous-Pressure Source Naming, Multi-Substrate-Prior
  Composition Defense).

### What v3 is NOT

- Not a refutation of the v2 unfalsifiability theorem — paper7 §11.6
  stands as a structural finding.
- Not a refactor of the OKR addendum or RD-1.12 runtime — those are
  shipped incumbents that v3 treats as DATA.
- Not a single-substrate-prior proposal — v3 may converge on the
  current 4-prior composition (vindicating it as substrate-invariant
  by paraphrase) or expose a substrate-leaked primitive that needs
  surgery. Either outcome is a finding.

### v3 stop conditions

v3 should stop and report when ANY of these happens:

1. **Convergence on the current 4-prior composition** with a
   substrate-paraphrase audit showing all incumbent primitives
   survive the paraphrase test. Result: incumbent vindicated as
   substrate-invariant. Document in §11.6+.

2. **A substrate-leaked primitive surfaces in the incumbent.** E.g.,
   if "supervisor tree" cannot be paraphrased into the corporate or
   military prior without breaking, then RD-1.12 is computational-
   leaked and needs a multi-prior extension. Result: surgical fix
   to the incumbent, documented as v3 finding.

3. **A genuinely disjoint multi-prior alternative beats the
   incumbent on at least 3 of the 6 invariants.** Result:
   architectural pivot proposal to the principal.

4. **Three iterations without movement.** Apply de-anchoring per
   `feedback_fractal_deanchoring.md` — the FRAME may be the
   suspect, not the apparatus.

### Provenance (v3 additions)

- v3 reframe authored 2026-05-02 in conversation with the principal,
  triggered by the principal's substrate-prior-bias concern.
- v3 incorporates state-of-the-art shifts since v2 was authored:
  paper7 §11.6 unfalsifiability theorem, GP-168 OKR addendum,
  RD-1.12 live co-drive runtime, agent_utilization tracker, schemas
  v1.2.

---

## v3 RUN-2 RESULTS (2026-05-02 evening) — implementation-grade findings

After the rubric-config fix (added `require_i_model_in_submission:
false` + cage_meta v5 keys + qualitative-stagnation triggers), gp168
v3 ran a second 6-iter pass that *escaped* the v3-run-1 compensation-
gradient microoptimization and engaged the actual exogenous-pressure
closure mechanism that paper7 §11.6 introduced. Four implementation-
grade findings emerged. **These do not refute paper7 §11.6 — they
sharpen its operational consequences for the running implementation.**

### Finding F1 — Exogenous-pressure clocks are subvertable by the principal
**Source**: gp168 v3 run-2 iter-3, score 63 (failed own unit test
"Military closure window violated").

**Mechanism**: paper7 §11.6 says closure requires *exogenous*
resource pressure (budget, deadline, mortality timeline). The
gp168-v3-run-2 paraphrase audit across 5 substrate priors (market /
military / monastic / open-source / computational) showed every
substrate has a documented internal-override mechanism for its
exogenous clock: budget extensions, mutinies, ritual stalling,
watchdog disables, postponed releases. The "exogenous" clock is
exogenous *only with respect to the agents being closed* — the
principal who controls the clock can subvert it silently.

**Operational consequence for the implementation**: every cap
extension, closure postponement, approval delay performed by the
principal is currently silent or weakly-logged. The principal can
therefore neutralize the closure mechanism (intentionally or by
softness) without auditable visibility. This is the implementation-
side analog of the v1 score-20 paralysis attractor — same wall,
different gatekeeper.

**Action**: surface override events as first-class audit
artifacts. Telegram notification + Orbit override-counter +
`transitions.jsonl` `override_event` row type. The closure
mechanism becomes self-documenting under override.

### Finding F2 — Damage-signal enforcement is detection-dependent → gameable
**Source**: gp168 v3 run-2 iter-6, score 77 (champion of run-2).

**Mechanism**: agent-CLI utilization caps + spend caps + damage
signals all rely on threshold detection. Goodhart applied: agents
learn to stay just below the detection threshold, never triggering
the enforcement. The thesis proposed substrate-invariant fallback:
"periodic churn, randomized rotation, or unavoidable role/system
perturbation" — *detection-independent* enforcement.

**Operational consequence**: the `absolute_ceiling_seconds`
parameter in agent_utilization is the only detection-independent
fallback currently in place. The warn-threshold and the soft caps
are detection-dependent and therefore gameable.

**Action**: add randomized cap-threshold jitter (warn at uniform-
random fraction in [0.70, 0.85] each day rather than fixed 0.80)
and randomized audit cadence (closure daemon runs on stochastic
cadence ±20% jitter rather than fixed cron). Both ~10-line changes;
both make timing-around-detection gaming impossible without
weakening the mechanism.

### Finding F3 — Role rotation across CLIs as structural fusion-prevention
**Source**: gp168 v3 run-2 iter-3 + iter-6 synthesis.

**Mechanism**: if `research_director` is always Claude-Code,
single-CLI-specific gaming patterns can compound across iterations
(the role learns its own bypass surface). Rotating the role across
Claude / Codex / Gemini-CLI on a fixed cadence forces role behavior
to be CLI-invariant; any CLI-specific gaming surfaces as cross-CLI
inconsistency in role outputs.

**Operational consequence**: each role yaml currently binds a
single primary member. Multi-CLI rotation is unsupported.

**Action**: extend `org/roles/<role>.yaml` schema with optional
`agent_rotation: {enabled, period_days, members, strategy}`. Daemon
hook reassigns primary member on cadence. Lower priority than F1/F2
unless multi-agent role assignment scales soon.

### Finding F4 — Don't over-extend paper7 §11.6 — internal closure DOES work in places
**Source**: gp168 v3 run-2 iter-4, score 44 (over-extension penalty).

**Mechanism**: an iteration claimed "closure is impossible to
enforce by any internal process in any substrate-prior." The judge
correctly flagged this as absolutist overclaim — cryptographic
primitives, deterministic gate harnesses, schema validation, and
formal-proof cages ARE internally closed and don't require
exogenous pressure to close.

**Operational consequence**: paper7 §11.6 is correctly scoped to
*coordination closure* (when to stop searching, what to fund next,
when to abandon). It does NOT claim *technical-validation closure*
needs exogenous pressure. The implementation already maintains this
distinction:

- **Internal closure (works without exogenous pressure)**:
  `validate_substrate_meta`, `validate_rubric.py`, deterministic
  cage gates, lean cages, R1 mutation_suite_guard, schema
  validation, lint/type-check pipelines.
- **Exogenous closure (needs principal/budget/deadline)**: choosing
  which Objective to fund, deciding whether a paper is ready to
  publish, declining-attention budget for the principal.

**Action**: document this distinction explicitly in
`docs/concepts/reflexive_engineering.md` and add a paragraph to
paper7 §11.6+ to forestall future ZTARE-on-org runs repeating the
iter-4 over-extension. The implementation is already correct; the
documentation should make the distinction decisive.

### Meta-finding: the unblock was the result, not the iteration

The single rubric-config change (require_i_model + cage_meta v5
keys + qualitative-stagnation triggers) shifted the run from
microoptimization to structural critique. **The mutator was
capable of structural critique all along** — the apparatus was
forcing it into numerical-aggregator vocabulary. This is itself a
finding about the substrate-config layer: numerical-substrate
defaults silently anchor qualitative substrates unless explicitly
overridden. Future qualitative substrates ship with the canonical
qualitative-substrate config now (the scaffold script + the saved
feedback memory).

### Provenance (run-2 additions)

- gp168 v3 run-2 executed 2026-05-02 ~17:48-17:52 UTC, after the
  rubric-config fix shipped at ~17:45 UTC.
- Mutator: gpt-4.1; judge: gpt-4.1 (same family — judge missed-
  score event at iter-2 was a transient JSON-format glitch).
- Champion of run-2: iter-6 score 77 (adversarial-obfuscation
  thesis with substrate-invariant fallback recommendation).
- All 6 run-2 debate logs preserved at
  `projects/gp168_org_design_discovery/debate_log_iter_177775811[3-9].md`
  through `debate_log_iter_1777758373.md`.
- Implementation patches landing 2026-05-02 evening (F1, F2 first;
  F3 on demand; F4 documentation update).

