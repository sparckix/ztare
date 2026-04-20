from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ProseAssertionType(str, Enum):
    CONTAINS_PHRASE = "contains_phrase"
    CONTAINS_CITATION = "contains_citation"
    HAS_SUBSECTION = "has_subsection"
    WORD_COUNT_RANGE = "word_count_range"
    ABSENT_PHRASE = "absent_phrase"


@dataclass(frozen=True)
class ProseSpecAssertion:
    assertion_id: str
    section_header: str
    assertion_type: ProseAssertionType
    target: str | None = None
    target_min: int | None = None
    target_max: int | None = None


@dataclass(frozen=True)
class ProseSpec:
    packet_id: str
    required_headers: tuple[str, ...]
    assertions: tuple[ProseSpecAssertion, ...]
    global_word_min: int
    global_word_max: int


def _legacy_assertions_from_payload(payload: dict[str, Any]) -> tuple[tuple[ProseSpecAssertion, ...], int, int]:
    assertions: list[ProseSpecAssertion] = []
    global_word_min = 0
    global_word_max = 0

    for item in payload.get("required_phrases", ()):
        assertions.append(
            ProseSpecAssertion(
                assertion_id=str(item.get("assertion_id") or f"required_phrase:{item['section_header']}:{item['phrase']}"),
                section_header=str(item.get("section_header", "")),
                assertion_type=ProseAssertionType.CONTAINS_PHRASE,
                target=str(item["phrase"]),
            )
        )

    for item in payload.get("banned_phrases", ()):
        assertions.append(
            ProseSpecAssertion(
                assertion_id=str(item.get("assertion_id") or f"banned_phrase:{item['section_header']}:{item['phrase']}"),
                section_header=str(item.get("section_header", "")),
                assertion_type=ProseAssertionType.ABSENT_PHRASE,
                target=str(item["phrase"]),
            )
        )

    for item in payload.get("required_citations", ()):
        assertions.append(
            ProseSpecAssertion(
                assertion_id=str(item.get("assertion_id") or f"required_citation:{item['section_header']}:{item['citation']}"),
                section_header=str(item.get("section_header", "")),
                assertion_type=ProseAssertionType.CONTAINS_CITATION,
                target=str(item["citation"]),
            )
        )

    for item in payload.get("word_count_bounds", ()):
        section_header = str(item.get("section_header", ""))
        min_words = int(item["min_words"])
        max_words = int(item["max_words"])
        if section_header == "__document__":
            global_word_min = min_words
            global_word_max = max_words
            continue
        assertions.append(
            ProseSpecAssertion(
                assertion_id=str(item.get("assertion_id") or f"word_count:{section_header or '__global__'}"),
                section_header=section_header,
                assertion_type=ProseAssertionType.WORD_COUNT_RANGE,
                target_min=min_words,
                target_max=max_words,
            )
        )

    return tuple(assertions), global_word_min, global_word_max


def _assertion_id_from_parts(*parts: object) -> str:
    normalized = [str(part).strip().replace(" ", "_") for part in parts if str(part).strip()]
    return ":".join(normalized) if normalized else "assertion"


def _assertion_from_payload_item(item: dict[str, Any], index: int) -> ProseSpecAssertion:
    if "assertion_type" in item or "assertion_id" in item:
        assertion_type = ProseAssertionType(str(item["assertion_type"]))
        target = str(item["target"]) if item.get("target") is not None else None
        target_min = int(item["target_min"]) if item.get("target_min") is not None else None
        target_max = int(item["target_max"]) if item.get("target_max") is not None else None
        assertion_id = str(
            item.get("assertion_id")
            or _assertion_id_from_parts(
                assertion_type.value,
                item.get("section_header", ""),
                target if target is not None else f"{target_min}-{target_max}",
                index,
            )
        )
        return ProseSpecAssertion(
            assertion_id=assertion_id,
            section_header=str(item.get("section_header", "")),
            assertion_type=assertion_type,
            target=target,
            target_min=target_min,
            target_max=target_max,
        )

    if len(item) != 1:
        raise KeyError("assertion_id")

    raw_assertion_type, raw_value = next(iter(item.items()))
    assertion_type = ProseAssertionType(str(raw_assertion_type))
    if assertion_type == ProseAssertionType.WORD_COUNT_RANGE:
        if not isinstance(raw_value, dict):
            raise KeyError("assertion_id")
        target_min = int(raw_value["min"])
        target_max = int(raw_value["max"])
        return ProseSpecAssertion(
            assertion_id=_assertion_id_from_parts(assertion_type.value, index),
            section_header="",
            assertion_type=assertion_type,
            target_min=target_min,
            target_max=target_max,
        )

    target = str(raw_value)
    return ProseSpecAssertion(
        assertion_id=_assertion_id_from_parts(assertion_type.value, target, index),
        section_header="",
        assertion_type=assertion_type,
        target=target,
    )


