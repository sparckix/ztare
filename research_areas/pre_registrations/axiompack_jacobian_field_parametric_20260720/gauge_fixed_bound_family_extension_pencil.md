# Generic fixed-bound family extension

## Eigenquestion

Given the complete compatible affine family of logarithmic
Hamiltonian/source contacts through order \(n-1\), all with source degree at
most \(D\), does the full family extend through order \(n\) at the same bound?

For the current discriminator the input is the complete degree-nine family
through order seven and the question is whether it extends through order
eight.  A single carried witness is insufficient: the lower-prefix
parameters must remain symbolic until the order-eight compatibility locus is
computed.

## Governing object

The object is a transition between compatible-family states, not an
order-specific solver:

\[
\mathcal F_{n-1,D}\longmapsto
\begin{cases}
\mathcal F_{n,D},&\text{if the compatibility locus is representable by
polynomial affine branches},\\
\varnothing,&\text{if the exact compatibility ideal is the unit ideal},\\
\text{unresolved algebraic locus},&\text{otherwise}.
\end{cases}
\]

A state owns:

- the fixed source bound \(D\) and completed order;
- the current rational parameters;
- every target and source logarithmic field through that order;
- the seed symbols and Jacobian.

Equality is coefficientwise replay of the formal target/source exponentials.
An extension must not silently select one point or one component of the
compatibility locus.

## Order-independent transition

At order \(n\):

1. Compute the parameter-polynomial residual
   \[
   R_n=F_n-n![s^n]\exp(B_s)\exp(A_s)F_0.
   \]
2. Build the complete linear image
   \[
   L_{n,D}(Y,K)=dF_0Y+X_K(F_0),
   \]
   with \(\deg Y\le D\) and the exhaustive \(C\)-normal-form target window
   derived from the residual component degrees.
3. Pair the residual coefficient columns with a basis of the cokernel of
   \(L_{n,D}\).  These pairings generate the compatibility ideal in the
   lower-prefix parameters.
4. Decompose every split rational compatibility branch without choosing a
   numerical lower prefix.  A constant obstruction kills the branch.
5. On each branch, solve every residual coefficient column in the image,
   add a basis of \(\ker L_{n,D}\) as the new order-\(n\) parameters, and
   replay the direct order-\(n\) identity.

The transition is independent of the family order.  Legacy modules provide
only the initial family state.

## Discriminating checks

1. Reproduce the complete order-five transition from the order-four family:
   same compatibility equations and solution, same image rank/nullity, and
   coefficientwise replay.
2. Reproduce the complete degree-nine order-seven family from the existing
   degree-nine order-six family.
3. Apply the same operator at order eight.

## Kill conditions

- A residual coefficient survives after the advertised compatibility
  substitution.
- The direct image of the constructed \(Y_n,K_n\) differs from \(R_n\).
- A nonlinear compatibility component is numerically selected or discarded.
- The target window is chosen by a fixed Hamiltonian-degree cutoff rather
  than the \(C\)-normal component window.
- A witness extending one lower prefix is reported as the based-uniform
  minimum.

## Claim boundary

Compatibility at bound nine proves \(c_8\le9\) in the declared first-order
slice.  Incompatibility at bound nine proves only \(c_8>9\); the exact value
then needs the first higher compatible bound.  No finite prefix determines
an all-order growth law.
