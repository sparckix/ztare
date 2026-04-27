import json
import re
from typing import Any, Dict, Iterable, List, Optional, Set

from src.ztare.common.paths import GLOBAL_PRIMITIVES_DIR, REPO_ROOT

ROOT_DIR = REPO_ROOT
APPROVED_DIR = GLOBAL_PRIMITIVES_DIR / "approved"

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "their",
    "they", "them", "then", "than", "when", "where", "will", "would", "could",
    "should", "must", "need", "have", "has", "had", "are", "was", "were", "been",
    "being", "over", "under", "into", "onto", "only", "also", "more", "less",
    "than", "just", "very", "much", "most", "some", "such", "what", "which", "while",
    "about", "across", "through", "after", "before", "against", "within", "without",
    "because", "there", "these", "those", "does", "did", "not", "but", "can",
}


def tokenize(text: str) -> Set[str]:
    tokens = set()
    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower()):
        if token in STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def confidence_weight(value: str) -> float:
    return {"low": 0.7, "medium": 1.0, "high": 1.25}.get((value or "").lower(), 1.0)


def load_approved_primitives() -> List[Dict[str, Any]]:
    primitives: List[Dict[str, Any]] = []
    if not APPROVED_DIR.exists():
        return primitives
    for path in sorted(APPROVED_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        data["_path"] = str(path.relative_to(ROOT_DIR))
        primitives.append(data)
    return primitives


def load_approved_primitives_index() -> Dict[str, Dict[str, Any]]:
    return {
        primitive.get("primitive_key"): primitive
        for primitive in load_approved_primitives()
        if primitive.get("primitive_key")
    }


def primitive_relevance_score(primitive: Dict[str, Any], query_text: str) -> float:
    query_tokens = tokenize(query_text)
    if not query_tokens:
        return 0.0

    tag_tokens = tokenize(" ".join(primitive.get("tags", [])))
    title_tokens = tokenize(primitive.get("title", ""))
    key_tokens = tokenize(primitive.get("primitive_key", "").replace("_", " "))
    summary_tokens = tokenize(primitive.get("summary", ""))
    mechanism_tokens = tokenize(primitive.get("mechanism", ""))
    scope_tokens = tokenize(" ".join(primitive.get("scope_conditions", [])))

    score = 0.0
    score += len(query_tokens & tag_tokens) * 4.0
    score += len(query_tokens & key_tokens) * 3.0
    score += len(query_tokens & title_tokens) * 3.0
    score += len(query_tokens & summary_tokens) * 1.5
    score += len(query_tokens & mechanism_tokens) * 1.5
    score += len(query_tokens & scope_tokens) * 1.0
    score *= confidence_weight(primitive.get("confidence", ""))
    return score


def retrieve_primitives(
    query_text: str,
    top_k: int = 3,
    epistemic_role: Optional[str] = None,
    primitive_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []
    for primitive in load_approved_primitives():
        if epistemic_role and primitive.get("epistemic_role") != epistemic_role:
            continue
        if primitive_type and primitive.get("primitive_type") != primitive_type:
            continue
        score = primitive_relevance_score(primitive, query_text)
        if score <= 0:
            continue
        primitive = dict(primitive)
        primitive["_relevance_score"] = round(score, 2)
        scored.append(primitive)
    scored.sort(key=lambda item: item["_relevance_score"], reverse=True)
    return scored[:top_k]


def retrieve_primitives_by_keys(
    primitive_keys: Iterable[str],
    epistemic_role: Optional[str] = None,
    primitive_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    index = load_approved_primitives_index()
    selected: List[Dict[str, Any]] = []
    for primitive_key in primitive_keys:
        primitive = index.get(primitive_key)
        if not primitive:
            continue
        if epistemic_role and primitive.get("epistemic_role") != epistemic_role:
            continue
        if primitive_type and primitive.get("primitive_type") != primitive_type:
            continue
        selected.append(dict(primitive))
    return selected


def _render_scope(lines: List[str], label: str, items: Iterable[str]) -> None:
    values = [item for item in items if item]
    if not values:
        return
    lines.append(f"{label}:")
    for item in values:
        lines.append(f"- {item}")


def format_attack_templates(primitives: List[Dict[str, Any]]) -> str:
    if not primitives:
        return "None."

    lines = [
        "KNOWN ADVERSARIAL PRECEDENTS (NOT EVIDENCE):",
        "Use these as attack/test prompts only. They are reusable precedents, not truths about the current project.",
        "",
    ]
    for idx, primitive in enumerate(primitives, start=1):
        lines.append(f"{idx}. {primitive.get('title', primitive.get('primitive_key', 'Untitled'))}")
        lines.append(f"   - Key: {primitive.get('primitive_key', '')}")
        lines.append(f"   - Mechanism: {primitive.get('mechanism', '').strip()}")
        lines.append(f"   - Attack: {primitive.get('verification_panel_attack', '').strip()}")
        transfer_test = primitive.get("required_transfer_test", "").strip()
        if transfer_test:
            lines.append(f"   - Transfer test: {transfer_test}")
        lines.append(f"   - Relevance score: {primitive.get('_relevance_score', 'n/a')}")
    return "\n".join(lines)


def format_transfer_hypotheses(primitives: List[Dict[str, Any]]) -> str:
    if not primitives:
        return "None."

    lines = [
        "TRANSFER HYPOTHESES (UNPROVEN HERE):",
        "These are reusable structural hypotheses from prior runs. They are not evidence and they are not axioms.",
        "If you use one, you must justify applicability in this domain and satisfy its transfer test.",
        "",
    ]
    for idx, primitive in enumerate(primitives, start=1):
        lines.append(f"{idx}. {primitive.get('title', primitive.get('primitive_key', 'Untitled'))}")
        lines.append(f"   - Pattern: {primitive.get('summary', '').strip()}")
        lines.append(f"   - Scope: {'; '.join(primitive.get('scope_conditions', [])) or 'Not specified'}")
        non_transfer = primitive.get("non_transfer_cases", [])
        if non_transfer:
            lines.append(f"   - Do not use if: {'; '.join(non_transfer)}")
        lines.append(f"   - Transfer test: {primitive.get('required_transfer_test', '').strip()}")
    return "\n".join(lines)


def format_transfer_candidates(primitives: List[Dict[str, Any]]) -> str:
    """Backward-compatible alias. Prefer format_transfer_hypotheses."""
    return format_transfer_hypotheses(primitives)


def format_judge_guardrail(primitives: List[Dict[str, Any]], require_transfer_proof: bool) -> str:
    if not primitives:
        return "None."

    lines = [
        "KNOWN FAILURE PRECEDENTS (NOT EVIDENCE):",
        "These are reusable adversarial precedents from prior runs. Do not reward a thesis for sounding similar to them.",
        "Only use them to detect whether the thesis repeats a known structural failure.",
        "",
    ]
    for idx, primitive in enumerate(primitives, start=1):
        lines.append(f"{idx}. {primitive.get('title', primitive.get('primitive_key', 'Untitled'))}")
        lines.append(f"   - Mechanism: {primitive.get('mechanism', '').strip()}")
        lines.append(f"   - Failure signal: {primitive.get('judge_penalty_condition', '').strip()}")
    lines.extend(
        [
            "",
            "EVIDENTIARY SAFE HARBOR:",
            "Do not fire a failure precedent merely because a thesis consumes upstream booleans, scores, or status tokens.",
            "If the thesis is explicitly scope-limited to a bounded local deterministic mapping or fail-closed gate, disclaims upstream truthfulness/completeness, and its tests exhaustively validate that local contract, treat that as acceptable local rigor rather than as a trust leak.",
            "Only apply the precedent if the thesis overclaims, treats upstream inputs as inherently truthful, or uses the local mapping as proof of whole-system validity.",
        ]
    )
    if require_transfer_proof:
        lines.extend(
            [
                "",
                "TRANSFER GATE:",
                "If the thesis relies on a transfer candidate without explicit domain-specific justification or without satisfying the stated transfer test, apply a severe penalty for unearned epistemic trust.",
            ]
        )
    return "\n".join(lines)