def prose_spec_from_dict(payload: dict[str, Any]) -> ProseSpec:
    if "assertions" in payload:
        assertions = tuple(
            _assertion_from_payload_item(item, index)
            for index, item in enumerate(payload.get("assertions", ()), start=1)
        )
        global_word_min = int(payload.get("global_word_min", 0))
        global_word_max = int(payload.get("global_word_max", 0))
    else:
        assertions, global_word_min, global_word_max = _legacy_assertions_from_payload(payload)

    return ProseSpec(
        packet_id=str(payload["packet_id"]),
        required_headers=tuple(str(item) for item in payload.get("required_headers", ())),
        assertions=assertions,
        global_word_min=global_word_min,
        global_word_max=global_word_max,
    )


def prose_spec_to_dict(spec: ProseSpec) -> dict[str, Any]:
    return asdict(spec)


def prose_spec_payload_has_canonical_shape(payload: dict[str, Any]) -> bool:
    return isinstance(payload.get("assertions"), list)


def prose_spec_path_has_canonical_shape(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return prose_spec_payload_has_canonical_shape(payload)


def load_prose_spec(path: Path) -> ProseSpec:
    return prose_spec_from_dict(json.loads(path.read_text()))


def validate_prose_spec(spec: ProseSpec) -> dict[str, object]:
    issues: list[str] = []

    if not spec.packet_id.strip():
        issues.append("missing_packet_id")

    if spec.global_word_min < 0:
        issues.append("negative_global_word_min")
    if spec.global_word_max < 0:
        issues.append("negative_global_word_max")
    if spec.global_word_max < spec.global_word_min:
        issues.append("global_word_range_inverted")

    header_set: set[str] = set()
    for header in spec.required_headers:
        normalized = header.strip()
        if not normalized:
            issues.append("blank_required_header")
            continue
        if normalized in header_set:
            issues.append(f"duplicate_required_header:{normalized}")
        header_set.add(normalized)

    assertion_ids: set[str] = set()
    for assertion in spec.assertions:
        if not assertion.assertion_id.strip():
            issues.append("blank_assertion_id")
        elif assertion.assertion_id in assertion_ids:
            issues.append(f"duplicate_assertion_id:{assertion.assertion_id}")
        assertion_ids.add(assertion.assertion_id)

        if assertion.assertion_type == ProseAssertionType.WORD_COUNT_RANGE:
            if assertion.target_min is None or assertion.target_max is None:
                issues.append(f"word_count_range_missing_bounds:{assertion.assertion_id}")
            else:
                if assertion.target_min < 0 or assertion.target_max < 0:
                    issues.append(f"word_count_range_negative:{assertion.assertion_id}")
                if assertion.target_max < assertion.target_min:
                    issues.append(f"word_count_range_inverted:{assertion.assertion_id}")
            if assertion.target not in {None, ""}:
                issues.append(f"word_count_range_target_not_empty:{assertion.assertion_id}")
        else:
            if assertion.target is None or not assertion.target.strip():
                issues.append(f"missing_target:{assertion.assertion_id}")
            if assertion.target_min is not None or assertion.target_max is not None:
                issues.append(f"unexpected_bounds:{assertion.assertion_id}")

    return {
        "packet_id": spec.packet_id,
        "passed": not issues,
        "issues": issues,
    }


def validate_prose_spec_path(path: Path) -> dict[str, object]:
    return validate_prose_spec(load_prose_spec(path))
