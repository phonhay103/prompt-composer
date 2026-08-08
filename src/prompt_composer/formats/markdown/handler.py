"""Markdown template format handler implementation."""

from typing import Any, override

from prompt_composer.formats.base import FormatHandler
from prompt_composer.section import PromptSection


class MarkdownHandler(FormatHandler):
    """Parses and serializes prompt templates in Markdown format using headings as section dividers."""

    @override
    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> tuple[str, list[PromptSection], str, dict[str, Any]]:
        import yaml

        lines = text.splitlines()
        metadata: dict[str, Any] = {}

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

        preamble_lines: list[str] = []
        sections: list[PromptSection] = []

        current_section_name: str | None = None
        current_tag_wrap: str | None = None
        current_content_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            is_heading = False

            heading_title = ""
            if stripped.startswith("#"):
                parts = stripped.split(maxsplit=1)
                if parts and all(c == "#" for c in parts[0]):
                    is_heading = True
                    heading_title = parts[1].strip() if len(parts) > 1 else ""

            if is_heading:
                if current_section_name is not None:
                    content = "\n".join(current_content_lines).strip()
                    sections.append(
                        PromptSection(
                            name=current_section_name,
                            content=content,
                            tag_wrap=current_tag_wrap if current_tag_wrap is not None else True,
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
                    tag_wrap=current_tag_wrap if current_tag_wrap is not None else True,
                )
            )

        preamble = "\n".join(preamble_lines).strip()
        return preamble, sections, "", metadata

    @override
    def serialize(
        self,
        preamble: str,
        sections: list[PromptSection],
        epilogue: str,
        metadata: dict[str, Any],
        **_kwargs
    ) -> str:
        parts: list[str] = []
        if metadata:
            import yaml
            parts.append("---")
            parts.append(yaml.safe_dump(metadata, sort_keys=False).strip())
            parts.append("---")

        if preamble:
            parts.append(preamble)

        for sec in sections:
            content_str = sec.content if isinstance(sec.content, str) else "<callable>"
            if sec.tag_wrap:
                header = f"## {sec.name}"
                if isinstance(sec.tag_wrap, str) and sec.tag_wrap.startswith("#"):
                    header = sec.tag_wrap
                parts.append(f"{header}\n{content_str}")
            else:
                parts.append(content_str)

        if epilogue:
            parts.append(epilogue)

        return "\n\n".join(parts)
