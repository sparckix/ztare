import Mathlib.Data.List.Basic
import Mathlib.Tactic

namespace ZtareProofs

inductive NSState where
  | oneI1Pos
  | oneI2Pos
  | oneI1Neg
  | twoI1Neg
  | twoI0Neg
  deriving DecidableEq, Repr

open NSState

/-- Certified finite trace extracted from `phase5o_state_transition_audit.json`. -/
def trace : List NSState :=
  [oneI1Pos, oneI2Pos, oneI1Pos, oneI1Neg, twoI1Neg, oneI1Pos, twoI0Neg]

def danger : NSState := oneI2Pos

def consecutivePairs : List (NSState × NSState) :=
  trace.zip (trace.drop 1)

def observedDangerSelfLoop : Bool :=
  consecutivePairs.any (fun p => p.1 == danger && p.2 == danger)

def stateAt1 : Option NSState :=
  match trace with
  | _ :: s1 :: _ => some s1
  | _ => none

def stateAt2 : Option NSState :=
  match trace with
  | _ :: _ :: s2 :: _ => some s2
  | _ => none

theorem unique_observed_danger_visit :
    trace.filter (fun s => s == danger) = [danger] := by
  decide

theorem danger_at_index_one :
    stateAt1 = some danger := by
  decide

theorem immediate_observed_eviction :
    stateAt2 = some oneI1Pos := by
  decide

theorem no_observed_danger_self_loop :
    observedDangerSelfLoop = false := by
  decide

/-- Observed redistribution timescale proxy from Phase 5o. -/
def tauRedist : Rat := (1 : Rat) / 20

/-- Observed consolidation timescale proxy from Phase 5o. -/
def tauConsProxy : Rat := (7540645060705461 : Rat) / 1000000000000000

theorem observed_timescale_separation :
    tauRedist < tauConsProxy := by
  norm_num [tauRedist, tauConsProxy]

theorem observed_timescale_ratio_lt_one_hundredth :
    tauRedist / tauConsProxy < (1 : Rat) / 100 := by
  norm_num [tauRedist, tauConsProxy]

end ZtareProofs
