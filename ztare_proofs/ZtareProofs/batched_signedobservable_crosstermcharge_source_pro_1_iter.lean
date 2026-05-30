import ztare_proofs.ZtareProofs.ns_leray_gain_tax_trackb_obligation

namespace ZtareProofs.NS

theorem crossTermCharged_of_fully_charged_proj
    {C : SignedObservable}
    (h : GlobalSignedObservableFullyCharged C) :
    C.crossTermCharged := by
  exact h.2.2.2.2.1

end ZtareProofs.NS
