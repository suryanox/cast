from cast.recorder import record, get_active_run, capture_step


def test_openai_completions_interceptor_captures(tmp_db, mock_openai_response):
    from cast.interceptors.openai.completions import OpenAICompletionsInterceptor

    results = {}
    interceptor = OpenAICompletionsInterceptor()

    @record
    def agent():
        results["run_id"] = get_active_run().id
        capture_step(
            model="gpt-4o-mini",
            prompt=[{"role": "user", "content": "what is the capital of France?"}],
            response="Paris is the capital of France.",
            input_tokens=mock_openai_response.usage.prompt_tokens,
            output_tokens=mock_openai_response.usage.completion_tokens,
            latency_ms=120,
        )

    agent()

    from cast.store import load_run
    run = load_run(results["run_id"])
    assert len(run.steps) == 1
    assert run.steps[0].response == "Paris is the capital of France."
    assert run.steps[0].input_tokens == 20
    assert run.steps[0].output_tokens == 10


def test_openai_completions_tool_call_captured(tmp_db, mock_openai_tool_response):
    from cast.models import ToolCall

    results = {}

    @record
    def agent():
        results["run_id"] = get_active_run().id
        capture_step(
            model="gpt-4o-mini",
            prompt=[{"role": "user", "content": "search the web"}],
            response="",
            input_tokens=30,
            output_tokens=15,
            latency_ms=200,
            tool_calls=[
                ToolCall(id="call_abc123", name="search",
                         arguments={"query": "weather Singapore"})
            ],
        )

    agent()

    from cast.store import load_run
    run = load_run(results["run_id"])
    assert len(run.steps[0].tool_calls) == 1
    assert run.steps[0].tool_calls[0].name == "search"


def test_no_capture_outside_record(tmp_db):
    assert get_active_run() is None
    step = capture_step(
        model="gpt-4o-mini",
        prompt=[],
        response="should not be stored",
    )
    assert step is None


def test_interceptor_patch_unpatch():
    from cast.interceptors.openai.completions import OpenAICompletionsInterceptor
    interceptor = OpenAICompletionsInterceptor()

    interceptor.patch()
    assert interceptor._patched is True

    interceptor.unpatch()
    assert interceptor._patched is False


def test_patch_idempotent():
    from cast.interceptors.openai.completions import OpenAICompletionsInterceptor
    interceptor = OpenAICompletionsInterceptor()

    interceptor.patch()
    interceptor.patch()
    assert interceptor._patched is True

    interceptor.unpatch()
    assert interceptor._patched is False