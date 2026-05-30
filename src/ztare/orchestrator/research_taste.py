"""Configurable research-taste scoring for next-move selection.

This mechanizes a narrow part of the operator loop: when several candidate
next moves exist, make their fit against an explicit principal preference
profile legible. It is an attention router, not a truth score, public-claim
license, or auto-dispatcher.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised in bare system Python
    yaml = None


DEFAULT_AXES = {
    "outstanding_problem_resolution": {
        "weight": 0.35,
        "keywords": (
            "open problem",
            "unresolved",
            "eigenquestion",
            "kill condition",
            "falsifier",
            "hard gate",
            "millennium",
            "gravity",
            "proof",
        ),
    },
    "prize_or_money_potential": {
        "weight": 0.25,
        "keywords": (
            "prize",
            "money",
            "funding",
            "publication",
            "paper",
            "ip",
            "patent",
            "commercial",
            "ssrn",
        ),
    },
    "architecture_fit": {
        "weight": 0.25,
        "keywords": (
            "current architecture",
            "bounded extension",
            "existing script",
            "template",
            "offline",
            "replay",
            "smoke",
            "fixture",
            "scaffold",
            "queue",
        ),
    },
    "self_recursive_governance": {
        "weight": 0.15,
        "keywords": (
            "ztare",
            "apparatus",
            "self recursive",
            "governance",
            "operator",
            "research director",
            "promotion guard",
            "ledger",
            "closure",
        ),
    },
}

DEFAULT_PENALTIES = {
    "public_claim_risk": {
        "weight": 0.20,
        "keywords": (
            "publish now",
            "declare",
            "discovery-grade",
            "universal law",
            "solved",
            "nobel",
            "claim",
        ),
    },
    "infrastructure_fragility": {
        "weight": 0.10,
        "keywords": (
            "gpu",
            "ssh",
            "cuda",
            "jax",
            "krylov",
            "timeout",
            "stiff",
            "ntfy",
            "api",
        ),
    },
}


@dataclass(frozen=True)
class ResearchTasteProfile:
    axes: dict[str, dict[str, Any]]
    penalties: dict[str, dict[str, Any]]
    pursue_now: float = 3.75
    queue: float = 2.25


def load_research_taste_profile(path: Path) -> ResearchTasteProfile:
    data = _load_yaml(path)
    taste = data.get("research_taste", {})
    axes = dict(DEFAULT_AXES)
    for name, spec in (taste.get("axes") or {}).items():
        merged = dict(axes.get(name, {}))
        merged.update(spec or {})
        merged.setdefault("keywords", DEFAULT_AXES.get(name, {}).get("keywords", ()))
        axes[name] = merged
    penalties = dict(DEFAULT_PENALTIES)
    for name, spec in (taste.get("penalties") or {}).items():
        merged = dict(penalties.get(name, {}))
        merged.update(spec or {})
        merged.setdefault("keywords", DEFAULT_PENALTIES.get(name, {}).get("keywords", ()))
        penalties[name] = merged
    thresholds = taste.get("routing_thresholds") or {}
    return ResearchTasteProfile(
        axes=axes,
        penalties=penalties,
        pursue_now=float(thresholds.get("pursue_now", 3.75)),
        queue=float(thresholds.get("queue", 2.25)),
    )


def _coerce_scalar(value: str) -> Any:
    text = value.strip()
    if not text:
        return {}
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _minimal_yaml_load(text: str) -> dict[str, Any]:
    """Small YAML subset parser for preference fixtures.

    The production path uses PyYAML. This fallback keeps offline fixture tests
    runnable in bare Python where optional provider/YAML deps are absent.
    It handles nested mappings with two-space indentation and scalar leaves.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        parsed = _coerce_scalar(value)
        parent[key.strip()] = parsed
        if isinstance(parsed, dict):
            stack.append((indent, parsed))
    return root


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return _minimal_yaml_load(text)


def _text_blob(candidate: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in candidate.items():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, dict):
            parts.append(json.dumps(value, sort_keys=True, default=str))
    return "\n".join(parts).lower()


def _keyword_score(text: str, keywords: tuple[str, ...] | list[str]) -> tuple[float, list[str]]:
    hits = []
    for keyword in keywords:
        pattern = re.escape(str(keyword).lower())
        if re.search(pattern, text):
            hits.append(str(keyword))
    if not keywords:
        return 0.0, hits
    if not hits:
        return 0.0, hits
    # Conservative saturation: one hit means weak evidence, three hits means
    # strong evidence. Explicit caller-supplied axis scores override this.
    return min(5.0, 1.5 + 1.25 * min(len(hits), 3)), hits


def _explicit_axis(candidate: dict[str, Any], name: str) -> float | None:
    axes = candidate.get("taste_axes")
    if isinstance(axes, dict) and name in axes:
        try:
            value = float(axes[name])
        except (TypeError, ValueError):
            return None
        return max(0.0, min(5.0, value))
    return None


