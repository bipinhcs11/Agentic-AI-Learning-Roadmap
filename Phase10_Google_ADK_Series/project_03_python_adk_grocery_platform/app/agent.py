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

from app.security_judge import SecurityGuardianPlugin
from app.tools import (
    ask_delivery_scheduler,
    create_cart,
    issue_demo_jit_token,
    prepare_checkout,
    render_grocery_a2ui,
    search_grocery_catalog,
    show_agent_bill_of_materials,
    verify_demo_agent_identity,
)


def configure_vertex_environment() -> None:
    """Configure Vertex AI defaults without requiring ADC during offline tests."""
    # gemini-flash-latest is served on the `global` endpoint, not regional ones.
    # Hard-set (not setdefault) so the eval harness's manifest region (e.g.
    # us-east1) cannot shadow it and trigger a 404 NOT_FOUND on the model.
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
    try:
        _, project_id = google.auth.default()
    except DefaultCredentialsError:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "local-grocery-demo")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)


configure_vertex_environment()


catalog_specialist = Agent(
    name="catalog_specialist",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Finds fictional grocery products and renders A2UI catalog cards.",
    instruction=(
        "You are the catalog specialist for a fictional grocery delivery demo. "
        "Use the catalog and A2UI tools. Never invent prices or products. "
        "Always finish your turn with a short natural-language summary of what "
        "you rendered or found — never end on a bare tool call."
    ),
    tools=[search_grocery_catalog, render_grocery_a2ui],
)

checkout_security_specialist = Agent(
    name="checkout_security_specialist",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Explains and applies checkout security controls.",
    instruction=(
        "You teach security by applying JIT downscoped tokens, signed agent "
        "identity checks, Vibe-Diff approval, UCP checkout, and AP2 mandate "
        "simulation. Use tools and keep all data fictional. "
        "When asked to explain the checkout security gates, enumerate each one "
        "concretely and specifically: (1) signed SPIFFE-style agent identity + "
        "spoof detection on every A2A call; (2) a JIT token scoped to exactly "
        "one action (create_ap2_mandate) and one cart id, that expires in "
        "minutes and is rejected for any other action or resource; (3) the "
        "hybrid policy gate (structural limits + semantic review); (4) the "
        "Vibe-Diff plain-English approval a human must confirm; (5) the AP2 "
        "mandate bound to that JIT token. Name what each gate blocks. "
        "Always end with a short natural-language summary."
    ),
    tools=[
        issue_demo_jit_token,
        verify_demo_agent_identity,
        show_agent_bill_of_materials,
    ],
)


root_agent = Agent(
    name="grocery_concierge",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Coordinates a secure fictional grocery delivery checkout flow.",
    instruction=(
        "You are a Python ADK 2.0 grocery delivery concierge for a learning "
        "roadmap. Keep the domain strictly grocery delivery and avoid cross-domain "
        "examples or real customer data. Use tools for catalog, cart, delivery scheduling, "
        "A2UI rendering, UCP checkout, AP2 mandate simulation, and security "
        "controls. For checkout, always explain the Vibe-Diff and require "
        "approval before creating the payment mandate. "
        "Always end your turn with a concise natural-language summary for the "
        "user — never stop on a bare tool call or a silent sub-agent transfer."
    ),
    tools=[
        search_grocery_catalog,
        render_grocery_a2ui,
        create_cart,
        ask_delivery_scheduler,
        prepare_checkout,
        show_agent_bill_of_materials,
    ],
    sub_agents=[catalog_specialist, checkout_security_specialist],
)

app = App(
    root_agent=root_agent,
    name="app",
    # Runtime Agent-as-a-Judge: intercepts the high-stakes checkout tool and
    # blocks any AP2 mandate that would escape approval / policy / JIT scoping.
    plugins=[SecurityGuardianPlugin()],
)
