"""World-model synthesis, evaluation, and control.

The package-level category is substrate-general: a world model has immutable
identity, issues forecasts before externally settled episodes, and remains one
member of a comparison committee. ``evaluation`` owns that shared membrane.

The original reference subsystem treats an interactive grid environment as an
open conjecture about a transition law: episodes are the search, and a
ratified transition program is the closure. Layout:

- `grid_dsl`: the typed seed grammar and evaluator for transition programs.
- `episode_log`: the canonical append-only `(s, a, s')` record; every other
  module reads the log, never a live environment.
- `synthesis`: enumeration + MDL ranking + behavioral dedup over the log.
- `gates`: replay-consistency and rollout-depth gates (fail-closed).
- `policy`: expected-information-gain action selection with typed fallbacks.
- `harness`: the pre-registered BC-0/1' runner for the sealed synthetic suite.
- `evaluation`: substrate-general candidate, forecast, episode, closed-matrix,
  and paired-survivor contracts used by domain adapters.

Seam of record: research_areas/seams/substrates/arc/GP-250_*.md.
"""

from .evaluation import (
    EvaluationMatrixReceipt,
    EvaluationScore,
    WorldModelCandidateView,
    WorldModelEpisodeView,
    WorldModelForecastView,
    compile_evaluation_integrity_receipt,
    conservative_paired_survivor_set,
    validate_evaluation_matrix,
)

__all__ = [
    "EvaluationMatrixReceipt",
    "EvaluationScore",
    "WorldModelCandidateView",
    "WorldModelEpisodeView",
    "WorldModelForecastView",
    "compile_evaluation_integrity_receipt",
    "conservative_paired_survivor_set",
    "validate_evaluation_matrix",
]
