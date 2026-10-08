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
        template_format: str | TemplateFormat = TemplateFormat.AUTO,
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
            template_format: The format of the prompt template (or AUTO to detect).
            renderer_name: The name of the template renderer engine.
            **kwargs: Extra parameters to pass to the provider's fetch_prompt method.
        """
        prompt_data = provider.fetch_prompt(name, version=version, **kwargs)

        v_style = variable_style
        if prompt_data.variable_style and variable_style == VariableStyle.BRACES:
            with contextlib.suppress(ValueError):
                v_style = VariableStyle(prompt_data.variable_style)

        t_fmt = template_format
        if prompt_data.format != "auto" and template_format == TemplateFormat.AUTO:
            with contextlib.suppress(ValueError):
                t_fmt = TemplateFormat(prompt_data.format)

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
