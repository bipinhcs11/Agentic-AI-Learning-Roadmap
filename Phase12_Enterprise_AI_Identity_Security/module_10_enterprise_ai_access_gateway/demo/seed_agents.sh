#!/usr/bin/env sh
set -eu

identity_url="${IDENTITY_URL:-http://identity.localhost:8081}"
admin_token="${IDENTITY_ADMIN_TOKEN:-phase12-local-admin-token}"

register_agent() {
  curl -fsS "$identity_url/agent/register" \
    -H "X-Identity-Token: $admin_token" \
    -H 'Content-Type: application/json' \
    -d "$1"
}

finance="$(register_agent '{"displayName":"Fictional Finance Agent","ownerId":"demo.user","tenantId":"fictional-acme","scopes":["invoice.read"]}')"
email="$(register_agent '{"displayName":"Fictional Email Draft Agent","ownerId":"demo.user","tenantId":"fictional-acme","scopes":["email.draft"]}')"

jq -n \
  --arg finance_agent_id "$(printf '%s' "$finance" | jq -r '.id')" \
  --arg email_agent_id "$(printf '%s' "$email" | jq -r '.id')" \
  '{finance_agent_id:$finance_agent_id,email_agent_id:$email_agent_id,note:"Fictional local agents only"}'
