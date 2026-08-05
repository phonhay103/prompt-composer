"""YAML template parser implementation."""

from typing import Tuple, List, Dict, Any
from prompt_composer.parsers.base import BaseParser
from prompt_composer.section import PromptSection


class YamlParser(BaseParser):
    """Parses prompt templates in YAML format."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> Tuple[str, List[PromptSection], str, Dict[str, Any]]:
        import yaml

        docs = list(yaml.safe_load_all(text))
        docs = [doc for doc in docs if doc is not None]

        metadata: Dict[str, Any] = {}
        data: Dict[str, Any] = {}

        if len(docs) > 1:
            metadata = docs[0]
            if not isinstance(metadata, dict):
                metadata = {}
            data = docs[1] if isinstance(docs[1], dict) else {}
        elif len(docs) == 1:
            data = docs[0] if isinstance(docs[0], dict) else {}
            if "metadata" in data and isinstance(data["metadata"], dict):
                metadata = data.pop("metadata")

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
