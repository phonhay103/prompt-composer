"""Comprehensive tests for PromptComposer."""
import pathlib
import tempfile

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

    def test_slot_extraction(self):
        section = PromptSection(name="tools", content="Tools: {available_tools}\nEngine: {engine}")
        slots = section.get_slots()
        assert "available_tools" in slots
        assert "engine" in slots

    def test_slot_rendering(self):
        section = PromptSection(name="tools", content="Tools: {available_tools}")
        rendered = section.render({"available_tools": "[tool1, tool2]"})
        assert "[tool1, tool2]" in rendered
        assert "{available_tools}" not in rendered

    def test_unresolved_slots_preserved(self):
        section = PromptSection(name="tools", content="{resolved} and {unresolved}")
        rendered = section.render({"resolved": "VALUE"})
        assert "VALUE" in rendered
        assert "{unresolved}" in rendered

    def test_repr(self):
        section = PromptSection(name="tools", content="{x}")
        r = repr(section)
        assert "tools" in r
        assert "slots" in r


# --- PromptComposer Factory Tests ---

class TestPromptComposerFactory:
    def test_from_text_with_xml_sections(self):
        template = """<role>\n  You are an expert planner.\n</role>\n\n<tools>\n{available_tools}\n</tools>"""
        composer = PromptComposer.from_text(template)
        assert composer.has_section("role")
        assert composer.has_section("tools")
        assert composer.list_sections() == ["role", "tools"]

    def test_from_text_no_sections(self):
        template = "Just a plain prompt with no sections."
        composer = PromptComposer.from_text(template)
        assert composer.list_sections() == []
        assert "plain prompt" in composer.render()

    def test_from_file(self):
        template = "<role>Expert</role>\n\n<rules>{rules}</rules>"
        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir) / "test.md"
            p.write_text(template)
            composer = PromptComposer.from_file("test.md", pathlib.Path(tmpdir))
            assert composer.has_section("role")
            assert composer.has_section("rules")

    def test_preamble_preserved(self):
        template = "Preamble text here.\n\n<role>Expert</role>"
        composer = PromptComposer.from_text(template)
        rendered = composer.render()
        assert "Preamble text here" in rendered


# --- Section Management Tests ---

class TestSectionManagement:
    def test_set_and_get_section(self):
        composer = PromptComposer()
        composer.set_section("role", "Expert planner")
        section = composer.get_section("role")
        assert section is not None
        assert section.content == "Expert planner"

    def test_update_existing_section(self):
        composer = PromptComposer()
        composer.set_section("role", "V1")
        composer.set_section("role", "V2")
        assert composer.get_section("role").content == "V2"

    def test_remove_section(self):
        composer = PromptComposer()
        composer.set_section("role", "Expert")
        composer.remove_section("role")
        assert not composer.has_section("role")

    def test_remove_nonexistent_section(self):
        composer = PromptComposer()
        composer.remove_section("nonexistent")  # Should not raise

    def test_insert_at_position(self):
        composer = PromptComposer()
        composer.set_section("first", "1")
        composer.set_section("third", "3")
        composer.set_section("second", "2", position=1)
        assert composer.list_sections() == ["first", "second", "third"]

    def test_method_chaining(self):
        result = (
            PromptComposer()
            .set_section("role", "Expert")
            .set_section("tools", "{tools}")
            .set_slot("tools", "tool1")
            .render()
        )
        assert "Expert" in result
        assert "tool1" in result


# --- Slot Management Tests ---

class TestSlotManagement:
    def test_global_slot(self):
        composer = PromptComposer()
        composer.set_section("tools", "Available: {tool_list}")
        composer.set_slot("tool_list", "hammer, wrench")
        rendered = composer.render()
        assert "hammer, wrench" in rendered

    def test_section_scoped_slot_overrides_global(self):
        composer = PromptComposer()
        composer.set_section("a", "Value: {x}")
        composer.set_section("b", "Value: {x}")
        composer.set_slot("x", "global")
        composer.set_section_slot("b", "x", "scoped")
        rendered = composer.render()
        parts = rendered.split("\n\n")
        assert "global" in parts[0]
        assert "scoped" in parts[1]

    def test_get_all_slots(self):
        composer = PromptComposer()
        composer.set_section("a", "{x} and {y}")
        composer.set_section("b", "{y} and {z}")
        assert sorted(composer.get_all_slots()) == ["x", "y", "z"]

    def test_get_unresolved_slots(self):
        composer = PromptComposer()
        composer.set_section("a", "{x} and {y}")
        composer.set_slot("x", "resolved")
        assert composer.get_unresolved_slots() == ["y"]

    def test_set_slots_bulk(self):
        composer = PromptComposer()
        composer.set_section("a", "{x} {y}")
        composer.set_slots({"x": "X", "y": "Y"})
        rendered = composer.render()
        assert "X" in rendered
        assert "Y" in rendered


# --- Render Tests ---

class TestRender:
    def test_render_preserves_section_order(self):
        composer = PromptComposer()
        composer.set_section("a", "AAA")
        composer.set_section("b", "BBB")
        composer.set_section("c", "CCC")
        rendered = composer.render()
        assert rendered.index("AAA") < rendered.index("BBB") < rendered.index("CCC")

    def test_render_real_world_planner_prompt(self):
        template = """<role>\n  You are an expert AI Planner.\n</role>\n\n<available_tools>\n{available_tools}\n</available_tools>\n\n<variable_binding_rules>\n  Use $task_<name> references.\n  {binding_instruction}\n{fallback_instruction}\n</variable_binding_rules>"""
        composer = PromptComposer.from_text(template)
        composer.set_slots({
            "available_tools": '[{"name": "search"}]',
            "binding_instruction": "Use JMESPath syntax",
            "fallback_instruction": "",
        })
        rendered = composer.render()
        assert "expert AI Planner" in rendered
        assert "search" in rendered
        assert "JMESPath" in rendered

    def test_repr(self):
        composer = PromptComposer()
        composer.set_section("a", "{x}")
        r = repr(composer)
        assert "PromptComposer" in r
        assert "a" in r
