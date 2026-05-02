## 2025-05-15 - Structured Statistics UI
**Learning:** Using `rich.table.Table` with brand-colored headers inside a `Panel` significantly improves the readability and "professional feel" of structured session data compared to raw multiline strings. It allows for better alignment of keys and values, especially when dealing with numeric metrics like token counts and costs.
**Action:** Default to `Table`-based layouts for any command output that presents multiple key-value pairs or structured metrics.
# 🎨 Palette's Journal - UX & Accessibility Learnings

## 2025-05-16 - Immediate Feedback for Invalid Commands
**Learning:** Returning `None` or failing silently when a user enters an invalid slash command in a CLI environment leads to confusion and a "broken" feel. Providing a localized error message with a hint for help (e.g., "Unknown command... type /help") improves user flow by immediately correcting their path.
**Action:** Always ensure the command dispatcher returns a descriptive error/hint for unrecognized inputs instead of silent failure.

## 2025-01-24 - Shortcut Discoverability in CLI
**Learning:** Custom keyboard shortcuts in CLI applications (like Ctrl+O for artifact expansion) are easily forgotten once the initial welcome screen scrolls out of view. Providing persistent hints in the primary help menu and contextually within relevant UI components (like Panels) ensures these powerful features remain accessible to users.
**Action:** Always include a "Shortcuts" footer or caption in the main help output and use Panel subtitles to reinforce shortcut availability during active interactions.

## 2025-05-17 - Fuzzy Slash Command Matching
**Learning:** Users often make typos when entering slash commands in a CLI (e.g., `/stat` instead of `/stats`). Providing immediate, fuzzy-matched suggestions (e.g., "Did you mean /stats?") reduces friction and prevents the frustration of "Unknown command" errors by guiding the user back to the correct path.
**Action:** Implement fuzzy matching (e.g., using `difflib`) for all interactive CLI command parsers to provide helpful suggestions on mismatch.
