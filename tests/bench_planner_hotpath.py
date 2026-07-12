"""Micro-benchmark: plan_progress + plan_to_goal on real champion + real start state.

Run once to write baseline parity file, then again after code changes to verify parity.
"""
import json
import statistics
import time
from pathlib import Path

REPO = Path(__file__).parent.parent
EPISODE = REPO / "projects/arc3_ls20_gov/raw/episodes/episode_001.jsonl"
BASELINE_FILE = Path("/tmp/planner_baseline_parity.json")
AFTER_FILE = Path("/tmp/planner_parity_after.json")
PROJECT_DIR = REPO / "projects/arc3_ls20_gov"


def _load_champion():
    from ztare.worldmodel.evidence_consolidation import _load_carrier_from_source
    src = (PROJECT_DIR / "test_model.py").read_text()
    return _load_carrier_from_source(src, str(PROJECT_DIR / "test_model.py"), PROJECT_DIR)


def _load_goal_fns():
    from ztare.worldmodel.distinguishing_play import _champion_goal_predicate
    result = _champion_goal_predicate(PROJECT_DIR)
    if result is None:
        return (lambda g: False), (lambda g: 0.0)
    gp, prog = result
    if gp is None:
        gp = lambda g: False
    if prog is None:
        prog = lambda g: 0.0
    return gp, prog


def _load_row(line: str):
    d = json.loads(line)
    return tuple(tuple(row) for row in d["s"])


def _read_episodes(indices):
    lines = EPISODE.read_text().splitlines()
    return [_load_row(lines[i]) for i in indices]


def _time_median(fn, n=3):
    times = []
    result = None
    for _ in range(n):
        t0 = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - t0)
    return statistics.median(times), result


def main():
    from ztare.worldmodel.planner import plan_progress, plan_to_goal

    champion = _load_champion()
    goal_fn, progress_fn = _load_goal_fns()

    all_lines = EPISODE.read_text().splitlines()
    total = len(all_lines)
    start = _load_row(all_lines[0])

    # --- BASELINE timing on row 0 ---
    med_prog, plan_prog = _time_median(
        lambda: plan_progress(champion, start, 4, progress_fn, max_depth=12, start_step=0)
    )
    med_goal, plan_goal = _time_median(
        lambda: plan_to_goal(champion, start, 4, goal_fn, max_depth=12, start_step=0)
    )
    print(f"BASELINE plan_progress: {med_prog:.4f}s")
    print(f"BASELINE plan_to_goal:  {med_goal:.4f}s")

    # --- Parity: 20 states spread across episode ---
    indices = [int(i * total / 20) for i in range(20)]
    states = _read_episodes(indices)

    records = []
    for s in states:
        pp = plan_progress(champion, s, 4, progress_fn, max_depth=12, start_step=0)
        pg = plan_to_goal(champion, s, 4, goal_fn, max_depth=12, start_step=0)
        records.append({
            "plan_progress_actions": pp.actions if pp is not None else None,
            "plan_to_goal_actions": pg.actions if pg is not None else None,
        })

    if not BASELINE_FILE.exists():
        # Baseline mode: write parity file
        BASELINE_FILE.write_text(json.dumps(records, indent=2))
        print(f"\nBaseline parity written → {BASELINE_FILE}")
        print("Run again after code changes to verify parity.")
    else:
        # Parity mode: compare
        AFTER_FILE.write_text(json.dumps(records, indent=2))
        baseline = json.loads(BASELINE_FILE.read_text())
        failures = []
        for i, (got, exp) in enumerate(zip(records, baseline)):
            if got != exp:
                failures.append((i, exp, got))
        if failures:
            for i, exp, got in failures:
                print(f"MISMATCH at state {i}: expected={exp}, got={got}")
            print(f"PARITY: {len(failures)}/20 FAIL")
        else:
            print(f"\nPARITY: 20/20 PASS")


if __name__ == "__main__":
    main()
