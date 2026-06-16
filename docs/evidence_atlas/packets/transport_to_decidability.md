---
description: "Evidence packet for transport-to-decidability under a kernel trichotomy: faithfulness/validity routed to a decision theory, every verdict a checkable artifact (CERTIFIED / REFUTED / OUT_OF_FRAGMENT), governed against laundering."
---
# Transport-to-Decidability Packet

> **Up:** [Evidence Packets](README.md)

## Scoped Claim

An untrusted claim's faithfulness/validity is an *opinion* problem only if you stay in one theory. LeanMill
routes each obligation to the decision theory where it is decidable (LIA/EUF, RCF/NIA, polynomial-ideal) and
returns ONE **kernel trichotomy** — `CERTIFIED` (a solver/kernel certificate), `REFUTED` (a concrete,
re-verifiable counterexample), or honestly `OUT_OF_FRAGMENT` (the Rice residue, declared, never a silent guess).
The router **composes** existing decision procedures (`certify_policy_faithfulness`, `nlsat_decide`,
`groebner_certificate`) — no procedure is reimplemented. A no-false-closure kernel re-verifies every certificate,
so cross-domain transport is **safe by construction** (a wrong transport cannot mint a closure).

## Evidence Level

L2 — runnable demonstrations with positive **and** negative controls, validated locally on real z3 (4.16) +
real Lean v4.30. **Not** a benchmark, **not** externally reviewed, **not** a production deployment. Corpora are
small-to-moderate (N=7 router seed, N=18 policy, N=9 IAM) with wide CIs; the `OUT_OF_FRAGMENT` residue is real and
reported. The IAM model is toy-scale boolean, **not** the full IAM grammar (see "Honest edge").

## Claims → receipts → how to re-run

| Claim | Result | Receipt | Re-run (committable) |
|---|---|---|---|
| Decidable-fraction lift | portfolio **5/7 = 71%** vs single best theory **2/7**, **+3**; 2 honest OUT | `results/decidability_router.md` | `python -m ztare.leanmill.solver.decidability_router --selftest` |
| Certified faithfulness (typed trichotomy) | selftest 11/11; CERTIFIED/REFUTED-with-witness/OUT | `results/certified_faithfulness_demo.md` | `python -m ztare.leanmill.solver.certified_faithfulness --selftest` |
| Non-math policy, at scale | engine **18/18** decided+correct (8 compliance domains); witness gap **null** at scale | `results/certify_policy_corpus_run.md` | corpus `scripts/public/control/leanmill/certify_policy_corpus.json` |
| IAM/cloud refinement (policy-permissiveness) | engine **9/9**, **5/5** over-grants caught w/ re-verifiable escalation witnesses | `results/iam_refinement_run.md` | corpus `scripts/public/control/leanmill/iam_refinement_corpus.json` |
| Transport-laundering soundness | red-team **8/8** rejected, **0** false-positive (wrong cofactor / false witness / asserted analogy) | `results/governance_redteam.md` | `governance_redteam.py` (gitignored runner) |
| Math transport lift | witness **12/12** vs native 0/12; Gröbner/SOS **+2** deg-≥3 | `results/transport_lift_controlled.md` | `transport_lift_controlled.py` (gitignored runner) |
| Benchmark, honest+bounded | miniF2F **43%** (N=23 bounded) / 67% (N=9 pilot), both kept | `results/minif2f_test_calibration_triage.md` | `minif2f_calibration.py` (gitignored runner) |

**Reproducibility note (honest).** The committable floor is the `--selftest` entrypoints above (in `src/`,
public, no network) plus the corpora JSON (in `scripts/public/`). The *experiment runners* (live-judge,
red-team, miniF2F, transport-lift) under `projects/leanmill_experiments/` and their `.md`/`.json` receipts under
`analytics/public/leanmill/results/` are currently **gitignored**; a clone reproduces the engine + corpus claims
from the selftests, but not the live-judge/red-team receipts without those runners. Un-gitignoring the four goal
runners + their receipts is the open step for full from-clone reproduction.

## Primary Sources

- [certified_faithfulness.py](../../../src/ztare/leanmill/solver/certified_faithfulness.py) — the typed trichotomy + `certify_policy_faithfulness` / `certify_policy_refinement` / `certify_polynomial_identity`.
- [decidability_router.py](../../../src/ztare/leanmill/solver/decidability_router.py) — the router + `decidable_fraction_lift` metric.
- [common/smt_checker.py](../../../src/ztare/common/smt_checker.py), [common/groebner_cert.py](../../../src/ztare/common/groebner_cert.py), [common/nlsat_oracle.py](../../../src/ztare/common/nlsat_oracle.py) — the composed decision procedures.
- [audit_external.py](../../../src/ztare/leanmill/audit_external.py) — the no-false-closure gate the red-team attacks.
- [LeanMill architecture §4.2 + §8](../../concepts/leanmill_architecture.md) — the firewall, the trichotomy, the prior-art positioning and the honest edge.

## Honest edge (vs the SMT-policy-verification line)

Permissiveness-by-SMT is a mature, production-grade technique (access-control/policy analysis, cloud access-policy
permissiveness reasoners, network-reachability verification, program-equivalence checking). We do **not**
out-verify those dedicated tools on their turf (each has a complete, hardened encoding of its real domain grammar;
this is a toy model). The edge is the LLM-era failure that line assumes away: the **intent→formal translation
firewall** (faithfulness, not formal→formal properties), **domain-generality** (one trichotomy router across
access-policy / compliance / mathematics, not a bespoke per-domain encoding), and **independent kernel
re-verification + a transport-laundering red-team**. Same SMT-certificate spirit; different and broader target.
See `results/iam_refinement_run.md`.
