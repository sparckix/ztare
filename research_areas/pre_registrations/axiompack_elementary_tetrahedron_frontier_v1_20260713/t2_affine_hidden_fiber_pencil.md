# T2 reconstruction: affine hidden-fiber pencil

Date: 2026-07-17

## Recording status

Target-conditioned self-play proposed the affine family below after the
five-card result deck had been frozen. This document records exploratory
output, its adversarial corrections, and the formal kill tests. It is not a
retroactive pre-registration. The surrounding `stp_target_wave_v1.md` is the
pre-registered experiment that generated the candidate.

## Eigenquestion

What information can the extraction of Bardakov et al. lose while still
producing a second tetrahedral 4-groupoid, and can that loss be characterized
as an exact fiber rather than by isolated finite counterexamples?

## Candidate family

Let `A` be an additive abelian group, let `a : A -> A` be additive, let
`mu : A -> A -> A` be biadditive, and fix `c : A`. Define

\[
T_{a,\mu,c}(x,y,z)
  =c+a(y-c)+\mu(x-c,z-c).
\]

After translating `c` to zero, the two sides of the tetrahedron equation
expand respectively to

\[
a^2t+a\mu(x,p)+\mu(ay,q)+\mu(\mu(x,z),q)
\]

and

\[
a^2t+a\mu(y,q)+\mu(x,ap)+\mu(x,\mu(z,q)).
\]

The proposed exact criterion is

\[
\operatorname{TE}(T_{a,\mu,c})
\iff
\begin{cases}
\mu(\mu(x,z),q)=\mu(x,\mu(z,q)),\\
a(\mu(x,z))=\mu(ax,z),\\
a(\mu(x,z))=\mu(x,az)
\end{cases}
\quad\text{for all }x,z,q.
\]

The three necessary identities are isolated by setting variables to zero:

1. `y=t=p=0` gives associativity;
2. `y=z=q=t=0` gives the right centroid law
   `a(mu(x,p)) = mu(x,a(p))`;
3. `x=z=p=t=0` gives the left centroid law
   `mu(a(y),q) = a(mu(y,q))`.

Substitution of the same three identities proves sufficiency. No
commutativity or unit law for `mu` is proposed.

## Extraction and forgotten fiber

Now require `a` to be an additive automorphism and define

\[
\beta(u)=c+a^{-1}(u-c).
\]

Biadditivity gives the five published extraction hypotheses:

\[
T(c,c,c)=c,
\qquad \beta(T(c,x,c))=x,
\qquad T(c,\beta(x),c)=x,
\]

\[
T(\beta(x),\beta(y),c)=\beta(T(x,y,c)),
\qquad
T(c,\beta(x),\beta(y))=\beta(T(c,x,y)).
\]

The extracted operations, in the source orientation, are

\[
x\star y=c+a(y-c),\qquad
x\circ y=c+a(x-c),
\]

\[
x\mathbin{\lhd}y=x,\qquad
x\mathbin{\rhd}y=y.
\]

They do not depend on `mu`. Hence every compatible associative `mu` lies in
one extraction fiber, and the published reconstruction is

\[
x\mathbin{\rhd}(y\circ z)=c+a(y-c).
\]

It equals `T(x,y,z)` for all arguments exactly when `mu=0`. The elementary
map is bijective because, for fixed `x,z`, its middle inverse is

\[
w\longmapsto
c+a^{-1}\bigl(w-c-\mu(x-c,z-c)\bigr).
\]

## Minimal two-point residual

On the pointed two-element carrier, identify `c=0` and the carrier with
`F_2`. Middle-slice bijectivity forces

\[
T(x,y,z)=y+f(x,z).
\]

The fixed-point condition gives `f(0,0)=0`. Two tetrahedron-equation
specializations force `f(0,1)=f(1,0)=0`, leaving only `f(1,1)`. Thus the two
pointed normal forms are

\[
T(x,y,z)=y
\quad\text{and}\quad
T(x,y,z)=y+xz.
\]

