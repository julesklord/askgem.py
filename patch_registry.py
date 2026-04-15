import re

with open('tests/test_tools_registry.py', 'r') as f:
    content = f.read()

content = content.replace('with patch("askgem.agent.tools_registry.is_command_safe", return_value=False):', 'with patch("askgem.agent.tools_registry.analyze_command_safety") as mock_analyze:\n                import askgem.core.security\n                mock_analyze.return_value.level = askgem.core.security.SafetyLevel.DANGEROUS\n                mock_analyze.return_value.category = "mock"\n                mock_analyze.return_value.description = "mock"')

with open('tests/test_tools_registry.py', 'w') as f:
    f.write(content)
