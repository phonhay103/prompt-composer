"""PromptSection — A named block of text within a composed prompt."""

import json
from typing import Any, Dict, List, Optional, Union, Callable

DEFAULT_FILTERS: Dict[str, Callable[[Any], str]] = {
    "json": lambda v: json.dumps(v, indent=2) if not isinstance(v, str) else v,
    "upper": lambda v: str(v).upper(),
    "lower": lambda v: str(v).lower(),
    "trim": lambda v: str(v).strip(),
    "strip": lambda v: str(v).strip(),
    "indent2": lambda v: "\n".join("  " + line if line else line for line in str(v).splitlines()),
    "indent4": lambda v: "\n".join("    " + line if line else line for line in str(v).splitlines()),
}


class PromptSection:
    """
    A named section within a prompt.
    Contains text content with optional {slot} variables.

    Attributes:
        name: Section identifier (e.g., "role", "tools", "rules")
        content: Raw text content, may contain {slot} placeholders, or a callable returning content.
        tag_wrap: If True, wrap content in <name>...</name> tags when rendering.
                  If a string starting with "#", treat as markdown header prefix.
                  If any other string, wrap in <tag_wrap>...</tag_wrap> tags.
        condition: Optional slot key string or callable predicate. Section is only rendered if true.
    """

    def __init__(
        self,
        name: str,
        content: Union[str, Callable[[Dict[str, Any]], str]],
        tag_wrap: Union[bool, str] = True,
        condition: Optional[Union[str, Callable[[Dict[str, Any]], bool]]] = None,
    ):
        self.name = name
        self.content = content
        self.tag_wrap = tag_wrap
        self.condition = condition

    def should_render(self, slots: Dict[str, Any]) -> bool:
        """Evaluate the render condition against the current slots."""
        if self.condition is None:
            return True
        if isinstance(self.condition, str):
            return bool(slots.get(self.condition))
        if callable(self.condition):
            return bool(self.condition(slots))
        return True

    def get_slots(self, slot_style: str = "braces") -> List[str]:
        """Extract all slot variable names from this section's content."""
        if callable(self.content):
            return []

        text = self.content
        keys: List[str] = []
        i = 0
        n = len(text)

        if slot_style in ("braces", "python"):
            while i < n:
                if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
                    j = text.find("}", i)
                    if j != -1:
                        placeholder = text[i + 1 : j]
                        key = placeholder.split(":", 1)[0]
                        if key.isidentifier() and key not in keys:
                            keys.append(key)
                        i = j + 1
                        continue
                i += 1
        elif slot_style in ("double_braces", "jinja"):
            while i < n:
                if i + 1 < n and text[i : i + 2] == "{{":
                    j = text.find("}}", i + 2)
                    if j != -1:
                        placeholder = text[i + 2 : j]
                        key = placeholder.split(":", 1)[0]
                        if key.isidentifier() and key not in keys:
                            keys.append(key)
                        i = j + 2
                        continue
                i += 1
        return keys

    def render(
        self,
        slots: Optional[Dict[str, Any]] = None,
        slot_style: str = "braces",
        filters: Optional[Dict[str, Callable[[Any], str]]] = None,
    ) -> str:
        """
        Render this section, optionally filling slot variables and applying filters.

        Args:
            slots: Dict of {variable_name: value} to substitute.
                   Unresolved slots are left as-is.
            slot_style: Slot placeholder format ('braces' or 'double_braces')
            filters: Dictionary of formatting filters

        Returns:
            Rendered section text, optionally wrapped in tags.
        """
        if callable(self.content):
            content_str = self.content(slots or {})
        else:
            content_str = self.content

        rendered = content_str
        if slots:
            active_filters = filters if filters is not None else DEFAULT_FILTERS
            rendered = self._replace_slots(content_str, slots, slot_style, active_filters)

        if self.tag_wrap is True:
            return f"<{self.name}>\n{rendered}\n</{self.name}>"
        elif isinstance(self.tag_wrap, str):
            if self.tag_wrap.startswith("#"):
                return f"{self.tag_wrap}\n{rendered}"
            else:
                return f"<{self.tag_wrap}>\n{rendered}\n</{self.tag_wrap}>"
        return rendered

    def _replace_slots(
        self,
        text: str,
        slots: Dict[str, Any],
        slot_style: str,
        filters: Dict[str, Callable[[Any], str]],
    ) -> str:
        """Perform regex-free slot replacement according to style."""
        result = []
        i = 0
        n = len(text)

        if slot_style in ("braces", "python"):
            while i < n:
                if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
                    j = text.find("}", i)
                    if j != -1:
                        placeholder = text[i + 1 : j]
                        if ":" in placeholder:
                            key, filter_name = placeholder.split(":", 1)
                        else:
                            key, filter_name = placeholder, None

                        if key.isidentifier():
                            if key in slots:
                                val = slots[key]
                                if filter_name and filter_name in filters:
                                    result.append(filters[filter_name](val))
                                else:
                                    result.append(str(val))
                            else:
                                result.append(text[i : j + 1])
                            i = j + 1
                            continue
                result.append(text[i])
                i += 1
        elif slot_style in ("double_braces", "jinja"):
            while i < n:
                if i + 1 < n and text[i : i + 2] == "{{":
                    j = text.find("}}", i + 2)
                    if j != -1:
                        placeholder = text[i + 2 : j]
                        if ":" in placeholder:
                            key, filter_name = placeholder.split(":", 1)
                        else:
                            key, filter_name = placeholder, None

                        if key.isidentifier():
                            if key in slots:
                                val = slots[key]
                                if filter_name and filter_name in filters:
                                    result.append(filters[filter_name](val))
                                else:
                                    result.append(str(val))
                            else:
                                result.append(text[i : j + 2])
                            i = j + 2
                            continue
                result.append(text[i])
                i += 1
        else:
            return text

        return "".join(result)

    def __repr__(self) -> str:
        if callable(self.content):
            content_desc = "<callable>"
            slots: List[str] = []
        else:
            content_desc = f"'{self.content[:20]}...'"
            slots = self.get_slots()
        slot_info = f", slots={slots}" if slots else ""
        cond_info = f", condition={self.condition}" if self.condition else ""
        return f"PromptSection(name='{self.name}', content={content_desc}{slot_info}{cond_info})"
