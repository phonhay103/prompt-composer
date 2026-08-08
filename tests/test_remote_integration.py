"""Tests for remote prompt integration components."""

from typing import Any


from prompt_composer import (
    PromptComposer,
    RemotePromptFormatter,
    RemoteProviderRegistry,
)
from prompt_composer.remote.base import RemotePromptData
from prompt_composer.remote.providers import InMemoryProvider, LangfuseProvider


class MockTransport:
    def __init__(self, response_data: dict[str, Any]):
        self.response_data = response_data
        self.last_request = {}

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.last_request = {
            "method": method,
            "url": url,
            "headers": headers or {},
            "json_data": json_data,
            "params": params or {},
        }
        return self.response_data


def test_in_memory_provider_and_formatter():
    prompts = {
        "text_prompt": RemotePromptData(
            template="You are a {role}. Task: {task}",
            default_variables={"role": "assistant"},
            metadata={"domain": "math"},
        ),
        "xml_prompt": RemotePromptData(
            template="<system>You are a {role}.</system><user>{input}</user>",
            format="xml",
        ),
    }

    provider = InMemoryProvider(prompts)

    # Test simple text prompt formatting
    formatter = RemotePromptFormatter.from_remote(provider, "text_prompt")
    assert formatter.composer.metadata["domain"] == "math"

    # Check default variables
    rendered_default = formatter.format({"task": "solve 1+1"})
    assert "You are a assistant." in rendered_default
    assert "Task: solve 1+1" in rendered_default

    # Test override
    rendered_override = formatter.format({"role": "tutor", "task": "solve 1+1"})
    assert "You are a tutor." in rendered_override

    # Test XML format detection & rendering
    xml_formatter = RemotePromptFormatter.from_remote(provider, "xml_prompt")
    xml_rendered = xml_formatter.format({"role": "scientist", "input": "simulate"})
    assert "<system>\nYou are a scientist.\n</system>" in xml_rendered
    assert "<user>\nsimulate\n</user>" in xml_rendered


def test_langfuse_provider_text_prompt():
    response = {
        "name": "tell-joke",
        "version": 3,
        "type": "text",
        "prompt": "Tell a joke about {topic}.",
        "config": {"temperature": 0.7},
        "tags": ["prod", "v3"],
    }

    transport = MockTransport(response)
    provider = LangfuseProvider(
        public_key="pk-123",
        secret_key="sk-456",
        host="https://api.my-langfuse.com",
        transport=transport,
    )

    formatter = RemotePromptFormatter.from_remote(provider, "tell-joke", version="3", label="production")

    # Verify request headers & params
    req = transport.last_request
    assert req["method"] == "GET"
    assert req["url"] == "https://api.my-langfuse.com/api/v1/prompts"
    assert req["params"]["name"] == "tell-joke"
    assert req["params"]["version"] == "3"
    assert req["params"]["label"] == "production"

    # Verify authentication header is present and is Basic auth
    auth_header = req["headers"].get("Authorization")
    assert auth_header is not None
    assert auth_header.startswith("Basic ")

    # Verify metadata & formatting
    assert formatter.composer.metadata["version"] == 3
    assert formatter.composer.metadata["temperature"] == 0.7
    assert "prod" in formatter.composer.metadata["tags"]

    result = formatter.format({"topic": "AI"})
    assert result == "Tell a joke about AI."


def test_langfuse_provider_chat_prompt():
    # Chat prompt is a list of dictionary messages
    response = {
        "name": "chat-agent",
        "version": 1,
        "type": "chat",
        "prompt": [{"role": "system", "content": "You are {role}."}, {"role": "user", "content": "Query: {query}"}],
        "config": {"max_tokens": 100},
    }

    transport = MockTransport(response)
    provider = LangfuseProvider(
        public_key="pk-123",
        secret_key="sk-456",
        transport=transport,
    )

    formatter = RemotePromptFormatter.from_remote(provider, "chat-agent")

    # The list of messages should be automatically converted to XML sections:
    # <system>You are {role}.</system>
    # <user>Query: {query}</user>
    result = formatter.format({"role": "helper", "query": "hello"})
    assert "<system>\nYou are helper.\n</system>" in result
    assert "<user>\nQuery: hello\n</user>" in result
    assert formatter.composer.metadata["max_tokens"] == 100


def test_prompt_composer_from_remote_convenience():
    prompts = {"test_prompt": "Hello {name}!"}
    provider = InMemoryProvider(prompts)

    composer = PromptComposer.from_remote(provider, "test_prompt")
    assert isinstance(composer, PromptComposer)
    composer.set_variable("name", "Alice")
    assert composer.render() == "Hello Alice!"


def test_remote_provider_registry():
    # Clear registry for testing
    RemoteProviderRegistry._providers.clear()

    p1 = InMemoryProvider()
    RemoteProviderRegistry.register("local_test", p1)

    assert RemoteProviderRegistry.get("local_test") is p1

    # Test class instantiation
    p2 = RemoteProviderRegistry.get("langfuse", public_key="pk", secret_key="sk", host="http://localhost")
    assert isinstance(p2, LangfuseProvider)
    assert p2.public_key == "pk"
    assert p2.secret_key == "sk"
    assert p2.host == "http://localhost"
