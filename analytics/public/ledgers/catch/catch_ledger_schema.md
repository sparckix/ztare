# Catch Ledger Schema (`analytics/public/ledgers/catch/catch_ledger.jsonl`)

**Purpose**: Replace narrative catch counting (which inflated 40% then 14% per
the meta-audits in `catch_ledger_meta_audit_2026_05_08_evening.md` and
`anti_laundering_ledger_meta_audit_2026_05_07.md`) with structured artifact
pointers under SOX/PCAOB AS §1220 (concurring-partner pre-issuance review)
and AS §1215 (workpaper retention) discipline.

Per `business_framing_meta_darwin_strange_loop_2026_05_08.md` §7, this is the
SMALLEST first instantiation. Rotation calendar and expiration policy are
deferred until the ledger has ≥10 ratified rows.

## File format

`analytics/public/ledgers/catch/catch_ledger.jsonl` is append-only JSON Lines. One catch per line.
Validator: `scripts/validators/validate_catch_ledger.py`.

## Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `catch_id` | string | yes | `C-YYYY-MM-DD-NN` (e.g. `C-2026-05-08-04`) |
| `title` | string | yes | Short description (one sentence) |
| `author_agent` | string | yes | Stable agent ID or `human:operator` |
| `concurring_agent` | string | yes | Different agent ID (independence rule); `pending` allowed only with `status: pending` |
| `workpaper_paths` | array<string> | yes | Repo-relative paths to supporting artifacts; all must exist on disk |
| `load_bearing` | bool | yes | `true` only if classified LOAD-BEARING by the meta-audit (not BOOKKEEPING/DUPLICATE/DEFERRED) |
| `category` | string | yes | One of the 9 anti-pattern names (see below) |
| `fix_artifact` | string \| null | yes | Path to the fix (Lean file diff, docstring patch, retraction note) or `null` if rule-update only |
| `ratified_at` | string (ISO 8601) | yes | Use `mtime` of the catch's research note; do NOT fabricate |
| `status` | string | yes | `pending` \| `ratified` \| `retired` |
| `superseded_by` | string \| null | optional | Required if `status == retired`: the load-bearing parent's `catch_id` |

## Category enum (must match `org/anti-patterns/*.md`)

1. `citation_laundering`
2. `sorry_obligation_laundering`
3. `vocabulary_smuggling`
4. `pattern_1_rabbit_hole`
5. `narrative_inflation`
6. `cross_agent_monoculture`
7. `charity_grade_inflation`
8. `deployment_time_pre_spec_laundering`
9. `criterion_selection_rigging`

## Independence rule (concurring-partner analog)

`author_agent != concurring_agent`. The validator REJECTS any row where they
match. If the only available reviewer is the author, set
`concurring_agent: "pending"` and `status: "pending"`; the catch does NOT
count toward the ratified tally until a non-author signs.

## Counting rule

Architecture's catch tally counts ONLY rows with `status == "ratified"` and
`load_bearing == true`. `retired` rows preserve audit trail without
incrementing the count.

## Anti-laundering vigilance

- Atomic-catch test before logging: would a single Lean diff or single
  docstring rewrite have prevented all the named sub-classes? If yes, log
  ONE row, not many.
- Pre-register the `category` and `load_bearing` flag at logging time, not
  retroactively.
- `workpaper_paths` are MANDATORY and validated for on-disk existence —
  un-cashed-receivable catches cannot accrue inflation interest.
