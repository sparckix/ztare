import Mathlib

namespace AxiomPack.BinaryLinearCodeLRATNegativeProbe

def selectRow (selected : Bool) (row : BitVec 51) : BitVec 51 :=
  if selected then row else 0

def encode (u : BitVec 20) : BitVec 51 :=
  selectRow (u.getLsbD 0) (BitVec.ofNat 51 0x24883bee00001) ^^^
  selectRow (u.getLsbD 1) (BitVec.ofNat 51 0x091077dd00002) ^^^
  selectRow (u.getLsbD 2) (BitVec.ofNat 51 0x1220ebbb00004) ^^^
  selectRow (u.getLsbD 3) (BitVec.ofNat 51 0x2441d37700008) ^^^
  selectRow (u.getLsbD 4) (BitVec.ofNat 51 0x0893a2ef00010) ^^^
  selectRow (u.getLsbD 5) (BitVec.ofNat 51 0x112741df00020) ^^^
  selectRow (u.getLsbD 6) (BitVec.ofNat 51 0x224e83be00040) ^^^
  selectRow (u.getLsbD 7) (BitVec.ofNat 51 0x049d077d00080) ^^^
  selectRow (u.getLsbD 8) (BitVec.ofNat 51 0x092a0efb00100) ^^^
  selectRow (u.getLsbD 9) (BitVec.ofNat 51 0x12441df700200) ^^^
  selectRow (u.getLsbD 10) (BitVec.ofNat 51 0x7081a9c300400) ^^^
  selectRow (u.getLsbD 11) (BitVec.ofNat 51 0x6113538600800) ^^^
  selectRow (u.getLsbD 12) (BitVec.ofNat 51 0x4236a30d01000) ^^^
  selectRow (u.getLsbD 13) (BitVec.ofNat 51 0x446d421b02000) ^^^
  selectRow (u.getLsbD 14) (BitVec.ofNat 51 0x48ca843704000) ^^^
  selectRow (u.getLsbD 15) (BitVec.ofNat 51 0x51850c6e08000) ^^^
  selectRow (u.getLsbD 16) (BitVec.ofNat 51 0x630a18dc10000) ^^^
  selectRow (u.getLsbD 17) (BitVec.ofNat 51 0x461435b820000) ^^^
  selectRow (u.getLsbD 18) (BitVec.ofNat 51 0x4c286b7040000) ^^^
  selectRow (u.getLsbD 19) (BitVec.ofNat 51 0x5840d6e180000)

theorem distanceAtLeast15_negative_probe :
    ∀ u : BitVec 20, u ≠ 0 → (BitVec.ofNat 51 15) ≤ (encode u).cpop := by
  simp only [encode, selectRow]
  bv_decide? (timeout := 30) (solverMode := .counterexample)

end AxiomPack.BinaryLinearCodeLRATNegativeProbe
