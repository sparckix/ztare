#!/usr/bin/env python3
"""Typed endpoint-bound context pack — Codex's >10x architecture (2026-05-06).

Supersedes typed_patch_proposer.py (which let the LLM choose any Lean shape
and still hallucinated at the type level). The improvement: constrain the
LLM to ONE OF THREE WELL-DEFINED PATCH CLASSES, with the field-type +
constructors/eliminators + nearest theorems by `uses` count baked into
an endpoint-bound context pack. The LLM becomes a SELECTOR over a typed
search space, not a generator.

# The three patch classes (Codex 2026-05-06)

  TRANSITIVITY_ADAPTER
    Chain N existing inequalities to discharge the field.
    Shape: theorem foo (h1 : a ≤ b) (h2 : b ≤ c) : a ≤ c := le_trans h1 h2

  BRANCH_WISE_FALSIFIER
    Prove the field is FALSE in a specific sub-case.
    Shape: theorem no_X_in_branch_Y (hY : branch_predicate) : ¬ X := ...

  SOURCE_PROVENANCE_BRIDGE
    Relate the field to its parent structure's projection.
    Shape: theorem field_le_struct_proj (s : ParentStruct) :
              s.field ≤ s.bound := s.proj_lemma

# Pipeline

  1. Read workmap target → pick a field
  2. Resolve field type from decl_index (TODO: real Lean elaboration;
     baseline: regex parse of structure body)
  3. Find all constructors/eliminators and result-type producers of that type
     in the spine
  4. Build "uses graph proxy": find theorems whose BODY references the
     field name (sharper than signature-name match)
  5. Choose patch class (CLI arg or auto-pick by class fit)
  6. Build endpoint-bound prompt: only resolved decls; only the chosen
     patch class shape; explicit refusal allowed
  7. Run lake build; on failure record failure_category + retry once
  8. Stage 4: accumulate failure_categories in a JSONL log; future runs
     condition next prompt on prior failures

# Failure categories (extensible)

  missing_constructor      — chose a type without resolved constructors
  dimensional_mismatch     — units don't line up
  endpoint_unbound         — referenced an identifier outside the pack
  patch_class_mismatch     — chose patch class doesn't fit the field
  unverifiable_other       — lake errored for other reason
  trivial_degenerate       — patch compiled but has no theorem (caught by anti-degen)

# Usage

  # auto-pick patch class on a target field:
  python scripts/public/lean/typed_endpoint_pack.py \\
      --target TrackBProfileLipschitzControlObligation \\
      --field profile_obligation \\
      --patch-class transitivity_adapter

  # list available targets:
  python scripts/public/lean/typed_endpoint_pack.py --list-targets
"""
from __future__ import annotations

# GP-241 #62 canonical path bootstrap (#49-class sweep). Imported by
# the kernel FORCING PDE-estimate workbench; its own `from src.ztare.*`
# imports were dead under bare invocation. Make repo-root + src + helper
# dirs importable regardless of cwd/launcher (same pattern as #49).
import sys as _bsys
from pathlib import Path as _BPath
_broot = next((q for q in _BPath(__file__).resolve().parents
               if (q / "src").is_dir() and (q / "scripts").is_dir()),
              _BPath(__file__).resolve().parents[-1])
for _bd in (_broot, _broot / "src",
            _broot / "scripts" / "public" / "lean",
            _broot / "scripts" / "public" / "utilities"):
    _bs = str(_bd)
    if _bs not in _bsys.path:
        _bsys.path.insert(0, _bs)

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from src.ztare.common.llm_runtime import (
    LLMRuntime,
    pick_default_model_id_for_scripts,
    resolve_model_id,
)
from src.ztare.formal.lean_candidate_hygiene import (
    decorative_negation_wrapper,
    duplicate_decl_names,
    extract_lean_block,
    normalize_candidate_source,
    safe_preview,
)
from src.ztare.supervisor.llm_budget_guard import (
    LLMBudgetDenied,
    LLMBudgetSession,
    estimate_llm_call_cost,
    print_budget_report,
    write_pending_operator_gate,
)

REPO = Path(__file__).resolve().parents[3]
LEAN_DIR = REPO / "ztare_proofs" / "ZtareProofs"
WORKMAP_PATH = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "ns_trackb_instantiation_workmap.json"
)
DECL_INDEX_PATH = REPO / "analytics" / "public" / "queries" / "lean" / "lean_decl_index.json"
FAILURE_LOG_PATH = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "typed_endpoint_failure_log.jsonl"
)
_RUNTIME = LLMRuntime()
_BUDGET_SESSION: LLMBudgetSession | None = None
_MODEL_ID: str | None = None
_ALLOW_MODEL_FALLBACK = False


# ---------------------------------------------------------------------------
# Patch class taxonomy
# ---------------------------------------------------------------------------

class PatchClass(str, Enum):
    TRANSITIVITY_ADAPTER = "transitivity_adapter"
    BRANCH_WISE_FALSIFIER = "branch_wise_falsifier"
    SOURCE_PROVENANCE_BRIDGE = "source_provenance_bridge"
    INSTANCE_WITH_EVIDENCE = "instance_with_evidence"


