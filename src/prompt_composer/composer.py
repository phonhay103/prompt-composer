"""PromptComposer — Structured prompt manager with sections and slot variables."""

import json
import pathlib
from typing import Any, Dict, List, Optional, Union, Callable
from collections import OrderedDict

from prompt_composer.section import PromptSection
from prompt_composer.parsers.base import BaseParser
from prompt_composer.filters import DEFAULT_FILTERS
from prompt_composer.enums import TemplateFormat, VariableStyle, OutputFormat


class PromptComposer:

    def __init__(
        self,
        sections: Optional[List[PromptSection]] = None,
        preamble: str = "",
        epilogue: str = "",
        variable_style: Union[str, VariableStyle] = VariableStyle.BRACES,
    ) -> None:
        self._sections: OrderedDict[str, PromptSection] = OrderedDict()
        self._global_variables: Dict[str, Any] = {}
        self._section_variables: Dict[str, Dict[str, Any]] = {}
        self._preamble: str = preamble
        self._epilogue: str = epilogue
        self._filters: Dict[str, Callable[[Any], str]] = dict(DEFAULT_FILTERS)

        try:
            self._variable_style: VariableStyle = VariableStyle(variable_style)
        except ValueError:
            raise ValueError(f"Unknown variable style: {variable_style}")

        if sections:
            for section in sections:
                self._sections[section.name] = section

    # --- Factory Methods ---

    @classmethod
    def from_file(
        cls,
        filename: str,
        prompts_dir: pathlib.Path,
        template_format: Union[str, TemplateFormat] = TemplateFormat.AUTO,
        variable_style: Union[str, VariableStyle] = VariableStyle.BRACES,
        parser: Optional[BaseParser] = None,
    ) -> "PromptComposer":
        """
        Load a template file and parse it into sections.
        Automatically detects JSON, YAML, XML, or Markdown formats based on file extension and contents.
        """
        filepath = prompts_dir / filename
        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()

        if parser is None:
            try:
                fmt = TemplateFormat(template_format)
            except ValueError:
                raise ValueError(f"Unknown template format: {template_format}")

            if fmt == TemplateFormat.AUTO:
                suffix = filepath.suffix.lower()
                if suffix == ".json":
                    fmt = TemplateFormat.JSON
                elif suffix in (".yaml", ".yml"):
                    fmt = TemplateFormat.YAML
                elif suffix in (".md", ".markdown"):
                    fmt = TemplateFormat.MARKDOWN
                elif suffix == ".xml":
                    fmt = TemplateFormat.XML
                else:
                    fmt = TemplateFormat(cls.detect_format(raw_text))
        else:
            fmt = template_format

        try:
            v_style = VariableStyle(variable_style)
        except ValueError:
            raise ValueError(f"Unknown variable style: {variable_style}")

        return cls.from_text(raw_text, template_format=fmt, variable_style=v_style, parser=parser)

    @classmethod
    def from_text(
        cls,
        raw_text: str,
        template_format: Union[str, TemplateFormat] = TemplateFormat.AUTO,
        variable_style: Union[str, VariableStyle] = VariableStyle.BRACES,
        parser: Optional[BaseParser] = None,
    ) -> "PromptComposer":
        """Parse raw prompt text into sections."""
        if parser is None:
            try:
                fmt = TemplateFormat(template_format)
            except ValueError:
                raise ValueError(f"Unknown template format: {template_format}")

            if fmt == TemplateFormat.AUTO:
                fmt = TemplateFormat(cls.detect_format(raw_text))

            parser = cls.get_parser(fmt)

        try:
            v_style = VariableStyle(variable_style)
        except ValueError:
            raise ValueError(f"Unknown variable style: {variable_style}")

        preamble, sections, epilogue = parser.parse(raw_text, variable_style=v_style)

        composer = cls(variable_style=v_style, preamble=preamble, epilogue=epilogue)
        for section in sections:
            composer._sections[section.name] = section
        return composer

    @staticmethod
    def detect_format(text: str) -> str:
        """Detect template format based on content analysis."""
        trimmed = text.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            return "json"
        if "sections:" in text or "preamble:" in text or "epilogue:" in text:
            return "yaml"
        
        # Check for Markdown headings using optimized substring searches
        for prefix in ("# ", "## ", "### ", "#### ", "##### ", "###### "):
            if text.startswith(prefix) or f"\n{prefix}" in text:
                return "markdown"
        return "xml"

    @staticmethod
    def get_parser(fmt: TemplateFormat) -> BaseParser:
        """Get the parser instance corresponding to the given format name."""
        from prompt_composer.parsers.json import JsonParser
        from prompt_composer.parsers.yaml import YamlParser
        from prompt_composer.parsers.xml import XmlParser
        from prompt_composer.parsers.markdown import MarkdownParser

        parsers = {
            TemplateFormat.JSON: JsonParser(),
            TemplateFormat.YAML: YamlParser(),
            TemplateFormat.XML: XmlParser(),
            TemplateFormat.MARKDOWN: MarkdownParser(),
        }
        if fmt not in parsers:
            raise ValueError(f"Unknown template format: {fmt}")
        return parsers[fmt]

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
        self._section_variables.pop(name, None)
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

    # --- Variable Management ---

    def set_variable(self, key: str, value: Any) -> "PromptComposer":
        """Set a global template variable."""
        self._global_variables[key] = value
        return self

    def set_variables(self, variables: Dict[str, Any]) -> "PromptComposer":
        """Set multiple global template variables at once."""
        for key, value in variables.items():
            self._global_variables[key] = value
        return self

    def set_section_variable(self, section_name: str, key: str, value: Any) -> "PromptComposer":
        """Set a template variable scoped to a specific section."""
        if section_name not in self._section_variables:
            self._section_variables[section_name] = {}
        self._section_variables[section_name][key] = value
        return self

    def get_all_variables(self) -> List[str]:
        """List all variable names found across all sections."""
        all_vars: set[str] = set()
        for section in self._sections.values():
            all_vars.update(section.get_variables(self._variable_style))
        return sorted(all_vars)

    def get_unresolved_variables(self) -> List[str]:
        """List variable names that have not been set (global or section-scoped)."""
        all_vars = set(self.get_all_variables())
        resolved: set[str] = set(self._global_variables.keys())
        for section_variables in self._section_variables.values():
            resolved.update(section_variables.keys())
        return sorted(all_vars - resolved)

    # --- Filter Management ---

    def register_filter(self, name: str, func: Callable[[Any], str]) -> "PromptComposer":
        """Register a custom filter for template values."""
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

    def render(self, output_format: Optional[Union[str, OutputFormat]] = None) -> str:
        """Render the full prompt by concatenating all sections with variables filled."""
        parts: List[str] = []

        if self._preamble.strip():
            parts.append(self._apply_variables_to_text(self._preamble))

        try:
            out_fmt = OutputFormat(output_format) if output_format is not None else None
        except ValueError:
            raise ValueError(f"Unknown output format: {output_format}")

        for name, section in self._sections.items():
            merged_vars = dict(self._global_variables)
            if name in self._section_variables:
                merged_vars.update(self._section_variables[name])

            if not section.should_render(merged_vars):
                continue

            rendered = section.render(
                merged_vars,
                self._variable_style,
                self._filters,
                output_format=out_fmt,
            )
            parts.append(rendered)

        if self._epilogue.strip():
            parts.append(self._apply_variables_to_text(self._epilogue))

        return "\n\n".join(parts)

    def _apply_variables_to_text(self, text: str) -> str:
        """Helper to apply variables directly to preamble/epilogue."""
        dummy_section = PromptSection(name="dummy", content=text, tag_wrap=False)
        return dummy_section.render(self._global_variables, self._variable_style, self._filters)

    def __repr__(self) -> str:
        sections = self.list_sections()
        unresolved = self.get_unresolved_variables()
        return (
            f"PromptComposer(sections={sections}, "
            f"unresolved_variables={unresolved}, variable_style='{self._variable_style.value}')"
        )
