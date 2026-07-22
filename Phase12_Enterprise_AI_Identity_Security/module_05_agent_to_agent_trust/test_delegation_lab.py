import unittest

from delegation_lab import AgentPolicy, Credential, DelegationDenied, delegate


class DelegationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parent = Credential(
            subject="agent:planner",
            audience="broker",
            tenant_id="fictional-acme",
            task_id="task-001",
            scopes=frozenset({"invoice.read", "email.draft"}),
            token_id="parent-jti",
            actor_id="user:demo",
            delegation_depth=0,
        )
        self.email = AgentPolicy(
            "agent:email", "fictional-email-api", frozenset({"email.draft"})
        )

    def test_attenuates_and_preserves_task_boundary(self) -> None:
        child = delegate(
            self.parent, self.email, {"email.draft"}, child_token_id="child-jti"
        )
        self.assertEqual(frozenset({"email.draft"}), child.scopes)
        self.assertEqual("fictional-acme", child.tenant_id)
        self.assertEqual("task-001", child.task_id)
        self.assertEqual("agent:planner", child.actor_id)
        self.assertEqual(1, child.delegation_depth)

    def test_rejects_parent_or_child_scope_escalation(self) -> None:
        with self.assertRaisesRegex(DelegationDenied, "outside its allow-list"):
            delegate(self.parent, self.email, {"invoice.read"}, child_token_id="x")

        narrow_parent = Credential(
            **{**self.parent.__dict__, "scopes": frozenset({"invoice.read"})}
        )
        with self.assertRaisesRegex(DelegationDenied, "not held by its parent"):
            delegate(narrow_parent, self.email, {"email.draft"}, child_token_id="x")

    def test_rejects_excessive_depth(self) -> None:
        deep_parent = Credential(
            **{**self.parent.__dict__, "delegation_depth": 2}
        )
        with self.assertRaisesRegex(DelegationDenied, "depth"):
            delegate(deep_parent, self.email, {"email.draft"}, child_token_id="x")


if __name__ == "__main__":
    unittest.main()
