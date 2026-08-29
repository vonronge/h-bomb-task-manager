from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable


SKIP_TOP = {"proc", "sys", "dev", "run"}


@dataclass
class DiskNode:
    path: str
    name: str
    size: int = 0
    is_dir: bool = False
    children: list["DiskNode"] = field(default_factory=list)
    file_count: int = 0
    dir_count: int = 0
    ext: str = ""

    def percent_of(self, parent_size: int) -> float:
        if parent_size <= 0:
            return 0.0
        return self.size / parent_size


def _should_skip(path: str) -> bool:
    parts = path.split(os.sep)
    if len(parts) >= 2 and parts[1] in SKIP_TOP:
        return True
    return False


def walk_python(root: str, cancel: Callable[[], bool] | None = None) -> list[tuple[str, int, bool]]:
    rows: list[tuple[str, int, bool]] = []
    root = os.path.abspath(root)
    rows.append((root, 0, True))
    stack = [root]
    while stack:
        if cancel and cancel():
            break
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for ent in it:
                    if _should_skip(ent.path):
                        continue
                    try:
                        is_dir = ent.is_dir(follow_symlinks=False)
                    except OSError:
                        continue
                    if is_dir:
                        rows.append((ent.path, 0, True))
                        stack.append(ent.path)
                    else:
                        try:
                            sz = ent.stat(follow_symlinks=False).st_size
                        except OSError:
                            sz = 0
                        rows.append((ent.path, sz, False))
        except OSError:
            continue
    return rows


def walk(root: str, cancel: Callable[[], bool] | None = None) -> list[tuple[str, int, bool]]:
    try:
        from hbomb import _native

        return list(_native.walk_flat(root))
    except Exception:
        return walk_python(root, cancel)


def build_tree(rows: list[tuple[str, int, bool]]) -> DiskNode:
    nodes: dict[str, DiskNode] = {}
    root_path = rows[0][0] if rows else os.sep
    for path, size, is_dir in rows:
        name = os.path.basename(path) or path
        ext = "" if is_dir else os.path.splitext(name)[1].lower()
        nodes[path] = DiskNode(path=path, name=name, size=size, is_dir=is_dir, ext=ext)
    for path, node in nodes.items():
        if path == root_path:
            continue
        parent = os.path.dirname(path)
        while parent and parent not in nodes and parent != path:
            parent = os.path.dirname(parent)
        if parent in nodes and parent != path:
            nodes[parent].children.append(node)
    for node in nodes.values():
        if node.is_dir:
            node.size = 0
    def roll(n: DiskNode) -> int:
        if not n.is_dir:
            n.file_count = 1
            return n.size
        total = 0
        files = 0
        dirs = 0
        for ch in n.children:
            total += roll(ch)
            if ch.is_dir:
                dirs += 1 + ch.dir_count
                files += ch.file_count
            else:
                files += 1
        n.size = total
        n.file_count = files
        n.dir_count = dirs
        n.children.sort(key=lambda c: c.size, reverse=True)
        return total

    root = nodes.get(root_path) or DiskNode(path=root_path, name=root_path, is_dir=True)
    if root_path in nodes:
        roll(root)
    return root


def squarify(node: DiskNode, x: float, y: float, w: float, h: float) -> list[tuple[DiskNode, float, float, float, float]]:
    children = [c for c in node.children if c.size > 0]
    if not children or w <= 1 or h <= 1:
        return [(node, x, y, w, h)] if not children else []
    total = sum(c.size for c in children) or 1
    rects: list[tuple[DiskNode, float, float, float, float]] = []
    row: list[DiskNode] = []
    worst = 1e18

    def row_worst(items: list[DiskNode], length: float) -> float:
        if not items or length <= 0:
            return 1e18
        s = sum(c.size for c in items) / total * (w * h)
        if s <= 0:
            return 1e18
        rmax = 0.0
        for c in items:
            a = c.size / total * (w * h)
            side = s / length
            other = a / side if side else 0
            rmax = max(rmax, side / other if other else 1e18, other / side if side else 1e18)
        return rmax

    remaining = children[:]
    vertical = h >= w
    length = h if vertical else w
    cx, cy, cw, ch = x, y, w, h

    def layout_row(items: list[DiskNode]) -> None:
        nonlocal cx, cy, cw, ch
        s = sum(c.size for c in items) / total * (w * h)
        if vertical:
            rw = s / ch if ch else 0
            yy = cy
            for c in items:
                hh = (c.size / total * (w * h)) / rw if rw else 0
                rects.append((c, cx, yy, rw, hh))
                yy += hh
            cx += rw
            cw -= rw
        else:
            rh = s / cw if cw else 0
            xx = cx
            for c in items:
                ww = (c.size / total * (w * h)) / rh if rh else 0
                rects.append((c, xx, cy, ww, rh))
                xx += ww
            cy += rh
            ch -= rh

    while remaining:
        nxt = remaining[0]
        trial = row + [nxt]
        tw = row_worst(trial, length)
        if row and tw > worst:
            layout_row(row)
            row = []
            worst = 1e18
            vertical = ch >= cw
            length = ch if vertical else cw
            continue
        remaining.pop(0)
        row = trial
        worst = tw
    if row:
        layout_row(row)
    return rects
