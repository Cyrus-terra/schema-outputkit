#!/usr/bin/env python3
"""Validate local packaging without installing clients or calling models."""

import argparse
import json
import re
from pathlib import Path

NAME = "schema-outputkit"
ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u3400-\u9fff]")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(root, relative):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def validate_skill(directory):
    entry = directory / "SKILL.md"
    text = entry.read_text(encoding="utf-8")
    require(text.startswith("---\nname: schema-outputkit\n"), "Invalid Skill identity")
    require(re.search(r"^description: .+", text, re.MULTILINE), "Missing Skill description")
    require(not CJK.search(text), "Skill prose must be English")
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if "://" in target or target.startswith("#"):
            continue
        resolved = (directory / target.split("#", 1)[0]).resolve()
        require(directory.resolve() in resolved.parents, "Skill link escapes standalone directory")
        require(resolved.is_file(), "Missing standalone Skill resource: " + target)


def validate_repository(root):
    validate_skill(root / "skills" / NAME)
    paths = (
        ".claude-plugin/plugin.json", ".codebuddy-plugin/plugin.json",
        ".codex-plugin/plugin.json", "gemini-extension.json",
        "openclaw.plugin.json", "package.json",
    )
    manifests = {path: read_json(root, path) for path in paths}
    version = manifests[".codebuddy-plugin/plugin.json"]["version"]
    require(re.fullmatch(r"\d+\.\d+\.\d+", version), "Invalid package version")
    for path, manifest in manifests.items():
        require(manifest.get("name") == NAME, "Invalid identity: " + path)
        require(manifest.get("version") == version, "Version drift: " + path)
        require(bool(manifest.get("description")), "Missing description: " + path)
        require(not CJK.search(manifest["description"]), "Metadata must be English: " + path)
        require("repository" not in manifest or bool(manifest["repository"]), "Empty repository metadata")
    for client in ("claude", "codebuddy"):
        manifest = manifests[f".{client}-plugin/plugin.json"]
        require(manifest.get("hooks") == "./hooks/development.json", "Invalid development Hook routing")
        market = read_json(root, f".{client}-plugin/marketplace.json")
        require(market.get("name") == NAME, "Marketplace identity drift")
        require(len(market.get("plugins", [])) == 1, "Unexpected marketplace entries")
        plugin = market["plugins"][0]
        require(plugin.get("name") == NAME and plugin.get("source") == "./", "Invalid local marketplace source")
        require(plugin.get("version") == version, "Marketplace version drift")
    codex = manifests[".codex-plugin/plugin.json"]
    require(codex.get("skills") == "./skills/" and codex.get("hooks") == {}, "Invalid Codex Skill-only package")
    marketplace = read_json(root, ".agents/plugins/marketplace.json")
    require(marketplace.get("name") == NAME, "Invalid Codex marketplace identity")
    require(len(marketplace.get("plugins", [])) == 1, "Unexpected Codex marketplace entries")
    plugin = marketplace["plugins"][0]
    require(plugin.get("name") == NAME, "Invalid Codex plugin identity")
    require(plugin.get("source") == {"source": "local", "path": "./"}, "Invalid Codex local source")
    hermes = (root / ".hermes-plugin/plugin.yaml").read_text(encoding="utf-8")
    require(f"name: {NAME}\n" in hermes and f"version: {version}\n" in hermes, "Hermes metadata drift")
    require("  - pre_llm_call\n" in hermes, "Missing Hermes callback")
    require((root / "plugin.yaml").read_text(encoding="utf-8") == hermes, "Root Hermes manifest drift")
    openclaw = manifests["openclaw.plugin.json"]
    require(openclaw.get("id") == NAME and openclaw.get("skills") == ["./skills"], "Invalid OpenClaw Skill path")
    package = manifests["package.json"]
    require(package.get("type") == "module" and package.get("private") is True, "Invalid private ESM package")
    require(package.get("openclaw", {}).get("extensions") == ["./index.js"], "Missing OpenClaw entry")
    for relative in ("index.js", "__init__.py", ".hermes-plugin/__init__.py", "scripts/hook.py", "LICENSE", ".github/workflows/ci.yml"):
        require((root / relative).is_file(), "Missing package file: " + relative)
    shared = read_json(root, "hooks/hooks.json")["hooks"]
    development = read_json(root, "hooks/development.json")["hooks"]
    require(set(shared) == {"SessionStart"}, "Shared Hooks must be session-only")
    require(set(development) == {"UserPromptSubmit", "PostToolUse"}, "Invalid development events")
    for event, entries in {**shared, **development}.items():
        require(len(entries) == 1 and len(entries[0]["hooks"]) == 1, "Duplicate Hook registration")
        command = entries[0]["hooks"][0]
        require(command.get("type") == "command", "Invalid Hook type")
        require('"${CODEBUDDY_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT' in command["command"], "Missing quoted client root")
        if event == "SessionStart":
            require("${extensionPath}" in command["command"] and "timeout" not in command, "Invalid shared Hook timeout/root")
        else:
            require(command.get("timeout") == 5, "Development timeout must be five seconds")
    require(development["PostToolUse"][0].get("matcher") == "^(Write|Edit)$", "Invalid edit matcher")
    for relative in ("README.md", "README.zh-CN.md", "CHANGELOG.md", "docs/installation.md", "docs/development.md"):
        path = root / relative
        text = path.read_text(encoding="utf-8")
        require(not CJK.search(text) or relative == "README.zh-CN.md", "Unexpected translated prose: " + relative)
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            require(root.resolve() in resolved.parents and resolved.is_file(), "Broken documentation link: " + target)
    require("](" + "README.zh-CN.md)" in (root / "README.md").read_text(encoding="utf-8"), "Missing Chinese README link")
    require("](README.md)" in (root / "README.zh-CN.md").read_text(encoding="utf-8"), "Missing English README link")
    require("supercoding contributors" in (root / "LICENSE").read_text(encoding="utf-8"), "Missing attribution")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        if (args.path / "SKILL.md").is_file():
            validate_skill(args.path)
        else:
            validate_repository(args.path)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        parser.exit(1, "Validation failed: " + str(error) + "\n")
    print("Validation passed")


if __name__ == "__main__":
    main()
