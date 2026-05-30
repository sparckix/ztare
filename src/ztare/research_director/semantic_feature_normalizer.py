"""Optional LLM semantic front-end for residual normal-form preflight.

The LLM is a recall aid, not the authority.  It may propose catalog feature ids
and normal-form ids with evidence spans; the deterministic packet/currency
checks still produce the operational verdict.
"""
from __future__ import annotations

import json
import os
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.ztare.research_director.residual_normal_form import evidence_negates_feature


DEFAULT_MODEL_CANDIDATES = ("gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini")


class SemanticFeatureAlias(BaseModel):
    feature_id: str = Field(description="Exact feature id from the provided catalog.")
    evidence_span: str = Field(description="Short quote or phrase from the proposal.")
    confidence: Literal["high", "medium", "low"]
    polarity: Literal[
        "proposal_claim",
        "missing_requirement",
        "negated_shortcut",
        "falsifier_condition",
    ] = Field(
        default="proposal_claim",
        description=(
            "How the evidence is used: actual proposal mechanism, named missing "
            "requirement, rejected/negated shortcut, or an explicitly stated "
            "kill/falsifier condition."
        ),
    )
    rationale: str = Field(description="One short sentence.")


class SemanticNormalFormCandidate(BaseModel):
    normal_form_id: str = Field(description="Exact canonical normal form id.")
    evidence_span: str = Field(description="Short quote or phrase from the proposal.")
    confidence: Literal["high", "medium", "low"]
    rationale: str = Field(description="One short sentence.")


class SemanticNormalizationPayload(BaseModel):
    feature_aliases: list[SemanticFeatureAlias] = Field(default_factory=list)
    candidate_normal_forms: list[SemanticNormalFormCandidate] = Field(default_factory=list)
    uncertainty: str = ""


def _catalog_for_prompt(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "features": profile.get("feature_vocab", {}),
        "normal_forms": [
            {
                "normal_form_id": row.get("canonical_name"),
                "aliases": row.get("aliases", []),
                "feature_signature": row.get("feature_signature", []),
                "required_new_signal": row.get("required_new_signal"),
            }
            for row in profile.get("normal_forms", [])
        ],
    }


def _model_candidates(model: str | None) -> list[str]:
    if model:
        return [model]
    env_model = os.environ.get("ZTARE_SEMANTIC_NORMALIZER_MODEL")
    if env_model:
        return [env_model]
    return list(DEFAULT_MODEL_CANDIDATES)