def _candidate_severity(candidate: dict[str, Any]) -> float:
    try:
        return max(0.0, min(5.0, float(candidate.get("severity_level", 0.0))))
    except (TypeError, ValueError):
        return 0.0


def _metadata_axis_score(candidate: dict[str, Any], name: str) -> tuple[float, list[str]]:
    """Use typed queue metadata as weak evidence for taste axes.

    Keyword scoring alone is too brittle for discriminator queues: the most
    important proposal may be short and concrete, while a generic policy gate
    contains more taste keywords. Metadata does not promote truth; it only
    routes attention among already-typed candidates.
    """
    severity = _candidate_severity(candidate)
    project = str(candidate.get("project", "")).lower()
    priority = str(candidate.get("priority", "")).lower()
    promotion_blocking = bool(candidate.get("promotion_blocking"))
    source = str(candidate.get("source", "")).lower()
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    template = str(metadata.get("replay_template", "")).lower() if isinstance(metadata, dict) else ""
    is_generic_template = template.startswith("generic_")
    signals: list[str] = []
    score = 0.0

    if name == "outstanding_problem_resolution":
        if severity >= 4 and promotion_blocking:
            score = max(score, min(5.0, 2.0 + 0.6 * severity))
            signals.append(f"severity_level={severity:g}")
        if project in {"gp163d_unified_accel", "ns_millennium_hunt"} and not is_generic_template:
            score = max(score, 3.25)
            signals.append(f"frontier_project={project}")
        if "gate" in template and severity >= 4 and not is_generic_template:
            score = max(score, 3.75)
            signals.append(f"replay_template={template}")

    elif name == "prize_or_money_potential":
        if is_generic_template:
            score = max(score, 1.5)
            signals.append(f"generic_template={template}")
        elif project == "ns_millennium_hunt":
            score = max(score, 4.5)
            signals.append("millennium_track")
        elif project == "gp163d_unified_accel" and severity >= 5:
            score = max(score, 4.0)
            signals.append("gravity_frontier_track")
        elif project == "gp163d_unified_accel":
            score = max(score, 3.25)
            signals.append("paper7_gravity_track")

    elif name == "architecture_fit":
        if candidate.get("auto_testable"):
            score = max(score, 4.25)
            signals.append("auto_testable")
        if candidate.get("cheapest_discriminator") or candidate.get("kill_condition"):
            score = max(score, 3.5)
            signals.append("typed_discriminator")
        if candidate.get("required_artifacts"):
            score = max(score, 3.25)
            signals.append("artifact_requirements")
        if source in {"operator_replay_audit", "manual_gpu_closure", "manual_dynamic_inversion"} and not is_generic_template:
            score = max(score, 3.75)
            signals.append(f"source={source}")

    elif name == "self_recursive_governance":
        if source in {"operator_replay_audit", "manual_gpu_closure", "manual_dynamic_inversion"} and not is_generic_template:
            score = max(score, 4.0)
            signals.append("operator_replay_mechanism")
        if "promotion" in str(candidate.get("claim_under_pressure", "")).lower():
            score = max(score, 3.5)
            signals.append("promotion_boundary")

    elif name == "public_claim_risk":
        if candidate.get("can_support_promotion"):
            score = max(score, 4.0)
            signals.append("can_support_promotion")
        if candidate.get("promotion_blocking") and severity >= 5:
            score = max(score, 2.5)
            signals.append("promotion_blocking_l5")

    elif name == "infrastructure_fragility":
        risk_text = " ".join(
            str(candidate.get(key, ""))
            for key in ("instrument_risk", "cheapest_discriminator", "weak_test_risk")
        ).lower()
        if any(token in risk_text for token in ("gpu", "ssh", "cuda", "jax", "krylov", "boundary", "solver")):
            score = max(score, 3.0)
            signals.append("instrument_fragility_terms")

    if "high" in priority or "urgent" in priority:
        score = min(5.0, score + 0.25)
        signals.append(f"priority={priority}")
    return score, signals


