# Demo Claims Charter

Purpose: exercise the public autoresearch packet and source-preflight path on a
small repository-local claim.

Bounded claim: the demo claim packet has source and evidence references that
validate in a clean checkout.

Scope:
- Evaluate packet shape, source references, evidence references, non-claims, and
  the next falsifier.
- Do not treat this fixture as a completed autoresearch run.
- Do not infer any scientific result outside the listed repository files.

Success criterion: the candidate keeps the claim bounded to the packet fixture
and preserves the source/evidence references without inventing external support.

Next falsifier: remove the evidence atlas reference or the source file and the
packet should fail validation before in-loop routing.
