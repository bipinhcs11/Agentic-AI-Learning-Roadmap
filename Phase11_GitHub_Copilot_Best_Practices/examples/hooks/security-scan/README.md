---
name: 'Security Scan'
description: 'Blocks Copilot agent sessions from writing secrets, PCI data (PANs), internal hostnames, or curl-pipe-shell patterns — deterministic, PCI-aware, allowlist-supported'
tags: ['security', 'pci', 'secrets', 'post-tool-use', 'session-end']
---

# Security Scan Hook

A deterministic guardrail for Copilot agent sessions in regulated environments.
After every file edit (`postToolUse`) and again at `sessionEnd`, it scans the
session's changed files for content that must never enter a banking codebase —
and in block mode, **rejects the change mechanically**. Instructions ask the model
to behave; this hook removes the choice.

## What it catches

| Rule | Example of what triggers it |
|---|---|
| `aws-access-key`, `github-pat`, `private-key-block` | Cloud/platform credentials, key material |
| `generic-api-key`, `password-literal`, `bearer-jwt` | Hardcoded secrets and tokens |
| `db-connection-uri` | Connection strings with inline credentials |
| `pci-pan` | 16-digit card numbers (Visa/MC/Amex/Discover shapes) outside the approved test range — the PCI-DSS non-negotiable |
| `internal-hostname` | `*.corp.* / *.internal.*` hostnames leaking topology into code |
| `curl-pipe-shell` | `curl … \| sh` supply-chain patterns |
| `ios-ats-disabled`, `ios-get-task-allow` | ATS weakened or debuggable entitlement — legitimate sometimes, silently never |
| `ios-plist-credential`, `ios-xcconfig-secret` | Credential-shaped keys landing in plists / xcconfig instead of the Keychain or CI secrets |

Canonical test PANs (4111 1111 1111 1111 etc.) and obvious placeholders are
allowlisted by default; extend with `SCAN_ALLOWLIST` (comma-separated regexes)
through a **reviewed** PR — the allowlist is itself a security-relevant change.

## Install

```bash
mkdir -p .github/hooks
cp -r examples/hooks/security-scan .github/hooks/
chmod +x .github/hooks/security-scan/scan-changed-files.sh
echo ".github/logs/" >> .gitignore
```

Commit to your default branch. Findings are logged (redacted) as JSON Lines to
`.github/logs/security-scan/findings.jsonl` for SIEM pickup.

## Configuration

| Env | Values | Default |
|---|---|---|
| `SCAN_MODE` | `warn` (log only) / `block` (exit non-zero) | `block` |
| `SCAN_SCOPE` | `diff` (vs HEAD + untracked) / `staged` | `diff` |
| `SCAN_ALLOWLIST` | comma-separated regexes | test PANs + placeholders |
| `SCAN_LOG_DIR` | log path | `.github/logs/security-scan` |

## Why both `postToolUse` AND `sessionEnd`

`postToolUse` catches the violation the moment it's written — the agent sees the
rejection and self-corrects in-session. `sessionEnd` is the backstop that scans the
final state of everything touched, so nothing slips through interleaved edits.
Belt and suspenders, both cheap.

## Format

The `hooks.json` schema (`version: 1`, event → command list, stdin JSON with
`toolName`/`toolInput`, non-zero exit blocks) follows the convention used by the
hooks in [github/awesome-copilot](https://github.com/github/awesome-copilot/tree/main/hooks) —
see `secrets-scanner` and `tool-guardian` there for sibling examples worth
installing alongside this one.
