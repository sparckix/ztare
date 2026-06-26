import Mathlib

def myDouble (n : Nat) : Nat := n + n
def decoyDouble (n : Nat) : Nat := n + 1

-- a TRUE overlap-agreement with the trusted reference (2 * n) — provable, so it PINS myDouble
theorem anchor_myDouble_agrees_two_mul : ∀ n : Nat, myDouble n = 2 * n := by
  intro n; simp [myDouble, Nat.two_mul]

-- a FALSE agreement: decoyDouble is a self-consistent decoy (decoyDouble 1 = 2 passes a sanity check)
-- but it does NOT equal 2 * n, so the agent CANNOT prove this — it stays sorried ⇒ no verified anchor
theorem anchor_decoyDouble_agrees_two_mul : ∀ n : Nat, decoyDouble n = 2 * n := by
  intro n; sorry
#print axioms anchor_decoyDouble_agrees_two_mul
