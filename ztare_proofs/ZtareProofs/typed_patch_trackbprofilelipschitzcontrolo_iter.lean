import Mathlib.Tactic
import ZtareProofs.ns_profile_lipschitz_clay_bridge

namespace ZtareProofs.NS

theorem no_trackB_profile_lipschitz_critical_control_falsifier
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData)
    (h : ¬ (O.evolution_of_initial_data u0).criticalControl) :
    False :=
  h (critical_control_of_trackB_profile_lipschitz_closure O u0)

end ZtareProofs.NS
