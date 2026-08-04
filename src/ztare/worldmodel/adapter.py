"""Environment adapter and the `acquire_evidence` move (GP-250 P1).

The adapter is the only component that touches a live environment, and its
canonical output is the project's episode log — everything downstream (the
synthesis kernel, the gates, the briefing provider, trace) reads the log.
Episodes land in the project shape as raw sources:

    projects/<slug>/raw/episodes/episode_NNN.jsonl      (typed source_evidence)
    projects/<slug>/workspace/worldmodel_committee.json (read model for briefing/UI)

`acquire_evidence` is the pivot handler's callable: one bounded batch of
policy-priced probes, appended to the log, with the refreshed committee and a
typed receipt returned. The loop's stagnation machinery decides *when* to call
it (candidate-side yield vs. observation-side yield); this module only knows
*how*. P0' proved the pieces; this wires them to the project layout without
touching loop internals.
"""

from __future__ import annotations

import json
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ztare.worldmodel.episode_log import EpisodeLog, Transition
from ztare.worldmodel.grid_dsl import Grid
from ztare.worldmodel.policy import context_key, select_action
from ztare.worldmodel.synthesis import SynthesisResult, synthesize


class EnvironmentAdapter(Protocol):
    """Turn-based act/observe interface. Implementations must be the only
    code path that spends environment budget."""
    env_id: str
    action_arity: int

    def reset(self) -> Grid: ...
    def step(self, action: int) -> Grid: ...


_PROJECT_ADAPTERS = {
    "arc_agi3": ("ztare.substrates.arc_agi3", "adapter_from_project"),
}


def resolve_project_adapter(project_dir: "Path | str") -> EnvironmentAdapter:
    """Construct a live adapter through a code-registered project profile."""
    project = Path(project_dir)
    try:
        config = json.loads((project / "play_config.json").read_text())
    except (OSError, ValueError):
        config = {}
    adapter_id = str(config.get("environment_adapter") or "").strip()
    if not adapter_id and project.name.startswith("arc3_"):
        adapter_id = "arc_agi3"
    try:
        module_name, factory_name = _PROJECT_ADAPTERS[adapter_id]
    except KeyError as exc:
        raise ValueError(
            f"project has no registered environment adapter: {adapter_id!r}"
        ) from exc
    factory = getattr(importlib.import_module(module_name), factory_name)
    return factory(project, config=config)


class SyntheticEnvAdapter:
    """Adapter over a sealed synthetic environment (`arc_synthetic`). Keeps
    its own step counter; the sealed law stays behind `step()`."""

    def __init__(self, env) -> None:
        self._env = env
        self.env_id = env.env_id
        self.action_arity = env.action_arity
        self._state: Grid = env.initial
        self._t = 0

    def reset(self) -> Grid:
        self._state, self._t = self._env.initial, 0
        return self._state

    def step(self, action: int) -> Grid:
        nxt = self._env.transition(self._state, action, self._t)
        self._state = nxt
        self._t += 1
        return nxt

    @property
    def t(self) -> int:
        return self._t

    @property
    def state(self) -> Grid:
        return self._state


def episode_log_path(project_dir: "Path | str", episode: int = 1) -> Path:
    return Path(project_dir) / "raw" / "episodes" / f"episode_{episode:03d}.jsonl"


def committee_read_model_path(project_dir: "Path | str") -> Path:
    return Path(project_dir) / "workspace" / "worldmodel_committee.json"


def observation_log(observed) -> EpisodeLog:
    """Normalize adapter observation packets through one typed boundary."""
    return EpisodeLog(
        observation
        if isinstance(observation, Transition)
        else Transition(
            t=observation[3],
            s=observation[0],
            a=observation[1],
            s_next=observation[2],
        )
        for observation in observed
    )


def admit_observations(
    project_dir: "Path | str",
    observed,
    *,
    log: EpisodeLog | None = None,
) -> tuple[EpisodeLog, int]:
    """Admit non-duplicate transition identities through one evidence door."""
    project = Path(project_dir)
    if log is None:
        log = EpisodeLog.read_jsonl(episode_log_path(project))
    index: dict[str, set[tuple[str, object]]] = {}
    for existing in log:
        index.setdefault(existing.context_hash(), set()).add(
            (existing.observation_hash(), existing.identity)
        )
    admitted: list[Transition] = []
    for row in observation_log(observed):
        consequence = (row.observation_hash(), row.identity)
        consequences = index.setdefault(row.context_hash(), set())
        if consequence in consequences:
            continue
        consequences.add(consequence)
        admitted.append(row)
    if admitted:
        log.append_jsonl(episode_log_path(project), admitted)
    return log, len(admitted)


