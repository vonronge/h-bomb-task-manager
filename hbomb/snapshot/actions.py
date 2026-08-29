from __future__ import annotations

import os
import signal
from dataclasses import dataclass


@dataclass
class ActionResult:
    ok: bool
    message: str = ""


def end_process(pid: int, kill: bool = False) -> ActionResult:
    sig = signal.SIGKILL if kill else signal.SIGTERM
    try:
        os.kill(pid, sig)
        return ActionResult(True, f"sent {sig} to {pid}")
    except OSError as exc:
        return ActionResult(False, str(exc))


def end_tree(pids: list[int], kill: bool = False) -> ActionResult:
    errors = []
    for pid in pids:
        r = end_process(pid, kill)
        if not r.ok:
            errors.append(f"{pid}: {r.message}")
    if errors:
        return ActionResult(False, "; ".join(errors))
    return ActionResult(True, f"signaled {len(pids)} pids")


def set_nice(pid: int, nice: int) -> ActionResult:
    try:
        os.setpriority(os.PRIO_PROCESS, pid, nice)
        return ActionResult(True)
    except OSError as exc:
        return ActionResult(False, str(exc))
