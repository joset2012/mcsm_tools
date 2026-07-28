import json
import os
import re
import sys
import tempfile
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QSplitter, QStatusBar, QMessageBox, QComboBox, QPushButton,
    QLabel, QLineEdit, QFormLayout, QGroupBox, QCheckBox,
    QDialogButtonBox, QDialog, QTextEdit, QListWidget, QListWidgetItem,
    QHeaderView, QAbstractItemView,
    QTreeWidget, QTreeWidgetItem, QProgressBar, QTableWidget,
    QTableWidgetItem, QFileDialog, QMenu, QInputDialog, QPlainTextEdit,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent, QRect, QSize, QRectF, QPointF
from PyQt5.QtGui import (
    QFont, QTextCursor, QColor, QPainter, QPen, QFontMetrics,
    QTextCharFormat, QSyntaxHighlighter, QPixmap, QIcon, QPainterPath,
)

from mcsm_tools.api import MCSManagerAPI
from mcsm_tools.config import load_config, save_config
from mcsm_tools.terminal import MCSMTerminal
from mcsm_tools.command_history import CommandHistory
from mcsm_tools.qt_nord import QSS, apply_nord_palette, Nord


class AppIcons:
    _cache = {}

    SIZE = 16

    @staticmethod
    def _pix(size, func):
        key = (size, func.__name__)
        if key in AppIcons._cache:
            return AppIcons._cache[key]
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        func(p, size)
        p.end()
        AppIcons._cache[key] = QIcon(pm)
        return AppIcons._cache[key]

    @staticmethod
    def icon(name, size=16):
        m = getattr(AppIcons, f"_draw_{name}", None)
        if m:
            return AppIcons._pix(size, m)
        return QIcon()

    @staticmethod
    def _draw_folder(p, s):
        c = QColor(Nord.frost_2)
        p.setPen(QPen(c.darker(130), 1))
        p.setBrush(QColor(c))
        path = QPainterPath()
        path.moveTo(s * 0.15, s * 0.3)
        path.lineTo(s * 0.35, s * 0.3)
        path.lineTo(s * 0.45, s * 0.4)
        path.lineTo(s * 0.85, s * 0.4)
        path.lineTo(s * 0.85, s * 0.8)
        path.lineTo(s * 0.15, s * 0.8)
        path.closeSubpath()
        p.drawPath(path)

    @staticmethod
    def _draw_file(p, s):
        c = QColor(Nord.aurora_yellow)
        p.setPen(QPen(c.darker(120), 1))
        p.setBrush(QColor(c))
        path = QPainterPath()
        path.moveTo(s * 0.2, s * 0.1)
        path.lineTo(s * 0.65, s * 0.1)
        path.lineTo(s * 0.8, s * 0.25)
        path.lineTo(s * 0.8, s * 0.9)
        path.lineTo(s * 0.2, s * 0.9)
        path.closeSubpath()
        p.drawPath(path)
        p.setPen(QPen(c.darker(160), 1))
        p.drawLine(int(s * 0.35), int(s * 0.55), int(s * 0.65), int(s * 0.55))
        p.drawLine(int(s * 0.35), int(s * 0.65), int(s * 0.65), int(s * 0.65))

    @staticmethod
    def _draw_image(p, s):
        c = QColor(Nord.aurora_pink)
        p.setPen(QPen(c.darker(120), 1))
        p.setBrush(QColor(c))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.15, s * 0.1, s * 0.7, s * 0.8), 2, 2)
        p.drawPath(path)
        p.setPen(QPen(QColor(Nord.snow_storm_1), 1))
        p.drawEllipse(QPointF(s * 0.45, s * 0.4), s * 0.1, s * 0.1)
        p.drawLine(int(s * 0.3), int(s * 0.7), int(s * 0.45), int(s * 0.55))
        p.drawLine(int(s * 0.45), int(s * 0.55), int(s * 0.6), int(s * 0.7))

    @staticmethod
    def _draw_archive(p, s):
        c = QColor(Nord.aurora_orange)
        p.setPen(QPen(c.darker(120), 1))
        p.setBrush(QColor(c))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.15, s * 0.2, s * 0.7, s * 0.65), 2, 2)
        p.drawPath(path)
        p.setPen(QPen(QColor(Nord.snow_storm_1), 1))
        p.drawLine(int(s * 0.25), int(s * 0.45), int(s * 0.75), int(s * 0.45))
        p.drawLine(int(s * 0.45), int(s * 0.3), int(s * 0.45), int(s * 0.6))

    @staticmethod
    def _draw_upload(p, s):
        c = QColor(Nord.aurora_green)
        p.setPen(QPen(c, 1.5))
        p.setBrush(QColor(Nord.polar_night_2))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.15, s * 0.55, s * 0.7, s * 0.35), 2, 2)
        p.drawPath(path)
        p.setPen(QPen(c, 2))
        p.drawLine(int(s * 0.5), int(s * 0.15), int(s * 0.5), int(s * 0.55))
        p.drawLine(int(s * 0.3), int(s * 0.35), int(s * 0.5), int(s * 0.15))
        p.drawLine(int(s * 0.7), int(s * 0.35), int(s * 0.5), int(s * 0.15))

    @staticmethod
    def _draw_download(p, s):
        c = QColor(Nord.frost_3)
        p.setPen(QPen(c, 1.5))
        p.setBrush(QColor(Nord.polar_night_2))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.15, s * 0.1, s * 0.7, s * 0.35), 2, 2)
        p.drawPath(path)
        p.setPen(QPen(c, 2))
        p.drawLine(int(s * 0.5), int(s * 0.45), int(s * 0.5), int(s * 0.85))
        p.drawLine(int(s * 0.3), int(s * 0.65), int(s * 0.5), int(s * 0.85))
        p.drawLine(int(s * 0.7), int(s * 0.65), int(s * 0.5), int(s * 0.85))

    @staticmethod
    def _draw_delete(p, s):
        c = QColor(Nord.aurora_red)
        p.setPen(QPen(c, 1.5))
        p.setBrush(QColor(Nord.polar_night_2))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.25, s * 0.3, s * 0.5, s * 0.6), 2, 2)
        p.drawPath(path)
        p.setPen(QPen(c.darker(130), 2))
        p.drawLine(int(s * 0.2), int(s * 0.3), int(s * 0.8), int(s * 0.3))
        p.drawLine(int(s * 0.35), int(s * 0.2), int(s * 0.45), int(s * 0.2))
        p.drawLine(int(s * 0.55), int(s * 0.2), int(s * 0.65), int(s * 0.2))

    @staticmethod
    def _draw_add(p, s):
        c = QColor(Nord.aurora_green)
        p.setPen(QPen(c, 2))
        p.drawLine(int(s * 0.5), int(s * 0.2), int(s * 0.5), int(s * 0.8))
        p.drawLine(int(s * 0.2), int(s * 0.5), int(s * 0.8), int(s * 0.5))
        p.setPen(QPen(c.darker(130), 1))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.1, s * 0.1, s * 0.8, s * 0.8), 3, 3)
        p.drawPath(path)

    @staticmethod
    def _draw_refresh(p, s):
        c = QColor(Nord.frost_2)
        p.setPen(QPen(c, 2))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.arcMoveTo(s * 0.15, s * 0.15, s * 0.7, s * 0.7, 45)
        path.arcTo(s * 0.15, s * 0.15, s * 0.7, s * 0.7, 45, -270)
        p.drawPath(path)
        p.setBrush(QColor(c))
        p.setPen(Qt.NoPen)
        pts = [
            (s * 0.4, s * 0.25), (s * 0.55, s * 0.15), (s * 0.6, s * 0.3)
        ]
        path2 = QPainterPath()
        path2.moveTo(*pts[0])
        path2.lineTo(*pts[1])
        path2.lineTo(*pts[2])
        path2.closeSubpath()
        p.drawPath(path2)

    @staticmethod
    def _draw_up(p, s):
        c = QColor(Nord.frost_2)
        p.setPen(QPen(c.darker(130), 1))
        p.setBrush(QColor(Nord.polar_night_2))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.2, s * 0.5, s * 0.6, s * 0.4), 2, 2)
        p.drawPath(path)
        p.setPen(QPen(c, 2))
        p.drawLine(int(s * 0.5), int(s * 0.15), int(s * 0.5), int(s * 0.5))
        p.drawLine(int(s * 0.3), int(s * 0.35), int(s * 0.5), int(s * 0.15))
        p.drawLine(int(s * 0.7), int(s * 0.35), int(s * 0.5), int(s * 0.15))

    @staticmethod
    def _draw_home(p, s):
        c = QColor(Nord.aurora_green)
        p.setPen(QPen(c.darker(130), 1))
        p.setBrush(QColor(c))
        path = QPainterPath()
        path.moveTo(s * 0.5, s * 0.1)
        path.lineTo(s * 0.85, s * 0.4)
        path.lineTo(s * 0.75, s * 0.4)
        path.lineTo(s * 0.75, s * 0.85)
        path.lineTo(s * 0.25, s * 0.85)
        path.lineTo(s * 0.25, s * 0.4)
        path.lineTo(s * 0.15, s * 0.4)
        path.closeSubpath()
        p.drawPath(path)

    @staticmethod
    def _draw_compress(p, s):
        c = QColor(Nord.aurora_orange)
        p.setPen(QPen(c.darker(130), 1))
        p.setBrush(QColor(c))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.15, s * 0.2, s * 0.7, s * 0.6), 2, 2)
        p.drawPath(path)
        p.setPen(QPen(QColor(Nord.snow_storm_1), 1.5))
        p.drawLine(int(s * 0.25), int(s * 0.5), int(s * 0.75), int(s * 0.5))

    @staticmethod
    def _draw_extract(p, s):
        c = QColor(Nord.aurora_yellow)
        p.setPen(QPen(c.darker(130), 1))
        p.setBrush(QColor(c))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.15, s * 0.2, s * 0.7, s * 0.6), 2, 2)
        p.drawPath(path)
        p.setPen(QPen(QColor(Nord.snow_storm_1), 1.5))
        ar = QPainterPath()
        ar.moveTo(s * 0.3, s * 0.35)
        ar.lineTo(s * 0.5, s * 0.2)
        ar.lineTo(s * 0.7, s * 0.35)
        p.drawPath(ar)
        p.drawLine(int(s * 0.5), int(s * 0.2), int(s * 0.5), int(s * 0.6))

    @staticmethod
    def _draw_edit(p, s):
        c = QColor(Nord.frost_2)
        p.setPen(QPen(c, 1.5))
        p.setBrush(QColor(Nord.polar_night_2))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.2, s * 0.7, s * 0.6, s * 0.2), 2, 2)
        p.drawPath(path)
        p.setPen(QPen(c, 2))
        p.drawLine(int(s * 0.3), int(s * 0.65), int(s * 0.6), int(s * 0.25))
        p.drawLine(int(s * 0.6), int(s * 0.25), int(s * 0.7), int(s * 0.3))
        p.drawLine(int(s * 0.7), int(s * 0.3), int(s * 0.4), int(s * 0.7))

    @staticmethod
    def _draw_rename(p, s):
        c = QColor(Nord.frost_3)
        p.setPen(QPen(c, 1.5))
        p.setBrush(QColor(Nord.polar_night_1))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.15, s * 0.3, s * 0.7, s * 0.5), 3, 3)
        p.drawPath(path)
        p.setPen(QPen(QColor(Nord.snow_storm_1), 1))
        p.drawText(QRectF(0, s * 0.35, s, s * 0.4), Qt.AlignCenter, "Aa")

    @staticmethod
    def _draw_cut(p, s):
        c = QColor(Nord.aurora_red)
        p.setPen(QPen(c, 2))
        p.drawLine(int(s * 0.15), int(s * 0.15), int(s * 0.7), int(s * 0.7))
        p.drawLine(int(s * 0.15), int(s * 0.85), int(s * 0.7), int(s * 0.3))
        p.setBrush(QColor(c))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(s * 0.15, s * 0.15), s * 0.08, s * 0.08)
        p.drawEllipse(QPointF(s * 0.15, s * 0.85), s * 0.08, s * 0.08)

    @staticmethod
    def _draw_copy(p, s):
        c = QColor(Nord.frost_2)
        p.setPen(QPen(c.darker(130), 1))
        p.setBrush(QColor(Nord.polar_night_2))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.25, s * 0.35, s * 0.6, s * 0.55), 2, 2)
        p.drawPath(path)
        p.setPen(QPen(c, 1))
        p.setBrush(QColor(c))
        path2 = QPainterPath()
        path2.addRoundedRect(QRectF(s * 0.15, s * 0.1, s * 0.6, s * 0.55), 2, 2)
        p.drawPath(path2)

    @staticmethod
    def _draw_paste(p, s):
        c = QColor(Nord.frost_3)
        p.setPen(QPen(c.darker(130), 1))
        p.setBrush(QColor(c))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.2, s * 0.2, s * 0.6, s * 0.7), 2, 2)
        p.drawPath(path)
        p.setBrush(QColor(Nord.polar_night_1))
        p.setPen(QPen(c, 1))
        p.drawRect(int(s * 0.3), int(s * 0.1), int(s * 0.4), int(s * 0.2))

    @staticmethod
    def _draw_world(p, s):
        c = QColor(Nord.aurora_green)
        p.setPen(QPen(c, 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(s * 0.1, s * 0.1, s * 0.8, s * 0.8))
        p.drawEllipse(QRectF(s * 0.1, s * 0.3, s * 0.8, s * 0.4))
        p.drawLine(int(s * 0.1), int(s * 0.5), int(s * 0.9), int(s * 0.5))
        p.drawEllipse(QRectF(s * 0.3, s * 0.1, s * 0.4, s * 0.8))

    @staticmethod
    def _draw_terminal(p, s):
        c = QColor(Nord.aurora_green)
        p.setPen(QPen(c, 1.5))
        p.setBrush(QColor(Nord.polar_night_1))
        path = QPainterPath()
        path.addRoundedRect(QRectF(s * 0.1, s * 0.1, s * 0.8, s * 0.8), 3, 3)
        p.drawPath(path)
        p.setPen(QPen(c, 2))
        p.drawLine(int(s * 0.25), int(s * 0.35), int(s * 0.4), int(s * 0.5))
        p.drawLine(int(s * 0.25), int(s * 0.65), int(s * 0.4), int(s * 0.5))
        p.drawLine(int(s * 0.5), int(s * 0.65), int(s * 0.7), int(s * 0.65))


_ANSI_RE = re.compile(r'\x1b\[([\d;]*)m')

ANSI_COLORS = {
    '30': Nord.polar_night_1, '31': Nord.aurora_red, '32': Nord.aurora_green,
    '33': Nord.aurora_yellow, '34': Nord.frost_4, '35': Nord.aurora_pink,
    '36': Nord.frost_1, '37': Nord.snow_storm_1,
    '90': Nord.polar_night_4, '91': Nord.aurora_red, '92': Nord.aurora_green,
    '93': Nord.aurora_yellow, '94': Nord.frost_3, '95': Nord.aurora_pink,
    '96': Nord.frost_2, '97': Nord.snow_storm_3,
}
ANSI_BG = {
    '40': Nord.polar_night_1, '41': Nord.aurora_red, '42': Nord.aurora_green,
    '43': Nord.aurora_yellow, '44': Nord.frost_4, '45': Nord.aurora_pink,
    '46': Nord.frost_1, '47': Nord.snow_storm_2,
}


def parse_ansi(text: str):
    parts = _ANSI_RE.split(text)
    segments = []
    fg = None
    bg = None
    bold = False
    for i, part in enumerate(parts):
        if i % 2 == 0:
            segments.append((fg, bg, bold, part))
        else:
            codes = part.split(';') if part else []
            for c in codes:
                if c == '' or c == '0':
                    fg = bg = None
                    bold = False
                elif c == '1':
                    bold = True
                elif c == '22':
                    bold = False
                elif c in ANSI_COLORS:
                    fg = ANSI_COLORS[c]
                elif c in ANSI_BG:
                    bg = ANSI_BG[c]
    return segments


class LogHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        fmt_info = QTextCharFormat()
        fmt_info.setForeground(QColor(Nord.aurora_green))
        self._rules.append((re.compile(r'\[?INFO\]?|\[?\d+:\d+:\d+\]?.*\[?\w+.*\]?.*:'), fmt_info))

        fmt_warn = QTextCharFormat()
        fmt_warn.setForeground(QColor(Nord.aurora_yellow))
        self._rules.append((re.compile(r'\[?WARN\]?|\[?WARNING\]?'), fmt_warn))

        fmt_error = QTextCharFormat()
        fmt_error.setForeground(QColor(Nord.aurora_red))
        self._rules.append((re.compile(r'\[?ERROR\]?|\[?SEVERE\]?|\[?FATAL\]?'), fmt_error))

        fmt_fatal = QTextCharFormat()
        fmt_fatal.setForeground(QColor(Nord.aurora_red))
        fmt_fatal.setFontWeight(QFont.Bold)
        self._rules.append((re.compile(r'\[?FATAL\]?'), fmt_fatal))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_paint_event(event)


class LineNumberTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self.document().blockCountChanged.connect(self._update_line_number_width)
        self.textChanged.connect(self._update_line_number_width)
        self.verticalScrollBar().valueChanged.connect(
            lambda v: self._update_line_number_width()
        )
        QTimer.singleShot(0, self._update_line_number_width)

    def line_number_width(self):
        digits = len(str(max(1, self.document().blockCount())))
        return 12 + digits * 10

    def _update_line_number_width(self):
        w = self.line_number_width()
        self.setViewportMargins(w, 0, 0, 0)
        self._line_number_area.update()

    def line_number_paint_event(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor(Nord.polar_night_2))
        painter.setPen(QColor(Nord.polar_night_4))

        block = self.document().begin()
        line_number = 1
        fm = QFontMetrics(self.font())
        viewport_offset = self.verticalScrollBar().value()
        doc_margin = self.document().documentMargin()
        top = viewport_offset + doc_margin
        lw = self.line_number_width()

        while block.isValid():
            if block.isVisible():
                block_rect = self.document().documentLayout().blockBoundingRect(block)
                block_top = int(top)
                block_height = int(block_rect.height())
                if block_top + block_height >= event.rect().top() and block_top <= event.rect().bottom():
                    painter.drawText(
                        2, block_top,
                        lw - 4, fm.height(),
                        Qt.AlignRight | Qt.AlignVCenter,
                        str(line_number)
                    )
                top += block_height
                line_number += 1
            block = block.next()

        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_width(), cr.height())
        )


