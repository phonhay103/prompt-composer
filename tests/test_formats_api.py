"""Tests for explicit per-format constructors and format dispatch (no auto-detection)."""

import pathlib

import pytest

from prompt_composer import PromptComposer, TemplateFormat

TEMPLATES = pathlib.Path(__file__).parent.parent / "templates"

# (file suffix, TemplateFormat) pairs for the bundled example templates.
EXAMPLE_FORMATS = [
    ("json", TemplateFormat.JSON),
    ("yaml", TemplateFormat.YAML),
    ("xml", TemplateFormat.XML),
    ("md", TemplateFormat.MARKDOWN),
    ("toml", TemplateFormat.TOML),
    ("toon", TemplateFormat.TOON),
    ("hcl", TemplateFormat.HCL),
    ("baml", TemplateFormat.BAML),
]


@pytest.mark.parametrize(("suffix", "fmt"), EXAMPLE_FORMATS)
def test_from_file_explicit_format(suffix, fmt):
    composer = PromptComposer.from_file(f"prompt_example.{suffix}", TEMPLATES, template_format=fmt)
    assert composer.render()


def test_per_format_constructors_dispatch_correctly():
    assert PromptComposer.from_xml("<role>You are a planner.</role>").list_sections() == ["role"]
    assert PromptComposer.from_json('{"sections": [{"name": "role", "content": "x"}]}').list_sections() == ["role"]
    assert PromptComposer.from_yaml("sections:\n  - name: role\n    content: x").list_sections() == ["role"]
    assert PromptComposer.from_markdown("## role\nx").list_sections() == ["role"]


def test_template_format_is_required():
    with pytest.raises(TypeError):
        PromptComposer.from_text("x")


def test_unknown_template_format_raises():
    with pytest.raises(ValueError):
        PromptComposer.from_text("x", template_format="nope")
