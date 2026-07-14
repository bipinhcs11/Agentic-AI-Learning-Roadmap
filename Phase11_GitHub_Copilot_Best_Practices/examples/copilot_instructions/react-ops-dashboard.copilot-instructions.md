<!-- EXAMPLE: save as .github/copilot-instructions.md in a React internal ops tool.
     Fictional app ("payments-ops-dashboard") — rename, keep the shape. -->

# Repository instructions for GitHub Copilot

## What this project is

`payments-ops-dashboard` is the internal tool operations staff use to monitor payment
flows, investigate stuck payments, and (with dual authorization) repair them. Users
are trained operators, not customers — density and speed beat hand-holding — but
every action here touches production money movement, so **auditability beats
convenience**.

## Architecture in five lines

- Vite + React 19 + TypeScript strict; feature folders under `src/features/*`
  (`queue-monitor/`, `payment-inspector/`, `repair-console/`, `audit-viewer/`).
- Server state: TanStack Query, key factories in `src/features/*/queries.ts` —
  no `useEffect` fetching, no ad-hoc keys. Live queue data polls via
  `refetchInterval` presets in `src/lib/polling.ts` (5s/30s/off — operator-selectable).
- Client state: Zustand for the operator's workspace (selected queue, filters,
  layout) — nothing server-derived goes in it.
- All mutations flow through `useAuthorizedMutation` — it enforces the reason-code
  prompt, dual-auth token for `repair.*` actions, and writes the audit breadcrumb.
  A raw `useMutation` for a repair action fails lint.
- Tables are TanStack Table via our `<OpsTable>` wrapper (virtualized, column
  presets, CSV export with the export-audit event built in).

## How to build, test, validate

- Dev: `npm run dev` (MSW mocks on by default; `VITE_MSW=off` for real APIs)
- Test: `npm run test` (Vitest + Testing Library + MSW)
- Lint + types: `npm run lint && npm run typecheck`
- A task is complete only when test, lint, and typecheck all pass.

## Ops-tool rules (non-negotiable)

- **Every mutation needs**: a reason code from `ReasonCodes` (no free-text-only),
  optimistic-update rollback, and an audit event — `useAuthorizedMutation` gives you
  all three; use it.
- **Repair actions are dual-auth**: initiator ≠ approver, enforced server-side but
  the UI must render the pending-approval state honestly — never fake completion.
- **Read scopes**: components render according to `usePermissions()` — hiding a
  button is UX, not security; never assume the UI is the enforcement point.
- **Data handling**: masked account display (`****1234`) via `<MaskedAccount>`
  with the reveal action itself audited; CSV exports go through `<OpsTable>` export
  (never hand-rolled `Blob` downloads — the export audit event is mandatory).
- **Time**: everything renders in the operator's selected timezone via `useOpsTime()`
  (UTC default) with the raw UTC timestamp in the title attribute — incident
  timelines have been corrupted by implicit local time before; don't repeat it.
- **Polling discipline**: no new intervals outside `src/lib/polling.ts` presets;
  every polled query pauses on `document.hidden`.

## Testing

- MSW handlers per feature in `src/features/*/mocks.ts` — new endpoints get handlers
  in the same PR (dev and tests share them).
- Repair-console tests must cover: happy path, rejection by approver, expiry of the
  dual-auth window, and the audit event payload.
- Table features test with virtualized rendering ON (that's where the bugs are).

## What NOT to do

- No new dependencies for UI primitives — `src/components/ui` (Radix-based) is the
  kit; ops tools don't get design experiments.
- No `useEffect` to synchronize state you own — derive it; if you can't derive it,
  the state shape is wrong.
- No swallowing errors into toasts for mutations — mutation failures render inline
  in the acting row/panel with the correlation id the operator can paste into the
  audit viewer.
- Do not touch `src/features/repair-console/` without also updating its
  `RUNBOOK.md` — operators follow it during incidents; drift there causes real harm.
