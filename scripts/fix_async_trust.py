import os
import re

# 1. First, make TrustManager.load_trust async
trust_path = "src/mentask/core/trust_manager.py"
with open(trust_path, "r", encoding="utf-8") as f:
    trust_content = f.read()

# Remove load_trust from __init__
trust_content = trust_content.replace("self.load_trust()", "# self.load_trust() - now called async by ExecutionManager")
# Change load_trust signature to async
trust_content = trust_content.replace("def load_trust(self) -> None:", "async def load_trust(self) -> None:")

with open(trust_path, "w", encoding="utf-8") as f:
    f.write(trust_content)

# 2. Update ExecutionManager to call it async
exec_path = "src/mentask/agent/core/execution.py"
with open(exec_path, "r", encoding="utf-8") as f:
    exec_content = f.read()

# Create or update an init method that handles async trust
if "async def initialize(self)" not in exec_content:
    replacement = """    async def initialize(self) -> None:
        \"\"\"Asynchronously prepares the execution environment.\"\"\"
        await self.trust.load_trust()
        if self.lsp is None:
            await self.ensure_lsp_started()
"""
    # Insert before confirm_tool_call
    exec_content = exec_content.replace("    async def confirm_tool_call", replacement + "\n    async def confirm_tool_call")

with open(exec_path, "w", encoding="utf-8") as f:
    f.write(exec_content)
