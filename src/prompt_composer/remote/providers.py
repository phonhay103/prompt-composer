"""Implementations of remote prompt providers."""

import base64
import os
from typing import override

from prompt_composer.remote.base import RemotePromptData, RemotePromptProvider, RemoteTransport
from prompt_composer.remote.transport import UrllibRemoteTransport


class LangfuseProvider(RemotePromptProvider):
    """Fetches prompt templates from the Langfuse API."""

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
        transport: RemoteTransport | None = None,
    ) -> None:
        self.public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY")
        self.host = (host or os.environ.get("LANGFUSE_HOST") or "https://cloud.langfuse.com").rstrip("/")
        self.transport = transport or UrllibRemoteTransport()

        # We don't raise immediately to allow lazy initialization/mocking in tests,
        # but we will check credentials when fetch_prompt is called.

    @override
    def fetch_prompt(self, name: str, version: str | None = None, **kwargs) -> RemotePromptData:
        """
        Fetch the prompt from Langfuse.

        Args:
            name: The name of the prompt.
            version: Optional version number (or version string/tag).
            **kwargs: Extra query parameters (e.g. `label` for production/staging tag).
        """
        if self.public_key in (None, "") or self.secret_key in (None, ""):
            raise ValueError(
                "Langfuse credentials missing. Please set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY, "
                "or pass them to the LangfuseProvider constructor."
            )

        auth_str = f"{self.public_key}:{self.secret_key}"
        auth_bytes = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {auth_bytes}",
            "User-Agent": "prompt-composer/remote-provider",
        }

        # Build url and params
        url = f"{self.host}/api/v1/prompts"
        params = {"name": name}
        if version is not None:
            params["version"] = version

        # Merge kwargs to allow custom params like `label`
        for k, v in kwargs.items():
            params[k] = v

        data = self.transport.request("GET", url, headers=headers, params=params)

        prompt_val = data.get("prompt")
        if prompt_val is None:
            raise RuntimeError(f"Langfuse response does not contain 'prompt': {data}")

        config = data.get("config") or {}
        metadata = dict(config) if isinstance(config, dict) else {"config": config}

        # Add prompt system metadata
        for k in ("name", "version", "type", "tags"):
            if k in data:
                metadata[k] = data[k]

        # Automatically translate chat prompt messages to XML sections if needed
        if isinstance(prompt_val, list):
            parts = []
            for idx, msg in enumerate(prompt_val):
                if isinstance(msg, dict):
                    role = msg.get("role", f"message_{idx}")
                    content = msg.get("content", "")
                    parts.append(f"<{role}>\n{content}\n</{role}>")
                else:
                    parts.append(str(msg))
            template = "\n\n".join(parts)
            fmt = "xml"
        else:
            template = str(prompt_val)
            fmt = None

        return RemotePromptData(
            template=template,
            format=fmt,
            metadata=metadata,
        )


class InMemoryProvider(RemotePromptProvider):
    """Local in-memory provider for testing or fallback purposes."""

    def __init__(self, prompts: dict[str, RemotePromptData | str] | None = None) -> None:
        self.prompts: dict[str, RemotePromptData] = {}
        if prompts is not None:
            for name, data in prompts.items():
                if isinstance(data, str):
                    self.prompts[name] = RemotePromptData(template=data)
                else:
                    self.prompts[name] = data

    @override
    def fetch_prompt(self, name: str, version: str | None = None, **_kwargs) -> RemotePromptData:
        """Fetch prompt from the local dictionary."""
        key = f"{name}:{version}" if version is not None and version != "" else name
        if key in self.prompts:
            return self.prompts[key]
        if name in self.prompts:
            return self.prompts[name]
        raise ValueError(f"Prompt '{name}' (version: {version}) not found in InMemoryProvider.")
