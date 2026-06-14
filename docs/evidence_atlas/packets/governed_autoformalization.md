---
description: "Evidence packet for governed autoformalization: a checker-agnostic faithfulness firewall with kernel-grade ground-truth checks."
---
# Governed Autoformalization Packet

> **Up:** [Evidence Packets](README.md)

## Scoped Claim

LeanMill's autoformalization faithfulness firewall — the gate that admits a candidate formal statement
only if it is a faithful rendering of the natural-language problem — has two **kernel-grade ground-truth
legs** beyond the LLM round-trip judge: a **semantic instance battery** (the formalized predicate must
`decide` to human-labelled concrete cases) and an **exhaustive provable-equivalence** check (`∀ x, ref ↔
cand`, a 100%-faithfulness certificate over a finite decidable domain). The same governance contract runs
over **multiple verification substrates** (Lean `lake`/`decide`, a pure-Python evaluator, and z3/SMT) —
checker-agnostic governance — and applies **beyond math** to decidable operational rules (access-control
policy; AML/sanctions rules), where a laundered formalization is rejected against ground truth rather than
an LLM's opinion.

## Evidence Level

L2 — runnable demonstration with positive **and** negative controls, validated locally on real Lean
(v4.30) and real z3 (4.16). **Not** a benchmark, **not** externally reviewed, **not** a production
deployment. The faithfulness firewall is opt-in apparatus, not wired into a live loop.

## Primary Sources

- [autoformalize.py](../../../src/ztare/leanmill/solver/autoformalize.py) — the firewall; `semantic_instance_battery` + `provable_equivalence` are the new legs; `faithfulness_gate` is the injectable seam.
- [common/governed_verification.py](../../../src/ztare/common/governed_verification.py) — the shared `CheckResult` + `is_ok` + `Checker` verdict contract (the substrate-neutral core).
- [common/smt_checker.py](../../../src/ztare/common/smt_checker.py) — the z3/SMT checker binding (equivalence + counterexample extraction).
- [solver_core.py](../../../src/ztare/leanmill/solver/solver_core.py) — `LeanLakeChecker` + the proof-side Checker indirection (closure certificate records which checker ratified).
- [LeanMill architecture, faithfulness firewall](../../concepts/leanmill_architecture.md) — the firewall section, with the two new legs documented.

## Runnable Anchor

```bash
# all public, no network, no gitignored artifacts:
PYTHONPATH=src python -m ztare.leanmill.solver.autoformalize        # 29 self-tests incl. the battery leg
PYTHONPATH=src python -m ztare.common.governed_verification --selftest
PYTHONPATH=src python -m ztare.common.smt_checker --selftest        # z3: faithful≡reordered, launders→counterexample
```

The Lean-substrate validation (battery + exhaustive equivalence on `lake`/`decide`) and the
access-control / AML demos are local runnables under `projects/governed_autoformalization_demo/`
(gitignored); they are not part of the public anchor above.

## Evidence Summary

The firewall self-test (29/29) exercises the new instance-battery leg: a faithful formalization is
admitted; broadened (`∧→∨`), dropped-clause, and other laundered formalizations are rejected because the
predicate misclassifies a labelled case (fail-closed on every leg). On real Lean (v4.30) the same legs
were validated against an access-control policy: the faithful policy is admitted and three laundered
variants are kernel-rejected; the exhaustive `∀ x, ref ↔ cand` check accepts a semantically-equivalent
reordering and rejects every launder over the whole finite domain. Checker-agnosticism was demonstrated
by running the **same** `faithfulness_gate` over a pure-Python checker (no Lean) with identical
admit/reject behaviour, and over z3, where laundered AML/sanctions rules are proven non-equivalent over
the **infinite** space of transaction amounts and the solver returns the **specific distinguishing
transaction** (e.g. the exactly-$10,000 structured transfer that a `>=`→`>` boundary edit lets slip). The
proof-side Checker indirection passed positive+negative calibration (a known-good probe closes, a `sorry`
probe is rejected, a swapped non-Lean MockChecker flows through unchanged).

## Non-Claims

- **No claim this replaces Zelkova/Cedar.** The SMT policy analysis is largely a re-implementation of
  established SMT-based policy verification (AWS Zelkova / Cedar); the contribution claimed here is the
  checker-agnostic governance integration, not the SMT analysis itself.
- **No claim the firewall closes the natural-language→formal faithfulness gap.** It narrows it; the
  round-trip judge is consensus-grade, and the irreducible residual (a faithful formal target is only as
  good as the human judgement that it captures the informal problem) is unclosed.
- **No benchmark claim.** There is no labelled corpus of faithful-vs-laundered formalizations measured
  against baselines; the substrates here are small and illustrative.
- **No production / regulatory claim.** The AML/sanctions rules are illustrative, not a compliance product.
- **No live-loop claim.** Autoformalization is opt-in apparatus.

## Missing Upgrade

A stronger packet needs one or more of:

- a **labelled benchmark** of faithful-vs-laundered formalizations (a measured reject-rate / false-admit
  rate), on a real corpus rather than constructed examples;
- the SMT checker now does the **core established policy-analysis operations** — subsumption /
  permissiveness ordering, the four-way compare (Equivalent / More- / Less-Permissive / Incomparable), and
  a **fail-closed non-vacuity guard** — which are a deliberate re-implementation of established tools (AWS
  Zelkova; Cedar's open, Lean-verified symbolic compiler), **not a novelty claim on the SMT analysis**. The
  deferred operations (set-level redundancy/shadowing, unsat-core diagnostics, string/CIDR types,
  quantitative model-counting) are built only as real consumers appear; the genuinely-distinct direction —
  using the SMT solver to **auto-generate the boundary labels the Lean instance-battery hand-codes**
  (cross-substrate test generation) — remains future work;
- one **externally reviewed** non-math case study on a real operational rule set with complete receipts.

Until then, claims should stay scoped to *demonstrated, locally-validated, checker-agnostic faithfulness
governance* — not benchmarked performance or a production policy analyzer.
