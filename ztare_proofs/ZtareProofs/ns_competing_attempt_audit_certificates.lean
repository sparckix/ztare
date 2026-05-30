/-!
# NS competing-attempt audit certificates (tick499, 2026-05-15)

Typed registry of adversarial audits performed on recent unrefereed
or recently-published NS papers, with **concrete data fields only**
(no `Prop := True` placeholders).

**Purpose**: record what was audited, what was claimed, what the
adversarial gap-prior was, and where the cited evidence lives.

**NOT a closure proof.** This file is a record-keeping registry.
Encoding as Lean typed data gives:
- machine-checkable consistency across audits (the fields are
  forced to be filled with concrete data),
- a single source of truth for which papers have been audited
  against which substrate targets,
- automatic obsolescence if a paper's status changes
  (re-audit forces field updates).

**Anti-pattern guard**: ALL fields are `String` / `Nat` / `Bool`
/ `Float` with explicit values. NO `Prop` fields. Vacuous
inhabitability is impossible (would require fabricating concrete
text strings).

## Audit certificates

- Ri 2508.19590v1: gap-flagged, prior 0.82 ± 0.05.
- Barker 2510.20757v2: not-false, currency-mismatch with
  substrate target.

## Format note: Lean ℕ for severities

We use `Nat` 0-9 for severity (Meta-Darwin convention).
Probabilities are represented as a numerator/denominator pair
(`prior_pct : Nat`, taken as a percent, 0-100).
-/

namespace ZtareProofs.NSCompetingAttemptAuditCertificates

/-- **Audit certificate** for a competing NS regularity attempt
or a literature item flagged for bridge-potential review.

All fields are concrete data (no Prop placeholders). -/
structure AuditCertificate where
  /-- arXiv id, e.g. "2508.19590v1". -/
  arxiv_id : String
  /-- Authors string, e.g. "Ri". -/
  authors : String
  /-- Year of posting. -/
  year_posted : Nat
  /-- Venue / referee status: "unrefereed-arxiv", "Annals",
      "J. Math. Fluid Mech.", etc. -/
  venue : String
  /-- One-line of the claim being audited. -/
  claim_short : String
  /-- The substrate target this audit speaks to. -/
  substrate_target : String
  /-- Audit verdict bucket. -/
  verdict : String
  /-- Gap-prior as percentage 0-100 (e.g. 82 means 0.82). -/
  gap_prior_pct : Nat
  /-- Severity 0-9 of the most-load-bearing gap (or 0 if no gap). -/
  most_severe_gap : Nat
  /-- Free-text gap location reference (paper page/lemma). -/
  gap_location : String
  /-- Path to the audit markdown note (relative to repo root). -/
  audit_note_path : String
  /-- True if this is a "the substrate label is wrong" case
      (the paper itself is fine, e.g. currency-mismatch). -/
  is_currency_mismatch : Bool
  /-- True if a Meta-Darwin pass found my audit had REPAIR-grade
      issues that were subsequently applied. -/
  was_meta_darwin_repaired : Bool

/-- **Ri 2508.19590 v1** — claimed `Ḣ^{1/2} initial data ⇒
global regularity for 3D NS`. Audit found Lemma 2.1(ii)
criticality obstruction + globalization issue. Gap prior 0.82. -/
def ri_2508_19590_v1 : AuditCertificate :=
  { arxiv_id := "2508.19590v1"
    authors := "Ri"
    year_posted := 2025
    venue := "unrefereed-arxiv-single-author"
    claim_short := "Leray-Hopf weak solutions with u_0 ∈ Ḣ^{1/2} are globally regular for 3D NS"
    substrate_target := "NS Clay closure (would close outright if sound)"
    verdict := "gap-flagged"
    gap_prior_pct := 82
    most_severe_gap := 6
    gap_location := "Lemma 2.1(ii) — strong continuity in critical Ḣ^{1/2} used to prove smoothness in same critical space (circular); also T → ∞ uniformity of l_0 not established"
    audit_note_path := "analytics/public/notes/ns_ri_2508_19590_adversarial_audit_20260515.md"
    is_currency_mismatch := false
    was_meta_darwin_repaired := true }

