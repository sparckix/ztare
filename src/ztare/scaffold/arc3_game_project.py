"""Scaffold an ARC-AGI-3 governed worldmodel project.

This is the project-shape compiler for GP-250: one call creates the same
surfaces now hand-copied across ``arc3_*_gov`` projects, then optionally spends
a bounded evidence/holdout budget through the adapter.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from ztare.worldmodel.adapter import (
    acquire_evidence,
    committee_read_model_path,
    episode_log_path,
    write_committee_read_model,
    write_deterministic_evidence,
)
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.synthesis import synthesize


REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / "projects"
RUBRICS = REPO / "rubrics"
CANONICAL_ARC3 = "arc3_ls20_gov"

DEFAULT_PLAY_CONFIG = {
    "mode": "hybrid",
    "sprint_steps": 1500,
    "sprint_rounds": 6,
    "governed_checkpoint_every": 3,
    "governed_iters": 3,
    "plan_depth": 12,
    "note": (
        "mode: governed | sprint | hybrid. Sprints = zero-token act-learn "
        "(abduce->play->absorb->re-abduce) playing only gate-passing models; "
        "governed checkpoints handle frontier physics + claims. Steering is "
        "exemplar-gated: novelty until a goal exemplar exists, then goal-first."
    ),
}

CHARTER_TEMPLATE = """# {slug} charter

Purpose: exercise the interactive-environment substrate path (GP-250) on a
sealed ARC-AGI-3 grid world. A hidden deterministic transition law exists
behind a turn-based act/observe interface with {arity} actions. Grading is
mechanical: exact replay over the episode log, then rollout depth on a
held-out episode. The law itself, its parameters, and its mechanics are not
described here (sealed-target rule).
"""

THESIS_TEMPLATE = """# {slug} initial thesis

No mechanism claim is made at scaffold time.

The project starts from typed episode logs only. The first actionable question
is which transition contexts maximize information about the hidden deterministic
law under exact replay and held-out rollout gates.
"""

TEST_MODEL_TEMPLATE = """# Baseline carrier for {slug}. Mutators replace this.