def _usage_dict(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def _validated_result(
    payload: SemanticNormalizationPayload,
    profile: dict[str, Any],
    *,
    requested_model: str,
    resolved_model: str | None,
    usage: dict[str, int],
) -> dict[str, Any]:
    valid_features = set(profile.get("feature_vocab", {}).keys())
    valid_normal_forms = {
        str(row.get("canonical_name"))
        for row in profile.get("normal_forms", [])
        if row.get("canonical_name")
    }

    feature_hits: list[dict[str, Any]] = []
    falsifier_feature_hits: list[dict[str, Any]] = []
    negated_feature_hits: list[dict[str, Any]] = []
    rejected_features: list[dict[str, Any]] = []
    for row in payload.feature_aliases:
        item = row.model_dump(mode="json")
        if row.feature_id in valid_features:
            polarity = row.polarity
            if (
                polarity in {"proposal_claim", "missing_requirement"}
                and evidence_negates_feature(
                    row.evidence_span,
                    row.feature_id,
                    profile.get("feature_vocab", {}),
                )
            ):
                polarity = "negated_shortcut"
            rendered = {
                "feature": row.feature_id,
                "hits": [row.evidence_span[:240]],
                "source": "llm_semantic_normalizer",
                "confidence": row.confidence,
                "polarity": polarity,
                "rationale": row.rationale[:240],
            }
            if polarity != row.polarity:
                rendered["polarity_override"] = "deterministic_negation_window"
            if polarity in {"proposal_claim", "missing_requirement"}:
                feature_hits.append(rendered)
            elif polarity == "falsifier_condition":
                falsifier_feature_hits.append(rendered)
            else:
                negated_feature_hits.append(rendered)
        else:
            rejected_features.append(item)

    candidates: list[dict[str, Any]] = []
    rejected_candidates: list[dict[str, Any]] = []
    for row in payload.candidate_normal_forms:
        item = row.model_dump(mode="json")
        if row.normal_form_id in valid_normal_forms:
            candidates.append(item)
        else:
            rejected_candidates.append(item)

    return {
        "enabled": True,
        "status": "ok",
        "provider": "openai",
        "transport": "responses.parse",
        "requested_model": requested_model,
        "resolved_model": resolved_model or requested_model,
        "feature_hits": feature_hits,
        "falsifier_feature_hits": falsifier_feature_hits,
        "negated_feature_hits": negated_feature_hits,
        "candidate_normal_forms": candidates,
        "rejected_feature_aliases": rejected_features,
        "rejected_candidate_normal_forms": rejected_candidates,
        "uncertainty": payload.uncertainty,
        "usage": usage,
        "authority": (
            "semantic hints only; deterministic normal-form, packet, currency, "
            "and theorem gates consume/validate the hints"
        ),
    }


def semantic_normalize_with_openai(
    text: str,
    profile: dict[str, Any],
    *,
    model: str | None = None,
    timeout: float = 20.0,
    max_output_tokens: int = 1200,
) -> dict[str, Any]:
    """Call the OpenAI API and return validated semantic feature hints.

    The call is synchronous by design: RD preflight should either wait for this
    receipt or run with semantic normalization disabled.
    """
    from openai import OpenAI

    catalog = _catalog_for_prompt(profile)
    instructions = (
        "You are a semantic alias classifier for a research-director preflight. "
        "Map proposal wording to the provided catalog ids. Do not invent ids. "
        "Do not decide novelty, proof validity, or closure. Use ids only when "
        "the proposal text contains evidence for that mathematical currency, "
        "carrier, packet, or hypothesis shape. Label polarity carefully: "
        "proposal_claim means the route actually uses the feature; "
        "missing_requirement means the route says that feature must be supplied; "
        "negated_shortcut means the route explicitly excludes it; "
        "falsifier_condition means the text says this would kill the route. "
        "Only proposal_claim and missing_requirement are consumed as semantic "
        "feature hints. For example, 'no new reserve' can be a missing "
        "freshness requirement; 'billed over and over' can be a proposal_claim "
        "nested_reuse hit only if the route relies on rebilling, but 'killed if "
        "nested reuse occurs' is a falsifier_condition. Return short evidence "
        "spans. Do not map generic active-tail/accounting language to "
        "local_tail_upgrade unless the text specifically claims a distribution, "
        "level-set, weak-Lq, reverse-Holder, or super-endpoint tail estimate."
    )
    prompt = (
        "Catalog JSON:\n"
        f"{json.dumps(catalog, ensure_ascii=False)}\n\n"
        "Proposal text:\n"
        f"{text[:8000]}\n\n"
        "Return the structured payload now."
    )
    last_error: str | None = None
    for candidate in _model_candidates(model):
        try:
            client = OpenAI(timeout=timeout)
            response = client.responses.parse(
                model=candidate,
                instructions=instructions,
                input=prompt,
                text_format=SemanticNormalizationPayload,
                max_output_tokens=max_output_tokens,
                temperature=0,
                store=False,
                truncation="disabled",
                timeout=timeout,
            )
            parsed = response.output_parsed
            if parsed is None:
                raise RuntimeError("OpenAI semantic normalizer returned no parsed payload")
            return _validated_result(
                parsed,
                profile,
                requested_model=candidate,
                resolved_model=getattr(response, "model", None),
                usage=_usage_dict(response),
            )
        except Exception as exc:  # pragma: no cover - exercised in live smoke.
            last_error = f"{type(exc).__name__}: {exc}"
            if model:
                break
            continue
    return {
        "enabled": True,
        "status": "error",
        "provider": "openai",
        "requested_model": model or ",".join(_model_candidates(None)),
        "error": last_error or "unknown error",
        "feature_hits": [],
        "falsifier_feature_hits": [],
        "negated_feature_hits": [],
        "candidate_normal_forms": [],
        "authority": "semantic normalization failed closed; no LLM hints consumed",
    }


def semantic_normalization_disabled() -> dict[str, Any]:
    return {
        "enabled": False,
        "status": "disabled",
        "feature_hits": [],
        "falsifier_feature_hits": [],
        "negated_feature_hits": [],
        "candidate_normal_forms": [],
    }
