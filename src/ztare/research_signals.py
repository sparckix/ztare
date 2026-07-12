"""Canonical interface for substrate-neutral research-economics signals.

The implementations predate this facade and retain their current ownership
modules.  This file gives new substrates one import surface and an inspectable
registry, avoiding parallel information-yield or MDL implementations.
"""
from __future__ import annotations

from dataclasses import dataclass

from ztare.common.information_yield_pricing import (
    ResidualYieldCoordinates,
    YieldComponents,
    price_experiment,
    residual_information_yield,
)
from ztare.fit.mdl import ItemStat, score_item
from ztare.validator.core.compression_progress import (
    CompressionObservation,
    CompressionProgressDecision,
    evaluate_compression_progress,
)
from ztare.validator.core.information_yield import (
    InformationYieldDecision,
    IterationSignal,
    LoopControlAction,
    ThesisControlMode,
    apply_latent_motion_veto,
    evaluate_information_yield,
    render_loop_control_prompt_context,
    select_thesis_control_mode,
)


@dataclass(frozen=True)
class ResearchSignalEngine:
    engine_id: str
    callable_ref: str
    role: str


ENGINE_REGISTRY: dict[str, ResearchSignalEngine] = {
    "loop_control": ResearchSignalEngine(
        engine_id="loop_control",
        callable_ref="ztare.validator.core.information_yield.evaluate_information_yield",
        role="decide whether another candidate iteration is informative",
    ),
    "experiment_pricing": ResearchSignalEngine(
        engine_id="experiment_pricing",
        callable_ref="ztare.common.information_yield_pricing.price_experiment",
        role="rank observations by committee separation, compression, and novelty",
    ),
    "residual_information_yield": ResearchSignalEngine(
        engine_id="residual_information_yield",
        callable_ref="ztare.common.information_yield_pricing.residual_information_yield",
        role="subtract a declared cheap baseline before pricing discriminative information",
    ),
    "compression_progress": ResearchSignalEngine(
        engine_id="compression_progress",
        callable_ref="ztare.validator.core.compression_progress.evaluate_compression_progress",
        role="track lower-is-better description-length progress",
    ),
    "mdl_library": ResearchSignalEngine(
        engine_id="mdl_library",
        callable_ref="ztare.fit.mdl.score_item",
        role="price reusable library items by description cost and reuse",
    ),
}


def engine_registry() -> dict[str, dict[str, str]]:
    """Return a JSON-compatible, immutable-by-copy view of the registry."""

    return {
        key: {
            "engine_id": value.engine_id,
            "callable_ref": value.callable_ref,
            "role": value.role,
        }
        for key, value in ENGINE_REGISTRY.items()
    }


__all__ = [
    "ENGINE_REGISTRY",
    "CompressionObservation",
    "CompressionProgressDecision",
    "InformationYieldDecision",
    "ItemStat",
    "IterationSignal",
    "LoopControlAction",
    "ResearchSignalEngine",
    "ResidualYieldCoordinates",
    "ThesisControlMode",
    "YieldComponents",
    "apply_latent_motion_veto",
    "engine_registry",
    "evaluate_compression_progress",
    "evaluate_information_yield",
    "price_experiment",
    "residual_information_yield",
    "render_loop_control_prompt_context",
    "score_item",
    "select_thesis_control_mode",
]
