from pydantic import ValidationError
import logging
from app.tools.registry import TOOLS
from app.mock_backend.bookings import BookingNotFoundError

logger = logging.getLogger(__name__)

def execute_tool(name:str,arguments:dict,user_id:str) ->str:
    """ function to execute required tool for the model"""
    
    if name not in TOOLS:
        return f"Unknown tool '{name}'"
    spec = TOOLS[name]
    try:
        validated = spec.args_model.model_validate(arguments)
    except ValidationError as error:
        return f"Invalid arguments for '{name}': {error}"
    try:
        result = spec.func(**validated.model_dump(), user_id=user_id)
    except BookingNotFoundError as error:
        return f"Error: {error}"
    except Exception:
        logger.exception("tool %s crashed", name)
        return f"Tool '{name}' failed. Try again or tell the user it is unavailable."
    return result.model_dump_json()