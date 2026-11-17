"""The module version. luvus-module.toml is the one source."""

from __future__ import annotations

import re
from pathlib import Path

# A regex, not tomllib: the module must still run on a python3 older than 3.11.
_MATCH = re.search(
    r'^version\s*=\s*"([^"]+)"',
    (Path(__file__).resolve().parent / "luvus-module.toml").read_text(),
    re.MULTILINE,
)
VERSION: str = _MATCH.group(1) if _MATCH else "unknown"
