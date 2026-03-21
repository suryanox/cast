from .base import BaseInterceptor
from .openai import (
    OpenAICompletionsInterceptor,
    OpenAIResponsesInterceptor,
    OpenAIAgentsInterceptor,
)

_interceptors: list[BaseInterceptor] = [
    OpenAICompletionsInterceptor(),
    OpenAIResponsesInterceptor(),
    OpenAIAgentsInterceptor(),
]


def patch_all():
    for interceptor in _interceptors:
        interceptor.patch()


def unpatch_all():
    for interceptor in _interceptors:
        interceptor.unpatch()