# Origin and adaptation

Derived from Matt Pocock's MIT-licensed skills at commit
`c55ee46073ed923f86ce59a5eb3b6d895095d1b7`, retrieved 2026-09-23:

- [grill-me](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/productivity/grill-me/SKILL.md)
- [grilling](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/productivity/grilling/SKILL.md)
- [License](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/LICENSE)

This directory is an enterprise adaptation, not an unchanged upstream release
or an endorsement by Matt Pocock. A copy of the upstream [MIT license](LICENSE)
is included so the folder can travel independently.

Changes: combine the delegating entrypoint with an executable file-based
workflow; remove the dependency on a named Skill tool and mandatory subagents;
bound interview rounds to the requested scope; respect decisions and implementation
authorization already given; add Spring/API/Batch decision examples. It retains
the design-tree approach and distinction between inspectable facts and user choices.
The upstream entrypoint's explicit-invocation policy is preserved in
`agents/openai.yaml`; normal development does not automatically start an interview.

The original files are separately retained in the Phase 14 third_party directory,
with hashes in its SOURCES.json. Those upstream files are reference material,
not automatically loaded operational instructions.
