"""Meta-cold-shot frontier script scaffold contract.

This module mechanizes the pattern used in gp163d/NS manual work:

1. decide the next discriminator,
2. choose the script family/template that should test it,
3. optionally propose a narrow Python script,
4. run a smoke test before spending GPU/API budget,
5. preserve artifacts for closure.

It deliberately does NOT call an LLM and does NOT write the proposed script.
Callers can use the prompt builder with any model API, parse strict JSON, then
review/write/run under normal code-edit discipline.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


REQUIRED_KEYS = {
    "answer",
    "eigenquestion",
    "script_family",
    "template_script_path",
    "reuse_strategy",
    "code_edit_mode",
    "exact_hypothesis_under_test",
    "target_script_path",
    "script_purpose",
    "inputs",
    "outputs",
    "command",
    "smoke_test_command",
    "code",
    "required_artifacts",
    "abort_conditions",
    "safety_notes",
}

BANNED_IMPORT_ROOTS = {
    "boto3",
    "paramiko",
    "requests",
    "shutil",
    "subprocess",
    "socket",
}

BANNED_CALLS = {
    "os.system",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.run",
    "shutil.rmtree",
}

BANNED_TEXT_PATTERNS = (
    r"\brm\s+-rf\b",
    r"\bssh\b",
    r"\bscp\b",
    r"\bcurl\b",
    r"StrictHostKeyChecking\s*=\s*no",
    r"/etc/",
    r"~/.ssh",
    r"[;&|`]",
)


@dataclass(frozen=True)
class FrontierScriptScaffold:
    answer: str
    eigenquestion: str
    script_family: str
    template_script_path: str
    reuse_strategy: str
    code_edit_mode: str
    exact_hypothesis_under_test: str
    target_script_path: str
    script_purpose: str
    inputs: list[str]
    outputs: list[str]
    command: str
    smoke_test_command: str
    code: str
    required_artifacts: list[str]
    abort_conditions: list[str]
    safety_notes: list[str]

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "answer": self.answer,
            "eigenquestion": self.eigenquestion,
            "script_family": self.script_family,
            "template_script_path": self.template_script_path,
            "reuse_strategy": self.reuse_strategy,
            "code_edit_mode": self.code_edit_mode,
            "exact_hypothesis_under_test": self.exact_hypothesis_under_test,
            "target_script_path": self.target_script_path,
            "script_purpose": self.script_purpose,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "command": self.command,
            "smoke_test_command": self.smoke_test_command,
            "code": self.code,
            "required_artifacts": self.required_artifacts,
            "abort_conditions": self.abort_conditions,
            "safety_notes": self.safety_notes,
        }


def build_frontier_script_scaffold_prompt(
    *,
    context: str,
    task: str,
    allowed_roots: list[str],
    existing_scripts: list[str] | None = None,
    forbidden_actions: list[str] | None = None,
) -> str:
    """Build a strict prompt for a meta-cold-shot script proposal."""
    scripts = existing_scripts or []
    forbidden = forbidden_actions or []
    return f"""You are a meta-cold-shot frontier-science script scaffolder.

Your job is NOT to make a broad research plan and NOT to freelance a large
program. Your first job is to classify the needed script family and choose the
closest existing script template. Only then may you propose one narrow,
smoke-testable Python script or patch that answers the eigenquestion with the
least new machinery.

Rules:
1. Reuse existing scripts and artifacts where possible.
2. Do not propose destructive shell commands.
3. Do not use network, SSH, cloud APIs, or credential paths.
4. The script must have a small smoke-test command.
5. The script must write explicit output artifacts.
6. Prefer offline extraction over new compute if existing artifacts suffice.
7. Prefer "patch_existing" or "new_file_from_template" over bespoke code.
8. If the task cannot be safely scripted, return code="" and explain why in
   abort_conditions.

Allowed target roots:
{json.dumps(allowed_roots, indent=2)}

Existing scripts/public/artifacts:
{json.dumps(scripts, indent=2)}

Forbidden actions:
{json.dumps(forbidden, indent=2)}

Task:
{task}

Context:
{context}

