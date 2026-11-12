# Import modules to trigger the @tool decorator registrations
from jarvis_system.tools.registry import TOOL_REGISTRY, tool, get_openai_tools, execute_tool
import jarvis_system.tools.system_tools
import jarvis_system.tools.file_tools
import jarvis_system.tools.python_tools
import jarvis_system.tools.gmail_tools
import jarvis_system.tools.calendar_tools
import jarvis_system.tools.whatsapp_tools

__all__ = ["TOOL_REGISTRY", "tool", "get_openai_tools", "execute_tool"]
