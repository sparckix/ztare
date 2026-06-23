# Compatibility Mirror

New public docs and command examples use
[`examples/project_packets/`](../project_packets/). This directory remains as a
compatibility mirror for older traces and scripts that still point at the
historical fixture path.

Prefer:

```bash
ztare project intake validate --path examples/project_packets/ready_demo_claims_intake.json
ztare autoresearch trace --project demo_claims --rubric demo_claims --intake examples/project_packets/ready_demo_claims_intake.json --json
ztare project intake validate --path examples/project_packets/malformed_missing_evidence_intake.json
```
