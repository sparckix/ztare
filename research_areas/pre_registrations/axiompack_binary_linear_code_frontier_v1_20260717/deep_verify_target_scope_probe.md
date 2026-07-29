---
description: "Pre-registered multi-declaration target-scope probe for deep governance rechecks."
status: closed_pass
date: 2026-07-17
---

# Deep-verification target-scope probe

## Identity boundary

Every governance detector and re-probe must act on the exact carried theorem
identity. Sibling declarations provide context but may not become the mutated
probe target.

## Hypothesis

The common aggregator correctly scopes shape detection to the resolved target
declaration, but its deep single-lemma and indirect-leakage calls still pass the
whole source to helpers that replace the first `:= by` occurrence. In a file
whose selected target is not first, the deep probe can therefore test a sibling.
Using the canonical named-declaration proof replacer will preserve the full
source while mutating exactly the selected theorem.

## Discriminating test

1. Build a two-namespace source with same-written-name sibling theorems.
2. Replace the selected theorem proof through each deep helper.
3. Intercept the generated probe before compilation and require the earlier
   sibling bytes to remain exact while only the qualified target body changes.
4. Replay target-scope and ratification controls.

## Success criterion

- both deep helpers target the qualified theorem;
- no first-match regular-expression replacement remains on the named path;
- ambiguous or missing target identity returns an inconclusive/unavailable
  result rather than probing a sibling;
- normal focused controls preserve their verdicts.

## Kill conditions

- preserving full source requires reconstructing theorem syntax;
- the repair introduces another Lean parser;
- any adapter-specific branch enters the governance path.

If killed, disable deep verification for multi-declaration sources and return
typed unavailability until the canonical source parser exposes the required
splice.

## Result

Passed. The exact and indirect deep probes now use the canonical qualified
target resolver and named proof-body replacer. Earlier declarations remain
byte-preserved, and only the selected qualified theorem body changes. Missing
or ambiguous selectors return no probe and become typed target-identity
unavailability at the common boundary.

`test_deep_probe_builders_replace_only_qualified_target` and the two
parameterized soft-failure controls in
`tests/test_lean_proof_gate_target_scope.py` cover the positive splice and the
unavailable states. No Lean parser or adapter branch was added.