class ConnectTab(QWidget):
    instance_selected = pyqtSignal(str, str)
    connection_status = pyqtSignal(str)

    def __init__(self, api, config, parent=None):
        super().__init__(parent)
        self.api = api
        self.config = config
        self._init_ui()
        self._prefill()

    def _prefill(self):
        if self.config.apikey:
            self.apikey.setText(self.config.apikey)
        if self.config.username:
            self.username.setText(self.config.username)
        if self.config.password:
            self.password.setText(self.config.password)
        if self.config.daemon_id and self.config.instance_uuid:
            self.instance_combo.addItem(
                f"{self.config.daemon_id[:16]}.../{self.config.instance_uuid[:16]}...",
                (self.config.daemon_id, self.config.instance_uuid)
            )
            self.select_btn.setEnabled(True)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("MCSM Tools")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {Nord.frost_2};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("MCSManager 管理客户端")
        subtitle.setStyleSheet(f"font-size: 13px; color: {Nord.fg_dim};")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        group = QGroupBox("面板连接")
        form = QFormLayout(group)
        form.setSpacing(8)

        self.base_url = QLineEdit(self.config.base_url)
        self.base_url.setPlaceholderText("https://mcsm.example.com")
        form.addRow("面板地址:", self.base_url)

        sep = QLabel()
        sep.setStyleSheet(f"color: {Nord.fg_dim}; padding: 4px 0;")
        sep.setText("\u2501" * 30 + " 认证方式 (二选一) " + "\u2501" * 30)
        sep.setAlignment(Qt.AlignCenter)
        form.addRow(sep)

        self.apikey = QLineEdit(self.config.apikey)
        self.apikey.setPlaceholderText("API Key (推荐)")
        form.addRow("API Key:", self.apikey)

        self.username = QLineEdit(self.config.username)
        self.username.setPlaceholderText("用户名")
        form.addRow("用户名:", self.username)

        self.password = QLineEdit(self.config.password)
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("密码")
        form.addRow("密码:", self.password)

        layout.addWidget(group)

        self.connect_btn = QPushButton("连接面板")
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Nord.frost_4};
                color: {Nord.snow_storm_3};
                font-weight: bold;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {Nord.frost_3};
            }}
            QPushButton:pressed {{
                background-color: {Nord.frost_2};
            }}
        """)
        self.connect_btn.clicked.connect(self._connect)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        inst_group = QGroupBox("实例选择")
        inst_form = QFormLayout(inst_group)
        self.instance_combo = QComboBox()
        self.instance_combo.setMinimumWidth(400)
        inst_form.addRow("选择实例:", self.instance_combo)
        self.select_btn = QPushButton("选择此实例")
        self.select_btn.clicked.connect(self._select_instance)
        self.select_btn.setEnabled(False)
        inst_form.addRow(self.select_btn)
        layout.addWidget(inst_group)

        layout.addStretch()

    def _connect(self):
        self.config.base_url = self.base_url.text().strip()
        self.api.set_base_url(self.config.base_url)

        apikey = self.apikey.text().strip()
        username = self.username.text().strip()
        password = self.password.text().strip()

        self.status_label.setStyleSheet(f"color: {Nord.aurora_yellow};")
        self.status_label.setText("正在连接...")
        self.connect_btn.setEnabled(False)

        from PyQt5.QtCore import QCoreApplication
        QCoreApplication.processEvents()

        ok = False
        if apikey:
            ok = self.api.login_with_apikey(apikey)
            if ok:
                self.config.apikey = apikey
        elif username and password:
            ok = self.api.login(username, password)
            if ok:
                self.config.username = username
                self.config.password = password

        if not ok:
            self.status_label.setStyleSheet(f"color: {Nord.aurora_red};")
            self.status_label.setText(f"连接失败: {self.api.last_error or '认证失败'}")
            self.connect_btn.setEnabled(True)
            return

        instances = self.api.list_instances()
        self.instance_combo.clear()
        if instances:
            for inst in instances:
                name = inst.get("nickname", inst.get("instanceUuid", "?"))
                did = inst.get("daemonId", "")
                iuid = inst.get("instanceUuid", "")
                self.instance_combo.addItem(f"{name}", (did, iuid))
            self.select_btn.setEnabled(True)
            self.status_label.setStyleSheet(f"color: {Nord.aurora_green};")
            self.status_label.setText(f"已连接: {self.api.base_url} ({len(instances)} 个实例)")
            self.connection_status.emit(f"已连接: {self.api.base_url}")
        else:
            self.status_label.setStyleSheet(f"color: {Nord.aurora_yellow};")
            self.status_label.setText("已认证，但未找到任何实例")
            self.select_btn.setEnabled(False)
            self.connection_status.emit("已认证，无实例")

        self.connect_btn.setEnabled(True)
        save_config(self.config)

    def _select_instance(self):
        idx = self.instance_combo.currentIndex()
        if idx < 0:
            return
        data = self.instance_combo.itemData(idx)
        if data:
            daemon_id, instance_uuid = data
            self.config.daemon_id = daemon_id
            self.config.instance_uuid = instance_uuid
            save_config(self.config)
            self.instance_selected.emit(daemon_id, instance_uuid)


class TerminalTab(QWidget):
    output_signal = pyqtSignal(str)
    disconnect_signal = pyqtSignal()

    def __init__(self, api, terminal_mgr, config, parent=None):
        super().__init__(parent)
        self.api = api
        self.terminal_mgr = terminal_mgr
        self.config = config
        self.command_history = CommandHistory()
        self._output_buffer = ""
        self._init_ui()
        self._register_callbacks()
        self.output_signal.connect(self._on_output_threadsafe)
        self.disconnect_signal.connect(self._on_disconnect_threadsafe)

    def _register_callbacks(self):
        self.terminal_mgr.on_output = lambda text: self.output_signal.emit(text)
        self.terminal_mgr.on_disconnect = lambda: self.disconnect_signal.emit()

    def _append_ansi_text(self, text: str):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)

        for fg, bg, bold, segment in parse_ansi(text):
            if not segment:
                continue
            fmt = QTextCharFormat()
            if fg:
                fmt.setForeground(QColor(fg))
            if bg:
                fmt.setBackground(QColor(bg))
            if bold:
                fmt.setFontWeight(QFont.Bold)
            cursor.insertText(segment, fmt)

        sb = self.output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_output_threadsafe(self, text: str):
        self._output_buffer += text
        if '\n' in self._output_buffer:
            lines = self._output_buffer.split('\n')
            self._output_buffer = lines.pop()
            for line in lines:
                self._append_ansi_text(line + '\n')

    def _on_disconnect_threadsafe(self):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(Nord.aurora_red))
        cursor.insertText("\n[连接已断开]\n", fmt)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("JetBrains Mono", 11))
        self.output.setStyleSheet("background-color: #2E3440; color: #D8DEE9; border: none;")
        layout.addWidget(self.output)

        cmd_layout = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("输入命令... (Ctrl+R 搜索, Ctrl+D 收藏, \u2191\u2193 历史)")
        self.cmd_input.returnPressed.connect(self._send_command)
        cmd_layout.addWidget(self.cmd_input)

        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self._send_command)
        cmd_layout.addWidget(self.send_btn)

        self.help_btn = QPushButton("!help")
        self.help_btn.clicked.connect(lambda: self._send_builtin("!help"))
        cmd_layout.addWidget(self.help_btn)

        self.clear_btn = QPushButton("清屏")
        self.clear_btn.clicked.connect(self._clear_screen)
        cmd_layout.addWidget(self.clear_btn)

        layout.addLayout(cmd_layout)

        self.input_history = []
        self.history_index = -1

        self.cmd_input.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.cmd_input:
            if event.type() == QEvent.KeyPress:
                key = event.key()
                if key == Qt.Key_Up:
                    self._history_prev()
                    return True
                elif key == Qt.Key_Down:
                    self._history_next()
                    return True
                elif key == Qt.Key_R and event.modifiers() & Qt.ControlModifier:
                    self._search_history()
                    return True
                elif key == Qt.Key_D and event.modifiers() & Qt.ControlModifier:
                    self._toggle_favorite()
                    return True
        return super().eventFilter(obj, event)

    def _history_prev(self):
        if self.input_history:
            self.history_index = max(0, self.history_index - 1)
            self.cmd_input.setText(self.input_history[self.history_index])

    def _history_next(self):
        if self.input_history:
            self.history_index = min(len(self.input_history), self.history_index + 1)
            if self.history_index >= len(self.input_history):
                self.cmd_input.clear()
            else:
                self.cmd_input.setText(self.input_history[self.history_index])

    def _search_history(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("命令历史搜索")
        dlg.resize(500, 400)
        layout = QVBoxLayout(dlg)
        search = QLineEdit()
        search.setPlaceholderText("输入关键词搜索...")
        layout.addWidget(search)
        lst = QListWidget()
        layout.addWidget(lst)
        results = self.command_history.search("")
        for c in results:
            lst.addItem(QListWidgetItem(c))
        def filter_cmds(text):
            lst.clear()
            for c in self.command_history.search(text):
                lst.addItem(QListWidgetItem(c))
        search.textChanged.connect(filter_cmds)
        def on_accept():
            if lst.currentItem():
                self.cmd_input.setText(lst.currentItem().text())
                dlg.accept()
        lst.itemDoubleClicked.connect(lambda: on_accept())
        dlg.exec_()

    def _toggle_favorite(self):
        text = self.cmd_input.text().strip()
        if not text:
            favs = self.command_history.favorites
            if favs:
                self._show_favorites()
            return
        fav_cmds = [f["cmd"] for f in self.command_history.favorites]
        if text in fav_cmds:
            self.command_history.remove_favorite(text)
            self.output.append(f"\n[已取消收藏: {text}]\n")
        else:
            self.command_history.add_favorite(text)
            self.output.append(f"\n[已收藏: {text}]\n")

    def _show_favorites(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("收藏命令")
        dlg.resize(400, 300)
        layout = QVBoxLayout(dlg)
        lst = QListWidget()
        for f in self.command_history.favorites:
            lst.addItem(QListWidgetItem(f["cmd"]))
        layout.addWidget(lst)
        def use_fav():
            if lst.currentItem():
                self.cmd_input.setText(lst.currentItem().text())
                dlg.accept()
        btn = QPushButton("使用选中")
        btn.clicked.connect(use_fav)
        layout.addWidget(btn)
        dlg.exec_()

    def _send_builtin(self, cmd: str):
        self.cmd_input.setText(cmd)
        self._send_command()

    def _clear_screen(self):
        self.output.clear()

    def _send_command(self):
        text = self.cmd_input.text().strip()
        if not text:
            return

        if text == "!clear":
            self._clear_screen()
            self.cmd_input.clear()
            return

        if text == "!help":
            help_text = (
                "内置命令:\n"
                "  !clear      - 清屏\n"
                "  !help       - 显示帮助\n"
            )
            cursor = self.output.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(help_text + "\n")
            self.cmd_input.clear()
            return

        if self.terminal_mgr and self.terminal_mgr.is_connected:
            self.terminal_mgr.send_command(text + "\n")
        self.cmd_input.clear()
        self.input_history.append(text)
        self.history_index = len(self.input_history)
        self.command_history.add(text)


class RemoteFileModel:
    def __init__(self, api, daemon_id, instance_uuid):
        self.api = api
        self.daemon_id = daemon_id
        self.instance_uuid = instance_uuid
        self.current_path = "/"


class FileManagerTab(QWidget):
    def __init__(self, api, daemon_id, instance_uuid, parent=None):
        super().__init__(parent)
        self.api = api
        self.daemon_id = daemon_id
        self.instance_uuid = instance_uuid
        self.current_path = "/"
        self._clipboard = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Horizontal)

        local_panel = QWidget()
        local_layout = QVBoxLayout(local_panel)
        local_layout.setContentsMargins(0, 0, 2, 0)
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("本地文件"))
        hdr.addStretch()
        local_layout.addLayout(hdr)

        local_nav = QHBoxLayout()
        self.local_path = QLineEdit(os.path.expanduser("~"))
        self.local_path.returnPressed.connect(self._load_local)
        local_nav.addWidget(self.local_path)
        self.local_go = QPushButton(AppIcons.icon("home"), "")
        self.local_go.setToolTip("刷新")
        self.local_go.clicked.connect(self._load_local)
        local_nav.addWidget(self.local_go)
        local_layout.addLayout(local_nav)

        self.local_tree = QTreeWidget()
        self.local_tree.setHeaderLabels(["名称", "大小", "修改时间"])
        self.local_tree.setColumnWidth(0, 200)
        self.local_tree.setColumnWidth(1, 70)
        self.local_tree.setRootIsDecorated(False)
        self.local_tree.setAlternatingRowColors(True)
        self.local_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.local_tree.customContextMenuRequested.connect(self._local_context_menu)
        self.local_tree.itemDoubleClicked.connect(self._local_item_double_clicked)
        local_layout.addWidget(self.local_tree)

        splitter.addWidget(local_panel)

        remote_panel = QWidget()
        remote_layout = QVBoxLayout(remote_panel)
        remote_layout.setContentsMargins(2, 0, 0, 0)
        hdr2 = QHBoxLayout()
        hdr2.addWidget(QLabel("远程文件"))
        hdr2.addStretch()
        remote_layout.addLayout(hdr2)

        nav_layout = QHBoxLayout()
        self.path_edit = QLineEdit("/")
        self.path_edit.returnPressed.connect(self._navigate_to_path)
        nav_layout.addWidget(self.path_edit)
        self.go_btn = QPushButton(AppIcons.icon("refresh"), "")
        self.go_btn.setToolTip("前往")
        self.go_btn.clicked.connect(self._navigate_to_path)
        nav_layout.addWidget(self.go_btn)
        self.up_btn = QPushButton(AppIcons.icon("up"), "")
        self.up_btn.setToolTip("上级目录")
        self.up_btn.clicked.connect(self._go_up)
        nav_layout.addWidget(self.up_btn)
        self.refresh_btn = QPushButton(AppIcons.icon("refresh"), "")
        self.refresh_btn.setToolTip("刷新")
        self.refresh_btn.clicked.connect(lambda: self._load_files(self.current_path))
        nav_layout.addWidget(self.refresh_btn)
        remote_layout.addLayout(nav_layout)

        action_layout = QHBoxLayout()
        self.upload_btn = QPushButton(AppIcons.icon("upload"), "上传")
        self.upload_btn.clicked.connect(self._upload_file)
        action_layout.addWidget(self.upload_btn)
        self.mkdir_btn = QPushButton(AppIcons.icon("add"), "新建")
        self.mkdir_btn.clicked.connect(self._mkdir)
        action_layout.addWidget(self.mkdir_btn)
        self.del_btn = QPushButton(AppIcons.icon("delete"), "删除")
        self.del_btn.clicked.connect(self._delete_selected)
        action_layout.addWidget(self.del_btn)
        self.dl_world_btn = QPushButton(AppIcons.icon("world"), "世界")
        self.dl_world_btn.clicked.connect(self._download_world)
        action_layout.addWidget(self.dl_world_btn)
        remote_layout.addLayout(action_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "大小", "修改时间", "类型"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 140)
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._remote_context_menu)
        self.tree.itemDoubleClicked.connect(self._item_double_clicked)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        remote_layout.addWidget(self.tree)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        remote_layout.addWidget(self.progress)

        splitter.addWidget(remote_panel)
        splitter.setSizes([350, 650])
        layout.addWidget(splitter)

        self._load_local()

    def _load_local(self, path=None):
        if path:
            self.local_path.setText(path)
        path = os.path.expanduser(self.local_path.text().strip())
        if not os.path.isdir(path):
            return
        self.local_tree.clear()
        try:
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                is_dir = os.path.isdir(full)
                try:
                    size = os.path.getsize(full) if not is_dir else 0
                    mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    size = 0
                    mtime = ""
                ti = QTreeWidgetItem([name, self._format_size(size) if not is_dir else "", mtime])
                ti.setData(0, Qt.UserRole, {"is_dir": is_dir, "name": name, "path": full})
                ti.setIcon(0, self._file_icon(name, is_dir))
                font = ti.font(0)
                if is_dir:
                    font.setBold(True)
                    ti.setForeground(0, QColor(Nord.frost_2))
                ti.setFont(0, font)
                self.local_tree.addTopLevelItem(ti)
        except PermissionError:
            pass

    def _local_item_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data and data.get("is_dir"):
            self._load_local(data["path"])

    def _local_context_menu(self, pos):
        item = self.local_tree.itemAt(pos)
        menu = QMenu()
        upload_action = menu.addAction(AppIcons.icon("upload"), "上传到当前远程目录")
        upload_action.triggered.connect(lambda: self._upload_local_item(item))
        menu.exec_(self.local_tree.viewport().mapToGlobal(pos))

    def _upload_local_item(self, item):
        if not item:
            return
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        local_path = data["path"]
        self.progress.setVisible(True)
        self.progress.setValue(0)
        def cb(pos, total):
            if total > 0:
                self.progress.setMaximum(total)
                self.progress.setValue(pos)
            QApplication.processEvents()
        if data["is_dir"]:
            self._upload_dir(local_path, self.current_path)
        else:
            self.api.upload_file(local_path, self.current_path, self.daemon_id, self.instance_uuid, cb)
        self.progress.setVisible(False)
        self._load_files(self.current_path)

    def _upload_dir(self, local_dir, remote_dir):
        for name in os.listdir(local_dir):
            local_path = os.path.join(local_dir, name)
            remote_path = remote_dir.rstrip("/") + "/" + name
            if os.path.isdir(local_path):
                self.api.create_directory(self.daemon_id, self.instance_uuid, remote_path)
                self._upload_dir(local_path, remote_path)
            else:
                self.api.upload_file(local_path, remote_dir, self.daemon_id, self.instance_uuid)

    @staticmethod
    def _file_icon(name, is_dir):
        if is_dir:
            return AppIcons.icon("folder")
        ext = os.path.splitext(name)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"):
            return AppIcons.icon("image")
        if ext in (".zip", ".tar", ".gz", ".7z", ".rar"):
            return AppIcons.icon("archive")
        return AppIcons.icon("file")

    def _load_files(self, path: str):
        self.current_path = path
        self.path_edit.setText(path)
        self.tree.clear()
        items = self.api.list_files(self.daemon_id, self.instance_uuid, path)
        if items is None:
            return
        for item in items:
            name = item.get("name", "?")
            is_dir = item.get("isDir", False)
            size = item.get("size", item.get("fileSize", 0))
            mtime = item.get("modTime", item.get("mtime", ""))
            if isinstance(size, (int, float)):
                size_str = self._format_size(size)
            else:
                size_str = str(size)
            typ = "文件夹" if is_dir else "文件"
            ti = QTreeWidgetItem([name, size_str, str(mtime), typ])
            ti.setData(0, Qt.UserRole, {"is_dir": is_dir, "name": name})
            ti.setIcon(0, self._file_icon(name, is_dir))
            font = ti.font(0)
            if is_dir:
                font.setBold(True)
                ti.setForeground(0, QColor(Nord.frost_2))
            ti.setFont(0, font)
            self.tree.addTopLevelItem(ti)

    def _navigate_to_path(self):
        path = self.path_edit.text().strip()
        if path:
            self._load_files(path)

    def _go_up(self):
        parent = "/".join(self.current_path.rstrip("/").split("/")[:-1])
        if not parent:
            parent = "/"
        self._load_files(parent)

    def _item_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data and data.get("is_dir"):
            name = data["name"]
            path = self.current_path.rstrip("/") + "/" + name
            self._load_files(path)
        else:
            self._download_item(item)

    def _upload_file(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "选择文件上传")
        if not fpath:
            return
        self.progress.setVisible(True)
        self.progress.setValue(0)
        def cb(pos, total):
            if total > 0:
                self.progress.setMaximum(total)
                self.progress.setValue(pos)
            QApplication.processEvents()
        ok = self.api.upload_file(fpath, self.current_path, self.daemon_id, self.instance_uuid, cb)
        self.progress.setVisible(False)
        if ok:
            self._load_files(self.current_path)

    def _mkdir(self):
        name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名称:")
        if ok and name.strip():
            path = self.current_path.rstrip("/") + "/" + name.strip()
            if self.api.create_directory(self.daemon_id, self.instance_uuid, path):
                self._load_files(self.current_path)

    def _delete_selected(self):
        items = self.tree.selectedItems()
        if not items:
            return
        targets = []
        for item in items:
            data = item.data(0, Qt.UserRole)
            if data:
                targets.append(self.current_path.rstrip("/") + "/" + data["name"])
        if not targets:
            return
        r = QMessageBox.question(self, "确认删除", f"删除 {len(targets)} 个文件/文件夹？\n此操作不可撤销！",
                                 QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            if self.api.delete_files(self.daemon_id, self.instance_uuid, targets):
                self._load_files(self.current_path)

    def _download_world(self):
        for world_dir in ["world", "worlds"]:
            path = self.current_path.rstrip("/") + "/" + world_dir
            info = self.api.get_file_info(self.daemon_id, self.instance_uuid, path)
            if info and info.get("isDir"):
                local, _ = QFileDialog.getSaveFileName(self, "保存世界压缩包", f"{world_dir}.zip",
                                                       "ZIP Files (*.zip)")
                if not local:
                    return
                self.progress.setVisible(True)
                self.progress.setValue(0)
                zip_remote = f"/{world_dir}.zip"
                if self.api.compress_files(self.daemon_id, self.instance_uuid, "/", [world_dir]):
                    def cb(pos, total):
                        if total > 0:
                            self.progress.setMaximum(total)
                            self.progress.setValue(pos)
                        QApplication.processEvents()
                    if self.api.download_file(self.daemon_id, self.instance_uuid, zip_remote, local, cb):
                        self.progress.setVisible(False)
                        QMessageBox.information(self, "完成", f"世界下载完成: {local}")
                        return
                self.progress.setVisible(False)
                QMessageBox.warning(self, "失败", "下载世界失败")
                return
        QMessageBox.warning(self, "未找到", "未找到 world/worlds 目录")

    def _remote_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        menu = QMenu()
        dl_action = menu.addAction(AppIcons.icon("download"), "下载")
        dl_action.triggered.connect(lambda: self._download_item(item))

        edit_action = menu.addAction(AppIcons.icon("edit"), "编辑 (文本文件)")
        edit_action.triggered.connect(lambda: self._edit_remote_file(item))

        menu.addSeparator()
        cut_action = menu.addAction(AppIcons.icon("cut"), "剪切")
        cut_action.triggered.connect(lambda: self._clipboard_cut(item))
        copy_action = menu.addAction(AppIcons.icon("copy"), "复制")
        copy_action.triggered.connect(lambda: self._clipboard_copy(item))

        paste_action = menu.addAction(AppIcons.icon("paste"), "粘贴")
        paste_action.setEnabled(self._clipboard is not None)
        paste_action.triggered.connect(self._clipboard_paste)

        menu.addSeparator()
        compress_action = menu.addAction(AppIcons.icon("compress"), "压缩")
        compress_action.triggered.connect(lambda: self._compress_items([item]))
        extract_action = menu.addAction(AppIcons.icon("extract"), "解压")
        extract_action.triggered.connect(lambda: self._extract_item(item))

        menu.addSeparator()
        rename_action = menu.addAction(AppIcons.icon("rename"), "重命名")
        rename_action.triggered.connect(lambda: self._rename_item(item))

        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def _download_item(self, item):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        local, _ = QFileDialog.getSaveFileName(self, "保存文件", data.get("name", "file"))
        if not local:
            return
        fpath = self.current_path.rstrip("/") + "/" + data["name"]
        self.progress.setVisible(True)
        self.progress.setValue(0)
        def cb(pos, total):
            if total > 0:
                self.progress.setMaximum(total)
                self.progress.setValue(pos)
            QApplication.processEvents()
        ok = self.api.download_file(self.daemon_id, self.instance_uuid, fpath, local, cb)
        self.progress.setVisible(False)
        if ok:
            QMessageBox.information(self, "完成", f"下载完成: {local}")

    def _edit_remote_file(self, item):
        data = item.data(0, Qt.UserRole)
        if not data or data.get("is_dir"):
            QMessageBox.warning(self, "提示", "只能编辑文件")
            return
        fpath = self.current_path.rstrip("/") + "/" + data["name"]
        tmp = os.path.join(tempfile.gettempdir(), f"mcsm_edit_{data['name']}")
        ok = self.api.download_file(self.daemon_id, self.instance_uuid, fpath, tmp)
        if not ok:
            QMessageBox.warning(self, "失败", "下载文件失败")
            return
        try:
            with open(tmp, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            QMessageBox.warning(self, "失败", "读取文件失败")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"编辑: {data['name']}")
        dlg.resize(700, 500)
        layout = QVBoxLayout(dlg)
        editor = QTextEdit()
        editor.setPlainText(content)
        editor.setFont(QFont("JetBrains Mono", 11))
        layout.addWidget(editor)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        result = {"saved": False}
        def on_save():
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
            def cb(pos, total):
                QApplication.processEvents()
            if self.api.upload_file(tmp, self.current_path, self.daemon_id, self.instance_uuid, cb):
                result["saved"] = True
                dlg.accept()
            else:
                QMessageBox.warning(dlg, "失败", "上传文件失败")
        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec_()
        try:
            os.unlink(tmp)
        except Exception:
            pass
        if result["saved"]:
            QMessageBox.information(self, "完成", "文件已保存")

    def _clipboard_cut(self, item):
        data = item.data(0, Qt.UserRole)
        if data:
            self._clipboard = {
                "action": "cut",
                "name": data["name"],
                "path": self.current_path.rstrip("/") + "/" + data["name"],
            }

    def _clipboard_copy(self, item):
        data = item.data(0, Qt.UserRole)
        if data:
            self._clipboard = {
                "action": "copy",
                "name": data["name"],
                "path": self.current_path.rstrip("/") + "/" + data["name"],
            }

    def _clipboard_paste(self):
        if not self._clipboard:
            return
        src = self._clipboard["path"]
        dst = self.current_path.rstrip("/") + "/" + self._clipboard["name"]
        if self._clipboard["action"] == "cut":
            if src != dst:
                ok = self.api.move_files(self.daemon_id, self.instance_uuid, [[src, dst]])
                if ok:
                    self._load_files(self.current_path)
        elif self._clipboard["action"] == "copy":
            ok = self.api.compress_files(self.daemon_id, self.instance_uuid, "/", [src.lstrip("/")])
            if ok:
                zip_src = f"/{self._clipboard['name']}.zip"
                ok2 = self.api.decompress_files(self.daemon_id, self.instance_uuid, zip_src, dst)
                if ok2:
                    self._load_files(self.current_path)
        self._clipboard = None

    def _compress_items(self, items):
        targets = []
        for item in items:
            data = item.data(0, Qt.UserRole)
            if data:
                targets.append(self.current_path.rstrip("/") + "/" + data["name"])
        if not targets:
            return
        name, ok = QInputDialog.getText(self, "压缩", "压缩包名称 (不含扩展名):", text="archive")
        if ok and name.strip():
            ok = self.api.compress_files(
                self.daemon_id, self.instance_uuid,
                self.current_path,
                [t.replace(self.current_path.rstrip("/") + "/", "") for t in targets]
            )
            if ok:
                self._load_files(self.current_path)

    def _extract_item(self, item):
        data = item.data(0, Qt.UserRole)
        if not data or data.get("is_dir"):
            QMessageBox.warning(self, "提示", "请选择一个压缩文件")
            return
        fpath = self.current_path.rstrip("/") + "/" + data["name"]
        ok = self.api.decompress_files(self.daemon_id, self.instance_uuid, fpath, self.current_path)
        if ok:
            self._load_files(self.current_path)
        else:
            QMessageBox.warning(self, "失败", "解压失败")

    def _rename_item(self, item):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        new_name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=data["name"])
        if ok and new_name.strip() and new_name.strip() != data["name"]:
            src = self.current_path.rstrip("/") + "/" + data["name"]
            dst = self.current_path.rstrip("/") + "/" + new_name.strip()
            ok = self.api.move_files(self.daemon_id, self.instance_uuid, [[src, dst]])
            if ok:
                self._load_files(self.current_path)

    @staticmethod
    def _format_size(size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class LogViewerTab(QWidget):
    LOG_DIRS = ["/logs", "/crash-reports", "/"]

    def __init__(self, api, daemon_id, instance_uuid, parent=None):
        super().__init__(parent)
        self.api = api
        self.daemon_id = daemon_id
        self.instance_uuid = instance_uuid
        self._log_text = ""
        self._init_ui()

    @staticmethod
    def _is_log_file(name: str) -> bool:
        if name == "eula.txt":
            return False
        return name.endswith(".log") or name.endswith(".txt") or name.endswith(".gz") or "crash" in name.lower()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        ctrl_layout = QHBoxLayout()
        self.file_combo = QComboBox()
        self.file_combo.setMinimumWidth(300)
        self.file_combo.currentIndexChanged.connect(self._load_selected_log)
        ctrl_layout.addWidget(self.file_combo)
        self.refresh_list_btn = QPushButton("刷新列表")
        self.refresh_list_btn.clicked.connect(self._refresh_file_list)
        ctrl_layout.addWidget(self.refresh_list_btn)
        self.refresh_btn = QPushButton("刷新内容")
        self.refresh_btn.clicked.connect(self._refresh_content)
        ctrl_layout.addWidget(self.refresh_btn)
        layout.addLayout(ctrl_layout)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("关键词过滤...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        search_layout.addWidget(self.filter_edit)

        self.wrap_check = QCheckBox("自动换行")
        self.wrap_check.setChecked(False)
        self.wrap_check.toggled.connect(self._toggle_wrap)

        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["全部", "/logs", "/crash-reports", "/"])
        self.dir_combo.currentIndexChanged.connect(self._refresh_file_list)
        search_layout.addWidget(QLabel("目录:"))
        search_layout.addWidget(self.dir_combo)
        search_layout.addWidget(self.wrap_check)
        layout.addLayout(search_layout)

        self.log_output = LineNumberTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("JetBrains Mono", 11))
        self.log_output.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._highlighter = LogHighlighter(self.log_output.document())
        layout.addWidget(self.log_output)

        self._refresh_file_list()

    def _toggle_wrap(self, checked):
        self.log_output.setLineWrapMode(
            QPlainTextEdit.WidgetWidth if checked else QPlainTextEdit.NoWrap
        )

    def _refresh_file_list(self):
        self.file_combo.clear()
        all_files = []
        dir_idx = self.dir_combo.currentIndex()
        dirs = self.LOG_DIRS if dir_idx == 0 else [self.LOG_DIRS[dir_idx - 1]]
        for d in dirs:
            items = self.api.list_files(self.daemon_id, self.instance_uuid, d)
            if items:
                for item in items:
                    name = item.get("name", "")
                    if item.get("isDir", False):
                        continue
                    if self._is_log_file(name):
                        full = d.rstrip('/') + '/' + name if d != '/' else '/' + name
                        all_files.append(full)
        if all_files:
            all_files.sort()
            self.file_combo.addItems(all_files)
        else:
            self.file_combo.addItem("未找到日志文件")

    def _load_selected_log(self):
        filename = self.file_combo.currentText()
        if not filename or filename == "未找到日志文件":
            return
        is_gz = filename.endswith('.gz')
        tmp = os.path.join(tempfile.gettempdir(), "mcsm_log_tmp" + (".gz" if is_gz else ".log"))
        ok = self.api.download_file(self.daemon_id, self.instance_uuid, filename, tmp)
        if ok:
            try:
                if is_gz:
                    import gzip
                    with gzip.open(tmp, 'rt', encoding='utf-8', errors='replace') as f:
                        self._log_text = f.read()
                else:
                    with open(tmp, encoding='utf-8', errors='replace') as f:
                        self._log_text = f.read()
            except Exception:
                self._log_text = "读取文件失败"
            self._apply_filter()
        try:
            os.unlink(tmp)
        except Exception:
            pass

    def _refresh_content(self):
        self._load_selected_log()

    def _apply_filter(self):
        keyword = self.filter_edit.text().strip().lower()
        if not self._log_text:
            self.log_output.clear()
            return
        if not keyword:
            self.log_output.setPlainText(self._log_text)
        else:
            lines = self._log_text.split('\n')
            filtered = '\n'.join(line for line in lines if keyword in line.lower())
            self.log_output.setPlainText(filtered)
        sb = self.log_output.verticalScrollBar()
        sb.setValue(sb.maximum())


class BackupDirDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择备份目录")
        self.setMinimumWidth(350)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("选择要备份的目录:"))
        self.checks = {}
        for name in ["world", "plugins", "mods", "config", "scripts"]:
            cb = QCheckBox(name)
            if name == "world":
                cb.setChecked(True)
            self.checks[name] = cb
            layout.addWidget(cb)
        layout.addSpacing(10)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("备份名称:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("留空自动命名")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_dirs(self):
        return [name for name, cb in self.checks.items() if cb.isChecked()]

    def get_backup_name(self):
        name = self.name_input.text().strip()
        return name or None


class BackupTab(QWidget):
    def __init__(self, api, daemon_id, instance_uuid, parent=None):
        super().__init__(parent)
        self.api = api
        self.daemon_id = daemon_id
        self.instance_uuid = instance_uuid
        self.backup_path = "/backups"
        self._init_ui()
        self._refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        ctrl_layout = QHBoxLayout()
        self.create_btn = QPushButton("创建备份")
        self.create_btn.clicked.connect(self._create_backup)
        ctrl_layout.addWidget(self.create_btn)
        self.dl_btn = QPushButton("下载选中")
        self.dl_btn.clicked.connect(self._download_selected)
        ctrl_layout.addWidget(self.dl_btn)
        self.del_btn = QPushButton("删除选中")
        self.del_btn.clicked.connect(self._delete_selected)
        ctrl_layout.addWidget(self.del_btn)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._refresh)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["文件名", "大小", "修改时间", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

    def _refresh(self):
        items = self.api.list_files(self.daemon_id, self.instance_uuid, self.backup_path)
        if items is None:
            self.table.setRowCount(0)
            return
        zip_items = [it for it in items if it.get("name", "").endswith(".zip")]
        self.table.setRowCount(len(zip_items))
        for i, item in enumerate(zip_items):
            name = item.get("name", "?")
            size = item.get("size", item.get("fileSize", 0))
            mtime = item.get("modTime", item.get("mtime", ""))
            self.table.setItem(i, 0, QTableWidgetItem(name))
            if isinstance(size, (int, float)):
                self.table.setItem(i, 1, QTableWidgetItem(self._fmt_size(size)))
            else:
                self.table.setItem(i, 1, QTableWidgetItem(str(size)))
            self.table.setItem(i, 2, QTableWidgetItem(str(mtime)))
            self.table.setItem(i, 3, QTableWidgetItem(""))

    def _create_backup(self):
        dlg = BackupDirDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return
        dirs = dlg.get_selected_dirs()
        if not dirs:
            QMessageBox.warning(self, "提示", "请至少选择一个目录")
            return
        backup_name = dlg.get_backup_name() or f"backup-{self._ts()}.zip"
        for d in dirs:
            self.api.compress_files(
                self.daemon_id, self.instance_uuid, "/", [d]
            )
        QMessageBox.information(self, "成功", f"备份创建完成: {backup_name}")
        self._refresh()

    def _download_selected(self):
        rows = {r.row() for r in self.table.selectedIndexes()}
        if not rows:
            return
        dir_path = QFileDialog.getExistingDirectory(self, "选择下载目录")
        if not dir_path:
            return
        self.progress.setVisible(True)
        self.progress.setValue(0)
        for row in rows:
            name = self.table.item(row, 0).text()
            remote = f"{self.backup_path}/{name}"
            local = f"{dir_path}/{name}"
            def cb(pos, total):
                if total > 0:
                    self.progress.setMaximum(total)
                    self.progress.setValue(pos)
                QApplication.processEvents()
            self.api.download_file(self.daemon_id, self.instance_uuid, remote, local, cb)
        self.progress.setVisible(False)
        QMessageBox.information(self, "完成", "下载完成")

    def _delete_selected(self):
        rows = {r.row() for r in self.table.selectedIndexes()}
        if not rows:
            return
        r = QMessageBox.question(self, "确认删除", f"删除 {len(rows)} 个备份？",
                                 QMessageBox.Yes | QMessageBox.No)
        if r != QMessageBox.Yes:
            return
        targets = []
        for row in rows:
            name = self.table.item(row, 0).text()
            targets.append(f"{self.backup_path}/{name}")
        if self.api.delete_files(self.daemon_id, self.instance_uuid, targets):
            self._refresh()
        else:
            QMessageBox.warning(self, "失败", "删除失败")

    @staticmethod
    def _fmt_size(size):
        for u in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {u}"
            size /= 1024
        return f"{size:.1f} TB"

    @staticmethod
    def _ts():
        return datetime.now().strftime("%Y%m%d_%H%M%S")


class PlayerTab(QWidget):
    def __init__(self, api, daemon_id, instance_uuid, parent=None):
        super().__init__(parent)
        self.api = api
        self.daemon_id = daemon_id
        self.instance_uuid = instance_uuid
        self.server_path = "/"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        tab_bar = QHBoxLayout()
        self.tab_combo = QComboBox()
        self.tab_combo.addItems(["白名单", "管理员(OP)", "封禁玩家", "封禁IP"])
        self.tab_combo.currentIndexChanged.connect(self._load_data)
        tab_bar.addWidget(self.tab_combo)
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self._add_entry)
        tab_bar.addWidget(self.add_btn)
        self.del_btn = QPushButton("移除选中")
        self.del_btn.clicked.connect(self._remove_selected)
        tab_bar.addWidget(self.del_btn)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._load_data)
        tab_bar.addStretch()
        layout.addLayout(tab_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["#", "值", ""])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._edit_entry)
        layout.addWidget(self.table)

        self._files = {
            0: "whitelist.json",
            1: "ops.json",
            2: "banned-players.json",
            3: "banned-ips.json",
        }
        self._load_data()

    def _get_remote_path(self, filename):
        for prefix in ("", "/"):
            path = prefix + filename
            info = self.api.get_file_info(self.daemon_id, self.instance_uuid, path)
            if info and info.get("isDir") is False:
                return path
        return "/" + filename

    def _load_data(self):
        idx = self.tab_combo.currentIndex()
        filename = self._files.get(idx, "whitelist.json")
        path = self._get_remote_path(filename)
        tmp = os.path.join(tempfile.gettempdir(), f"mcsm_{filename}")
        if self.api.download_file(self.daemon_id, self.instance_uuid, path, tmp):
            try:
                with open(tmp, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
            self._display_data(data)
            os.unlink(tmp)

    def _display_data(self, data):
        if isinstance(data, list):
            self.table.setRowCount(len(data))
            for i, entry in enumerate(data):
                name = entry.get("name") or entry.get("uuid") or str(entry)
                self.table.setItem(i, 0, QTableWidgetItem(str(i)))
                self.table.setItem(i, 1, QTableWidgetItem(str(name)))
                reason = entry.get("reason", entry.get("source", ""))
                self.table.setItem(i, 2, QTableWidgetItem(reason))
        elif isinstance(data, dict):
            self.table.setRowCount(len(data))
            for i, (k, v) in enumerate(data.items()):
                self.table.setItem(i, 0, QTableWidgetItem(str(i)))
                self.table.setItem(i, 1, QTableWidgetItem(k))
                self.table.setItem(i, 2, QTableWidgetItem(str(v)))

    def _edit_entry(self, item):
        row = item.row()
        idx = self.tab_combo.currentIndex()
        filename = self._files.get(idx, "whitelist.json")
        path = self._get_remote_path(filename)
        tmp = os.path.join(tempfile.gettempdir(), f"mcsm_{filename}")
        if not self.api.download_file(self.daemon_id, self.instance_uuid, path, tmp):
            return
        try:
            with open(tmp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
        col = 1
        old_val = self.table.item(row, col).text() if self.table.item(row, col) else ""
        new_val, ok = QInputDialog.getText(self, "编辑", "新值:", text=old_val)
        if ok and new_val.strip():
            if isinstance(data, list) and row < len(data):
                entry = data[row]
                if "name" in entry:
                    entry["name"] = new_val.strip()
                elif "uuid" in entry:
                    entry["uuid"] = new_val.strip()
            elif isinstance(data, dict):
                keys = list(data.keys())
                if row < len(keys):
                    old_key = keys[row]
                    data[new_val.strip()] = data.pop(old_key)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.api.upload_file(tmp, "/", self.daemon_id, self.instance_uuid)
            os.unlink(tmp)
            self._load_data()

    def _add_entry(self):
        name, ok = QInputDialog.getText(self, "添加", "玩家名称/UUID:")
        if ok and name.strip():
            idx = self.tab_combo.currentIndex()
            filename = self._files.get(idx, "whitelist.json")
            path = self._get_remote_path(filename)
            tmp = os.path.join(tempfile.gettempdir(), f"mcsm_{filename}")
            if self.api.download_file(self.daemon_id, self.instance_uuid, path, tmp):
                try:
                    with open(tmp, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = []
                if isinstance(data, list):
                    data.append({"name": name.strip(), "uuid": ""})
                else:
                    data[name.strip()] = ""
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.api.upload_file(tmp, "/", self.daemon_id, self.instance_uuid)
                os.unlink(tmp)
                self._load_data()

    def _remove_selected(self):
        rows = {r.row() for r in self.table.selectedIndexes()}
        if not rows:
            return
        idx = self.tab_combo.currentIndex()
        filename = self._files.get(idx, "whitelist.json")
        path = self._get_remote_path(filename)
        tmp = os.path.join(tempfile.gettempdir(), f"mcsm_{filename}")
        if self.api.download_file(self.daemon_id, self.instance_uuid, path, tmp):
            try:
                with open(tmp, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
            indices = sorted(rows, reverse=True)
            if isinstance(data, list):
                for ri in indices:
                    if ri < len(data):
                        data.pop(ri)
            else:
                keys = list(data.keys())
                for ri in indices:
                    if ri < len(keys):
                        data.pop(keys[ri])
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.api.upload_file(tmp, "/", self.daemon_id, self.instance_uuid)
            os.unlink(tmp)
            self._load_data()


class PluginTab(QWidget):
    def __init__(self, api, daemon_id, instance_uuid, parent=None):
        super().__init__(parent)
        self.api = api
        self.daemon_id = daemon_id
        self.instance_uuid = instance_uuid
        self.plugin_dir = "plugins"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        ctrl_layout = QHBoxLayout()
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["plugins", "mods"])
        self.dir_combo.currentIndexChanged.connect(self._on_dir_changed)
        ctrl_layout.addWidget(QLabel("目录:"))
        ctrl_layout.addWidget(self.dir_combo)
        self.upload_btn = QPushButton("上传")
        self.upload_btn.clicked.connect(self._upload)
        ctrl_layout.addWidget(self.upload_btn)
        self.toggle_btn = QPushButton("启用/禁用")
        self.toggle_btn.clicked.connect(self._toggle)
        ctrl_layout.addWidget(self.toggle_btn)
        self.del_btn = QPushButton("删除")
        self.del_btn.clicked.connect(self._delete)
        ctrl_layout.addWidget(self.del_btn)
        self.create_dir_btn = QPushButton("创建目录")
        self.create_dir_btn.clicked.connect(self._create_dir)
        ctrl_layout.addWidget(self.create_dir_btn)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._refresh)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["文件名", "大小", "状态", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

    def _on_dir_changed(self, idx):
        self.plugin_dir = self.dir_combo.currentText()
        self._refresh()

    def _detect_dir(self):
        for i, d in enumerate(["plugins", "mods"]):
            items = self.api.list_files(self.daemon_id, self.instance_uuid, d)
            if items is not None:
                self.plugin_dir = d
                self.dir_combo.setCurrentIndex(i)
                return

    def _create_dir(self):
        d = self.dir_combo.currentText()
        if self.api.create_directory(self.daemon_id, self.instance_uuid, d):
            self._refresh()
        else:
            QMessageBox.warning(self, "失败", f"创建目录 {d} 失败")

    def _refresh(self):
        items = self.api.list_files(self.daemon_id, self.instance_uuid, self.plugin_dir)
        if items is None:
            self.table.setRowCount(0)
            return
        self.table.setRowCount(len(items))
        for i, item in enumerate(items):
            name = item.get("name", "?")
            size = item.get("size", 0)
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(self._fmt_size(size)))
            is_jar = name.endswith((".jar", ".py", ".js", ".litemod"))
            ext = ".disabled" if name.endswith(".disabled") else ""
            if ext:
                status = "已禁用"
                color = QColor(Nord.polar_night_4)
            elif is_jar:
                status = "已启用"
                color = QColor(Nord.aurora_green)
            else:
                status = "N/A"
                color = QColor(Nord.fg_dim)
            item_widget = QTableWidgetItem(status)
            item_widget.setForeground(color)
            self.table.setItem(i, 2, item_widget)

    def _upload(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "选择插件文件", "",
                                                "Plugin Files (*.jar *.py *.js *.litemod *.zip);;All Files (*)")
        if not fpath:
            return
        ok = self.api.upload_file(fpath, self.plugin_dir, self.daemon_id, self.instance_uuid)
        if ok:
            self._refresh()
        else:
            QMessageBox.warning(self, "失败", "上传失败")

    def _toggle(self):
        rows = {r.row() for r in self.table.selectedIndexes()}
        if not rows:
            return
        for row in rows:
            name = self.table.item(row, 0).text()
            if name.endswith(".disabled"):
                new_name = name[:-9]
            else:
                new_name = name + ".disabled"
            self.api.move_files(self.daemon_id, self.instance_uuid,
                                [[f"{self.plugin_dir}/{name}", f"{self.plugin_dir}/{new_name}"]])
        self._refresh()

    def _delete(self):
        rows = {r.row() for r in self.table.selectedIndexes()}
        if not rows:
            return
        r = QMessageBox.question(self, "确认删除", "删除选中的插件？",
                                 QMessageBox.Yes | QMessageBox.No)
        if r != QMessageBox.Yes:
            return
        targets = []
        for row in rows:
            name = self.table.item(row, 0).text()
            targets.append(f"{self.plugin_dir}/{name}")
        self.api.delete_files(self.daemon_id, self.instance_uuid, targets)
        self._refresh()

    @staticmethod
    def _fmt_size(size):
        for u in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {u}"
            size /= 1024
        return f"{size:.1f} TB"


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        self.setMinimumWidth(450)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        panel_group = QGroupBox("面板设置")
        panel_layout = QFormLayout(panel_group)
        self.base_url = QLineEdit(self.config.base_url)
        panel_layout.addRow("面板地址:", self.base_url)
        layout.addWidget(panel_group)

        auth_group = QGroupBox("认证")
        auth_layout = QFormLayout(auth_group)
        self.username = QLineEdit(self.config.username)
        self.password = QLineEdit(self.config.password)
        self.password.setEchoMode(QLineEdit.Password)
        self.token = QLineEdit(self.config.token)
        self.cookie = QLineEdit(self.config.cookie)
        self.apikey = QLineEdit(self.config.apikey)
        auth_layout.addRow("用户名:", self.username)
        auth_layout.addRow("密码:", self.password)
        auth_layout.addRow("Token:", self.token)
        auth_layout.addRow("Cookie:", self.cookie)
        auth_layout.addRow("API Key:", self.apikey)
        layout.addWidget(auth_group)

        instance_group = QGroupBox("实例")
        inst_layout = QFormLayout(instance_group)
        self.daemon_id = QLineEdit(self.config.daemon_id)
        self.instance_uuid = QLineEdit(self.config.instance_uuid)
        self.instance_name = QLineEdit(self.config.instance_name)
        inst_layout.addRow("Daemon ID:", self.daemon_id)
        inst_layout.addRow("Instance UUID:", self.instance_uuid)
        inst_layout.addRow("实例名称:", self.instance_name)
        layout.addWidget(instance_group)

        ui_group = QGroupBox("UI")
        ui_layout = QFormLayout(ui_group)
        self.auto_connect = QCheckBox()
        self.auto_connect.setChecked(self.config.auto_connect)
        ui_layout.addRow("自动连接:", self.auto_connect)
        self.show_exit = QCheckBox()
        self.show_exit.setChecked(self.config.show_exit_dialog)
        ui_layout.addRow("退出确认:", self.show_exit)
        self.term_mem = QCheckBox()
        self.term_mem.setChecked(self.config.terminal_memory)
        ui_layout.addRow("终端记忆:", self.term_mem)
        layout.addWidget(ui_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self):
        self.config.base_url = self.base_url.text().strip()
        self.config.username = self.username.text().strip()
        self.config.password = self.password.text().strip()
        self.config.token = self.token.text().strip()
        self.config.cookie = self.cookie.text().strip()
        self.config.apikey = self.apikey.text().strip()
        self.config.daemon_id = self.daemon_id.text().strip()
        self.config.instance_uuid = self.instance_uuid.text().strip()
        self.config.instance_name = self.instance_name.text().strip()
        self.config.auto_connect = self.auto_connect.isChecked()
        self.config.show_exit_dialog = self.show_exit.isChecked()
        self.config.terminal_memory = self.term_mem.isChecked()
        return self.config


class MCSManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.api = MCSManagerAPI(self.config.base_url)
        self.terminal_mgr = MCSMTerminal()
        self.daemon_id = self.config.daemon_id
        self.instance_uuid = self.config.instance_uuid
        self._init_ui()
        if self.config.has_auth and self.config.is_instance_configured:
            QTimer.singleShot(100, self._auto_connect)

    def _init_ui(self):
        self.setWindowTitle("MCSM Tools")
        self.setMinimumSize(1050, 720)
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

        self.connect_tab = ConnectTab(self.api, self.config)
        self.connect_tab.instance_selected.connect(self._on_instance_selected)
        self.tabs.addTab(self.connect_tab, "连接")

        self.terminal_tab = TerminalTab(self.api, self.terminal_mgr, self.config)
        self.tabs.addTab(self.terminal_tab, "终端")

        self.file_tab = FileManagerTab(self.api, self.daemon_id, self.instance_uuid)
        self.tabs.addTab(self.file_tab, "文件管理")

        self.log_tab = LogViewerTab(self.api, self.daemon_id, self.instance_uuid)
        self.tabs.addTab(self.log_tab, "日志")

        self.backup_tab = BackupTab(self.api, self.daemon_id, self.instance_uuid)
        self.tabs.addTab(self.backup_tab, "备份")

        self.player_tab = PlayerTab(self.api, self.daemon_id, self.instance_uuid)
        self.tabs.addTab(self.player_tab, "玩家")

        self.plugin_tab = PluginTab(self.api, self.daemon_id, self.instance_uuid)
        self.tabs.addTab(self.plugin_tab, "插件/Mod")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("请先连接面板")
        self.status_bar.addPermanentWidget(self.status_label)

        self.player_count_label = QLabel("")
        self.player_count_label.setStyleSheet(f"color: {Nord.aurora_green}; padding-right: 10px;")
        self.status_bar.addPermanentWidget(self.player_count_label)

        menu = self.menuBar()
        file_menu = menu.addMenu("文件")
        settings_action = file_menu.addAction("设置")
        settings_action.triggered.connect(self._show_settings)

        file_menu.addSeparator()
        about_action = file_menu.addAction("关于")
        about_action.triggered.connect(self._show_about)

    def _on_tab_changed(self, index):
        pass

    def _show_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec_() == QDialog.Accepted:
            cfg = dlg.get_config()
            save_config(cfg)
            self.api.set_base_url(cfg.base_url)
            self.api.refresh_auth_from_config(cfg)
            self.daemon_id = cfg.daemon_id
            self.instance_uuid = cfg.instance_uuid
            QMessageBox.information(self, "设置", "设置已保存")

    def _auto_connect(self):
        try:
            self.status_label.setText("正在自动连接...")
            self.api.refresh_auth_from_config(self.config)
            if self.config.is_instance_configured:
                self.status_label.setText(f"已连接: {self.api.base_url}")
                self._connect_terminal()
                for tab_name in ["文件管理", "日志", "备份", "玩家", "插件/Mod"]:
                    for i in range(self.tabs.count()):
                        if self.tabs.tabText(i) == tab_name:
                            tab = self.tabs.widget(i)
                            if hasattr(tab, 'daemon_id'):
                                tab.daemon_id = self.daemon_id
                                tab.instance_uuid = self.instance_uuid
                            if hasattr(tab, '_detect_dir'):
                                tab._detect_dir()
                            if hasattr(tab, '_load_files'):
                                tab._load_files("/")
                            elif hasattr(tab, '_refresh_file_list'):
                                tab._refresh_file_list()
                            elif hasattr(tab, '_load_data'):
                                tab._load_data()
                            elif hasattr(tab, '_refresh'):
                                tab._refresh()
                            break
        except Exception:
            self.status_label.setText("自动连接失败，请前往连接标签页手动连接")

    def _connect_terminal(self):
        if not self.daemon_id or not self.instance_uuid:
            return
        try:
            result = self.api.get_websocket_password(self.daemon_id, self.instance_uuid)
            if result:
                password, addr = result
                self.terminal_mgr.connect(addr, password, self.api.base_url)
                self.terminal_mgr.on_players_update = self._on_players_update
        except Exception:
            pass

    def _on_players_update(self, players):
        if players:
            self.player_count_label.setText(f"\u25cf {len(players)} 人在线")
        else:
            self.player_count_label.setText("")

    def _on_instance_selected(self, daemon_id, instance_uuid):
        self.daemon_id = daemon_id
        self.instance_uuid = instance_uuid
        for tab_name in ["文件管理", "日志", "备份", "玩家", "插件/Mod"]:
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == tab_name:
                    tab = self.tabs.widget(i)
                    tab.daemon_id = daemon_id
                    tab.instance_uuid = instance_uuid
                    if hasattr(tab, '_detect_dir'):
                        tab._detect_dir()
                    if hasattr(tab, '_load_files'):
                        tab._load_files("/")
                    elif hasattr(tab, '_refresh_file_list'):
                        tab._refresh_file_list()
                    elif hasattr(tab, '_load_data'):
                        tab._load_data()
                    elif hasattr(tab, '_refresh'):
                        tab._refresh()
                    break
        self._connect_terminal()
        self.status_label.setText(f"实例: {daemon_id[:16]}...")

    def _show_about(self):
        QMessageBox.about(self, "关于 MCSM Tools",
                          "MCSM Tools - MCSManager 管理客户端\n"
                          "基于 PyQt5 构建\n"
                          "版本 2.0.0")

    def closeEvent(self, event):
        if self.config.show_exit_dialog:
            r = QMessageBox.question(self, "退出确认", "确定要退出 MCSM Tools？",
                                     QMessageBox.Yes | QMessageBox.No)
            if r != QMessageBox.Yes:
                event.ignore()
                return
        if self.terminal_mgr:
            self.terminal_mgr.disconnect()
        event.accept()


def main():
    if sys.platform == "linux" and not os.environ.get("WAYLAND_DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_nord_palette(app)
    app.setStyleSheet(QSS)

    font = QFont("JetBrains Mono", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    win = MCSManagerWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
