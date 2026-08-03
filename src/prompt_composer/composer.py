"""PromptComposer — Structured prompt manager with sections and slot variables."""

import re
import pathlib
from typing import Any, Dict, List, Optional
from collections import OrderedDict

from prompt_composer.section import PromptSection

# Regex to match XML-like section tags: <section_name>content</section_name>
_SECTION_TAG_RE = re.compile(
    r"<(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>"   # Opening tag
    r"(?P<content>.*?)"                        # Content (non-greedy)
    r"</(?P=name)>",                           # Matching closing tag
    re.DOTALL,
)


class PromptComposer:
    """
    Structured prompt manager with section-based composition and slot variables.

    Two layers of composition:
    - Sections: Named blocks of text (role, tools, rules, context, etc.)
      that can be added/updated/removed independently.
    - Slots: {variable} placeholders within sections, filled at render time.

    Sections maintain insertion order. The final prompt is rendered by
    concatenating all sections in order, with slot variables filled in.

    Slot resolution priority (highest to lowest):
    1. Section-scoped slots (set via set_section_slot)
    2. Global slots (set via set_slot / set_slots)
    3. Unresolved slots are left as-is
    """

    def __init__(self) -> None:
        self._sections: OrderedDict[str, PromptSection] = OrderedDict()
        self._global_slots: Dict[str, str] = {}
        self._section_slots: Dict[str, Dict[str, str]] = {}
        self._preamble: str = ""
        self._epilogue: str = ""

    # --- Factory Methods ---

    @classmethod
    def from_file(cls, filename: str, prompts_dir: pathlib.Path) -> "PromptComposer":
        """
        Load a template file and parse it into sections.

        Sections are detected by XML-like tags: <section_name>...</section_name>
        Text before the first section becomes the preamble.
        Text after the last section becomes the epilogue.

        Args:
            filename: Template file name (e.g., "planner_prompt.md")
            prompts_dir: Directory containing the template file

        Returns:
            PromptComposer instance with parsed sections
        """
        filepath = prompts_dir / filename
        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()
        return cls.from_text(raw_text)

    @classmethod
    def from_text(cls, raw_text: str) -> "PromptComposer":
        """
        Parse raw prompt text into sections.

        Args:
            raw_text: Template text with XML-like section tags

        Returns:
            PromptComposer instance with parsed sections
        """
        composer = cls()
        composer._parse_template(raw_text)
        return composer

    # --- Section Management ---

    def set_section(
        self,
        name: str,
        content: str,
        tag_wrap: bool = True,
        position: Optional[int] = None,
    ) -> "PromptComposer":
        """
        Add or update a named section.

        If the section exists, its content is replaced in-place (position preserved).
        If the section is new and no position is given, it's appended at the end.

        Args:
            name: Section identifier
            content: Text content (may contain {slot} placeholders)
            tag_wrap: Wrap in <name>...</name> tags when rendering
            position: Insertion index for new sections (None = append)

        Returns:
            self (for method chaining)
        """
        section = PromptSection(name=name, content=content, tag_wrap=tag_wrap)

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
        """
        Remove a section by name. No-op if section doesn't exist.

        Returns:
            self (for method chaining)
        """
        self._sections.pop(name, None)
        self._section_slots.pop(name, None)
        return self

    def has_section(self, name: str) -> bool:
        """Check if a section exists."""
        return name in self._sections

    def list_sections(self) -> List[str]:
        """List all section names in order."""
        return list(self._sections.keys())

    # --- Slot Management ---

    def set_slot(self, key: str, value: Any) -> "PromptComposer":
        """
        Set a global slot variable. Applied to all sections during render.

        Returns:
            self (for method chaining)
        """
        self._global_slots[key] = str(value)
        return self

    def set_slots(self, slots: Dict[str, Any]) -> "PromptComposer":
        """
        Set multiple global slot variables at once.

        Returns:
            self (for method chaining)
        """
        for key, value in slots.items():
            self._global_slots[key] = str(value)
        return self

    def set_section_slot(
        self, section_name: str, key: str, value: Any
    ) -> "PromptComposer":
        """
        Set a slot variable scoped to a specific section.
        Section-scoped slots override global slots for that section.

        Returns:
            self (for method chaining)
        """
        if section_name not in self._section_slots:
            self._section_slots[section_name] = {}
        self._section_slots[section_name][key] = str(value)
        return self

    def get_all_slots(self) -> List[str]:
        """List all slot variable names found across all sections."""
        all_slots: set[str] = set()
        for section in self._sections.values():
            all_slots.update(section.get_slots())
        return sorted(all_slots)

    def get_unresolved_slots(self) -> List[str]:
        """List slot variable names that have not been set (global or section-scoped)."""
        all_slots = set(self.get_all_slots())
        resolved: set[str] = set(self._global_slots.keys())
        for section_slots in self._section_slots.values():
            resolved.update(section_slots.keys())
        return sorted(all_slots - resolved)

    # --- Rendering ---

    def render(self) -> str:
        """
        Render the full prompt by concatenating all sections with slots filled.

        Returns:
            Complete prompt string ready for LLM consumption
        """
        parts: List[str] = []

        if self._preamble.strip():
            parts.append(self._apply_slots(self._preamble, None))

        for name, section in self._sections.items():
            merged_slots = dict(self._global_slots)
            if name in self._section_slots:
                merged_slots.update(self._section_slots[name])
            rendered = section.render(merged_slots)
            parts.append(rendered)

        if self._epilogue.strip():
            parts.append(self._apply_slots(self._epilogue, None))

        return "\n\n".join(parts)

    # --- Internal ---

    def _parse_template(self, raw_text: str) -> None:
        """Parse raw template text into sections using XML-like tags."""
        matches = list(_SECTION_TAG_RE.finditer(raw_text))

        if not matches:
            self._preamble = raw_text
            return

        self._preamble = raw_text[: matches[0].start()].strip()

        for match in matches:
            name = match.group("name")
            content = match.group("content").strip()
            self._sections[name] = PromptSection(
                name=name, content=content, tag_wrap=True
            )

        self._epilogue = raw_text[matches[-1].end() :].strip()

    def _apply_slots(self, text: str, section_name: Optional[str]) -> str:
        """Apply slot variables to arbitrary text."""
        merged = dict(self._global_slots)
        if section_name and section_name in self._section_slots:
            merged.update(self._section_slots[section_name])
        for key, value in merged.items():
            text = text.replace(f"{{{key}}}", value)
        return text

    def __repr__(self) -> str:
        sections = self.list_sections()
        unresolved = self.get_unresolved_slots()
        return (
            f"PromptComposer(sections={sections}, "
            f"unresolved_slots={unresolved})"
        )
