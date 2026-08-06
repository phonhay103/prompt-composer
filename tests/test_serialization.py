"""Tests for universal serialization and format slices in PromptComposer."""

import json

import tomllib
import yaml

from prompt_composer import PromptComposer, TemplateFormat


def test_json_serialization():
    template = {
        "preamble": "Hello JSON",
        "epilogue": "Bye JSON",
        "metadata": {"name": "JSON Test", "version": "1.0"},
        "sections": [
            {"name": "role", "content": "Assistant", "tag_wrap": True},
            {"name": "context", "content": "{input}", "tag_wrap": False}
        ]
    }
    composer = PromptComposer.from_text(json.dumps(template), template_format=TemplateFormat.JSON)

    # 1. Test json compact
    compact_out = composer.serialize(TemplateFormat.JSON_COMPACT)
    # Check no extra whitespace/newlines
    assert "\n" not in compact_out
    parsed_compact = json.loads(compact_out)
    assert parsed_compact["metadata"] == {"name": "JSON Test", "version": "1.0"}

    # 2. Test json pretty
    pretty_out = composer.serialize(TemplateFormat.JSON_PRETTY)
    assert "\n" in pretty_out
    parsed_pretty = json.loads(pretty_out)
    assert parsed_pretty["preamble"] == "Hello JSON"

    # 3. Test standard json (default is pretty/indented)
    standard_out = composer.serialize(TemplateFormat.JSON)
    assert "\n" in standard_out


def test_yaml_serialization():
    template = """
    preamble: "Hello YAML"
    metadata:
      title: "YAML test"
    sections:
      - name: "rules"
        content: "Rule 1"
        tag_wrap: false
    """
    composer = PromptComposer.from_text(template, template_format=TemplateFormat.YAML)

    yaml_out = composer.serialize(TemplateFormat.YAML)
    parsed = yaml.safe_load(yaml_out)
    assert parsed["preamble"] == "Hello YAML"
    assert parsed["metadata"] == {"title": "YAML test"}
    assert parsed["sections"][0]["name"] == "rules"


def test_xml_serialization():
    template = """<metadata>
        <title>XML test</title>
    </metadata>
    <preamble>
    Pre content
    </preamble>
    <role>
    System Admin
    </role>"""
    composer = PromptComposer.from_text(template, template_format=TemplateFormat.XML)

    xml_out = composer.serialize(TemplateFormat.XML)
    assert "<metadata>" in xml_out
    assert "<title>XML test</title>" in xml_out
    assert "<role>" in xml_out
    assert "System Admin" in xml_out


def test_markdown_serialization():
    template = """---
    title: MD test
    ---
    Preamble MD
    
    ## role
    Translator
    """
    composer = PromptComposer.from_text(template, template_format=TemplateFormat.MARKDOWN)

    md_out = composer.serialize(TemplateFormat.MARKDOWN)
    assert "title: MD test" in md_out
    assert "## role" in md_out
    assert "Translator" in md_out


def test_baml_serialization():
    template = """
    class Query {
      q string
    }

    function Search(query: Query) -> string {
      client "google"
      prompt #"
        <role>
        You are a search query router.
        </role>
      "#
    }
    """
    composer = PromptComposer.from_text(template, template_format=TemplateFormat.BAML)

    baml_out = composer.serialize(TemplateFormat.BAML)
    assert "class Query" in baml_out
    assert "function Search" in baml_out
    assert "client \"google\"" in baml_out
    assert "<role>" in baml_out


def test_toml_serialization():
    template = """
    preamble = "Hello TOML"
    
    [metadata]
    author = "AI"

    [[sections]]
    name = "role"
    content = "Translator"
    tag_wrap = true
    """
    composer = PromptComposer.from_text(template, template_format=TemplateFormat.TOML)

    toml_out = composer.serialize(TemplateFormat.TOML)
    parsed = tomllib.loads(toml_out)
    assert parsed["preamble"] == "Hello TOML"
    assert parsed["metadata"]["author"] == "AI"
    assert parsed["sections"][0]["name"] == "role"


def test_toon_serialization():
    template = """
    preamble: Hello TOON
    
    metadata:
      version: 1.0
      
    sections[1]{name,content,tag_wrap}:
      role,System,true
    """
    composer = PromptComposer.from_text(template, template_format=TemplateFormat.TOON)

    toon_out = composer.serialize(TemplateFormat.TOON)
    assert "preamble: " in toon_out and "Hello TOON" in toon_out
    assert "metadata:" in toon_out
    assert "sections[1]" in toon_out
