"""Grammar extension at the ceiling: the mutator's one job (GP-250 P1).

When synthesis returns `grammar_ceiling`, the LLM is invoked — and only then —
to propose ONE new plain transform (a pure `Grid -> Grid` function) named for
its mathematical operation. The sealed-target rule holds throughout: the
prompt carries raw transition grids and the seed-grammar spec, never
environment names, mechanics vocabulary, or goals.

Promotion is earned, not granted: the proposal is compiled in the sandbox
(`ztare.common.sandboxed_python.script_is_safe` + a minimal-builtins exec),
registered provisionally, and kept only if the re-synthesized champion passes
replay over the full log and full-depth rollout on a held-out episode.
Rejected extensions are rolled back. Every attempt writes a receipt to
`workspace/grammar_extension_receipts.jsonl` — model, prompt hash, code,
rationale, verdict — which is the promotion-contract audit trail.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ztare.common.sandboxed_python import script_is_safe
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import replay_consistency_gate, rollout_depth
from ztare.worldmodel.grid_dsl import register_extension, unregister_extension
from ztare.worldmodel.synthesis import context_coverage, synthesize

_SAFE_BUILTINS = {
    "range": range, "len": len, "tuple": tuple, "list": list, "enumerate": enumerate,
    "min": min, "max": max, "sum": sum, "abs": abs, "reversed": reversed,
    "zip": zip, "sorted": sorted, "all": all, "any": any, "int": int, "bool": bool,
}


def render_ceiling_prompt(log: EpisodeLog, action_arity: int, max_examples: int = 10) -> str:
    """Raw evidence + grammar spec + contract. No mechanics vocabulary."""
    def render_grid(g) -> str:
        return "\n".join(" ".join(str(c) for c in row) for row in g)

    def render_diff(s, s_next) -> str:
        changed = [(y, x) for y in range(len(s)) for x in range(len(s[0]))
                   if s[y][x] != s_next[y][x]]
        lines = [f"changed cells ({len(changed)}):"]
        for y, x in changed[:120]:
            lines.append(f"  (row {y}, col {x}): {s[y][x]} -> {s_next[y][x]}")
        if len(changed) > 120:
            lines.append(f"  ... {len(changed) - 120} more")
        return "\n".join(lines)

    # Size-adaptive rendering: small grids print in full; large grids (real
    # environments, 64x64) print the first example in full for spatial context
    # and changed-cell diffs after — still raw observations, no vocabulary.
    rows0 = log.transitions()[0].s if len(log) else ()
    large = bool(rows0) and len(rows0) * len(rows0[0]) > 400
    if large:
        max_examples = min(max_examples, 6)
    examples, seen = [], 0
    for tr in log:
        if tr.s == tr.s_next:
            continue
        if large and seen > 0:
            body = render_diff(tr.s, tr.s_next)
        else:
            body = f"before:\n{render_grid(tr.s)}\nafter:\n{render_grid(tr.s_next)}"
        examples.append(f"--- transition (t={tr.t}, action={tr.a}) ---\n{body}")
        seen += 1
        if seen >= max_examples:
            break
    identity_note = sum(1 for tr in log if tr.s == tr.s_next)

    return f"""You are extending a small symbolic grammar for grid transition programs.

The grammar currently has: identity; SHIFT(grid, dy, dx) — translate all
non-zero cells by (dy, dx), cells leaving the grid disappear, vacated cells
become 0; RECOLOR(grid, a, b) — every cell of value a becomes b; conditionals
over action id, step index modulo 2 or 3, and cell counts; and compositions of
depth two. That grammar CANNOT express the transitions below (an exhaustive
search failed), so exactly one new primitive transform is needed.

Observed transitions from an environment with {action_arity} actions
({identity_note} other logged transitions left the grid unchanged):

{chr(10).join(examples)}

Propose ONE new primitive as a pure Python function:

    def extension(grid):
        # grid is a tuple of tuples of small ints; return the same shape
        ...

Rules: name it for the MATHEMATICAL OPERATION it performs (lowercase snake_case;
no application/domain words); it must be deterministic, total on rectangular
integer grids, use no imports and no I/O, and return a tuple of tuples of ints.
The function receives only the grid (conditionals on action/step already exist
in the grammar, so do not branch on anything but the grid itself).

