import os

from dotenv import load_dotenv  # python-dotenv reads your .env file
# and puts the values into os.environ

load_dotenv()
# load_dotenv() finds the .env file in the current directory and
# loads every KEY=VALUE line into environment variables.
# Think of environment variables as a dictionary your OS keeps.

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# error if key is not found so it not become confusing

if not GEMINI_API_KEY:
    print("\n❌  ERROR: GEMINI_API_KEY not found.")
    print("    Steps to fix:")
    print("    1. Copy .env.example  →  .env")
    print("    2. Open .env and paste your key from https://aistudio.google.com/app/apikey")
    print("    3. Run the program again.\n")
    raise SystemExit(1)
