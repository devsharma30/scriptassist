# executor.py —> Runs the generated script + handles retry

# subprocess.run() executes a command as if you typed it in the terminal and WAITS for it to finish.

# our flow in this file is:
#   1. Write script to a temp .py file
#   2. Run it with subprocess.run()
#   3. If success → show output → done
#   4. If failure → pass traceback to LLM → get fix → run fix once


import subprocess
import tempfile
import os
import sys

from llmcaller import generate_fix

# ── ANSI colors ──────────────────────────────────────────────
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _write_temp_script(script: str) -> str:
    """
    Writes a Python script string to a temporary file.
    Returns the file path.

    WHY TEMPFILE?
        If we wrote to a fixed path like /tmp/script.py, two
        simultaneous runs would overwrite each other. tempfile
        generates a unique name every time (e.g. /tmp/tmpXk9mR.py).

    PYTHON CONCEPT — with statement (context manager):
        'with open(path) as f:' automatically closes the file
        when the block exits — even if an error occurs.
        Always use 'with' when opening files.
    """
    # tempfile.NamedTemporaryFile creates a temp file.
    # delete=False → don't delete it immediately (we need to run it first)
    # suffix=".py"  → give it a .py extension so Python recognizes it
    # mode="w"      → open for writing text (not binary)

    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".py",
        mode="w",
        encoding="utf-8",
    )

    with tmp:
        tmp.write(script)

    return tmp.name         # return the path, e.g. "/tmp/tmpXk9.py"


def _delete_temp_file(path: str) -> None:
    """
    Deletes the temporary script file after execution.
    Wrapped in try/except because deletion can fail (permission error,
    file already gone) and we don't want that to crash the main app.
    """
    try:
        os.remove(path)
    except OSError:
        pass


def run_script(script: str) -> dict:
    """
    Runs a Python script string and returns the result.

    Returns a dict with:
        {
            "success":  bool,      # True if returncode == 0
            "stdout":   str,       # everything the script printed
            "stderr":   str,       # error messages (traceback)
            "returncode": int,     # 0 = success, non-zero = error
        }

    CONCEPT — Exit / return codes:
        When any program finishes, it returns a number to the OS.
        0 = success (universally)
        1, 2, ... = various errors
        Python raises an exception → returncode = 1
        This is how subprocess.run knows if the script crashed.
    """

    temp_path = _write_temp_script(script)

    print(f"\n{CYAN}▶   Running script...{RESET}")

    try:
        # [sys.executable, temp_path]
        #   sys.executable → full path to current Python binary
        #     e.g. "/usr/bin/python3" or "C:\Python311\python.exe"
        #   We use sys.executable instead of just "python" because:
        #     - "python" might point to Python 2 on some systems
        #     - sys.executable always points to the SAME Python that
        #       is running scriptassist right now (same version,
        #       same installed packages)
        #   temp_path → the file we just wrote
        #
        # capture_output=True
        #   Captures stdout (normal print output) AND stderr
        #   (error messages) into result.stdout and result.stderr
        #   Without this, output just goes to the terminal and we
        #   can't programmatically check what happened.
        #
        # text=True
        #   Returns stdout/stderr as strings instead of bytes.
        #   Without this: b"Hello\n" (bytes literal)
        #   With this: "Hello\n" (regular string)
        #
        # timeout=60
        #   If the script runs for more than 60 seconds, kill it.
        #   This prevents infinite loops from hanging the tool.
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=60,
        )

        return {
            "success":    result.returncode == 0,
            "stdout":     result.stdout,
            "stderr":     result.stderr,
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        # This fires if the script runs > 60 seconds
        return {
            "success":    False,
            "stdout":     "",
            "stderr":     "Script timed out after 60 seconds.",
            "returncode": -1,
        }

    finally:
        # 'finally' runs NO MATTER WHAT — even if an exception occurs.
        # Perfect for cleanup code like deleting the temp file.
        _delete_temp_file(temp_path)


def show_output(result: dict) -> None:
    """
    Prints the script's output to the terminal in a readable way.
    Shows stdout on success, stderr on failure.
    """
    if result["success"]:
        print(f"\n{GREEN}{BOLD}✅  Script completed successfully!{RESET}")
        if result["stdout"].strip():
            print(f"\n{DIM}── Script output ──────────────────────{RESET}")
            # .rstrip() removes trailing newlines
            print(result["stdout"].rstrip())
            print(f"{DIM}───────────────────────────────────────{RESET}")
    else:
        print(
            f"\n{RED}{BOLD}❌  Script failed (exit code {result['returncode']}){RESET}")
        if result["stderr"].strip():
            print(f"\n{RED}── Error output ───────────────────────{RESET}")
            print(result["stderr"].rstrip())
            print(f"{RED}───────────────────────────────────────{RESET}")


def run_with_retry(script: str,
                   original_task: str,
                   conversation_history: list) -> tuple[bool, str]:
    """
    Runs a script. If it fails, asks the LLM to fix it and tries once more.

    Parameters:
        script (str): The generated script to run
        original_task (str): Original user task (for the fix prompt)
        conversation_history (list): Previous conversation context

    Returns:
        tuple[bool, str]:
            (True, final_script)  if execution succeeded
            (False, final_script) if both attempts failed

    PYTHON CONCEPT — Tuple return:
        Functions can return multiple values as a tuple.
        success, script = run_with_retry(...)
        This is called "tuple unpacking" — very Pythonic.
    """

    # ── First attempt ─────────────────────────────────────────
    result = run_script(script)
    show_output(result)

    if result["success"]:
        return True, script   # Return immediately on success

    # ── Script failed — attempt a fix ────────────────────────
    print(f"\n{YELLOW}⚡  Attempting automatic fix (1 retry)...{RESET}")

    # Build the error context: combine stdout + stderr
    # because sometimes the actual error shows in stdout
    full_error = ""
    if result["stdout"]:
        full_error += f"STDOUT:\n{result['stdout']}\n"
    if result["stderr"]:
        full_error += f"STDERR:\n{result['stderr']}\n"

    # Ask LLM for a fix
    fixed_script = generate_fix(
        original_task=original_task,
        broken_script=script,
        traceback=full_error,
        conversation_history=conversation_history,
    )

    print(f"\n{CYAN}── Fixed script ────────────────────────{RESET}")
    for i, line in enumerate(fixed_script.split("\n"), 1):
        print(f"{YELLOW}{i:3d}{RESET}  {line}")
    print(f"{CYAN}───────────────────────────────────────{RESET}")

    # Ask user if they want to run the fix
    answer = input(
        f"\n{BOLD}Run the fixed script? [yes/no]: {RESET}").strip().lower()
    if answer not in ("yes", "y"):
        print(f"{YELLOW}Skipped.{RESET}")
        return False, fixed_script

    # ── Second attempt ────────────────────────────────────────
    result2 = run_script(fixed_script)
    show_output(result2)

    if result2["success"]:
        return True, fixed_script
    else:
        print(
            f"\n{RED}Both attempts failed. Please refine your task description.{RESET}")
        return False, fixed_script
