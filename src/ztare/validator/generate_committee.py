import os
import json
import argparse
import concurrent.futures
from ztare.common import utils
from ztare.common.dispatch_model import (
    dispatch_env_for_call_site,
    dispatch_model,
    dispatch_result_receipt,
    resolve_agent_execution_mode,
    resolve_dispatch_capability,
)
from ztare.common.llm_runtime import PRODUCTION_CALL_RETRIES, LLMRuntime, resolve_model_id
from ztare.common.paths import PROJECTS_DIR, REPO_ROOT, RUBRICS_DIR
import time
from ztare.primitives.primitive_library import format_attack_templates, retrieve_primitives
from ztare.validator.committees.shadow_board import build_shadow_board_committee
from ztare.validator.utilities.v4_family import is_v4_family_project
parser = argparse.ArgumentParser()
parser.add_argument("--project", required=True)
parser.add_argument("--use_primitives", action="store_true")
parser.add_argument("--primitive_top_k", type=int, default=3)
parser.add_argument(
    "--model",
    default=os.environ.get("ZTARE_COMMITTEE_MODEL", "gemini"),
    help=(
        "Committee generator model label (ZTARE alias — one of: "
        "gemini, gemini-lite, gemini-pro, claude, claude-opus, "
        "gpt4o, gpt4.1, gpt4.1-mini). Default 'gemini' maps to "
        "the standard gemini-2.5-flash for committee generation. "
        "Override via CLI or ZTARE_COMMITTEE_MODEL env var."
    ),
)
args = parser.parse_known_args()[0]
COMMITTEE_WORKER_DISPATCH_RECEIPTS: list[dict[str, object]] = []

_COMMITTEE_MODEL_LABEL = args.model.strip()
MODEL_ID = resolve_model_id(_COMMITTEE_MODEL_LABEL)
_IS_GEMINI = _COMMITTEE_MODEL_LABEL.startswith("gemini")
_RUNTIME = LLMRuntime()


PROJECT_DIR = str(PROJECTS_DIR / args.project)
THESIS_PATH = f"{PROJECT_DIR}/thesis.md"
EVIDENCE_PATH = f"{PROJECT_DIR}/evidence.txt"
TEST_MODEL_PATH = f"{PROJECT_DIR}/test_model.py"

def read_file(filepath):
    with open(filepath, 'r') as f:
        return f.read()

class _RuntimeResponse:
    """Duck-typed shim matching genai response.text interface."""
    def __init__(self, text):
        self.text = text


def _prompt_with_response_config_hint(prompt: str, config) -> str:
    if config is None:
        return prompt
    response_mime = (
        config.get("response_mime_type")
        if isinstance(config, dict)
        else getattr(config, "response_mime_type", None)
    )
    response_schema = (
        config.get("response_schema")
        if isinstance(config, dict)
        else getattr(config, "response_schema", None)
    )
    if not response_mime and response_schema is None:
        return prompt
    try:
        schema_text = json.dumps(response_schema, default=str, indent=2) if response_schema is not None else ""
    except TypeError:
        schema_text = str(response_schema)
    return (
        prompt.rstrip()
        + "\n\nRESPONSE CONTRACT FOR SUBSCRIPTION WORKER:\n"
        + (f"- MIME/type expectation: {response_mime}\n" if response_mime else "")
        + (
            "- Return only a JSON value matching this schema. No markdown, "
            "no code fences, no explanatory preamble.\n"
            f"{schema_text}\n"
            if schema_text
            else ""
        )
    )


