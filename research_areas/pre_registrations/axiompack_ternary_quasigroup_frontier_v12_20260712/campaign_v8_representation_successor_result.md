# Representation-successor result (2026-07-13)

Campaign: `leanmill-campaign:31952cd29837a78c5465af0fc334555760d776c20424914ace52a297388e0398`
Attempt: `attempt-d0e1831467e644758af87176dc80360b`

The corrected v8 equational baseline removed the earlier diagonal tautology. The
first frozen program was refuted by one larger-model boundary query; its witness
was returned to the cold navigator, which selected a different two-law program.
The leaf changed lineage but did not request a new theory language.

For a coordinate-recoverable ternary operation `p`, the second program implies

```text
p(x, p(y, z, y), x) = z.
```

Writing `T_a(b) = p(a,b,a)`, the second premise and first-coordinate cancellation
make `T_a` independent of `a`; the first premise then makes the common unary map
an involution. Isabelle checked the implication, and the canonical LeanSource
recheck proved it with empty and leave-one-premise-out failures. Governance
receipt: `4d5398e9eefd808d34c25ea9689018e8b2ba7a36452304f84c9a65896af243fc`.

The bounded source review found the ambient ternary-quasigroup literature but no
exact formula or implication. Its novelty disposition is
`not_located_in_bounded_review`, not a novelty certificate. Interpretation
receipt: `6481f602aa03889d7be56556136da836d3a292a26f577885b64df3d8f6d84f9a`.

Result: one compact, premise-necessary lemma and a successful counterexample-led
lineage pivot; the representation-change discriminator failed. The fixed
finite-equation chart is now a calibrated referee, not the next campaign's
research identity.
