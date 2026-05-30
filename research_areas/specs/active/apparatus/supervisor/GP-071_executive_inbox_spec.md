# GP-071 Executive Inbox Spec

**Track:** supervisor / operator surface
**Status:** `draft` (authorized by `D4_distribution_form_factor_seam.md` Turn 4)
**Origin:** 2026-04-15 carve-out from D4 — the external product brief keeps the Workbench and Judgment Coach; the *internal* operator surface needed to clear gate escalations is separated out into this spec.
**Depends on:** GP-036 (`emit_gate_escalation` writes `ztare_workspace/gates/pending/`), GP-070 (declares gates as the transition-request boundary between State Machine Core and operator)
**Seam tension note:** Standing rule is seam-before-spec. GP-071 is spec-direct because its "debate" lives on the D4 seam (Turn 4 authorizes carve-out) and because it is a narrow internal tool, not a research claim. If a dedicated GP-071 seam is later required, the debate track can be opened retroactively — this spec stays the blueprint.

---

## 1. Purpose and Scope

**Mandate:** Provide a local, asynchronous resolution surface for gate escalations the ZTARE findings runner already writes to disk. Today those records accumulate in `ztare_workspace/gates/pending/` with no reader; the operator opens the JSON files in an IDE. This spec replaces that with a single-page local UI for reviewing and resolving the queue.

**Relationship to GP-070.** GP-070 argues that in the hybrid State-Machine-Core / Declarative-Goal-Config / Emergent-Agent-Runtime architecture, the core's *only* interaction with the operator is at the gate boundary — the State Machine Core calls `emit_gate_escalation`, the operator responds. GP-071 is the first concrete consumer of that boundary. The Inbox is the operator-side half of what GP-070 formalizes as `/gates/pending/` → `/gates/resolved/`.

**Out of scope.**
- Not the external D4 Workbench. The Workbench is an *authoring* surface where the operator types new content (specs, board rows, pre-regs). The Inbox is a *resolving* surface where the operator says approve / reject / defer on records the core already wrote. These are distinct audit postures and must not collapse into one UI.
- Not the Judgment Coach.
- No authentication. No external database. No cloud hosting. Localhost only.
- No AST / code editing. If the debate is failing, close the Inbox and open the IDE.

## 2. Operating mode

**Advisory, not blocking.** The runner writes a gate record (`emit_gate_escalation`) with `advisory: true` and exits. It does not poll for resolution. Clicking Approve in the Inbox does NOT resume the runner. Approve is a **mark-as-read + audit-trail write**; the operator must then manually re-run the relevant command (e.g., `python -m src.ztare.validator.supervisor_findings_runner --seam-path ... --execute`) if they want the debate to continue.

**Why ship advisory-first.** Two reasons: (1) the runner as of GP-036 is deliberately fire-and-forget, and making it poll `/gates/resolved/` is a decisive behavioral change that collides with the GP-036 contract Codex signed off on. (2) The queue is expected to be small (a handful of items per day). Manual re-run after Approve is a cheaper cost than runner-poll code. **Revisit this decision only after `/gates/resolved/` has at least 30 days of data showing "operator approved, forgot to re-run" as a repeating failure mode.**

## 3. Architecture — the file-system-as-API pattern

**Read state:** the Inbox reads `ztare_workspace/gates/pending/*.json`. Each file is a gate payload written by `emit_gate_escalation`. Actual payload schema (verified against `supervisor_findings_runner.py` — do not trust aspirational fields):

```json
{
  "seam_path": "research_areas/private/seams/GP-NNN_...md",
  "escalation_reason": "COST_BUDGET" | "ESCALATED_CAP" | ...,
  "equivalent_gate_reason": "SPEC_REFINEMENT_BUDGET_REACHED" | "",
  "cycle_count": 9,
  "total_cost_usd": 0.42,
  "notes": ["...", "..."],
  "timestamp_utc": "2026-04-15T18:07:00+00:00",
  "advisory": true
}
```

Note: **there is no `findings_context` field in the payload.** To render decisive claims, the Inbox must read `seam_path` and load the seam file directly. Do not design the UI against a non-existent field.

