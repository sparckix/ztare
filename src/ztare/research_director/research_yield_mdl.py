"""MDL-style research-yield scoring for candidate avenues.

This is a ranking primitive, not a theorem gate.  It reuses the canonical
MDL accounting from :mod:`ztare.fit.mdl` and the loop-yield signal vocabulary
from :mod:`ztare.validator.core.information_yield`, then leaves the substrate
caller to provide domain-specific candidates and amnesia evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any

try:
    from ztare.fit.mdl import (
        DEFAULT_CITATION_COST,
        DEFAULT_MIN_EXPOSURE,
        ItemStat,
        KEEP,
        PROVISIONAL,
        RETIRE,
        score_item,
    )
    from ztare.research_director.source_currency_discriminator import (
        classify_source_currency,
    )
    from ztare.validator.core.information_yield import IterationSignal
except ModuleNotFoundError:
    from ztare.fit.mdl import (
        DEFAULT_CITATION_COST,
        DEFAULT_MIN_EXPOSURE,
        ItemStat,
        KEEP,
        PROVISIONAL,
        RETIRE,
        score_item,
    )
    from ztare.research_director.source_currency_discriminator import (
        classify_source_currency,
    )
    from ztare.validator.core.information_yield import IterationSignal


_WORD_RE = re.compile(r"[A-Za-z0-9_./:+-]+")
CANONICAL_MDL_ENGINE = "ztare.fit.mdl.score_item"


@dataclass(frozen=True)
class ResearchAvenue:
    """A candidate research route with inspectable scoring features."""

    avenue_id: str
    description: str
    receipts: tuple[str, ...] = field(default_factory=tuple)
    kill_conditions: tuple[str, ...] = field(default_factory=tuple)
    expected_reuse: int = 1
    exposure: int = 0
    estimated_complexity: int | None = None
    amnesia_hits: int = 0
    prior_negative_receipts: int = 0
    novelty_hints: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResearchAvenueScore:
    """Score for one candidate route."""

    avenue_id: str
    source_currency_class: str
    source_currency_confidence: str
    description_units: int
    mdl_verdict: str
    mdl_marginal: int
    information_units: float
    recurrence_penalty_units: float
    net_information_units: float
    yield_density: float
    recommendation: str
    required_receipts: tuple[str, ...]
    nearest_confusers: tuple[str, ...]
    rationale: str
    positive_projection_receipt: bool
    shell_transport_receipt: bool
    canonical_mdl_engine: str = CANONICAL_MDL_ENGINE
    mdl_citation_cost: int = DEFAULT_CITATION_COST
    mdl_min_exposure: int = DEFAULT_MIN_EXPOSURE

    def as_dict(self) -> dict[str, Any]:
        return {
            "avenue_id": self.avenue_id,
            "canonical_mdl_engine": self.canonical_mdl_engine,
            "source_currency_class": self.source_currency_class,
            "source_currency_confidence": self.source_currency_confidence,
            "description_units": self.description_units,
            "mdl_verdict": self.mdl_verdict,
            "mdl_marginal": self.mdl_marginal,
            "mdl_citation_cost": self.mdl_citation_cost,
            "mdl_min_exposure": self.mdl_min_exposure,
            "information_units": round(self.information_units, 4),
            "recurrence_penalty_units": round(self.recurrence_penalty_units, 4),
            "net_information_units": round(self.net_information_units, 4),
            "yield_density": round(self.yield_density, 6),
            "recommendation": self.recommendation,
            "required_receipts": list(self.required_receipts),
            "nearest_confusers": list(self.nearest_confusers),
            "positive_projection_receipt": self.positive_projection_receipt,
            "shell_transport_receipt": self.shell_transport_receipt,
            "rationale": self.rationale,
        }


def description_units(*parts: object) -> int:
    """Approximate description length in stable token-like units."""

    text = " ".join(str(part) for part in parts if part is not None)
    return max(1, len(_WORD_RE.findall(text)))


def _iteration_signal_for_avenue(
    avenue: ResearchAvenue,
    source_currency_class: str,
) -> IterationSignal:
    """Expose the avenue as the existing information-yield signal shape."""

    return IterationSignal(
        iteration_index=0,
        score=0,
        weakest_point=avenue.description[:120],
        novel_attack_ids=tuple(avenue.kill_conditions),
        novel_hinge_ids=(source_currency_class,)
        if source_currency_class != "unknown"
        else (),
        novel_primitive_ids=tuple(avenue.novelty_hints or avenue.receipts),
        weakest_class=source_currency_class,
    )


def _information_units(
    avenue: ResearchAvenue,
    source_currency_class: str,
    mdl_stat: ItemStat,
) -> float:
    """Deterministic utility proxy for new discriminators."""

    signal = _iteration_signal_for_avenue(avenue, source_currency_class)
    units = 0.0
    if signal.novel_hinge_ids:
        units += 4.0
    units += 2.5 * len(set(signal.novel_primitive_ids))
    units += 1.5 * len(set(signal.novel_attack_ids))
    if signal.has_novelty():
        units += 2.0
    if mdl_stat.verdict == KEEP:
        units += 2.0
    elif mdl_stat.verdict == PROVISIONAL:
        units += 0.75
    return units


def _recommendation(
    *,
    net_information_units: float,
    yield_density: float,
    mdl_verdict: str,
    amnesia_hits: int,
    prior_negative_receipts: int,
    source_currency_class: str,
    positive_projection_receipt: bool,
    shell_transport_receipt: bool,
) -> str:
    if (
        amnesia_hits >= 4
        and net_information_units <= 2.0
        and source_currency_class == "unknown"
    ):
        return "kill_or_alias_to_prior_negative"
    if source_currency_class == "unknown":
        if prior_negative_receipts or amnesia_hits:
            return "defer_until_new_receipt"
        return "repair_source_profile_first"
    if prior_negative_receipts >= 2 and yield_density <= 0.05:
        return "defer_until_new_receipt"
    if source_currency_class == "scalar_shell_price" and not shell_transport_receipt:
        return "defer_until_transport_receipt"
    if (
        source_currency_class == "coefficient_tensor_projection"
        and not positive_projection_receipt
    ):
        return "defer_until_new_receipt"
    if source_currency_class == "coefficient_tensor_projection" and net_information_units > 0:
        return "formalize_or_counterexample"
    if mdl_verdict == RETIRE and yield_density <= 0.0:
        return "defer_until_complexity_drops"
    if net_information_units > 0 and yield_density >= 0.05:
        return "pursue"
    return "watchlist"


def _has_positive_projection_receipt(avenue: ResearchAvenue) -> bool:
    """Check whether the route declares payment, not just tensor vocabulary."""

    text = " ".join([*avenue.receipts, *avenue.novelty_hints]).lower()
    has_projected_penalty = (
        ("projected" in text or "projection" in text)
        and ("penalty" in text or "payment" in text or "budget" in text)
    )
    has_owner_prefix = (
        ("owner-preimage" in text or "owner preimage" in text)
        and ("prefix" in text or "budget" in text or "no-rebilling" in text)
    )
    has_named_receipt = (
        "fouriertriadpositivepenaltyreceipt" in text
        or "liftedtriadtowerprojectionreceipt" in text
        or "selectedtreeownerpreimagecarleson" in text
    )
    return has_projected_penalty or has_owner_prefix or has_named_receipt


def _has_shell_transport_receipt(avenue: ResearchAvenue) -> bool:
    """Check whether shell prices are explicitly transported to selected events."""

    text = " ".join([*avenue.receipts, *avenue.novelty_hints]).lower()
    has_shell_transport = (
        "shell-to-selected-event" in text
        or "shell to selected event" in text
        or "shell-to-event" in text
        or "shell to event" in text
    )
    has_prefix_control = (
        "no-rebilling" in text
        or "prefix" in text
        or "owner-preimage" in text
        or "owner preimage" in text
    )
    return has_shell_transport and has_prefix_control


def score_research_avenue(avenue: ResearchAvenue) -> ResearchAvenueScore:
    """Score one avenue for expected information yield per description cost."""

    source = classify_source_currency(
        avenue.description,
        avenue.receipts,
        avenue.kill_conditions,
        avenue.novelty_hints,
    )
    size = avenue.estimated_complexity or description_units(
        avenue.description,
        avenue.receipts,
        avenue.kill_conditions,
        avenue.novelty_hints,
    )
    mdl_stat = score_item(
        avenue.avenue_id,
        size=size,
        reuse=max(0, int(avenue.expected_reuse)),
        exposure=max(0, int(avenue.exposure)),
    )
    source_class = str(source["source_currency_class"])
    info_units = _information_units(avenue, source_class, mdl_stat)
    recurrence_penalty = (
        2.0 * math.log1p(max(0, avenue.amnesia_hits))
        + 1.5 * max(0, avenue.prior_negative_receipts)
    )
    net_info = info_units - recurrence_penalty
    density = net_info / max(1, size)
    positive_projection_receipt = _has_positive_projection_receipt(avenue)
    shell_transport_receipt = _has_shell_transport_receipt(avenue)
    recommendation = _recommendation(
        net_information_units=net_info,
        yield_density=density,
        mdl_verdict=mdl_stat.verdict,
        amnesia_hits=avenue.amnesia_hits,
        prior_negative_receipts=avenue.prior_negative_receipts,
        source_currency_class=source_class,
        positive_projection_receipt=positive_projection_receipt,
        shell_transport_receipt=shell_transport_receipt,
    )
    rationale = (
        f"{source_class}; MDL={mdl_stat.verdict}; "
        f"net_info={net_info:.2f}; density={density:.4f}; "
        f"amnesia_hits={avenue.amnesia_hits}; "
        f"positive_projection_receipt={positive_projection_receipt}; "
        f"shell_transport_receipt={shell_transport_receipt}"
    )
    return ResearchAvenueScore(
        avenue_id=avenue.avenue_id,
        source_currency_class=source_class,
        source_currency_confidence=str(source["confidence"]),
        description_units=size,
        mdl_verdict=mdl_stat.verdict,
        mdl_marginal=mdl_stat.marginal,
        information_units=info_units,
        recurrence_penalty_units=recurrence_penalty,
        net_information_units=net_info,
        yield_density=density,
        recommendation=recommendation,
        required_receipts=tuple(source["required_receipts"]),
        nearest_confusers=tuple(source["nearest_confusers"]),
        rationale=rationale,
        positive_projection_receipt=positive_projection_receipt,
        shell_transport_receipt=shell_transport_receipt,
    )


def score_research_avenues(
    avenues: list[ResearchAvenue],
) -> list[ResearchAvenueScore]:
    """Rank avenues by recommendation class, density, then net information."""

    priority = {
        "formalize_or_counterexample": 0,
        "pursue": 1,
        "watchlist": 2,
        "defer_until_transport_receipt": 3,
        "defer_until_new_receipt": 4,
        "repair_source_profile_first": 5,
        "defer_until_complexity_drops": 6,
        "kill_or_alias_to_prior_negative": 7,
    }
    scores = [score_research_avenue(avenue) for avenue in avenues]
    scores.sort(
        key=lambda score: (
            priority.get(score.recommendation, 9),
            -score.yield_density,
            -score.net_information_units,
            score.avenue_id,
        )
    )
    return scores


__all__ = [
    "ResearchAvenue",
    "ResearchAvenueScore",
    "description_units",
    "score_research_avenue",
    "score_research_avenues",
]
