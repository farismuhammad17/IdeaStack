import os
import sys
import json
import importlib

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QSplitter, QTreeWidget, QLabel,
    QShortcut, QInputDialog, QTreeWidgetItem,
    QMenu, QMessageBox
)

class Sidebar(QTreeWidget):
    def __init__(self, parent_window):
        super().__init__()

        self.parent_window = parent_window

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.InternalMove)

    def drop_event(self, event):
        dragged_item = self.currentItem()
        target_item = self.itemAt(event.pos())

        if target_item:
            target_info = self.parent_window.current_data['data'].get(target_item.text(0), {})
            if target_info.get('type') != 'folder':
                event.ignore()
                return

        old_path = self.parent_window.get_full_path(dragged_item)
        super().drop_event(event)
        new_path = self.parent_window.get_full_path(dragged_item)

        if old_path != new_path:
            if old_path in self.parent_window.current_data['hierarchy']:
                self.parent_window.current_data['hierarchy'].remove(old_path)
            self.parent_window.current_data['hierarchy'].append(new_path)
            self.parent_window.update_json()

class IdeaStack(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_data = {}
        self.active_stack_name = None
        self.workspace = None

        self.setWindowTitle("Idea Stack")
        self.setMinimumSize(1280, 720)

        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)

        self.layout = QVBoxLayout()
        self.main_container.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)

        self.sidebar = Sidebar(self)
        self.sidebar.setHeaderLabel("IdeaStacks")
        self.splitter.addWidget(self.sidebar)
        self.sidebar.setMinimumWidth(150)

        self.sidebar.setDragEnabled(True)
        self.sidebar.setAcceptDrops(True)
        self.sidebar.setDragDropMode(QTreeWidget.InternalMove)

        self.sidebar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sidebar.customContextMenuRequested.connect(self.show_right_click)

        self.content_area = QLabel("Select a stack to view content")
        self.content_area.setAlignment(Qt.AlignCenter)
        self.splitter.addWidget(self.content_area)

        self.splitter.setSizes([200, 720])

        self.create_temp_json()

        for path in sorted(self.current_data["hierarchy"]):
            parts = path.split("/")
            parent_item = self.sidebar

            for part in parts:
                found_item = None

                if parent_item == self.sidebar:
                    count = parent_item.topLevelItemCount()
                else:
                    count = parent_item.childCount()
                not_sidebar = parent_item != self.sidebar

                for j in range(count):
                    child = parent_item.child(j) if not_sidebar else parent_item.topLevelItem(j)
                    if child.text(0) == part:
                        found_item = child
                        break

                if found_item:
                    parent_item = found_item
                else:
                    new_item = QTreeWidgetItem(parent_item, [part])
                    parent_item = new_item

        self.sidebar.itemClicked.connect(self.load_stack_content)

        self.new_stack_key = QShortcut(QKeySequence("Ctrl+N"), self)
        self.new_stack_key.activated.connect(self.show_stack_selector)

    def show_stack_selector(self):
        stack_options = ["Folder"] + [
            file[:-3]
            for file in os.listdir("stacks")
            if file.endswith(".py")
        ]

        stack_type, ok = QInputDialog.getItem(
            self,
            "New Stack",
            "Select stack type:",
            stack_options,
            0,
            False
        )

        if ok and stack_type:
            if stack_type == "Folder":
                self.add_folder_to_sidebar()
            else:
                self.add_stack_to_sidebar(stack_type)

    def add_folder_to_sidebar(self):
        name = "New Folder"

        if name in self.current_data['data']:
            i = 1
            while f"{name} {i}" in self.current_data['data']:
                i += 1
            name = f"{name} {i}"

        new_folder = QTreeWidgetItem(self.sidebar, [name])
        new_folder.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)

        self.current_data['hierarchy'].append(name)
        self.current_data['data'][name] = {"type": "folder"}

        self.update_json()

    def add_stack_to_sidebar(self, stack_type):
        name = f"New {stack_type}"

        if name in self.current_data["data"]:
            i = 1
            while f"{name} {i}" in self.current_data["data"]:
                i += 1
            name = f"{name} {i}"

        QTreeWidgetItem(self.sidebar, [name])

        self.current_data['hierarchy'].append(name)
        self.current_data['data'][name] = {"type": stack_type}

        self.update_json()

    def load_stack_content(self, item):
        if self.workspace:
            self.current_data = self.workspace.get_data()
            self.update_json()

        stack_name = item.text(0)
        stack_info = self.current_data['data'].get(stack_name)

        if not stack_info or stack_info.get('type') == 'folder':
            return

        stack_type = stack_info['type']

        current_sizes = self.splitter.sizes()

        old_widget = self.splitter.widget(1)
        if old_widget:
            old_widget.setParent(None)
            old_widget.deleteLater()

        try:
            module = importlib.import_module(f"stacks.{stack_type}")
            stack_class = getattr(module, "Stack")
            self.workspace = stack_class(stack_name, self.current_data)

        except (ImportError, AttributeError) as e:
            print(f"Error loading {stack_name}: {e}")

        self.splitter.addWidget(self.workspace)
        self.splitter.setSizes(current_sizes)

        self.active_stack_name = stack_name

    def show_right_click(self, position):
        item = self.sidebar.itemAt(position)
        if item is None:
            return

        menu = QMenu()

        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")

        action = menu.exec_(self.sidebar.mapToGlobal(position))

        if action == rename_action:
            self.rename_item(item)
        elif action == delete_action:
            self.delete_item(item)

    def rename_item(self, item):
        old_name = item.text(0)

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Stack",
            "Enter new name:",
            text=old_name
        )

        if not ok or not new_name or new_name == old_name:
            return

        if new_name in self.current_data['data']:
            QMessageBox.critical(
                self,
                "Rename Error",
                f"The name '{new_name}' is already in use. Please choose a unique name."
            )

            return

        for i, path in enumerate(self.current_data["hierarchy"]):
            parts = path.split("/")
            if parts[-1] == old_name:
                parts[-1] = new_name
                self.current_data["hierarchy"][i] = "/".join(parts)

                break

        if old_name == self.active_stack_name:
            self.active_stack_name = new_name

        self.current_data['data'][new_name] = self.current_data['data'].pop(old_name)

        item.setText(0, new_name)
        self.update_json()

    def delete_item(self, item):
        stack_name = item.text(0)

        reply = QMessageBox.question(
            self,
            "Delete",
            f"Are you sure you want to delete {stack_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        current_sizes = self.splitter.sizes()

        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            index = self.sidebar.indexOfTopLevelItem(item)
            self.sidebar.takeTopLevelItem(index)

        if stack_name in self.current_data['data']:
            self.current_data['data'].pop(stack_name)

        for path in self.current_data['hierarchy'][:]:
            if path.split('/')[-1] == stack_name:
                self.current_data['hierarchy'].remove(path)
                break

        if self.active_stack_name == stack_name:
            old_widget = self.splitter.widget(1)
            if old_widget:
                old_widget.setParent(None)
                old_widget.deleteLater()

            self.content_area = QLabel("Select a stack to view content")
            self.content_area.setAlignment(Qt.AlignCenter)
            self.splitter.addWidget(self.content_area)

            self.splitter.setSizes(current_sizes)

            self.active_stack_name = None

        self.update_json()

    def create_temp_json(self):
        if not os.path.exists("temp.json"):
            default_scheme = {
                "name": None,
                "hierarchy": [],
                "data": {}
            }

            with open("temp.json", "w", encoding="utf-8") as file:
                json.dump(default_scheme, file, indent=4)

            self.current_data = default_scheme

        else:
            with open("temp.json", "r", encoding="utf-8") as file:
                self.current_data = json.load(file)

    def update_json(self):
        with open("temp.json", "w", encoding="utf-8") as file:
            json.dump(self.current_data, file, indent=4)

    def get_full_path(self, item):
        parts = []
        curr = item
        while curr:
            parts.insert(0, curr.text(0))
            curr = curr.parent()
        return "/".join(parts)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = IdeaStack()
    window.show()

    sys.exit(app.exec())
