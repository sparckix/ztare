"""Typed config for a ZTARE **Scenario** — a declarative, named bundle that binds the reasoning kernel to a
use-case: which rubric drives the judge, run config (iters/models/dynamic), which gate-package to append, and
the declared extension surface (goal-type / solvers / evidence / renderer).

A Scenario COMPOSES existing kernel capabilities — it never re-implements them. The filesystem is the registry
(a new scenario is a dropped `scenarios/<name>.yaml`, no core edit), mirroring the roles/personas/primitives
pattern already in the repo. Binding happens ONE place, engine-side (`scenarios.resolver`); the CLI passes
`--scenario` as an opaque string so scenario config never round-trips through argparse/env sprawl.

Pattern mirrors the leanmill `YamlConfig` precedent (YAML → validate) but is deliberately DECOUPLED from
leanmill — the scenario layer is a peer of the kernel, not a dependent of the solver. `extra="forbid"` makes a
typo'd scenario field a loud error instead of a silent no-op.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


WORKBENCH_PANEL_HOSTS = ("results",)
DELIVERABLE_KINDS = ("thesis", "claim", "evidence", "tension", "gap", "constraint", "falsifier", "rejected")


class DeliverableSection(BaseModel):
    """A safe composition recipe: a heading may only draw from governed node kinds."""

    model_config = ConfigDict(extra="forbid")

    label: str
    kinds: list[str] = Field(default_factory=list)
    limit: int = 0  # 0 = all matching governed elements; positive values are a presentation cap only.

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        value = str(value or "").strip()
        if not value:
            raise ValueError("deliverable section label cannot be empty")
        return value

    @field_validator("kinds")
    @classmethod
    def validate_kinds(cls, values: list[str]) -> list[str]:
        cleaned = [str(value or "").strip() for value in values if str(value or "").strip()]
        if not cleaned:
            raise ValueError("deliverable section needs at least one governed kind")
        unknown = sorted(set(cleaned) - set(DELIVERABLE_KINDS))
        if unknown:
            raise ValueError(f"unknown governed deliverable kind(s): {', '.join(unknown)}")
        return list(dict.fromkeys(cleaned))

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        value = int(value or 0)
        if value < 0:
            raise ValueError("deliverable section limit must be zero or positive")
        return value


class DeliverableSpec(BaseModel):
    """Scenario metadata for a post-run document.

    ``presentation_brief`` is an instruction to a renderer about audience and
    emphasis, never a source of facts. The provenance firewall still requires
    every factual slot and relation to come from governed state.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    label: str = ""
    audience: str = ""
    description: str = ""
    presentation_brief: str = ""
    sections: list[DeliverableSection] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = str(value or "").strip()
        if not value or not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError("deliverable spec name must be a simple slug")
        return value

    @field_validator("presentation_brief")
    @classmethod
    def validate_brief(cls, value: str) -> str:
        value = str(value or "").strip()
        if len(value) > 2000:
            raise ValueError("presentation_brief is limited to 2000 characters")
        return value


class ScenarioConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a typo'd YAML key is an ERROR, not a silent no-op

    # ── identity
    name: str = ""
    description: str = ""

    # ── WIRED + HONORED today: these directly steer the autoresearch loop (see resolver.apply_scenario_to_args).
    rubric: str = ""            # -> rubrics/<rubric>.json — drives judge dimensions/persona/steering (fully honored)
    iters: int = 0             # 0 => keep the loop's own default
    mutator_model: str = ""    # "" => keep CLI/env default (a scenario should not force a model the user lacks)
    judge_model: str = ""
    dynamic: bool = False      # rubric-DAG dynamic mode

    # ── WIRED mechanism (honored wherever the Cage engages): gate names appended to the default Cage.
    #    Empty for claim-governance scenarios (their levers are the rubric); populated by fit/analysis scenarios.
    gate_package: list[str] = Field(default_factory=list)

    # ── Governed OUTPUT contract: deliverable template names produced post-run, through the provenance firewall
    #    (scenarios.artifacts) — every element must trace to the run's HARDENED governed state, verbatim; nothing
    #    ungoverned ships. NB: the deliverable SET is ideally pre-registered in the charter (immutable → anti-
    #    cherry-pick); declaring it here (editable) is the v1 format layer. Empty ⇒ no domain artifacts.
    deliverables: list[str] = Field(default_factory=list)
    # Optional presentation metadata for those declared names. This does not
    # create facts or a new carrier; templates/renderers remain the authority.
    deliverable_specs: list[DeliverableSpec] = Field(default_factory=list)

    # ── DECLARED extension surface — recorded + surfaced by the resolver; per-capability wiring lands per
    #    scenario (this is the seam people plug new EvidenceProviders / Solvers / Renderers / Rechecks into).
    goal_type: str = ""                                  # GP-070 goal-type YAML this scenario drives, by name
    solvers: list[str] = Field(default_factory=list)     # e.g. leanmill, fit — future plugged capabilities
    evidence_sources: list[str] = Field(default_factory=list)  # e.g. local_files, confluence, jira
    renderer: str = ""                                   # e.g. workbench, obsidian, pdf
    rechecks: list[str] = Field(default_factory=list)    # re-executable warrant checks, resolved by name

    # Declarative Workbench contributions. The frontend maps these stable panel ids to installed renderers;
    # scenarios select panels without the chrome branching on a domain or scenario name.
    workbench_panels: list[str] = Field(default_factory=list)

    @field_validator("workbench_panels")
    @classmethod
    def validate_workbench_panels(cls, refs: list[str]) -> list[str]:
        """Panels target explicit extension slots: ``<host>:<panel-id>``."""
        for ref in refs:
            host, separator, panel = str(ref).partition(":")
            if not separator or host not in WORKBENCH_PANEL_HOSTS or not panel.strip():
                raise ValueError(
                    f"workbench panel {ref!r} must be <host>:<panel-id>; hosts: {WORKBENCH_PANEL_HOSTS}"
                )
        return refs

    @field_validator("deliverable_specs")
    @classmethod
    def validate_deliverable_specs(cls, specs: list[DeliverableSpec]) -> list[DeliverableSpec]:
        names = [spec.name for spec in specs]
        if len(names) != len(set(names)):
            raise ValueError("deliverable_specs names must be unique")
        return specs

    @classmethod
    def load(cls, path: "str | Path") -> "ScenarioConfig":
        """Read + validate a scenario YAML. FAIL LOUD (feedback: silent-degrade was a hole): a MISSING file
        yields defaults, but a PRESENT-but-unparseable file raises ValueError, and a malformed value / unknown
        key fails loud via pydantic. Callers that must not crash on one bad manifest (the `list` command) catch
        per-scenario; the `run`/`validate` paths surface the error instead of silently running an empty default."""
        p = Path(path)
        data: dict = {}
        if p.exists():
            import yaml  # repo dep
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                raise ValueError(f"scenario YAML at {p} does not parse: {exc}") from exc
            if not isinstance(data, dict):
                raise ValueError(f"scenario YAML at {p} is not a mapping (got {type(data).__name__})")
        return cls(**data)
