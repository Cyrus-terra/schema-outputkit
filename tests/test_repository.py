"""Check client adapters and local packaging without host installation."""

import ast
import copy
import io
import json
import os
import runpy
import shutil
import subprocess
import tempfile
import tokenize
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ROOT_VARIABLES = ("CODEBUDDY_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT", "extensionPath")


def load_validator():
    return runpy.run_path(str(ROOT / "scripts/validate_repository.py"))


class RepositoryTests(unittest.TestCase):
    def test_repository_and_standalone_contracts(self):
        validator = load_validator()
        validator["validate_repository"](ROOT)
        with tempfile.TemporaryDirectory() as directory:
            standalone = Path(directory) / "schema-outputkit"
            shutil.copytree(ROOT / "skills/schema-outputkit", standalone)
            shutil.copyfile(ROOT / "LICENSE", standalone / "LICENSE")
            validator["validate_skill"](standalone)
            self.assertEqual(set(path.name for path in standalone.iterdir()), {"SKILL.md", "LICENSE"})

    def test_validator_rejects_version_drift_and_broken_skill(self):
        validator = load_validator()
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            shutil.copytree(ROOT, plugin, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
            manifest = plugin / "gemini-extension.json"
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["version"] = "99.0.0"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Version drift"):
                validator["validate_repository"](plugin)
            skill = plugin / "skills/schema-outputkit"
            entry = skill / "SKILL.md"
            entry.write_text(entry.read_text(encoding="utf-8") + "\n[Missing](missing.md)\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing standalone"):
                validator["validate_skill"](skill)
            entry.write_text("---\nname: schema-outputkit\ndescription: Test\n---\n[Outside](../../LICENSE)\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escapes"):
                validator["validate_skill"](skill)

    def test_publishable_text_has_no_trailing_whitespace(self):
        suffixes = {".py", ".js", ".json", ".yaml", ".yml", ".md"}
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.name == ".DS_Store":
                continue
            if path.suffix not in suffixes and path.name not in {"LICENSE", ".gitignore"}:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                self.assertEqual(line, line.rstrip(), f"{path.relative_to(ROOT)}:{number}")

    def test_python_syntax_supports_minimum_version_and_english_comments(self):
        cjk = load_validator()["CJK"]
        for relative in ("scripts/hook.py", "scripts/validate_repository.py", ".hermes-plugin/__init__.py", "__init__.py"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source, feature_version=(3, 9))
            self.assertTrue(tree.body)
            # Multilingual regex data is allowed; emitted text and comments remain English.
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type == tokenize.COMMENT:
                    self.assertIsNone(cjk.search(token.string), relative)

    @unittest.skipUnless(os.name == "posix", "Native command expansion is verified on POSIX only")
    def test_actual_hook_commands_for_each_client(self):
        with tempfile.TemporaryDirectory(prefix="schema plugin ") as directory:
            plugin = Path(directory) / "plugin with spaces 模型"
            shutil.copytree(ROOT, plugin, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
            before = sorted(path.relative_to(plugin) for path in plugin.rglob("*"))
            configs = [json.loads((plugin / "hooks/hooks.json").read_text(encoding="utf-8"))]
            configs.append(json.loads((plugin / "hooks/development.json").read_text(encoding="utf-8")))
            for client in ("codebuddy", "claude", "gemini"):
                environment = {key: value for key, value in os.environ.items() if key not in ROOT_VARIABLES}
                if client != "gemini":
                    environment[ROOT_VARIABLES[0 if client == "codebuddy" else 1]] = str(plugin)
                for config in configs[:1] if client == "gemini" else configs:
                    for event, entries in config["hooks"].items():
                        with self.subTest(client=client, event=event):
                            payload = {"hook_event_name": event, "prompt": "Implement LLM output validation", "private": "secret-fixture"}
                            if event == "PostToolUse":
                                payload.update(tool_name="Write", tool_input={"file_path": "service.ts", "content": "await generateObject({model, schema});"})
                            command = entries[0]["hooks"][0]["command"]
                            if client == "gemini":
                                command = command.replace("${extensionPath}", str(plugin))
                            result = subprocess.run(command, shell=True, input=json.dumps(payload).encode(), capture_output=True, env=environment, cwd=directory, timeout=5)
                            self.assertEqual(result.returncode, 0, result.stderr.decode())
                            self.assertEqual(result.stderr, b"")
                            output = json.loads(result.stdout)["hookSpecificOutput"]
                            self.assertEqual(output["hookEventName"], event)
                            self.assertIn(str(plugin / "skills/schema-outputkit/SKILL.md"), output["additionalContext"])
                            self.assertNotIn("secret-fixture", output["additionalContext"])
                            self.assertLessEqual(len(output["additionalContext"].encode()), 4096)
            self.assertEqual(before, sorted(path.relative_to(plugin) for path in plugin.rglob("*")))

    def test_hermes_registration_first_turn_and_isolation(self):
        adapter = runpy.run_path(str(ROOT / ".hermes-plugin/__init__.py"))

        class Context:
            def __init__(self):
                self.skills = []
                self.hooks = {}

            def register_skill(self, name, path, **metadata):
                self.skills.append((name, path, metadata))

            def register_hook(self, name, callback):
                self.hooks[name] = callback

        first, second = Context(), Context()
        adapter["register"](first)
        adapter["register"](second)
        self.assertEqual(first.skills[0][0], "schema-outputkit")
        self.assertTrue(first.skills[0][1].is_file())
        callback = first.hooks["pre_llm_call"]
        kwargs = {"is_first_turn": True, "platform": "cli", "messages": [{"content": "private-fixture"}]}
        original = copy.deepcopy(kwargs)
        output = callback(**kwargs)
        self.assertEqual(set(output), {"context"})
        self.assertNotIn("private-fixture", output["context"])
        output["context"] = "caller mutation"
        self.assertNotEqual(callback(**kwargs)["context"], "caller mutation")
        self.assertEqual(kwargs, original)
        self.assertIsNone(callback(is_first_turn=False, platform="cli"))
        self.assertIsNone(callback(is_first_turn=True, platform="subagent"))
        self.assertIsNone(callback())
        self.assertIsNot(callback, second.hooks["pre_llm_call"])
        with tempfile.TemporaryDirectory() as directory, patch.dict(adapter["register"].__globals__, ENTRY=Path(directory) / "missing.md"):
            with self.assertRaisesRegex(RuntimeError, "missing"):
                adapter["register"](Context())

    def test_hermes_root_entry_registers_the_shared_skill(self):
        adapter = runpy.run_path(str(ROOT / "__init__.py"))
        from unittest.mock import Mock
        context = Mock()
        adapter["register"](context)
        context.register_skill.assert_called_once()
        self.assertEqual(context.register_skill.call_args.args[0], "schema-outputkit")
        self.assertEqual(context.register_skill.call_args.args[1], ROOT / "skills/schema-outputkit/SKILL.md")
        self.assertEqual(context.register_hook.call_args.args[0], "pre_llm_call")

    def test_openclaw_entry_import(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required for the OpenClaw adapter check")
        result = subprocess.run([
            node, "--input-type=module", "-e",
            "import {pathToFileURL} from 'node:url'; "
            "const {default: plugin} = await import(pathToFileURL(process.argv[1])); "
            "if (plugin.id !== 'schema-outputkit' || typeof plugin.register !== 'function') process.exit(1); "
            "plugin.register(Object.freeze({}));",
            str(ROOT / "index.js"),
        ], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stdout, b"")


if __name__ == "__main__":
    unittest.main()
