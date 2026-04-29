## 2025-05-15 - Structured Statistics UI
**Learning:** Using `rich.table.Table` with brand-colored headers inside a `Panel` significantly improves the readability and "professional feel" of structured session data compared to raw multiline strings. It allows for better alignment of keys and values, especially when dealing with numeric metrics like token counts and costs.
**Action:** Default to `Table`-based layouts for any command output that presents multiple key-value pairs or structured metrics.
