import asyncio
import os
from typing import Any, AsyncGenerator, Callable, List, Optional

from .schema import AgentTurnStatus, AssistantMessage, Message, Role, ToolCall, ToolResult
from .tools.base import ToolRegistry
from ..core.trust_manager import TrustManager

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

    async def run_query(self, user_prompt: str, history: List[Message], config: Any | None = None, confirmation_callback: Optional[Callable] = None) -> AsyncGenerator[Any, None]:
        """
        Runs the agentic loop. Yields events for the UI.
        """
        # 1. Preparar Turno
        history.append(Message(role=Role.USER, content=user_prompt))
        self.active_status = AgentTurnStatus.THINKING

        while True:
            yield {"status": AgentTurnStatus.THINKING}

            # 2. Llamada al LLM
            try:
                # [Plan Injection Logic - Keeping it clean]
                import os
                plan_file = ".askgem_plan.md"
                plan_context = ""
                if os.path.exists(plan_file):
                    try:
                        with open(plan_file, "r", encoding="utf-8") as f:
                            plan_context = f"\n\n## CURRENT EXECUTION PLAN:\n{f.read()}"
                    except Exception:
                        pass

                turn_config = config
                if plan_context and hasattr(turn_config, "system_instruction"):
                     from copy import copy
                     turn_config = copy(config)
                     turn_config.system_instruction += plan_context

                model_response = await self.client.generate_response(history, self.tools.get_all_schemas(), config=turn_config)
            except Exception as e:
                yield {"type": "error", "content": f"Critical model failure: {e}"}
                break

            # 3. Procesar Respuesta (Texto, Pensamiento y Tool Calls)
            assistant_msg = model_response["message"]
            history.append(assistant_msg)

            if assistant_msg.thought:
                yield {"type": "thought", "content": assistant_msg.thought}

            if assistant_msg.content:
                yield {"type": "text", "content": assistant_msg.content}

            if assistant_msg.usage:
                yield {"type": "metrics", "usage": assistant_msg.usage}

            # 4. ¿Hay herramientas que ejecutar?
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
                if tc.arguments and "path" in tc.arguments:
                    if hasattr(self.client, "update_recent_files"):
                        self.client.update_recent_files(tc.arguments["path"])

                # Seguridad y Auditoría Proactiva
                security_warning = ""
                if tc.name == "execute_command":
                    from ..core.security import analyze_command_safety, SafetyLevel
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
                
                if tool and tool.requires_confirmation and confirmation_callback and not is_dir_trusted:
                    try:
                        allowed = await confirmation_callback(tc.name, tc.arguments, warning=security_warning)
                        if not allowed:
                            immediate_results.append(ToolResult(tool_call_id=tc.id, content=f"Error: User denied execution of {tc.name}.", is_error=True))
                            continue
                    except Exception as e:
                        immediate_results.append(ToolResult(tool_call_id=tc.id, content=f"Error during confirmation: {e}", is_error=True))
                        continue
                
                # If trusted but had a security warning, just log it to the user
                if is_dir_trusted and security_warning:
                    yield {"type": "warning", "content": f"TRUSTED EXECUTION WITH WARNING: {security_warning}"}

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
                
                history.append(Message(
                    role=Role.TOOL, 
                    content=res.content, 
                    metadata={"tool_call_id": res.tool_call_id, "tool_name": tc_name}
                ))
                yield {"type": "tool_result", "content": res.content, "is_error": res.is_error}

            # Volver al inicio del bucle para que el modelo vea los resultados de las herramientas
