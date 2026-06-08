# GP-058 Bug-bounty + factory integration seam

> **Seam metadata** · `seam_id:` GP-058 · `track:` gaming · `status:` unrecorded · `last_updated:` 2026-05-08


Status: open
Opened: 2026-04-14
Owner: Daniel
Siblings: GP-056 (axiomatic patching), GP-057 (ratio-finiteness gate),
GP-055 (meta-judge parse robustness)

Current routing: this seam is the discovery-mode precedent for
factory/honeypot bounty reports. Current vector status, promotion evidence,
and runtime enforcement are routed through
`docs/concepts/gaming_behavior_catalog_map.md`.

## Problem

ZTARE currently runs in two disconnected modes:

- **Factory mode.** Tight deterministic gate battery, project charter,
  5–10 iters, synthesis output. The charter contamination fix
  (GP-023 sandbox_07 proof) makes the gates the binding constraint.
- **Honeypot mode.** Loose rubric (`honeypot_minimal.json`), 50 iters,
  max 115 score, no pre-run. Designed to reward surprise and
  failure-mode revelation. Useful for finding bugs the factory
  battery is missing.

These two modes do not feed each other. When honeypot produces a
champion that reveals a new gaming pattern (Hormuz MMCT on
2026-04-14), the finding lives in the debate log and maybe a private
analysis file, but there is no standing mechanism to promote it to a
new factory gate. Conversely, when the factory battery crashes or
silently misses a pattern (meta-judge JSON crash on 2026-04-14 iter
4), there is no standing mechanism to open a honeypot probe on the
apparatus itself.

The result: every new gaming strategy has to be manually noticed,
written up, argued about, and eventually coded as a gate. The factory
battery grows by operator attention, which is the bottleneck.

## Eigenquestion

Can ZTARE maintain a standing **bug-bounty loop** where honeypot runs
continuously red-team factory champions and any pattern the honeypot
can exploit becomes a candidate factory gate, without the loop
devolving into an adversarial arms race that wastes compute on
arbitrary gate proliferation?

## The proposed integration pattern

Three-stage cycle, operator-gated at each stage:

**Stage 1 — Factory produces a champion.** Normal factory run,
closed seam, champion scored under tight rubric. No change from
today.

**Stage 2 — Honeypot red-teams the champion.** Run the honeypot
rubric against the *same charter* as the factory run, with the
factory champion injected as a seed thesis. If the honeypot champion
scores ≥100/115 by exploiting a pattern the factory didn't catch,
the run emits a **bounty report**: a structured artifact naming
(a) the champion's exploit, (b) the gate the factory was missing,
(c) the first operator with ≥1 prior instance of that exploit in
their memory (to short-circuit duplicates).

**Stage 3 — Operator promotes or rejects.** The bounty report is
not automatically converted to a gate. The operator reviews it,
decides whether the pattern is a real gap or an artifact of the
honeypot's looseness, and either writes a new seam (following the
seam-first rule) or rejects with reason. Rejected bounties stay in
a ledger so the same pattern doesn't re-trigger a bounty on the
next cycle.

## Hypothesis under test

- **H1 (standing loop works).** A bug-bounty loop run on a cadence
  of one cycle per week (or per charter) produces a net positive
  inflow of new factory gates over ~8 weeks, measured by
  `gates_promoted / operator_hours_reviewing_bounties`.
- **H2 (arms race).** The honeypot rubric's looseness allows the
  mutator to find "exploits" that are actually rubric artifacts
  (the judge rationalized a high score for a thesis that would
  never pass a tighter rubric). Most bounty reports are rejected,
  and the loop becomes a drag on operator attention.
- **H3 (duplicate discovery).** Real new gaming patterns are rare.
  The honeypot finds the same 2–3 patterns repeatedly (axiomatic
  patching, float masking, assert narrowing) and the duplicate-
  short-circuit becomes the dominant behavior. Net inflow of
  genuinely new gates is low.

H1 is what the integration pattern is optimistically claiming. H2 is
the Mungerian inversion. H3 is the "discovery is front-loaded"
counter-claim that would mean running honeypot continuously is
wasted compute past the initial few cycles.

## Discriminating test

Run one full cycle manually using the three artifacts already on
disk, as a proof that the pattern is executable:

1. **Factory champion:** any recent closed factory run with a
   champion above its rubric threshold.
2. **Honeypot champion to convert to bounty report:**
   `projects/hormuz_oil_shock_2026/history/1776211055_iter10_score_115_honeypot_minimal.md`
   (already on disk, score 115/115, exploit = axiomatic patching).
3. **Operator review:** write the bounty report by hand, review it,
   either accept and open GP-056 (already done this session as a
   sibling seam) or reject with reason.

If the manual cycle produces a clean seam promotion (GP-056 is the
evidence that it does), the pattern is executable. The open question
is whether automating Stage 2 is worth it, or whether the honeypot
is best run ad-hoc on specific suspicious champions.

## Success criterion

After 4 weekly cycles:

- **Pass.** At least 2 bounty reports produced, at least 1 promoted
  to a factory gate candidate, operator review time under 1 hr per
  cycle. The loop is earning its keep.
- **Fail.** Zero novel bounty reports (all duplicates), or review
  time above 2 hr per cycle, or bounty reports consistently
  producing rubric-artifact exploits that the operator rejects.
  Revert to ad-hoc honeypot runs and close this seam as Outcome B.

## What would make this uninterpretable

- Running honeypot on a *different* charter than the factory
  champion — different evidence, different gate landscape. The
  red-team value collapses. Stage 2 must reuse the factory charter.
- Auto-promoting bounty reports to gates without operator review.
  That's how a factory gate becomes a dial: the mutator learns to
  trigger bounty reports in ways that make the gates easier to
  satisfy, not harder.
- Treating the honeypot's weakest-point narrative as the gate spec.
  The narrative is a prompt for gate design, not the gate itself.
- Letting the mutator inside the bounty loop read rejected bounty
  reports. That's a direct contamination channel.

## Relationship to other seams

- **GP-055** (meta-judge parse robustness) would have been caught by
  this loop if the loop existed — the iter-4 JSON crash is a bounty
  report on the apparatus itself. It is already closed as a fix this
  session, but it is the first empirical instance of the pattern and
  validates H1.
- **GP-056** (axiomatic patching) is the first empirical instance of
  the pattern on a *model*, not the apparatus, and its existence is
  the evidence that Stage 2 is executable.
- **GP-057** (ratio-finiteness gate) is the first candidate *new
  gate* the loop would produce once GP-056's discriminating test
  runs. It is the downstream artifact of this seam, not a sibling.

## Scope boundary

This seam is the pattern. It is not an implementation plan for the
honeypot-to-factory pipeline. A spec for automation lives in a
sibling seam only after ≥2 manual cycles have run and the pattern
has produced ≥2 promoted gates. Per seam-first rule.
