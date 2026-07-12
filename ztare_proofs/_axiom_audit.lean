import Mathlib

abbrev Grid := List (List Nat)

def countColor (g : Grid) (c : Nat) : Nat :=
  (g.map (fun row => (row.filter (fun v => v = c)).length)).foldl (· + ·) 0

opaque specStep : Grid → Nat → Nat → Grid

theorem iso_lemma1_row_map_count_le
    (g : Grid) (f : List Nat → List Nat) (color : Nat)
    (h : ∀ row ∈ g,
      ((f row).filter (fun v => v = color)).length ≤
        (row.filter (fun v => v = color)).length) :
    countColor (g.map f) color ≤ countColor g color :=
by
  have foldl_add (a : Nat) (xs : List Nat) :
      xs.foldl (· + ·) a = a + xs.foldl (· + ·) 0 := by
    induction xs generalizing a with
    | nil => simp
    | cons x xs ih =>
        simp only [List.foldl_cons]
        rw [ih (a + x), ih (0 + x)]
        simp [Nat.add_assoc]
  intro g f color h
  induction g with
  | nil =>
      simp [countColor]
  | cons row rows ih =>
      simp only [List.map_cons, countColor]
      simp only [List.foldl_cons]
      rw [foldl_add
        (0 + ((f row).filter (fun v => v = color)).length)
        ((rows.map f).map (fun r => (r.filter (fun v => v = color)).length))]
      rw [foldl_add
        (0 + (row.filter (fun v => v = color)).length)
        (rows.map (fun r => (r.filter (fun v => v = color)).length))]
      simp only [Nat.zero_add]
      apply Nat.add_le_add
      · exact h row (by simp)
      · apply ih
        intro r hr
        exact h r (by simp [hr])

#print axioms iso_lemma1_row_map_count_le
