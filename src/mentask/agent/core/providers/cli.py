import asyncio
import contextlib
import json
import logging
import re
import shlex
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from ....core.compression import ContextCompressor
from ....core.config_manager import SettingsProvider
from ...schema import Message, Role, ToolCall, UsageMetrics
from .base import BaseProvider

_logger = logging.getLogger("mentask.agent.providers.cli")

# Patterns to intercept in stderr (system warnings to beautify)
_SYSTEM_WARNING_PATTERNS = [
    r"Windows 10 detected",
    r"Windows 11 is recommended",
    r"Ripgrep is not available",
    r"Falling back to GrepTool",
    r"True color \(24-bit\) support not detected",
    r"256-color support not detected",
    r"DEP0190",  # Node.js deprecation warning for shell option
    r"Use `node --trace-deprecation",
]

# Patterns to completely ignore (too noisy)
_IGNORED_STDERR_PATTERNS = [
    r"Debugger listening on ws://",
    r"For help, see: https://nodejs.org/en/docs/inspector",
]


# Alias map: user-facing shorthand → list of candidate binary names (in priority order)
_CLI_ALIAS_MAP: dict[str, list[str]] = {
    "codex": ["codex"],
    "opencode": ["opencode"],
    "pi": ["pi"],
    "copilot": ["copilot", "gh-copilot"],
    "devin": ["devin"],
}


def _resolve_binary(name: str) -> str | None:
    """Resolves a CLI alias or binary name to its full path. Returns None if not found."""
    import shutil

    candidates = _CLI_ALIAS_MAP.get(name.lower(), [name])
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    return None


