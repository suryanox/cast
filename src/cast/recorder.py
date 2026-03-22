from __future__ import annotations
import uuid
import asyncio
import functools
from datetime import datetime
from typing import  Callable, Optional

from .models import Run, Step, StepType, RunStatus, ToolCall
from .store import save_run

_active_run: Optional[Run] = None


def get_active_run() -> Optional[Run]:
    return _active_run


def record(fn: Callable) -> Callable:
    if asyncio.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            global _active_run
            run = Run(
                id=str(uuid.uuid4())[:8],
                name=fn.__name__,
                status=RunStatus.RUNNING,
                started_at=datetime.utcnow(),
            )
            _active_run = run
            try:
                result = await fn(*args, **kwargs)
                run.status = RunStatus.DONE
                return result
            except Exception as e:
                run.status = RunStatus.FAILED
                run.error = str(e)
                raise
            finally:
                run.ended_at = datetime.utcnow()
                save_run(run)
                _active_run = None
                print(f"\n[cast] run recorded → {run.id}  "
                      f"steps={len(run.steps)}  "
                      f"tokens={run.total_tokens}  "
                      f"status={run.status.value}")
        return async_wrapper

    else:
        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            global _active_run
            run = Run(
                id=str(uuid.uuid4())[:8],
                name=fn.__name__,
                status=RunStatus.RUNNING,
                started_at=datetime.utcnow(),
            )
            _active_run = run
            try:
                result = fn(*args, **kwargs)
                run.status = RunStatus.DONE
                return result
            except Exception as e:
                run.status = RunStatus.FAILED
                run.error = str(e)
                raise
            finally:
                run.ended_at = datetime.utcnow()
                save_run(run)
                _active_run = None
                print(f"\n[cast] run recorded → {run.id}  "
                      f"steps={len(run.steps)}  "
                      f"tokens={run.total_tokens}  "
                      f"status={run.status.value}")
        return sync_wrapper


def capture_step(
    model: str,
    prompt: list[dict],
    response: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: int = 0,
    tool_calls: list[ToolCall] = [],
) -> Optional[Step]:
    run = get_active_run()
    if not run:
        return None

    step = Step(
        id=str(uuid.uuid4())[:8],
        run_id=run.id,
        index=len(run.steps),
        type=StepType.LLM_CALL,
        model=model,
        prompt=prompt,
        response=response,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        tool_calls=tool_calls,
        timestamp=datetime.utcnow(),
    )
    run.steps.append(step)
    return step
