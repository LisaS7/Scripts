import json

with open("data.json") as f:
    data = json.load(f)

print("| Page | Prompt | Status |")
print("|------|--------|--------|")

for item in data:
    if item["completed"]:
        status = "✅"
    elif item["started"]:
        status = "🟡"
    else:
        status = "⬜"

    print(f'| {item["page"]} | {item["prompt"]} | {status} |')
