import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH_ROOT = Path(__file__).resolve().parent
SPECIMENS_ROOT = BENCH_ROOT / 'specimens'
MAIN_SPECIMEN_ROOTS = [
    SPECIMENS_ROOT / 'bad',
    SPECIMENS_ROOT / 'good',
    SPECIMENS_ROOT / 'corpus_bad',
]
OOD_ROOT = SPECIMENS_ROOT / 'ood'
STAGE1_OOD_ROOT = BENCH_ROOT / 'stage1_ood'
STAGE3_OOD_ROOT = BENCH_ROOT / 'stage3_ood'
DERIVED_SUBTLE_ROOT = BENCH_ROOT / 'derived_subtle'
CLAIM_TEST_MISMATCH_ROOT = BENCH_ROOT / 'claim_test_mismatch'
AUXILIARY_HISTORICAL_ROOT = BENCH_ROOT / 'auxiliary_historical'
RUNS_ROOT = BENCH_ROOT / 'runs'

STAGE1_REGRESSION_SPECIMENS = {
    't2_ai_inference',
    'deterministic_score_contract',
    'fail_closed_test_status',
}

STAGE2_REGRESSION_SPECIMENS = {
    't2_ai_inference',
    'deterministic_score_contract',
    'future_distress_threshold_fabrication',
    'opaque_local_risk_router',
    'local_gate_whole_system_overclaim',
}

STAGE3_REGRESSION_SPECIMENS = {
    't2_ai_inference',
    'deterministic_score_contract',
    'future_distress_threshold_fabrication',
    'opaque_local_risk_router',
    'local_gate_whole_system_overclaim',
    'straw_man_design_central_station',
}

BASE_CONDITIONS = {
    'A_baseline_soft_judge': [],
    'B_deterministic_gates': ['--deterministic_score_gates'],
    'C_gates_plus_primitives': ['--deterministic_score_gates', '--use_primitives'],
}

ORDINARY_REVIEW_CONDITION = 'D_ordinary_review'
DEFAULT_ORDINARY_REVIEW_CONTRACT = (
    ROOT / 'benchmarks' / 'evaluator_hardening_frozen' / 'ordinary_review_arm_contract.json'
)

EXPERIMENTAL_CONDITIONS = {
    'C2_gates_plus_primitives_crux_first': [
        '--deterministic_score_gates',
        '--use_primitives',
        '--crux_first_primitives',
    ],
}

_MODEL_MAP = {
    'gemini': 'gemini-2.5-flash',
    'claude': 'claude-sonnet-4-6',
    'claude-opus': 'claude-opus-4-6',
    'gpt4o': 'gpt-4o',
}

_gemini_client = None
_anthropic_client = None
_openai_client = None


def _debug_print(enabled, message):
    if enabled:
        print(f"[debug] {message}", flush=True)


def _get_model_client(model_key):
    global _gemini_client, _anthropic_client, _openai_client
    model_id = _MODEL_MAP[model_key]
    if model_key == 'gemini':
        if _gemini_client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise RuntimeError(
                    "Gemini model access requires the optional 'google' dependency; "
                    "install it with `pip install 'ztare[google]'`."
                ) from exc
            _gemini_client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
        return model_id, _gemini_client
    if model_key in {'claude', 'claude-opus'}:
        if _anthropic_client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise RuntimeError(
                    "Claude model access requires the optional 'anthropic' dependency; "
                    "install it with `pip install 'ztare[anthropic]'`."
                ) from exc
            _anthropic_client = anthropic.Anthropic(
                api_key=os.environ.get('ANTHROPIC_API_KEY')
            )
        return model_id, _anthropic_client
    if _openai_client is None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI model access requires the optional 'openai' dependency; "
                "install it with `pip install 'ztare[openai]'`."
            ) from exc
        _openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    return model_id, _openai_client


def _call_json_model(prompt, model_key):
    model_id, client = _get_model_client(model_key)
    if model_key == 'gemini':
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
        )
        text = response.text
    elif model_key in {'claude', 'claude-opus'}:
        response = client.messages.create(
            model=model_id,
            max_tokens=1200,
            messages=[{'role': 'user', 'content': prompt}],
        )
        text = response.content[0].text
    else:
        response = client.chat.completions.create(
            model=model_id,
            max_tokens=1200,
            messages=[{'role': 'user', 'content': prompt}],
        )
        text = response.choices[0].message.content

    text = text.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f'Could not parse JSON from adjudicator response: {text[:300]}')
    return json.loads(text[start:end + 1])


def load_ordinary_review_contract(path=DEFAULT_ORDINARY_REVIEW_CONTRACT):
    contract_path = Path(path)
    if not contract_path.exists():
        raise SystemExit(f'ordinary-review contract not found: {contract_path}')
    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    if contract.get('arm_id') != ORDINARY_REVIEW_CONDITION:
        raise SystemExit(f'ordinary-review contract has wrong arm_id: {contract.get("arm_id")}')
    return contract


def load_ordinary_review_imports(path):
    import_path = Path(path)
    if not import_path.exists():
        raise SystemExit(f'ordinary-review import file not found: {import_path}')
    payload = json.loads(import_path.read_text(encoding='utf-8'))
    if isinstance(payload, dict) and 'reviews' in payload:
        rows = payload['reviews']
    elif isinstance(payload, dict) and 'rows' in payload:
        rows = payload['rows']
    elif isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = [
            dict(value, specimen_id=key) if isinstance(value, dict) else {
                'specimen_id': key,
                'review': value,
            }
            for key, value in payload.items()
        ]
    else:
        raise SystemExit('ordinary-review import must be a list, mapping, or object with rows/reviews')

    imported = {}
    for row in rows:
        if not isinstance(row, dict):
            raise SystemExit(f'ordinary-review import row is not an object: {row!r}')
        specimen_id = row.get('specimen_id')
        if not isinstance(specimen_id, str) or not specimen_id:
            raise SystemExit(f'ordinary-review import row missing specimen_id: {row!r}')
        if specimen_id in imported:
            raise SystemExit(f'ordinary-review import has duplicate specimen_id: {specimen_id}')
        review = row.get('review') if isinstance(row.get('review'), dict) else row
        provenance = {
            key: value
            for key, value in row.items()
            if key not in {'review'}
        }
        missing_provenance = []
        if not isinstance(provenance.get('model'), str) or not provenance.get('model'):
            missing_provenance.append('model')
        if not any(isinstance(provenance.get(key), str) and provenance.get(key) for key in {'timestamp', 'reviewed_at', 'created_at'}):
            missing_provenance.append('timestamp|reviewed_at|created_at')
        if not any(isinstance(provenance.get(key), str) and provenance.get(key) for key in {'prompt_sha256', 'prompt_hash', 'prompt_path', 'prompt'}):
            missing_provenance.append('prompt_sha256|prompt_hash|prompt_path|prompt')
        if not any(isinstance(provenance.get(key), str) and provenance.get(key) for key in {'provider', 'runtime', 'provider_runtime'}):
            missing_provenance.append('provider|runtime|provider_runtime')
        if missing_provenance:
            raise SystemExit(
                'ordinary-review import row missing provenance '
                f'{missing_provenance}: {specimen_id}'
            )
        imported[specimen_id] = {
            'review': review,
            'provenance': provenance,
            'import_base_dir': str(import_path.parent),
        }
    return imported


