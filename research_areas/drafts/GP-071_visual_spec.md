# GP-071 Executive Inbox — Visual Spec

**Status:** draft 2026-04-15. Required by `research_areas/private/specs/active/GP-071_executive_inbox_spec.md` §10b before any `inbox_streamlit.py` code is written. Inherits visual register from GP-071 §5a and D4 brief §7 (Forensic mode).

**Target length:** one page. If this grows past two screens, the constraint set is drifting — revise down.

---

## 1. Wireframes

ASCII sketches below are the central artifacts. If you prefer a phone-photo hand sketch, replace these two blocks with the photos and keep the annotations — the annotations are the spec, not the ASCII.

### 1.1 Empty state (no files in `ztare_workspace/gates/pending/`)

```
+--------------------------------------------------------------------+
| EXECUTIVE INBOX — advisory mode. This is not the Workbench.        |  <- banner, always visible
| It does not edit code. Append an Operator turn to the seam and     |
| re-run the runner to change premises.                              |
+--------------------------------------------------------------------+
|                      |                                             |
|  QUEUE (0)           |                                             |
|  ─────────           |                                             |
|                      |           no item selected                  |
|  (empty)             |                                             |
|                      |                                             |
|                      |                                             |
|                      |                                             |
|                      |                                             |
|                      |                                             |
+--------------------------------------------------------------------+
```

Annotations:
- banner occupies full width, ~2 lines tall, not collapsible, stays on-screen during scroll
- sidebar width ~22 ch, fixed; main panel fills the rest
- "(empty)" rendered in the body monospace at normal weight; not italicized, not a pastel illustration, no "nothing here yet, come back later" copywriting
- no spinner, no skeleton loader; an empty queue is a normal, frequent state

### 1.2 Loaded with selection (one of N files selected)

```
+--------------------------------------------------------------------+
| EXECUTIVE INBOX — advisory mode. This is not the Workbench.        |
| It does not edit code. Append an Operator turn to the seam and     |
| re-run the runner to change premises.                              |
+--------------------------------------------------------------------+
|                      |  GP-070_meta_supervisor               [x]   |
|  QUEUE (4)           |  reason: SPEC_REFINEMENT_BUDGET_REACHED     |
|  ─────────           |  cycles: 9   cost: $0.42                    |
|                      |  utc: 2026-04-15T18:07:00+00:00             |
| >GP-070_meta_super   |  ---------------------------------------    |
|   SPEC_REFINEMENT    |  NOTES                                      |
|   $0.42              |  - budget cap hit; 3 unresolved claims      |
|                      |  - equivalent_gate_reason matched           |
|  GP-059_findings…    |  ---------------------------------------    |
|   COST_BUDGET        |  SEAM PREVIEW                               |
|   $0.31              |                                             |
|                      |  # GP-070 — Meta Supervisor Seam            |
|  GP-033_structural…  |  Status: note                               |
|   ESCALATED_CAP      |                                             |
|   $0.18              |  ## Turn 1 — Claude ...                     |
|                      |  (full seam markdown, scrollable, verba-    |
|  GP-012_…            |  tim, monospace, no edit affordance)        |
|   COST_BUDGET        |                                             |
|   $0.04              |                                             |
|                      |  ---------------------------------------    |
|                      |  operator_note (mandatory field, may be     |
|                      |  empty):                                    |
|                      |  +---------------------------------------+  |
|                      |  |                                       |  |
|                      |  |                                       |  |
|                      |  |                                       |  |
|                      |  +---------------------------------------+  |
|                      |                                             |
|                      |  [ Approve ]  [ Reject ]  [ Defer ]         |
+--------------------------------------------------------------------+
```

Annotations:
- sidebar rows: 3 stacked lines per row — `seam_stem` (truncated to sidebar width), `escalation_reason`, `$cost`; `>` marker on the selected row; row separators are a single blank line, no borders, no cards
- sort order: `total_cost_usd` descending, ties broken by `timestamp_utc` ascending (per spec §5); the 4 rows above are illustrative, not prescriptive
- main panel top bar is 4 lines: stem, reason, cycles+cost, utc; right-aligned `[x]` is the "close detail, stay in queue" affordance — it does NOT resolve the gate
- NOTES block is `notes[]` verbatim, one bullet per line, no re-formatting
- SEAM PREVIEW is the largest block on the detail panel and MUST remain the largest block; if any other block grows past its height, resize the other block first
- operator_note is exactly three text lines tall at the default monospace metric; grows no more; never becomes a rich editor
- buttons are text-only, no icons, no filled backgrounds; stroke color per §3 below

