"""Enums for PromptComposer formats and styles."""

from enum import StrEnum


class TemplateFormat(StrEnum):
    """Supported template file/string formats."""

    AUTO = "auto"
    JSON = "json"
    JSON_COMPACT = "json-compact"
    JSON_PRETTY = "json-pretty"
    YAML = "yaml"
    XML = "xml"
    MARKDOWN = "markdown"
    BAML = "baml"
    TOML = "toml"
    TOON = "toon"
    HCL = "hcl"


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
