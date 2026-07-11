---
mode: agent
description: "Typed React feature component with query-library data and full state handling"
---

# /react-feature-component

**Role**: You are a senior React engineer on an enterprise app with a design system
and a query library already in place — your job is to use them, not to reinvent them.

**Context**: `react.instructions.md` applies. Feature to build:
${input:feature:Name + responsibility, e.g. "PayeeList — searchable list of saved payees with delete"}

**Task**: Implement the feature slice — data hook + presentational component(s) —
plus tests.

**Constraints**:
- Server data through the repo's query library with its key-factory convention;
  mutations invalidate precisely, not globally. Zero `useEffect` fetching.
- Loading, empty, error, populated states all rendered, using design-system
  components for spinner/empty/error patterns.
- Presentational components take typed props and perform no data access.
- Accessibility: list/table semantics, labeled controls, focus management on
  destructive actions (confirm dialog per repo pattern).
- No new dependencies, no new global state.

**Output**: Hook + component files, RTL tests with mocked network (all four states,
search interaction, delete flow incl. optimistic/rollback if the repo pattern uses it),
and test-run evidence.

**Reference**: ${input:reference:Path to the closest existing feature slice}
