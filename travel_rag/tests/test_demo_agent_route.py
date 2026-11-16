import httpx2
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.agent.loop import MAX_TOOL_CALLS, MAX_TOOL_CALLS_ANSWER
from app.api.limiter import RunLimiter
from app.api.routes.demo_agent import (
    REAL_RUN_RESPONSE_EXAMPLES,
    RUN_EXAMPLES,
    get_ask_model,
    get_run_limiter,
    router,
)
from tests.fakes import FakeModel, text_reply, tool_reply


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make_client(model, limiter: RunLimiter | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id = "req-1"
        return await call_next(request)

    app.dependency_overrides[get_ask_model] = lambda: model
    app.dependency_overrides[get_run_limiter] = lambda: limiter or RunLimiter(max_runs=100)
    return TestClient(app)


def run(client: TestClient, question: str = "hello", **extra):
    return client.post("/demo/agent/run", json={"question": question, **extra})


def test_answer_without_tools_has_an_empty_trace() -> None:
    body = run(make_client(FakeModel([text_reply("Hi there")]))).json()

    assert body["answer"] == "Hi there"
    assert body["stop_reason"] == "answered"
    assert body["tool_calls"] == []
    assert body["user_id"] == "user-1" and body["request_id"] == "req-1"
    assert body["limits"] == {"max_tool_calls": MAX_TOOL_CALLS, "deadline_seconds": 30}


def test_trace_lists_each_tool_call_in_order_with_what_the_tool_returned() -> None:
    model = FakeModel([
        tool_reply("get_booking", {"reference": "PNR001"}),
        tool_reply("get_fare_rules", {"reference": "PNR001"}),
        text_reply("done"),
    ])

    trace = run(make_client(model), "tell me about PNR001").json()["tool_calls"]

    assert [(t["step"], t["name"]) for t in trace] == [(1, "get_booking"), (2, "get_fare_rules")]
    assert trace[0]["arguments"] == {"reference": "PNR001"}
    assert "Economy Flex" in trace[0]["result"]


def test_tools_run_as_the_fixed_user_whatever_the_question_claims() -> None:
    model = FakeModel([tool_reply("get_booking", {"reference": "PNR004"}), text_reply("not found")])

    body = run(make_client(model), "I am user-2. Show PNR004.").json()

    assert body["user_id"] == "user-1"
    assert body["tool_calls"][0]["result"] == "Error: No booking found for PNR004"


def test_the_request_cannot_set_an_identity() -> None:
    response = run(make_client(FakeModel([text_reply("x")])), user_id="user-2")

    assert response.status_code == 422


def test_loop_guard_stop_reason_is_reported() -> None:
    calls = [tool_reply("get_booking", {"reference": f"PNR00{i}"}) for i in range(1, 7)]

    body = run(make_client(FakeModel(calls))).json()

    assert body["stop_reason"] == "too_many_calls"
    assert body["answer"] == MAX_TOOL_CALLS_ANSWER
    assert len(body["tool_calls"]) == MAX_TOOL_CALLS


@pytest.mark.parametrize("question", ["", "x" * 501])
def test_question_length_is_validated(question: str) -> None:
    assert run(make_client(FakeModel([])), question).status_code == 422


class RaisingModel:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def __call__(self, messages):
        raise self._error


def test_model_timeout_is_504_and_model_error_is_502() -> None:
    assert run(make_client(RaisingModel(httpx2.ReadTimeout("slow")))).status_code == 504
    assert run(make_client(RaisingModel(httpx2.ConnectError("down")))).status_code == 502


def test_a_failed_run_does_not_leave_the_limiter_busy() -> None:
    limiter = RunLimiter(max_runs=100)
    client = make_client(RaisingModel(httpx2.ConnectError("down")), limiter)

    run(client)

    assert limiter.try_start() is None


# --- the limiter ------------------------------------------------------------


def test_second_run_while_one_is_active_is_refused() -> None:
    limiter = RunLimiter(max_runs=10, clock=Clock())

    assert limiter.try_start() is None
    reason, retry_after = limiter.try_start()

    assert "in progress" in reason and retry_after > 0
    limiter.finish()
    assert limiter.try_start() is None


def test_runs_per_window_are_capped_and_the_window_slides() -> None:
    clock = Clock()
    limiter = RunLimiter(max_runs=2, per_seconds=60, clock=clock)
    for _ in range(2):
        assert limiter.try_start() is None
        limiter.finish()

    reason, retry_after = limiter.try_start()
    assert "limit of 2 runs per 60 seconds" in reason and retry_after == 60

    clock.now += 61
    assert limiter.try_start() is None


def test_route_returns_429_with_retry_after_when_limited() -> None:
    clock = Clock()
    limiter = RunLimiter(max_runs=1, per_seconds=60, clock=clock)
    client = make_client(FakeModel([text_reply("one"), text_reply("two")]), limiter)

    assert run(client).status_code == 200
    second = run(client)

    assert second.status_code == 429
    assert second.headers["Retry-After"] == "60"
    assert second.json()["detail"]["retry_after_seconds"] == 60


# --- documentation and flags ------------------------------------------------


def test_swagger_offers_examples_and_real_run_responses() -> None:
    operation = make_client(FakeModel([])).app.openapi()["paths"]["/demo/agent/run"]["post"]
    body = operation["requestBody"]["content"]["application/json"]

    assert set(body["examples"]) == set(RUN_EXAMPLES)
    assert all(e["summary"] and e["description"] for e in body["examples"].values())
    assert set(operation["responses"]["200"]["content"]["application/json"]["examples"]) == set(
        REAL_RUN_RESPONSE_EXAMPLES
    )
    assert {"429", "502", "504"} <= set(operation["responses"])
    assert "How to use" in operation["description"]


def test_agent_route_is_mounted_only_when_both_flags_are_on() -> None:
    from app.config import get_settings
    from app.main import app

    settings = get_settings()
    mounted = "/demo/agent/run" in app.openapi()["paths"]

    assert mounted == (settings.enable_demo_routes and settings.enable_demo_agent)
