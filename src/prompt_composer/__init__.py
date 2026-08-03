"""
prompt-composer — Section-based prompt composition for LLM applications.

Two layers of composition:
1. Sections: Named blocks of text (role, tools, rules, context, etc.)
   that can be added, updated, or removed independently.
2. Slots: {variable} placeholders within sections, filled at render time.

Usage:
    from prompt_composer import PromptComposer

    prompt = PromptComposer.from_file("planner.md", prompts_dir)
    prompt.set_slot("tools", tools_json)
    prompt.remove_section("fallback")
    text = prompt.render()
"""

from prompt_composer.composer import PromptComposer
from prompt_composer.section import PromptSection

__all__ = [
    "PromptComposer",
    "PromptSection",
]
