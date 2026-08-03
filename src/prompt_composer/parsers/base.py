"""Base template parser protocol/interface."""

from abc import ABC, abstractmethod
from typing import Tuple, List
from prompt_composer.section import PromptSection


class BaseParser(ABC):
    """Abstract base class for all template format parsers."""

    @abstractmethod
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
        pass
