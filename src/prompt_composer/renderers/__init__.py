from typing import ClassVar

from prompt_composer.renderers.base import TemplateRenderer
from prompt_composer.renderers.jinja import JinjaTemplateRenderer
from prompt_composer.renderers.simple import SimpleTemplateRenderer


class RendererRegistry:
    """Registry to register and fetch template rendering engines."""

    _renderers: ClassVar[dict[str, TemplateRenderer]] = {}

    @classmethod
    def register(cls, name: str, renderer: TemplateRenderer) -> None:
        """Register a template renderer engine."""
        cls._renderers[name] = renderer

    @classmethod
    def get(cls, name: str) -> TemplateRenderer:
        """Get a registered template renderer engine."""
        if name not in cls._renderers:
            raise ValueError(f"No template renderer registered with name: {name}")
        return cls._renderers[name]


# Register default renderers
RendererRegistry.register("simple_braces", SimpleTemplateRenderer("braces"))
RendererRegistry.register("simple_double_braces", SimpleTemplateRenderer("double_braces"))
RendererRegistry.register("jinja", JinjaTemplateRenderer())
