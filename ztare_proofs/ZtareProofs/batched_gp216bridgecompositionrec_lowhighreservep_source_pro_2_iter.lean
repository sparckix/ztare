import ztare_proofs.ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

def gp216_low_high_reserve_pde_source_of_continuation
    (continuationSource : GP216ContinuationSourceBundle) :
    GP216LowHighReservePDESourceBundle continuationSource.handoff :=
  continuationSource.lowHighReservePDESource

end ZtareProofs.NS
