# The canonical-coordinates reframe (2026-07-22)

Operator's challenge, verbatim principles applied. Verdict first: **the frame was wrong, and the week's receipts prove it.** We optimized pixel-exact replay of a *rendering* while the game's actual state is a handful of latent coordinates. Every "hard" law we fought is a shadow of a trivial law in the right space.

## The diagnosis under each principle

**"Miraculous cancellations are shadows of hidden linear/equivariant structure in a larger space."**
The 84-cell simultaneous bar flip, the 4-cell pip decrements, the "restoration" family itself — all shadows of scalar updates (`energy = E_max; reserves -= 1`) pushed through a fixed rendering homomorphism `render: (energy, reserves, mode, pos) → grid regions`. We built an operator family (pattern_write), a memorizer cage, and a guard cascade to imitate, cell by cell, what is ONE assignment in the latent space. The machinery is sound — and it is the shadow-theater's stagehand.

**"Find the canonical coordinates" / "replace identities with mechanisms."**
Measured canonical state: avatar position on the 5-stride lattice (~65 cells/level), level marker, key-mode bit, energy scalar (~21 values), reserve count (~3). The transition law in these coordinates is a small labeled graph plus a few special edges (portal, warps, key-flip). The pixel identities we've been fitting (which cells turn 11) are not mechanisms; `energy -= cost` is a mechanism.

**"Concentrate the mystery / study the exceptional set."**
The exceptional set — non-stride transitions (portal, warps), mode-changing transitions (key pickup), and the single t=47 state where the display box changes and the refill law suspends — is exactly the level-clearing physics. This week's pipeline treated each exceptional row as *noise to guard against* (I literally ceded action-2 to dodge one such state). Their principle inverts this: the 27 portal rows deserve more modeling attention than the 335 bar rows, not less. The residual-support ranking (8a-6) optimizes the wrong thing at the top of the stack: support counts rows; the mystery concentrates in the rows with the least support.

**"Expand before you simplify."**
Lift first: append derived latent coordinates to the observation (position, mode, scalars) — the repo's own `alpha`/factor machinery is exactly this and already exists (`compiled_fiber_planning`: controlled base, finite configuration, ordered feasibility = position, mode, energy!). The failure is architectural placement: **identification runs in pixel space; only planning gets factors.** Expansion (latent features available to the law-miner) would let one-line laws replace guard cascades.

**"Don't attack complexity directly / change viewpoint until complexity is a consequence of structure."**
In canonical coordinates: HUD laws = consequences of scalar mechanics + rendering (equivariance machinery already in-repo can certify the rendering map); the "compound row" problem that stalled the delta chain *disappears* (one latent step renders as bar+pip+sprite changes — compound only in pixel space); the 80.4% duplication we quotiented is near-total collapse (16.5k rows → a few hundred distinct canonical transitions); and the win is a shortest-path query on a ~130-node graph.

## Why this explains the stall precisely

1. **No level because the objective machinery starves in pixel space:** epoch scoping severed the level-2 witness; goal-less acquisition explores pixel-novelty; the exit edge is one specific canonical node never deliberately visited post-key. In graph coordinates the whole exploration problem is "visit the unwitnessed (node, action) pairs" — dozens, not thousands.
2. **"Same codex hill climb" because the fitness function is HUD fidelity:** visible-replay-exact makes every candidate pay for dashboard pixels; 83% of the residual was bookkeeping with zero bearing on reaching the exit. The leaf climbs the gradient we gave it.
3. **Action learning doesn't compound because actions are evaluated by pixel surprise**, not by canonical-graph coverage. Witness-gap acquisition (8a-1) was the right idea one level too low: (alpha, action) with alpha = pixel-quotient still drowns in rendering.

## The operational rewiring (in-architecture, no new ontology)

1. **Canonical graph as a first-class evidence projection** (deterministic producer, ~150 LOC): from the bank, build nodes (marker, mode, lattice-pos) × edges (action → node′, Δenergy, Δreserves), with the exceptional-edge ledger (portal/warp/key edges as typed mechanisms). This is the `ObservationChart` the docs already prescribe; measured tonight by the probe (file continues with its numbers).
2. **Point acquisition at the graph's frontier:** witness-gap over canonical (node, action) pairs — the same planner fallback, alpha swapped. The unwitnessed pairs at level 3 number in the dozens; one or two acquisition legs saturate the level's physics.
3. **Terminal edge from the graph:** the level-2 win was a corridor-dead-end node + press-in action. The candidate level-3 terminal nodes are enumerable from the graph (dead-ends in post-key mode). Steer there; the sealed adjudicator still owns success.
4. **Render-map certification** (later, for replay exactness): learn `render` per region once (bar = unary meter of energy; pips = unary meter of reserves; equivariance machinery certifies), after which pixel-exact prediction is latent-step + render — and the entire pattern_write chain becomes derivable rather than mined.
5. **General-engine lesson (AGENTS-worthy after validation):** support-ranking surfaces the dominant *residual*; a second, opposing rank must surface the concentrated *mystery* — the exceptional set (non-stride, mode-changing, law-suspending rows) gets first-class attention regardless of support. Both ranks exist for a reason; only one was built.

## Measured (the probe's numbers, live bank, 2026-07-22)

- **The entire observed game is a 129-node graph with 371 distinct edges** — 16,506 pixel rows collapse 44:1 into canonical (marker, mode, lattice-pos) coordinates.
- **Level 3's acquisition frontier is 129 unwitnessed (node, action) pairs** — the whole remaining exploration problem is ~129 button presses, not thousands of steps of pixel-novelty.
- **57 (node, action) pairs are nondeterministic in (pos, mode) alone** — the scalars (energy/reserves) condition movement on exactly those edges (exhaustion-warps). The canonical state needs the scalars for a slice of the graph — and those 57 pairs ARE the concentrated mystery, enumerated.
- **The exceptional set is 452 transitions, and it is structured:** post-key level-3 movement is *dominated* by non-stride physics (155 rows — the warp-home behavior found by live contact is the rule, not the exception, in key-mode), plus 95 mode/level-changing rows and 196 legacy level-1 strides. The mode-flip rewrites movement wholesale; any exit plan must run on post-key physics that pixel-space identification never prioritized (155 rows of it sat inside the "other 17%" of the residual).

Prediction the frame makes: graph-frontier acquisition (129 targeted presses) + post-key dead-end steering closes level 3 in one or two short legs — without ever finishing the HUD model.

## Honest scope note

The week's harness work is not wasted: acquisition-under-unresolved, row-dominance promotion, content-quotient replay, and the deletion passes are frame-independent and load-bearing. What changes is the *target of identification* and the *coordinates of acquisition*. The pattern_write family remains correct as the rendering-layer law language — it was built one abstraction level below where it should be consumed.
