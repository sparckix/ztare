# Lane B — APN Audit Receipts (canonical L1+L2+L3)

Re-audit consolidated: 2026-05-29 (supersedes the earlier native-only table, which
ran L3 on files that fail native compile and so reported `confirmed_blocker`
artifacts that are not real top-level findings).
Audit module: `scripts/public/control/leanmill/proof_audit.py`
(+ `external_proof_audit.py` v4.27 sidecar wrapper).

## How to read this

**Two toolchains matter.** *Native* is the current default (v4.30). *Pinned* is the
v4.27 toolchain APN's proofs were written against, run via the sidecar. A native
`compile_failed` carrying a version-specific (`drift`) error is a **toolchain-pinning**
fact, not a proof defect — the authoritative verdict for these foreign proofs is at the
pinned toolchain they target.

**On L3 (read this before citing it).** L3 is an anti-laundering gate built for *our own
solver's* credit — does a claimed "closure" just restate a gold lemma? Its discriminating
signal is a **top-level** flag: the headline theorem itself being a verbatim/trivial
restatement. A **helper-level** `gold_name_verbatim` flag only means a helper lemma cites
a Mathlib lemma by name — which is **normal, expected library use** and is near-vacuous as
a quality signal when auditing someone else's finished proof (the Lane-B governance case).
Helper-level L3 flags are therefore **advisory**, not a finding against APN. Earlier drafts
that reported a "7/8 helper-blocker" count gave the helper flags weight they do not carry.

## Verdicts at the pinned toolchain (v4.27)

| Target | Compiles @ pinned | Kernel axioms allowlisted | L3 top-level | L3 helper-level (advisory) | Native (v4.30) |
|---|---|---|---|---|---|
| conjecture_2 | ✓ | ✓ | clean | flag present | compile_failed (pinned-only) |
| P1 | ✓ | ✓ | clean | none | compiles natively |
| P2 | ✓ | ✓ | clean | flag present | compiles natively |
| P3 | ✓ | ✓ | clean | flag present | compile_failed, drift (pinned-only) |
| P4 | ✓ | ✓ | clean | flag present | compile_failed (pinned-only) |
| P5 | ✓ | ✓ | clean | flag present | audit_invocation_failed (harness bug) |
| P7 | ✓ | ✓ | clean | flag present | compile_failed (pinned-only) |
| P8 | ✓ | ✓ | clean | flag present | compiles natively |

Allowlist = {`propext`, `Classical.choice`, `Quot.sound`}.

## Honest bottom line

- **8/8 compile kernel-clean at the pinned v4.27 toolchain** — L1 (no `sorry`/`admit`)
  and L2 (only allowlisted kernel axioms) both pass for all eight.
- **All 8 are top-level L3-clean** — no headline theorem is a vacuous restatement of a
  library lemma.
- **7/8 carry advisory helper-level library-citation flags** (P1 is the exception). These
  are expected and are **not** a defect.
- The two **substantive** caveats are: **(a) toolchain-pinning** — 5/8 fail native v4.30
  compile (P5's native run hit a harness `audit_invocation_failed`, an infra bug, not a
  falsification); **(b) library-composition** — the proofs assemble existing Mathlib
  lemmas (limited novel-math content), which is normal for formalization.
- We do **NOT** claim DeepMind/APN published anything fake. Two earlier framings were both
  wrong — one ("laundering caught" / "7–8 of 8 clean closures") overstated quality, the
  other ("1 clean, 7 carry blockers") overstated a defect — and both are retracted in
  favor of the table above.

Per-target receipts: `analytics/public/queries/lane_b_apn_audit_receipts.json`.
Re-audit raw log retained on the VPS run host.
