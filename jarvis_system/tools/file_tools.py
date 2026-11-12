import os
import glob
from pathlib import Path
from typing import Optional, List, Dict, Any
from jarvis_system.tools.registry import tool
from jarvis_system.config import JarvisConfig

def _resolve_path(path_str: str) -> Path:
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = Path(JarvisConfig.DEFAULT_WORKING_DIR) / p
    return p.resolve()

@tool(
    name="read_file",
    description="Read the text content of a file on the system. Supports line limiting."
)
def read_file(file_path: str, max_lines: int = 300) -> str:
    path = _resolve_path(file_path)
    if not path.exists():
        return f"Error: File '{file_path}' does not exist."
    if not path.is_file():
        return f"Error: Path '{file_path}' is not a regular file."

    try:
        lines = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... [Truncated: reached limit of {max_lines} lines] ...")
                    break
                lines.append(line)
        return "".join(lines)
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"

@tool(
    name="write_file",
    description="Write or append text content to a file. Automatically creates any missing parent directories."
)
def write_file(file_path: str, content: str, append: bool = False) -> str:
    path = _resolve_path(file_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
        action = "Appended to" if append else "Created/Overwrote"
        return f"Successfully {action} file '{path}' ({len(content)} characters)."
    except Exception as e:
        return f"Error writing to file '{file_path}': {str(e)}"

@tool(
    name="list_directory",
    description="List files and folders in a directory with file sizes and type indicators."
)
def list_directory(directory_path: str = ".", show_hidden: bool = False) -> str:
    path = _resolve_path(directory_path)
    if not path.exists():
        return f"Error: Directory '{directory_path}' does not exist."
    if not path.is_dir():
        return f"Error: Path '{directory_path}' is not a directory."

    try:
        items = []
        for entry in os.scandir(path):
            if not show_hidden and entry.name.startswith("."):
                continue
            try:
                stat = entry.stat()
                is_dir = entry.is_dir()
                size_str = "<DIR>" if is_dir else f"{stat.st_size} bytes"
                items.append({
                    "name": entry.name,
                    "type": "directory" if is_dir else "file",
                    "size": size_str
                })
            except Exception:
                continue

        items.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
        import json
        return json.dumps({"directory": str(path), "total_items": len(items), "entries": items}, indent=2)
    except Exception as e:
        return f"Error listing directory '{directory_path}': {str(e)}"

@tool(
    name="search_files",
    description="Search for files by name pattern (e.g. '*.py', '*config*') inside a directory recursively."
)
def search_files(directory_path: str, filename_pattern: str, max_results: int = 30) -> str:
    path = _resolve_path(directory_path)
    if not path.exists():
        return f"Error: Path '{directory_path}' does not exist."

    try:
        pattern = str(path / "**" / filename_pattern)
        matches = []
        for file in glob.iglob(pattern, recursive=True):
            matches.append(file)
            if len(matches) >= max_results:
                break

        import json
        return json.dumps({
            "search_path": str(path),
            "pattern": filename_pattern,
            "count": len(matches),
            "matches": matches
        }, indent=2)
    except Exception as e:
        return f"Error searching files: {str(e)}"
