from app.agent.completeness import RequiredFact, missing_facts, parse_result, quote_summaries, required_facts
from app.agent.state import ToolCallRecord
from app.tools.executor import execute_tool


def test_valid_result_object_is_returned_as_a_dict():
    data = parse_result('{"notes": ["x"], "credit_issued": 700}')
    assert data == {"notes": ["x"], "credit_issued": 700}


def test_error_message_is_not_a_result():
    assert parse_result("No booking found for PNR999") is None


def test_json_that_is_not_an_object_is_not_a_result():
    assert parse_result("[1, 2, 3]") is None
    assert parse_result("123") is None
    assert parse_result('"text"') is None
    assert parse_result("null") is None


def test_empty_string_is_not_a_result():
    assert parse_result("") is None


def test_real_tool_output_parses():
    from app.tools.executor import execute_tool

    data = parse_result(execute_tool("get_booking", {"reference": "PNR001"}, "user-1"))
    assert data is not None and data["reference"] == "PNR001"


def test_real_tool_error_does_not_parse():
    from app.tools.executor import execute_tool

    assert parse_result(execute_tool("get_booking", {"reference": "PNR999"}, "user-1")) is None


def record(name: str, arguments: dict, user_id: str = "user-1") -> ToolCallRecord:
    """A ToolCallRecord built from the real executor, as the loop would store it."""
    return ToolCallRecord(name, arguments, execute_tool(name, arguments, user_id), key=f"{name}{arguments}")


def quote(reference: str, new_date: str = "2026-12-12") -> ToolCallRecord:
    return record("quote_change", {"reference": reference, "new_date": new_date})


def test_no_tool_calls_means_no_required_facts():
    assert required_facts([]) == []


def test_quote_with_credit_and_note_requires_both():
    facts = required_facts([quote("PNR001")])
    assert RequiredFact("Tax difference is not included.", "Tax difference is not included.") in facts
    assert RequiredFact("Travel credit of ₹700, valid for 12 months", "700") in facts


def test_same_note_from_two_quotes_is_listed_once():
    facts = required_facts([quote("PNR001"), quote("PNR006")])
    notes = [fact for fact in facts if fact.text == "Tax difference is not included."]
    assert len(notes) == 1


def test_results_without_notes_or_credit_add_nothing():
    assert required_facts([record("get_booking", {"reference": "PNR001"})]) == []
    assert required_facts([record("get_fare_rules", {"reference": "PNR001"})]) == []


def test_tool_errors_are_skipped():
    failed = record("get_booking", {"reference": "PNR999"})
    assert required_facts([failed]) == []


def test_refused_quote_requires_no_credit():
    refused = quote("PNR005")  # restricted fare, not changeable
    assert not any("credit" in fact.text for fact in required_facts([refused]))


def test_facts_come_only_from_the_records_given():
    assert required_facts([quote("PNR001")]) != required_facts([])


COMPLETE_ANSWER = (
    "PNR001: fee 3,500 INR. You get a 700 INR credit valid for 12 months. "
    "Tax difference is not included."
)


def test_complete_answer_has_nothing_missing():
    assert missing_facts([quote("PNR001")], COMPLETE_ANSWER) == []


def test_answer_without_the_note_reports_the_note():
    answer = "Fee 3,500 INR. You get a ₹700 credit."
    missing = missing_facts([quote("PNR001")], answer)
    assert [fact.text for fact in missing] == ["Tax difference is not included."]


def test_answer_without_the_credit_reports_the_credit():
    answer = "Fee 3,500 INR. Tax difference is not included."
    missing = missing_facts([quote("PNR001")], answer)
    assert [fact.text for fact in missing] == ["Travel credit of ₹700, valid for 12 months"]


def test_answer_with_neither_reports_both():
    assert len(missing_facts([quote("PNR001")], "It will cost 3,500 INR.")) == 2


def test_credit_is_found_whatever_the_wording_or_currency_sign():
    for answer in ("₹700 credit", "a credit of 700 INR", "700.00 voucher"):
        facts = missing_facts([quote("PNR001")], answer + " Tax difference is not included.")
        assert facts == [], answer


def test_nothing_is_missing_when_no_tool_returned_facts():
    assert missing_facts([], "anything") == []
    assert missing_facts([record("get_booking", {"reference": "PNR001"})], "anything") == []


def test_quote_summary_uses_the_tool_figures():
    assert quote_summaries([quote("PNR001")]) == [
        "PNR001 to 2026-12-12: change fee ₹3,500, fare difference -₹700, total to pay ₹3,500"
    ]


def test_quote_summary_shows_a_zero_fare_difference_without_a_sign():
    assert quote_summaries([quote("PNR001", "2026-12-01")]) == [
        "PNR001 to 2026-12-01: change fee ₹3,500, fare difference ₹0, total to pay ₹3,500"
    ]


def test_quote_summary_skips_refusals_and_non_quotes():
    refused = quote("PNR005")
    assert quote_summaries([refused, record("get_booking", {"reference": "PNR001"})]) == []


def test_identical_quotes_are_summarised_once():
    assert len(quote_summaries([quote("PNR001"), quote("PNR001")])) == 1
