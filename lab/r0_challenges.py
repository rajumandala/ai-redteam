"""R0: what FinBot's challenges ask for, and how FinBot decides one is solved. No model is called.

Reads the challenge definitions in the pinned checkout (targets/finbot-ctf). Each names a detector,
the code that decides success. A detector with a judge prompt asks a model to decide; the rest
check FinBot's events and database in code.
"""

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHALLENGES = ROOT / "targets" / "finbot-ctf" / "finbot" / "ctf" / "definitions" / "challenges"


def field(text: str, name: str) -> str:
    match = re.search(rf"^{name}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip().strip('"') if match else "?"


def main() -> None:
    rows = []
    for path in sorted(CHALLENGES.glob("*/*.yaml")):
        text = path.read_text()
        rows.append({
            "title": field(text, "title"),
            "category": field(text, "category"),
            "difficulty": field(text, "difficulty"),
            "detector": field(text, "detector_class"),
            "graded_by": "a model as judge" if "judge_system_prompt:" in text else "code",
        })
    print(f"{len(rows)} challenges")
    for name in ["category", "difficulty", "graded_by"]:
        print(f"by {name}: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(r[name] for r in rows).items())))
    print("graded by a model:")
    for r in rows:
        if r["graded_by"] != "code":
            print(f"  {r['category']}: {r['title']} ({r['detector']})")


if __name__ == "__main__":
    main()