Return ONLY strict JSON:
{{
  "answer": "short verdict label",
  "eigenquestion": "smallest question the script answers",
  "script_family": "one of: cold_shot_panel | post_run_discriminator | artifact_diagnostic | gpu_batch_runner | proof_target_extractor | other",
  "template_script_path": "relative/path/to/existing_template.py, or empty string if none",
  "reuse_strategy": "how the target script reuses/forks the template",
  "code_edit_mode": "new_file_from_template | patch_existing | no_code_needed | unsafe",
  "exact_hypothesis_under_test": "falsifiable claim this script tests",
  "target_script_path": "relative/path/to/new_or_updated_script.py",
  "script_purpose": "one-sentence purpose",
  "inputs": ["input artifact/path/argument", "..."],
  "outputs": ["output artifact/path", "..."],
  "command": "full command for the real run",
  "smoke_test_command": "cheap command that verifies plumbing",
  "code": "complete Python source, or empty string if unsafe",
  "required_artifacts": ["artifact needed to interpret output", "..."],
  "abort_conditions": ["condition that should stop execution", "..."],
  "safety_notes": ["why this is safe/narrow", "..."]
}}
"""


def _strip_fences(text: str) -> str:
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(line for line in lines if not line.strip().startswith("```")).strip()
    return raw


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("expected list")
    out: list[str] = []
    for value in values:
        text = re.sub(r"\s+", " ", str(value)).strip()
        if text:
            out.append(text)
    return out


def _validate_relative_py_path(path_text: str, allowed_roots: list[str], *, field_name: str, required: bool) -> str:
    if not path_text:
        if required:
            raise ValueError(f"{field_name} is required")
        return ""
    path = PurePosixPath(path_text)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field_name} must be a relative path without '..'")
    if path.suffix != ".py":
        raise ValueError(f"{field_name} must be a .py file")
    allowed = [root.strip("/ ") for root in allowed_roots if root.strip("/ ")]
    if allowed and not any(str(path).startswith(root + "/") or str(path) == root for root in allowed):
        raise ValueError(f"{field_name} {path_text!r} is outside allowed roots")
    return str(path)


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def validate_scaffold_code(code: str) -> None:
    """Static safety check for proposed Python source.

    This is intentionally conservative. It is not a sandbox; it is a first
    rejection layer before a human or runner decides whether to write/run.
    """
    if not code.strip():
        return
    for pattern in BANNED_TEXT_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            raise ValueError(f"banned text pattern in code: {pattern}")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(f"code is not valid Python: {exc}") from exc
    has_main_guard = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif node.module:
                names = [node.module.split(".")[0]]
            banned = sorted(set(names) & BANNED_IMPORT_ROOTS)
            if banned:
                raise ValueError(f"banned import root(s): {', '.join(banned)}")
        if isinstance(node, ast.Call):
            call_name = _dotted_name(node.func)
            if call_name in BANNED_CALLS:
                raise ValueError(f"banned call: {call_name}")
        if isinstance(node, ast.If):
            test_src = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
            if "__name__" in test_src and "__main__" in test_src:
                has_main_guard = True
    if not has_main_guard:
        raise ValueError("script must use an if __name__ == '__main__' guard")


def validate_scaffold_command(command: str, *, field_name: str) -> None:
    """Reject dangerous command proposal strings.

    Commands are still human-reviewed strings, not executed by this module.
    This check prevents obviously unsafe handoff text from being cached and
    printed as if it were an admissible smoke/real-run command.
    """
    text = (command or "").strip()
    if not text:
        return
    for pattern in BANNED_TEXT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError(f"banned text pattern in {field_name}: {pattern}")
    first = text.split()[0]
    allowed_prefixes = {
        "python",
        "python3",
        "./venv/bin/python",
        "./venv/bin/python3",
        "venv/bin/python",
        "venv/bin/python3",
    }
    if first not in allowed_prefixes:
        raise ValueError(f"{field_name} must start with a Python interpreter, got {first!r}")


def parse_frontier_script_scaffold_json(text: str, *, allowed_roots: list[str]) -> FrontierScriptScaffold:
    data = json.loads(_strip_fences(text))
    missing = sorted(REQUIRED_KEYS - set(data))
    if missing:
        raise ValueError(f"frontier script scaffold JSON missing keys: {', '.join(missing)}")
    target = _validate_relative_py_path(
        str(data["target_script_path"]).strip(),
        allowed_roots,
        field_name="target_script_path",
        required=True,
    )
    template = _validate_relative_py_path(
        str(data["template_script_path"]).strip(),
        allowed_roots,
        field_name="template_script_path",
        required=False,
    )
    edit_mode = str(data["code_edit_mode"]).strip()
    if edit_mode not in {"new_file_from_template", "patch_existing", "no_code_needed", "unsafe"}:
        raise ValueError("code_edit_mode must be one of new_file_from_template, patch_existing, no_code_needed, unsafe")
    if edit_mode in {"new_file_from_template", "patch_existing"} and not template:
        raise ValueError("template_script_path is required when reusing or patching a script")
    code = str(data.get("code") or "")
    if edit_mode in {"new_file_from_template", "patch_existing"} and not code.strip():
        raise ValueError("code is required for new_file_from_template or patch_existing")
    validate_scaffold_code(code)
    command = str(data["command"]).strip()
    smoke_test_command = str(data["smoke_test_command"]).strip()
    validate_scaffold_command(command, field_name="command")
    validate_scaffold_command(smoke_test_command, field_name="smoke_test_command")
    return FrontierScriptScaffold(
        answer=str(data["answer"]).strip(),
        eigenquestion=str(data["eigenquestion"]).strip(),
        script_family=str(data["script_family"]).strip(),
        template_script_path=template,
        reuse_strategy=str(data["reuse_strategy"]).strip(),
        code_edit_mode=edit_mode,
        exact_hypothesis_under_test=str(data["exact_hypothesis_under_test"]).strip(),
        target_script_path=target,
        script_purpose=str(data["script_purpose"]).strip(),
        inputs=_clean_list(data["inputs"]),
        outputs=_clean_list(data["outputs"]),
        command=command,
        smoke_test_command=smoke_test_command,
        code=code,
        required_artifacts=_clean_list(data["required_artifacts"]),
        abort_conditions=_clean_list(data["abort_conditions"]),
        safety_notes=_clean_list(data["safety_notes"]),
    )
