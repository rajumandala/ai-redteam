# AI Red Teaming

Notes and a lab on red teaming AI applications and agents: scoping an engagement, planning attacks from a threat model, manual and automated attacks, red teaming agents, measuring results, safety versus security testing, and reporting.

These notes continue the [main course on AI application security](https://github.com/rajumandala/aisec-notes). The main course built one system, a broker's AI order assistant. This part attacks two systems other people built, so the attacks are not shaped by knowing how the defences were written:

- **[AgentDojo](https://github.com/ethz-spylab/agentdojo)** (ETH Zurich): simulated banking, Slack, travel and workspace agents, with user tasks, attacker goals and attacks. It grades every run from the simulated environment's state, so it is used where a note needs a measured rate.
- **[FinBot CTF](https://github.com/GenAI-Security-Project/finbot-ctf)** (OWASP GenAI Security Project): an intentionally vulnerable multi-agent vendor-management platform with MCP tools and challenges. It is used for hands-on attacks on a whole application.

Both are pinned to exact commits in `targets.lock` and cloned into `targets/`, which is gitignored. Third-party code is not copied into this repo.

Start with [R0. AI Red Teaming](notes/R0.%20AI%20Red%20Teaming.md). R0 and R1 are written and their runs are recorded in each note. R2 to R8 are planned.

## Running the lab

```bash
cp lab/.env.example .env && chmod 600 .env     # then add the keys; .env is gitignored
git clone https://github.com/ethz-spylab/agentdojo.git targets/agentdojo            # optional: to read the source
git clone https://github.com/GenAI-Security-Project/finbot-ctf.git targets/finbot-ctf
git -C targets/finbot-ctf checkout "$(awk '$1=="finbot-ctf"{print $3}' targets.lock)"
docker build -t "finbot-ctf:$(awk '$1=="finbot-ctf"{print substr($3,1,7)}' targets.lock)" targets/finbot-ctf

cd lab
uv sync                          # installs AgentDojo at the pinned commit
uv run python r1_checks.py       # rules of engagement; no model calls
uv run python r0_rates.py        # R0's attacks on AgentDojo, 10 runs each; calls the model
finbot/up.sh                     # FinBot at http://127.0.0.1:8000, locked down; finbot/down.sh stops it
```

Every attack goes through `lab/engagement.toml`. Change the scope there, not in the scripts. Transcripts are written to `lab/results/`, which is never committed. FinBot is intentionally vulnerable: run it only through `up.sh`, which keeps it on this machine, and never point the scripts at the hosted CTF.
