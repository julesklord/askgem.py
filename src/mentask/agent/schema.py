import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class UsageMetrics(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_call_id: str = ""
    content: str
    is_error: bool = False
    metadata: dict[str, Any] | None = None


class Message(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Role
    timestamp: datetime = Field(default_factory=datetime.now)
    content: str | list[dict[str, Any]]
    thought: str | None = None
    is_virtual: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserMessage(Message):
    role: Role = Role.USER
    origin: str | None = "keyboard"  # keyboard, bridge, mcp


class AssistantMessage(Message):
    role: Role = Role.ASSISTANT
    model: str = ""
    stop_reason: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: UsageMetrics = Field(default_factory=UsageMetrics)


class AgentTurnStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    ERROR = "error"
    COMPLETED = "completed"


class EngineeringLevel(str, Enum):
    """Defines the level of architectural rigor and tool orchestration complexity."""

    @property
    def level_name(self) -> str:
        return self.value

    L0_INQUIRY = "l0_inquiry"  # Pure questions, no tools needed.
    L1_PRAGMATIC = "l1_pragmatic"  # Direct execution, minimal research, simple tools.
    L2_STANDARD = "l2_standard"  # Research -> Plan -> Execute cycle. Default.
    L3_ARCHITECT = "l3_architect"  # Deep analysis, repository mapping, subagent delegation.


# Decoupled Multi-Client Event Streaming Models
class AgentEvent(BaseModel):
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ThoughtEvent(AgentEvent):
    event_type: str = "thought"
    content: str


class TextChunkEvent(AgentEvent):
    event_type: str = "text_chunk"
    content: str


class ToolCallEvent(AgentEvent):
    event_type: str = "tool_call"
    tool_call: ToolCall


class ToolResultEvent(AgentEvent):
    event_type: str = "tool_result"
    result: ToolResult


class StatusEvent(AgentEvent):
    event_type: str = "status"
    status: AgentTurnStatus
    message: str | None = None


@runtime_checkable
class EventSink(Protocol):
    """Protocol for decoupled event streaming from the agent to a UI/client renderer."""

    _streaming: bool
    _label_printed: bool
    console: Any
    C_BRAND: str
    C_SUCCESS: str

    def reset_turn(self) -> None:
        """Resets state for a new agent response turn."""
        ...

    def show_thinking(self) -> None:
        """Indicates to the user that the agent is generating thoughts/reasoning."""
        ...

    def stop_thinking(self) -> None:
        """Stops the thinking/reasoning indicator."""
        ...

    def start_stream(self, is_natural: bool = True) -> None:
        """Signals the start of incremental text generation."""
        ...

    def update_stream(self, content: str) -> None:
        """Sends incremental text chunks to be rendered."""
        ...

    def end_stream(self, full_text: str | None = None) -> None:
        """Signals the end of text stream generation."""
        ...

    def print_thought(self, content: str) -> None:
        """Renders the agent's chain-of-thought block."""
        ...

    def print_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        """Renders an outgoing tool call invocation."""
        ...

    def print_tool_result(self, ok: bool, content: str, tool_name: str | None = None) -> None:
        """Renders the execution result returned by a tool."""
        ...

    def _print_agent_label(self, tool: str | None = None, is_natural: bool = False) -> None:
        """Prints the agent header block."""
        ...

    def print_command_output(self, result: Any) -> None:
        """Renders the output of an executed slash command."""
        ...

    def print_error(self, message: str) -> None:
        """Renders an error message."""
        ...

    def print_metrics(self, summary: str) -> None:
        """Renders turn execution metrics."""
        ...

    def update_status_bar(
        self,
        model: str | None = None,
        mode: str | None = None,
        tokens: int | None = None,
        cost: float | None = None,
    ) -> None:
        """Updates status bar parameters."""
        ...

    def print_turn_divider(self, model: str = "") -> None:
        """Renders the divider at the end of a turn."""
        ...

    def print_warning(self, message: str) -> None:
        """Renders a warning message."""
        ...

    def print_status(self, message: str) -> None:
        """Logs or displays status messages."""
        ...

