# Independent shortening-family oracle

Date: 2026-07-19

## Question

Does any one-coordinate shortening of the frozen `[51,20,14]` control retain
dimension 20 while reaching length 50 and distance at least 14?

## Exact method

For coordinate `j`, shortening is the puncture of

\[
  C_{j=0}=\{c\in C:c_j=0\}.
\]

The oracle enumerates all `2^20-1` nonzero source messages once. For every
coordinate it records the exact least weight among source codewords with
`c_j=0`; puncturing such a word preserves its weight. Independently, it builds
a basis for the kernel of the coordinate functional, punctures that basis,
and computes its GF(2) rank.

## Claim boundary

This decides exactly the 51 one-coordinate shortenings of the byte-frozen
source matrix. It says nothing about other `[50,20]` constructions and does
not grant campaign review or kernel-ratification authority.

## Result

The exact replay examined `1,048,575` nonzero source messages. Every one of
the 51 coordinate shortenings has rank 19 and minimum distance 14, and every
coordinate has an explicit weight-14 source word with zero in that coordinate.
Thus this family consists exactly of 51 `[50,19,14]` codes and contains no
`[50,20,14]` witness.

Receipt SHA-256:
`ba5addf1588ea1d4c337c1f72eae2ed86a20dc25f46b385e38163598936a2861`.

## Replay

`PYTHONPATH=src ./venv/bin/python research_areas/pre_registrations/axiompack_binary_linear_code_structured_successor_v2_20260719/shortening_family_oracle.py`
