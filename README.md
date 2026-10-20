# AI Red Teaming

Notes and a lab on red teaming AI applications and agents: scoping an engagement, planning attacks from a threat model, manual and automated attacks, red teaming agents, measuring results, safety versus security testing, and reporting.

These notes continue the [main course on AI application security](https://github.com/rajumandala/aisec-notes). The target is the same AI order assistant inside a broker's trading app, rebuilt small in `lab/` so that every attack runs for real against synthetic clients and a fake exchange.

Start with [R0. AI Red Teaming](notes/R0.%20AI%20Red%20Teaming.md). R0 and R1 are written; R1's checks have been run, R0's attack run has not yet. R2 to R8 are planned.

## Running the lab

```bash
cp lab/.env.example .env        # then add OPENAI_API_KEY; .env is gitignored
cd lab
uv sync
uv run python r1_checks.py      # rules of engagement; no model calls
uv run python r0_rates.py       # R0's attack, 10 runs per wording; calls the model
```

Every attack goes through `lab/engagement.toml`. Change the scope there, not in the scripts. Transcripts are written to `lab/results/`, which is never committed.
