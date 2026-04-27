"""GP-154 monitor — single-shot state check + selective ntfy + auto-kill on champion.

Runs once per invocation. Designed to be called by the cron wakeup. State
persisted in .gp154_monitor_state.json so consecutive runs only notify on
substantive change (no spam).

Discipline:
  - ntfy ONLY on: (a) new champion >= 85 with gates pass, (b) genuinely new
    critique class (not seen earlier in run), (c) anomaly (gate harness
    error / runtime crash), (d) run completion / stagnation kill.
  - Skip notifications for: routine sub-85 iters, self-refuting cycles
    (RH-10 pattern — same critique class returning), procedural critiques.
  - On champion + gates_pass: SIGTERM `make experiment-loop` to save money.

Usage:
  python scripts/gp154_monitor.py [--force-status]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "projects" / "gp154_scaling_law_exponents"
STATE_FILE = REPO / ".gp154_monitor_state.json"
NTFY_TOPIC_FILE = REPO / "org" / "mandates" / ".ntfy_topic"

CHAMPION_THRESHOLD = 85
HOLDOUT_MRE_THRESHOLD = 0.25
FARTHER_TAIL_MRE_THRESHOLD = 0.35


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "max_score": 0,
        "n_iters_seen": 0,
        "last_iter_timestamp": "",
        "critique_classes_seen": [],
        "champion_announced": False,
        "anomalies_announced": [],
        "run_completed": False,
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _scan_debate_logs() -> list[dict[str, Any]]:
    """Return list of {timestamp, score, weakest_point} sorted by timestamp asc."""
    logs = sorted(PROJECT.glob("debate_log_iter_*.md"))
    rows = []
    for log in logs:
        try:
            text = log.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        score_m = re.search(r"Final Score:\s*(-?\d+)", text)
        weak_m = re.search(r"Weakest Point:\*\*\s*(.+)", text)
        ts_m = re.search(r"debate_log_iter_(\d+)\.md", log.name)
        if not (score_m and ts_m):
            continue
        rows.append({
            "timestamp": int(ts_m.group(1)),
            "score": int(score_m.group(1)),
            "weakest_point": (weak_m.group(1).strip()[:300] if weak_m else ""),
            "filename": log.name,
        })
    return rows


def _classify_weakest(text: str) -> str:
    """Coarse cluster the weakest-point text into a class label."""
    t = text.lower()
    classes = {
        "calibration_anchor_failure": ["sharma", "α=2/d", "alpha=2/d", "calibration anchor"],
        "regime_classification": ["variance-limited", "resolution-limited", "two-regime", "regime"],
        "negative_exponent": ["negative exponent", "negative scaling", "α<0", "alpha<0"],
        "cross_task_variation": ["olmo", "cross-task", "task-class", "simpleqa"],
        "intrinsic_dimension": ["intrinsic dimension", "manifold", "intrinsic_dim"],
        "rival_falsification": ["rival", "alternative form", "competing form"],
        "holdout_overfit": ["overfit", "memorization", "literature lookup"],
        "no_mechanism": ["no mechanism", "phenomenological", "empirical only", "no derivation"],
        "scope_overreach": ["overclaim", "extrapolat", "beyond evidence", "scope"],
        "fit_convention": ["joint fit", "separable", "kaplan vs chinchilla", "convention"],
        "data_quality": ["bansal", "noise", "data-quality"],
        "procedural": ["learning-mechanics desiderata", "procedural", "no empirical sampling"],
    }
    for label, kws in classes.items():
        if any(k in t for k in kws):
            return label
    return "other"


def _read_champion() -> Optional[dict[str, Any]]:
    p = PROJECT / "champion_eval_results.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _read_gate_harness_result() -> Optional[dict[str, Any]]:
    """Run gate_harness.py and parse JSON output. None if can't run."""
    try:
        out = subprocess.run(
            [sys.executable, str(PROJECT / "gate_harness.py")],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode in (0, 1) and out.stdout.strip().startswith("{"):
            return json.loads(out.stdout)
    except Exception:
        pass
    return None


def _ntfy(title: str, message: str, priority: str = "default", tags: Optional[list[str]] = None) -> bool:
    """Push to ntfy. Reads topic from NTFY_TOPIC_FILE. Returns True on success."""
    if not NTFY_TOPIC_FILE.exists():
        print(f"NTFY topic file missing: {NTFY_TOPIC_FILE}")
        return False
    topic = NTFY_TOPIC_FILE.read_text().strip()
    os.environ["ZTARE_NTFY_TOPIC"] = topic
    sys.path.insert(0, str(REPO))
    try:
        from src.ztare.notifications.push import push_notification
        return bool(push_notification(
            title=title, message=message, priority=priority,
            tags=tags or ["gp154"],
        ))
    except Exception as exc:
        print(f"ntfy push error: {exc}")
        return False


def _kill_experiment_loop() -> bool:
    """SIGTERM all `make experiment-loop` and `autoresearch_loop` processes."""
    killed = False
    try:
        # Find processes
        out = subprocess.run(
            ["pgrep", "-f", "experiment-loop|autoresearch_loop.*gp154"],
            capture_output=True, text=True,
        )
        pids = [p.strip() for p in out.stdout.splitlines() if p.strip().isdigit()]
        for pid in pids:
            try:
                subprocess.run(["kill", "-TERM", pid], timeout=5)
                killed = True
            except Exception:
                pass
    except Exception:
        pass
    return killed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-status", action="store_true",
                        help="Send ntfy regardless of state delta (status ping)")
    args = parser.parse_args()

    state = _load_state()
    rows = _scan_debate_logs()
    if not rows:
        if args.force_status:
            _ntfy("gp154 status", "No debate logs yet. Run not started or just initialized.")
        return 0

    # Sort and find latest
    rows_sorted = sorted(rows, key=lambda r: r["timestamp"])
    n_iters = len(rows_sorted)
    latest = rows_sorted[-1]
    max_score = max(r["score"] for r in rows_sorted)

    # Classify all weakest points
    classes_now = {_classify_weakest(r["weakest_point"]) for r in rows_sorted}
    new_classes = classes_now - set(state.get("critique_classes_seen", []))

    notifications = []

    # Notification logic
    is_new_iter = n_iters > state.get("n_iters_seen", 0)

    # Champion check (score >= 85 + gates pass)
    champion_eval = _read_champion()
    champion_score = champion_eval.get("score", 0) if champion_eval else 0
    is_champion = champion_score >= CHAMPION_THRESHOLD and not state.get("champion_announced")

    if is_champion:
        # Try gate harness
        gh = _read_gate_harness_result()
        ho_pass = ft_pass = False
        if gh:
            ho_pass = gh.get("holdout", {}).get("passed", False)
            ft_pass = gh.get("farther_tail", {}).get("passed", False)
        if ho_pass and ft_pass:
            notifications.append({
                "title": "gp154 CHAMPION",
                "message": (
                    f"Iter {n_iters} score {champion_score} (>= {CHAMPION_THRESHOLD}). "
                    f"Holdout MRE {gh['holdout']['mean_relative_error']:.4f} (pass), "
                    f"farther-tail MRE {gh['farther_tail']['mean_relative_error']:.4f} (pass). "
                    f"Killing make experiment-loop to save money."
                ),
                "priority": "high",
                "tags": ["gp154", "champion", "killed"],
            })
            _kill_experiment_loop()
            state["champion_announced"] = True
        else:
            ho_mre = (gh or {}).get("holdout", {}).get("mean_relative_error", "?")
            ft_mre = (gh or {}).get("farther_tail", {}).get("mean_relative_error", "?")
            notifications.append({
                "title": "gp154 high-score (gate fail)",
                "message": (
                    f"Iter {n_iters} score {champion_score} but gates failed: "
                    f"holdout MRE {ho_mre}, farther-tail MRE {ft_mre}. "
                    f"NOT killing — score is structural-blocker high."
                ),
                "priority": "default",
                "tags": ["gp154", "high-score", "gate-fail"],
            })
            state["champion_announced"] = True

    # New substantive critique class — gated on score > 30 to filter
    # score-0/sub-30 noise (a new "class" at score 0 is just another
    # flavor of stub-failure, not progress).
    if (
        is_new_iter
        and new_classes
        and latest["score"] > 30
        and "procedural" not in new_classes - set(state.get("critique_classes_seen", []))
    ):
        substantive_new = new_classes - {"procedural", "other"}
        if substantive_new:
            notifications.append({
                "title": f"gp154 iter {n_iters} ({latest['score']})",
                "message": (
                    f"New critique class(es): {', '.join(sorted(substantive_new))}. "
                    f"Weakest: {latest['weakest_point'][:200]}"
                ),
                "priority": "default",
                "tags": ["gp154", "new-class"],
            })

    # Run completion: process gone OR all 12 iters done (user launched with ITERS=12)
    iter_log_count = len(rows_sorted)
    process_alive = False
    try:
        out = subprocess.run(
            ["pgrep", "-f", "experiment-loop|autoresearch_loop.*gp154"],
            capture_output=True, text=True,
        )
        process_alive = bool(out.stdout.strip())
    except Exception:
        process_alive = True  # benefit of the doubt; don't false-fire completion
    if (iter_log_count >= 12 or not process_alive) and not state.get("run_completed"):
        reason = "12-iter budget done" if iter_log_count >= 12 else "process gone"
        notifications.append({
            "title": "gp154 run complete",
            "message": (
                f"Run finished ({reason}). {iter_log_count}/12 iters. "
                f"Max score {max_score}. Champion: {champion_score}. "
                f"Distinct classes: {len(classes_now)} ({sorted(classes_now)})."
            ),
            "priority": "default",
            "tags": ["gp154", "completed"],
        })
        state["run_completed"] = True

    # Anomaly detection: only fire on REAL runtime crashes, not the
    # designed score-0-at-iter-0 path (test_model.py grammar contract
    # raises "harness defect" when I_model returns NaN — this is the
    # mutator-forcing discipline, not a system anomaly). Also fire if
    # score 0 persists for 3+ consecutive iters (real stagnation).
    if is_new_iter:
        latest_text = ""
        latest_path = PROJECT / latest["filename"]
        try:
            latest_text = latest_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
        # Only true runtime crash markers (NOT "harness defect" which is by design)
        anomaly_kws = ["Traceback (most recent call last)", "ImportError",
                       "FileNotFoundError", "OOM", "SIGKILL",
                       "fatal: cannot", "MemoryError"]
        for kw in anomaly_kws:
            if kw in latest_text and kw not in state.get("anomalies_announced", []):
                notifications.append({
                    "title": "gp154 anomaly",
                    "message": f"Iter {n_iters} log contains '{kw}'. Investigate.",
                    "priority": "high",
                    "tags": ["gp154", "anomaly"],
                })
                state.setdefault("anomalies_announced", []).append(kw)
                break

        # Persistent score-0 stagnation: 3+ consecutive iters at score 0
        last_three = rows_sorted[-3:] if len(rows_sorted) >= 3 else []
        if (
            len(last_three) == 3
            and all(r["score"] == 0 for r in last_three)
            and "score_0_stagnation" not in state.get("anomalies_announced", [])
        ):
            notifications.append({
                "title": "gp154 score-0 stagnation",
                "message": (
                    f"3 consecutive iters at score 0 (n_iters={n_iters}). "
                    "Mutator may not be escaping the empty-stub baseline. "
                    "Investigate before continuing."
                ),
                "priority": "high",
                "tags": ["gp154", "stagnation"],
            })
            state.setdefault("anomalies_announced", []).append("score_0_stagnation")

    # Force status (manual ping)
    if args.force_status and not notifications:
        notifications.append({
            "title": "gp154 status",
            "message": (
                f"{n_iters}/20 iters done. Max score {max_score}. "
                f"Classes seen: {len(classes_now)}. "
                f"Champion: {champion_score} ({'announced' if state.get('champion_announced') else 'pending'})."
            ),
            "priority": "low",
            "tags": ["gp154", "status"],
        })

    # Update state
    state["n_iters_seen"] = n_iters
    state["max_score"] = max_score
    state["last_iter_timestamp"] = latest["timestamp"]
    state["critique_classes_seen"] = sorted(classes_now)
    _save_state(state)

    # Push notifications
    for n in notifications:
        ok = _ntfy(n["title"], n["message"], priority=n["priority"], tags=n["tags"])
        print(f"NTFY [{n['priority']}] {n['title']}: {ok}")

    if not notifications:
        print(f"No new substantive change. n_iters={n_iters} max_score={max_score} (silent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
