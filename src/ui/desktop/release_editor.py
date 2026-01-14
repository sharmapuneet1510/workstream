from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QComboBox, QPushButton, QMessageBox
)

from services.config_store import list_users
from services.release_store import update_release


class ReleaseEditorDialog(QDialog):
    def __init__(self, release: dict, parent=None):
        super().__init__(parent)
        self.release = release
        self.setWindowTitle(f"Edit Release — {release['id']}")
        self.resize(650, 420)

        users = list_users()

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name"))
        self.name = QLineEdit(release.get("name", ""))
        layout.addWidget(self.name)

        layout.addWidget(QLabel("Description"))
        self.desc = QTextEdit(release.get("description", ""))
        layout.addWidget(self.desc)

        row = QHBoxLayout()
        self.manager = QComboBox()
        self.manager.addItems(users)
        if release.get("release_manager") in users:
            self.manager.setCurrentText(release["release_manager"])
        row.addWidget(QLabel("Release Manager"))
        row.addWidget(self.manager)
        layout.addLayout(row)

        layout.addWidget(QLabel("Window Start (ISO)  e.g. 2026-01-20T22:00:00"))
        self.win_start = QLineEdit(release.get("window_start", ""))
        layout.addWidget(self.win_start)

        layout.addWidget(QLabel("Window End (ISO)  e.g. 2026-01-20T23:30:00"))
        self.win_end = QLineEdit(release.get("window_end", ""))
        layout.addWidget(self.win_end)

        btns = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")
        btns.addStretch()
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        self.btn_save.clicked.connect(self.save)
        self.btn_cancel.clicked.connect(self.reject)

    def save(self):
        # Basic validation
        n = self.name.text().strip()
        ws = self.win_start.text().strip()
        we = self.win_end.text().strip()

        if not n or not ws or not we:
            QMessageBox.warning(self, "Validation", "Name, Window Start and Window End are required.")
            return

        patch = {
            "name": n,
            "description": self.desc.toPlainText().strip(),
            "release_manager": self.manager.currentText(),
            "window_start": ws,
            "window_end": we,
        }

        try:
            update_release(self.release["id"], patch)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.accept()