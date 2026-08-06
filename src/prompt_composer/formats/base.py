"""Base template format handler protocol."""

from typing import Tuple, List, Dict, Any, Protocol, runtime_checkable
from prompt_composer.section import PromptSection


@runtime_checkable
class FormatHandler(Protocol):
    """Protocol for all template format handlers (parsing and serialization)."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> Tuple[str, List[PromptSection], str, Dict[str, Any]]:
        """
        Parse raw template text into components.

        Args:
            text: Raw template text.
            variable_style: Delimiter format for variable placeholders.

        Returns:
            A tuple of (preamble, list of PromptSections, epilogue, metadata).
        """
        ...

    def serialize(
        self,
        preamble: str,
        sections: List[PromptSection],
        epilogue: str,
        metadata: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Serialize template components back into format-specific string.

        Args:
            preamble: Preamble text.
            sections: List of PromptSections.
            epilogue: Epilogue text.
            metadata: Metadata dictionary.
            **kwargs: Format-specific serialization options.

        Returns:
            Serialized template string.
        """
        ...
