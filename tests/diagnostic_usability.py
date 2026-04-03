#!/usr/bin/env python3
"""
Usability Diagnostic for askgem — automated test harness.

Simulates the user's interactive flow (create file → write content → read file → verify)
across multiple languages. Monitors token usage per request and switches models on quota errors.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google import genai
from google.genai import types

from askgem.tools.file_tools import edit_file, read_file
from askgem.tools.system_tools import execute_bash, list_directory

# ── Config ──────────────────────────────────────────────────────────────
API_KEY_PATH = os.path.expanduser("~/.askgem/.gemini_api_key_unencrypted")
TEST_DIR = "/tmp/askgem_diagnostic"
# Models ordered by generosity of free-tier quota
MODEL_FALLBACK_ORDER = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
]
SYSTEM_INSTRUCTION = (
    "You are askgem, a coding agent. Working directory: {cwd}. "
    "Use edit_file to create or write files. Use read_file to read them. "
    "Always reply briefly. Do NOT explain code unless asked."
)
TOOLS = [list_directory, execute_bash, read_file, edit_file]

# ── Test Cases (small scripts to save tokens) ──────────────────────────
TEST_CASES = [
    {
        "id": "python",
        "prompt": f"Create the file {TEST_DIR}/hello.py with a Python script that prints 'Hello World'",
        "expected_file": f"{TEST_DIR}/hello.py",
        "verify_cmd": f"python3 {TEST_DIR}/hello.py",
        "expected_output": "Hello World",
    },
    {
        "id": "bash",
        "prompt": f"Create the file {TEST_DIR}/sum.sh with a bash script that prints the result of 2+2",
        "expected_file": f"{TEST_DIR}/sum.sh",
        "verify_cmd": f"bash {TEST_DIR}/sum.sh",
        "expected_output": "4",
    },
    {
        "id": "javascript",
        "prompt": f"Create the file {TEST_DIR}/greet.js with a Node.js script that prints 'Hola Mundo'",
        "expected_file": f"{TEST_DIR}/greet.js",
        "verify_cmd": f"node {TEST_DIR}/greet.js",
        "expected_output": "Hola Mundo",
    },
]


def load_api_key():
    with open(API_KEY_PATH) as f:
        return f.read().strip()


def count_tokens_in_text(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return max(1, len(text) // 4)


def execute_tool_call(fc):
    """Execute a function call from the model and return the result Part."""
    name = fc.name
    args = dict(fc.args) if fc.args else {}
    print(f"    🔧 Tool call: {name}({json.dumps(args, ensure_ascii=False)[:120]})")

    if name == "edit_file":
        result = edit_file(**args)
    elif name == "read_file":
        result = read_file(**args)
    elif name == "execute_bash":
        result = execute_bash(**args)
    elif name == "list_directory":
        result = list_directory(**args)
    else:
        result = f"Unknown tool: {name}"

    status = "✅" if "Success" in result or "Error" not in result else "❌"
    print(f"    {status} Result: {result[:100]}")
    return types.Part.from_function_response(name=name, response={"result": result})


def run_single_test(client, model_name, test_case):
    """Run a single test case. Returns (success, token_count, model_used)."""
    print(f"\n  ── Test: {test_case['id']} (model: {model_name}) ──")

    config = types.GenerateContentConfig(
        temperature=0.2,  # Low temp for deterministic tool use
        tools=TOOLS,
        system_instruction=SYSTEM_INSTRUCTION.format(cwd=TEST_DIR),
        max_output_tokens=256,  # TIGHT cap to save quota
    )

    prompt = test_case["prompt"]
    est_input_tokens = count_tokens_in_text(prompt + SYSTEM_INSTRUCTION)
    print(f"    📊 Est. input tokens: ~{est_input_tokens}")

    try:
        chat = client.chats.create(model=model_name, config=config)

        # Send the prompt (non-streaming for simplicity)
        response = chat.send_message(prompt)
        total_tokens = est_input_tokens

        # Process up to 5 rounds of tool calls
        for _ in range(5):
            function_calls = []

            # Detect function calls
            if response.candidates:
                for candidate in response.candidates:
                    content = getattr(candidate, "content", None)
                    parts = getattr(content, "parts", []) or []
                    for part in parts:
                        fc = getattr(part, "function_call", None)
                        if fc and getattr(fc, "name", None):
                            function_calls.append(fc)

            if not function_calls:
                # Model responded with text only
                text = getattr(response, "text", "") or ""
                total_tokens += count_tokens_in_text(text)
                print(f"    💬 Model text: {text[:120]}")
                break

            # Execute all tool calls
            tool_responses = [execute_tool_call(fc) for fc in function_calls]
            for tr in tool_responses:
                total_tokens += count_tokens_in_text(str(tr))

            # Feed results back
            response = chat.send_message(tool_responses)
            total_tokens += 50  # overhead estimate

        # ── Verify output ──
        expected_file = test_case["expected_file"]
        file_exists = os.path.exists(expected_file)

        exec_ok = False
        if file_exists and test_case.get("verify_cmd"):
            import subprocess
            try:
                result = subprocess.run(
                    test_case["verify_cmd"], shell=True, capture_output=True, text=True, timeout=10
                )
                exec_ok = test_case["expected_output"] in result.stdout
                print(f"    🏃 Exec output: '{result.stdout.strip()}' (expected: '{test_case['expected_output']}')")
            except Exception as e:
                print(f"    ⚠️  Exec failed: {e}")

        print(f"    📊 Total est. tokens used: ~{total_tokens}")

        success = file_exists and exec_ok
        return success, total_tokens, model_name

    except Exception as e:
        err = str(e)
        if "429" in err:
            print(f"    ❌ QUOTA EXHAUSTED on {model_name}")
            return None, 0, model_name  # None = quota error, need fallback
        else:
            print(f"    ❌ Error: {err[:150]}")
            return False, 0, model_name


def main():
    os.makedirs(TEST_DIR, exist_ok=True)
    api_key = load_api_key()
    client = genai.Client(api_key=api_key)

    print("=" * 60)
    print("  askgem Usability Diagnostic")
    print(f"  Test directory: {TEST_DIR}")
    print(f"  Models to try: {MODEL_FALLBACK_ORDER}")
    print("=" * 60)

    results = []
    cumulative_tokens = 0
    current_model_idx = 0

    for test in TEST_CASES:
        # Clean up from previous runs
        if os.path.exists(test["expected_file"]):
            os.remove(test["expected_file"])

        success = None
        tokens = 0
        model_used = ""

        while success is None and current_model_idx < len(MODEL_FALLBACK_ORDER):
            model = MODEL_FALLBACK_ORDER[current_model_idx]
            success, tokens, model_used = run_single_test(client, model, test)

            if success is None:
                # Quota hit — try next model
                current_model_idx += 1
                print(f"    ↪ Switching to next model (idx={current_model_idx})...")
                time.sleep(2)

        cumulative_tokens += tokens

        if success is None:
            print("\n  🛑 ALL MODELS EXHAUSTED. Stopping diagnostic.")
            results.append({"test": test["id"], "status": "QUOTA_EXHAUSTED", "tokens": 0, "model": "N/A"})
            break

        results.append({
            "test": test["id"],
            "status": "PASS" if success else "FAIL",
            "tokens": tokens,
            "model": model_used,
        })

        # Token budget check
        if cumulative_tokens > 5000:
            print(f"\n  ⚠️  Token budget exceeded ({cumulative_tokens} > 5000). Stopping tests early.")
            break

        # Cooldown between tests to avoid RPM limits
        print("    ⏳ Cooling down 5s to avoid rate limits...")
        time.sleep(5)

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  DIAGNOSTIC SUMMARY")
    print("=" * 60)
    for r in results:
        icon = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "🛑"
        print(f"  {icon} {r['test']:12} | {r['status']:16} | ~{r['tokens']:4} tokens | model: {r['model']}")
    print(f"\n  Cumulative tokens: ~{cumulative_tokens}")
    print("=" * 60)


if __name__ == "__main__":
    main()
