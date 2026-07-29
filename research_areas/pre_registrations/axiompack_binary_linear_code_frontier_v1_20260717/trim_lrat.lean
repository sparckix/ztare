import Lean.Elab.Tactic.BVDecide.LRAT.Trim
import Std.Tactic.BVDecide.LRAT.Parser

def main (args : List String) : IO Unit := do
  let [input, output] := args
    | throw <| IO.userError "usage: trim_lrat INPUT OUTPUT"
  let proof ← Std.Tactic.BVDecide.LRAT.loadLRATProof input
  let trimmed ← IO.ofExcept <| Lean.Elab.Tactic.BVDecide.LRAT.trim proof
  Std.Tactic.BVDecide.LRAT.dumpLRATProof output trimmed false
  IO.println s!"input_steps={proof.size} trimmed_steps={trimmed.size}"
