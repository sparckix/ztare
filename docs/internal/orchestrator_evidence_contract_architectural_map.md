---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/evidence_contract.py + src/ztare/fit/parsers/__init__.py (Layer 2 typed evidence contract)
---

# orchestrator/evidence_contract.py + fit/parsers — architectural map

GP-157 v5.0 Layer 2 self-model. Mirrors L1 (`contract_table.py`) for the
substrate-evidence text format. Eliminates implicit-format sniffing
that the markdown-parser fix patched accidentally.

## Region map (evidence_contract.py)

region: evidence_format_enum  lines: 25-65  entry: class EvidenceFormat(Enum)
region: evidence_spec  lines: 68-115  entry: @dataclass(frozen=True)
region: evidence_contract_error  lines: 118-150  entry: class EvidenceContractError
region: get_evidence_spec  lines: 158-180  entry: def get_evidence_spec
region: list_evidence_formats  lines: 182-186  entry: def list_evidence_formats

## Function/method index

func: get_evidence_spec  sig: (rubric_data: Mapping[str, Any]) -> Optional[EvidenceSpec]
func: list_evidence_formats  sig: () -> tuple[str, ...]

## Companion: fit/parsers/__init__.py — per-format parsers + dispatch registry

Per-format parsers (one per EvidenceFormat enum value):
  - `_parse_whitespace` — WHITESPACE_TABULAR
  - `_parse_markdown` — MARKDOWN_TABLE (handles `|---|---|` separator + pipe delimiter)
  - `_parse_sweep_block` — SWEEP_BLOCK (2D `=== var2 = val ===` headers)
  - `_parse_csv` / `_parse_tsv` — delimited shared impl
  - `_parse_jsonl` — JSON Lines
  - `_parse_none` — substrates with no fittable evidence (returns empty)

Public dispatcher: `parse_evidence_typed(text, spec) -> ParsedEvidence`.
Raises `EvidenceContractError` on shape violation; never sniffs format.

Shared validator `_validate_parsed`:
  - row floor (spec.min_rows)
  - finite check (spec.require_finite)
  - monotone check (spec.require_monotone_in)

## Drift policy

Two paired arch maps registered: `evidence_contract` (the spec) and
`fit_parsers` (the registry). Run `make arch-validate` after edits.

## Wire-in (post-Task #71 ship)

- `scripts/validate_evidence.py:check #15` — when rubric has
  `evidence_contract` block, dispatch via spec; raises at seal time.
- `scripts/validate_evidence.py:check #16` — L1 Protocol boundary
  check (adapt) on the substrate's test_model.py at seal time.
- L1+L2 now together provide typed contracts at:
  - mutator → apparatus boundary (L1 SubstrateABI)
  - substrate evidence text (L2 EvidenceFormat)

## Migration plan

Existing substrates without `evidence_contract` block fall through to
the legacy auto-detection path in `fit_primitive.py` (markdown-pipe
heuristic + whitespace fallback). New substrates add the block at
ingestion time via generate_substrate.py (Task: extend ingestion).
After 10+ substrates ship the block, deprecate the heuristic.

## Format taxonomy

| Format | Used by | Example |
|---|---|---|
| WHITESPACE_TABULAR | gp090, gp091, gp077 | `1.3  1.6935` |
| MARKDOWN_TABLE | gp159, gp160, gp161 | `\| 1.3 \| 1.6935 \|` |
| SWEEP_BLOCK | grid-sweep substrates | `=== v=0.5 ===\n1.3 0.94` |
| CSV_HEADER / TSV_HEADER | exported research data | `x,y\n1.3,1.6935` |
| JSON_LINES | per-row metadata-rich | `{"x":1.3,"y":1.69}` |
| NONE | proof_target, audit, closed_form_constant | (skip fit) |
