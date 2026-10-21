"""R3: which uploaded documents reach FinBot's fraud agent? No model is called.

Runs finbot/delivery_probe.py in a throwaway container of the pinned FinBot image: no network,
no API key, no capabilities, and a database that is thrown away with the container.
"""

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
SHA = next(line.split()[2] for line in (HERE.parent / "targets.lock").read_text().splitlines()
           if line.split()[:1] == ["finbot-ctf"])
IMAGE = f"finbot-ctf:{SHA[:7]}"

# What the source review in R3 predicts: True means the file's text reaches the prompt.
EXPECTED = {
    "eligible document": {"soc2_report.txt": True},
    "task is not a document review": {"soc2_report.txt": False},
    "filename has no compliance word": {"letter.txt": False},
    "wrong folder": {"soc2_report.txt": False},
    "empty file": {"soc2_report.txt": False},
    "another vendor's file": {"soc2_report.txt": False},
    "three eligible files": {"iso_old.txt": False, "iso_mid.txt": True, "iso_new.txt": True},
    "words that only contain a keyword": {"price_comparison.txt": True},
}


def main() -> None:
    out = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
         "--security-opt", "no-new-privileges", "--memory", "512m", "--pids-limit", "128",
         "-e", "DATABASE_URL=sqlite:////tmp/r3.db", "-e", "PYTHONPATH=/app", "-e", "OPENAI_API_KEY=",
         "-v", f"{HERE / 'finbot' / 'delivery_probe.py'}:/probe/delivery_probe.py:ro",
         "--entrypoint", "python", IMAGE, "/probe/delivery_probe.py"],
        capture_output=True, text=True, check=True)
    results = json.loads(out.stdout.strip().splitlines()[-1])
    failed = 0
    for case, expected in EXPECTED.items():
        ok = results.get(case) == expected
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'} {case}: {results.get(case)}")
    print(f"{len(EXPECTED) - failed}/{len(EXPECTED)} match the source review ({IMAGE}, no network, no model calls)")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
