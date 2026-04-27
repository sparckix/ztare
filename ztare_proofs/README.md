# ZTARE Proof Stubs

Lean 4 proof obligations generated from ZTARE gate harness results.

Each file encodes the empirical verification of a discovered asymptotic law:
gate passes become `#eval` checks on Float bounds (decidable, no `sorry`),
gate failures become exclusion witnesses, and PSLQ identifications become
named axiom conjectures with explicit `sorry` marking the epistemic boundary.

## Setup

Install Lean 4 and Lake:

```bash
# macOS
brew install elan
elan default leanprover/lean4:stable

# Linux
curl https://raw.githubusercontent.com/leanprover/elan/main/elan-init.sh -sSf | sh
```

Build the project (downloads Mathlib, takes 10-30 minutes on first run):

```bash
cd ztare_proofs
lake build
```

## What the proofs verify

Each `.lean` file corresponds to a ZTARE substrate:

| File | Substrate | What is verified |
|------|-----------|-----------------|
| `gp088calibrationa01.lean` | Hardy-Ramanujan (A000041) | 4 gate passes on holdout + farther-tail |
| `gp096sandbox20.lean` | Ring polymer relaxation | Gate bounds on real rheological data |
| `oeis_a000959.lean` | Lucky numbers (A000959) | Gate passes at 50K scale |
| `oeis_a000009.lean` | Distinct partitions (A000009) | Holdout gate pass, rival exclusion |
| `oeis_a000607.lean` | Prime partitions (A000607) | Stage 2 compositional gate passes |

## Reading a proof stub

Gate PASS (sorry-free, decidable):
```lean
def check_holdout_global_residual_pass : Bool :=
  holdout_grid.all fun (n, v) =>
    (Float.abs ((expression evaluated at n) - v)) < threshold

#eval check_holdout_global_residual_pass  -- prints true
```

The `#eval` line runs the computation in the Lean kernel. If it prints `true`,
the gate bound holds on every point in the holdout grid. No `sorry` needed.

PSLQ conjecture (sorry-bearing, epistemic boundary explicit):
```lean
-- axiom pslq_a : a = pi*sqrt(2/3)  -- CONJECTURE (sorry)
```

The `sorry` marks where empirical measurement ends and mathematical conjecture
begins. The sorry-free portion (gate checks) is certified. The sorry-bearing
portion (exact constant identification) is a challenge to the community.

## Regenerating proof stubs

After running `make discover` on a substrate:

```bash
python -m src.ztare.formal.lean_compiler --project <name> --output ztare_proofs/ZtareProofs/<name>.lean
```

Then add the import to `ZtareProofs.lean` and rebuild:

```bash
lake build
```

## Architecture

Product A (Certified Empirical Bounds): `#eval` on Float arithmetic.
The Lean kernel verifies that the model predictions match the holdout
data within pre-registered tolerances. No theorem proving required.

Product B (Automated Conjectures): PSLQ maps fitted floats to exact
constants. The conjecture is published with an explicit `sorry` that
names the logical gap. The community can discharge it or refute it.

Product C (Deductive Proofs): Killed by design. Formalizing the circle
method or Meinardus theory in Mathlib is a multi-year project outside
the scope of this apparatus. See GP-081 seam for the panel debate.
