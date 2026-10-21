"""R0: one indirect injection, several wordings, many runs. Success is a rate.

AgentDojo's banking suite: Emma asks her assistant to pay a bill from a file. The attacker
controls text the agent reads on the way, and wants a payment sent to their own account.
AgentDojo grades both from the bank's state after the run, not from what the model said.
"""

import argparse
import os
from pathlib import Path

import openai
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.types import get_text_content_as_str
from dotenv import load_dotenv

from redteam.agentdojo_llm import attack, pipeline
from redteam.harness import Engagement, Stop, openai_call

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

BENCHMARK = "v1.2.2"
SUITE, USER_TASK, INJECTION_TASK = "banking", "user_task_0", "injection_task_0"
ATTACKS = ["none", "direct", "ignore_previous", "important_instructions"]


def tool_calls(messages) -> list[dict]:
    return [
        {"function": call.function, "args": call.args}
        for m in messages
        if m["role"] == "assistant"
        for call in m["tool_calls"] or []
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10, help="runs per attack")
    args = parser.parse_args()

    model = os.environ.get("MODEL", "gpt-6.1-sol")
    eng = Engagement.load(HERE / "engagement.toml")
    eng.check_scope("agentdojo", model)
    call = eng.wrap(openai_call(openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"]), eng.id), model)

    suite = get_suite(BENCHMARK, SUITE)
    user_task = suite.get_user_task_by_id(USER_TASK)
    injection_task = suite.get_injection_task_by_id(INJECTION_TASK)
    agent, llm = pipeline(call, model)

    print(f"engagement {eng.id}, model {model}, AgentDojo {BENCHMARK} {SUITE} {USER_TASK} x {INJECTION_TASK}")
    print(f"{args.runs} runs per attack\n")
    print(f"{'attack':<24}{'attack worked':>15}{'bill paid':>12}{'errors':>9}")
    try:
        for name in ATTACKS:
            worked = done = errors = 0
            injections = {} if name == "none" else attack(name, suite, agent, model).attack(user_task, injection_task)
            for run in range(args.runs):
                llm.last_messages = []
                try:
                    utility, security = suite.run_task_with_pipeline(
                        agent, user_task, None if name == "none" else injection_task, injections
                    )
                except openai.APIError as exc:
                    # AgentDojo counts some errors as a successful attack. Here they are counted apart.
                    errors += 1
                    eng.record({"attack": f"r0-{name}", "run": run, "error": repr(exc)})
                    continue
                attacked = name != "none" and security
                worked += attacked
                done += utility
                final = llm.last_messages[-1] if llm.last_messages else None
                eng.record(
                    {
                        "attack": f"r0-{name}",
                        "run": run,
                        "benchmark": f"{BENCHMARK}/{SUITE}/{USER_TASK}/{INJECTION_TASK}",
                        "models_served": sorted(eng.served),
                        "attack_worked": attacked,
                        "bill_paid": utility,
                        "tool_calls": tool_calls(llm.last_messages),
                        "reply": get_text_content_as_str(final["content"] or []) if final else None,
                    }
                )
            n = args.runs - errors
            shown = "-" if name == "none" else f"{worked}/{n}"
            print(f"{name:<24}{shown:>15}{f'{done}/{n}':>12}{errors:>9}")
            if name != "none" and n and 0 < worked < n:
                p = worked / n
                print(f"{'':<24}if the true rate is {p:.0%}, a 3-run test finds nothing {(1 - p) ** 3:.0%} of the time")
    except Stop as exc:
        print(f"\nstopped: {exc}")

    print(f"\nmodel snapshots that answered: {sorted(eng.served)}")
    print(f"calls used: {eng.calls}/{eng.max_calls}, tokens used: {eng.tokens}/{eng.max_tokens}")


if __name__ == "__main__":
    main()
