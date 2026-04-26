import os

# 1. Clean history_manager.py indentation
h_path = "src/mentask/core/history_manager.py"
with open(h_path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# Simple fix for the reported line 52
with open(h_path, "w", encoding="utf-8") as f:
    for line in lines:
        if 'return {"__raw__": repr(obj)}' in line:
            f.write('        except Exception:\n            return {"__raw__": repr(obj)}\n')
        else:
            f.write(line)

# 2. Clean orchestrator.py indentation
o_path = "src/mentask/agent/orchestrator.py"
with open(o_path, "r", encoding="utf-8") as f:
    o_content = f.read()
# The error was in the snap block
o_content = o_content.replace(
    '                            new_history = await self._perform_context_snap(history, turn_config)',
    '                            new_history = await self._perform_context_snap(history, turn_config)' # Ensure 28 spaces or similar
)
# Better: just rewrite the file with correct indentation for the entire loop
