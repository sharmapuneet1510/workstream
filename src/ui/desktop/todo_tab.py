from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox
)
from PySide6.QtCore import Qt

from services.todo_store import (
    list_todos, create_todo, add_subtask,
    update_todo_status, update_subtask_status,
    todo_progress, due_in
)
from services.project_store import list_projects
from services.config_store import list_users


def _ro(txt):
    it = QTableWidgetItem(txt)
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    return it


class TodoListTab(QWidget):
    def __init__(self):
        super().__init__()
        self.users = list_users()
        self.projects = list_projects()

        layout = QVBoxLayout(self)

        # Create todo
        form = QHBoxLayout()
        self.t_title = QLineEdit()
        self.t_title.setPlaceholderText("Task description")
        self.t_assignee = QComboBox()
        self.t_assignee.addItems(self.users)
        self.t_project = QComboBox()
        self.t_project.addItems([p["name"] for p in self.projects])
        self.t_priority = QComboBox()
        self.t_priority.addItems(["High", "Medium", "Low"])
        self.t_due = QLineEdit()
        self.t_due.setPlaceholderText("Due date ISO")
        self.btn_add = QPushButton("Add To-Do")

        for w in [self.t_title, self.t_assignee, self.t_project, self.t_priority, self.t_due, self.btn_add]:
            form.addWidget(w)

        layout.addLayout(form)

        # Table
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Task", "Assignee", "Project", "Priority",
            "Status", "Due In", "Progress %", "Subtasks"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.btn_add.clicked.connect(self.on_add)
        self.refresh()

    def on_add(self):
        title = self.t_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation", "Task title required")
            return

        proj = next(p for p in self.projects if p["name"] == self.t_project.currentText())

        create_todo(
            title=title,
            assignee=self.t_assignee.currentText(),
            project_id=proj["id"],
            priority=self.t_priority.currentText(),
            due_date=self.t_due.text().strip(),
        )
        self.t_title.clear()
        self.t_due.clear()
        self.refresh()

    def refresh(self):
        todos = list_todos()
        self.table.setRowCount(len(todos))
        for r, t in enumerate(todos):
            self.table.setItem(r, 0, _ro(t["id"]))
            self.table.setItem(r, 1, _ro(t["title"]))
            self.table.setItem(r, 2, _ro(t["assignee"]))
            proj = next(p["name"] for p in self.projects if p["id"] == t["project_id"])
            self.table.setItem(r, 3, _ro(proj))
            self.table.setItem(r, 4, _ro(t["priority"]))
            self.table.setItem(r, 5, _ro(t["status"]))
            self.table.setItem(r, 6, _ro(due_in(t["due_date"])))
            self.table.setItem(r, 7, _ro(str(todo_progress(t))))
            self.table.setItem(r, 8, _ro(str(len(t["subtasks"]))))