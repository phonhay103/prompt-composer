import contextlib
from typing import Any

from prompt_composer.composer import PromptComposer
from prompt_composer.enums import OutputFormat, TemplateFormat, VariableStyle
from prompt_composer.remote.base import RemotePromptProvider


class RemotePromptFormatter:
    """Orchestrates fetching a template from a remote registry and formatting it using PromptComposer."""

    def __init__(self, composer: PromptComposer) -> None:
        self.composer = composer

    @classmethod
    def from_remote(
        cls,
        provider: RemotePromptProvider,
        name: str,
        version: str | None = None,
        variable_style: str | VariableStyle = VariableStyle.BRACES,
        template_format: str | TemplateFormat | None = None,
        renderer_name: str | None = None,
        **kwargs,
    ) -> "RemotePromptFormatter":
        """
        Factory method to fetch, parse, and initialize the formatter.

        Args:
            provider: RemotePromptProvider instance.
            name: The name of the prompt.
            version: Optional version tag or number.
            variable_style: The variable style to use for interpolation.
            template_format: Explicit template format. If omitted, the provider's
                ``RemotePromptData.format`` is used. Auto-detection is not supported,
                so a ``ValueError`` is raised when neither yields a concrete format.
            renderer_name: The name of the template renderer engine.
            **kwargs: Extra parameters to pass to the provider's fetch_prompt method.
        """
        prompt_data = provider.fetch_prompt(name, version=version, **kwargs)

        v_style = variable_style
        if prompt_data.variable_style and variable_style == VariableStyle.BRACES:
            with contextlib.suppress(ValueError):
                v_style = VariableStyle(prompt_data.variable_style)

        # Resolve the format explicitly: caller override wins, else provider metadata.
        t_fmt: str | TemplateFormat | None = template_format if template_format is not None else prompt_data.format
        if t_fmt is None or t_fmt in ("", "auto"):
            raise ValueError(
                "Remote prompt format must be explicit; got 'auto'/missing. "
                "Pass template_format=... or set RemotePromptData.format."
            )

        composer = PromptComposer.from_text(
            raw_text=prompt_data.template,
            template_format=t_fmt,
            variable_style=v_style,
            renderer_name=renderer_name,
        )

        if prompt_data.default_variables:
            composer.set_variables(prompt_data.default_variables)

        if prompt_data.metadata:
            composer.metadata.update(prompt_data.metadata)

        return cls(composer)

    def format(
        self,
        variables: dict[str, Any] | None = None,
        output_format: str | OutputFormat | None = None,
    ) -> str:
        """
        Apply variables and format/render the prompt.

        Args:
            variables: Variables to bind before rendering.
            output_format: Optional forced output formatting (e.g. XML, Markdown).
        """
        if variables is not None:
            self.composer.set_variables(variables)
        return self.composer.render(output_format=output_format)
