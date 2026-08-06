"""JSON template format handler implementation."""

import json
from typing import Tuple, List, Dict, Any
from prompt_composer.formats.base import FormatHandler
from prompt_composer.section import PromptSection


class JsonHandler(FormatHandler):
    """Parses and serializes prompt templates in JSON format."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> Tuple[str, List[PromptSection], str, Dict[str, Any]]:
        data = json.loads(text)
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

    def serialize(
        self,
        preamble: str,
        sections: List[PromptSection],
        epilogue: str,
        metadata: Dict[str, Any],
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
