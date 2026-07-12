/-
LeanMill campaign provenance — deferred_acceptance_stability_and_quiescence_load_bearing
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=notes_gale_shapley_stable_matching_blueprint_0707T0327) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : formalization-nonmath
  time        : wall 7993.92s launch→close = formalize 5138.74s (theory+statement+firewall) + prove 2855.18s (proof search) · prove p50 1732.92s p95 7856.73s
  compute     : cost-to-closure 656.75s mean · 2152.7s total
  yield       : 9/15 attempts closed (6 failed)
  phases      : 1849.4s leaf.dispatch · 434.9s formalize · 161.6s govern.mnc · 59.8s native · 0s pool · 0s consolidate
  reuse       : 5 rung(s) banked this run · 0 reused from prior bank
  moves       : native_hammer×6 · claude_warm×6 · cache_reuse×3
  milestone   : campaign family 'notes_gale_shapley_stable_matching_blueprint' — 23 run(s) · REAL elapsed (launch→last) 59685.8s (~995 min) = formalize 3611.2s + prove/other · active-solve 21001.6s · 133 closures [launch→last is the honest wall]
     - notes_gale_shapley_stable_matching_blueprint_0706T0006: 6/53 closed · elapsed 5420.68s (~90.3 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T0157: 5/42 closed · elapsed 2689.81s (~44.8 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T0304: 5/41 closed · elapsed 2643.13s (~44.1 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T0403: 11/45 closed · elapsed 3983.66s (~66.4 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T0522: 7/11 closed · elapsed 972.02s (~16.2 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T0549: 6/7 closed · elapsed 600.72s (~10.0 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T0602: 8/18 closed · elapsed 2326.34s (~38.8 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T0642: 11/20 closed · elapsed 3110.78s (~51.8 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T0739: 4/5 closed · elapsed 3112.05s (~51.9 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T1645: 4/8 closed · elapsed 1474.21s (~24.6 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T1734: 3/24 closed · elapsed 3669.86s (~61.2 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T1839: 3/6 closed · elapsed 762.6s (~12.7 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T1903: 9/33 closed · elapsed 3125.46s (~52.1 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T1959: 2/4 closed · elapsed 483.77s (~8.1 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T2011: 6/14 closed · elapsed 1740.71s (~29.0 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T2047: 6/7 closed · elapsed 850.24s (~14.2 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T2119: 6/7 closed · elapsed 1362.83s (~22.7 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T2204: 4/11 closed · elapsed 3396.06s (~56.6 min)
     - notes_gale_shapley_stable_matching_blueprint_0706T2333: 11/26 closed · elapsed 5998.36s (~100.0 min)
     - notes_gale_shapley_stable_matching_blueprint_0707T0132: 2/2 closed · elapsed 435.06s (~7.3 min)
     - notes_gale_shapley_stable_matching_blueprint_0707T0152: 1/1 closed · elapsed 110.36s (~1.8 min)
     - notes_gale_shapley_stable_matching_blueprint_0707T0227: 4/13 closed · elapsed 3421.88s (~57.0 min)
     - notes_gale_shapley_stable_matching_blueprint_0707T0327: 9/15 closed · elapsed 7995.18s (~133.3 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/gale_shapley_stable_matching_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

set_option linter.unusedSectionVars false

namespace GaleShapleyStableMatchingFormalizeProbe

universe u v

variable {Agent : Type u} {Alt : Type v}
variable {Man : Type u} {Woman : Type v}

structure StrictPreference (Agent : Type u) (Alt : Type v) where
  pref : Agent → Alt → Alt → Prop
  decidablePref : ∀ agent x y, Decidable (pref agent x y)
  irrefl : ∀ agent x, ¬ pref agent x x
  trans : ∀ agent {x y z}, pref agent x y → pref agent y z → pref agent x z
  total : ∀ agent {x y}, x ≠ y → pref agent x y ∨ pref agent y x

def WeaklyPrefers (prefs : StrictPreference Agent Alt)
    (agent : Agent) (x y : Alt) : Prop :=
  x = y ∨ prefs.pref agent x y

def chooseBetterForW (prefW : StrictPreference Woman Man)
    (w : Woman) (a b : Man) : Man :=
  letI : Decidable (prefW.pref w a b) := prefW.decidablePref w a b
  if prefW.pref w a b then a else b

structure Matching (Man : Type u) (Woman : Type v) where
  held : Woman → Option Man

/-- No man is held by two different women. -/

def NoDuplicateHolds (μ : Matching Man Woman) : Prop :=
  ∀ {w₁ w₂ : Woman} {m : Man}, μ.held w₁ = some m → μ.held w₂ = some m → w₁ = w₂

def emptyMatching : Matching Man Woman :=
  { held := fun _ => none }

def freeMan [DecidableEq Man] (μ : Matching Man Woman) (m : Man) : Prop :=
  ∀ w : Woman, μ.held w ≠ some m

instance instDecidableFreeMan [Fintype Woman] [DecidableEq Man]
    (μ : Matching Man Woman) (m : Man) : Decidable (freeMan μ m) := by
  unfold freeMan
  infer_instance

noncomputable def partnerOfMan (μ : Matching Man Woman) (m : Man) : Option Woman :=
  by
    classical
    exact if h : ∃ w : Woman, μ.held w = some m then some (Classical.choose h) else none

def ManPrefersOption (prefM : StrictPreference Man Woman)
    (m : Man) (w : Woman) : Option Woman → Prop
  | none => True
  | some w' => prefM.pref m w w'

def WomanPrefersOption (prefW : StrictPreference Woman Man)
    (w : Woman) (m : Man) : Option Man → Prop
  | none => True
  | some m' => prefW.pref w m m'

noncomputable def ManPrefersCurrent [DecidableEq Man]
    (prefM : StrictPreference Man Woman) (μ : Matching Man Woman) (m : Man) (w : Woman) :
    Prop :=
  ManPrefersOption prefM m w (partnerOfMan μ m)

noncomputable def BlockingPair [DecidableEq Man]
    (prefM : StrictPreference Man Woman) (prefW : StrictPreference Woman Man)
    (μ : Matching Man Woman) (m : Man) (w : Woman) : Prop :=
  ManPrefersCurrent prefM μ m w ∧ WomanPrefersOption prefW w m (μ.held w)

noncomputable def Stable [DecidableEq Man]
    (prefM : StrictPreference Man Woman) (prefW : StrictPreference Woman Man)
    (μ : Matching Man Woman) : Prop :=
  ∀ m w, ¬ BlockingPair prefM prefW μ m w

def FreeManIn (μ : Matching Man Woman) (m : Man) : Prop :=
  ∀ w : Woman, μ.held w ≠ some m

structure ProposalState (Man : Type u) (Woman : Type v) where
  matching : Matching Man Woman
  rem : Man → List Woman

/-- The opening state: nobody is held, and every man has his full proposal list. -/

def openingState (fullList : Man → List Woman) : ProposalState Man Woman :=
  { matching := emptyMatching, rem := fullList }

def ProposalStepRel (prefW : StrictPreference Woman Man)
    (state : ProposalState Man Woman) (m : Man) (next : ProposalState Man Woman) : Prop :=
  (¬ FreeManIn state.matching m ∧ next = state) ∨
    (FreeManIn state.matching m ∧ state.rem m = [] ∧ next = state) ∨
      ∃ w tail,
        FreeManIn state.matching m ∧
          state.rem m = w :: tail ∧
            ((state.matching.held w = none ∧ next.matching.held w = some m) ∨
              ∃ old,
                state.matching.held w = some old ∧
                  next.matching.held w = some (chooseBetterForW prefW w m old)) ∧
              (∀ w', w' ≠ w → next.matching.held w' = state.matching.held w') ∧
                next.rem m = tail ∧
                  ∀ m', m' ≠ m → next.rem m' = state.rem m'

inductive ProposalRun (prefW : StrictPreference Woman Man) :
    ProposalState Man Woman → List Man → ProposalState Man Woman → Prop
  | nil (state : ProposalState Man Woman) : ProposalRun prefW state [] state
  | cons {state mid final : ProposalState Man Woman} {m : Man} {schedule : List Man} :
      ProposalStepRel prefW state m mid →
        ProposalRun prefW mid schedule final →
          ProposalRun prefW state (m :: schedule) final

def ProposalListOrdered (prefM : StrictPreference Man Woman)
    (m : Man) (women : List Woman) : Prop :=
  women.Pairwise (fun w₁ w₂ => prefM.pref m w₁ w₂)

def ProposalListsSound (prefM : StrictPreference Man Woman)
    (fullList : Man → List Woman) : Prop :=
  ∀ m, (fullList m).Nodup ∧ ProposalListOrdered prefM m (fullList m)

def Quiescent [DecidableEq Man] (state : ProposalState Man Woman) : Prop :=
  ∀ m, freeMan state.matching m → state.rem m = []

def QuiescentState (state : ProposalState Man Woman) : Prop :=
  ∀ m : Man, FreeManIn state.matching m → state.rem m = []

noncomputable def ManPrefersCurrentNoDecidable
    (prefM : StrictPreference Man Woman) (μ : Matching Man Woman) (m : Man) (w : Woman) :
    Prop :=
  ManPrefersOption prefM m w (partnerOfMan μ m)

noncomputable def BlockingPairNoDecidable
    (prefM : StrictPreference Man Woman) (prefW : StrictPreference Woman Man)
    (μ : Matching Man Woman) (m : Man) (w : Woman) : Prop :=
  ManPrefersCurrentNoDecidable prefM μ m w ∧ WomanPrefersOption prefW w m (μ.held w)

theorem deferred_acceptance_stability_and_quiescence_load_bearing : (∀ {Man : Type u} {Woman : Type v}
      [Fintype Man] [Fintype Woman] [DecidableEq Man] [DecidableEq Woman]
      (prefM : StrictPreference Man Woman) (prefW : StrictPreference Woman Man)
      (fullList : Man → List Woman) (schedule : List Man)
      (state : ProposalState Man Woman),
        ProposalListsSound prefM fullList →
          (∀ m : Man, ∀ w : Woman, w ∈ fullList m) →
            ProposalRun prefW (openingState fullList) schedule state →
              Quiescent state →
                Stable prefM prefW state.matching) ∧
      (∃ (Man : Type u) (Woman : Type v),
        Nonempty (Fintype Man) ∧
          Nonempty (Fintype Woman) ∧
            ∃ (prefM : StrictPreference Man Woman) (prefW : StrictPreference Woman Man)
              (fullList : Man → List Woman) (schedule : List Man)
              (state : ProposalState Man Woman) (m : Man) (w : Woman),
                ProposalListsSound prefM fullList ∧
                  (∀ m : Man, ∀ w : Woman, w ∈ fullList m) ∧
                    ProposalRun prefW (openingState fullList) schedule state ∧
                      FreeManIn state.matching m ∧
                        w ∈ state.rem m ∧
                          ¬ QuiescentState state ∧
                            BlockingPairNoDecidable prefM prefW state.matching m w) := by
  constructor
  · intro Man Woman _ _ _ _ prefM prefW fullList schedule state hSound hComplete hRun hQuiet
    let RemOrdered (st : ProposalState Man Woman) : Prop :=
      ∀ m, ProposalListOrdered prefM m (st.rem m)
    let RemLowerClosed (st : ProposalState Man Woman) : Prop :=
      ∀ m {better worse : Woman},
        better ∈ st.rem m →
          worse ∈ fullList m → prefM.pref m better worse → worse ∈ st.rem m
    let HeldRemoved (st : ProposalState Man Woman) : Prop :=
      ∀ m w, st.matching.held w = some m → w ∉ st.rem m
    let WomanBest (st : ProposalState Man Woman) : Prop :=
      ∀ m w,
        w ∈ fullList m →
          w ∉ st.rem m →
            ∃ held, st.matching.held w = some held ∧ WeaklyPrefers prefW w held m
    let Inv (st : ProposalState Man Woman) : Prop :=
      RemOrdered st ∧ RemLowerClosed st ∧ HeldRemoved st ∧ WomanBest st
    have weak_trans :
        ∀ (w : Woman) (a b c : Man),
          WeaklyPrefers prefW w a b →
            WeaklyPrefers prefW w b c → WeaklyPrefers prefW w a c := by
      intro w a b c hab hbc
      rcases hab with rfl | hab
      · exact hbc
      · rcases hbc with rfl | hbc
        · exact Or.inr hab
        · exact Or.inr (prefW.trans w hab hbc)
    have weak_strict_false :
        ∀ (w : Woman) (a b : Man),
          WeaklyPrefers prefW w a b → prefW.pref w b a → False := by
      intro w a b hab hba
      rcases hab with hEq | hab
      · subst a
        exact prefW.irrefl w b hba
      · exact prefW.irrefl w a (prefW.trans w hab hba)
    have choose_weak_old :
        ∀ (w : Woman) (incoming old : Man),
          WeaklyPrefers prefW w (chooseBetterForW prefW w incoming old) old := by
      intro w incoming old
      unfold chooseBetterForW WeaklyPrefers
      by_cases h : prefW.pref w incoming old
      · simp [h]
      · simp [h]
    have choose_weak_incoming :
        ∀ (w : Woman) (incoming old : Man),
          WeaklyPrefers prefW w (chooseBetterForW prefW w incoming old) incoming := by
      intro w incoming old
      unfold chooseBetterForW WeaklyPrefers
      by_cases h : prefW.pref w incoming old
      · simp [h]
      · simp [h]
        by_cases hEq : old = incoming
        · exact Or.inl hEq
        · have hNe : incoming ≠ old := by
            intro hio
            exact hEq hio.symm
          rcases prefW.total w hNe with hin | hold
          · exact False.elim (h hin)
          · exact Or.inr hold
    have step_preserves :
        ∀ {st next : ProposalState Man Woman} (proposer : Man),
          Inv st → ProposalStepRel prefW st proposer next → Inv next := by
      intro st next proposer hInv hStep
      rcases hInv with ⟨hOrd, hLow, hHeld, hBest⟩
      unfold ProposalStepRel at hStep
      rcases hStep with hNoop | hNoop | hProposal
      · rcases hNoop with ⟨_, rfl⟩
        exact ⟨hOrd, hLow, hHeld, hBest⟩
      · rcases hNoop with ⟨_, _, rfl⟩
        exact ⟨hOrd, hLow, hHeld, hBest⟩
      · rcases hProposal with
          ⟨proposed, tail, hFree, hRem, hChange, hOtherHeld, hNextRem, hOtherRem⟩
        have hProposedNotTail : proposed ∉ tail := by
          intro hInTail
          have hThis := hOrd proposer
          rw [hRem] at hThis
          unfold ProposalListOrdered at hThis
          cases hThis with
          | cons hHead _ =>
              exact (prefM.irrefl proposer proposed) (hHead proposed hInTail)
        constructor
        · intro m
          by_cases hm : m = proposer
          · subst m
            have hThis := hOrd proposer
            rw [hRem] at hThis
            rw [hNextRem]
            unfold ProposalListOrdered at hThis ⊢
            simpa using hThis.tail
          · rw [hOtherRem m hm]
            exact hOrd m
        constructor
        · intro m better worse hBetter hWorse hPref
          by_cases hm : m = proposer
          · subst m
            rw [hNextRem] at hBetter ⊢
            have hBetterOld : better ∈ st.rem proposer := by
              rw [hRem]
              exact List.mem_cons_of_mem proposed hBetter
            have hWorseOld : worse ∈ st.rem proposer := hLow proposer hBetterOld hWorse hPref
            rw [hRem] at hWorseOld
            rcases (List.mem_cons.mp hWorseOld) with hWorseEq | hWorseTail
            · subst worse
              have hThis := hOrd proposer
              rw [hRem] at hThis
              unfold ProposalListOrdered at hThis
              cases hThis with
              | cons hHead _ =>
                  exact False.elim
                    ((prefM.irrefl proposer better) (prefM.trans proposer hPref (hHead better hBetter)))
            · exact hWorseTail
          · rw [hOtherRem m hm] at hBetter ⊢
            exact hLow m hBetter hWorse hPref
        constructor
        · intro m w hHeldNext
          by_cases hw : w = proposed
          · subst w
            rcases hChange with hVacant | hOccupied
            · rcases hVacant with ⟨_, hNextHeld⟩
              have hm : m = proposer := Option.some.inj (hHeldNext.symm.trans hNextHeld)
              subst m
              rw [hNextRem]
              exact hProposedNotTail
            · rcases hOccupied with ⟨old, hOldHeld, hNextHeld⟩
              have hmChoose : m = chooseBetterForW prefW proposed proposer old :=
                Option.some.inj (hHeldNext.symm.trans hNextHeld)
              unfold chooseBetterForW at hmChoose
              by_cases hPref : prefW.pref proposed proposer old
              · simp [hPref] at hmChoose
                subst m
                rw [hNextRem]
                exact hProposedNotTail
              · simp [hPref] at hmChoose
                subst m
                have hOldNe : old ≠ proposer := by
                  intro hOldEq
                  subst old
                  exact hFree proposed hOldHeld
                rw [hOtherRem old hOldNe]
                exact hHeld old proposed hOldHeld
          · have hHeldOld : st.matching.held w = some m := by
              rw [hOtherHeld w hw] at hHeldNext
              exact hHeldNext
            by_cases hm : m = proposer
            · subst m
              exact False.elim (hFree w hHeldOld)
            · rw [hOtherRem m hm]
              exact hHeld m w hHeldOld
        · intro m w hFull hNotRem
          by_cases hm : m = proposer
          · subst m
            by_cases hw : w = proposed
            · subst w
              rcases hChange with hVacant | hOccupied
              · rcases hVacant with ⟨_, hNextHeld⟩
                exact ⟨proposer, hNextHeld, Or.inl rfl⟩
              · rcases hOccupied with ⟨old, _, hNextHeld⟩
                exact ⟨chooseBetterForW prefW proposed proposer old, hNextHeld,
                  choose_weak_incoming proposed proposer old⟩
            · have hOldNot : w ∉ st.rem proposer := by
                rw [hRem]
                intro hMem
                rcases (List.mem_cons.mp hMem) with hEq | hTail
                · exact hw hEq
                · rw [hNextRem] at hNotRem
                  exact hNotRem hTail
              rcases hBest proposer w hFull hOldNot with ⟨held, hHeldW, hWeak⟩
              have hNextHeld : next.matching.held w = some held := by
                rw [hOtherHeld w hw]
                exact hHeldW
              exact ⟨held, hNextHeld, hWeak⟩
          · have hOldNot : w ∉ st.rem m := by
              rw [hOtherRem m hm] at hNotRem
              exact hNotRem
            rcases hBest m w hFull hOldNot with ⟨held, hHeldW, hWeak⟩
            by_cases hw : w = proposed
            · subst w
              rcases hChange with hVacant | hOccupied
              · rcases hVacant with ⟨hOldNone, _⟩
                rw [hOldNone] at hHeldW
                cases hHeldW
              · rcases hOccupied with ⟨old, hOldHeld, hNextHeld⟩
                have hHeldEq : held = old := Option.some.inj (hHeldW.symm.trans hOldHeld)
                subst held
                exact ⟨chooseBetterForW prefW proposed proposer old, hNextHeld,
                  weak_trans proposed (chooseBetterForW prefW proposed proposer old) old m
                    (choose_weak_old proposed proposer old) hWeak⟩
            · have hNextHeld : next.matching.held w = some held := by
                rw [hOtherHeld w hw]
                exact hHeldW
              exact ⟨held, hNextHeld, hWeak⟩
    have inv_open : Inv (openingState fullList) := by
      constructor
      · intro m
        exact (hSound m).2
      constructor
      · intro m better worse _ hWorse _
        simpa [openingState] using hWorse
      constructor
      · intro m w hHeld
        simp [openingState, emptyMatching] at hHeld
      · intro m w hFull hNotRem
        exact False.elim (hNotRem (by simpa [openingState] using hFull))
    have run_preserves :
        ∀ {start finish : ProposalState Man Woman} {sched : List Man},
          ProposalRun prefW start sched finish → Inv start → Inv finish := by
      intro start finish sched hRun'
      induction hRun' with
      | nil st =>
          intro h
          exact h
      | cons hStep hTail ih =>
          intro h
          exact ih (step_preserves _ h hStep)
    have hInvState : Inv state := run_preserves hRun inv_open
    rcases hInvState with ⟨_, hLowState, hHeldState, hBestState⟩
    unfold Stable BlockingPair ManPrefersCurrent
    intro m w hBlock
    rcases hBlock with ⟨hMan, hWoman⟩
    cases hPartner : partnerOfMan state.matching m with
    | none =>
        have hFree : freeMan state.matching m := by
          intro w' hHeld
          have hExists : ∃ w' : Woman, state.matching.held w' = some m := ⟨w', hHeld⟩
          unfold partnerOfMan at hPartner
          simp [hExists] at hPartner
        have hRemEmpty : state.rem m = [] := hQuiet m hFree
        have hNotRem : w ∉ state.rem m := by
          rw [hRemEmpty]
          simp
        rcases hBestState m w (hComplete m w) hNotRem with ⟨held, hHeldW, hWeak⟩
        rw [hHeldW] at hWoman
        exact weak_strict_false w held m hWeak hWoman
    | some partner =>
        have hHeldPartner : state.matching.held partner = some m := by
          unfold partnerOfMan at hPartner
          by_cases hExists : ∃ w' : Woman, state.matching.held w' = some m
          · simp [hExists] at hPartner
            have hChooseEq : Classical.choose hExists = partner := by
              simpa using hPartner
            rw [← hChooseEq]
            exact Classical.choose_spec hExists
          · simp [hExists] at hPartner
        simp [hPartner] at hMan
        have hPartnerNotRem : partner ∉ state.rem m := hHeldState m partner hHeldPartner
        have hWNotRem : w ∉ state.rem m := by
          intro hWRem
          exact hPartnerNotRem (hLowState m hWRem (hComplete m partner) hMan)
        rcases hBestState m w (hComplete m w) hWNotRem with ⟨held, hHeldW, hWeak⟩
        rw [hHeldW] at hWoman
        exact weak_strict_false w held m hWeak hWoman
  · let prefM : StrictPreference PUnit.{u + 1} PUnit.{v + 1} :=
      { pref := fun _ _ _ => False
        decidablePref := fun _ _ _ => isFalse id
        irrefl := by
          intro _ _ h
          exact h
        trans := by
          intro _ _ _ _ h _
          exact False.elim h
        total := by
          intro _ x y hxy
          cases x
          cases y
          exact False.elim (hxy rfl) }
    let prefW : StrictPreference PUnit.{v + 1} PUnit.{u + 1} :=
      { pref := fun _ _ _ => False
        decidablePref := fun _ _ _ => isFalse id
        irrefl := by
          intro _ _ h
          exact h
        trans := by
          intro _ _ _ _ h _
          exact False.elim h
        total := by
          intro _ x y hxy
          cases x
          cases y
          exact False.elim (hxy rfl) }
    let fullList : PUnit.{u + 1} → List PUnit.{v + 1} := fun _ => [PUnit.unit]
    refine ⟨PUnit.{u + 1}, PUnit.{v + 1}, ⟨inferInstance⟩, ⟨inferInstance⟩,
      prefM, prefW, fullList, [], openingState fullList, PUnit.unit, PUnit.unit, ?_⟩
    constructor
    · intro m
      cases m
      constructor
      · simp [fullList]
      · simp [ProposalListOrdered, fullList]
    constructor
    · intro m w
      cases m
      cases w
      simp [fullList]
    constructor
    · exact ProposalRun.nil (openingState fullList)
    constructor
    · intro w h
      cases w
      simp [openingState, emptyMatching] at h
    constructor
    · simp [openingState, fullList]
    constructor
    · intro hQuietState
      have hFree : FreeManIn (openingState fullList).matching PUnit.unit := by
        intro w h
        cases w
        simp [openingState, emptyMatching] at h
      have hEmpty := hQuietState PUnit.unit hFree
      simp [openingState, fullList] at hEmpty
    · constructor
      · unfold ManPrefersCurrentNoDecidable ManPrefersOption partnerOfMan
        simp [openingState, emptyMatching]
      · unfold WomanPrefersOption
        simp [openingState, emptyMatching]
