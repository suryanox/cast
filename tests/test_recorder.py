import pytest
from cast import recorder
from cast.models import RunStatus
from cast.recorder import record, capture_step, get_active_run


def test_record_creates_run(tmp_db):
    @record
    def agent():
        return "done"

    agent()
    assert recorder._active_run is None


def test_record_status_done(tmp_db):
    results = {}

    @record
    def agent():
        results["run_id"] = get_active_run().id

    agent()
    from cast.store import load_run
    run = load_run(results["run_id"])
    assert run.status == RunStatus.DONE


def test_record_status_failed(tmp_db):
    results = {}

    @record
    def agent():
        results["run_id"] = get_active_run().id
        raise ValueError("something broke")

    with pytest.raises(ValueError):
        agent()

    from cast.store import load_run
    run = load_run(results["run_id"])
    assert run.status == RunStatus.FAILED
    assert "something broke" in run.error


def test_record_captures_steps(tmp_db):
    results = {}

    @record
    def agent():
        results["run_id"] = get_active_run().id
        capture_step(
            model="gpt-4o-mini",
            prompt=[{"role": "user", "content": "hello"}],
            response="hi there",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
        )

    agent()

    from cast.store import load_run
    run = load_run(results["run_id"])
    assert len(run.steps) == 1
    assert run.steps[0].response == "hi there"
    assert run.steps[0].model == "gpt-4o-mini"
    assert run.total_tokens == 15


def test_record_multiple_steps(tmp_db):
    results = {}

    @record
    def agent():
        results["run_id"] = get_active_run().id
        for i in range(3):
            capture_step(
                model="gpt-4o-mini",
                prompt=[{"role": "user", "content": f"step {i}"}],
                response=f"response {i}",
                input_tokens=10,
                output_tokens=5,
                latency_ms=50,
            )

    agent()

    from cast.store import load_run
    run = load_run(results["run_id"])
    assert len(run.steps) == 3
    assert run.steps[0].index == 0
    assert run.steps[2].index == 2


def test_no_active_run_capture_returns_none():
    step = capture_step(
        model="gpt-4o-mini",
        prompt=[],
        response="ignored",
    )
    assert step is None


@pytest.mark.asyncio
async def test_record_async_done(tmp_db):
    results = {}

    @record
    async def async_agent():
        results["run_id"] = get_active_run().id
        capture_step(
            model="gpt-4o-mini",
            prompt=[{"role": "user", "content": "async hello"}],
            response="async response",
            input_tokens=10,
            output_tokens=5,
            latency_ms=80,
        )

    await async_agent()

    from cast.store import load_run
    run = load_run(results["run_id"])
    assert run.status == RunStatus.DONE
    assert len(run.steps) == 1


@pytest.mark.asyncio
async def test_record_async_failed(tmp_db):
    results = {}

    @record
    async def async_agent():
        results["run_id"] = get_active_run().id
        raise RuntimeError("async failure")

    with pytest.raises(RuntimeError):
        await async_agent()

    from cast.store import load_run
    run = load_run(results["run_id"])
    assert run.status == RunStatus.FAILED
    assert "async failure" in run.error