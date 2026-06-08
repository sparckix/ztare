"""Source-currency discriminators for residual and forecast-validity checks.

The formal-residual classifier is advisory: it does not prove the missing fact
and it does not override domain-specific gap typing. The forecasting classifier
is a narrow metadata primitive: it separates stored cutoff flags from computed
resolution-date-vs-model-cutoff relation so source-validity reports can detect
stale flags explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class SourceCurrencyClass:
    source_currency_class: str
    confidence: str
    matched_terms: tuple[str, ...]
    required_receipts: tuple[str, ...]
    nearest_confusers: tuple[str, ...]
    downstream_consumer_check: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_currency_class": self.source_currency_class,
            "confidence": self.confidence,
            "matched_terms": list(self.matched_terms),
            "required_receipts": list(self.required_receipts),
            "nearest_confusers": list(self.nearest_confusers),
            "downstream_consumer_check": self.downstream_consumer_check,
        }


@dataclass(frozen=True)
class ForecastSourceCurrency:
    cutoff_relation: str
    provenance: str
    stored_cutoff_relation: str | None
    computed_cutoff_relation: str | None
    cutoff_relation_conflict: bool
    required_receipts: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "cutoff_relation": self.cutoff_relation,
            "provenance": self.provenance,
            "stored_cutoff_relation": self.stored_cutoff_relation,
            "computed_cutoff_relation": self.computed_cutoff_relation,
            "cutoff_relation_conflict": self.cutoff_relation_conflict,
            "required_receipts": list(self.required_receipts),
        }


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def classify_forecast_source_currency(
    *,
    resolve_date: str | None,
    model_cutoff_date: str | None,
    stored_post_training_cutoff: int | bool | None = None,
    prefer_computed_cutoff: bool = False,
) -> dict[str, Any]:
    """Classify whether a forecast row is pre/post cutoff for a model panel.

    This is the forecasting-specific source-currency primitive. It keeps the
    stored DB flag separate from the relation computed from resolution date and
    model cutoff date, because stale stored flags are exactly the metadata
    failure mode the cutoff-validity law must detect.
    """
    stored_relation: str | None = None
    if stored_post_training_cutoff is not None:
        stored_relation = "post_cutoff" if int(stored_post_training_cutoff) else "pre_cutoff"

    computed_relation: str | None = None
    resolved = _parse_iso_date(resolve_date)
    cutoff = _parse_iso_date(model_cutoff_date)
    if resolved and cutoff:
        computed_relation = "post_cutoff" if resolved > cutoff else "pre_cutoff"

    conflict = bool(stored_relation and computed_relation and stored_relation != computed_relation)
    receipts = (
        "strict resolution date, not latest observed data",
        "model or panel cutoff date",
        "stored relation provenance when using a DB flag",
        "computed relation provenance when overriding stale stored flags",
    )
    if prefer_computed_cutoff and computed_relation:
        provenance = "computed_from_panel_cutoff_date"
        if conflict:
            provenance += "_over_stored_flag"
        return ForecastSourceCurrency(
            cutoff_relation=computed_relation,
            provenance=provenance,
            stored_cutoff_relation=stored_relation,
            computed_cutoff_relation=computed_relation,
            cutoff_relation_conflict=conflict,
            required_receipts=receipts,
        ).as_dict()
    if stored_relation:
        return ForecastSourceCurrency(
            cutoff_relation=stored_relation,
            provenance="contracts.post_training_cutoff",
            stored_cutoff_relation=stored_relation,
            computed_cutoff_relation=computed_relation,
            cutoff_relation_conflict=conflict,
            required_receipts=receipts,
        ).as_dict()
    if computed_relation:
        return ForecastSourceCurrency(
            cutoff_relation=computed_relation,
            provenance="computed_from_panel_cutoff_date",
            stored_cutoff_relation=stored_relation,
            computed_cutoff_relation=computed_relation,
            cutoff_relation_conflict=conflict,
            required_receipts=receipts,
        ).as_dict()
    return ForecastSourceCurrency(
        cutoff_relation="unknown",
        provenance="missing_cutoff_relation",
        stored_cutoff_relation=stored_relation,
        computed_cutoff_relation=computed_relation,
        cutoff_relation_conflict=conflict,
        required_receipts=receipts,
    ).as_dict()


_PROFILES: tuple[tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...], str], ...] = (
    (
        "coefficient_tensor_projection",
        (
            "coefficient tensor",
            "coefficient-level",
            "raw lamb throughput",
            "rawlambtriadthroughput",
            "fouriertriadpositivepenaltyreceipt",
            "fourier triad",
            "resonant triad",
            "triad",
            "lamb vector",
            "lamb",
            "leray",
            "biot-savart",
            "helicity",
            "phase coherence",
            "phase",
            "tensor",
            "projection",
            "no-rebilling",
            "owner-preimage",
            "same-carrier",
        ),
        (
            "resonant coefficient relation fixed before shell aggregation",
            "divergence-free or projected tensor frame on the same carrier",
            "numerical event-payment-to-projected-penalty inequality",
            "prefix-bounded projected penalty with no rebilling under projection",
        ),
        (
            "scalar shell coherence price in place of coefficient tensor payment",
            "helicity or phase labels without a numerical projected penalty",
            "local frame split that ignores the Biot-Savart projection tail",
            "lifted tower or congruence surplus without projection injectivity and no-rebilling",
        ),
        "consumer is bounded by the projected coefficient-level penalty, not by a shell-level label",
    ),
    (
        "owner_preimage_budget",
        (
            "owner-preimage",
            "owner preimage",
            "selected-prefix",
            "selected prefix",
            "carleson",
            "wavepacket",
            "same-carrier",
            "no-rebilling",
            "prefix budget",
            "packet owner",
        ),
        (
            "owner map fixed before payoff",
            "selected-prefix owner-preimage inequality",
            "same-carrier source/output binding",
            "finite owner multiplicity or no-rebilling receipt",
        ),
        (
            "phase-space or wavepacket labels without owner multiplicity",
            "same-carrier vocabulary without a selected-prefix inequality",
            "projection labels that move payment to descendants",
        ),
        "consumer is bounded by selected-prefix owner accounting, not by labels on packets",
    ),
    (
        "scalar_shell_price",
        (
            "scalar shell",
            "shell coherence",
            "shell price",
            "littlewood-paley shell",
            "frequency shell",
            "coherenceprice",
            "crossprice",
            "shell-indexed",
        ),
        (
            "shell-to-selected-event transport receipt",
            "coefficient-level uplift receipt when the consumer is triad-local",
            "prefix no-rebilling receipt for shell aggregation",
            "explicit statement of what shell averaging forgets",
        ),
        (
            "shell aggregate treated as coefficient tensor payment",
            "phase or helicity decorrelation hidden by spherical averaging",
            "selected-tree rebilling inside one shell",
        ),
        "consumer is bounded by shell-indexed prices only after a shell-to-event transport receipt",
    ),
    (
        "source_contract_repair",
        (
            "source contract",
            "source field",
            "contract",
            "data contract",
            "source shape",
            "consumer",
        ),
        (
            "name the consumer theorem or gate",
            "name the missing source fact in the upstream data object",
            "show the source fact is not derived from the downstream conclusion",
            "add the narrowest reusable upstream field or bridge",
        ),
        (
            "repairing the consumer by weakening the conclusion",
            "using a bounded integral inequality as an unstated integrability source",
            "treating a label match as a source receipt",
        ),
        "consumer theorem consumes the repaired upstream field without adding a new logical cycle",
    ),
    (
        "integrability_membership",
        (
            "integrableon",
            "integrable on",
            "integrability",
            "memlp",
            "membership",
            "indicator",
            "restrict",
            "restriction",
        ),
        (
            "measurability or ae-strong-measurability receipt",
            "finite integral, lintegral, or IntegrableOn receipt on the stated set",
            "indicator/restriction transport receipt",
            "target MemLp or membership statement with measure and exponent fixed",
        ),
        (
            "bounded Bochner integral inequality implies IntegrableOn",
            "UnifIntegrable alone implies MemLp for every sequence member",
            "indicator transport without proving the restricted integral is finite",
        ),
        "downstream theorem unfolds the same measure/exponent/set as the membership receipt",
    ),
    (
        "norm_currency_bridge",
        (
            "elpnorm",
            "pairwise elpnorm",
            "cauchy",
            "lp norm",
            "l2 bound",
            "norm squared",
            "norm sq",
            "bochner",
            "setintegral",
            "integral convergence",
        ),
        (
            "membership receipt needed before eLpNorm is finite",
            "real-integral-to-eLpNorm equality or inequality receipt",
            "exponent and measure alignment receipt",
            "eventual or uniform finite-bound receipt for the consumed sequence",
        ),
        (
            "finite real integral controls eLpNorm without membership",
            "pointwise norm-squared bound is the same currency as Lp membership",
            "real integral convergence is convergence in measure without a metric bound",
        ),
        "consumer uses finite eLpNorm or Lp metric in the exact exponent requested",
    ),
    (
        "convergence_currency_bridge",
        (
            "tendstoinmeasure",
            "in measure",
            "ae convergence",
            "a.e. convergence",
            "almost everywhere",
            "diagonal convergence",
            "limit passage",
            "diagonal limit",
        ),
        (
            "selected subsequence or diagonal extraction receipt",
            "target convergence mode receipt, stated independently of the conclusion",
            "membership/tail-finite receipt when upgrading real-integral convergence",
            "limit measurability or MemLp receipt when the consumer needs a limit object",
        ),
        (
            "real integral convergence implies convergence in measure without MemLp or tail control",
            "a.e. convergence gives Lp convergence without uniform integrability",
            "diagonal extraction provides the wrong convergence mode for the consumer",
        ),
        "consumer theorem sees the same diagonal family and convergence mode as the source receipt",
    ),
    (
        "uniform_integrability_upgrade",
        (
            "uniformintegrable",
            "uniform integrable",
            "unifintegrable",
            "uniformly integrable",
            "vitali",
        ),
        (
            "ae-strong-measurability receipt for the family",
            "small-set or UnifIntegrable source receipt",
            "finite eLpNorm or integrability source for each family member",
            "Vitali upgrade receipt if convergence is strengthened",
        ),
        (
            "small-set control alone implies global finite norm",
            "UniformIntegrable is a substitute for the convergence source",
            "Vitali used without the convergence hypothesis it upgrades",
        ),
        "consumer separates the UI source from the convergence source and the finite-norm source",
    ),
    (
        "limit_membership",
        (
            "limit memlp",
            "limit membership",
            "limit finite",
            "fatou",
            "diagonal limit memlp",
            "limit object",
        ),
        (
            "a.e. or in-measure convergence receipt to the named limit",
            "eventual finite-bound receipt for the approximating sequence",
            "Fatou or lower-semicontinuity bridge receipt",
            "limit measurability receipt",
        ),
        (
            "finite sequence-side norm bound proves limit membership without convergence",
            "Fatou applies without an a.e. or in-measure limit identification",
            "limit object is renamed without binding to the diagonal extraction",
        ),
        "consumer's limit object is definitionally the same object proved finite",
    ),
)


def _matches(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(term for term in terms if term in text)


def _has_coefficient_tensor_core(hits: tuple[str, ...]) -> bool:
    core = {
        "coefficient tensor",
        "coefficient-level",
        "raw lamb throughput",
        "rawlambtriadthroughput",
        "fouriertriadpositivepenaltyreceipt",
        "fourier triad",
        "resonant triad",
        "triad",
        "tensor",
    }
    return bool(core.intersection(hits))


def classify_source_currency(*parts: object) -> dict[str, Any]:
    """Classify the source-currency shape of a residual.

    The first matching high-signal profile wins, with a small bias toward
    convergence/membership classes when multiple profiles fire. Inputs are
    free-form strings or structured objects already available to callers.
    """
    text = " ".join(str(p) for p in parts if p is not None).lower()
    scored: list[SourceCurrencyClass] = []
    for name, terms, receipts, confusers, consumer_check in _PROFILES:
        hits = _matches(text, terms)
        if not hits:
            continue
        if name == "coefficient_tensor_projection" and not _has_coefficient_tensor_core(hits):
            continue
        confidence = "medium" if len(hits) >= 2 else "low"
        scored.append(SourceCurrencyClass(
            source_currency_class=name,
            confidence=confidence,
            matched_terms=hits,
            required_receipts=receipts,
            nearest_confusers=confusers,
            downstream_consumer_check=consumer_check,
        ))
    if not scored:
        return SourceCurrencyClass(
            source_currency_class="unknown",
            confidence="low",
            matched_terms=(),
            required_receipts=(
                "state the claimed source fact",
                "state the downstream consumer",
                "state the missing conversion or transport receipt",
            ),
            nearest_confusers=("label-level analogy without an executable receipt",),
            downstream_consumer_check=(
                "no source-currency profile fired; use the domain gap classifier"
            ),
        ).as_dict()

    priority = {
        "coefficient_tensor_projection": 0,
        "owner_preimage_budget": 1,
        "scalar_shell_price": 2,
        "convergence_currency_bridge": 3,
        "limit_membership": 4,
        "integrability_membership": 5,
        "uniform_integrability_upgrade": 6,
        "norm_currency_bridge": 7,
        "source_contract_repair": 8,
    }

    def _rank(item: SourceCurrencyClass) -> tuple[int, int]:
        class_priority = priority.get(item.source_currency_class, 99)
        if item.source_currency_class == "coefficient_tensor_projection":
            if not _has_coefficient_tensor_core(item.matched_terms):
                class_priority = 8
        if (
            item.source_currency_class == "norm_currency_bridge"
            and "elpnorm" in item.matched_terms
            and "cauchy" in item.matched_terms
        ):
            class_priority = 0
        elif (
            item.source_currency_class == "norm_currency_bridge"
            and "elpnorm" in item.matched_terms
            and (
                "restrict" in text
                or "restricted" in text
                or "target_currency" in text
            )
        ):
            class_priority = 1
        return (class_priority, -len(item.matched_terms))

    scored.sort(
        key=_rank
    )
    result = scored[0].as_dict()
    result["also_matched"] = [
        item.as_dict()
        for item in scored[1:]
    ]
    return result


__all__ = ["classify_source_currency", "classify_forecast_source_currency"]
