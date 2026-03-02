import re
from pathlib import Path

import requests

OBSIDIAN_ROOT = Path("/home/lisa/Documents/TheLedger")
CACHE_PATH = "obsidian_cache.json"
LLAMA_LOCATION = "http://localhost:11434/api/generate"


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


def ask_model(prompt: str, model: str = "llama3"):
    response = requests.post(
        LLAMA_LOCATION,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )

    response.raise_for_status()
    data = response.json()
    return data["response"]


# --------------- RUN IT ---------------


def main():
    project = "DrawABox"
    context = get_project_context(project)
    user_query = "Summarise my current DrawABox progress and suggest next steps."

    full_prompt = f"""
            You are assisting with project: {project}

            PROJECT FILES:
            ----------------
            {context}
            ----------------

            TASK:
            {user_query}
            """
    answer = ask_model(full_prompt)

    print("\n--- MODEL RESPONSE ---\n")
    print(answer)


if __name__ == "__main__":
    main()