**Write state:** the Inbox writes to `ztare_workspace/gates/resolved/gate_<seam_stem>.json` and deletes `ztare_workspace/gates/pending/gate_<seam_stem>.json`.

**Startup behavior:** on launch, the Inbox calls `Path.mkdir(parents=True, exist_ok=True)` on both `pending/` and `resolved/`. First-run state is an empty queue, not a crash.

**Atomicity of resolve.** The move is two-phase: (a) write `resolved/gate_<stem>.json.tmp` with the resolution payload, fsync, rename to `resolved/gate_<stem>.json`; (b) delete `pending/gate_<stem>.json`. If the process crashes between (a) and (b), startup reconciliation deletes any `pending/` file whose stem already has a matching `resolved/` file — resolved wins.

## 4. Resolution payload schema

Whatever the Inbox writes to `resolved/` must be self-contained (do not require joining with the deleted pending file). Schema:

```json
{
  "original_gate": { ...the full pending payload, carried forward verbatim... },
  "decision": "approve" | "reject" | "defer",
  "operator_note": "free-text, may be empty string but field is mandatory",
  "resolved_at_utc": "2026-04-15T18:12:30+00:00",
  "resolver": "operator"
}
```

The `operator_note` field is mandatory (the field, not the content). The UI must expose a three-line text box; operator may leave it empty. "I want to know why" is almost always the question asked in six months, and a one-liner now beats reconstructing from git blame.

## 5. UI layout (single page)

**Sidebar — the queue.** Lists every file in `pending/`, one row per file, showing `seam_stem`, `escalation_reason`, and `total_cost_usd`. **Sort order: `total_cost_usd` descending.** Rationale: the CEO reads the item burning the most budget first. Ties broken by `timestamp_utc` ascending (older first).

**Main window — the context.** When a queue row is selected, the main window shows:

1. Top bar: `seam_stem`, escalation reason, cycles, total_cost_usd, UTC timestamp.
2. Notes block: the `notes[]` array from the payload, one per line.
3. **Seam preview:** the Inbox reads `seam_path` from disk and renders the seam as markdown. This is how the operator sees the decisive claims without opening an IDE. The preview is scrollable; no edit controls; render the file verbatim.
4. Action bar: three buttons — Approve, Reject, Defer — plus the mandatory `operator_note` text box above them. Defer closes the detail view without writing anything to `resolved/`; the file stays in `pending/` and can be resolved later.

**Guardrails visible in the UI:**
- Top-of-page banner: "This is the Executive Inbox. It does not edit code. To change the debate's premises, append an Operator turn to the seam and re-run the runner."
- Approve/Reject do not prompt for code changes; the only input is the note.

## 5a. Visual register (inherited from D4 brief §7, Forensic mode)

GP-071 is an operator tool. It must read as **forensic-adjacent**: dense, instrument-panel, monospace-adjacent, close to the file surface. Not editorial, not didactic, not "app-shaped." Streamlit's defaults (rounded pastel buttons, generous whitespace, chat-like flow) are the opposite of this and must be overridden.

Hard constraints for implementation:

1. **Monospace for payload and seam rendering.** The `notes[]` array, JSON fields, and seam markdown render in a monospace font (system default: `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`). Operator should feel they are looking at a file, not a chat message.
2. **Dense information, minimal chrome.** Sidebar queue rows show 3 fields stacked tight (stem, reason, cost) — no cards, no shadows, no rounded corners beyond ~2px. Detail panel uses a single column with section dividers, not cards.
3. **No emoji, no color accents beyond status.** The only color beyond foreground/background is: red for `reject`, amber for `defer`, green for `approve` — applied to the button stroke only, not the fill. No icons in buttons; text labels only.
4. **Banner and mode discipline.** The "this is not the Workbench" banner at the top is not decorative. It is the visual firebreak between authoring surface and resolving surface per D4 brief §5.2 (generation and judgment must remain visually distinct). The banner stays on-screen at all times, not collapsible.
5. **File-preview affordance is first-class.** The rendered seam markdown is the largest block on the detail panel. D4 brief §5.3: "show me the underlying file" is a first-class affordance, not advanced/hidden.
6. **No governance-cockpit visual leakage into D4 surfaces.** Per D4 brief §5.5, the Workbench and Judgment Coach must not grow affordances that duplicate GP-071's role. If the implementation ends up importing shared design tokens from a future D4 design system, the Inbox is allowed to use the token set but must not use any component that lives in the Workbench's "authoring" visual vocabulary.

