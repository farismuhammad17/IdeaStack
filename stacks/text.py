import json

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QTextEdit, QShortcut
)

class Stack(QTextEdit):
    def __init__(self, stack_name: str, current_data: dict = None):
        super().__init__()

        self.stack_name = stack_name
        self.current_data = current_data

        if not current_data:
            with open("temp.json", "r", encoding="utf-8") as file:
                self.current_data = json.load(file)

        if "content" not in self.current_data["data"][self.stack_name]:
            self.current_data["data"][self.stack_name]["content"] = ""
        self.text = self.current_data["data"][self.stack_name]["content"]

        self.setPlainText(self.text)
        self.textChanged.connect(self.sync_data)

        self.new_stack_key = QShortcut(QKeySequence("Ctrl+S"), self)
        self.new_stack_key.activated.connect(self.save_data)

    def sync_data(self):
        self.current_data["data"][self.stack_name]["content"] = self.toPlainText()

    def save_data(self):
        with open("temp.json", "w", encoding="utf-8") as file:
            json.dump(self.current_data, file, indent=4)

    def get_data(self):
        self.current_data["data"][self.stack_name]["content"] = self.toPlainText()
        return self.current_data
