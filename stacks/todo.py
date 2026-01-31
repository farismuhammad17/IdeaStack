from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLineEdit
from PyQt5.QtCore import Qt

class Stack(QWidget):
    def __init__(self, stack_name, current_data):
        super().__init__()

        self.stack_name = stack_name
        self.current_data = current_data

        self.layout = QVBoxLayout(self)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter task and press Enter...")
        self.input_field.returnPressed.connect(self.add_task)

        self.list_widget = QListWidget()

        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.list_widget)

        self.load_data()

    def add_task(self, text=None, checked=False):
        task_text = text if text else self.input_field.text()
        if not task_text:
            return

        item = QListWidgetItem(task_text)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
        state = Qt.Checked if checked else Qt.Unchecked
        item.setCheckState(state)

        self.list_widget.addItem(item)
        self.input_field.clear()

    def get_data(self):
        tasks = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            tasks.append({
                "text": item.text(),
                "done": item.checkState() == Qt.Checked
            })

        self.current_data['data'][self.stack_name]['content'] = tasks
        return self.current_data

    def load_data(self):
        content = self.current_data['data'][self.stack_name].get('content', [])
        for task in content:
            self.add_task(task['text'], task['done'])
