import Mathlib

-- Natural-language specification (blueprint): blueprints/defi_liquidation_safety_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

/-!
# DeFi liquidation safety: reachable-state solvency under guarded actions

A collateralized-debt position evolved by deposit/borrow/repay/withdraw, each behind the protocol's
solvency guard. Main theorem `reachable_state_solvency_guarded_actions`: from any healthy position, every
state reached by an admissible action sequence stays healthy and non-liquidatable, AND the per-step guard is
load-bearing (dropping it admits a borrow into an unhealthy state). Axiom-clean (propext, Classical.choice,
Quot.sound).
-/

variable {K : Type*} [Field K] [LinearOrder K] [IsStrictOrderedRing K]

structure Position (K : Type*) [Field K] [LinearOrder K] [IsStrictOrderedRing K] where
  collateral : K
  debt : K
  collateral_nonneg : 0 ≤ collateral
  debt_nonneg : 0 ≤ debt

def CollateralFactor (theta : K) : Prop :=
  0 < theta ∧ theta ≤ 1

/-- A position is healthy when debt is within its collateral-factor capacity. -/

def Healthy (theta : K) (p : Position K) : Prop :=
  p.debt ≤ theta * p.collateral

/-- A position is liquidatable when debt strictly exceeds capacity. -/

def Liquidatable (theta : K) (p : Position K) : Prop :=
  theta * p.collateral < p.debt

/-- Undercollateralization gap; nonpositive exactly on healthy states. -/

def healthGap (theta : K) (p : Position K) : K :=
  p.debt - theta * p.collateral

inductive UserActionKind where
  | deposit
  | repay
  | borrow
  | withdraw
deriving DecidableEq

/-- A protocol user action with a nonnegative submitted amount. -/

structure UserAction (K : Type*) [Field K] [LinearOrder K] [IsStrictOrderedRing K] where
  kind : UserActionKind
  amount : K
  amount_nonneg : 0 ≤ amount

def depositAction (amount : K) (hamount : 0 ≤ amount) : UserAction K :=
  { kind := UserActionKind.deposit, amount := amount, amount_nonneg := hamount }

def repayAction (amount : K) (hamount : 0 ≤ amount) : UserAction K :=
  { kind := UserActionKind.repay, amount := amount, amount_nonneg := hamount }

def borrowAction (amount : K) (hamount : 0 ≤ amount) : UserAction K :=
  { kind := UserActionKind.borrow, amount := amount, amount_nonneg := hamount }

def withdrawAction (amount : K) (hamount : 0 ≤ amount) : UserAction K :=
  { kind := UserActionKind.withdraw, amount := amount, amount_nonneg := hamount }

def applyUserAction (p : Position K) (a : UserAction K) : Position K :=
  match a.kind with
  | UserActionKind.deposit =>
      { collateral := p.collateral + a.amount
        debt := p.debt
        collateral_nonneg := add_nonneg p.collateral_nonneg a.amount_nonneg
        debt_nonneg := p.debt_nonneg }
  | UserActionKind.borrow =>
      { collateral := p.collateral
        debt := p.debt + a.amount
        collateral_nonneg := p.collateral_nonneg
        debt_nonneg := add_nonneg p.debt_nonneg a.amount_nonneg }
  | UserActionKind.repay =>
      { collateral := p.collateral
        debt := p.debt - min p.debt a.amount
        collateral_nonneg := p.collateral_nonneg
        debt_nonneg := by
          have hmin : min p.debt a.amount ≤ p.debt := min_le_left p.debt a.amount
          linarith }
  | UserActionKind.withdraw =>
      { collateral := p.collateral - min p.collateral a.amount
        debt := p.debt
        collateral_nonneg := by
          have hmin : min p.collateral a.amount ≤ p.collateral :=
            min_le_left p.collateral a.amount
          linarith
        debt_nonneg := p.debt_nonneg }

def AdmissibleAction (theta : K) (p : Position K) (a : UserAction K) : Prop :=
  match a.kind with
  | UserActionKind.deposit => True
  | UserActionKind.repay => True
  | UserActionKind.borrow => Healthy theta (applyUserAction p a)
  | UserActionKind.withdraw => Healthy theta (applyUserAction p a)

def executeUserActions (p : Position K) (actions : List (UserAction K)) : Position K :=
  actions.foldl applyUserAction p

def AdmissibleSequence (theta : K) :
    Position K → List (UserAction K) → Prop
  | _p, [] => True
  | p, a :: actions =>
      AdmissibleAction theta p a ∧
        AdmissibleSequence theta (applyUserAction p a) actions

def userTrajectory : Position K → List (UserAction K) → List (Position K)
  | p, [] => [p]
  | p, a :: actions => p :: userTrajectory (applyUserAction p a) actions

def TrajectoryHealthy (theta : K) (p : Position K)
    (actions : List (UserAction K)) : Prop :=
  ∀ q, q ∈ userTrajectory p actions → Healthy theta q

def priceMove (p : Position K) (lambda : K) (hlambda : 0 ≤ lambda) :
    Position K :=
  { collateral := lambda * p.collateral
    debt := p.debt
    collateral_nonneg := mul_nonneg hlambda p.collateral_nonneg
    debt_nonneg := p.debt_nonneg }

