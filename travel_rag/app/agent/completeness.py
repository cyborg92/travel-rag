import json
from dataclasses import dataclass
from app.agent.state import ToolCallRecord

@dataclass(frozen=True)
class RequiredFact:
    text: str      # what to show the user if missing
    needle: str    # what must appear in the answer to count as present

def parse_result(result: str) -> dict | None:
    try:
        data = json.loads(result)
        if isinstance(data,dict):
            return data
        return None
    except json.JSONDecodeError:
        return None

def required_facts(tool_calls: list[ToolCallRecord]) -> list[RequiredFact]:
    """Facts in the tool results that the final answer must mention."""
    facts: list[RequiredFact] = []
    for record in tool_calls:
        data = parse_result(record.result)
        if data is None:
            continue
        for note in data.get("notes", []):
            fact = RequiredFact(text=note, needle=note)
            if fact not in facts:
                facts.append(fact)
        credit = data.get("credit_issued", 0)
        if credit > 0:
            months = data.get("credit_valid_months")
            validity = f", valid for {months} months" if months else ""
            fact = RequiredFact(text=f"Travel credit of ₹{credit}{validity}", needle=str(credit))
            if fact not in facts:
                facts.append(fact)
    return facts


def missing_facts(tool_calls: list[ToolCallRecord], answer: str) -> list[RequiredFact]:
    """Required facts whose needle does not appear in the answer."""
    return [fact for fact in required_facts(tool_calls) if fact.needle not in answer]


def quote_summaries(tool_calls: list[ToolCallRecord]) -> list[str]:
    """One line per successful quote, built from the tool result and not from the model.

    The model sometimes states a wrong total (it once added the new fare to the
    change fee). These lines carry the figures the tool actually returned.
    """
    lines: list[str] = []
    for record in tool_calls:
        data = parse_result(record.result)
        if data is None or not data.get("changeable") or data.get("total_to_pay") is None:
            continue
        line = (
            f"{data['reference']} to {data['new_date']}: "
            f"change fee {_rupees(data['change_fee'])}, "
            f"fare difference {_rupees(data['fare_difference'])}, "
            f"total to pay {_rupees(data['total_to_pay'])}"
        )
        if line not in lines:
            lines.append(line)
    return lines


def _rupees(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}₹{abs(amount):,}"
