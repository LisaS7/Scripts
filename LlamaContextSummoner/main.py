import re
from pathlib import Path

import requests

# In Progress:
# switch from /generate to /chat and maintain a chat history

# TODO:
# Make interactive mode optional?
# Deal with context window filling up
# Run from the command line with args
# Add a list-projects command
# Stop reading the whole vault on every run. Cache last mod time?
# Arg to output to xml file?

OBSIDIAN_ROOT = Path("/home/lisa/Documents/TheLedger")
CACHE_PATH = "obsidian_cache.json"
LLAMA_LOCATION = "http://localhost:11434/api/chat"


# --------------- FILE STUFF ---------------


def extract_frontmatter(path: Path):
    with path.open("r", encoding="utf-8") as f:
        text = f.read()

    if not text.startswith("---"):
        return {}

    # extract the properties block from the md file (if it has one)
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    block = match.group(1)

    # parse the properties into a dict
    fm = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fm[key.strip()] = value.strip()

    return fm


def get_project_context(project_name: str):
    matched_files = []

    for f in OBSIDIAN_ROOT.rglob("*.md"):
        fm = extract_frontmatter(f)
        if fm.get("project") == project_name:
            matched_files.append(f)

    print(f"Found {len(matched_files)} files for project '{project_name}'")

    chunks = []

    for f in matched_files:
        with f.open("r", encoding="utf-8") as raw:
            content = raw.read()

        chunks.append(f"\n\n===== FILE: {f.name} =====\n{content}")

    full_context = "\n".join(chunks)
    return full_context


# --------------- MODEL STUFF ---------------


def ask_model(messages: list[dict], model: str = "llama3"):
    response = requests.post(
        LLAMA_LOCATION,
        json={
            "model": model,
            "messages": messages,
            "stream": False,
        },
        timeout=120,
    )

    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]


# --------------- RUN IT ---------------


def main():
    project = "DrawABox"
    context = get_project_context(project)

    history = [
        {"role": "system", "content": f"You are assisting with project: {project}."},
        {
            "role": "system",
            "content": f"PROJECT FILES:\n----------------\n{context}\n----------------",
        },
    ]

    print("\nInteractive mode. Type 'quit' to exit.")

    while True:
        # Get the input from the user
        user_query = input("\nYou: ").strip()
        if not user_query:
            continue
        if user_query.lower() in {"exit", "quit", "q"}:
            break

        # Ask model, and add both query and response to history
        history.append({"role": "user", "content": user_query})
        answer = ask_model(history)
        history.append({"role": "assistant", "content": answer})

        print("\Llama:\n")
        print(answer)

    answer = ask_model(history)

    print("\n--- MODEL RESPONSE ---\n")
    print(answer)


if __name__ == "__main__":
    main()
