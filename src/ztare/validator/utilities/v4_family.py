from __future__ import annotations


def is_v4_family_project(project: str) -> bool:
    return project == "epistemic_engine_v4" or project.startswith("epistemic_engine_v4_")
