import pytest
from unittest.mock import MagicMock
from cast import recorder


@pytest.fixture(autouse=True)
def reset_active_run():
    recorder._active_run = None
    yield
    recorder._active_run = None


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    import cast.store as store
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test_runs.db")
    monkeypatch.setattr(store, "CAST_DIR", tmp_path)
    yield tmp_path


@pytest.fixture
def mock_openai_response():
    choice = MagicMock()
    choice.message.content = "Paris is the capital of France."
    choice.message.tool_calls = None
    choice.finish_reason = "stop"

    response = MagicMock()
    response.choices = [choice]
    response.usage.prompt_tokens = 20
    response.usage.completion_tokens = 10
    response.model = "gpt-4o-mini"
    return response


@pytest.fixture
def mock_openai_tool_response():
    import json

    tool_call = MagicMock()
    tool_call.id = "call_abc123"
    tool_call.function.name = "search"
    tool_call.function.arguments = json.dumps({"query": "weather Singapore"})

    choice = MagicMock()
    choice.message.content = ""
    choice.message.tool_calls = [tool_call]
    choice.finish_reason = "tool_calls"

    response = MagicMock()
    response.choices = [choice]
    response.usage.prompt_tokens = 30
    response.usage.completion_tokens = 15
    return response