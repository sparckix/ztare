import ztare_proofs.ZtareProofs.ns_leray_gain_tax_trackb_obligation

namespace ZtareProofs.NS

theorem crossTermCharged_of_matrix_intertwiner
    (C : SignedObservable)
    (h_kind : C.kind = ObservableKind.matrixBlock)
    (h_intertwiner : MatrixIntertwinerCharged C) :
    C.crossTermCharged := by
  have h_charged := h_intertwiner h_kind
  exact h_charged.2.2.2

end ZtareProofs.NS
