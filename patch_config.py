import re

with open('tests/core/test_config_manager.py', 'r') as f:
    content = f.read()

content = content.replace('gemini-2.0-flash', 'gemini-2.5-flash')

with open('tests/core/test_config_manager.py', 'w') as f:
    f.write(content)

with open('src/askgem/core/config_manager.py', 'r') as f:
    content2 = f.read()

content2 = content2.replace('gemini-2.0-flash', 'gemini-2.5-flash')

with open('src/askgem/core/config_manager.py', 'w') as f:
    f.write(content2)
