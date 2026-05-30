# Decision-history calibration (GP-148 self-applied)

_Generated 2026-05-05 13:49 from `research_areas/EXPERIMENT_TRACK_RECORD.md` F-rows + `ztare_workspace/gates/resolved/` + `org/directives/`._

This is the empirical evidence base for broadening role `authorized_paths` and mandate scope. Each broadening recommendation in §4 cites historical decisions where the agent drove closure without principal-explicit input.

---

## 1. Totals

- Closed decisions analyzed (F-rows): **262**
- Principal-driven: **23** (9%)
- Agent-driven: **157** (60%)
- Mixed: **27** (10%)
- Unknown: **55** (21%)
- Resolved gates (any source): **9** total
- Principal directives filed: **9**

## 2. Role-affinity breakdown

Each F-row's source paths map (longest-prefix-wins) to one of the four roles. The classification within each role is what we use to calibrate broadening.

| Role | Total | Principal | Agent | Mixed | Unknown | Agent-share |
|---|---|---|---|---|---|---|
| engineer | 7 | 0 | 5 | 2 | 0 | 71% |
| research_director | 120 | 9 | 102 | 9 | 0 | 85% |
| principal | 1 | 1 | 0 | 0 | 0 | 0% |
| unknown | 134 | 13 | 50 | 16 | 55 | 37% |

## 3. Top-touched directories

| Directory | Total touches | Agent-driven | Principal-driven |
|---|---|---|---|
| `projects/ns_millennium_hunt` | 75 | 63 | 8 |
| `research_areas/private` | 45 | 35 | 1 |
| `projects/gp163d_unified_accel` | 19 | 16 | 1 |
| `ztare_proofs/ZtareProofs` | 13 | 11 | 0 |
| `projects/survey_s1` | 7 | 7 | 0 |
| `projects/gp154_scaling_law_normalized` | 5 | 5 | 0 |
| `src/ztare` | 5 | 5 | 0 |
| `projects/gp023_planck_sandbox_06` | 4 | 3 | 0 |
| `projects/gp023_sandbox_09` | 3 | 3 | 0 |
| `projects/riemann_operator_search` | 3 | 3 | 0 |
| `org/mandates` | 2 | 0 | 1 |
| `projects/gp152_framer_architecture_audit` | 2 | 2 | 0 |
| `projects/gp145b_saw_narrow_null` | 2 | 2 | 0 |
| `docs/concepts` | 2 | 2 | 0 |
| `projects/gp023_crucial_01` | 2 | 1 | 1 |
| `projects/gp116_cot_exchange` | 2 | 2 | 0 |
| `rubrics/gp154_scaling_law_normalized.json` | 1 | 1 | 0 |
| `scripts/external_run_monitor.py` | 1 | 0 | 0 |
| `scripts/verify_v1_3_frame_invariance.py` | 1 | 1 | 0 |
| `projects/gp153_framer_spec_critique` | 1 | 1 | 0 |

## 4. Mandate broadening recommendations

For each role, recommend `authorized_paths` broadening based on directories where ≥3 historical F-rows show agent-driven closure with no principal-explicit signal. Each recommendation cites examples.

### engineer

| Directory | Agent-driven F-rows | Examples |
|---|---|---|
| `ztare_proofs/ZtareProofs` | 4 | F-GP186-NS-DECISIVE-FORK-AUDITS-01, F-GP186-NS-PROOFSEARCH-R5-POSTRUN-01, F-GP186-PHASE5BU-01 |

### research_director

| Directory | Agent-driven F-rows | Examples |
|---|---|---|
| `projects/ns_millennium_hunt` | 62 | F-GP186-NS-R5-TRANSPORT-SCALE-AUDIT-01, F-GP186-PHASE5CF-02, F-GP186-PHASE5CG-PRESSUREL2-01 |
| `research_areas/private` | 35 | F-GP154-RAWV22-01, F-GP163D-STENCILINV-01, F-GP186-PHASE5-01 |
| `projects/gp163d_unified_accel` | 16 | F-GP163D-STENCILINV-01, F-GP163D-OFFDIAG-LOCAL-N48-01, F-GP163D-COS4-SUSCEPTIBILITY-01 |
| `ztare_proofs/ZtareProofs` | 7 | F-GP186-PHASE5AP-01, F-GP186-PHASE5AQ-01, F-GP186-PHASE5AT-01 |
| `projects/survey_s1` | 7 | F-SURVEY-S1-01, F-SURVEY-S1-02, F-SURVEY-S1-03 |
| `projects/gp154_scaling_law_normalized` | 5 | F-GP154-RAWV22-01, F-GP154N-AXIS-01, F-GP154N-AXISLIVE-01 |
| `projects/gp023_sandbox_09` | 3 | F-CAP-FLASH-RC-01 |
| `projects/gp023_planck_sandbox_06` | 3 | F-GP023-S06-01 |
| `src/ztare` | 3 | F-GP090-01, F-GP103-01 |
| `projects/riemann_operator_search` | 3 | F-GP125-01, F-GP125-BIMODAL-GAP, F-GP125-A10-DENSE-01 |

### unknown

| Directory | Agent-driven F-rows | Examples |
|---|---|---|

## 5. Caveats

- Classifier is heuristic. Keyword + path signals approximate principal-vs-agent; manual review of borderline F-rows is the right next step before applying broadening.
- F-rows undercount engineer-role work: many bug fixes / refactors close without an F-row (commit-only). Use git log for that channel separately.
- INS-row references force `principal` classification. That's intentional (paper-grade findings are principal-blessed) but means decisions that landed an insight AND mechanized something appear `mixed`, biasing the agent-share down.
- This is a snapshot. Re-run after applying broadening to see whether agent-share trends up (intended effect) without principal-driven decisions getting silenced (failure mode).
