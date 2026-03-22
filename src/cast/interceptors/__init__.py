from .base import BaseInterceptor
from .openai import (
    OpenAICompletionsInterceptor,
    OpenAIResponsesInterceptor,
)
from .litellm import LiteLLMCompletionInterceptor

_interceptors: list[BaseInterceptor] = [
    OpenAICompletionsInterceptor(),
    OpenAIResponsesInterceptor(),
    LiteLLMCompletionInterceptor(),
]


def patch_all():
    for interceptor in _interceptors:
        interceptor.patch()


def unpatch_all():
    for interceptor in _interceptors:
        interceptor.unpatch()