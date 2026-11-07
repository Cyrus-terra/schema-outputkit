# Installation and verification

Use a reviewed checkout named `schema-outputkit`. Commands below describe installation; repository checks never run them or change client settings. Choose one installation method per client. There is no model-server installation and no application-level import of this plugin.

## Claude Code and CodeBuddy

Load a single session with `claude --plugin-dir /absolute/path/to/schema-outputkit` or `codebuddy --plugin-dir /absolute/path/to/schema-outputkit`.

For persistent installation, run inside the selected client:

```text
/plugin marketplace add /absolute/path/to/schema-outputkit
/plugin install schema-outputkit@schema-outputkit --scope user
```

Use `--scope project` only when intentionally sharing project configuration. Invoke `/schema-outputkit:schema-outputkit`, inspect the host's plugin/Hook listings and restart after updates. The default `hooks/hooks.json` supplies SessionStart; the manifest adds `hooks/development.json` for UserPromptSubmit and PostToolUse. The files have disjoint events to avoid duplicate session reminders. Claude/CodeBuddy use seconds for timeout; the shared session Hook omits timeout because Gemini uses milliseconds. The development Hooks have a five-second timeout.

After changing the checkout, refresh the local marketplace and update the installed copy separately:

```text
/plugin marketplace update schema-outputkit
/plugin update schema-outputkit@schema-outputkit
```

To remove it, use `/plugin uninstall schema-outputkit@schema-outputkit` in the installation scope, then remove the local marketplace through the host if no longer needed. Do not delete shared settings files.

## Codex

The package contains `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json`. On a version with native plugin support, use:

```text
codex plugin marketplace add /absolute/path/to/schema-outputkit
codex
/plugins
```

Install from the added marketplace in `/plugins`. Refresh via the host's marketplace controls and check the installed version separately. Manage removal there as well. The local Codex launcher currently lacks its native executable, so this path is package-checked only. If the installed version differs, use the standalone Skill option and `/skills` or `$schema-outputkit`. No native Hook integration is declared.

## Gemini CLI

```sh
gemini extensions install /absolute/path/to/schema-outputkit
gemini extensions update schema-outputkit
```

Restart after installation or updates; inspect `/extensions list` and available Skills. Gemini reads `gemini-extension.json`, `skills/` and the session-only `hooks/hooks.json`. It does not load the Claude/CodeBuddy manifest's development events. The host substitutes `${extensionPath}` in the shared command; the local shell check simulates that substitution and is not native verification. Gemini CLI is not installed in the verification environment.

Remove with `gemini extensions uninstall schema-outputkit`. Source copying and updates belong to Gemini. Do not enable automatic updates unless you intend to trust future source changes.

## Hermes Agent

The native adapter is `.hermes-plugin/plugin.yaml` plus its registration module. The root `plugin.yaml` and `__init__.py` expose it to current Hermes directory discovery; retaining only the hidden directory is insufficient for that host. With a published Git repository, use `hermes plugins install` with the actual repository source and `--enable`; no repository URL is assumed here. Inspect `hermes plugins install --help` for supported source types in your version. For local development, use the active profile's plugin directory only when its dedicated target is absent, then explicitly enable the plugin. The standalone option below is simpler when testing only the Skill.

The adapter registers `schema-outputkit:schema-outputkit` under the host's normal namespace and returns first-turn context for the main agent. It does not inject context into subagents or read their messages. Use the discovered Skill name with `skill_view`; restart after changes. Use `hermes plugins list`, `hermes plugins update schema-outputkit` and `hermes plugins remove schema-outputkit` for lifecycle management. The callback is tested using a fake context; a live Hermes session is not verified.

## OpenClaw

```sh
openclaw plugins install --link /absolute/path/to/schema-outputkit
openclaw plugins list
openclaw plugins inspect schema-outputkit
```

Review host trust prompts. A linked checkout follows local file changes; it does not fetch updates. The package exposes `skills/` through `openclaw.plugin.json` and a minimal ESM entry, without dependencies or application runtime behavior. Check the Gateway's reload requirements and start a new conversation after changes. Remove the registration with `openclaw plugins uninstall schema-outputkit`; keep your source checkout if still needed. Node import checks do not prove Gateway discovery. The package is marked private to prevent accidental npm publication.

## Standalone Skill

Copy the complete `skills/schema-outputkit/` directory into one supported Skill location. Copy the root `LICENSE` into that dedicated Skill directory as `LICENSE` as well. The Skill entry has no dependency on repository scripts or client adapters.

| Client | Typical user Skill parent | Project/profile alternative |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/` | `<project>/.claude/skills/` |
| CodeBuddy | `~/.codebuddy/skills/` | Use a supported project Skill directory |
| Codex | `~/.agents/skills/` | `<project>/.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` | Trusted workspace Skill directory |
| Hermes | `~/.hermes/skills/` | Active profile's Skill directory |
| OpenClaw | `~/.openclaw/skills/` | Active agent workspace's `skills/` directory |

Check your host's configured roots and precedence before copying. Preserve an existing directory instead of overwriting it. Standalone installations have no plugin reminders; use the host's discovered invocation name or explicitly request this Skill. Refresh the Skill list or start a new session. Updates are reviewed file replacements, not automatic downloads: compare with the new checkout and preserve local edits. Remove only the dedicated copy you installed, leaving sibling Skills and shared instructions intact.

## Verification evidence

P = deterministic package/adapter checks. N = native validator. L = real client discovery and lifecycle. M = successful model task using the Skill. These levels are independent; a passing P/N check does not establish L/M.

| Client | P | N | L | M |
| --- | --- | --- | --- | --- |
| Claude Code | Covered by repository tests | Manifest and marketplace pass | Not run | Not run |
| CodeBuddy | Covered by repository tests | Manifest and marketplace pass | Not run | Not run |
| Codex | Covered by repository tests | Blocked: missing native executable | Not run | Not run |
| Gemini CLI | Covered; extension-path substitution simulated | Not available locally | Not run | Not run |
| Hermes | Registration and first-turn fake-context checks | No native package validator run | Not run | Not run |
| OpenClaw | Manifest and ESM import checks | No native package validator run | Not run | Not run |

These records concern this package, not supercoding's prior results. Re-run the commands in the README before relying on package checks. Native Windows Hook startup, client reminder inheritance and actual deployment/model compatibility remain unverified. No external model calls are part of the offline suite.

## Troubleshooting

- Skill missing: inspect enabled plugins, installation scope and the host's Skill list; avoid duplicate standalone/native copies.
- Reminder missing: check the Hook listing, executable `python3`, quoted root expansion and supported event names. Prompt and code matching is heuristic; manually load the Skill when appropriate.
- Existing application still accepts invalid output: implement the runtime contract, validation and recovery in that application's code. Client installation alone cannot alter it.
- Different model fails a valid schema: verify the actual endpoint and SDK capability, preserve canonical final validation, and fail explicitly if no supported adapter can satisfy the contract.
