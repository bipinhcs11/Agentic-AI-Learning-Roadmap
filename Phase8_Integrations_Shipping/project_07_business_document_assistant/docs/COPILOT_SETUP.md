# Direct GitHub Copilot setup

This adapter targets the organization's GitHub Copilot environment. It does not need Bedrock or a separate model-provider key. Product owners click **Generate with Copilot**, then review the document. Structured responses remain internal.

## Administrator setup for the local pilot

1. Confirm the organization's Copilot SDK/runtime policy, user entitlement, and permitted model. Use Python 3.11+.
2. In the project's own virtual environment, run `python -m pip install -r requirements-copilot.txt`. The adapter pins `github-copilot-sdk==1.0.14`; the root roadmap dependencies are unchanged.
3. Provision the compatible runtime through your approved software channel. The SDK documentation describes `python -m copilot download-runtime`, but enterprise machines may require centrally staged binaries. Preserve the runtime's adjacent assets. This app requires an explicit executable path and does not initiate runtime download.
4. Establish the operator's approved Copilot sign-in using the organization's supported runtime/CLI setup. A Confluence PAT is separate and cannot provide Copilot model access. Do not paste credentials into the browser or commit them.
5. Set these administrator variables before starting the app (PowerShell users should use `$env:NAME = 'value'`):

```bash
export BDA_COPILOT_ENABLED=1
export BDA_COPILOT_CLI=/absolute/path/to/approved/copilot-runtime
export BDA_COPILOT_MODEL=exact-org-approved-model-id
export COPILOT_SKIP_CLI_DOWNLOAD=1
python app.py
```

The UI reports **configured**, not authenticated: the first generation verifies live access. Without the SDK/path/model, Copilot is disabled and the fictional demo remains usable. Model changes require changing the administrator variable and restarting. Future model brands mentioned by the organization are not assumed to be available through Copilot; verify their exact runtime model IDs and entitlement before selection. A separate future provider adapter can be added without changing the product-owner flow.

## Runtime behavior

The server retrieves and snapshots selected evidence before inference. The SDK receives only the document request, context, previous version and required template. It runs in an empty temporary workspace, with no available tools, no custom project instructions and a rejecting permission callback. It cannot use the model to read arbitrary files or publish a page. Generation has a 120-second response timeout inside a 150-second adapter deadline; runtime teardown may add cleanup time. Response size, headings, note/source citations and baseline references are validated. These are structural checks, not semantic verification.

No unstructured provider error or credential is returned to the browser. Authentication, timeout or malformed-output failures fail the job without substituting an offline draft. The user can retry. Review/approval and publication remain application operations.

## Verification status

The implementation was checked against the installed SDK 1.0.14 constructor, session, permission and response method signatures. Controlled tests exercise prompt construction, resource cleanup and invalid/null responses. No Copilot runtime or sign-in exists on the development machine, so **live organization inference is not verified**. Before the demo inside the org, run one fictional MOM request and one BRD revision; confirm the provider label says Copilot, the selected model is recorded, and Word contains the reviewed text.

## Shared enterprise service (next phase)

Do not expose this loopback POC or reuse one employee's personal sign-in for all product owners. Replace browser-cookie ownership with SSO/project authorization, use an approved per-user or service authentication arrangement supported by GitHub and your enterprise, durable jobs, user quotas, audit retention and permission-aware retrieval. Validate deployment/authentication choices with your Copilot administrators before a shared rollout.

Official references: [Python SDK and runtime setup](https://github.com/github/copilot-sdk/blob/main/python/README.md), [backend services setup](https://docs.github.com/en/copilot/how-tos/copilot-sdk/setup/backend-services). Checked September 23, 2026; the pinned adapter should be contract-tested before upgrading.
