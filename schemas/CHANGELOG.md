# Schema CHANGELOG

Tracks versioned changes to JSON schemas under `schemas/`. The kernel
is **substrate-agnostic** (per GP-191) and these schemas define the
structural invariants any org instantiation must honor.

The contract:

- **Breaking change** → bump the major version (`role.v1.schema.json` →
  `role.v2.schema.json`), keep the old file alive so existing yamls
  don't suddenly fail validation, and document the migration here.
- **Non-breaking field addition** → just add the field with
  `additionalProperties: true` already in place. Document here for
  forks who want to opt in.

---

## role.v1.schema.json

### v1.3 — 2026-05-02 (gp168 v3 run-2 findings)

Added optional `agent_rotation` block (finding F3). Rotates a role's
primary member across multiple agent CLIs (Claude / Codex / Gemini) on
a fixed cadence. Single-CLI-specific gaming patterns surface as
cross-CLI inconsistency in role outputs.

Fields (all required when `enabled: true`):
- `enabled` (bool, default false)
- `rotation_period_days` (integer, ≥1; typical 7)
- `members` (array of member.* identifiers, ≥2)
- `strategy` (enum: round_robin | random | stratified)
- `fallback_member` (member.* identifier, used when rotated CLI is
  unavailable)

Also documented in the schema description: warn-threshold jitter
(finding F2, ±10% per role/cli/date) and override-event recording
(finding F1, audit trail of principal-side subversions of the
exogenous-pressure clock).

**Migration**: none required — block is optional; legacy roles without
`agent_rotation` continue to use static primary-member binding.

### v1.2 — 2026-05-02 (RD-1.12 release)

Added optional `agent_utilization` block. Tracks Claude-Code / Codex /
Gemini-CLI session-window usage as a **capacity dimension orthogonal to
USD spend**. Consumed by `src/ztare/supervisor/agent_utilization_tracker.py`.
Warn-threshold trip emits a Telegram push (GP-128b) AND a damage signal
at `org/signals/damage/`.

Fields (all optional; module defaults apply if block is absent):
- `daily_cap_seconds` (number, default 10800 = 3h)
- `daily_cap_output_tokens` (integer, default 500000)
- `daily_cap_turn_count` (integer, default 200)
- `session_cap_seconds` (number, default 1800 = 30min)
- `absolute_ceiling_seconds` (number, default 21600 = 6h hard ceiling)
- `warn_threshold_frac` (number 0–1, default 0.80)

**Migration**: none required — block is optional, additive.

### v1.1 — 2026-04-27 (GP-168 OKR addendum)

Added optional `signs_gates`, `opened_date`, `opened_by` for audit-trail
purposes. No breaking changes.

**Migration**: none.

### v1.0 — 2026-04-15 (GP-072 ratification)

Initial schema. Defines:
- `schema_version` (const 1)
- `role_id`, `role_class`, `description`
- `authorized_paths`, `forbidden_paths`
- `delegates_to`, `escalates_to`
- `budget` block (USD caps)
- `mandate_path`, `sla`, `failure_mode`

`role_class` enum: authority | principal | manager | director |
specialist | reviewer.

`additionalProperties: true` at the top level — additive extensions
(per-domain fields like `research_taste_axes`) are allowed without
schema bump.

---

## Future: v2 (when needed)

A v2 bump is reserved for the first **breaking** change. Likely
candidates if/when they accrue:

- Promoting `agent_utilization` from optional to required for all
  non-authority roles (currently absent → defaults apply).
- Restructuring `budget` to nest currency (e.g., `{usd: {...}, eur: {...}}`)
  — only if multi-currency becomes a real requirement.
- Splitting `authorized_paths` / `forbidden_paths` into a typed
  `path_permissions: [{glob, mode}]` shape.

When v2 lands:
1. Ship `role.v2.schema.json` alongside v1.
2. The role loader picks the schema by `schema_version` field.
3. Provide a migration script under `scripts/migrate_role_schema_v1_to_v2.py`.
4. Document the migration here.