theorem admissible_sequence_keeps_trajectory_healthy : ∀ (theta : K) (hfactor : CollateralFactor theta) (p : Position K) (hp : Healthy theta p) (actions : List (UserAction K)) (hadm : AdmissibleSequence theta p actions), TrajectoryHealthy theta p actions :=
  by
  intro theta hfactor p hp actions hadm
  have htheta : 0 ≤ theta := le_of_lt hfactor.1
  have healthy_after_admissible_action :
      ∀ {p : Position K} {a : UserAction K},
        Healthy theta p →
          AdmissibleAction theta p a →
            Healthy theta (applyUserAction p a) := by
    intro p a hp_a hadm_a
    rcases a with ⟨kind, amount, hamount⟩
    cases kind
    · dsimp [Healthy, AdmissibleAction, applyUserAction] at hp_a hadm_a ⊢
      have hcap : 0 ≤ theta * amount := mul_nonneg htheta hamount
      nlinarith
    · dsimp [Healthy, AdmissibleAction, applyUserAction] at hp_a hadm_a ⊢
      have hmin_nonneg : 0 ≤ min p.debt amount := le_min p.debt_nonneg hamount
      nlinarith
    · simpa [Healthy, AdmissibleAction, applyUserAction] using hadm_a
    · simpa [Healthy, AdmissibleAction, applyUserAction] using hadm_a
  intro q hq
  induction actions generalizing p with
  | nil =>
      simp [userTrajectory] at hq
      simpa [hq] using hp
  | cons a actions ih =>
      simp [userTrajectory] at hq
      rcases hq with hq | hq
      · simpa [hq] using hp
      · exact ih
          (p := applyUserAction p a)
          (healthy_after_admissible_action hp hadm.1)
          hadm.2
          hq

theorem admissible_reachable_states_not_liquidatable : ∀ (theta : K) (hfactor : CollateralFactor theta) (p : Position K) (hp : Healthy theta p) (actions : List (UserAction K)) (hadm : AdmissibleSequence theta p actions), (∀ q, q ∈ userTrajectory p actions → ¬ Liquidatable theta q) :=
  by
  intro theta hfactor p hp actions hadm q hq hliq
  have htheta : 0 ≤ theta := le_of_lt hfactor.1
  have healthy_after_admissible_action :
      ∀ {p : Position K} {a : UserAction K},
        Healthy theta p →
          AdmissibleAction theta p a →
            Healthy theta (applyUserAction p a) := by
    intro p a hp_a hadm_a
    rcases a with ⟨kind, amount, hamount⟩
    cases kind
    · dsimp [Healthy, AdmissibleAction, applyUserAction] at hp_a hadm_a ⊢
      have hcap : 0 ≤ theta * amount := mul_nonneg htheta hamount
      nlinarith
    · dsimp [Healthy, AdmissibleAction, applyUserAction] at hp_a hadm_a ⊢
      have hmin_nonneg : 0 ≤ min p.debt amount := le_min p.debt_nonneg hamount
      nlinarith
    · simpa [Healthy, AdmissibleAction, applyUserAction] using hadm_a
    · simpa [Healthy, AdmissibleAction, applyUserAction] using hadm_a
  have trajectory_healthy :
      ∀ {p : Position K} {actions : List (UserAction K)},
        Healthy theta p →
          AdmissibleSequence theta p actions →
            ∀ q, q ∈ userTrajectory p actions → Healthy theta q := by
    intro p actions hp hadm q hq
    induction actions generalizing p with
    | nil =>
        simp [userTrajectory] at hq
        simpa [hq] using hp
    | cons a actions ih =>
        simp [userTrajectory] at hq
        rcases hq with hq | hq
        · simpa [hq] using hp
        · exact ih
            (healthy_after_admissible_action hp hadm.1)
            hadm.2
            hq
  have hhealthy : Healthy theta q := trajectory_healthy hp hadm q hq
  unfold Healthy at hhealthy
  unfold Liquidatable at hliq
  linarith

theorem withdraw_borrow_guard_is_load_bearing : ∀ (theta : K) (hfactor : CollateralFactor theta) (p : Position K) (hp : Healthy theta p) (actions : List (UserAction K)) (hadm : AdmissibleSequence theta p actions), ∃ (p₀ : Position K) (amount : K) (hamount : 0 ≤ amount), Healthy theta p₀ ∧ ¬ AdmissibleAction theta p₀ (borrowAction amount hamount) ∧ ¬ Healthy theta (applyUserAction p₀ (borrowAction amount hamount)) :=
  by
  intro theta _hfactor _p _hp _actions _hadm
  let p₀ : Position K :=
    { collateral := 0
      debt := 0
      collateral_nonneg := le_refl 0
      debt_nonneg := le_refl 0 }
  refine ⟨p₀, 1, zero_le_one, ?_, ?_, ?_⟩
  · simp [Healthy, p₀]
  · simp [AdmissibleAction, borrowAction, Healthy, applyUserAction, p₀]
  · simp [Healthy, borrowAction, applyUserAction, p₀]

theorem reachable_state_solvency_guarded_actions (theta : K) (hfactor : CollateralFactor theta) (p : Position K) (hp : Healthy theta p) (actions : List (UserAction K)) (hadm : AdmissibleSequence theta p actions) :
    TrajectoryHealthy theta p actions ∧ (∀ q, q ∈ userTrajectory p actions → ¬ Liquidatable theta q) ∧ ∃ (p₀ : Position K) (amount : K) (hamount : 0 ≤ amount), Healthy theta p₀ ∧ ¬ AdmissibleAction theta p₀ (borrowAction amount hamount) ∧ ¬ Healthy theta (applyUserAction p₀ (borrowAction amount hamount)) :=
  ⟨admissible_sequence_keeps_trajectory_healthy theta hfactor p hp actions hadm, admissible_reachable_states_not_liquidatable theta hfactor p hp actions hadm, withdraw_borrow_guard_is_load_bearing theta hfactor p hp actions hadm⟩
