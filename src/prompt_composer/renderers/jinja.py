from collections.abc import Callable

import jinja2

from prompt_composer.renderers.base import TemplateRenderer


class JinjaTemplateRenderer(TemplateRenderer):
    """Template rendering engine using Jinja2."""

    def render(
        self,
        text: str,
        variables: dict[str, object],
        filters: dict[str, Callable[[object], str]],
    ) -> str:
        """Render using Jinja2 with mapped filters."""
        # Initialize Jinja environment that leaves undefined variables untouched,
        # or we can use DebugUndefined so they are not silently ignored as empty strings
        env = jinja2.Environment(
            undefined=jinja2.DebugUndefined,
            autoescape=False,  # noqa: S701
        )

        # Register custom filters
        for name, func in filters.items():
            env.filters[name] = func

        template = env.from_string(text)
        return template.render(**variables)
