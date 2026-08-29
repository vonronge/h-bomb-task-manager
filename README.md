# H-Bomb Task Manager

A native Linux system monitor built with **Python** and **Qt 6** (PySide6). No Electron, no embedded browser — just a fast desktop app that reads `/proc`, sysfs, and other kernel interfaces directly.

H-Bomb gives you a Task Manager–style overview of CPU, GPU, memory, disk, network, processes, and more, with live graphs, customizable themes, and optional Rust-accelerated disk scanning.

## Features

- **Overview dashboard** — CPU, GPU (with VRAM), temperature, memory, disk, and network at a glance
- **Performance hub** — per-resource charts for processor, RAM, power draw, thermals, disk I/O, network, and graphics
- **Running apps** — process tree with CPU bars and filtering
- **Disk usage** — treemap and folder-tree views with background scanning
- **Extras** — login items, accounts, services, connections, power/clocks, benchmarks, installed software
- **Themes** — multiple ambiances, color modes, brightness/contrast, and graph styling
- **Native Rust walker** — optional `maturin` extension for faster directory scans (falls back to Python if unavailable)

## Requirements

- Linux (developed on Kubuntu; should work on most distros with standard `/proc` and sysfs)
- Python **3.12+**
- Rust toolchain (only if you want the native disk walker built from source)

## Install & run

```bash
git clone https://github.com/vonronge/h-bomb-task-manager.git
cd h-bomb-task-manager

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python -m hbomb
```

If the Rust extension fails to compile, the app still runs; disk scans use a Python `os.scandir` fallback.

### Desktop entry

After install, you can copy or link `resources/hbomb.desktop` into `~/.local/share/applications/` if your desktop environment does not pick it up automatically.

## Configuration

Settings are stored via Qt `QSettings`:

`~/.config/H-Bomb/H-Bomb Task Manager.conf`

## Development

```bash
source .venv/bin/activate
pytest
```

## License

This project is licensed under the [MIT License](LICENSE) — free to use, modify, and distribute, including commercially, as long as the license notice is included.

## Disclaimer

H-Bomb is a user-mode monitor. It does not require root for normal operation, but some information (system services, certain sensors) may be limited by kernel policy or your distribution. Benchmark and power features depend on hardware and drivers being available on your machine.
