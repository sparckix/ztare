---
description: "Final bounded disposition of the AxiomPack binary [50,20,14] structured-successor campaign."
---

# Binary `[50,20,14]` structured successor: final disposition

Date: 2026-07-23

Attempt: `attempt-94ec5a8edc72497d96dca15be93b7e85`

## Outcome

The frozen success criterion was not met. The campaign produced three durable
wave-3 generator matrices, and the registered `binary_linear_code.v1`
boundary checked every nonzero message for each matrix. All three matrices
have rank 20 and fail the required distance 14:

| execution coordinate | exact distance | rejecting message | codeword | verification receipt |
|---|---:|---|---|---|
| `c15c1116c75883f900601534f1f9c546a35ddfaf38922f52f82f75ba3fc8b4a8` | 13 | `0x00004` | `0x0064f44c80004` | `5020bf8d3091345ae267205fbd8c3c33201a9bcc124f0a76b6b9a1a5c211112e` |
| `d21259df62764748486786d313056fb456377f874cc056569a59754227286c64` | 13 | `0x00004` | `0x3150a13c00004` | `a6492e604fd965018599563194b325df4d1dc4bcd1699af67cf88f1c677bfd97` |
| `2e31975410d833262e65b8b7aebfbb0c2312726c81ee8bb19e4247ecc832aa75` | 12 | `0x00004` | `0x1e0880cb00004` | `aced9f1d45ddd86d3c896c249398c6d3e17e07d74c02b6bf4552038bc44f314f` |

Each distance result examined exactly `1,048,575 = 2^20 - 1` nonzero
messages. Boundary completion receipt:
`3b9de1e76912c08a4af46d1c21d1d87ae152e70e6dab0f8a934be472a91cc762`.

No reviewed finite construction family was completely enumerated. Therefore
this run establishes neither existence nor nonexistence of a binary
`[50,20,14]` code, and it does not change the table interval

\[
13 \le d_2(50,20) \le 14.
\]

## Information gained

The same normalized message, `0x00004`, realizes the minimum in all three
wave-3 candidates. The failure is concentrated in a shared low-weight
direction rather than spread across unrelated combinations. The next
construction chart should expose that exceptional direction as an explicit
constraint or quotient coordinate before proposing another matrix.

The preferred successor remains the coset/syndrome-extension chart developed
in `coset_extension_pencil.md` and `coset_syndrome_certificate_pencil.md`.
Its generator should work with canonical code coordinates and admissible
syndrome/coset data, while the exact matrix checker remains the lowering
referee. A fresh campaign must freeze a finite parameter extent before it can
earn a family-scoped null.

## Apparatus disposition

Cold replay recovered the three campaign-authored candidates from durable role
artifacts and routed them through the registered data-only boundary. Provider
usage stayed `34 -> 34`; the recovery transition receipt is
`edfaa1179c1cb0d30407fa0b39f6431e9bf6d1f637261a309f51047e646701b8`.

The recovery work repaired general lifecycle invariants: candidate-outcome
memory survives cold reconstruction; the latest append-only budget stop owns
retry identity; immutable authority slots are bounded and link-safe; a
budget-stopped run can authorize only its exact witness boundary; and that
activation is consumed after adjudication. These rules are adapter-neutral.

## Final campaign status

- target witness: absent;
- reviewed family exhaustion: absent;
- exact candidate rejections: three;
- provider-free replay: complete;
- next scientific representation: coset/syndrome extension with the shared
  low-weight direction carried as negative evidence;
- forecast outcome: unsuccessful.
