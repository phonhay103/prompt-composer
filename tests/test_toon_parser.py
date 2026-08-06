"""Tests for ToonParser in PromptComposer."""

import pathlib
import tempfile
from prompt_composer import PromptComposer, TemplateFormat


def test_toon_parsing():
    template = """
    preamble: Hello TOON
    epilogue: Bye TOON

    metadata:
      name: TOON Prompt
      version: "1.0"

    sections[2]{name,content,tag_wrap}:
      role,You are a translator.,true
      context,{text},false
    """
    composer = PromptComposer.from_text(template, template_format=TemplateFormat.TOON)
    
    assert composer.metadata == {"name": "TOON Prompt", "version": "1.0"}
    assert composer.list_sections() == ["role", "context"]
    assert composer._preamble == "Hello TOON"
    assert composer._epilogue == "Bye TOON"
    
    composer.set_variable("text", "world")
    rendered = composer.render()
    assert "Hello TOON" in rendered
    assert "<role>\nYou are a translator.\n</role>" in rendered
    assert "world" in rendered
    assert "Bye TOON" in rendered


def test_toon_from_file_auto_detect():
    template = """
    sections[1]{name,content}:
      role,System
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        p_toon = pathlib.Path(tmpdir) / "prompt.toon"
        p_toon.write_text(template)
        composer = PromptComposer.from_file("prompt.toon", pathlib.Path(tmpdir))
        assert composer.list_sections() == ["role"]
