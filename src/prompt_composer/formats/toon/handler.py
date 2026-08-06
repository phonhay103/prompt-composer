"""TOON template format handler implementation."""

import re
from typing import Tuple, List, Dict, Any
from prompt_composer.formats.base import FormatHandler
from prompt_composer.section import PromptSection


class ToonHandler(FormatHandler):
    """Parses and serializes prompt templates in TOON format."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> Tuple[str, List[PromptSection], str, Dict[str, Any]]:
        data = self._decode_toon(text)
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
        lines = []
        if preamble:
            lines.append(f'preamble: {self._escape_toon_str(preamble)}')
        if epilogue:
            lines.append(f'epilogue: {self._escape_toon_str(epilogue)}')
        
        if metadata:
            lines.append('metadata:')
            for k, v in metadata.items():
                lines.append(f'  {k}: {self._escape_toon_str(str(v))}')
                
        if sections:
            lines.append(f'sections[{len(sections)}]{{name,content,tag_wrap}}:')
            for sec in sections:
                name_val = self._escape_toon_str(sec.name)
                content_val = self._escape_toon_str(sec.content)
                tag_wrap_val = str(sec.tag_wrap).lower()
                lines.append(f'  {name_val},{content_val},{tag_wrap_val}')
                
        return "\n".join(lines)

    def _decode_toon(self, text: str) -> Dict[str, Any]:
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(' '))
            lines.append((indent, stripped))

        if not lines:
            return {}

        base_indent = lines[0][0]
        data, _ = self._parse_object(lines, 0, base_indent)
        return data

    def _parse_object(
        self, lines: List[Tuple[int, str]], start_idx: int, base_indent: int
    ) -> Tuple[Dict[str, Any], int]:
        result = {}
        i = start_idx
        n = len(lines)
        while i < n:
            indent, content = lines[i]
            if indent < base_indent:
                break

            if indent == base_indent:
                # 1. Tabular array header
                tab_match = re.match(r'^(\w+)?\[(\d+)([^\]]*?)\]\{([^\}]+)\}:$', content)
                if tab_match:
                    key = tab_match.group(1) or "array"
                    length = int(tab_match.group(2))
                    delim_char = tab_match.group(3).strip() or ","
                    fields_str = tab_match.group(4)
                    fields = [f.strip() for f in fields_str.split(delim_char)]

                    rows = []
                    i += 1
                    row_count = 0
                    while i < n and row_count < length:
                        r_indent, r_content = lines[i]
                        if r_indent <= base_indent:
                            break
                        cells = self._split_delimited(r_content, delim_char)
                        row_dict = {}
                        for field, cell in zip(fields, cells):
                            row_dict[field] = self._parse_value(cell)
                        rows.append(row_dict)
                        row_count += 1
                        i += 1

                    result[key] = rows
                    continue

                # 2. Inline array
                inline_match = re.match(r'^(\w+)\[(\d+)([^\]]*?)\]:\s*(.*)$', content)
                if inline_match:
                    key = inline_match.group(1)
                    delim_char = inline_match.group(3).strip() or ","
                    vals_str = inline_match.group(4).strip()
                    
                    if vals_str:
                        cells = self._split_delimited(vals_str, delim_char)
                        result[key] = [self._parse_value(c) for c in cells]
                    else:
                        result[key] = []
                    i += 1
                    continue

                # 3. Standard key-value or key-only
                colon_idx = self._find_unquoted_char(content, ':')
                if colon_idx != -1:
                    key = content[:colon_idx].strip()
                    val_str = content[colon_idx+1:].strip()
                    if key.startswith('"') and key.endswith('"') and len(key) >= 2:
                        key = key[1:-1]

                    if val_str:
                        result[key] = self._parse_value(val_str)
                        i += 1
                    else:
                        if i + 1 < n:
                            next_indent, next_content = lines[i+1]
                            if next_indent > base_indent:
                                if next_content.startswith("- "):
                                    list_val, next_i = self._parse_list(lines, i + 1, next_indent)
                                    result[key] = list_val
                                    i = next_i
                                else:
                                    nested_obj, next_i = self._parse_object(lines, i + 1, next_indent)
                                    result[key] = nested_obj
                                    i = next_i
                            else:
                                result[key] = {}
                                i += 1
                        else:
                            result[key] = {}
                            i += 1
                    continue

            i += 1

        return result, i

    def _parse_list(
        self, lines: List[Tuple[int, str]], start_idx: int, base_indent: int
    ) -> Tuple[List[Any], int]:
        result = []
        i = start_idx
        n = len(lines)
        while i < n:
            indent, content = lines[i]
            if indent < base_indent:
                break
            if indent == base_indent:
                if content.startswith("- "):
                    item_str = content[2:].strip()
                    if not item_str:
                        if i + 1 < n:
                            next_indent, next_content = lines[i+1]
                            if next_indent > base_indent:
                                nested_obj, next_i = self._parse_object(lines, i + 1, next_indent)
                                result.append(nested_obj)
                                i = next_i
                                continue
                        result.append(None)
                    else:
                        result.append(self._parse_value(item_str))
            i += 1
        return result, i

    def _find_unquoted_char(self, text: str, char: str) -> int:
        in_quotes = False
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == '"':
                in_quotes = not in_quotes
            elif c == '\\' and i + 1 < n:
                i += 2
                continue
            elif c == char and not in_quotes:
                return i
            i += 1
        return -1

    def _split_delimited(self, text: str, delim: str) -> List[str]:
        result = []
        current = []
        in_quotes = False
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == '"':
                in_quotes = not in_quotes
                current.append(c)
                i += 1
            elif c == '\\' and i + 1 < n:
                current.append(text[i:i+2])
                i += 2
            elif c == delim and not in_quotes:
                result.append("".join(current).strip())
                current = []
                i += 1
            else:
                current.append(c)
                i += 1
        result.append("".join(current).strip())
        return result

    def _parse_value(self, val_str: str) -> Any:
        val_str = val_str.strip()
        if not val_str:
            return ""
        if val_str.startswith('"') and val_str.endswith('"') and len(val_str) >= 2:
            import json
            try:
                return json.loads(val_str)
            except Exception:
                return val_str[1:-1]
        if val_str == "true":
            return True
        if val_str == "false":
            return False
        if val_str == "null":
            return None
        if re.match(r'^-?[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?$', val_str, re.IGNORECASE):
            try:
                if "." in val_str or "e" in val_str.lower():
                    return float(val_str)
                return int(val_str)
            except ValueError:
                pass
        return val_str

    def _escape_toon_str(self, val: Any) -> str:
        if not isinstance(val, str):
            return str(val)
        needs_quotes = (
            not val or 
            any(c in val for c in (' ', '\n', '\r', '\t', ',', ':', '{', '}', '[', ']')) or
            val.startswith('#') or
            val in ('true', 'false', 'null')
        )
        if needs_quotes:
            import json
            return json.dumps(val)
        return val
