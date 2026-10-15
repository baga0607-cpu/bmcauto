# Domain Docs

How the engineering skills should consume this repository's domain documentation when exploring the codebase.

## Before exploring, read these

- `CONTEXT.md` at the repository root.
- `CONTEXT-MAP.md` at the repository root if it exists; it points to one `CONTEXT.md` per context.
- Relevant ADRs under `docs/adr/`.

If these files do not exist, proceed silently. Do not require them to be created up front. The `domain-modeling` skill, including when reached through `grill-with-docs` or `improve-codebase-architecture`, creates them lazily when terminology or decisions are resolved.

## File structure

This is a single-context repository:

```text
/
|-- CONTEXT.md
|-- docs/
|   `-- adr/
`-- main_program/
```

## Use the glossary's vocabulary

When output names a domain concept in an issue title, refactor proposal, hypothesis, or test name, use the term defined in `CONTEXT.md`. Do not drift to synonyms the glossary explicitly avoids.

If a needed concept is not in the glossary, reconsider whether the term belongs to the project or note the gap for `domain-modeling`.

## Flag ADR conflicts

If proposed work contradicts an existing ADR, surface the conflict explicitly rather than silently overriding the recorded decision.
