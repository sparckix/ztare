import os
import json
import argparse
from google import genai
from google.genai import types
from src.ztare.common import utils
from src.ztare.common.llm_runtime import PRODUCTION_CALL_RETRIES
from src.ztare.common.paths import PROJECTS_DIR, RUBRICS_DIR
import time
import concurrent.futures
from src.ztare.primitives.primitive_library import format_attack_templates, retrieve_primitives
from src.ztare.validator.shadow_board import build_shadow_board_committee
from src.ztare.validator.v4_family import is_v4_family_project
parser = argparse.ArgumentParser()
parser.add_argument("--project", required=True)
parser.add_argument("--use_primitives", action="store_true")
parser.add_argument("--primitive_top_k", type=int, default=3)
args = parser.parse_known_args()[0]

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
#MODEL_ID = "gemini-3.1-pro-preview"
#MODEL_ID = 'gemini-3-flash-preview'
MODEL_ID = "gemini-2.5-flash"


PROJECT_DIR = str(PROJECTS_DIR / args.project)
THESIS_PATH = f"{PROJECT_DIR}/thesis.md"
EVIDENCE_PATH = f"{PROJECT_DIR}/evidence.txt"
TEST_MODEL_PATH = f"{PROJECT_DIR}/test_model.py"

def read_file(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def safe_generate_committee(prompt, config=None):
    """Retries for 503 (High Demand) and 429 (Rate Limits)."""
    for i in range(PRODUCTION_CALL_RETRIES):
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            print(f"📡 [DEBUG] Dispatching request to {MODEL_ID}... (Attempt {i+1})")
            start_time = time.time()
            
            future = executor.submit(
                client.models.generate_content,
                model=MODEL_ID, contents=prompt, config=config
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
                raise e
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
    One of these attackers MUST focus exclusively on the mathematical solvency of the Python falsification suite and the LOAD-BEARING VARIABLES table
    Do NOT give them scoring criteria. They exist only to find logical flaws.

    KNOWN ADVERSARIAL PRECEDENTS:
    {primitive_context}
    
    EVIDENCE: {evidence_text}
    THESIS: {thesis_text}
    """
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
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
        }
    )
    
    response = safe_generate_committee(prompt, config=config)
    return utils.parse_llm_json(response.text)
         
    

if __name__ == "__main__":
    print(f"🕵️ Generating Specialized Firing Squad for [{args.project}]...")
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

    output_path = RUBRICS_DIR / f"dynamic_{args.project}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
        
    print(f"✅ Firing Squad generated and saved to {output_path}")
