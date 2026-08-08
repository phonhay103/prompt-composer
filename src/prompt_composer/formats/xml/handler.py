"""XML template format handler implementation using regex-free scanner."""

from typing import Any, override

from prompt_composer.formats.base import FormatHandler
from prompt_composer.section import PromptSection


class XmlHandler(FormatHandler):
    """Parses and serializes prompt templates in XML format."""

    @override
    def parse(
        self, text: str, variable_style: str = "braces"
    ) -> tuple[str, list[PromptSection], str, dict[str, Any]]:
        sections: list[PromptSection] = []
        preamble = ""
        epilogue = ""
        metadata: dict[str, Any] = {}

        i = 0
        n = len(text)
        last_end = 0

        while i < n:
            start_open = text.find("<", i)
            if start_open == -1:
                break
            end_open = text.find(">", start_open)
            if end_open == -1:
                break

            tag_name = text[start_open + 1 : end_open].strip()
            if tag_name.startswith("/") or not tag_name.replace("_", "").isalnum():
                i = start_open + 1
                continue

            close_tag = f"</{tag_name}>"
            start_close = text.find(close_tag, end_open + 1)
            if start_close == -1:
                i = start_open + 1
                continue

            content = text[end_open + 1 : start_close].strip()

            if tag_name in ("metadata", "meta"):
                meta_content = content
                meta_i = 0
                meta_n = len(meta_content)
                while meta_i < meta_n:
                    m_start_open = meta_content.find("<", meta_i)
                    if m_start_open == -1:
                        break
                    m_end_open = meta_content.find(">", m_start_open)
                    if m_end_open == -1:
                        break
                    m_tag = meta_content[m_start_open + 1 : m_end_open].strip()
                    if m_tag.startswith("/") or not m_tag.replace("_", "").isalnum():
                        meta_i = m_start_open + 1
                        continue
                    m_close = f"</{m_tag}>"
                    m_start_close = meta_content.find(m_close, m_end_open + 1)
                    if m_start_close == -1:
                        meta_i = m_end_open + 1
                        continue
                    m_val = meta_content[m_end_open + 1 : m_start_close].strip()
                    metadata[m_tag] = m_val
                    meta_i = m_start_close + len(m_close)
            else:
                if not sections:
                    part = text[last_end:start_open].strip()
                    if part:
                        if preamble:
                            preamble += "\n\n" + part
                        else:
                            preamble = part

                sections.append(
                    PromptSection(name=tag_name, content=content, tag_wrap=True)
                )

            last_end = start_close + len(close_tag)
            i = last_end

        if not sections:
            preamble = text[last_end:].strip()
        else:
            epilogue = text[last_end:].strip()

        return preamble, sections, epilogue, metadata

    @override
    def serialize(
        self,
        preamble: str,
        sections: list[PromptSection],
        epilogue: str,
        metadata: dict[str, Any],
        **kwargs
    ) -> str:
        parts: list[str] = []
        if metadata:
            parts.append("<metadata>")
            for k, v in metadata.items():
                parts.append(f"  <{k}>{v}</{k}>")
            parts.append("</metadata>")

        if preamble:
            parts.append(preamble)

        for sec in sections:
            content_str = sec.content if isinstance(sec.content, str) else "<callable>"
            if sec.tag_wrap:
                tag_name = sec.name
                if isinstance(sec.tag_wrap, str) and sec.tag_wrap.startswith("<") and sec.tag_wrap.endswith(">"):
                    tag_name = sec.tag_wrap[1:-1]
                parts.append(f"<{tag_name}>\n{content_str}\n</{tag_name}>")
            else:
                parts.append(content_str)

        if epilogue:
            parts.append(epilogue)

        return "\n\n".join(parts)
