package phase12.delegation

import rego.v1

default allow := false

allowed_scopes := {"invoice.read", "email.draft"}

invalid_scopes contains scope if {
    scope := input.requested_scopes[_]
    not scope in allowed_scopes
}

allow if {
    input.user_tenant == input.agent_tenant
    input.audience == "http://mcp.localhost:8086/mcp"
    count(input.requested_scopes) > 0
    count(invalid_scopes) == 0
}