def grow_evidence(
    project_dir: "Path | str",
    observed,
    adapter: EnvironmentAdapter,
    *,
    log: EpisodeLog | None = None,
) -> int:
    """Admit live observations and refresh their derived read models."""
    project = Path(project_dir)
    log, grown = admit_observations(project, observed, log=log)
    if grown == 0:
        return 0
    result = synthesize(log, adapter.action_arity)
    witnessed = {context_key(tr.a, tr.t) for tr in log}
    write_committee_read_model(project, result, witnessed, log)
    write_deterministic_evidence(project)
    return grown


def write_committee_read_model(project_dir: "Path | str", result: SynthesisResult,
                               witnessed: "set[tuple]", log: EpisodeLog) -> Path:
    """The workspace read model the briefing provider and UI consume."""
    path = committee_read_model_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "ztare-worldmodel-committee-v1",
        "status": result.status,
        "committee_size": len(result.committee),
        "champion": result.champion,
        "guard_families": result.guard_family,
        "evidence_hash": result.evidence_hash or log.content_hash(),
        "transitions": len(log),
        "witnessed_contexts": sorted(list(c) for c in witnessed),
    }
    path.write_text(json.dumps(payload, indent=2, default=list))
    return path


def write_deterministic_evidence(project_dir: "Path | str", episode: int = 1) -> Path:
    """Deterministic evidence compiler for interactive substrates: renders
    `evidence.txt` from the episode log and writes the standard
    `compiled_evidence_provenance.json` receipt (schema v1) with real source
    hashes. No model call — the rendering is a pure function of the log, so
    the provenance command records exactly that. Precedent: the static public
    fixture receipts on demo_claims.
    """
    import hashlib
    from datetime import datetime, timezone

    project_dir = Path(project_dir)
    slug = project_dir.name
    log_path = episode_log_path(project_dir, episode)
    log = EpisodeLog.read_jsonl(log_path)
    model_path = committee_read_model_path(project_dir)
    model = json.loads(model_path.read_text()) if model_path.exists() else {}

    lines = [
        f"Evidence for {slug} (deterministic rendering of the episode log).",
        "",
        f"episode log: raw/episodes/{log_path.name}  ({len(log)} transitions, "
        f"sha256 {log.content_hash()[:16]})",
        f"committee status: {model.get('status')}  size: {model.get('committee_size')}  "
        f"guard families: {model.get('guard_families')}",
        f"witnessed guard contexts: {len(model.get('witnessed_contexts') or [])}",
        "",
        "Visible data (episode transitions; (t, action): state -> next_state;",
        "rows ';'-separated, cells space-separated):",
    ]

    def _render_grid(g):
        return "; ".join(" ".join(str(c) for c in row) for row in g)

    large = len(log) > 0 and len(log.transitions()[0].s) * len(log.transitions()[0].s[0]) > 400
    if large:
        # 64x64-class worlds: full grid once for spatial context, then
        # changed-cell diffs — the mutator-facing render must fit a briefing
        first_rendered = False
        for tr in log:
            if not first_rendered and tr.s != tr.s_next:
                lines.append(f"  ({tr.t}, {tr.a}): [{_render_grid(tr.s)}] -> [{_render_grid(tr.s_next)}]")
                first_rendered = True
                continue
            changed = [(y, x) for y in range(len(tr.s)) for x in range(len(tr.s[0]))
                       if tr.s[y][x] != tr.s_next[y][x]]
            cells = "; ".join(f"({y},{x}):{tr.s[y][x]}->{tr.s_next[y][x]}" for y, x in changed[:60])
            more = f" ...+{len(changed)-60}" if len(changed) > 60 else ""
            lines.append(f"  ({tr.t}, {tr.a}): changed {len(changed)} cells [{cells}{more}]")
    else:
        for tr in log:
            lines.append(f"  ({tr.t}, {tr.a}): [{_render_grid(tr.s)}] -> [{_render_grid(tr.s_next)}]")
    arity = 1 + max(tr.a for tr in log) if len(log) else 0
    lines += [
        "",
        "Constraints:",
        "  - The transition rule is deterministic: next_state is a function of (state, action, t).",
        f"  - Actions are integers 0..{arity - 1}; grids keep their shape; cell values are small naturals.",
        "  - The rule must be expressed in the sealed grid grammar (grid_dsl): shift, recolor,",
        "    if/eq guards over action, step residues (t % 2, t % 3), and cell counts.",
        "",
        "How to submit (python contract):",
        "  Submit test_model.py exposing PROGRAM — the grid_dsl AST as nested lists.",
        "  Example of the FORM only (deliberately not a law consistent with the data above):",
        "```python",
        'PROGRAM = ["if", ["eq", ["mod", ["step"], ["lit", 2]], ["lit", 0]],',
        '           ["recolor", ["s"], ["lit", 3], ["lit", 4]], ["s"]]',
        "```",
        "  The frozen gate_harness.py scores it by exact replay on the visible episode and a",
        "  full-depth hidden-holdout rollout that propagates the candidate's own predictions.",
    ]
    evidence_path = project_dir / "evidence.txt"
    evidence_path.write_text("\n".join(lines) + "\n")

    # hash exactly as the kernel's source preflight does (read_typed_source
    # + strip + sha256 over utf-8 text), so the freshness contract verifies
    # by construction rather than by coincidence of encoding
    from ztare.workspace.compile_evidence import read_typed_source
    typed_text, _stype, _bad = read_typed_source(log_path)
    src_hash = hashlib.sha256(typed_text.strip().encode("utf-8")).hexdigest()
    provenance = {
        "schema": "ztare-compiled-evidence-provenance-v1",
        "compile_command": "deterministic worldmodel rendering (GP-250; no model call)",
        "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evidence_path": f"projects/{slug}/evidence.txt",
        "output_path": f"projects/{slug}/evidence.txt",
        "output_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
        "source_count": 1,
        "sources": [{
            "path": f"projects/{slug}/raw/episodes/{log_path.name}",
            "role": "episode log (earned transitions)",
            "sha256": src_hash,
            "full_sha256": src_hash,
            "source_id": f"{slug}_episode_{episode:03d}",
            "source_type": "source_evidence",
        }],
    }
    (project_dir / "compiled_evidence_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True))
    return evidence_path


@dataclass(frozen=True)
class AcquireEvidenceReceipt:
    """Typed outcome of one evidence-acquisition batch.

    status: "acquired"          — probes taken, log extended
            "identified"        — committee was already singleton; nothing spent
            "underidentified"   — policy exited typed; nothing more to learn in budget
            "grammar_ceiling"   — synthesis cannot express the log; mutator's turn
    """
    status: str
    probes_taken: int
    committee_size: int
    evidence_hash: str
    detail: str = ""


def acquire_evidence(project_dir: "Path | str", adapter: EnvironmentAdapter,
                     max_probes: int = 5, episode: int = 1) -> AcquireEvidenceReceipt:
    """One bounded batch of policy-priced probes against the environment."""
    log_path = episode_log_path(project_dir, episode)
    log = EpisodeLog.read_jsonl(log_path) if log_path.exists() else EpisodeLog()
    witnessed = {context_key(tr.a, tr.t) for tr in log}

    # resync the adapter to the log head (deterministic environments replay)
    state = adapter.reset()
    for tr in log:
        state = adapter.step(tr.a)

    probes = 0
    tried: "dict[int, int]" = {}
    for tr in log:
        tried[tr.a] = tried.get(tr.a, 0) + 1

    result = synthesize(log, adapter.action_arity)
    while probes < max_probes:
        if result.status == "grammar_ceiling":
            log.write_jsonl(log_path)
            write_committee_read_model(project_dir, result, witnessed, log)
            return AcquireEvidenceReceipt("grammar_ceiling", probes, 0,
                                          log.content_hash(),
                                          "seed grammar cannot express the log; mutator's turn")
        committee = result.committee if result.status == "committee" else ()
        step = len(log)
        decision = select_action(committee, state, step, adapter.action_arity,
                                 remaining_budget=max_probes - probes,
                                 witnessed_contexts=witnessed, tried_counts=tried)
        if decision.status == "identified":
            log.write_jsonl(log_path)
            write_committee_read_model(project_dir, result, witnessed, log)
            return AcquireEvidenceReceipt("identified", probes, len(committee),
                                          log.content_hash(), "committee is singleton")
        if decision.status == "underidentified":
            log.write_jsonl(log_path)
            write_committee_read_model(project_dir, result, witnessed, log)
            return AcquireEvidenceReceipt("underidentified", probes, len(committee),
                                          log.content_hash(), decision.reason)
        action = decision.action
        t_now = adapter.t  # the environment's step, robust to future resets
        s_next = adapter.step(action)
        log.append(state, action, s_next, t=t_now)
        witnessed.add(context_key(action, step))
        tried[action] = tried.get(action, 0) + 1
        state = s_next
        probes += 1
        result = synthesize(log, adapter.action_arity)

    log.write_jsonl(log_path)
    write_committee_read_model(project_dir, result, witnessed, log)
    return AcquireEvidenceReceipt("acquired", probes,
                                  len(result.committee) if result.status == "committee" else 0,
                                  log.content_hash(),
                                  f"{probes} probes appended to {log_path.name}")
