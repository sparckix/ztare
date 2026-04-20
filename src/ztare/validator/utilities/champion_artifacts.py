from __future__ import annotations

from typing import Callable


FingerprintFromScoreContract = Callable[[dict | None], str | None]
FingerprintFromMeta = Callable[[dict | None], str | None]


def artifact_regime_fingerprint(
    payload: dict | None,
    *,
    score_regime_fingerprint_from_score_contract: FingerprintFromScoreContract,
) -> str | None:
    if not isinstance(payload, dict):
        return None
    fingerprint = payload.get("score_regime_fingerprint")
    if isinstance(fingerprint, str) and fingerprint.strip():
        return fingerprint.strip()
    score_contract = payload.get("score_contract")
    return score_regime_fingerprint_from_score_contract(score_contract)


def set_artifact_role(
    payload: dict,
    artifact_role: str,
    *,
    score_regime_fingerprint_from_score_contract: FingerprintFromScoreContract,
) -> dict:
    updated = dict(payload)
    updated["artifact_role"] = artifact_role
    updated["describes_baseline"] = artifact_role
    fingerprint = artifact_regime_fingerprint(
        updated,
        score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
    )
    if fingerprint:
        updated["score_regime_fingerprint"] = fingerprint
    return updated


def default_gap_severity_from_score_contract(score_contract: dict) -> str:
    if not isinstance(score_contract, dict):
        return "degrading"
    if score_contract.get("blocking_evidence_gap_count", 0):
        return "blocking"
    if score_contract.get("degrading_evidence_gap_count", 0):
        return "degrading"
    if score_contract.get("enriching_evidence_gap_count", 0):
        return "enriching"
    return "degrading"


def reconstruct_evidence_gaps_from_saved_meta(meta: dict) -> list[dict]:
    if not isinstance(meta, dict):
        return []
    score_contract = meta.get("score_contract", {})
    if not isinstance(score_contract, dict):
        score_contract = {}
    gap_types = score_contract.get("evidence_gap_types", [])
    gap_targets = score_contract.get("evidence_gap_targets", [])
    if not isinstance(gap_types, list):
        gap_types = []
    if not isinstance(gap_targets, list):
        gap_targets = []

    weakest_point = str(meta.get("weakest_point", "") or "").strip()
    cap_reason_detail = str(score_contract.get("cap_reason_detail", "") or "").strip()
    severity = default_gap_severity_from_score_contract(score_contract)
    gaps: list[dict] = []
    max_len = max(len(gap_types), len(gap_targets))
    for idx in range(max_len):
        gap_type = str(gap_types[idx] if idx < len(gap_types) else "other")
        target = str(gap_targets[idx] if idx < len(gap_targets) else f"gap_{idx + 1}")
        description = cap_reason_detail or weakest_point or target
        gaps.append(
            {
                "gap_type": gap_type,
                "target": target,
                "description": description,
                "severity": severity,
                "producer": "history_reconstruction",
                "producer_rationale": "Reconstructed from saved best meta because explicit champion gap artifacts were missing or stale.",
                "fetch_query": "",
                "adversarial_direction": True,
            }
        )
    return gaps


def build_champion_eval_from_saved_best(
    meta: dict,
    history_stem: str,
    *,
    project_rubric: str,
    project_dynamic: bool,
    project_mutator_model_id: str,
    project_judge_model_id: str,
    score_regime_fingerprint_from_meta: FingerprintFromMeta,
    score_regime_fingerprint_from_score_contract: FingerprintFromScoreContract,
) -> dict:
    score_contract = meta.get("score_contract", {}) if isinstance(meta, dict) else {}
    if not isinstance(score_contract, dict):
        score_contract = {}
    payload = {
        "score": meta.get("score"),
        "weakest_point": meta.get("weakest_point", ""),
        "rubric": meta.get("rubric", project_rubric),
        "dynamic": meta.get("dynamic", project_dynamic),
        "mutator_model": meta.get("mutator_model", project_mutator_model_id),
        "judge_model": meta.get("judge_model", project_judge_model_id),
        "timestamp": meta.get("timestamp", ""),
        "score_contract": score_contract,
        "score_regime_fingerprint": score_regime_fingerprint_from_meta(meta),
        "history_stem": history_stem,
        "evidence_gaps": reconstruct_evidence_gaps_from_saved_meta(meta),
    }
    return set_artifact_role(
        payload,
        "champion",
        score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
    )


def build_champion_gap_payload_from_saved_best(
    meta: dict,
    *,
    project_name: str,
    score_regime_fingerprint_from_meta: FingerprintFromMeta,
    score_regime_fingerprint_from_score_contract: FingerprintFromScoreContract,
) -> dict:
    score_contract = meta.get("score_contract", {}) if isinstance(meta, dict) else {}
    if not isinstance(score_contract, dict):
        score_contract = {}
    payload = {
        "project": project_name,
        "judge_model": meta.get("judge_model", ""),
        "generated_on": meta.get("timestamp", ""),
        "score": meta.get("score"),
        "weakest_point": meta.get("weakest_point", ""),
        "evidence_boundary_ceiling_detected": bool(
            score_contract.get("evidence_boundary_ceiling_detected", False)
        ),
        "cap_reason": score_contract.get("cap_reason", "none"),
        "cap_reason_detail": score_contract.get("cap_reason_detail", ""),
        "score_regime_fingerprint": score_regime_fingerprint_from_meta(meta) or "",
        "evidence_gaps": reconstruct_evidence_gaps_from_saved_meta(meta),
    }
    return set_artifact_role(
        payload,
        "champion",
        score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
    )


def champion_artifacts_out_of_sync_with_saved_best(
    champion_eval: dict | None,
    *,
    history_stem: str | None,
    saved_meta: dict | None,
    score_regime_fingerprint_from_meta: FingerprintFromMeta,
    score_regime_fingerprint_from_score_contract: FingerprintFromScoreContract,
) -> bool:
    if not history_stem or not isinstance(saved_meta, dict):
        return champion_eval is None
    if champion_eval is None:
        return True
    champion_score = champion_eval.get("score")
    saved_score = saved_meta.get("score")
    if champion_score != saved_score:
        return True
    champion_history_stem = champion_eval.get("history_stem")
    if isinstance(champion_history_stem, str) and champion_history_stem != history_stem:
        return True
    champion_fingerprint = artifact_regime_fingerprint(
        champion_eval,
        score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
    )
    saved_fingerprint = score_regime_fingerprint_from_meta(saved_meta)
    return bool(saved_fingerprint and champion_fingerprint != saved_fingerprint)
