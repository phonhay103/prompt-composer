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

    def test_slot_extraction(self):
        section = PromptSection(name="tools", content="Tools: {available_tools}\nEngine: {engine}")
        slots = section.get_slots()
        assert "available_tools" in slots
        assert "engine" in slots

        # Double braces slot extraction
        section_double = PromptSection(name="tools", content="Tools: {{available_tools}}")
        assert section_double.get_slots("double_braces") == ["available_tools"]

    def test_slot_rendering_with_filters(self):
        section = PromptSection(name="tools", content="Tools: {available_tools:upper}")
        rendered = section.render({"available_tools": "tool1, tool2"})
        assert "TOOL1, TOOL2" in rendered

    def test_unresolved_slots_preserved(self):
        section = PromptSection(name="tools", content="{resolved} and {unresolved}")
        rendered = section.render({"resolved": "VALUE"})
        assert "VALUE" in rendered
        assert "{unresolved}" in rendered

    def test_condition_eval(self):
        # String condition checking slot presence
        section1 = PromptSection(name="sec", content="Content", condition="flag")
        assert section1.should_render({"flag": True}) is True
        assert section1.should_render({"flag": False}) is False
        assert section1.should_render({}) is False

        # Callable condition checking slot value
        section2 = PromptSection(name="sec", content="Content", condition=lambda slots: slots.get("x", 0) > 5)
        assert section2.should_render({"x": 10}) is True
        assert section2.should_render({"x": 2}) is False

    def test_callable_content(self):
        section = PromptSection(name="sec", content=lambda slots: f"Mode: {slots.get('mode')}", tag_wrap=False)
        rendered = section.render({"mode": "fast"})
        assert rendered == "Mode: fast"

    def test_repr(self):
        section = PromptSection(name="tools", content="{x}")
        r = repr(section)
        assert "tools" in r
        assert "slots" in r


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
        composer.set_slot("text", "world")
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


# --- Slot Management Tests ---

class TestSlotManagement:
    def test_slot_styles(self):
        # Braces style (default)
        c1 = PromptComposer(slot_style="braces")
        c1.set_section("s1", "Val: {x}")
        c1.set_slot("x", "1")
        assert "Val: 1" in c1.render()

        # Double braces style
        c2 = PromptComposer(slot_style="double_braces")
        c2.set_section("s1", "Val: {{x}}")
        c2.set_slot("x", "2")
        assert "Val: 2" in c2.render()

    def test_filters(self):
        composer = PromptComposer()
        composer.set_section("s", "Json: {d:json} Upper: {u:upper} Indent: {i:indent2}")
        composer.set_slots({
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
        composer.set_slot("x", "hello")
        assert "Val: *hello*" in composer.render()
