"""Assembled from pages_parts/ for GitHub upload size limits."""
from __future__ import annotations

from pathlib import Path

_code = []
for _path in sorted(Path(__file__).with_name("pages_parts").glob("part*.py")):
    _code.append(_path.read_text(encoding="utf-8"))
exec(compile("".join(_code), __file__, "exec"), globals())
