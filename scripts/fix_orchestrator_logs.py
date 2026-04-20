import os

path = "src/askgem/agent/orchestrator.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Log reasoning start
content = content.replace(
    '        while True:',
    '        turn_id = 0\n        while True:\n            turn_id += 1\n            _logger.info(f"--- Agent Turn {turn_id} Start ---")'
)

# Log tool execution
content = content.replace(
    '            # Delegate execution batch to ExecutionManager',
    '            _logger.info(f"Executing {len(assistant_msg.tool_calls)} tools...")'
)

# Log tool results
content = content.replace(
    '                yield {',
    '                _logger.debug(f"Tool {tool_name} result received (error={result.is_error})")\n                yield {'
)

# Log snapping
content = content.replace(
    '_logger.info("Context threshold reached. Snapping...")',
    '_logger.warning(f"Context Snapping Triggered! Threshold exceeded. Current model: {self.client.model_name}")'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
