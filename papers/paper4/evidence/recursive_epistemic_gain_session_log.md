# Recursive Epistemic Gain Session Log (2026-04-10)

## Purpose

This note is the public evidence-side companion to Paper 4's discussion of
recursive epistemic gain. It records, in cleaned form, a single dated session
in which a warm drafting pair missed a structural flaw in an expensive planned
experiment and a cold review surfaced it before the run began.

It is not a seam, not a spec, and not a general proof. It is a scoped evidence
note for one session and one claim.

## Short version

While preparing a pre-registration for a 100-iteration experiment, the warm
drafting pair missed a tautology in Success Criterion 1. A cold review,
operating on the frozen pre-registration and a small failure-family grammar the
warm pair had just extracted from earlier mistakes, identified the problem:
the criterion would have been satisfied automatically by a pre-existing control
condition and therefore could have produced a false positive.

The key point is not that a second read found a bug. The key point is that:

1. the failure family had first been extracted from earlier artisanal work,
2. that grammar was then used to audit a later high-cost artifact, and
3. the resulting catch was translated into deterministic enforcement before the
   expensive run began.

That is the narrow sense in which the gain is recursive.

## What happened

The session unfolded in three layers:

1. A warm drafting pair produced a candidate pre-registration for an expensive
   experiment.
2. The same session produced a small catch grammar from recent drafting
   failures.
3. A cold review of the pre-registration, using that grammar, found a
   decisive flaw the warm pair had missed.

The flaw was not cosmetic. It affected the first success criterion and would
have made the experiment look stronger than it really was.

## Why this matters for Paper 4

Paper 4 argues that recursive systems become unreliable when generation and
evaluation share the same optimization gradient. The session recorded here is a
small but direct instance of that problem one layer above code generation:

- the warm pair had history, momentum, and local commitment to the artifact
- the cold review had neither of those things
- that separation alone was enough to surface a structural error

This is why the paper treats separation as a governance property rather than a
prompting trick.

## Public artifact chain

The public repo contains the deterministic artifacts that resulted from this
session:

- `src/ztare/catch_grammar/rule_3_profile_check.py`
  - deterministic profile check for profile-dependent claims
- `src/ztare/catch_grammar/quote_locality_verifier.py`
  - deterministic sidecar for quote existence and paragraph-locality checks
- `tests/test_rule_3_profile_check.py`
  - known-clean / known-dirty regression pair for the profile check
- `tests/test_quote_locality_verifier.py`
  - regression cases for fabricated quotes, cross-paragraph drift, and related
    grounding failures

These artifacts matter because the session did not end at “the reviewer found a
problem.” The failure was converted into a concrete enforcement floor.

## What was translated into enforcement

Three durable changes came out of the session:

1. A deterministic profile check was added so a run that depends on a named
   pivot profile cannot start if that profile has been silently trimmed.
2. A deterministic quote/locality sidecar was added so future auditor outputs
   can be killed when they cite nonexistent evidence or drift across
   paragraphs.
3. The wording of the relevant catch-grammar rule was tightened to match the
   deterministic sidecar rather than leaving a looser prose formulation in
   place.

This is the central point for the paper: the catch became a rule, not just
an anecdote.

## Honest scope

This is an `N=1` demonstration, not a general theorem.

It does **not** show:

- that cold review is sufficient in general
- that the catch grammar is complete
- that the full semantic side of the audit is already automated
- that the operator can be removed from the loop

It **does** show something narrower:

- a warm pair can miss a structural flaw
- a cold review can catch it
- the catch can be turned into deterministic enforcement before an expensive
  run proceeds

That narrower claim is the one Paper 4 relies on.

## Relationship to the build-pipeline evidence

This note is not a replacement for the supervisor build-pipeline telemetry
bundle in `stage2_derivation_009/`.

The two artifacts support different claims:

- `stage2_derivation_009/`
  - the supervisor can execute a bounded, verified build program to closure
- this note
  - the system can surface and harden against a higher-order drafting failure
    before an expensive experiment is launched

Paper 4 uses both because they are different kinds of evidence.
