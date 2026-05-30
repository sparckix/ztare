import Mathlib.Tactic
import ZtareProofs.ns_profile_lsc_self_tax_obligation

namespace ZtareProofs.NS

/-- A defect-inclusive output-limit receipt rules out the corresponding
relaxed-output defect floor falsifier, demonstrating that the numeric defects
are actually present in the relaxed output price. -/
theorem no_relaxed_output_defect_floor_falsifier
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPriceReceipt S) :
    ¬ LeraySelfTaxRelaxedOutputDefectFloorFalsifier R := by
  intro F
  cases F with
  | selfTax hbad =>
    exact not_lt_of_ge R.self_tax_relaxed_output_includes_numeric_defects hbad
  | crossDefect hbad =>
    exact not_lt_of_ge R.cross_defect_relaxed_output_includes_numeric_defects hbad
  | coherence hbad =>
    exact not_lt_of_ge R.coherence_relaxed_output_includes_numeric_defects hbad

end ZtareProofs.NS
