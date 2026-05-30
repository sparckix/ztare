---
description: "Conservative benchmark evidence for ZTARE claim discipline and comparison baselines."
---

# Benchmark Evidence

This page summarizes public benchmark evidence that already exists in the
repository. It is intentionally narrow. The PySR comparison is **historical**:
it was run against an older code path and should not be read as a benchmark of
the current in-loop plus out-of-loop research engine. It remains useful as
evidence for the gate idea: hard out-of-sample gates can force null returns
where a search procedure emits plausible-looking forms.

The evidence supports a claim about **claim discipline, false-positive
suppression, and null-returning gates**. It does not support a broad claim that
ZTARE is generally the leading system for autonomous research, scientific
generation, scientific validation, or mathematical discovery.

## What The Current Evidence Supports

The strongest historically benchmark-supported claim is:

ZTARE-style gate architecture can force null returns on substrates where a
search procedure finds a plausible-looking form but the form does not survive
the predeclared out-of-sample test.

The benchmark evidence currently comes from two places:

- the historical PySR comparison in the experimental-math letter;
- the constraint-memory evaluator benchmark.

Those benchmark families test different things. The PySR comparison tests an
older symbolic-regression path plus hard out-of-sample gates. The
constraint-memory benchmark tests whether hardened evaluator conditions reduce
known false accepts without collapsing into reject-all behavior. Neither one
benchmarks the current full system as a general-purpose reasoning engine.

Run the model-free evidence check:

```bash
make benchmark-evidence
```

This check reads the artifacts linked below and fails if the conservative
historical claims on this page stop matching the stored results.

## PySR Baseline

The PySR comparison lives in the experimental-math letter and its raw result
JSON:

- [experimental-math letter draft](../papers/experimental_math_letter/draft.md)
- [PySR baseline full JSON](../papers/experimental_math_letter/pysr_baseline_full.json)
- [PySR baseline harness](../papers/experimental_math_letter/scripts/pysr_baseline.py)

The comparison used PySR 1.5.10 with 40 iterations, complexity limit 20, and
operators `{+, -, *, /, pow, log, sqrt, exp}`. It used the same out-of-sample
gate discipline as the letter's ZTARE runs.

The important result is not "ZTARE beats PySR everywhere." The important
result is that the hard gate changes what the system is allowed to say.

On the three incompressible or window-fit substrates, default PySR still emits
a form. Under the ZTARE-style gate, those same PySR outputs are forced to null:

- S1 abundant-density window fit: PySR emits a form, but gated verdict is
  `null-under-gate` because `max_oos / max|y| = 0.01049 > 0.01`.
- S2 Mertens `M(n)/sqrt(n)`: PySR emits a form that produces `NaN` on
  extrapolation, so the gated verdict is null.
- S3 normalized prime gaps: PySR emits a form, but gated verdict is
  `null-under-gate` because `max_abs_oos = 1.728 > 0.08`.

The same comparison includes two sanity baselines:

- Lucky-number density: PySR recovers `1.2031957 * log(n) + 0.48700628`, close
  to the ZTARE coefficient `1.200`, and passes the gate.
- Hardy-Ramanujan `log p(n)`: ZTARE recovers the expected `sqrt(n) + log(n)`
  topology, while the PySR budget returns a nested exponential that fails the
  farther-tail gate with `max_abs_oos = 0.2649 > 0.08`.

The conservative reading is:

- PySR triangulates the Lucky-number coefficient.
- PySR failure on Hardy-Ramanujan shows that default evolutionary search does
  not automatically find the intended topology under this small budget.
- The null-returning behavior comes from gate architecture, not from a
  magical search algorithm.

## Constraint-Memory Benchmark

The constraint-memory benchmark tests evaluator discipline rather than the
full mutator loop:

- [constraint-memory benchmark](constraint_memory/README.md)
- [run script](constraint_memory/run_benchmark.py)
- [representative metrics summary](constraint_memory/runs/20260404_195100/metrics_summary.json)

The representative run compares three conditions:

- `A_baseline_soft_judge`: rubric-only judge, no deterministic gates, no
  primitives.
- `B_deterministic_gates`: deterministic score gates, no primitives.
- `C_gates_plus_primitives`: deterministic gates plus approved
  attacker/judge-side primitives.

