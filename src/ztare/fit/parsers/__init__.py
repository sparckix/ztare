"""GP-157 v5.0 Layer 2 — per-format evidence parsers + dispatch registry.

Per-format parsers each have signature:
    `parse_<format>(text: str, spec: EvidenceSpec) -> ParsedEvidence`

`ParsedEvidence` is a tuple `(xdata: list[list[float]], ydata: list[float])`
matching the legacy `parse_evidence_for_fitting` return shape, so the fit
primitive can drop in either path.

Parsers raise `EvidenceContractError` on shape violations. Validation
(row floor, finite, monotone) is shared across formats via `_validate`.
"""

from __future__ import annotations

from typing import Callable

from src.ztare.orchestrator.evidence_contract import (
    EvidenceFormat,
    EvidenceSpec,
    EvidenceContractError,
)

ParsedEvidence = tuple[list[list[float]], list[float]]
ParserFn = Callable[[str, EvidenceSpec], ParsedEvidence]


def _validate_parsed(
    xs: list[list[float]],
    ys: list[float],
    spec: EvidenceSpec,
) -> None:
    """Shared post-parse validation. Raises EvidenceContractError on any
    violation per spec. Called by every parser before returning."""
    import math as _math

    if not ys:
        raise EvidenceContractError(
            "PARSE_FAILED",
            spec,
            observed="0 rows extracted",
            remediation="check evidence.txt format matches declared spec",
        )

    if len(ys) < spec.min_rows:
        raise EvidenceContractError(
            "ROW_FLOOR_VIOLATION",
            spec,
            observed=f"{len(ys)} rows < min_rows={spec.min_rows}",
            remediation="add data rows or lower min_rows",
        )

    if spec.require_finite:
        for i, y in enumerate(ys):
            if _math.isnan(y) or _math.isinf(y):
                raise EvidenceContractError(
                    "NON_FINITE",
                    spec,
                    observed=f"y[{i}]={y}",
                    remediation="evidence rows must be finite floats",
                )
        for col_idx, col in enumerate(xs):
            for row_idx, x in enumerate(col):
                if _math.isnan(x) or _math.isinf(x):
                    raise EvidenceContractError(
                        "NON_FINITE",
                        spec,
                        observed=f"xs[{col_idx}][{row_idx}]={x}",
                        remediation="evidence rows must be finite floats",
                    )

    if spec.require_monotone_in:
        try:
            col_idx = list(spec.columns[:-1]).index(spec.require_monotone_in)
        except ValueError:
            return
        col = xs[col_idx]
        is_monotone = all(col[i] <= col[i + 1] for i in range(len(col) - 1)) or \
                      all(col[i] >= col[i + 1] for i in range(len(col) - 1))
        if not is_monotone:
            raise EvidenceContractError(
                "NON_MONOTONE",
                spec,
                observed=f"column {spec.require_monotone_in!r} not monotone",
                remediation="sort evidence by independent variable, or relax require_monotone_in",
            )


def _parse_whitespace(text: str, spec: EvidenceSpec) -> ParsedEvidence:
    """Plain whitespace-separated rows. Header rows (non-numeric first
    token) auto-skipped. Comments starting with `#` ignored."""
    n_indep = len(spec.independent_vars) or max(1, len(spec.columns) - 1)
    xs: list[list[float]] = [[] for _ in range(n_indep)]
    ys: list[float] = []

    for raw in text.splitlines()[spec.header_skip:]:
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("==="):
            continue
        parts = line.split()
        if len(parts) < n_indep + 1:
            continue
        try:
            row_x = [float(parts[i]) for i in range(n_indep)]
            y = float(parts[n_indep])
        except ValueError:
            continue  # header or malformed
        for i, v in enumerate(row_x):
            xs[i].append(v)
        ys.append(y)

    _validate_parsed(xs, ys, spec)
    return xs, ys


def _parse_markdown(text: str, spec: EvidenceSpec) -> ParsedEvidence:
    """Markdown table: `| x | y |` rows, `|---|---|` separator dropped."""
    n_indep = len(spec.independent_vars) or max(1, len(spec.columns) - 1)
    xs: list[list[float]] = [[] for _ in range(n_indep)]
    ys: list[float] = []

    for raw in text.splitlines()[spec.header_skip:]:
        line = raw.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        inner = line.strip("|").strip()
        # Reject pure separator rows like `|---|---|`
        if all(set(p.strip()) <= set("-:= \t") for p in inner.split("|")):
            continue
        parts = [p.strip() for p in inner.split("|") if p.strip()]
        if len(parts) < n_indep + 1:
            continue
        try:
            row_x = [float(parts[i]) for i in range(n_indep)]
            y = float(parts[n_indep])
        except ValueError:
            continue  # header row
        for i, v in enumerate(row_x):
            xs[i].append(v)
        ys.append(y)

    _validate_parsed(xs, ys, spec)
    return xs, ys


