from __future__ import annotations
import time
import json

from cast.interceptors.base import BaseInterceptor
from cast.recorder import capture_step, get_active_run
from cast.models import ToolCall


class OpenAIResponsesInterceptor(BaseInterceptor):
    """
    Intercepts openai.OpenAI().responses.create()
    Supports: Responses API text output, tool calls.
    Passthrough: streaming (not yet supported).
    """

    _original_init = None

    def _apply_patch(self):
        try:
            import openai
            OpenAIResponsesInterceptor._original_init = openai.OpenAI.__init__
            existing_init = openai.OpenAI.__init__

            def patched_init(client_self, *args, **kwargs):
                existing_init(client_self, *args, **kwargs)

                if not hasattr(client_self, "responses"):
                    return

                original_create = client_self.responses.create

                def patched_create(**kwargs):
                    if not get_active_run():
                        return original_create(**kwargs)

                    if kwargs.get("stream", False):
                        return original_create(**kwargs)

                    input_messages = kwargs.get("input", [])
                    if isinstance(input_messages, str):
                        input_messages = [{"role": "user", "content": input_messages}]

                    model = kwargs.get("model", "unknown")

                    start = time.time()
                    response = original_create(**kwargs)
                    latency_ms = int((time.time() - start) * 1000)

                    text = ""
                    tool_calls = []
                    for item in getattr(response, "output", []):
                        item_type = getattr(item, "type", "")
                        if item_type == "message":
                            for block in getattr(item, "content", []):
                                if getattr(block, "type", "") == "output_text":
                                    text = getattr(block, "text", "")
                        elif item_type == "function_call":
                            tool_calls.append(ToolCall(
                                id=getattr(item, "call_id", ""),
                                name=getattr(item, "name", ""),
                                arguments=json.loads(getattr(item, "arguments", "{}")),
                            ))

                    usage = getattr(response, "usage", None)
                    capture_step(
                        model=model,
                        prompt=input_messages,
                        response=text,
                        input_tokens=getattr(usage, "input_tokens", 0),
                        output_tokens=getattr(usage, "output_tokens", 0),
                        latency_ms=latency_ms,
                        tool_calls=tool_calls,
                    )
                    return response

                client_self.responses.create = patched_create

            openai.OpenAI.__init__ = patched_init

        except ImportError:
            pass

    def _remove_patch(self):
        try:
            import openai
            if OpenAIResponsesInterceptor._original_init:
                openai.OpenAI.__init__ = OpenAIResponsesInterceptor._original_init
        except ImportError:
            pass