The representative metrics show the evaluator hardening pattern:

- Baseline soft judge: false accept rate `0.1429`, false reject rate `0.5`,
  exploit detection rate `0.5714`.
- Deterministic gates: false accept rate `0.0`, false reject rate `0.5`,
  exploit detection rate `0.8571`.
- Gates plus primitives: false accept rate `0.0`, false reject rate `0.0`,
  exploit detection rate `0.8571`.

The conservative reading is:

- deterministic gates removed false accepts in this benchmark run;
- primitives recovered the good controls that deterministic gates alone were
  over-rejecting;
- this is evidence for evaluator hardening, not evidence for general
  scientific discovery performance.

## What This Does Not Support

These benchmarks do not support a global public ranking claim.

They do not establish:

- that ZTARE beats all symbolic-regression systems;
- that ZTARE is the best autonomous mathematical research system;
- that ZTARE is the best general-purpose reasoning engine;
- that ZTARE is the best scientific generation or validation engine;
- that the current hard-problem campaigns are externally benchmarked;
- that the current in-loop plus out-of-loop architecture has been benchmarked
  as a whole;
- that null-returning gates are sufficient for discovery;
- that historical benchmarks alone license current architecture claims.

The current benchmark-supported public claim should remain:

ZTARE has public evidence that hard gates and evaluator primitives improve
claim discipline and false-positive control on the benchmark families tested.

## Benchmarking The Current System

The current system is not just a symbolic-regression engine. It combines:

- in-loop claim generation, validation, gates, and demotion;
- out-of-loop research operations, ledgers, source-readiness, and project
  routing;
- scientific substrate work where the valuable output can be a null, a
  falsifier, a source-design upgrade, or a bounded claim rather than a solved
  theorem.

That means there is probably no single honest competitor set. Different slices
compete with different baselines:

- **Claim validation:** ordinary LLM review, rubric-only judges, human review,
  and fact-checking workflows.
- **Symbolic recovery:** PySR, Eureqa-style symbolic regression, genetic
  programming, and hand-designed template enumeration.
- **Formal proof work:** LeanDojo/ReProver/LeanHammer-style systems, tactic
  search, and human theorem-proving workflows.
- **Research operations:** notebooks, lab wikis, issue trackers, AutoGPT-style
  agent loops, and organizational operating systems.
- **Scientific generation:** human research groups plus LLM-assisted literature
  and experiment-design workflows.

The fair benchmark shape is therefore a **portfolio benchmark**, not one
leaderboard. A current-system benchmark should measure whether the whole
operating loop improves the quality of research decisions over time.

Candidate benchmark axes:

- **False-positive control:** how often does the system promote claims that
  should have been demoted?
- **Useful nulls:** how often does it correctly return null and name the
  binding constraint?
- **Falsifier quality:** how often does the next proposed test actually change
  the belief state?
- **Source-readiness accuracy:** does it correctly distinguish ready, partial,
  and blocked sources before allocation?
- **Time-to-demotion:** how quickly does it retire an attractive wrong story?
- **Cross-run learning:** do later runs avoid earlier documented failure modes?
- **Research-output value:** did the system produce a reusable artifact,
  public claim, proof stub, source packet, or negative result that a human
  researcher would keep?

The most honest first current-system benchmark would be small:

- freeze 8 to 12 claim packets across different domains;
- include good claims, overclaims, stale claims, null-worthy claims, and
  source-blocked claims;
- define the expected output as `promote`, `demote`, `null`, `source-blocked`,
  or `needs next falsifier`;
- compare against a rubric-only LLM judge and a human baseline;
- score not just verdict accuracy, but whether the system names the right
  missing evidence and next falsifier.

That would benchmark what ZTARE actually is now: a reasoning and research
governance engine whose job is not only to generate answers, but to prevent
premature closure.

## What Would Be Needed For A Stronger Claim

A stronger benchmark claim needs a frozen public benchmark suite with:

- named external baselines;
- fixed tasks and held-out data;
- predeclared pass/fail metrics;
- a public result artifact for every baseline and every ZTARE condition;
- a non-claim section for each benchmark family;
- at least one replication run after the benchmark surface is frozen.

Until that exists, the right public posture is benchmark-backed claim
discipline and a benchmark plan for the current architecture, not a broad
ranking claim.
