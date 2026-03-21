from __future__ import annotations
import time
from .recorder import capture_step, get_active_run
from .models import ToolCall

def _patch_openai():
    try:
        import openai

        original_init = openai.OpenAI.__init__

        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            original_create = self.chat.completions.create

            def patched_create(**kwargs):
                if not get_active_run():
                    return original_create(**kwargs)

                messages = kwargs.get("messages", [])
                model = kwargs.get("model", "unknown")

                start = time.time()
                response = original_create(**kwargs)
                latency_ms = int((time.time() - start) * 1000)

                choice = response.choices[0]
                text = choice.message.content or ""

                tool_calls = []
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        import json
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

            self.chat.completions.create = patched_create

        openai.OpenAI.__init__ = patched_init

    except ImportError:
        pass


def patch_all():
    _patch_openai()
