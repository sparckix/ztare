# Orphaned-attempt recovery receipt

Source attempt:
`attempt-3675702211534d2abcf399a2011bdcfc`.

Frozen packet digest:
`sha256:cf3c2df7358cc7301ebf1582529bd4bdf5c196827325c0c3c82a855b1f20d6ed`.

The attempt retained its campaign packet, signature, context, budget journal,
and prompt/result call artifacts. It did not retain
`campaign_signer_public.pem` or `private/campaign_signer.pem`. Consequently the
signature is **unverifiable**, not disproved. The source packet is preserved
unchanged and is not re-signed.

## Cause

`run_frontier_campaign_definition` generated the attempt keypair before
navigation but persisted both keys only in its final cleanup. The stale
systemd-run service was stopped with `SIGTERM`; Python cleanup did not execute.
Durable model calls survived, while the in-memory keypair did not.

The general repair persists the attempt keypair immediately after the
directory owner creates the attempt and before provider work. Regressions
`test_campaign_signer_is_persisted_before_provider_work` and
`test_attempt_initializer_owns_first_write_after_directory_creation` check the
ordering, ownership, and private-key file mode.

## Typed successor extraction

No mathematical request was authored by the host. The corrected runtime
replayed two isolated prompt/result streams against the frozen context and
reconstructed their host-bound language requests:

- lineage 0: 6 calls; terminal result digest
  `a96792e1346deca711fcabe84ba4717199d7f4e77f2d8a2e5f5938f15d4c9174`;
  request
  `theory-language-request:6006693347fb9df51e4bd051ab73c7c02876adc408830ccdf561672c0efa2187`;
- lineage 1: 7 calls; terminal result digest
  `ede456b6334e75d9c5eca74f2c0069a82cbe80398b4627ed98549f035618c6c5`;
  request
  `theory-language-request:54104e94c5cad5353f77381f58cf3235015405ef3e164dd1db269c619f752323`.

The successor input is
`orphaned_attempt_successor_input.json`, input SHA-256
`2a898467dba20c9d25038272dfe3de91716b4dd380230a33e9589cacaab71f0a`.
It carries the three cited, content-verified trace receipts (`5f45…`, `74ce…`,
and `a5ea…`); context artifact refs remain owned by the frozen context. After
two paid synthesis first-fires exposed downstream contract defects, the next
successor charges only the remaining 37 provider calls. A lineage synthesizer
decides between or composes the two requests; the host does not select one.

Claim boundary: this receipt preserves durable agent-authored requests across
an authority-credential loss. It does not certify the predecessor campaign
signature, restore its attempt identity, or transfer scientific credit from
the successor.
