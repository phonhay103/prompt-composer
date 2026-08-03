"""PromptComposer — Structured prompt manager with sections and slot variables."""

import json
import pathlib
from typing import Any, Dict, List, Optional, Union, Callable
from collections import OrderedDict

from prompt_composer.section import PromptSection

DEFAULT_FILTERS: Dict[str, Callable[[Any], str]] = {
    "json": lambda v: json.dumps(v, indent=2) if not isinstance(v, str) else v,
    "upper": lambda v: str(v).upper(),
    "lower": lambda v: str(v).lower(),
    "trim": lambda v: str(v).strip(),
    "strip": lambda v: str(v).strip(),
    "indent2": lambda v: "\n".join("  " + line if line else line for line in str(v).splitlines()),
    "indent4": lambda v: "\n".join("    " + line if line else line for line in str(v).splitlines()),
}


class PromptComposer:
    """
    Structured prompt manager with section-based composition and slot variables.

    Two layers of composition:
    - Sections: Named blocks of text (role, tools, rules, context, etc.)
      that can be added/updated/removed independently.
    - Slots: {variable} placeholders within sections, filled at render time.

    Sections maintain insertion order. The final prompt is rendered by
    concatenating all sections in order, with slot variables filled in.
    """

    def __init__(
        self,
        sections: Optional[List[PromptSection]] = None,
        preamble: str = "",
        epilogue: str = "",
        slot_style: str = "braces",
    ) -> None:
        self._sections: OrderedDict[str, PromptSection] = OrderedDict()
        self._global_slots: Dict[str, Any] = {}
        self._section_slots: Dict[str, Dict[str, Any]] = {}
        self._preamble: str = preamble
        self._epilogue: str = epilogue
        self._filters: Dict[str, Callable[[Any], str]] = dict(DEFAULT_FILTERS)

        if slot_style not in ("braces", "python", "double_braces", "jinja"):
            raise ValueError(f"Unknown slot style: {slot_style}")
        self._slot_style: str = slot_style

        if sections:
            for section in sections:
                self._sections[section.name] = section

    # --- Factory Methods ---

    @classmethod
    def from_file(
        cls,
        filename: str,
        prompts_dir: pathlib.Path,
        template_format: str = "auto",
        slot_style: str = "braces",
    ) -> "PromptComposer":
        """
        Load a template file and parse it into sections.
        Automatically detects JSON, YAML, or XML formats based on file extension and contents.
        """
        filepath = prompts_dir / filename
        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()

        fmt = template_format
        if fmt == "auto":
            if filepath.suffix in (".json",):
                fmt = "json"
            elif filepath.suffix in (".yaml", ".yml"):
                fmt = "yaml"
            else:
                # Text content-based auto detection
                trimmed = raw_text.strip()
                if trimmed.startswith("{") and trimmed.endswith("}"):
                    fmt = "json"
                elif (
                    "sections:" in raw_text
                    or "preamble:" in raw_text
                    or "epilogue:" in raw_text
                ):
                    fmt = "yaml"
                else:
                    fmt = "xml"

        if fmt == "json":
            return cls.from_json_text(raw_text, slot_style=slot_style)
        elif fmt == "yaml":
            return cls.from_yaml_text(raw_text, slot_style=slot_style)
        else:
            composer = cls(slot_style=slot_style)
            composer._parse_xml(raw_text)
            return composer

    @classmethod
    def from_text(
        cls,
        raw_text: str,
        template_format: str = "auto",
        slot_style: str = "braces",
    ) -> "PromptComposer":
        """Parse raw prompt text into sections."""
        fmt = template_format
        if fmt == "auto":
            trimmed = raw_text.strip()
            if trimmed.startswith("{") and trimmed.endswith("}"):
                fmt = "json"
            elif (
                "sections:" in raw_text
                or "preamble:" in raw_text
                or "epilogue:" in raw_text
            ):
                fmt = "yaml"
            else:
                fmt = "xml"

        if fmt == "json":
            return cls.from_json_text(raw_text, slot_style=slot_style)
        elif fmt == "yaml":
            return cls.from_yaml_text(raw_text, slot_style=slot_style)
        else:
            composer = cls(slot_style=slot_style)
            composer._parse_xml(raw_text)
            return composer

    @classmethod
    def from_json_text(cls, json_text: str, slot_style: str = "braces") -> "PromptComposer":
        """Load structured prompt from a JSON string."""
        data = json.loads(json_text)
        return cls._from_dict(data, slot_style=slot_style)

    @classmethod
    def from_yaml_text(cls, yaml_text: str, slot_style: str = "braces") -> "PromptComposer":
        """Load structured prompt from a YAML string."""
        import yaml
        data = yaml.safe_load(yaml_text) or {}
        return cls._from_dict(data, slot_style=slot_style)

    @classmethod
    def _from_dict(cls, data: dict, slot_style: str = "braces") -> "PromptComposer":
        composer = cls(slot_style=slot_style)
        composer._preamble = data.get("preamble", "")
        composer._epilogue = data.get("epilogue", "")

        # Load sections
        for item in data.get("sections", []):
            name = item["name"]
            content = item["content"]
            tag_wrap = item.get("tag_wrap", True)
            condition = item.get("condition", None)
            composer.set_section(name, content, tag_wrap=tag_wrap, condition=condition)

        return composer

    # --- Section Management ---

    def set_section(
        self,
        name: str,
        content: Union[str, Callable[[Dict[str, Any]], str]],
        tag_wrap: Union[bool, str] = True,
        position: Optional[int] = None,
        condition: Optional[Union[str, Callable[[Dict[str, Any]], bool]]] = None,
    ) -> "PromptComposer":
        """Add or update a named section."""
        section = PromptSection(name=name, content=content, tag_wrap=tag_wrap, condition=condition)

        if position is not None and name not in self._sections:
            items = list(self._sections.items())
            items.insert(position, (name, section))
            self._sections = OrderedDict(items)
        else:
            self._sections[name] = section

        return self

    def get_section(self, name: str) -> Optional[PromptSection]:
        """Get a section by name, or None if not found."""
        return self._sections.get(name)

    def remove_section(self, name: str) -> "PromptComposer":
        """Remove a section by name."""
        self._sections.pop(name, None)
        self._section_slots.pop(name, None)
        return self

    def has_section(self, name: str) -> bool:
        """Check if a section exists."""
        return name in self._sections

    def list_sections(self) -> List[str]:
        """List all section names in order."""
        return list(self._sections.keys())

    # --- Common Section Helpers ---

    def set_role(
        self,
        content: Union[str, Callable[[Dict[str, Any]], str]],
        tag_wrap: Union[bool, str] = True,
        condition: Optional[Union[str, Callable[[Dict[str, Any]], bool]]] = None,
    ) -> "PromptComposer":
        """Set the 'role' section."""
        return self.set_section("role", content, tag_wrap=tag_wrap, condition=condition)

    def set_tools(
        self,
        content: Union[str, Callable[[Dict[str, Any]], str]],
        tag_wrap: Union[bool, str] = True,
        condition: Optional[Union[str, Callable[[Dict[str, Any]], bool]]] = None,
    ) -> "PromptComposer":
        """Set the 'tools' section."""
        return self.set_section("tools", content, tag_wrap=tag_wrap, condition=condition)

    def set_rules(
        self,
        content: Union[str, Callable[[Dict[str, Any]], str]],
        tag_wrap: Union[bool, str] = True,
        condition: Optional[Union[str, Callable[[Dict[str, Any]], bool]]] = None,
    ) -> "PromptComposer":
        """Set the 'rules' section."""
        return self.set_section("rules", content, tag_wrap=tag_wrap, condition=condition)

    def set_instructions(
        self,
        content: Union[str, Callable[[Dict[str, Any]], str]],
        tag_wrap: Union[bool, str] = True,
        condition: Optional[Union[str, Callable[[Dict[str, Any]], bool]]] = None,
    ) -> "PromptComposer":
        """Set the 'instructions' section."""
        return self.set_section("instructions", content, tag_wrap=tag_wrap, condition=condition)

    def set_context(
        self,
        content: Union[str, Callable[[Dict[str, Any]], str]],
        tag_wrap: Union[bool, str] = True,
        condition: Optional[Union[str, Callable[[Dict[str, Any]], bool]]] = None,
    ) -> "PromptComposer":
        """Set the 'context' section."""
        return self.set_section("context", content, tag_wrap=tag_wrap, condition=condition)

    # --- Slot Management ---

    def set_slot(self, key: str, value: Any) -> "PromptComposer":
        """Set a global slot variable."""
        self._global_slots[key] = value
        return self

    def set_slots(self, slots: Dict[str, Any]) -> "PromptComposer":
        """Set multiple global slot variables at once."""
        for key, value in slots.items():
            self._global_slots[key] = value
        return self

    def set_section_slot(self, section_name: str, key: str, value: Any) -> "PromptComposer":
        """Set a slot variable scoped to a specific section."""
        if section_name not in self._section_slots:
            self._section_slots[section_name] = {}
        self._section_slots[section_name][key] = value
        return self

    def get_all_slots(self) -> List[str]:
        """List all slot variable names found across all sections."""
        all_slots: set[str] = set()
        for section in self._sections.values():
            all_slots.update(section.get_slots(self._slot_style))
        return sorted(all_slots)

    def get_unresolved_slots(self) -> List[str]:
        """List slot variable names that have not been set (global or section-scoped)."""
        all_slots = set(self.get_all_slots())
        resolved: set[str] = set(self._global_slots.keys())
        for section_slots in self._section_slots.values():
            resolved.update(section_slots.keys())
        return sorted(all_slots - resolved)

    # --- Filter Management ---

    def register_filter(self, name: str, func: Callable[[Any], str]) -> "PromptComposer":
        """Register a custom filter for slot values."""
        self._filters[name] = func
        return self

    def list_filters(self) -> List[str]:
        """List all registered filter names."""
        return list(self._filters.keys())

    def get_filter(self, name: str) -> Optional[Callable[[Any], str]]:
        """Get a registered filter by name."""
        return self._filters.get(name)

    def has_filter(self, name: str) -> bool:
        """Check if a filter exists."""
        return name in self._filters

    # --- Rendering ---

    def render(self) -> str:
        """Render the full prompt by concatenating all sections with slots filled."""
        parts: List[str] = []

        if self._preamble.strip():
            # Apply slots to preamble using section.py's regex-free replacement
            parts.append(self._apply_slots_to_text(self._preamble))

        for name, section in self._sections.items():
            merged_slots = dict(self._global_slots)
            if name in self._section_slots:
                merged_slots.update(self._section_slots[name])

            if not section.should_render(merged_slots):
                continue

            rendered = section.render(merged_slots, self._slot_style, self._filters)
            parts.append(rendered)

        if self._epilogue.strip():
            parts.append(self._apply_slots_to_text(self._epilogue))

        return "\n\n".join(parts)

    # --- Internal Parsing ---

    def _parse_xml(self, text: str) -> None:
        """Parse raw template text into sections using a 100% regex-free XML tag scanner."""
        self._sections.clear()
        i = 0
        n = len(text)
        last_end = 0

        while i < n:
            start_open = text.find("<", i)
            if start_open == -1:
                break
            end_open = text.find(">", start_open)
            if end_open == -1:
                break

            tag_name = text[start_open + 1 : end_open].strip()
            # Valid tag name check (alphanumeric and underscores only, not a closing tag)
            if tag_name.startswith("/") or not tag_name.replace("_", "").isalnum():
                i = start_open + 1
                continue

            close_tag = f"</{tag_name}>"
            start_close = text.find(close_tag, end_open + 1)
            if start_close == -1:
                i = start_open + 1
                continue

            content = text[end_open + 1 : start_close].strip()

            if not self._sections:
                self._preamble = text[last_end:start_open].strip()

            self._sections[tag_name] = PromptSection(name=tag_name, content=content, tag_wrap=True)
            last_end = start_close + len(close_tag)
            i = last_end

        if not self._sections:
            self._preamble = text.strip()
        else:
            self._epilogue = text[last_end:].strip()

    def _apply_slots_to_text(self, text: str) -> str:
        """Helper to apply slots directly to preamble/epilogue."""
        dummy_section = PromptSection(name="dummy", content=text, tag_wrap=False)
        return dummy_section.render(self._global_slots, self._slot_style, self._filters)

    def __repr__(self) -> str:
        sections = self.list_sections()
        unresolved = self.get_unresolved_slots()
        return (
            f"PromptComposer(sections={sections}, "
            f"unresolved_slots={unresolved}, slot_style='{self._slot_style}')"
        )
