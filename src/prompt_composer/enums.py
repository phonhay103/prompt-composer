"""Enums for PromptComposer formats and styles."""

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum
    class StrEnum(str, Enum):
        pass


class TemplateFormat(StrEnum):
    """Supported template file/string formats."""
    AUTO = "auto"
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    MARKDOWN = "markdown"
    BAML = "baml"
    TOML = "toml"



class VariableStyle(StrEnum):
    """Delimiter styles for template variable placeholders."""
    BRACES = "braces"
    PYTHON = "python"
    DOUBLE_BRACES = "double_braces"
    JINJA = "jinja"


class OutputFormat(StrEnum):
    """Forced output formats when rendering the final prompt."""
    XML = "xml"
    MARKDOWN = "markdown"
    MD = "md"
