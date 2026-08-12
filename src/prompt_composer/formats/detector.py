"""Format detection interface and default implementation."""

import pathlib
import re
from typing import Protocol, runtime_checkable

from prompt_composer.enums import TemplateFormat


@runtime_checkable
class FormatDetector(Protocol):
    """Protocol for template format detection."""

    def detect(self, text: str, filepath: pathlib.Path | None = None) -> TemplateFormat:
        """
        Detect template format based on content and/or file path.

        Args:
            text: Raw template content.
            filepath: Optional path to the template file.

        Returns:
            The TemplateFormat enum value.
        """
        ...


class DefaultFormatDetector:
    """Default implementation of FormatDetector using Magic Detector suite."""

    def __init__(self) -> None:
        try:
            from magic_detector import MagicDetectorSuite
            self._suite = MagicDetectorSuite()
        except ImportError:
            self._suite = None

    def detect(self, text: str, filepath: pathlib.Path | None = None) -> TemplateFormat:
        # Use advanced detection if magic_detector suite is available
        if self._suite:
            try:
                # Pass both buffer and file_name, MagicSuite automatically prioritizes 
                # extension-based and heuristic checks under the hood
                file_name = filepath.name if filepath else None
                result = self._suite.detect_normalized(
                    text.encode("utf-8"), 
                    file_name=file_name,
                    use_parallel=True
                )
                
                ext = result.extension
                if ext:
                    ext = ext.lower()
                    if ext in ("yml", "yaml"):
                        return TemplateFormat.YAML
                    if ext in ("md", "markdown"):
                        return TemplateFormat.MARKDOWN
                    try:
                        return TemplateFormat(ext)
                    except ValueError:
                        pass
            except Exception:
                pass

        # Fallback for plain text detection (when magic_detector fails or is not installed)
        if filepath is not None:
            suffix = filepath.suffix.lower()
            if suffix == ".json": return TemplateFormat.JSON
            if suffix in (".yaml", ".yml"): return TemplateFormat.YAML
            if suffix in (".md", ".markdown"): return TemplateFormat.MARKDOWN
            if suffix == ".xml": return TemplateFormat.XML
            if suffix == ".baml": return TemplateFormat.BAML
            if suffix == ".toml": return TemplateFormat.TOML
            if suffix == ".toon": return TemplateFormat.TOON
            if suffix == ".hcl": return TemplateFormat.HCL
        trimmed = text.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"): return TemplateFormat.JSON
        if re.search(r'\bsection\s+"[^"]+"\s*\{', text) or "preamble = " in text: return TemplateFormat.HCL
        if "sections:" in text or "preamble:" in text or "epilogue:" in text: return TemplateFormat.YAML
        if re.search(r"\bfunction\s+\w+\s*\(", text) and re.search(r'\bprompt\s*#"', text): return TemplateFormat.BAML
        if "[[sections]]" in text or "[metadata]" in text: return TemplateFormat.TOML
        if "]{" in text or re.search(r"\w+\[\d+[^\]]*\]:", text): return TemplateFormat.TOON
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                parts = stripped.split(maxsplit=1)
                if parts and all(c == "#" for c in parts[0]): return TemplateFormat.MARKDOWN

        return TemplateFormat.XML


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
