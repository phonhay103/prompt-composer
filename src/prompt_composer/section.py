"""PromptSection — A named block of text within a composed prompt."""

import re
from typing import Dict, List, Optional

# Regex to find slot variables: {variable_name}
SLOT_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class PromptSection:
    """
    A named section within a prompt.
    Contains text content with optional {slot} variables.

    Attributes:
        name: Section identifier (e.g., "role", "tools", "rules")
        content: Raw text content, may contain {slot} placeholders
        tag_wrap: If True, wrap content in <name>...</name> tags when rendering
    """

    def __init__(self, name: str, content: str, tag_wrap: bool = True):
        self.name = name
        self.content = content
        self.tag_wrap = tag_wrap

    def get_slots(self) -> List[str]:
        """Extract all {slot} variable names from this section's content."""
        return SLOT_RE.findall(self.content)

    def render(self, slots: Optional[Dict[str, str]] = None) -> str:
        """
        Render this section, optionally filling slot variables.

        Args:
            slots: Dict of {variable_name: value} to substitute.
                   Unresolved slots are left as-is.

        Returns:
            Rendered section text, optionally wrapped in XML tags.
        """
        rendered = self.content
        if slots:
            for key, value in slots.items():
                rendered = rendered.replace(f"{{{key}}}", str(value))

        if self.tag_wrap:
            return f"<{self.name}>\n{rendered}\n</{self.name}>"
        return rendered

    def __repr__(self) -> str:
        slots = self.get_slots()
        slot_info = f", slots={slots}" if slots else ""
        return f"PromptSection(name='{self.name}'{slot_info})"
