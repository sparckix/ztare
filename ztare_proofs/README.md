# ZTARE Lean Gate Artifacts

Lean 4 gate artifacts generated from ZTARE harness results.

Each file encodes bounded checks around a candidate form: gate passes become
`#eval` checks on finite Float grids, gate failures become exclusion witnesses,
and PSLQ identifications become named conjectural boundaries when present.
These artifacts are not theorem discoveries by themselves; they are executable
receipts for what the harness checked.

For the Navier-Stokes campaign specifically, start with the public journey and
current status checkpoint before reading the large Lean corpus:
[`projects/ns_millennium_hunt/public/JOURNEY.md`](../projects/ns_millennium_hunt/public/JOURNEY.md).
The current NS posture is an obstruction/residual atlas with many conditional
and local Lean surfaces, not an unconditional Clay proof.

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

The `#eval` line runs the finite computation through Lean. If it prints `true`,
the gate bound holds on every listed point in the holdout grid under the encoded
Float arithmetic. That is a bounded gate receipt, not a proof of the underlying
scientific law.

PSLQ conjecture (sorry-bearing, epistemic boundary explicit):
```lean
-- axiom pslq_a : a = pi*sqrt(2/3)  -- CONJECTURE (sorry)
```

The `sorry` marks where empirical measurement ends and mathematical conjecture
begins. The sorry-free portion is the executable gate check. The sorry-bearing
portion is not a claimed closure; it is a named unresolved boundary.

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

Product A (Executable Empirical Bounds): `#eval` on Float arithmetic.
Lean checks that the encoded model predictions match the listed holdout data
within pre-registered tolerances. No theorem proving is implied.

Product B (Candidate Constant Identifications): PSLQ maps fitted floats to
possible exact constants. Any such identification is published with an explicit
boundary that names the logical gap.

Product C (Full Deductive Theory Formalization): out of scope for this artifact
class unless a separate project declares the theorem, assumptions, proof route,
and verification gate. See GP-081 seam for the panel debate.
