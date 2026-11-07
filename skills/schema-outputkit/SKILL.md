---
name: schema-outputkit
description: Use when writing or modifying code that calls large language models, consumes their outputs, extracts structured data, validates tool arguments, or repairs invalid model results. Keep one canonical business Schema across providers and models, with capability-based adaptation and final validation. Covers Python Instructor/Pydantic and equivalent SDK/schema validation in TypeScript and other languages. Skip ordinary REST/JSON work, pure translation, documentation editing, model usage without coding, and general conversation.
---

# schema-outputkit

Make model output safe for its actual consumer through an explicit contract, supported request constraints, runtime validation and bounded failure handling. Apply these instructions across languages; respond in the user's language.

## Scope and activation

- Apply before implementing or modifying LLM integrations and their direct consumers, including executable examples and relevant tests. A task need not literally mention JSON or Instructor.
- Reuse complete, unchanged instructions already loaded in context. Otherwise invoke this Skill through the client's available name (possibly namespaced), or read this entry directly.
- A Hook reminder is a discovery aid. Hook keyword matches are heuristic, not proof that a task is relevant or its code is correct. If related code reveals an LLM integration that Hooks missed, apply the Skill then.
- Pure explanations, translations and documentation editing do not trigger implementation work. Reviews may use the standards as criteria but do not authorize edits.
- Inspect the current change and directly affected callers. Do not audit or rewrite unrelated integrations, create a universal gateway, or install dependencies just because this Skill is available.
- Honor explicit user requirements and project standards within client permissions. This Skill grants no permission to install packages, publish, modify global settings, or send production requests.

## 1. Establish the output contract

Read the affected request entry point, consumer, existing types/schemas, provider configuration and dependency versions before changing code.

Classify the output by its consumer:

| Output use | Required contract |
| --- | --- |
| User-facing chat or prose | Keep the text/stream contract; handle completion, failure and cancellation. Do not impose arbitrary JSON wrapping. |
| Data used by code, storage or downstream APIs | Define or reuse a typed schema and validate the actual model result at runtime before use. |
| Tool/function arguments | Define and validate the arguments per tool. Keep model decisions separate from authorization and execution. |
| Mixed text and structured data | Keep channels or fields explicit; validate structured parts without breaking the user-facing text flow. |

Derive fields from requirements and existing consumers. Specify required versus optional/null, enums, numeric bounds, list bounds and unknown-field policy where relevant. Do not invent missing business facts or fill required values with guesses just to pass validation. Ask for information only when a missing contract materially changes behavior.

Prefer the existing schema as the source of truth for types, request constraints and response validation. JSON parsing, a TypeScript cast, or checking that a response is an object is not schema validation. Include business constraints that can actually be checked; distinguish syntax/type validity from factual correctness and grounding.

## 2. Reuse the project's language and runtime

| Project | Preferred approach |
| --- | --- |
| Python with Instructor | Reuse the client factory and Pydantic response models; pass the response model on each structured request and configure finite retries. Use `from_provider` for a new Instructor integration where it fits existing conventions. |
| Python without Instructor | Reuse existing SDK parsing/Pydantic validation first. Introduce Instructor only if its provider adapters and retry behavior add needed value under project dependency rules. |
| TypeScript / JavaScript | Reuse the SDK's structured-output/tool API and existing Zod, Ajv or equivalent runtime validator. Use a compatible schema conversion already supported by installed versions. Types alone cannot validate remote output. |
| Go, Java, C#, Rust and other languages | Reuse the project's typed DTO/schema validation and provider SDK. Preserve required-field and null semantics; successful deserialization alone may not enforce them. |

Keep existing client configuration, authentication, transport timeouts, async behavior and error contracts. Avoid duplicating provider logic across callers; extend an existing shared entry point when needed. Do not force a Python dependency into another language or build a new shared layer for a single call.

Preserve request isolation when adding constraints or repairing output:

