"""Advisory cross-model review of candidate LeanMill eigenquestions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ztare.common.llm_runtime import subscription_model_route
from ztare.leanmill import prompts
from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.frontier_agent_runtime import (
    FrontierAgentConfig,
    SubscriptionJSONRole,
)
from ztare.leanmill.theory_ir import content_hash


def eigenquestion_review_output_schema(question_ids: Sequence[str]) -> dict[str, Any]:
    ids = tuple(dict.fromkeys(str(row) for row in question_ids if str(row)))
    if not ids:
        raise ValueError("eigenquestion review requires candidate IDs")
    ranking = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "question_id", "rank", "information_yield", "novelty_headroom",
            "harness_readiness", "fatal_confounder", "discriminating_test",
            "kill_condition", "minimum_artifact", "apparatus_vs_scarcity",
        ],
        "properties": {
            "question_id": {"enum": list(ids)},
            "rank": {"type": "integer", "minimum": 1, "maximum": len(ids)},
            "information_yield": {"type": "string", "minLength": 1},
            "novelty_headroom": {"type": "string", "minLength": 1},
            "harness_readiness": {"type": "string", "minLength": 1},
            "fatal_confounder": {"type": "string", "minLength": 1},
            "discriminating_test": {"type": "string", "minLength": 1},
            "kill_condition": {"type": "string", "minLength": 1},
            "minimum_artifact": {"type": "string", "minLength": 1},
            "apparatus_vs_scarcity": {"type": "string", "minLength": 1},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "ranked_questions", "portfolio_sequence", "portfolio_rationale",
            "scope_notes",
        ],
        "properties": {
            "ranked_questions": {
                "type": "array", "minItems": len(ids), "maxItems": len(ids),
                "items": ranking,
            },
            "portfolio_sequence": {
                "type": "array", "minItems": len(ids), "maxItems": len(ids),
                "items": {"enum": list(ids)},
            },
            "portfolio_rationale": {"type": "string", "minLength": 1},
            "scope_notes": {"type": "string", "minLength": 1},
        },
    }


def run_eigenquestion_review(
    questions: Sequence[Mapping[str, Any]],
    *,
    context: Mapping[str, Any],
    artifact_dir: str | Path,
    repo: str | Path,
    model: str = "fable",
    reasoning_effort: str = "low",
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Run one source-free advisory review through the shared subscription runtime."""

    rows = [dict(row) for row in questions]
    ids = tuple(str(row.get("question_id") or "") for row in rows)
    if any(not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("eigenquestion IDs must be non-empty and unique")
    runtime, resolved_model = subscription_model_route(model)
    role = SubscriptionJSONRole(
        role="eigenquestion_reviewer",
        agent_id=f"leanmill-eigenreview-{resolved_model}",
        repo=Path(repo),
        artifact_dir=Path(artifact_dir),
        config=FrontierAgentConfig(
            runtime=runtime,
            model=resolved_model,
            reasoning_effort=reasoning_effort,
            timeout_seconds=timeout_seconds,
            visible_workbench=False,
            web_research=False,
        ),
        output_schema=eigenquestion_review_output_schema(ids),
    )
    payload = {"context": dict(context), "questions": rows}
    prompt = prompts.LEANMILL_EIGENQUESTION_REVIEW_PROMPT.format(
        payload_json=json.dumps(payload, sort_keys=True, separators=(",", ":"))
    )
    raw_review = role(prompt)
    review = dict(raw_review)
    if "ranked_questions" not in review and isinstance(review.get("rankings"), list):
        review["ranked_questions"] = [
            {
                **dict(row),
                "fatal_confounder": str(
                    row.get("fatal_confounder")
                    or row.get("strongest_fatal_confounder")
                    or ""
                ),
            }
            for row in review.pop("rankings")
            if isinstance(row, Mapping)
        ]
        for row in review["ranked_questions"]:
            row.pop("strongest_fatal_confounder", None)
    from jsonschema import Draft202012Validator

    Draft202012Validator(eigenquestion_review_output_schema(ids)).validate(review)
    ranked_ids = [str(row.get("question_id") or "") for row in review["ranked_questions"]]
    sequence = [str(row) for row in review["portfolio_sequence"]]
    if set(ranked_ids) != set(ids) or len(set(ranked_ids)) != len(ids):
        raise ValueError("eigenquestion review did not rank each candidate exactly once")
    if set(sequence) != set(ids) or len(set(sequence)) != len(ids):
        raise ValueError("eigenquestion portfolio is not a permutation of candidates")
    core = {
        "schema": "leanmill.eigenquestion_review.v1",
        "authority": "advisory_only",
        "runtime": runtime,
        "model": resolved_model,
        "prompt_sha256": content_hash({"prompt": prompt}),
        "recommended_question_id": sequence[0],
        "review": review,
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(Path(artifact_dir) / "review.json", receipt)
    return receipt


__all__ = ["eigenquestion_review_output_schema", "run_eigenquestion_review"]
