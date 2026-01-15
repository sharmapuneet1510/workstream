from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QGroupBox, QSplitter, QFormLayout, QHeaderView
)

from services.config_store import list_users
from services.project_store import list_projects
from services.todo_store import (
    list_todos, create_todo, update_todo,
    add_subtask, toggle_subtask,
    due_in_str, compute_task_pct
)


def _ro(text: str) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    return it


class TodoListTab(QWidget):
    """
    To-Do List tab:
      - Tasks linked to project (dropdown stores project_id in itemData)
      - Assignee, priority, due time, status
      - Subtasks drive completion % (or status if no subtasks)
    """

    STATUSES = ["TODO", "IN_PROGRESS", "DONE"]
    PRIORITIES = ["P0", "P1", "P2", "P3"]

    def __init__(self):
        super().__init__()

        self.users = list_users() or ["Unassigned"]
        self._row_to_task_id: list[str] = []
        self._selected_task_id: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # -------------------- Create Task Panel --------------------
        create_box = QGroupBox("Add To-Do Task (linked to Project)")
        cf = QVBoxLayout(create_box)
        cf.setSpacing(8)

        row1 = QHBoxLayout()
        self.c_project = QComboBox()
        self.c_assignee = QComboBox()
        self.c_assignee.addItems(self.users)

        self.c_priority = QComboBox()
        self.c_priority.addItems(self.PRIORITIES)
        self.c_priority.setCurrentText("P2")

        self.c_status = QComboBox()
        self.c_status.addItems(self.STATUSES)
        self.c_status.setCurrentText("TODO")

        self.c_due = QLineEdit()
        self.c_due.setPlaceholderText("Due time ISO (e.g. 2026-01-20T18:30:00)")

        row1.addWidget(QLabel("Project"))
        row1.addWidget(self.c_project, 5)
        row1.addWidget(QLabel("Assignee"))
        row1.addWidget(self.c_assignee, 2)
        row1.addWidget(QLabel("Priority"))
        row1.addWidget(self.c_priority, 1)
        row1.addWidget(QLabel("Status"))
        row1.addWidget(self.c_status, 2)
        row1.addWidget(QLabel("Due"))
        row1.addWidget(self.c_due, 3)
        cf.addLayout(row1)

        row2 = QHBoxLayout()
        self.c_desc = QLineEdit()
        self.c_desc.setPlaceholderText("Task description (required)")
        self.btn_add = QPushButton("Add To-Do")
        row2.addWidget(self.c_desc, 8)
        row2.addWidget(self.btn_add, 2)
        cf.addLayout(row2)

        row3 = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setProperty("variant", "secondary")
        self.btn_reload_projects = QPushButton("Reload Projects")
        self.btn_reload_projects.setProperty("variant", "secondary")
        row3.addWidget(self.btn_refresh)
        row3.addWidget(self.btn_reload_projects)
        row3.addStretch()
        cf.addLayout(row3)

        root.addWidget(create_box)

        # -------------------- Split: Table + Editor --------------------
        splitter = QSplitter(Qt.Horizontal)

        # LEFT: tasks table
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)

        ll.addWidget(QLabel("To-Do Tasks"))

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Project", "Assignee", "Priority", "Status", "Due", "Due In", "%", "Description"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)   # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)   # Project
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)   # Assignee
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)   # Priority
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)   # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)   # Due
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)   # Due In
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)   # %
        header.setSectionResizeMode(8, QHeaderView.Stretch)            # Description

        ll.addWidget(self.table)
        splitter.addWidget(left)

        # RIGHT: editor + subtasks
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)

        editor_box = QGroupBox("Selected Task Editor")
        ef = QFormLayout(editor_box)
        ef.setLabelAlignment(Qt.AlignLeft)
        ef.setFormAlignment(Qt.AlignTop)

        self.e_id = QLabel("-")

        self.e_project = QComboBox()
        self.e_assignee = QComboBox()
        self.e_assignee.addItems(self.users)

        self.e_priority = QComboBox()
        self.e_priority.addItems(self.PRIORITIES)

        self.e_status = QComboBox()
        self.e_status.addItems(self.STATUSES)

        self.e_due = QLineEdit()
        self.e_due.setPlaceholderText("Due time ISO")
        self.e_desc = QLineEdit()
        self.e_pct = QLabel("-")

        ef.addRow("Task ID", self.e_id)
        ef.addRow("Project", self.e_project)
        ef.addRow("Assignee", self.e_assignee)
        ef.addRow("Priority", self.e_priority)
        ef.addRow("Status", self.e_status)
        ef.addRow("Due Time", self.e_due)
        ef.addRow("Description", self.e_desc)
        ef.addRow("% Complete", self.e_pct)

        rl.addWidget(editor_box)

        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setProperty("variant", "secondary")
        self.btn_save.setEnabled(False)
        btn_row.addWidget(self.btn_save)
        btn_row.addStretch()
        rl.addLayout(btn_row)

        sub_box = QGroupBox("Subtasks (double-click to toggle done)")
        sl = QVBoxLayout(sub_box)

        self.sub_table = QTableWidget(0, 3)
        self.sub_table.setHorizontalHeaderLabels(["Done", "Subtask", "ID"])
        self.sub_table.verticalHeader().setVisible(False)
        self.sub_table.verticalHeader().setDefaultSectionSize(28)
        self.sub_table.setAlternatingRowColors(True)

        sh = self.sub_table.horizontalHeader()
        sh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(1, QHeaderView.Stretch)
        sh.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        sl.addWidget(self.sub_table)

        add_sub = QHBoxLayout()
        self.sub_title = QLineEdit()
        self.sub_title.setPlaceholderText("New subtask title")
        self.btn_add_sub = QPushButton("Add Subtask")
        add_sub.addWidget(self.sub_title, 6)
        add_sub.addWidget(self.btn_add_sub, 2)
        sl.addLayout(add_sub)

        rl.addWidget(sub_box)
        rl.addStretch()

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter)

        # -------------------- Events --------------------
        self.btn_add.clicked.connect(self.on_create)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_reload_projects.clicked.connect(self.reload_projects)
        self.table.itemSelectionChanged.connect(self.on_select_row)

        self.btn_save.clicked.connect(self.on_save_task)
        self.btn_add_sub.clicked.connect(self.on_add_subtask)
        self.sub_table.cellDoubleClicked.connect(self.on_toggle_subtask)

        # update "Due In" periodically
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_due_in_only)
        self._timer.start(30_000)

        # initial loads
        self.reload_projects()
        self.refresh()

    # ---------- Projects ----------
    def reload_projects(self):
        projs = list_projects() or []

        def fill(combo: QComboBox):
            current_id = combo.currentData() if combo.count() else None
            combo.blockSignals(True)
            combo.clear()
            for p in projs:
                combo.addItem(p.get("name", ""), p.get("id", ""))
            # restore selection
            if current_id is not None:
                for i in range(combo.count()):
                    if combo.itemData(i) == current_id:
                        combo.setCurrentIndex(i)
                        break
            combo.blockSignals(False)

        fill(self.c_project)
        fill(self.e_project)

    # ---------- Refresh ----------
    def refresh(self):
        tasks = list_todos() or []
        self._row_to_task_id = [t["id"] for t in tasks]
        self.table.setRowCount(len(tasks))

        for r, t in enumerate(tasks):
            pct = compute_task_pct(t)
            due = t.get("due_time", "")

            self.table.setItem(r, 0, _ro(t.get("id", "")))
            self.table.setItem(r, 1, _ro(t.get("project_name", "")))
            self.table.setItem(r, 2, _ro(t.get("assignee", "")))
            self.table.setItem(r, 3, _ro(t.get("priority", "")))
            self.table.setItem(r, 4, _ro(t.get("status", "")))
            self.table.setItem(r, 5, _ro(due))
            self.table.setItem(r, 6, _ro(due_in_str(due)))
            self.table.setItem(r, 7, _ro(f"{pct}%"))
            self.table.setItem(r, 8, _ro(t.get("description", "")))

        if self._selected_task_id and self._selected_task_id in self._row_to_task_id:
            row = self._row_to_task_id.index(self._selected_task_id)
            self.table.blockSignals(True)
            self.table.selectRow(row)
            self.table.blockSignals(False)
            self.load_selected(self._selected_task_id)
        else:
            self.clear_editor()

    def refresh_due_in_only(self):
        tasks = list_todos() or []
        for r, t in enumerate(tasks):
            if r >= self.table.rowCount():
                break
            due = t.get("due_time", "")
            pct = compute_task_pct(t)
            self.table.setItem(r, 6, _ro(due_in_str(due)))
            self.table.setItem(r, 7, _ro(f"{pct}%"))

    # ---------- Selection ----------
    def clear_editor(self):
        self._selected_task_id = None
        self.e_id.setText("-")
        self.e_due.setText("")
        self.e_desc.setText("")
        self.e_pct.setText("-")
        self.sub_table.setRowCount(0)
        self.btn_save.setEnabled(False)

        if self.e_project.count():
            self.e_project.setCurrentIndex(0)
        if self.e_assignee.count():
            self.e_assignee.setCurrentIndex(0)
        self.e_priority.setCurrentText("P2")
        self.e_status.setCurrentText("TODO")

    def on_select_row(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._row_to_task_id):
            self.clear_editor()
            return
        self.load_selected(self._row_to_task_id[row])

    def load_selected(self, task_id: str):
        t = next((x for x in (list_todos() or []) if x.get("id") == task_id), None)
        if not t:
            self.clear_editor()
            return

        self._selected_task_id = task_id
        self.e_id.setText(t.get("id", ""))

        # project by id
        pid = t.get("project_id", "")
        for i in range(self.e_project.count()):
            if self.e_project.itemData(i) == pid:
                self.e_project.setCurrentIndex(i)
                break

        ass = t.get("assignee", "")
        if ass and ass in self.users:
            self.e_assignee.setCurrentText(ass)

        pr = t.get("priority", "P2")
        if pr in self.PRIORITIES:
            self.e_priority.setCurrentText(pr)

        st = t.get("status", "TODO")
        if st in self.STATUSES:
            self.e_status.setCurrentText(st)

        self.e_due.setText(t.get("due_time", ""))
        self.e_desc.setText(t.get("description", ""))

        self.e_pct.setText(f"{compute_task_pct(t)}%")
        self.load_subtasks(t)
        self.btn_save.setEnabled(True)

    def load_subtasks(self, t: dict):
        subs = t.get("subtasks") or []
        self.sub_table.setRowCount(len(subs))
        for r, s in enumerate(subs):
            done_item = QTableWidgetItem("✓" if s.get("done") else "")
            done_item.setTextAlignment(Qt.AlignCenter)
            done_item.setFlags(done_item.flags() & ~Qt.ItemIsEditable)
            self.sub_table.setItem(r, 0, done_item)
            self.sub_table.setItem(r, 1, _ro(s.get("title", "")))
            self.sub_table.setItem(r, 2, _ro(s.get("id", "")))

    # ---------- Actions ----------
    def on_create(self):
        # keep projects fresh
        self.reload_projects()

        if self.c_project.count() == 0:
            QMessageBox.warning(self, "No Projects", "Create a project first.")
            return

        desc = self.c_desc.text().strip()
        if not desc:
            QMessageBox.warning(self, "Validation", "Task description is required.")
            return

        proj_id = self.c_project.currentData()
        proj_name = self.c_project.currentText()

        if not proj_id:
            QMessageBox.warning(self, "Validation", "Select a valid project.")
            return

        create_todo(
            project_id=str(proj_id),
            project_name=str(proj_name),
            assignee=self.c_assignee.currentText(),
            description=desc,
            priority=self.c_priority.currentText(),
            due_iso=self.c_due.text().strip(),
            status=self.c_status.currentText(),
        )

        self.c_desc.clear()
        self.c_due.clear()
        self.refresh()

    def on_save_task(self):
        if not self._selected_task_id:
            return

        patch = {
            "project_id": self.e_project.currentData(),
            "project_name": self.e_project.currentText(),
            "assignee": self.e_assignee.currentText(),
            "priority": self.e_priority.currentText(),
            "status": self.e_status.currentText(),
            "due_time": self.e_due.text().strip(),
            "description": self.e_desc.text().strip(),
        }

        update_todo(self._selected_task_id, patch)
        self.refresh()

    def on_add_subtask(self):
        if not self._selected_task_id:
            QMessageBox.information(self, "Select Task", "Select a task first.")
            return

        title = self.sub_title.text().strip()
        if not title:
            return

        add_subtask(self._selected_task_id, title)
        self.sub_title.clear()
        self.refresh()

    def on_toggle_subtask(self, row: int, col: int):
        if not self._selected_task_id:
            return

        sid_item = self.sub_table.item(row, 2)
        if not sid_item:
            return
        sid = sid_item.text()

        t = next((x for x in (list_todos() or []) if x.get("id") == self._selected_task_id), None)
        if not t:
            return

        s = next((x for x in (t.get("subtasks") or []) if x.get("id") == sid), None)
        if not s:
            return

        toggle_subtask(self._selected_task_id, sid, not bool(s.get("done")))
        self.refresh()