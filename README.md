# schema-outputkit

English | [简体中文](README.zh-CN.md)

Schema-first LLM development standards for AI coding assistants. One portable Skill helps assistants implement consistent business output contracts across providers and models, using the application's existing SDKs and validators.

**Install in your coding client, not in your model service or business application's dependencies.** Generated application code must implement the runtime validation and recovery. Installing this plugin does not rewrite existing integrations or guarantee that every model can satisfy every schema.

## What it guides

- One canonical schema per business operation: stable fields, types, required/optional/null semantics and serialization across models.
- Request adaptation based on verified provider, model, endpoint and SDK capabilities.
- Runtime schema and business validation before persistence, tool execution or success responses.
- Request-local repair state; bounded total attempts, deadlines, usage accounting and parsing work.
- Explicit refusal, truncation and failure handling; safe diagnostics without raw prompts or completions.
- Appropriate text, streaming and tool contracts: ordinary chat is not forced into JSON.

For example, ask: “Implement invoice extraction using our existing SDK and validator. Keep the same business schema when switching providers.” The assistant should inspect the consumer, reuse or define its schema, select a supported output mode, validate the final result and verify relevant failure cases. Matching structure does not imply identical values or factual accuracy.

The complete runtime is [SKILL.md](skills/schema-outputkit/SKILL.md). Instructions, generated reminders, metadata, comments and maintenance documents are English. Chinese trigger tokens and multilingual test fixtures are intentional functional data. The assistant can still respond in your preferred language.

## Quick start

From a reviewed local checkout, start one session with either client:

```sh
codebuddy --plugin-dir "/absolute/path/to/schema-outputkit"
claude --plugin-dir "/absolute/path/to/schema-outputkit"
```

When needed, invoke `/schema-outputkit:schema-outputkit`. Automatic reminders are heuristic discovery aids; load the Skill explicitly if the client misses a relevant task.

For persistent Claude Code or CodeBuddy use, run these commands inside that client:

```text
/plugin marketplace add /absolute/path/to/schema-outputkit
/plugin install schema-outputkit@schema-outputkit --scope user
```

User scope makes the plugin available across projects for that client. Use project scope when your team intentionally shares the setting. Avoid simultaneously installing a standalone copy. No global settings are changed by this repository itself.

## Client packages

| Client | Packaging | Additional reminders |
| --- | --- | --- |
| Claude Code | Native plugin and local marketplace | Session start, relevant prompts and recognizable Write/Edit changes |
| CodeBuddy | Native plugin and local marketplace | Session start, relevant prompts and recognizable Write/Edit changes |
| Codex | Plugin and local marketplace descriptors | None; Skill discovery/invocation |
| Gemini CLI | Native extension | Session start |
| Hermes Agent | Skill registration adapter | First main-agent turn |
| OpenClaw | Native plugin and dependency-free ESM entry | None; Skill discovery/invocation |

Client versions and permissions affect activation. Multiple-client packaging does not coordinate agents. When delegating implementation, the parent must pass the contract and applicable standards through its host's context mechanism; reminder inheritance is not assumed.

See [installation and verification evidence](docs/installation.md) for all six clients, standalone installation, updates and removal. Python 3.9+ with a `python3` executable is required for command reminders; Node is needed for the OpenClaw host. Standalone Skill use requires neither this plugin's Python scripts nor an application dependency. Native Windows shell startup has not been verified.

## Local checks

```sh
python3 -B scripts/validate_repository.py
python3 -B scripts/validate_repository.py skills/schema-outputkit
python3 -B -m unittest discover -s tests -v
codebuddy plugin validate .codebuddy-plugin/plugin.json
claude plugin validate .claude-plugin/plugin.json
```

Package tests, native validation, actual client discovery and real-model tasks are separate evidence levels. See the [evidence matrix](docs/installation.md#verification-evidence). Passing Hook tests does not prove provider compatibility or generated-code compliance.

## Boundaries and publication

Hooks read bounded event input and emit fixed context plus the Skill path. They do not read business files, store events, call model services, block requests or replace tool outputs. Prompt/code recognition is heuristic and does not cover every language syntax. Read [maintenance guidance](docs/development.md) before changing adapters or publishing a release.

This checkout includes local marketplace descriptors; it does not claim an official listing, npm publication or published release. Add the actual repository URL after choosing the GitHub location. No credentials are needed for local checks.

## License and attribution

[MIT](LICENSE). Client-packaging and reminder patterns were adapted from supercoding; its copyright notice is retained. Instructor informed the schema-validation and bounded-recovery design; no Instructor runtime is bundled or required. Preserve the applicable license notices when redistributing the plugin or a standalone Skill.
