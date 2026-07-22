import json
import tempfile
import unittest
from pathlib import Path

from validate_provider_mapping import validate


class ProviderMappingValidationTest(unittest.TestCase):
    def test_rejects_long_lived_key_recommendation(self) -> None:
        document = {
            "platform": "example",
            "principal": "workload",
            "delegated_actor": "user",
            "credential_strategy": "static key",
            "audience_binding": "none",
            "revocation": "delete key",
            "audit": "logs",
            "no_long_lived_keys": False,
            "limitations": ["educational fixture"],
            "official_sources": ["https://example.invalid/docs"],
            "last_verified": "2026-07-20",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mapping.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            self.assertIn(
                "no_long_lived_keys must be true for the recommended mapping",
                validate(path),
            )


if __name__ == "__main__":
    unittest.main()
