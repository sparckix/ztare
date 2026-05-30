# GP-186 Phase 5g Symmetry-Break Pre-Registration

Opened: 2026-04-29 18:02:00
Status: active

Hypothesis

The current `chiral_torus_knot` peak object is a symmetry-protected twin-peak mechanism rather than a robust non-symmetric singular-core lead. A tiny asymmetric divergence-free poison should therefore either collapse the late-window growth materially or preserve a twin-peak object, rather than converting the event into one dominant clean peak.

Eigenquestion

Is the knot branch structurally robust to symmetry breaking, or is the current high-intensity event protected by exact involution symmetry?

Discriminating test

Run the knot branch only with three starts:

- clean baseline
- `0.1%` asymmetric divergence-free poison
- `1%` asymmetric divergence-free poison

at fixed apparatus and fixed resolution (`N=256` default, `N=384` if budget allows), with peak capture enabled.

Success criterion

The phase succeeds if it cleanly distinguishes among:

- `single_peak_survives_poison`
- `twin_peak_persists_under_poison`
- `symmetry_death_under_poison`

using the saved top-set component counts, peak capture sidecars, and late-window slopes.

Failure criterion

The phase fails if the poison implementation is not divergence-free, is numerically destabilizing in a way unrelated to the branch physics, or if the variant outcomes do not change the causal interpretation.

Do-not-do

- Do not widen the ansatz search.
- Do not claim that survival under poison is already a proof.
- Do not spend larger GPU on a higher-N ladder before the symmetry-break question is answered.
