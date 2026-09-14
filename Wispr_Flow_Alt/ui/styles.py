"""
Design tokens and stylesheets for Wispr Flow Alt GUI.
Modern dark glassmorphism aesthetic inspired by native macOS Sequoia interfaces.
"""
import os
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
CHECK_ICON_PATH = (ASSETS_DIR / "check_white.png").as_posix()

DARK_THEME_QSS = """
/* Base Application Window */
QMainWindow, QDialog, QWidget#centralWidget {
    background-color: #0F1117;
    color: #E2E8F0;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #2D3748;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #4A5568;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Card Containers */
QFrame.card, QFrame#controlCard, QFrame#rawBox, QFrame#polishedBox, QFrame#prefCard, QFrame#infoCard {
    background-color: #1A1D27;
    border: 1px solid #272C3D;
    border-radius: 12px;
}

QFrame#centerCard {
    background-color: #161922;
    border: 1px solid #232736;
    border-radius: 14px;
}

/* Default label behavior */
QLabel {
    color: #E2E8F0;
    background-color: transparent;
    border: none;
}

/* Badges & Headers */
QLabel.headerTitle {
    font-size: 20px;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.4px;
}

QLabel.headerSubtitle {
    font-size: 13px;
    color: #94A3B8;
}

QLabel.badge {
    background-color: #242938;
    color: #CBD5E1;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid #333B50;
}

QLabel.statusReady {
    background-color: rgba(16, 185, 129, 0.15);
    color: #34D399;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

QLabel.statusRecording {
    background-color: rgba(239, 68, 68, 0.2);
    color: #F87171;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 6px;
    border: 1px solid rgba(239, 68, 68, 0.4);
}

QLabel.statusProcessing {
    background-color: rgba(99, 102, 241, 0.2);
    color: #818CF8;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid rgba(99, 102, 241, 0.4);
}

/* Dropdowns (ComboBox) */
QComboBox {
    background-color: #1E2333;
    color: #F1F5F9;
    border: 1px solid #333B52;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    min-width: 150px;
}

QComboBox:hover {
    border: 1px solid #6366F1;
    background-color: #252B3E;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1A1D27;
    color: #E2E8F0;
    border: 1px solid #333B52;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #4F46E5;
    selection-color: #FFFFFF;
}

/* Buttons */
QPushButton.primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
    color: #FFFFFF;
    font-weight: 600;
    font-size: 13px;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
}

QPushButton.primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
}

QPushButton.primaryBtn:pressed {
    background-color: #4338CA;
}

QPushButton.secondaryBtn {
    background-color: #242938;
    color: #CBD5E1;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid #333B50;
    border-radius: 8px;
    padding: 6px 12px;
}

QPushButton.secondaryBtn:hover {
    background-color: #2E3547;
    border-color: #475569;
    color: #FFFFFF;
}

/* Big Record Mic Button */
QPushButton#recordBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4F46E5, stop:1 #7C3AED);
    color: #FFFFFF;
    font-size: 36px;
    font-weight: bold;
    border-radius: 42px;
    border: 3px solid rgba(255, 255, 255, 0.2);
}

QPushButton#recordBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366F1, stop:1 #8B5CF6);
    border: 3px solid rgba(255, 255, 255, 0.4);
}

QPushButton#recordBtn.recording {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EF4444, stop:1 #DC2626);
    border: 3px solid rgba(248, 113, 113, 0.7);
}

/* Text Display Areas */
QTextEdit, QPlainTextEdit, QLineEdit {
    background-color: #141721;
    color: #F8FAFC;
    border: 1px solid #272C3D;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 14px;
    line-height: 1.5;
    selection-background-color: #4F46E5;
}

QTextEdit:focus, QPlainTextEdit:focus, QLineEdit:focus {
    border: 1px solid #6366F1;
    background-color: #171A26;
}

/* Checkbox */
QCheckBox {
    color: #E2E8F0;
    font-size: 13px;
    font-weight: 500;
    spacing: 8px;
    padding-right: 14px;
}

QCheckBox#noiseCancelCb {
    color: #94A3B8;
}

QCheckBox#noiseCancelCb:checked {
    color: #34D399;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #475569;
    background-color: #1E2333;
}

QCheckBox::indicator:hover {
    border-color: #818CF8;
}

QCheckBox::indicator:checked {
    background-color: #6366F1;
    border-color: #6366F1;
    image: url("__CHECK_ICON_PATH__");
}

/* Tab Bar */
QTabWidget::pane {
    border: none;
    background: transparent;
}

QTabBar::tab {
    background: #141721;
    color: #94A3B8;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 22px;
    min-width: 130px;
    margin-right: 6px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid transparent;
}

QTabBar::tab:selected {
    background: #1A1D27;
    color: #F8FAFC;
    border-bottom: 2px solid #6366F1;
}

QTabBar::tab:hover:!selected {
    color: #E2E8F0;
    background: #191D2A;
}

/* Preference Chip & Settings Button */
QLabel.prefChip {
    background-color: #242938;
    color: #E2E8F0;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 8px;
    border: 1px solid #333B50;
}

QPushButton.settingsBtnSmall {
    background-color: #2D3748;
    color: #CBD5E1;
    font-size: 12px;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 8px;
    border: 1px solid #4A5568;
}

QPushButton.settingsBtnSmall:hover {
    background-color: #3B4259;
    color: #FFFFFF;
    border-color: #6366F1;
}

/* History List / Table */
QTableWidget {
    background-color: #141721;
    color: #E2E8F0;
    gridline-color: #272C3D;
    border: 1px solid #272C3D;
    border-radius: 8px;
    font-size: 13px;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #1E2333;
}

QTableWidget::item:selected {
    background-color: #24293D;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #1A1D27;
    color: #94A3B8;
    font-size: 12px;
    font-weight: 600;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #272C3D;
}
"""

