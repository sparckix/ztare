# Project Intake Examples

These fixtures show the public pre-kernel intake boundary. `ztare project
intake` is the preferred command; the fixture directory keeps the historical
`project_packets/` name for compatibility.

- `ready_demo_claims_intake.json` is a minimal intake file backed by the public
  `projects/demo_claims/` and `rubrics/demo_claims.json` fixture. It validates
  in a clean checkout and its declared missing-reference falsifier is
  executable through the intake validator.
- `malformed_missing_evidence_intake.json` is intentionally invalid. It has no
  evidence refs, so it must fail before any in-loop autoresearch run.
- `projects/ops_root_cause_diagnosis_demo/ops_root_cause_diagnosis_demo_intake.json`
  is the larger public starter pilot. It validates a synthetic operations
  diagnosis fixture with typed local sources, compiled evidence, non-claims,
  and a next falsifier.

Try them:

```bash
ztare project intake validate --path examples/project_packets/ready_demo_claims_intake.json
ztare project intake falsify --path examples/project_packets/ready_demo_claims_intake.json --remove-ref 'evidence_refs[1]'
ztare autoresearch trace --project demo_claims --rubric demo_claims --intake examples/project_packets/ready_demo_claims_intake.json --json
ztare project intake validate --path examples/project_packets/malformed_missing_evidence_intake.json
ztare autoresearch trace --project ops_root_cause_diagnosis_demo --rubric ops_root_cause_diagnosis_demo --intake projects/ops_root_cause_diagnosis_demo/ops_root_cause_diagnosis_demo_intake.json --json
```

Prefer `ztare project ...` for new commands. `ztare substrate ...` remains a
compatibility namespace for the same project/data surface implementation. The
CLI still accepts `ztare project packet ...` for existing scripts. The intake
file itself is only a boundary check: it does not run RD agents and does not
schedule autoresearch iterations. The trace command is also read-only; it
reports readiness and the exact route command without calling a model.
