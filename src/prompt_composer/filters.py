"""Centralized filters for PromptComposer slot variables."""

import json
from typing import Any, Dict, Callable

DEFAULT_FILTERS: Dict[str, Callable[[Any], str]] = {
    "json": lambda v: json.dumps(v, indent=2) if not isinstance(v, str) else v,
    "upper": lambda v: str(v).upper(),
    "lower": lambda v: str(v).lower(),
    "trim": lambda v: str(v).strip(),
    "strip": lambda v: str(v).strip(),
    "indent2": lambda v: "\n".join("  " + line if line else line for line in str(v).splitlines()),
    "indent4": lambda v: "\n".join("    " + line if line else line for line in str(v).splitlines()),
}
