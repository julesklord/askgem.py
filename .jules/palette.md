## 2025-05-15 - Structured Statistics UI
**Learning:** Using `rich.table.Table` with brand-colored headers inside a `Panel` significantly improves the readability and "professional feel" of structured session data compared to raw multiline strings. It allows for better alignment of keys and values, especially when dealing with numeric metrics like token counts and costs.
**Action:** Default to `Table`-based layouts for any command output that presents multiple key-value pairs or structured metrics.
# 🎨 Palette's Journal - UX & Accessibility Learnings

## 2025-01-24 - Shortcut Discoverability in CLI
**Learning:** Custom keyboard shortcuts in CLI applications (like Ctrl+O for artifact expansion) are easily forgotten once the initial welcome screen scrolls out of view. Providing persistent hints in the primary help menu and contextually within relevant UI components (like Panels) ensures these powerful features remain accessible to users.
**Action:** Always include a "Shortcuts" footer or caption in the main help output and use Panel subtitles to reinforce shortcut availability during active interactions.
