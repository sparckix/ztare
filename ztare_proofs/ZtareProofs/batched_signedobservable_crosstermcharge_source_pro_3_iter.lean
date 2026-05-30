import ztare_proofs.ZtareProofs.ns_leray_gain_tax_trackb_obligation

namespace ZtareProofs.NS

theorem crossTermCharged_of_admissible_matrix
    (C : SignedObservable)
    (h_admissible : IsAdmissibleObservable C)
    (h_kind : C.kind = ObservableKind.matrixBlock) :
    C.crossTermCharged := by
  rcases h_admissible with ⟨_, _, h_intertwiner⟩
  have h_charged := h_intertwiner h_kind
  rcases h_charged with ⟨_, _, _, h_cross⟩
  exact h_cross

end ZtareProofs.NS
