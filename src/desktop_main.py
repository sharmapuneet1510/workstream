import sys
from PySide6.QtWidgets import QApplication
from ui.desktop.app import WorkstreamDesktop
from ui.desktop.theme import WHITE_RED_QSS

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(WHITE_RED_QSS)  # <-- apply theme globally
    win = WorkstreamDesktop()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()