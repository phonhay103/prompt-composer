"""TOML template parser implementation."""

import tomllib

from typing import Tuple, List, Dict, Any
from prompt_composer.parsers.base import BaseParser
from prompt_composer.section import PromptSection


class TomlParser(BaseParser):
    """Parses prompt templates in TOML format."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> Tuple[str, List[PromptSection], str, Dict[str, Any]]:
        data = tomllib.loads(text)
        metadata = data.pop("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        preamble = data.get("preamble", "")
        epilogue = data.get("epilogue", "")
        sections: List[PromptSection] = []

        for item in data.get("sections", []):
            name = item["name"]
            content = item["content"]
            tag_wrap = item.get("tag_wrap", True)
            condition = item.get("condition", None)
            sections.append(
                PromptSection(
                    name=name, content=content, tag_wrap=tag_wrap, condition=condition
                )
            )

        return preamble, sections, epilogue, metadata
