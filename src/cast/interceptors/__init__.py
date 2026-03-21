from .base import BaseInterceptor
from .openai import (
    OpenAICompletionsInterceptor,
    OpenAIResponsesInterceptor
)

_interceptors: list[BaseInterceptor] = [
    OpenAICompletionsInterceptor(),
    OpenAIResponsesInterceptor()
]


def patch_all():
    for interceptor in _interceptors:
        interceptor.patch()


def unpatch_all():
    for interceptor in _interceptors:
        interceptor.unpatch()