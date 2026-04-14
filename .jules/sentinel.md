## 2024-04-04 - [CRITICAL] SSRF / Local File Read in web_fetch
**Vulnerability:** The `web_fetch` function in `src/askgem/tools/web_tools.py` directly uses `urllib.request.urlopen` with user-supplied URLs without validating the URL scheme.
**Learning:** `urllib.request.urlopen` implicitly supports multiple schemes, including `file://`. If an application does not restrict schemes to `http://` and `https://`, an attacker can retrieve arbitrary local system files (like `/etc/passwd`) via local file read / Server-Side Request Forgery (SSRF).
**Prevention:** Always validate and sanitize user-provided URLs before passing them to networking functions. Ensure URLs start with the expected protocol (e.g., `http://` or `https://`).

## 2026-04-14 - Path Traversal in Directory Listing
**Vulnerability:** os.listdir() returns paths without bounds checking and were directly appended to the path and used without verification, allowing an attacker to insert ../ patterns to step out of boundaries during operations like listing directory contents.
**Learning:** Whenever paths derived from potentially untrusted inputs or environment functions (like os.listdir, even on trusted directories if symlinks are involved) are used, they must be rigorously validated.
**Prevention:** Always pass constructed full paths through validation constraints like ensure_safe_path() before accessing them, even for simple read/listing tasks.
