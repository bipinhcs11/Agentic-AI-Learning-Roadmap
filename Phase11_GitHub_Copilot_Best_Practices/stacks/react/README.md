# Stack Overlay — React

Drop-on addition to the [generic starter kit](../../copilot_starter_kit/): copy
`react.instructions.md` into `.github/instructions/` and the prompts into
`.github/prompts/`.

## Contents

| File | What it does |
|---|---|
| `react.instructions.md` | Path-scoped rules for `**/*.{tsx,ts}` — function components, server-state discipline, hook hygiene |
| `prompts/react-feature-component.prompt.md` | A typed feature component with explicit loading/empty/error states |
| `prompts/react-hook-with-tests.prompt.md` | A custom hook extracted and tested in isolation |

## The failure mode these target

Copilot's React output defaults to tutorial style: `useEffect`-driven fetching,
`useState` for everything including server data, and business logic braided into JSX.
Fine in a sandbox, expensive in an enterprise app with a query library, a design
system, and accessibility obligations. The instructions pin the grown-up defaults;
the prompts encode the two most-repeated tasks.

## Reference repos worth pinning

- [TanStack Query examples](https://github.com/TanStack/query/tree/main/examples) —
  server-state patterns done right
- [bulletproof-react](https://github.com/alan2207/bulletproof-react) — widely-adopted
  enterprise React architecture reference
- Your design-system repo — name it in `copilot-instructions.md`.
