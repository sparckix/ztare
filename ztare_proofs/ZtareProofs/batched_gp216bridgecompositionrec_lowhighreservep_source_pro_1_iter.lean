import ztare_proofs.ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

def GP216BridgeCompositionReceipt.lowHighReservePDESource_from_continuation_bundle
    (R : GP216BridgeCompositionReceipt) :
    GP216LowHighReservePDESourceBundle R.continuationSource.handoff :=
  R.continuationSource.reservePDESource

end ZtareProofs.NS
