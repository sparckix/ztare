# The proposed Q2C repair removes the prefix itself

## Exact identity

The delayed positive-contact coefficient is the order-one target velocity

\[
V^{\rm tgt}(s)=\lambda sQ^2C.
\]

Because it is a single commuting Hamiltonian letter, its left-Magnus
logarithm is exactly

\[
\Omega^{\rm tgt}(s)=\frac{\lambda s^2}{2}Q^2C.
\]

The previously identified source preimage satisfies

\[
L_2=8\left(\frac12Q^2C\right)(P_0,Q_0).
\]

Now prescribe the proposed target-logarithmic repair

\[
\Delta\Omega^{\rm tgt}(s)
=-\frac{\lambda s^2}{2}Q^2C.
\]

Its exact left-forward-`dexp` image is

\[
\Delta V^{\rm tgt}(s)=-\lambda sQ^2C.
\]

Hence the delayed prefix and repair cancel as target velocities:

\[
V^{\rm tgt}+\Delta V^{\rm tgt}=0.
\]

This is an all-order group identity.  Relative to the normalized
background, the combined target connection is the identity, so its complete
source pullback is also the no-prefix background.  Both \(L_2\) and
\(L_3\) disappear.

Equivalently, for the moving source pullback

\[
\Phi_s(H)=8H(P_s,Q_s),
\]

the induced velocities are \(\lambda s\Phi_s(H)\) and
\(-\lambda s\Phi_s(H)\).  They cancel coefficientwise at every cost.  The
identity lies in \(\mathbb Q[\lambda,s]\), so every fixed rational amplitude
specialization preserves it; there are no remaining amplitude sectors to
collide in this erased branch.

## Why the static cost-three quotient survived

The fixed-cost compiler correctly showed two separate facts:

1. \(L_2\) lies in the pullback image of \(Q^2C/2\); and
2. \(L_3\) is outside every same-cost lift-compatible pullback column.

The second calculation held the lower row fixed.  It did not transport the
change of the cost-two target logarithm through the coupled connection.
Consequently its annihilator is a useful same-cost negative control, but it
is not a post-repair quotient.

Freezing this invalid \(L_3\) and iterating once produces the particularly
misleading response

\[
D_5=[-L_2,L_3].
\]

It has 26 terms and survives every same-cost target pullback.  Weight caps 24
and 30 give the same all-weight witness, whose top pairing is

\[
\frac{6144}{665}[u^6z^{12}]
-\frac{1024}{665}[u^7z^{12}]=1.
\]

This strong-looking quotient is now a regression fixture: a coupled adapter
must reject it because its frozen \(L_3\) premise has already disappeared.

## Deterministic replay

[`gauge_q2c_repair_identity.py`](gauge_q2c_repair_identity.py) checks:

- the target Magnus and forward-`dexp` identities exactly;
- the pullback identity for \(L_2\);
- cancellation of all five monomials in \(Q^2C\); and
- equality with the no-prefix radial staircase through five target rows,
  including source-right and target-left round trips, source normal layers,
  source top terms, target top terms, and both rate bounds; and
- the all-weight frozen-\(L_3\) negative control described above.

The finite staircase is a stress test.  The all-order conclusion follows
from the exact cancellation of the target velocity polynomial.

## Boundary and corrected residual

This result does not negate the all-weight contact-zero associated-grade
recurrence.  It corrects the attempted transition into positive contact.

The next object is the least nonzero positive-contact coefficient over an
arbitrary moving contact-zero backbone.  Subtracting that coefficient's own
target logarithm simply sets it to zero and shifts the least-contact index;
it is not an independent later cancellation.  The required invariant must
be uniform under that shift and must retain fixed-amplitude collisions.
