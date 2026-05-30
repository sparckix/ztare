# GP-245 Forecasting Calibration — Methodology Architecture

How this program does LLM forecast calibration rigorously. This is the methodology contract the program upholds; specific findings live in `CLAIM_SUMMARY.md` (program-level claims) and per-subproject workspaces.

Updated 2026-05-29.

## 1. Apparatus shape

Five-family panel (Claude Opus 4.7, GPT-5.5, GPT-5.4-mini, Gemini 2.5 Flash, DeepSeek Chat) firing forecasts on a fixed slate of contracts. Two corpus classes:

- **Internal** — apparatus-internal science estimation: Lean proof tokens, code refactor sizes, paper-section word counts, debugging time. Resolves via instrumented harness measurement. ~45 contracts with `y_known` to date; refire to ~142 parity with external is in flight (task #70).
- **External** — prediction-market and benchmark questions: Polymarket, Manifold, Metaculus, FRED, yfinance, plus the diversified n=42 Metaculus+FRED corpus. Resolves via market closeout or benchmark ground truth. 142+ contracts with `y_known`.

Each forecast call lands a `(contract_id, agent_id, family, primitive, p_success, parsed_json, fired_at)` row in the canonical `pilot_calls` table.

## 2. Storage: forecaster_calibration.db

Canonical DB at `analytics/public/calibration/forecaster_calibration.db`. Single source of truth.

**Tables.**

- `contracts(contract_id PK, question, source, source_corpus, horizon, y_known, post_training_cutoff, task_type, ...)` — every distinct contract once. `y_known ∈ {0, 1, NULL}` (NULL = unresolved).
- `pilot_calls(call_id PK auto, pilot_id, contract_id, agent_id, family, condition, primitive, primitive_base, phase, role, pair_id, p_success, brier, schema_ok, parsed_json, fired_at, raw_json)` — every forecast call. `brier = (p_success - y_known)²` computed at ingest.
- `pilot_runs(pilot_id PK, pilot_name, primitive, corpus, source_jsonl_path, fired_at, n_calls, n_schema_ok)` — metadata per pilot.
- `pre_registrations(...)` — Fisher-z power calculations + legal-verdict commitments fixed before fire.
- `family_elo_by_corpus_class(family, corpus_class, elo, n_games, computed_at)` — refreshed by `ztare forecast elo-refresh`. Not derivable as a SQL view because Elo is iterative.

**Views.**

- `v_corpus_class` — derives `corpus_class ∈ {internal, external}` from `contracts.source`. Heuristic: known external markets (polymarket, manifold, metaculus, fred, yfinance, ...) → external; apparatus-tagged or NULL source → internal. *Definition is policy; revise here.*
- `v_family_brier_by_pilot` — Brier mean per (family, pilot_id).
- `v_family_brier_by_corpus_class` — Brier mean per (family, corpus_class). The headline roll-up. **Source of truth for paper Brier numbers.**
- `v_family_brier_by_subsource` — Brier mean per (family, corpus_class, sub_source, source_corpus). Drill-down for per-platform claims.
- `v_family_brier_by_primitive_corpus` — Brier mean per (family, primitive, corpus). For channel-routing claims.
- `v_pilot_summary` — per-pilot roll-up.
- `v_intervention_vs_baseline` — for paired-permutation interventions (e.g., confident_NO discount vs raw).

## 3. Pre-registration discipline (verdict resolver)

Every claim that lands in `CLAIM_SUMMARY.md` or the working paper passes this gate:

1. **Pre-fire**: Fisher-z power calculator computes required N for the detectable effect size at α=0.05, β=0.20. Required N goes into `pre_registrations` table before fire.
2. **Post-fire**: three legal verdicts only — `h1_supported` (clears the power bar in the predicted direction), `h0_kept` (TOST-equivalent within ±0.05 Brier or ±0.20 ρ bound), `inconclusive_underpowered` (everything else). Replaces "p > 0.05 = no effect" abuse.
3. **Multiple-comparison**: BH-FDR across panel tests where five families are tested simultaneously.
4. **Small-N R²**: leave-one-out R² instead of in-sample R² when k regressors ≥ N/5.

Statistics primitives at `src/ztare/experiment_stats.py` (power calculator, bootstrap CI, paired permutation, Fisher-z Spearman, TOST, BH-FDR, power-aware verdict). Forecasting-specific wrappers in the subprojects' `calibration_stats.py`.

## 4. Per-call workflow

```
prompt template
   ↓
runtime dispatcher (subscription claude/codex via CLI; API gemini/deepseek)
   ↓
schema check (parsed_json must contain {p_success, ...}; schema_ok flag)
   ↓
jsonl ledger (per-pilot, in subproject workspace/)
   ↓
DB ingest (forecast_ingest_smoke_jsonl.py for smokes; per-pilot ingest scripts otherwise)
   ↓
Brier compute (joined with contracts.y_known where resolved)
   ↓
verdict resolver (calibration_stats.py finding <X>)
```

All five panel families share the same prompt template per pilot. Per-family heterogeneity is the measurement.

## 5. Aggregation methodology — Brier + Elo

**Brier (per family, per corpus class).** Lower is better. Headline view = `v_family_brier_by_corpus_class`. Per-subsource drill-down = `v_family_brier_by_subsource`.

**Elo (per family, per corpus class).** Lower-Brier family wins each head-to-head; equal-Brier = draw. K=16, init=1500. Operates over the SHARED-COHORT contracts (where ≥2 families fired). Takes best (lowest) Brier per (family, contract) when a family fired the contract across multiple pilots, to avoid double-counting.

**Why Brier + Elo together.** Brier measures average squared error; Elo measures head-to-head win rate. They diverge when a family makes EXTREME calls that win when right and lose hard when wrong — same Brier, different Elo. The F99-extension probe found Gemini wins external Elo (#2) despite #5 Brier — direction-correct more often than its calibration confidence suggests. The conditional router (F107) routes by Elo signal where Brier doesn't differentiate.

## 6. Ensemble and routing methodology

Naive aggregation (mean-of-5, median-of-5) does NOT beat best-single on Brier at N=157 shared cohort (F99 extension, 2026-05-29). The deployable shape is **conditional routing** keyed on (panel disagreement σ, corpus_class, family Elo on similar contracts), codified in `org/calibration/per_agent_prompt_policy.yaml` under `meta_routing:` (F107). Pre-registered, requires N≥300 per quartile for confirmation.

## 7. Auxiliary code map (references, not duplicates)

- **Per-agent prompt policy**: `org/calibration/per_agent_prompt_policy.yaml` — deployable rules (confident_no_discount, channel_routing, meta_routing). Read by the forecast pool and the conditional router consumer.
- **Forecast pool**: `scripts/public/control/forecast/pool.py` — orchestrates a forecast pool run. Wired as `ztare forecast pool`.
- **Forecast resolution**: `scripts/public/control/forecast/resolve_from_json.py` — resolves contracts from JSON oracle. Wired as `ztare forecast resolve`.
- **Calibration stats**: `src/ztare/forecasting/calibration_stats.py` and `src/ztare/forecasting/calibration_db.py` — power calculator + DB query helpers. Wired as `ztare forecast calibration-stats` and `ztare forecast calibration-db`.
- **Prediction ledger**: `analytics/public/ledgers/prediction/prediction_ledger.jsonl` — long-form prediction log scored by `scripts/public/control/forecast/score_prediction_ledger_calibration.py` (wired as `ztare forecast score`).
- **DB tooling** (new 2026-05-29): `forecast_ingest_smoke_jsonl.py`, `forecast_compute_elo_by_corpus.py`, `forecast_brier_elo_report.py`. Wired as `ztare forecast ingest-smoke|elo-refresh|brier-elo`.
- **Working paper**: `workingpapers/llm-forecast-calibration-cross-corpus/main.tex` (22 pages, F1-F104).

## 8. Known methodology debts

- **Source-alias unification**: `manifold` vs `manifold_bulk` in contracts.source likely the same platform (task #69). Family-alias unification was done 2026-05-29 (`codex_mini` → `codex_54mini`, 3385 rows renamed). Re-check views afterwards.
- **Internal y_known parity**: only 45 internal contracts resolve; external has 142+. Re-fire to parity is task #70.
- **Terminology**: "pilot" vs "experiment" is inconsistent across the codebase (task #65). Pre-registered convention TBD.
- **Ingest watchdog**: the 5-file smoke ingest landed 2026-05-29 manually. A watchdog that auto-ingests new jsonls when fired would close the audit gap that today's DB-migration audit (task #63) surfaced.

## 9. What this methodology does NOT do

- Does NOT measure model intelligence in any general sense. The Brier/Elo numbers are calibration-on-this-slate, not capability.
- Does NOT establish independence of the five families. Codex_55 and codex_54mini share an underlying model lineage; correlated errors are expected and visible in the F99-extension Spearman ρ matrix (codex+claude cluster ρ≈0.77).
- Does NOT solve corpus contamination. The Halawi 2024 dataset has a documented post-cutoff filter requirement (F101); the program applies it but cannot retroactively unwind training-data overlap from pre-cutoff data already absorbed by the panel.
- Does NOT generalize beyond the five families and the two corpus classes. Public release of the internal corpus (sanitized) is task #61.

---

Cross-reference: `project_charter.md` (parent-level charter), `CLAIM_SUMMARY.md` (parent-level public claim), `forecaster_skill_calibration_v1/workspace/research_log.md` (all F-row findings).
