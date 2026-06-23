from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from ztare.findings.prose_spec import (
    ProseAssertionType,
    ProseSpec,
    ProseSpecAssertion,
    load_prose_spec,
    validate_prose_spec,
)

HEADER_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)
WORD_RE = re.compile(r"\b\w+\b")


@dataclass(frozen=True)
class ProseVerificationFailure:
    assertion_id: str
    assertion_type: str
    section_header: str
    reason: str


@dataclass(frozen=True)
class ProseVerificationResult:
    passed: bool
    checked_assertions: int
    failed_assertions: tuple[ProseVerificationFailure, ...]
    total_word_count: int
    sections_present: tuple[str, ...]


def _normalize_header(header: str) -> str:
    return header.strip()


def _count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def _canonicalize_markdown_text(markdown_text: str) -> str:
    normalized = markdown_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def _extract_sections(markdown_text: str) -> dict[str, str]:
    matches = list(HEADER_RE.finditer(markdown_text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        header = _normalize_header(match.group(2))
        level = len(match.group(1))
        start = match.end()
        end = len(markdown_text)
        for candidate in matches[index + 1 :]:
            candidate_level = len(candidate.group(1))
            if candidate_level <= level:
                end = candidate.start()
                break
        sections[header] = markdown_text[start:end].strip()
    return sections


def _has_subsection(section_text: str, target_header: str) -> bool:
    target = _normalize_header(target_header)
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("##"):
            candidate = stripped.lstrip("#").strip()
            if candidate == target:
                return True
    return False


def _resolve_section_text(
    assertion: ProseSpecAssertion,
    *,
    markdown_text: str,
    sections: dict[str, str],
) -> tuple[str, str]:
    section_header = _normalize_header(assertion.section_header)
    if not section_header:
        return "", markdown_text
    return section_header, sections.get(section_header, "")


def _check_assertion(
    assertion: ProseSpecAssertion,
    *,
    markdown_text: str,
    sections: dict[str, str],
) -> ProseVerificationFailure | None:
    section_header, section_text = _resolve_section_text(
        assertion,
        markdown_text=markdown_text,
        sections=sections,
    )

    if section_header and section_header not in sections:
        return ProseVerificationFailure(
            assertion_id=assertion.assertion_id,
            assertion_type=assertion.assertion_type.value,
            section_header=section_header,
            reason="target_section_missing",
        )

    target = assertion.target or ""

    if assertion.assertion_type == ProseAssertionType.CONTAINS_PHRASE:
        if target not in section_text:
            return ProseVerificationFailure(
                assertion_id=assertion.assertion_id,
                assertion_type=assertion.assertion_type.value,
                section_header=section_header,
                reason="required_phrase_missing",
            )
        return None

    if assertion.assertion_type == ProseAssertionType.CONTAINS_CITATION:
        if target not in section_text:
            return ProseVerificationFailure(
                assertion_id=assertion.assertion_id,
                assertion_type=assertion.assertion_type.value,
                section_header=section_header,
                reason="required_citation_missing",
            )
        return None

    if assertion.assertion_type == ProseAssertionType.HAS_SUBSECTION:
        if not _has_subsection(section_text, target):
            return ProseVerificationFailure(
                assertion_id=assertion.assertion_id,
                assertion_type=assertion.assertion_type.value,
                section_header=section_header,
                reason="required_subsection_missing",
            )
        return None

    if assertion.assertion_type == ProseAssertionType.WORD_COUNT_RANGE:
        section_word_count = _count_words(section_text)
        assert assertion.target_min is not None
        assert assertion.target_max is not None
        if not (assertion.target_min <= section_word_count <= assertion.target_max):
            return ProseVerificationFailure(
                assertion_id=assertion.assertion_id,
                assertion_type=assertion.assertion_type.value,
                section_header=section_header,
                reason=(
                    f"section_word_count_out_of_range:{section_word_count}:"
                    f"{assertion.target_min}-{assertion.target_max}"
                ),
        )
        return None

    if assertion.assertion_type == ProseAssertionType.ABSENT_PHRASE:
        if target in section_text:
            return ProseVerificationFailure(
                assertion_id=assertion.assertion_id,
                assertion_type=assertion.assertion_type.value,
                section_header=section_header,
                reason="forbidden_phrase_present",
            )
        return None

    raise ValueError(f"Unsupported assertion type: {assertion.assertion_type}")


def verify_prose_markdown(markdown_text: str, spec: ProseSpec) -> ProseVerificationResult:
    spec_validation = validate_prose_spec(spec)
    if spec_validation["passed"] is not True:
        raise ValueError(f"Invalid prose spec: {spec_validation['issues']}")

    markdown_text = _canonicalize_markdown_text(markdown_text)
    sections = _extract_sections(markdown_text)
    failures: list[ProseVerificationFailure] = []

    total_word_count = _count_words(markdown_text)
    if not (spec.global_word_min <= total_word_count <= spec.global_word_max):
        failures.append(
            ProseVerificationFailure(
                assertion_id="global_word_count",
                assertion_type=ProseAssertionType.WORD_COUNT_RANGE.value,
                section_header="",
                reason=(
                    f"global_word_count_out_of_range:{total_word_count}:"
                    f"{spec.global_word_min}-{spec.global_word_max}"
                ),
            )
        )

    for header in spec.required_headers:
        if _normalize_header(header) not in sections:
            failures.append(
                ProseVerificationFailure(
                    assertion_id=f"required_header:{header}",
                    assertion_type="required_header",
                    section_header=_normalize_header(header),
                    reason="required_header_missing",
                )
            )

    for assertion in spec.assertions:
        failure = _check_assertion(
            assertion,
            markdown_text=markdown_text,
            sections=sections,
        )
        if failure is not None:
            failures.append(failure)

    return ProseVerificationResult(
        passed=not failures,
        checked_assertions=len(spec.assertions) + len(spec.required_headers) + 1,
        failed_assertions=tuple(failures),
        total_word_count=total_word_count,
        sections_present=tuple(sections.keys()),
    )


def verify_prose_file(*, draft_path: Path, spec_path: Path) -> ProseVerificationResult:
    return verify_prose_markdown(
        draft_path.read_text(),
        load_prose_spec(spec_path),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify prose against a deterministic prose spec.")
    parser.add_argument("--draft-path", type=Path, required=True)
    parser.add_argument("--spec-path", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    result = verify_prose_file(draft_path=args.draft_path, spec_path=args.spec_path)
    payload = {
        "passed": result.passed,
        "checked_assertions": result.checked_assertions,
        "failed_assertions": [asdict(item) for item in result.failed_assertions],
        "total_word_count": result.total_word_count,
        "sections_present": list(result.sections_present),
    }
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n")

    print(
        f"Prose verifier: passed={result.passed} "
        f"checked_assertions={result.checked_assertions} "
        f"failed_assertions={len(result.failed_assertions)}"
    )
    for failure in result.failed_assertions:
        print(
            f"- FAIL {failure.assertion_id} [{failure.assertion_type}] "
            f"section={failure.section_header or '<global>'} reason={failure.reason}"
        )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
