# scripts/public/utilities/examples/

> **Up:** [utilities/](../README.md) · [scripts/](../../../README.md)

Input fixtures for `scripts/public/utilities/instance_gate_harness.py`.
One passes, one fails on purpose: together they show the harness both
accepts a well-formed candidate and rejects a malformed one.

| Fixture | What it is |
|---|---|
| `instance_candidate_minimal.json` | A minimal well-formed instance candidate (positive control: the harness should accept it). |
| `instance_candidate_dimensional_violation.json` | A candidate that fails the dimensional gate (negative control: the harness should reject it). |

## Related

- Consumed by: [`instance_gate_harness.py`](../README.md)
