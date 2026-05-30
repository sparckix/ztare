# mine_trajectories.py

## What it does

`mine_trajectories.py` is Stage 1 of the ZTARE trajectory-mining pipeline. It walks every directory under `/projects/` that looks like a ZTARE project (has both a `project_charter.md` and at least one `debate_log_iter_*.md`) and emits one JSON record per iteration into a unified archive at `/analytics/public/ledgers/trajectory/trajectory_archive.jsonl`. One line per iteration, one archive across all projects, so cross-project and cross-iter queries become a single `jq` or `pandas.read_json(lines=True)` call.

For each iteration it parses the debate-log markdown (score, weakest-point, rationale), joins against that project's `workspace/iteration_telemetry.jsonl` (failed gates, gate engagement, stagnation, falsification mode, model ids, champion promotion, score-improved flag), reads the rubric version from `rubrics/<project_slug>.json`, and — best-effort — attaches thesis primitive names from `current_iteration.md` when its `best_iteration` marker points at the iteration in question. Missing or malformed files are logged to stderr as `[warn]` lines and the record is still emitted with nulls; the script never aborts mid-walk.

The extractor is pure-extraction by design. No analysis, no derived metrics, no normalization beyond parsing. Stage 2 (weakest-link taxonomy, score-ceiling signatures, primitive reuse, climb triggers, judge-bias detection) runs against this archive later.

## How to re-run

```bash
python3 /scripts/public/mine_trajectories.py
```

Standard library only (Python 3.13 confirmed; any 3.10+ will work). The script overwrites the archive each run and is idempotent: same inputs produce identical output (records are walked in sorted project slug, then chronological iter_timestamp order).

## Output schema

One JSON object per line at `analytics/public/ledgers/trajectory/trajectory_archive.jsonl`:

| field | type | source |
|---|---|---|
| `project` | str | project directory name |
| `iter_timestamp` | int | unix seconds parsed from `debate_log_iter_<ts>.md` |
| `iteration_index` | int \| null | telemetry `iteration_index` |
| `score` | int \| null | `# Final Score: N` in debate log |
| `weakest_point` | str \| null | `**Weakest Point:** ...` first match |
| `rationale` | str \| null | `**Rationale:** ...` first match |
| `failed_gate_ids` | list[str] | telemetry |
| `gate_engagement` | bool \| null | telemetry |
| `gate_failure_count` | int \| null | telemetry |
| `stagnation_count` | int \| null | telemetry |
| `falsification_mode` | str \| null | telemetry (fallback: run_start) |
| `mutator_model_id` | str \| null | telemetry (fallback: run_start.mutator_model) |
| `judge_model_id` | str \| null | telemetry (fallback: run_start.judge_model) |
| `rubric_version` | str \| null | `rubrics/<slug>.json` `rubric_version` |
| `thesis_primitive_names` | list[str] | `### Primitive N: <name>` in current_iteration.md (only attached when `best_iteration` marker matches this iter_timestamp) |
| `champion_promoted` | bool \| null | telemetry |
| `score_improved` | bool \| null | telemetry |

## Known limitations

1. **Telemetry joins are positional**, not timestamp-based. We sort debate logs by filename timestamp ascending and join index-wise to `record_type: iteration` rows in telemetry. If a debate log is missing for an iteration (harness crash, in-flight) or a telemetry row is missing, downstream rows in the same project will shift by one. Stage 2 should detect this by cross-checking `iteration_index` monotonicity.
2. **`thesis_primitive_names` is only attached to a single iteration per project** — the one pointed at by the `best_iteration` HTML comment in `current_iteration.md`. Historical primitive lists are not reconstructed; earlier iterations report an empty list even if they had different primitives at the time. This is the "best-effort" part of the spec.
3. **`_bench_*` sandbox runs are included** if they have a charter and a debate log. They show up as their own project slugs; filter by prefix if needed.
4. **Rubric versioning is sparse.** Many rubric files lack a `rubric_version` field; those records carry `null`. Do not treat null as a distinct version.
5. **No deduplication.** If two debate logs share an `iter_timestamp` inside the same project (shouldn't happen but filesystem is unpoliced), both are emitted.
6. **Defensive parsing.** Score regex requires exactly `# Final Score: <int>`; non-integer scores or alternate headers (e.g. `## Final Score`) are skipped with null. If Stage 2 needs tolerant parsing, extend `SCORE_RE`.