def safe_generate_committee(prompt, config=None):
    """Retries for 503 (High Demand) and 429 (Rate Limits).

    Dispatches through the shared lazy provider runtime or a subscription worker.
    """
    capability = resolve_dispatch_capability("committee")
    if capability == "agent":
        result = dispatch_model(
            _prompt_with_response_config_hint(prompt, config),
            capability="agent",
            fungible=True,
            stateful=False,
            backend=os.environ.get("ZTARE_AUTORESEARCH_COMMITTEE_AGENT_RUNTIME"),
            repo=REPO_ROOT,
            agent_id=f"autoresearch_committee_{args.project}",
            timeout_seconds=int(os.environ.get("ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS", "600")),
            enabled_env=dispatch_env_for_call_site("committee"),
            agent_execution_mode=resolve_agent_execution_mode("committee"),
        )
        if result.returncode != 0:
            raise RuntimeError(
                "subscription committee dispatch failed "
                f"(returncode={result.returncode}): {result.stderr[:1200]}"
            )
        COMMITTEE_WORKER_DISPATCH_RECEIPTS.append(
            dispatch_result_receipt("committee", result)
        )
        if result.recovery_note:
            print(f"🔁 Subscription committee recovery: {result.recovery_note}")
        return _RuntimeResponse(result.text)
    if capability != "llm":
        raise ValueError(f"unsupported committee dispatch capability: {capability}")

    if not _IS_GEMINI:
        full_prompt = _prompt_with_response_config_hint(prompt, config)
        for i in range(PRODUCTION_CALL_RETRIES):
            try:
                print(f"📡 [DEBUG] Dispatching request to {MODEL_ID} via llm_runtime... (Attempt {i+1})")
                start_time = time.time()
                response = _RUNTIME.call_text(
                    full_prompt,
                    model_id=MODEL_ID,
                    max_tokens=4096,
                    timeout_wait_seconds=15,
                    request_label="committee_generation",
                )
                elapsed = time.time() - start_time
                print(f"✅ [DEBUG] Response received in {elapsed:.1f}s")
                return _RuntimeResponse(response.text)
            except Exception as e:
                error_str = str(e)
                if any(code in error_str for code in ["429", "500", "502", "503", "504"]):
                    wait_time = (i + 1) * 15
                    print(f"⚠️ API Transient Issue ({error_str[:15]}...). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Unhandled Exception: {error_str}")
                    raise
        raise Exception("Max retries exceeded.")

    # Keep the established Gemini structured-output and 150-second deadline.
    # Imports remain inside the actual API route, so subscription committees do
    # not need the Google SDK merely to start.
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Gemini committee generation requires the optional SDK. "
            "Install `ztare[google]` or select subscription dispatch."
        ) from exc
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    gemini_config = types.GenerateContentConfig(**config) if isinstance(config, dict) else config
    for i in range(PRODUCTION_CALL_RETRIES):
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            print(f"📡 [DEBUG] Dispatching request to {MODEL_ID}... (Attempt {i+1})")
            start_time = time.time()
            future = executor.submit(
                client.models.generate_content,
                model=MODEL_ID,
                contents=prompt,
                config=gemini_config,
            )
            response = future.result(timeout=150)
            elapsed = time.time() - start_time
            print(f"✅ [DEBUG] Response received in {elapsed:.1f}s")
            return response
        except concurrent.futures.TimeoutError:
            wait_time = (i + 1) * 15
            print(f"⚠️ Zombie Connection Killed (150s Timeout). Retrying in {wait_time}s...")
            time.sleep(wait_time)
        except Exception as e:
            error_str = str(e)
            if any(code in error_str for code in ["429", "500", "502", "503", "504"]):
                wait_time = (i + 1) * 15
                print(f"⚠️ API Transient Issue ({error_str[:15]}...). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ Unhandled Exception: {error_str}")
                raise
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    raise Exception("Max retries exceeded.")

def generate_dynamic_attackers(thesis_text, evidence_text):
    primitive_context = "None."
    if args.use_primitives:
        primitive_context = format_attack_templates(
            retrieve_primitives(
                "\n".join([thesis_text, evidence_text]),
                top_k=args.primitive_top_k,
                epistemic_role="attack_template",
            )
        )
    prompt = f"""
    You are an elite epistemological expert, knowledgable across domains.
    Read the thesis and the immutable evidence.
    Identify the 3 most vulnerable assumptions.
    
    Generate a JSON array of 3 distinct, highly specialized 'Attacker' personas to audit this specific document.
    They must be adversarial, mathematically rigorous, and focused exclusively on edge cases and execution friction.
    One of these attackers MUST focus exclusively on the mathematical solvency of the Python falsification suite and the CRUX VARIABLES table
    Do NOT give them scoring criteria. They exist only to find logical flaws.

    KNOWN ADVERSARIAL PRECEDENTS:
    {primitive_context}
    
    EVIDENCE: {evidence_text}
    THESIS: {thesis_text}
    """
    
    config = {
        "response_mime_type": "application/json",
        "response_schema": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "role": {"type": "STRING", "description": "e.g., Hospital CFO, Enterprise IT Architect"},
                    "persona": {"type": "STRING", "description": "Detailed psychological priming. How do they attack?"},
                    "focus_area": {"type": "STRING", "description": "The specific vulnerability they must target."}
                },
                "required": ["role", "persona", "focus_area"]
            }
        },
    }
    
    response = safe_generate_committee(prompt, config=config)
    return utils.parse_llm_json(response.text)
         
    

if __name__ == "__main__":
    print(f"🕵️ Generating Specialized Verification Panel for [{args.project}]...")
    thesis = read_file(THESIS_PATH)
    evidence = read_file(EVIDENCE_PATH)
    test_model = read_file(TEST_MODEL_PATH) if os.path.exists(TEST_MODEL_PATH) else ""

    if is_v4_family_project(args.project):
        output = build_shadow_board_committee(
            thesis_text=thesis,
            evidence_text=evidence,
            test_model_text=test_model,
        )
    else:
        output = {"committee": generate_dynamic_attackers(thesis, evidence)}
    output["worker_dispatch_receipts"] = list(COMMITTEE_WORKER_DISPATCH_RECEIPTS)

    output_path = RUBRICS_DIR / f"dynamic_{args.project}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
        
    print(f"✅ Verification Panel generated and saved to {output_path}")
