# Level-3 win plan — out-of-loop, sim-verified (2026-07-19)

Conductor-authored via the real champion carrier (97-100% exact on level 3) + one hand-patched law (the witnessed row-14262 portal). Out-of-loop, `admissible_to_synthesis=false`; the point is to WIN live — the win banks an adapter-attested terminal witness + fresh evidence, which is what unblocks the governed loop.

## The reframe that produced this

The loop treats "model level 3 perfectly" as prerequisite to "win level 3." Backwards. The win is button presses; the model is already good enough to find them. Win → terminal witness + portal witnesses land in-bank → goal-directed planning and grammar extension both unblock. Win your way to the learning.

## The key fact (in plain sight)

Full reachability sweep from the canonical level-3 reset state (bank row 15815, t=1, avatar (45,14), energy 40): **62 reachable avatar positions, exactly ONE dead-end: (45,54)** — bottom of the right-edge corridor (rows 45-49, cols 54-58), adjacent to the lock-glyph display box (rows 49-52, cols 52-59). Level-2's win = pressing into the corridor dead-end (row 14254, action 1, 1,421-cell relayout). This is the unique level-3 analog. Path cost 23 moves of a 40-unit energy budget; the route never enters the portal region (no unmodeled physics on-path).

## Plan A — direct (execute first)

Action string from the reset state (0=up, 1=down, 2/3=lateral as decoded by the carrier; replay in-sim to view frames):

```
0 2 0 0 0 0 0 0 0 2 1 1 1 1 1 3 3 3 3 3 1 1 1    → arrive (45,54), 23 moves
then: 1 (press INTO the dead end — the level-2 win gesture), repeat 1 up to 3x
```

Energy after arrival ≈ 17 — margin for 3+ probe presses.

## Plan B — key-first variant (if A does not fire)

The multicolor 3×3 object (`9ee/9.8/cc8`, rows 46-48, cols 30-32) has never been touched in play; avatar position (45,29) overlaps it and IS reachable. Route: reset → (45,29) (touch object) → (45,54) → press in. If the game requires collecting the key/shape before the exit accepts, this is the discharge. Live behavior at the object is unwitnessed — every frame there is admissible new evidence regardless of outcome.

## Plan C — portal probe (only if A and B both fail)

Enter (10,9) and press 0: the witnessed portal drops the avatar at (5,34) at 2-energy cost. Explore top-strip dead-ends beyond the portal (positions (5,44)/(5,49) region). Also yields the portal's second/third witnesses for the grammar card.

## Execution notes

- Resume at level 3 via the verified `level_boundary_seed` replay path (declared_epoch == observed_epoch verified 07-16) — do NOT use the old win_attempt driver shape that called `adapter.reset()` (the AGENT_CORRECTIONS class: it restarts at level 1).
- Execute as a scripted action sequence through the play loop's seeded entry; every frame appends to the governed bank as ordinary evidence.
- If a win fires: the boundary receipt is adapter-attested → task-discharge counts, level-4 evidence starts accruing, and the terminal witness gives the planner its objective class for future levels.
- Whatever happens at (45,54) and (45,29) is new typed evidence at rows the loop has never visited — the cheapest information in the game right now.

## LIVE RESULTS (2026-07-19, conductor closed-loop runs — quarantined trace: workspace/win_attempt_l3_trace.jsonl)

Three live sessions (seed replay `verified`, level 3 reached each time). No discharge yet, but the level's actual physics are now measured:

1. **Portal CONFIRMED live, twice**: (10,9)+up → (5,34), exactly as hand-modeled from row 14262.
2. **(45,54) is NOT an exit — it is a warp-home hazard**: entering from the north at (40,54)+down teleports the avatar back to (45,9). The "unique dead-end" hypothesis is refuted; the plan-A press-in gesture is dead.
3. **The key object is real and reachable**: avatar overlapped it live at (45,29) (route: portal → col-29 south).
4. **Touching the key CHANGES the physics**: pre-key, (30,34)+east → (30,39) (normal); post-key, the same move warps home to (45,9), and (45,14) became movement-locked for 6 consecutive presses. Level 3 is a collect-key-then-exit puzzle with **key-conditional transition rules** — a two-mode dynamics family the current carrier cannot express (mode bit + per-mode transition law).
5. **Session variation**: an identical action sequence that reached the key in session 2 bounced home in session 3 — start-state or t-phase dependence across lives; a discriminating observation for the lawful_time model.

**Where the crack now stands**: the remaining work is a closed-loop MPC with a two-mode carrier (pre-key/post-key) fitted from this trace (~100 fresh transitions at never-visited positions), goal = post-key route to the lock box avoiding the discovered warp cells. All the machinery for this exists in `workspace/win_attempt_l3_mpc.py` — swap the sim_step for the two-mode patch and re-run. For the governed loop: the trace contains multiple witnesses for two new operator families (`portal_transport`, `mode_conditional_guard`) — exactly the residual cards the grammar-extension leg should implement once switched on.

## Simulator (for replay/verification)

Carrier via `carrier_loader.load_carrier_path(<proj>/test_model.py, dynamics_assumption='lawful_time')`; portal patch: avatar at (10..14, 9..13) + action 0 → relocate 5×5 block to (5..9, 34..38), energy −2 (4 bar cells). Start state: bank row 15815. BFS dedup on (avatar_pos, t).
