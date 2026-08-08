from collections.abc import Callable
from typing import cast, override

from prompt_composer.enums import VariableStyle
from prompt_composer.renderers.base import TemplateRenderer


class SimpleTemplateRenderer(TemplateRenderer):
    """The default regex-free brace-matching variable replacing engine."""

    def __init__(self, variable_style: str | VariableStyle = VariableStyle.BRACES) -> None:
        try:
            v_style = VariableStyle(variable_style)
        except ValueError:
            v_style = cast(VariableStyle, VariableStyle.BRACES)
        self.variable_style = v_style

    @override
    def render(
        self,
        text: str,
        variables: dict[str, object],
        filters: dict[str, Callable[[object], str]],
    ) -> str:
        """Perform regex-free variable replacement according to style."""
        result = []
        i = 0
        n = len(text)
        v_style = self.variable_style

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
