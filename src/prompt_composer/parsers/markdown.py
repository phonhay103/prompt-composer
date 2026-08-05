"""Markdown template parser implementation."""

from typing import Tuple, List, Optional, Dict, Any
from prompt_composer.parsers.base import BaseParser
from prompt_composer.section import PromptSection


class MarkdownParser(BaseParser):
    """Parses prompt templates in Markdown format using headings as section dividers."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> Tuple[str, List[PromptSection], str, Dict[str, Any]]:
        import yaml

        lines = text.splitlines()
        metadata: Dict[str, Any] = {}

        if lines and lines[0].strip() == "---":
            frontmatter_lines = []
            remaining_lines = []
            in_frontmatter = True
            for line in lines[1:]:
                if in_frontmatter:
                    if line.strip() == "---":
                        in_frontmatter = False
                    else:
                        frontmatter_lines.append(line)
                else:
                    remaining_lines.append(line)
            
            if not in_frontmatter:
                frontmatter_text = "\n".join(frontmatter_lines)
                try:
                    metadata = yaml.safe_load(frontmatter_text) or {}
                    if not isinstance(metadata, dict):
                        metadata = {}
                except Exception:
                    metadata = {}
                lines = remaining_lines

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
        return preamble, sections, "", metadata
