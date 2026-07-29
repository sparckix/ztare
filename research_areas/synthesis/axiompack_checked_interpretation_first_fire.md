# Checked interpretation first fire

Date: 2026-07-18

The rebuilt interpretation seam was exercised on two separately named
single-sorted semigroup signatures with the non-identity operation image

\[
x\star y \longmapsto y\cdot x.
\]

The source associativity law translated to

\[
z\cdot(y\cdot x)=(z\cdot y)\cdot x.
\]

Results:

- exhaustive target-model replay through carrier size 2 found no
  countermodel to the translated axiom under target associativity;
- the two-element XOR model satisfied the target law and witnessed that the
  mapped operation is nonconstant;
- the generated conditional Lean task compiled with proof
  `exact (pack.target_assoc z y x).symm`;
- the target-specific axiom audit returned an empty axiom dependency set;
- identical proof bytes failed under the empty and leave-one-out packs;
- the checked interpretation admission was minted with receipt
  `974120386905b01c526f83a4d7e7d1545ceb0e52b6caec1276b13ec937932fcd`.

Key component receipts:

- interpretation:
  `theory-interpretation:807d6335846a988f30a3e213c97e2f41a014c0aa20aecb33d0ea688fdfb31d64`;
- finite implication:
  `0a07ea1fdfe19422775324dbd4dba1824a97633ee9a3116a5454a27c90eb3e16`;
- non-collapse witness:
  `af984d6f957192ad0dc4066824a33e3b31d758b82fc9bb1d43b3152133aa3188`;
- matched premise attribution:
  `21abb0d916c47a8e5725ad6bc3d819a6f15f88c423b24f7765c3f2a79be5af64`;
- axiom allowlist:
  `136d88e4848c0411330a915905c3ac7429f692bd9bd1fb443d3182df7e62ab87`.

This first fire validates the interpretation contract and its formal consumer.
It is not an E4 result: the theories are controlled fixtures, no transported
conjecture cohort or matched de-novo control was run, and no novelty claim is
attached.
