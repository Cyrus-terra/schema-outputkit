"""Exercise the actual Hook process without credentials or network requests."""

import copy
import json
import os
import runpy
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/hook.py"


class HookTests(unittest.TestCase):
    def invoke(self, payload, script=SCRIPT, cwd=ROOT):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        result = subprocess.run(
            [sys.executable, str(script)], input=raw, capture_output=True,
            cwd=cwd, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        if not result.stdout.strip():
            return None
        output = json.loads(result.stdout)
        self.assertEqual(set(output), {"hookSpecificOutput"})
        self.assertEqual(
            set(output["hookSpecificOutput"]), {"hookEventName", "additionalContext"}
        )
        return output["hookSpecificOutput"]

    def prompt(self, text):
        return self.invoke({"hook_event_name": "UserPromptSubmit", "prompt": text})

    def edit(self, text, suffix=".py", tool="Edit", **fields):
        arguments = {"file_path": "/unused/project/service" + suffix, **fields}
        arguments["content" if tool == "Write" else "new_string"] = text
        return self.invoke({
            "hook_event_name": "PostToolUse", "tool_name": tool,
            "tool_input": arguments,
        })

    def test_session_start_on_all_sources(self):
        for source in ("startup", "resume", "clear", "compact"):
            with self.subTest(source=source):
                output = self.invoke({"hook_event_name": "SessionStart", "source": source})
                self.assertEqual(output["hookEventName"], "SessionStart")
                self.assertIn(str(ROOT / "skills/schema-outputkit/SKILL.md"), output["additionalContext"])

    def test_development_prompts(self):
        for text in (
            "接入大模型，实现订单提取接口", "修复模型输出校验失败后的重试",
            "帮我写一个 OpenAI 聊天接口", "给现有 LLM 接口增加流式响应",
            "Implement structured output validation with Zod",
            "Refactor Anthropic messages API to validate tool arguments",
            "开发一个使用本地 Ollama 的摘要服务",
            "帮我接入OpenAI接口", "实现LLM输出校验", "修改DeepSeek调用逻辑",
            "编写文档里的可运行 OpenAI 示例代码",
            "Write a runnable LLM example for the documentation",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.prompt(text)["hookEventName"], "UserPromptSubmit")

    def test_mixed_development_and_documentation_prompts(self):
        for text in (
            "接入 OpenAI，并更新 README",
            "更新 README，并实现 OpenAI 输出校验",
            "把模型返回的结果加上校验",
            "解释现有流程，然后修复 LLM 输出解析",
            "Integrate OpenAI and update the README",
            "Update documentation, then implement LLM output validation",
            "开发大模型翻译功能",
        ):
            with self.subTest(text=text):
                self.assertIsNotNone(self.prompt(text))

    def test_explicit_explanation_and_no_code_requests(self):
        for text in (
            "不要修改代码，解释如何实现 OpenAI 输出验证",
            "解释如何实现 OpenAI 输出验证",
            "只说明怎么接入大模型",
            "请解释如何修改 LLM 输出校验",
            "Do not modify code; explain how to implement OpenAI validation",
            "Explain how to implement LLM structured output",
            "Only describe how to integrate OpenAI",
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.prompt(text))

    def test_unrelated_and_prose_prompts(self):
        for text in (
            "你好", "修复订单 JSON 接口", "为表单增加 Zod 验证",
            "给数据库模型新增字段", "What is OpenAI?",
            "解释 Instructor 的重试机制", "翻译 OpenAI 的代码示例",
            "润色 LLM 项目的 README", "编写大模型输出规范文档",
            "Translate: implement OpenAI structured output validation",
            "Update the LLM documentation", "为大模型输出插件起名",
            "修改 skill 的 description", "聊天内容提到了 OpenAI",
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.prompt(text))

    def test_recognizable_code_edits(self):
        for text, suffix in (
            ('result = client.chat.completions.create(response_model=Result)', ".py"),
            ('client = instructor.from_provider("provider/model")', ".py"),
            ('const result = await generateObject({ model, schema });', ".ts"),
            ('const result = await streamText({ model, messages });', ".tsx"),
            ('import anthropic\nresult = client.messages.create(model=model)', ".py"),
            ('import openai\nresult = client.responses.parse(model=model)', ".py"),
            ('from google import genai\n# Gemini\nclient.models.generate_content()', ".py"),
            ('llm.output_schema = Result.model_json_schema()\nresponse_model = Result', ".py"),
            ('llm.with_structured_output(Result)', ".py"),
        ):
            for tool in ("Write", "Edit"):
                with self.subTest(text=text, suffix=suffix, tool=tool):
                    output = self.edit(text, suffix, tool)
                    self.assertEqual(output["hookEventName"], "PostToolUse")

    def test_sdk_calls_without_import_in_changed_fragment(self):
        for text, suffix in (
            ("result = client.responses.create(model=model, input=prompt)", ".py"),
            ("result = client.messages.create(model=model, messages=messages)", ".py"),
            ("result = client.messages.stream(\n model=model,\n messages=messages\n)", ".py"),
            ("await client.responses.parse({model: model, input: prompt})", ".ts"),
            ("await client.messages.create({ model, messages })", ".ts"),
            ("client.models.generate_content(model=model, contents=prompt)", ".py"),
            ("model.with_structured_output(Result)", ".py"),
        ):
            with self.subTest(text=text):
                self.assertIsNotNone(self.edit(text, suffix))

    def test_comments_and_string_examples_do_not_trigger(self):
        for text, suffix in (
            ("# example: client.chat.completions.create()", ".py"),
            ('example = "client.chat.completions.create()"', ".py"),
            ('"""client.chat.completions.create()\nexample only"""', ".py"),
            ("// client.chat.completions.create()", ".ts"),
            ("/* client.chat.completions.create()\nexample */", ".js"),
            ("const example = `client.chat.completions.create()`;", ".ts"),
            ('const example = "client.responses.create({model, input})";', ".ts"),
            ("import openai\n# client.responses.create()", ".py"),
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.edit(text, suffix))

    def test_call_parameters_must_belong_to_the_same_call(self):
        for text in (
            "client.responses.create(response)\nother(model=model, input=prompt)",
            "client.messages.create(message)\nother(model=model, messages=messages)",
            "# model=model, input=prompt\nclient.responses.create(response)",
            "client.responses.create(model=model)",
            "client.messages.create(messages=messages)",
            "client.responses.create(model=model, input=prompt",
            "client.messages.create(model=model)\nclient.responses.create(input=prompt)",
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.edit(text))

    def test_real_call_survives_comments_strings_and_urls(self):
        for text, suffix in (
            ('url = "https://example.invalid"\nclient.chat.completions.create()', ".py"),
            ('const url = "https://example.invalid";\nawait generateObject({model, schema});', ".ts"),
            ('# example only\nclient.responses.create(model=model, input="text")', ".py"),
            ('/* comment */\nawait client.messages.create({model: "name", messages: []})', ".ts"),
        ):
            with self.subTest(text=text):
                self.assertIsNotNone(self.edit(text, suffix))

    def test_ordinary_code_and_old_deleted_calls_do_not_trigger(self):
        for text in (
            "payload = json.loads(response.text)", "schema = z.object({id: z.string()})",
            "client.messages.create(message)", "client.responses.create(response)",
            "response_format = 'json'", "instructor = Teacher()",
            "", "   ", "return cached_result",
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.edit(
                    text, old_string="client.chat.completions.create()"
                ))

    def test_document_and_data_edits_are_excluded(self):
        for suffix in (".md", ".json", ".yaml", ".txt", ".lock", ""):
            with self.subTest(suffix=suffix):
                self.assertIsNone(self.edit("client.chat.completions.create()", suffix, "Write"))

    def test_invalid_input_is_silent(self):
        invalid = (
            b"", b"{", b"\xff", b"[]", b"null", b'"text"',
            b"{" + b'"a":' + b"[" * 2000 + b"]" * 2000 + b"}",
            {"hook_event_name": "UserPromptSubmit", "prompt": None},
            {"hook_event_name": "UserPromptSubmit", "prompt": {"text": "LLM"}},
            {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": []},
            {"hook_event_name": "PostToolUse", "tool_name": [], "tool_input": {}},
            {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {
                "file_path": None, "new_string": "client.chat.completions.create()",
            }},
            {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {
                "file_path": "service.py", "new_string": {},
            }},
        )
        for payload in invalid:
            with self.subTest(payload_type=type(payload).__name__):
                self.assertIsNone(self.invoke(payload))

    def test_oversized_input_is_silent(self):
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": "实现 LLM 输出" + "x" * (256 * 1024)}
        self.assertIsNone(self.invoke(payload))

    def test_unknown_events_and_tools_are_silent(self):
        for event in ("Stop", "PreToolUse", "SubagentStop", "Other", None, []):
            with self.subTest(event=event):
                self.assertIsNone(self.invoke({"hook_event_name": event, "prompt": "实现 LLM 输出"}))
        self.assertIsNone(self.edit("client.chat.completions.create()", tool="Bash"))

    def test_does_not_echo_sensitive_input(self):
        secret = "sensitive-test-value-72381"
        output = self.prompt("实现 LLM 输出验证 " + secret)
        self.assertNotIn(secret, json.dumps(output))
        output = self.edit('client.chat.completions.create(api_key="' + secret + '")')
        self.assertNotIn(secret, json.dumps(output))

    def test_related_events_include_core_standards_without_payloads(self):
        outputs = (
            self.prompt("修复 LLM 重试预算"),
            self.edit("client.chat.completions.create()"),
        )
        for output in outputs:
            context = output["additionalContext"]
            for requirement in (
                "caller-owned", "request-local", "total attempts", "SDK retries",
                "overall deadline", "missing usage is unknown", "not a hard spending cap",
                "cumulative output size", "ambiguous extraction", "Allowlist diagnostics",
            ):
                with self.subTest(requirement=requirement):
                    self.assertIn(requirement, context)
            self.assertLessEqual(len(context.encode("utf-8")), 4096)
        session = self.invoke({"hook_event_name": "SessionStart"})
        self.assertLess(len(session["additionalContext"]), len(outputs[0]["additionalContext"]))

    def test_cross_model_requests_and_canonical_contract_reminders(self):
        for prompt in (
            "实现千问模型的结构化响应", "接入DeepSeek并校验结果",
            "开发 GPT 的数据提取接口", "实现跨模型统一 Schema 适配与校验",
            "给所有模型增加统一输出校验", "接入未知厂商语言模型的输出接口",
            "Implement schema validation for a future LLM provider",
        ):
            with self.subTest(prompt=prompt):
                output = self.prompt(prompt)
                self.assertIsNotNone(output)
                context = output["additionalContext"]
                for requirement in (
                    "canonical business schema", "verified capabilities",
                    "unchanged canonical schema", "stable business serialization",
                    "unsupported contracts must fail explicitly",
                ):
                    self.assertIn(requirement, context)
        for text in ("千问有什么特点", "解释 GPT 的输出格式", "修改普通表单的统一 Schema 校验"):
            with self.subTest(prompt=text):
                self.assertIsNone(self.prompt(text))
        context = self.edit("client.chat.completions.create()")['additionalContext']
        self.assertIn("one canonical business schema across providers and models", context)

    def test_policy_edits_need_llm_context(self):
        for text in (
            "llm.token_budget = 1000", "openai.max_retries = 2",
            "llm.timeout = 10", "llm.validation_context = context",
        ):
            with self.subTest(text=text):
                self.assertIsNotNone(self.edit(text))
        for text in ("max_retries = 2", "http.timeout = 10", "token_budget = 1000"):
            with self.subTest(text=text):
                self.assertIsNone(self.edit(text))

    def test_input_byte_boundary_is_not_character_boundary(self):
        prefix = json.dumps({"hook_event_name": "SessionStart", "unused": "预算"}, ensure_ascii=False).encode()
        for offset in (-1, 0, 1):
            raw = prefix + b" " * (256 * 1024 + offset - len(prefix))
            with self.subTest(offset=offset):
                output = self.invoke(raw)
                self.assertEqual(output is not None, offset <= 0)

    def test_analysis_boundary_does_not_truncate_into_false_positive(self):
        prompt = "实现LLM输出校验"
        code = "client.chat.completions.create()"
        for offset in (-1, 0, 1):
            with self.subTest(offset=offset):
                text = prompt + " " * (32 * 1024 + offset - len(prompt))
                self.assertEqual(self.prompt(text) is not None, offset <= 0)
                text = code + " " * (32 * 1024 + offset - len(code))
                self.assertEqual(self.edit(text) is not None, offset <= 0)

    def test_call_scan_exact_boundary_and_cumulative_exhaustion(self):
        for offset in (-1, 0, 1):
            arguments = "model=model,input=prompt"
            arguments += " " * (4096 + offset - len(arguments) - 1)
            with self.subTest(offset=offset):
                self.assertEqual(
                    self.edit("client.responses.create(" + arguments + ")") is not None,
                    offset <= 0,
                )
        # Closed unrelated calls spend exactly 4096 scan characters each.
        unrelated = "client.responses.create(" + "x" * 4095 + ")\n"
        valid = "client.responses.create(model=model,input=prompt)"
        self.assertIsNotNone(self.edit(unrelated * 3 + valid))
        self.assertIsNone(self.edit(unrelated * 4 + valid))
        self.assertIsNotNone(self.edit(valid))
        malformed = "client.responses.create(" * 500
        self.assertIsNone(self.edit(malformed))

    def test_direct_calls_preserve_inputs_and_return_independent_results(self):
        hook = runpy.run_path(str(SCRIPT))
        build = hook["build_output"]
        payload = {
            "hook_event_name": "PostToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": "service.py", "new_string": "llm.token_budget = 100"},
            "messages": [{"content": ["private-test-input"]}],
        }
        original = copy.deepcopy(payload)
        first = build(payload)
        first["hookSpecificOutput"]["additionalContext"] = "changed-by-caller"
        second = build(payload)
        self.assertEqual(payload, original)
        self.assertNotIn("changed-by-caller", json.dumps(second))
        self.assertNotIn("private-test-input", json.dumps(second))
        scan = hook["sdk_call_with_arguments"]
        self.assertFalse(scan("client.responses.create(" * 500))
        self.assertTrue(scan("client.responses.create(model=model,input=prompt)"))

    def test_context_budget_is_checked_without_truncation(self):
        hook = runpy.run_path(str(SCRIPT))
        build = hook["build_output"]
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": "实现LLM输出校验"}
        size = len(build(payload)["hookSpecificOutput"]["additionalContext"].encode("utf-8"))
        for limit in (size, size - 1):
            with self.subTest(limit=limit), patch.dict(build.__globals__, MAX_CONTEXT_BYTES=limit):
                self.assertEqual(build(payload) is not None, limit == size)
        self.assertIsNotNone(build(payload))

    def test_concurrent_requests_do_not_share_state_or_sensitive_values(self):
        hook = runpy.run_path(str(SCRIPT))
        build = hook["build_output"]
        payloads = []
        for index in range(12):
            if index % 3 == 0:
                payload = {"hook_event_name": "UserPromptSubmit", "prompt": "实现LLM输出校验"}
            elif index % 3 == 1:
                payload = {"hook_event_name": "UserPromptSubmit", "prompt": "普通聊天"}
            else:
                payload = {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {
                    "file_path": "service.py", "new_string": "client.responses.create(" * 500,
                }}
            payload.update(session_id="private-session-" + str(index), cwd="/private-test-project")
            payloads.append(payload)
        original = copy.deepcopy(payloads)
        expected = [build(payload) for payload in payloads]
        with ThreadPoolExecutor(max_workers=4) as executor:
            self.assertEqual(list(executor.map(build, payloads)), expected)
        with ThreadPoolExecutor(max_workers=4) as executor:
            actual = list(executor.map(self.invoke, payloads))
        for payload, output in zip(payloads, actual):
            self.assertEqual(output is not None, "实现LLM" in payload.get("prompt", ""))
            self.assertNotIn(payload["session_id"], json.dumps(output))
            self.assertNotIn(payload["cwd"], json.dumps(output))
        self.assertEqual(payloads, original)

    @unittest.skipUnless(os.name == "posix", "Native command expansion is verified on POSIX only")
    def test_quoted_configured_command_and_no_side_effects(self):
        config = json.loads((ROOT / "hooks/hooks.json").read_text())
        config["hooks"].update(json.loads((ROOT / "hooks/development.json").read_text())["hooks"])
        with tempfile.TemporaryDirectory(prefix="llm plugin test ") as directory:
            plugin = Path(directory) / "plugin with spaces"
            shutil.copytree(ROOT, plugin, ignore=shutil.ignore_patterns("__pycache__"))
            before = sorted(path.relative_to(plugin) for path in plugin.rglob("*"))
            environment = dict(os.environ, CODEBUDDY_PLUGIN_ROOT=str(plugin))
            for event, entries in config["hooks"].items():
                payload = {"hook_event_name": event}
                if event == "UserPromptSubmit":
                    payload["prompt"] = "实现大模型输出校验"
                if event == "PostToolUse":
                    payload.update(tool_name="Write", tool_input={
                        "file_path": "service.py", "content": "client.chat.completions.create()",
                    })
                command = entries[0]["hooks"][0]["command"]
                result = subprocess.run(
                    command, shell=True, input=json.dumps(payload).encode(),
                    capture_output=True, timeout=5, cwd=directory, env=environment,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stderr, b"")
                context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
                self.assertIn(str(plugin / "skills/schema-outputkit/SKILL.md"), context)
            self.assertEqual(before, sorted(path.relative_to(plugin) for path in plugin.rglob("*")))

    def test_missing_skill_is_silent(self):
        with tempfile.TemporaryDirectory(prefix="llm missing skill ") as directory:
            scripts = Path(directory) / "scripts"
            scripts.mkdir()
            script = scripts / "hook.py"
            shutil.copyfile(SCRIPT, script)
            self.assertIsNone(self.invoke({"hook_event_name": "SessionStart"}, script, directory))

    def test_plugin_configuration(self):
        manifest = json.loads((ROOT / ".codebuddy-plugin/plugin.json").read_text())
        self.assertRegex(manifest["name"], r"^[a-z][a-z0-9-]*$")
        config = json.loads((ROOT / "hooks/hooks.json").read_text())
        self.assertEqual(set(config["hooks"]), {"SessionStart"})
        config["hooks"].update(json.loads((ROOT / "hooks/development.json").read_text())["hooks"])
        self.assertEqual(set(config["hooks"]), {"SessionStart", "UserPromptSubmit", "PostToolUse"})
        self.assertEqual(manifest["hooks"], "./hooks/development.json")
        matcher = re.compile(config["hooks"]["PostToolUse"][0]["matcher"])
        self.assertIsNotNone(matcher.fullmatch("Write"))
        self.assertIsNotNone(matcher.fullmatch("Edit"))
        self.assertIsNone(matcher.search("OtherWrite"))
        for entries in config["hooks"].values():
            hook = entries[0]["hooks"][0]
            self.assertEqual(hook["type"], "command")
            self.assertLessEqual(hook.get("timeout", 5), 5)
        skill = ROOT / "skills/schema-outputkit/SKILL.md"
        self.assertTrue(skill.read_text().startswith("---\nname: schema-outputkit\n"))


if __name__ == "__main__":
    unittest.main()
