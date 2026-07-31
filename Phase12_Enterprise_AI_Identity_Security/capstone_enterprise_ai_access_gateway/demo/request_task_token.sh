#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: $0 AGENT_ID SCOPE" >&2
  exit 2
fi

agent_id="$1"
scope="$2"
identity_url="${IDENTITY_URL:-http://identity.localhost:8081}"
broker_token="${IDENTITY_BROKER_TOKEN:-phase12-local-broker-token}"
task_id="task-smoke-$(date +%s)"

jq -n \
  --arg agentId "$agent_id" \
  --arg taskId "$task_id" \
  --arg scope "$scope" \
  '{agentId:$agentId,taskId:$taskId,actorId:"workload:smoke-test",requestedScopes:[$scope],audience:"http://mcp.localhost:8086/mcp",ttlSeconds:600,delegationDepth:0}' \
| curl -fsS "$identity_url/agent/task-token" \
    -H "X-Identity-Token: $broker_token" \
    -H 'Content-Type: application/json' \
    --data-binary @-
