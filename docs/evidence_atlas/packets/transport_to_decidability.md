---
description: "Review packet for transport-to-decidability: routed decision procedures, checkable trichotomy verdicts, and anti-laundering governance."
---
# Transport-to-Decidability Packet

> **Up:** [Review Packets](README.md)

## Scoped Claim

An untrusted claim's faithfulness/validity is an *opinion* problem only if you stay in one theory. LeanMill
routes each obligation to the decision theory where it is decidable (LIA/EUF, RCF/NIA, polynomial-ideal) and
returns ONE **kernel trichotomy**: `CERTIFIED` (a solver/kernel certificate), `REFUTED` (a concrete,
re-verifiable counterexample), or honestly `OUT_OF_FRAGMENT` (the Rice residue, declared, never a silent guess).
The router **composes** existing decision procedures (`certify_policy_faithfulness`, `nlsat_decide`,
`groebner_certificate`) without reimplementing any of them. A no-false-closure kernel re-verifies every certificate,
so cross-domain transport is **safe by construction** (a wrong transport cannot mint a closure).

## Evidence Level

L2: runnable demonstrations with positive **and** negative controls, validated locally on real z3 (4.16) +
real Lean v4.30. **Not** a benchmark, **not** externally reviewed, **not** a production deployment. Corpora are
small-to-moderate (N=7 router seed, N=18 policy, N=9 IAM) with wide CIs. The `OUT_OF_FRAGMENT` residue is real and
reported. The IAM model is toy-scale boolean, **not** the full IAM grammar (see "Honest edge").

## Evidence Summary

The current evidence is a bounded transport-to-decidability packet: a router,
typed trichotomy, policy/IAM corpora, transport-laundering red team, and small
math-transport controls. The strongest supported claim is governance and
artifact discipline: every positive result must be a certificate or
kernel-checked witness, every negative result must be a concrete counterexample
or explicit `OUT_OF_FRAGMENT`, and transport attempts that launder an analogy
are rejected by the audit gate.

Each claim links to its receipt and reproducible anchor.

| Claim | Result | Receipt | Re-run (committable) |
|---|---|---|---|
| Decidable-fraction lift | portfolio **5/7 = 71%** vs single best theory **2/7**, **+3**; 2 honest OUT | `results/decidability_router.md` | `python -m ztare.leanmill.solver.decidability_router --selftest` |
| Certified faithfulness (typed trichotomy) | selftest 11/11; CERTIFIED/REFUTED-with-witness/OUT | `results/certified_faithfulness_demo.md` | `python -m ztare.leanmill.solver.certified_faithfulness --selftest` |
| Non-math policy, at scale | engine *decides* 18/18 (8 compliance domains) — **z3-vs-z3 = consistency, NOT accuracy**; value is the artifact + the **null** judge gap | `results/certify_policy_corpus_run.md` | `projects/leanmill_experiments/public/certified_faithfulness_demo.py --corpus scripts/public/control/leanmill/certify_policy_corpus.json` |
| IAM/cloud refinement (policy-permissiveness) | **5/5** over-grants caught w/ re-verifiable escalation witnesses (9/9-vs-z3 = consistency, not accuracy) | `results/iam_refinement_run.md` | corpus `scripts/public/control/leanmill/iam_refinement_corpus.json` (engine = `certified_faithfulness.certify_policy_refinement`) |
| Transport-laundering soundness | red-team **8/8** rejected, **0** false-positive (wrong cofactor / false witness / asserted analogy) | `results/governance_redteam.md` | `projects/leanmill_experiments/public/governance_redteam.py` |
| Math transport lift (vs native) | Gröbner/SOS **+2** deg-≥3; witness 20/20 vs native 0/20 — *but native is a weak baseline* | `results/transport_lift_controlled.md` | `projects/leanmill_experiments/public/transport_lift_controlled.py` |
| **Exogenous-compute edge (vs a bare model), kernel-confirmed** | only-N factoring: bare deepseek **1/4** (control only) vs leanmill **4/4** kernel-verified → **+3**; 16/22/26-digit semiprimes the model can't factor, the kernel re-verifies. *Honest correction: the earlier Pell/Kronecker "12/12" was subsumed by a strong reasoning model (sum-leak); only-N factoring is the clean test.* | `witness_transport_separation/` (`factoring_separation_run.json`) | `witness_vs_bare_controlled.py --no-fixed --factoring --bare-models deepseek-chat` |
| Benchmark, honest+bounded | miniF2F **43%** (N=23 bounded) / 67% (N=9 pilot), both kept | `results/minif2f_test_calibration_triage.md` | `minif2f_calibration.py` (env-heavy; not committed) |