## 2. State transition table

| from                | event                      | to                  | side effect                                           |
|---                  |---                         |---                  |---                                                    |
| `empty`             | `list_pending` returns >0  | `pending_items`     | sidebar renders rows, main stays blank                |
| `pending_items`     | row clicked                | `item_selected`     | main panel fills; `operator_note` field empty         |
| `item_selected`     | note typed                 | `note_drafted`      | button strokes un-dim; no disk write                  |
| `note_drafted`      | Approve / Reject clicked   | `resolved`          | `resolve_gate` writes `resolved/`, deletes `pending/` |
| `note_drafted`      | Defer clicked              | `pending_items`     | no disk write; file stays in `pending/`               |
| `item_selected`     | `[x]` clicked              | `pending_items`     | main panel returns to blank; file stays in `pending/` |
| `resolved`          | (automatic)                | `pending_items` or `empty` | queue re-lists; selection cleared              |

Note: `note_drafted` is a soft state — buttons are enabled whether or not the field has content (the spec says the field is mandatory, the content is not). The transition exists for visual feedback only.

## 3. Type scale and color tokens

**Type — 2 sizes, 1 family.**

| token    | family            | size  | weight  | used for                                           |
|---       |---                |---    |---      |---                                                 |
| `mono-m` | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` | 13px / 1.4 | regular | body: sidebar rows, notes, seam preview, note field, button labels |
| `mono-l` | same              | 15px / 1.3 | regular | banner copy and main panel top-bar stem line       |

No italic. No bold except where a terminal would bold (none, in practice). No variable weight.

**Color — foreground/background + three status strokes only.**

| token         | hex        | used for                                    |
|---            |---         |---                                          |
| `fg`          | `#1a1a1a`  | all text, all dividers                      |
| `bg`          | `#fafafa`  | entire page background                      |
| `fg-dim`      | `#6b6b6b`  | sidebar row secondary lines, divider rules  |
| `status-red`  | `#b0201c`  | `Reject` button stroke, and nothing else    |
| `status-amb`  | `#b8791a`  | `Defer` button stroke, and nothing else     |
| `status-grn`  | `#2a6b2a`  | `Approve` button stroke, and nothing else   |

Button fills are always `bg`. Status color is on the 1px stroke only. No hover fill, no active fill — change stroke weight from 1px to 2px on hover, that is the entire hover treatment. No shadows at any state.

Dark mode: not in v1. If the operator's OS is in dark mode, the Inbox still renders `bg=#fafafa` — this is the forensic register, not a theme-aware app. Revisit at N>3 operator complaints.

**Banner copy — verbatim.**

> EXECUTIVE INBOX — advisory mode. This is not the Workbench. It does not edit code. Append an Operator turn to the seam and re-run the runner to change premises.

Line breaks are renderer-driven; the text is one sentence logically, wrap where the viewport wraps. Do not shorten. Do not embellish. The banner is the visual firebreak per D4 brief §5.2 and is central — if it drops, the whole audit distinction between Workbench (authoring) and Inbox (resolving) collapses.

## 4. What this is not — three forbidden patterns

1. **No cards-with-shadows.** Rounded corners are capped at 2px; no `box-shadow` anywhere in the tree; no elevation gradient. The sidebar rows are not cards. The detail panel is not a card. Cards imply "tap me, I am an app." The Inbox is a file surface, not an app surface.

2. **No chat bubbles.** The `notes[]` array is a list of strings, rendered as bullet lines in monospace. Not as dialogue turns. Not with an avatar column. Not with timestamps floated right. The operator is reading a payload, not watching a conversation.

3. **No pastel buttons.** Buttons are text labels with a 1px stroke in `status-red` / `status-amb` / `status-grn`, on a `bg` fill. Streamlit's default button is a filled pill with rounded corners and a faint shadow — override it. If the override turns out to require importing a third-party theme package, consider whether stdlib `http.server` is cheaper (spec §6 leaves this revisit door open).

## 5. Implementation note for the wrapper author

The whole point of this spec being thin is that the wrapper is thin. `inbox_streamlit.py` should be under 50 lines per the functional spec §6. If you find yourself writing CSS overrides that exceed the wrapper's own line count, stop — either the constraints are wrong (bring it back to the operator) or Streamlit is the wrong framework (revisit §6's framework choice). The forensic register should fall out of strict adherence to §3's tokens plus §5a's constraints, not out of 200 lines of custom styling.

---

*End of visual spec. Next step per functional spec §10b: write `src/ztare/supervisor/inbox_state.py` + fixtures, then `inbox_streamlit.py` against this register.*
