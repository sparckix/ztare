# Failure Cluster Analysis

Generated: 2026-05-09T19:23:47.985047
Total failures: 18

## Single-axis distributions

### By category

- llm_refused: 7
- patch_class_mismatch: 4
- unverifiable_other: 3
- endpoint_unbound: 3
- trivial_degenerate: 1

### By patch_class

- instance_with_evidence: 12
- source_provenance_bridge: 6

### By type_head

- Obligation: 12
- Source: 6

## Clusters (size ≥ 2)

### 3x: type_head=Obligation, class=instance_with_evidence, category=unverifiable_other

- TrackBProfileLipschitzClayObligation::continuation (2026-05-06T03:40:08)
- TrackBProfileLipschitzClayObligation::continuation (2026-05-06T03:40:47)
- TrackBProfileLipschitzControlObligation::generated_quartic_survival_projection (2026-05-06T04:16:01)


### 3x: type_head=Obligation, class=instance_with_evidence, category=llm_refused

- TrackBProfileLipschitzControlObligation::generated_quartic_survival_projection (2026-05-06T04:00:15)
- TrackBProfileLipschitzControlObligation::generated_quartic_survival_projection (2026-05-06T04:12:54)
- TrackBProfileLipschitzControlObligation::generated_quartic_survival_projection (2026-05-06T04:15:01)

  **Hypothesis:** the LLM correctly identifies missing primitives. Run `cannot_patch_harvester.py` to extract the named missing objects and add them to the spine.

### 3x: type_head=Obligation, class=source_provenance_bridge, category=patch_class_mismatch

- TrackBProfileLipschitzControlObligation::generated_quartic_survival_amplitude_observable_source (2026-05-06T22:35:15)
- TrackBProfileLipschitzControlObligation::generated_quartic_survival_amplitude_observable_source (2026-05-07T01:20:34)
- TrackBProfileLipschitzControlObligation::generated_quartic_survival_amplitude_observable_source (2026-05-07T06:45:00)


### 3x: type_head=Source, class=instance_with_evidence, category=endpoint_unbound

- GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource::projected_compactness_measure_valued_source (2026-05-07T14:29:36)
- GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource::projected_compactness_measure_valued_source (2026-05-07T14:30:30)
- GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource::projected_compactness_measure_valued_source (2026-05-07T14:31:47)

  **Hypothesis:** the resolved set for type_head=`Source` is missing some constructor / lemma the LLM keeps reaching for. Action: dump the actual stderr to find the unresolved name; add to the pack's resolved set.

### 2x: type_head=Obligation, class=source_provenance_bridge, category=llm_refused

- TrackBProfileLipschitzControlObligation::generated_quartic_survival_projection (2026-05-06T03:59:57)
- TrackBProfileDecompositionObligation::threshold_defect_of_family_no_arbitrage (2026-05-06T04:01:12)

  **Hypothesis:** the LLM correctly identifies missing primitives. Run `cannot_patch_harvester.py` to extract the named missing objects and add them to the spine.

### 2x: type_head=Source, class=instance_with_evidence, category=llm_refused

- GP216ContinuumProjectedSelectedBranchMeasureValuedAuditedOutputSource::projected_measure_valued_source (2026-05-07T14:06:44)
- LeraySelfTaxCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource::compactness_mv_source_of_global (2026-05-07T14:46:00)

  **Hypothesis:** the LLM correctly identifies missing primitives. Run `cannot_patch_harvester.py` to extract the named missing objects and add them to the spine.
