"""XML template parser implementation using regex-free scanner."""

from typing import Tuple, List
from prompt_composer.parsers.base import BaseParser
from prompt_composer.section import PromptSection


class XmlParser(BaseParser):
    """Parses prompt templates in XML format using tag scanner."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> Tuple[str, List[PromptSection], str]:
        sections: List[PromptSection] = []
        preamble = ""
        epilogue = ""

        i = 0
        n = len(text)
        last_end = 0

        while i < n:
            start_open = text.find("<", i)
            if start_open == -1:
                break
            end_open = text.find(">", start_open)
            if end_open == -1:
                break

            tag_name = text[start_open + 1 : end_open].strip()
            if tag_name.startswith("/") or not tag_name.replace("_", "").isalnum():
                i = start_open + 1
                continue

            close_tag = f"</{tag_name}>"
            start_close = text.find(close_tag, end_open + 1)
            if start_close == -1:
                i = start_open + 1
                continue

            content = text[end_open + 1 : start_close].strip()

            if not sections:
                preamble = text[last_end:start_open].strip()

            sections.append(
                PromptSection(name=tag_name, content=content, tag_wrap=True)
            )
            last_end = start_close + len(close_tag)
            i = last_end

        if not sections:
            preamble = text.strip()
        else:
            epilogue = text[last_end:].strip()

        return preamble, sections, epilogue
