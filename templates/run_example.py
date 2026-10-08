#!/usr/bin/env python3
import pathlib
import sys

# Ensure packages/prompt_composer/src is in Python path for running as script
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from prompt_composer import PromptComposer


def main() -> None:
    templates_dir = pathlib.Path(__file__).parent
    slots = {
        "name": "Gemini",
        "text": "hello prompt composer world!",
        "has_tools": True,
        "tools": [{"name": "translator", "description": "Translates text"}],
    }

    formats = ["json", "yaml", "xml", "md", "toml", "toon", "hcl", "baml"]
    for fmt in formats:
        print(f"=== Loading from {fmt.upper()} ===")
        filename = f"prompt_example.{fmt}"
        composer = PromptComposer.from_file(filename, templates_dir, template_format=fmt)
        composer.set_variables(slots)
        print(composer.render())
        print()

    print("=== Custom Filters Example ===")
    composer_yaml = PromptComposer.from_file("prompt_example.yaml", templates_dir, template_format="yaml")
    composer_yaml.set_variables(slots)
    # Registering a custom filter
    composer_yaml.register_filter("exclaim", lambda v: f"{str(v).upper()}!!!")
    composer_yaml.set_role("Greetings: {name:exclaim}")
    print(composer_yaml.render())


if __name__ == "__main__":
    main()
