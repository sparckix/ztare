# T2-groupoid reconstruction question: confirmatory pencil

Date: 2026-07-15

## Recording status

An exploratory replay of the preserved finalist-one table already exposed the
candidate counterexample described below. This file does not claim
pre-registration of that observation. It freezes the subsequent confirmatory
formal test, exact source reading, and kill conditions before the Lean artifact
is written.

## Named question

Section 9.3 of Bardakov et al., *Set-Theoretical Solutions of Simplex
Equations* (arXiv:2206.08906), extracts a second tetrahedral 4-groupoid from an
elementary 2-solution `T=[·,·,·]` under a basepoint `c` and unary map `{·}`.
Preprint Question 9.12, published as Question 9.69 in *Matematicheskie Trudy*
27(1), asks whether the reconstructed ternary operation

\[
x\mathbin{\mR}(y\mathbin{\mc}z)
=T\bigl(x,\{T(c,y,z)\},c\bigr)
\]

must equal the original `T(x,y,z)`.

## Candidate counterexample

Use the campaign's finalist-one operation on `Fin 3`:

\[
T(x,y,z)=
\begin{cases}
\operatorname{swap}_{01}(y),&x=2\text{ and }z\in\{0,1\},\\
y,&\text{otherwise}.
\end{cases}
\]

The existing kernel artifacts establish the elementary tetrahedron equation
and middle injectivity. The finalist-one laws imply

\[
T(c,x,c)=x
\]

for every `c,x`. Consequently every unary map satisfying the paper's extraction
hypotheses is forced to be the identity. Reconstruction therefore reduces to

\[
T(x,T(c,y,z),c).
\]

The preserved finite replay reports a mismatch for each `c∈Fin 3`.

## Confirmatory formal surface

Create a separate Lean module that defines:

1. the exact four-operation T2-groupoid axioms from the paper;
2. the extraction hypotheses with arbitrary `c` and unary map;
3. the reconstructed ternary operation;
4. the elementary map `(x,y,z) ↦ (x,T(x,y,z),z)`.

Prove for finalist one:

- the elementary map is bijective and satisfies the tetrahedron equation;
- the identity unary map satisfies every extraction hypothesis for every `c`;
- the four extracted operations satisfy all T2-groupoid axioms;
- every admissible unary map equals the identity;
- reconstruction fails for every `c`, hence no admissible extraction
  reconstructs the original operation.

Prefer kernel reduction (`decide`) or explicit cases for the finite facts. If
native compilation is needed, expose that trust boundary separately.

## Kill conditions

- The paper's operation orientation or quantifier scope differs from the frozen
  formal definitions.
- Finalist one fails one extraction hypothesis for some basepoint.
- Reconstruction equality holds after using the paper's unary map in the
  correct argument position.
- The elementary map is not a bijection under the paper's solution convention.
- A later primary source already answers Question 9.12 with the same or a more
  general counterexample. This kills novelty, while leaving the formal example
  valid.

## Claim boundary

A successful Lean replay is a counterexample to the displayed universal
reconstruction question. It does not classify T2-groupoids or elementary
2-solutions. Novelty remains provisional until a targeted forward-citation and
later-literature audit is complete.
