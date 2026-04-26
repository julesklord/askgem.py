# Repository Standard

`mentask.py` is the current reference repository for hygiene, Git discipline, architecture boundaries, and release readiness across this workspace.

This document defines the minimum standard that other repositories should converge toward.

## 1. Repository Shape

Required structure:
- `src/` contains product code only.
- `tests/` contains automated tests only.
- `scratch/` contains probes, diagnostics, and disposable experiments.
- root contains packaging, policy, and core project documentation only.

Rules:
- No throwaway scripts in the repository root.
- No experimental probes under `tests/`.
- No stale UI, feature, or platform claims in docs once behavior changes.

## 2. Git Hygiene

Minimum expectations:
- default branch is clear and tracked correctly.
- local branches should not drift far from remote without intent.
- working tree should stay clean or have clearly intentional changes.
- `.gitignore` must block local artifacts, environments, caches, backups, and scratch output.

Rules:
- avoid long-lived unpushed branch divergence without a reason.
- do not keep broken ad hoc files at root just because pytest ignores them.
- keep remotes and upstreams explicit and predictable.

## 3. Versioning And Releases

Minimum expectations:
- project version in packaging metadata must match the documented current release state.
- changelog, roadmap, and README must not contradict runtime behavior.
- release automation should map cleanly to tags and published artifacts.

Rules:
- if Python support changes, update both metadata and docs in the same change.
- if a feature is removed, docs and tests must stop presenting it as active.
- if version numbers move, update all user-facing references in the same pass.

## 4. Architecture Standard

Design rules:
- orchestration logic should be decomposed into small internal helpers, not one giant control method.
- composition of dependencies should be explicit.
- runtime coordination should be separated from dependency construction.
- UI rendering, orchestration, session management, and tool execution should remain distinct layers.

Current reference patterns in this repo:
- `AgentOrchestrator` coordinates turns but delegates setup, tool execution, and LSP post-processing to helpers.
- `ChatAgent` coordinates session flow and rendering, but dependency composition is explicit through `ChatAgentDependencies`.

## 5. Test Standard

Minimum expectations:
- CLI entrypoints have contract tests.
- orchestration flows have focused unit tests.
- fragile external integrations should be isolated from unit tests when possible.
- deterministic or mocked tests are preferred for CI reliability.

Rules:
- unit tests should not boot heavyweight external processes unless the test is explicitly an integration test.
- runtime probes belong in `scratch/`, not in `tests/`.
- when behavior changes, update tests immediately instead of tolerating stale coverage.

Recommended verification baseline:
- `pytest tests/cli -q`
- `pytest tests/test_orchestrator.py tests/test_lsp_integration.py -q`
- targeted agent tests for changed surfaces

## 6. Documentation Standard

Minimum expectations:
- `README.md` describes current behavior, not historical behavior.
- technical wiki pages must reflect the actual architecture.
- roadmap should describe current stabilization priorities honestly.

Rules:
- remove or mark deprecated features explicitly.
- avoid marketing language that conflicts with runtime reality.
- keep public install/runtime requirements aligned with `pyproject.toml`.

## 7. CI Standard

Minimum expectations:
- linting runs in CI.
- automated tests run in CI.
- release workflows exist only for actually supported release paths.

Rules:
- CI should validate the repo as it is today, not as it used to be.
- if a workflow tests an interface that no longer exists, fix the workflow or the tests immediately.

## 8. Change Discipline

When touching a critical path:
- update code
- update tests
- update docs
- verify the changed surface

This is the standard that made `mentask.py` stronger during the current cleanup. Other repositories should be evaluated against these same criteria.

## 9. Adoption Checklist For Other Repositories

Use this sequence when normalizing another repo:
1. Align runtime, tests, and docs.
2. Remove scratch artifacts from root and `tests/`.
3. Fix version/documentation contradictions.
4. Refactor oversized control paths into internal helpers.
5. Introduce explicit dependency composition where construction is too implicit.
6. Tighten CI around the current real surface area.

## 10. Non-Goals

This standard does not require:
- overengineering
- a dependency injection framework
- maximal abstraction
- perfect coverage

It does require:
- coherence
- test honesty
- repo cleanliness
- explicit architecture boundaries
- release/documentation discipline
