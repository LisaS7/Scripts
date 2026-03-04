import argparse
import re
from pathlib import Path

import requests

# In Progress:
# Deal with context window filling up

# TODO:
# Stop reading the whole vault on every run. Cache last mod time?
# Arg to output to xml file?
# On loading files, measure token size and summarise if large

OBSIDIAN_ROOT = Path("/home/lisa/Documents/TheLedger")
CACHE_PATH = "obsidian_cache.json"
LLAMA_LOCATION = "http://localhost:11434/api/chat"
MAIN_PROMPT_PATH = Path(
    "/home/lisa/Documents/TheLedger/Areas/The Workshop/Llama/main_prompt.md"
)

# Increase this if the script is not capturing the entire frontmatter
FRONTMATTER_READ_LIMIT = 2048  # bytes


# --------------- CLI ---------------


def parse_args():
    parser = argparse.ArgumentParser(prog="LlamaContextSummoner")

    parser.add_argument(
        "--list-projects",
        action="store_true",
        help="List all unique project names found in frontmatter and exit",
    )

    parser.add_argument(
        "-p",
        "--project",
        default="DrawABox",
        help="Project name to load from frontmatter (default: DrawABox)",
    )

    parser.add_argument(
        "-m", "--model", default="llama3", help="Ollama model name (default: llama3)"
    )

    parser.add_argument(
        "question",
        nargs="*",
        help="If provided, runs single-shot mode. If omitted, starts interactive mode.",
    )

    return parser.parse_args()


def list_projects():
    projects = set()

    for f in OBSIDIAN_ROOT.rglob("*.md"):
        fm = extract_frontmatter(f)
        project = fm.get("project")
        if not project:
            continue

        # normalise a bit (handles 'DrawABox' vs DrawABox)
        project = project.strip().strip('"').strip("'")
        if project:
            projects.add(project)

    return sorted(projects, key=str.lower)


# --------------- FILE STUFF ---------------


def load_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def extract_frontmatter(path: Path):
    with path.open("rb") as f:
        # only read a small amount of data from the beginning of the file
        prefix = f.read(FRONTMATTER_READ_LIMIT)
        text = prefix.decode("utf-8", errors="ignore")

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


def build_history(project: str):
    main_prompt = load_file(MAIN_PROMPT_PATH)
    context = get_project_context(project)

    return [
        {"role": "system", "content": main_prompt},
        {"role": "system", "content": f"You are assisting with project: {project}."},
        {
            "role": "system",
            "content": f"PROJECT FILES:\n----------------\n{context}\n----------------",
        },
    ]


def summarise_conversation(history: list[dict], model: str):
    SYSTEM_PREFIX_LEN = 3
    system_prefix = history[:SYSTEM_PREFIX_LEN]
    convo = history[SYSTEM_PREFIX_LEN:]

    if not convo:
        print("📝 Nothing to summarise yet.")
        return history

    # Conversation to plain text for summary
    convo_text_lines = []
    for msg in convo:
        role = msg.get("role", "user")
        if role == "user":
            convo_text_lines.append(f"USER: {msg.get('content','')}")
        elif role == "assistant":
            convo_text_lines.append(f"ASSISTANT: {msg.get('content','')}")

    convo_text = "\n".join(convo_text_lines)

    summary_prompt = [
        {"role": "system", "content": "You write concise, structured summaries."},
        {
            "role": "user",
            "content": (
                "Summarise the following conversation so it can replace the full chat history.\n\n"
                "Requirements:\n"
                "- Use bullet points.\n"
                "- Include: goals, what was decided, what was tried, key facts, open questions.\n"
                "- Keep it under ~250 words.\n\n"
                "CONVERSATION:\n"
                f"{convo_text}"
            ),
        },
    ]

    summary, usage = ask_model(summary_prompt, model=model)

    new_history = system_prefix + [
        {
            "role": "system",
            "content": "CONVERSATION SUMMARY (most recent):\n" + summary.strip(),
        }
    ]

    print(
        f"\n🧾 summary tokens | in: {usage.get('prompt_eval_count')} | out: {usage.get('eval_count')}\n"
    )

    return new_history


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

    content = data["message"]["content"]

    usage = {
        "prompt_eval_count": data.get("prompt_eval_count"),
        "eval_count": data.get("eval_count"),
    }

    return content, usage


# --------------- RUN IT ---------------


def main():
    args = parse_args()

    if args.list_projects:
        projects = list_projects()

        if not projects:
            print("No projects found (no 'project:' in frontmatter).")
        else:
            print("Projects:")
            for p in projects:
                print(f"- {p}")
        return

    project = args.project
    model = args.model
    user_question = " ".join(args.question).strip()

    print(f"\n🦙 Project: {project} | Model: {model} | Type 'quit' to exit.")

    history = build_history(project)

    total_prompt_tokens = 0
    total_output_tokens = 0

    # If a question is provided then run non-interactive
    if user_question:
        history.append({"role": "user", "content": user_question})
        answer, usage = ask_model(history, model=model)
        total_prompt_tokens += usage.get("prompt_eval_count") or 0
        total_output_tokens += usage.get("eval_count") or 0
        print("\n🦙 >\n")
        print(answer)
        print(
            f"\n🧾 tokens | in: {usage.get('prompt_eval_count')} | out: {usage.get('eval_count')}\n"
        )
        return

    # Otherwise run in interactive mode
    print(
        "\n🦙 Interactive mode. Type 'quit' to exit. Type ':reload' to reload context."
    )

    while True:
        # Get the input from the user
        user_query = input("\nHuman 🖤 > ").strip()
        if not user_query:
            continue
        if user_query.lower() in {"exit", "quit", "q"}:
            break
        if user_query.lower() == ":reload":
            print("\n🔄 Reloading context from vault...\n")
            history = build_history(project)
            print("✅ Reloaded.\n")
            continue

        # Ask model, and add both query and response to history
        history.append({"role": "user", "content": user_query})
        answer, usage = ask_model(history, model=model)
        total_prompt_tokens += usage.get("prompt_eval_count") or 0
        total_output_tokens += usage.get("eval_count") or 0
        history.append({"role": "assistant", "content": answer})

        print("\nLlama 🦙 >\n")
        print(answer)
        print(
            f"\n🧾 tokens | in: {usage.get('prompt_eval_count')} | out: {usage.get('eval_count')} | total in: {total_prompt_tokens} | total out: {total_output_tokens}\n"
        )


if __name__ == "__main__":
    main()
