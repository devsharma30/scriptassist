# this is the main file of our project, it will run the whole project.


# THIS FILE:
#   1. Shows a welcome banner
#   2. Runs an infinite loop: ask for task → generate → safety check
#      → execute → log → repeat
#   3. Maintains conversation history so follow-up tasks work
#   4. Handles special commands: 'history', 'clear', 'quit'


# ARCHITECTURE OVERVIEW:
#   main.py → calls → llm_caller.py (generate script)
#          → calls → safety.py     (show code, ask permission)
#          → calls → executor.py   (run script, retry on failure)
#          → calls → logger.py     (save log)

import sys   # sys.exit() to quit cleanly

from llm_caller import generate_script
from safety import ask_user_permission
from executor import run_with_retry
from logger import log_run, get_recent_logs


# ── ANSI colors ──────────────────────────────────────────────
# These are used to make the terminal output more readable and visually appealing.
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BLUE = "\033[34m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── Special commands the user can type ────────────────────────
# Instead of a task, typing these triggers special actions.
QUIT_COMMANDS = {"quit", "exit", "q", ":q"}  # ":q" for vim users :)
HISTORY_COMMANDS = {"history", "logs", "h"}
CLEAR_COMMANDS = {"clear", "cls", "new"}

# ── Max conversation history to send to LLM ──────────────────
# Sending too much history = more tokens = more cost.
# 6 messages = 3 rounds of conversation (user + assistant pairs)
MAX_HISTORY_PAIRS = 6


def print_banner() -> None:
    """
    Prints the welcome banner when the tool starts.
    Uses ANSI colors and box-drawing characters (─, ╔, ║, etc.)
    for a professional terminal look.
    """
    banner = f"""
{CYAN}{BOLD}
╔══════════════════════════════════════════════════════╗
║           ScriptAssist — AI Terminal Tool             ║
║     Describe a task → get Python code → run it       ║
╚══════════════════════════════════════════════════════╝{RESET}
 
{DIM}Commands:{RESET}
  {YELLOW}any text{RESET}     →  generate & run a script
  {YELLOW}history{RESET}      →  show recent logs
  {YELLOW}clear{RESET}        →  clear conversation history
  {YELLOW}quit{RESET}         →  exit
 
{DIM}Example tasks:{RESET}
  "List all PDF files in my Downloads folder"
  "Rename all .jpeg files to .jpg in current folder"
  "Delete .log files older than 7 days from /tmp"
  "Show total size of each subfolder in current directory"
"""
    print(banner)


def print_history_summary(conversation_history: list) -> None:
    """
    Shows recent log files so the user can see their past runs.
    """
    recent = get_recent_logs(n=5)
    if not recent:
        print(f"\n{DIM}No logs yet.{RESET}\n")
        return

    print(f"\n{CYAN}── Recent runs ─────────────────────────{RESET}")
    for path in recent:
        # path.name = just the filename, without the directory
        # path.stat().st_size = file size in bytes
        size_kb = path.stat().st_size / 1024   # convert bytes → KB
        print(f"  {DIM}{path.name}{RESET}  ({size_kb:.1f} KB)")
    print(f"{CYAN}────────────────────────────────────────{RESET}")
    print(f"{DIM}Logs saved in: ~/.scriptassist_logs/{RESET}\n")


def trim_history(history: list) -> list:
    """
    Keeps only the most recent MAX_HISTORY_PAIRS exchanges.

    Each "exchange" = 2 messages: user + assistant.
    So MAX_HISTORY_PAIRS * 2 = max messages we keep.

    WHY TRIM?
        AI platforms charges per token (word fragment).
        A very long history makes every call expensive.
        We keep only recent context — enough for follow-up tasks.
    """
    max_messages = MAX_HISTORY_PAIRS * 2
    if len(history) > max_messages:
        # list[-n:] = last n items
        # If history has 20 items and max is 12, return last 12
        return history[-max_messages:]
    return history


def main() -> None:
    """
    The main loop of the application.

    PYTHON CONCEPT — while True:
        An infinite loop. Runs forever until we explicitly call
        'break' (to exit the loop) or sys.exit() (to quit entirely).
        This is the standard pattern for CLI tools that keep running
        until the user types 'quit'.
    """
    print_banner()

    # conversation_history stores the exchange history for context.
    # Format: [
    #   {"role": "user",      "content": "the task"},
    #   {"role": "assistant", "content": "the generated script"},
    #   ...
    # ]
    # This is what makes follow-up tasks work:
    # "do the same for .txt files" requires context of previous task.
    conversation_history: list = []

    while True:
        # ── Prompt the user ───────────────────────────────────
        try:
            raw_input = input(f"\n{GREEN}{BOLD}❯ {RESET}").strip()

        except (KeyboardInterrupt, EOFError):
            # KeyboardInterrupt: user pressed Ctrl+C
            # EOFError: input stream ended (e.g. piped input)
            # Both should exit cleanly
            print(f"\n\n{DIM}Goodbye!{RESET}\n")
            sys.exit(0)

        # ── Handle empty input ────────────────────────────────
        if not raw_input:
            continue

        # .lower() so "QUIT", "Quit", "quit" all work
        command = raw_input.lower()

        # ── Handle special commands ───────────────────────────
        if command in QUIT_COMMANDS:
            print(f"\n{DIM}Goodbye!{RESET}\n")
            sys.exit(0)

        if command in HISTORY_COMMANDS:
            print_history_summary(conversation_history)
            continue

        if command in CLEAR_COMMANDS:
            conversation_history = []   # reset to empty list
            print(f"{DIM}Conversation history cleared.{RESET}")
            continue

        # ── Main flow: Generate → Check → Execute → Log ───────
        task = raw_input   # the user's plain-English task

        # STEP 1: Generate script from LLM
        # ─────────────────────────────────
        try:
            script = generate_script(task, conversation_history)
        except Exception as e:
            # Exception is the base class for all Python errors.
            # 'as e' binds the exception object to the name 'e'.
            # str(e) converts the exception to a readable message.
            print(f"\n{RED}❌  LLM API error: {str(e)}{RESET}")
            print(f"{DIM}Check your API key and internet connection.{RESET}")
            continue

        # STEP 2: Safety check — show code, ask permission
        # ─────────────────────────────────────────────────
        approved = ask_user_permission(script)

        if not approved:
            print(f"{YELLOW}Script cancelled.{RESET}")
            continue

        # STEP 3: Execute the script (with one retry on failure)
        # ───────────────────────────────────────────────────────
        try:
            success, final_script = run_with_retry(
                script=script,
                original_task=task,
                conversation_history=conversation_history,
            )
        except Exception as e:
            print(f"\n{RED}❌  Execution error: {str(e)}{RESET}")
            success = False
            final_script = script

        # STEP 4: Update conversation history
        # ─────────────────────────────────────
        # Append user task and the final script (fixed or original)
        # so the next task has context.
        conversation_history.append({"role": "user",      "content": task})
        conversation_history.append(
            {"role": "assistant", "content": final_script})
        conversation_history = trim_history(conversation_history)

        # STEP 5: Log the run
        # ─────────────────────
        try:
            log_path = log_run(task=task, script=final_script, success=success)
            print(f"\n{DIM}📝  Log saved: {log_path.name}{RESET}")
        except Exception as e:
            # Logging failure should NEVER crash the main app.
            # It's a nice-to-have, not critical.
            print(f"{DIM}(Logging failed: {e}){RESET}")


#   This pattern ensures that main() only runs when you execute
#   this file directly — NOT when it's imported as a module.
if __name__ == "__main__":
    main()
