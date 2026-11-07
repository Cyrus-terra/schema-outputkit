# Development and release checks

## Layout and language

- `skills/schema-outputkit/SKILL.md`: one portable runtime entry; no installation-script dependencies.
- `scripts/hook.py`: bounded standard-library event analysis and fixed context output.
- `hooks/hooks.json`: shared SessionStart configuration; `hooks/development.json`: additional Claude/CodeBuddy events.
- Client descriptors and minimal registration entries: packaging only, not model adapters. Hermes has a root manifest/forwarding entry for current directory discovery plus its shared hidden adapter.
- `scripts/validate_repository.py` and `tests/`: offline maintenance tools.

Keep natural-language instructions, prompts, metadata, diagnostics, comments and maintenance documents English. Only `README.zh-CN.md` is a translated prose edition. Chinese literals in trigger patterns and regression input fixtures intentionally preserve Chinese request support; do not translate them away. The language check can detect unintended CJK in prose locations, but does not establish English grammar or translation equivalence.

## Checks

Run the commands in the README from the repository root. Python 3.9+ and Node 18+ are sufficient for deterministic tests. Shell-command checks run on POSIX and are skipped on Windows; the remaining tests are portable. The CI matrix does not prove native host startup on any operating system.

Native plugin and marketplace validators must target the actual descriptor files separately: validating the root may select only the marketplace. A valid manifest is not proof that a client merges/discovers Hooks correctly. For live checks, inspect exactly one session reminder and verify prompt/edit events, scope, update/removal and duplicate-install behavior without bypassing permissions.

Hook budgets are local parser/reminder safeguards: 256 KiB stdin, 32 Ki characters analyzed, 4096 characters per candidate call, 16 Ki cumulative call inspection and 4096 UTF-8 context bytes. They do not enforce application token budgets. Shared session configuration omits timeout because clients use different units. Development Hooks use five seconds on Claude/CodeBuddy. Missing inputs/Skill and unsupported events silently produce no context.

## Preparing a publication

1. Run offline repository, standalone and adapter tests; review changed files and retain multilingual regression cases.
2. Run installed native validators. Record warnings and distinguish package checks from discovery/lifecycle and model tasks in the evidence matrix.
3. Keep every version-bearing descriptor synchronized. Use `CHANGELOG.md` to distinguish Unreleased work from a real published release.
4. Select the actual GitHub repository identity before adding remote URLs, badges or clone commands. Review license notices, ignored local files and any proposed release archive.
5. Publish only after separate authorization. This repository contains no release/push action, credentials, automatic updater or global installer. The OpenClaw package is intentionally private for npm.

Do not advertise arbitrary-model success. Authorized real-model checks require representative business schemas and validation of invalid/refusal/truncation paths; structure, accuracy and success rate are separate outcomes. Do not print credentials, private inputs or raw completions during verification.

## Attribution

Packaging conventions and the small Hermes/OpenClaw adapter patterns reference supercoding. Preserve the MIT notice in the root license and include it with standalone redistributions. Instructor inspired the validation/retry principles; this project does not vendor its source or runtime.
