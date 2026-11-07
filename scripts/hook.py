#!/usr/bin/env python3
"""Emit bounded, non-blocking client context reminders for LLM development."""

import json
import re
import sys
from pathlib import Path

MAX_INPUT_BYTES = 256 * 1024
MAX_ANALYSIS_CHARS = 32 * 1024
MAX_CALL_SCAN_CHARS = 4096
MAX_TOTAL_CALL_SCAN_CHARS = 16 * 1024
MAX_CONTEXT_BYTES = 4096
CORE_REMINDER = (
    "Use one canonical business schema across providers and models. Adapt wire schemas "
    "by verified capabilities; validate final data against the unchanged canonical schema "
    "and use stable business serialization. Unknown models need verified adapters, not "
    "brand guesses; unsupported contracts must fail explicitly. "
    "Preserve caller-owned messages/configuration; keep repair history, counters, "
    "validation context and stream buffers request-local. Check total attempts including "
    "SDK retries, per-call timeouts and the overall deadline. When token/cost budgets "
    "are required, accumulate usage across attempts; missing usage is unknown, and "
    "post-response accounting is not a hard spending cap. Bound cumulative output size, "
    "nesting and stream buffers; reject ambiguous extraction. Allowlist diagnostics; "
    "exceptions and raw responses may contain private inputs. Verify isolation after "
    "success/failure and concurrency, budget exhaustion and missing usage."
)
SKILL = Path(__file__).resolve().parents[1] / "skills/schema-outputkit/SKILL.md"
CODE_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts",
    ".cts", ".vue", ".svelte", ".go", ".java", ".kt", ".kts", ".cs",
    ".rs", ".rb", ".php", ".swift", ".scala", ".ex", ".exs", ".dart",
    ".ipynb",
}
LLM_TOPIC = re.compile(
    r"大模型|语言模型|千问|通义千问|模型(?:调用|输出|返回|响应|结果|生成)|结构化输出|"
    r"(?:跨|多|所有|不同|任意)模型|"
    r"(?<![a-z0-9_])(?:llm|large language model|openai|anthropic|gemini|ollama|litellm|"
    r"instructor|pydanticai|langchain|deepseek|qwen|gpt)(?![a-z0-9_])|"
    r"\b(?:structured outputs?|tool calling|function calling|response_model)\b",
    re.IGNORECASE,
)
DEVELOPMENT = re.compile(
    r"编写|开发|实现|接入|新增|修改|修复|重构|优化|调整|增加|加上|集成|迁移|封装|"
    r"写(?:一个|个|一下|段|代码|接口|函数|脚本)|"
    r"\b(?:implement|integrate|add|write|build|fix|refactor|modify|update|"
    r"migrate|develop|validate|debug)\b",
    re.IGNORECASE,
)
PROSE_TASK = re.compile(
    r"翻译|润色|改写|文案|命名|起名|取名|\breadme\b|"
    r"(?:写|修改|编写|更新|生成).{0,12}(?:文档|说明书|文章)|"
    r"\b(?:translate|translation|proofread|rephrase|rename|documentation)\b",
    re.IGNORECASE,
)
EXECUTABLE_REQUEST = re.compile(
    r"(?:编写|实现|开发|生成|修改).{0,16}(?:可运行|可执行|代码实现)|"
    r"\b(?:write|implement|build|update).{0,24}(?:runnable|executable)\b",
    re.IGNORECASE,
)
NO_CODE = re.compile(
    r"(?:不要|不用|无需|别|禁止|暂不)(?:直接|实际)?(?:修改|编写|改动|写|实现|开发)(?:任何)?(?:代码|文件)|"
    r"\b(?:do not|don't|without)\s+(?:modify|write|change|edit|changing|modifying|writing)\s+(?:any\s+)?(?:code|files?)\b",
    re.IGNORECASE,
)
EXPLANATION = re.compile(
    r"^\s*(?:请|帮我|先|只|仅|只需|只要)*(?:解释|说明|讲解|介绍|分析)|"
    r"^\s*(?:(?:please|only|just)\s+)*(?:explain|describe|discuss|analyze)\b",
    re.IGNORECASE,
)
PROMPT_CLAUSES = re.compile(r"[，,。；;！!？?\n]+|然后|并且|并(?=更新|修改|实现|接入)|\b(?:and|then)\b", re.IGNORECASE)
CODE_NON_EXECUTABLE = re.compile(
    r'(?P<string>"""[\s\S]*?(?:"""|\Z)|'
    r"'''[\s\S]*?(?:'''|\Z)|"
    r'"(?:\\[\s\S]|[^"\\])*"|'
    r"'(?:\\[\s\S]|[^'\\])*'|"
    r"`(?:\\[\s\S]|[^`\\])*`)"
    r"|(?P<comment>\#[^\n]*|//[^\n]*|/\*[\s\S]*?(?:\*/|\Z))"
)
SDK_CALL = re.compile(
    r"\b(?P<api>responses|messages)\.(?:create|parse|stream)\s*\("
)
CALL_SIGNAL = re.compile(
    r"\b(?:chat\.completions\.(?:create|parse)|responses\.(?:create|parse|stream)|"
    r"messages\.(?:create|stream)|models\.(?:generate_content|generateContent|"
    r"generate_content_stream)|(?:a?completion|generateText|streamText|"
    r"generateObject|streamObject|ChatCompletion|CreateChatCompletion|"
    r"Converse|converse|GenerateContent))\s*\(",
)
STRONG_CALL = re.compile(
    r"\bchat\.completions\.(?:create|parse)\s*\(|"
    r"\binstructor\.from_provider\s*\(|"
    r"\b(?:generateText|streamText|generateObject|streamObject|with_structured_output)\s*\(|"
    r"\bmodels\.(?:generate_content|generateContent|generate_content_stream)\s*\(",
)
SCHEMA_SIGNAL = re.compile(
    r"\b(?:response_model|response_format|output_schema|response_schema|"
    r"json_schema|tool_choice)\s*[:=]|\bwith_structured_output\s*\(",
)
POLICY_SIGNAL = re.compile(
    r"\b(?:max_retries|max_attempts|token_budget|timeout|deadline|validation_context|"
    r"max_output_bytes|max_json_depth|stream_buffer)\s*[:=]"
)


