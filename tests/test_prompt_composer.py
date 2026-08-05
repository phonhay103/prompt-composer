"""Comprehensive tests for PromptComposer."""
import pathlib
import tempfile
import json

from prompt_composer import PromptComposer, PromptSection


# --- PromptSection Tests ---

class TestPromptSection:
    def test_basic_render(self):
        section = PromptSection(name="role", content="You are an expert.")
        rendered = section.render()
        assert "<role>" in rendered
        assert "You are an expert." in rendered
        assert "</role>" in rendered

    def test_render_without_tag_wrap(self):
        section = PromptSection(name="role", content="You are an expert.", tag_wrap=False)
        rendered = section.render()
        assert "<role>" not in rendered
        assert rendered == "You are an expert."

    def test_render_with_custom_string_tag_wrap(self):
        # XML custom tag
        section = PromptSection(name="role", content="You are an expert.", tag_wrap="custom_tag")
        rendered = section.render()
        assert "<custom_tag>" in rendered
        assert "</custom_tag>" in rendered

        # Markdown header prefix custom tag
        section = PromptSection(name="role", content="You are an expert.", tag_wrap="## Role Header")
        rendered = section.render()
        assert rendered == "## Role Header\nYou are an expert."

    def test_variable_extraction(self):
        section = PromptSection(name="tools", content="Tools: {available_tools}\nEngine: {engine}")
        variables = section.get_variables()
        assert "available_tools" in variables
        assert "engine" in variables

        # Double braces variable extraction
        section_double = PromptSection(name="tools", content="Tools: {{available_tools}}")
        assert section_double.get_variables("double_braces") == ["available_tools"]

    def test_variable_rendering_with_filters(self):
        section = PromptSection(name="tools", content="Tools: {available_tools:upper}")
        rendered = section.render({"available_tools": "tool1, tool2"})
        assert "TOOL1, TOOL2" in rendered

    def test_unresolved_variables_preserved(self):
        section = PromptSection(name="tools", content="{resolved} and {unresolved}")
        rendered = section.render({"resolved": "VALUE"})
        assert "VALUE" in rendered
        assert "{unresolved}" in rendered

    def test_condition_eval(self):
        # String condition checking variable presence
        section1 = PromptSection(name="sec", content="Content", condition="flag")
        assert section1.should_render({"flag": True}) is True
        assert section1.should_render({"flag": False}) is False
        assert section1.should_render({}) is False

        # Callable condition checking variable value
        section2 = PromptSection(name="sec", content="Content", condition=lambda vars: vars.get("x", 0) > 5)
        assert section2.should_render({"x": 10}) is True
        assert section2.should_render({"x": 2}) is False

    def test_callable_content(self):
        section = PromptSection(name="sec", content=lambda vars: f"Mode: {vars.get('mode')}", tag_wrap=False)
        rendered = section.render({"mode": "fast"})
        assert rendered == "Mode: fast"

    def test_repr(self):
        section = PromptSection(name="tools", content="{x}")
        r = repr(section)
        assert "tools" in r
        assert "variables" in r


# --- PromptComposer Factory & Formats Tests ---

