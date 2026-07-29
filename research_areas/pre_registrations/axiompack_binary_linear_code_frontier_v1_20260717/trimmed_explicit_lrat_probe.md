---
description: "Pre-registered trimmed explicit-LRAT successor after the untrimmed proof-term timeout."
status: closed_killed
date: 2026-07-17
---

# Trimmed explicit LRAT successor probe

## Prior result

The exact CNF controls behaved correctly, but explicit proof construction from
the 92 MB untrimmed LRAT trace crossed 180 seconds. That result is frozen in
`explicit_lrat_proof_term_probe.md`.

## Hypothesis

Lean 4.31's use-analysis LRAT trimmer will delete enough unused proof steps to
reduce the textual trace by at least 40%. Mathlib's explicit `lrat_proof`
constructor will then finish within 180 seconds and report only the existing
allowed axioms.

## Discriminating test

1. Parse and trim the exact LRAT file with
   `Lean.Elab.Tactic.BVDecide.LRAT.trim`.
2. Emit standard textual LRAT and record its size/hash and retained step count.
3. Re-run the unchanged `lrat_proof` source against the trimmed trace.
4. If it closes, alter one retained hint in a copied trace and require the
   explicit constructor to reject it.

## Success criteria

- trimmed byte size is at most 60% of the original;
- explicit proof construction completes within 180 seconds;
- `#print axioms` is contained in the current allowlist;
- tampered proof rejection is deterministic.

## Kill conditions

- parsing/trimming failure;
- less than 40% byte reduction;
- another 180-second proof-term timeout;
- any private native-check or otherwise unallowed axiom.

If killed, the fixed-kernel architecture remains valid but this LRAT
proof-term implementation is not operationally adequate for the current
control. The next certificate must exploit code structure or use a separately
reviewed checker tier; the common allowlist must not be widened by default.

## Result

The Lean 4.31 trimmer parsed and processed the exact trace in 13.72 seconds.
It changed 532,459 input actions into 540,931 output actions because it inserted
deletion steps, while reducing bytes from 92,168,978 to 78,099,369. The 15.27%
byte reduction is below the required 40%, so the experiment stops at the first
kill condition and does not spend another 180-second proof-term attempt.

- trimmed LRAT SHA-256:
  `67cd6f7e746e1458903e88bf6d20ddcf32304377a88219481424413081780ca3`
- trimmer source SHA-256:
  `40e7cfc04286c3359e23513356214aaec73ae749efdc6814cb4b064463ce8009`
- original bytes: `92,168,978`
- trimmed bytes: `78,099,369`
- byte reduction: `15.27%`
- provider calls: zero

The capacity/trust boundary is therefore separated. A fixed axiom-clean LRAT
proof constructor is available, but this generic CNF proof is too large for the
current operational envelope. A structure-aware certificate—starting with the
parity-extension composition for this positive control—is the next scientific
route. No common-kernel change follows from this negative result.