FLOATING_PILL_QSS = """
QFrame#pillFrame {
    background-color: rgba(16, 21, 35, 0.95);
    border: 1.2px solid rgba(255, 255, 255, 0.18);
    border-radius: 18px;
}

QFrame#pillFrame:hover {
    border: 1.2px solid rgba(129, 140, 248, 0.55);
    background-color: rgba(19, 25, 42, 0.98);
}

QPushButton#pillMicBtn {
    background: transparent;
    border: none;
    font-size: 15px;
    padding: 0px;
    margin: 0px;
}

QPushButton#pillMicBtn:hover {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 12px;
}

QLabel#pillStatus {
    color: #F1F5F9;
    font-size: 11.5px;
    font-weight: 600;
    letter-spacing: -0.2px;
}

/* Interactive Language Chip Button */
QPushButton#pillLangBtn {
    background-color: rgba(99, 102, 241, 0.18);
    color: #C7D2FE;
    border: 1px solid rgba(99, 102, 241, 0.35);
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 11px;
}

QPushButton#pillLangBtn:hover {
    background-color: rgba(99, 102, 241, 0.38);
    border: 1px solid rgba(129, 140, 248, 0.65);
    color: #FFFFFF;
}

/* Interactive Tone Chip Button */
QPushButton#pillToneBtn {
    background-color: rgba(16, 185, 129, 0.16);
    color: #6EE7B7;
    border: 1px solid rgba(16, 185, 129, 0.32);
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 11px;
}

QPushButton#pillToneBtn:hover {
    background-color: rgba(16, 185, 129, 0.35);
    border: 1px solid rgba(52, 211, 153, 0.65);
    color: #FFFFFF;
}

/* Floating Pill Interactive QMenu */
QMenu#pillDropdown {
    background-color: rgba(22, 27, 44, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 12px;
    padding: 6px;
}

QMenu#pillDropdown::item {
    color: #E2E8F0;
    font-size: 12px;
    font-weight: 500;
    padding: 6px 14px;
    border-radius: 6px;
    margin: 2px 0px;
}

QMenu#pillDropdown::item:selected {
    background-color: #4F46E5;
    color: #FFFFFF;
}
"""

