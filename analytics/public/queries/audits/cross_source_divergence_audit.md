# Cross-Source Divergence Audit (ACRR/PECVP kernel)

_Generated 2026-05-09T23:24:02.365712+00:00_  
_Sources loaded:_ 5/5  _Entities tracked:_ 1119  _Single-source flags:_ 933  _Multi-source disagreements:_ 10  _Catch-demotion-drift hits:_ 0

**Kernel of the substrate-produced ACRR/PECVP primitive.** Full ACRR/PECVP requires multi-host isolated infrastructure + crypto attestation (over-engineering for solo-operator setup). This kernel applies the divergence-check pattern to mining outputs we already produce.

## Multi-source kind disagreements (semantic drift candidates)

| Entity | Sources | Kinds per source |
|---|---:|---|
| `research_areas/private/seams/protocol/GP-075_rubric_for_unkn` | 3 | recursive_gain: one_shot_artifact; process_catalog: unclassified |
| `research_areas/private/seams/engine/mutator/GP-030_determini` | 3 | recursive_gain: one_shot_artifact; process_catalog: unclassified |
| `research_areas/private/seams/charters/GP-154_T14_v4_external` | 3 | recursive_gain: one_shot_artifact; process_catalog: unclassified |
| `scripts/scaffold_rubric.py` | 2 | process_catalog: one_shot; recursive_gain: one_shot_artifact |
| `scripts/upgrade_mlh_rubrics.py` | 2 | recursive_gain: one_shot_artifact; process_catalog: unclassified |
| `research_areas/private/seams/substrates/planck/GP-023_planck` | 2 | recursive_gain: load_bearing_seam; process_catalog: unclassified |
| `research_areas/private/seams/audits/2026_04_25/GP-163d_unifi` | 2 | recursive_gain: load_bearing_seam; process_catalog: unclassified |
| `research_areas/private/seams/engine/GP-154_learning_mechanic` | 2 | recursive_gain: load_bearing_seam; process_catalog: unclassified |
| `research_areas/private/seams/mission/GP-140_ztare_discovery_` | 2 | recursive_gain: load_bearing_seam; process_catalog: unclassified |
| `research_areas/private/seams/engine/GP-216_theory_building_o` | 2 | process_catalog: recently_authored; recursive_gain: load_bearing_seam |

## Single-source flags (potential coverage gaps)

| Entity | Sole source | Tag |
|---|---|---|
| `R24` | `cross_audit` | `flagged` |
| `GP-130` | `cross_audit` | `flagged` |
| `GP-140` | `cross_audit` | `flagged` |
| `GP-173` | `cross_audit` | `flagged` |
| `GP-188` | `cross_audit` | `flagged` |
| `GP-192` | `cross_audit` | `flagged` |
| `R21` | `cross_audit` | `flagged` |
| `analytics/queries/agent_panels/20260506T161007Z_ns_trackb_so` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161007Z_ns_trackb_so` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161007Z_ns_trackb_so` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161007Z_ns_trackb_so` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161007Z_ns_trackb_so` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161007Z_ns_trackb_so` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161007Z_ns_trackb_so` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161557Z_ns_trackb_li` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161557Z_ns_trackb_li` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161557Z_ns_trackb_li` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161557Z_ns_trackb_li` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161557Z_ns_trackb_li` | `process_catalog` | `recently_authored` |
| `analytics/queries/agent_panels/20260506T161557Z_ns_trackb_li` | `process_catalog` | `recently_authored` |

