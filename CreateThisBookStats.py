import json
import random
from dataclasses import dataclass
from typing import Any

BAR_WIDTH = 30
GREEN = "\033[32m"
YELLOW = "\033[33m"
GREY = "\033[90m"
RESET = "\033[0m"


@dataclass(frozen=True)
class Prompt:
    page: int
    prompt: str
    started: bool
    completed: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Prompt":
        return cls(
            page=int(data["page"]),
            prompt=str(data["prompt"]),
            started=bool(data["started"]),
            completed=bool(data["completed"]),
        )


@dataclass(frozen=True)
class Stats:
    total: int
    completed: int
    started: int
    remaining: int

    @property
    def progress(self) -> float:
        return (self.completed / self.total) if self.total else 0.0

    @classmethod
    def build(
        cls,
        *,
        completed: list[Prompt],
        started: list[Prompt],
        remaining: list[Prompt],
        total: int,
    ) -> "Stats":
        return cls(
            total=total,
            completed=len(completed),
            started=len(started),
            remaining=len(remaining),
        )

    def bar(self, width: int = BAR_WIDTH) -> str:
        """Coloured stacked bar: completed (green), started (yellow), remaining (grey)."""
        if self.total == 0:
            return f"{GREY}{'░' * width}{RESET}"

        completed_width = round((self.completed / self.total) * width)
        started_width = round((self.started / self.total) * width)

        # Prevent rounding overflow
        if completed_width + started_width > width:
            started_width = width - completed_width

        remaining_width = width - completed_width - started_width

        return (
            f"{GREEN}{'█' * completed_width}"
            f"{YELLOW}{'█' * started_width}"
            f"{GREY}{'░' * remaining_width}"
            f"{RESET}"
        )


def load_data(filename: str) -> list[Prompt]:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"{filename} should contain a JSON list of prompt objects.")

    return [Prompt.from_dict(item) for item in data]


def group_by_status(
    prompts: list[Prompt],
) -> tuple[list[Prompt], list[Prompt], list[Prompt]]:
    completed = [p for p in prompts if p.completed]
    started = [p for p in prompts if p.started and not p.completed]
    remaining = [p for p in prompts if not p.started and not p.completed]
    return completed, started, remaining


def pick_random(remaining: list[Prompt]) -> Prompt:
    return random.choice(remaining)


def print_stats(stats: Stats) -> None:
    print()
    print("Create This Book Progress")
    print("=" * 24)
    print(f"Total pages: {stats.total}")
    print(f"✅ Completed : {stats.completed}")
    print(f"🟨 Started   : {stats.started}")
    print(f"⬜ Remaining : {stats.remaining}")
    print()
    print(f"Progress: [{stats.bar()}] {int(round(stats.progress * 100))}%")
    print()


def main() -> None:
    data = load_data("data.json")
    total = len(data)

    completed, started, remaining = group_by_status(data)
    stats = Stats.build(
        total=total, completed=completed, started=started, remaining=remaining
    )

    if not remaining and total and len(completed) == total:
        print("🎉 Everything is completed! No prompts left.")
        return

    if not remaining:
        print("No remaining prompts found (check your started/completed flags).")
        return

    print_stats(stats)

    pick = pick_random(remaining)
    print("Next new prompt:")
    print(f"  P{pick.page}: {pick.prompt}")


if __name__ == "__main__":
    main()
