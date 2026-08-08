"""YAML template format handler implementation."""

from typing import Any, override

import yaml

from prompt_composer.formats.base import FormatHandler
from prompt_composer.section import PromptSection


class YamlHandler(FormatHandler):
    """Parses and serializes prompt templates in YAML format."""

    @override
    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> tuple[str, list[PromptSection], str, dict[str, Any]]:
        docs = list(yaml.safe_load_all(text))
        docs = [doc for doc in docs if doc is not None]

        metadata: dict[str, Any] = {}
        data: dict[str, Any] = {}

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
        sections: list[PromptSection] = []

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

    @override
    def serialize(
        self,
        preamble: str,
        sections: list[PromptSection],
        epilogue: str,
        metadata: dict[str, Any],
        **kwargs
    ) -> str:
        data = {}
        if preamble:
            data["preamble"] = preamble
        if epilogue:
            data["epilogue"] = epilogue
        if metadata:
            data["metadata"] = metadata

        sec_list = []
        for sec in sections:
            item = {
                "name": sec.name,
                "content": sec.content if isinstance(sec.content, str) else "",
                "tag_wrap": sec.tag_wrap,
            }
            if sec.condition is not None:
                item["condition"] = sec.condition
            sec_list.append(item)
        if sec_list:
            data["sections"] = sec_list

        return yaml.safe_dump(data, sort_keys=False)