LIGHT_THEME_QSS = """
/* Base Application Window */
QMainWindow, QDialog, QWidget#centralWidget {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Card Containers */
QFrame.card, QFrame#controlCard, QFrame#rawBox, QFrame#polishedBox, QFrame#prefCard, QFrame#infoCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}

QFrame#centerCard {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
}

/* Default label behavior */
QLabel {
    color: #0F172A;
    background-color: transparent;
    border: none;
}

/* Badges & Headers */
QLabel.headerTitle {
    font-size: 20px;
    font-weight: 700;
    color: #0F172A;
    letter-spacing: -0.4px;
}

QLabel.headerSubtitle {
    font-size: 13px;
    color: #64748B;
}

QLabel.badge {
    background-color: #F1F5F9;
    color: #334155;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid #CBD5E1;
}

QLabel.statusReady {
    background-color: rgba(16, 185, 129, 0.12);
    color: #059669;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

QLabel.statusRecording {
    background-color: rgba(239, 68, 68, 0.12);
    color: #DC2626;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 6px;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

QLabel.statusProcessing {
    background-color: rgba(99, 102, 241, 0.12);
    color: #4F46E5;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

/* Dropdowns (ComboBox) */
QComboBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    min-width: 150px;
}

QComboBox:hover {
    border: 1px solid #6366F1;
    background-color: #F8FAFC;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #4F46E5;
    selection-color: #FFFFFF;
}

/* Buttons */
QPushButton.primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
    color: #FFFFFF;
    font-weight: 600;
    font-size: 13px;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
}

QPushButton.primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9);
}

QPushButton.primaryBtn:pressed {
    background-color: #3730A3;
}

QPushButton.secondaryBtn {
    background-color: #F1F5F9;
    color: #334155;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 12px;
}

QPushButton.secondaryBtn:hover {
    background-color: #E2E8F0;
    border-color: #94A3B8;
    color: #0F172A;
}

/* Big Record Mic Button */
QPushButton#recordBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4F46E5, stop:1 #7C3AED);
    color: #FFFFFF;
    font-size: 36px;
    font-weight: bold;
    border-radius: 42px;
    border: 3px solid rgba(79, 70, 229, 0.25);
}

QPushButton#recordBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4338CA, stop:1 #6D28D9);
    border: 3px solid rgba(79, 70, 229, 0.45);
}

QPushButton#recordBtn.recording {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EF4444, stop:1 #DC2626);
    border: 3px solid rgba(239, 68, 68, 0.5);
}

/* Text Display Areas */
QTextEdit, QPlainTextEdit, QLineEdit {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 14px;
    line-height: 1.5;
    selection-background-color: #4F46E5;
}

QTextEdit:focus, QPlainTextEdit:focus, QLineEdit:focus {
    border: 1px solid #6366F1;
    background-color: #FFFFFF;
}

/* Checkbox */
QCheckBox {
    color: #334155;
    font-size: 13px;
    font-weight: 500;
    spacing: 8px;
    padding-right: 14px;
}

QCheckBox#noiseCancelCb {
    color: #64748B;
}

QCheckBox#noiseCancelCb:checked {
    color: #059669;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #94A3B8;
    background-color: #FFFFFF;
}

QCheckBox::indicator:hover {
    border-color: #6366F1;
}

QCheckBox::indicator:checked {
    background-color: #4F46E5;
    border-color: #4F46E5;
    image: url("__CHECK_ICON_PATH__");
}

/* Tab Bar */
QTabWidget::pane {
    border: none;
    background: transparent;
}

QTabBar::tab {
    background: #E2E8F0;
    color: #64748B;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 22px;
    min-width: 130px;
    margin-right: 6px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid transparent;
}

QTabBar::tab:selected {
    background: #FFFFFF;
    color: #0F172A;
    border-bottom: 2px solid #4F46E5;
}

QTabBar::tab:hover:!selected {
    color: #0F172A;
    background: #CBD5E1;
}

/* Preference Chip & Settings Button */
QLabel.prefChip {
    background-color: #F1F5F9;
    color: #334155;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 8px;
    border: 1px solid #CBD5E1;
}

QPushButton.settingsBtnSmall {
    background-color: #F1F5F9;
    color: #334155;
    font-size: 12px;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 8px;
    border: 1px solid #CBD5E1;
}

QPushButton.settingsBtnSmall:hover {
    background-color: #E2E8F0;
    color: #0F172A;
    border-color: #6366F1;
}

/* History List / Table */
QTableWidget {
    background-color: #FFFFFF;
    color: #0F172A;
    gridline-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    font-size: 13px;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #F1F5F9;
}

QTableWidget::item:selected {
    background-color: #EEF2FF;
    color: #312E81;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    font-size: 12px;
    font-weight: 600;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
}
"""

FLOATING_PILL_LIGHT_QSS = """
QFrame#pillFrame {
    background-color: rgba(255, 255, 255, 0.95);
    border: 1.2px solid rgba(0, 0, 0, 0.12);
    border-radius: 18px;
}

QFrame#pillFrame:hover {
    border: 1.2px solid rgba(99, 102, 241, 0.55);
    background-color: rgba(255, 255, 255, 0.98);
}

QPushButton#pillMicBtn {
    background: transparent;
    border: none;
    font-size: 15px;
    padding: 0px;
    margin: 0px;
}

QPushButton#pillMicBtn:hover {
    background: rgba(0, 0, 0, 0.08);
    border-radius: 12px;
}

QLabel#pillStatus {
    color: #0F172A;
    font-size: 11.5px;
    font-weight: 600;
    letter-spacing: -0.2px;
}

/* Floating Pill Interactive QMenu for Light Mode */
QMenu#pillDropdown {
    background-color: rgba(255, 255, 255, 0.98);
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 12px;
    padding: 6px;
}

QMenu#pillDropdown::item {
    color: #0F172A;
    font-size: 12px;
    font-weight: 500;
    padding: 6px 14px;
    border-radius: 6px;
    margin: 2px 0px;
}

QMenu#pillDropdown::item:selected {
    background-color: #4F46E5;
    color: #FFFFFF;
}
"""

DARK_THEME_QSS = DARK_THEME_QSS.replace("__CHECK_ICON_PATH__", CHECK_ICON_PATH)
LIGHT_THEME_QSS = LIGHT_THEME_QSS.replace("__CHECK_ICON_PATH__", CHECK_ICON_PATH)


