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

        self._row_to_task_index: list[int] = []   # maps visible row -> real task idx in storage
        self._selected_task_index: int | None = None

        self.setWindowTitle(f"Release Details — {release_id}")
        self.resize(1220, 820)

        root = QVBoxLayout(self)

        # ---- Summary ----
        summary = QGroupBox("Summary")
        s = QHBoxLayout(summary)
        self.lbl_name = QLabel("Release: -")
        self.lbl_mgr = QLabel("Manager: -")
        self.lbl_window = QLabel("Window: -")
        self.lbl_expected = QLabel("Expected: -")

        self.pb_tasks = QProgressBar()
        self.pb_tasks.setFormat("Tasks: %p%")
        self.pb_tasks.setMaximumWidth(260)

        s.addWidget(self.lbl_name, 2)
        s.addWidget(self.lbl_mgr, 1)
        s.addWidget(self.lbl_window, 3)
        s.addWidget(self.lbl_expected, 1)
        s.addStretch()
        s.addWidget(self.pb_tasks)
        root.addWidget(summary)

        # ---- Notes ----
        notes_box = QGroupBox("Release Notes (top-level)")
        nl = QVBoxLayout(notes_box)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Add release notes, key decisions, risks, links, etc...")
        nl.addWidget(self.notes)

        nbtn = QHBoxLayout()
        self.btn_save_notes = QPushButton("Save Notes")
        self.btn_save_notes.setProperty("variant", "secondary")
        nbtn.addStretch()
        nbtn.addWidget(self.btn_save_notes)
        nl.addLayout(nbtn)
        root.addWidget(notes_box)

        # ---- Split: Task list (left) + Editor (right) ----
        splitter = QSplitter(Qt.Horizontal)

        # LEFT: Task list
        left = QWidget()
        left_layout = QVBoxLayout(left)

        task_box = QGroupBox("Release Tasks")
        tl = QVBoxLayout(task_box)

        self.tasks_table = QTableWidget(0, 6)
        self.tasks_table.setHorizontalHeaderLabels(
            ["Title", "Assignee", "Status", "Due", "Category", "State"]
        )
        self.tasks_table.horizontalHeader().setStretchLastSection(True)
        self.tasks_table.verticalHeader().setVisible(False)
        self.tasks_table.verticalHeader().setDefaultSectionSize(30)
        self.tasks_table.setAlternatingRowColors(True)

        # column widths for readability
        self.tasks_table.setColumnWidth(0, 360)
        self.tasks_table.setColumnWidth(1, 140)
        self.tasks_table.setColumnWidth(2, 130)
        self.tasks_table.setColumnWidth(3, 200)
        self.tasks_table.setColumnWidth(4, 140)
        self.tasks_table.setColumnWidth(5, 110)

        tl.addWidget(self.tasks_table)

        # Add task (simple row)
        add_row = QHBoxLayout()
        self.t_title = QLineEdit()
        self.t_title.setPlaceholderText("New task title")
        self.t_assignee = QComboBox()
        self.t_assignee.addItems(self.users)
        self.t_due = QLineEdit()
        self.t_due.setPlaceholderText("Due time ISO (blank = release start)")
        self.t_cat = QLineEdit()
        self.t_cat.setPlaceholderText("Category (Workflow/QA/Dev)")
        self.btn_add_task = QPushButton("Add Task")

        add_row.addWidget(self.t_title, 5)
        add_row.addWidget(self.t_assignee, 2)
        add_row.addWidget(self.t_due, 3)
        add_row.addWidget(self.t_cat, 2)
        add_row.addWidget(self.btn_add_task, 1)

        tl.addLayout(add_row)
        left_layout.addWidget(task_box)

        splitter.addWidget(left)

        # RIGHT: Big editor
        right = QWidget()
        right_layout = QVBoxLayout(right)

        editor_box = QGroupBox("Selected Task Editor (comfortable)")
        ef = QFormLayout(editor_box)

        self.e_title = QLineEdit()
        self.e_assignee = QComboBox()
        self.e_assignee.addItems(self.users)

        self.e_status = QComboBox()
        self.e_status.addItems(self.STATUSES)

        self.e_due = QLineEdit()
        self.e_due.setPlaceholderText("Due time ISO (e.g. 2026-01-20T21:30:00)")

        self.e_cat = QLineEdit()

        self.e_task_id = QLabel("-")
        self.e_state = QLabel("-")

        ef.addRow("Title", self.e_title)
        ef.addRow("Assignee", self.e_assignee)
        ef.addRow("Status", self.e_status)
        ef.addRow("Due Time (ISO)", self.e_due)
        ef.addRow("Category", self.e_cat)
        ef.addRow("Task ID", self.e_task_id)
        ef.addRow("State", self.e_state)

        right_layout.addWidget(editor_box)

        # Editor buttons
        eb = QHBoxLayout()
        self.btn_save_task = QPushButton("Save Task Changes")
        self.btn_save_task.setProperty("variant", "secondary")
        self.btn_delete_task = QPushButton("Delete Task (requires comment)")
        self.btn_delete_task.setProperty("variant", "secondary")
        self.btn_delete_task.setEnabled(False)
        self.btn_save_task.setEnabled(False)

        eb.addWidget(self.btn_save_task)
        eb.addWidget(self.btn_delete_task)
        eb.addStretch()
        right_layout.addLayout(eb)

        # Helper label
        self.help_lbl = QLabel("Tip: Select a task from the left table to edit it here.")
        self.help_lbl.setStyleSheet("color: gray;")
        right_layout.addWidget(self.help_lbl)

        splitter.addWidget(right)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter)

        # ---- Footer ----
        footer = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setProperty("variant", "secondary")
        self.btn_close = QPushButton("Close")
        footer.addWidget(self.btn_refresh)
        footer.addStretch()
        footer.addWidget(self.btn_close)
        root.addLayout(footer)

        # ---- Events ----
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

    def _get_release(self) -> dict | None:
        return next((r for r in list_releases() if r["id"] == self.release_id), None)

    def _refresh_expected_only(self):
        rel = self._get_release()
        if not rel:
            return
        ws = rel.get("window_start", "")
        self.lbl_expected.setText(f"Expected: Release in {countdown_str(ws) if ws else '-'}")

    def refresh(self):
        rel = self._get_release()
        if not rel:
            QMessageBox.warning(self, "Not Found", "Release not found.")
            self.reject()
            return

        # Summary
        self.lbl_name.setText(f"Release: {rel.get('name','')} ({rel.get('id','')})")
        self.lbl_mgr.setText(f"Manager: {rel.get('release_manager','')}")
        ws, we = rel.get("window_start", ""), rel.get("window_end", "")
        self.lbl_window.setText(f"Window: {ws} → {we}")
        self.lbl_expected.setText(f"Expected: Release in {countdown_str(ws) if ws else '-'}")

        # Notes
        self.notes.blockSignals(True)
        self.notes.setPlainText(rel.get("notes", ""))
        self.notes.blockSignals(False)

        # Tasks ordering: active then deleted
        tasks = rel.get("tasks", [])
        indexed = list(enumerate(tasks))
        active = [(i, t) for i, t in indexed if not t.get("deleted")]
        deleted = [(i, t) for i, t in indexed if t.get("deleted")]
        ordered = active + deleted

        self._row_to_task_index = [i for i, _ in ordered]

        self.tasks_table.setRowCount(len(ordered))

        for row, (idx, t) in enumerate(ordered):
            is_deleted = bool(t.get("deleted"))

            title = t.get("title", "")
            assignee = t.get("assignee", "")
            status = t.get("status", "TODO")
            due = t.get("due_time", "")
            cat = t.get("category", "")
            state = "DELETED" if is_deleted else "ACTIVE"

            it_title = _ro(title)
            it_ass = _ro(assignee)
            it_st = _ro(status)
            it_due = _ro(due)
            it_cat = _ro(cat)
            it_state = _ro(state)

            if is_deleted:
                for it in [it_title, it_ass, it_st, it_due, it_cat, it_state]:
                    it.setForeground(Qt.gray)

            self.tasks_table.setItem(row, 0, it_title)
            self.tasks_table.setItem(row, 1, it_ass)
            self.tasks_table.setItem(row, 2, it_st)
            self.tasks_table.setItem(row, 3, it_due)
            self.tasks_table.setItem(row, 4, it_cat)
            self.tasks_table.setItem(row, 5, it_state)

        # Progress ignore deleted
        active_tasks = [t for t in tasks if not t.get("deleted")]
        total = len(active_tasks) or 1
        done = sum(1 for x in active_tasks if x.get("status") == "DONE")
        self.pb_tasks.setValue(int((done / total) * 100))

        # preserve selection if possible
        if self._selected_task_index is not None:
            try:
                row = self._row_to_task_index.index(self._selected_task_index)
                self.tasks_table.blockSignals(True)
                self.tasks_table.selectRow(row)
                self.tasks_table.blockSignals(False)
            except ValueError:
                self.clear_editor()

    def clear_editor(self):
        self._selected_task_index = None
        self.e_title.setText("")
        self.e_assignee.setCurrentIndex(0 if self.users else -1)
        self.e_status.setCurrentText("TODO")
        self.e_due.setText("")
        self.e_cat.setText("")
        self.e_task_id.setText("-")
        self.e_state.setText("-")
        self.btn_save_task.setEnabled(False)
        self.btn_delete_task.setEnabled(False)

    def on_select_task_row(self):
        row = self.tasks_table.currentRow()
        if row < 0 or row >= len(self._row_to_task_index):
            self.clear_editor()
            return

        rel = self._get_release()
        if not rel:
            return
        idx = self._row_to_task_index[row]
        tasks = rel.get("tasks", [])
        if idx < 0 or idx >= len(tasks):
            self.clear_editor()
            return

        t = tasks[idx]
        self._selected_task_index = idx

        is_deleted = bool(t.get("deleted"))
        self.e_title.setText(t.get("title", ""))
        self.e_assignee.setCurrentText(t.get("assignee", "") if t.get("assignee", "") in self.users else (self.users[0] if self.users else ""))
        st = t.get("status", "TODO")
        self.e_status.setCurrentText(st if st in self.STATUSES else "TODO")
        self.e_due.setText(t.get("due_time", ""))
        self.e_cat.setText(t.get("category", ""))

        self.e_task_id.setText(t.get("id", ""))
        if is_deleted:
            comment = t.get("delete_comment", "")
            self.e_state.setText(f"DELETED — {comment}" if comment else "DELETED")
        else:
            self.e_state.setText("ACTIVE")

        self.btn_save_task.setEnabled(not is_deleted)
        self.btn_delete_task.setEnabled(not is_deleted)

    def on_save_task_changes(self):
        if self._selected_task_index is None:
            return
        idx = self._selected_task_index

        patch = {
            "title": self.e_title.text().strip(),
            "assignee": self.e_assignee.currentText(),
            "status": self.e_status.currentText(),
            "due_time": self.e_due.text().strip(),
            "category": self.e_cat.text().strip() or "Workflow",
        }
        update_release_task(self.release_id, idx, patch)
        self.refresh()

    def on_delete_selected_task(self):
        if self._selected_task_index is None:
            return
        idx = self._selected_task_index

        comment, ok = QInputDialog.getText(self, "Delete Task", "Reason / comment (required):")
        if not ok:
            return
        comment = (comment or "").strip()
        if not comment:
            QMessageBox.warning(self, "Validation", "Comment is required to delete a task.")
            return
        soft_delete_release_task(self.release_id, idx, comment)
        self.refresh()

    def on_add_task(self):
        rel = self._get_release()
        if not rel:
            return

        title = self.t_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation", "Task title is required.")
            return

        assignee = self.t_assignee.currentText()
        cat = self.t_cat.text().strip() or "Workflow"
        due = self.t_due.text().strip() or rel.get("window_start", "")

        add_release_task(self.release_id, title=title, assignee=assignee, category=cat, due_time_iso=due)

        self.t_title.clear()
        self.t_due.clear()
        self.t_cat.clear()
        self.refresh()

    def on_save_notes(self):
        txt = self.notes.toPlainText().strip()
        update_release(self.release_id, {"notes": txt})
        QMessageBox.information(self, "Saved", "Release notes saved.")