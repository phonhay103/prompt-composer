class Message {
  role string
  content string
}

function Translate(text: string, name: string) -> string {
  client "openai/gpt-4o"
  prompt #"
This is a preamble block.

<role>
You are a translation assistant named {name}.
</role>

<context>
Source text: {text:upper}
</context>

<tools>
Use these tools:
{tools:json}
</tools>

Please output the translation now.
  "#
}
