# GP-147 Gate Discovery Validation — Public Claim Summary

> Public-evidence surface for an apparatus hardening project on the
> gate library. Working directory private; cited by
> `docs/public_claim_register.md` under *Apparatus Self-Audits*.

## Claim

Six file-level guardrail gates were added at the Phase-D / E¹ bridge of
the `make discover` pipeline, on the hypothesis that every
mathematically wrong claim-artifact will violate at least one of the
named hazards H1–H8 before external submission. The Phase-C admission
gates (gp136–gp138) and gp139 Lean-kernel hardening are held fixed as
shipped; the six new gates (e.g. `bridge/continuum_limit_gate.py` for
hazard H1, continuum-limit instability, with `EXACT_SYMBOLIC_VETO`
provenance) augment them. Apparatus-internal champion score:
**88 / 100**.

## What this hardens

The project closes the gap between an apparatus's *output* veto and
its *input/process* veto: prior gates checked the candidate claim,
the new gates check the *artifact's structural admissibility* against
the hazard catalogue before any human editing. This is the canonical
INS-006-adjacent "negative-space" hardening — failure modes that
would otherwise pass an output-only check now trip on structural
admissibility.

## Retest tag

*Original-run only (n=1); methodology / framework claim.* Each new
gate is anchored to a *named* hazard and a *named* admissibility
contract; the hardening discipline is what generalizes, not the
specific six gates.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Apparatus Self-Audits* (`gp147_gate_discovery_validation`).
- Working directory (private): `projects/gp147_gate_discovery_validation/`.
- Related: apparatus hardening review
  [`projects/gp156_apparatus_hardening_review/public/CLAIM_SUMMARY.md`](../../gp156_apparatus_hardening_review/public/CLAIM_SUMMARY.md).
