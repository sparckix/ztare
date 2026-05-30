# Pattern Catalog Index

**Canonical source-of-truth for `PATTERN-XXX` identifiers.**

The `id:` frontmatter field in each file under `org/patterns/*.md` is the
**authoritative** namespace. Any other artifact (architecture index,
dispatch prompts, code, research notes) that references a `PATTERN-XXX`
ID must agree with this table. Disagreements are
ANTI-PATTERN-003 (vocabulary smuggling, sub-mode: id-namespace drift)
and should be patched at the consumer site, never by mutating the
source-of-truth file.

**Discovered**: 2026-05-08 from a session-mining catch (a990c47e
empirical-test agent surfaced "PATTERN-008 vs PATTERN-010" disagreement
between a dispatch prompt and the file frontmatter). Audit then surfaced
8 of 11 pattern ids out-of-sync between `org/patterns/` and
`analytics/architecture_index.jsonl`, `architecture_index.jsonl` was
patched to match the canonical ids; future drift should be patched the
same direction.

## Canonical ID table

| ID | File | Name |
|---|---|---|
| PATTERN-001 | `org/patterns/pattern_1_friction_debate.md` | friction_debate |
| PATTERN-002 | `org/patterns/darwin_idea_killer.md` | darwin_idea_killer |
| PATTERN-003 | `org/patterns/reducer.md` | reducer |
| PATTERN-004 | `org/patterns/vocabulary_quarantine.md` | vocabulary_quarantine |
| PATTERN-005 | `org/patterns/falsifiable_asymmetry.md` | falsifiable_asymmetry |
| PATTERN-006 | `org/patterns/tautology_trap.md` | tautology_trap_detector |
| PATTERN-007 | `org/patterns/smuggling_audit.md` | smuggling_audit |
| PATTERN-008 | `org/patterns/three_leg_verification.md` | three_leg_verification |
| PATTERN-009 | `org/patterns/independent_cas_verification.md` | independent_cas_verification |
| PATTERN-010 | `org/patterns/business_framing.md` | business_framing |
| PATTERN-011 | `org/patterns/swarm_dispatch.md` | swarm_dispatch |
| PATTERN-028 | `org/patterns/recursive_tool_depth_loop.md` | recursive_tool_depth_loop |

## Anti-pattern catalog

See `org/anti-patterns/INDEX.md` for the parallel `ANTI-PATTERN-XXX`
namespace.

## Drift-detection protocol

Any consumer that references a `PATTERN-XXX` ID:

1. Validates the id against this table (or against the `id:` frontmatter
   in the source file).
2. On mismatch, patches the consumer site (prompt, code, JSONL row,
   research note) and records a catch under ANTI-PATTERN-003 sub-mode
   `id_namespace_drift`.
3. Never mutates the source-of-truth file to match the consumer.

The `scripts/render_architecture_index.py` renderer should validate that
each `PATTERN-XXX-*` row in `analytics/architecture_index.jsonl` matches
the `id:` frontmatter at the file path it points to. (Future: bake the
check in.)

## Versioning

When a new pattern is minted (≥2 N-instances per the falsifiable-
asymmetry test), increment to the next free PATTERN-XXX id in this
table FIRST, then create the file with that id in frontmatter, then
add a row to `analytics/architecture_index.jsonl` with the same id.
