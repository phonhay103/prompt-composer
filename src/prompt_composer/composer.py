"""PromptComposer — Structured prompt manager with sections and slot variables."""

import pathlib
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, override

from prompt_composer.enums import OutputFormat, TemplateFormat, VariableStyle
from prompt_composer.filters import DEFAULT_FILTERS
from prompt_composer.formats import FormatDetector, FormatDetectorRegistry, FormatRegistry
from prompt_composer.renderers import RendererRegistry
from prompt_composer.section import PromptSection


class PromptComposer:
    def __init__(
        self,
        sections: list[PromptSection] | None = None,
        preamble: str = "",
        epilogue: str = "",
        variable_style: str | VariableStyle = VariableStyle.BRACES,
        metadata: dict[str, Any] | None = None,
        renderer_name: str | None = None,
    ) -> None:
        self._sections: OrderedDict[str, PromptSection] = OrderedDict()
        self._global_variables: dict[str, Any] = {}
        self._section_variables: dict[str, dict[str, Any]] = {}
        self._preamble: str = preamble
        self._epilogue: str = epilogue
        self._filters: dict[str, Callable[[Any], str]] = dict(DEFAULT_FILTERS)
        self._metadata: dict[str, Any] = metadata or {}

        try:
            self._variable_style: VariableStyle = VariableStyle(variable_style)
        except ValueError:
            raise ValueError(f"Unknown variable style: {variable_style}") from None

        if renderer_name is not None:
            self._renderer_name = renderer_name
        else:
            if self._variable_style == VariableStyle.JINJA:
                self._renderer_name = "jinja"
            elif self._variable_style == VariableStyle.DOUBLE_BRACES:
                self._renderer_name = "simple_double_braces"
            else:
                self._renderer_name = "simple_braces"

        if sections is not None:
            for section in sections:
                self._sections[section.name] = section

    @property
    def metadata(self) -> dict[str, Any]:
        """Get the prompt metadata."""
        return self._metadata

    @metadata.setter
    def metadata(self, val: dict[str, Any]) -> None:
        """Set the prompt metadata."""
        self._metadata = val or {}

    # --- Factory Methods ---

    @classmethod
    def from_remote(
        cls,
        provider: Any,
        name: str,
        version: str | None = None,
        variable_style: str | VariableStyle = VariableStyle.BRACES,
        template_format: str | TemplateFormat = TemplateFormat.AUTO,
        renderer_name: str | None = None,
        **kwargs,
    ) -> "PromptComposer":
        """
        Fetch a template from a remote registry provider and return an initialized PromptComposer.
        """
        from prompt_composer.remote.composer import RemotePromptFormatter

        formatter = RemotePromptFormatter.from_remote(
            provider=provider,
            name=name,
            version=version,
            variable_style=variable_style,
            template_format=template_format,
            renderer_name=renderer_name,
            **kwargs,
        )
        return formatter.composer

    @classmethod
    def from_file(
        cls,
        filename: str,
        prompts_dir: pathlib.Path,
        template_format: str | TemplateFormat = TemplateFormat.AUTO,
        variable_style: str | VariableStyle = VariableStyle.BRACES,
        parser: Any | None = None,
        renderer_name: str | None = None,
        detector: FormatDetector | None = None,
    ) -> "PromptComposer":
        """
        Load a template file and parse it into sections.
        Automatically detects template format based on file extension and contents.
        """
        filepath = prompts_dir / filename
        with open(filepath, encoding="utf-8") as f:
            raw_text = f.read()

        if parser is None:
            try:
                fmt = TemplateFormat(template_format)
            except ValueError:
                raise ValueError(f"Unknown template format: {template_format}") from None

            if fmt == TemplateFormat.AUTO:
                active_detector = detector or FormatDetectorRegistry.get_default()
                fmt = TemplateFormat(active_detector.detect(raw_text, filepath))
        else:
            fmt = template_format

        try:
            v_style = VariableStyle(variable_style)
        except ValueError:
            raise ValueError(f"Unknown variable style: {variable_style}") from None

        return cls.from_text(
            raw_text,
            template_format=fmt,
            variable_style=v_style,
            parser=parser,
            renderer_name=renderer_name,
            detector=detector,
        )

    @classmethod
    def from_text(
        cls,
        raw_text: str,
        template_format: str | TemplateFormat = TemplateFormat.AUTO,
        variable_style: str | VariableStyle = VariableStyle.BRACES,
        parser: Any | None = None,
        renderer_name: str | None = None,
        detector: FormatDetector | None = None,
    ) -> "PromptComposer":
        """Parse raw prompt text into sections."""
        if parser is None:
            try:
                fmt = TemplateFormat(template_format)
            except ValueError:
                raise ValueError(f"Unknown template format: {template_format}") from None

            if fmt == TemplateFormat.AUTO:
                active_detector = detector or FormatDetectorRegistry.get_default()
                fmt = TemplateFormat(active_detector.detect(raw_text))

            parser = cls.get_parser(fmt)

        try:
            v_style = VariableStyle(variable_style)
        except ValueError:
            raise ValueError(f"Unknown variable style: {variable_style}") from None

        parsed = parser.parse(raw_text, variable_style=v_style)
        if len(parsed) == 4:
            preamble, sections, epilogue, metadata = parsed
        else:
            preamble, sections, epilogue = parsed
            metadata = {}

        composer = cls(
            variable_style=v_style,
            preamble=preamble,
            epilogue=epilogue,
            metadata=metadata,
            renderer_name=renderer_name,
        )
        for section in sections:
            composer._sections[section.name] = section
        return composer

    @staticmethod
    def detect_format(text: str) -> TemplateFormat:
        """Detect template format based on content analysis using the default format detector."""
        return FormatDetectorRegistry.get_default().detect(text)

    @staticmethod
    def get_parser(fmt: TemplateFormat) -> Any:
        """Get the parser instance corresponding to the given format name."""
        return FormatRegistry.get(fmt.value)

    # --- Section Management ---

    def set_section(
        self,
        name: str,
        content: str | Callable[[dict[str, Any]], str],
        tag_wrap: bool | str = True,
        position: int | None = None,
        condition: str | Callable[[dict[str, Any]], bool] | None = None,
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

    def get_section(self, name: str) -> PromptSection | None:
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

    def list_sections(self) -> list[str]:
        """List all section names in order."""
        return list(self._sections.keys())

    # --- Common Section Helpers ---

    def set_role(
        self,
        content: str | Callable[[dict[str, Any]], str],
        tag_wrap: bool | str = True,
        condition: str | Callable[[dict[str, Any]], bool] | None = None,
    ) -> "PromptComposer":
        """Set the 'role' section."""
        return self.set_section("role", content, tag_wrap=tag_wrap, condition=condition)

    def set_tools(
        self,
        content: str | Callable[[dict[str, Any]], str],
        tag_wrap: bool | str = True,
        condition: str | Callable[[dict[str, Any]], bool] | None = None,
    ) -> "PromptComposer":
        """Set the 'tools' section."""
        return self.set_section("tools", content, tag_wrap=tag_wrap, condition=condition)

    def set_rules(
        self,
        content: str | Callable[[dict[str, Any]], str],
        tag_wrap: bool | str = True,
        condition: str | Callable[[dict[str, Any]], bool] | None = None,
    ) -> "PromptComposer":
        """Set the 'rules' section."""
        return self.set_section("rules", content, tag_wrap=tag_wrap, condition=condition)

    def set_instructions(
        self,
        content: str | Callable[[dict[str, Any]], str],
        tag_wrap: bool | str = True,
        condition: str | Callable[[dict[str, Any]], bool] | None = None,
    ) -> "PromptComposer":
        """Set the 'instructions' section."""
        return self.set_section("instructions", content, tag_wrap=tag_wrap, condition=condition)

    def set_context(
        self,
        content: str | Callable[[dict[str, Any]], str],
        tag_wrap: bool | str = True,
        condition: str | Callable[[dict[str, Any]], bool] | None = None,
    ) -> "PromptComposer":
        """Set the 'context' section."""
        return self.set_section("context", content, tag_wrap=tag_wrap, condition=condition)

    # --- Variable Management ---

    def set_variable(self, key: str, value: Any) -> "PromptComposer":
        """Set a global template variable."""
        self._global_variables[key] = value
        return self

    def set_variables(self, variables: dict[str, Any]) -> "PromptComposer":
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

    def get_all_variables(self) -> list[str]:
        """List all variable names found across all sections."""
        all_vars: set[str] = set()
        for section in self._sections.values():
            all_vars.update(section.get_variables(self._variable_style))
        return sorted(all_vars)

    def get_unresolved_variables(self) -> list[str]:
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

    def list_filters(self) -> list[str]:
        """List all registered filter names."""
        return list(self._filters.keys())

    def get_filter(self, name: str) -> Callable[[Any], str] | None:
        """Get a registered filter by name."""
        return self._filters.get(name)

    def has_filter(self, name: str) -> bool:
        """Check if a filter exists."""
        return name in self._filters

    # --- Rendering ---

    def render(self, output_format: str | OutputFormat | None = None) -> str:
        """Render the full prompt by concatenating all sections with variables filled."""
        parts: list[str] = []

        if self._preamble.strip():
            parts.append(self._apply_variables_to_text(self._preamble))

        try:
            out_fmt = OutputFormat(output_format) if output_format is not None else None
        except ValueError:
            raise ValueError(f"Unknown output format: {output_format}") from None

        renderer = RendererRegistry.get(self._renderer_name)

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
                renderer=renderer,
            )
            parts.append(rendered)

        if self._epilogue.strip():
            parts.append(self._apply_variables_to_text(self._epilogue))

        return "\n\n".join(parts)

    def _apply_variables_to_text(self, text: str) -> str:
        """Helper to apply variables directly to preamble/epilogue."""
        dummy_section = PromptSection(name="dummy", content=text, tag_wrap=False)
        return dummy_section.render(
            self._global_variables,
            self._variable_style,
            self._filters,
            renderer=RendererRegistry.get(self._renderer_name),
        )

    @override
    def __repr__(self) -> str:
        sections = self.list_sections()
        unresolved = self.get_unresolved_variables()
        return (
            f"PromptComposer(sections={sections}, "
            f"unresolved_variables={unresolved}, variable_style='{self._variable_style.value}', "
            f"metadata={self._metadata})"
        )

    def serialize(self, fmt: str | TemplateFormat, **kwargs) -> str:
        """Serialize the prompt composer state back into the specified format."""
        try:
            fmt_val = TemplateFormat(fmt)
        except ValueError:
            raise ValueError(f"Unknown format: {fmt}") from None

        handler_key = fmt_val.value
        if handler_key in ("json-compact", "json-pretty"):
            handler = FormatRegistry.get("json")
            kwargs["format"] = handler_key
        else:
            handler = FormatRegistry.get(handler_key)

        return handler.serialize(
            preamble=self._preamble,
            sections=list(self._sections.values()),
            epilogue=self._epilogue,
            metadata=self._metadata,
            **kwargs,
        )