class CLIProvider(BaseProvider):
    """
    Provider that bridges MentAsk to external CLI agents (e.g., codex, opencode, copilot).
    It translates history and tools into a text prompt, runs the binary, and parses stdout.
    """

    def __init__(self, model_name: str, config: SettingsProvider):
        # Strip 'agent:' prefix if present
        pure_cmd = model_name.removeprefix("agent:")
        super().__init__(pure_cmd, config)

        # Parse 'binary:model_id' format: e.g. 'codex:gpt-4.1'
        # If there's a colon, split into CLI binary and the model to select
        if ":" in pure_cmd:
            parts = pure_cmd.split(":", 1)
            self.cli_command = parts[0]      # The binary to invoke (e.g. 'codex')
            self.cli_model: str | None = parts[1]        # The model to request (e.g. 'gemini-2.5-pro')
        else:
            self.cli_command = pure_cmd
            self.cli_model = None            # Use the binary's default model

        # Resolved binary path (set in setup())
        self._binary_path: str | None = None
        # Display name for renderer: 'bin/model' or 'bin'
        if self.cli_model:
            self.display_name = f"{self.cli_command}/{self.cli_model}"
        else:
            self.display_name = self.cli_command

    async def setup(self) -> bool:
        # If the command is a template string (contains spaces or {prompt}), extract the binary
        try:
            first_token = shlex.split(self.cli_command)[0]
        except (ValueError, IndexError):
            first_token = self.cli_command

        resolved = _resolve_binary(first_token)
        if resolved is None:
            _logger.error(
                f"CLI binary '{first_token}' not found in PATH. "
                f"Tried aliases: {_CLI_ALIAS_MAP.get(first_token.lower(), [first_token])}"
            )
            return False

        self._binary_path = resolved
        _logger.info(f"CLI Bridge: resolved '{first_token}' → '{resolved}'")
        return True

    def _build_prompt(
        self, history: list[Message], tools_schema: list[dict[str, Any]], config: Any | None = None
    ) -> str:
        system_instruction = (
            config.get("system_instruction", "")
            if isinstance(config, dict)
            else (getattr(config, "system_instruction", "") if config else "")
        )
        prompt_parts = []

        # 1. System Instruction & Tool Schema
        # We use a very prominent format to ensure the "Brain" CLI sees it
        prompt_parts.append("### MENTASK CORE PROTOCOL")
        prompt_parts.append(f"MISSION: {system_instruction}")

        if tools_schema:
            prompt_parts.append("\n### TOOLBOX & PROTOCOL")
            prompt_parts.append("You are the BRAIN. MentAsk is your BODY and your OPERATING SYSTEM.")
            prompt_parts.append("CRITICAL: You are a 'Headless' model. You have NO eyes, NO hands, and NO direct system access.")
            prompt_parts.append("Everything you see or do MUST go through MentAsk tools.")

            prompt_parts.append("\n### CAPABILITIES MAPPING")
            prompt_parts.append("- To see files/folders: Use 'list_dir' or 'glob_find'.")
            prompt_parts.append("- To read code: Use 'read_file' or 'grep_search'.")
            prompt_parts.append("- To change code: Use 'edit_file' or 'write_file'.")
            prompt_parts.append("- To run commands: Use 'execute_command' (Windows) or 'execute_bash' (Unix).")
            prompt_parts.append("- To search web: Use 'web_search'.")
            prompt_parts.append("- To remember things: Use 'working_memory' or 'memory'.")

            prompt_parts.append("\n### EXECUTION FORMAT")
            prompt_parts.append("To call a tool, you MUST output a single JSON block. DO NOT use your internal tool-calling syntax.")
            prompt_parts.append("FORMAT:")
            prompt_parts.append(
                '```json\n{\n  "mentask_tool_call": {\n    "name": "tool_name",\n    "arguments": {"arg": "val"}\n  }\n}\n```'
            )
            prompt_parts.append("\nRULES:")
            prompt_parts.append("1. ALWAYS explore with 'list_dir' before assuming a file's location.")
            prompt_parts.append("2. Use 'read_file' before editing to ensure context.")
            prompt_parts.append("3. You can only call ONE tool at a time.")
            prompt_parts.append("4. Use EXACT tool names from the schema below.")

            prompt_parts.append("\nAVAILABLE TOOLS (JSON Schema):")
            for tool in tools_schema:
                # Keep it compact to save CLI args space
                minimal_tool = {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                }
                prompt_parts.append(f"- {tool['name']}: {json.dumps(minimal_tool)}")

        prompt_parts.append("\n### CONVERSATION LOG")

        session_id = config.get("session_id") if isinstance(config, dict) else getattr(config, "session_id", None)
        is_first_turn = (
            config.get("is_first_turn", True) if isinstance(config, dict) else getattr(config, "is_first_turn", True)
        )

        # If the external CLI is maintaining state (resuming), we only send the latest message
        # Otherwise, send last 10 messages to avoid shell arg limits
        history_to_send = history[-1:] if (session_id and not is_first_turn) else history[-10:]

        for msg in history_to_send:
            if msg.role == Role.SYSTEM:
                continue

            role = "USER" if msg.role in (Role.USER, Role.TOOL) else "AGENT"
            content = ContextCompressor.smart_compress(str(msg.content))

            if msg.role == Role.TOOL:
                tool_name = msg.metadata.get("tool_name", "unknown")
                prompt_parts.append(f"[{role} - {tool_name} RESULT]: {content}")
            elif msg.role == Role.ASSISTANT:
                content = str(msg.content) if msg.content else ""
                # Force a thought block if missing to satisfy strict external CLI validators (like HistoryHardener)
                thought = getattr(msg, "thought", None) or "Analyzing the state and determining next steps..."
                content = f"<thought>\n{thought}\n</thought>\n\n{content}"
                prompt_parts.append(f"ASSISTANT: {content}")
            else:
                prompt_parts.append(f"[{role}]: {content}")

        prompt_parts.append("\n### YOUR RESPONSE (AGENT):")
        return "\n".join(prompt_parts)

    def _build_cli_args(self, full_prompt: str, config: Any | None = None) -> tuple[list[str], bool]:
        """
        Builds the argv list for the subprocess.
        Returns a tuple of (args, uses_stdin).
        """
        # Parse cli_command into its tokens (handles "python script.py" etc.)
        try:
            cmd_parts = shlex.split(self.cli_command)
        except (ValueError, IndexError):
            cmd_parts = [self.cli_command]

        binary = self._binary_path or cmd_parts[0]
        extra_args = cmd_parts[1:]
        binary_name = Path(binary).stem.lower()

        # Non-interactive / pipe-friendly flags per known CLI tool
        _NON_INTERACTIVE_FLAGS: dict[str, list[str]] = {
            "codex": ["exec", "--json"],
            "opencode": ["run", "--format", "json"],
            "pi": ["--non-interactive"],
            "copilot": ["--non-interactive"],
            "devin": ["--non-interactive"],
        }

        if "{prompt}" in self.cli_command:
            # User-defined template: replace {prompt} and split
            cmd_str = self.cli_command.replace("{prompt}", full_prompt)
            parts = shlex.split(cmd_str)
            parts[0] = binary
            return parts, False

        flags = _NON_INTERACTIVE_FLAGS.get(binary_name, [])

        # Generic CLI: apply model flag from descriptor if known
        from ....core.model_discovery import get_model_flag
        model_flag = get_model_flag(binary_name)
        args = [binary, *extra_args]
        if self.cli_model and model_flag:
            args.extend([model_flag, self.cli_model])
        args.extend(flags)
        args.append(full_prompt)
        return args, False

    async def generate_stream(
        self,
        history: list[Message],
        tools_schema: list[dict[str, Any]],
        config: Any | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:

        full_prompt = self._build_prompt(history, tools_schema, config)
        args, use_stdin = self._build_cli_args(full_prompt, config)

        _logger.debug(f"Invoking CLI Bridge: {args[0]} (prompt len: {len(full_prompt)}, stdin: {use_stdin})")

        # Emit thinking status to trigger UI spinner
        from ...schema import AgentTurnStatus

        yield {"status": AgentTurnStatus.THINKING}

        has_resume = "--resume" in args
        should_retry = False

        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE if use_stdin else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            if has_resume:
                try:
                    await asyncio.wait_for(process.wait(), timeout=0.25)
                    if process.returncode == 42:
                        should_retry = True
                        _logger.info("CLI Bridge: session resume failed with code 42. Falling back to starting a new session.")
                except asyncio.TimeoutError:
                    # Process is still running, no early exit
                    pass

            if should_retry:
                # Re-build prompt and args forcing a new session
                new_config = {}
                if isinstance(config, dict):
                    new_config = config.copy()
                elif config is not None:
                    new_config = {k: getattr(config, k) for k in dir(config) if not k.startswith("_")}

                new_config["is_first_turn"] = True

                full_prompt = self._build_prompt(history, tools_schema, new_config)
                args, use_stdin = self._build_cli_args(full_prompt, new_config)

                _logger.info(f"Retrying CLI Bridge with new session arguments: {args}")

                process = await asyncio.create_subprocess_exec(
                    *args,
                    stdin=asyncio.subprocess.PIPE if use_stdin else None,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            if use_stdin and process.stdin:
                process.stdin.write(full_prompt.encode("utf-8"))
                await process.stdin.drain()
                process.stdin.close()

            if process.stdout is None or process.stderr is None:
                raise RuntimeError("Failed to open process pipes")

            json_buffer = ""
            in_json_block = False
            actual_metrics = None

            async def read_stream(stream, is_stderr=False):
                nonlocal in_json_block, json_buffer, actual_metrics

                async def process_text_line(line):
                    nonlocal in_json_block, json_buffer
                    # Logic to detect JSON blocks even if mixed with text
                    if "```json" in line:
                        in_json_block = True
                        json_buffer = ""
                        pre = line.split("```json")[0]
                        if pre.strip():
                            yield {"type": "text", "content": pre}
                        return

                    if in_json_block:
                        if "```" in line:
                            in_json_block = False
                            post = line.split("```")[1]
                            try:
                                clean_json = json_buffer.strip()
                                parsed = json.loads(clean_json)
                                if "mentask_tool_call" in parsed:
                                    tc_data = parsed["mentask_tool_call"]
                                    yield {
                                        "type": "tool_call",
                                        "content": ToolCall(
                                            id=str(uuid.uuid4()),
                                            name=tc_data.get("name", ""),
                                            arguments=tc_data.get("arguments", {}),
                                        ),
                                    }
                                else:
                                    yield {"type": "text", "content": "```json\n" + json_buffer + "\n```"}
                            except (json.JSONDecodeError, KeyError):
                                yield {"type": "text", "content": "```json\n" + json_buffer + "\n```"}

                            if post.strip():
                                yield {"type": "text", "content": post}
                        else:
                            json_buffer += line
                    else:
                        yield {"type": "text", "content": line}

                while True:
                    line_bytes = await stream.readline()
                    if not line_bytes:
                        break

                    try:
                        line = line_bytes.decode("utf-8", errors="replace")
                    except Exception:
                        line = str(line_bytes)

                    if is_stderr:
                        # 1. Intercept system warnings to beautify them
                        if any(re.search(p, line) for p in _SYSTEM_WARNING_PATTERNS):
                            clean_msg = line.replace("Warning:", "").strip()
                            # Strip common prefixes from the external CLI if present
                            clean_msg = clean_msg.removeprefix("[stderr]").strip()
                            yield {"type": "info", "content": f"󰀦 {clean_msg}"}
                            continue

                        # 2. Filter out completely ignored patterns
                        if any(re.search(p, line) for p in _IGNORED_STDERR_PATTERNS):
                            continue

                        # 3. Yield other stderr as text
                        if line.strip():
                            yield {"type": "text", "content": f"[dim][stderr] {line.strip()}[/dim]"}
                        continue

                    # Handle JSONL events (from modern CLI providers)
                    # A line might contain text before or after the JSONL event due to stdout buffering.
                    # We extract all text segments and valid JSON components.
                    parts = []
                    if "{\"type\":" in line:
                        current_pos = 0
                        while True:
                            idx = line.find("{\"type\":", current_pos)
                            if idx == -1:
                                rem = line[current_pos:]
                                if rem:
                                    parts.append((rem, None))
                                break

                            pre = line[current_pos:idx]
                            if pre:
                                parts.append((pre, None))

                            candidate = line[idx:]
                            try:
                                parsed = json.loads(candidate.strip())
                                parts.append(("", parsed))
                                break
                            except (json.JSONDecodeError, ValueError):
                                parsed_ok = False
                                for i in range(len(candidate), idx, -1):
                                    sub_cand = candidate[:i-idx]
                                    try:
                                        parsed = json.loads(sub_cand.strip())
                                        parts.append(("", parsed))
                                        current_pos = i
                                        parsed_ok = True
                                        break
                                    except (json.JSONDecodeError, ValueError):  # nosec B112
                                        continue

                                if not parsed_ok:
                                    parts.append((line[idx:idx+8], None))
                                    current_pos = idx + 8
                    else:
                        parts = [(line, None)]

                    for text_segment, event in parts:
                        if text_segment:
                            async for parsed_event in process_text_line(text_segment):
                                yield parsed_event
                            continue

                        if event is not None:
                            try:
                                event_type = event.get("type")

                                # 1. Parse assistant text chunks
                                text_to_process = None
                                if event_type == "item.completed":  # Codex
                                    item = event.get("item", {})
                                    if item.get("type") == "agent_message":
                                        text_to_process = item.get("text", "")
                                elif event_type == "text":  # OpenCode
                                    part = event.get("part", {})
                                    text_to_process = part.get("text", "")
                                elif event_type == "message":  # Gemini
                                    if event.get("role") == "assistant":
                                        text_to_process = event.get("content", "")

                                if text_to_process is not None:
                                    for text_line in text_to_process.splitlines(keepends=True):
                                        async for parsed_event in process_text_line(text_line):
                                            yield parsed_event
                                    continue

                                # 2. Parse token usage metrics
                                input_tokens, output_tokens = None, None
                                if event_type == "turn.completed":  # Codex
                                    usage = event.get("usage", {})
                                    input_tokens = usage.get("input_tokens")
                                    output_tokens = usage.get("output_tokens")
                                elif event_type == "step_finish":  # OpenCode
                                    tokens = event.get("tokens", {})
                                    input_tokens = tokens.get("input")
                                    output_tokens = tokens.get("output")
                                elif event_type == "result":  # Gemini
                                    stats = event.get("stats", {})
                                    input_tokens = stats.get("input_tokens")
                                    output_tokens = stats.get("output_tokens")

                                if input_tokens is not None or output_tokens is not None:
                                    actual_metrics = UsageMetrics(
                                        input_tokens=input_tokens or 0,
                                        output_tokens=output_tokens or 0,
                                    )
                                    continue

                                # 3. Skip other lifecycle events to prevent visual noise
                                if event_type in (
                                    "thread.started", "turn.started",  # Codex
                                    "step_start", "step-start",  # OpenCode
                                    "init", "message", "result", "tool_use", "tool_result",  # Gemini
                                ):
                                    continue
                            except Exception as e:
                                _logger.debug(f"CLI stream parsing failed: {e}")

            async def stream_merger():
                queue = asyncio.Queue()

                async def producer(generator):
                    try:
                        async for item in generator:
                            await queue.put(item)
                    except Exception as e:
                        _logger.error(f"Producer error: {e}")

                tasks = [
                    asyncio.create_task(producer(read_stream(process.stdout, is_stderr=False))),
                    asyncio.create_task(producer(read_stream(process.stderr, is_stderr=True))),
                ]

                while True:
                    if all(t.done() for t in tasks) and queue.empty():
                        break

                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=0.05)
                        yield item
                    except asyncio.TimeoutError:
                        continue

            async def stream_merger_wrapper():
                async for event in stream_merger():
                    yield event

            async for event in stream_merger_wrapper():
                yield event

            try:
                await asyncio.wait_for(process.wait(), timeout=30)
            except asyncio.TimeoutError:
                _logger.warning("CLI Bridge process did not exit within 30s after streaming ended, killing it")
                with contextlib.suppress(Exception):
                    process.kill()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    _logger.error("CLI Bridge process still alive after kill, giving up")

            if process.returncode != 0:
                _logger.warning(f"CLI Bridge process exited with code {process.returncode}")

            # Flush json_buffer if we died mid-block
            if in_json_block and json_buffer:
                yield {"type": "text", "content": "```json\n" + json_buffer + "\n```"}

            # Emit actual or dummy metrics
            if actual_metrics:
                yield {"type": "metrics", "content": actual_metrics}
            else:
                yield {"type": "metrics", "content": UsageMetrics(input_tokens=len(full_prompt) // 4, output_tokens=0)}

        except Exception as e:
            _logger.error(f"CLI Bridge failure ({self.cli_command}): {e}")
            yield {"type": "error", "content": f"CLI Bridge Error: {e}"}

    async def list_models(self) -> list[str]:
        # Return the resolved binary path if available, else the original command
        name = self._binary_path or self.cli_command
        return [name]

    async def check_health(self, model_name: str) -> tuple[bool, str | None]:
        # model_name here is the user alias, not necessarily a binary name
        alias = model_name.removeprefix("agent:")
        try:
            first_token = shlex.split(alias)[0]
        except (ValueError, IndexError):
            first_token = alias

        path = _resolve_binary(first_token)
        if path is not None:
            return True, None
        return False, f"Binary not found in PATH (tried: {_CLI_ALIAS_MAP.get(first_token.lower(), [first_token])})"

    @property
    def key_source(self) -> str:
        return "local binary"
