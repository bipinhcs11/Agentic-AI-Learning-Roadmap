package phase12.delegation_test

import rego.v1
import data.phase12.delegation.allow

test_allows_tenant_matched_invoice_scope if {
    allow with input as {
        "user_tenant": "fictional-acme",
        "agent_tenant": "fictional-acme",
        "requested_scopes": ["invoice.read"],
        "audience": "http://mcp.localhost:8086/mcp"
    }
}

test_denies_cross_tenant_delegation if {
    not allow with input as {
        "user_tenant": "fictional-acme",
        "agent_tenant": "fictional-globex",
        "requested_scopes": ["invoice.read"],
        "audience": "http://mcp.localhost:8086/mcp"
    }
}

test_denies_unknown_scope if {
    not allow with input as {
        "user_tenant": "fictional-acme",
        "agent_tenant": "fictional-acme",
        "requested_scopes": ["invoice.approve"],
        "audience": "http://mcp.localhost:8086/mcp"
    }
}
