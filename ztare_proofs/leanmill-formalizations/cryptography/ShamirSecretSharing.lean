/-
LeanMill campaign provenance — shamir_threshold_reconstruction_secrecy_tightness
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=shamir_secret_sharing_v6) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms [propext, Classical.choice, Quot.sound]
  domain      : formalization-cryptography
  time        : wall 1172.48s launch→close = formalize 736.16s (theory+statement+firewall) + prove 436.32s (proof search) · prove p50 652.49s p95 764.74s
  compute     : cost-to-closure 404.68s mean · 548.61s total
  yield       : 4/7 attempts closed (3 failed)
  phases      : 308.8s leaf.dispatch · 151.9s formalize · 6.7s native · 6s govern.mnc · 5s pool
  reuse       : cited 0 banked rung(s)
  moves       : native_hammer×6 · claude_warm×1
  milestone   : campaign family 'shamir_secret_sharing' — 4 run(s) · REAL elapsed (launch→last) 5577.3s (~93 min) = formalize 1923.2s + prove/other · active-solve 2304.4s · 9 closures [launch→last is the honest wall]
     - shamir_secret_sharing: 1/16 closed · elapsed 1551.98s (~25.9 min)
     - shamir_secret_sharing_v2: 1/9 closed · elapsed 936.24s (~15.6 min)
     - shamir_secret_sharing_v4: 3/19 closed · elapsed 1916.45s (~31.9 min)
     - shamir_secret_sharing_v6: 4/7 closed · elapsed 1172.62s (~19.5 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/shamir_secret_sharing_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

/-!
# Shamir secret sharing: foundational vocabulary

This file builds the scheme-level vocabulary for Shamir threshold secret sharing over
a field.  The definitions are deliberately thin wrappers around Mathlib primitives:
polynomials are `Polynomial F`, degree bounds are `Polynomial.natDegree < t`, and share
nodes are the subtype of nonzero field elements, so `0` remains reserved for the secret.

The major interpolation and threshold theorems are stated at the end as solver work
items.  The sanity lemmas above them are kernel-proved model cases that pin the chosen
definitions to Mathlib's polynomial API.
-/

noncomputable section

open Polynomial

namespace ShamirSecretSharing

variable {F : Type*}

/-!
Definition trial notes.

* Degree bound candidates considered:
  1. `P.natDegree < t`;
  2. `P.degree < t` in `WithBot ℕ`;
  3. membership in Mathlib's `Polynomial.degreeLT`.
  We select (1) because the constant-polynomial sanity lemmas below close immediately
  with `Polynomial.natDegree_C` and because the campaign threshold is a natural number.

* Node candidates considered:
  1. raw field elements plus side hypotheses `x ≠ 0`;
  2. a bundled subtype of nonzero elements;
  3. an indexed vector of nodes.
  We select (2): a `Finset (ShareNode F)` gives distinct nonzero share nodes by
  construction and keeps the secret point `0` out of share observations definitionally.

* Consistency candidates considered:
  1. a relation against an observation function on all share nodes;
  2. a relation against a list of pairs;
  3. equality of two generated share tables.
  We select (1): the observed domain is exactly a `Finset` of distinct nonzero nodes,
  and the value function is easy to restrict to that domain.
-/

/-- The threshold is the natural number of shares required for reconstruction. -/
def IsThreshold (t : ℕ) : Prop :=
  1 ≤ t

def DegreeBelowThreshold [Semiring F] (t : ℕ) (P : F[X]) : Prop :=
  P.natDegree < t

def IsSharingPolynomial [Semiring F] (t : ℕ) (s : F) (P : F[X]) : Prop :=
  DegreeBelowThreshold t P ∧ P.eval 0 = s

abbrev ShareNode (F : Type*) [Zero F] :=
  {x : F // x ≠ 0}

def shareAt [Semiring F] (P : F[X]) (x : ShareNode F) : F :=
  P.eval (x : F)

def Shares [Semiring F] (P : F[X]) : ShareNode F → F :=
  fun x => shareAt P x

def ConsistentOn [Semiring F] (nodes : Finset (ShareNode F)) (obs : ShareNode F → F)
    (P : F[X]) : Prop :=
  ∀ x ∈ nodes, shareAt P x = obs x

def ReconstructsPolynomial [Semiring F] (t : ℕ) (nodes : Finset (ShareNode F))
    (P : F[X]) : Prop :=
  nodes.card = t ∧
    DegreeBelowThreshold t P ∧
      ∀ Q : F[X], DegreeBelowThreshold t Q → ConsistentOn nodes (Shares P) Q → Q = P

def PerfectSecrecy [Semiring F] (t : ℕ) (nodes : Finset (ShareNode F))
    (obs : ShareNode F → F) : Prop :=
  ∀ w : F, ∃! P : F[X], IsSharingPolynomial t w P ∧ ConsistentOn nodes obs P

def secretOf [Semiring F] (P : F[X]) : F :=
  P.eval 0

def TightAtObservation [Semiring F] (t : ℕ) (nodes : Finset (ShareNode F))
    (obs : ShareNode F → F) : Prop :=
  ∃ P Q : F[X],
    DegreeBelowThreshold t P ∧
      DegreeBelowThreshold t Q ∧
        ConsistentOn nodes obs P ∧
          ConsistentOn nodes obs Q ∧ secretOf P ≠ secretOf Q

end ShamirSecretSharing

namespace ShamirSecretSharing

/-!
Append-only perfect-secrecy assembly.  The interpolation existence/uniqueness theorem
is the load-bearing algebraic work item; the Shamir secrecy statement below is just
the definitional translation from node evaluations to `ConsistentOn`.
-/

end ShamirSecretSharing


namespace ShamirSecretSharing

/-!
Append-only consolidation rungs.  The original solver-facing statements above remain
unchanged; these theorems bank the proved route through the root-count rung
`iso_lemma1__2c12dc18`.
-/

end ShamirSecretSharing


namespace ShamirSecretSharing

/-!
Append-only substrate consolidation.

Definition trial notes for this round:

* Exact observation candidates considered:
  1. keep raw `nodes` and `hcard` arguments everywhere;
  2. bundle `nodes`, `obs`, and `nodes.card = t - 1` in a structure;
  3. encode the observation as a subtype of functions on a finite type.
  We select (2): it preserves the existing `Finset (ShareNode F)` API while making the
  exact `t - 1` count a reusable field.

* Reconstruction-node candidates considered:
  1. raw `nodes` plus a card proof;
  2. a bundled exact-cardinality structure;
  3. a vector/list of nodes.
  We select (2), for the same reason: the existing `Finset` distinctness and
  `ShareNode` nonzeroness remain available definitionally.

* Bijection candidates considered:
  1. define secrecy only as `PerfectSecrecy`;
  2. define the consistent-polynomial subtype and later prove an equivalence;
  3. construct a noncomputable equivalence directly from `PerfectSecrecy`.
  We select (3) as substrate, because its sanity theorem proves that the strong
  `forall secret, exists unique polynomial` predicate really yields the promised
  bijection with no extra compatibility hypotheses.
-/

end ShamirSecretSharing

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open ShamirSecretSharing

-- [family-lemma-library] banked: existsUnique_sharing_polynomial_of_card
theorem existsUnique_sharing_polynomial_of_card : ∀ [Field F] {ι : Type*} {t : ℕ}
    (ht : IsThreshold t) (nodes : Finset ι) (x : ι → F)
    (hx0 : ∀ i ∈ nodes, x i ≠ 0)
    (hinj : ∀ i ∈ nodes, ∀ j ∈ nodes, x i = x j → i = j)
    (hcard : nodes.card = t - 1) (obs : ι → F) (w : F), ∃! P : F[X],
      IsSharingPolynomial t w P ∧ ∀ i ∈ nodes, P.eval (x i) = obs i := by
  intro _ ι t ht nodes x hx0 hinj hcard obs w
  classical
  let s : Finset (Option ι) := insert none (nodes.image some)
  let v : Option ι → F := fun o =>
    match o with
    | none => 0
    | some i => x i
  let r : Option ι → F := fun o =>
    match o with
    | none => w
    | some i => obs i
  have hs_card : s.card = t := by
    have hnone : (none : Option ι) ∉ nodes.image some := by
      intro h
      rcases Finset.mem_image.mp h with ⟨i, hi, hsome⟩
      cases hsome
    have hcard_image : (nodes.image some).card = nodes.card := by
      exact Finset.card_image_of_injective _ (fun _ _ h => Option.some.inj h)
    calc
      s.card = (nodes.image some).card + 1 := Finset.card_insert_of_notMem hnone
      _ = nodes.card + 1 := by rw [hcard_image]
      _ = (t - 1) + 1 := by rw [hcard]
      _ = t := Nat.sub_add_cancel ht
  have hvinj : Set.InjOn v (s : Set (Option ι)) := by
    intro a ha b hb hab
    simp only [s, Finset.mem_coe, Finset.mem_insert, Finset.mem_image] at ha hb
    rcases ha with rfl | ⟨i, hi, rfl⟩
    · rcases hb with rfl | ⟨j, hj, hbj⟩
      · rfl
      · cases hbj
        simp only [v] at hab
        exact (hx0 j hj hab.symm).elim
    · rcases hb with rfl | ⟨j, hj, hbj⟩
      · simp only [v] at hab
        exact (hx0 i hi hab).elim
      · cases hbj
        simp only [v] at hab
        exact congrArg some (hinj i hi j hj hab)
  let P : F[X] := Lagrange.interpolate s v r
  have hPdeg : DegreeBelowThreshold t P := by
    have hdeg : P.degree < (t : WithBot ℕ) := by
      simpa [P, hs_card] using (Lagrange.degree_interpolate_lt (r := r) hvinj)
    by_cases hP0 : P = 0
    · simpa [DegreeBelowThreshold, IsThreshold, hP0] using ht
    · exact (Polynomial.natDegree_lt_iff_degree_lt hP0).mpr hdeg
  have hPzero : P.eval 0 = w := by
    have hmem : (none : Option ι) ∈ s := by simp [s]
    simpa [P, s, v, r] using (Lagrange.eval_interpolate_at_node (r := r) hvinj hmem)
  have hPobs : ∀ i ∈ nodes, P.eval (x i) = obs i := by
    intro i hi
    have hmem : some i ∈ s := by
      simp [s, hi]
    simpa [P, s, v, r] using (Lagrange.eval_interpolate_at_node (r := r) hvinj hmem)
  refine ⟨P, ⟨⟨hPdeg, hPzero⟩, hPobs⟩, ?_⟩
  intro Q hQ
  have hQdeg : Q.degree < (t : WithBot ℕ) := by
    by_cases hQ0 : Q = 0
    · simp [hQ0, IsThreshold, ht]
    · exact (Polynomial.natDegree_lt_iff_degree_lt hQ0).mp hQ.1.1
  have hQdeg_s : Q.degree < (s.card : WithBot ℕ) := by
    simpa [hs_card] using hQdeg
  have hQeval : ∀ o ∈ s, Q.eval (v o) = r o := by
    intro o ho
    simp only [s, Finset.mem_insert, Finset.mem_image] at ho
    rcases ho with rfl | ⟨i, hi, rfl⟩
    · simpa [v, r] using hQ.1.2
    · simpa [v, r] using hQ.2 i hi
  exact Lagrange.eq_interpolate_of_eval_eq (r := r) hvinj hQdeg_s hQeval

-- [family-lemma-library] banked: shamir_threshold_reconstruction_secrecy_tightness_conj2__25601c47
theorem shamir_threshold_reconstruction_secrecy_tightness_conj2__25601c47 : ∀ [Field F] [Nontrivial F] {t : ℕ}
    (ht : IsThreshold t), (∀ nodes : Finset (ShareNode F), nodes.card = t - 1 →
        ∀ obs : ShareNode F → F, PerfectSecrecy t nodes obs) := by
  intro _ _ t ht nodes hcard obs
  have h :=
    existsUnique_sharing_polynomial_of_card
      (F := F) (ι := ShareNode F) (t := t) ht nodes (fun x : ShareNode F => (x : F))
      (by
        intro x hx
        exact x.property)
      (by
        intro x hx y hy hxy
        exact Subtype.ext hxy)
      hcard obs
  simpa [PerfectSecrecy, ConsistentOn, shareAt] using h

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open ShamirSecretSharing

-- [family-lemma-library] banked: shamir_threshold_reconstruction_secrecy_tightness_conj3__2ba681de
theorem shamir_threshold_reconstruction_secrecy_tightness_conj3__2ba681de : ∀ [Field F] [Nontrivial F] {t : ℕ}
    (ht : IsThreshold t), (∀ nodes : Finset (ShareNode F), nodes.card = t - 1 →
          ∀ obs : ShareNode F → F, TightAtObservation t nodes obs) := by
  classical
  intro _ _ t ht nodes hcard obs
  let S : Finset (Option (ShareNode F)) := insert none (nodes.image some)
  let v : Option (ShareNode F) → F
    | none => 0
    | some x => (x : F)
  let values : F → Option (ShareNode F) → F := fun w o =>
    match o with
    | none => w
    | some x => obs x
  let interp : F → F[X] := fun w => Lagrange.interpolate S v (values w)
  have hsome_mem : ∀ x ∈ nodes, (some x : Option (ShareNode F)) ∈ S := by
    intro x hx
    simp [S, hx]
  have hnone_mem : (none : Option (ShareNode F)) ∈ S := by
    simp [S]
  have hinj : Set.InjOn v S := by
    intro a ha b hb hab
    cases a with
    | none =>
        cases b with
        | none => rfl
        | some y =>
            exfalso
            exact y.property hab.symm
    | some x =>
        cases b with
        | none =>
            exfalso
            exact x.property hab
        | some y =>
            exact congrArg some (Subtype.ext hab)
  have hcardS : S.card = t := by
    have hnone_not_mem : (none : Option (ShareNode F)) ∉ nodes.image some := by
      simp
    calc
      S.card = (nodes.image some).card + 1 := by
        simpa [S] using Finset.card_insert_of_notMem hnone_not_mem
      _ = nodes.card + 1 := by
        rw [Finset.card_image_of_injective nodes]
        intro x y hxy
        exact Option.some.inj hxy
      _ = t := by
        have ht' : 1 ≤ t := ht
        omega
  have hdegree : ∀ w : F, DegreeBelowThreshold t (interp w) := by
    intro w
    by_cases hp : interp w = 0
    · simp [DegreeBelowThreshold, hp, IsThreshold] at ht ⊢
      exact ht
    · rw [DegreeBelowThreshold]
      rw [Polynomial.natDegree_lt_iff_degree_lt hp]
      simpa [interp, hcardS] using
        (Lagrange.degree_interpolate_lt (s := S) (v := v) (r := values w) hinj)
  have hconsistent : ∀ w : F, ConsistentOn nodes obs (interp w) := by
    intro w x hx
    have h :=
      Lagrange.eval_interpolate_at_node (s := S) (v := v) (r := values w)
        hinj (hsome_mem x hx)
    simpa [interp, shareAt, v, values] using h
  obtain ⟨a, b, hab⟩ := exists_pair_ne F
  refine ⟨interp a, interp b, hdegree a, hdegree b, hconsistent a, hconsistent b, ?_⟩
  intro hsecret
  apply hab
  have ha :
      secretOf (interp a) = a := by
    have h :=
      Lagrange.eval_interpolate_at_node (s := S) (v := v) (r := values a)
        hinj hnone_mem
    simpa [secretOf, interp, v, values] using h
  have hb :
      secretOf (interp b) = b := by
    have h :=
      Lagrange.eval_interpolate_at_node (s := S) (v := v) (r := values b)
        hinj hnone_mem
    simpa [secretOf, interp, v, values] using h
  exact ha.symm.trans (hsecret.trans hb)

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open ShamirSecretSharing

-- [family-lemma-library] banked: degree_lt_card_of_degreeBelowThreshold
lemma degree_lt_card_of_degreeBelowThreshold [Field F] {t : ℕ} {nodes : Finset α}
    {P : F[X]} (hcard : nodes.card = t) (hP : DegreeBelowThreshold t P) :
    P.degree < (nodes.card : WithBot ℕ) := by
  by_cases hP0 : P = 0
  · rw [hP0, Polynomial.degree_zero]
    exact WithBot.bot_lt_coe _
  · rw [Polynomial.degree_eq_natDegree hP0]
    exact WithBot.coe_lt_coe.2 (by simpa [DegreeBelowThreshold, hcard] using hP)

-- [family-lemma-library] banked: low_degree_unique_of_agree_on_injective_finset
lemma low_degree_unique_of_agree_on_injective_finset [Field F] {ι : Type*}
    {t : ℕ} (nodes : Finset ι) (x : ι → F)
    (hinj : ∀ a ∈ nodes, ∀ b ∈ nodes, x a = x b → a = b)
    (hcard : nodes.card = t) {P Q : F[X]}
    (hP : DegreeBelowThreshold t P) (hQ : DegreeBelowThreshold t Q)
    (hagree : ∀ a ∈ nodes, P.eval (x a) = Q.eval (x a)) :
    P = Q := by
  classical
  have hinjOn : Set.InjOn x (nodes : Set ι) := by
    intro a ha b hb hab
    exact hinj a ha b hb hab
  have hPdeg : P.degree < (nodes.card : WithBot ℕ) :=
    degree_lt_card_of_degreeBelowThreshold hcard hP
  have hQdeg : Q.degree < (nodes.card : WithBot ℕ) :=
    degree_lt_card_of_degreeBelowThreshold hcard hQ
  exact Polynomial.eq_of_degrees_lt_of_eval_index_eq (s := nodes) hinjOn hPdeg hQdeg hagree

-- [family-lemma-library] banked: reconstruction_correctness_aux
lemma reconstruction_correctness_aux [Field F] {t : ℕ} {s : F}
    {nodes : Finset (ShareNode F)} {P Q : F[X]}
    (hcard : nodes.card = t) (hP : IsSharingPolynomial t s P)
    (hQ : DegreeBelowThreshold t Q) (hagree : ConsistentOn nodes (Shares P) Q) :
    Q = P := by
  have hinj :
      ∀ a ∈ nodes, ∀ b ∈ nodes,
        ((fun x : ShareNode F => (x : F)) a =
          (fun x : ShareNode F => (x : F)) b) → a = b := by
    intro a _ b _ hab
    exact Subtype.ext hab
  refine low_degree_unique_of_agree_on_injective_finset
    (nodes := nodes) (x := fun x : ShareNode F => (x : F))
    hinj hcard hQ hP.1 ?_
  intro x hx
  have hxagree : shareAt Q x = Shares P x := hagree x hx
  simpa [Shares, shareAt] using hxagree

-- [family-lemma-library] banked: shamir_threshold_reconstruction_secrecy_tightness_conj1__ed911c0e
theorem shamir_threshold_reconstruction_secrecy_tightness_conj1__ed911c0e : ∀ [Field F] [Nontrivial F] {t : ℕ}
    (ht : IsThreshold t), (∀ (s : F) (P : F[X]), IsSharingPolynomial t s P →
      ∀ nodes : Finset (ShareNode F), nodes.card = t →
        ReconstructsPolynomial t nodes P ∧
          ∀ Q : F[X], DegreeBelowThreshold t Q → ConsistentOn nodes (Shares P) Q →
            Q = P ∧ Q.eval 0 = s) := by
  intro _ _ t _ s P hP nodes hcard
  constructor
  · refine ⟨hcard, hP.1, ?_⟩
    intro Q hQ hagree
    exact reconstruction_correctness_aux hcard hP hQ hagree
  · intro Q hQ hagree
    have hQP : Q = P := reconstruction_correctness_aux hcard hP hQ hagree
    exact ⟨hQP, by rw [hQP, hP.2]⟩

end

namespace ShamirSecretSharing

/-!
Append-only public campaign API.

Definition trial notes for this round:

* Final theorem package candidates considered:
  1. leave the target only as one large anonymous conjunction;
  2. introduce three named `Prop` legs and package their conjunction;
  3. make a structure with proof fields.
  We select (2): the statements stay proof-irrelevant, can be rewritten by `Iff.rfl`
  anchors, and still expose each campaign leg as a citable definition.

* Public theorem-name candidates considered:
  1. keep only generated hash-suffixed banked rungs;
  2. rename existing declarations in place;
  3. append exact-name aliases that cite the banked rungs.
  We select (3) to preserve append-only governance while giving downstream assembly
  stable names.
-/

/-- Reconstruction guarantee: any exact `t` share nodes determine the sharing polynomial. -/
def ReconstructionGuarantee (F : Type*) [Semiring F] (t : ℕ) : Prop :=
  ∀ (s : F) (P : F[X]), IsSharingPolynomial t s P →
    ∀ nodes : Finset (ShareNode F), nodes.card = t →
      ReconstructsPolynomial t nodes P ∧
        ∀ Q : F[X], DegreeBelowThreshold t Q → ConsistentOn nodes (Shares P) Q →
          Q = P ∧ Q.eval 0 = s

def PerfectSecrecyGuarantee (F : Type*) [Semiring F] (t : ℕ) : Prop :=
  ∀ nodes : Finset (ShareNode F), nodes.card = t - 1 →
    ∀ obs : ShareNode F → F, PerfectSecrecy t nodes obs

def TightnessGuarantee (F : Type*) [Semiring F] (t : ℕ) : Prop :=
  ∀ nodes : Finset (ShareNode F), nodes.card = t - 1 →
    ∀ obs : ShareNode F → F, TightAtObservation t nodes obs

end ShamirSecretSharing

section

open ShamirSecretSharing

/-- Public exact-name alias for the reconstruction leg. -/
theorem shamir_threshold_reconstruction_secrecy_tightness_conj1 [Field F] [Nontrivial F]
    {t : ℕ} (ht : IsThreshold t) :
    ReconstructionGuarantee F t := by
  exact shamir_threshold_reconstruction_secrecy_tightness_conj1__ed911c0e ht

/-- Public exact-name alias for the perfect-secrecy leg. -/
theorem shamir_threshold_reconstruction_secrecy_tightness_conj2 [Field F] [Nontrivial F]
    {t : ℕ} (ht : IsThreshold t) :
    PerfectSecrecyGuarantee F t := by
  exact shamir_threshold_reconstruction_secrecy_tightness_conj2__25601c47 ht

/-- Public exact-name alias for the tightness leg. -/
theorem shamir_threshold_reconstruction_secrecy_tightness_conj3 [Field F] [Nontrivial F]
    {t : ℕ} (ht : IsThreshold t) :
    TightnessGuarantee F t := by
  exact shamir_threshold_reconstruction_secrecy_tightness_conj3__2ba681de ht

/-- Public packaged theorem for the full Shamir threshold result. -/
theorem shamir_threshold_reconstruction_secrecy_tightness [Field F] [Nontrivial F]
    {t : ℕ} (ht : IsThreshold t) :
    (∀ (s : F) (P : F[X]), IsSharingPolynomial t s P →
      ∀ nodes : Finset (ShareNode F), nodes.card = t →
        ReconstructsPolynomial t nodes P ∧
          ∀ Q : F[X], DegreeBelowThreshold t Q → ConsistentOn nodes (Shares P) Q →
            Q = P ∧ Q.eval 0 = s) ∧
      (∀ nodes : Finset (ShareNode F), nodes.card = t - 1 →
        ∀ obs : ShareNode F → F, PerfectSecrecy t nodes obs) ∧
        (∀ nodes : Finset (ShareNode F), nodes.card = t - 1 →
          ∀ obs : ShareNode F → F, TightAtObservation t nodes obs) := by
  exact ⟨shamir_threshold_reconstruction_secrecy_tightness_conj1 ht,
    shamir_threshold_reconstruction_secrecy_tightness_conj2 ht,
    shamir_threshold_reconstruction_secrecy_tightness_conj3 ht⟩

end

#print axioms shamir_threshold_reconstruction_secrecy_tightness
