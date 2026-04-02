# Changelog

All changes to the underlying AskGem structure are documented here and track standard SemVer.

For the latest structural changes resolving legacy architecture scaling, reference the primary [CHANGES.md](../CHANGES.md) at the repository root.

## Recent Major Updates: v2.0 (Structural Reorganization)

* **Phase Extraction**: Separated pure UI operations (`cli/`) from Cognitive Operations (`agent/`).
* **Safety Context**: Resolved circular paths inside state configs by creating root-level explicit map targets (`core/paths.py`).
* **Code Transparency**: Added boundary condition enforcement DocStrings across all python logic targets.
* **Technical Debt Documented**: Added inline refactor flags targeting overgrown generation aggregation payload scopes.
