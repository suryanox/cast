from datetime import datetime
from cast.models import Run, Step, RunStatus, StepType, ToolCall
from cast.store import save_run, load_run, list_runs, clear_runs


def make_run(run_id="abc12345", name="test_agent", steps=0) -> Run:
    run = Run(
        id=run_id,
        name=name,
        status=RunStatus.DONE,
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow(),
    )
    for i in range(steps):
        run.steps.append(Step(
            id=f"step{i}",
            run_id=run_id,
            index=i,
            type=StepType.LLM_CALL,
            model="gpt-4o-mini",
            prompt=[{"role": "user", "content": f"message {i}"}],
            response=f"response {i}",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
        ))
    return run


def test_save_and_load_run(tmp_db):
    run = make_run(steps=2)
    save_run(run)

    loaded = load_run(run.id)
    assert loaded is not None
    assert loaded.id == run.id
    assert loaded.name == run.name
    assert loaded.status == RunStatus.DONE
    assert len(loaded.steps) == 2


def test_load_nonexistent_run(tmp_db):
    result = load_run("doesnotexist")
    assert result is None


def test_list_runs(tmp_db):
    for i in range(5):
        save_run(make_run(run_id=f"run0000{i}", name=f"agent_{i}"))

    runs = list_runs()
    assert len(runs) == 5


def test_list_runs_limit(tmp_db):
    for i in range(10):
        save_run(make_run(run_id=f"run000{i:02d}"))

    runs = list_runs(limit=3)
    assert len(runs) == 3


def test_clear_runs(tmp_db):
    for i in range(4):
        save_run(make_run(run_id=f"clr0000{i}"))

    count = clear_runs()
    assert count == 4
    assert list_runs() == []


def test_save_run_with_tool_calls(tmp_db):
    run = make_run()
    run.steps.append(Step(
        id="steptool",
        run_id=run.id,
        index=0,
        type=StepType.LLM_CALL,
        model="gpt-4o-mini",
        prompt=[{"role": "user", "content": "search something"}],
        response="",
        tool_calls=[
            ToolCall(id="tc1", name="search", arguments={"query": "test"})
        ],
        input_tokens=20,
        output_tokens=10,
        latency_ms=200,
    ))
    save_run(run)

    loaded = load_run(run.id)
    assert len(loaded.steps[0].tool_calls) == 1
    assert loaded.steps[0].tool_calls[0].name == "search"
    assert loaded.steps[0].tool_calls[0].arguments == {"query": "test"}


def test_total_tokens(tmp_db):
    run = make_run(steps=3)
    save_run(run)

    loaded = load_run(run.id)
    assert loaded.total_tokens == 45


def test_forked_run(tmp_db):
    original = make_run(run_id="orig0001", steps=2)
    save_run(original)

    forked = make_run(run_id="fork0001", steps=1)
    forked.forked_from = "orig0001"
    forked.forked_at_step = 1
    save_run(forked)

    loaded = load_run("fork0001")
    assert loaded.forked_from == "orig0001"
    assert loaded.forked_at_step == 1