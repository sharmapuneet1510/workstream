from __future__ import annotations

from typing import List

# ✅ FIX: Qt is required in _ro()
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QMessageBox, QGroupBox
)

from services.config_store import list_applications, list_users, list_workflow_config
from services.project_store import (
    list_projects, create_project, add_task,
    update_task_status, project_completion, category_completion
)
from services.release_store import (
    list_releases, create_release, countdown_str
)

from ui.desktop.release_editor import ReleaseEditorDialog
from ui.desktop.release_details_modal import ReleaseDetailsDialog


def _ro(text: str) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    return it


class ProjectManagementTab(QWidget):
    def __init__(self):
        super().__init__()
        self.apps = list_applications()
        self.users = list_users()

        layout = QVBoxLayout(self)

        box = QGroupBox("Create Project")
        form = QHBoxLayout(box)
        self.p_name = QLineEdit()
        self.p_name.setPlaceholderText("Project Name")
        self.p_app = QComboBox()
        self.p_app.addItems(self.apps)
        self.p_desc = QLineEdit()
        self.p_desc.setPlaceholderText("Description (optional)")
        self.btn_p_create = QPushButton("Add Project")
        form.addWidget(self.p_name)
        form.addWidget(QLabel("Application"))
        form.addWidget(self.p_app)
        form.addWidget(self.p_desc)
        form.addWidget(self.btn_p_create)
        layout.addWidget(box)

        layout.addWidget(QLabel("Projects (counts by status)"))
        self.projects_table = QTableWidget(0, 6)
        self.projects_table.setHorizontalHeaderLabels(["Project ID", "Name", "Application", "TODO", "IN_PROGRESS", "DONE"])
        self.projects_table.horizontalHeader().setStretchLastSection(True)
        self.projects_table.verticalHeader().setVisible(False)
        self.projects_table.verticalHeader().setDefaultSectionSize(28)
        layout.addWidget(self.projects_table)

        tbox = QGroupBox("Add Task to Selected Project")
        tform = QHBoxLayout(tbox)
        self.t_title = QLineEdit()
        self.t_title.setPlaceholderText("Task title")
        self.t_jira = QLineEdit()
        self.t_jira.setPlaceholderText("Jira Ref (e.g. ABC-123)")
        self.t_cat = QLineEdit()
        self.t_cat.setPlaceholderText("Category (QA/Dev/UAT/etc)")
        self.t_assignee = QComboBox()
        self.t_assignee.addItems(self.users)
        self.btn_t_add = QPushButton("Add Task")
        tform.addWidget(self.t_title)
        tform.addWidget(self.t_jira)
        tform.addWidget(self.t_cat)
        tform.addWidget(QLabel("Assignee"))
        tform.addWidget(self.t_assignee)
        tform.addWidget(self.btn_t_add)
        layout.addWidget(tbox)

        layout.addWidget(QLabel("Tasks for Selected Project"))
        self.tasks_table = QTableWidget(0, 7)
        self.tasks_table.setHorizontalHeaderLabels(["Task ID", "Title", "Jira", "Category", "Assignee", "Status", "Project %"])
        self.tasks_table.horizontalHeader().setStretchLastSection(True)
        self.tasks_table.verticalHeader().setVisible(False)
        self.tasks_table.verticalHeader().setDefaultSectionSize(28)
        layout.addWidget(self.tasks_table)

        layout.addWidget(QLabel("Category completion for Selected Project"))
        self.cat_table = QTableWidget(0, 4)
        self.cat_table.setHorizontalHeaderLabels(["Category", "Total", "Done", "Pct"])
        self.cat_table.horizontalHeader().setStretchLastSection(True)
        self.cat_table.verticalHeader().setVisible(False)
        self.cat_table.verticalHeader().setDefaultSectionSize(26)
        self.cat_table.setMaximumHeight(180)
        layout.addWidget(self.cat_table)

        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setProperty("variant", "secondary")
        self.btn_mark_todo = QPushButton("Set TODO")
        self.btn_mark_inp = QPushButton("Set IN_PROGRESS")
        self.btn_mark_done = QPushButton("Set DONE")
        btns.addWidget(self.btn_refresh)
        btns.addStretch()
        btns.addWidget(self.btn_mark_todo)
        btns.addWidget(self.btn_mark_inp)
        btns.addWidget(self.btn_mark_done)
        layout.addLayout(btns)

        self.btn_p_create.clicked.connect(self.on_create_project)
        self.btn_t_add.clicked.connect(self.on_add_task)
        self.btn_refresh.clicked.connect(self.refresh)
        self.projects_table.itemSelectionChanged.connect(self.refresh_selected_project_tasks)
        self.btn_mark_todo.clicked.connect(lambda: self.set_selected_task_status("TODO"))
        self.btn_mark_inp.clicked.connect(lambda: self.set_selected_task_status("IN_PROGRESS"))
        self.btn_mark_done.clicked.connect(lambda: self.set_selected_task_status("DONE"))

        self.refresh()

    def selected_project_id(self) -> str | None:
        row = self.projects_table.currentRow()
        if row < 0:
            return None
        return self.projects_table.item(row, 0).text()

    def refresh(self):
        projs = list_projects()
        self.projects_table.setRowCount(len(projs))
        for r, p in enumerate(projs):
            tasks = p.get("tasks", [])
            todo = sum(1 for t in tasks if t["status"] == "TODO")
            inp = sum(1 for t in tasks if t["status"] == "IN_PROGRESS")
            done = sum(1 for t in tasks if t["status"] == "DONE")
            self.projects_table.setItem(r, 0, _ro(p["id"]))
            self.projects_table.setItem(r, 1, _ro(p["name"]))
            self.projects_table.setItem(r, 2, _ro(p["application"]))
            self.projects_table.setItem(r, 3, _ro(str(todo)))
            self.projects_table.setItem(r, 4, _ro(str(inp)))
            self.projects_table.setItem(r, 5, _ro(str(done)))
        self.refresh_selected_project_tasks()

    def on_create_project(self):
        name = self.p_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Project name is required.")
            return
        create_project(name=name, application=self.p_app.currentText(), description=self.p_desc.text().strip())
        self.p_name.clear()
        self.p_desc.clear()
        self.refresh()

    def on_add_task(self):
        pid = self.selected_project_id()
        if not pid:
            QMessageBox.warning(self, "Select Project", "Select a project first.")
            return
        title = self.t_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation", "Task title is required.")
            return
        add_task(
            pid,
            title=title,
            jira_ref=self.t_jira.text().strip(),
            category=self.t_cat.text().strip() or "Uncategorized",
            assignee=self.t_assignee.currentText(),
            status="TODO",
        )
        self.t_title.clear()
        self.t_jira.clear()
        self.t_cat.clear()
        self.refresh_selected_project_tasks()
        self.refresh()

    def refresh_selected_project_tasks(self):
        pid = self.selected_project_id()
        if not pid:
            self.tasks_table.setRowCount(0)
            self.cat_table.setRowCount(0)
            return

        p = next((x for x in list_projects() if x["id"] == pid), None)
        if not p:
            return

        pct = project_completion(p)
        tasks = p.get("tasks", [])
        self.tasks_table.setRowCount(len(tasks))
        for r, t in enumerate(tasks):
            self.tasks_table.setItem(r, 0, _ro(t["id"]))
            self.tasks_table.setItem(r, 1, _ro(t["title"]))
            self.tasks_table.setItem(r, 2, _ro(t.get("jira_ref", "")))
            self.tasks_table.setItem(r, 3, _ro(t.get("category", "")))
            self.tasks_table.setItem(r, 4, _ro(t.get("assignee", "")))
            self.tasks_table.setItem(r, 5, _ro(t.get("status", "")))
            self.tasks_table.setItem(r, 6, _ro(f"{pct}%"))

        cats = category_completion(p)
        items = list(cats.items())
        self.cat_table.setRowCount(len(items))
        for r, (cat, v) in enumerate(items):
            self.cat_table.setItem(r, 0, _ro(cat))
            self.cat_table.setItem(r, 1, _ro(str(v["total"])))
            self.cat_table.setItem(r, 2, _ro(str(v["done"])))
            self.cat_table.setItem(r, 3, _ro(f'{v["pct"]}%'))

    def set_selected_task_status(self, status: str):
        pid = self.selected_project_id()
        if not pid:
            return
        row = self.tasks_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Task", "Select a task row first.")
            return
        task_id = self.tasks_table.item(row, 0).text()
        update_task_status(pid, task_id, status)
        self.refresh_selected_project_tasks()
        self.refresh()