def relevant_prompt(prompt):
    if (
        not isinstance(prompt, str)
        or len(prompt) > MAX_ANALYSIS_CHARS
        or NO_CODE.search(prompt)
    ):
        return False
    for clause in PROMPT_CLAUSES.split(prompt):
        if EXPLANATION.search(clause):
            continue
        if PROSE_TASK.search(clause) and not EXECUTABLE_REQUEST.search(clause):
            # Translation can be the product being implemented, not a prose request.
            if not re.search(r"(?:开发|实现|接入).*(?:翻译|润色).*(?:功能|接口|服务)", clause):
                continue
        if LLM_TOPIC.search(clause) and DEVELOPMENT.search(clause):
            return True
    return False


def executable_text(text, suffix):
    def mask(match):
        # Preserve offsets and line boundaries, without scanning strings as code.
        if match.group("comment"):
            comment = match.group()
            if comment.startswith("#") and suffix not in {".py", ".pyi", ".rb", ".php"}:
                return comment
            if comment.startswith("//") and suffix in {".py", ".pyi", ".rb"}:
                return comment
        return re.sub(r"[^\n]", " ", match.group())

    return CODE_NON_EXECUTABLE.sub(mask, text)


def sdk_call_with_arguments(text):
    remaining = MAX_TOTAL_CALL_SCAN_CHARS
    for call in SDK_CALL.finditer(text):
        depth = 1
        # Each inspection charges the current invocation, including malformed calls.
        for end in range(call.end(), min(len(text), call.end() + MAX_CALL_SCAN_CHARS)):
            if remaining == 0:
                return False
            remaining -= 1
            if text[end] == "(":
                depth += 1
            elif text[end] == ")":
                depth -= 1
                if depth == 0:
                    break
        else:
            continue
        arguments = text[call.end():end]
        fields = set(re.findall(r"(?:^|[{,])\s*(model|input|messages)\s*(?=[:=,}])", arguments))
        expected = "input" if call.group("api") == "responses" else "messages"
        if {"model", expected}.issubset(fields):
            return True
    return False


def relevant_edit(payload):
    tool = payload.get("tool_name")
    if tool not in {"Write", "Edit"}:
        return False
    arguments = payload.get("tool_input")
    if not isinstance(arguments, dict):
        return False
    file_path = arguments.get("file_path")
    if not isinstance(file_path, str) or Path(file_path).suffix.lower() not in CODE_SUFFIXES:
        return False
    text = arguments.get("content" if tool == "Write" else "new_string")
    if not isinstance(text, str) or len(text) > MAX_ANALYSIS_CHARS or not text.strip():
        return False
    text = executable_text(text, Path(file_path).suffix.lower())
    if STRONG_CALL.search(text) or sdk_call_with_arguments(text):
        return True
    return bool(
        LLM_TOPIC.search(text)
        and (CALL_SIGNAL.search(text) or SCHEMA_SIGNAL.search(text) or POLICY_SIGNAL.search(text))
    )


def build_output(payload):
    event = payload.get("hook_event_name")
    if event == "SessionStart":
        message = (
            "For code that calls LLMs or consumes their output, apply the schema-outputkit "
            "Skill. Reuse complete unchanged rules already in context; otherwise "
            "invoke the available Skill or read its entry below. Skip ordinary REST/JSON, "
            "pure documentation/translation and conversation. Hooks are reminders, not "
            "runtime validation or provider compatibility checks."
        )
    elif event == "UserPromptSubmit" and relevant_prompt(payload.get("prompt")):
        message = (
            "This request may involve LLM output development. Confirm relevance from the "
            "actual task and load the schema-outputkit Skill if not already loaded. "
            "Reuse existing schemas and SDKs; choose text, structured data or tool-argument "
            "contracts by consumer. Validate final data at runtime, bound retries/timeouts, "
            "and verify actual provider capabilities. This reminder grants no new permissions."
        )
    elif event == "PostToolUse" and relevant_edit(payload):
        message = (
            "The code edit contains an LLM integration signal; this is a heuristic reminder, "
            "not a source audit. Apply the schema-outputkit Skill if relevant and not "
            "already loaded. Check the affected consumer's contract, final runtime validation, "
            "effective retry/deadline limits and supported provider mode. Keep free-text "
            "and tool/stream semantics appropriate to the task."
        )
    else:
        return None
    if not SKILL.is_file():
        return None
    if event != "SessionStart":
        message += " " + CORE_REMINDER
    context = message + "\nSkill entry (literal path):\n" + str(SKILL)
    if len(context.encode("utf-8")) > MAX_CONTEXT_BYTES:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        }
    }


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            return
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return
        output = build_output(payload)
        if output is not None:
            print(json.dumps(output, ensure_ascii=False))
    except (ValueError, TypeError, OSError, RecursionError):
        # Broken or unsupported hook input must never interrupt the coding session.
        return


if __name__ == "__main__":
    main()
