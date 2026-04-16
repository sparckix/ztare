"""GP-070 Goal Orchestrator + Executive Inbox.

Run:
    streamlit run src/ztare/supervisor/inbox_streamlit.py

Principal dashboard for the ZTARE goal lifecycle. Two panels:
  Left  — goal queue (all goals) or gate queue (pending gates)
  Right — detail view with timeline, stage map, and actions

Visual register: D4 brief §7 (forensic mode). Monospace, file-surface,
no cards, no shadows, no pastel buttons.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

import streamlit as st

from src.ztare.orchestration.config_parser import (
    list_available_goal_types,
    load_goal_config,
)
from src.ztare.orchestration.core import GoalConfig, GoalStatus
from src.ztare.orchestration.persistence import (
    GOALS_ROOT,
    read_state,
    read_transitions,
)
from src.ztare.supervisor.inbox_state import (
    list_pending,
    load_seam_text,
    reconcile_pending_resolved,
    resolve_gate,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PENDING_DIR = REPO_ROOT / "ztare_workspace" / "gates" / "pending"
RESOLVED_DIR = REPO_ROOT / "ztare_workspace" / "gates" / "resolved"

# ---------------------------------------------------------------------------
# Visual register — D4 brief §7, GP-071 visual spec §3
# ---------------------------------------------------------------------------

_MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

_CSS = f"""
<style>
html, body, [class*="css"] {{
    font-family: {_MONO};
    font-size: 13px;
    line-height: 1.4;
    background: #fafafa;
    color: #1a1a1a;
}}
.main .block-container {{ max-width: 1200px; padding-top: 1.5rem; }}

div[data-testid="stSidebar"] {{
    background: #fafafa;
    border-right: 1px solid #1a1a1a;
}}

/* Override Streamlit button defaults — stroke-only, no fill, no shadow */
.stButton > button {{
    background: #fafafa !important;
    color: #1a1a1a !important;
    border-radius: 2px !important;
    box-shadow: none !important;
    font-family: {_MONO} !important;
    font-size: 13px !important;
    border: 1px solid #1a1a1a !important;
    padding: 4px 12px !important;
}}
.stButton > button:hover {{
    border-width: 2px !important;
    background: #fafafa !important;
}}

