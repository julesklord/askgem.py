## 2024-04-04 - [CRITICAL] SSRF / Local File Read in web_fetch
**Vulnerability:** The `web_fetch` function in `src/askgem/tools/web_tools.py` directly uses `urllib.request.urlopen` with user-supplied URLs without validating the URL scheme.
**Learning:** `urllib.request.urlopen` implicitly supports multiple schemes, including `file://`. If an application does not restrict schemes to `http://` and `https://`, an attacker can retrieve arbitrary local system files (like `/etc/passwd`) via local file read / Server-Side Request Forgery (SSRF).
**Prevention:** Always validate and sanitize user-provided URLs before passing them to networking functions. Ensure URLs start with the expected protocol (e.g., `http://` or `https://`).
