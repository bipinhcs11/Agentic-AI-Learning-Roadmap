import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("aws", "azure", "gcp")
REQUIRED_FILES = {
    "versions.tf",
    "providers.tf",
    "variables.tf",
    "main.tf",
    "outputs.tf",
    "terraform.tfvars.example",
    ".terraform.lock.hcl",
    "tests/foundation.tftest.hcl",
}


class InfrastructureContractTest(unittest.TestCase):
    def track_text(self, track: str) -> str:
        return "\n".join(
            path.read_text()
            for path in sorted((ROOT / track).glob("*.tf"))
        )

    def test_each_track_has_a_complete_terraform_foundation(self):
        for track in TRACKS:
            with self.subTest(track=track):
                present = {
                    str(path.relative_to(ROOT / track))
                    for path in (ROOT / track).rglob("*")
                    if path.is_file() and ".terraform" not in path.parts
                }
                self.assertTrue(REQUIRED_FILES <= present)

    def test_runtime_creation_is_disabled_by_default(self):
        for track in TRACKS:
            with self.subTest(track=track):
                variables = (ROOT / track / "variables.tf").read_text()
                runtime = re.search(
                    r'variable "enable_runtime"\s*\{(?P<body>.*?)\n\}',
                    variables,
                    re.DOTALL,
                )
                self.assertIsNotNone(runtime)
                self.assertRegex(runtime.group("body"), r"default\s*=\s*false")

    def test_every_track_requires_a_bounded_budget(self):
        expected = {
            "aws": "aws_budgets_budget",
            "azure": "azurerm_consumption_budget_resource_group",
            "gcp": "google_billing_budget",
        }
        for track, resource in expected.items():
            with self.subTest(track=track):
                text = self.track_text(track)
                self.assertIn(resource, text)
                self.assertIn("monthly_budget_usd", text)
                self.assertIn("<= 100", text)

    def test_cloud_ci_uses_github_oidc_instead_of_keys(self):
        for track in TRACKS:
            with self.subTest(track=track):
                text = self.track_text(track)
                self.assertIn("token.actions.githubusercontent.com", text)

        self.assertIn(
            "sts:AssumeRoleWithWebIdentity", self.track_text("aws")
        )
        self.assertIn(
            "azurerm_federated_identity_credential", self.track_text("azure")
        )
        self.assertIn(
            "google_iam_workload_identity_pool_provider", self.track_text("gcp")
        )

    def test_runtime_images_must_be_immutable_digests(self):
        for track in TRACKS:
            with self.subTest(track=track):
                self.assertIn("@sha256:", self.track_text(track))

    def test_examples_contain_no_credentials_or_employer_names(self):
        forbidden = (
            r"AKIA[0-9A-Z]{16}",
            r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY",
            "(?i)" + "fide" + "lity",
            "(?i)\\b" + "f" + "mr\\b",
        )
        for path in ROOT.rglob("*"):
            if (
                not path.is_file()
                or ".terraform" in path.parts
                or "__pycache__" in path.parts
                or path.suffix in {".pyc", ".pyo"}
            ):
                continue
            text = path.read_text(errors="ignore")
            for pattern in forbidden:
                with self.subTest(path=path, pattern=pattern):
                    self.assertIsNone(re.search(pattern, text))


if __name__ == "__main__":
    unittest.main()