PATCH_CLASS_DESCRIPTION = {
    PatchClass.TRANSITIVITY_ADAPTER: """TRANSITIVITY ADAPTER

You will produce a theorem that chains existing inequalities to discharge
the target field. The shape is:

```lean
theorem <name> (h1 : a ≤ b) (h2 : b ≤ c) ... : a ≤ z := by
  exact le_trans h1 (le_trans h2 ...)
  -- or: exact h1.trans h2 ... (variant)
  -- or: linarith [h1, h2, ...] (when applicable)
```

Constraints:
- Every hypothesis name (h1, h2, ...) MUST appear in the resolved theorem
  set below as the conclusion of an EXISTING theorem you reference by
  decl name.
- The intermediate quantities (a, b, c, ...) MUST appear as resolved
  identifiers in the field-type or its constructors.
- DO NOT introduce new symbols. The theorem is glue between existing
  bounds, not a new mathematical claim.""",

    PatchClass.BRANCH_WISE_FALSIFIER: """BRANCH-WISE FALSIFIER

You will produce a theorem that proves the target field is FALSE in a
specific named sub-case (branch). The shape is:

```lean
theorem no_<field>_in_branch_<branch_name>
    (hY : <branch_predicate>) : ¬ <field_proposition> := by
  intro hcontra
  -- derive contradiction from hY + hcontra using existing lemmas
  exact <existing_falsifier_lemma> hY hcontra
```

Constraints:
- The branch predicate MUST be a constructor / case of a resolved
  inductive type listed below.
- The contradiction derivation MUST use ONLY the existing falsifier
  guards listed in the resolved set.
- This patch type is appropriate when the obligation is suspected of
  being TRUE only in some branches; the falsifier rules out the others
  and narrows the closure to the remaining branch.""",

    PatchClass.INSTANCE_WITH_EVIDENCE: """INSTANCE WITH EVIDENCE

You will produce a `def` (or `noncomputable def`) that constructs an
INSTANCE of the target structure type, supplying explicit evidence for
each field. The shape is:

```lean
noncomputable def <target>_instance_<scenario>
    (<typed_assumptions>) : <TargetStructure> :=
{ field1 := <existing_decl_or_proof_of_field1_type>,
  field2 := <existing_decl_or_proof_of_field2_type>,
  ... }
```

Constraints:
- Every field's value MUST be either an existing declaration in the
  resolved set OR an inline construction using only resolved decls.
- Every typed assumption MUST cite an existing structure or hypothesis
  type from the resolved set.
- This patch type is appropriate when the target obligation is itself a
  structure that needs to be INSTANTIATED, not derived as an inequality.
  Example: `TrackBProfileLipschitzControlObligation` requires building
  the obligation as an instance with field-evidence, not bounding it
  from another quantity.

If the resolved set lacks a field's evidence (e.g. no construction of
`QuarticSurvivalProjectionReceipt` is available), output `# CANNOT PATCH`
and name the missing constructor explicitly.""",

    PatchClass.SOURCE_PROVENANCE_BRIDGE: """SOURCE PROVENANCE BRIDGE

You will produce a theorem that relates the target field to its parent
structure's projection or canonical bound. The shape is:

```lean
theorem <field>_le_<parent>_<bound>
    (s : <ParentStruct>) : s.<field> ≤ s.<bound_field> := by
  exact s.<projection_lemma>
  -- or: simp [<parent>.<unfold>]; exact s.<inner_lemma>
```

Constraints:
- ParentStruct MUST be a resolved structure in the field-type's
  parent chain.
- Both s.<field> and s.<bound_field> MUST be resolved fields of
  ParentStruct.
- The projection_lemma MUST be an existing lemma of ParentStruct (or
  a definitional identity).
- This patch type is appropriate when the field is bounded by an
  existing projection in its parent structure but the bound has
  never been stated as a separate theorem.""",
}


# ---------------------------------------------------------------------------
# Workmap / decl-index loading
# ---------------------------------------------------------------------------

def load_workmap() -> list[dict]:
    if not WORKMAP_PATH.exists():
        print(f"missing {WORKMAP_PATH}")
        return []
    w = json.loads(WORKMAP_PATH.read_text())
    return w if isinstance(w, list) else w.get("structures", [])


def load_workmap_target(target_name: str) -> dict | None:
    for ob in load_workmap():
        if ob.get("name") == target_name or ob.get("structure") == target_name:
            return ob
    return load_decl_index_target(target_name)


def load_decl_index() -> dict:
    if not DECL_INDEX_PATH.exists():
        sys.path.insert(0, str(REPO))
        import lean_decl_index as ldi
        idx = ldi.build_index(ldi.LEAN_DIR)
        DECL_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        DECL_INDEX_PATH.write_text(json.dumps(idx, indent=2))
        return idx
    return json.loads(DECL_INDEX_PATH.read_text())


# ---------------------------------------------------------------------------
# Field type resolution (regex baseline; TODO: real Lean elaboration)
# ---------------------------------------------------------------------------

def resolve_field(target: dict, field_name: str) -> dict | None:
    fields = target.get("fields", [])
    for f in fields:
        name = f.get("name") if isinstance(f, dict) else f
        if name == field_name:
            ftype = f.get("type", "?") if isinstance(f, dict) else "?"
            # Extract the result-type head, not the first binder type.  For
            # fields like `∀ (U : NSEvolution), Quartic...`, the first
            # capitalised token is a binder type and is the wrong endpoint.
            result_surface = ftype
            if "," in result_surface:
                result_surface = result_surface.rsplit(",", 1)[-1]
            if "→" in result_surface:
                result_surface = result_surface.rsplit("→", 1)[-1]
            if "->" in result_surface:
                result_surface = result_surface.rsplit("->", 1)[-1]
            type_head = None
            if not looks_like_bound_type(result_surface):
                for m in re.finditer(r"\b([A-Z][A-Za-z0-9_]*)\b", result_surface):
                    candidate = m.group(1)
                    next_char = result_surface[m.end():m.end() + 1]
                    if candidate == "Prop":
                        continue
                    # Skip namespace/local-object heads such as `P.foo` or
                    # `R.field`; they are not endpoint type constructors.
                    if next_char == ".":
                        continue
                    type_head = candidate
                    break
            return {
                "field_name": field_name,
                "field_type": ftype,
                "result_surface": result_surface.strip(),
                "type_head": type_head,
            }
    return None


