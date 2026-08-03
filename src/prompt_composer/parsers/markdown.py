"""Markdown template parser implementation."""

from typing import Tuple, List, Optional
from prompt_composer.parsers.base import BaseParser
from prompt_composer.section import PromptSection


class MarkdownParser(BaseParser):
    """Parses prompt templates in Markdown format using headings as section dividers."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> Tuple[str, List[PromptSection], str]:
        lines = text.splitlines()
        preamble_lines: List[str] = []
        sections: List[PromptSection] = []

        current_section_name: Optional[str] = None
        current_tag_wrap: Optional[str] = None
        current_content_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            is_heading = False

            if stripped.startswith("#"):
                parts = stripped.split(maxsplit=1)
                if parts and all(c == "#" for c in parts[0]):
                    is_heading = True
                    heading_prefix = parts[0]
                    heading_title = parts[1].strip() if len(parts) > 1 else ""

            if is_heading:
                if current_section_name is not None:
                    content = "\n".join(current_content_lines).strip()
                    sections.append(
                        PromptSection(
                            name=current_section_name,
                            content=content,
                            tag_wrap=current_tag_wrap,
                        )
                    )
                    current_content_lines = []
                current_section_name = heading_title
                current_tag_wrap = stripped
            else:
                if current_section_name is not None:
                    current_content_lines.append(line)
                else:
                    preamble_lines.append(line)

        if current_section_name is not None:
            content = "\n".join(current_content_lines).strip()
            sections.append(
                PromptSection(
                    name=current_section_name,
                    content=content,
                    tag_wrap=current_tag_wrap,
                )
            )

        preamble = "\n".join(preamble_lines).strip()
        return preamble, sections, ""
