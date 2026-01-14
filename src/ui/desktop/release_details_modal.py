from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QComboBox,
    QLineEdit, QMessageBox, QProgressBar, QTextEdit, QInputDialog,
    QSplitter, QWidget, QFormLayout
)

from services.config_store import list_users
from services.release_store import (
    list_releases, countdown_str,
    add_release_task, update_release_task,
    update_release, soft_delete_release_task
)


def _ro(text: str) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    return it


class ReleaseDetailsDialog(QDialog):
    STATUSES = ["TODO", "IN_PROGRESS", "DONE"]

    def __init__(self, release_id: str, parent=None):
        super().__init__(parent)
        self.release_id = release_id
        self.users = list_users()

        self._row_to_task_index: list[int] = []
        self._selected_task_index: int | None = None

        self.setWindowTitle(f"Release Details — {release_id}")
        self.resize(1320, 820)

        root = QVBoxLayout(self)

        # ---------------- Summary ----------------
        summary = QGroupBox("Summary")
        s = QHBoxLayout(summary)

        self.lbl_name = QLabel("Release: -")
        self.lbl_mgr = QLabel("Manager: -")
        self.lbl_window = QLabel("Window: -")
        self.lbl_expected = QLabel("Expected: -")

        self.pb_tasks = QProgressBar()
        self.pb_tasks.setFormat("Tasks: %p%")
        self.pb_tasks.setMaximumWidth(260)

        s.addWidget(self.lbl_name, 3)
        s.addWidget(self.lbl_mgr, 1)
        s.addWidget(self.lbl_window, 3)
        s.addWidget(self.lbl_expected, 1)
        s.addStretch()
        s.addWidget(self.pb_tasks)

        root.addWidget(summary)

        # ---------------- Notes ----------------
        notes_box = QGroupBox("Release Notes")
        nl = QVBoxLayout(notes_box)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText(
            "High-level release notes, risks, approvals, rollback notes, links…"
        )
        nl.addWidget(self.notes)

        nb = QHBoxLayout()
        self.btn_save_notes = QPushButton("Save Notes")
        self.btn_save_notes.setProperty("variant", "secondary")
        nb.addStretch()
        nb.addWidget(self.btn_save_notes)
        nl.addLayout(nb)

        root.addWidget(notes_box)

        # ---------------- Split: Editor LEFT, List RIGHT ----------------
        splitter = QSplitter(Qt.Horizontal)

        # ===== LEFT: Task Editor (wide) =====
        left = QWidget()
        left_layout = QVBoxLayout(left)

        editor_box = QGroupBox("Selected Task Editor")
        ef = QFormLayout(editor_box)
        ef.setLabelAlignment(Qt.AlignLeft)
        ef.setFormAlignment(Qt.AlignTop)

        self.e_title = QLineEdit()
        self.e_title.setPlaceholderText("Task title (clear and descriptive)")
        self.e_title.setMinimumHeight(36)

        self.e_assignee = QComboBox()
        self.e_assignee.addItems(self.users)

        self.e_status = QComboBox()
        self.e_status.addItems(self.STATUSES)

        self.e_due = QLineEdit()
        self.e_due.setPlaceholderText("Due time ISO (e.g. 2026-01-20T21:30:00)")

        self.e_cat = QLineEdit()
        self.e_cat.setPlaceholderText("Category (Workflow / QA / Dev / Ops)")

        self.e_task_id = QLabel("-")
        self.e_state = QLabel("-")

        ef.addRow("Title", self.e_title)
        ef.addRow("Assignee", self.e_assignee)
        ef.addRow("Status", self.e_status)
        ef.addRow("Due Time", self.e_due)
        ef.addRow("Category", self.e_cat)
        ef.addRow("Task ID", self.e_task_id)
        ef.addRow("State", self.e_state)

        left_layout.addWidget(editor_box)

        # Editor buttons
        eb = QHBoxLayout()
        self.btn_save_task = QPushButton("Save Task Changes")
        self.btn_delete_task = QPushButton("Delete Task (with comment)")
        self.btn_save_task.setProperty("variant", "secondary")
        self.btn_delete_task.setProperty("variant", "secondary")
        self.btn_save_task.setEnabled(False)
        self.btn_delete_task.setEnabled(False)

        eb.addWidget(self.btn_save_task)
        eb.addWidget(self.btn_delete_task)
        eb.addStretch()

        left_layout.addLayout(eb)
        left_layout.addStretch()

        splitter.addWidget(left)

        # ===== RIGHT: Task List (scan-only) =====
        right = QWidget()
        right_layout = QVBoxLayout(right)

        task_box = QGroupBox("Release Tasks")
        tl = QVBoxLayout(task_box)

        self.tasks_table = QTableWidget(0, 6)
        self.tasks_table.setHorizontalHeaderLabels(
            ["Title", "Assignee", "Status", "Due", "Category", "State"]
        )
        self.tasks_table.verticalHeader().setVisible(False)
        self.tasks_table.verticalHeader().setDefaultSectionSize(30)
        self.tasks_table.setAlternatingRowColors(True)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tasks_table.setSelectionMode(QTableWidget.SingleSelection)

        self.tasks_table.setColumnWidth(0, 300)
        self.tasks_table.setColumnWidth(1, 130)
        self.tasks_table.setColumnWidth(2, 120)
        self.tasks_table.setColumnWidth(3, 170)
        self.tasks_table.setColumnWidth(4, 120)
        self.tasks_table.setColumnWidth(5, 90)

        tl.addWidget(self.tasks_table)

        # Add task row
        add_row = QHBoxLayout()
        self.t_title = QLineEdit()
        self.t_title.setPlaceholderText("New task title")
        self.t_assignee = QComboBox()
        self.t_assignee.addItems(self.users)
        self.t_due = QLineEdit()
        self.t_due.setPlaceholderText("Due time (optional)")
        self.t_cat = QLineEdit()
        self.t_cat.setPlaceholderText("Category")
        self.btn_add_task = QPushButton("Add Task")

        add_row.addWidget(self.t_title, 4)
        add_row.addWidget(self.t_assignee, 2)
        add_row.addWidget(self.t_due, 2)
        add_row.addWidget(self.t_cat, 2)
        add_row.addWidget(self.btn_add_task, 1)

        tl.addLayout(add_row)

        right_layout.addWidget(task_box)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter)

        # ---------------- Footer ----------------
        footer = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setProperty("variant", "secondary")
        self.btn_close = QPushButton("Close")
        footer.addWidget(self.btn_refresh)
        footer.addStretch()
        footer.addWidget(self.btn_close)
        root.addLayout(footer)

        # ---------------- Events ----------------
        self.btn_close.clicked.connect(self.accept)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_add_task.clicked.connect(self.on_add_task)
        self.btn_save_notes.clicked.connect(self.on_save_notes)
        self.tasks_table.itemSelectionChanged.connect(self.on_select_task_row)
        self.btn_save_task.clicked.connect(self.on_save_task_changes)
        self.btn_delete_task.clicked.connect(self.on_delete_selected_task)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_expected_only)
        self._timer.start(30_000)

        self.refresh()

    # ---- Logic below unchanged from previous version ----
    # (no backend changes)

    # [The rest of the methods remain exactly the same as before]