import inspect
import json
import logging
from typing import Callable, Dict, Any, List, Optional, get_type_hints

logger = logging.getLogger("JARVIS.Tools")

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

def _python_type_to_json_type(py_type) -> str:
    if py_type in (str, Optional[str]):
        return "string"
    elif py_type in (int, Optional[int]):
        return "integer"
    elif py_type in (float, Optional[float]):
        return "number"
    elif py_type in (bool, Optional[bool]):
        return "boolean"
    elif py_type in (list, List, Optional[list], Optional[List]):
        return "array"
    elif py_type in (dict, Dict, Optional[dict], Optional[Dict]):
        return "object"
    return "string"

def tool(name: Optional[str] = None, description: Optional[str] = None):
    """
    Decorator to register a function as an LLM-accessible tool.
    Automatically generates the OpenAI Tool Calling JSON schema.
    """
    def decorator(fn: Callable):
        tool_name = name or fn.__name__
        tool_doc = description or (inspect.getdoc(fn) or f"Execute {tool_name}").strip()
        
        sig = inspect.signature(fn)
        type_hints = get_type_hints(fn) if hasattr(fn, "__annotations__") else {}
        
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = type_hints.get(param_name, str)
            json_type = _python_type_to_json_type(param_type)

            properties[param_name] = {
                "type": json_type,
                "description": f"Parameter {param_name}"
            }

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        schema = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_doc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

        TOOL_REGISTRY[tool_name] = {
            "name": tool_name,
            "description": tool_doc,
            "fn": fn,
            "schema": schema
        }

        logger.debug(f"Registered tool: {tool_name}")
        return fn

    return decorator

def get_openai_tools() -> List[Dict[str, Any]]:
    """Returns the list of all registered tools in OpenAI format."""
    return [entry["schema"] for entry in TOOL_REGISTRY.values()]

def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Executes a registered tool by name with arguments, returning a string result."""
    if name not in TOOL_REGISTRY:
        return f"Error: Tool '{name}' is not registered."

    entry = TOOL_REGISTRY[name]
    fn = entry["fn"]

    try:
        logger.info(f"Executing tool '{name}' with arguments: {arguments}")
        result = fn(**arguments)
        if isinstance(result, (dict, list)):
            return json.dumps(result, indent=2, default=str)
        return str(result)
    except Exception as e:
        logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
        return f"Error executing '{name}': {str(e)}"
