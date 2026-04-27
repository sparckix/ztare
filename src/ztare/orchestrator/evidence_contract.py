"""GP-157 v5.0 Layer 2 — typed evidence contract.

Mirrors Layer 1's substrate-ABI design (see `contract_table.py`) for the
evidence.txt parseable shape. Eliminates the gp159-class implicit-format
sniffing that the markdown-table parser fix patched only by accident.

Per panel synthesis (Task #67 Expert 4 + the architectural review):
  - One stable enumeration of evidence shapes (Linux syscall-table discipline).
  - Per-format parsers, dispatched via registry.
  - Validation at seal time: declared format + actual data shape.
  - Fail-loud on mismatch (`EvidenceContractError`), no implicit fallback.

The substrate declares its format in rubric.json's `evidence_contract`
block (sibling of `cage_meta`). The fit primitive's parser becomes a
thin shell that dispatches via the registry instead of sniffing pipes.

Companion: `src/ztare/fit/parsers/` (per-format parsers + registry impl).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional


class EvidenceFormat(Enum):
    """Stable enumeration of evidence.txt parseable shapes.

    Linux-syscall discipline: monotonic numbering, never renumbered.
    Adding a new format = appending a new enum value + a parser.
    """

    WHITESPACE_TABULAR = 1
    """Plain whitespace-separated rows: `x  y` or `x  y  z`. Header
    rows (non-numeric first token) auto-skipped. Used by gp090,
    gp091, gp077-style integer / scaling substrates."""

    MARKDOWN_TABLE = 2
    """Markdown table format: `| x | y |` with `|---|---|` separator.
    Used by gp159 family (operator-friendly evidence with column headers)."""

    SWEEP_BLOCK = 3
    """Sweep-block 2D format: `=== var2 = val ===` section headers,
    body rows have `var1 target`. Used by grid-sweep experiments."""

    CSV_HEADER = 4
    """Comma-separated with named header row. Common in shipped
    research data exports."""

    TSV_HEADER = 5
    """Tab-separated with named header row. Distinct from
    WHITESPACE_TABULAR in that columns are explicitly named."""

    JSON_LINES = 6
    """One JSON object per row. Used when evidence has rich
    per-row metadata (e.g. measurement uncertainty, source citation)."""

    NONE = 7
    """Substrate has no fittable tabular evidence. Used by
    closed_form_constant (PSLQ), proof_target (Lean), audit
    substrates whose evidence is prose + Lean snippets / research
    artifacts. Fit-primitive engagement is silently skipped."""


@dataclass(frozen=True)
class EvidenceSpec:
    """Frozen specification for one substrate's evidence shape.

    Immutable after construction — substrate registration writes the
    spec into the rubric's `evidence_contract` block at substrate-
    construction time and never mutates afterward.
    """

    format: EvidenceFormat
    """The format identifier. Determines which parser dispatches."""

    columns: tuple[str, ...]
    """Ordered column names (last is target). For NONE, empty tuple."""

    independent_vars: tuple[str, ...] = ()
    """Subset of columns[:-1] that are independent variables. Tells
    the fit primitive which columns to treat as `x` vs the y target."""

    delimiter: Optional[str] = None
    """Explicit delimiter. None for whitespace; `|` for markdown;
    `,` for CSV; `\\t` for TSV. Per-format parsers may infer from
    format if unset."""

    header_skip: int = 0
    """Number of leading rows to drop before parsing data."""

    block_header_pattern: Optional[str] = None
    """For SWEEP_BLOCK: regex matching the `=== var = val ===` header.
    Default per-format pattern used when None."""

    min_rows: int = 5
    """Minimum number of valid data rows the parser must produce.
    Below this, validation raises."""

    require_finite: bool = True
    """If True, every parsed value must be a finite float (no NaN, no inf)."""

    require_monotone_in: Optional[str] = None
    """If set, parsed rows must be monotone in this column name. Useful
    catching sorted-vs-unsorted invariants."""

    docstring: str = ""
    """Free-form description for evidence-template rendering."""


class EvidenceContractError(Exception):
    """One canonical error class for L2 violations.

    Codes (used in error.code attribute):
      - NO_DECLARATION: rubric lacks `evidence_contract` block
      - FORMAT_UNREGISTERED: declared format not in EVIDENCE_PARSER_REGISTRY
      - PARSE_FAILED: parser couldn't extract any rows
      - ROW_FLOOR_VIOLATION: parsed fewer rows than min_rows
      - NON_NUMERIC_CELL: non-numeric value in numeric column
      - NON_FINITE: NaN/inf encountered when require_finite=True
      - NON_MONOTONE: data not monotone in require_monotone_in column
      - COLUMN_COUNT_MISMATCH: row column count doesn't match spec.columns
    """

    def __init__(
        self,
        code: str,
        spec: Optional["EvidenceSpec"] = None,
        *,
        observed: Any = None,
        remediation: str = "",
    ) -> None:
        self.code = code
        self.spec = spec
        self.observed = observed
        self.remediation = remediation
        format_name = spec.format.name if spec else "<unknown>"
        msg = (
            f"EvidenceContractError[{code}] for format={format_name}: "
            f"observed={observed!r}; remediation={remediation!r}"
        )
        super().__init__(msg)


EVIDENCE_ERROR_CODES: frozenset[str] = frozenset({
    "NO_DECLARATION",
    "FORMAT_UNREGISTERED",
    "PARSE_FAILED",
    "ROW_FLOOR_VIOLATION",
    "NON_NUMERIC_CELL",
    "NON_FINITE",
    "NON_MONOTONE",
    "COLUMN_COUNT_MISMATCH",
})


# ── Public lookup helpers ────────────────────────────────────────────────


def get_evidence_spec(rubric_data: Mapping[str, Any]) -> Optional[EvidenceSpec]:
    """Read the substrate's declared EvidenceSpec from rubric.json.

    Returns None if the rubric lacks an `evidence_contract` block.
    Caller decides whether to raise NO_DECLARATION (strict mode) or
    fall back to legacy auto-detection (legacy substrates).
    """
    block = rubric_data.get("evidence_contract")
    if not isinstance(block, Mapping):
        return None
    fmt_name = (block.get("format") or "").strip()
    try:
        fmt = EvidenceFormat[fmt_name]
    except (KeyError, TypeError):
        return None
    cols = tuple(block.get("columns") or ())
    indep = tuple(block.get("independent_vars") or cols[:-1])
    return EvidenceSpec(
        format=fmt,
        columns=cols,
        independent_vars=indep,
        delimiter=block.get("delimiter"),
        header_skip=int(block.get("header_skip", 0)),
        block_header_pattern=block.get("block_header_pattern"),
        min_rows=int(block.get("min_rows", 5)),
        require_finite=bool(block.get("require_finite", True)),
        require_monotone_in=block.get("require_monotone_in"),
        docstring=block.get("docstring") or "",
    )


def list_evidence_formats() -> tuple[str, ...]:
    """All registered EvidenceFormat names. Useful for seal-time lints."""
    return tuple(f.name for f in EvidenceFormat)
