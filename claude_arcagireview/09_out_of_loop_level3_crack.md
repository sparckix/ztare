# Out-of-loop crack attempt — ls20 level 3 (and level 4)

Conductor (Claude) hands-on analysis, 2026-07-17. **Authority note:** everything here is out-of-loop conductor diagnostics — `admissible_to_synthesis=false` per the repo's own rule. Visible bank only (`episode_001.jsonl`, 16,176 rows); the holdout (`episode_002`) was never opened. If any finding matters scientifically, the governed collector must reacquire it inside the active epoch; the legitimate in-loop route for the goal hypothesis below is a goal-abduction steering candidate or an operator-supplied experiment, not a briefing hint.

## Method

Loaded the champion PATCH_BASE carrier through the canonical loader (`carrier_loader.load_carrier_path`, `lawful_time`) — verified **97/100 exact** on level-segment rows (the 3 misses are excluded env frames). Ran in-model BFS with the real carrier as simulator. Diffed win/death/boundary frames directly from the bank.

## The game, derived from data (LS20)

- 64×64 board; avatar = a 5×5 two-tone block (2 rows value-12 on top, 3 rows value-9). Actions: **0=up, 1=down, 2/3=left/right**; moves land on a 5-cell grid stride.
- **Energy**: bottom bar (rows 61-62, fill value-11), 1 unit (2 cells) per normal move; exhausted → death/reset (t-reset; 66 deaths in the 1,966-row current segment; the `588` pips at cols 56-63 are reserve units).
- **Wins are corridor-end events**: the level-2→3 win fired at row 14254 — action 1 (down) at the bottom of the col-14-18 corridor, triggering a 1,421-cell relayout. Win = drive the avatar into the exit corridor's dead end. (My first BFS reached the *top strip* in 8 moves in-model — top strip is trivially reachable, so it is NOT the win condition.)
- Displays: the 6×6 bottom-left glyph box (rows 55-60, cols 3-8) changes per level — the documented 4-state display; lock-glyph boxes (5-border with 9-patterns) appear per level; ring objects (`bbb/b3b/bbb`) are pickups.

## Level 3's blocking mechanic, characterized

The first live level-3 rows produced the documented counterexample at **row 14262** (t=71, a=0). Measured from the diff:

> Avatar at rows 10-14, cols 9-13 (left corridor) moves **up** → environment places the same 5×5 structure at rows 5-9, **cols 34-38** (top-right). The champion predicts straight-line continuation at cols 9-13. The move also costs **2 energy units** instead of 1 (4 bar cells cleared).

This is a **portal/tunnel mechanic**: entering the top strip from the left corridor teleports the avatar to a fixed distant drop point, at double energy cost. The operator catalog (translate_block + guards) cannot express source→destination teleportation — **this is a grammar ceiling, exactly the case the grammar-extension reflex exists for, and that reflex is switched off** (budget=0 + `governed_carrier` short-circuit; 106 proposals / 0 promotions).

Also confirmed: in level 3, value 12 is no longer avatar-unique (displays/objects reuse it), so any v12-based avatar tracking or role assignment from earlier levels mislabels — consistent with the object_roles/epoch-scoping work.

## Why a week was lost — the sequenced verdict

1. **Most of the week was harness** (now fixed): the P0 planner quartet — novelty collapse from interned/visited conflation, positional set-cursor, cross-epoch visited leakage marking unexplored level-3 states as seen, clock-cell novelty churn — plus `within_epoch_view` silently feeding roles/goals from 7% of the bank, and the candidate-pool committee no-op. Every one of these specifically cripples *exploration of a new level*. All fixed as of 07-16/17 (see 08); receipts down 10x.
2. **The residual blocker is science + one switched-off loop, not the fixed bugs:**
   - **No terminal witness exists for level 3** — epoch scoping correctly severed the level-2 witness, and by design the planner "does not invent or transport an objective," so it runs acquisition-only exploration. Nothing is steering toward any exit corridor.
   - **The portal law is outside the grammar**, so even acquisition can't compress it into the carrier — and the one mechanism that could admit a new operator autonomously is disabled.
   - Fresh receipts agree: `pursuit.plan` eats ~99% of live-play leg time; factored search exhausts 5,000 states with no goal.

So: it *was* mostly the harness; the harness part is now largely fixed and was fixable easily (it was — the operator fixed all 8 P0s in ~2 days); what remains is one real mechanic to learn and one loop to switch on.

## Can I crack it? — honest answer

**Level 3: partially, and here is the crack plan.** What I demonstrated out-of-loop: loaded the exact carrier, simulated the level, derived win semantics, localized and characterized the blocking mechanic. What I cannot do out-of-loop: plan through the portal with the current carrier (the model is wrong exactly there — any in-model route through the portal region is untrustworthy), and I cannot press buttons. The crack sequence for the governed loop:

1. **Turn on the grammar-extension implement leg** (budget≥1, drop the `governed_carrier` short-circuit) with the row-14262 triple as the residual card. The needed operator family is `portal_transport(source_rect, entry_direction, dest_anchor, energy_cost)` — parameterized from evidence like every other catalog operator, no game constants. Two witnesses likely already exist in-bank (the docs note recurrence support acquisition works: the {14950,14952} pattern).
2. **Acquire the level-3 terminal witness deliberately**: the win pattern is corridor-dead-end entry. Steer (via goal-abduction steering candidates, which are legitimately admissible) to each dead-end corridor of the level-3 map in turn — right-edge column (cols ~54-58), bottom-right box (rows 49-52, cols 52-59, which contains a lock glyph), and the top-strip portal exits — under the repaired energy accounting (portals cost 2). One boundary event gives the planner its objective; task-directed factored search then closes it the way level 2 closed (45-intervention plan, zero replans).
3. If the exit requires a shape/state precondition (the lock-glyph box suggests it), the ring pickups and the 4-state display are the candidates — the display's `0→1→2→3` chain is already in the version space; the distinguishing experiment is one pickup-then-exit-attempt pair.

**Level 4: no.** Level 4 has never been observed — zero rows, zero layout, zero mechanics evidence. Any claim about it would be invention. What transfers: the win-is-corridor-end pattern, the energy economy, and the expectation (from the 1→2→3 difficulty curve) that level 4 composes the portal mechanic with a shape precondition. The honest path to level 4 is: crack level 3, bank the boundary seed, and let the same acquisition transaction open level 4's first counterexample.

## One-line summary

The apparatus was the bottleneck for most of the week and is now largely repaired; level 3 itself is one unlearnable-under-current-grammar portal law plus one unwitnessed terminal edge — both closable this week if the grammar loop is switched on and one steering campaign is pointed at the dead-end corridors.
