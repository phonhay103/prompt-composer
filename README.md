# prompt-composer

A lightweight, section-based prompt composition library for LLM applications.

## Features

- **Section-Based Composition**: Build prompts from named sections that can be added, updated, or removed independently.
- **Template Variables**: Use `{variable}` or `{{variable}}` placeholders within sections, filled at render time with global or section-scoped values.
- **Multi-Format Parsers**: Load and parse prompt templates in XML (`<section>...</section>`), YAML, JSON, Markdown (`## Section Heading`), TOML, TOON, HCL, and BAML formats.
- **Forced Output Formatting**: Output the final prompt rendered inside XML tags or as Markdown headers dynamically.
- **StrEnum Validation**: Type-safe configuration via `TemplateFormat`, `VariableStyle`, and `OutputFormat` enums.
- **Minimal Dependencies**: Only `pyyaml`, `jinja2`, and `pydantic`. Advanced file-type detection is an optional integration.
- **Method Chaining**: Fluent API for concise prompt construction.
- **Optimized Performance**: C-based string jumps and variable resolution caching.

## Installation

```bash
pip install prompt-composer
```

### Optional: advanced format detection

By default `prompt-composer` detects template formats using file extensions and structural
heuristics. If the optional [`magic-detector`](https://github.com/phonhay103/json-schema-transformer)
suite is importable, it is used automatically for more accurate detection. This integration is
**not** a package dependency (PyPI does not allow direct-URL dependencies, and the
`magic-detector` name on PyPI belongs to an unrelated project). To enable it in a local/dev
environment:

```bash
uv pip install "magic-detector @ git+https://github.com/phonhay103/json-schema-transformer.git@main#subdirectory=packages/magic_detector"
```

When it is absent, `prompt-composer` degrades gracefully to built-in detection.

## Quick Start

### From Template File

`prompt-composer` can auto-detect format from the file extension (`.json`, `.yaml`, `.yml`, `.xml`, `.md`, `.markdown`) or structure.

```python
from prompt_composer import PromptComposer, TemplateFormat

# Auto-detects Markdown heading structure
prompt = PromptComposer.from_file("planner_prompt.yaml", prompts_dir)
prompt.set_variable("available_tools", tools_json)
prompt.set_variable("binding_instruction", "Use JMESPath syntax")

if not enable_fallback:
    prompt.set_variable("fallback_instruction", "")

text = prompt.render()
```

### Programmatic Composition

```python
from prompt_composer import PromptComposer, VariableStyle

prompt = (
    PromptComposer(variable_style=VariableStyle.BRACES)
    .set_section("role", "You are an expert AI planner.")
    .set_section("tools", "{available_tools}")
    .set_section("rules", "Follow these rules:\n1. Be precise\n2. Be concise")
    .set_variable("available_tools", '[{"name": "search"}]')
)

text = prompt.render()
```

### Section-Scoped Variables

```python
from prompt_composer import PromptComposer

prompt = PromptComposer()
prompt.set_section("header", "Model: {model}")
prompt.set_section("footer", "Model: {model}")
prompt.set_variable("model", "gemini-2.5-flash")
prompt.set_section_variable("footer", "model", "gpt-4o")

text = prompt.render()
# header uses "gemini-2.5-flash", footer uses "gpt-4o"
```

### Formatting Filters

You can use built-in filters inside placeholders to format output values:

* `{var:upper}`: Converts to uppercase.
* `{var:lower}`: Converts to lowercase.
* `{var:json}`: Dumps data structures to a JSON string.
* `{var:indent2}`: Indents multi-line content by 2 spaces.

```python
prompt.set_section("config", "Config: {config_dict:json}")
prompt.set_variable("config_dict", {"debug": True})
```

### Forced Output Formatting

No matter how the template was loaded, you can force the rendered output format when calling `render()`:

```python
from prompt_composer import OutputFormat

# Wraps sections in XML tags
xml_prompt = prompt.render(output_format=OutputFormat.XML)

# Wraps sections as Level 2 Markdown headings
markdown_prompt = prompt.render(output_format=OutputFormat.MARKDOWN)
```

### Introspection

```python
prompt = PromptComposer.from_text("<role>Expert</role><tools>{tools}</tools>")
prompt.list_sections()  # ["role", "tools"]
prompt.get_all_variables()  # ["tools"]
prompt.get_unresolved_variables()  # ["tools"]
prompt.set_variable("tools", "...")
prompt.get_unresolved_variables()  # []
```
