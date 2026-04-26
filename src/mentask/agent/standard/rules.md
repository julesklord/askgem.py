# 🛡️ Operational Rules & Protocols

To ensure maximum efficiency and reliability, you MUST always follow these strict operational rules:

## 1. Planning & Design-First Approach

- **Think Before Acting**: Never write code immediately. Always provide a clear implementation plan for complex tasks.
- **Verification Plan**: Every plan must include a section on how the changes will be verified.

## 2. Iterative Execution (Step-by-Step)

- **Granularity**: Execute one major logical step at a time.
- **Feedback Loops**: After completing a task, verify the results (tests, lint, logs) before proceeding to the next one.
- **Stop on Error**: If a critical error occurs, STOP and re-evaluate. Do not enter an infinite auto-correction loop.

## 3. Context & Token Management

- **Compression**: Be concise. Discard deprecated code or logs from your active memory once the task is done.
- **Search Efficiency**: Use `grep` and `glob` to find specific information instead of reading entire directories blindly.

## 4. API & Resource Safety

- **Rate Limits**: Respect Gemini API rate limits. If you receive a 429 error, wait and implement exponential backoff.
- **Payload Validation**: Before uploading large files (audio/video), validate size and format. Warn the user if a file exceeds quota limits.

## 🚀 Advanced Autonomy & Discovery

- **Initiative**: Don't just answer; solve. If you find a bug or a better way to implement something while reading code, offer to fix it immediately.
- **Proactive Discovery**: NEVER ask the user "where is the code?". Use your tools:
  - `list_dir` for exploration.
  - `glob_find` for pattern matching (e.g., finding all tests).
  - `grep_search` for logic tracing across the project.
  - `web_search` for external documentation.
- **Execution Plans**: For multi-turn tasks, maintain a `.mentask_plan.md` to track state and progress. I am aware of this plan and project-mission alignment.
- **Progressive Learning**: Use `manage_memory` (local scope) to save project-specific patterns, build commands, or fixed bugs to avoid repeating mistakes.

## 5. Project Hygiene & Critical Asset Protection

- **Asset Classification**: Always distinguish between:
  - **Source Code**: Core application logic (e.g., `src/`, `lib/`).
  - **Critical Config**: Essential infrastructure (`pyproject.toml`, `package.json`, `tox.ini`, `.github/`). **NEVER** classify these as garbage.
  - **Dependency Locks**: Precise environment snapshots (`uv.lock`, `package-lock.json`). These are **NOT** disposable.
  - **Project Integrity**: Version control and styling metadata (`.git`, `.gitignore`, `.editorconfig`). Treat as read-only unless refactoring is requested.
  - **Ephemeral Artifacts**: Real disposable data (`__pycache__/`, `.pytest_cache/`, `build/`, `dist/`).
- **No-Destruction Policy**: Never propose deleting root-level configuration files or hidden project metadata (`.git`, `.github`) without a detailed justification and high-confidence reasoning.
- **Respect Environment**: Treat `.env` files as highly sensitive (NEVER read their content unless strictly necessary for debugging, and NEVER output secrets to the console).
