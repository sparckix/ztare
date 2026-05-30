-- Curriculum variant: LeraySelfTaxProfilePriceStream → LeraySelfTaxProfilePriceStream_OneD
-- Transform: DIMENSION_REDUCE (drop spatial dimensions (3D → 1D))
-- HONEST CAVEAT: template-based; may be ill-typed.
-- Codex must validate before sending to typed_endpoint_pack.

-/
inductive LeraySelfTaxPriceComponent where
  | selfTax
  | crossDefect
  | coherence
deriving DecidableEq, Repr

/-- A fixed LP/profile price stream for the Leray self-tax limit obligation.

The three prefix price fields are the declared finite-prefix prices for the
assembled self-tax, cross-profile/cross-shell defect, and coherence/inner-product
terms.  The three limit fields are declared before payoff scoring; the file
does not choose a PDE topology or a profile decomposition. -/
structure LeraySelfTaxProfilePriceStream_OneD where
  prefixPayoff : ℕ → Real
  prefixSelfTaxPrice : ℕ → Real
  prefixCrossDefectPrice : ℕ → Real
  prefixCoherencePrice : ℕ → Real
  payoffLimit : Real
  selfTaxLimitPrice : Real
  crossDefectLimitPrice : Real
  coherenceLimitPrice : Real
  profileTopologyDeclaredBeforePayoff : Prop
  profileStreamDeclaredBeforePayoff : Prop
  prefixComponentPricesDeclaredBeforePayoff : Prop
  limitComponentPricesDeclaredBeforePayoff : Prop
  noPosthocPayoffDependentStreamChoice : Prop

/-- Zero scalar stream used only to refute assumption-free macroscopic
triangulation shortcuts.  It is not a PDE object and supplies no LSC receipt. -/
def zeroLeraySelfTaxProfilePriceStream_OneD : LeraySelfTaxProfilePriceStream_OneD where
  prefixPayoff := fun _ => 0
  prefixSelfTaxPrice := fun _ => 0
  prefixCrossDefectPrice := fun _ => 0
  prefixCoherencePrice := fun _ => 0
  payoffLimit := 0
  selfTaxLimitPrice := 0
  crossDefectLimitPrice := 0
  coherenceLimitPrice := 0
  profileTopologyDeclaredBeforePayoff := True
  profileStreamDeclaredBeforePayoff := True
  prefixComponentPricesDeclaredBeforePayoff := True
  limitComponentPricesDeclaredBeforePayoff := True
  noPosthocPayoffDependentStreamChoice := True

/-- Total finite-prefix declared price. -/
def leraySelfTaxPrefixPrice
    (S : LeraySelfTaxProfilePriceStream_OneD) (n : ℕ) : Real :=
  S.prefixSelfTaxPrice n +
    S.prefixCrossDefectPrice n +
      S.prefixCoherencePrice n

/-- Total declared limiting price. -/
def leraySelfTaxLimitPrice
    (S : LeraySelfTaxProfilePriceStream_OneD) : Real :=
  S.selfTaxLimitPrice + S.crossDefectLimitPrice + S.coherenceLimitPrice

/-- False theorem shape surfaced by graph-only macroscopic triangulation. -/
def MacroscopicTriangulationLimitCandidate : Prop :=
  ∀ S : LeraySelfTaxProfilePriceStream_OneD,
    sharpTarget ≤ leraySelfTaxLimitPrice S + S.payoffLimit

/-- The macroscopic triangulation shortcut is false without the real
component-LSC/continuum-coupling receipts.  The zero scalar stream already
violates it. -/
theorem not_macroscopic_triangulation_limit_candidate :
    ¬ MacroscopicTriangulationLimitCandidate := by
  intro h
  have hzero := h zeroLeraySelfTaxProfilePriceStream_OneD
  norm_num [MacroscopicTriangulationLimitCandidate,
    zeroLeraySelfTaxProfilePriceStream_OneD, leraySelfTaxLimitPrice, sharpTarget] at hzero

/-- Finite-prefix no-arbitrage for the assembled Leray self-tax ledger. -/
def LeraySelfTaxFinitePrefixNoArbitrage
    (S : LeraySelfTaxProfilePriceStream_OneD) : Prop :=
  ∀ n, S.prefixPayoff n ≤ leraySelfTaxPrefixPrice S n

/-- The limiting payoff is visible from finite prefixes. -/
def LeraySelfTaxPayoffApproximatedByPrefixes
    (S : LeraySelfTaxProfilePriceStream_OneD) : Prop :=
  ∀ ε : Real, 0 < ε → ∃ n, S.payoffLimit ≤ S.prefixPayoff n + ε

/-- Tail-visible payoff approximation.

The weaker `∃ n` prefix approximation can be satisfied by one early prefix.
The profile-limit topology needs eventual visibility: after any prefix cutoff,
some later prefix must still see the limiting payoff. -/
def LeraySelfTaxPayoffTailApproximatedByPrefixes
    (S : LeraySelfTaxProfilePriceStream_OneD) : Prop :=
  ∀ N : ℕ, ∀ ε : Real, 0 < ε →
    ∃ n : ℕ, N ≤ n ∧ S.payoffLimit ≤ S.prefixPayoff n + ε

/-- Tail-visible payoff approximation implies the weaker prefix approximation
used by the generic profile-limit LSC adapter. -/
theorem payoff_approximated_by_prefix_of_tail_approx
    (S : LeraySelfTaxProfilePriceStream_OneD)
    (h : LeraySelfTaxPayoffTailApproximatedByPrefixes S) :
    LeraySelfTaxPayoffApproximatedByPrefixes S := by
  intro ε hε
  obtain ⟨n, _, hn⟩ := h 0 ε hε
  exact ⟨n, hn⟩

/-- Single early-spike stream used to separate weak prefix visibility from
tail visibility.  The limiting payoff is seen by prefix `0`, but no later
prefix sees it. -/
def weakButNotTailPayoffApproxStream :
    LeraySelfTaxProfilePriceStream_OneD where
  prefixPayoff := fun n => if n = 0 then 1 else 0
  prefixSelfTaxPrice := fun _ => 1
  prefixCrossDefectPrice := fun _ => 0
  prefixCoherencePrice := fun _ => 0
  payoffLimit := 1
  selfTaxLimitPrice := 1
  crossDefectLimitPrice := 0
  coherenceLimitPrice := 0
  profileTopologyDeclaredBeforePayoff := True
  profileStreamDeclaredBeforePayoff := True
  prefixComponentPricesDeclaredBeforePayoff := True
  limitComponentPricesDeclaredBeforePayoff := True
  noPosthocPayoffDependentStreamChoice := True

/-- Weak prefix payoff approximation is strictly weaker than tail-visible
p