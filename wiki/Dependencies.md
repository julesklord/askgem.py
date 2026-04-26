# Dependencies

`mentask` forces an extremely strict minimal dependency tree.

### Core Requirements (`>= 3.10`)

| Package | Version Pinned | Purpose | License | Replaceable? |
|---|---|---|---|---|
| `google-genai` | `>=0.2.0` | Powers the fundamental API transaction protocols and generative model context. | Apache-2.0 | No. Direct platform wrapper. |
| `rich` | `>=13.0.0` | Handles low-level console formatting, Markdown rendering, and styled tables. | MIT | Highly difficult. |
| `keyring` | `>=25.0.0` | **[v0.10.0]** Secure OS-level storage for API keys. | MIT | Recommended for security standards. |

*No heavy ORMs, web frameworks, or arbitrary third-party utility loaders exist in the core footprint.*

### Development Tools (`dev`)

* `pytest` (>= 8.0.0) : Assert-driven test suite executions.
* `ruff` (>= 0.4.0) : Fastest-in-class Rust-based python linter.
* `build` / `twine` : PyPI standards distribution building mapping points.
* `tox` (>= 4.0.0) : Multi-version runtime simulation mapping.
