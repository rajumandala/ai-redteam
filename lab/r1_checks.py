"""R1: check that the harness enforces the rules of engagement. No model is called."""

import json
import shutil
import stat
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from agentdojo.task_suite.load_suites import get_suite
from openai.types.responses import ResponseFunctionToolCall

from redteam.agentdojo_llm import pipeline
from redteam.harness import Engagement, OutOfScope, Stop, openai_call

HERE = Path(__file__).parent
MODEL = "gpt-6.1-sol"
CANARY = "sk-lab-canary-000000000000000000000000"
failed: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        failed.append(f"{name}: {detail}")


def refused(name: str, text: str, fn) -> None:
    try:
        fn()
    except (OutOfScope, Stop) as exc:
        check(name, text in str(exc), str(exc))
    else:
        check(name, False, "not refused")


def stub_completion(tool: str | None = None, text: str = "") -> SimpleNamespace:
    output = [ResponseFunctionToolCall(type="function_call", name=tool, arguments="{}", call_id="c0")] if tool else []
    return SimpleNamespace(output=output, output_text=text, model="stub-model", usage=SimpleNamespace(total_tokens=120))


def fresh(tmp: Path, **changes) -> Engagement:
    shutil.copy(HERE / "engagement.toml", tmp / "engagement.toml")
    eng = Engagement.load(tmp / "engagement.toml")
    for key, value in changes.items():
        setattr(eng, key, value)
    return eng


def run_bill_task(call) -> None:
    suite = get_suite("v1.2.2", "banking")
    agent, _ = pipeline(call, MODEL)
    suite.run_task_with_pipeline(agent, suite.get_user_task_by_id("user_task_0"), None, {})


def docker_inspect(name: str) -> dict | None:
    try:
        out = subprocess.run(["docker", "inspect", name], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return json.loads(out.stdout)[0] if out.returncode == 0 else None


def main() -> None:
    today = date(2026, 10, 21)
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        eng = fresh(tmp)

        eng.check_scope("agentdojo", MODEL, today)
        eng.check_scope("finbot-local", MODEL, today)
        check("AgentDojo, the local FinBot and the model under test are in scope", True)
        refused("production is out of scope", "environment production", lambda: eng.check_scope("production", MODEL, today))
        refused("another model is out of scope", "model gpt-other", lambda: eng.check_scope("agentdojo", "gpt-other", today))
        refused("an expired authorisation stops the engagement", "expired on 2026-11-30", lambda: eng.check_scope("agentdojo", MODEL, date(2026, 12, 1)))
        unsigned = fresh(tmp, authorised_by="")
        refused("no written authorisation, no attack", "no written authorisation", lambda: unsigned.check_scope("agentdojo", MODEL, today))

        eng.check_url("http://127.0.0.1:8000/vendor/onboarding")
        check("the local FinBot is in scope", True)
        refused("the hosted FinBot CTF is out of scope", "owasp-finbot-ctf.org", lambda: eng.check_url("https://owasp-finbot-ctf.org/"))
        refused("another port on this machine is out of scope", "127.0.0.1:8001", lambda: eng.check_url("http://127.0.0.1:8001/"))

        # A model that never stops calling tools, inside AgentDojo's real agent loop: the call budget ends it.
        looping = fresh(tmp, max_calls=3)
        call = looping.wrap(lambda **kw: stub_completion(tool="get_balance"), MODEL)
        refused("the call budget stops a runaway agent loop", "call budget of 3 used", lambda: run_bill_task(call))
        check("the budget stopped it after exactly 3 calls", looping.calls == 3, str(looping.calls))

        stopping = fresh(tmp)
        call = stopping.wrap(lambda **kw: stub_completion(text="Paid."), MODEL)
        run_bill_task(call)
        (tmp / "STOP").touch()
        refused("the stop file halts the next call", "stop file STOP", lambda: run_bill_task(call))
        check("no call was sent after the stop file appeared", stopping.calls == 1, str(stopping.calls))
        (tmp / "STOP").unlink()

        rec = fresh(tmp, canaries={CANARY})
        digest = rec.record({"attack": "canary check", "reply": f"The key is {CANARY}"})
        path = rec.results_dir / f"{rec.id}.jsonl"
        check("a planted canary key in a reply is recorded, not a stop", len(digest) == 12, digest)
        check("the transcript file is readable by the tester only", stat.S_IMODE(path.stat().st_mode) == 0o600, oct(path.stat().st_mode))
        check("the results folder is private too", stat.S_IMODE(rec.results_dir.stat().st_mode) == 0o700, oct(rec.results_dir.stat().st_mode))
        check("every line carries the engagement ID and tester", '"engagement": "RT-2026-001"' in path.read_text() and '"tester": "kiran"' in path.read_text())
        lines = len(path.read_text().splitlines())
        fake_key = "sk-" + "Q7" * 16
        refused("a key-shaped value that is not a canary stops the engagement", "an API key", lambda: rec.record({"attack": "leak check", "reply": fake_key}))
        check("and that line is not written to the transcript", len(path.read_text().splitlines()) == lines)

    ignored = subprocess.run(["git", "check-ignore", "-q", str(HERE / "results" / "x.jsonl")], cwd=HERE).returncode == 0
    check("transcripts are never committed: lab/results is gitignored", ignored)

    sent: dict = {}
    fake_client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kw: sent.update(kw)))
    openai_call(fake_client, "RT-2026-001")(model=MODEL, input=[])
    check(
        "every request is tagged with the engagement and sent with storage off",
        sent.get("metadata") == {"red_team_engagement": "RT-2026-001"} and sent.get("store") is False,
        str(sent),
    )

    app, redis = docker_inspect("finbot-app"), docker_inspect("finbot-redis")
    if app is None or redis is None:
        print("SKIP FinBot container checks: finbot-app or finbot-redis is not running (lab/finbot/up.sh)")
    else:
        bindings = [b["HostIp"] for ports in app["HostConfig"]["PortBindings"].values() for b in ports]
        check("FinBot listens on this machine only", bindings == ["127.0.0.1"], str(bindings))
        check("FinBot's Redis is not published at all", not redis["HostConfig"]["PortBindings"], str(redis["HostConfig"]["PortBindings"]))
        for c in (app, redis):
            name = c["Name"].lstrip("/")
            hc = c["HostConfig"]
            check(f"{name} drops every Linux capability", hc["CapDrop"] == ["ALL"] and not hc["CapAdd"], f"{hc['CapDrop']} {hc['CapAdd']}")
            check(f"{name} cannot gain privileges", "no-new-privileges" in (hc["SecurityOpt"] or []), str(hc["SecurityOpt"]))
            check(f"{name} has a memory limit", hc["Memory"] > 0, str(hc["Memory"]))

    if failed:
        print("\n".join(failed))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
