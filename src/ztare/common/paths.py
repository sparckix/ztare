from pathlib import Path


# src/ztare/common/paths.py -> common -> ztare -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]

DOCS_DIR = REPO_ROOT / "docs"
PROJECTS_DIR = REPO_ROOT / "projects"
CONFIG_DIR = REPO_ROOT / "config"
PROMPTS_DIR = CONFIG_DIR / "prompts"
RENDERERS_DIR = CONFIG_DIR / "renderers"
RUBRICS_DIR = REPO_ROOT / "rubrics"
SCENARIOS_DIR = REPO_ROOT / "scenarios"
GLOBAL_PRIMITIVES_DIR = REPO_ROOT / "global_primitives"
PAPERS_DIR = REPO_ROOT / "papers"
PAPER1_DIR = PAPERS_DIR / "paper1"
PAPER2_DIR = PAPERS_DIR / "paper2"
