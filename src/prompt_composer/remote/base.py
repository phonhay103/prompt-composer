"""Base interfaces and data structures for remote prompt registries."""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class RemotePromptData(BaseModel):
    """Standardized representation of a remote prompt template and its configuration."""

    template: str
    format: str = "auto"
    variable_style: str = "braces"
    metadata: dict[str, Any] = Field(default_factory=dict)
    default_variables: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class RemoteTransport(Protocol):
    """Protocol for making HTTP requests to remote registries."""

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an HTTP request and return the parsed JSON response."""
        ...


@runtime_checkable
class RemotePromptProvider(Protocol):
    """Protocol for fetching prompt templates from a remote service."""

    def fetch_prompt(self, name: str, version: str | None = None, **kwargs) -> RemotePromptData:
        """Fetch the prompt template and associated metadata by name."""
        ...
