# H-Bomb Task Manager

Native Qt system monitor for Kubuntu. Python + PySide6 Widgets, thin snapshot layer, optional Rust disk walker.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m hbomb
```

If the native walker fails to build, scans fall back to Python `os.scandir`.

Config: `~/.config/H-Bomb/H-Bomb Task Manager.conf`
