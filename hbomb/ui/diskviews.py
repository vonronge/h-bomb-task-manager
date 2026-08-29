from __future__ import annotations

from dataclasses import dataclass

import math
import random
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem, QHeaderView

from hbomb.providers.linux.diskspace import DiskNode, squarify
from hbomb.ui.fmt import bytes_h, compact_bytes
from hbomb.ui.theme import Theme
