from __future__ import annotations

import ast
import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from src.ztare.gates.claim_polarity import hard_positive_phrase_group_labels


PhraseGroup = tuple[str, ...]

_SYMBOL_TRANSLATIONS = str.maketrans(
    {
        "Λ": " lambda ",
        "λ": " lambda ",
        "Δ": " delta ",
        "∇": " grad ",
        "∞": " infty ",
        "≤": " <= ",
        "≥": " >= ",
        "→": " -> ",
        "·": " ",
        "—": " ",
        "–": " ",
        "_": " ",
        "-": " ",
        "/": " ",
    }
)


@dataclass(frozen=True)
class FunctionContract:
    """One module-scope function required by a qualitative theorem packet.

    `own_groups` must be present in the named function body itself.
    `packet_groups` may be satisfied in the named function plus related
    theorem-packet functions listed in `packet_scope`.
    """

    name: str
    description: str
    own_groups: tuple[PhraseGroup, ...] = ()
    packet_groups: tuple[PhraseGroup, ...] = ()
    packet_scope: tuple[str, ...] = ()


@dataclass(frozen=True)
class TheoremPacketGateSpec:
    gate_name: str
    threshold: str
    functions: tuple[FunctionContract, ...]
    banned_groups: Mapping[str, Sequence[str]]
    overclaim_checks: tuple[Callable[[str], str | None], ...] = ()
    baseline_marker: str = "baseline_incomplete"
    content_groups_hard: bool = True
    semantic_near_miss_missing_group_budget: int | None = None


def function_source(source: str, name: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    lines = source.splitlines()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            start = max(0, node.lineno - 1)
            end = getattr(node, "end_lineno", node.lineno)
            return "\n".join(lines[start:end])
    return ""


def combined_source(*parts: str) -> str:
    return "\n".join(part for part in parts if part)


def canonical_contract_text(text: str) -> str:
    """Normalize theorem-packet prose before matching contract clauses.

    Theorem-packet gates should fail on missing ideas, not on whether a mutator
    wrote `LowHighBony`, `low-high`, `LP/Bony`, or Unicode math symbols. This
    normalizer keeps the gate deterministic while removing punctuation,
    camel-case, and common math-symbol brittleness.
    """

    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", normalized)
    normalized = normalized.translate(_SYMBOL_TRANSLATIONS)
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    compact = normalized.replace(" ", "")
    return f"{normalized}\n{compact}" if compact else normalized


def _phrase_present(text_lowered: str, text_canonical: str, phrase: str) -> bool:
    phrase_lowered = phrase.lower()
    if phrase_lowered in text_lowered:
        return True
    phrase_canonical = canonical_contract_text(phrase)
    if not phrase_canonical:
        return False
    phrase_variants = [line for line in phrase_canonical.splitlines() if line]
    return any(variant in text_canonical for variant in phrase_variants)


def missing_groups(text: str, groups: tuple[PhraseGroup, ...]) -> list[str]:
    lowered = text.lower()
    canonical = canonical_contract_text(text)
    if not lowered:
        return ["function body absent"]
    bad = ("todo", "placeholder", "unknown", "not_yet_derived", "not yet derived")
    if any(_phrase_present(lowered, canonical, token) for token in bad):
        return ["placeholder/unknown content"]
    missing: list[str] = []
    for group in groups:
        if not any(_phrase_present(lowered, canonical, token) for token in group):
            missing.append("/".join(group[:4]))
    return missing


def evaluate_theorem_packet(source: str, spec: TheoremPacketGateSpec) -> dict:
    functions = {contract.name: function_source(source, contract.name) for contract in spec.functions}
    reasons: list[str] = []
    content_warnings: list[str] = []
    semantic_missing_group_count = 0
    semantic_near_miss = False

    if spec.baseline_marker and spec.baseline_marker in source.lower():
        reasons.append("Baseline skeleton copied without completing the theorem packet.")

    for contract in spec.functions:
        body = functions[contract.name]
        if not body:
            description = contract.description.strip().rstrip(".")
            reasons.append(f"Missing top-level {contract.name}() {description}.")
            continue

        own_missing = missing_groups(body, contract.own_groups) if contract.own_groups else []
        packet_text = combined_source(
            body,
            *(functions.get(name, "") for name in contract.packet_scope),
        )
        packet_missing = (
            missing_groups(packet_text, contract.packet_groups)
            if contract.packet_groups
            else []
        )
        combined_missing = own_missing + [
            group for group in packet_missing if group not in own_missing
        ]
        if combined_missing:
            message = (
                f"{contract.name}() exists but is incomplete; missing content groups: "
                + ", ".join(combined_missing)
            )
            semantic_missing_group_count += len(combined_missing)
            placeholder_missing = "placeholder/unknown content" in combined_missing
            if spec.content_groups_hard and (
                spec.semantic_near_miss_missing_group_budget is None
                or placeholder_missing
            ):
                reasons.append(message)
            elif spec.content_groups_hard:
                content_warnings.append(message)
            else:
                content_warnings.append(message)

    if (
        spec.content_groups_hard
        and spec.semantic_near_miss_missing_group_budget is not None
        and semantic_missing_group_count > spec.semantic_near_miss_missing_group_budget
    ):
        reasons.extend(content_warnings)
        content_warnings = []
    elif (
        spec.content_groups_hard
        and spec.semantic_near_miss_missing_group_budget is not None
        and semantic_missing_group_count > 0
    ):
        semantic_near_miss = True

    reasons.extend(hard_positive_phrase_group_labels(source, spec.banned_groups))
    for check in spec.overclaim_checks:
        reason = check(source)
        if reason:
            reasons.append(reason)

    passed = not reasons
    return {
        "harness_ok": True,
        "all_gates_pass": passed,
        "gates": [
            {
                "name": spec.gate_name,
                "passed": passed,
                "value": "pass" if passed else "; ".join(reasons),
                "threshold": spec.threshold,
                "operator": "must_satisfy",
                "near_miss": semantic_near_miss,
            }
        ],
        "function_presence": {name: bool(body) for name, body in functions.items()},
        "reasons": reasons,
        "content_warnings": content_warnings,
        "semantic_missing_group_count": semantic_missing_group_count,
        "semantic_near_miss": semantic_near_miss,
    }
