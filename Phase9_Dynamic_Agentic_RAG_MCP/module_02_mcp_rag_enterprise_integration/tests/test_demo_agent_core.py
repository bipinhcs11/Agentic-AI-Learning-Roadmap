import unittest

from demo_agent_core import answer


class DemoAgentCoreTest(unittest.TestCase):

    def test_combined_question_returns_mcp_and_rag_shape(self):
        response = answer(
            "I contribute 6% to my primary contribution. Am I getting the full match, and what is the 2026 employee limit?"
        )

        self.assertEqual("mcp+rag", response["route"])
        self.assertIn("Python MCP + RAG", response["backend"])
        self.assertIn("$5,400", response["answer"])
        self.assertIn("$24,500", response["answer"])
        self.assertIn("toolCalls", response)
        self.assertIn("retrievedDocuments", response)
        self.assertIn("citations", response)
        self.assertIn("calculate_primary_contribution_match", [tool["name"] for tool in response["toolCalls"]])
        self.assertIn("search_benefits_docs", [tool["name"] for tool in response["toolCalls"]])

    def test_savings_account_limit_routes_to_rag(self):
        response = answer("What is the 2026 savings account family contribution limit?")

        self.assertEqual("rag", response["route"])
        self.assertEqual(["search_benefits_docs", "list_sources"], [
            tool["name"] for tool in response["toolCalls"]
        ])
        self.assertEqual("savings_account_reference.md", response["retrievedDocuments"][0]["source"])
        self.assertIn("$8,750", response["answer"])

    def test_general_question_routes_directly(self):
        response = answer("What can this benefits assistant do?")

        self.assertEqual("direct", response["route"])
        self.assertEqual([], response["toolCalls"])
        self.assertEqual([], response["retrievedDocuments"])


if __name__ == "__main__":
    unittest.main()
