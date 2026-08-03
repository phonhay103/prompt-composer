# prompt-composer

A lightweight, zero-dependency, section-based prompt composition library for LLM applications.

## Features

- **Section-Based Composition**: Build prompts from named sections that can be added, updated, or removed independently.
- **Slot Variables**: Use `{variable}` placeholders within sections, filled at render time with global or section-scoped values.
- **Template Parsing**: Load `.md` template files with XML-like section tags (`<role>...</role>`) and auto-parse into structured sections.
- **Zero Dependencies**: Pure Python standard library — no Pydantic, no LangChain, no external packages.
- **Method Chaining**: Fluent API for concise prompt construction.

## Installation

```bash
pip install prompt-composer
```

## Quick Start

### From Template File

```python
from prompt_composer import PromptComposer

prompt = PromptComposer.from_file("planner_prompt.md", prompts_dir)
prompt.set_slot("available_tools", tools_json)
prompt.set_slot("binding_instruction", "Use JMESPath syntax")

if not enable_fallback:
    prompt.set_slot("fallback_instruction", "")

text = prompt.render()
```

### Programmatic Composition

```python
from prompt_composer import PromptComposer

prompt = (
    PromptComposer()
    .set_section("role", "You are an expert AI planner.")
    .set_section("tools", "{available_tools}")
    .set_section("rules", "Follow these rules:\n1. Be precise\n2. Be concise")
    .set_slot("available_tools", '[{"name": "search"}]')
)

text = prompt.render()
```

### Section-Scoped Slots

```python
prompt = PromptComposer()
prompt.set_section("header", "Model: {model}")
prompt.set_section("footer", "Model: {model}")
prompt.set_slot("model", "gemini-2.5-flash")
prompt.set_section_slot("footer", "model", "gpt-4o")

text = prompt.render()
# header uses "gemini-2.5-flash", footer uses "gpt-4o"
```

### Introspection

```python
prompt = PromptComposer.from_text("<role>Expert</role><tools>{tools}</tools>")
prompt.list_sections()        # ["role", "tools"]
prompt.get_all_slots()        # ["tools"]
prompt.get_unresolved_slots() # ["tools"]
prompt.set_slot("tools", "...")
prompt.get_unresolved_slots() # []
```
