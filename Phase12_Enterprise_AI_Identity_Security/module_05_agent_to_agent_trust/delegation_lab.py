"""Framework-free permission attenuation for fictional enterprise agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


class DelegationDenied(ValueError):
    pass


@dataclass(frozen=True)
class Credential:
    subject: str
    audience: str
    tenant_id: str
    task_id: str
    scopes: FrozenSet[str]
    token_id: str
    actor_id: str
    delegation_depth: int


@dataclass(frozen=True)
class AgentPolicy:
    agent_id: str
    audience: str
    allowed_scopes: FrozenSet[str]
    max_delegation_depth: int = 2


def delegate(
    parent: Credential,
    child: AgentPolicy,
    requested_scopes: set[str],
    *,
    child_token_id: str,
) -> Credential:
    requested = frozenset(requested_scopes)
    if not requested:
        raise DelegationDenied("a child credential needs at least one scope")
    if not requested.issubset(parent.scopes):
        raise DelegationDenied("child requested scopes not held by its parent")
    if not requested.issubset(child.allowed_scopes):
        raise DelegationDenied("child requested scopes outside its allow-list")
    next_depth = parent.delegation_depth + 1
    if next_depth > child.max_delegation_depth:
        raise DelegationDenied("delegation depth exceeds policy")
    return Credential(
        subject=child.agent_id,
        audience=child.audience,
        tenant_id=parent.tenant_id,
        task_id=parent.task_id,
        scopes=requested,
        token_id=child_token_id,
        actor_id=parent.subject,
        delegation_depth=next_depth,
    )


def main() -> None:
    planner = Credential(
        subject="agent:planner",
        audience="agent-delegation-broker",
        tenant_id="fictional-acme",
        task_id="task-001",
        scopes=frozenset({"invoice.read", "email.draft"}),
        token_id="token-planner",
        actor_id="user:demo",
        delegation_depth=0,
    )
    finance_policy = AgentPolicy(
        "agent:finance", "fictional-invoice-api", frozenset({"invoice.read"})
    )
    email_policy = AgentPolicy(
        "agent:email", "fictional-email-api", frozenset({"email.draft"})
    )
    finance = delegate(planner, finance_policy, {"invoice.read"}, child_token_id="token-finance")
    email = delegate(planner, email_policy, {"email.draft"}, child_token_id="token-email")

    print("Planner scopes:", " ".join(sorted(planner.scopes)))
    print("Finance scopes:", " ".join(sorted(finance.scopes)))
    print("Email scopes:", " ".join(sorted(email.scopes)))
    try:
        delegate(planner, email_policy, {"invoice.read"}, child_token_id="token-denied")
    except DelegationDenied as error:
        print(f"Escalation check: DENY ({error})")


if __name__ == "__main__":
    main()