- Do not mutate caller-owned message history, tools, schema definitions or generation configuration. Copy the containers and nested values that the adapter or retry handler actually changes; do not indiscriminately deep-copy opaque SDK objects or resources.
- Keep repair messages, retry counters, validation context and streaming buffers local to the current operation. Concurrent calls sharing a client or response model must not overwrite one another's state.
- Keep intentional conversation updates separate from internal retry history. Success, exhausted retries, cancellation and exceptions must leave reusable caller inputs unchanged unless the caller's explicit contract says otherwise.

## 3. Use one canonical contract across models

For each structured business operation, keep one canonical schema independent of model brands. Qwen, DeepSeek, GPT, local models and future providers use the same business contract when selected for that operation. This is extensible adaptation, not a guarantee that every model can satisfy every schema. Different business operations may legitimately have different schemas.

- Prefer a JSON Schema representation with an explicit dialect supported by the project's validator for interchange. Reuse or derive it from the existing Pydantic, Zod or other authoritative schema rather than maintaining inconsistent copies. Retain business validators that JSON Schema cannot express.
- Keep the canonical schema and its version stable when changing models. Field names, types, required/optional/null semantics, enum values, unknown-field policy and top-level shape must remain the same. A wire-schema adapter works on its own copy and must not weaken the canonical validation rules.
- Build the provider's wire schema from the canonical contract using installed SDK converters where available. A provider may require a root object, a limited JSON Schema subset or different request parameter names. Explicitly map temporary transport wrappers back to the canonical value before validating it; do not expose those wrappers as business data.
- When strict provider constraints require all fields to be present, do not silently turn an optional field into a required business field or replace omission with null. Use an explicit semantics-preserving mapping, another supported mode or a clear unsupported-contract error.
- If a provider cannot enforce a constraint during generation, retain it in final validation and state the weaker generation guarantee. If the contract cannot be represented or reliably recovered, fail explicitly. Do not remove fields, invent defaults, coerce values or select a different schema merely to make a model pass.

Use this pipeline for structured results:

**Canonical contract → capability-based request adaptation → provider output extraction → canonical validation and business checks → stable business serialization.**

- Select capabilities by the configured provider, model, endpoint, deployment and SDK version, using explicit configuration and authorized verification. Do not use a closed three-brand allowlist or infer all capabilities from a model-name substring. New providers can reuse a verified protocol adapter; incompatible protocols require their own adapter.
- Prefer supported schema-constrained generation; use tool arguments, JSON mode or explicit schema prompting only under the actual capability and fallback policy. All paths must converge on the same final validator. JSON mode alone guarantees neither schema compliance nor truthful content.
- Extract only the designated final result or expected tool name/call identifier. Keep reasoning, refusal text, SDK response envelopes and unrelated tool calls outside business data; preserve refusal/error handling instead of trying to coerce it into a valid result.
- Return the validated canonical value using one serialization policy for aliases, omitted versus null fields, dates, numbers and unknown fields. Provider metadata, usage and request identifiers belong in the project's existing metadata/error channel. Preserve an existing public response envelope; do not impose a new universal wrapper on every application.
- The accepted structure and serialization contract can be the same while values, accuracy and success rates vary. JSON object key order is not structural compatibility; require deterministic serialization only when a consumer or signature protocol needs it.
- On refusal, unsupported capability or exhausted repair attempts, use the established typed/sanitized error contract, never a success-shaped object containing invalid or fabricated data. Preserve budget and request-isolation rules while switching providers or modes.

For a new or changed multi-provider integration, replay equivalent local SDK fixtures for configured adapters through the same canonical validator and serializer. Cover valid results, wrong types, missing/extra fields, null/omission, wire-wrapper removal, unknown tool calls and refusals as relevant. Invalid results must be rejected consistently, and changing provider must not change the contract. Separately run authorized checks on actual deployments before claiming compatibility; no fixture or Hook test proves that all models comply.

