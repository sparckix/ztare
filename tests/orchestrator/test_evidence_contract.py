"""Tests for L2 typed evidence contract (Task #71)."""

from __future__ import annotations

import pytest

from src.ztare.fit.parsers import (
    EVIDENCE_PARSER_REGISTRY,
    parse_evidence_typed,
)
from src.ztare.orchestrator.evidence_contract import (
    EVIDENCE_ERROR_CODES,
    EvidenceContractError,
    EvidenceFormat,
    EvidenceSpec,
    get_evidence_spec,
    list_evidence_formats,
)


# ── Spec construction + lookup ───────────────────────────────────────────


class TestEvidenceSpec:
    def test_construct_minimal(self):
        spec = EvidenceSpec(
            format=EvidenceFormat.WHITESPACE_TABULAR,
            columns=("x", "y"),
        )
        assert spec.format is EvidenceFormat.WHITESPACE_TABULAR
        assert spec.columns == ("x", "y")
        assert spec.min_rows == 5
        assert spec.require_finite is True

    def test_frozen(self):
        spec = EvidenceSpec(format=EvidenceFormat.NONE, columns=())
        with pytest.raises(Exception):
            spec.format = EvidenceFormat.MARKDOWN_TABLE  # type: ignore[misc]

    def test_get_evidence_spec_from_rubric(self):
        rubric = {
            "evidence_contract": {
                "format": "MARKDOWN_TABLE",
                "columns": ["x", "y"],
                "independent_vars": ["x"],
                "min_rows": 7,
            }
        }
        spec = get_evidence_spec(rubric)
        assert spec is not None
        assert spec.format is EvidenceFormat.MARKDOWN_TABLE
        assert spec.columns == ("x", "y")
        assert spec.min_rows == 7

    def test_get_evidence_spec_missing_block(self):
        assert get_evidence_spec({}) is None
        assert get_evidence_spec({"evidence_contract": "not a dict"}) is None

    def test_get_evidence_spec_unknown_format(self):
        rubric = {"evidence_contract": {"format": "INVENTED_FORMAT", "columns": ["x", "y"]}}
        assert get_evidence_spec(rubric) is None

    def test_list_evidence_formats(self):
        names = list_evidence_formats()
        assert "WHITESPACE_TABULAR" in names
        assert "MARKDOWN_TABLE" in names
        assert "NONE" in names


# ── Per-format parsers ───────────────────────────────────────────────────


class TestWhitespaceParser:
    def test_basic_2col(self):
        text = "1.0 2.0\n3.0 6.0\n5.0 10.0\n7.0 14.0\n9.0 18.0\n"
        spec = EvidenceSpec(
            format=EvidenceFormat.WHITESPACE_TABULAR,
            columns=("x", "y"),
        )
        xs, ys = parse_evidence_typed(text, spec)
        assert ys == [2.0, 6.0, 10.0, 14.0, 18.0]
        assert xs[0] == [1.0, 3.0, 5.0, 7.0, 9.0]

    def test_skips_header_and_comments(self):
        text = "# header\nx y\n1.0 2.0\n3.0 6.0\n5.0 10.0\n7.0 14.0\n9.0 18.0\n"
        spec = EvidenceSpec(
            format=EvidenceFormat.WHITESPACE_TABULAR,
            columns=("x", "y"),
        )
        xs, ys = parse_evidence_typed(text, spec)
        assert len(ys) == 5

    def test_row_floor_violation(self):
        text = "1.0 2.0\n3.0 6.0\n"
        spec = EvidenceSpec(
            format=EvidenceFormat.WHITESPACE_TABULAR,
            columns=("x", "y"),
            min_rows=5,
        )
        with pytest.raises(EvidenceContractError) as exc:
            parse_evidence_typed(text, spec)
        assert exc.value.code == "ROW_FLOOR_VIOLATION"


class TestMarkdownParser:
    def test_basic_markdown(self):
        text = """| x | y |
|---|---|
| 1.3 | 1.69 |
| 1.8 | 1.38 |
| 3.1 | 0.94 |
| 4.4 | 0.69 |
| 5.2 | 0.61 |
"""
        spec = EvidenceSpec(
            format=EvidenceFormat.MARKDOWN_TABLE,
            columns=("x", "y"),
        )
        xs, ys = parse_evidence_typed(text, spec)
        assert len(ys) == 5
        assert ys[0] == 1.69

    def test_separator_row_skipped(self):
        text = """| x | y |
|---|---|
| 1.0 | 2.0 |
| 3.0 | 6.0 |
| 5.0 | 10.0 |
| 7.0 | 14.0 |
| 9.0 | 18.0 |
"""
        spec = EvidenceSpec(
            format=EvidenceFormat.MARKDOWN_TABLE,
            columns=("x", "y"),
        )
        _, ys = parse_evidence_typed(text, spec)
        assert ys == [2.0, 6.0, 10.0, 14.0, 18.0]


class TestSweepBlockParser:
    def test_2d_sweep(self):
        text = """=== v = 0.5 ===
1.0 2.0
2.0 4.0
3.0 6.0
=== v = 1.0 ===
1.0 3.0
2.0 5.0
"""
        spec = EvidenceSpec(
            format=EvidenceFormat.SWEEP_BLOCK,
            columns=("u", "v", "y"),
            independent_vars=("u", "v"),
            min_rows=4,
        )
        xs, ys = parse_evidence_typed(text, spec)
        assert len(ys) == 5
        # First three rows have v=0.5
        assert xs[1][0] == 0.5

    def test_sweep_block_requires_two_indep(self):
        text = "=== v = 0.5 ===\n1.0 2.0\n"
        spec = EvidenceSpec(
            format=EvidenceFormat.SWEEP_BLOCK,
            columns=("u", "y"),
            independent_vars=("u",),
        )
        with pytest.raises(EvidenceContractError) as exc:
            parse_evidence_typed(text, spec)
        assert exc.value.code == "COLUMN_COUNT_MISMATCH"