A dedicated GP-071 visual spec (separate markdown file with two hand-drawn wireframes: empty state and loaded-with-selection state) is **required before implementation begins but after the functional spec converges.** See §11.

## 6. Implementation shape

**Factor the logic out of the UI framework.** The Inbox is split into two files:

- `src/ztare/supervisor/inbox_state.py` — pure functions, no Streamlit import, no I/O framework. Functions:
  - `list_pending(pending_dir: Path) -> list[GatePayload]`
  - `load_seam_text(seam_path: Path) -> str`
  - `resolve_gate(stem: str, decision: Literal["approve","reject","defer"], operator_note: str, now_utc: datetime, pending_dir: Path, resolved_dir: Path) -> Path`  — returns the resolved-file path; defer is a no-op that returns `None`
  - `reconcile_pending_resolved(pending_dir: Path, resolved_dir: Path) -> list[Path]` — startup cleanup, returns the list of pending files deleted
- `src/ztare/supervisor/inbox_streamlit.py` — thin Streamlit wrapper, imports `inbox_state`, does nothing the module layer doesn't do. ~50 lines.

**Fixture regression.** A new test file `src/ztare/supervisor/inbox_state_fixture_regression.py` exercises `inbox_state.py` end-to-end against `tempfile.TemporaryDirectory()` fixtures — no Streamlit in the test path. Minimum test set:

1. `test_list_pending_empty_returns_empty_list`
2. `test_list_pending_sorts_by_cost_descending`
3. `test_resolve_gate_approve_writes_resolved_and_deletes_pending`
4. `test_resolve_gate_reject_writes_resolved_and_deletes_pending`
5. `test_resolve_gate_defer_is_noop`
6. `test_resolve_gate_carries_forward_original_payload`
7. `test_resolve_gate_requires_operator_note_field_but_allows_empty_string`
8. `test_reconcile_deletes_pending_when_resolved_exists`
9. `test_atomic_resolve_survives_mid_write_crash` (simulate crash via raising inside the tmpfile write path; verify startup reconcile converges)
10. `test_list_pending_ignores_malformed_json_and_logs_to_stderr` (a bad file must not take the whole queue down)

Streamlit is itself not fixture-testable and is therefore out of the regression suite. The wrapper is kept under 50 lines specifically so that the test coverage on `inbox_state.py` is enough.

**Framework choice:** Streamlit. Rationale: already familiar, free markdown rendering, buttons are one-liners, auto-reloads on file change. The stdlib `http.server` alternative saves the dependency but costs an HTML template; not worth it at this scale. **Flag for revisit:** if the D4 Workbench also ends up on Streamlit, check for shared boilerplate before the second page lands. Do not prematurely extract.

## 7. What this spec does NOT do (explicit deferrals)

- **Blocking HITL.** The runner does not wait on `/gates/resolved/`. See §2.
- **Gate types beyond GP-036 runner output.** GP-039 (Gate Library Formalization) is the place to generalize the payload schema across goal types. This spec codes against the GP-036 schema only; if a new writer emits differently-shaped records, the Inbox should display them in a degraded-but-safe mode (top bar + notes + raw JSON viewer) rather than crash — implement this as a fallback render branch but do not design new schemas here.
- **Retention / archival.** `/gates/resolved/` accumulates forever in v1. Revisit at N>10k files.
- **Authentication.** Localhost only. If you port this to a shared machine, authentication is a different spec.
- **Editing the seam from the Inbox.** Already covered by the top-of-page banner. The UI must not grow an editor.

## 8. Acceptance criteria

Shipped when:

- [ ] `inbox_state.py` exists with the 4 functions named in §6 and 10/10 fixture tests pass.
- [ ] `inbox_streamlit.py` renders the queue, sidebar, main window, and action bar described in §5 against a hand-authored fixture gate record in `/tmp/gate_fixture/pending/`.
- [ ] Approve, Reject, and Defer each produce the expected disk effect (verified manually once; covered by fixtures in `inbox_state`).
- [ ] Atomicity test passes (simulated crash leaves state recoverable on next startup).
- [ ] `README` section in `src/ztare/supervisor/README.md` (one paragraph) explaining: "this is the internal cockpit; it does not gate the runner; advisory mode only."

