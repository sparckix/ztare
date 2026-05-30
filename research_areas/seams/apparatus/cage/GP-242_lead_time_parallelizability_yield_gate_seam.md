---
id: GP-242
status: SPEC — pending cold cross-provider review (GPT-5.5 xhigh), NOT implemented
discovered: 2026-05-17
---

# GP-242 — Lead-time / parallelizability yield gate

> **Seam metadata** · `seam_id:` GP-242 · `track:` apparatus · `status:` SPEC - pending cold cross-provider review (GPT-5.5 xhigh), N · `last_updated:` 2026-05-17


## The gap (operator-surfaced, RCA-grounded)

Tick / GP-233 / post_tick price **epistemic** yield only (closure |
exact-gap | falsifier | consequence-exposure | 0-false-ratify +
adversarial honesty). There is NO axis for **time-to-decisive-signal
/ parallelizability**. `--budget-agent-minutes` exists but nothing
checks or punishes a serial design 10–50× slower than an equivalent
batched/parallel one. Lead-time is **unpriced ⇒ unoptimized**. Evidence:
the operator had to push 4–5× to get batching/parallelism; a valuable
move that is not a forcing function is never taken (buried-prescription
/ non-forcing = dead — the program's own memorized failure class).

## The proposed mechanism (to be cold-reviewed BEFORE implement)

A **pre-run lead-time HARD gate** (owner-scoped, like the axiom /
post_tick gates): any sandbox-bound / long run whose estimated
wall-time exceeds a threshold is BLOCKED until it answers, in a typed
machine-checkable form (NOT free prose):

1. **Independent units?** If the work decomposes into N independent
   units → must thread/parallelize or give a typed reason it cannot.
2. **Amortizable fixed cost?** If a fixed cost (import, model load,
   sandbox spin-up) repeats per unit → must batch it or typed-reason.
3. **Dry-run-validated?** A seconds-long dry-run on the real inputs
   must have run and passed before the long run launches.

Unanswered serial-when-batchable ⇒ blocked, not "noticed if the
operator nags". Plus: record **lead-time-to-first-decisive-signal** as
a recorded axis in every claim-bearing F-row / GP-233 entry, with "did
a cheaper equivalent design exist?" — makes slowness visible and
punishable so it is optimized like the epistemic axes.

## Open design questions FOR THE COLD REVIEW (do not self-answer)

- Where does the gate physically bind so an agent cannot route around
  it (the GP-241 lesson: must be at an un-bypassable chokepoint, not
  advisory text / not an opt-in flag)? Candidates: the propose/daemon
  membrane (a long run is itself a transition needing a stamped
  pre-run obligation), or a wrapper on the sandbox-launch primitive.
- How is "estimated wall-time" derived deterministically without being
  an agent-gameable self-estimate? (Same class as the GP-241
  declared-signal-underreporting sev-5: a self-reported estimate is a
  gaming hole — must be verifier-derived or structurally bounded.)
- Threshold value + false-block risk (benign-must-not): a genuinely
  irreducibly-serial run (data dependency) must not be blocked — typed
  exemption with machine-checkable precondition, not free prose.
- Does it belong as a GP-241 obligation clause (v?_activation.yaml)
  rather than a new bespoke gate (anti point-fix / reuse the membrane)?
- Interaction with the just-fixed GP-241 fail-closed posture: a new
  forcing gate must not re-introduce a fail-open path.

## Discipline

Spec (this) → cold cross-provider review (GPT-5.5 xhigh, same as
GP-241, NOT a self-Claude agent — the monoculture lesson) → implement
ONLY the cold-reviewed design → re-verify fail-closed → trust. No
self-certified hot-add. Sequenced AFTER the GP-241 sev-5 hardening
(do not stack an unreviewed forcing gate on a membrane still being
hardened).
