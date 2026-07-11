# ruff: noqa
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

import os

import google.auth
from google.auth.exceptions import DefaultCredentialsError
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.scheduler import recommend_delivery_windows


def configure_vertex_environment() -> None:
    """Configure Vertex AI defaults without requiring ADC during offline tests."""
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
    try:
        _, project_id = google.auth.default()
    except DefaultCredentialsError:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "local-grocery-demo")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)


configure_vertex_environment()


root_agent = Agent(
    name="delivery_scheduler",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="A remote A2A specialist that recommends fictional grocery delivery windows.",
    instruction=(
        "You are the delivery scheduler for a fictional grocery delivery demo. "
        "Use the delivery-window tool and do not handle payment or real customer data."
    ),
    tools=[recommend_delivery_windows],
)

app = App(
    root_agent=root_agent,
    name="app",
)
