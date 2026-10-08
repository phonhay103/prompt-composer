"""Tests for TomlParser in PromptComposer."""

import pathlib
import tempfile

from prompt_composer import PromptComposer, TemplateFormat


def test_toml_parsing():
    template = """
    preamble = "Hello TOML"
    epilogue = "Bye TOML"

    [metadata]
    name = "TOML Prompt"
    version = "1.0"

    [[sections]]
    name = "role"
    content = "You are a translator."
    tag_wrap = true

    [[sections]]
    name = "context"
    content = "{text}"
    tag_wrap = false
    """
    composer = PromptComposer.from_text(template, template_format=TemplateFormat.TOML)

    assert composer.metadata == {"name": "TOML Prompt", "version": "1.0"}
    assert composer.list_sections() == ["role", "context"]
    assert composer._preamble == "Hello TOML"
    assert composer._epilogue == "Bye TOML"

    composer.set_variable("text", "world")
    rendered = composer.render()
    assert "Hello TOML" in rendered
    assert "<role>\nYou are a translator.\n</role>" in rendered
    assert "world" in rendered
    assert "Bye TOML" in rendered


def test_toml_from_file_explicit_format():
    template = """
    [[sections]]
    name = "role"
    content = "System"
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        p_toml = pathlib.Path(tmpdir) / "prompt.toml"
        p_toml.write_text(template)
        composer = PromptComposer.from_file("prompt.toml", pathlib.Path(tmpdir), template_format=TemplateFormat.TOML)
        assert composer.list_sections() == ["role"]
