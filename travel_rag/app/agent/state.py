
from dataclasses import dataclass, field
from datetime import datetime

import json

@dataclass(frozen=True)
class ToolCallRecord:
    name: str
    arguments: dict
    result: str
    key:str

@dataclass
class AgentState:
    messages: list[dict]
    started_at:datetime
    tool_calls: list[ToolCallRecord] = field(default_factory=list)

    @property
    def tool_call_count(self) ->int:
        return len(self.tool_calls)

    def has_called(self,name:str,arguments:dict) ->bool:
        key= call_key(name,arguments)
        for record in self.tool_calls:
            if record.key == key:
                return True
        return False
    
    def elapsed(self,now:datetime) ->float:
        return (now-self.started_at).total_seconds()

    def record_call(self,name:str,arguments:dict,result:str) -> None:
        key= call_key(name,arguments)
        self.tool_calls.append(
            ToolCallRecord(
                name = name,
                arguments = arguments,
                result = result,
                key = key
            )
        )

def call_key(name:str, arguments:dict) -> str:
    return f"{name}: {json.dumps(arguments, sort_keys=True)}"