/* Status buttons — stroke color only */
.approve-btn button {{ border-color: #2a6b2a !important; color: #2a6b2a !important; }}
.approve-btn button:hover {{ border-color: #2a6b2a !important; }}
.reject-btn button {{ border-color: #b0201c !important; color: #b0201c !important; }}
.reject-btn button:hover {{ border-color: #b0201c !important; }}
.defer-btn button {{ border-color: #b8791a !important; color: #b8791a !important; }}
.defer-btn button:hover {{ border-color: #b8791a !important; }}

/* Banner */
#banner {{
    font-size: 15px;
    line-height: 1.3;
    padding: 8px 0;
    border-bottom: 1px solid #1a1a1a;
    margin-bottom: 16px;
}}

/* Dim text */
.dim {{ color: #6b6b6b; }}

/* No decoration on headings */
h1, h2, h3 {{
    font-family: {_MONO} !important;
    font-size: 15px !important;
    font-weight: normal !important;
    line-height: 1.3 !important;
    border: none !important;
}}

/* Text inputs */
textarea, input {{
    font-family: {_MONO} !important;
    font-size: 13px !important;
    border-radius: 2px !important;
}}
</style>
"""

BANNER_GOALS = (
    "GOAL ORCHESTRATOR — forensic mode. Shows all tracked goals, "
    "their lifecycle stage, and transition history. "
    "Create goals via natural language or advance them through the stage graph."
)
BANNER_INBOX = (
    "EXECUTIVE INBOX — advisory mode. This is not the Workbench. "
    "It does not edit code. Append an Operator turn to the seam and "
    "re-run the runner to change premises."
)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def _all_goals() -> list[dict]:
    if not GOALS_ROOT.exists():
        return []
    goals = []
    for gd in sorted(GOALS_ROOT.iterdir()):
        if not gd.is_dir():
            continue
        state = read_state(gd.name)
        if state:
            config, _ = load_goal_config(state.target_type)
            transitions = read_transitions(gd.name)
            goals.append({
                "state": state,
                "config": config,
                "transitions": transitions,
            })
    return goals


def _run_cli(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "src.ztare.orchestration.cli", *args],
        capture_output=True, text=True,
    )
    if result.stdout.strip():
        return json.loads(result.stdout)
    return {"error": result.stderr.strip() or "empty response"}


# ---------------------------------------------------------------------------
# Natural language → goal type
# ---------------------------------------------------------------------------

_TYPE_KEYWORDS = {
    "science_sandbox": [
        "experiment", "sandbox", "hypothesis", "measure", "eigenquestion",
        "ztare", "seam", "pre-reg", "substrate", "finding", "science",
        "pre-registration", "formal",
    ],
    "exploratory": [
        "probe", "explore", "investigate", "sweep", "capability", "test",
        "try", "check", "quick", "lightweight", "flash", "model",
        "parameter", "instrument", "calibrate", "scout",
    ],
    "synthetic_test": [
        "integration", "smoke", "synthetic", "debug", "validate", "fixture",
    ],
}

def _match_goal_type(description: str) -> str | None:
    desc_lower = description.lower()
    scores = {t: sum(1 for kw in kws if kw in desc_lower) for t, kws in _TYPE_KEYWORDS.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else None


# ---------------------------------------------------------------------------
# Stage map renderer — plain text, no pills, no progress bars
# ---------------------------------------------------------------------------

def _render_stage_map(config: GoalConfig, current_stage: str, status: GoalStatus) -> str:
    if not config:
        return ""
    lines = []
    current_idx = config.stage_index(current_stage)
    for i, s in enumerate(config.stages):
        if i < current_idx:
            marker = "[x]"
        elif i == current_idx:
            if status == GoalStatus.GATE_PENDING:
                marker = "[GATE]"
            else:
                marker = "[>]"
        else:
            marker = "[ ]"
        gate = " (gate)" if s.is_gate else ""
        lines.append(f"  {marker} {s.name}{gate}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def _view_goals(goals: list[dict]) -> None:
    st.markdown(f'<div id="banner">{BANNER_GOALS}</div>', unsafe_allow_html=True)

    # Counts
    active = sum(1 for g in goals if g["state"].status == GoalStatus.ACTIVE)
    gate = sum(1 for g in goals if g["state"].status == GoalStatus.GATE_PENDING)
    closed = sum(1 for g in goals if g["state"].status in (
        GoalStatus.CLOSED, GoalStatus.CLOSED_NULL, GoalStatus.CLOSED_ABANDONED))
    st.text(f"active: {active}   gate_pending: {gate}   closed: {closed}   total: {len(goals)}")
    st.text("─" * 72)

    if not goals:
        st.text("(no goals)")
        return

    # Goal list
    for g in goals:
        state = g["state"]
        config = g["config"]
        transitions = g["transitions"]

        status_val = state.status.value.upper()
        created = state.created_at[:10] if state.created_at else "—"
        st.text(f"{state.name}")
        st.text(f"  slug: {state.slug}   type: {state.target_type}")
        st.text(f"  stage: {state.current_stage}   status: {status_val}   transitions: {len(transitions)}   created: {created}")

        if state.status == GoalStatus.GATE_PENDING and state.gate_pending_reason:
            st.text(f"  gate: {state.gate_pending_reason[:100]}")

        with st.expander(f"detail — {state.slug}"):
            left, right = st.columns([3, 2])

            with left:
                # Stage map
                st.text("STAGE MAP")
                if config:
                    st.text(_render_stage_map(config, state.current_stage, state.status))
                st.text("")

                # Timeline
                st.text("TRANSITION LOG")
                for t in reversed(transitions[-12:]):
                    ts = t.get("timestamp_utc", "")[:19].replace("T", " ")
                    from_s = t.get("from_stage", "—") or "—"
                    to_s = t.get("to_stage", "—")
                    action = t.get("action", "")
                    reason = t.get("reason", "")
                    drift = " [DRIFT]" if t.get("artifact_drift") else ""
                    st.text(f"  {ts}  {action}{drift}")
                    st.text(f"    {from_s} → {to_s}")
                    if reason:
                        st.text(f"    {reason[:80]}")

            with right:
                # Actions
                st.text("ACTIONS")
                if config and not config.is_terminal(state.current_stage):
                    if state.status == GoalStatus.GATE_PENDING:
                        st.text("  gate pending — resume to clear")
                        if st.button("Resume", key=f"resume_{state.slug}"):
                            result = _run_cli("resume", state.slug)
                            if result.get("accepted"):
                                st.text(f"  resumed → {result.get('current_stage')}")
                                st.rerun()
                            else:
                                st.text(f"  FAIL: {result.get('reason', str(result))}")
                    else:
                        next_default = config.next_stage_default(state.current_stage)
                        if next_default:
                            next_def = config.stage_by_name(next_default)
                            gate_note = " (gate)" if next_def and next_def.is_gate else ""
                            if st.button(f"Advance → {next_default}{gate_note}", key=f"adv_{state.slug}"):
                                result = _run_cli("advance", state.slug, "--to", next_default)
                                if result.get("accepted"):
                                    st.text(f"  advanced → {result.get('current_stage')}")
                                    st.rerun()
                                else:
                                    st.text(f"  FAIL: {result.get('reason', str(result))}")
                elif config and config.is_terminal(state.current_stage):
                    st.text("  (terminal)")

                st.text("")
                st.text("INFO")
                st.text(f"  owner: {state.owner or '—'}")
                if config:
                    gates = [s.name for s in config.stages if s.is_gate]
                    st.text(f"  stages: {len(config.stages)}   gates: {len(gates)}")
                    if gates:
                        st.text(f"  gate stages: {', '.join(gates)}")

        st.text("─" * 72)


def _view_create() -> None:
    st.markdown(f'<div id="banner">CREATE GOAL — describe what you want to accomplish. The system maps natural language to a goal type and creates the goal through the orchestrator.</div>', unsafe_allow_html=True)

    description = st.text_area(
        "description (what you want to accomplish)",
        placeholder="Run a ZTARE experiment on a quadratic substrate to test Component B...",
        height=80,
        key="nl_desc",
    )

    available_types = list_available_goal_types()
    matched_type = _match_goal_type(description) if description.strip() else None

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("goal name", placeholder="GP-073 Sandbox 15", key="g_name")
    with col2:
        type_index = 0
        if matched_type and matched_type in available_types:
            type_index = available_types.index(matched_type)
        goal_type = st.selectbox("goal type (auto-detected)", available_types, index=type_index, key="g_type")

    if matched_type and description.strip():
        config, _ = load_goal_config(matched_type)
        if config:
            st.text(f"  matched: {matched_type}")
            st.text(f"  {config.description.strip()[:120]}")
            st.text(f"  lifecycle: {' → '.join(config.stage_names())}")

    owner = st.text_input("owner (optional)", value="", key="g_owner")

    if st.button("Create", disabled=not (name and goal_type)):
        args = ["create", name, "--type", goal_type, "--description", description or ""]
        if owner:
            args.extend(["--owner", owner])
        result = _run_cli(*args)
        if result.get("created"):
            st.text(f"  created: {result['slug']}   stage: {result['current_stage']}")
            st.rerun()
        else:
            st.text(f"  FAIL: {result.get('error', result)}")

    st.text("─" * 72)

    # Stage map preview
    if goal_type:
        st.text(f"STAGE MAP — {goal_type}")
        config, errors = load_goal_config(goal_type)
        if config:
            for s in config.stages:
                gate = " (gate)" if s.is_gate else ""
                strict = " [strict]" if s.strict_gate_mode else ""
                dispatch = f"[{s.dispatch}]"
                st.text(f"  {s.name}{gate}{strict}  {dispatch}")
                if s.description.strip():
                    desc = s.description.strip()[:100]
                    st.markdown(f'<span class="dim">    {desc}</span>', unsafe_allow_html=True)
        elif errors:
            for e in errors:
                st.text(f"  ERROR: {e}")


def _view_inbox(pending_items) -> None:
    st.markdown(f'<div id="banner">{BANNER_INBOX}</div>', unsafe_allow_html=True)

    st.text(f"QUEUE ({len(pending_items)})")
    st.text("─" * 72)

    if not pending_items:
        st.text("(empty)")
        return

    for payload in pending_items:
        st.text(f"{payload.stem}")
        st.text(f"  {payload.escalation_reason}")
        st.text(f"  cycles: {payload.cycle_count}   cost: ${payload.total_cost_usd:.2f}   {payload.timestamp_utc[:19] if payload.timestamp_utc else '—'}")

        with st.expander(f"review — {payload.stem}"):
            if payload.notes:
                st.text("NOTES")
                for n in payload.notes:
                    st.text(f"- {n}")
                st.text("")

            st.text("SEAM PREVIEW")
            seam_path = (
                REPO_ROOT / payload.seam_path
                if not Path(payload.seam_path).is_absolute()
                else Path(payload.seam_path)
            )
            seam_text = load_seam_text(seam_path)
            if seam_text and not seam_text.startswith("[inbox_state]"):
                st.code(seam_text[:3000], language="markdown")

            st.text("")
            note = st.text_area(
                "operator_note (mandatory field, may be empty)",
                value="",
                height=60,
                key=f"note_{payload.stem}",
            )

            c1, c2, c3 = st.columns(3)
            now = datetime.now(timezone.utc)
            with c1:
                st.markdown('<div class="approve-btn">', unsafe_allow_html=True)
                if st.button("Approve", key=f"approve_{payload.stem}"):
                    resolve_gate(payload.stem, "approve", note, now, PENDING_DIR, RESOLVED_DIR)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="reject-btn">', unsafe_allow_html=True)
                if st.button("Reject", key=f"reject_{payload.stem}"):
                    resolve_gate(payload.stem, "reject", note, now, PENDING_DIR, RESOLVED_DIR)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with c3:
                st.markdown('<div class="defer-btn">', unsafe_allow_html=True)
                if st.button("Defer", key=f"defer_{payload.stem}"):
                    resolve_gate(payload.stem, "defer", note, now, PENDING_DIR, RESOLVED_DIR)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.text("")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="ZTARE Orchestrator",
        layout="wide",
    )
    st.markdown(_CSS, unsafe_allow_html=True)

    reconcile_pending_resolved(PENDING_DIR, RESOLVED_DIR)
    pending_items = list_pending(PENDING_DIR)
    goals = _all_goals()

    # Sidebar — mode switch
    st.sidebar.text("ZTARE")
    st.sidebar.text("─" * 22)

    inbox_label = f"Inbox ({len(pending_items)})" if pending_items else "Inbox"
    view = st.sidebar.radio(
        "mode",
        ["Goals", "Create", inbox_label],
        label_visibility="collapsed",
    )

    st.sidebar.text("─" * 22)
    st.sidebar.text(f"goals: {len(goals)}")
    st.sidebar.text(f"types: {', '.join(list_available_goal_types())}")
    st.sidebar.text(f"gates pending: {len(pending_items)}")

    # Main content
    if view == "Goals":
        _view_goals(goals)
    elif view == "Create":
        _view_create()
    else:
        _view_inbox(pending_items)


if __name__ == "__main__":
    main()
