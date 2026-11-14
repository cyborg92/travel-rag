import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.demo import DEMO_USER_ID, router


def make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def execute(client: TestClient, name: str, arguments: dict, **kwargs):
    return client.post("/demo/tools/execute", json={"name": name, "arguments": arguments}, **kwargs)


def test_demo_routes_are_not_mounted_by_default() -> None:
    from app.main import app

    assert not [path for path in app.openapi()["paths"] if path.startswith("/demo")]


def test_execute_returns_own_booking_as_the_fixed_user() -> None:
    body = execute(make_client(), "get_booking", {"reference": "PNR001"}).json()

    assert body["user_id"] == DEMO_USER_ID
    assert json.loads(body["observation"])["reference"] == "PNR001"


def test_missing_and_someone_elses_booking_look_identical() -> None:
    client = make_client()

    missing = execute(client, "get_booking", {"reference": "PNR999"}).json()["observation"]
    not_yours = execute(client, "get_booking", {"reference": "PNR004"}).json()["observation"]

    assert missing.replace("PNR999", "X") == not_yours.replace("PNR004", "X")
    assert "user-2" not in not_yours and "Other Passenger" not in not_yours


def test_unknown_tool_and_invalid_arguments_become_observations() -> None:
    client = make_client()

    unknown = execute(client, "delete_booking", {}).json()["observation"]
    invalid = execute(client, "get_booking", {"reference": "bad"}).json()["observation"]

    assert unknown.startswith("Unknown tool")
    assert invalid.startswith("Invalid arguments")


def test_client_cannot_supply_an_identity() -> None:
    client = make_client()

    in_arguments = execute(client, "get_booking", {"reference": "PNR004", "user_id": "user-2"})
    as_field = client.post(
        "/demo/tools/execute",
        json={"name": "get_booking", "arguments": {"reference": "PNR004"}, "user_id": "user-2"},
    )

    assert in_arguments.json()["observation"].startswith("Invalid arguments")
    assert as_field.status_code == 422


def test_quote_uses_the_supplied_now_for_the_fee_band() -> None:
    client = make_client()
    far = client.post(
        "/demo/tools/quote",
        json={"reference": "PNR001", "new_date": "2026-11-21", "now": "2026-11-12T10:00:00"},
    ).json()
    near = client.post(
        "/demo/tools/quote",
        json={"reference": "PNR001", "new_date": "2026-11-21", "now": "2026-11-19T10:00:00"},
    ).json()

    assert far["changeable"] is True and far["change_fee"] == 3500
    assert near["change_fee"] != far["change_fee"] or near["changeable"] is False


def test_quote_for_someone_elses_booking_is_404() -> None:
    response = make_client().post(
        "/demo/tools/quote", json={"reference": "PNR004", "new_date": "2026-12-20"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No booking found for PNR004"
