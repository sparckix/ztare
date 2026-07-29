# STP wave v2: extraction-invariant pencil

Date: 2026-07-17

Source candidate: `target-conjecture:380439f9ee8cbd031b0cf50ddf08c961d9d7e580e50a918cb4f6a234e54137a7`

## Eigenquestion

For a fixed basepoint `c` and fixed auxiliary map `brace`, does equality of
the reconstructed ternary operations determine equality of all four extracted
binary operations?

## Candidate theorem

Let `T` and `U` satisfy `ExtractionHypotheses` at the same `c` and `brace`.
Then

```text
reconstructed T c brace = reconstructed U c brace
```

if and only if their extracted `star`, `circle`, `left`, and `right`
operations agree pointwise.

No tetrahedron equation, finiteness, or injectivity assumption is proposed.

## Recovery skeleton

Write `R_T = reconstructed T c brace`. The inverse-slice clauses in
`ExtractionHypotheses` give the following recovery formulas:

```text
extractedCircle T c y z       = R_T c y z
extractedStar T c x y         = R_T x y c
extractedRight T c brace x y  = R_T x (brace y) c
extractedLeft T c brace x y   = R_T c (brace x) y
```

The first formula uses `T c (brace q) c = q`; the second and third use
`brace (T c q c) = q`; the fourth reduces to the first formula. Thus equality
of reconstructed operations implies equality of each extracted operation.
The reverse direction unfolds reconstruction, which depends only on
`extractedRight` and `extractedCircle`.

## Kill conditions

- Any recovery formula above fails under the exact five clauses of
  `ExtractionHypotheses`.
- The proof requires an undeclared tetrahedron, bijectivity, or extensionality
  assumption.
- A finite model with common `c` and `brace`, equal reconstructed operations,
  and a differing extracted operation.

## Formal surface

Create one theorem over arbitrary `X`, with pointwise equality on both sides.
Compile the module independently, inspect its declarations for `sorry`, new
axioms, and `unsafe`, then route the terminal proposition through provider-free
ratification.
