with open('tests/cli/test_dashboard_smoke.py', 'r') as f:
    content = f.read()

content = content.replace('AskGem v0.9.0', 'AskGem v0.10.0')

with open('tests/cli/test_dashboard_smoke.py', 'w') as f:
    f.write(content)
