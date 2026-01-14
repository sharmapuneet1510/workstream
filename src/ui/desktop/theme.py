# White + Red theme (Qt StyleSheet / QSS)
# Note: Qt uses a CSS-like syntax (QSS)

WHITE_RED_QSS = """
/* ---------- App base ---------- */
QMainWindow, QWidget {
    background: #FFFFFF;
    color: #111111;
    font-family: -apple-system, "Segoe UI", Arial;
    font-size: 13px;
}

/* ---------- Headings / Labels ---------- */
QLabel {
    color: #111111;
}
QGroupBox {
    border: 1px solid #E6E6E6;
    border-radius: 10px;
    margin-top: 10px;
    padding: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #B00020; /* red */
    font-weight: 600;
}

/* ---------- Inputs ---------- */
QLineEdit, QTextEdit, QComboBox, QDateTimeEdit {
    background: #FFFFFF;
    border: 1px solid #DADADA;
    border-radius: 8px;
    padding: 8px;
    selection-background-color: #B00020;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #B00020;
}

/* Combo dropdown arrow */
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 7px solid #B00020;
    margin-right: 10px;
}

/* ---------- Buttons ---------- */
QPushButton {
    background: #B00020;      /* primary red */
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 9px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #C5152D;
}
QPushButton:pressed {
    background: #8F001A;
}
QPushButton:disabled {
    background: #E7B3BC;
    color: #FFFFFF;
}

/* Secondary button class: setProperty("variant","secondary") */
QPushButton[variant="secondary"] {
    background: #FFFFFF;
    color: #B00020;
    border: 1px solid #B00020;
}
QPushButton[variant="secondary"]:hover {
    background: #FFF1F3;
}
QPushButton[variant="secondary"]:pressed {
    background: #FFE2E7;
}

/* ---------- Tabs ---------- */
QTabWidget::pane {
    border: 1px solid #E6E6E6;
    border-radius: 12px;
    top: -1px;
}
QTabBar::tab {
    background: #F7F7F7;
    color: #333333;
    border: 1px solid #E6E6E6;
    border-bottom: none;
    padding: 10px 14px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    margin-right: 6px;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #B00020;
    border: 1px solid #B00020;
    border-bottom: none;
    font-weight: 700;
}
QTabBar::tab:hover {
    color: #B00020;
}

/* ---------- Tables ---------- */
QTableWidget {
    background: #FFFFFF;
    border: 1px solid #E6E6E6;
    border-radius: 12px;
    gridline-color: #EFEFEF;
    selection-background-color: #FFE2E7;
    selection-color: #111111;
}
QHeaderView::section {
    background: #FFF1F3;
    color: #B00020;
    border: none;
    border-bottom: 1px solid #E6E6E6;
    padding: 10px;
    font-weight: 700;
}
QTableWidget::item {
    padding: 8px;
}
QTableWidget::item:selected {
    background: #FFE2E7;
}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {
    background: #FAFAFA;
    width: 12px;
    margin: 0px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #E0E0E0;
    min-height: 25px;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover {
    background: #B00020;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ---------- Checkbox ---------- */
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #B00020;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background: #B00020;
    border: 1px solid #B00020;
}
"""