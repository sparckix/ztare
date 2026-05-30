import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem macroscopicFlatTorusClockSource_is_unfalsifiable
    (R : GP216BridgeCompositionReceipt) :
    IsEmpty (MacroscopicFlatTorusClockSourceFalsifier R.macroscopicFlatTorusClockSource) := by
  rw [← not_nonempty_iff]
  exact gp216_no_macroscopic_flat_torus_clock_source_falsifier R

end ZtareProofs.NS
