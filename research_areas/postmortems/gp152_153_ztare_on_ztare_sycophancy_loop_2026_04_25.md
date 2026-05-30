# GP-152 / GP-153 — ZTARE-on-ZTARE Sycophancy Loop (2026-04-25)

## What happened

GP-152 (Framer architecture audit, 24 iters) and GP-153 (Framer v1.0
spec critique, 24 iters) produced "spec confirmed, no patch needed"
verdicts. The v2.0 Framer was implemented from those audits and
shipped. Within days of shipping, three independent issues surfaced
that the audit had not flagged:

1. **Heteroscedasticity-guard sign error** (caught post-ship by
   external Gemini-Pro review) — present in v1.1, partially fixed in
   v2.0, fully fixed in v2.1.
2. **Live-loop integration gap** — v2.0 Framer was never live-tested
   in the autoresearch_loop. The audit was spec-only; the loop
   integration code path was not exercised. Surfaced 2026-04-25 when
   gp155 was built specifically to test it.
3. **R1 contract gap** — the audit assumed mutators ship working
   Python; in practice (gp154 v3 post-bug-fix run + gp155 iter 1) the
   mutator emitted prose-correct theses with empty / crashing Python
   blocks. The R1 reject path did not catch import-time crashes,
   wasting iters at ~$0.40/each.

Net: 7 of 12 archived gp154+gp155 post-bug-fix iters failed on CODE,
not concept (5 import-crashes, 2 empty Python blocks, 2 fabricated
visible-MRE claims, 3 catastrophic constant-fitting failures). The
spec audits never noticed because they never ran a Python interpreter.

## Why the spec audits missed it

Three structural failure modes (Gemini-Pro framing, 2026-04-25):

### 1. Prose-vs-Code Mirage
LLMs are "Theorists without Calculators". The mutator could explain
the regime crossover (Sharma α=2/d / Bahri α=1) in fluent prose. The
judge rewarded this fluency. Neither side noticed the Python `_fit_params`
TypeError until gp155 actually ran the harness.

### 2. Lookup-Table Ghost
The MDL penalty couldn't see `if/else` table memorization disguised as
a "zero-parameter law" (RH-17 Lookup-Table Fallacy in
docs/concepts/anti_pattern_catalog.md). The judge scored the prose
description; the K_law claim of 5 hid 16+ hardcoded constants.

### 3. Sycophancy Loop
Both mutator and judge are LLMs. The judge rewarded the SOPHISTICATION
of the proposal while ignoring runtime correctness. The 24-iter gp153
"recursive audit" was structurally a single conversation, with the
participants reinforcing each other's framing.

## What the protocol fix is

**Mandatory two-step protocol for any ZTARE-on-ZTARE meta-project,
effective immediately:**

### Step 1 — Python integration smoke test (cost: $0)

Build a smoke-test script BEFORE the spec audit. The smoke test runs
the proposed mechanisms against:
- REAL ARCHIVED debate-log data from the motivating-case project
- ADJACENT substrates that should NOT be affected (negative control)
- Synthetic ground truth where applicable
- AST / eval safety attempts

Reference implementation: `scripts/public/audits/gp156_integration_smoke_test.py`
(2026-04-25). Three sections:
- A: classifier behavior on synthetic discrepancy patterns
- B: ground-truth recovery on synthetic substrate
- C: cross-substrate safety (no false positives)

Plus an extension that ran Proposal 2 attestation against the actual
gp154 archived debate logs and confirmed 2/2 fabrications caught with
0 false positives — a check that should have happened on v2.0 Framer
before it shipped.

### Step 2 — Inverted spec audit (cost: API budget)

Charter the audit as EXECUTION-HOSTILE, not parsimony / elegance.
Replace dimensions:
- "Functional Form Discovery" → "Adversarial Bypass Concreteness"
- "Universality" → "Compositional Interaction Discovery"
- "Parsimony" → "Implementation-Layer Specificity"

Forbid theoretical-elegance critiques. Reward concrete runnable Python
attack snippets. Reference: `projects/gp156_apparatus_hardening_review/
project_charter.md` and `rubrics/gp156_apparatus_hardening_review.json`
(2026-04-25).

### Why never skip Step 1

Step 2 alone reproduces the gp152/153 failure mode. The integration
test costs $0 in API budget and catches the static execution bugs that
the LLM judge is structurally incapable of catching. Skipping Step 1 to
"save time" guarantees the same class of post-ship surprises.

## Detection signal

Before shipping any ZTARE-on-ZTARE-validated artifact, run:
```
python scripts/public/gp101_validate_arch_map.py ex-post
```
plus the GP-156-pattern integration smoke test against the artifact.
If either fails, the artifact is not ready.

## Postmortem completion checklist

- [x] Failure modes named (Prose-vs-Code Mirage, Lookup-Table Ghost,
      Sycophancy Loop)
- [x] Anti-pattern catalog updated (RH-17 Lookup-Table Fallacy added
      2026-04-25)
- [x] Protocol fix shipped (`scripts/public/audits/gp156_integration_smoke_test.py`
      pattern, `projects/gp156_apparatus_hardening_review/` charter)
- [x] Memory entry added (`feedback_ztare_on_ztare_postmortem.md`)
- [x] In-repo postmortem (this file) added to
      `research_areas/private/postmortems/`

## Cross-references

- Spec: `research_areas/private/specs/active/GP-156_apparatus_hardening_proposal.md`
- Memory: `feedback_ztare_on_ztare_postmortem.md` (auto-memory)
- Anti-patterns: `docs/concepts/anti_pattern_catalog.md` RH-13 / RH-14
  / RH-15 / RH-17
- Smoke test: `scripts/public/audits/gp156_integration_smoke_test.py`
- Audit project: `projects/gp156_apparatus_hardening_review/`
- Audit rubric: `rubrics/gp156_apparatus_hardening_review.json`
- Architectural map: `docs/internal/architectural_maps/autoresearch_loop_architectural_map.md`
  (regions prepare_candidate L1687-1826 + main_loop GP-156 hooks at L4359)
