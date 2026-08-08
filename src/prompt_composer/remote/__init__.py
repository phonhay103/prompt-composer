"""Remote prompt registry module initialization."""

from typing import ClassVar

from prompt_composer.remote.base import RemotePromptData, RemotePromptProvider, RemoteTransport
from prompt_composer.remote.composer import RemotePromptFormatter
from prompt_composer.remote.providers import InMemoryProvider, LangfuseProvider
from prompt_composer.remote.transport import UrllibRemoteTransport


class RemoteProviderRegistry:
    """Registry to register and retrieve remote provider instances or classes."""

    _providers: ClassVar[dict[str, RemotePromptProvider]] = {}
    _provider_classes: ClassVar[dict[str, type[RemotePromptProvider]]] = {}

    @classmethod
    def register(cls, name: str, provider: RemotePromptProvider) -> None:
        """Register a remote provider instance."""
        cls._providers[name] = provider

    @classmethod
    def register_class(cls, name: str, provider_cls: type[RemotePromptProvider]) -> None:
        """Register a remote provider class."""
        cls._provider_classes[name] = provider_cls

    @classmethod
    def get(cls, name: str, **kwargs) -> RemotePromptProvider:
        """Get a registered remote provider instance, or instantiate its class with kwargs."""
        if name in cls._providers:
            return cls._providers[name]
        if name in cls._provider_classes:
            return cls._provider_classes[name](**kwargs)
        raise ValueError(f"No remote provider registered with name: {name}")


# Register default classes
RemoteProviderRegistry.register_class("langfuse", LangfuseProvider)
RemoteProviderRegistry.register_class("in_memory", InMemoryProvider)

__all__ = [
    "InMemoryProvider",
    "LangfuseProvider",
    "RemotePromptData",
    "RemotePromptFormatter",
    "RemotePromptProvider",
    "RemoteProviderRegistry",
    "RemoteTransport",
    "UrllibRemoteTransport",
]
