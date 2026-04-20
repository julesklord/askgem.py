import os

path = "src/askgem/agent/orchestrator.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace ensure_lsp_started with the more complete initialize()
content = content.replace(
    'await self.executor.ensure_lsp_started()',
    'await self.executor.initialize()'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
