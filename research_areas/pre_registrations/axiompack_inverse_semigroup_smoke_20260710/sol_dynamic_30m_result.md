# Sol-medium regular-unary AxiomPack result (2026-07-10)

## Frozen run

- Campaign: `campaign_sol_dynamic_30m.md`
- Hetzner attempt: `/tmp/axiompack_sol_dynamic_20260710_successor/attempt-555625dd018447359304289162803356`
- Context: `b3e20c7eabf6e4f403a3baf08a6bebbe6fda1855d3bc311ef6381aebed549b3e`
- Search surface: 47 canonical models, 71 formulas, 39 theory nodes
- Subscription usage: eight Sol 5.6 medium navigation turns, three governed
  Lean turns, and one GPT-5.5 medium post-freeze review; metered API charge was
  zero.

The navigator first previewed an extent-four presentation; the host rejected it
because the bounded equational plus finite-structure baseline explained every
consequence. It then froze this ordered exact-two presentation:

1. `inv(x) * x = x`
2. `x * y = y * x`

The regular-unary base includes associativity and a selected inverse witness:

- `inv(x) = (inv(x) * x) * inv(x)`;
- `x = (x * inv(x)) * x`.

The navigator ranked these boundary targets:

1. `x * x = inv(x)`;
2. `inv(x * x) = x`.

## Historical boundary result

The first target earned `proved_exact_two_synergy` under the baseline frozen
with the campaign.

- Z3 found no countermodel at carrier sizes four or five (receipts `af5260ea…`
  and `6b5a7e33…`).
- Isabelle/Sledgehammer returned `by fastforce`; a complete theory rebuild was
  kernel-accepted (receipt `db853a50…`).
- The ordinary LeanMill `solve_adhoc` path produced a proof, and full, empty,
  and both leave-one-out arms were replayed. The provider-free governance
  recheck retained one attributed proof (receipt `80992c06…`).
- Concrete finite models satisfy the base plus either singleton premise while
  falsifying the target, so neither premise alone implies it (receipt
  `c94e241b…`).

The short derivation explains the result. The selected-inverse-right base law
and absorption give `inv(x) = x * inv(x)`; commutativity and absorption then
give `inv(x) = x`. Substituting that equality into absorption yields
`x*x = x = inv(x)`.

