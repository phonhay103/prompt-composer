"""TOML template format handler implementation."""

import tomllib
from typing import Any, override

from prompt_composer.formats.base import FormatHandler
from prompt_composer.section import PromptSection


class TomlHandler(FormatHandler):
    """Parses and serializes prompt templates in TOML format."""

    @override
    def parse(self, text: str, variable_style: str = "braces") -> tuple[str, list[PromptSection], str, dict[str, Any]]:
        data = tomllib.loads(text)
        metadata = data.pop("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        preamble = data.get("preamble", "")
        epilogue = data.get("epilogue", "")
        sections: list[PromptSection] = []

        for item in data.get("sections", []):
            name = item["name"]
            content = item["content"]
            tag_wrap = item.get("tag_wrap", True)
            condition = item.get("condition", None)
            sections.append(PromptSection(name=name, content=content, tag_wrap=tag_wrap, condition=condition))

        return preamble, sections, epilogue, metadata

    @override
    def serialize(
        self, preamble: str, sections: list[PromptSection], epilogue: str, metadata: dict[str, Any], **kwargs
    ) -> str:
        lines = []
        if preamble:
            lines.append(f'preamble = "{self._escape_toml_str(preamble)}"')
        if epilogue:
            lines.append(f'epilogue = "{self._escape_toml_str(epilogue)}"')

        if metadata:
            lines.append("")
            lines.append("[metadata]")
            for k, v in metadata.items():
                if isinstance(v, str):
                    lines.append(f'{k} = "{self._escape_toml_str(v)}"')
                elif isinstance(v, bool):
                    lines.append(f"{k} = {str(v).lower()}")
                elif isinstance(v, (int, float)):
                    lines.append(f"{k} = {v}")
                else:
                    import json

                    lines.append(f'{k} = "{self._escape_toml_str(json.dumps(v))}"')

        if sections:
            for sec in sections:
                lines.append("")
                lines.append("[[sections]]")
                lines.append(f'name = "{self._escape_toml_str(sec.name)}"')
                content_str = sec.content if isinstance(sec.content, str) else "<callable>"
                lines.append(f'content = "{self._escape_toml_str(content_str)}"')
                lines.append(f"tag_wrap = {str(sec.tag_wrap).lower()}")
                if sec.condition is not None:
                    cond_str = sec.condition if isinstance(sec.condition, str) else "<callable>"
                    lines.append(f'condition = "{self._escape_toml_str(cond_str)}"')

        return "\n".join(lines)

    def _escape_toml_str(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
