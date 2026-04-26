# Installation & Setup

## Prerequisites

* **Python:** 3.8 to 3.14 Supported.
* **API Key:** Required from [Google AI Studio](https://aistudio.google.com/).
* **System Deps:** Access to standard OS commands (bash on UNIX, pwsh on Windows) to populate agent utilities.

## Installation Steps

Recommended local development linkage:

```bash
git clone https://github.com/julesklord/mentask
cd mentask.py
python -m venv venv
# On Windows: venv\Scripts\activate
source venv/bin/activate
pip install -e ".[dev]"
```

## Configuration Reference

Upon launching `mentask`, user profile folders generate under `~/.mentask/` (POSIX) or `%APPDATA%/mentask/` (Windows).

### Config Schema (`settings.json`)

| Key | Type | Default | Description | Breaks if wrong |
|---|---|---|---|---|
| `model_name` | `str` | `gemini-1.5-flash` | LLM bound to session. | Triggers execution error if string does not map to Gemini SDK endpoint. |
| `edit_mode` | `str` | `manual` | Safety execution mode. Takes `auto` or `manual`. | Reverts to string mismatches natively. |

### Auth Persistence [v0.10.0]

mentask utilizes the `keyring` library to securely store credentials in the OS vault (Windows Credential Manager / macOS Keychain).

### Environment Variables

| Variable | Type | Description |
|---|---|---|
| `GEMINI_API_KEY` | `str` | Authorized token. Suppresses the UI request prompt at boot. |
| `LANG` / `LC_ALL` | `str` | ISO key code like `en` or `es`. Enforces translated text modes instead of Auto-Detect. |
