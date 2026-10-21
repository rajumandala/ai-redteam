"""Free course-integrity checks: local Markdown destinations and note structure."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ["## The idea", "## What happened", "## OWASP risks in this note",
            "## Problem and next step", "## Sources"]


def main() -> None:
    errors = []
    notes = sorted((ROOT / "notes").glob("R*.md"))
    if len(notes) != 9:
        errors.append(f"expected 9 notes, found {len(notes)}")
    for path in [ROOT / "README.md", *notes]:
        text = path.read_text()
        if path in notes:
            # R0 has an introductory form of The idea rather than the later exact heading.
            headings = ["## The idea:" if path.name.startswith("R0.") else REQUIRED[0], *REQUIRED[1:]]
            positions = [text.find(h) for h in headings]
            if min(positions) < 0 or positions != sorted(positions):
                errors.append(f"{path.name}: missing or unordered required sections")
        for match in re.finditer(r"\]\((<[^>]+>|[^\s)]+)\)", text):
            target = match.group(1).strip("<>")
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            resolved = path.parent / unquote(parts.path)
            if not resolved.is_file():
                errors.append(f"{path.name}: missing destination {target}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS {len(notes)} notes: required section order and local Markdown destinations")
    print("External URLs and fragment anchors are not checked; this is not a content or target evaluation.")


if __name__ == "__main__":
    main()
