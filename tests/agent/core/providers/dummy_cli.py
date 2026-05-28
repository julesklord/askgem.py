import json
import sys
import time


def main():
    if len(sys.argv) < 2:
        print("Usage: dummy_cli.py <prompt>")
        sys.exit(1)

    _prompt = sys.argv[1]

    # Simulate processing delay
    time.sleep(1)

    print("I received your prompt. Let me check the tools.\n", flush=True)
    time.sleep(1)

    # Simulate tool call
    print("```json")
    print(json.dumps({"mentask_tool_call": {"name": "read_file", "arguments": {"path": "README.md"}}}, indent=2))
    print("```", flush=True)

    time.sleep(1)
    print("\nExecuting tool...", flush=True)


if __name__ == "__main__":
    main()