def _parse_sweep_block(text: str, spec: EvidenceSpec) -> ParsedEvidence:
    """Sweep-block 2D format: `=== var2 = val ===` headers separate
    blocks of `var1 target` rows. Requires exactly 2 independent vars."""
    import re as _re
    if len(spec.independent_vars) != 2:
        raise EvidenceContractError(
            "COLUMN_COUNT_MISMATCH",
            spec,
            observed=f"SWEEP_BLOCK requires 2 independent_vars, got {len(spec.independent_vars)}",
            remediation="use WHITESPACE_TABULAR for 1D substrates",
        )
    pattern = spec.block_header_pattern or r"===\s*(\w+)\s*=\s*([\d.eE+-]+)\s*==="
    block_re = _re.compile(pattern)

    xs: list[list[float]] = [[], []]
    ys: list[float] = []
    current_var2: float | None = None

    for raw in text.splitlines()[spec.header_skip:]:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = block_re.match(line)
        if m:
            try:
                current_var2 = float(m.group(2))
            except (ValueError, IndexError):
                current_var2 = None
            continue
        if current_var2 is None:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            x1 = float(parts[0])
            y = float(parts[1])
        except ValueError:
            continue
        xs[0].append(x1)
        xs[1].append(current_var2)
        ys.append(y)

    _validate_parsed(xs, ys, spec)
    return xs, ys


def _parse_delimited(text: str, spec: EvidenceSpec, delim: str) -> ParsedEvidence:
    """Common implementation for CSV / TSV / explicit-delimiter formats."""
    n_indep = len(spec.independent_vars) or max(1, len(spec.columns) - 1)
    xs: list[list[float]] = [[] for _ in range(n_indep)]
    ys: list[float] = []

    for raw in text.splitlines()[spec.header_skip:]:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(delim)]
        if len(parts) < n_indep + 1:
            continue
        try:
            row_x = [float(parts[i]) for i in range(n_indep)]
            y = float(parts[n_indep])
        except ValueError:
            continue  # header row
        for i, v in enumerate(row_x):
            xs[i].append(v)
        ys.append(y)

    _validate_parsed(xs, ys, spec)
    return xs, ys


def _parse_csv(text: str, spec: EvidenceSpec) -> ParsedEvidence:
    return _parse_delimited(text, spec, ",")


def _parse_tsv(text: str, spec: EvidenceSpec) -> ParsedEvidence:
    return _parse_delimited(text, spec, "\t")


def _parse_jsonl(text: str, spec: EvidenceSpec) -> ParsedEvidence:
    """One JSON object per row. Each object must contain the columns
    declared in `spec.columns`."""
    import json as _json
    n_indep = len(spec.independent_vars) or max(1, len(spec.columns) - 1)
    xs: list[list[float]] = [[] for _ in range(n_indep)]
    ys: list[float] = []
    target_col = spec.columns[-1] if spec.columns else "y"

    for raw in text.splitlines()[spec.header_skip:]:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = _json.loads(line)
        except _json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        try:
            for i, col in enumerate(spec.independent_vars or spec.columns[:-1]):
                xs[i].append(float(obj[col]))
            ys.append(float(obj[target_col]))
        except (KeyError, ValueError, TypeError):
            continue

    _validate_parsed(xs, ys, spec)
    return xs, ys


def _parse_none(text: str, spec: EvidenceSpec) -> ParsedEvidence:
    """NONE format: substrate has no fittable evidence. Returns empty
    arrays. Caller (fit primitive dispatch) treats this as 'skip fit'."""
    return [], []


# ── Registry ─────────────────────────────────────────────────────────────


EVIDENCE_PARSER_REGISTRY: dict[EvidenceFormat, ParserFn] = {
    EvidenceFormat.WHITESPACE_TABULAR: _parse_whitespace,
    EvidenceFormat.MARKDOWN_TABLE: _parse_markdown,
    EvidenceFormat.SWEEP_BLOCK: _parse_sweep_block,
    EvidenceFormat.CSV_HEADER: _parse_csv,
    EvidenceFormat.TSV_HEADER: _parse_tsv,
    EvidenceFormat.JSON_LINES: _parse_jsonl,
    EvidenceFormat.NONE: _parse_none,
}


def parse_evidence_typed(text: str, spec: EvidenceSpec) -> ParsedEvidence:
    """Public dispatcher: format-driven, no sniffing. Raises
    EvidenceContractError on missing parser or shape violation."""
    parser = EVIDENCE_PARSER_REGISTRY.get(spec.format)
    if parser is None:
        raise EvidenceContractError(
            "FORMAT_UNREGISTERED",
            spec,
            observed=spec.format.name,
            remediation="add a parser to EVIDENCE_PARSER_REGISTRY",
        )
    return parser(text, spec)
