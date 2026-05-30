"""ztare.forecasting — general-purpose tools for binary-forecast calibration programs.

Hoisted 2026-05-27 from `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/`.
Used as a library by any GP-style calibration program; the workspace versions
are thin CLI wrappers that import from here. Companion to `ztare.experiment_stats`.

Modules:
  - calibration_db: SQLite schema (contracts / pilot_calls / pre_registrations),
                    ingest functions, pre-registration table.
  - calibration_stats: forecasting-specific stat wrappers (Brier ± CI,
                       paired Δ-Brier, Elo across families, Murphy decomposition).
"""
