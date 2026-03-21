from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum
import uuid


class StepType(str, Enum):
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"


class RunStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    result: Optional[Any] = None


@dataclass
class Step:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    run_id: str = ""
    index: int = 0
    type: StepType = StepType.LLM_CALL
    model: str = ""
    prompt: list[dict] = field(default_factory=list)
    response: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class Run:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    status: RunStatus = RunStatus.RUNNING
    steps: list[Step] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    error: Optional[str] = None
    forked_from: Optional[str] = None
    forked_at_step: Optional[int] = None

    @property
    def total_tokens(self) -> int:
        return sum(s.total_tokens for s in self.steps)

    @property
    def duration_ms(self) -> int:
        if not self.ended_at:
            return 0
        return int((self.ended_at - self.started_at).total_seconds() * 1000)
