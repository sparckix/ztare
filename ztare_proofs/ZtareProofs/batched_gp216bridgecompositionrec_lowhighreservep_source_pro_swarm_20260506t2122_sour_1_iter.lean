import ztare_proofs.ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

def gp216_low_high_reserve_pde_source_witness_struct
    (H : TrackBContinuationHandoffReceipt)
    (obligation : LowHighLipschitzReservePDEObligation)
    (energyBudgetShellReserveClosure :
      LowHighEnergyBudgetShellReserveClosure
        (trackBGeneratedLowFrequencyLipschitzLedger
          H.profile_lipschitz
          H.initialData))
    (energyBudgetPDEHandoff :
      LowHighEnergyBudgetShellReservePDEHandoff
        obligation
        (trackBGeneratedLowFrequencyLipschitzLedger
          H.profile_lipschitz
          H.initialData)
        energyBudgetShellReserveClosure) :
    GP216LowHighReservePDESourceBundle H where
  obligation := obligation
  energyBudgetShellReserveClosure := energyBudgetShellReserveClosure
  energyBudgetPDEHandoff := energyBudgetPDEHandoff

end ZtareProofs.NS