def extract_structure_fields(decl_body: str) -> list[dict]:
    """Best-effort Lean structure-field extraction with multiline support."""
    field_start_re = re.compile(
        r"^\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\))*\s*:\s*(.*)$"
    )
    fields: list[dict] = []
    current: dict | None = None
    for line in decl_body.splitlines():
        match = field_start_re.match(line)
        if match:
            if current is not None:
                current["type"] = " ".join(current["_type_lines"]).strip()
                current.pop("_type_lines", None)
                fields.append(current)
            current = {"name": match.group(1), "_type_lines": []}
            rest = match.group(2).strip()
            if rest:
                current["_type_lines"].append(rest)
            continue
        if current is not None:
            if line and not line.startswith((" ", "\t")):
                current["type"] = " ".join(current["_type_lines"]).strip()
                current.pop("_type_lines", None)
                fields.append(current)
                current = None
                continue
            stripped = line.strip()
            if not stripped or stripped.startswith(("/--", "--", "-/")):
                continue
            current["_type_lines"].append(stripped)
    if current is not None:
        current["type"] = " ".join(current["_type_lines"]).strip()
        current.pop("_type_lines", None)
        fields.append(current)
    return fields


def find_type_constructors(type_head: str, decl_index: dict) -> list[dict]:
    """Find structure/inductive declarations matching type_head + their fields."""
    if not type_head:
        return []
    decls = decl_index.get("decls", {})
    matches = decls.get(type_head, [])
    out = []
    for entry in matches:
        kind = entry.get("kind", "")
        if kind not in ("structure", "class", "inductive"):
            continue
        file_stem = entry["file"]
        path = LEAN_DIR / f"{file_stem}.lean"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Find the declaration body
        decl_re = re.compile(
            rf"^{kind}\s+{re.escape(type_head)}(?![A-Za-z0-9_'.])(.*?)(?=^(?:theorem|lemma|def|"
            rf"structure|class|instance|inductive|abbrev)\s+|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        for m in decl_re.finditer(text):
            full_body = m.group(0)
            body = safe_preview(full_body, 2000)
            fields = extract_structure_fields(full_body)
            out.append({
                "type_head": type_head,
                "kind": kind,
                "file": file_stem,
                "body_preview": body,
                "fields": fields[:15],
            })
    return out


def load_decl_index_target(target_name: str) -> dict | None:
    """Fallback target loader for receipt interfaces outside the workmap.

    The workmap deliberately ranks top-level open structures. Some proof work
    targets a narrower receipt/interface introduced to reduce an obligation.
    Those should still be usable by endpoint tooling when their Lean structure
    body is present in the declaration index.
    """
    decl_index = load_decl_index()
    constructors = find_type_constructors(target_name, decl_index)
    if not constructors:
        return None
    target = constructors[0]
    fields = target.get("fields", [])
    return {
        "name": target_name,
        "structure": target_name,
        "file": target.get("file"),
        "fields": fields,
        "n_fields": len(fields),
        "leverage_score": None,
        "target_source": "decl_index_fallback",
    }


# ---------------------------------------------------------------------------
# Uses-graph proxy: find theorems whose BODY references the field
# ---------------------------------------------------------------------------

def lean_signature_prefix(decl_body: str) -> str:
    """Return the source prefix before a Lean declaration body starts.

    Lean declarations often put the result type immediately before either
    `:=` or a structure-constructor `where`.  A line-start split misses common
    constructors of the form `Target args where`, then accidentally includes
    field assignments and trailing doc comments in the "signature".  This
    helper intentionally stays syntax-light, but stops at the first body
    opener before any proof/constructor body can pollute return-type parsing.
    """
    opener = re.search(r"(?:\s:=|\swhere\b)", decl_body)
    if opener:
        return decl_body[:opener.start()]
    return decl_body


def lean_result_surface(signature: str) -> str:
    """Best-effort final return surface from a Lean declaration signature."""
    return signature.rsplit(":", 1)[-1] if ":" in signature else signature


def find_type_producers(type_head: str | None, top_n: int = 15) -> list[dict]:
    """Find defs/theorems/lemmas whose declared signature returns type_head.

    This catches adapter constructors such as `foo_of_bar : TargetType ...`
    whose declaration name is not the target type itself. It is intentionally
    syntax-level, but the signal is strong enough for endpoint context packs:
    if the target type appears in the declaration signature before the proof
    body, the declaration is a candidate producer.
    """
    if not type_head:
        return []
    out = []
    decl_re = re.compile(
        r"^(?:(noncomputable)\s+)?(theorem|lemma|def|abbrev)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)",
        re.MULTILINE,
    )
    for path in LEAN_DIR.glob("ns_*.lean"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        positions = [(m.start(), m.group(2), m.group(3))
                     for m in decl_re.finditer(text)]
        positions.append((len(text), "", ""))
        for i in range(len(positions) - 1):
            start, kind, name = positions[i]
            end = positions[i + 1][0]
            body = text[start:end]
            signature = lean_signature_prefix(body)
            result_surface = lean_result_surface(signature)
            type_uses = len(re.findall(rf"\b{re.escape(type_head)}\b",
                                       result_surface))
            if type_uses <= 0:
                continue
            # Prefer definitions over theorem wrappers. A declaration counts
            # as a producer only when the type appears in the return surface;
            # binder-only mentions are consumers and are filtered above.
            kind_bonus = 3 if kind in ("def", "abbrev") else 1
            result_bonus = 2
            out.append({
                "name": name,
                "kind": kind,
                "file": path.stem,
                "signature_preview": safe_preview(signature, 900),
                "type_uses": type_uses,
                "score": type_uses + kind_bonus + result_bonus,
            })
    out.sort(key=lambda r: (-r["score"], r["file"], r["name"]))
    return out[:top_n]


def find_theorems_using_field(field_name: str, type_head: str | None,
                                top_n: int = 10) -> list[dict]:
    """Find theorems whose body invokes the field name + type head as terms."""
    out = []
    decl_re = re.compile(
        r"^(theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)",
        re.MULTILINE,
    )
    for path in LEAN_DIR.glob("ns_*.lean"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        positions = [(m.start(), m.group(2)) for m in decl_re.finditer(text)]
        positions.append((len(text), ""))
        for i in range(len(positions) - 1):
            start, tname = positions[i]
            end = positions[i + 1][0]
            body = text[start:end]
            # Score by uses
            field_uses = len(re.findall(rf"\b{re.escape(field_name)}\b", body))
            type_uses = (len(re.findall(rf"\b{re.escape(type_head)}\b", body))
                         if type_head else 0)
            score = field_uses + (type_uses * 2)  # type-head uses weighted higher
            if score > 0:
                out.append({
                    "name": tname, "file": path.stem,
                    "body_preview": safe_preview(body, 500),
                    "field_uses": field_uses,
                    "type_uses": type_uses,
                    "score": score,
                })
    out.sort(key=lambda r: -r["score"])
    return out[:top_n]


# ---------------------------------------------------------------------------
# Failure category accumulator (Stage 4 wiring)
# ---------------------------------------------------------------------------

FAILURE_CATEGORIES = [
    "missing_constructor",      # type without resolved constructors in pack
    "dimensional_mismatch",     # units/types don't line up
    "endpoint_unbound",         # referenced ID outside the pack
    "patch_class_mismatch",     # chosen class doesn't fit the field
    "unverifiable_other",       # lake errored for other reason
    "trivial_degenerate",       # compiled but no theorem (anti-degen catch)
    "llm_refused",              # LLM said it cannot patch with given pack
]


def return_type_segment(field_type: str) -> str:
    """Best-effort endpoint extraction for Lean dependent function fields."""
    surface = field_type.strip()
    if "," in surface:
        surface = surface.rsplit(",", 1)[-1].strip()
    if "→" in surface:
        surface = surface.rsplit("→", 1)[-1].strip()
    if "->" in surface:
        surface = surface.rsplit("->", 1)[-1].strip()
    return surface


def looks_like_bound_type(type_text: str) -> bool:
    """Return true when the produced endpoint is a scalar relation."""
    stripped = type_text.strip()
    if stripped.startswith(("≤", "<", "≥", ">", "=")):
        return True
    relation_re = r"(^|[)\]\w.])\s*(≤|<|≥|>|=)\s*([^=]|$)"
    return bool(re.search(relation_re, stripped))


def patch_class_fit_guard(
    field_info: dict,
    patch_class: PatchClass,
    constructors: list[dict],
) -> tuple[bool, str]:
    """Reject mechanically wrong class/endpoint pairings before LLM spend.

    This guard is intentionally narrow. It catches the expensive failure class
    where a receipt/structure-valued field is routed to scalar inequality
    patches. It does not try to prove that an allowed class will work.
    """
    endpoint = return_type_segment(field_info.get("field_type", ""))
    type_head = field_info.get("type_head")
    if constructors and type_head and type_head != "Prop":
        if patch_class != PatchClass.INSTANCE_WITH_EVIDENCE:
            return (
                False,
                (
                    f"field returns resolved structure/receipt {type_head}; "
                    f"{patch_class.value} would treat a constructed object as "
                    "a scalar/provenance theorem. Use instance_with_evidence."
                ),
            )
    if patch_class == PatchClass.TRANSITIVITY_ADAPTER and not looks_like_bound_type(endpoint):
        return (
            False,
            (
                "transitivity_adapter requires an inequality/equality endpoint; "
                f"returned endpoint is {endpoint!r}"
            ),
        )
    return True, "patch class is syntactically compatible with endpoint shape"


def categorize_failure(stderr: str, llm_response: str, current_src: str) -> str:
    if not current_src.strip() or not re.search(
            r"\b(theorem|lemma|def|structure|instance)\s+\w", current_src):
        return "trivial_degenerate"
    if "CANNOT PATCH" in llm_response.upper():
        return "llm_refused"
    if "unknown identifier" in stderr or "unknown constant" in stderr:
        return "endpoint_unbound"
    if "type mismatch" in stderr or "expected type" in stderr:
        return "dimensional_mismatch"
    if "unknown free variable" in stderr or "unknown structure field" in stderr:
        return "missing_constructor"
    return "unverifiable_other"


def load_prior_failures(target: str, field: str, patch_class: str) -> list[dict]:
    """Pull prior failure entries for the same (target, field, class) triple."""
    if not FAILURE_LOG_PATH.exists():
        return []
    out = []
    for line in FAILURE_LOG_PATH.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (row.get("target") == target and row.get("field") == field
                and row.get("patch_class") == patch_class):
            out.append(row)
    return out[-5:]  # last 5


def append_failure(target: str, field: str, patch_class: str, category: str,
                   stderr_tail: str, llm_response_tail: str) -> None:
    FAILURE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FAILURE_LOG_PATH.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.now(UTC).isoformat(),
            "target": target, "field": field, "patch_class": patch_class,
            "category": category,
            "stderr_tail": stderr_tail[-500:],
            "llm_response_tail": llm_response_tail[-500:],
        }) + "\n")


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_prompt(target: dict, field_info: dict, patch_class: PatchClass,
                  target_constructors: list[dict],
                  target_producers: list[dict],
                  constructors: list[dict], type_producers: list[dict],
                  using_theorems: list[dict],
                  prior_failures: list[dict]) -> str:
    target_constructor_block = ("\n\n".join(
        f"### {c['kind']} {c['type_head']} (from {c['file']}.lean)\n"
        f"```lean\n{c.get('body_preview', '')}\n```\n"
        f"Fields:\n" + "\n".join(f"  - {f['name']} : {f['type']}" for f in c['fields'])
        for c in target_constructors) or "(NO RESOLVED TARGET STRUCTURE BODY)")
    target_producer_block = ("\n\n".join(
        f"### {p['kind']} {p['name']} (in {p['file']}.lean, score={p['score']} type_uses={p['type_uses']})\n"
        f"```lean\n{p['signature_preview']}\n```"
        for p in target_producers) or "(NO TARGET-TYPE PRODUCERS FOUND)")
    constructor_block = ("\n\n".join(
        f"### {c['kind']} {c['type_head']} (from {c['file']}.lean)\n"
        f"```lean\n{c.get('body_preview', '')}\n```\n"
        f"Fields:\n" + "\n".join(f"  - {f['name']} : {f['type']}" for f in c['fields'])
        for c in constructors) or "(NO RESOLVED CONSTRUCTORS — refuse via CANNOT PATCH if patch class needs one)")
    using_block = ("\n\n".join(
        f"### {t['name']} (in {t['file']}.lean, score={t['score']} field_uses={t['field_uses']} type_uses={t['type_uses']})\n"
        f"```lean\n{t['body_preview']}\n```"
        for t in using_theorems) or "(NO THEOREMS USE THIS FIELD — patch will be hard; consider CANNOT PATCH)")
    producer_block = ("\n\n".join(
        f"### {p['kind']} {p['name']} (in {p['file']}.lean, score={p['score']} type_uses={p['type_uses']})\n"
        f"```lean\n{p['signature_preview']}\n```"
        for p in type_producers) or "(NO RESULT-TYPE PRODUCERS FOUND — patch may need a new analytic constructor)")
    failure_block = ""
    if prior_failures:
        failure_block = "\n\n## Prior failures on this same (target, field, class) triple\n\n"
        for f in prior_failures:
            failure_block += f"- {f['category']}: {f['stderr_tail'][:120]}\n"
        failure_block += ("\nDo NOT repeat these failure modes. If you cannot avoid "
                           "them, output `# CANNOT PATCH` with a one-paragraph diagnosis.\n")
    target_field_name = field_info.get("field_name") or field_info.get("name") or "<target_field>"

    return f"""You are working on closing the NS Track B Clay obligation `{target.get('name')}`. You will produce ONE LAKE-CHECKABLE Lean patch in the chosen patch class. Refuse with `# CANNOT PATCH` if you cannot do so within the constraints.

# Target obligation

  {target.get('name')}
  leverage_score: {target.get('leverage_score')}
  n_fields: {target.get('n_fields')}
  source file: ztare_proofs/ZtareProofs/{target.get('file')}.lean

# Target field

  Field name: {field_info['field_name']}
  Field type: {field_info['field_type']}
  Type head: {field_info['type_head']}

# Resolved target structure body

{target_constructor_block}

# Existing declarations that PRODUCE the target structure

{target_producer_block}

# Resolved type constructors (full type body for type_head)

{constructor_block}

# Existing declarations that PRODUCE the target type

{producer_block}

# Theorems that USE this field as a term (top-{len(using_theorems)} by uses count)

{using_block}

# Patch class you MUST use

{PATCH_CLASS_DESCRIPTION[patch_class]}

# Strict constraints

- Only reference identifiers in the resolved target-structure,
  constructor, type-producer, and using-theorem set above.
- Do NOT invent names. Do NOT use sorry/admit/axiom/native_decide.
- Do NOT repeat an existing top-level declaration name.
- Do NOT prove this endpoint by reading the target field itself from the
  target record. If the field is `{target_field_name}`, then `R.{target_field_name}`,
  `rw [R.{target_field_name}]`, or `simpa using R.{target_field_name}` is
  self-reference, not progress.
- Do NOT return a decorative negation wrapper of the form
  `theorem no_X (...)(h : ¬ existing_positive_endpoint) : False := h (...)`;
  it is compiler-green but not endpoint progress.
- Prefer falsifier-first patches: if a positive bridge is not available,
  return `# CANNOT PATCH` with the exact missing source constructor or
  analytic primitive instead of compiling a tautology.
- Return a COMPLETE Lean file. Include the needed `import ZtareProofs.<module>`
  lines and wrap declarations in `namespace ZtareProofs.NS ... end ZtareProofs.NS`
  whenever using NS spine declarations.
- Output ONE Lean file in a single ```lean fenced block.
- If the constraints make the patch impossible (e.g. no usable existing
  bound for the transitivity adapter), output `# CANNOT PATCH` followed
  by a one-paragraph specification of the missing analytic inequality
  or constructor that would be needed.
{failure_block}
Return your patch in a single ```lean fenced block, OR output `# CANNOT PATCH` with the diagnosis."""


