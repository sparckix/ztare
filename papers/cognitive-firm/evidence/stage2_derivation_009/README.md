# Stage 2 Derivation Seam Hardening, Run 009 Telemetry

Frozen copy of the supervisor telemetry cited in `papers/paper4/draft.md`
Section 5.6 ("Build Pipeline Evidence"). The original run files live
under `/tmp/stage2_derivation_009/` which is ephemeral; this directory is
the durable audit trail.

## Run identity

- program: `stage2_derivation_seam_hardening`
- manifest: `supervisor/program_manifests/stage2_derivation_seam_hardening.json`
- genesis: `supervisor/program_genesis/stage2_derivation_seam_hardening.json`
- run_id: `stage2_derivation_009`
- packet verified: `stage2_live_handoff_integration` (packet 2 of the manifest)
- program registry status: `closed`, `owner_mode: frozen`

## Files in this directory

- `status.json`, final supervisor status at closure (revision 5, state D,
  `status_reason: program_closed`, `human_gate_resolved: true`).
  Contains the implementation_snapshot with sha256 fingerprints for the
  four authorized artifacts and the complete cost ledger.
- `events.jsonl`, full event stream for the closing revision: spec agent
  registration, implementation agent verification, deterministic verifier
  pass, and human gate resolution.
- `verification_report.txt`, the verifier's own output from the closure
  run, one line per fixture case. 23/23 deterministic cases pass:
  4/4 Stage 2 derivation + 8/8 Stage 2→4 bridge + 3/3 live stage-2 gate
  smoke tests + 8/8 Stage 4.

## Reproducing the verifier verdict today

The verification command from the run is reproducible. Against the
implementation files whose sha256s are recorded in `status.json` under
`implementation_snapshot`, the same three-suite chain returns the same
result:

```
python -m src.ztare.validator.stage2_derivation_fixture_regression && \
python -m src.ztare.validator.stage24_bridge_fixture_regression && \
python -m src.ztare.validator.stage4_fixture_regression
```

This reproducibility is the structural property Section 5.6 claims for
deterministic enforcement: a verifier whose output does not depend on
model temperature or sampling returns the same verdict on the same
inputs regardless of when it is run.

## Key numbers cited in Section 5.6

Directly from `status.json`:

- `program_cost_usd`: 0.64631685
- `refinement_cost_usd`: 0.0
- `spec_refinement_rounds`: 0
- `consecutive_build_failures`: 0
- `gate_on_verifier_pass`: true
- `human_gate_reason`: "contract_promotion"
- `human_gate_resolved`: true

## Write-scope evidence

The packet manifest declares four authorized artifacts:

- `src/ztare/validator/hinge_handoff.py`
- `src/ztare/validator/stage2_derivation.py`
- `src/ztare/validator/stage24_bridge_fixture_regression.py`
- `src/ztare/validator/stage4_fixture_regression.py`

The run's `implementation_snapshot` in `status.json` records sha256
fingerprints for exactly these four paths and no others. The authorized
set and the modified set match exactly, this is the hard-gated write-
scope enforcement Section 5.1 claims for the M-Form's governance layer,
captured as file-level evidence rather than a narrative assertion.

<!-- AUTO-INDEX:START (managed by scripts/public/gen_folder_index.py, edit prose OUTSIDE this block) -->

## Index

**Documents**

- [status.json](status.json)

<sub>0 sub-folder(s), 1 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
