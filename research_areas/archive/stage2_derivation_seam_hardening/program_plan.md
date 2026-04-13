# stage2_derivation_seam_hardening Program Plan

- manifest: `/Users/daalami/figs_activist_loop/supervisor/program_manifests/stage2_derivation_seam_hardening.json`
- completion_policy: `manifest_exhausted_to_D`

## Packets

### 1. Seam-local evaluator and four-fixture fail-closed gate

- packet_id: `derivation_evaluator_v1`
- status: `complete`
- target: `derivation_boundary`
- summary: Freeze mismatch vocabulary, derivation record, fail-closed rule, and four deterministic seam fixtures for fabricated or contradicted safe-harbor anchors.
- allowed_artifacts:
  - `src/ztare/validator/stage2_derivation.py`
  - `src/ztare/validator/stage2_derivation_fixture_regression.py`
- success_condition: Fixture regression passes 4/4 and fabricated safe-harbor anchors fail closed.

### 2. Wire the seam gate into the live Stage 2 handoff path

- packet_id: `stage2_live_handoff_integration`
- status: `complete`
- target: `derivation_boundary`
- summary: Integrate `evaluate_derivation_seam()` into the live `build_stage2_handoff()` path as the kernel-facing fail-closed gate so bad upstream derivations stop before downstream routing.
- depends_on: `derivation_evaluator_v1`
- allowed_artifacts:
  - `src/ztare/validator/hinge_handoff.py`
  - `src/ztare/validator/stage2_derivation.py`
  - `src/ztare/validator/stage24_bridge_fixture_regression.py`
  - `src/ztare/validator/stage4_fixture_regression.py`
- success_condition: Live Stage 2 handoff uses the seam evaluator or an equivalent fail-closed sidecar, preserving frozen downstream contracts while blocking fabricated safe-harbor anchors.

### 3. Close out and promote seam hardening

- packet_id: `stage2_seam_promotion`
- status: `complete`
- target: `derivation_boundary`
- summary: After live integration is verified, route the program to human promotion/closure instead of silently looping to another packet.
- depends_on: `stage2_live_handoff_integration`
- success_condition: Manifest is exhausted, verifier passes, and the program pauses at human review for promotion or closure.