The second form is the smallest possible reconstruction failure:

\[
T(1,0,1)=1,
\qquad
\widehat T(1,0,1)=0.
\]

The exact assumption is a **bijective** elementary map, equivalently every
middle slice is bijective. Dropping it kills the dichotomy: Boolean
`T(x,y,z)=xyz`, with `c=1` and identity brace, satisfies the tetrahedron
equation and all five extraction hypotheses but is in neither normal form.

An exhaustive exploratory attack over all 256 Boolean ternary tables, both
basepoints, and all four unary maps found four admissible bijective rows and
exactly the two pointed forms above. This finite enumeration is orientation
evidence, not the terminal proof.

## Prior-art boundary after consequence replay

The associative-ring map

\[
(X,Y,Z)\longmapsto(X,Y+XMZ,Z)
\]

was proved to be a tetrahedron map by Igonin in 2022. Taking `M=1`
already includes the `Y+XZ` family over arbitrary associative rings. The
scalar map

\[
(x,y,z)\longmapsto
\left(x,\frac{y-xz}{k},z\right)
\]

is also published tetrahedron-map prior art. It is the specialization
`a(y)=k^{-1}y`, `mu(x,z)=-k^{-1}xz`, `c=0`. Applying Bardakov's extraction
with `beta(u)=ku` gives reconstruction `y/k`, so the known map already has the
counterexample consequence whenever `xz != 0`.

Consequences for claim scope:

- the associative-product map and a broad first-counterexample claim are
  excluded;
- the existing `Fin 3` theorem remains a valid independent kernel witness;
- live priority candidates are the explicit extraction-fiber theorem, the
  exact associativity-plus-centroid characterization, and the pointed
  cardinality-two classification/minimality result;
- those narrower candidates still require primary-source comparison and
  expert priority review.

This corrects the earlier forward-citation audit. Searching reconstruction
terminology alone was insufficient: retrieved example families must be run
through the target extraction predicate to expose implicit answers.

## Attack vectors and kill conditions

- **Expansion error:** a direct symbolic expansion or Lean normalization
  produces an additional term. Kill or correct the iff before using it.
- **Necessity conflation:** the tetrahedron equation may imply only a combined
  identity if zero specializations were invalid. The additive zero laws must
  be explicit in the formal proof.
- **Centroid omission:** associativity alone is false. Componentwise
  multiplication on `F_2^2` with coordinate-swap `a` violates a centroid law
  and the tetrahedron equation.
- **Extraction orientation:** every one of the five source equations must
  reduce under the displayed `beta`; a left/right or brace mismatch kills the
  extraction theorem.
- **Bijectivity leakage:** invertibility of `a` belongs only to the elementary
  map and extraction results, not to the tetrahedron iff.
- **Two-point overreach:** the dichotomy must retain global middle-slice
  bijectivity and a fixed basepoint. The `xyz` example is the declared
  negative control.
- **Known-family absorption:** if associative-ring tetrahedron literature
  already states the same iff or extraction fiber, demote those portions and
  retain only any demonstrably new consequence.

## Intended formal surface

The first Lean module should use the centered form

\[
T(x,y,z)=a(y)+\mu(x,z)
\]

over an additive commutative group. It should prove, in this order:

1. the exact tetrahedron-equation iff;
2. bijectivity of the elementary map when `a` is an additive equivalence;
3. all five extraction hypotheses at basepoint zero with brace `a.symm`;
4. the four extracted-operation formulas and reconstruction formula;
5. reconstruction iff `mu` is identically zero;
6. an explicit `ZMod 2` instance `T(x,y,z)=y+x*z` if the abstract theorem
   makes the instance concise.

The translated-center theorem and complete two-point uniqueness theorem are
separate extensions. They should not be claimed from finite enumeration alone.

## Stop rule

Continue to kernel ratification if the abstract iff and extraction-fiber
theorems compile without extra mathematical hypotheses. Stop or narrow the
lane if primary literature already contains the same characterization, if the
source extraction fails, or if kernel normalization exposes a missing term.
