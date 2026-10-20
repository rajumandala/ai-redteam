"""The engagement harness: R1's rules of engagement, enforced in code.

Every attack goes through an Engagement. It refuses targets, accounts and models that
are out of scope, stops at the budget, stops when the stop file appears, tags every
request with the engagement ID, and writes transcripts where only the tester can read them.
"""

import hashlib
import json
import os
import re
import tomllib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")


class OutOfScope(Exception):
    pass


class Stop(Exception):
    """The engagement must stop now: budget used, stop file present, or a stop condition hit."""


@dataclass
class Engagement:
    id: str
    tester: str
    authorised_by: str
    expires: date
    environments: set[str]
    accounts: set[str]
    models: set[str]
    max_calls: int
    max_tokens: int
    stop_file: Path
    results_dir: Path
    known_pans: set[str]
    calls: int = 0
    tokens: int = 0

    @classmethod
    def load(cls, path: Path, known_pans: set[str]) -> "Engagement":
        raw = tomllib.loads(path.read_text())
        base = path.parent
        return cls(
            id=raw["id"],
            tester=raw["tester"],
            authorised_by=raw["authorised_by"],
            expires=date.fromisoformat(raw["expires"]),
            environments=set(raw["scope"]["environments"]),
            accounts=set(raw["scope"]["accounts"]),
            models=set(raw["scope"]["models"]),
            max_calls=raw["budget"]["max_calls"],
            max_tokens=raw["budget"]["max_tokens"],
            stop_file=base / raw["stop_file"],
            results_dir=base / raw["results_dir"],
            known_pans=known_pans,
        )

    def check_scope(self, environment: str, account: str, model: str, today: date | None = None) -> None:
        today = today or date.today()
        if not self.authorised_by:
            raise OutOfScope("no written authorisation")
        if today > self.expires:
            raise OutOfScope(f"authorisation expired on {self.expires.isoformat()}")
        if environment not in self.environments:
            raise OutOfScope(f"environment {environment} is not in scope")
        if account not in self.accounts:
            raise OutOfScope(f"account {account} is not in scope")
        if model not in self.models:
            raise OutOfScope(f"model {model} is not in scope")

    def guard(self) -> None:
        if self.stop_file.exists():
            raise Stop(f"stop file {self.stop_file.name} is present")
        if self.calls >= self.max_calls:
            raise Stop(f"call budget of {self.max_calls} used")
        if self.tokens >= self.max_tokens:
            raise Stop(f"token budget of {self.max_tokens} used")

    def wrap(self, raw_call: Callable[..., Any], model: str) -> Callable[..., Any]:
        """A model call that checks the stop rules before it is sent and counts what it used."""

        def call_model(**kwargs: Any) -> Any:
            self.guard()
            response = raw_call(model=model, **kwargs)
            self.calls += 1
            self.tokens += response.usage.input_tokens + response.usage.output_tokens
            return response

        return call_model

    def unknown_pans(self, text: str) -> set[str]:
        """PAN-shaped strings that are not one of the lab's canaries: possibly real client data."""
        return set(PAN.findall(text)) - self.known_pans

    def record(self, attempt: dict[str, Any]) -> str:
        """Append one attempt to this engagement's transcript file and return its hash."""
        self.results_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.results_dir / f"{self.id}.jsonl"
        line = json.dumps(
            {"engagement": self.id, "tester": self.tester, "at": datetime.now(timezone.utc).isoformat(), **attempt},
            default=str,
            sort_keys=True,
        )
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as out:
            out.write(line + "\n")
        leaked = self.unknown_pans(line)
        if leaked:
            raise Stop(f"stop condition: {len(leaked)} PAN-shaped value(s) that are not lab canaries")
        return hashlib.sha256(line.encode()).hexdigest()[:12]


def openai_call(client: Any, engagement_id: str) -> Callable[..., Any]:
    """The real model call. Storage is off (note 14), and the engagement ID goes with every request."""

    def raw_call(**kwargs: Any) -> Any:
        return client.responses.create(
            store=False,
            include=["reasoning.encrypted_content"],
            metadata={"red_team_engagement": engagement_id},
            **kwargs,
        )

    return raw_call