class ReleaseManagementTab(QWidget):
    def __init__(self):
        super().__init__()
        self.users = list_users()
        self.workflow_cfg = list_workflow_config()
        self.templates = self.workflow_cfg.get("templates", [])

        layout = QVBoxLayout(self)

        create_box = QGroupBox("Create Release")
        create_form = QVBoxLayout(create_box)

        row1 = QHBoxLayout()
        self.r_name = QLineEdit()
        self.r_name.setPlaceholderText("Release name (e.g. Jan Staging Release)")
        self.r_manager = QComboBox()
        self.r_manager.addItems(self.users)
        row1.addWidget(self.r_name, 7)
        row1.addWidget(QLabel("Release Manager"))
        row1.addWidget(self.r_manager, 2)
        create_form.addLayout(row1)

        row2 = QHBoxLayout()
        self.r_start = QLineEdit()
        self.r_start.setPlaceholderText("Window Start ISO (e.g. 2026-01-20T22:00:00)")
        self.r_end = QLineEdit()
        self.r_end.setPlaceholderText("Window End ISO (e.g. 2026-01-20T23:30:00)")
        row2.addWidget(self.r_start)
        row2.addWidget(self.r_end)
        create_form.addLayout(row2)

        row3 = QHBoxLayout()
        self.r_desc = QLineEdit()
        self.r_desc.setPlaceholderText("Description")
        self.r_template = QComboBox()
        self.r_template.addItems([t["name"] for t in self.templates])
        self.btn_r_create = QPushButton("Create Release")
        row3.addWidget(self.r_desc, 7)
        row3.addWidget(QLabel("Workflow Template"))
        row3.addWidget(self.r_template, 2)
        row3.addWidget(self.btn_r_create, 2)
        create_form.addLayout(row3)

        layout.addWidget(create_box)

        layout.addWidget(QLabel("Releases"))
        self.releases_table = QTableWidget(0, 6)
        self.releases_table.setHorizontalHeaderLabels(
            ["Release ID", "Name", "Manager", "Window Start", "Window End", "Expected In"]
        )
        self.releases_table.horizontalHeader().setStretchLastSection(True)
        self.releases_table.verticalHeader().setVisible(False)
        self.releases_table.verticalHeader().setDefaultSectionSize(30)
        layout.addWidget(self.releases_table)

        bottom = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setProperty("variant", "secondary")

        self.btn_view = QPushButton("View Details")
        self.btn_edit = QPushButton("Edit Selected Release")
        self.btn_edit.setProperty("variant", "secondary")

        bottom.addWidget(self.btn_refresh)
        bottom.addStretch()
        bottom.addWidget(self.btn_view)
        bottom.addWidget(self.btn_edit)
        layout.addLayout(bottom)

        self.btn_r_create.clicked.connect(self.on_create_release)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_view.clicked.connect(self.view_selected_release)
        self.btn_edit.clicked.connect(self.edit_selected_release)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_countdowns_only)
        self._timer.start(30_000)

        self.refresh()

    def selected_release_id(self) -> str | None:
        row = self.releases_table.currentRow()
        if row < 0:
            return None
        return self.releases_table.item(row, 0).text()

    def on_create_release(self):
        name = self.r_name.text().strip()
        ws = self.r_start.text().strip()
        we = self.r_end.text().strip()
        if not name or not ws or not we:
            QMessageBox.warning(self, "Validation", "Release name, window start and window end are required.")
            return

        desc = self.r_desc.text().strip()
        manager = self.r_manager.currentText()

        selected_name = self.r_template.currentText()
        main_tpl = next((t for t in self.templates if t["name"] == selected_name), None)
        main_items = (main_tpl.get("items") if main_tpl else []) or []

        lm_name = self.workflow_cfg.get("last_minute_template_name", "Last Minute Add-ons")
        lm_tpl = next((t for t in self.templates if t["name"] == lm_name), None)
        lm_items = (lm_tpl.get("items") if lm_tpl else []) or []

        lm_days = int(self.workflow_cfg.get("last_minute_days_threshold", 4))

        create_release(
            name=name,
            description=desc,
            notes="",
            window_start_iso=ws,
            window_end_iso=we,
            release_manager=manager,
            project_ids=[],
            template_name=selected_name,
            template_items=main_items,
            last_minute_items=lm_items,
            last_minute_days_threshold=lm_days,
        )

        self.r_name.clear()
        self.r_start.clear()
        self.r_end.clear()
        self.r_desc.clear()
        self.refresh()

    def refresh(self):
        rels = list_releases()
        self.releases_table.setRowCount(len(rels))
        for r, rel in enumerate(rels):
            self.releases_table.setItem(r, 0, _ro(rel["id"]))
            self.releases_table.setItem(r, 1, _ro(rel.get("name", "")))
            self.releases_table.setItem(r, 2, _ro(rel.get("release_manager", "")))
            self.releases_table.setItem(r, 3, _ro(rel.get("window_start", "")))
            self.releases_table.setItem(r, 4, _ro(rel.get("window_end", "")))
            ws = rel.get("window_start", "")
            self.releases_table.setItem(r, 5, _ro(("Release in " + countdown_str(ws)) if ws else ""))

    def refresh_countdowns_only(self):
        for row in range(self.releases_table.rowCount()):
            ws = self.releases_table.item(row, 3).text() if self.releases_table.item(row, 3) else ""
            txt = ("Release in " + countdown_str(ws)) if ws else ""
            self.releases_table.setItem(row, 5, _ro(txt))

    def view_selected_release(self):
        rid = self.selected_release_id()
        if not rid:
            QMessageBox.information(self, "Select", "Select a release row first.")
            return
        dlg = ReleaseDetailsDialog(rid, self)
        dlg.exec()
        self.refresh()

    def edit_selected_release(self):
        rid = self.selected_release_id()
        if not rid:
            QMessageBox.information(self, "Select", "Select a release row first.")
            return
        rel = next((x for x in list_releases() if x["id"] == rid), None)
        if not rel:
            QMessageBox.warning(self, "Error", "Release not found.")
            return
        dlg = ReleaseEditorDialog(rel, self)
        if dlg.exec():
            self.refresh()


class WorkstreamDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Workstream Desktop")
        self.resize(1200, 800)

        tabs = QTabWidget()
        tabs.addTab(ProjectManagementTab(), "Project Management")
        tabs.addTab(ReleaseManagementTab(), "Release Management")

        root = QWidget()
        lay = QVBoxLayout(root)
        lay.addWidget(tabs)
        self.setCentralWidget(root)