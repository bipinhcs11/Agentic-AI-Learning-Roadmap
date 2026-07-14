# 07 — Model Selection & Context Engineering

Two skills separate developers who get consistently good Copilot output from those who
get lottery tickets: choosing the right model class for the task, and controlling what's
in the context window. Neither requires anything your enterprise hasn't already enabled.

## Model selection

The picker's exact lineup changes quarterly and your org curates it, so think in
**classes**, not product names:

| Class | Traits | Right tasks |
|---|---|---|
| **Fast / economy** | Lowest latency, smaller reasoning budget, often unlimited or cheap in premium-request terms | Completions-adjacent chat: explain this function, rename suggestions, commit messages, quick syntax questions, boilerplate |
| **Balanced default** | The org's standard chat/edit model | Day-to-day implementation, test generation, ordinary refactors — 80% of work |
| **Deep reasoning** | Slow, expensive, biggest context + reasoning budget | Architecture tradeoffs, gnarly concurrency/debugging, security review of complex diffs, cross-cutting migrations, agent-mode runs on non-trivial slices |

Three rules that survive every lineup change:

1. **Match cost to consequence.** A commit message drafted by the deep-reasoning model
   is waste; an auth-flow review done by the economy model is risk. Most enterprises
   meter premium requests — spend them where being wrong is expensive.
2. **Escalate on failure, don't retry.** If the default model produced a wrong fix
   twice, the third identical attempt is a superstition; move the task up a class or
   shrink the task.
3. **Pin models in prompt files where it matters.** `.prompt.md` and `.agent.md`
   frontmatter can specify a model — the security-review prompt should not silently
   run on whatever the developer last selected.

## Context engineering

The model can only be as right as what it can see — and *wrong context hurts more than
missing context*, because the model will confidently use it.

**The core discipline — small, verifiable tasks.** (The theme Addy Osmani keeps
hammering, and the single biggest predictor of agent-mode success.) "Build the service"
fails; "add the expiry-validation branch to `TokenValidator`, with tests" succeeds.
If you can't state how you'll verify the output, the task is too big — slice it.

**Curate, don't dump:**

- Attach the 2–3 files that matter (`#file`) instead of 20 "for context" — every
  irrelevant file dilutes attention over the relevant ones.
- Use `#codebase` for *finding* things, then attach what it found; don't make every
  request a repo-wide search.
- Pipe real artifacts, not paraphrases: `#testFailure`, `#terminalLastCommand`,
  `#changes`. Your summary of an error message deletes the one line that mattered.
- Point at reference implementations ("follow `src/orders/`") — one worked example
  outweighs paragraphs of description. This is the Reference line of the 6-part shape.

**Manage the conversation like memory:**

- Long chats rot: early corrections fall out of the effective window and the model
  reverts. **New task → new chat**, always.
- If a chat went sideways, don't argue with it — restate the corrected requirements
  fresh. Ten messages of "no, not like that" is context poisoning you're paying for.
- The always-on instruction files (chapter 02) are your persistent memory — anything
  you keep re-explaining per chat belongs there, stated once, versioned.

**Token economy in enterprise terms:** instructions inject into every request — that's
why chapter 02 caps them at ~60 lines. Skills load only on match — that's why deep
procedure lives there. Prompt files cost only when invoked. Put content in the cheapest
layer that still guarantees it's present when needed.

**Generate less: the reuse-first ladder.** The most expensive Copilot output isn't
wrong code — it's *unnecessary* code: a hand-rolled utility the framework already
ships, a new abstraction for one call site, three defensive layers nobody asked for.
Every surplus line is review burden, attack surface, and future migration cost. The
starter kit's instructions therefore include an ordered ladder the model must walk
before writing anything new: needed at all? → already in this codebase? → in the
stdlib/framework? → in an installed dependency? → only then write the minimum. Two
guardrails make this safe in a regulated org: the ladder never prunes validation,
error handling, authorization, audit, tests, or accessibility (those are
requirements, not verbosity), and for non-trivial changes the model states which
rung it stopped at — making "why does this code exist" a reviewable claim. (Pattern
distilled from [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail),
which reports large reductions in generated-code volume from exactly this
discipline; we take the ladder and the safety carve-out, not the framework.)

## The pairing that makes agent mode reliable

Small task + pinned verification (build/test/lint commands in the instructions) +
right model class + curated context. Remove any one and agent mode becomes a slot
machine; keep all four and it becomes a junior engineer who never gets tired.
