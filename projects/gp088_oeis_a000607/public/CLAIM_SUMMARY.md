# GP-088 OEIS A000607 (Prime Partitions, Blind) — Public Claim Summary (Null)

> **What this file is.** The public-evidence surface for a sealed blind
> investigation of OEIS A000607 (number of partitions of `n` into prime
> parts). The working directory is private. This summary records a
> **null result** under this apparatus protocol.

## One-line claim (a null)

Presented blind with the prime-partition sequence A000607 under cold
variable names, the engine did not propose a closed-form law that
survives the gate battery in this project. Apparatus-internal score:
**0 / 100**.

## What was tested

The mutator was given evidence rows for a sub-linear monotone
increasing positive-integer sequence (A000607) with no domain labels
and no Vaughan-theorem hints. The investigation surface is the bare
sequence; the apparatus's compositional-template layer (which would
search for `√(n/log n)` composition) was not the configuration here.

## Result — sealed null

No specific law was proposed against the gate battery in this project.
Apparatus-internal score 0 reflects that no candidate form cleared the
hard gates.

## Honest framing — protocol-bound null, not a generalized claim

A separate apparatus thread investigated A000607 with the
**compositional-template** layer enabled, which can express the
Vaughan compositional form `a · √(n / log n) + b · log n + c`. That
thread is not the subject of this project's sealed state; the cleaner
compositional-template result is held privately and is not part of the
current public record. *Do not infer from this null that A000607 is
incompressible under all apparatus protocols* — only that this blind
bare-sequence protocol returned null without the compositional layer.

## Retest tag

*Original-run only (n=1); null result by protocol.* The null is a
function of the search space (no compositional templates) and the
absence of category-switch hints, not a general claim about prime-
partition asymptotics.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`, section
  *Asymptotic-Law Sandbox Recoveries (Per-Substrate)* (A000607 bullet).
- Working directory (private): `projects/gp088_oeis_a000607/`.
- Next falsifier or source-design step: enable the
  compositional-template layer (Stage-2 depth-1) before re-running;
  Vaughan's `√(n / log n)` topology is the candidate to test under that
  configuration.
