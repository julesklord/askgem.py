## 2024-04-04 - [CRITICAL] SSRF / Local File Read in web_fetch
**Vulnerability:** The `web_fetch` function in `src/askgem/tools/web_tools.py` directly uses `urllib.request.urlopen` with user-supplied URLs without validating the URL scheme.
**Learning:** `urllib.request.urlopen` implicitly supports multiple schemes, including `file://`. If an application does not restrict schemes to `http://` and `https://`, an attacker can retrieve arbitrary local system files (like `/etc/passwd`) via local file read / Server-Side Request Forgery (SSRF).
**Prevention:** Always validate and sanitize user-provided URLs before passing them to networking functions. Ensure URLs start with the expected protocol (e.g., `http://` or `https://`).

## 2026-04-14 - Plaintext Storage of Search API Key on Keyring Failure
**Vulnerability:** In `src/askgem/core/config_manager.py`, the `save_settings` method failed to remove sensitive API keys from the configuration dictionary if storing them in the system keyring encountered an exception. This resulted in the plaintext key being persisted to the `settings.json` file.
**Learning:** When handling sensitive data that is intended for secure storage (like a keyring), always implement a fail-safe mechanism to ensure that the data is not leaked to less secure channels (like plaintext config files) if the primary secure storage method fails.
**Prevention:** Explicitly clear sensitive keys from any objects destined for plaintext persistence within `except` blocks when attempting to move them to secure storage.
## 2024-04-14 - Path Traversal Vulnerability in Session Loading and Deletion
**Vulnerability:** Path Traversal
**Learning:** `os.path.join` does not inherently prevent path traversal if the injected path contains absolute path structures or traversal elements (`../`). Using user input directly as a filename without bounds checking allows arbitrary file read and delete operations outside the target directory.
**Prevention:** Always combine `os.path.abspath` on both the target file path and the base directory. Then, validate the path remains within the intended boundary using `os.path.commonpath([base_dir, resolved_target_path]) == base_dir`.
