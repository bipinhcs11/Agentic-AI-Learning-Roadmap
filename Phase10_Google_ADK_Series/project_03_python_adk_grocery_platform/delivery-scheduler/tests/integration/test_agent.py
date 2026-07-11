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

from app.agent import root_agent
from app.scheduler import recommend_delivery_windows


def test_delivery_scheduler_agent_configuration() -> None:
    """Verify the remote A2A specialist exposes delivery scheduling behavior."""
    assert root_agent.name == "delivery_scheduler"
    assert "delivery" in root_agent.description.lower()


def test_delivery_window_tool_contract() -> None:
    """Verify the deterministic scheduling logic used behind the A2A agent."""
    result = recommend_delivery_windows(zip_code="60601", requested_day="tomorrow")
    assert result["status"] == "success"
    assert result["recommended_window"] in result["available_windows"]