def score_research_candidate(candidate: dict[str, Any], profile: ResearchTasteProfile) -> dict[str, Any]:
    text = _text_blob(candidate)
    axis_scores: dict[str, dict[str, Any]] = {}
    weighted = 0.0
    total_weight = 0.0
    for name, spec in profile.axes.items():
        weight = float(spec.get("weight", 0.0) or 0.0)
        explicit = _explicit_axis(candidate, name)
        if explicit is None:
            score, hits = _keyword_score(text, spec.get("keywords", ()))
            meta_score, meta_hits = _metadata_axis_score(candidate, name)
            if meta_score > score:
                score, hits = meta_score, meta_hits
                source = "metadata_inference"
            else:
                source = "keyword_inference"
        else:
            score, hits = explicit, []
            source = "explicit"
        axis_scores[name] = {"score": score, "weight": weight, "source": source, "hits": hits}
        weighted += score * weight
        total_weight += weight
    base_score = weighted / total_weight if total_weight else 0.0
    penalty_details: dict[str, dict[str, Any]] = {}
    total_penalty = 0.0
    for name, spec in profile.penalties.items():
        weight = float(spec.get("weight", 0.0) or 0.0)
        explicit = _explicit_axis(candidate, name)
        if explicit is None:
            score, hits = _keyword_score(text, spec.get("keywords", ()))
            meta_score, meta_hits = _metadata_axis_score(candidate, name)
            if meta_score > score:
                score, hits = meta_score, meta_hits
                source = "metadata_inference"
            else:
                source = "keyword_inference"
        else:
            score, hits = explicit, []
            source = "explicit"
        penalty = score * weight
        penalty_details[name] = {
            "score": score,
            "weight": weight,
            "penalty": penalty,
            "source": source,
            "hits": hits,
        }
        total_penalty += penalty
    final_score = max(0.0, min(5.0, base_score - total_penalty))
    if final_score >= profile.pursue_now:
        attention_band = "pursue_now"
    elif final_score >= profile.queue:
        attention_band = "queue"
    else:
        attention_band = "defer"
    has_cheapest = bool(candidate.get("cheapest_discriminator") or candidate.get("single_best_next_discriminator"))
    has_kill = bool(candidate.get("kill_condition"))
    can_support_promotion = bool(candidate.get("can_support_promotion", False))
    return {
        "candidate_id": str(
            candidate.get("id")
            or candidate.get("proposal_id")
            or candidate.get("replay_template_id")
            or candidate.get("claim_under_pressure")
            or "candidate"
        ),
        "final_score": round(final_score, 4),
        "base_score": round(base_score, 4),
        "total_penalty": round(total_penalty, 4),
        "attention_band": attention_band,
        "axis_scores": axis_scores,
        "penalties": penalty_details,
        "anti_goodhart_checks": {
            "has_cheapest_discriminator": has_cheapest,
            "has_kill_condition": has_kill,
            "can_support_promotion": can_support_promotion,
            "preference_priority_cannot_promote_confidence": True,
        },
    }


def build_opportunity_card(candidate: dict[str, Any], profile: ResearchTasteProfile) -> dict[str, Any]:
    score = score_research_candidate(candidate, profile)
    axis_assessments = {}
    for name, details in score["axis_scores"].items():
        axis_assessments[name] = {
            "rating": details["score"],
            "confidence": "medium" if details["source"] == "explicit" else "low",
            "source": details["source"],
            "evidence": details["hits"],
        }
    return {
        "schema_version": 1,
        "candidate_id": score["candidate_id"],
        "source_artifact": candidate.get("trigger_artifact") or candidate.get("source_artifact") or "",
        "eigenquestion": candidate.get("eigenquestion") or candidate.get("tightened_eigenquestion") or "",
        "proposed_action": (
            candidate.get("cheapest_discriminator")
            or candidate.get("single_best_next_discriminator")
            or candidate.get("proposed_action")
            or ""
        ),
        "preference_profile_version": "research_taste.schema_version=1",
        "axis_assessments": axis_assessments,
        "advisory_sort_score": score["final_score"],
        "attention_band": score["attention_band"],
        "anti_goodhart_checks": score["anti_goodhart_checks"],
        "operator_decision": "unset",
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def rank_candidates(candidates: list[dict[str, Any]], profile: ResearchTasteProfile) -> list[dict[str, Any]]:
    scored = []
    for candidate in candidates:
        score = score_research_candidate(candidate, profile)
        scored.append({
            "candidate": candidate,
            "taste_score": score,
            "opportunity_card": build_opportunity_card(candidate, profile),
        })
    scored.sort(key=lambda item: item["taste_score"]["final_score"], reverse=True)
    return scored


def write_ranking_report(
    *,
    candidates: list[dict[str, Any]],
    profile: ResearchTasteProfile,
    out_path: Path,
) -> dict[str, Any]:
    report = {
        "schema_version": 1,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "profile": {
            "axes": {k: {"weight": v.get("weight")} for k, v in profile.axes.items()},
            "penalties": {k: {"weight": v.get("weight")} for k, v in profile.penalties.items()},
            "routing_thresholds": {"pursue_now": profile.pursue_now, "queue": profile.queue},
        },
        "ranked": rank_candidates(candidates, profile),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank next research moves against principal taste preferences.")
    parser.add_argument("--queue", type=Path, required=True, help="JSONL candidate/proposal queue.")
    parser.add_argument("--preferences", type=Path, default=Path("org/preferences/principal.yaml"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    profile = load_research_taste_profile(args.preferences)
    candidates = load_jsonl(args.queue)
    report = write_ranking_report(candidates=candidates, profile=profile, out_path=args.out)
    print(f"Wrote {args.out}")
    for item in report["ranked"][:5]:
        score = item["taste_score"]
        print(f"{score['final_score']:.3f} {score['attention_band']} {score['candidate_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
