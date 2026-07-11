# Stack Overlay — Angular

Drop-on addition to the [generic starter kit](../../copilot_starter_kit/): copy
`angular.instructions.md` into `.github/instructions/` and the prompts into
`.github/prompts/`.

## Contents

| File | What it does |
|---|---|
| `angular.instructions.md` | Path-scoped rules for `**/*.ts` in Angular apps — standalone + Signals-first, typed forms, injection patterns |
| `prompts/signals-component.prompt.md` | A standalone component with Signals state, typed inputs/outputs, OnPush |
| `prompts/typed-reactive-form.prompt.md` | A strictly-typed Reactive Form with validation and accessible errors |
| `prompts/functional-interceptor.prompt.md` | A functional HTTP interceptor (auth/correlation/errors) with tests |

## Why these three prompts

They target exactly the places where Copilot's training data skews old: it will happily
generate NgModules, untyped `FormGroup`s, and class-based interceptors — all legacy
patterns in modern Angular. The instructions file pins the modern baseline; the prompts
encode the full pattern for the three most-repeated tasks so nobody relearns them per
sprint.

## Reference repos worth pinning

- [angular/examples](https://github.com/angular/examples) — official Signals-era samples
- Your design-system/component library repo — name it in `copilot-instructions.md`;
  in-house patterns beat public ones.
