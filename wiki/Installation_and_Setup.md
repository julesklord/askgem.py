# Installation & Setup

## Prerequisites

* **Python:** 3.8 to 3.13 Supported.
* **System Deps:** Access to standard OS commands (bash on UNIX, powershell on Windows) to populate agent utilities.

## Installation Steps

Local development package link:

```bash
python -m venv venv
source venv/bin/activate
pip install -e "."
```

## Configuration Reference

Upon launching `askgem`, user profile folders generate under `~/.askgem/`.

### Config Schema (`~/.askgem/settings.json`)

| Key | Type | Default | Description | Breaks if wrong |
|---|---|---|---|---|
| `model_name` | `str` | `gemini-2.5-pro` | LLM bound to session. | Triggers execution error if string does not map to Gemini SDK endpoint. |
| `edit_mode` | `str` | `manual` | Safety execution mode. Takes `auto` or `manual`. | Reverts to string mismatches natively. |

### Environment Variables

| Variable | Type | Description |
|---|---|---|
| `GOOGLE_API_KEY` | `str` | Authorized token. Suppresses the UI request prompt at boot. |
| `LANG` / `LC_ALL` | `str` | ISO key code like `en` or `es`. Enforces translated text modes instead of Auto-Detect. |