class TestCSVParser:
    def test_basic_csv(self):
        text = "x,y\n1.0,2.0\n3.0,6.0\n5.0,10.0\n7.0,14.0\n9.0,18.0\n"
        spec = EvidenceSpec(
            format=EvidenceFormat.CSV_HEADER,
            columns=("x", "y"),
        )
        _, ys = parse_evidence_typed(text, spec)
        assert ys == [2.0, 6.0, 10.0, 14.0, 18.0]


class TestJSONLParser:
    def test_basic_jsonl(self):
        text = "\n".join([
            '{"x": 1.0, "y": 2.0}',
            '{"x": 3.0, "y": 6.0}',
            '{"x": 5.0, "y": 10.0}',
            '{"x": 7.0, "y": 14.0}',
            '{"x": 9.0, "y": 18.0}',
        ])
        spec = EvidenceSpec(
            format=EvidenceFormat.JSON_LINES,
            columns=("x", "y"),
        )
        _, ys = parse_evidence_typed(text, spec)
        assert ys == [2.0, 6.0, 10.0, 14.0, 18.0]


class TestNoneFormat:
    def test_none_returns_empty(self):
        spec = EvidenceSpec(format=EvidenceFormat.NONE, columns=(), min_rows=0)
        xs, ys = parse_evidence_typed("anything goes here", spec)
        assert xs == []
        assert ys == []


# ── Validation guarantees ────────────────────────────────────────────────


class TestValidation:
    def test_finite_check_catches_nan(self):
        text = "1.0 2.0\n3.0 nan\n5.0 10.0\n7.0 14.0\n9.0 18.0\n"
        spec = EvidenceSpec(
            format=EvidenceFormat.WHITESPACE_TABULAR,
            columns=("x", "y"),
            require_finite=True,
        )
        # nan parses as float, should be caught by validator
        with pytest.raises(EvidenceContractError) as exc:
            parse_evidence_typed(text, spec)
        assert exc.value.code == "NON_FINITE"

    def test_monotone_check(self):
        text = "5.0 10.0\n1.0 2.0\n9.0 18.0\n3.0 6.0\n7.0 14.0\n"
        spec = EvidenceSpec(
            format=EvidenceFormat.WHITESPACE_TABULAR,
            columns=("x", "y"),
            require_monotone_in="x",
        )
        with pytest.raises(EvidenceContractError) as exc:
            parse_evidence_typed(text, spec)
        assert exc.value.code == "NON_MONOTONE"

    def test_error_codes_canonical(self):
        for code in EVIDENCE_ERROR_CODES:
            err = EvidenceContractError(code, None)
            assert err.code == code


# ── Round-trip spike (panel-recommended discriminator) ──────────────────


class TestRoundTripSpike:
    """Three-substrate spike per panel: same data through whitespace,
    markdown, and sweep_block parsers should produce bit-identical
    (xs, ys) when given equivalent format-rendered evidence."""

    def test_whitespace_vs_markdown_bit_identical(self):
        # Same data in two formats
        ws_text = "1.0 2.0\n3.0 6.0\n5.0 10.0\n7.0 14.0\n9.0 18.0\n"
        md_text = """| x | y |
|---|---|
| 1.0 | 2.0 |
| 3.0 | 6.0 |
| 5.0 | 10.0 |
| 7.0 | 14.0 |
| 9.0 | 18.0 |
"""
        ws_spec = EvidenceSpec(format=EvidenceFormat.WHITESPACE_TABULAR, columns=("x", "y"))
        md_spec = EvidenceSpec(format=EvidenceFormat.MARKDOWN_TABLE, columns=("x", "y"))
        ws_xs, ws_ys = parse_evidence_typed(ws_text, ws_spec)
        md_xs, md_ys = parse_evidence_typed(md_text, md_spec)
        assert ws_ys == md_ys
        assert ws_xs == md_xs

    def test_csv_vs_whitespace_bit_identical(self):
        csv_text = "x,y\n1.0,2.0\n3.0,6.0\n5.0,10.0\n7.0,14.0\n9.0,18.0\n"
        ws_text = "1.0 2.0\n3.0 6.0\n5.0 10.0\n7.0 14.0\n9.0 18.0\n"
        csv_spec = EvidenceSpec(format=EvidenceFormat.CSV_HEADER, columns=("x", "y"))
        ws_spec = EvidenceSpec(format=EvidenceFormat.WHITESPACE_TABULAR, columns=("x", "y"))
        csv_xs, csv_ys = parse_evidence_typed(csv_text, csv_spec)
        ws_xs, ws_ys = parse_evidence_typed(ws_text, ws_spec)
        assert csv_ys == ws_ys
        assert csv_xs == ws_xs


# ── Fail-loud: typed path catches what the heuristic silently dropped ──


class TestFailLoudSemantics:
    def test_format_mismatch_raises_not_silent(self):
        # Pure-prose evidence (no rows) declared as WHITESPACE_TABULAR
        text = "This is a discussion of the substrate.\nNo data rows here.\n"
        spec = EvidenceSpec(
            format=EvidenceFormat.WHITESPACE_TABULAR,
            columns=("x", "y"),
        )
        with pytest.raises(EvidenceContractError) as exc:
            parse_evidence_typed(text, spec)
        # Either PARSE_FAILED or ROW_FLOOR_VIOLATION; both are explicit
        assert exc.value.code in {"PARSE_FAILED", "ROW_FLOOR_VIOLATION"}
