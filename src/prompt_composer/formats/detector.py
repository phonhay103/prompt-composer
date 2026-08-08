"""Format detection interface and default implementation."""

import pathlib
import re
from typing import Protocol, runtime_checkable


@runtime_checkable
class FormatDetector(Protocol):
    """Protocol for template format detection."""

    def detect(self, text: str, filepath: pathlib.Path | None = None) -> str:
        """
        Detect template format based on content and/or file path.

        Args:
            text: Raw template content.
            filepath: Optional path to the template file.

        Returns:
            The format name (e.g. "json", "yaml", "xml", etc.)
        """
        ...


class DefaultFormatDetector:
    """Default implementation of FormatDetector using extension mapping and regex content analysis."""

    def detect(self, text: str, filepath: pathlib.Path | None = None) -> str:
        if filepath is not None:
            suffix = filepath.suffix.lower()
            if suffix == ".json":
                return "json"
            if suffix in (".yaml", ".yml"):
                return "yaml"
            if suffix in (".md", ".markdown"):
                return "markdown"
            if suffix == ".xml":
                return "xml"
            if suffix == ".baml":
                return "baml"
            if suffix == ".toml":
                return "toml"
            if suffix == ".toon":
                return "toon"
            if suffix == ".hcl":
                return "hcl"

        # Content analysis fallback
        trimmed = text.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            return "json"

        # Check for HCL sections
        if re.search(r'\bsection\s+"[^"]+"\s*\{', text) or "preamble = " in text:
            return "hcl"

        if "sections:" in text or "preamble:" in text or "epilogue:" in text:
            return "yaml"

        # Check for BAML function and prompt pattern
        if re.search(r"\bfunction\s+\w+\s*\(", text) and re.search(r'\bprompt\s*#"', text):
            return "baml"

        # Check for TOML tables
        if "[[sections]]" in text or "[metadata]" in text:
            return "toml"

        # Check for TOON format patterns
        if "]{" in text or re.search(r"\w+\[\d+[^\]]*\]:", text):
            return "toon"

        # Check for Markdown headings (allowing leading indentation)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                parts = stripped.split(maxsplit=1)
                if parts and all(c == "#" for c in parts[0]):
                    return "markdown"

        return "xml"


class FormatDetectorRegistry:
    """Dependency Injection registry for template format detectors."""

    _default_detector: FormatDetector = DefaultFormatDetector()

    @classmethod
    def get_default(cls) -> FormatDetector:
        """Get the active default format detector."""
        return cls._default_detector

    @classmethod
    def set_default(cls, detector: FormatDetector) -> None:
        """Set the active default format detector."""
        cls._default_detector = detector