**Reproducibility note (honest).** Committable + from-clone runnable: the `--selftest` entrypoints (in `src/`,
public, no network), the corpora JSON (in `scripts/public/`), and the three self-contained experiment runners now
under `projects/leanmill_experiments/public/` (governed red-team, certified-faithfulness/policy corpus,
transport-lift). The live runners need warm Lean or a subscription model in the env, but the scripts ship. Still
**not** from-clone: the `.md`/`.json` receipts under `analytics/public/leanmill/results/` (gitignored by the
private-accounting convention) and the env-heavy `minif2f_calibration.py` (needs the PutnamBench substrate). A
clone reproduces every engine + corpus + governance claim by running the shipped selftests and `public/` runners.

## Runnable Anchors

From-clone, model-free anchors:

```bash
python -m ztare.leanmill.solver.decidability_router --selftest
python -m ztare.leanmill.solver.certified_faithfulness --selftest
```

Public runner anchors, with environment caveats described above:

```bash
projects/leanmill_experiments/public/certified_faithfulness_demo.py --corpus scripts/public/control/leanmill/certify_policy_corpus.json
projects/leanmill_experiments/public/governance_redteam.py
projects/leanmill_experiments/public/transport_lift_controlled.py
```

## Primary Sources

- [certified_faithfulness.py](../../../src/ztare/leanmill/solver/certified_faithfulness.py): the typed trichotomy + `certify_policy_faithfulness` / `certify_policy_refinement` / `certify_polynomial_identity`.
- [decidability_router.py](../../../src/ztare/leanmill/solver/decidability_router.py): the router + `decidable_fraction_lift` metric.
- [common/smt_checker.py](../../../src/ztare/common/smt_checker.py), [common/groebner_cert.py](../../../src/ztare/common/groebner_cert.py), [common/nlsat_oracle.py](../../../src/ztare/common/nlsat_oracle.py): the composed decision procedures.
- [audit_external.py](../../../src/ztare/leanmill/audit_external.py): the no-false-closure gate the red-team attacks.
- [LeanMill architecture §4.2 + §8](../../concepts/leanmill_architecture.md): the firewall, the trichotomy, the prior-art positioning and the honest edge.

## Honest edge (vs the SMT-policy-verification line)

Permissiveness-by-SMT is a mature, production-grade technique (access-control/policy analysis, cloud access-policy
permissiveness reasoners, network-reachability verification, program-equivalence checking). We do **not**
out-verify those dedicated tools on their turf, as each has a complete, hardened encoding of its real domain grammar
and this implementation is a toy model. The edge is the LLM-era failure that line assumes away: the **intent→formal translation
firewall** (faithfulness, not formal→formal properties), **domain-generality** (one trichotomy router across
access-policy / compliance / mathematics, not a bespoke per-domain encoding), and **independent kernel
re-verification** with a transport-laundering red-team. Same SMT-certificate spirit, different and broader target.
See `results/iam_refinement_run.md`.

## Non-Claims

- Not a broad theorem-prover performance benchmark.
- Not a claim that the toy IAM encoding matches a production IAM grammar.
- Not a claim that z3-vs-z3 consistency proves real-world policy accuracy.
- Not an externally reviewed result.
- Not a broad LeanMill measured proof-search lift claim.
- Not a production deployment claim.
- Not a claim that `OUT_OF_FRAGMENT` residue is small or ignorable.

## Missing Upgrade

A stronger packet needs:

- committed public receipt exports for the current `.md` and `.json` result
  files, replacing the references to gitignored accounting artifacts they
  currently carry
- a named external baseline for each benchmark-style claim
- external review of at least one policy or mathematics transport artifact
- a production-grade domain grammar for any policy/IAM accuracy claim
- confidence intervals or repeated runs for the small corpus results
- a from-clone runnable benchmark packet for the env-heavy miniF2F and
  PutnamBench-related paths

Until those exist, this packet supports bounded governance and artifact
discipline around decidability transport, not broad performance or deployment
claims.
