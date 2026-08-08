"""
prompt-composer — Section-based prompt composition for LLM applications.

Two layers of composition:
1. Sections: Named blocks of text (role, tools, rules, context, etc.)
   that can be added, updated, or removed independently.
2. Variables: {variable} placeholders within sections, filled at render time.

Usage:
    from prompt_composer import PromptComposer, TemplateFormat, VariableStyle

    prompt = PromptComposer.from_file("planner.yaml", prompts_dir, template_format=TemplateFormat.YAML)
    prompt.set_variable("tools", tools_json)
    prompt.remove_section("fallback")
    text = prompt.render()
"""

from prompt_composer.composer import PromptComposer
from prompt_composer.enums import OutputFormat, TemplateFormat, VariableStyle
from prompt_composer.formats import DefaultFormatDetector, FormatDetector, FormatDetectorRegistry
from prompt_composer.remote import RemotePromptFormatter, RemoteProviderRegistry
from prompt_composer.section import PromptSection

__all__ = [
    "DefaultFormatDetector",
    "FormatDetector",
    "FormatDetectorRegistry",
    "OutputFormat",
    "PromptComposer",
    "PromptSection",
    "RemotePromptFormatter",
    "RemoteProviderRegistry",
    "TemplateFormat",
    "VariableStyle",
]
