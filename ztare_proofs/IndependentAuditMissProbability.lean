import Mathlib.Probability.Distributions.SetBernoulli

open MeasureTheory Measure unitInterval
open scoped ENNReal Finset

namespace ProbabilityTheory

/-!
This theory proves only the product-Bernoulli probability of the empty audit
schedule. Interpreting that event as a harm miss additionally requires
persistence, certain audit detection, and a private nonadaptive draw; those
operational conditions are not modeled by these theorems.
-/

/-- A schedule over `L` relevant rounds records the rounds selected for audit. -/
abbrev AuditSchedule (L : Nat) : Type := Set (Fin L)

-- @denotation-anchor: anchor=anchor_AuditSchedule_eq_set; target=AuditSchedule; kind=definitional; external=Set
theorem anchor_AuditSchedule_eq_set (L : Nat) :
    AuditSchedule L = Set (Fin L) := rfl

/-- The schedule selecting no relevant round. -/
def emptyAuditSchedule (L : Nat) : AuditSchedule L := ∅

-- @denotation-anchor: anchor=anchor_emptyAuditSchedule_eq_empty; target=emptyAuditSchedule; kind=definitional; external=EmptyCollection.empty
theorem anchor_emptyAuditSchedule_eq_empty (L : Nat) :
    emptyAuditSchedule L = (∅ : Set (Fin L)) := rfl

/-- No round belongs to the empty audit schedule. -/
theorem emptyAuditSchedule_no_round (L : Nat) (i : Fin L) :
    i ∉ emptyAuditSchedule L := by
  simp [emptyAuditSchedule]

/-- The product Bernoulli measure that independently includes every relevant
round with the fixed unit-interval probability `p`. -/
noncomputable def iidAuditSchedule (L : Nat) (p : I) : Measure (AuditSchedule L) :=
  setBernoulli (Set.univ : Set (Fin L)) p

-- @denotation-anchor: anchor=anchor_iidAuditSchedule_eq_setBernoulli; target=iidAuditSchedule; kind=definitional; external=ProbabilityTheory.setBernoulli
theorem anchor_iidAuditSchedule_eq_setBernoulli (L : Nat) (p : I) :
    iidAuditSchedule L p = setBernoulli (Set.univ : Set (Fin L)) p := rfl

/-- The event containing exactly the schedule that selects no relevant round.
This is a singleton event, not the empty event. -/
def auditMissEvent (L : Nat) : Set (AuditSchedule L) := {emptyAuditSchedule L}

-- @denotation-anchor: anchor=anchor_auditMissEvent_eq_singleton_empty; target=auditMissEvent; kind=definitional; external=Set.singleton
theorem anchor_auditMissEvent_eq_singleton_empty (L : Nat) :
    auditMissEvent L = Set.singleton (∅ : Set (Fin L)) := rfl

/-- With zero selection probability, the empty-schedule event has probability one. -/
theorem iidAuditSchedule_zero_model (L : Nat) :
    iidAuditSchedule L 0 (auditMissEvent L) = 1 := by
  simp [iidAuditSchedule, auditMissEvent, emptyAuditSchedule]

/-- Under the product Bernoulli audit schedule, the probability of auditing no
relevant round is the product of the `L` per-round non-selection probabilities. -/
theorem iidAudit_emptyScheduleProbability (L : Nat) (p : I) :
    (setBernoulli (Set.univ : Set (Fin L)) p
      ({∅} : Set (Set (Fin L)))).toReal =
      (1 - (p : Real)) ^ L := by
  rw [setBernoulli_singleton (u := Set.univ) (p := p) (by simp) Set.finite_univ]
  simp

/-- The empty-schedule identity stated through the reusable schedule and miss-event API. -/
theorem iidAudit_missEventProbability (L : Nat) (p : I) :
    (iidAuditSchedule L p (auditMissEvent L)).toReal =
      (1 - (p : Real)) ^ L := by
  exact iidAudit_emptyScheduleProbability L p

/-- At zero relevant rounds, the empty schedule is selected with probability one. -/
theorem iidAudit_missEventProbability_zero_rounds (p : I) :
    (iidAuditSchedule 0 p (auditMissEvent 0)).toReal = 1 := by
  exact iidAudit_missEventProbability 0 p

end ProbabilityTheory
