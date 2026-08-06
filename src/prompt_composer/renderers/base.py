from collections.abc import Callable
from typing import Protocol


class TemplateRenderer(Protocol):
    """Protocol for all template rendering engines."""

    def render(
        self,
        text: str,
        variables: dict[str, object],
        filters: dict[str, Callable[[object], str]],
    ) -> str:
        """
        Render the template text with variables and custom filters.

        Args:
            text: Raw template string.
            variables: Dict of variables to format/substitute.
            filters: Dict of registered filter functions.

        Returns:
            Rendered string.
        """
        ...
