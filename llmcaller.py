import google.generativeai as genai
# Google's official Gemini library
from config import GEMINI_API_KEY

# genai.configure() sets the API key globally.
# All subsequent calls use this key automatically.
genai.configure(api_key=GEMINI_API_KEY)
# model that we are using
MODEL = "gemini-1.5-flash"

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
    Sends the user's task to Gemini and returns a Python script.

    Parameters:
        task (str): Plain-English description
        conversation_history (list): Previous messages for context

    Returns:
        str: The generated Python script as a plain string
    """
    print(f"\n{CYAN}⏳  Asking Gemini to generate script...{RESET}")

    # ── Build the full prompt ─────────────────────────────────
    # We combine the system prompt + conversation history + current task into one single prompt string.
    # This is how we give Gemini context of previous tasks.

    history_text = ""

    # if we have previous history then it will run
    # conversation_history is of [list] data type

    if conversation_history:
        history_text = "\n\nPREVIOUS CONVERSATION CONTEXT:\n"
        for msg in conversation_history:
            role = "User" if msg["role"] == "user" else "Assistant (script)"
            history_text += f"{role}: {msg['content']}\n\n"

    full_prompt = f"{SYSTEM_PROMPT}{history_text}\n\nCurrent task: {task}"

    # ── The actual Gemini API call ──────────────────
    # genai.GenerativeModel() creates a model instance.
    # .generate_content() sends the prompt and returns a response.

    model = genai.GenerativeModel(
        model_name=MODEL,
        # configuration for generation which include temperature and max token limit.token limit is set to 1500 which means the response will be capped at 1500 tokens. Temperature is set to 0.2 which means the output will be more deterministic and less random.
        generation_config={
            "temperature": 0.2,
            "max_output_tokens": 1500,
        }
    )

    response = model.generate_content(full_prompt)

    # now to Parse the response->
    # response.text is the generated text string directly.
    script = response.text.strip()

    # Clean up any markdown code fences the model might add
    script = _strip_code_fences(script)

    return script


def generate_fix(original_task: str,
                 broken_script: str,
                 traceback: str,
                 conversation_history: list) -> str:
    """
    When a script fails, sends the error back to Gemini
    and asks for a single-shot fix.

    Parameters:
        original_task (str): What the user originally wanted
        broken_script (str): The script that failed
        traceback (str): The error output from Python
        conversation_history (list): Previous context

    Returns:
        str: A fixed Python script
    """
    print(f"\n{CYAN}⏳  Asking Gemini to fix the error...{RESET}")

    fix_prompt = f"""{SYSTEM_PROMPT}
 
The following Python script failed to execute.
 
ORIGINAL TASK:
{original_task}
 
SCRIPT THAT FAILED:
{broken_script}
 
ERROR TRACEBACK:
{traceback}
 
Please fix the script. Return ONLY the corrected Python code.
No explanations, no markdown, just the fixed code."""

    model = genai.GenerativeModel(
        model_name=MODEL,
        generation_config={
            "temperature": 0.1,    # Even lower for fixes
            "max_output_tokens": 1500,
        }
    )

    response = model.generate_content(fix_prompt)
    fixed_script = response.text.strip()
    fixed_script = _strip_code_fences(fixed_script)
    return fixed_script


def _strip_code_fences(text: str) -> str:
    """
    Removes markdown code fences from Gemini output.
    Gemini sometimes wraps code in ```python ... ``` even
    when instructed not to. This cleans that up.
    """
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # Remove first line (```python)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Remove closing ```
        text = "\n".join(lines)
    return text.strip()
