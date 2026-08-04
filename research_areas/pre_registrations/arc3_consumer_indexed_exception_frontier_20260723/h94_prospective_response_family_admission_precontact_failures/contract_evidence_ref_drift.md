# H94 pre-contact contract-identity correction

The first H94 launch reached only ARC environment discovery and initial
observation reconstruction. It stopped before controller inference and before
any primitive action.

The proposed H94 object-role contract had replaced H93's final evidence
reference with the H93 result reference. Because evidence ancestry is part of
the contract receipt, this produced a different contract SHA-256 despite
identical object selectors. The response family correctly refused to govern
the altered contract.

Correction before controller contact: retain H93's exact object-role contract,
including its H92 evidence reference. Carry H93 result identity separately in
the response-family source receipt.

A second launch also stopped before controller inference or action. The H90
rehydration check tried to read a convenience `sha256` property that the
credit-state object does not expose. The canonical identity was already
available in `state.to_receipt()["sha256"]`; the harness now checks that field.
