"""I-5 pattern-bank injector — kernel-side hook for autoresearch_loop.

Spec: research_areas/private/seams/engine/GP-214_pattern_bank_kernel_injection_seam.md

Two modes:
  manual                         — operator supplies rubric.inject_pattern_bank.class;
                                   the injector reads the matching .md file and
                                   returns its body for grounding-payload append.
  auto_catastrophic_fit          — Mode B: only one class allowed, auto-injection
                                   if the previous iteration's runtime classifier
                                   labelled the weakest-point as
                                   catastrophic_fit_failure.

The injector returns a dict shaped for autoresearch_loop's consumption:

    {
        "fired": bool,
        "class": str | None,
        "header": str,
        "body": str,
        "source_path": Path | None,
        "log_record": dict | None,   # if fired, the record to append to
                                     # operator_overrides.jsonl
    }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BANK_DIR = REPO_ROOT / "analytics" / "queries" / "pattern_bank_redacted"
DEFAULT_OVERRIDE_LOG = REPO_ROOT / "analytics" / "operator_overrides.jsonl"

# Mode B is locked to this class until cross-LLM stability lifts.
MODE_B_CLASS = "catastrophic_fit_failure"

# GP-149 §10 cross-LLM disclosure for the injection footer.
CROSS_LLM_FOOTER = (
    "\n\n---\n"
    "_(GP-214 I-5 injection — class label cross-LLM stability 0.538 < 0.60 threshold; "
    "this exemplar block is grounding only; the runtime classifier's verdict is "
    "operator-confirmed where this is configured manually.)_"
)


def _read_class_body(class_name: str, bank_dir: Path) -> tuple[str | None, Path | None]:
    """Return (body, path) for the named class. body is the file content with the
    H1 + Source preamble stripped, suitable for direct append to grounding payload.
    Returns (None, None) if the file does not exist.
    """
    path = bank_dir / f"{class_name}.md"
    if not path.is_file():
        return None, None
    raw = path.read_text(encoding="utf-8")
    # Strip the H1 line and any leading metadata block; keep from "## Mechanism" onward
    # so the autoresearch grounding payload doesn't carry the bank's internal header.
    marker = "\n## Mechanism"
    idx = raw.find(marker)
    body = raw[idx + 1 :] if idx >= 0 else raw
    return body, path


def _write_override_log(record: dict[str, Any], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def evaluate_injection(
    *,
    rubric: dict[str, Any],
    last_weakest_class: str | None,
    project: str | None = None,
    iteration: int | None = None,
    bank_dir: Path = DEFAULT_BANK_DIR,
    override_log_path: Path = DEFAULT_OVERRIDE_LOG,
    write_log: bool = True,
) -> dict[str, Any]:
    """Decide whether to inject and produce the payload.

    Inputs:
      rubric                 — full rubric_data dict for the current iteration
      last_weakest_class     — output of the runtime classifier on the previous
                               iteration's weakest_point (None if not classified)
      project, iteration     — used only for the override log entry
      bank_dir               — pattern bank directory
      override_log_path      — where to append the log line
      write_log              — disable for dry-run / testing

    Returns the result dict described in the module docstring.
    """
    flag = rubric.get("inject_pattern_bank")
    if not flag:
        return {"fired": False, "class": None, "header": "", "body": "", "source_path": None, "log_record": None}

    if isinstance(flag, str):
        mode_str = flag.strip().lower()
        flag = {"mode": mode_str}
    if not isinstance(flag, dict):
        return {"fired": False, "class": None, "header": "", "body": "", "source_path": None, "log_record": None}

    mode = (flag.get("mode") or "off").strip().lower()
    fired = False
    chosen_class: str | None = None
    source_label = "off"

    if mode == "off":
        return {"fired": False, "class": None, "header": "", "body": "", "source_path": None, "log_record": None}

    if mode == "manual":
        chosen_class = (flag.get("class") or "").strip() or None
        if chosen_class:
            fired = True
            source_label = "manual"
    elif mode == "auto_catastrophic_fit":
        if last_weakest_class == MODE_B_CLASS:
            chosen_class = MODE_B_CLASS
            fired = True
            source_label = "auto_catastrophic_fit"
    else:
        return {"fired": False, "class": None, "header": "", "body": "", "source_path": None, "log_record": None}

    if not (fired and chosen_class):
        return {"fired": False, "class": chosen_class, "header": "", "body": "", "source_path": None, "log_record": None}

    body, path = _read_class_body(chosen_class, bank_dir)
    if not body:
        return {"fired": False, "class": chosen_class, "header": "", "body": "", "source_path": None, "log_record": None}

    header = (
        f"PATTERN-BANK EXEMPLARS — class={chosen_class} (GP-214 I-5, mode={source_label}). "
        "Concrete past-failure exemplars from the mining corpus. Avoid these specific "
        "shapes; structural avoidance does NOT trump the rubric — the rubric is still "
        "load-bearing.\n\n"
    )
    body_with_footer = body + CROSS_LLM_FOOTER

    log_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intervention": "I-5_pattern_bank",
        "class": chosen_class,
        "source": source_label,
        "project": project,
        "iteration": iteration,
        "bank_path": str(path) if path else None,
    }
    if write_log:
        _write_override_log(log_record, override_log_path)

    return {
        "fired": True,
        "class": chosen_class,
        "header": header,
        "body": body_with_footer,
        "source_path": path,
        "log_record": log_record,
    }
