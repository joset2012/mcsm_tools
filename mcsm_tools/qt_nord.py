from PyQt5.QtGui import QColor, QPalette

from .theme import Nord

__all__ = ["QSS", "Nord", "apply_nord_palette"]


QSS = """
QMainWindow, QDialog {
    background-color: #2E3440;
    color: #D8DEE9;
}
QWidget {
    background-color: #2E3440;
    color: #D8DEE9;
    font-family: "JetBrains Mono", "Noto Sans CJK SC", "Segoe UI", sans-serif;
    font-size: 12px;
}
QTabWidget::pane {
    border: 1px solid #434C5E;
    background-color: #2E3440;
}
QTabBar::tab {
    background-color: #3B4252;
    color: #D8DEE9;
    padding: 8px 18px;
    border: 1px solid #434C5E;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #2E3440;
    border-bottom: 1px solid #2E3440;
}
QTabBar::tab:hover:!selected {
    background-color: #434C5E;
}
QTextEdit, QPlainTextEdit {
    background-color: #2E3440;
    color: #D8DEE9;
    border: 1px solid #434C5E;
    selection-background-color: #434C5E;
}
QLineEdit {
    background-color: #3B4252;
    color: #D8DEE9;
    border: 1px solid #434C5E;
    padding: 4px 8px;
    border-radius: 3px;
}
QLineEdit:focus {
    border: 1px solid #88C0D0;
}
QPushButton {
    background-color: #434C5E;
    color: #D8DEE9;
    border: 1px solid #4C566A;
    padding: 5px 14px;
    border-radius: 3px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #4C566A;
    border: 1px solid #81A1C1;
}
QPushButton:pressed {
    background-color: #5E81AC;
}
QPushButton:disabled {
    background-color: #3B4252;
    color: #4C566A;
}
QTreeView, QTableView, QListWidget, QTableWidget {
    background-color: #2E3440;
    color: #D8DEE9;
    border: 1px solid #434C5E;
    selection-background-color: #434C5E;
    selection-color: #ECEFF4;
    alternate-background-color: #3B4252;
    outline: none;
}
QTreeView::item, QTableView::item, QTableWidget::item {
    padding: 3px 5px;
    border-bottom: 1px solid #3B4252;
}
QTreeView::item:selected, QTableView::item:selected, QTableWidget::item:selected {
    background-color: #434C5E;
    color: #ECEFF4;
}
QHeaderView::section {
    background-color: #3B4252;
    color: #D8DEE9;
    padding: 5px;
    border: 1px solid #434C5E;
    font-weight: bold;
}
QLabel {
    color: #D8DEE9;
    background: transparent;
}
QComboBox {
    background-color: #3B4252;
    color: #D8DEE9;
    border: 1px solid #434C5E;
    padding: 4px 8px;
    border-radius: 3px;
    min-height: 22px;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #3B4252;
    color: #D8DEE9;
    selection-background-color: #434C5E;
    border: 1px solid #434C5E;
}
QComboBox:focus {
    border: 1px solid #88C0D0;
}
QCheckBox {
    color: #D8DEE9;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #4C566A;
    border-radius: 2px;
    background-color: #3B4252;
}
QCheckBox::indicator:checked {
    background-color: #5E81AC;
    border: 1px solid #88C0D0;
}
QScrollBar:vertical {
    background-color: #2E3440;
    width: 10px;
    border: none;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #434C5E;
    min-height: 20px;
    border-radius: 4px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #4C566A;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: #2E3440;
    height: 10px;
    border: none;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #434C5E;
    min-width: 20px;
    border-radius: 4px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #4C566A;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QProgressBar {
    background-color: #3B4252;
    border: 1px solid #434C5E;
    border-radius: 3px;
    text-align: center;
    color: #D8DEE9;
    min-height: 18px;
}
QProgressBar::chunk {
    background-color: #5E81AC;
    border-radius: 2px;
}
QMenuBar {
    background-color: #3B4252;
    color: #D8DEE9;
    border-bottom: 1px solid #434C5E;
}
QMenuBar::item:selected {
    background-color: #434C5E;
}
QMenu {
    background-color: #3B4252;
    color: #D8DEE9;
    border: 1px solid #434C5E;
}
QMenu::item:selected {
    background-color: #434C5E;
}
QStatusBar {
    background-color: #3B4252;
    color: #D8DEE9;
    border-top: 1px solid #434C5E;
}
QGroupBox {
    border: 1px solid #434C5E;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 12px;
    color: #D8DEE9;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #88C0D0;
}
QSplitter::handle {
    background-color: #434C5E;
    width: 2px;
}
QToolTip {
    background-color: #3B4252;
    color: #D8DEE9;
    border: 1px solid #434C5E;
    padding: 4px;
}
QDialogButtonBox QPushButton {
    min-width: 70px;
}
QFrame[frameShape="4"] {
    color: #434C5E;
}
"""


def apply_nord_palette(app):
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(Nord.polar_night_1))
    palette.setColor(QPalette.WindowText, QColor(Nord.snow_storm_1))
    palette.setColor(QPalette.Base, QColor(Nord.polar_night_2))
    palette.setColor(QPalette.AlternateBase, QColor(Nord.polar_night_1))
    palette.setColor(QPalette.ToolTipBase, QColor(Nord.polar_night_2))
    palette.setColor(QPalette.ToolTipText, QColor(Nord.snow_storm_1))
    palette.setColor(QPalette.Text, QColor(Nord.snow_storm_1))
    palette.setColor(QPalette.Button, QColor(Nord.polar_night_3))
    palette.setColor(QPalette.ButtonText, QColor(Nord.snow_storm_1))
    palette.setColor(QPalette.BrightText, QColor(Nord.snow_storm_3))
    palette.setColor(QPalette.Highlight, QColor(Nord.frost_4))
    palette.setColor(QPalette.HighlightedText, QColor(Nord.snow_storm_3))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(Nord.polar_night_4))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(Nord.polar_night_4))
    app.setPalette(palette)
