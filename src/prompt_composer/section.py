"""PromptSection — A named block of text within a composed prompt."""

from collections.abc import Callable
from typing import Any, override

from prompt_composer.enums import VariableStyle
from prompt_composer.filters import DEFAULT_FILTERS


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
        content: str | Callable[[dict[str, Any]], str],
        tag_wrap: bool | str = True,
        condition: str | Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        self.name = name
        self.content = content
        self.tag_wrap = tag_wrap
        self.condition = condition
        self._cached_variables: dict[str, list[str]] = {}

    def should_render(self, variables: dict[str, Any]) -> bool:
        """Evaluate the render condition against the current variables."""
        if self.condition is None:
            return True
        if callable(self.condition):
            from typing import cast

            cond_fn = cast(Callable[[dict[str, Any]], bool], self.condition)
            return bool(cond_fn(variables))
        if isinstance(self.condition, str):
            cond_str = self.condition.strip()
            # If condition contains spaces or standard operators, parse it
            if any(op in cond_str for op in (" AND ", " OR ", "NOT ", "(", ")")):
                return self._evaluate_boolean_expression(cond_str, variables)
            return bool(variables.get(cond_str))
        return True

    def _evaluate_boolean_expression(self, expr: str, variables: dict[str, Any]) -> bool:
        """
        Safely evaluate a boolean expression with AND, OR, NOT operators.
        Avoids eval() by using a simple recursive descent parser.
        """
        tokens = []
        i = 0
        n = len(expr)
        while i < n:
            if expr[i].isspace():
                i += 1
                continue
            if expr[i] == "(":
                tokens.append("(")
                i += 1
            elif expr[i] == ")":
                tokens.append(")")
                i += 1
            else:
                start = i
                while i < n and not expr[i].isspace() and expr[i] not in ("(", ")"):
                    i += 1
                token = expr[start:i]
                tokens.append(token)

        idx = 0
        num_tokens = len(tokens)

        def peek() -> str | None:
            if idx < num_tokens:
                return tokens[idx]
            return None

        def consume(expected: str | None = None) -> str:
            nonlocal idx
            if idx >= num_tokens:
                raise ValueError("Unexpected end of expression")
            token = tokens[idx]
            if expected and token != expected:
                raise ValueError(f"Expected {expected}, got {token}")
            idx += 1
            return token

        def parse_factor() -> bool:
            token = peek()
            if token == "NOT":  # noqa: S105
                consume("NOT")
                return not parse_factor()
            elif token == "(":  # noqa: S105
                consume("(")
                val = parse_expr()
                consume(")")
                return val
            else:
                ident = consume()
                return bool(variables.get(ident))

        def parse_term() -> bool:
            val = parse_factor()
            while peek() == "AND":
                consume("AND")
                right = parse_factor()
                val = val and right
            return val

        def parse_expr() -> bool:
            val = parse_term()
            while peek() == "OR":
                consume("OR")
                right = parse_term()
                val = val or right
            return val

        try:
            result = parse_expr()
            if idx < num_tokens:
                raise ValueError(f"Unexpected token at end: {tokens[idx]}")
            return result
        except Exception:
            return bool(variables.get(expr))

    def get_variables(self, variable_style: str | VariableStyle = VariableStyle.BRACES) -> list[str]:
        """Extract all variable names from this section's content."""
        if callable(self.content):
            return []

        style_str = str(variable_style)
        if style_str in self._cached_variables:
            return self._cached_variables[style_str]

        text = self.content
        keys: list[str] = []
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
    def get_slots(self, slot_style: str = "braces") -> list[str]:
        """Extract all slot names (deprecated, use get_variables)."""
        return self.get_variables(variable_style=slot_style)

    def render(
        self,
        variables: dict[str, Any] | None = None,
        variable_style: str | VariableStyle = VariableStyle.BRACES,
        filters: dict[str, Callable[[Any], str]] | None = None,
        output_format: Any | None = None,
        renderer: Any | None = None,
    ) -> str:
        """
        Render this section, optionally filling variables and applying filters.

        Args:
            variables: Dict of {variable_name: value} to substitute.
                       Unresolved variables are left as-is.
            variable_style: Variable placeholder format ('braces' or 'double_braces')
            filters: Dictionary of formatting filters
            output_format: Optional forced output format ('xml' or 'markdown'/'md')
            renderer: Optional template renderer engine

        Returns:
            Rendered section text, optionally wrapped in tags.
        """
        content_str: str
        if callable(self.content):
            from typing import cast

            content_str = cast(Callable[[dict[str, Any]], str], self.content)(variables or {})
        else:
            content_str = str(self.content)

        rendered: str = content_str
        if variables:
            active_filters = filters if filters is not None else DEFAULT_FILTERS
            if renderer is not None:
                rendered = str(renderer.render(content_str, variables, active_filters))
            else:
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
        variables: dict[str, Any],
        variable_style: str | VariableStyle,
        filters: dict[str, Callable[[Any], str]],
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
                parts = placeholder.split(":")
                key = parts[0]
                filter_names = parts[1:]
                if key.isidentifier():
                    if key in variables:
                        val = variables[key]
                        for f_name in filter_names:
                            if f_name in filters:
                                val = filters[f_name](val)
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
                parts = placeholder.split(":")
                key = parts[0]
                filter_names = parts[1:]
                if key.isidentifier():
                    if key in variables:
                        val = variables[key]
                        for f_name in filter_names:
                            if f_name in filters:
                                val = filters[f_name](val)
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

    @override
    def __repr__(self) -> str:
        if callable(self.content):
            content_desc = "<callable>"
            vars_list: list[str] = []
        else:
            content_desc = f"'{self.content[:20]}...'"
            vars_list = self.get_variables()
        var_info = f", variables={vars_list}" if vars_list else ""
        cond_info = f", condition={self.condition}" if self.condition else ""
        return f"PromptSection(name='{self.name}', content={content_desc}{var_info}{cond_info})"
