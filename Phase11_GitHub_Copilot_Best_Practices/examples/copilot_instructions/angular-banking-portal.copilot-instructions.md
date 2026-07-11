<!-- EXAMPLE: save as .github/copilot-instructions.md in an Angular banking web app.
     Fictional app ("retail-banking-portal") — rename, keep the shape. -->

# Repository instructions for GitHub Copilot

## What this project is

`retail-banking-portal` is the customer-facing web app for retail banking: accounts,
transfers, payees, statements, secure messages. Angular 19 workspace with feature
libs under `libs/` (Nx). Sessions are short-lived by regulation; every screen may be
a customer's only channel to their money — accessibility failures are outages here,
not polish items.

## Architecture in five lines

- Nx workspace: `apps/portal` is thin shell + routing; ALL features live in
  `libs/feature-*`; shared UI only from `libs/ui` (the design system); data access
  only from `libs/data-access-*`.
- Standalone components, Signals for state, OnPush everywhere; RxJS only at
  event-stream edges, converted with `toSignal` in the data-access layer.
- Server calls ONLY through `libs/data-access-*` services returning typed models —
  a component importing `HttpClient` fails lint (`no-restricted-imports`).
- Auth: OIDC PKCE via `AuthService`; interceptor chain order is fixed:
  `authInterceptor → correlationIdInterceptor → problemDetailInterceptor` — register
  new interceptors in `core/http/provideHttp.ts`, nowhere else.
- Money renders through `<bk-amount>` / `AmountPipe` (minor units in, locale-aware
  out) — never `{{ amount | number }}` for currency.

## How to build, test, validate

- Affected build+test+lint (the normal loop): `npx nx affected -t build test lint`
- One lib: `npx nx test feature-transfers`
- E2E smoke (Playwright): `npx nx e2e portal-e2e --grep @smoke`
- A11y unit checks run inside component tests (axe) — an axe violation is a test failure.

## Banking-portal rules (non-negotiable)

- **Session & idle**: any new route must declare `data.sessionPolicy`
  (`standard | elevated`); elevated screens (payees, transfers over limit) trigger
  step-up auth via `StepUpGuard` — never build a bypass "for testing".
- **No PII in browser storage**: nothing customer-identifying in
  localStorage/sessionStorage/IndexedDB — session state lives server-side; the SPA
  holds tokens in memory only. Also: no PII in URLs, ever (routes use opaque ids).
- **Amounts**: integers in minor units end-to-end; parsing user input goes through
  `AmountInputDirective` (locale decimal handling) — never `parseFloat` on money.
- **Errors**: every data-access call maps failures to `ProblemDetail`; components
  render the four states (loading/empty/error/populated) — an unhandled error state
  fails review. Retry only reads, never mutations.
- **Accessibility (WCAG 2.2 AA)**: semantic first; forms use `libs/ui/forms` field
  components (label, error wiring, `aria-describedby` built in); focus management on
  route change via `FocusService`; all flows keyboard-complete. Dynamic content
  announcements through `LiveAnnouncer`, not custom aria-live divs.
- **i18n**: all user-facing strings through the i18n pipeline (`$localize`) — no
  hardcoded English, including error messages and aria-labels.

## Testing

- Component tests via Testing Library + axe; interact through the DOM, assert what
  the customer sees. HTTP via `provideHttpClientTesting`.
- Every feature lib keeps a `*.a11y.spec.ts` covering its primary flow at AA.
- Transfers/payees features additionally keep decision-table tests for limits and
  step-up boundaries (`libs/feature-transfers/DECISIONS.md` is the source of truth).

## What NOT to do

- No new global state containers — state is Signals in feature stores
  (`libs/feature-*/store`); if two features need the same state, it moves to a
  shared data-access lib, not a global store.
- No direct `window.open`/`location.href` — navigation through `Router`, external
  links through `ExternalLinkService` (it applies the interstitial policy).
- No `innerHTML` with any server-provided string; sanitization exceptions need a
  security reviewer on the PR.
- Do not add npm dependencies to `libs/ui` — the design system stays dependency-light
  by policy.
