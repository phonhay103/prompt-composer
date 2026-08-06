"""Format registry initialization and DI registration."""

from typing import Dict
from prompt_composer.formats.base import FormatHandler
from prompt_composer.formats.json.handler import JsonHandler
from prompt_composer.formats.yaml.handler import YamlHandler
from prompt_composer.formats.xml.handler import XmlHandler
from prompt_composer.formats.markdown.handler import MarkdownHandler
from prompt_composer.formats.baml.handler import BamlHandler
from prompt_composer.formats.toml.handler import TomlHandler
from prompt_composer.formats.toon.handler import ToonHandler


class FormatRegistry:
    """Dependency Injection registry for prompt template format handlers."""

    _handlers: Dict[str, FormatHandler] = {}

    @classmethod
    def register(cls, fmt: str, handler: FormatHandler) -> None:
        """Register a format handler."""
        cls._handlers[fmt] = handler

    @classmethod
    def get(cls, fmt: str) -> FormatHandler:
        """Get a registered format handler."""
        handler = cls._handlers.get(fmt)
        if not handler:
            raise ValueError(f"No handler registered for template format: {fmt}")
        return handler


# Register default format slices (Dependency Injection)
FormatRegistry.register("json", JsonHandler())
FormatRegistry.register("json-compact", JsonHandler())
FormatRegistry.register("json-pretty", JsonHandler())
FormatRegistry.register("yaml", YamlHandler())
FormatRegistry.register("xml", XmlHandler())
FormatRegistry.register("markdown", MarkdownHandler())
FormatRegistry.register("baml", BamlHandler())
FormatRegistry.register("toml", TomlHandler())
FormatRegistry.register("toon", ToonHandler())
