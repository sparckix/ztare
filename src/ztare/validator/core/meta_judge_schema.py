RAW_META_JUDGE_REQUIRED_FIELDS = (
    "score",
    "weakest_point",
    "verified_axioms",
    "retired_axioms_approved",
    "evidence_gaps",
    "derived_constraints",
    "logic_gaps",
    "debate_summary",
    "adversarial_alignment",
    "friction_points",
    "probability_dag",
)


def raw_meta_judge_shape_errors(evaluation: object) -> list[str]:
    """Return verdict-schema defects for raw non-Gemini judge responses."""
    if not isinstance(evaluation, dict):
        return ["top_level_not_object"]

    errors: list[str] = []
    for field in RAW_META_JUDGE_REQUIRED_FIELDS:
        if field not in evaluation:
            errors.append(f"missing:{field}")

    if "score" in evaluation:
        try:
            score = int(evaluation.get("score"))
            if score < 0 or score > 100:
                errors.append("invalid:score_out_of_range")
        except (TypeError, ValueError):
            errors.append("invalid:score_not_integer")

    for field in (
        "verified_axioms",
        "retired_axioms_approved",
        "evidence_gaps",
        "derived_constraints",
        "logic_gaps",
        "friction_points",
    ):
        if field in evaluation and not isinstance(evaluation.get(field), list):
            errors.append(f"invalid:{field}_not_array")

    for field in ("weakest_point", "debate_summary", "adversarial_alignment"):
        if field in evaluation and not isinstance(evaluation.get(field), str):
            errors.append(f"invalid:{field}_not_string")

    if "probability_dag" in evaluation:
        probability_dag = evaluation.get("probability_dag")
        if not isinstance(probability_dag, dict):
            errors.append("invalid:probability_dag_not_object")
        else:
            if not isinstance(probability_dag.get("outcome"), dict):
                errors.append("invalid:probability_dag.outcome_not_object")
            if "nodes" in probability_dag and not isinstance(probability_dag.get("nodes"), list):
                errors.append("invalid:probability_dag.nodes_not_array")
            if "edges" in probability_dag and not isinstance(probability_dag.get("edges"), list):
                errors.append("invalid:probability_dag.edges_not_array")

    if (
        "score" not in evaluation
        and isinstance(evaluation, dict)
        and any(field in evaluation for field in ("gap_type", "target", "description"))
    ):
        errors.append("wrong_top_level:evidence_gap_payload")

    return errors


def coerce_raw_meta_judge_score(evaluation: dict) -> dict:
    coerced = dict(evaluation)
    score = int(coerced.get("score", 0))
    coerced["score"] = max(0, min(100, score))
    return coerced
