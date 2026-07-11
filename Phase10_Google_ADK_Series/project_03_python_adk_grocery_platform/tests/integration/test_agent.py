# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from app.agent import catalog_specialist, checkout_security_specialist, root_agent


def test_agent_configuration_has_grocery_specialists() -> None:
    """Verify the ADK agent is wired to the grocery module capabilities."""
    assert root_agent.name == "grocery_concierge"
    assert {agent.name for agent in root_agent.sub_agents} == {
        "catalog_specialist",
        "checkout_security_specialist",
    }
    assert catalog_specialist.description
    assert checkout_security_specialist.description


def test_agent_instruction_keeps_domain_clean() -> None:
    """The grocery module must stay in its own domain."""
    instruction = root_agent.instruction.lower()
    assert "grocery" in instruction
    blocked_terms = (
        "".join(("bene", "fits")),
        "".join(("retire", "ment")),
        "".join(("pay", "roll")),
        "".join(("h", "sa")),
        "".join((str(400 + 1), "k")),
    )
    assert not any(term in instruction for term in blocked_terms)
