import unittest

from claims_lab import authorize, decode_payload, encode_fixture


class ClaimsLabTest(unittest.TestCase):
    def setUp(self) -> None:
        self.claims = {
            "sub": "agent:finance-assistant",
            "aud": ["fictional-invoice-api"],
            "scope": "invoice.read invoice.list",
            "tenant_id": "fictional-acme",
        }

    def test_fixture_round_trip(self) -> None:
        self.assertEqual(self.claims, decode_payload(encode_fixture(self.claims)))

    def test_authorizes_exact_resource_context(self) -> None:
        decision = authorize(
            self.claims,
            audience="fictional-invoice-api",
            scope="invoice.read",
            tenant="fictional-acme",
        )
        self.assertTrue(decision.allowed)

    def test_rejects_wrong_audience(self) -> None:
        decision = authorize(
            self.claims,
            audience="fictional-email-api",
            scope="invoice.read",
            tenant="fictional-acme",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("audience mismatch", decision.reason)

    def test_rejects_scope_or_tenant_escalation(self) -> None:
        missing_scope = authorize(
            self.claims,
            audience="fictional-invoice-api",
            scope="invoice.approve",
            tenant="fictional-acme",
        )
        cross_tenant = authorize(
            self.claims,
            audience="fictional-invoice-api",
            scope="invoice.read",
            tenant="fictional-globex",
        )
        self.assertEqual("missing scope", missing_scope.reason)
        self.assertEqual("tenant mismatch", cross_tenant.reason)


if __name__ == "__main__":
    unittest.main()
