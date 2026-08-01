# Five-Day Delivery Plan

## Planning assumptions

- Two engineers are full-time for the week.
- The goal is a sandbox MVP, not a production release.
- The test corpus is fictional and deterministic.
- One supported VS Code MCP host is selected and pinned on day 1.
- Work stops at one working vertical slice before optional features begin.

## Workstreams

| Workstream | Owner | Output |
|---|---|---|
| Gateway and registry | Platform engineer | MCP endpoint, validated snapshot, policy, routing, audit |
| Server and integration | MCP engineer | three tools, fictional CI adapter, schemas, server tests |
| Security and acceptance | Shared + reviewer | threat review, negative tests, evidence pack |
| Client and demo | Shared + DevEx owner | VS Code configuration, runbook, recorded demo |

## Day 1 — Freeze the contract

**Build**

- confirm use case, data boundary, and three tool contracts;
- pin Java, Spring, MCP SDK/starter, VS Code, and protocol versions;
- validate VS Code to a minimal remote Streamable HTTP MCP server;
- finalize registry schema and example manifest;
- draw trust boundaries and agree the token claims;
- create the Docker Compose skeleton and deterministic CI fixtures.

**Exit criteria**

- the selected VS Code build completes `initialize` and `tools/list` against a
  spike server;
- architecture, tool schemas, and explicit exclusions are signed off;
- IdP and CI dependencies are classified as ready or fallback;
- no unresolved question changes the service boundaries.

**Stop condition:** If the IDE cannot traverse the intended gateway transport,
continue with a protocol test client and report IDE compatibility as unproven.
Do not spend the entire week building a custom extension.

## Day 2 — Complete the happy path

**Platform engineer**

- load and validate the registry snapshot;
- implement `initialize`, `tools/list`, route lookup, and `tools/call` proxy;
- add correlation IDs, timeout, and bounded request parsing.

**MCP engineer**

- implement the three tool schemas and handlers;
- build the fictional CI adapter;
- ensure resources, prompts, sampling, and write tools are not advertised.

**Exit criteria**

- a protocol client obtains exactly three tools through the gateway;
- an allowed build-status call returns deterministic fictional data;
- the server is not directly reachable from the client network in Compose.

## Day 3 — Prove deny-by-default

**Build**

- validate issuer, audience, expiry, user, and client ID;
- authorize server, tool, application, environment, and registry status;
- reject unknown fields, oversized values, malformed IDs, and non-read tools;
- add separate gateway-to-server identity and server-side scope checks;
- produce metadata-only allow and deny audit events;
- run a focused threat-model review.

**Exit criteria**

- the negative matrix in the acceptance plan passes;
- no inbound user token reaches the MCP server's CI adapter;
- audit evidence contains no token, prompt, tool arguments, or tool result;
- security reviewer either accepts the demo scope or records a stop issue.

## Day 4 — Integrate the IDE and failure controls

**Build**

- connect the pinned VS Code host to the gateway;
- exercise the target build-failure scenario;
- add response caps, upstream timeout, sanitized errors, and health checks;
- prove disabled-server and stale-snapshot behavior;
- write the operator and demo runbooks;
- run the complete local test suite twice from a clean environment.

**Exit criteria**

- VS Code completes the end-to-end tool call through the gateway;
- timeout, deny, malformed input, and server-disable scenarios are observable;
- a second developer can follow the runbook without tribal knowledge.

## Day 5 — Evidence and decision

**Build**

- fix only release-blocking defects;
- record the approved demo and capture test results;
- document unproven dependencies and residual risks;
- estimate the production-pilot discovery and hardening backlog;
- hold the go/no-go review.

**Exit criteria**

- all mandatory acceptance criteria pass;
- reviewers can correlate each demo call by trace ID;
- the team demonstrates emergency disablement;
- the decision record says one of: stop, extend the sandbox, or fund pilot
  discovery.

## Scope fallback ladder

Cut scope in this order when the schedule is threatened:

1. remove enterprise test IdP integration and use the local issuer;
2. remove live CI sandbox integration and use fictional fixtures;
3. remove `get_application_owner`;
4. remove `get_test_failures`;
5. keep one end-to-end `get_build_status` tool.

Never cut:

- gateway-only routing;
- audience validation and separate downstream credentials;
- deny-by-default tool and application policy;
- bounded schemas and timeouts;
- metadata-only audit correlation;
- negative acceptance tests.

## After the week

A realistic production pilot requires a separate discovery and hardening phase.
Plan it only after the MVP produces evidence. Likely work includes enterprise
SSO and entitlement onboarding, signed registry distribution, gateway HA,
network policy, SIEM/DLP integration, conformance CI, support ownership,
capacity tests, incident runbooks, and one approved internal CI API integration.

IntelliJ, source intelligence, a portal, and self-service onboarding should be
sequenced after the first production-pilot use case is stable.
