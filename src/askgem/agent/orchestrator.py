import asyncio
from collections.abc import AsyncGenerator, Callable
from typing import Any

from ..core.trust_manager import TrustManager
from .schema import AgentTurnStatus, AssistantMessage, Message, Role, ToolResult
from .tools.base import ToolRegistry
from .core.lsp_client import LSPClient


class AgentOrchestrator:
    """
    Core reasoning loop for AskGem.
    Manages the Thinking -> Action -> Observation cycle.
    """

    def __init__(self, client, tool_registry: ToolRegistry, config: Any = None):
        self.client = client
        self.tools = tool_registry
        self.config = config
        self.active_status = AgentTurnStatus.IDLE
        self.trust = TrustManager()
        self.lsp: Optional[LSPClient] = None

    async def run_query(self, user_prompt: str | Any, history: list[Message], config: Any | None = None, confirmation_callback: Callable | None = None) -> AsyncGenerator[Any, None]:
        """
        Runs the agentic loop. Yields events for the UI.
        """
        # 1. Preparar Turno
        history.append(Message(role=Role.USER, content=user_prompt))
        self.active_status = AgentTurnStatus.THINKING

        while True:
            # Iniciar LSP si no está activo
            if self.lsp is None:
                self.lsp = LSPClient(workspace_path=".")
                await self.lsp.start()

            yield {"status": AgentTurnStatus.THINKING}

            # 2. Llamada al LLM
            try:
                # [Plan Injection Logic - Keeping it clean]
                import os
                plan_file = ".askgem_plan.md"
                plan_context = ""
                if os.path.exists(plan_file):
                    try:
                        with open(plan_file, encoding="utf-8") as f:
                            raw_plan = f.read().strip()
                            if raw_plan:
                                plan_context = (
                                    f"\n\n## ACTIVE EXECUTION PLAN (from {plan_file}):\n"
                                    "You are currently executing the following multi-turn plan. "
                                    "Reference this to maintain state and know your next steps:\n"
                                    f"```markdown\n{raw_plan}\n```"
                                )
                    except Exception:
                        pass

                turn_config = config
                if plan_context and hasattr(turn_config, "system_instruction"):
                    from copy import copy
                    turn_config = copy(config)
                    # Support both string and dynamic system_instruction
                    instr = turn_config.system_instruction or ""
                    turn_config.system_instruction = f"{instr}{plan_context}"

                # Pre-calculate full message structure to populate as stream arrives
                assistant_msg = AssistantMessage(
                    content="", thought=None, tool_calls=[], model=self.client.model_name
                )
                history.append(assistant_msg)

                async for chunk in self.client.generate_stream(history[:-1], self.tools.get_all_schemas(), config=turn_config):
                    c_type = chunk["type"]
                    c_val = chunk["content"]

                    if c_type == "text":
                        assistant_msg.content += c_val
                        yield {"type": "text", "content": c_val}
                    elif c_type == "thought":
                        assistant_msg.thought = c_val
                        yield {"type": "thought", "content": c_val}
                    elif c_type == "tool_call":
                        assistant_msg.tool_calls.append(c_val)
                    elif c_type == "metrics":
                        assistant_msg.usage = c_val
                        yield {"type": "metrics", "usage": c_val}
            except Exception as e:
                yield {"type": "error", "content": f"Critical model failure: {e}"}
                break

            # 3. ¿Hay herramientas que ejecutar?
            if not assistant_msg.tool_calls:
                self.active_status = AgentTurnStatus.COMPLETED
                yield {"status": AgentTurnStatus.COMPLETED}
                break

            # 5. Ejecución asíncrona de herramientas con chequeo de permisos
            self.active_status = AgentTurnStatus.EXECUTING
            yield {"status": AgentTurnStatus.EXECUTING, "tool_calls": assistant_msg.tool_calls}

            tool_tasks = []
            immediate_results = []

            for tc in assistant_msg.tool_calls:
                tool = self.tools.get_tool(tc.name)

                # Rastreo de archivos recientes
                if tc.arguments and "path" in tc.arguments and hasattr(self.client, "update_recent_files"):
                    self.client.update_recent_files(tc.arguments["path"])

                # Seguridad y Auditoría Proactiva
                security_warning = ""
                if tc.name == "execute_command":
                    from ..core.security import SafetyLevel, analyze_command_safety
                    report = analyze_command_safety(tc.arguments.get("command", ""))
                    if report.level != SafetyLevel.SAFE:
                        security_warning = f"DANGEROUS COMMAND DETECTED ({report.category}): {report.description}"

                elif tc.name in ("read_file", "write_file", "edit_file", "list_dir"):
                    from ..core.security import ensure_safe_path
                    try:
                        ensure_safe_path(tc.arguments.get("path", "."))
                    except PermissionError as e:
                        security_warning = f"PATH ESCAPE ATTEMPT: {str(e)}"

                # Solicitar confirmación con advertencia si existe
                is_dir_trusted = self.trust.is_trusted(os.getcwd())
                
                # CRITICAL SECURITY FIX: Trusted directory ONLY bypasses confirmation for regular tools.
                # If there's a SECURITY WARNING (like PATH ESCAPE), we MUST ask or block.
                force_confirmation = bool(security_warning)

                if tool and tool.requires_confirmation and confirmation_callback and (not is_dir_trusted or force_confirmation):
                    try:
                        allowed = await confirmation_callback(tc.name, tc.arguments, warning=security_warning)
                        if not allowed:
                            immediate_results.append(ToolResult(tool_call_id=tc.id, content=f"Error: User denied execution of {tc.name}.", is_error=True))
                            continue
                    except Exception as e:
                        immediate_results.append(ToolResult(tool_call_id=tc.id, content=f"Error during confirmation: {e}", is_error=True))
                        continue

                # Preparar tarea con captura de errores individual
                async def safe_call(t_name, t_id, t_args):
                    try:
                        return await self.tools.call_tool(t_name, t_id, t_args)
                    except Exception as exc:
                        return ToolResult(tool_call_id=t_id, content=f"Tool execution failed: {exc}", is_error=True)

                tool_tasks.append(safe_call(tc.name, tc.id, tc.arguments))

            # Ejecutar y procesar resultados
            results = []
            if tool_tasks:
                results = await asyncio.gather(*tool_tasks)

            all_results = immediate_results + list(results)

            for res in all_results:
                tc_name = "unknown"
                for tc in assistant_msg.tool_calls:
                    if tc.id == res.tool_call_id:
                        tc_name = tc.name
                        break

                # Validación LSP para archivos Python
                if res.content.startswith("Success") and tc_name in ("edit_file", "write_file"):
                    path = tc.arguments.get("path", "")
                    if path.endswith(".py") and self.lsp:
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                code = f.read()
                            diagnostics = await self.lsp.check_file(path, code)
                            if diagnostics:
                                diag_msg = "\n\n[LSP DIAGNOSTICS - Syntax/Lint Errors Detected]:\n"
                                for d in diagnostics:
                                    severity = "ERROR" if d.get("severity") == 1 else "WARNING"
                                    msg = d.get("message")
                                    line = d.get("range", {}).get("start", {}).get("line", 0) + 1
                                    diag_msg += f"- [{severity}] line {line}: {msg}\n"
                                diag_msg += "\n[!] Please fix these errors in your next turn."
                                res.content += diag_msg
                        except Exception as lsp_err:
                            # Silently fail or log LSP errors to not break core loop
                            pass

                history.append(Message(
                    role=Role.TOOL,
                    content=res.content,
                    metadata={"tool_call_id": res.tool_call_id, "tool_name": tc_name}
                ))
                yield {"type": "tool_result", "content": res.content, "is_error": res.is_error}

            # Volver al inicio del bucle para que el modelo vea los resultados de las herramientas
