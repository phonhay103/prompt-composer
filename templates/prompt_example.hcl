preamble = "This is a preamble block."
epilogue = "Please output the translation now."

section "role" {
  content = "You are a translation assistant named {name}."
  tag_wrap = true
}

section "context" {
  content = "Source text: {text:upper}"
  tag_wrap = true
}

section "tools" {
  content = <<-EOF
Use these tools:
{tools:json}
EOF
  tag_wrap = true
  condition = "has_tools"
}

metadata {
  test_key = "test_value"
}
