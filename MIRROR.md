# MIRROR.md — Private → Public Document Map

Every public-facing doc that summarizes private authoritative content must be listed here.
When a private source changes, check this table and update or re-sync the corresponding public derivative.

**Last reviewed:** 2026-04-19

---

## How to use this file

1. When you edit a private authoritative doc → look it up in the **Private (authoritative)** column → update or flag the corresponding public derivative.
2. When a public doc feels stale → look it up in the **Public derivative** column → read the private source → resync.
3. Staleness trigger = listed Trigger event has occurred since Last synced date.

---

## Map

| Private (authoritative) | Public derivative | Last synced | Staleness trigger |
|---|---|---|---|
| `research_areas/private/philosophy/three_legs_of_ztare.md` | *(none yet — create `docs/concepts/three_legs.md` when paper5 ships)* | — | Paper 5 first public draft |
| `research_areas/private/philosophy/operational_manual_substrate_construction.md` | `docs/guides/experiment_cookbook.md` | 2026-04-18 | `make seal` workflow changes; new checklist step added |
| `research_areas/private/papers/paper1.md` + `paper2.md` + `paper3.md` | `docs/concepts/epistemic_principles.md` | 2026-04-17 (v0.2) | Paper revision / new principle elevation |
| `research_areas/private/EXPERIMENT_TRACK_RECORD.md` | `research_areas/EXPERIMENT_TRACK_RECORD.md` | ongoing (per-experiment) | Experiment close; visibility-three-test pass |
| `research_areas/private/ZTARE_BOARD.md` | `research_areas/ZTARE_BOARD.md` | ongoing | Seam promoted public |
| `research_areas/private/distribution/field_manual_v1.md` | `config/renderers/field_manual.md` | unknown — verify | Field manual revision |
| `research_areas/private/gate_library/` | `docs/concepts/architecture.md` (gate types section) | unknown — verify | New gate type added |
| `research_areas/private/philosophy/cognitive_gym.md` | *(none — internal only until paper 5 ships; Torvalds move: will go public same day as SSRN Paper 5 URL resolves 200 OK)* | 2026-04-19 (§12 gag order postmortem added) | Paper 5 SSRN live |
| `research_areas/private/philosophy/reflexive_engineering_primitives.md` | `docs/concepts/reflexive_engineering.md` | 2026-04-20 (initial promotion) | New primitive added to catalog; GP-102 spec revised |
| `research_areas/private/specs/active/apparatus/instrumentation/GP-102_reflexive_primitive_discovery_spec.md` | `docs/guides/reflexive_audit_workflow.md` | 2026-04-20 (initial promotion) | GP-102 spec revised; CLI flags change; new failure mode added |
| `research_areas/private/specs/active/GP-072_role_separation_sandbox_construction_spec.md` | `docs/guides/experiment_cookbook.md` §4 + `AGENTS.md` MANDATORY rule | 2026-04-18 | GP-072 spec revision |

---

## Staleness signals to watch

- `docs/concepts/epistemic_principles.md` (v0.2) was last synced 2026-04-17 from papers 1–4 + postmortem registry. It is **not** the canonical source — it is a derivative. Any new principle elevated from the postmortem registry must be added here **and** flagged for paper5 as a potential section.
- `config/renderers/field_manual.md` — sync date unknown. Operator should verify against `distribution/field_manual_v1.md` before any field-manual-facing delivery.
- `docs/concepts/architecture.md` gate type section may lag `research_areas/private/gate_library/` — see map row above.

---

## Docs with no private counterpart (standalone public docs)

These are not derivatives — they own their own content and do not need mirroring:

| File | Owner | Notes |
|---|---|---|
| `docs/concepts/architecture.md` | Public | Gate type section may lag private gate_library — see map row above |
| `docs/guides/workflow.md` | Public | Route for external researchers; kept current with loop CLI changes |
| `docs/guides/for_researchers.md` | Public | Audience: independent replicators |
| `docs/concepts/glossary.md` | Public | Maintained separately; flag undefined terms |
| `docs/guides/experiment_cookbook.md` | Public | Canonical pre-run guide; `make seal` as centerpiece |
| `docs/reference/make_targets.md` | Generated | Auto-generated from `make help`; regenerate when Makefile changes |
| `AGENTS.md` | Public | Agent instructions; both Claude Code and Codex read this |
| `README.md` | Public | Entry point |

---

## Amendment rule

When a new private-to-public relationship is created, add a row here in the same session. Do not let the map drift behind reality. If a derivative doc is deprecated or merged, remove or update its row.
