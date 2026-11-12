import os
import shutil
import psutil
import datetime
import subprocess
from typing import Optional, Dict, Any, List
from jarvis_system.tools.registry import tool
from jarvis_system.config import JarvisConfig

@tool(
    name="run_terminal_command",
    description="Execute a bash shell command directly on the host system. Use this to run scripts, git commands, check processes, install packages, etc."
)
def run_terminal_command(command: str, timeout_seconds: int = 60, cwd: Optional[str] = None) -> str:
    if not JarvisConfig.SYSTEM_ACCESS_ENABLED:
        return "Error: System access is currently disabled in JarvisConfig."

    work_dir = cwd or JarvisConfig.DEFAULT_WORKING_DIR
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=work_dir
        )
        output = proc.stdout
        if proc.stderr:
            if output:
                output += "\n--- STDERR ---\n" + proc.stderr
            else:
                output = proc.stderr

        return json_format({
            "command": command,
            "exit_code": proc.returncode,
            "cwd": work_dir,
            "output": output.strip() or "(No output)"
        })
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout_seconds} seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

@tool(
    name="get_system_status",
    description="Retrieve live hardware and operating system status: CPU, RAM, Disk, NVIDIA GPU VRAM/temperature, battery, and uptime."
)
def get_system_status() -> str:
    try:
        # CPU
        cpu_pct = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count(logical=True)

        # Memory
        mem = psutil.virtual_memory()
        mem_used_gb = round(mem.used / (1024 ** 3), 2)
        mem_total_gb = round(mem.total / (1024 ** 3), 2)

        # Disk
        disk = psutil.disk_usage("/")
        disk_used_gb = round(disk.used / (1024 ** 3), 2)
        disk_total_gb = round(disk.total / (1024 ** 3), 2)

        # Battery
        battery = psutil.sensors_battery()
        battery_info = f"{round(battery.percent)}% ({'Charging' if battery.power_plugged else 'Discharging'})" if battery else "AC Powered (No Battery detected)"

        # GPU via nvidia-smi
        gpu_info = "N/A"
        if shutil.which("nvidia-smi"):
            try:
                gpu_proc = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5
                )
                if gpu_proc.returncode == 0:
                    parts = [p.strip() for p in gpu_proc.stdout.strip().split(",")]
                    if len(parts) >= 5:
                        gpu_info = f"{parts[0]} | VRAM: {parts[1]}MB / {parts[2]}MB | Load: {parts[3]}% | Temp: {parts[4]}°C"
            except Exception:
                pass

        # Uptime
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = str(datetime.datetime.now() - boot_time).split(".")[0]

        return json_format({
            "os_user": os.getenv("USER", "user"),
            "system_uptime": uptime,
            "cpu_usage": f"{cpu_pct}% ({cpu_count} cores)",
            "ram_usage": f"{mem_used_gb} GB / {mem_total_gb} GB ({mem.percent}%)",
            "disk_root_usage": f"{disk_used_gb} GB / {disk_total_gb} GB ({disk.percent}%)",
            "gpu_status": gpu_info,
            "battery_status": battery_info
        })
    except Exception as e:
        return f"Error gathering system status: {str(e)}"

@tool(
    name="open_application_or_url",
    description="Launch an application or open a URL/file on the host desktop (e.g. 'https://github.com', 'google-chrome', 'code .', or a file path)."
)
def open_application_or_url(target: str) -> str:
    try:
        # Check if xdg-open works
        subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Successfully opened '{target}' on desktop."
    except Exception as e:
        return f"Failed to open '{target}': {str(e)}"

@tool(
    name="control_volume",
    description="Set the master audio volume level (0 to 100 percent)."
)
def control_volume(level_percent: int) -> str:
    level = max(0, min(100, level_percent))
    try:
        if shutil.which("pactl"):
            proc = subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"], capture_output=True, text=True)
            if proc.returncode == 0:
                return f"System volume set to {level}%."
        elif shutil.which("amixer"):
            proc = subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"], capture_output=True, text=True)
            if proc.returncode == 0:
                return f"System volume set to {level}% via amixer."
        return "Could not adjust volume: neither pactl nor amixer responded successfully."
    except Exception as e:
        return f"Error setting volume: {str(e)}"

@tool(
    name="send_desktop_notification",
    description="Display a native Linux desktop banner notification to the user."
)
def send_desktop_notification(title: str, message: str) -> str:
    try:
        if shutil.which("notify-send"):
            subprocess.run(["notify-send", title, message])
            return f"Notification displayed: '{title} - {message}'"
        return "notify-send is not installed."
    except Exception as e:
        return f"Error sending notification: {str(e)}"

@tool(
    name="list_active_processes",
    description="List active processes currently running on the system, optionally filtered by name."
)
def list_active_processes(search_keyword: Optional[str] = None, limit: int = 15) -> str:
    try:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                if search_keyword:
                    if search_keyword.lower() not in (info['name'] or '').lower():
                        continue
                procs.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "user": info['username'],
                    "cpu_pct": round(info['cpu_percent'] or 0, 1),
                    "mem_pct": round(info['memory_percent'] or 0, 1)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: x['cpu_pct'], reverse=True)
        return json_format(procs[:limit])
    except Exception as e:
        return f"Error listing processes: {str(e)}"

def json_format(data: Any) -> str:
    import json
    return json.dumps(data, indent=2, default=str)
