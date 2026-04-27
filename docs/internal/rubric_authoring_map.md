# Rubric Authoring Map

**Purpose:** a mandatory pre-flight map for anyone (human or agent) authoring a new rubric JSON or a new project substrate. If you skip this, the pre-run gates reject at launch and the iteration budget is wasted.

**When to use:** before writing ANY `rubrics/*.json` or creating any new `projects/<slug>/` directory.

**Canonical generator:** `make generate-gp PROJECT=<slug> BRIEF="<one paragraph>"`. This is the correct default. Only hand-author when you are deliberately overriding a generator default; in that case consult §5 below.

---

## 1. Canonical authoring path (Type B qualitative thesis)

```
make generate-gp \
    PROJECT=my_project \
    BRIEF="one paragraph thesis question" \
    [JUDGE_MODEL=gpt4.1]
```

Produces:
- `projects/<slug>/project_charter.md` — template shape
- `projects/<slug>/thesis.md` — stub (mutator fills in iter 1)
- `projects/<slug>/evidence.txt` — empty; operator fills in
- `projects/<slug>/raw/source_type_map.json` — empty map
- `rubrics/<slug>.json` — LLM-drafted adversarial rubric with correct gate opt-outs

Use the generator even if you plan to rewrite the charter / evidence / rubric afterward. The generator pre-fills three non-obvious gate opt-outs (`farther_tail_region: null`, `disable_evidence_fit_gate: true`, `disable_uniqueness_gap_gate: true`) plus `fit_score_mode: "none"` and correct reasons. Missing any of those causes hard fails that look like scoring failures.

## 2. Required files in every project_dir

Each project directory MUST contain at minimum:
- `project_charter.md`
- `evidence.txt`
- `thesis.md` (may be empty-stub if mutator writes iter 1; MUST exist)
- `raw/` directory (may be empty; MUST exist)

Missing `thesis.md` or `raw/` → autoresearch_loop.py may or may not tolerate it depending on mode. Don't find out the hard way. Create both.

## 3. Rubric pre-launch checklist (GP-133 R4 compliance)

Read `docs/concepts/rubric_specification.md` BEFORE authoring a rubric. The short version of the gates the rubric-loader enforces fail-closed:

**§16 rubric_mode discipline (fail-closed):**
- `rubric_mode: "newton"` → MUST include a dimension whose name contains "Generative Yield" (case-insensitive) with `weight >= 15`. Fail → refuses to launch.
- `rubric_mode: "kepler"` → passes gate unconditionally. Default.

**§17 py_exec grammar gates (fail-closed):**
- `fit_expression_grammar: "py_exec"` → requires `py_exec_authorized_by: <seam-id>` + `expression_byte_budget: <int>`. Missing either → refuses to launch.

**§§18-20 Newton-mode dimension discipline:**
- Generative Yield dimension description must be specific to the substrate class (not a generic template).
- If the substrate is algorithmic (not scalar-function), ALSO include a "Mechanism Algorithmic Concreteness" dimension (weight ≥ 10).
- Charter must have a "Secondary observable" field mandatory for Newton-mode.

**Other structural requirements:**
- `dimensions` list weight sum = exactly 100.
- `persona` string present and non-empty.
- `criteria` dict mirrors the dimensions by short key.
- `falsification_mode` set to a known value (`numerical_proof`, `bounded_discriminator`, etc.).
- If `falsification_mode: "bounded_discriminator"` → globally the modules `state_incompatibility / entropy_stripping / dimensional_shift / interface_discipline` must be wired (they are; this is already live).
- `disable_evidence_fit_gate: true` + `_reason` for qualitative substrates.
- `disable_uniqueness_gap_gate: true` + `_reason` for qualitative substrates.
- `farther_tail_region: null` + `_disable_reason` for qualitative substrates.

## 4. Pre-flight validation (run BEFORE launching)

```bash
python3 -c "
import json
r = json.load(open('rubrics/<slug>.json'))
assert sum(d['weight'] for d in r['dimensions']) == 100, 'weight sum != 100'
if r.get('rubric_mode') == 'newton':
    gy = [d for d in r['dimensions'] if 'generative yield' in d['name'].lower()]
    assert gy and gy[0]['weight'] >= 15, 'newton mode requires Generative Yield >=15'
assert r.get('persona'), 'persona missing'
assert r.get('dimensions'), 'dimensions missing'
print('rubric pre-flight OK')
"
```

Run this. If it fails, fix the rubric before invoking `make loop`.

## 5. Overriding generator defaults (only if needed)

If you must hand-edit the generator-produced rubric:
- NEVER remove a `disable_*_gate` key without adding a `_reason` field.
- NEVER change `rubric_mode` from kepler → newton without also adding the Generative Yield dimension in the same edit. Promotion to newton requires principal signoff per rubric_specification.md §16.
- Weight rebalancing: maintain sum = 100. Use `python3 -c "import json; r=json.load(open('...')); print(sum(d['weight'] for d in r['dimensions']))"` to verify.

## 6. Common mistakes this map exists to prevent

Each item below is a real mistake made by agents (or by me) in 2026-04:
- Hand-authored rubric with `rubric_mode: "newton"` but no Generative Yield dimension → GP-133 R4 gate rejects at launch. **Fix:** run the §4 validation or use `make generate-gp`.
- Hand-created project dir missing `thesis.md` or `raw/` → silently may or may not crash depending on iteration path. **Fix:** match gp140_ztare_discovery's file set exactly: `project_charter.md`, `evidence.txt`, `thesis.md`, `raw/`.
- Invented new top-level rubric keys → rubric loader silently ignores, loop runs with defaults. **Fix:** stick to the key set in rubric_specification.md §§2-8 unless you've extended the loader.
- Forgot to mirror dimension names in `criteria` short-key dict → judge scoring may collapse. **Fix:** for each dimension, add a `criteria["N_Short_Name"]` line.
- Rubric version not bumped after edit → version-reason field stale; no one can tell what changed. **Fix:** bump `rubric_version` + add `rubric_version_reason` on every substantive edit.

## 7. When to consult this map

- Before creating any new rubric JSON.
- Before hand-editing an existing rubric (not the regen case; fully-generator-driven edits stay safe).
- After GP-133 R4 or any other pre-run gate rejects at launch (the specific gate message tells you which §16-20 rule you violated).
- After a mutator run produces surprisingly low or erratic scores — sometimes the rubric is malformed in a way that degrades scoring silently.

## 8. Relationship to other docs

- `docs/concepts/rubric_specification.md` — authoritative spec. This file is a checklist / index over it.
- `docs/internal/autoresearch_loop_architectural_map.md` — the runtime map. Read alongside this for end-to-end flow.
- `docs/guides/quickstart.md` §Qualitative Projects — the user-facing shortest path.
- `docs/guides/experiment_cookbook.md` §0A — expanded scenarios.