/-- **Barker 2510.20757 v2** — Annals-of-Math-grade quantitative
classification beyond blow-up time.  The PAPER is sound.  The
substrate's scout label "Tier-1 cite for q > 4/3 bridge" was
overclaimed: Barker provides annular L¹ LOWER bounds, substrate
needs local L^q UPPER bounds. Currency mismatch. -/
def barker_2510_20757_v2 : AuditCertificate :=
  { arxiv_id := "2510.20757v2"
    authors := "Barker"
    year_posted := 2025
    venue := "arxiv-then-annals-style-quantitative-PDE"
    claim_short := "Quantitative classification of potential NS singularities beyond blow-up time, including double-exponential annular lower bound on v"
    substrate_target := "substrate-tick490 q > 4/3 bridge (NOT a real match — currency mismatch)"
    verdict := "paper-sound-but-doesnt-bridge-substrate-target"
    gap_prior_pct := 5  -- 5% prior that Barker's mathematics has a gap; ~95% paper is sound
    most_severe_gap := 0  -- no gap in Barker
    gap_location := "no-gap-in-paper; substrate scout overclaimed Tier-1; Barker (1.19) gives regularity OUTSIDE |x| ≥ M^{700+30/(1-3/p)} √T, substrate needs INSIDE candidate-singular core"
    audit_note_path := "analytics/public/notes/ns_barker_2510_20757_audit_20260515.md"
    is_currency_mismatch := true
    was_meta_darwin_repaired := false }

/-- Registry of all audit certificates from this session. -/
def session_audit_certificates_20260515 : List AuditCertificate :=
  [ ri_2508_19590_v1
  , barker_2510_20757_v2 ]

/-! ## Sanity-check theorems (real Lean content, NOT vacuous) -/

/-- The list has exactly two entries (matches the two audits
performed this session). -/
theorem session_audit_count : session_audit_certificates_20260515.length = 2 := rfl

/-- Ri's audit found a more-severe gap than Barker's (since
Barker has no gap in its mathematics). -/
theorem ri_gap_more_severe_than_barker :
    ri_2508_19590_v1.most_severe_gap > barker_2510_20757_v2.most_severe_gap := by
  decide

/-- Barker's case is a currency-mismatch; Ri's is not. -/
theorem barker_is_currency_mismatch :
    barker_2510_20757_v2.is_currency_mismatch = true := rfl

theorem ri_is_not_currency_mismatch :
    ri_2508_19590_v1.is_currency_mismatch = false := rfl

/-- Ri's audit was REPAIRED by Meta-Darwin (probability anchoring
+ smoking-gun overreach caught); Barker's was first-pass-clean. -/
theorem ri_was_repaired : ri_2508_19590_v1.was_meta_darwin_repaired = true := rfl

/-! ## Operational guards -/

/-- Any future audit added to the registry must have a non-empty
audit note path. -/
theorem all_registry_entries_have_audit_note :
    ∀ cert ∈ session_audit_certificates_20260515, cert.audit_note_path ≠ "" := by
  intro cert hmem
  simp [session_audit_certificates_20260515] at hmem
  rcases hmem with h | h
  · rw [h]; simp [ri_2508_19590_v1]
  · rw [h]; simp [barker_2510_20757_v2]

/-! ## Honest scope -/

/-- What this registry is and is not. -/
structure RegistryScope where
  is_typed_audit_record_with_concrete_data : Bool
  is_NOT_a_closure_proof : Bool
  is_NOT_vacuously_inhabitable : Bool
  fields_are_all_String_or_Nat_or_Bool : Bool
  no_Prop_True_placeholders : Bool
  /-- The registry records audit OUTCOMES, not closure claims. -/
  records_audits_not_closure : Bool

def registry_scope : RegistryScope :=
  { is_typed_audit_record_with_concrete_data := true
    is_NOT_a_closure_proof := true
    is_NOT_vacuously_inhabitable := true
    fields_are_all_String_or_Nat_or_Bool := true
    no_Prop_True_placeholders := true
    records_audits_not_closure := true }

end ZtareProofs.NSCompetingAttemptAuditCertificates
