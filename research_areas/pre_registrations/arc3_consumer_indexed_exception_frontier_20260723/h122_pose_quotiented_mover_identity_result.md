# H122 result — pose was fragmenting mover identity

Status: **passed**.

The original exact-shape alpha map split the oriented H119 player into two
members and exposed only two action displacements. Canonicalizing colored
component identity over D4 while retaining pose in the abstract state produced
one mover member across all 22 pre-boundary observations.

The recovered action map is complete: action `0` moves `(-6,0)` with support
3, action `1` moves `(+6,0)` with support 7, action `2` moves `(0,-6)` with
support 3, and action `3` moves `(0,+6)` with support 8. All four observed
poses remain distinguishable. Synthetic regression confirms that static
same-palette components remain outside the mover identity.

This repairs the abstraction needed to externalize part of H121's valuable
fast state. It does not yet show that a fresh actor can consume the recovered
map or regain Level-2 performance.

Evidence: `h122_pose_quotiented_mover_identity_result.json`; audit:
`h122_pose_quotiented_mover_identity_audit.py`.
