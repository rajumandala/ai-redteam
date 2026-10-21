"""R4: what the harness does and does not do for automated attacks. Stub model; no API calls.

Two checks show controls that hold, and two pin down known gaps, so a later fix makes them fail
and the note gets updated.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "src"))
from redteam.harness import Engagement, OutOfScope, Stop  # noqa: E402

MODEL = "gpt-6.1-sol"


def stub(tokens: int):
    return lambda **_: SimpleNamespace(model="stub-model", usage=SimpleNamespace(total_tokens=tokens))


class HarnessForAutomation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(HERE / "engagement.toml", self.tmp / "engagement.toml")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def load(self, **changes) -> Engagement:
        eng = Engagement.load(self.tmp / "engagement.toml")
        for key, value in changes.items():
            setattr(eng, key, value)
        return eng

    def test_generated_destinations_refused(self):
        eng = self.load()
        eng.check_url("http://127.0.0.1:8000/vendor/chat")
        for url in ["https://127.0.0.1:8000", "http://127.0.0.1:8001", "http://localhost:8000",
                    "https://finbot.example.org"]:
            with self.assertRaises(OutOfScope, msg=url):
                eng.check_url(url)

    def test_attacker_model_needs_a_scope_change(self):
        with self.assertRaises(OutOfScope):
            self.load().check_scope("agentdojo", "attacker-model")

    def test_known_gap_budget_is_per_process(self):
        sent = 0
        for _ in range(2):  # two scripts, or two runs of one script
            call = self.load(max_calls=3).wrap(stub(10), MODEL)
            while True:
                try:
                    call(input="x")
                    sent += 1
                except Stop:
                    break
        self.assertEqual(sent, 6)  # twice the engagement's limit of 3

    def test_known_gap_token_budget_can_overshoot(self):
        eng = self.load(max_tokens=100)
        call = eng.wrap(stub(150), MODEL)
        call(input="x")  # checked before sending, when 0 tokens were used
        self.assertEqual(eng.tokens, 150)
        with self.assertRaises(Stop):
            call(input="x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
