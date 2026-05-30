# scripts/public/audits/

> **Up:** [scripts/](../../README.md) · **Siblings:** [validators/](../validators/README.md) · [analytics_shared/](../analytics_shared/README.md) · [lean/](../lean/README.md) · [control/](../control/README.md)

Gate and judge audits, the backend behind `make gates`. Where
[validators/](../validators/README.md) assert that a static artifact
still matches its contract, these answer the dynamic question: are the
gates real or theater. They mine run logs and source to find gates that
exist on paper but never fire on the failures they exist to catch. They
are themselves run under the gate discipline.

| Script | What it does |
|---|---|
| `audit_gate_coverage.py` | META-GATE 2A, static scope-narrowing linter: catches the gp163d-class blind spot at source level (a function whose own scope quietly shrinks). |
| `audit_gate_effectiveness.py` | META-GATE 2B, dynamic check: mines run logs for gates that engage but never raise a verdict (the historical R20-R24 form_str key bug). |
| `audit_gate_engagement.py` | GP-157 gate-engagement audit (`make gates` backend): which gates in `src/ztare/gates/` are live and wired vs dead. |
| `audit_judge_drift.py` | GP-134 judge-drift audit: reads a project's debate logs and flags three judge-drift patterns. |
| `seam_health_audit.py` | GP-221 periodic corpus audit over the seam tree: parses frontmatter and reports per-seam health. |
| `cross_provider_ns_packet_rescore.py` | Re-scores the same NS Track B packet under gpt-4.1-mini, claude-haiku-4.5, gemini-2.5-flash-lite to expose single-provider scoring bias. |
| `gp156_integration_smoke_test.py` | GP-156 integration smoke test: proves Proposals 2 (attestation) + 3 (fit primitive) actually compose, the check the gp152/153 audits skipped. |
| `run_i5_mode_b_experiment.py` | I-5 Mode B experiment scaffold: tests whether auto-injecting the pattern bank changes outcomes. |

## Related

- The gates these audit: `src/ztare/gates/`
- Static counterpart: [validators/](../validators/README.md)
- Concept: [goodhart at every layer](../../../docs/concepts/goodhart_at_every_layer.md)