## 4. Select a supported request constraint

- Check the actual provider, model, endpoint, deployment and installed SDK capabilities. OpenAI-compatible transport does not guarantee support for every tool/JSON feature.
- Use supported native JSON Schema/structured output or tool calling when appropriate. Where those are unavailable, an explicit schema prompt plus parsing and runtime validation can be used, with the weaker generation guarantee stated accurately.
- Use the schema's supported subset for the target API; do not silently remove constraints that the runtime must still enforce. Keep existing tools and agent orchestration working rather than overwriting their definitions with an extraction-only schema.
- Configure a known mode when possible. Any fallback must be an explicit, bounded policy based on a confirmed unsupported-capability error. Do not downgrade on authentication, authorization, network, rate-limit or business-validation failures.
- A provider-level capability table or heuristic mode selector is a starting point, not evidence that a particular deployment works. Verify representative schemas on the actual configured deployment when authorized.

## 5. Validate before exposing success

Parse the response through the runtime schema and relevant business validators at the external boundary. Consumers, persistence and side effects must receive only validated final values.

Handle provider refusal, truncated output, empty responses and schema errors explicitly using the project's error contract. Never pass an unvalidated original response as the successful fallback. Do not fabricate default business values, remove failing fields, broadly coerce types, or strip arbitrary text until a result happens to pass. Use intentional conversions only when the contract allows them.

For extraction, distinguish missing evidence from a false/zero/empty value. For generated citations or factual claims, use source-based checks when required; a matching schema cannot establish truth.

Bound parsing work before accepting model-controlled output:

- Choose response-size, nesting-depth and stream-buffer limits appropriate to the business contract. State whether a size limit counts bytes or characters and enforce cumulative limits across chunks, not only per chunk. Do not copy another library's numeric thresholds without checking the workload.
- Prefer the SDK's designated structured-output or tool-argument channel. If text extraction is necessary, define its framing and how many results are allowed; reject ambiguous multiple candidates rather than blindly taking the first or last JSON span. Sequence protocols may explicitly allow multiple independently validated items.
- Use bounded parsing/extraction and avoid repeated scans of all accumulated text. On oversized or excessively nested output, stop parsing and release stream resources; malformed or truncated results must not be exposed as successful data. Any recovery must follow the explicit bounded retry policy below. Do not buffer indefinitely while waiting for closing delimiters or silently truncate content into apparent success.

## 6. Keep retries and resources bounded

- Reuse project policies. If a new policy is necessary and no policy exists, start with at most three total application-level attempts including the initial attempt. Check the installed library's parameter semantics: a retry count can exclude the initial call, while an attempt count includes it. Translate the policy to actual outbound calls rather than assuming `max_retries=3` means three calls.
- Account for SDK retries, validation retries and mode fallbacks together. Document or configure the effective bound on outbound requests so nested retry loops do not multiply unexpectedly.
- Distinguish per-call transport timeouts from the overall operation deadline. The overall budget covers calls, backoff, repair processing and required validation; check remaining time before another attempt and propagate cancellation/deadline limits through supported APIs. A retry stop condition alone does not interrupt an already running call.
- When the operation has a token/cost requirement, accumulate compatible usage from all attempts and fallbacks, including failed generations. Distinguish per-response output-token limits from cumulative retry budgets; include additional billable token categories where the provider reports them.
- Usage-based accounting happens after a response and cannot guarantee that an in-flight call will stay below the remaining token/cost budget. Do not claim a hard spending cap from post-response checks; use supported pre-call limits as well where needed. Token counts alone are not a monetary cost without the applicable pricing and usage categories.
- If a required budget cannot be enforced because usage metadata is missing or the selected streaming/mode combination is unsupported, use the project's explicit failure or conservative fallback policy. Do not count missing usage as zero, silently disable the budget, or assume every SDK supports streaming usage accounting.
- For repairable output-validation failures, return concise field-level error information with the same contract to the model. Do not include sensitive field values or dump full validation inputs into repair prompts or logs.
- Keep a supported mode for data-validation repairs. Retry transient transport failures only under the existing transport policy; stop on non-retryable failures and on exhausted attempts/deadline.
- Respect cancellation and concurrency limits. After failure, expose an explicit typed error or the established error result, preserving enough safe diagnostic information for the caller.
- Retrying model generation must not replay payments, database writes, messages or tool side effects. Validate before executing; preserve existing idempotency boundaries.

