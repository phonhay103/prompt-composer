"""PromptSection — A named block of text within a composed prompt."""

from typing import Any, Dict, List, Optional, Union, Callable

from prompt_composer.filters import DEFAULT_FILTERS
from prompt_composer.enums import VariableStyle


class PromptSection:
    """
    A named section within a prompt.
    Contains text content with optional {variable} placeholders, or a callable returning content.

    Attributes:
        name: Section identifier (e.g., "role", "tools", "rules")
        content: Raw text content, may contain {variable} placeholders, or a callable.
        tag_wrap: If True, wrap content in <name>...</name> tags when rendering.
                  If a string starting with "#", treat as markdown header prefix.
                  If any other string, wrap in <tag_wrap>...</tag_wrap> tags.
        condition: Optional variable key string or callable predicate. Section is only rendered if true.
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
        self._cached_variables: Dict[str, List[str]] = {}

    def should_render(self, variables: Dict[str, Any]) -> bool:
        """Evaluate the render condition against the current variables."""
        if self.condition is None:
            return True
        if isinstance(self.condition, str):
            return bool(variables.get(self.condition))
        if callable(self.condition):
            return bool(self.condition(variables))
        return True

    def get_variables(self, variable_style: Union[str, VariableStyle] = VariableStyle.BRACES) -> List[str]:
        """Extract all variable names from this section's content."""
        if callable(self.content):
            return []

        style_str = str(variable_style)
        if style_str in self._cached_variables:
            return self._cached_variables[style_str]

        text = self.content
        keys: List[str] = []
        i = 0
        n = len(text)

        try:
            v_style = VariableStyle(variable_style)
        except ValueError:
            v_style = VariableStyle.BRACES

        if v_style in (VariableStyle.BRACES, VariableStyle.PYTHON):
            while i < n:
                start_open = text.find("{", i)
                if start_open == -1:
                    break
                if start_open > 0 and text[start_open - 1] == "\\":
                    i = start_open + 1
                    continue
                end_close = text.find("}", start_open + 1)
                if end_close == -1:
                    break
                placeholder = text[start_open + 1 : end_close]
                key = placeholder.split(":", 1)[0]
                if key.isidentifier() and key not in keys:
                    keys.append(key)
                i = end_close + 1
        elif v_style in (VariableStyle.DOUBLE_BRACES, VariableStyle.JINJA):
            while i < n:
                start_open = text.find("{{", i)
                if start_open == -1:
                    break
                end_close = text.find("}}", start_open + 2)
                if end_close == -1:
                    break
                placeholder = text[start_open + 2 : end_close]
                key = placeholder.split(":", 1)[0]
                if key.isidentifier() and key not in keys:
                    keys.append(key)
                i = end_close + 2

        self._cached_variables[style_str] = keys
        return keys

    # Backward compatibility alias
    def get_slots(self, slot_style: str = "braces") -> List[str]:
        """Extract all slot names (deprecated, use get_variables)."""
        return self.get_variables(variable_style=slot_style)

    def render(
        self,
        variables: Optional[Dict[str, Any]] = None,
        variable_style: Union[str, VariableStyle] = VariableStyle.BRACES,
        filters: Optional[Dict[str, Callable[[Any], str]]] = None,
        output_format: Optional[Any] = None,
    ) -> str:
        """
        Render this section, optionally filling variables and applying filters.

        Args:
            variables: Dict of {variable_name: value} to substitute.
                       Unresolved variables are left as-is.
            variable_style: Variable placeholder format ('braces' or 'double_braces')
            filters: Dictionary of formatting filters
            output_format: Optional forced output format ('xml' or 'markdown'/'md')

        Returns:
            Rendered section text, optionally wrapped in tags.
        """
        if callable(self.content):
            content_str = self.content(variables or {})
        else:
            content_str = self.content

        rendered = content_str
        if variables:
            active_filters = filters if filters is not None else DEFAULT_FILTERS
            rendered = self._replace_variables(content_str, variables, variable_style, active_filters)

        if self.tag_wrap is False:
            return rendered

        if output_format == "xml":
            return f"<{self.name}>\n{rendered}\n</{self.name}>"
        elif output_format in ("markdown", "md"):
            return f"## {self.name}\n{rendered}"

        if self.tag_wrap is True:
            return f"<{self.name}>\n{rendered}\n</{self.name}>"
        elif isinstance(self.tag_wrap, str):
            if self.tag_wrap.startswith("#"):
                return f"{self.tag_wrap}\n{rendered}"
            else:
                return f"<{self.tag_wrap}>\n{rendered}\n</{self.tag_wrap}>"
        return rendered

    def _replace_variables(
        self,
        text: str,
        variables: Dict[str, Any],
        variable_style: Union[str, VariableStyle],
        filters: Dict[str, Callable[[Any], str]],
    ) -> str:
        """Perform regex-free variable replacement according to style."""
        result = []
        i = 0
        n = len(text)

        try:
            v_style = VariableStyle(variable_style)
        except ValueError:
            v_style = VariableStyle.BRACES

        if v_style in (VariableStyle.BRACES, VariableStyle.PYTHON):
            while i < n:
                start_open = text.find("{", i)
                if start_open == -1:
                    result.append(text[i:])
                    break
                result.append(text[i:start_open])
                if start_open > 0 and text[start_open - 1] == "\\":
                    result.append("{")
                    i = start_open + 1
                    continue
                end_close = text.find("}", start_open + 1)
                if end_close == -1:
                    result.append(text[start_open])
                    i = start_open + 1
                    continue
                placeholder = text[start_open + 1 : end_close]
                if ":" in placeholder:
                    key, filter_name = placeholder.split(":", 1)
                else:
                    key, filter_name = placeholder, None
                if key.isidentifier():
                    if key in variables:
                        val = variables[key]
                        if filter_name and filter_name in filters:
                            result.append(filters[filter_name](val))
                        else:
                            result.append(str(val))
                    else:
                        result.append(text[start_open : end_close + 1])
                    i = end_close + 1
                else:
                    result.append(text[start_open])
                    i = start_open + 1
        elif v_style in (VariableStyle.DOUBLE_BRACES, VariableStyle.JINJA):
            while i < n:
                start_open = text.find("{{", i)
                if start_open == -1:
                    result.append(text[i:])
                    break
                result.append(text[i:start_open])
                end_close = text.find("}}", start_open + 2)
                if end_close == -1:
                    result.append(text[start_open : start_open + 2])
                    i = start_open + 2
                    continue
                placeholder = text[start_open + 2 : end_close]
                if ":" in placeholder:
                    key, filter_name = placeholder.split(":", 1)
                else:
                    key, filter_name = placeholder, None
                if key.isidentifier():
                    if key in variables:
                        val = variables[key]
                        if filter_name and filter_name in filters:
                            result.append(filters[filter_name](val))
                        else:
                            result.append(str(val))
                    else:
                        result.append(text[start_open : end_close + 2])
                    i = end_close + 2
                else:
                    result.append(text[start_open : start_open + 2])
                    i = start_open + 2
        else:
            return text

        return "".join(result)

    def __repr__(self) -> str:
        if callable(self.content):
            content_desc = "<callable>"
            vars_list: List[str] = []
        else:
            content_desc = f"'{self.content[:20]}...'"
            vars_list = self.get_variables()
        var_info = f", variables={vars_list}" if vars_list else ""
        cond_info = f", condition={self.condition}" if self.condition else ""
        return f"PromptSection(name='{self.name}', content={content_desc}{var_info}{cond_info})"
