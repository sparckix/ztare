import ztare_proofs.ZtareProofs.ns_leray_gain_tax_trackb_obligation

namespace ZtareProofs.NS

theorem crossTermCharged_of_fully_charged
    (C : SignedObservable)
    (h : GlobalSignedObservableFullyCharged C) :
    C.crossTermCharged := by
  rcases h with ⟨_, _, _, _, h_cross, _⟩
  exact h_cross

end ZtareProofs.NS
