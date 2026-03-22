from __future__ import annotations
import time
import json

from cast.interceptors.base import BaseInterceptor
from cast.recorder import capture_step, get_active_run
from cast.models import ToolCall


class LiteLLMCompletionInterceptor(BaseInterceptor):
    _original_completion = None
    _original_acompletion = None

    def _apply_patch(self):
        try:
            import litellm

            original_completion = litellm.completion
            LiteLLMCompletionInterceptor._original_completion = original_completion

            def patched_completion(*args, **kwargs):
                if not get_active_run():
                    return original_completion(*args, **kwargs)

                if kwargs.get("stream", False):
                    return original_completion(*args, **kwargs)

                messages = kwargs.get("messages", [])
                model = kwargs.get("model", "unknown")

                start = time.time()
                response = original_completion(*args, **kwargs)
                latency_ms = int((time.time() - start) * 1000)

                choice = response.choices[0]
                text = choice.message.content or ""

                tool_calls = []
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        tool_calls.append(ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=json.loads(tc.function.arguments),
                        ))

                capture_step(
                    model=model,
                    prompt=messages,
                    response=text,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    latency_ms=latency_ms,
                    tool_calls=tool_calls,
                )
                return response

            litellm.completion = patched_completion

            original_acompletion = litellm.acompletion
            LiteLLMCompletionInterceptor._original_acompletion = original_acompletion

            async def patched_acompletion(*args, **kwargs):
                if not get_active_run():
                    return await original_acompletion(*args, **kwargs)

                if kwargs.get("stream", False):
                    return await original_acompletion(*args, **kwargs)

                messages = kwargs.get("messages", [])
                model = kwargs.get("model", "unknown")

                start = time.time()
                response = await original_acompletion(*args, **kwargs)
                latency_ms = int((time.time() - start) * 1000)

                choice = response.choices[0]
                text = choice.message.content or ""

                tool_calls = []
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        tool_calls.append(ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=json.loads(tc.function.arguments),
                        ))

                capture_step(
                    model=model,
                    prompt=messages,
                    response=text,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    latency_ms=latency_ms,
                    tool_calls=tool_calls,
                )
                return response

            litellm.acompletion = patched_acompletion

        except ImportError:
            pass

    def _remove_patch(self):
        try:
            import litellm
            if LiteLLMCompletionInterceptor._original_completion:
                litellm.completion = LiteLLMCompletionInterceptor._original_completion
            if LiteLLMCompletionInterceptor._original_acompletion:
                litellm.acompletion = LiteLLMCompletionInterceptor._original_acompletion
        except ImportError:
            pass