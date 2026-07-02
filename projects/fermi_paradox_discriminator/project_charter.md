# Project Charter — fermi_paradox_discriminator (v1.0, 2026-05-06)

## Eigenquestion

What is the smallest 2026–2030 observable design (target selection +
instrument + null hypothesis + Bayesian update size) that would
discriminate at least one pair of major Fermi-paradox resolution
classes from observationally-equivalent to discriminated — and what is
the structural reason the existing literature has optimized for
**resolution-proposal** rather than **resolution-discrimination**?

## What this is NOT

- An enumeration or ranking of resolutions (Great Filter, Dark Forest,
  Rare Earth, Zoo, Berserker, Aestivation, etc.). Listing is the failure
  mode this project is designed to escape.
- A new resolution. The substrate is the **discriminator**, not the
  resolution.
- A SETI strategy memo. SETI vocabulary (radio surveys, technosignatures
  by frequency band, optical SETI) is admissible only as instances of a
  structural discriminator class.
- A Drake equation refinement. Plugging numbers into N = R* × f_p × n_e
  × f_l × f_i × f_c × L is the contamination this project must escape.
- A philosophical treatment of the anthropic principle.

## The anti-tautology constraint

A "discriminator" is not a discriminator if both resolutions it claims
to separate predict the SAME observation. The thesis must show, for
the proposed observable O and resolution-pair (R_a, R_b):

  Step 1: State R_a and R_b in vocabulary that does not presuppose O.
  Step 2: Derive the predicted observable distribution P(O | R_a) under
          R_a's structural commitments (not R_a's marketing label).
  Step 3: Derive P(O | R_b) similarly.
  Step 4: Show |P(O | R_a) − P(O | R_b)| exceeds the noise floor of
          the named instrument by a stated margin. The instrument
          must be Class I (deployed or first-light by 2030) or Class
          II (TRL ≥4 + decadal endorsement + design-now / fund-by-
          2030 / first-light-by-2035, e.g. HWO).
  Step 5: Specify the prior-to-posterior shift size on a pre-stated
          mixture of the two resolutions, and show it exceeds a
          publication-relevance threshold (e.g. ≥2 nats).

If any step is hand-waved, the thesis is a discriminator-in-name-only —
indistinguishable from a SETI press release. Score zero on the
Discrimination Math Gate.

The substitution test: replace "alien civilizations" with
"pre-100kya extinct human-tier civilizations on Earth that left no
artifact-grade record" — does the discriminator argument survive? If
yes, the framing is detection-of-extinct-tech-tier, not Fermi-specific,
and may be a stronger result. If no, what specifically about the
cosmic / interstellar context is load-bearing?

## Admissible outcomes

(1) **DESIGNED DISCRIMINATOR.** Specific resolution-pair named in
structural vocabulary; specific observable specified on a Class I
(≤2030) or Class II (TRL ≥4 / fund-by-2030 / first-light ≤2035,
HWO-class) instrument; the five-step derivation passes; the
structural reason the field has not pursued this discriminator is
named (institutional, instrumental, cognitive). Class II theses
that argue "the highest-leverage discriminator requires this
instrument; design now, fund by 2030, launch by 2035" are positive
findings — they convert resolution-discrimination into a fundable
program. This is the full positive bridge.

(2) **CONSTRUCTIVE OBSERVATIONAL EQUIVALENCE.** Constructive proof
that for SOME named resolution-pair, no Class I or Class II
instrument can produce a discriminator passing the five-step test —
these resolutions are *informationally closed* for the next
generation under the Bayesian update threshold. Major negative
finding; positive implication: the field's continuing to debate
that pair is rational only if the prior is doing all the work.

(3) **PARADOX MALFORMATION.** Constructive proof that the standard
formulation of the paradox conflates resolution classes that are
not parameter-distinguishable in the Drake/anthropic framework — the
paradox is malformed because the relevant parameters are not
identifiable from any cosmologically achievable observation set. Major
reframe.

(4) **META-FINDING ON FIELD OPTIMIZATION.** Constructive
characterization of why the literature has optimized for
resolution-proposal — the structural property of the field
(citation-economy, narrative-friendly, low-cost-to-publish, no
observational accountability) that produced the asymmetry between
resolution-richness and discriminator-paucity. This is the load-bearing
meta-claim of the project.

## Forbidden frames (cold-shot routing)

The Erdős seed is forbidden from: SETI strategy literature,
Drake-equation literature, anthropic-principle philosophy, futurology,
science-fiction (Liu Cixin / Banks / Clarke / Lem), grabby-aliens
debate, simulation hypothesis. These domains have ossified frames the
apparatus must not import.

The seed should come from: Bayesian model comparison and weak-signal
detection theory; dark-matter direction-detection methodology
(WIMP/axion experiments — how do you discriminate models when the
signal is at the noise floor?); survey design and observation-selection
correction in cosmology; hypothesis-test design under strong selection
effects (medical-trial methodology, lensed-quasar surveys);
information-theoretic limits on inferential discrimination
(Cramér–Rao, Fisher information, mutual information).

## Run command

  make loop PROJECT=fermi_paradox_discriminator
