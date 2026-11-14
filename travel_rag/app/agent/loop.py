import logging
from dataclasses import dataclass
from datetime import datetime

from app.agent.prompts import build_system_prompt
from app.agent.state import AgentState, ToolCallRecord
from app.agent.completeness import missing_facts, quote_summaries
from app.tools.executor import execute_tool
from app.agent.text_tool_calls import tool_calls_from_text

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class AgentResult:
    answer: str                         # text to show the user
    stop_reason: str                    # "answered", "too_many_calls", "timeout"
    tool_calls: list[ToolCallRecord]    # what ran, for tracing

MAX_TOOL_CALLS = 5 
MAX_TOOL_CALLS_ANSWER = "I couldn't complete this request."
HAS_CALLED_TOOL_ANSWER = "you already made this call; use the earlier result"
DEADLINE_SECONDS = 30
TIMEOUT_ANSWER = "Request has been timed out"
PREFIX = "Note: "
SEPARATOR = "; "
CONFIRMED_HEADER = "Confirmed figures from the booking system (these are correct if anything above differs):"

async def run_agent(question, user_id, ask_model, clock=datetime.now) -> AgentResult:
    start=clock()
    messages = [
            {"role": "system", "content": build_system_prompt(start)},
            {"role": "user", "content": question},
        ]
    state = AgentState(messages=messages, started_at = start)
    logger.info("agent start: user=%s", user_id)
    reply = await ask_model(state.messages)
    state.messages.append(reply)
    tool_calls = requests_from(reply)
    while tool_calls:
        elapsed = state.elapsed(clock())
        if elapsed > DEADLINE_SECONDS:
            logger.warning("agent stop: timeout after %.1fs, %d tool calls", elapsed, state.tool_call_count)
            return AgentResult(answer=TIMEOUT_ANSWER, stop_reason="timeout", tool_calls=state.tool_calls)
        for request in tool_calls:
            if state.tool_call_count >= MAX_TOOL_CALLS:
                logger.warning("agent stop: too_many_calls at limit %d", MAX_TOOL_CALLS)
                return AgentResult(answer=MAX_TOOL_CALLS_ANSWER, stop_reason="too_many_calls", tool_calls=state.tool_calls)
            
            name = request["function"]["name"]
            arguments = request["function"]["arguments"]
            if state.has_called(name,arguments):
                logger.info("agent skip duplicate: %s %s", name, arguments)
                state.messages.append({"role": "tool", "content": HAS_CALLED_TOOL_ANSWER})
                continue
            logger.info("agent tool: %s %s", name, arguments)
            observation = execute_tool(name, arguments,user_id)
            state.record_call(name, arguments, observation)
            state.messages.append({"role": "tool", "content": observation})
        reply= await ask_model(state.messages)
        state.messages.append(reply)
        tool_calls = requests_from(reply)
    logger.info("agent done: answered after %d tool calls", state.tool_call_count)
    answer= reply["content"]
    facts = missing_facts(state.tool_calls, answer)
    texts = [fact.text for fact in facts]
    if texts:
        logger.warning("%d facts missing from answer: %s", len(texts), texts)
        answer = answer + "\n\n" + PREFIX + SEPARATOR.join(texts)
    summaries = quote_summaries(state.tool_calls)
    if summaries:
        answer = answer + "\n\n" + CONFIRMED_HEADER + "".join(f"\n- {line}" for line in summaries)
    return AgentResult(answer=answer, stop_reason="answered", tool_calls=state.tool_calls)

def requests_from(reply) -> list[dict]:
    real = reply.get("tool_calls") or []
    if not real:
        real = tool_calls_from_text(reply.get("content"))
        if real:
            logger.warning("agent recovered tool call from text: %s", real[0]["function"]["name"])
    return real
