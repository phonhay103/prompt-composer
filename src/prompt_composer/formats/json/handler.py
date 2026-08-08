"""JSON template format handler implementation."""

import json
from typing import Any, override

from prompt_composer.formats.base import FormatHandler
from prompt_composer.section import PromptSection


class JsonHandler(FormatHandler):
    """Parses and serializes prompt templates in JSON format."""

    @override
    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> tuple[str, list[PromptSection], str, dict[str, Any]]:
        data = json.loads(text)
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

        data = {}
        if preamble:
            data["preamble"] = preamble
        if epilogue:
            data["epilogue"] = epilogue
        if metadata:
            data["metadata"] = metadata
        if sec_list:
            data["sections"] = sec_list

        compact = kwargs.get("compact", False)
        fmt = kwargs.get("format", "")
        if fmt == "json-compact":
            compact = True
        elif fmt == "json-pretty":
            compact = False

        if compact:
            return json.dumps(data, separators=(',', ':'))
        else:
            return json.dumps(data, indent=2)
