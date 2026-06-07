"""Reference-leakage gate (governance, 2026-06-03).

A capability claim is only as clean as its leakage controls. The premise-shelf leakage check
(GP-246) covers the RETRIEVAL channel — but the 2026-06-03 contamination catch showed a SECOND
channel: a SOLVED reference proof checked into the repo, reachable by the agent's `workspace-write`
sandbox (which permits broad READS). A closure on a target whose solved reference the agent could
read is NOT a capability result.

This gate mechanizes the clean discipline so contamination cannot silently recur:
  • `reachable_solved_references(...)` — find sorry-free `.lean` files that define a target (or its
    key invented decls) and sit OUTSIDE the agent's own project dir but inside the repo it can read.
  • `quarantine(...)` / `restore(...)` and the `clean_capability(...)` context manager — move those
    references out of reach for the duration of a run, then restore. Non-iatrogenic: it only relocates
    files transiently; the target (the sorried candidate) is never touched; restore is guaranteed on
    exit. A capability run wrapped in this gate is leakage-clean by construction for the IN-REPO
    channel (the training-data channel is separate, needs a novel/non-public target).
"""
from __future__ import annotations

import shutil
from contextlib import contextmanager
from pathlib import Path


def _is_sorry_free(p: Path) -> bool:
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return "sorry" not in t and "admit" not in t


def reachable_solved_references(target_names: "list[str]", repo_root: "str | Path",
                                agent_dir: "str | Path",
                                keep_substrings=("/candidates/",)) -> "list[Path]":
    """SOLVED (sorry-free) .lean files under `repo_root` that mention any `target_names`, are
    OUTSIDE `agent_dir` (the sandbox cwd), and are not protected by `keep_substrings` (e.g. the
    sorried candidate = the target itself). These are the in-repo references the agent could read.
    Excludes .lake builds and the leanmill_experiments artifacts (our own closures)."""
    repo_root, agent_dir = Path(repo_root).resolve(), Path(agent_dir).resolve()
    hits: list[Path] = []
    for p in repo_root.rglob("*.lean"):
        rp = str(p)
        if "/.lake/" in rp or "/leanmill_experiments/" in rp:
            continue
        if any(k in rp for k in keep_substrings):
            continue
        try:
            p.resolve().relative_to(agent_dir)  # inside the agent's own dir → not external leakage
            continue
        except ValueError:
            pass
        if not _is_sorry_free(p):
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        if any(name in txt for name in target_names):
            hits.append(p)
    return hits


def quarantine(refs: "list[Path]", quarantine_dir: "str | Path") -> "dict[str, str]":
    """Move each ref into `quarantine_dir`, returning {moved_path: original_path} for restore."""
    qd = Path(quarantine_dir); qd.mkdir(parents=True, exist_ok=True)
    moved: dict[str, str] = {}
    for i, ref in enumerate(refs):
        ref = Path(ref)
        dest = qd / f"{i}__{ref.name}"
        shutil.move(str(ref), str(dest))
        moved[str(dest)] = str(ref)
    return moved


def restore(moved: "dict[str, str]") -> None:
    for dest, orig in moved.items():
        if Path(dest).exists():
            Path(orig).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(dest, orig)


@contextmanager
def clean_capability(target_names, repo_root, agent_dir, quarantine_dir="/tmp/ref_leakage_quarantine"):
    """Context manager: quarantine reachable solved references for the duration of a capability
    run, ALWAYS restoring on exit (even on error). Yields the list of quarantined original paths
    so the caller can record what was guarded."""
    refs = reachable_solved_references(target_names, repo_root, agent_dir)
    moved = quarantine(refs, quarantine_dir)
    try:
        yield [Path(p) for p in moved.values()]
    finally:
        restore(moved)


def _self_test() -> int:
    import tempfile, os
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    root = Path(tempfile.mkdtemp())
    agent = root / "atlas_lean"; agent.mkdir()
    (root / "refs").mkdir(); (root / "candidates").mkdir()
    # a SOLVED reference of the target, outside the agent dir → leakage
    (root / "refs" / "solved_TargetX.lean").write_text("theorem TargetX : True := trivial\n")
    # the sorried candidate (the target itself) → protected by keep_substrings, NOT leakage
    (root / "candidates" / "TargetX_sorried.lean").write_text("theorem TargetX : True := by sorry\n")
    # a sorry'd file mentioning the target outside agent → NOT a solved reference
    (root / "refs" / "open_TargetX.lean").write_text("theorem TargetX : True := by sorry\n")
    # a solved file INSIDE the agent dir → its own workspace, not external leakage
    (agent / "local.lean").write_text("theorem TargetX : True := trivial\n")

    refs = reachable_solved_references(["TargetX"], root, agent)
    names = {p.name for p in refs}
    ok("finds_external_solved_reference", "solved_TargetX.lean" in names)
    ok("excludes_sorried_open_file", "open_TargetX.lean" not in names)
    ok("excludes_candidate_target", "TargetX_sorried.lean" not in names)
    ok("excludes_agent_local", "local.lean" not in names)

    qd = root / "q"
    moved = quarantine(refs, qd)
    ok("quarantine_moves_out", not (root / "refs" / "solved_TargetX.lean").exists()
       and any(Path(d).exists() for d in moved))
    restore(moved)
    ok("restore_puts_back", (root / "refs" / "solved_TargetX.lean").exists())

    # context manager: gone inside, restored after (even on exception)
    seen_gone = {"v": None}
    try:
        with clean_capability(["TargetX"], root, agent, quarantine_dir=str(root / "q2")):
            seen_gone["v"] = not (root / "refs" / "solved_TargetX.lean").exists()
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    ok("ctx_quarantines_inside", seen_gone["v"] is True)
    ok("ctx_restores_on_error", (root / "refs" / "solved_TargetX.lean").exists())

    shutil.rmtree(root, ignore_errors=True)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