# ---------------------------------------------------------------------------
# LLM call + lake build (reuses prior infra)
# ---------------------------------------------------------------------------

def call_gemini(
    prompt: str,
    max_tokens: int = 8000,
    *,
    request_label: str = "typed_endpoint_pack",
) -> str:
    """Provider-agnostic paid LLM call with optional budget enforcement.

    The legacy function name is preserved for callers, but dispatch now goes
    through `LLMRuntime` so pricing/telemetry and provider fallback are shared
    with other out-of-loop scripts.
    """
    model_id = _MODEL_ID or pick_default_model_id_for_scripts(
        preference_order=("google", "openai", "anthropic")
    )
    if model_id is None:
        return (
            "ERROR: no LLM provider available — set ANTHROPIC_API_KEY, "
            "OPENAI_API_KEY, or GEMINI_API_KEY"
        )
    try:
        estimate = None
        if _BUDGET_SESSION is not None:
            estimate = _BUDGET_SESSION.preflight(
                prompt=prompt,
                model_name=model_id,
                max_output_tokens=max_tokens,
                label=request_label,
            )
        response = _RUNTIME.call_text(
            prompt,
            model_id=model_id,
            fallback_model_ids=None if _ALLOW_MODEL_FALLBACK else (),
            max_tokens=max_tokens,
            request_label=request_label,
        )
        if _BUDGET_SESSION is not None and estimate is not None:
            _BUDGET_SESSION.record_response(
                usage=response.usage,
                fallback_estimate=estimate,
                label=request_label,
            )
        return response.text or "(empty)"
    except LLMBudgetDenied as exc:
        return f"ERROR: budget denied: {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {type(exc).__name__}: {exc}"


