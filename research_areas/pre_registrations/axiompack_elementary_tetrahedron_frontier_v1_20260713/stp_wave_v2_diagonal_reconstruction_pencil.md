# STP wave v2: diagonal reconstruction pencil

Date: 2026-07-17

Source candidate: `target-conjecture:9148011829a954f062313fc608b4eaf9813f2fe3385ea7393fd82256f23dfe7f`

## Eigenquestion

Which hypotheses alone make the published extraction/reconstruction formula
collapse a ternary operation to the middle projection?

## Candidate theorem

Assume

```text
T x x z = x
T x y x = y
Function.Injective (fun y => T x y z)
```

for all indices. At any fixed basepoint `c`, an auxiliary map satisfying
`ExtractionHypotheses` reconstructs `T` if and only if `T x y z = y`.

The tetrahedron equation and the finalist-specific cross identity are absent.

## Forward skeleton

1. `brace (T c y c) = y` and `T c y c = y` imply `brace y = y`.
2. Reconstruction therefore reduces to
   `T x y z = T x (T c y z) c`.
3. Set the first two variables to `y`. Both diagonal instances give
   `T y (T c y z) c = T y y c`; injectivity of the middle slice at `(y,c)`
   yields `T c y z = y`.
4. Substitute this into reconstruction. Comparing the result at `z` and at
   `x`, then using `T x y x = y`, yields `T x y z = y`.

## Reverse skeleton

For the middle projection choose `brace = id`. All five extraction clauses
reduce definitionally, and reconstruction evaluates to `y`.

## Kill conditions

- Any forward step needs the tetrahedron equation or a finalist-only law.
- A model satisfies the displayed diagonal and injectivity package, admits an
  extraction/reconstruction witness, and is not the middle projection.
- The existential auxiliary-map direction cannot be expressed without adding
  a hidden nonemptiness assumption.

## Formal surface

One arbitrary-carrier theorem with the existential `brace` kept explicit.
Compile it independently and submit the proposition to provider-free
ratification.
