import uuid
from datetime import datetime
from enum import Enum
from typing import Any

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
    tool_call_id: str
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
    """
    Defines the level of architectural rigor and tool orchestration complexity.
    """

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