This collapses the selected inverse to the identity and the product to an
idempotent commutative semigroup, i.e. a semilattice. Standard inverse-semigroup
references describe inverse semigroups through commuting idempotents and
semilattices; see [Encyclopedia of Mathematics](https://encyclopediaofmath.org/wiki/Inversion_semi-group)
and [Lawson's inverse-semigroup notes](https://www.macs.hw.ac.uk/~markl/3-inverse.pdf).
The implication is therefore assessed as elementary/likely known; this run
supports no theorem-novelty claim.

## Provider-free post-run repricing

The boundary proof exposed a deduction missed by the campaign's four-rewrite
baseline. The corrected `leanmill.bidirectional_equational_deduction.v5`
searches for a common reduct of the target sides for at most eight rewrite
steps, prioritizes contractions under a hard state cap, and emits replayable
steps. It contains no inverse-semigroup rule.

Repricing the exact 47-model/71-formula context under v5 takes about 0.45
seconds on the development machine. All four joint consequences, including both navigator
targets, receive bounded equational witnesses. The residual consequence set
and residual identification bits are both zero. The first target's finite,
Isabelle, Lean, attribution, and singleton-countermodel receipts remain valid,
but they no longer confer discovery credit: the host can derive the result at
the cheap baseline tier.

## Second target and apparatus findings

Z3 also found no size-four or size-five countermodel to the second target
(receipts `c54d9176…` and `30bf1a81…`). The frozen one-attempt Isabelle cap was
then exhausted, and the older boundary loop stopped before Isabelle or Lean
could attempt that target. Its historical formal-peer status remains
unresolved. Current v5 replay derives it cheaply, so completing those old
verifier legs would add no useful discriminator.

Two implementation corrections follow from the run:

- an exhausted optional verifier allowance now records
  `skipped_budget_exhausted` and lets later targets/cascade stages continue;
- post-freeze result packet v3 includes the frozen base formulas, signature,
  primitive semantics, and eigenquestion. The initial GPT-5.5 review saw only
  base hashes, searched anonymous `op0`/`op1` strings, and returned
  `not_located_in_bounded_review` (receipt `995ecdd2…`). Future literature and
  explanation passes receive the ambient theory after candidate freeze.

The boundary result is `582d23f2…`; its historical completion status is
`campaign_stopped` because of the optional-peer control bug. The first target's
Isabelle, Lean, attribution, singleton-countermodel, and recheck receipts remain
valid and content-bound.

## After-action review

### Verdict

The campaign validated the dynamic navigator, ranked boundary selection,
finite-model checks, two formal kernels, causal premise ablation, and
post-freeze interpretation. Its mathematical output is a recovery of a cheap
semilattice-collapse consequence. It is not a frontier theorem.

The campaign's main eigenquestion remains unanswered. The false residual made
the seed chart appear adequate, so `propose_frontier_formula`—the agency surface
the experiment was meant to test—was never exercised.

### What the run expected and what occurred

The intended discriminator was whether Sol could leave the exhausted seed
chart and nominate an exact-two consequence with nonzero residual information
after the named cheap baseline. Sol did nominate such a consequence under the
frozen baseline. That baseline had an arbitrary four-step horizon and failed to
reuse a short intermediate equality. Extending the same domain-neutral
deduction procedure to eight steps removes all residual information.

The navigator therefore optimized the criterion it was shown. Its quick freeze
is weak evidence of low difficulty; the decisive evidence is the short
replayable derivation and the standard semilattice interpretation. Elapsed time
must remain an observation, never a novelty gate.

### Category error in the old stop rule

The run conflated four independent boundaries:

1. **Domain frontier:** the campaign points at an under-explored part of a
   mathematical area.
2. **Semantic frontier:** a formula separates models in the current finite
   context after a declared structural baseline.
3. **Deductive frontier:** the consequence survives the declared bounded
   deduction and proof-complexity tiers.
4. **Knowledge frontier:** the result is not already catalogued, routinely
   derivable, or readily recoverable from model priors and public sources.

This candidate crossed only the frozen semantic boundary. A frontier domain
does not make every consequence frontier mathematics, and cold anonymous
generation does not establish independence from training memory.

### Trace-based root cause and harness iatrogenesis

The eight navigator receipts show a methodical leaf rather than random
nomination. Sol paged through all 39 theory nodes, inspected two groups of
formula profiles, rejected a first pair after the host reported zero residual,
then previewed the commutativity/absorption pair. It froze only after the host
reported two residual targets, calling the information-per-cost “modest” and
explaining that this was the only inspected positive candidate. Its final turn
used the advertised `finish` exit because one finalist already existed.

The causal chain was:

1. the four-step baseline misclassified two short deductions as residual;
2. the cold manifest hid the three frozen base equations, so the leaf could not
   independently reconstruct the collapse and had to trust the host score;
3. the preview reported information-per-cost `0.03867846`, below the configured
   `0.05` floor, but the floor was implemented as a patience signal rather than
   a finalist-quality condition;
4. six of eight navigation turns were spent on topology, formula inspection,
   and two previews, making the first positive residual salient near the
   horizon;
5. the prompt presented formula expansion mainly as an escape when the seed
   grammar expressed no distinction, while this false-positive residual made
   the seed chart appear adequate;
6. the named `finish` affordance made “one finalist exists” a natural stopping
   reason even though `max_finalists` was four.

The dominant fault was the host's false residual. The prompt and action economy
amplified it. Sol's rationale identified one constant-unary generator before a
host preview disposed of that region, but this trace does not isolate anonymity
as the cause of the avoidance. Exact-two arity was the declared campaign
question, although it should not become a default for broader novelty search.
Keeping literature sealed until freeze was appropriate; exposing the anonymous
base equations was the missing mathematical context.

Corrections now expose the frozen base equations with positional symbols,
state explicitly that finite residual is necessary but insufficient, and make
formula expansion legitimate when seed survivors are routine. Verification
also caught a second iatrogenic risk introduced by the stronger baseline: a
20,000-state negative search made two navigation tests take 71 and 137 seconds.
The ordered search now caps each side at 4,096 states, allows size-increasing
rewrites only at the root or a direct child, and receipts the explored state
counts. The same two tests take about four seconds while both frozen deductions
remain found.

Fable's independent AAR review identified the remaining recurrence path: a
state-cap-saturated negative search was still counted as positive residual.
`theory_residual_information_yield.v3` now separates such targets as
`cheap_baseline_inconclusive`; they receive no residual bits, cannot justify a
freeze, and cannot mint a zero-residual conflict. The existing presentation
preview already exposes the baseline witnesses and inconclusive receipts, so no
duplicate navigator tool was added.

### Discovery versus recovery

The apparatus should record two facts separately:

- **search provenance:** whether the candidate was generated before theory
  names, literature, or sealed source rows were revealed;
- **knowledge relation:** `catalogued_recovery`, `routine_reconstruction`,
  `discovery_candidate`, or `unresolved`.

This run has cold search provenance and a `routine_reconstruction` knowledge
relation. A source match establishes recovery. Failure to find a source does
not establish discovery. Training-prior dependence cannot be observed
directly, so an independent closed-book recognition/derivation probe can only
measure recoverability: quick recognition lowers the claim; failure leaves the
status unresolved. No closed-book probe was run here; its status is
`not_attempted`. The short host derivation and semilattice mapping already
suffice for the weaker routine-reconstruction disposition.

### Corrected stopping and promotion frame

Candidate freeze is a provisional boundary nomination. Spend beyond the cheap
host tier should be selected from a lazily filled receipted vector, without
blending it into one score:

- semantic residual after the versioned baseline;
- shortest host deduction/proof-description tier;
- primitive structural-collapse class;
- persistence across carrier sizes or semantic strata;
- exact premise necessity;
- post-freeze external-knowledge and closed-book recoverability status;
- downstream proof or task lift when an axiom is proposed for promotion.

Only the cheap available coordinates—residual, deduction disposition, and
primitive collapse—belong before nomination. Cross-size, premise-necessity,
external-knowledge, and downstream-lift coordinates are filled only after a
candidate survives the earlier tier; `unavailable` is preserved rather than
guessed.

Zero deductive residual is a hard rejection for a discovery campaign. Primitive
collapse and high recoverability normally return the leaf to formula expansion
or receipted refusal, unless the campaign explicitly targets that slice.
Cross-size persistence and exact-two dependence strengthen a theorem but do not
establish novelty.

### Next move

Do not rerun this frozen pack. Preserve its receipts as a baseline regression.
One bounded, zero-boundary-spend apparatus discriminator should use the full fix
stack and ask only whether the leaf authors a new formula or returns a
receipted null. It is not a mathematical-novelty campaign. After that, move the
novelty hunt to a semantics-richer executable substrate unless an authored
formula creates a new post-v5 residual profile. Source/recoverability screening
stays after freeze and before costly formal work.
