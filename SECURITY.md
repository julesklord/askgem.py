# Security Policy: AskGem

This document outlines the security protocols, vulnerability reporting procedures, and the established trust model for **AskGem v0.16.0**. As an autonomous agent capable of executing code and shell commands, security and integrity are central to our architectural design.

## Technical Safeguards

AskGem implements a multi-layer defense strategy to mitigate risks associated with autonomous execution:

1. **TrustManager (Filesystem Boundaries)**: AskGem utilizes a centralized trust model. Tools with write or execute capabilities are restricted to directories explicitly authorized in the `trusted.json` configuration file. Any attempt to modify files or execute scripts outside of these "trusted zones" triggers an immediate security alert and requires explicit overhead authorization.
2. **Native Credential Management**: Sensitive API credentials (e.g., Gemini API keys) are never stored in plaintext within the repository or local configuration files. AskGem integrates with the system-native credential store via the `keyring` module, ensuring secrets are handled by the operating system's established security primitives.
3. **Human-in-the-Loop Orchestration**: By default, the agent operates in `manual` mode. This ensures that every high-impact tool invocation—such as permanent file writes or terminal commands—requires secondary confirmation from the user.
4. **Input & Path Sanitization**: The core engine performs proactive validation of all filesystem paths to prevent directory traversal attacks (dot-dot-slash) and ensures that tool arguments conform to expected Pydantic schemas before execution.

## Inherent Risk Assessment

Users should be aware of the specific risks associated with LLM-based autonomous agents:

- **Prompt Injection**: LLMs may be susceptible to instructions embedded in untrusted data. AskGem may inadvertently attempt to execute unauthorized actions if it processes malicious content from local files or web assets.
- **Execution Side Effects**: Given its ability to modify the local environment, it is highly recommended to run AskGem within isolated development environments, containers, or version-controlled repositories (e.g., Git) to facilitate recovery from unintended state changes.

## Supported Versions

We currently provide security updates and patches for the following versions:

| Version | Status | Security Support |
| ------- | ------ | ---------------- |
| v0.16.x | Stable | Active Support   |
| < v0.16 | Legacy | No Support       |

## Reporting a Vulnerability

If you identify a critical security vulnerability, **do not open a public Issue**. Public disclosure of vulnerabilities prior to a patch endangers the user base.

1. Submit a report through [GitHub Security Advisories](https://github.com/julesklord/askgem.py/security/advisories/new) (if enabled) or send a detailed report to your designated security contact email.
2. Include a proof-of-concept (PoC) or clear steps to reproduce the issue.
3. We commit to acknowledging and responding to your report within 48 business hours.

---

*Security is a shared responsibility. Ensure your execution environments are isolated and project permissions are strictly limited.*
