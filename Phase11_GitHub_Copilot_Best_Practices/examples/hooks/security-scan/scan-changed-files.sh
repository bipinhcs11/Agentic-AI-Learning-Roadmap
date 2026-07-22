#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Security Scan Hook — deterministic guardrail for Copilot agent sessions
#
# Scans files the agent modified for secrets, PCI data (PAN), and
# banned patterns a regulated enterprise never allows in code.
# Runs after each edit (postToolUse) and at sessionEnd — see hooks.json.
#
# Exit non-zero in block mode => the agent's action is rejected.
# Instructions can be argued with; this script cannot. That's the point.
#
#   SCAN_MODE        warn | block                 (default: block)
#   SCAN_SCOPE       diff | staged                (default: diff — files vs HEAD)
#   SCAN_ALLOWLIST   comma-separated regexes of known false positives
#   SCAN_LOG_DIR     log directory                (default: .github/logs/security-scan)
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

MODE="${SCAN_MODE:-block}"
SCOPE="${SCAN_SCOPE:-diff}"
LOG_DIR="${SCAN_LOG_DIR:-.github/logs/security-scan}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/findings.jsonl"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# ── Collect changed files ───────────────────────────────────────────────────
if [[ "$SCOPE" == "staged" ]]; then
  FILES=$(git diff --cached --name-only --diff-filter=ACM)
else
  FILES=$(git diff HEAD --name-only --diff-filter=ACM; git ls-files --others --exclude-standard)
fi
[[ -z "$FILES" ]] && exit 0

# ── Patterns: name|regex  (extend for your org; keep names stable for logs) ─
# Secrets & credentials
PATTERNS=(
  'aws-access-key|AKIA[0-9A-Z]{16}'
  'github-pat|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}'
  'private-key-block|-----BEGIN (RSA|EC|OPENSSH|DSA|PGP) PRIVATE KEY'
  'generic-api-key|(api[_-]?key|apikey|secret[_-]?key)["'"'"'[:space:]]*[:=]["'"'"'[:space:]]*[A-Za-z0-9/+_-]{16,}'
  'password-literal|(password|passwd|pwd)["'"'"'[:space:]]*[:=]["'"'"'[:space:]]*["'"'"'][^"'"'"']{6,}'
  'bearer-jwt|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.'
  'db-connection-uri|(postgres|postgresql|mysql|mongodb|redis|jdbc:[a-z]+)://[^[:space:]"'"'"']*:[^[:space:]"'"'"']*@'
  # PCI: 16-digit PANs for major networks (Visa/MC/Amex/Discover shapes),
  # with or without separators. Test ranges are excluded via allowlist below.
  'pci-pan|\b(4[0-9]{3}|5[1-5][0-9]{2}|3[47][0-9]{2}|6011)([ -]?)[0-9]{4}\2[0-9]{4}\2[0-9]{2,4}\b'
  # Enterprise hygiene
  'internal-hostname|[a-z0-9-]+\.(corp|internal|intranet)\.[a-z0-9.-]+'
  'curl-pipe-shell|curl[^|;&]*\|[[:space:]]*(ba)?sh'
  # iOS/mobile estate: plists, entitlements, xcconfig. These flag *reviewable*
  # changes, not always violations — weakening ATS or enabling get-task-allow
  # is exactly the diff that must page a human, per the iOS instructions.
  'ios-ats-disabled|NSAllowsArbitraryLoads'
  'ios-get-task-allow|get-task-allow'
  'ios-plist-credential|<key>[^<]*(secret|api[_-]?key|token|password)[^<]*</key>'
  'ios-xcconfig-secret|^[A-Z0-9_]*(SECRET|API_KEY|TOKEN|PASSWORD)[A-Z0-9_]*[[:space:]]*=[[:space:]]*[^$[:space:]]+'
)

# Default allowlist: canonical test PANs + obvious placeholders. Extend via env.
# Placeholder tags must be hyphenated (<your-token>) — a bare <[a-z-]+> would
# match structural XML (<key>, <string>) and exempt entire plists from scanning.
ALLOWLIST='4111[ -]?1111[ -]?1111[ -]?1111,5555[ -]?5555[ -]?5555[ -]?4444,37828224631000[5],YOUR_|EXAMPLE|PLACEHOLDER|CHANGEME|<[a-z]+(-[a-z]+)+>|TODO'
[[ -n "${SCAN_ALLOWLIST:-}" ]] && ALLOWLIST="$ALLOWLIST,${SCAN_ALLOWLIST}"

FINDINGS=0
while IFS= read -r f; do
  [[ -f "$f" ]] || continue
  # Skip binaries, lockfiles, vendored dirs, and this hook's own patterns
  case "$f" in
    *.png|*.jpg|*.gif|*.pdf|*.zip|*.jar|*.lock|package-lock.json|node_modules/*|vendor/*|.github/hooks/security-scan/*) continue ;;
  esac
  file "$f" | grep -q text || continue

  for entry in "${PATTERNS[@]}"; do
    NAME="${entry%%|*}"; REGEX="${entry#*|}"
    while IFS= read -r hit; do
      [[ -z "$hit" ]] && continue
      LINE_NO="${hit%%:*}"; CONTENT="${hit#*:}"
      # Allowlist check (any allowlist regex match on the line ⇒ skip)
      SKIP=0
      IFS=',' read -ra ALLOW <<< "$ALLOWLIST"
      for a in "${ALLOW[@]}"; do
        [[ -n "$a" ]] && printf '%s' "$CONTENT" | grep -qiE "$a" && { SKIP=1; break; }
      done
      [[ "$SKIP" == "1" ]] && continue

      FINDINGS=$((FINDINGS + 1))
      REDACTED="$(printf '%s' "$CONTENT" | cut -c1-40)…[redacted]"
      printf '{"ts":"%s","file":"%s","line":%s,"rule":"%s","preview":"%s"}\n' \
        "$TS" "$f" "$LINE_NO" "$NAME" "${REDACTED//\"/\\\"}" >> "$LOG_FILE"
      echo "SECURITY-SCAN [$NAME] $f:$LINE_NO — $REDACTED" >&2
    done < <(grep -nEi "$REGEX" "$f" 2>/dev/null || true)
  done
done <<< "$FILES"

# ── Verdict ─────────────────────────────────────────────────────────────────
if [[ "$FINDINGS" -gt 0 ]]; then
  echo "SECURITY-SCAN: $FINDINGS finding(s). Log: $LOG_FILE" >&2
  if [[ "$MODE" == "block" ]]; then
    echo "SECURITY-SCAN: blocking (SCAN_MODE=block). Remove the flagged content or add a reviewed allowlist entry." >&2
    exit 1
  fi
fi
exit 0
