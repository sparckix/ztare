# AxiomPack GP-251 — 20-minute anonymous frontier smoke

Prepared 2026-07-10 before any model dispatch.

## Hypothesis

Within the frozen 20-minute campaign envelope, an agent using only the
anonymous exact context can freeze at least one two-law presentation that
passes host-checked independence, noncollapse, and joint-only-consequence
gates, then nominate a boundary query that separates finite-bound structure
from a consequence that lifts.

## Eigenquestion

Does exact anonymous theory cartography give an agent enough usable structure
to select a small axiom pack worth testing beyond the enumerated size-2/3
context?

## Discriminating test

Run
`research_areas/pre_registrations/axiompack_gp251_smoke_20260710/campaign.md`
on the Hetzner Lean node through the canonical `leanmill campaign` door with
Codex gpt-5.5 at low effort. The campaign has 9
cumulative navigator-call slots before protected later phases, at most 2
boundary queries, 2 fixed-size SMT calls, and 1 governed Lean attempt. After
the anonymous finalists freeze, execute only their selected size-4/5 and
conditional Lean checks while budget remains.

Deployment and execution use the named `deploy/vps_run.sh` actions and the
curated sync manifest. The run does not execute on the campaign author's
workstation.

Classify the result by the first failing boundary:

1. no valid finalist: navigator/workbench interaction bottleneck;
2. finalist refuted at size 4/5: finite-bound instability;
3. no larger countermodel but Lean unresolved: formal-lift bottleneck;
4. `proved_unattributed`: consequence did not depend on the proposed pack;
5. `proved_attributed`: conditional consequence survived matched attribution.

## Success criterion

At least one anonymous finalist is frozen with host-checked independence,
extent of at least two canonical models, and a nonempty joint-only consequence
set; at least one selected boundary query then returns a concrete larger-model
counterexample or a governed, premise-attributed conditional proof.

## Kill conditions

- the agent cannot use the advertised actions to freeze a valid presentation;
- every frozen presentation is immediately redundant, collapsed, or lacks a
  joint-only consequence;
- selected queries merely recover facts already true with no proposed premise;
- any result depends on interpretation names or literature exposed before
  freeze;
- the run exhausts budget without leaving replayable finalists and receipts.

## Claim boundary

This smoke can locate an interaction, finite-bound, or formal-lift bottleneck.
It cannot establish mathematical novelty, unrestricted consistency, or an
advantage over other conjecture systems. Literature interpretation begins only
after finalist freeze and boundary recording.
