# Ghost-Gram Falsifier Patterns - Worker 3

Purpose: adversarial patterns for generated profile/Lipschitz blocks where local quartic/root bounds can be satisfied while the continuum defect or self-tax measure vanishes, moves, or detaches. This is a tautology-prevention checklist, not a proof plan.

## Highest-risk gaps

1. `GG-W3-01-zero-defect-measure-ghost`
   Local generated-block root receipts do not force a nonzero measure-valued defect floor. Existing `LeraySelfTaxOutputLimitPriceReceipt` fields ensure included floors are priced, but zero floors can still pass.

2. `GG-W3-02-generated-block-self-tax-stream-detach`
   `TrackBProfileLipschitzSourceCoupling` ties profile family to the generated Lipschitz block, and `ProfileFamilySelfTaxStreamIdentityCompatibility` can tie profile payoff/price to a stream, but there is still a sharp guard to demand: the exact generated block must be the exact self-tax stream used downstream.

3. `GG-W3-03-root-ledger-local-but-continuum-defect-detached`
   `QuarticSurvivalRootDefectLedgerMatchReceipt` blocks local root/profit detachment, but it does not by itself connect `thresholdDefectGapAtRoot B` to `LeraySelfTaxRelaxedOutputDefectLedger` floors.

4. `GG-W3-07-scalar-amplitude-receipt-with-undercharged-observable`
   Preferred endpoints now use `QuarticSurvivalAmplitudeObservableSource` and `GlobalSignedObservableFullyCharged`, but any legacy scalar-only `QuarticSurvivalAmplitudeProjectionReceipt` route remains a ghost lane.

## Existing receipts that matter

- Local quartic/root: `QuarticSurvivalProjectionReceipt`, `QuarticSurvivalAmplitudeProjectionReceipt`, `QuarticSurvivalThresholdRootObservableSource`, `QuarticSurvivalAmplitudeObservableSource`.
- Local detachment falsifiers: `QuarticSurvivalProjectionGuardFalsifier`, `QuarticSurvivalAmplitudeProjectionFalsifier`, `QuarticSurvivalAmplitudeObservableSourceFalsifier`, `QuarticSurvivalRootDefectLedgerMatchFalsifier`.
- Profile/Lipschitz coupling: `TrackBProfileLipschitzSourceCoupling`, `TrackBProfileLipschitzGeneratedBlockSourceReady`, `TrackBProfileLipschitzGeneratedBlockHandoffSourceReady`.
- Self-tax output source: `LeraySelfTaxMeasureValuedDefectSource`, `LeraySelfTaxOutputLimitPriceReceipt`, `LeraySelfTaxOutputLimitPassageAuditedSourceReceipt`, `LeraySelfTaxOutputDerivedStreamReceipt`.
- Gram/OT import: `OTGramImportCalibration`, `OTGramLSCImportReceipt`, `OTActionLSCButGramGapFalsifier`.

## Suggested next guard names

- `GeneratedBlockSelfTaxStreamIdentityReceipt`
- `GeneratedRootDefectOutputFloorReceipt`
- `same_tail_defect_tightness_of_output_limit_passage`
- `generated_block_component_floor_compatibility`

The key bar: do not accept local `FullLedgerNoSurvivor` closure unless the generated block, survival observable, root-defect ledger, self-tax stream, and continuum relaxed-output defect source are all the same predeclared object path.
