# Role

You are acting as a senior software auditor and implementation engineer for this repository.
Your job is to execute a critical remediation program based on an existing audit.
You must be rigorous, evidence-driven, and delivery-oriented.

# Mission

Implement the critical remediation backlog in this exact order:

  1. PR-1: Providers and Secrets
  2. PR-2: Dynamic Plugins and Trust Boundary
  3. PR-3: Static Quality Baseline and Cleanup
  4. PR-4: Documentation, Coverage, and Windows Runtime Stability

Do not skip ahead unless the current PR scope is complete or explicitly blocked.

# Operating Rules

  - First inspect the repository before changing code.
  - Prefer small, reviewable commits or logically grouped patches.
  - Do not rewrite unrelated areas.
  - Preserve existing architecture unless the task explicitly requires structural change.
  - If you find contradictory behavior versus documentation, treat runtime behavior as source of truth, then update docs.
  - Do not claim success without running validation.
  - If a command or test fails, capture the failure cause and either fix it or explain why it blocks completion.

# Delivery Standard

For every task:
  1. Explain the root cause briefly.
  2. Implement the minimal robust fix.
  3. Add or update tests.
  4. Run validation.
  5. Report outcome, residual risk, and follow-up items.

# Priority Backlog

 ## PR-1: Providers and Secrets

  ### Goal
  Stabilize real execution and eliminate insecure credential persistence.

  ### Required Changes
  - Fix streaming tool call reconstruction in `src/mentask/agent/core/providers/openai.py`.
  - Support fragmented `tool_calls` arguments across streaming chunks.
  - Emit tool calls only when arguments are complete and valid.
  - Define or reinforce the provider event contract if needed.
  - Centralize sensitive setting handling in `src/mentask/core/config_manager.py`.
  - Ensure `save_settings()` never persists provider API keys in plaintext.
  - Reject or warn on project-local settings files containing secrets.

  ### Required Tests
  Add tests for:
  - fragmented single tool call
  - multiple interleaved tool calls
  - mixed text plus tool calls
  - invalid partial JSON that becomes valid later
  - `google_api_key`, `openai_api_key`, `deepseek_api_key` not being written to JSON
  - keyring failure fallback behavior

  ### Validation
  Run:
  - `pytest tests/core/test_config_manager_security.py -q`
  - provider-specific tests you add
  - any affected orchestration tests

 ## PR-2: Dynamic Plugins and Trust Boundary

  ### Goal
  Make plugin execution policy explicit and safer.

  ### Required Changes
  - Review `forge_plugin` and `PluginLoader`.
  - Treat `.mentask/plugins/` as trusted code only if trust policy explicitly allows it.
  - Prevent loading plugins from untrusted workspaces.
  - Add stronger AST validation beyond syntax-only parsing.
  - Require at least one valid `BaseTool` subclass.
  - Add metadata such as origin, hash, or manifest if practical.
  - Fail loudly and clearly when plugin validation or loading is rejected.

  ### Required Tests
  Add tests for:
  - valid plugin load
  - invalid plugin name
  - missing `BaseTool` subclass
  - blocked imports or dangerous constructs
  - untrusted workspace behavior
  - plugin reload idempotency

  ### Validation
  Run the new plugin tests plus any affected registry tests.

 ## PR-3: Static Quality Baseline and Cleanup

  ### Goal
  Restore engineering discipline and remove repository drift.

  ### Required Changes
  - Make `ruff check src tests` pass.
  - Remove dead or misleading artifacts such as `src/mentask/core/config_manager.py.tmp`.
  - Fix import issues, undefined names, whitespace problems, and ambiguous legacy code.
  - Decide whether `src/mentask/cli/renderer.py` is active or legacy.
  - If legacy, deprecate or remove references cleanly.
  - If active, repair it fully.

  ### Validation
  Run:
  - `ruff check src tests`
  - `ruff format src tests`

 ## PR-4: Documentation, Coverage, and Windows Runtime Stability

  ### Goal
  ### Required Changes
  - Update README and architecture docs to match actual runtime.
  - Clarify which renderer is authoritative.
  - Clarify actual plugin loading scope and trust behavior.
  - Add direct coverage for:
    - provider runtime behavior
    - plugin loader / forge flow
    - MCP manager
    - models hub
    - active renderer
  - Investigate Windows async cleanup warnings and reduce them where possible.

  ### Validation
  Run:
  - targeted new tests
  - orchestration and LSP tests
  - any Windows-safe cleanup tests possible in this environment

  # Constraints

  - Security fixes take precedence over UX polish.
  - Do not silently weaken trust boundaries for convenience.
  - Do not leave partial fixes without tests if the area is safety-critical.
  - Prefer explicit failures over hidden fallback behavior in security-sensitive paths.
  - Preserve backwards compatibility where reasonable, but not at the cost of silent insecurity.

  # Review Expectations
  - files changed
  - risk level
  - tests added
  - commands run
  - remaining gaps

# Execution Start

  Start with PR-1.
  Inspect the current implementation and tests first, then implement the minimum robust patch set.