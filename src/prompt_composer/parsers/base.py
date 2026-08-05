"""Base template parser protocol/interface."""

from typing import Tuple, List, Protocol, runtime_checkable
from prompt_composer.section import PromptSection


@runtime_checkable
class BaseParser(Protocol):
    """Protocol for all template format parsers."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> Tuple[str, List[PromptSection], str]:
        """
        Parse raw template text into components.

        Args:
            text: Raw template text.
            variable_style: Delimiter format for variable placeholders.

        Returns:
            A tuple of (preamble, list of PromptSections, epilogue).
        """
        ...