def resolve_script_model(model: str | None) -> str | None:
    """Resolve a CLI model alias/id or pick the Google-first script default."""
    if model:
        try:
            return resolve_model_id(model)
        except ValueError:
            return model
    return pick_default_model_id_for_scripts(
        preference_order=("google", "openai", "anthropic")
    )


def lake_build_check(lean_src: str, slug: str) -> dict:
    sys.path.insert(0, str(REPO / "src"))
    from src.ztare.gates.lean_proof_gate import write_lean_target
    from lean_fast_compile import compile_lean_fast_combined_output
    proofs_root = REPO / "ztare_proofs"
    lean_src = normalize_candidate_source(lean_src)
    target = write_lean_target(lean_src, slug, proofs_root)
    result = compile_lean_fast_combined_output(
        target, proofs_root, timeout_seconds=120)
    result["lean_path"] = str(target)
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    global _BUDGET_SESSION, _MODEL_ID, _ALLOW_MODEL_FALLBACK
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-targets", action="store_true")
    ap.add_argument("--list-fields", help="list fields of a workmap target")
    ap.add_argument("--target", help="workmap target name")
    ap.add_argument("--field", help="field of the target to discharge")
    ap.add_argument("--patch-class", choices=[c.value for c in PatchClass],
                    default=PatchClass.TRANSITIVITY_ADAPTER)
    ap.add_argument("--max-revisions", type=int, default=2)
    ap.add_argument("--model",
                    help="model alias/id for paid generation; e.g. gemini-pro")
    ap.add_argument("--allow-model-fallback", action="store_true",
                    help="allow provider fallback if the requested/default model fails")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget-estimate-only", action="store_true",
                    help="print/write the paid-call estimate, then exit before LLM dispatch")
    ap.add_argument("--allow-paid", action="store_true",
                    help="authorize paid LLM dispatch after reviewing the estimate")
    ap.add_argument("--max-total-cost-usd", type=float,
                    help="hard per-run spend cap for LLM calls")
    ap.add_argument("--role-id", default="research_director",
                    help="role budget to enforce via spend_tracker")
    ap.add_argument("--session-id",
                    default=f"typed-endpoint-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
                    help="spend-tracker session id")
    ap.add_argument("--write-approval-gate", action="store_true",
                    help="write an org/gates/pending budget approval JSON and exit")
    ap.add_argument("--out-dir", type=Path,
                    default=REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries" / "typed_endpoint_runs")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.list_targets:
        for ob in load_workmap()[:30]:
            print(f"  {ob.get('name')} (n_fields={ob.get('n_fields')}, "
                  f"leverage={ob.get('leverage_score')})")
        return 0

    if args.list_fields:
        ob = load_workmap_target(args.list_fields)
        if not ob:
            print(f"unknown target: {args.list_fields}")
            return 1
        for fld in ob.get("fields", []):
            name = fld.get("name") if isinstance(fld, dict) else fld
            ftype = fld.get("type", "?") if isinstance(fld, dict) else "?"
            print(f"  {name} : {ftype}")
        return 0

    if not (args.target and args.field):
        ap.print_help()
        return 1

    print(f"=== typed endpoint pack ===")
    print(f"  target: {args.target}")
    print(f"  field:  {args.field}")
    args.patch_class = PatchClass(args.patch_class)
    print(f"  class:  {args.patch_class.value}")
    _MODEL_ID = resolve_script_model(args.model)
    _ALLOW_MODEL_FALLBACK = args.allow_model_fallback
    if _MODEL_ID is None:
        print("  no configured LLM provider found")
        return 2
    print(f"  model:  {_MODEL_ID}")

    target = load_workmap_target(args.target)
    if not target:
        print(f"  target not in workmap")
        return 1

    field_info = resolve_field(target, args.field)
    if not field_info:
        print(f"  field not in target")
        return 1
    print(f"  field type head: {field_info['type_head']}")

    decl_index = load_decl_index()
    target_name = target.get("name") or target.get("structure") or args.target
    target_constructors = find_type_constructors(target_name, decl_index)
    print(f"  resolved {len(target_constructors)} target body record(s) for {target_name}")
    target_producers = find_type_producers(target_name, top_n=10)
    print(f"  found {len(target_producers)} producers of target {target_name}")

    constructors = find_type_constructors(field_info["type_head"], decl_index)
    print(f"  resolved {len(constructors)} constructor(s) of {field_info['type_head']}")

    fit_ok, fit_reason = patch_class_fit_guard(
        field_info, args.patch_class, constructors)
    print(f"  patch-class fit: {fit_reason}")
    if not fit_ok:
        append_failure(
            args.target,
            args.field,
            args.patch_class.value,
            "patch_class_mismatch",
            fit_reason,
            "",
        )
        print("  stopping before prompt/model call")
        return 2

    type_producers = find_type_producers(field_info["type_head"], top_n=15)
    print(f"  found {len(type_producers)} producers of {field_info['type_head']}")

    using_theorems = find_theorems_using_field(args.field, field_info["type_head"], top_n=10)
    print(f"  found {len(using_theorems)} theorems referencing field/type")

    prior_failures = load_prior_failures(args.target, args.field, args.patch_class.value)
    print(f"  prior failures on this triple: {len(prior_failures)}")

    prompt = build_prompt(target, field_info, args.patch_class,
                           target_constructors, target_producers,
                           constructors, type_producers, using_theorems,
                           prior_failures)
    prompt_path = args.out_dir / f"{args.target}_{args.field}_{args.patch_class.value}_prompt.txt"
    prompt_path.write_text(prompt)
    print(f"  prompt: {len(prompt)} chars → {prompt_path}")

    estimate = estimate_llm_call_cost(
        prompt=prompt,
        model_name=_MODEL_ID,
        max_output_tokens=8000,
        label="typed_endpoint_initial",
    )
    print_budget_report(estimate, max_total_cost_usd=args.max_total_cost_usd)
    budget_path = args.out_dir / f"{args.target}_{args.field}_{args.patch_class.value}_budget.json"
    budget_path.write_text(json.dumps({
        "target": args.target,
        "field": args.field,
        "patch_class": args.patch_class.value,
        "estimate": {
            "model_name": estimate.model_name,
            "input_tokens_est": estimate.input_tokens,
            "max_output_tokens": estimate.output_tokens,
            "estimated_cost_usd": estimate.estimated_cost_usd,
        },
        "max_total_cost_usd": args.max_total_cost_usd,
        "allow_paid": args.allow_paid,
        "session_id": args.session_id,
        "requested_model": args.model,
        "effective_model_for_estimate": _MODEL_ID,
        "allow_model_fallback": args.allow_model_fallback,
        "note": (
            "Initial-call estimate only. Revisions are checked by the same "
            "run cap before dispatch."
        ),
    }, indent=2), encoding="utf-8")
    print(f"  budget: {budget_path}")
    if args.write_approval_gate:
        gate = write_pending_operator_gate(
            estimate=estimate,
            action="typed_endpoint_pack",
            reason=f"{args.target}::{args.field} ({args.patch_class.value})",
            max_total_cost_usd=args.max_total_cost_usd,
        )
        print(f"  wrote approval gate: {gate.relative_to(REPO)}")
        return 0

    if args.dry_run:
        print(f"\n[dry-run] skipping LLM call + lake build")
        return 0
    if args.budget_estimate_only:
        print(f"\n[budget-estimate-only] skipping LLM call + lake build")
        return 0
    if not args.allow_paid:
        print("\npaid LLM dispatch blocked; rerun with --allow-paid after reviewing budget")
        return 2
    _BUDGET_SESSION = LLMBudgetSession(
        allow_paid=args.allow_paid,
        max_total_cost_usd=args.max_total_cost_usd,
        role_id=args.role_id,
        session_id=args.session_id,
        action="typed_endpoint_pack",
    )

    print(f"\n[calling Gemini]")
    response = call_gemini(prompt, request_label="typed_endpoint_initial")
    response_path = args.out_dir / f"{args.target}_{args.field}_{args.patch_class.value}_response.md"
    response_path.write_text(response)
    print(f"  response: {len(response)} chars")

    if "# CANNOT PATCH" in response.upper():
        print(f"\n  Gemini refused: CANNOT PATCH")
        diag = response.upper().split("# CANNOT PATCH", 1)[1][:400]
        print(f"  diagnosis: {diag}")
        append_failure(args.target, args.field, args.patch_class.value,
                        "llm_refused", "", response[:500])
        # Auto-trigger: retry once with context-deidentified prompt (PDF §2.7)
        # Conservatism-trip detection: refusal mentions paper / open / conjecture
        diag_lower = diag.lower()
        if any(t in diag_lower for t in
                ("open problem", "conjecture", "open question", "millennium",
                 "long-standing", "unsolved", "famous")):
            print(f"\n  refusal mentions open-problem framing — "
                  f"auto-retrying with context de-identification")
            try:
                from context_deidentifier import deidentify_text
                deid_prompt, changes = deidentify_text(prompt)
                print(f"  applied {len(changes)} de-identifications")
                response2 = call_gemini(
                    deid_prompt,
                    request_label="typed_endpoint_deidentified_retry",
                )
                response_path2 = (args.out_dir
                    / f"{args.target}_{args.field}_{args.patch_class.value}_deidentified_response.md")
                response_path2.write_text(response2)
                print(f"  retry response: {len(response2)} chars → {response_path2}")
                if "# CANNOT PATCH" not in response2.upper():
                    response = response2  # use the de-identified response
                    print(f"  ✓ de-identified retry succeeded; proceeding with that response")
                else:
                    print(f"  de-identified retry also refused; consider "
                          f"`scripts/public/utilities/negative_prompting_wrapper.py --problem '...'` "
                          f"to enumerate methodological alternatives before giving up")
                    return 0
            except Exception as e:
                print(f"  de-identification retry failed: {type(e).__name__}: {e}")
                print(f"  manual fallback: run "
                      f"`scripts/public/utilities/negative_prompting_wrapper.py --problem '...'`")
                return 0
        else:
            print(f"  refusal does not match open-problem-conservatism pattern; "
                  f"skipping deidentified retry. Consider `scripts/public/utilities/negative_prompting_wrapper.py` "
                  f"to enumerate methodological alternatives.")
            return 0

    lean_src = extract_lean_block(response)
    if not lean_src:
        print(f"  no Lean block in response")
        append_failure(args.target, args.field, args.patch_class.value,
                        "unverifiable_other", "no Lean block", response[:500])
        return 1
    duplicates = duplicate_decl_names(lean_src, decl_index)
    if duplicates:
        print("  duplicate top-level declaration(s) in response; "
              "treating as UNVERIFIABLE before lake build")
        print(f"  duplicates: {duplicates}")
        append_failure(args.target, args.field, args.patch_class.value,
                        "trivial_degenerate",
                        f"duplicate declarations: {duplicates}",
                        response[:500])
        return 1

    print(f"\n[lake build verification]")
    slug = f"endpoint_{args.target.lower()[:25]}_{args.field.lower()[:20]}_{args.patch_class.value[:10]}"
    current_src = lean_src
    last_response = response
    for attempt in range(args.max_revisions + 1):
        try:
            result = lake_build_check(current_src, slug)
        except Exception as e:
            print(f"  attempt {attempt}: lake raised {type(e).__name__}: {e}")
            append_failure(args.target, args.field, args.patch_class.value,
                            "unverifiable_other", str(e)[:500], last_response[:500])
            break
        compiled = result.get("compiled", False)
        # Anti-degeneracy
        has_real = bool(re.search(
            r"\b(theorem|lemma|def|structure|instance)\s+\w", current_src))
        if compiled and not has_real:
            compiled = False
            print(f"  attempt {attempt}: compiled but degenerate (no theorem)")
            append_failure(args.target, args.field, args.patch_class.value,
                            "trivial_degenerate", "no theorem in compiled file",
                            current_src[:500])
        if compiled and decorative_negation_wrapper(current_src):
            compiled = False
            print(f"  attempt {attempt}: compiled but decorative negation wrapper")
            append_failure(args.target, args.field, args.patch_class.value,
                            "trivial_degenerate",
                            "decorative negation wrapper", current_src[:500])
        if compiled:
            print(f"\n  *** ATTEMPT {attempt} VERIFIED — endpoint patch lake-builds ***")
            print(f"     class: {args.patch_class.value}")
            print(f"     file:  ztare_proofs/ZtareProofs/{slug}_iter.lean")
            return 0
        else:
            stderr = result.get("stderr", "")
            category = categorize_failure(stderr, last_response, current_src)
            print(f"  attempt {attempt}: failed (exit={result.get('exit_code')}) "
                  f"category={category}")
            append_failure(args.target, args.field, args.patch_class.value,
                            category, stderr, last_response[:500])
            if attempt >= args.max_revisions:
                break
            # Build revision prompt with original context preserved
            revision_prompt = (f"ORIGINAL TASK:\n\n{prompt[:5000]}\n\n"
                               f"Your prior patch:\n```lean\n{current_src[:2500]}\n```\n\n"
                               f"Failed lake build with category `{category}`:\n"
                               f"```\n{stderr[:1500]}\n```\n\n"
                               f"Revise. Same constraints; do NOT introduce names not in the resolved set; "
                               f"MUST contain at least one theorem/lemma. Or output `# CANNOT PATCH`.")
            revised = call_gemini(
                revision_prompt,
                request_label=f"typed_endpoint_revision_{attempt + 1}",
            )
            last_response = revised
            new_src = extract_lean_block(revised)
            if not new_src:
                print(f"  revision had no Lean block")
                append_failure(args.target, args.field, args.patch_class.value,
                                "unverifiable_other", "revision had no Lean block",
                                revised[:500])
                break
            duplicates = duplicate_decl_names(new_src, decl_index)
            if duplicates:
                print("  revision repeated existing top-level declaration(s); "
                      "aborting before lake build")
                append_failure(args.target, args.field, args.patch_class.value,
                                "trivial_degenerate",
                                f"duplicate declarations: {duplicates}",
                                revised[:500])
                break
            current_src = new_src

    print(f"\n=== UNVERIFIABLE after {args.max_revisions + 1} attempts ===")
    print(f"  failure log: {FAILURE_LOG_PATH}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
