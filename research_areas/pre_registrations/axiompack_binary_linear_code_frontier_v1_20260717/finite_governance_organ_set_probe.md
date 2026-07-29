---
description: "Pre-registered repair probe for the finite LeanMill governance-organ set."
status: closed_pass
date: 2026-07-17
---

# Finite governance-organ set probe

## Identity boundary

Lean remains the proof-soundness authority. LeanMill's common governance path
owns a fixed set of domain-neutral anti-laundering checks. Theory adapters own
domain lowering and certificate production; they may not add, omit, or replace
governance organs.

## Hypothesis

All six required anti-laundering organs now live under `src/ztare/gates`.
Replacing the compatibility-era filesystem discovery with an explicit imported
organ map will preserve current verdicts while making absence of a required
organ an import failure instead of silently reducing the check set.

## Discriminating test

1. Import `ztare.gates.lean_proof_gate` and assert the exact six-name organ map.
2. Run the target-scope regressions for namespaced targets and nested helper
   composition.
3. Run the ratification and closed-artifact regressions that consume the common
   governance result.
4. Confirm no filesystem fallback or optional `None` result remains in the
   organ resolver.

## Success criterion

- the organ map is exactly the frozen six-name set;
- all focused regressions pass with unchanged verdict semantics;
- removing or renaming a required organ would fail module import or map
  construction;
- no theory-specific vocabulary enters the common verifier.

## Kill conditions

- static imports create a circular dependency;
- any existing accepted/rejected control changes without a separately explained
  semantic defect;
- the repair requires an adapter-specific branch in the common verifier.

If killed, retain the current loader but make every required-name miss a typed
verifier-unavailable outcome. Do not add another governance organ for this
repair.

## Result

Passed. `lean_proof_gate` now imports an explicit, immutable six-module
`ANTI_LAUNDERING_ORGANS` implementation map. The compatibility-era `importlib`
loader and its `scripts/public/control` fallback were removed; a missing
required module now prevents the verifier module from importing.

The completed authority algebra has three finite code-owned layers:

- six anti-laundering implementations;
- eleven target-governance authorities, roster SHA-256
  `6c278e4c552be6c597d7966f6453d0c8a1c9e98907cb3ebfcf6b5c35a790217f`;
- fourteen final-ratification authorities after adding compile, matched-control,
  and axiom-allowlist receipts, roster SHA-256
  `dfe23b3412b575d0868979eed73087257baee696fab06cf07fce18bf6f2bdd82`.

Both rosters are immutable `frozenset` values in
`src/ztare/leanmill/ratification_policy.py`. The executable implementation map
asserts equality with the six-organ policy set at import time. An adapter or
runtime plugin therefore cannot add, omit, or replace an authority.

Regression evidence:

- `tests/test_lean_proof_gate_target_scope.py` carries the exact finite-set,
  roster-digest, namespaced-target, and typed-unavailability controls;
- `tests/test_ratification_route.py`,
  `tests/test_closed_artifact_finalizer.py`, and
  `tests/test_construction_artifact_ratification.py` exercise the producer and
  consumer boundaries;
- focused `git diff --check` and Python byte-compilation passed;
- policy source SHA-256:
  `ad10712499aafd9e2599ac6983debdb3fbf7a3344fddc6a8cf4472e78dd222c0`;
- verifier source SHA-256:
  `63cb49c019f646d411440f4173ba400846b2464b029c858bcbf7c21b56c1ec22`;
- closed-artifact source SHA-256:
  `4e5f00eb0061ce9d7f645dea41aac09145405da1122f366381631e143a9edb3d`;
- finite-set test SHA-256:
  `26a66f82407bc56347f8191c87d84b63abc45691c18e6a00a04b535c7452be03`.

No adapter-specific vocabulary entered the authority roster.