## 7. Preserve streaming and tool semantics

- Treat partial structured objects as provisional. Required fields may be absent during generation; apply complete validation at the end and do not commit provisional values as final data.
- Retrying after emitting stream data can duplicate content. Follow the project's restart/reconciliation contract, or surface a final failure instead of silently appending a second answer.
- Validate tool names and each argument schema, then perform normal server-side authorization and business checks. Schema-valid model arguments are not authorization.
- Keep async/sync APIs consistent with their callers and close/cancel streams according to the SDK lifetime rules.

## 8. Keep runtime diagnostics useful and safe

- Reuse the application's existing logging/metrics/tracing facilities. Where diagnostics are needed, allowlist error category/code, attempt and effective attempt limit, elapsed time, final outcome, available cumulative usage and a non-sensitive schema version or identifier. Distinguish provider/transport failures, parsing or business-validation failures, refusal/truncation, cancellation and budget exhaustion rather than reporting every failure as a retry error.
- Do not log or return a complete exception, `str(exception)`, serialized SDK response, failed-attempt history or request kwargs without checking its contents. Library exceptions and tracebacks can embed prompts, field inputs and raw completions. Extract safe fields; redact or omit sensitive values, and mark unavailable usage as unknown rather than zero.
- Preserve the useful error cause internally without automatically forwarding the original exception to telemetry or external API clients. Use the project's sanitized error contract at outward boundaries; do not add an observability platform or raw-payload storage solely for this Skill.
- These are application runtime diagnostics. The plugin's client Hooks only inject development reminders and do not collect or measure application model calls.

## 9. Verify and report evidence

Choose checks proportionate to the changed boundary. For substantive changes, cover a valid result plus the relevant invalid-field, missing-value, refusal/truncation, exhausted-budget or streaming-finalization path. When those mechanisms change, also check caller input preservation after recovery/failure, concurrent request isolation, retry-to-attempt mapping, missing usage, cumulative size/depth limits, ambiguous extraction and diagnostic redaction. Use project tests and safe local substitutes before real network calls. Do not add tests for unchanged integrations solely to satisfy a generic checklist.

Real provider checks require an authorized environment and credentials; never print or store credentials, prompts, private inputs or complete raw responses. Do not call external models just to load this Skill. Report local tests separately from actual provider compatibility and client behavior evaluations.

On delivery, state what contract and integration changed, which checks ran, and any unverified deployment capabilities. Do not describe a Hook reminder or a valid plugin manifest as proof of runtime compatibility.

## What the plugin actually does

One portable Skill supplies these standards across clients. Claude Code and CodeBuddy packaging adds session-start, relevant development-prompt and recognizable code-edit reminders; Gemini packaging supplies a session-start reminder; Hermes registers the Skill and a first-turn reminder. Codex and OpenClaw packaging expose the Skill without additional reminder hooks. Standalone Skill copies have no plugin Hooks. Available events, discovery and namespacing depend on the client version; verify actual loading instead of assuming equivalent behavior.

These adapters do not coordinate agents, intercept the assistant's underlying model requests, validate all generated source code, or wrap application calls at runtime. When delegating relevant implementation work, pass the contract and applicable standards to the worker using the host's normal context mechanism; do not assume parent reminders are inherited or introduce delegation solely for this Skill. The resulting application must use its own SDK/library and validation code for these guarantees to continue after the coding session.
