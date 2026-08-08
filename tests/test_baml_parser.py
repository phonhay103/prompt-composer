"""Tests for BamlParser in PromptComposer."""

import pathlib
import tempfile

from prompt_composer import PromptComposer, TemplateFormat


def test_baml_comment_stripping():
    template = """
    // This is a comment
    class User {
      id int // user identifier
      name string
    }

    /*
     * Multi-line comment
     */
    function GetUser(id: int) -> User {
      client "openai/gpt-4o"
      prompt #"
        // This is NOT a comment because it is inside the prompt raw string.
        Hello: {{ id }}
      "#
    }
    """
    composer = PromptComposer.from_text(template, template_format=TemplateFormat.BAML)

    # Check classes and enums extracted
    assert "User" in composer.metadata["classes"]
    # Check comments inside class body are stripped (though we don't strictly parse class body yet, we check clean_text was used)
    assert "// user identifier" not in composer.metadata["classes"]["User"]

    # Check function metadata
    assert composer.metadata["function_name"] == "GetUser"
    assert composer.metadata["client"] == "openai/gpt-4o"
    assert composer.metadata["return_type"] == "User"
    assert composer.metadata["arguments"] == {"id": "int"}

    # Check sections (single function, plain text fallback)
    assert len(composer.list_sections()) == 1
    assert "GetUser" in composer.list_sections()
    content = composer.get_section("GetUser").content
    # The comment inside prompt raw string MUST be preserved!
    assert "// This is NOT a comment because it is inside the prompt raw string." in content
    assert "Hello: {{ id }}" in content


def test_single_function_nested_xml():
    template = """
    function GetTranslation(text: string) -> string {
      client openai
      prompt #"
        <role>
        You are a translator.
        </role>
        <instructions>
        Translate {text} to French.
        </instructions>
      "#
    }
    """
    composer = PromptComposer.from_text(template)  # should auto-detect BAML
    assert composer.metadata["function_name"] == "GetTranslation"
    assert composer.metadata["client"] == "openai"
    assert composer.list_sections() == ["role", "instructions"]
    assert composer.get_section("role").content == "You are a translator."


def test_single_function_nested_markdown():
    template = """
    function GetSummary(text: string) -> string {
      client "claude-3"
      prompt #"
        ## role
        You are a summarizer.
        ## context
        Text: {text}
      "#
    }
    """
    composer = PromptComposer.from_text(template)
    assert composer.metadata["function_name"] == "GetSummary"
    assert composer.list_sections() == ["role", "context"]
    assert composer.get_section("role").content == "You are a summarizer."


def test_multiple_functions():
    template = """
    function FuncOne(x: int) -> int {
      client "model-1"
      prompt #"
        Prompt one: {x}
      "#
    }

    function FuncTwo(y: string) -> string {
      client "model-2"
      prompt #"
        Prompt two: {y}
      "#
    }
    """
    composer = PromptComposer.from_text(template)
    assert composer.list_sections() == ["FuncOne", "FuncTwo"]
    assert composer.metadata["functions"]["FuncOne"]["client"] == "model-1"
    assert composer.metadata["functions"]["FuncTwo"]["client"] == "model-2"
    assert "Prompt one: {x}" in composer.get_section("FuncOne").content
    assert "Prompt two: {y}" in composer.get_section("FuncTwo").content


def test_baml_from_file_auto_detect():
    template = """
    class Query {
      q string
    }

    function Search(query: Query) -> string {
      client "google-search"
      prompt #"
        Perform search for: {query}
      "#
    }
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        p_baml = pathlib.Path(tmpdir) / "search.baml"
        p_baml.write_text(template)
        composer = PromptComposer.from_file("search.baml", pathlib.Path(tmpdir))
        assert composer.metadata["function_name"] == "Search"
        assert composer.metadata["arguments"] == {"query": "Query"}
        assert composer.list_sections() == ["Search"]
