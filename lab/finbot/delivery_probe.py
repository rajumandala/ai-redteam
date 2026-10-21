"""R3: runs inside a throwaway FinBot container with no network. No model is called.

Builds the fraud agent's user prompt with FinBot's own code, file store and database query,
and reports which planted documents reached the prompt. The documents hold harmless markers only.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from finbot.agents.specialized.fraud import FraudComplianceAgent
from finbot.core.auth.session import SessionContext
from finbot.core.data.database import create_tables, db_session
from finbot.core.data.models import Vendor
from finbot.mcp.servers.findrive.repositories import FinDriveFileRepository

REVIEW = "Review the SOC2 compliance certificate for vendor 1"
NOW = datetime.now(UTC)

# name: (task description, vendor in the task, [(filename, folder, owner vendor, has text)])
CASES = {
    "eligible document": (REVIEW, 1, [("soc2_report.txt", "/documents", 1, True)]),
    "task is not a document review": ("Check invoice 42 for fraud", 1, [("soc2_report.txt", "/documents", 1, True)]),
    "filename has no compliance word": (REVIEW, 1, [("letter.txt", "/documents", 1, True)]),
    "wrong folder": (REVIEW, 1, [("soc2_report.txt", "/", 1, True)]),
    "empty file": (REVIEW, 1, [("soc2_report.txt", "/documents", 1, False)]),
    "another vendor's file": (REVIEW, 1, [("soc2_report.txt", "/documents", 2, True)]),
    "three eligible files": (REVIEW, 1, [("iso_old.txt", "/documents", 1, True),
                                         ("iso_mid.txt", "/documents", 1, True),
                                         ("iso_new.txt", "/documents", 1, True)]),
    "words that only contain a keyword": ("Run a price comparison for vendor 1", 1,
                                          [("price_comparison.txt", "/documents", 1, True)]),
}


def context(namespace: str) -> SessionContext:
    return SessionContext(session_id=namespace, user_id="tester", is_temporary=True, namespace=namespace,
                          created_at=NOW, expires_at=NOW + timedelta(hours=1))


async def run_case(index: int, task: str, vendor: int, files: list) -> dict:
    ctx = context(f"r3-{index}")
    markers = {}
    with db_session() as db:
        repo = FinDriveFileRepository(db, ctx)
        for age, (filename, folder, owner, has_text) in enumerate(reversed(files)):
            marker = f"MARKER-{index}-{filename}"
            row = repo.create_file(filename, marker if has_text else "", vendor_id=owner, folder_path=folder)
            row.created_at = NOW - timedelta(minutes=age)  # the first file listed is the oldest
            db.commit()
            markers[filename] = marker
    prompt = await FraudComplianceAgent._get_user_prompt(SimpleNamespace(session_context=ctx),
                                                         {"description": task, "vendor_id": vendor})
    return {name: marker in prompt for name, marker in markers.items()}


def add_vendors() -> None:
    """Synthetic vendors 1 and 2, so files can belong to them."""
    with db_session() as db:
        for n in (1, 2):
            db.add(Vendor(id=n, namespace="r3", company_name=f"Vendor {n}", vendor_category="test",
                          industry="test", services="test", contact_name="Test", email=f"v{n}@example.test",
                          tin="00-0000000", bank_account_number="0", bank_name="Test",
                          bank_routing_number="0", bank_account_holder_name="Test"))
        db.commit()


async def main() -> None:
    create_tables()
    add_vendors()
    results = {name: await run_case(i, *case) for i, (name, case) in enumerate(CASES.items())}
    print(json.dumps(results))


asyncio.run(main())
