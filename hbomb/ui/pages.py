from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from PySide6.QtCore import (
    QAbstractItemModel,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QPainter,
    QPalette,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from hbomb.core.config import AppConfig
from hbomb.core.constants import (
    APP_NAME,
    DEFAULT_REFRESH_INTERVAL_SEC,
    PRIORITY_LABELS,
    STATUS_LABELS,
    TaskPriority,
    TaskStatus,
)
from hbomb.core.models import Task, TaskFilter, TaskSort
from hbomb.core.scheduler import Scheduler
from hbomb.core.storage import TaskStorage
from hbomb.core.utils import format_duration, format_timestamp, human_size
from hbomb.providers.base import ProviderRegistry
from hbomb.ui.theme import ThemeManager
from hbomb.ui.widgets import (
    CollapsibleSection,
    DetailPanel,
    FilterBar,
    MetricCard,
    PriorityBadge,
    StatusBadge,
    TaskTable,
    TimelineWidget,
)

# PLACEHOLDER_TRUNCATED_TEST