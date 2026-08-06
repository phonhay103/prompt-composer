"""BAML template format handler implementation."""

import re
from typing import Any

from prompt_composer.formats.base import FormatHandler
from prompt_composer.section import PromptSection


class BamlHandler(FormatHandler):
    """Parses and serializes prompt templates in BAML format."""

    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> tuple[str, list[PromptSection], str, dict[str, Any]]:
        cleaned_text = self._strip_comments(text)
        blocks = self._parse_blocks(cleaned_text)

        metadata: dict[str, Any] = {
            "classes": {},
            "enums": {},
            "functions": {}
        }

        functions_data = []

        for header, body in blocks:
            header = header.strip()
            body = body.strip()

            if header.startswith("class "):
                parts = header.split()
                if len(parts) > 1:
                    class_name = parts[1]
                    metadata["classes"][class_name] = body
            elif header.startswith("enum "):
                parts = header.split()
                if len(parts) > 1:
                    enum_name = parts[1]
                    metadata["enums"][enum_name] = body
            elif header.startswith("function "):
                func_info = self._parse_function_header(header)
                if func_info:
                    body_info = self._parse_function_body(body)
                    func_data = {
                        "name": func_info["name"],
                        "arguments": func_info["arguments"],
                        "return_type": func_info["return_type"],
                        "client": body_info["client"],
                        "prompt": body_info["prompt"]
                    }
                    functions_data.append(func_data)
                    metadata["functions"][func_info["name"]] = func_data

        preamble = ""
        epilogue = ""
        sections: list[PromptSection] = []

        if len(functions_data) == 1:
            # Single function case
            func = functions_data[0]
            metadata["function_name"] = func["name"]
            metadata["client"] = func["client"]
            metadata["return_type"] = func["return_type"]
            metadata["arguments"] = func["arguments"]

            prompt_content = func["prompt"]

            # Detect nested format within the prompt content
            from prompt_composer.composer import PromptComposer
            detected_fmt = PromptComposer.detect_format(prompt_content)

            if detected_fmt == "xml":
                if "<" in prompt_content and ">" in prompt_content:
                    from prompt_composer.formats.xml.handler import XmlHandler
                    preamble, sections, epilogue, p_metadata = XmlHandler().parse(prompt_content, variable_style)
                    metadata.update(p_metadata)
                else:
                    sections = [PromptSection(name=func["name"], content=prompt_content, tag_wrap=False)]
            elif detected_fmt == "markdown":
                from prompt_composer.formats.markdown.handler import MarkdownHandler
                preamble, sections, epilogue, p_metadata = MarkdownHandler().parse(prompt_content, variable_style)
                metadata.update(p_metadata)
            elif detected_fmt == "json":
                from prompt_composer.formats.json.handler import JsonHandler
                preamble, sections, epilogue, p_metadata = JsonHandler().parse(prompt_content, variable_style)
                metadata.update(p_metadata)
            elif detected_fmt == "yaml":
                from prompt_composer.formats.yaml.handler import YamlHandler
                preamble, sections, epilogue, p_metadata = YamlHandler().parse(prompt_content, variable_style)
                metadata.update(p_metadata)
            else:
                sections = [PromptSection(name=func["name"], content=prompt_content, tag_wrap=False)]
        elif len(functions_data) > 1:
            # Multiple functions case
            for func in functions_data:
                sections.append(
                    PromptSection(
                        name=func["name"],
                        content=func["prompt"],
                        tag_wrap=False
                    )
                )
        else:
            preamble = text

        return preamble, sections, epilogue, metadata

    def serialize(
        self,
        preamble: str,
        sections: list[PromptSection],
        epilogue: str,
        metadata: dict[str, Any],
        **kwargs
    ) -> str:
        parts = []

        # Classes
        classes = metadata.get("classes", {})
        for name, body in classes.items():
            parts.append(f"class {name} {{\n{body}\n}}")

        # Enums
        enums = metadata.get("enums", {})
        for name, body in enums.items():
            parts.append(f"enum {name} {{\n{body}\n}}")

        # Reconstruct prompt content from sections
        prompt_parts = []
        if preamble:
            prompt_parts.append(preamble)
        for sec in sections:
            if sec.tag_wrap:
                tag_name = sec.name
                if isinstance(sec.tag_wrap, str):
                    if sec.tag_wrap.startswith("<") and sec.tag_wrap.endswith(">"):
                        tag_name = sec.tag_wrap[1:-1]
                        prompt_parts.append(f"<{tag_name}>\n{sec.content}\n</{tag_name}>")
                    elif sec.tag_wrap.startswith("#"):
                        prompt_parts.append(f"{sec.tag_wrap}\n{sec.content}")
                    else:
                        prompt_parts.append(f"<{sec.name}>\n{sec.content}\n</{sec.name}>")
                else:
                    prompt_parts.append(f"<{sec.name}>\n{sec.content}\n</{sec.name}>")
            else:
                prompt_parts.append(sec.content)
        if epilogue:
            prompt_parts.append(epilogue)

        prompt_text = "\n\n".join(prompt_parts)

        # Function definition
        func_name = metadata.get("function_name", "PromptFunction")
        client = metadata.get("client", "openai/gpt-4o")

        args = metadata.get("arguments", {})
        args_str = ", ".join(f"{k}: {v}" for k, v in args.items())

        ret_type = metadata.get("return_type", "string")

        # Ident nested prompt text to match typical BAML formatting style
        indented_prompt = "\n".join("    " + line if line else "" for line in prompt_text.splitlines())

        parts.append(
            f"function {func_name}({args_str}) -> {ret_type} {{\n"
            f"  client \"{client}\"\n"
            f"  prompt #\"\n"
            f"{indented_prompt}\n"
            f"  \"#\n"
            f"}}"
        )

        return "\n\n".join(parts)

    def _strip_comments(self, text: str) -> str:
        result = []
        i = 0
        n = len(text)
        while i < n:
            if text[i:i+2] == '#"':
                result.append('#"')
                i += 2
                while i < n:
                    if text[i:i+2] == '"#':
                        result.append('"#')
                        i += 2
                        break
                    else:
                        result.append(text[i])
                        i += 1
            elif text[i] == '"':
                result.append('"')
                i += 1
                while i < n:
                    if text[i] == '\\' and i + 1 < n:
                        result.append(text[i:i+2])
                        i += 2
                    elif text[i] == '"':
                        result.append('"')
                        i += 1
                        break
                    else:
                        result.append(text[i])
                        i += 1
            elif text[i:i+2] == '//':
                i += 2
                while i < n and text[i] != '\n':
                    i += 1
                if i < n:
                    result.append(text[i])
                    i += 1
            elif text[i:i+2] == '/*':
                i += 2
                while i < n:
                    if text[i:i+2] == '*/':
                        i += 2
                        break
                    else:
                        if text[i] == '\n':
                            result.append('\n')
                        i += 1
            else:
                result.append(text[i])
                i += 1
        return "".join(result)

    def _parse_blocks(self, text: str) -> list[tuple[str, str]]:
        i = 0
        n = len(text)
        blocks = []
        header_start = 0
        while i < n:
            if text[i:i+2] == '#"':
                i += 2
                while i < n and text[i:i+2] != '"#':
                    i += 1
                if i < n:
                    i += 2
            elif text[i] == '"':
                i += 1
                while i < n:
                    if text[i] == '\\' and i + 1 < n:
                        i += 2
                    elif text[i] == '"':
                        i += 1
                        break
                    else:
                        i += 1
            elif text[i] == '{':
                header = text[header_start:i].strip()
                brace_count = 1
                body_start = i + 1
                i += 1
                while i < n and brace_count > 0:
                    if text[i:i+2] == '#"':
                        i += 2
                        while i < n and text[i:i+2] != '"#':
                            i += 1
                        if i < n:
                            i += 2
                    elif text[i] == '"':
                        i += 1
                        while i < n:
                            if text[i] == '\\' and i + 1 < n:
                                i += 2
                            elif text[i] == '"':
                                i += 1
                                break
                            else:
                                i += 1
                    elif text[i] == '{':
                        brace_count += 1
                        i += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            body = text[body_start:i]
                            blocks.append((header, body))
                            i += 1
                            header_start = i
                            break
                        else:
                            i += 1
                    else:
                        i += 1
            else:
                i += 1
        return blocks

    def _parse_function_header(self, header: str) -> dict[str, Any] | None:
        header = header.strip()
        if not header.startswith("function"):
            return None

        open_paren = header.find("(")
        if open_paren == -1:
            return None
        name = header[8:open_paren].strip()

        close_paren = header.find(")", open_paren)
        if close_paren == -1:
            return None
        args_str = header[open_paren+1:close_paren].strip()

        arguments = {}
        if args_str:
            for arg in args_str.split(","):
                arg = arg.strip()
                if ":" in arg:
                    arg_name, arg_type = arg.split(":", 1)
                    arguments[arg_name.strip()] = arg_type.strip()
                else:
                    arguments[arg] = "unknown"

        arrow = header.find("->", close_paren)
        return_type = "unknown"
        if arrow != -1:
            return_type = header[arrow+2:].strip()

        return {
            "name": name,
            "arguments": arguments,
            "return_type": return_type
        }

    def _parse_function_body(self, body: str) -> dict[str, Any]:
        client = ""
        client_match = re.search(r'\bclient\s+("[^"]+"|\w+)', body)
        if client_match:
            client = client_match.group(1).strip('"')

        prompt_content = ""
        prompt_match = re.search(r'prompt\s*#"', body)
        if prompt_match:
            content_start = prompt_match.end()
            prompt_end = body.find('"#', content_start)
            if prompt_end != -1:
                prompt_content = body[content_start:prompt_end]

        return {
            "client": client,
            "prompt": prompt_content
        }
