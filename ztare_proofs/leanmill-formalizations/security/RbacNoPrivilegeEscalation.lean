/-
LeanMill campaign provenance — reachable_blocks_effective_with_boundary_widening_witness
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=notes_rbac_no_privilege_escalation_blueprint_0704T2010) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Quot.sound
  domain      : formalization-nonmath
  time        : wall 1108.02s launch→close = formalize 589.87s (theory+statement+firewall) + prove 518.15s (proof search) · prove p50 610.24s p95 1077.09s
  compute     : cost-to-closure 307.44s mean · 680.53s total
  yield       : 9/29 attempts closed (15 failed)
  phases      : 696.1s leaf.dispatch · 58.9s pool · 53.3s formalize · 15.3s native · 0.2s govern.mnc · 0s consolidate
  reuse       : 4 rung(s) banked this run · 0 reused from prior bank
  moves       : native_hammer×14 · claude_warm×9 · conjecture_lemma×5 · proposer_pool×1
  milestone   : campaign family 'notes_rbac_no_privilege_escalation_blueprint' — 6 run(s) · REAL elapsed (launch→last) 31772.4s (~530 min) = formalize 4084.7s + prove/other · active-solve 6703.3s · 49 closures [launch→last is the honest wall]
     - notes_rbac_no_privilege_escalation_blueprint_0704T0737: 14/187 closed · elapsed 16421.2s (~273.7 min)
     - notes_rbac_no_privilege_escalation_blueprint_0704T1342: 18/152 closed · elapsed 7125.55s (~118.8 min)
     - notes_rbac_no_privilege_escalation_blueprint_0704T1649: 1/10 closed · elapsed 1939.78s (~32.3 min)
     - notes_rbac_no_privilege_escalation_blueprint_0704T1746: 3/42 closed · elapsed 2926.01s (~48.8 min)
     - notes_rbac_no_privilege_escalation_blueprint_0704T1922: 4/14 closed · elapsed 2246.83s (~37.4 min)
     - notes_rbac_no_privilege_escalation_blueprint_0704T2010: 9/29 closed · elapsed 1113.04s (~18.6 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/rbac_no_privilege_escalation_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

abbrev Permission := Type

structure AuthState (Perm : Type*) where
  granted : Set Perm
  boundary : Set Perm

def effective {Perm : Type*} (s : AuthState Perm) : Set Perm :=
  s.granted ∩ s.boundary

def BoundaryExcludes {Perm : Type*} (root : Perm) (s : AuthState Perm) : Prop :=
  root ∉ s.boundary

inductive Operation (Perm : Type*) where
  | assignRole (grantDelta boundaryDelta : Set Perm)
  | addHierarchyEdge (grantDelta boundaryDelta : Set Perm)
  | grantTrustPolicy (grantDelta boundaryDelta : Set Perm)

def grants {Perm : Type*} : Operation Perm → Set Perm
  | Operation.assignRole grantDelta _ => grantDelta
  | Operation.addHierarchyEdge grantDelta _ => grantDelta
  | Operation.grantTrustPolicy grantDelta _ => grantDelta

/-- Permissions newly admitted to the boundary by an operation. -/

def boundaryAdds {Perm : Type*} : Operation Perm → Set Perm
  | Operation.assignRole _ boundaryDelta => boundaryDelta
  | Operation.addHierarchyEdge _ boundaryDelta => boundaryDelta
  | Operation.grantTrustPolicy _ boundaryDelta => boundaryDelta

def Operation.grants {Perm : Type*} : Operation Perm → Set Perm
  | Operation.assignRole grantDelta _ => grantDelta
  | Operation.addHierarchyEdge grantDelta _ => grantDelta
  | Operation.grantTrustPolicy grantDelta _ => grantDelta

-- [family-lemma-library] banked: Operation.boundaryAdds

def Operation.boundaryAdds {Perm : Type*} : Operation Perm → Set Perm
  | Operation.assignRole _ boundaryDelta => boundaryDelta
  | Operation.addHierarchyEdge _ boundaryDelta => boundaryDelta
  | Operation.grantTrustPolicy _ boundaryDelta => boundaryDelta

-- [family-lemma-library] banked: iso_lemma2__727e0321

def AdmissibleOperation {Perm : Type*} (root : Perm) (op : Operation Perm) : Prop :=
  root ∉ op.boundaryAdds

def applyOp {Perm : Type*} (s : AuthState Perm) (op : Operation Perm) :
    AuthState Perm :=
  { granted := s.granted ∪ op.grants
    boundary := s.boundary ∪ op.boundaryAdds }

def postOps {Perm : Type*} (s : AuthState Perm) (ops : List (Operation Perm)) :
    AuthState Perm :=
  ops.foldl applyOp s

def AdmissibleSequence {Perm : Type*}
    (root : Perm) (ops : List (Operation Perm)) : Prop :=
  ∀ op ∈ ops, AdmissibleOperation root op

def Reachable {Perm : Type*} (root : Perm)
    (initial target : AuthState Perm) : Prop :=
  ∃ ops : List (Operation Perm),
    AdmissibleSequence root ops ∧ postOps initial ops = target

theorem reachable_blocks_effective_with_boundary_widening_witness : ∀ {Perm : Type*} {root : Perm} {initial target : AuthState Perm}
    (hboundary : BoundaryExcludes root initial)
    (hreach : Reachable root initial target), root ∉ effective target ∧
      root ∈ effective
        (applyOp ({ granted := ∅, boundary := ∅ } : AuthState Perm)
          (Operation.assignRole ({root} : Set Perm) ({root} : Set Perm))) ∧
      ¬ AdmissibleOperation root
        (Operation.assignRole ({root} : Set Perm) ({root} : Set Perm)) := by
  intro Perm root initial target hboundary hreach
  have applyOp_preserves_boundary_excludes :
      ∀ {s : AuthState Perm} {op : Operation Perm},
        BoundaryExcludes root s →
        AdmissibleOperation root op →
        BoundaryExcludes root (applyOp s op) := by
    intro s op hs hop
    intro hmem
    exact hmem.elim hs hop
  have postOps_preserves_boundary_excludes :
      ∀ {s : AuthState Perm} {ops : List (Operation Perm)},
        BoundaryExcludes root s →
        AdmissibleSequence root ops →
        BoundaryExcludes root (postOps s ops) := by
    intro s ops
    induction ops generalizing s with
    | nil =>
        intro hs _
        exact hs
    | cons op ops ih =>
        intro hs hadm
        exact ih
          (applyOp_preserves_boundary_excludes hs (hadm op (by simp)))
          (by
            intro op' hop'
            exact hadm op' (by simp [hop']))
  have boundary_excludes_blocks_effective :
      ∀ {s : AuthState Perm}, BoundaryExcludes root s → root ∉ effective s := by
    intro s hs hmem
    exact hs hmem.2
  rcases hreach with ⟨ops, hadm, hpost⟩
  constructor
  · rw [← hpost]
    exact boundary_excludes_blocks_effective
      (postOps_preserves_boundary_excludes hboundary hadm)
  · constructor
    · simp [effective, applyOp, Operation.grants, Operation.boundaryAdds]
    · simp [AdmissibleOperation, Operation.boundaryAdds]
