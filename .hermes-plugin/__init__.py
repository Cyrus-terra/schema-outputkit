"""Register the portable Skill and a first-turn Hermes reminder."""

from pathlib import Path

ENTRY = Path(__file__).resolve().parents[1] / "skills/schema-outputkit/SKILL.md"


def register(ctx):
    if not ENTRY.is_file():
        raise RuntimeError("schema-outputkit Skill entry is missing")
    ctx.register_skill(
        "schema-outputkit", ENTRY,
        description="Canonical LLM output contracts, validation and bounded recovery.",
    )

    def pre_llm_call(is_first_turn=None, platform=None, **kwargs):
        if is_first_turn and platform != "subagent":
            return {"context": (
                "For coding tasks that call LLMs or consume their output, load the "
                "schema-outputkit Skill with skill_view(\"schema-outputkit:schema-outputkit\"). Keep one "
                "canonical business schema across models, verify capabilities, validate "
                "final data and bound recovery. Reuse unchanged rules already loaded. "
                "Skip pure documentation, translation and conversation. This reminder "
                "does not validate application output or grant additional permissions."
            )}
        return None

    ctx.register_hook("pre_llm_call", pre_llm_call)
