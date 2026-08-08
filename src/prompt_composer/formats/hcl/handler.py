"""HCL prompt template format handler implementation."""

import re
from typing import Any, override

from prompt_composer.formats.base import FormatHandler
from prompt_composer.section import PromptSection


class HclHandler(FormatHandler):
    """Parses and serializes prompt templates in HCL format."""

    @override
    def parse(self, text: str, variable_style: str = "braces") -> tuple[str, list[PromptSection], str, dict[str, Any]]:
        # A simple robust parser for HCL prompt configuration format
        preamble = ""
        epilogue = ""
        sections = []
        metadata = {}

        lines = text.splitlines()
        i = 0
        n = len(lines)

        def parse_value(start_idx: int) -> tuple[Any, int]:
            line = lines[start_idx].strip()
            eq_idx = line.find("=")
            if eq_idx == -1:
                return None, start_idx + 1
            val_part = line[eq_idx + 1 :].strip()

            # Check for Heredoc
            if val_part.startswith("<<"):
                strip_indent = val_part.startswith("<<-")
                marker = val_part[2:].strip("-")
                # Accumulate lines until marker
                content_lines = []
                idx = start_idx + 1
                while idx < n:
                    if lines[idx].strip() == marker:
                        break
                    content_lines.append(lines[idx])
                    idx += 1

                if strip_indent and content_lines:
                    min_indent = None
                    for item_line in content_lines:
                        stripped_item_line = item_line.lstrip()
                        if stripped_item_line:
                            indent = len(item_line) - len(stripped_item_line)
                            if min_indent is None or indent < min_indent:
                                min_indent = indent
                    if min_indent is not None and min_indent > 0:
                        content_lines = [
                            item_line[min_indent:] if len(item_line) >= min_indent else item_line.lstrip()
                            for item_line in content_lines
                        ]

                return "\n".join(content_lines), idx + 1

            # Check for quoted string
            if val_part.startswith('"') and val_part.endswith('"'):
                return val_part[1:-1].replace('\\"', '"').replace("\\n", "\n"), start_idx + 1

            # Check for boolean
            if val_part.lower() == "true":
                return True, start_idx + 1
            if val_part.lower() == "false":
                return False, start_idx + 1

            # Fallback
            return val_part, start_idx + 1

        while i < n:
            line = lines[i].strip()
            if not line or line.startswith("#") or line.startswith("//"):
                i += 1
                continue

            if line.startswith("preamble"):
                val, i = parse_value(i)
                if val is not None:
                    preamble = val
            elif line.startswith("epilogue"):
                val, i = parse_value(i)
                if val is not None:
                    epilogue = val
            elif line.startswith("section"):
                match = re.match(r'^section\s+"([^"]+)"\s*\{$', line)
                if match:
                    sec_name = match.group(1)
                    sec_content = ""
                    sec_tag_wrap = True
                    sec_condition = None
                    i += 1
                    while i < n:
                        sub_line = lines[i].strip()
                        if sub_line == "}":
                            i += 1
                            break
                        if sub_line.startswith("content"):
                            val, i = parse_value(i)
                            if val is not None:
                                sec_content = val
                        elif sub_line.startswith("tag_wrap"):
                            val, i = parse_value(i)
                            if val is not None:
                                sec_tag_wrap = val
                        elif sub_line.startswith("condition"):
                            val, i = parse_value(i)
                            if val is not None:
                                sec_condition = val
                        else:
                            i += 1
                    sections.append(
                        PromptSection(
                            name=sec_name, content=sec_content, tag_wrap=sec_tag_wrap, condition=sec_condition
                        )
                    )
                else:
                    i += 1
            elif line.startswith("metadata"):
                if line.endswith("{"):
                    i += 1
                    while i < n:
                        sub_line = lines[i].strip()
                        if sub_line == "}":
                            i += 1
                            break
                        if "=" in sub_line:
                            eq_idx = sub_line.find("=")
                            k = sub_line[:eq_idx].strip()
                            val_str = sub_line[eq_idx + 1 :].strip()
                            if val_str.startswith('"') and val_str.endswith('"'):
                                v = val_str[1:-1]
                            elif val_str.lower() == "true":
                                v = True
                            elif val_str.lower() == "false":
                                v = False
                            else:
                                v = val_str
                            metadata[k] = v
                            i += 1
                        else:
                            i += 1
                else:
                    i += 1
            else:
                i += 1

        return preamble, sections, epilogue, metadata

    @override
    def serialize(
        self, preamble: str, sections: list[PromptSection], epilogue: str, metadata: dict[str, Any], **_kwargs
    ) -> str:
        lines = []

        def format_string(s: str) -> str:
            if "\n" in s:
                return f"<<-EOF\n{s}\nEOF"
            escaped = s.replace('"', '\\"')
            return f'"{escaped}"'

        if preamble:
            lines.append(f"preamble = {format_string(preamble)}")
            lines.append("")

        for sec in sections:
            lines.append(f'section "{sec.name}" {{')
            content_str = sec.content if isinstance(sec.content, str) else "<callable>"
            lines.append(f"  content = {format_string(content_str)}")
            if isinstance(sec.tag_wrap, bool):
                lines.append(f"  tag_wrap = {str(sec.tag_wrap).lower()}")
            else:
                lines.append(f"  tag_wrap = {format_string(str(sec.tag_wrap))}")
            if sec.condition is not None:
                cond_str = sec.condition if isinstance(sec.condition, str) else "<callable>"
                lines.append(f"  condition = {format_string(cond_str)}")
            lines.append("}")
            lines.append("")

        if epilogue:
            lines.append(f"epilogue = {format_string(epilogue)}")
            lines.append("")

        if metadata:
            lines.append("metadata {")
            for k, v in metadata.items():
                if isinstance(v, bool):
                    v_str = str(v).lower()
                elif isinstance(v, (int, float)):
                    v_str = str(v)
                else:
                    v_str = f'"{v!s}"'
                lines.append(f"  {k} = {v_str}")
            lines.append("}")
            lines.append("")

        return "\n".join(lines).strip()