class TestPromptComposerFactory:
    def test_from_text_xml(self):
        template = """<role>\n  You are an expert planner.\n</role>\n\n<tools>\n{available_tools}\n</tools>"""
        composer = PromptComposer.from_text(template)
        assert composer.has_section("role")
        assert composer.has_section("tools")
        assert composer.list_sections() == ["role", "tools"]

    def test_from_text_json(self):
        template = {
            "preamble": "Hello JSON",
            "sections": [
                {"name": "role", "content": "You are a translator.", "tag_wrap": True},
                {"name": "context", "content": "{text}", "tag_wrap": False}
            ],
            "epilogue": "Bye JSON"
        }
        composer = PromptComposer.from_text(json.dumps(template))
        assert composer.list_sections() == ["role", "context"]
        composer.set_variable("text", "world")
        rendered = composer.render()
        assert "Hello JSON" in rendered
        assert "<role>\nYou are a translator.\n</role>" in rendered
        assert "world" in rendered
        assert "Bye JSON" in rendered

    def test_from_text_yaml(self):
        template = """
preamble: "Hello YAML"
sections:
  - name: role
    content: "You are an assistant."
    tag_wrap: true
  - name: rules
    content: "Rule 1: Be polite."
    tag_wrap: false
"""
        composer = PromptComposer.from_text(template)
        assert composer.list_sections() == ["role", "rules"]
        rendered = composer.render()
        assert "Hello YAML" in rendered
        assert "<role>\nYou are an assistant.\n</role>" in rendered
        assert "Rule 1: Be polite." in rendered

    def test_from_file_auto_detect(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p_json = pathlib.Path(tmpdir) / "test.json"
            p_json.write_text(json.dumps({"sections": [{"name": "s1", "content": "c1"}]}))
            composer_json = PromptComposer.from_file("test.json", pathlib.Path(tmpdir))
            assert composer_json.list_sections() == ["s1"]

            p_yaml = pathlib.Path(tmpdir) / "test.yaml"
            p_yaml.write_text("sections:\n  - name: s2\n    content: c2")
            composer_yaml = PromptComposer.from_file("test.yaml", pathlib.Path(tmpdir))
            assert composer_yaml.list_sections() == ["s2"]


# --- Programmatic & Helper Methods Tests ---

class TestProgrammaticHelpers:
    def test_helpers(self):
        composer = (
            PromptComposer()
            .set_role("You are a model.")
            .set_tools("Tool 1")
            .set_rules("Rule 1")
            .set_instructions("Inst 1")
            .set_context("Ctx 1")
        )
        assert composer.list_sections() == ["role", "tools", "rules", "instructions", "context"]
        assert composer.get_section("role").content == "You are a model."

    def test_constructor_sections(self):
        s1 = PromptSection("s1", "content1")
        s2 = PromptSection("s2", "content2")
        composer = PromptComposer(sections=[s1, s2], preamble="Pre")
        assert composer.list_sections() == ["s1", "s2"]
        assert "Pre" in composer.render()


# --- Variable Management Tests ---

class TestVariableManagement:
    def test_variable_styles(self):
        # Braces style (default)
        c1 = PromptComposer(variable_style="braces")
        c1.set_section("s1", "Val: {x}")
        c1.set_variable("x", "1")
        assert "Val: 1" in c1.render()

        # Double braces style
        c2 = PromptComposer(variable_style="double_braces")
        c2.set_section("s1", "Val: {{x}}")
        c2.set_variable("x", "2")
        assert "Val: 2" in c2.render()

    def test_filters(self):
        composer = PromptComposer()
        composer.set_section("s", "Json: {d:json} Upper: {u:upper} Indent: {i:indent2}")
        composer.set_variables({
            "d": {"a": 1},
            "u": "low",
            "i": "line1\nline2"
        })
        rendered = composer.render()
        assert '"a": 1' in rendered
        assert 'LOW' in rendered
        assert '  line2' in rendered

    def test_custom_filters(self):
        composer = PromptComposer()
        composer.register_filter("custom", lambda v: f"*{v}*")
        composer.set_section("s", "Val: {x:custom}")
        composer.set_variable("x", "hello")
        assert "Val: *hello*" in composer.render()

    def test_markdown_parsing(self):
        template = """
This is the preamble.

## role
You are an assistant.

## tools
{available_tools}
"""
        composer = PromptComposer.from_text(template)
        assert composer._preamble == "This is the preamble."
        assert composer.list_sections() == ["role", "tools"]
        assert composer.get_section("role").content == "You are an assistant."
        assert composer.get_section("role").tag_wrap == "## role"

        composer.set_variable("available_tools", "Tool1")
        rendered = composer.render()
        assert "This is the preamble." in rendered
        assert "## role\nYou are an assistant." in rendered
        assert "## tools\nTool1" in rendered

    def test_output_formatting(self):
        template_yaml = """
sections:
  - name: role
    content: "You are a YAML assistant."
    tag_wrap: true
  - name: rules
    content: "Be nice."
    tag_wrap: false
"""
        composer = PromptComposer.from_text(template_yaml, template_format="yaml")

        # Render normally
        rendered_normal = composer.render()
        assert "<role>\nYou are a YAML assistant.\n</role>" in rendered_normal
        assert "Be nice." in rendered_normal

        # Force XML
        rendered_xml = composer.render(output_format="xml")
        assert "<role>\nYou are a YAML assistant.\n</role>" in rendered_xml
        assert "Be nice." in rendered_xml  # tag_wrap=False remains unwrapped

        # Force Markdown / md
        rendered_md = composer.render(output_format="markdown")
        assert "## role\nYou are a YAML assistant." in rendered_md
        assert "Be nice." in rendered_md  # tag_wrap=False remains unwrapped

    def test_enums(self):
        from prompt_composer import TemplateFormat, VariableStyle, OutputFormat
        
        composer = PromptComposer(variable_style=VariableStyle.DOUBLE_BRACES)
        composer.set_section("s", "Val: {{x}}")
        composer.set_variable("x", "100")
        assert "Val: 100" in composer.render(output_format=OutputFormat.XML)

        template_yaml = "sections:\n  - name: s\n    content: c"
        composer2 = PromptComposer.from_text(
            template_yaml,
            template_format=TemplateFormat.YAML,
            variable_style=VariableStyle.BRACES
        )
        assert composer2.list_sections() == ["s"]

    def test_parser_injection(self):
        from prompt_composer.parsers.base import BaseParser
        from typing import Tuple, List, Dict, Any
        import tempfile
        import pathlib

        class MockCustomParser(BaseParser):
            def parse(self, text: str, variable_style: str = "braces") -> Tuple[str, List[PromptSection], str, Dict[str, Any]]:
                sections = []
                for line in text.strip().split("\n"):
                    if "=" in line:
                        name, content = line.split("=", 1)
                        sections.append(PromptSection(name=name.strip(), content=content.strip()))
                return "Mock Preamble", sections, "Mock Epilogue", {"source": "injected"}

        # Instantiate mock parser
        parser_instance = MockCustomParser()

        # Test from_text with injected parser
        composer = PromptComposer.from_text("role = System Admin\nrules = Be secure", parser=parser_instance)
        assert composer.list_sections() == ["role", "rules"]
        assert composer.get_section("role").content == "System Admin"
        assert "Mock Preamble" in composer.render()
        assert composer.metadata == {"source": "injected"}

        # Test from_file with injected parser
        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir) / "test.custom"
            p.write_text("role = Custom Admin\nrules = Rule 1")
            composer_file = PromptComposer.from_file("test.custom", pathlib.Path(tmpdir), parser=parser_instance)
            assert composer_file.list_sections() == ["role", "rules"]
            assert composer_file.get_section("role").content == "Custom Admin"
            assert composer_file.metadata == {"source": "injected"}

    def test_legacy_parser_backward_compatibility(self):
        from typing import Tuple, List
        class MockLegacyParser:
            def parse(self, text: str, variable_style: str = "braces") -> Tuple[str, List[PromptSection], str]:
                sections = [PromptSection(name="test", content="Legacy Content")]
                return "Legacy Preamble", sections, "Legacy Epilogue"

        composer = PromptComposer.from_text("some text", parser=MockLegacyParser())
        assert composer.list_sections() == ["test"]
        assert composer.get_section("test").content == "Legacy Content"
        assert composer.metadata == {}

    def test_prompt_metadata_parsing(self):
        # 1. YAML Parser with Frontmatter
        yaml_text_frontmatter = """---
name: Translator Prompt
version: 1.2.3
description: Translates user text
---
preamble: "Translate"
sections:
  - name: role
    content: "translator"
"""
        composer_yaml1 = PromptComposer.from_text(yaml_text_frontmatter, template_format="yaml")
        assert composer_yaml1.metadata == {
            "name": "Translator Prompt",
            "version": "1.2.3",
            "description": "Translates user text"
        }
        assert composer_yaml1.list_sections() == ["role"]

        # 2. YAML Parser with top-level metadata key
        yaml_text_key = """
metadata:
  name: Key Prompt
  version: 2.0.0
preamble: "Translate"
sections:
  - name: role
    content: "translator"
"""
        composer_yaml2 = PromptComposer.from_text(yaml_text_key, template_format="yaml")
        assert composer_yaml2.metadata == {
            "name": "Key Prompt",
            "version": "2.0.0"
        }

        # 3. JSON Parser with top-level metadata key
        json_text = """{
            "metadata": {
                "name": "JSON Prompt",
                "version": "1.0"
            },
            "preamble": "Preamble",
            "sections": [
                {"name": "role", "content": "system"}
            ]
        }"""
        composer_json = PromptComposer.from_text(json_text, template_format="json")
        assert composer_json.metadata == {
            "name": "JSON Prompt",
            "version": "1.0"
        }

        # 4. Markdown Parser with Frontmatter
        md_text = """---
title: Markdown Prompt
author: AI
---
# role
You are a markdown parser
"""
        composer_md = PromptComposer.from_text(md_text, template_format="markdown")
        assert composer_md.metadata == {
            "title": "Markdown Prompt",
            "author": "AI"
        }
        assert composer_md.list_sections() == ["role"]

        # 5. XML Parser with `<metadata>`
        xml_text = """<metadata>
            <title>XML Prompt</title>
            <version>4.2</version>
        </metadata>
        <role>
            You are XML
        </role>"""
        composer_xml = PromptComposer.from_text(xml_text, template_format="xml")
        assert composer_xml.metadata == {
            "title": "XML Prompt",
            "version": "4.2"
        }
        assert composer_xml.list_sections() == ["role"]

    def test_advanced_boolean_conditions(self):
        # NOT condition
        sec_not = PromptSection("s", "Content", condition="NOT flag")
        assert sec_not.should_render({"flag": False}) is True
        assert sec_not.should_render({"flag": True}) is False

        # AND condition
        sec_and = PromptSection("s", "Content", condition="a AND b")
        assert sec_and.should_render({"a": True, "b": True}) is True
        assert sec_and.should_render({"a": True, "b": False}) is False

        # OR condition
        sec_or = PromptSection("s", "Content", condition="a OR b")
        assert sec_or.should_render({"a": False, "b": True}) is True
        assert sec_or.should_render({"a": False, "b": False}) is False

        # Parenthesis and complex logic
        sec_complex = PromptSection("s", "Content", condition="a AND (b OR NOT c)")
        assert sec_complex.should_render({"a": True, "b": True, "c": True}) is True
        assert sec_complex.should_render({"a": True, "b": False, "c": False}) is True
        assert sec_complex.should_render({"a": True, "b": False, "c": True}) is False
        assert sec_complex.should_render({"a": False, "b": True, "c": False}) is False

        # Fallback to single variable lookup on syntax error
        sec_err = PromptSection("s", "Content", condition="invalid syntax OR")
        assert sec_err.should_render({"invalid syntax OR": True}) is True
        assert sec_err.should_render({"invalid syntax OR": False}) is False

    def test_chained_formatting_filters(self):
        composer = PromptComposer()
        composer.set_section("s", "Val: {x:upper:trim}")
        composer.set_variable("x", "  hello  ")
        assert "Val: HELLO" in composer.render()

        # Chain 3 filters
        composer.set_section("s2", "Val: {x:json:upper:trim}")
        composer.set_variable("x", ["a", "b"])
        # JSON output will be parsed, dumped, upper-cased, then trimmed
        rendered = composer.render()
        assert "Val: [\n  \"A\",\n  \"B\"\n]" in rendered or "Val: [\n  \"A\",\n  \"B\"\n]" in rendered

