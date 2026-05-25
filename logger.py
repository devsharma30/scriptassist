import os
from datetime import datetime
from pathlib import Path


# ── Where logs are stored ─────────────────────────────────────
# Path.home() → returns your home directory as a Path object
# / is overloaded for Path objects — it joins paths cleanly:
# Path("/home/user") / ".scriptassist_logs" → Path("/home/user/.scriptassist_logs")
LOG_DIR = Path.home() / ".scriptassist_logs"


def _ensure_log_dir() -> None:
    """
    Creates the log directory if it doesn't exist yet.
    mkdir(parents=True) creates parent dirs too.
    exist_ok=True means "don't crash if it already exists".
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_run(task: str,
            script: str,
            success: bool,
            stdout: str = "",
            stderr: str = "") -> Path:
    """
    Saves a complete run to a timestamped log file.

    Parameters:
        task (str): The original user task description
        script (str): The generated Python script
        success (bool): Whether execution succeeded
        stdout (str): Script's standard output
        stderr (str): Script's error output

    Returns:
        Path: The path where the log was saved

    PYTHON CONCEPT — Default parameter values:
        stdout: str = ""   means: if you call log_run(task, script, True)
        without passing stdout, it defaults to empty string.
    """
    _ensure_log_dir()

    # datetime.now() → current date and time
    # .strftime(format) → formats it as a string
    # "%Y-%m-%d_%H-%M-%S" → "2024-01-15_14-30-22"

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # year-month-day_hour-minute-second

    log_path = LOG_DIR / f"{timestamp}.log"

    # Build the log content as a multiline string
    # "=" * 60 → "============================================================"
    status_label = "SUCCESS" if success else "FAILURE"

    content = f"""ScriptAssist Log
{'=' * 60}
Timestamp : {timestamp}
Status    : {status_label}
{'=' * 60}
 
TASK:
{task}
 
GENERATED SCRIPT:
{'-' * 40}
{script}
{'-' * 40}
"""

    if stdout.strip():
        content += f"\nSTDOUT:\n{stdout}\n"

    if stderr.strip():
        content += f"\nSTDERR:\n{stderr}\n"

    # Write the log to disk
    # Path objects have a .write_text() method — no need to open/close
    log_path.write_text(content, encoding="utf-8")

    return log_path

# gives paths of 5 recent logs to us in a form of list of Path objects.


def get_recent_logs(n: int = 5) -> list[Path]:
    """
    Returns the n most recent log file paths.

    sorted() sorts a list. key=... tells it what to sort by.
    os.path.getmtime() returns the file modification time.
    reverse=True → newest first.
    [:n] → take only the first n items (Python list slicing)
    """
    _ensure_log_dir()

    # LOG_DIR.glob("*.log") → generator of all .log files in LOG_DIR
    # We convert to list so we can sort it
    all_logs = list(LOG_DIR.glob("*.log"))
    # all_logs is a list of Path objects representing log files.

    sorted_logs = sorted(
        all_logs, key=lambda p: p.stat().st_mtime, reverse=True)

    # lambda p: p.stat().st_mtime
    # lambda = anonymous one-line function: lambda [args]: [expression]
    # p.stat().st_mtime = file's last modification time (Unix timestamp)

    return sorted_logs[:n]