## 9. Explicit non-goals (to prevent drift)

- This spec will not make the runner blocking. Separate seam required.
- This spec will not propose a schema migration for gate payloads. That's GP-039.
- This spec will not add authentication. That's a different spec for a different deployment target.
- The Inbox will not become the Workbench. The Workbench is authoring; the Inbox is resolving; collapsing them destroys the audit distinction the D4 seam Turn 4 just spent a turn carving.

## 10a. Consistency check against D4 v1 design brief

GP-071 was cross-checked against `research_areas/private/drafts/D4_form_factor_v1_design_brief.md` on 2026-04-15. Findings:

- **§5.1 evidence-first, not chat-first:** PASS. Inbox has no chat surface; operator interaction is approve/reject/defer + free-text note.
- **§5.2 generation and judgment visually distinct:** PASS with active guardrail. The top-of-page banner and §5a visual register enforce this; the spec explicitly forbids the Inbox growing an editor.
- **§5.3 local-first inspectability:** PASS. Reads gate payloads from disk, renders seam files verbatim as the main block.
- **§5.5 no governance UI in v1:** PASS-with-asterisk. The D4 brief defers the supervisor/principal cockpit out of v1. GP-071 *is* a thin slice of that cockpit, but it is (a) a separate tool at a separate entry point, not inside the Workbench or Judgment Coach, (b) authorized as a carve-out internal tool by D4 seam Turn 4, and (c) scoped to a single operator action (gate resolution), not to the full cockpit the brief defers. The brief's intent — "do not let governance leak into the v1 product surfaces" — is honored because GP-071 does not leak into those surfaces.
- **§6 shared design system:** DEFERRED. GP-071 ships before any D4 design system exists. §5a mandates monospace + minimal chrome today; when the D4 design system lands, GP-071 should be revisited to share type/color tokens (not components).
- **§9 trust posture:** PASS. All three trust mechanisms (read the files, see what was just done, inspect why) are first-class in the UI.

## 10b. Do we need a separate UX/UI spec for GP-071?

**Yes, but lightweight.** A second markdown file — `research_areas/private/drafts/GP-071_visual_spec.md` — containing:

1. Two hand-drawn wireframes (phone photo is fine): **empty state** and **loaded-with-selection state**. No Figma.
2. State transition table: `empty → pending_items → item_selected → note_drafted → resolved → back_to_queue`.
3. Type scale (2 sizes), color tokens (foreground, background, red/amber/green status), and the banner copy verbatim.
4. A "what this is not" panel listing three visual patterns it must not adopt (cards-with-shadows, chat bubbles, pastel buttons).

Total document length target: one page. Rationale: GP-071 has ~5 UI primitives; a full D4-style brief is overkill, but shipping without *any* visual constraint artifact means whoever writes the Streamlit wrapper defaults to Streamlit's visual language, which is the opposite of forensic register. The visual spec is the firebreak.

**Timing:** write the visual spec after the functional spec (this file) converges through debate, and before any `inbox_streamlit.py` code is written.

## 11. Operator decisions (locked 2026-04-15)

1. **Framework: Streamlit.** Not stdlib. Decision locked — do not re-open unless a second UI page lands that would justify a shared stdlib host.
2. **Note field: free text only.** Three-line text box, mandatory field (may be empty), no structured tags, no dropdowns. If retrieval shape ever needs tag-facets, that is a separate spec.
3. **No shell-out. Period.** Approve does not re-run the originating command. Approve does not invoke any subprocess. Approve writes to `resolved/` and returns to the queue. The operator manually re-runs the command in their terminal if they want the debate to continue. This is the strict boundary between "audit write" and "execution control" — GP-071 is on the audit side, and any future crossing of that boundary requires a new spec, not a configuration flag on this one.

---

*Last updated: 2026-04-15, spec draft after Turn 4 carve-out on D4 seam.*