PROGRAM = ["s"]
"""


@dataclass(frozen=True)
class Arc3ScaffoldReceipt:
    project: str
    game_id: str
    action_arity: int
    visible_rows: int
    holdout_rows: int
    files: list[str]


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path)


def _copy_text(src: Path, dst: Path, *, replace: dict[str, str] | None = None,
               force: bool = False) -> bool:
    if dst.exists() and not force:
        return False
    text = src.read_text(encoding="utf-8")
    for old, new in (replace or {}).items():
        text = text.replace(old, new)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    return True


def _write_json(path: Path, payload: dict, *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return True


def _write_text(path: Path, text: str, *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _resolve_game(short: str) -> str:
    from ztare.substrates.arc_agi3 import list_games
    games = list_games()
    match = next((g for g in games if g.startswith(short)), None)
    if match is None:
        raise ValueError(f"game {short!r} not found")
    return str(match)


def _adapter_for(game_id: str):
    from ztare.substrates.arc_agi3 import ArcAgi3Adapter
    adapter = ArcAgi3Adapter(game_id)
    adapter.reset()
    return adapter


def _init_logs(project: Path, *, force: bool = False) -> None:
    for episode in (1, 2):
        path = episode_log_path(project, episode)
        if force or not path.exists():
            EpisodeLog().write_jsonl(path)
    raw_map = project / "raw" / "source_type_map.json"
    _write_json(raw_map, {
        "episodes/episode_001.jsonl": "source_evidence",
        "episodes/episode_002.jsonl": "source_evidence",
    }, force=force)


def _collect_holdout(project: Path, adapter, actions: int, *, force: bool = False) -> int:
    path = episode_log_path(project, 2)
    if actions <= 0:
        return len(EpisodeLog.read_jsonl(path)) if path.exists() else 0
    if path.exists() and len(EpisodeLog.read_jsonl(path)) and not force:
        return len(EpisodeLog.read_jsonl(path))
    log = EpisodeLog()
    state = adapter.reset()
    for i in range(actions):
        action = i % max(int(adapter.action_arity), 1)
        t_now = adapter.t
        nxt = adapter.step(action)
        log.append(state, action, nxt, t=t_now)
        state = nxt
    log.write_jsonl(path)
    return len(log)


def _ensure_committee(project: Path, arity: int) -> None:
    path = committee_read_model_path(project)
    if path.exists():
        return
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    write_committee_read_model(project, synthesize(log, arity), set(), log)


def scaffold_game_project(
    game: str,
    *,
    project_slug: str | None = None,
    game_id: str | None = None,
    adapter=None,
    visible_probes: int = 0,
    holdout_actions: int = 0,
    force: bool = False,
) -> Arc3ScaffoldReceipt:
    """Create standard ARC project surfaces, optionally acquiring evidence.

    ``adapter`` is injectable for tests and offline harnesses. Without it the
    live ARC adapter is constructed from ``game_id``/``game``.
    """
    gid = game_id or getattr(adapter, "game_id", None) or _resolve_game(game)
    slug = project_slug or f"arc3_{game}_gov"
    project = PROJECTS / slug
    project.mkdir(parents=True, exist_ok=True)
    (project / "workspace").mkdir(exist_ok=True)
    (project / "raw" / "episodes").mkdir(parents=True, exist_ok=True)

    if adapter is None:
        adapter = _adapter_for(gid)
    arity = int(adapter.action_arity)

    written: list[str] = []
    for path, payload in (
        (project / "play_config.json", DEFAULT_PLAY_CONFIG),
        (project / "project_charter.md", CHARTER_TEMPLATE.format(slug=slug, arity=arity)),
        (project / "thesis.md", THESIS_TEMPLATE.format(slug=slug)),
        (project / "test_model.py", TEST_MODEL_TEMPLATE.format(slug=slug)),
    ):
        ok = _write_json(path, payload, force=force) if isinstance(payload, dict) \
            else _write_text(path, payload, force=force)
        if ok:
            written.append(_repo_rel(path))

    rubric_src = RUBRICS / f"{CANONICAL_ARC3}.json"
    rubric = json.loads(rubric_src.read_text(encoding="utf-8"))
    rubric["rubric_id"] = slug
    rubric_path = RUBRICS / f"{slug}.json"
    if _write_json(rubric_path, rubric, force=force):
        written.append(_repo_rel(rubric_path))

    harness_src = PROJECTS / CANONICAL_ARC3 / "gate_harness.py"
    if _copy_text(harness_src, project / "gate_harness.py",
                  replace={CANONICAL_ARC3: slug}, force=force):
        written.append(_repo_rel(project / "gate_harness.py"))

    _init_logs(project, force=force)
    if visible_probes > 0:
        acquire_evidence(project, adapter, max_probes=visible_probes)
    holdout_rows = _collect_holdout(project, adapter, holdout_actions, force=force)
    _ensure_committee(project, arity)
    write_deterministic_evidence(project)

    visible_rows = len(EpisodeLog.read_jsonl(episode_log_path(project)))
    receipt = Arc3ScaffoldReceipt(slug, gid, arity, visible_rows, holdout_rows, written)
    (project / "workspace" / "arc3_scaffold_receipt.json").write_text(
        json.dumps(receipt.__dict__, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", required=True, help="short game prefix, e.g. ls20")
    parser.add_argument("--game-id", default="", help="full ARC game id; skips list lookup")
    parser.add_argument("--project", default="", help="project slug; default arc3_<game>_gov")
    parser.add_argument("--visible-probes", type=int, default=0)
    parser.add_argument("--holdout-actions", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    ns = parser.parse_args(argv)
    receipt = scaffold_game_project(
        ns.game,
        project_slug=ns.project or None,
        game_id=ns.game_id or None,
        visible_probes=ns.visible_probes,
        holdout_actions=ns.holdout_actions,
        force=ns.force,
    )
    print(json.dumps(receipt.__dict__, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
