from app.agent.completeness import parse_result
from app.tools.registry import TOOLS

def tool_calls_from_text(content:str) -> list[dict]:
    if not content:
        return []
    data = parse_result(content)
    if data is None:
        return []
    tool_name =data.get("name")
    tool_arguments = data.get("arguments") or data.get("parameters")
    if not isinstance(tool_name,str):
        return []
    if tool_name not in TOOLS:
        return []
    if not isinstance(tool_arguments,dict):
        return []
    return [ {"function": {"name": tool_name, "arguments":tool_arguments}} ]