def build_ordinary_review_prompt(specimen, contract):
    thesis = (specimen['_dir'] / 'thesis.md').read_text(encoding='utf-8')
    evidence = (specimen['_dir'] / 'evidence.txt').read_text(encoding='utf-8')
    schema = contract['review_prompt_contract']['required_output_schema']
    rubric = specimen.get('rubric', 'epistemic_engine_v4')
    return f"""
You are an ordinary unstructured reviewer of one research claim. You are not
using ZTARE deterministic gates, mined primitive memory, exploit labels, prior
benchmark-condition outputs, or expected-answer fields.

Task: decide whether the claim should be accepted as stated.

Return strict JSON only, with exactly these keys:
{json.dumps(schema, indent=2)}

Interpretation:
- "accept_claim_as_stated": true only if the thesis is acceptable at its stated
  scope based on the supplied thesis and evidence.
- "score": a number from 0 to 100 for acceptability as stated.
- "fatal_flaw_identified": true if your review names a flaw that should block
  acceptance at the stated scope.
- "flaw_summary": one concise sentence. Use an empty string only if no fatal
  flaw is identified.
- "confidence": one of "low", "medium", or "high".

Allowed context:
- specimen thesis;
- specimen evidence;
- public rubric name;
- question: should this claim be accepted as stated?

Forbidden context:
- deterministic score-gate outputs;
- mined primitive or precedent labels;
- expected exploit labels or detection keywords;
- prior A/B/C benchmark condition outputs.

Rubric name: {rubric}

Specimen id: {specimen.get('id')}

Thesis:
{thesis}

Evidence:
{evidence}
"""


