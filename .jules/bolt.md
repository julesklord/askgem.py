## 2024-04-06 - Path.rglob Performance Bottleneck
**Learning:** `Path.rglob("*")` is a massive performance bottleneck for directory traversal when large directories (like `node_modules` or `.git`) need to be excluded. It generates paths for every file before exclusion can happen.
**Action:** Always use `os.walk()` with in-place directory pruning (`dirs[:] = [d for d in dirs if d not in exclude_dirs]`) to avoid traversing excluded directories entirely. Use `Path.match()` on the yielded files for pattern matching instead of relying on `rglob`.
