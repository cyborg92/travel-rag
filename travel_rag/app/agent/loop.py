from app.agent.state import AgentState, ToolCallRecord
from app.agent.prompts import build_system_prompt
from app.tools.executor import execute_tool
from dataclasses import dataclass 
from datetime import datetime

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

async def run_agent(question, user_id, ask_model, clock=datetime.now) -> AgentResult:
    start=clock()
    messages = [
            {"role": "system", "content": build_system_prompt(start)},
            {"role": "user", "content": question},
        ]
    state = AgentState(messages=messages, started_at = start)
    reply = await ask_model(state.messages)
    state.messages.append(reply)
    tool_calls = reply.get("tool_calls") or []
    while tool_calls:
        if state.elapsed(clock()) > DEADLINE_SECONDS:
            return AgentResult(answer=TIMEOUT_ANSWER, stop_reason="timeout", tool_calls=state.tool_calls)
        for request in tool_calls:
            if state.tool_call_count >= MAX_TOOL_CALLS:
                return AgentResult(answer=MAX_TOOL_CALLS_ANSWER, stop_reason="too_many_calls", tool_calls=state.tool_calls)
            
            name = request["function"]["name"]
            arguments = request["function"]["arguments"]
            if state.has_called(name,arguments):
                state.messages.append({"role": "tool", "content": HAS_CALLED_TOOL_ANSWER})
                continue
            observation = execute_tool(name, arguments,user_id)
            state.record_call(name, arguments, observation)
            state.messages.append({"role": "tool", "content": observation})
        reply= await ask_model(state.messages)
        state.messages.append(reply)
        tool_calls = reply.get("tool_calls") or []
    return AgentResult(answer=reply["content"], stop_reason="answered", tool_calls=state.tool_calls)
