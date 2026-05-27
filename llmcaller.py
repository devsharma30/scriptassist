from groq import Groq
# Groq's official Python library
from config import GROQ_API_KEY

# ── Create the Groq client ────────────────────────────────────
# Groq() creates a client object — same pattern as OpenAI.
# All API calls go through this client.
client = Groq(api_key=GROQ_API_KEY)


# model that we are using
MODEL = "llama-3.3-70b-versatile"

# ── ANSI colors ──
CYAN = "\033[36m"
RESET = "\033[0m"


# ── The System Prompt ─────────────────────────────────────────
# This is the instruction we give the AI about HOW to behave.
# Gemini supports system instructions separately from user input.

SYSTEM_PROMPT = """You are a Python scripting assistant for local filesystem automation.
 
Your job: convert the user's plain-English task into a single, executable Python script.
 
STRICT OUTPUT RULES:
- Return ONLY raw Python code. No markdown. No ```python```. No explanations.
- The output must be directly runnable with `python script.py`
- Do not include any text before or after the code.
 
SAFETY RULES (always follow these):
- For any operation that DELETES or MODIFIES files:
    1. First print what would be affected (dry-run preview)
    2. Then ask: input("Proceed? [yes/no]: ")
    3. Only proceed if user types 'yes' or 'y'
- Never delete files without showing the list first.
- Use try/except around risky operations and print clear error messages.
 
CODE QUALITY RULES:
- Use os, shutil, glob, pathlib — standard library only.
- Add a comment on each non-obvious line.
- Print progress messages so the user knows what's happening.
- At the end, print a clear summary: how many files processed, etc.
- Do not make network requests unless the user explicitly asks.
"""


def generate_script(task: str, conversation_history: list) -> str:
    """
    Sends the user's task to Groq and returns a Python script.

    Parameters:
        task (str): Plain-English description
        conversation_history (list): Previous messages for context

    Returns:
        str: The generated Python script as a plain string
    """
    print(f"\n{CYAN}⏳  Asking Groq to generate script...{RESET}")

    # Build the messages list.
    # system message = instructions for the AI
    # conversation_history = previous exchanges for context
    # user message = current task
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *conversation_history,              # unpack history into list
        {"role": "user",   "content": task},
    ]

    # ── The actual API call ───────────────────────────────────
    # Groq uses exact same interface as OpenAI.
    # client.chat.completions.create() sends the request.
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2,       # low = more deterministic code
        max_tokens=1500,       # cap response length
    )

    # ── Parse the response ────────────────────────────────────
    # Same navigation as OpenAI:
    # response.choices[0].message.content = the generated text
    script = response.choices[0].message.content.strip()
    script = _strip_code_fences(script)
    return script


def generate_fix(original_task: str,
                 broken_script: str,
                 traceback: str,
                 conversation_history: list) -> str:
    """
    When a script fails, sends the error back to Groq
    and asks for a single-shot fix.

    Parameters:
        original_task (str): What the user originally wanted
        broken_script (str): The script that failed
        traceback (str): The error output from Python
        conversation_history (list): Previous context

    Returns:
        str: A fixed Python script
    """
    print(f"\n{CYAN}⏳  Asking Groq to fix the error...{RESET}")

    fix_prompt = f"""The following Python script failed to execute.
 
ORIGINAL TASK:
{original_task}
 
SCRIPT THAT FAILED:
{broken_script}
 
ERROR TRACEBACK:
{traceback}
 
Please fix the script. Return ONLY the corrected Python code.
No explanations, no markdown, just the fixed code."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *conversation_history,
        {"role": "user", "content": fix_prompt},
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1,       # even lower for fixes — max determinism
        max_tokens=1500,
    )

    fixed_script = response.choices[0].message.content.strip()
    fixed_script = _strip_code_fences(fixed_script)
    return fixed_script


def _strip_code_fences(text: str) -> str:
    """
    Removes markdown code fences from Groq output.
    Groq sometimes wraps code in ```python ... ``` even
    when instructed not to. This cleans that up.
    """
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # Remove first line (```python)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Remove closing ```
        text = "\n".join(lines)
    return text.strip()
