# AI Red Teaming

Notes and a lab on red teaming AI applications and agents: scoping an engagement, planning attacks from a threat model, manual and automated attacks, red teaming agents, measuring results, safety versus security testing, and reporting.

These notes continue the [main course on AI application security](https://github.com/rajumandala/aisec-notes). The main course built one system, a broker's AI order assistant. This part attacks systems other people built, so the attacks are not shaped by knowing how the defences were written:

- **[FinBot CTF](https://github.com/GenAI-Security-Project/finbot-ctf)** (OWASP GenAI Security Project), from R0: an intentionally vulnerable multi-agent vendor-management platform with MCP tools and challenges. It is the target for hands-on attacks on a whole application.
- **[AgentDojo](https://github.com/ethz-spylab/agentdojo)** (ETH Zurich), from R4: simulated banking, Slack, travel and workspace agents, with user tasks, attacker goals and attacks. It resets and grades every run in code, so it is used where a note needs a measured rate.

Both are pinned to exact commits in `targets.lock` and cloned into `targets/`, which is gitignored. Third-party code is not copied into this repo.

Start with [R0. AI Red Teaming](notes/R0.%20AI%20Red%20Teaming.md). R4 records a paid run against AgentDojo. Every other note records a free run that calls no model: a survey of how FinBot grades its challenges, harness checks, FinBot's document delivery in an offline container, graders and regression tests.

## Course

| Note | Focus |
|---|---|
| [R0. AI Red Teaming](notes/R0.%20AI%20Red%20Teaming.md) | FinBot, and how an AI red team differs from a pentest |
| [R1. Scope and Rules of Engagement](notes/R1.%20Scope%20and%20Rules%20of%20Engagement.md) | Authorisation, scope and stop rules |
| [R2. Plans from the Threat Model](notes/R2.%20Plans%20from%20the%20Threat%20Model.md) | Goals, boundaries and test cases |
| [R3. Writing Attacks by Hand](notes/R3.%20Writing%20Attacks%20by%20Hand.md) | Experiment cards, delivery checks and controls |
| [R4. Automated Attacks](notes/R4.%20Automated%20Attacks.md) | AgentDojo, search, scanners and held-out evaluation |
| [R5. Red Teaming Agents](notes/R5.%20Red%20Teaming%20Agents.md) | Tool effects and multi-agent chains |
| [R6. Measuring](notes/R6.%20Measuring.md) | Denominators, uncertainty and coverage |
| [R7. Safety and Security Red Teaming](notes/R7.%20Safety%20and%20Security%20Red%20Teaming.md) | Content harm, uplift and security |
| [R8. Reporting and Retesting](notes/R8.%20Reporting%20and%20Retesting.md) | Evidence, severity, regression and disclosure |

### Free checks (no model calls)

```bash
cd lab
python3 course_checks.py         # note structure and local links
python3 r0_challenges.py         # R0: FinBot's challenges and how each is graded; reads the pinned checkout
uv run python r1_checks.py       # R1: harness rules, stub model; containment checks need FinBot running
python3 r3_delivery.py           # R3: which documents reach FinBot's fraud agent; offline container, needs the image
python3 r4_harness_checks.py     # R4: scope and budget limits for automated attacks, stub model
python3 r5_grader_checks.py      # R5: the agent-run grader on hand-written traces
python3 measurement_checks.py    # R4, R6: rates, intervals and error counting
python3 r7_scoring_checks.py     # R7: content, security and utility scorecards
python3 r8_regression_checks.py  # R8: payment rule and the RT-R4-01 assurance check
```

All but `r1_checks.py` and `r3_delivery.py` use the standard library only. These check the lab's own tools and how FinBot handles documents and grades challenges, not how well a model resists attacks. Do not start FinBot just to run a free check: its workflows can call the model.

## Running the lab

**These commands can spend money.** `r4_rates.py` calls the model, and so does anything that makes FinBot's agents work. Get approval for the spend first, as R1 requires. The harness does not yet count or stop the model calls FinBot makes from its own server, so a live FinBot experiment also needs that, and the spending limit on FinBot's own key, before it starts.

```bash
cp lab/.env.example .env && chmod 600 .env     # then add the keys; .env is gitignored
git clone https://github.com/GenAI-Security-Project/finbot-ctf.git targets/finbot-ctf
git -C targets/finbot-ctf checkout "$(awk '$1=="finbot-ctf"{print $3}' targets.lock)"
docker build -t "finbot-ctf:$(awk '$1=="finbot-ctf"{print substr($3,1,7)}' targets.lock)" targets/finbot-ctf
git clone https://github.com/ethz-spylab/agentdojo.git targets/agentdojo            # optional: to read the source

cd lab
finbot/up.sh                     # FinBot at http://127.0.0.1:8000, locked down; finbot/down.sh stops it
uv sync                          # installs AgentDojo at the pinned commit
uv run python r1_checks.py       # rules of engagement; no model calls
uv run python r4_rates.py        # R4's attacks on AgentDojo, 10 runs each; calls the model
```

Every attack goes through `lab/engagement.toml`. Change the scope there, not in the scripts. Transcripts are written to `lab/results/`, which is never committed. FinBot is intentionally vulnerable: run it only through `up.sh`, which keeps it on this machine, and never point the scripts at the hosted CTF.
