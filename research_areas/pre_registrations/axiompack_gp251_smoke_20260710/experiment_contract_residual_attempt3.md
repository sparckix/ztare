# AxiomPack GP-251 — residual-selection smoke, attempt 3 amendment

Recorded 2026-07-10 after attempt 2 froze a finalist and before attempt 3.

Attempt 2 made eight navigator calls and no boundary calls. It froze the
singleton `(x*x)*y = x*y` because the host incorrectly counted the generator
itself and the direct substitution instance `(x*x)*x = x*x` as residual
consequences. Zero-provider replay under the corrected scorer returns no
residual consequence and `ok=false` (receipt
`39da4f56148ff07b88202e4febb77aa29681583cf550f12bd89df7d833336066`).

Attempt 3 tests one apparatus correction: the named magma baseline is now
`leanmill.direct_equational_deduction.v2`, which excludes presentation formulas
and receipts direct substitution instances before residual pricing. Boundary
execution also replays frozen selection receipts and residual coordinates
before dispatch.

All scientific inputs and caps remain those in `campaign_residual.md` and
`experiment_contract_residual.md`: same frozen context, Codex gpt-5.5 low,
20-minute wall cap, zero metered API, navigation before any boundary work.

Success is either:

- an explicit freeze whose host-replayed residual IDs are nonempty and whose
  residual identification bits are positive under v2; or
- a host-receipted `reject_all`, which closes this bounded region as a null and
  triggers a change of mathematical region rather than a weaker baseline.

Kill this scorer version if a frozen finalist contains one of its own premises,
a direct substitution instance classified as residual, or fails deterministic
replay before boundary approval. No attempt-2 row may be promoted or repaired
in place.
