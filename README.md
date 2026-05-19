<div align="center">

# 🤖 ScriptAssist

### LLM-Powered CLI Scripting Assistant

**Describe a task in plain English → AI generates Python code → Safety gate → Executes on your filesystem**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat)
![Status](https://img.shields.io/badge/Status-Active-22c55e?style=flat)
![IIT Guwahati](https://img.shields.io/badge/IIT-Guwahati-003366?style=flat)

</div>

---

## 📌 What is this?

**ScriptAssist** is a command-line AI agent that bridges natural language and filesystem automation. You type a task in plain English — the tool uses an LLM to generate a Python script, shows it to you for review, and executes it via subprocess with automatic error recovery.

This is a **minimal ReAct-style AI agent** (Reason → Act → Observe) built from scratch — the same architecture powering production tools like Devin and GitHub Copilot's terminal features, implemented with intentional safety constraints for real filesystem operations.

```
❯ Delete all .log files in /tmp older than 7 days

📄  Generated script:
────────────────────────────────────────────
  1  import os, glob
  2  from datetime import datetime, timedelta
  3
  4  # Dry-run: show files that would be deleted
  5  threshold = datetime.now() - timedelta(days=7)
  6  files = glob.glob("/tmp/*.log")
  7  old_files = [f for f in files if ...]
  8  print(f"Would delete {len(old_files)} file(s):")
  9  for f in old_files: print(f"  {f}")
 10
 11  confirm = input("Proceed? [yes/no]: ")
 12  if confirm.lower() == 'yes':
 13      for f in old_files: os.remove(f)
 14      print("Done.")
────────────────────────────────────────────

⚠️   WARNING — Dangerous operations detected:
  - os.remove

Run this script? [yes/no]: yes

▶   Running script...
✅  Script completed successfully!
📝  Log saved: 2024-01-15_14-30-22.log
```

---

## 🏗️ Architecture

```
User Input (plain English)
        │
        ▼
┌──────────────────┐
│   llm_caller.py  │  ← Calls OpenAI API with engineered system prompt
│   (The Brain)    │    Returns raw Python code string
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   safety.py      │  ← Scans for dangerous ops (os.remove, shutil.rmtree...)
│   (Safety Gate)  │    Shows code to user, requires explicit YES
└────────┬─────────┘
         │ approved
         ▼
┌──────────────────┐     failure    ┌─────────────────┐
│   executor.py    │ ─────────────► │  LLM Retry      │
│   (subprocess)   │                │  (traceback →   │
│                  │ ◄───────────── │   fixed script) │
└────────┬─────────┘   fixed once   └─────────────────┘
         │ success
         ▼
┌──────────────────┐
│   logger.py      │  ← Saves timestamped log: task + script + result
└──────────────────┘
```

**Files at a glance:**

| File | Responsibility |
|------|---------------|
| `main.py` | CLI loop, conversation history, ties everything together |
| `llm_caller.py` | OpenAI API calls, prompt engineering, code fence stripping |
| `executor.py` | `subprocess.run()` execution, temp file management, retry logic |
| `safety.py` | Dangerous pattern detection, user confirmation gate |
| `logger.py` | Timestamped session logs via `pathlib` |
| `config.py` | Secure API key loading via `python-dotenv` |

---

## ✨ Features

- **Natural language → executable Python** — no syntax knowledge required from the user
- **Multi-turn conversation memory** — follow-up tasks work contextually ("now do it for .txt files")
- **Safety gate before every execution** — dangerous operations (delete, overwrite, network) are flagged and require explicit confirmation
- **LLM-prompted dry-run mode** — system prompt instructs the model to preview actions before executing them
- **Automatic single-shot error recovery** — on failure, the full traceback is passed back to the LLM for a one-time fix attempt
- **Session logging** — every run is saved to `~/.scriptassist_logs/` with timestamp, task, generated script, and output
- **Conversation trimming** — history is capped to prevent token overuse and context window overflow

---

## 🛡️ Safety Design

Real filesystem operations require careful safety thinking. Every design decision here solves a specific failure mode:

| Safety Feature | What failure it prevents |
|---|---|
| **Show code before running** | User never executes code they haven't seen |
| **Dangerous pattern scanner** | Warns explicitly on `os.remove`, `shutil.rmtree`, `os.system` etc. |
| **Explicit YES confirmation** | Accidental enter key cannot trigger destructive actions |
| **LLM-prompted dry-run** | System prompt instructs model to preview before deleting/modifying |
| **Single retry only** | Prevents infinite LLM loops consuming tokens and causing repeated errors |
| **60-second timeout** | Infinite loops in generated scripts cannot hang the tool |
| **`sys.executable` for subprocess** | Ensures generated scripts use the exact same Python version — no version mismatch bugs |
| **`tempfile` for script storage** | Concurrent runs never overwrite each other's generated scripts |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- An OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOURUSERNAME/scriptassist.git
cd scriptassist

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate      # Mac/Linux
# .venv\Scripts\activate       # Windows

# 3. Install dependencies (only 2 packages)
pip install -r requirements.txt

# 4. Set up your API key
cp .env.example .env
# Open .env and paste your key:
# OPENAI_API_KEY=sk-...your key here...

# 5. Run
python main.py
```

### Example tasks you can try

```bash
❯ List all Python files in current directory with their line counts
❯ Find all files larger than 10MB in my Downloads folder
❯ Rename all .jpeg files to .jpg in the current folder
❯ Create a summary of all .txt files in this directory
❯ Show total disk usage of each subfolder here
❯ Delete all __pycache__ folders recursively from this project
```

### In-session commands

| Command | Action |
|---------|--------|
| Any text | Generate and run a script |
| `history` | View recent log files |
| `clear` | Reset conversation context |
| `quit` / `exit` | Exit the tool |

---

## 🧠 Technical Concepts Demonstrated

This project was built to demonstrate the following in depth:

**AI / LLM Engineering**
- Prompt engineering for code generation safety (output format constraints, dry-run instruction, error handling requirements)
- Multi-turn conversation context management with token budgeting
- Structured error-feedback prompting for LLM-based debugging loops
- ReAct (Reason + Act + Observe) agent pattern implementation

**Python Standard Library**
- `subprocess.run()` with `capture_output`, `text`, `timeout` for process management
- `tempfile.NamedTemporaryFile` for safe, concurrent script storage
- `pathlib.Path` for cross-platform file operations
- `os.environ` / `python-dotenv` for secure secret management
- `datetime` with `strftime` for chronological log naming

**Software Engineering Practices**
- Separation of concerns across 6 single-responsibility modules
- Fail-fast pattern with clear error messages in `config.py`
- Defensive coding — cleaning LLM output even when prompted correctly
- Cleanup guarantee via `finally` blocks
- `.gitignore` for secret protection, clean commit history

---

## 📁 Project Structure

```
scriptassist/
├── main.py              # Entry point — CLI loop and orchestration
├── llm_caller.py        # OpenAI API communication and prompt engineering
├── executor.py          # subprocess execution, retry logic, temp file management
├── safety.py            # Dangerous pattern detection and user confirmation
├── logger.py            # Session logging with pathlib
├── config.py            # API key loading via python-dotenv
├── requirements.txt     # openai, python-dotenv
├── .env.example         # Template — copy to .env and add your key
├── .gitignore           # Excludes .env, __pycache__, venv
└── README.md
```

---

## 🔮 Potential Extensions

- **Sandbox mode** — run generated scripts inside a temporary directory copy instead of the real filesystem
- **Script library** — save and reuse previously generated scripts by task description
- **Streaming output** — real-time stdout using `subprocess.Popen` instead of `run()`
- **Local LLM support** — swap OpenAI for Ollama to run fully offline
- **Web interface** — wrap the CLI in a FastAPI + React frontend

---

## 📄 License

MIT — free to use, modify, and distribute.

---

<div align="center">

Built by **[DEV SHARMA]** · IIT Guwahati
<br>
[LinkedIn](https://www.linkedin.com/in/dev-sharma-324747383/) · [GitHub](https://github.com/devsharma30)

</div>