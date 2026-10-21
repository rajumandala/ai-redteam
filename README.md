# AI Red Teaming

Notes and a lab on red teaming AI applications and agents: scoping an engagement, planning attacks from a threat model, manual and automated attacks, red teaming agents, measuring results, safety versus security testing, and reporting.

These notes continue the [main course on AI application security](https://github.com/rajumandala/aisec-notes). The main course built one system, a broker's AI order assistant. This part attacks two systems other people built, so the attacks are not shaped by knowing how the defences were written:

- **[AgentDojo](https://github.com/ethz-spylab/agentdojo)** (ETH Zurich): simulated banking, Slack, travel and workspace agents, with user tasks, attacker goals and attacks. It grades every run from the simulated environment's state, so it is used where a note needs a measured rate.
- **[FinBot CTF](https://github.com/GenAI-Security-Project/finbot-ctf)** (OWASP GenAI Security Project): an intentionally vulnerable multi-agent vendor-management platform with MCP tools and challenges. It is used for hands-on attacks on a whole application.

Both are pinned to exact commits in `targets.lock` and cloned into `targets/`, which is gitignored. Third-party code is not copied into this repo.

Start with [R0. AI Red Teaming](notes/R0.%20AI%20Red%20Teaming.md). R0–R8 are written. R0 records the historical paid experiment; R1 records the harness checks; R2–R8 distinguish source review, free exercises and experiment plans from live results. **No new paid experiments were authorised for R3–R8.** FinBot attacks and broader AgentDojo measurements remain unrun, not passed.

## Course

| Note | Focus |
|---|---|
| [R0. AI Red Teaming](notes/R0.%20AI%20Red%20Teaming.md) | Targets, rates and utility |
| [R1. Scope and Rules of Engagement](notes/R1.%20Scope%20and%20Rules%20of%20Engagement.md) | Authorisation, scope and stop rules |
| [R2. Plans from the Threat Model](notes/R2.%20Plans%20from%20the%20Threat%20Model.md) | Goals, boundaries and test cases |
| [R3. Writing Attacks by Hand](notes/R3.%20Writing%20attacks%20by%20hand.md) | Manual experiments and indirect entry points |
| [R4. Automated Attacks](notes/R4.%20Automated%20Attacks.md) | Search, scanners and held-out evaluation |
| [R5. Red Teaming Agents](notes/R5.%20Red%20teaming%20agents.md) | Tool effects and multi-agent chains |
| [R6. Measuring](notes/R6.%20Measuring.md) | Denominators, uncertainty and coverage |
| [R7. Safety and Security Red Teaming](notes/R7.%20Safety%20and%20Security%20Red%20Teaming.md) | Content harm, uplift and security |
| [R8. Reporting and Retesting](notes/R8.%20Reporting%20and%20Retesting.md) | Evidence, severity, regression and disclosure |

### Free checks (no API calls)

```bash
cd lab
python3 course_checks.py         # standard library only; note structure and local links
python3 measurement_checks.py    # standard library only; 9 measurement tests
uv run python r1_checks.py      # stub model; 28 checks when local FinBot containers are present
```

The measurement exercise checks arithmetic and outcome accounting, not attack resistance. Container checks are skipped when FinBot is absent. Do not start it merely to run a no-cost exercise: its application workflows can make paid calls.

## Running the lab

**The current continuation authorises no paid calls.** The setup and paid-run commands below are reference instructions, not commands executed to complete these notes. Obtain explicit approval before running the rate script, invoking FinBot agents or adding another model. The existing harness is not a complete live FinBot attack adapter; verify internal-call accounting, stop propagation, output containment and graders before a live experiment.

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
