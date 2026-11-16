import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.demo import (
    DEMO_USER_ID,
    EXECUTE_EXAMPLES,
    EXECUTE_RESPONSE_EXAMPLES,
    QUOTE_EXAMPLES,
    QUOTE_RESPONSE_EXAMPLES,
    router,
)
from app.config import get_settings


def make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def execute(client: TestClient, name: str, arguments: dict, **kwargs):
    return client.post("/demo/tools/execute", json={"name": name, "arguments": arguments}, **kwargs)


def test_demo_routes_are_mounted_only_when_the_flag_is_on() -> None:
    from app.main import app

    mounted = any(path.startswith("/demo") for path in app.openapi()["paths"])

    assert mounted == get_settings().enable_demo_routes


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


# --- the documented examples must match real behaviour ----------------------

EXECUTE_EXPECTED_START = {
    "own_booking": '{"reference":"PNR001"',
    "not_yours": "Error: No booking found for PNR004",
    "missing": "Error: No booking found for PNR999",
    "identity_injection": "Invalid arguments for 'get_booking'",
    "unknown_tool": "Unknown tool 'cancel_booking'",
    "bad_reference": "Invalid arguments for 'get_booking'",
    "placeholder_date": "Invalid arguments for 'quote_change'",
    "fare_rules_restricted": '{"reference":"PNR005"',
}

# key -> (changeable, change_fee, total_to_pay)
QUOTE_EXPECTED = {
    "costlier_date": (True, 3500, 4300),
    "cheaper_date_credit": (True, 3500, 3500),
    "domestic_credit": (True, 500, 500),
    "boundary_exactly_72h": (True, 1000, 2500),
    "boundary_73h": (True, 500, 2000),
    "too_close": (False, None, None),
    "non_changeable_fare": (False, None, None),
    "cancelled_booking": (False, None, None),
}


def test_every_execute_example_has_a_documented_response_that_matches_the_endpoint() -> None:
    client = make_client()
    assert set(EXECUTE_EXAMPLES) == set(EXECUTE_EXPECTED_START) == set(EXECUTE_RESPONSE_EXAMPLES)

    for key, example in EXECUTE_EXAMPLES.items():
        response = client.post("/demo/tools/execute", json=example["value"])

        assert response.status_code == 200, key
        assert response.json()["observation"].startswith(EXECUTE_EXPECTED_START[key]), key
        assert response.json() == EXECUTE_RESPONSE_EXAMPLES[key]["value"], key


def test_every_quote_example_matches_the_endpoint_and_the_documented_figures() -> None:
    client = make_client()
    assert set(QUOTE_EXPECTED) | {"not_yours"} == set(QUOTE_EXAMPLES)

    for key, (changeable, fee, total) in QUOTE_EXPECTED.items():
        body = client.post("/demo/tools/quote", json=QUOTE_EXAMPLES[key]["value"]).json()

        assert (body["changeable"], body["change_fee"], body["total_to_pay"]) == (changeable, fee, total), key
        assert body == QUOTE_RESPONSE_EXAMPLES[key]["value"], key
    assert client.post("/demo/tools/quote", json=QUOTE_EXAMPLES["not_yours"]["value"]).status_code == 404


def test_swagger_schema_offers_the_examples_and_descriptions() -> None:
    schema = make_client().app.openapi()
    execute = schema["paths"]["/demo/tools/execute"]["post"]
    quote = schema["paths"]["/demo/tools/quote"]["post"]

    for operation, examples in ((execute, EXECUTE_EXAMPLES), (quote, QUOTE_EXAMPLES)):
        body = operation["requestBody"]["content"]["application/json"]
        assert set(body["examples"]) == set(examples)
        assert operation["summary"] and "How to use" in operation["description"]
        assert all(example["summary"] and example["description"] for example in body["examples"].values())
        assert operation["responses"]["200"]["content"]["application/json"]["examples"]
