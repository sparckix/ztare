# H92 object-linked judgment quotient result

**Status:** rejected by frozen construct kill  
**Machine result:** `h92_object_linked_judgment_quotient/result.json`  
**Result SHA-256:** `60bacd9d859d05bafb37d6f7df59758ce9ce33f16559109174ae00f5dc379e79`

## Result

Two balanced-order pairs completed before the third target arm failed closed.
The completed pairs showed the intended direction:

| pair | target boundary | placebo boundary | target typed uptake | placebo typed uptake | composite delta |
|---|---:|---:|---|---|---:|
| 1 | 13 | 16 | supported transport | contradiction | +0.03 |
| 2 | 13 | miss | supported transport | contradiction | +0.88 |

Descriptively, target typed uptake was `2/2`, placebo spontaneous uptake was
`0/2`, task delta was `+1`, and mean paired composite delta was `+0.455`.
These are partial results; the pre-registered four-pair criterion was not
completed.

In pair 3, before its first charged action, the target controller returned a
syntactically valid 64-hex occurrence ref with a one-character copy error. The
kernel rejected the unknown ref under H92's explicit kill condition. H92 is
therefore `rejected`, despite the favorable completed pairs.

## What failed

H92 correctly separated object identity from words, then exposed a second
category boundary: identity and presentation are distinct.

- The content hash is the evidence authority.
- A controller needs a short, catalog-scoped pointer into that authority.
- Requiring the controller to reproduce a cryptographic digest makes copying
  fidelity part of judgment.

The brain analogy is sparse local addressability. A working plan recruits an
assembly or channel through connectivity; it does not reconstruct a molecular
fingerprint as a symbol string. The matching architecture is a catalog-bound
presentation assignment such as `o00 -> object:<sha256>`. The actor emits the
short handle; the bridge resolves it to the exact occurrence before any
contract or credit operation.

This is already consonant with the existing fiber-planning distinction between
partition identity and presentation assignment. The controller/worldmodel
bridge had failed to carry that distinction across `alpha_judgment`.

## Instrumentation finding

The failed pre/post proposal pair was not persisted before reference
validation, so the exception contains the bad ref but the raw pair is absent
from the experiment directory. The repaired harness must checkpoint raw
proposal calls before resolution or compilation.

## Next discriminator

Use deterministic, role-free handles (`o00`, `o01`, …) scoped by an immutable
catalog-presentation digest. Persist raw pre/post handle proposals before
resolution. Resolve handles to exact occurrence refs inside the adapter, then
run two new alternating-order pairs. Unknown handles, presentation drift,
weak typed uptake, or external reversal still fail closed.
