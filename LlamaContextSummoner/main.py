import re
from pathlib import Path

OBSIDIAN_ROOT = Path("/home/lisa/Documents/TheLedger")
CACHE_PATH = "obsidian_cache.json"


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
        key, value = line.split(":", 1)
        fm[key.strip()] = value.strip()

    print(fm)
    return fm


for f in OBSIDIAN_ROOT.rglob("*.md"):
    fm = extract_frontmatter(f)