Answer with ONLY a JSON object, no code fences:
{{"name": "<snake_case_operation_name>", "python": "def extension(grid):\\n    ...", "rationale": "<one sentence>"}}"""


@dataclass
class ExtensionReceipt:
    env_hint: str
    model_id: str
    prompt_sha256: str
    name: str
    python: str
    rationale: str
    verdict: str            # promoted | rejected_unsafe | rejected_bad_shape | rejected_gates | rejected_parse
    detail: str = ""


def _write_receipt(project_dir: "Path | str", receipt: ExtensionReceipt) -> None:
    path = Path(project_dir) / "workspace" / "grammar_extension_receipts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(asdict(receipt)) + "\n")


def compile_extension(code: str):
    """Sandbox-compile a proposed extension. Returns (fn, error)."""
    if not script_is_safe(code):
        return None, "rejected by sandbox safety scan"
    namespace: dict = {"__builtins__": _SAFE_BUILTINS}
    try:
        exec(code, namespace)  # noqa: S102 — gated by script_is_safe + minimal builtins
    except Exception as exc:
        return None, f"exec failed: {exc}"
    fn = namespace.get("extension")
    if not callable(fn):
        return None, "no `extension` function defined"
    probe = ((0, 1), (2, 0))
    try:
        out = fn(probe)
    except Exception as exc:
        return None, f"probe call failed: {exc}"
    if not isinstance(out, tuple) or not all(isinstance(r, tuple) for r in out):
        return None, "probe call returned wrong shape"
    return fn, ""


def attempt_extension(project_dir: "Path | str", log: EpisodeLog, holdout: EpisodeLog,
                      action_arity: int, reply_text: str, *, model_id: str,
                      prompt: str, env_hint: str = "",
                      retain_on_coverage_gain: bool = False) -> ExtensionReceipt:
    """Parse → compile → provisionally register → re-synthesize → gate → keep or roll back.

    `retain_on_coverage_gain` is the multi-extension mode for worlds no single
    primitive can close (every real environment so far): an extension that
    does not close synthesis is still RETAINED (verdict `retained_partial`)
    when it strictly increases guard-context coverage, so later proposals
    stack on it; zero gain still rolls back."""
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

    def receipt(name, python, rationale, verdict, detail=""):
        r = ExtensionReceipt(env_hint, model_id, prompt_hash, name, python,
                             rationale, verdict, detail)
        _write_receipt(project_dir, r)
        return r

    text = reply_text.strip()
    if text.startswith("```"):
        text = text.strip("`\n")
        text = text[text.find("{"):]
    try:
        proposal = json.loads(text[text.find("{"): text.rfind("}") + 1])
        name = str(proposal["name"]).strip()
        code = str(proposal["python"])
        rationale = str(proposal.get("rationale", ""))
    except Exception as exc:
        return receipt("", reply_text[:400], "", "rejected_parse", f"unparseable proposal: {exc}")

    if not name.replace("_", "").isalnum() or name != name.lower():
        return receipt(name, code, rationale, "rejected_parse", "name is not snake_case")

    fn, err = compile_extension(code)
    if fn is None:
        verdict = "rejected_unsafe" if "sandbox" in err else "rejected_bad_shape"
        return receipt(name, code, rationale, verdict, err)

    baseline_cov = context_coverage(log, action_arity) if retain_on_coverage_gain else None
    register_extension(name, fn)
    result = synthesize(log, action_arity)
    if result.status != "committee":
        if retain_on_coverage_gain:
            cov = context_coverage(log, action_arity)
            if cov[0] > baseline_cov[0]:
                return receipt(name, code, rationale, "retained_partial",
                               f"coverage {baseline_cov[0]}/{baseline_cov[1]} -> "
                               f"{cov[0]}/{cov[1]}; kept for stacking")
        return receipt(name, code, rationale, "rejected_gates",
                       f"re-synthesis returned {result.status}")
    champion = result.champion
    replay = replay_consistency_gate(champion, log)
    if not replay.ok:
        return receipt(name, code, rationale, "rejected_gates", replay.detail)
    depth = rollout_depth(champion, holdout)
    if depth < len(holdout):
        return receipt(name, code, rationale, "rejected_gates",
                       f"rollout depth {depth} < {len(holdout)} on held-out episode")
    promoted = receipt(name, code, rationale, "promoted",
                       f"champion {champion} survives replay + full-depth rollout "
                       f"({depth}/{len(holdout)}); committee {len(result.committee)}")
    _write_promotion_contract(project_dir, promoted)
    return promoted


def _write_promotion_contract(project_dir: "Path | str", r: ExtensionReceipt) -> None:
    """Route the promoted extension through the kernel's learning-promotion
    contract (the same typed contract operations-intelligence candidates use)
    instead of an ad-hoc receipt format."""
    from ztare.research_director.learning_promotion_contract import (
        build_learning_promotion_contract, validate_learning_promotion_contract,
    )
    contract = build_learning_promotion_contract({
        "candidate_id": f"grid_ext_{r.name}",
        "source_kind": "worldmodel_grammar_extension",
        "transition_kind": "primitive_promotion",
        "object_ref": f"workspace/grammar_extension_receipts.jsonl#{r.name}",
        "nearest_existing_surface": "grid_dsl seed library (guarded shift/recolor chains)",
        "nearest_confuser": ("a guarded composition of existing primitives that "
                             "replays the log but fails held-out rollout"),
        "typed_carrier": "ztare-worldmodel-extension-receipt-v1",
        "carrier_required_fields": ["name", "python", "prompt_sha256", "verdict"],
        "deterministic_validator": ("worldmodel replay_consistency_gate + full-depth "
                                    "rollout_depth + post-hoc sealed equivalence"),
        "ex_post_usage_criterion": ("the extension appears in a promoted champion "
                                    "on a later environment or episode"),
        "non_claim": ("no claim beyond the witnessed reachable set; a python-level "
                      "extension carries no Lean certificate"),
        "kill_criterion": ("any replay mismatch or rollout failure of a champion "
                           "using this extension demotes it"),
    })
    ok, problems = validate_learning_promotion_contract(contract)
    contract["_validated"] = ok
    if problems:
        contract["_validation_problems"] = problems
    path = Path(project_dir) / "workspace" / "grammar_extension_promotion_contracts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(contract) + "\n")


def rollback_if_rejected(receipt: ExtensionReceipt) -> None:
    if receipt.verdict not in ("promoted", "retained_partial"):
        unregister_extension(receipt.name)
