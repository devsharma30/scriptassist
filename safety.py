# ── Dangerous patterns we watch for ────────────────────
# These are Python functions/modules that can permanently
# destroy data or compromise the system.

DANGEROUS_PATTERNS = [
    # File deletion
    "os.remove",          # deletes a single file
    "os.unlink",          # same as os.remove
    "shutil.rmtree",      # deletes an ENTIRE directory recursively
    "os.rmdir",           # deletes an empty directory

    # File overwriting
    "open(",              # could open a file and overwrite it
    "shutil.move",        # moves/renames files (can overwrite)
    "shutil.copy",        # copies (destination might be overwritten)

    # System commands (subprocess running shell commands is risky)
    "subprocess.call",
    "subprocess.Popen",
    "os.system",          # runs a raw shell command — very dangerous

    # Network (we don't want the script phoning home)
    "requests.get",
    "requests.post",
    "urllib",
    "socket",
]

# it is a list of patterns that are dangerous and this list is of strings.


RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


def scan_for_danger(script: str) -> list[str]:
    """
    Scans a script string for dangerous patterns.
    Returns a list of dangerous patterns found.

    Parameters:
        script (str): The generated Python script as a string

    Returns:
        list[str]: List of dangerous patterns detected

    PYTHON CONCEPT — Type hints:
        The ': str' and '-> list[str]' are TYPE HINTS.
        They don't enforce anything at runtime but tell other
        developers (and you, 3 months later) what types to expect.
    """
    found = []  # empty list; we'll append to it

    for pattern in DANGEROUS_PATTERNS:
        if pattern in script:
            found.append(pattern)

    return found


def show_code(script: str) -> None:
    """
    It prints the generated script in the terminal
    with a clear border so the user knows what they're
    about to run.

    it is a void function when compared to c++.

    """
    print(f"\n{CYAN}{'─' * 60}{RESET}")
    print(f"{BOLD}📄  Generated script:{RESET}")
    print(f"{CYAN}{'─' * 60}{RESET}")

    # enumerate() gives you both the index and the value when looping over a list.like a eg->enumerate(["a","b","c"]) → (0,"a"), (1,"b"), (2,"c")
    lines = script.split("\n")   # split the script into lines
    for i, line in enumerate(lines, start=1):
        # f-string with formatting: {i:3d} = integer, 3 chars wide; we use to allign line numbers neatly.
        print(f"{YELLOW}{i:3d}{RESET}  {line}")

    print(f"{CYAN}{'─' * 60}{RESET}\n")


def ask_user_permission(script: str) -> bool:
    """
    Shows the generated code, warns about dangerous operations,
    then asks the user for explicit YES confirmation.

    Returns True if user approves, False if they decline.

    """
    # to Show the code
    show_code(script)

    # then we will scan for dangerous patterns
    dangers = scan_for_danger(script)

    # if dangers list is not empty we will code forward

    if dangers:
        # '\\n  - '.join(dangers) joins list items with newline+dash.   for eg->  ["a", "b"] → "\n  - a\n  - b"
        danger_list = "\n  - ".join(dangers)
        print(f"{RED}{BOLD}⚠️   WARNING — Dangerous operations detected:{RESET}")
        print(f"{RED}  - {danger_list}{RESET}\n")

    # now we have to ask for confirmation for user

    while True:
        # input() pauses the program and waits for the user to type something and press Enter. Returns the typed string.
        answer = input(
            f"{BOLD}Run this script? [yes/no]: {RESET}").strip().lower()

        if answer in ("yes", "y"):
            return True
        elif answer in ("no", "n"):
            return False
        else:
            # Otherwise loop again — keep asking
            print("  Please type 'yes' or 'no'.")


# if the outcome comes true the program will do further work otherwise we will ask to answer in the form of only yes or no(y or n) also.
# for demo purpose you can read the readme.md file for a example and see what does this code is doing as  it will help.
