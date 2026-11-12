import sys
import subprocess
from typing import Optional
from jarvis_system.tools.registry import tool

@tool(
    name="run_python_code",
    description="Execute Python code in a dedicated subprocess and return the standard output or error. Perfect for quick calculations, data parsing, or logic verification."
)
def run_python_code(code: str, timeout_seconds: int = 30) -> str:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )
        output = proc.stdout
        if proc.stderr:
            output += "\n--- STDERR ---\n" + proc.stderr
        return output.strip() or "(Executed successfully with no output)"
    except subprocess.TimeoutExpired:
        return f"Error: Code execution timed out after {timeout_seconds} seconds."
    except Exception as e:
        return f"Error running Python code: {str(e)}"
