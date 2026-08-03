"""YAML template parser implementation."""

from typing import Tuple, List
from prompt_composer.parsers.base import BaseParser
from prompt_composer.section import PromptSection


class YamlParser(BaseParser):
    """Parses prompt templates in YAML format."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> Tuple[str, List[PromptSection], str]:
        import yaml

        data = yaml.safe_load(text) or {}
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

        return preamble, sections, epilogue
