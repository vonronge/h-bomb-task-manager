"""H-Bomb UI pages — assembled from parts (GitHub MCP size limit workaround)."""
from pathlib import Path
_ns = globals()
for _p in sorted(Path(__file__).with_name("pages_parts").glob("part*.py")):
    exec(compile(_p.read_text(), str(_p), "exec"), _ns)
del _ns, _p
