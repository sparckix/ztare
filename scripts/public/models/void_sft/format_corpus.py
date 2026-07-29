#!/usr/bin/env python3
"""Format the LeanMill training corpus (export_training_corpus.py output) into instruction→completion SFT pairs.

Three tasks from the four exported streams — the strange-loop's OWN void data (task #71/#73):
  • prove       : (statement) -> (kernel-verified proof)          [prover_corpus, void slice = uniquely ours]
  • formalize   : (natural language) -> (Lean statement)          [autoformalization_corpus, firewall-faithful]
  • faithfulness: (Lean statement) -> FAITHFUL / UNFAITHFUL+reason [autoformalization faithful positives +
                                                                    discriminator caught negatives]

The point is the REACHABLE-SCALE test the reframe named: does a narrow LoRA fine-tune on ~270 diverse void pairs
lift proving, at a scale a domain adaptation actually needs (10^2-10^3) — not the 10^4 corpus-size theater. A
content-family holdout is mandatory so proof evaluation does not split shared
definitions, theorem siblings, or near-duplicate statements across train/eval.

  python format_corpus.py --corpus <dir with *_corpus.jsonl> --out <dir> [--eval-frac 0.15]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))


def _read(p: Path) -> "list[dict]":
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _corpus_sha256(corpus: Path) -> str:
    files = []
    for name in (
        "prover_corpus.jsonl",
        "autoformalization_corpus.jsonl",
        "faithfulness_discriminator_corpus.jsonl",
    ):
        path = corpus / name
        files.append({
            "name": name,
            "sha256": _sha256_path(path) if path.is_file() else None,
        })
    payload = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _rec(task: str, prompt: str, completion: str) -> dict:
    # trailing space before completion is the standard SFT convention (the model learns to continue the prompt)
    return {"task": task, "prompt": prompt.rstrip() + "\n", "completion": " " + completion.strip()}


def build(corpus: Path) -> "list[dict]":
    out: "list[dict]" = []
    for r in _read(corpus / "prover_corpus.jsonl"):
        stmt, proof = (r.get("statement") or "").strip(), (r.get("proof") or "").strip()
        if stmt and proof:
            # CoT distillation: when the agent's decomposition reasoning was joined (export _attach_reasoning),
            # train think-then-prove — the plan as a Lean comment the kernel ignores, so a generation still compiles.
            reason = (r.get("reasoning") or "").strip()
            completion = f"/- Plan: {reason} -/\n{proof}" if reason else proof
            prompt = ("Prove the following Lean 4 theorem. If it helps, give a one-line plan as a `/- ... -/` "
                      f"comment first, then the proof.\n\n{stmt}")
            rec = _rec("prove", prompt, completion)
            # carry the self-contained probe + names so a GENERATED proof can be kernel-checked (real pass@k, not just NLL)
            rec["target"] = r.get("target")
            rec["probe"] = r.get("recompilable_probe") or ""
            rec["gold_proof"] = proof   # BARE proof (for splicing the generation into the probe; comment is stripped by the kernel)
            rec["has_cot"] = bool(reason)
            out.append(rec)
    for r in _read(corpus / "autoformalization_corpus.jsonl"):
        nl, lean = (r.get("nl") or "").strip(), (r.get("lean_statement") or "").strip()
        if nl and lean:
            out.append(_rec("formalize", f"Formalize the following as a single Lean 4 statement.\n\n{nl}", lean))
    # faithfulness classification: faithful positives (from autoformalization) + caught negatives (discriminator)
    for r in _read(corpus / "autoformalization_corpus.jsonl"):
        lean = (r.get("lean_statement") or "").strip()
        if lean:
            out.append(_rec("faithfulness", f"Is this Lean 4 statement a faithful formalization of its intended claim? Answer FAITHFUL or UNFAITHFUL with a one-line reason.\n\n{lean}", "FAITHFUL. The statement preserves the intended hypotheses and conclusion."))
    for r in _read(corpus / "faithfulness_discriminator_corpus.jsonl"):
        stmt, why = (r.get("statement") or "").strip(), (r.get("witness") or "").strip()
        if stmt:
            out.append(_rec("faithfulness", f"Is this Lean 4 statement a faithful formalization of its intended claim? Answer FAITHFUL or UNFAITHFUL with a one-line reason.\n\n{stmt}", f"UNFAITHFUL. {why or 'the target signature or a referenced definition was altered.'}"))
    return out


def split(rows: "list[dict]", eval_frac: float) -> "tuple[list, list]":
    """Per-task stratified split. Deterministic (every k-th item to eval), so no RNG (reproducible + the runtime
    forbids Math.random anyway). k derived from eval_frac."""
    tr, ev = [], []
    by_task: "dict[str, list]" = {}
    for r in rows:
        by_task.setdefault(r["task"], []).append(r)
    for task, items in by_task.items():
        k = max(2, round(1 / max(0.01, eval_frac)))  # every k-th → eval
        for i, r in enumerate(items):
            (ev if i % k == 0 else tr).append(r)
    return tr, ev


def _is_generic(target: str) -> bool:
    """A generically AUTO-NAMED decomposition sub-lemma (`lemma`, `lemma7`, `goal2`, `aux3`, `step1`…) — a real
    kernel-verified proof, but its NAME carries no semantic content, so as a pass@k EVAL item it measures nothing
    (there is no domain to prove). Kept in TRAIN (real signal); excluded from EVAL eligibility. Also prevents the
    `_family` digit-strip from collapsing 28 independent `lemmaN` into one bogus 28-member 'family'."""
    import re as _re
    return bool(_re.match(r"^(lemma|goal|claim|step|aux|sub|h|thm|prop|fact)_?\d*$", (target or "").strip(), _re.I))


def _family(target: str) -> str:
    """Theorem FAMILY key: strip sibling/version suffixes so `iso_lemma1`, `iso_lemma3`, `foo_conj2`, `bar_v4`
    collapse to one family. Holding out whole families (not siblings) is what kills the memorization inflation
    the first pass@k run had (design step 2)."""
    import re as _re
    t = _re.sub(r"(_conj\d+|_v\d+|_rung[A-Z]\d*|_case\d+)$", "", target or "")
    t = _re.sub(r"\d+$", "", t)
    return _re.sub(r"^iso_", "", t)


def _row_identity(row: dict) -> str:
    """Statement identity for splitting; short theorem names are not unique."""
    payload = json.dumps(
        {
            "target": row.get("target") or "",
            "prompt": row.get("prompt") or "",
            "probe": row.get("probe") or "",
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _custom_defs(probe: str) -> set[str]:
    """Names of locally introduced theory objects used to prevent family leakage."""
    try:
        from ztare.leanmill.lean_source import decl_blocks

        rows = decl_blocks(probe or "")
        return {
            name.rsplit(".", 1)[-1]
            for name, block in rows
            if name and re.match(
                r"\s*(?:noncomputable\s+|private\s+|protected\s+|opaque\s+)*"
                r"(?:def|abbrev|structure|inductive|class|opaque)\b",
                block,
            )
        }
    except Exception:  # noqa: BLE001 — portable formatter fallback
        return set(
            re.findall(
                r"(?m)^\s*(?:noncomputable\s+|private\s+|protected\s+)*"
                r"(?:def|abbrev|structure|inductive|class|opaque)\s+([A-Za-z_]\w*)",
                probe or "",
            )
        )


def _content_tokens(row: dict) -> set[str]:
    text = (row.get("prompt") or "") + "\n" + (row.get("probe") or "")
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text.lower()))


def content_family_map(rows: "list[dict]") -> "dict[str, str]":
    """Backfill a CONTENT family for every prover target from the domain vocabulary in its probe (the custom
    `def`s), NOT its name — so generic auto-named decomposition sub-lemmas (`iso_lemma1/2/3`, `lemmaN`) group with
    the REAL theory they belong to (waterfall `AbsolutePriority`, median `IsMedian`, …) instead of collapsing into
    one bogus 'lemma' family. Union-find: two targets share a family iff their probes share a custom def
    (transitively) ⇒ connected component = the domain/theory. A target with NO custom defs (pure-Mathlib) is its own
    family. This keeps all 96 verified proofs (no filtering — improve data quality, don't discard) with an honest,
    leak-free holdout (whole theories held out together, never a sibling split across train/eval)."""
    prove = [r for r in rows if r.get("task") == "prove" and r.get("target")]
    parent = list(range(len(prove)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    definitions = [_custom_defs(r.get("probe") or "") for r in prove]
    by_definition: "dict[str, list[int]]" = {}
    for i, names in enumerate(definitions):
        for name in names:
            by_definition.setdefault(name, []).append(i)
    for indices in by_definition.values():
        for i in indices[1:]:
            union(indices[0], i)

    # Pure-Mathlib siblings still share a family by stable name stem. Generic
    # planner names carry no subject identity and therefore remain content-led.
    by_stem: "dict[str, list[int]]" = {}
    for i, row in enumerate(prove):
        if definitions[i] or _is_generic(row.get("target") or ""):
            continue
        by_stem.setdefault(_family(row.get("target") or ""), []).append(i)
    for indices in by_stem.values():
        for i in indices[1:]:
            union(indices[0], i)

    # A theorem renamed or lightly rewrapped must not cross the split. This is
    # a split-time guard only; it does not discard logically distinct examples.
    tokens = [_content_tokens(r) for r in prove]
    for i in range(len(prove)):
        for j in range(i + 1, len(prove)):
            if not tokens[i] or not tokens[j]:
                continue
            jac = len(tokens[i] & tokens[j]) / max(1, len(tokens[i] | tokens[j]))
            if jac >= 0.90:
                union(i, j)

    members: "dict[int, list[str]]" = {}
    for i, row in enumerate(prove):
        members.setdefault(find(i), []).append(_row_identity(row))
    component = {
        root: "content:" + hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest()[:20]
        for root, ids in members.items()
    }
    return {_row_identity(row): component[find(i)] for i, row in enumerate(prove)}


def split_family_holdout(rows: "list[dict]", min_eval: int = 30) -> "tuple[list, list]":
    """Design step 2: hold out whole theorem FAMILIES (by CONTENT — content_family_map, not name) for the prover
    eval so pass@k measures proving UNSEEN theories. Accumulate families (deterministic hash order, no RNG) until
    the eval `prove` set reaches `min_eval` (the ≥30 floor) while keeping the rest for training. ALL 96 proofs are
    kept — generic-named sub-lemmas are backfilled to their real domain, never discarded. Eval = held-out
    families' `prove` rows; train = every task's rows for the remaining families (formalize/faithfulness carry no
    target ⇒ stay in train; the PROVER pass@k headline is leak-free)."""
    import hashlib
    fam = content_family_map(rows)
    members: "dict[str, list]" = {}
    for r in rows:
        row_id = _row_identity(r)
        if r.get("task") == "prove" and row_id in fam:
            members.setdefault(fam[row_id], []).append(r)
    fams = sorted(members, key=lambda f: hashlib.sha1(str(f).encode()).hexdigest())
    holdout, n = set(), 0
    for f in fams:
        if n >= min_eval:
            break
        holdout.add(f)
        n += len(members[f])
    _held = lambda r: r.get("task") == "prove" and fam.get(_row_identity(r)) in holdout  # noqa: E731
    ev = [r for r in rows if _held(r)]
    tr = [r for r in rows if not _held(r)]
    metrics = holdout_leakage_metrics(tr, ev)
    if metrics["shared_custom_definition_count"]:
        raise RuntimeError(
            "content-family holdout leaked custom definitions: "
            f"{metrics['shared_custom_definitions']}"
        )
    if metrics["near_duplicate_cross_pair_count"]:
        raise RuntimeError(
            "content-family holdout leaked a >=0.90-Jaccard theorem pair"
        )
    return tr, ev


def holdout_leakage_metrics(train: "list[dict]", evaluation: "list[dict]") -> dict:
    """Return deterministic cross-split leakage evidence for proof rows."""

    train_prove = [r for r in train if r.get("task") == "prove"]
    eval_prove = [r for r in evaluation if r.get("task") == "prove"]
    train_defs = (
        set().union(*(_custom_defs(r.get("probe") or "") for r in train_prove))
        if train_prove else set()
    )
    eval_defs = (
        set().union(*(_custom_defs(r.get("probe") or "") for r in eval_prove))
        if eval_prove else set()
    )
    shared_defs = sorted(train_defs & eval_defs)
    maximum = 0.0
    near_pairs = 0
    for left in train_prove:
        left_tokens = _content_tokens(left)
        for right in eval_prove:
            right_tokens = _content_tokens(right)
            if not left_tokens or not right_tokens:
                continue
            similarity = len(left_tokens & right_tokens) / max(
                1, len(left_tokens | right_tokens)
            )
            maximum = max(maximum, similarity)
            near_pairs += int(similarity >= 0.90)
    return {
        "shared_custom_definition_count": len(shared_defs),
        "shared_custom_definitions": shared_defs,
        "near_duplicate_jaccard_threshold": 0.90,
        "near_duplicate_cross_pair_count": near_pairs,
        "maximum_cross_split_jaccard": maximum,
    }


def _with_receipt(core: dict) -> dict:
    payload = json.dumps(core, sort_keys=True, separators=(",", ":"))
    return {
        **core,
        "receipt_sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }


def verify_format_manifest(data_dir: Path) -> dict:
    """Fail closed unless data bytes carry the mandatory family-holdout receipt."""

    manifest_path = data_dir / "format_manifest.json"
    if not manifest_path.is_file():
        raise ValueError("format manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("format manifest is malformed")
    core = {key: value for key, value in manifest.items() if key != "receipt_sha256"}
    if _with_receipt(core) != manifest:
        raise ValueError("format manifest receipt mismatch")
    policy = manifest.get("split_policy") or {}
    leakage = manifest.get("leakage_receipt") or {}
    leakage_core = {
        key: value for key, value in leakage.items() if key != "receipt_sha256"
    }
    if (
        policy.get("id") != "content_family_holdout"
        or policy.get("version") != 2
        or int(policy.get("minimum_proof_eval_rows", 0)) < 1
        or _with_receipt(leakage_core) != leakage
        or leakage.get("shared_custom_definition_count") != 0
        or leakage.get("near_duplicate_cross_pair_count") != 0
        or float(leakage.get("maximum_cross_split_jaccard", 1.0))
        >= float(leakage.get("near_duplicate_jaccard_threshold", 0.90))
    ):
        raise ValueError("dataset lacks a passing content-family holdout receipt")
    outputs = manifest.get("output_sha256s") or {}
    for name in ("sft_train.jsonl", "sft_eval.jsonl", "holdout_eval.json"):
        path = data_dir / name
        if not path.is_file() or outputs.get(name) != _sha256_path(path):
            raise ValueError(f"formatted dataset bytes changed identity: {name}")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--eval-frac", type=float, default=0.15)
    ap.add_argument("--holdout-eval-min", type=int, default=30,
                    help="hold out whole theorem families until the PROVER eval reaches this many proofs")
    ap.add_argument("--allow-legacy-diagnostic", action="store_true")
    a = ap.parse_args()
    from ztare.leanmill.training_corpus_contract import validate_training_corpus_directory
    validate_training_corpus_directory(
        a.corpus,
        required_files=(
            "prover_corpus.jsonl",
            "autoformalization_corpus.jsonl",
            "faithfulness_discriminator_corpus.jsonl",
        ),
        allow_legacy_diagnostic=a.allow_legacy_diagnostic,
    )
    a.out.mkdir(parents=True, exist_ok=True)
    rows = build(a.corpus)
    if a.holdout_eval_min < 1:
        ap.error("--holdout-eval-min must be positive; the leaking legacy split is disabled")
    tr, ev = split_family_holdout(rows, a.holdout_eval_min)
    # Eval rows carry prompt/probe/gold_proof/target for sample_vllm.py and passk_score.py.
    (a.out / "holdout_eval.json").write_text(json.dumps(ev, ensure_ascii=False), encoding="utf-8")
    (a.out / "sft_train.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in tr), encoding="utf-8")
    (a.out / "sft_eval.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ev), encoding="utf-8")
    from collections import Counter
    leakage = _with_receipt({
        "schema": "leanmill.content_family_holdout_receipt.v1",
        **holdout_leakage_metrics(tr, ev),
        "authority": "deterministic_dataset_splitter",
    })
    manifest = _with_receipt({
        "schema": "leanmill.void_sft_format_manifest.v2",
        "corpus_sha256": _corpus_sha256(a.corpus),
        "split_policy": {
            "id": "content_family_holdout",
            "version": 2,
            "minimum_proof_eval_rows": a.holdout_eval_min,
        },
        "leakage_receipt": leakage,
        "output_sha256s": {
            name: _sha256_path(a.out / name)
            for name in ("sft_train.jsonl", "sft_eval.jsonl", "holdout_eval.json")
        },
        "total": len(rows), "train": len(tr), "eval": len(ev),
        "by_task": dict(Counter(r["task"] for r in rows)),
        "train_by_task": dict(Counter(r["task"] for r in tr)),
        "eval_by_task": dict(Counter(r["task"] for r in ev)),
    })
    (a.out / "format_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
