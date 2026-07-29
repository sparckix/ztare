# Adjacent-shell rigidity of the public equivariant Keller map

**Status:** exact characteristic-zero calculation; a bounded formal-rigidity
result extending the same-degree theorem by the complete first omitted
equivariant degree shell. Novelty remains provisional pending specialist
review.

## Coordinate enlargement

Retain

\[
\gamma=1-\frac32v+t,\qquad P=\beta\gamma,\qquad
Q=\alpha\gamma^2,
\]

and the normalized coordinates `a=-3/2`, `b_(1,0)=1/2`. Increasing each
component-degree ceiling by one adds exactly

\[
b_{4,0},\quad b_{1,2},\quad c_{5,0},\quad c_{2,2}.
\]

These coordinates come from the complete equivariant degree lattice, not
from the weighted-lift ansatz.

## Exact result

All 15 nonempty subsets of the four-coordinate shell were checked over
`QQ`. Eleven subsets add no tangent direction. The four subsets containing
the pair `(b_(1,2), c_(2,2))` without a compensating restriction expose one
additional tangent.

For the full shell, the Keller coefficient scheme has:

- 51 coefficient equations;
- 20 normalized coefficient variables;
- linearization rank 18;
- a two-dimensional tangent space.

Write its two tangent parameters as `(r0,r1)`. The shell projection is

\[
(b_{4,0},b_{1,2},c_{5,0},c_{2,2})=(0,r_1,0,r_1).
\]

The exact cokernel-valued quadratic obstruction ideal has reduced basis

\[
\langle r_1^2\rangle.
\]

Thus the newly exposed shell direction cannot lift to order two. The old
same-degree direction `r0` does lift to order two because the previously
absent coordinates `b_(4,0)` and `c_(5,0)` can appear as quadratic
corrections. This explains why the same-degree obstruction disappears after
the support enlargement.

That escape stops at order three. Parameterizing the most general
second-order correction by both tangent directions and imposing all
third-order compatibility conditions yields nonzero rational constants,
independent of both correction parameters. The raw nonzero values include

\[
\frac1{216},\quad -\frac{11}{486},\quad \frac1{18},
\quad -\frac3{64},\quad \frac{27317}{5832}.
\]

Consequently neither projective tangent direction admits a formal lift. The
normalized public point has no nonconstant formal arc in the full adjacent
degree-shell coefficient scheme.

## Interpretation

The calculation isolates the mechanism hidden by the earlier cancellation.
The first new support pair creates an infinitesimal direction, but the
quadratic obstruction makes it nilpotent. The older tangent can borrow two
higher-degree coordinates for one order, but its failure is concentrated in
the next cokernel compatibility class. This is stronger information than a
same-degree rank computation and identifies the next exceptional set to
study.

## Claim boundary

This is a local, normalized, equivariant, adjacent-degree statement. It does
not classify arbitrary-degree Keller maps or prove global rigidity. The
subsequent cumulative-shell calculation identifies these failures as the
first layers of a filtered deformation problem: the known cubic family needs
five support shells for cancellation, and its eventual tangent is a
Hamiltonian formal-coordinate direction while its generic fiber degree still
jumps at higher order.

The deterministic replay is
[`equivariant_public_map_adjacent_shell.py`](equivariant_public_map_adjacent_shell.py).
It reconstructs the public base point, enumerates every shell subset, derives
the coefficient equations, computes exact tangent and cokernel spaces, and
checks the quadratic and third-order obstructions without floating-point
rank decisions. The continuation is recorded in
[`equivariant_public_map_cumulative_shells_result.md`](equivariant_public_map_cumulative_shells_result.md).