def normalize_prompt_text(text):
    return re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE).rstrip() + '\n'


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def source_run_specimen_ids(source_run):
    source_run_path = Path(source_run)
    if source_run_path.is_dir():
        results_path = source_run_path / 'results.json'
    else:
        results_path = source_run_path
    if not results_path.exists():
        raise SystemExit(f'source-run results not found: {results_path}')
    rows = json.loads(results_path.read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise SystemExit(f'source-run results must be a list: {results_path}')
    ids = sorted({
        row.get('specimen_id')
        for row in rows
        if isinstance(row, dict) and 'error' not in row and isinstance(row.get('specimen_id'), str)
    })
    if not ids:
        raise SystemExit(f'source-run results contain no specimen ids: {results_path}')
    return ids


def export_ordinary_review_prompt_packet(specimens, contract, out_dir, source_run=None):
    output_root = Path(out_dir)
    prompts_dir = output_root / 'prompts'
    prompts_dir.mkdir(parents=True, exist_ok=True)
    source_run_label = str(source_run) if source_run else '<source-run-results-or-directory>'

    manifest_rows = []
    import_template_rows = []
    for specimen in specimens:
        prompt = normalize_prompt_text(build_ordinary_review_prompt(specimen, contract))
        prompt_hash = sha256_text(prompt)
        prompt_path = prompts_dir / f"{specimen['id']}.txt"
        prompt_path.write_text(prompt, encoding='utf-8')
        manifest_rows.append(
            {
                'specimen_id': specimen['id'],
                'prompt_path': str(prompt_path.relative_to(output_root)),
                'prompt_sha256': prompt_hash,
                'rubric': specimen.get('rubric', 'epistemic_engine_v4'),
                'review_schema': contract['review_prompt_contract']['required_output_schema'],
            }
        )
        import_template_rows.append(
            {
                'specimen_id': specimen['id'],
                'model': '<ordinary-reviewer-model>',
                'timestamp': '<ISO-8601 review timestamp>',
                'prompt_sha256': prompt_hash,
                'provider_runtime': '<provider/runtime>',
                'review': {
                    'accept_claim_as_stated': '<boolean>',
                    'score': '<number from 0 to 100>',
                    'fatal_flaw_identified': '<boolean>',
                    'flaw_summary': '<string>',
                    'confidence': '<low|medium|high>',
                },
            }
        )

    manifest = {
        'arm_id': ORDINARY_REVIEW_CONDITION,
        'source_contract': str(Path(DEFAULT_ORDINARY_REVIEW_CONTRACT).relative_to(ROOT)),
        'source_run': source_run_label if source_run else None,
        'specimen_count': len(manifest_rows),
        'prompts': manifest_rows,
        'provenance_required_for_import': contract.get('required_import_provenance', {}),
        'forbidden_context': contract['review_prompt_contract']['forbidden_context'],
        'answer_key_fields_omitted': [
            'label',
            'expected_exploit',
            'detection_keywords',
            'structural_detection_keywords',
            'expected_flags',
            'structural_expected_flags',
            'prior condition outputs from A/B/C',
        ],
    }
    (output_root / 'ordinary_review_prompt_manifest.json').write_text(
        json.dumps(manifest, indent=2) + '\n',
        encoding='utf-8',
    )
    (output_root / 'ordinary_review_import_template.json').write_text(
        json.dumps({'reviews': import_template_rows}, indent=2) + '\n',
        encoding='utf-8',
    )
    (output_root / 'README.md').write_text(
        f"""# Ordinary Review Packet

This packet is the `D_ordinary_review` reviewer handoff for the frozen
constraint-memory evaluator-hardening suite.

## What to Review

- Source run: `{source_run_label}`
- Specimens: `{len(manifest_rows)}`
- Prompt files: `prompts/*.txt`
- Return format: fill `ordinary_review_import_template.json`

Review each prompt independently. Use only the prompt text. Do not use ZTARE
deterministic gate output, mined primitive memory, exploit labels, prior
benchmark-condition output, or any expected-answer metadata.

## Required Row Shape

Each row must keep:

- `specimen_id`
- `model`
- `timestamp`
- `prompt_sha256`
- `provider_runtime`
- `review.accept_claim_as_stated`
- `review.score`
- `review.fatal_flaw_identified`
- `review.flaw_summary`
- `review.confidence`

`prompt_sha256` must stay equal to the hash in the template. The import path
fails closed if a row is missing provenance, if a selected specimen is missing,
or if prompt provenance does not bind to the exact generated prompt.

## Preflight Returned Rows

From the repository root:

```bash
make benchmark-ordinary-review-validate-import BENCH_ORDINARY_IMPORT=path/to/ordinary_review_rows.json
```

## Freeze As Fourth Arm

After preflight passes:

```bash
make benchmark-ordinary-review BENCH_ORDINARY_IMPORT=path/to/ordinary_review_rows.json
```

Before editing frozen-suite metadata:

```bash
make benchmark-ordinary-review-freeze-check BENCH_ORDINARY_RUN=benchmarks/constraint_memory/runs/<run_id>
```

Do not describe the suite as a completed four-arm comparison until a real
ordinary-review import run has been frozen under
`benchmarks/constraint_memory/runs/<run_id>/` and promoted into the frozen
suite metadata.
""",
        encoding='utf-8',
    )
    return {
        'ok': True,
        'arm_id': ORDINARY_REVIEW_CONDITION,
        'output_dir': str(output_root),
        'specimen_count': len(manifest_rows),
        'manifest_path': str(output_root / 'ordinary_review_prompt_manifest.json'),
        'import_template_path': str(output_root / 'ordinary_review_import_template.json'),
        'readme_path': str(output_root / 'README.md'),
    }


def normalize_ordinary_review(raw):
    if not isinstance(raw, dict):
        raise ValueError('ordinary-review response must be a JSON object')
    required = {
        'accept_claim_as_stated',
        'score',
        'fatal_flaw_identified',
        'flaw_summary',
        'confidence',
    }
    missing = sorted(required.difference(raw))
    if missing:
        raise ValueError(f'ordinary-review response missing keys: {missing}')
    if not isinstance(raw['accept_claim_as_stated'], bool):
        raise ValueError('accept_claim_as_stated must be boolean')
    if not isinstance(raw['fatal_flaw_identified'], bool):
        raise ValueError('fatal_flaw_identified must be boolean')
    if not isinstance(raw['flaw_summary'], str):
        raise ValueError('flaw_summary must be string')
    if raw['confidence'] not in {'low', 'medium', 'high'}:
        raise ValueError('confidence must be low, medium, or high')
    score = raw['score']
    if not isinstance(score, (int, float)):
        raise ValueError('score must be numeric')
    if not 0 <= float(score) <= 100:
        raise ValueError('score must be between 0 and 100')
    return {
        'accept_claim_as_stated': raw['accept_claim_as_stated'],
        'score': float(score),
        'fatal_flaw_identified': raw['fatal_flaw_identified'],
        'flaw_summary': raw['flaw_summary'].strip(),
        'confidence': raw['confidence'],
    }


def validate_ordinary_review_prompt_binding(import_row, prompt, prompt_path):
    provenance = import_row.get('provenance') or {}
    import_base_dir = import_row.get('import_base_dir')
    expected_hash = sha256_text(prompt)
    observed_hash = provenance.get('prompt_sha256') or provenance.get('prompt_hash')
    if isinstance(observed_hash, str) and observed_hash:
        if observed_hash != expected_hash:
            raise ValueError(
                'ordinary-review import prompt hash mismatch: '
                f'expected {expected_hash}, got {observed_hash}'
            )
        return expected_hash

    prompt_literal = provenance.get('prompt')
    if isinstance(prompt_literal, str) and prompt_literal:
        literal_hash = sha256_text(prompt_literal)
        if literal_hash != expected_hash:
            raise ValueError(
                'ordinary-review import prompt literal mismatch: '
                f'expected hash {expected_hash}, got {literal_hash}'
            )
        return expected_hash

    prompt_ref = provenance.get('prompt_path')
    if isinstance(prompt_ref, str) and prompt_ref:
        candidate = Path(prompt_ref)
        candidates = [candidate]
        if not candidate.is_absolute():
            if import_base_dir:
                candidates.append(Path(import_base_dir) / candidate)
            candidates.append(Path(prompt_path).parent / candidate)
        candidate = next((path for path in candidates if path.exists()), candidates[0])
        if not candidate.exists():
            raise ValueError(f'ordinary-review import prompt_path not found: {prompt_ref}')
        path_hash = sha256_text(candidate.read_text(encoding='utf-8'))
        if path_hash != expected_hash:
            raise ValueError(
                'ordinary-review import prompt_path content mismatch: '
                f'expected hash {expected_hash}, got {path_hash}'
            )
        return expected_hash

    raise ValueError('ordinary-review import missing prompt hash, prompt literal, or readable prompt_path')


def validate_ordinary_review_import_packet(specimens, contract, imported_reviews):
    rows = []
    missing = []
    for specimen in specimens:
        import_row = (imported_reviews or {}).get(specimen['id'])
        if not import_row:
            missing.append(specimen['id'])
            continue
        prompt = normalize_prompt_text(build_ordinary_review_prompt(specimen, contract))
        validation_prompt_path = (
            RUNS_ROOT
            / '_ordinary_review_import_preflight'
            / specimen['id']
            / ORDINARY_REVIEW_CONDITION
            / 'ordinary_review_prompt.txt'
        )
        validate_ordinary_review_prompt_binding(import_row, prompt, validation_prompt_path)
        review = normalize_ordinary_review(import_row['review'])
        rows.append(
            {
                'specimen_id': specimen['id'],
                'prompt_sha256': sha256_text(prompt),
                'model': import_row['provenance'].get('model'),
                'reviewed_at': (
                    import_row['provenance'].get('timestamp')
                    or import_row['provenance'].get('reviewed_at')
                    or import_row['provenance'].get('created_at')
                ),
                'provider_runtime': (
                    import_row['provenance'].get('provider_runtime')
                    or import_row['provenance'].get('provider')
                    or import_row['provenance'].get('runtime')
                ),
                'accept_claim_as_stated': review['accept_claim_as_stated'],
                'score': review['score'],
                'fatal_flaw_identified': review['fatal_flaw_identified'],
                'confidence': review['confidence'],
            }
        )
    if missing:
        raise SystemExit(f'ordinary-review import missing selected specimen ids: {missing}')
    extra = sorted(set(imported_reviews or {}).difference({specimen['id'] for specimen in specimens}))
    return {
        'ok': True,
        'arm_id': ORDINARY_REVIEW_CONDITION,
        'selected_specimen_count': len(specimens),
        'validated_row_count': len(rows),
        'specimen_ids': [row['specimen_id'] for row in rows],
        'extra_import_rows_ignored': extra,
        'rows': rows,
    }


def load_specimens(specimen_filter=None, suite='main', specimen_ids=None):
    specimen_id_set = set(specimen_ids or [])
    specimens = []
    roots = []
    if suite in {'main', 'all'}:
        roots.extend(MAIN_SPECIMEN_ROOTS)
    if suite == 'stage1_regression':
        roots.extend(MAIN_SPECIMEN_ROOTS)
    if suite == 'stage2_regression':
        roots.extend(MAIN_SPECIMEN_ROOTS)
        roots.append(STAGE1_OOD_ROOT)
    if suite == 'stage3_regression':
        roots.extend(MAIN_SPECIMEN_ROOTS)
        roots.append(STAGE1_OOD_ROOT)
        roots.append(STAGE3_OOD_ROOT)
    if suite in {'ood', 'all'}:
        roots.append(OOD_ROOT)
    if suite == 'stage1_ood':
        roots.append(STAGE1_OOD_ROOT)
    if suite in {'derived_subtle', 'all'}:
        roots.append(DERIVED_SUBTLE_ROOT)
    if suite in {'claim_test_mismatch', 'all'}:
        roots.append(CLAIM_TEST_MISMATCH_ROOT)
    if suite in {'auxiliary_historical', 'all'}:
        roots.append(AUXILIARY_HISTORICAL_ROOT)
    for root in roots:
        if not root.exists():
            continue
        for meta_path in sorted(root.rglob('specimen.json')):
            meta = json.loads(meta_path.read_text())
            if specimen_filter and meta['id'] != specimen_filter:
                continue
            if specimen_id_set and meta['id'] not in specimen_id_set:
                continue
            if suite == 'stage1_regression' and meta['id'] not in STAGE1_REGRESSION_SPECIMENS:
                continue
            if suite == 'stage2_regression' and meta['id'] not in STAGE2_REGRESSION_SPECIMENS:
                continue
            if suite == 'stage3_regression' and meta['id'] not in STAGE3_REGRESSION_SPECIMENS:
                continue
            meta['_dir'] = meta_path.parent
            specimens.append(meta)
    if not specimens:
        raise SystemExit('No specimens found for requested filter.')
    if specimen_id_set:
        loaded_ids = {specimen['id'] for specimen in specimens}
        missing = sorted(specimen_id_set.difference(loaded_ids))
        if missing:
            raise SystemExit(f'Requested source-run specimen ids missing from suite {suite}: {missing}')
    return specimens


def stage_project(specimen, run_id, condition_name):
    project_name = f"_bench_{run_id}_{specimen['id']}_{condition_name}"
    project_dir = ROOT / 'projects' / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(specimen['_dir'] / 'thesis.md', project_dir / 'current_iteration.md')
    shutil.copyfile(specimen['_dir'] / 'evidence.txt', project_dir / 'evidence.txt')
    shutil.copyfile(specimen['_dir'] / 'test_model.py', project_dir / 'test_model.py')
    axioms_path = specimen['_dir'] / 'verified_axioms.json'
    if axioms_path.exists():
        shutil.copyfile(axioms_path, project_dir / 'verified_axioms.json')
    else:
        (project_dir / 'verified_axioms.json').write_text('[]\n', encoding='utf-8')
    return project_name, project_dir


def get_latest_log(project_dir, before_logs):
    after_logs = set(project_dir.glob('debate_log_iter_*.md'))
    new_logs = sorted(after_logs - before_logs)
    if new_logs:
        return new_logs[-1]
    all_logs = sorted(after_logs)
    return all_logs[-1] if all_logs else None


def detect_specimen(specimen, evaluation):
    text_parts = [
        str(evaluation.get('weakest_point', '')),
        str(evaluation.get('debate_summary', '')),
        json.dumps(evaluation.get('score_contract', {})),
        json.dumps(evaluation.get('criteria_failed', [])),
    ]
    haystack = ' '.join(text_parts).lower()
    family_matched_keywords = [
        keyword
        for keyword in specimen.get('detection_keywords', [])
        if keyword.lower() in haystack
    ]
    structural_matched_keywords = [
        keyword
        for keyword in specimen.get('structural_detection_keywords', [])
        if keyword.lower() in haystack
    ]
    expected_flags = specimen.get('expected_flags', {})
    family_flags_match = bool(expected_flags) and all(
        evaluation.get(key) == value for key, value in expected_flags.items()
    )
    structural_expected_flags = specimen.get('structural_expected_flags', {})
    structural_flags_match = bool(structural_expected_flags) and all(
        evaluation.get(key) == value for key, value in structural_expected_flags.items()
    )
    family_detected = bool(family_matched_keywords) or family_flags_match
    structural_detected = (
        family_detected
        or bool(structural_matched_keywords)
        or structural_flags_match
    )
    return {
        'family_detected': family_detected,
        'family_matched_keywords': family_matched_keywords,
        'family_flags_match': family_flags_match,
        'structural_detected': structural_detected,
        'structural_matched_keywords': structural_matched_keywords,
        'structural_flags_match': structural_flags_match,
    }


def adjudicate_detection(specimen, evaluation, adjudicator_model):
    prompt = f"""
You are adjudicating whether an evaluator correctly identified:
1. the expected exploit family, and/or
2. an acceptable alternative fatal structural flaw.

Return strict JSON with this schema:
{{
  "family_detected": true or false,
  "fatal_structural_detected": true or false,
  "confidence_family": "high" | "medium" | "low",
  "confidence_structural": "high" | "medium" | "low",
  "rationale_family": "<one short paragraph>",
  "rationale_structural": "<one short paragraph>"
}}

Rules:
- Focus on semantic equivalence, not exact wording.
- `family_detected` means the evaluator clearly identified the same exploit family or a very close taxonomic equivalent.
- `fatal_structural_detected` means the evaluator identified a genuinely fatal structural flaw that should count as a true positive kill even if it did not use the expected exploit-family label.
- Do not require the exact exploit label to appear verbatim.
- If the evaluator only criticizes a generic weakness without reaching either the exploit family or an acceptable fatal structural flaw, return false.
- Be stricter for `family_detected` than for `fatal_structural_detected`.
- A generic critique such as "weak forecast", "unsupported assumption", or "unproven inevitability claim" is NOT enough for `family_detected` unless it also identifies exploit-family behavior like rigged thresholds, hardcoded constants, cherry-picked parameters, fake differentiability, self-certification, or equivalent quantitative manipulation.

Expected exploit family:
{specimen.get("expected_exploit")}

Family-detection strict rule:
{specimen.get("family_detection_strict_rule", "None.")}

Acceptable alternative fatal structural failures:
{json.dumps(specimen.get("acceptable_structural_failures", []), indent=2)}

Specimen description:
{specimen.get("description", "")}

Known exploit-family keywords:
{json.dumps(specimen.get("detection_keywords", []), indent=2)}

Family-detection negative examples:
{json.dumps(specimen.get("family_negative_examples", []), indent=2)}

Known structural-failure keywords:
{json.dumps(specimen.get("structural_detection_keywords", []), indent=2)}

Evaluator weakest point:
{evaluation.get("weakest_point", "")}

Evaluator debate summary:
{evaluation.get("debate_summary", "")}

Evaluator criteria_failed:
{json.dumps(evaluation.get("criteria_failed", []))}

Evaluator score_contract:
{json.dumps(evaluation.get("score_contract", {}), indent=2)}
"""
    return _call_json_model(prompt, adjudicator_model)


def run_one(specimen, condition_name, flags, judge_model, run_id, pass_threshold, debug=False, stream_child=False, adjudicator_model=None, suite='main'):
    project_name, project_dir = stage_project(specimen, run_id, condition_name)
    results_dir = RUNS_ROOT / run_id / specimen['id'] / condition_name
    results_dir.mkdir(parents=True, exist_ok=True)
    before_logs = set(project_dir.glob('debate_log_iter_*.md'))

    eval_path = results_dir / 'eval_results.raw.json'
    _debug_print(debug, f"staged project={project_name}")

    cmd = [
        sys.executable,
        '-m',
        'ztare.validator.test_thesis',
        '--project', project_name,
        '--rubric', specimen.get('rubric', 'epistemic_engine_v4'),
        '--judge_model', judge_model,
        '--mutator_model', 'benchmark',
        '--disable_attacker_tools',
        '--eval_results_path', str(eval_path),
        *flags,
    ]
    if suite == 'stage3_regression' and '--use_primitives' in flags:
        cmd.extend(['--primitive_routing_profile', 'v4'])
    _debug_print(debug, f"running {' '.join(cmd)}")

    if stream_child:
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        stdout_lines = []
        assert proc.stdout is not None
        prefix = f"[{specimen['id']}::{condition_name}] "
        for line in proc.stdout:
            stdout_lines.append(line)
            print(prefix + line.rstrip(), flush=True)
        proc.wait()
        proc_stdout = ''.join(stdout_lines)
        proc_stderr = ''
    else:
        proc_completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        proc = proc_completed
        proc_stdout = proc_completed.stdout
        proc_stderr = proc_completed.stderr

    (results_dir / 'stdout.txt').write_text(proc_stdout, encoding='utf-8')
    (results_dir / 'stderr.txt').write_text(proc_stderr, encoding='utf-8')

    if proc.returncode != 0:
        _debug_print(debug, f"subprocess failed returncode={proc.returncode}")
        return {
            'project_name': project_name,
            'condition': condition_name,
            'returncode': proc.returncode,
            'error': 'validator module failed to execute',
            'stdout_path': str(results_dir / 'stdout.txt'),
            'stderr_path': str(results_dir / 'stderr.txt'),
        }

    if not eval_path.exists():
        _debug_print(debug, "missing eval_results output")
        return {
            'project_name': project_name,
            'condition': condition_name,
            'returncode': proc.returncode,
            'error': 'eval_results.json not produced',
            'stdout_path': str(results_dir / 'stdout.txt'),
            'stderr_path': str(results_dir / 'stderr.txt'),
        }

    evaluation = json.loads(eval_path.read_text(encoding='utf-8'))
    (results_dir / 'eval_results.json').write_text(
        json.dumps(evaluation, indent=2) + '\n', encoding='utf-8'
    )

    log_path = get_latest_log(project_dir, before_logs)
    if log_path:
        shutil.copyfile(log_path, results_dir / 'debate_log.md')

    detection = detect_specimen(specimen, evaluation)
    adjudication = None
    family_adjudicator_detected = None
    structural_adjudicator_detected = None
    if specimen['label'] == 'bad' and adjudicator_model:
        try:
            adjudication = adjudicate_detection(specimen, evaluation, adjudicator_model)
            family_adjudicator_detected = bool(adjudication.get('family_detected'))
            structural_adjudicator_detected = bool(adjudication.get('fatal_structural_detected'))
        except Exception as exc:
            adjudication = {
                'error': str(exc),
                'family_detected': None,
                'fatal_structural_detected': None,
            }
        (results_dir / 'detection_adjudication.json').write_text(
            json.dumps(adjudication, indent=2) + '\n', encoding='utf-8'
        )
    family_detected = detection['family_flags_match'] or (
        family_adjudicator_detected if adjudicator_model else detection['family_detected']
    )
    structural_detected = (
        family_detected
        or detection['structural_flags_match']
        or (structural_adjudicator_detected if adjudicator_model else detection['structural_detected'])
    )
    score = evaluation.get('score')
    passed = isinstance(score, (int, float)) and score >= pass_threshold

    row = {
        'project_name': project_name,
        'condition': condition_name,
        'label': specimen['label'],
        'specimen_id': specimen['id'],
        'expected_exploit': specimen.get('expected_exploit'),
        'acceptable_structural_failures': specimen.get('acceptable_structural_failures', []),
        'score': score,
        'passed_threshold': passed,
        'detected': structural_detected,
        'family_detected': family_detected,
        'structural_detected': structural_detected,
        'heuristic_detected': detection['structural_detected'],
        'heuristic_family_detected': detection['family_detected'],
        'heuristic_structural_detected': detection['structural_detected'],
        'adjudicator_detected': structural_adjudicator_detected,
        'adjudicator_family_detected': family_adjudicator_detected,
        'adjudicator_structural_detected': structural_adjudicator_detected,
        'matched_keywords': detection['structural_matched_keywords'],
        'matched_family_keywords': detection['family_matched_keywords'],
        'matched_structural_keywords': detection['structural_matched_keywords'],
        'flags_match': detection['structural_flags_match'],
        'family_flags_match': detection['family_flags_match'],
        'structural_flags_match': detection['structural_flags_match'],
        'weakest_point': evaluation.get('weakest_point'),
        'stdout_path': str(results_dir / 'stdout.txt'),
        'stderr_path': str(results_dir / 'stderr.txt'),
        'eval_results_path': str(results_dir / 'eval_results.json'),
        'detection_adjudication_path': str(results_dir / 'detection_adjudication.json') if adjudicator_model and specimen['label'] == 'bad' else None,
        'debate_log_path': str(results_dir / 'debate_log.md') if log_path else None,
        'returncode': proc.returncode,
    }

    if condition_name == 'A_baseline_soft_judge' and specimen['label'] == 'bad':
        row['score_decoupling'] = bool(structural_detected and passed)

    _debug_print(
        debug,
        f"completed score={score} family={family_detected} structural={structural_detected} "
        f"heur_family={detection['family_detected']} heur_struct={detection['structural_detected']} "
        f"adj_family={family_adjudicator_detected} adj_struct={structural_adjudicator_detected} "
        f"passed_threshold={passed}",
    )
    return row


def run_ordinary_review_one(
    specimen,
    judge_model,
    run_id,
    pass_threshold,
    contract,
    debug=False,
    imported_reviews=None,
    require_imported_review=False,
):
    results_dir = RUNS_ROOT / run_id / specimen['id'] / ORDINARY_REVIEW_CONDITION
    results_dir.mkdir(parents=True, exist_ok=True)
    prompt = normalize_prompt_text(build_ordinary_review_prompt(specimen, contract))
    prompt_path = results_dir / 'ordinary_review_prompt.txt'
    raw_path = results_dir / 'ordinary_review.raw.json'
    eval_path = results_dir / 'eval_results.json'
    prompt_path.write_text(prompt, encoding='utf-8')

    import_row = (imported_reviews or {}).get(specimen['id'])
    source = 'imported' if import_row else 'live_provider'
    _debug_print(debug, f"ordinary-review {specimen['id']} using {source}:{judge_model}")
    if require_imported_review and not import_row:
        return {
            'project_name': None,
            'condition': ORDINARY_REVIEW_CONDITION,
            'label': specimen['label'],
            'specimen_id': specimen['id'],
            'returncode': 1,
            'error': f'ordinary review import missing specimen_id: {specimen["id"]}',
            'ordinary_review_source': 'missing_import',
            'ordinary_review_prompt_path': str(prompt_path),
            'ordinary_review_raw_path': None,
        }
    try:
        if import_row:
            validate_ordinary_review_prompt_binding(import_row, prompt, prompt_path)
        raw = import_row['review'] if import_row else _call_json_model(prompt, judge_model)
        raw_path.write_text(json.dumps(raw, indent=2) + '\n', encoding='utf-8')
        review = normalize_ordinary_review(raw)
    except Exception as exc:
        return {
            'project_name': None,
            'condition': ORDINARY_REVIEW_CONDITION,
            'label': specimen['label'],
            'specimen_id': specimen['id'],
            'returncode': 1,
            'error': f'ordinary review failed: {exc}',
            'ordinary_review_source': source,
            'ordinary_review_prompt_path': str(prompt_path),
            'ordinary_review_raw_path': str(raw_path) if raw_path.exists() else None,
        }

    passed = bool(review['accept_claim_as_stated'])
    import_provenance = import_row.get('provenance') if import_row else {}
    reviewed_at = (
        import_provenance.get('timestamp')
        or import_provenance.get('reviewed_at')
        or import_provenance.get('created_at')
        or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    )
    row = {
        'project_name': None,
        'condition': ORDINARY_REVIEW_CONDITION,
        'label': specimen['label'],
        'specimen_id': specimen['id'],
        'expected_exploit': None,
        'acceptable_structural_failures': [],
        'score': review['score'],
        'passed_threshold': passed,
        'detected': review['fatal_flaw_identified'],
        'family_detected': False,
        'structural_detected': review['fatal_flaw_identified'],
        'heuristic_detected': None,
        'heuristic_family_detected': None,
        'heuristic_structural_detected': None,
        'adjudicator_detected': None,
        'adjudicator_family_detected': None,
        'adjudicator_structural_detected': None,
        'matched_keywords': [],
        'matched_family_keywords': [],
        'matched_structural_keywords': [],
        'flags_match': False,
        'family_flags_match': False,
        'structural_flags_match': False,
        'weakest_point': review['flaw_summary'],
        'accept_claim_as_stated': review['accept_claim_as_stated'],
        'fatal_flaw_identified': review['fatal_flaw_identified'],
        'confidence': review['confidence'],
        'ordinary_review_source': source,
        'ordinary_review_model': judge_model,
        'ordinary_review_reviewed_at': reviewed_at,
        'ordinary_review_import_provenance': import_provenance or None,
        'ordinary_review_prompt_path': str(prompt_path),
        'ordinary_review_raw_path': str(raw_path),
        'eval_results_path': str(eval_path),
        'returncode': 0,
    }
    eval_path.write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
    return row


def summarize(rows, pass_threshold, conditions):
    summary = {'pass_threshold': pass_threshold, 'conditions': {}}
    for condition_name in conditions:
        all_cond_rows = [r for r in rows if r['condition'] == condition_name]
        error_rows = [r for r in all_cond_rows if 'error' in r]
        cond_rows = [r for r in all_cond_rows if 'error' not in r]
        bad_rows = [r for r in cond_rows if r['label'] == 'bad']
        good_rows = [r for r in cond_rows if r['label'] == 'good']
        condition_summary = {
            'num_specimens': len(cond_rows),
            'attempted_specimens': len(all_cond_rows),
            'error_count': len(error_rows),
            'error_specimens': [r.get('specimen_id') for r in error_rows],
            'num_bad': len(bad_rows),
            'num_good': len(good_rows),
            'exploit_family_detection_rate': (sum(1 for r in bad_rows if r['family_detected']) / len(bad_rows)) if bad_rows else None,
            'fatal_structural_detection_rate': (sum(1 for r in bad_rows if r['structural_detected']) / len(bad_rows)) if bad_rows else None,
            'exploit_detection_rate': (sum(1 for r in bad_rows if r['structural_detected']) / len(bad_rows)) if bad_rows else None,
            'false_accept_rate': (sum(1 for r in bad_rows if r['passed_threshold']) / len(bad_rows)) if bad_rows else None,
            'false_reject_rate': (sum(1 for r in good_rows if not r['passed_threshold']) / len(good_rows)) if good_rows else None,
            'mean_bad_score': (sum(r['score'] for r in bad_rows) / len(bad_rows)) if bad_rows else None,
            'mean_good_score': (sum(r['score'] for r in good_rows) / len(good_rows)) if good_rows else None,
        }
        if condition_name == 'A_baseline_soft_judge' and bad_rows:
            condition_summary['score_decoupling_rate'] = sum(
                1 for r in bad_rows if r.get('score_decoupling')
            ) / len(bad_rows)
        summary['conditions'][condition_name] = condition_summary
    return summary


def build_ordinary_review_freeze_manifest(rows, summary, args, run_root, source_run_ids):
    ordinary_rows = [row for row in rows if row.get('condition') == ORDINARY_REVIEW_CONDITION]
    ordinary_errors = [row for row in ordinary_rows if 'error' in row]
    ordinary_success = [row for row in ordinary_rows if 'error' not in row]
    selected_ids = sorted(row.get('specimen_id') for row in ordinary_rows if row.get('specimen_id'))
    expected_ids = sorted(source_run_ids or selected_ids)
    missing_ids = sorted(set(expected_ids).difference(selected_ids))
    extra_ids = sorted(set(selected_ids).difference(expected_ids))

    row_manifests = []
    prompt_hashes = {}
    provenance_failures = []
    sources = sorted({row.get('ordinary_review_source') for row in ordinary_success})
    for row in ordinary_success:
        prompt_path = Path(row.get('ordinary_review_prompt_path', ''))
        raw_path = Path(row.get('ordinary_review_raw_path', ''))
        prompt_sha256 = None
        if prompt_path.exists():
            prompt_sha256 = sha256_text(prompt_path.read_text(encoding='utf-8'))
            prompt_hashes[row['specimen_id']] = prompt_sha256
        else:
            provenance_failures.append(f"missing prompt file: {row.get('specimen_id')}")
        if not raw_path.exists():
            provenance_failures.append(f"missing raw review file: {row.get('specimen_id')}")
        import_provenance = row.get('ordinary_review_import_provenance') or {}
        provider_runtime = (
            import_provenance.get('provider_runtime')
            or import_provenance.get('provider')
            or import_provenance.get('runtime')
            or row.get('ordinary_review_source')
        )
        reviewer_model = import_provenance.get('model') or row.get('ordinary_review_model')
        reviewed_at = (
            import_provenance.get('timestamp')
            or import_provenance.get('reviewed_at')
            or import_provenance.get('created_at')
            or row.get('ordinary_review_reviewed_at')
        )
        if not reviewer_model:
            provenance_failures.append(f"missing reviewer model: {row.get('specimen_id')}")
        if not reviewed_at:
            provenance_failures.append(f"missing review timestamp: {row.get('specimen_id')}")
        if not provider_runtime:
            provenance_failures.append(f"missing provider/runtime: {row.get('specimen_id')}")
        row_manifests.append(
            {
                'specimen_id': row['specimen_id'],
                'prompt_sha256': prompt_sha256,
                'prompt_path': row.get('ordinary_review_prompt_path'),
                'raw_review_path': row.get('ordinary_review_raw_path'),
                'eval_results_path': row.get('eval_results_path'),
                'source': row.get('ordinary_review_source'),
                'model': reviewer_model,
                'reviewed_at': reviewed_at,
                'provider_runtime': provider_runtime,
                'import_provenance': import_provenance or None,
            }
        )

    condition_summary = (summary.get('conditions') or {}).get(ORDINARY_REVIEW_CONDITION, {})
    blockers = []
    if not args.match_source_run:
        blockers.append('missing --match-source-run binding')
    if missing_ids:
        blockers.append(f'missing selected specimen ids: {missing_ids}')
    if extra_ids:
        blockers.append(f'extra specimen ids outside source run: {extra_ids}')
    if ordinary_errors:
        blockers.append(f'ordinary-review error rows: {len(ordinary_errors)}')
    if provenance_failures:
        blockers.extend(provenance_failures)
    if condition_summary.get('num_specimens') != len(expected_ids):
        blockers.append('metrics_summary specimen count does not match source-run specimen count')

    return {
        'arm_id': ORDINARY_REVIEW_CONDITION,
        'run_id': run_root.name,
        'run_root': str(run_root),
        'source_run': args.match_source_run,
        'source_run_bound': bool(args.match_source_run),
        'ordinary_review_import_results': args.ordinary_review_import_results,
        'ordinary_review_contract': args.ordinary_review_contract,
        'selected_specimen_count': len(selected_ids),
        'expected_source_specimen_count': len(expected_ids),
        'selected_specimen_ids': selected_ids,
        'expected_source_specimen_ids': expected_ids,
        'missing_source_specimen_ids': missing_ids,
        'extra_specimen_ids': extra_ids,
        'review_sources': sources,
        'prompt_hashes': dict(sorted(prompt_hashes.items())),
        'condition_summary': condition_summary,
        'row_count': len(ordinary_rows),
        'error_count': len(ordinary_errors),
        'error_rows': ordinary_errors,
        'rows': row_manifests,
        'can_promote_to_frozen_suite': not blockers,
        'promotion_blockers': blockers,
        'promotion_rule': (
            'Promote only when this manifest has can_promote_to_frozen_suite=true, '
            'the run remains bound to the frozen source run, every selected row has '
            'prompt/raw/model/provider provenance, and suite metadata is updated '
            'without changing the source specimen population.'
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--judge-model',
        default='gemini',
        choices=['gemini', 'claude', 'claude-opus', 'gpt4o'],
    )
    parser.add_argument('--specimen', help='Run only one specimen id')
    parser.add_argument(
        '--suite',
        default='main',
        choices=['main', 'stage1_regression', 'stage2_regression', 'stage3_regression', 'stage1_ood', 'ood', 'derived_subtle', 'claim_test_mismatch', 'auxiliary_historical', 'all'],
        help='Which specimen suite to run. `main` is the corpus/control benchmark, `stage1_regression` is the cheap 3-specimen V4 gate-check set, `stage2_regression` is the cheap 5-specimen hinge-alignment set, `stage3_regression` is the cheap 6-specimen primitive-routing set, `stage1_ood` is the cheap 3-specimen stage-1 out-of-distribution probe set, `ood` is the out-of-distribution stress-test set, `derived_subtle` is the synthetic sensitivity test set, `claim_test_mismatch` is the historical selective-rigor mini-suite, and `auxiliary_historical` is a separate holdout set of additional historical candidates.',
    )
    parser.add_argument('--pass-threshold', type=int, default=60)
    parser.add_argument('--jobs', type=int, default=1, help='Number of specimen/condition runs to execute in parallel.')
    parser.add_argument('--debug', action='store_true', help='Print detailed benchmark progress.')
    parser.add_argument(
        '--adjudicator-model',
        choices=['gemini', 'claude', 'claude-opus', 'gpt4o'],
        help='Optional LLM adjudicator used to decide whether the evaluator semantically caught the exploit family.',
    )
    parser.add_argument(
        '--include-crux-first-condition',
        action='store_true',
        help='Include the experimental C2 condition where the meta-judge identifies the load-bearing claim before consulting primitive context.',
    )
    parser.add_argument(
        '--include-ordinary-review-condition',
        action='store_true',
        help='Include D_ordinary_review: a plain LLM review arm with no deterministic gates or mined primitive context.',
    )
    parser.add_argument(
        '--ordinary-review-model',
        choices=['gemini', 'claude', 'claude-opus', 'gpt4o'],
        help='Model for D_ordinary_review. Defaults to --judge-model.',
    )
    parser.add_argument(
        '--ordinary-review-contract',
        default=str(DEFAULT_ORDINARY_REVIEW_CONTRACT),
        help='JSON contract that defines the D_ordinary_review prompt and scoring fields.',
    )
    parser.add_argument(
        '--ordinary-review-import-results',
        help='JSON file of precomputed D_ordinary_review rows. When supplied, every selected specimen must have an imported review row; the runner will not fall back to live provider calls.',
    )
    parser.add_argument(
        '--ordinary-review-export-prompts',
        help='Write a reviewer-safe D_ordinary_review prompt packet and import template, then exit without calling a provider.',
    )
    parser.add_argument(
        '--ordinary-review-validate-import-only',
        action='store_true',
        help='Validate imported D_ordinary_review rows for coverage, schema, provenance, and exact prompt binding, then exit without creating a benchmark run.',
    )
    parser.add_argument(
        '--match-source-run',
        help='Restrict selected specimens to the specimen ids in an existing benchmark run results.json. Use this for D_ordinary_review when comparing against a frozen source run.',
    )
    parser.add_argument(
        '--conditions',
        nargs='*',
        choices=['A_baseline_soft_judge', 'B_deterministic_gates', 'C_gates_plus_primitives', 'C2_gates_plus_primitives_crux_first', ORDINARY_REVIEW_CONDITION],
        help='Optional subset of benchmark conditions to run.',
    )
    args = parser.parse_args()
    conditions = dict(BASE_CONDITIONS)
    if args.include_crux_first_condition:
        conditions.update(EXPERIMENTAL_CONDITIONS)
    if args.include_ordinary_review_condition:
        conditions[ORDINARY_REVIEW_CONDITION] = None
    if args.suite == 'stage1_regression' and not args.conditions:
        conditions = {
            'B_deterministic_gates': BASE_CONDITIONS['B_deterministic_gates'],
            'C_gates_plus_primitives': BASE_CONDITIONS['C_gates_plus_primitives'],
        }
    if args.suite == 'stage2_regression' and not args.conditions:
        conditions = {
            'B_deterministic_gates': BASE_CONDITIONS['B_deterministic_gates'],
            'C_gates_plus_primitives': BASE_CONDITIONS['C_gates_plus_primitives'],
        }
    if args.suite == 'stage3_regression' and not args.conditions:
        conditions = {
            'B_deterministic_gates': BASE_CONDITIONS['B_deterministic_gates'],
            'C_gates_plus_primitives': BASE_CONDITIONS['C_gates_plus_primitives'],
        }
    if args.conditions:
        selected_conditions = {}
        all_conditions = dict(BASE_CONDITIONS)
        all_conditions.update(EXPERIMENTAL_CONDITIONS)
        all_conditions[ORDINARY_REVIEW_CONDITION] = None
        for name in args.conditions:
            selected_conditions[name] = all_conditions[name]
        conditions = selected_conditions

    source_run_ids = source_run_specimen_ids(args.match_source_run) if args.match_source_run else None
    specimens = load_specimens(args.specimen, suite=args.suite, specimen_ids=source_run_ids)
    ordinary_review_contract = None
    ordinary_review_imports = None
    if ORDINARY_REVIEW_CONDITION in conditions:
        ordinary_review_contract = load_ordinary_review_contract(args.ordinary_review_contract)
        if args.ordinary_review_import_results:
            ordinary_review_imports = load_ordinary_review_imports(args.ordinary_review_import_results)
    elif args.ordinary_review_import_results:
        raise SystemExit('--ordinary-review-import-results requires D_ordinary_review to be selected')
    if args.ordinary_review_export_prompts:
        if ORDINARY_REVIEW_CONDITION not in conditions:
            raise SystemExit('--ordinary-review-export-prompts requires D_ordinary_review to be selected')
        payload = export_ordinary_review_prompt_packet(
            specimens,
            ordinary_review_contract,
            args.ordinary_review_export_prompts,
            source_run=args.match_source_run,
        )
        print(json.dumps(payload, indent=2))
        return
    if args.ordinary_review_validate_import_only:
        if ORDINARY_REVIEW_CONDITION not in conditions:
            raise SystemExit('--ordinary-review-validate-import-only requires D_ordinary_review to be selected')
        if not ordinary_review_imports:
            raise SystemExit('--ordinary-review-validate-import-only requires --ordinary-review-import-results')
        payload = validate_ordinary_review_import_packet(
            specimens,
            ordinary_review_contract,
            ordinary_review_imports,
        )
        print(json.dumps(payload, indent=2))
        return
    run_id = time.strftime('%Y%m%d_%H%M%S')
    run_root = RUNS_ROOT / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    tasks = []
    for specimen in specimens:
        for condition_name, flags in conditions.items():
            tasks.append((specimen, condition_name, flags))

    rows = []
    if args.jobs <= 1:
        for specimen, condition_name, flags in tasks:
            print(f"[benchmark] {specimen['id']} :: {condition_name}")
            if condition_name == ORDINARY_REVIEW_CONDITION:
                rows.append(
                    run_ordinary_review_one(
                        specimen,
                        args.ordinary_review_model or args.judge_model,
                        run_id,
                        args.pass_threshold,
                        ordinary_review_contract,
                        debug=args.debug,
                        imported_reviews=ordinary_review_imports,
                        require_imported_review=ordinary_review_imports is not None,
                    )
                )
            else:
                rows.append(
                    run_one(
                        specimen,
                        condition_name,
                        flags,
                        args.judge_model,
                        run_id,
                        args.pass_threshold,
                        debug=args.debug,
                        stream_child=args.debug,
                        adjudicator_model=args.adjudicator_model,
                        suite=args.suite,
                    )
                )
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
            future_map = {}
            for specimen, condition_name, flags in tasks:
                print(f"[benchmark] queued {specimen['id']} :: {condition_name}")
                if condition_name == ORDINARY_REVIEW_CONDITION:
                    future = executor.submit(
                        run_ordinary_review_one,
                        specimen,
                        args.ordinary_review_model or args.judge_model,
                        run_id,
                        args.pass_threshold,
                        ordinary_review_contract,
                        args.debug,
                        ordinary_review_imports,
                        ordinary_review_imports is not None,
                    )
                else:
                    future = executor.submit(
                        run_one,
                        specimen,
                        condition_name,
                        flags,
                        args.judge_model,
                        run_id,
                        args.pass_threshold,
                        args.debug,
                        False,
                        args.adjudicator_model,
                        args.suite,
                    )
                future_map[future] = (specimen['id'], condition_name)

            for future in concurrent.futures.as_completed(future_map):
                specimen_id, condition_name = future_map[future]
                print(f"[benchmark] finished {specimen_id} :: {condition_name}")
                rows.append(future.result())

    (run_root / 'results.json').write_text(
        json.dumps(rows, indent=2) + '\n', encoding='utf-8'
    )
    summary = summarize(rows, args.pass_threshold, conditions)
    (run_root / 'metrics_summary.json').write_text(
        json.dumps(summary, indent=2) + '\n', encoding='utf-8'
    )
    if ORDINARY_REVIEW_CONDITION in conditions:
        freeze_manifest = build_ordinary_review_freeze_manifest(
            rows,
            summary,
            args,
            run_root,
            source_run_ids,
        )
        (run_root / 'ordinary_review_freeze_manifest.json').write_text(
            json.dumps(freeze_manifest, indent=2) + '\n',
            encoding='utf-8',
        )
    print(json.dumps(summary, indent=2))
    print(f"Saved benchmark run to {run_root}")
    error_rows = [row for row in rows if 'error' in row]
    if error_rows:
        raise SystemExit(f"benchmark failed: {len(error_rows)} row(s) errored")


if __name__ == '__main__':
    main()
