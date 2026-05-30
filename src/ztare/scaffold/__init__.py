"""Substrate and GP-project generator.

Takes a Ground Truth spec and emits the full artifact set under
``projects/<project>/`` with Division A / Division B information
isolation enforced:

- Division A (GT-aware, never mutator-visible): ``substrate_gt.py``,
  ``evidence_holdout.txt``, ``.denylist``.
- Division B (GT-blind, mutator-visible): ``evidence.txt``,
  ``gate_harness.py``, ``test_model.py``, ``thesis.md``.

The discipline that keeps mutator-visible material free of ground
truth.
"""
