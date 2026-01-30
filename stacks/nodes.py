import json

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QShortcut,
    QGraphicsProxyWidget,
    QGraphicsWidget,
    QGraphicsLinearLayout,
    QTextEdit,
    QPushButton,
    QMenu,
    QGraphicsEllipseItem,
    QGraphicsPathItem
)
from PyQt5.QtGui import QBrush, QPen, QColor, QPainter, QKeySequence, QPainterPath

NODE_BG_COLOR = QColor(45, 45, 45)
SOCKET_COLOR = QColor("#555")
WIRE_COLOR = QColor("#00d627")
WIRE_SELECTED_COLOR = QColor("#FFCC00")
COLORS = {
    "Comment": "#4a4a4a"
}

class Socket(QGraphicsEllipseItem):
    def __init__(self, parent, is_input=True):
        super().__init__(-7, -7, 14, 14, parent)

        self.is_input = is_input

        self.setBrush(QBrush(SOCKET_COLOR))
        self.setPen(QPen(Qt.transparent))

        self.connected_wires = []

        if is_input:
            self.setPos(0, 50)
        else:
            self.setPos(180, 50)

    def mousePressEvent(self, event):
        view = self.scene().views()[0]
        view.start_connection(self)

        event.accept()

    def update_wires(self):
        for wire in self.connected_wires:
            wire.update_path()

class Wire(QGraphicsPathItem):
    def __init__(self, start_socket, end_socket):
        super().__init__()

        self.start_socket = start_socket
        self.end_socket = end_socket
        self.setPen(QPen(WIRE_COLOR, 2))

        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)
        self.setZValue(-1)

        self.update_path()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.remove_self()
        else:
            super().keyPressEvent(event)

    def remove_self(self):
        scene = self.scene()

        if self.start_socket and self in self.start_socket.connected_wires:
            self.start_socket.connected_wires.remove(self)
        if self.end_socket and self in self.end_socket.connected_wires:
            self.end_socket.connected_wires.remove(self)

        if scene:
            scene.removeItem(self)

    def update_path(self):
        path = QPainterPath()

        p1 = self.start_socket.scenePos()
        p2 = self.end_socket.scenePos()

        path.moveTo(p1)

        path.cubicTo(p1.x() + 50, p1.y(), p2.x() - 50, p2.y(), p2.x(), p2.y())
        self.setPath(path)

    def paint(self, painter, option, widget):
        if self.isSelected():
            self.setPen(QPen(WIRE_SELECTED_COLOR, 3))
        else:
            self.setPen(QPen(WIRE_COLOR, 2))

        super().paint(painter, option, widget)

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

class Node(QGraphicsWidget):
    def __init__(self, x, y, node_type="Comment"):
        super().__init__()

        self.node_type = node_type

        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemIsFocusable |
            QGraphicsItem.ItemSendsScenePositionChanges
        )

        self.layout = QGraphicsLinearLayout(Qt.Vertical)
        self.setLayout(self.layout)

        self.type_button = QPushButton(f"{self.node_type.upper()}")
        self.type_button.setStyleSheet("""
            QPushButton {
                color: #4a4a4a;
                border: 0;
            }
        """)
        self.type_button.clicked.connect(self.show_type_menu)
        self.type_button.setFocusPolicy(Qt.NoFocus)

        self.proxy_type = QGraphicsProxyWidget(self)
        self.proxy_type.setWidget(self.type_button)
        self.layout.addItem(self.proxy_type)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Enter content...")
        self.editor.setFixedSize(180, 100)
        self.editor.setStyleSheet("""
            background-color: #222;
            color: white;
            border: 1px solid #444;
        """)

        self.proxy_editor = QGraphicsProxyWidget(self)
        self.proxy_editor.setWidget(self.editor)
        self.layout.addItem(self.proxy_editor)

        self.setAutoFillBackground(False)

        self.update_type()

        self.input_socket = Socket(self, is_input=True)
        self.output_socket = Socket(self, is_input=False)

    def show_type_menu(self):
        menu = QMenu()
        menu.addAction("Comment")

        action = menu.exec_(self.type_button.mapToGlobal(self.type_button.rect().bottomLeft()))

        if action:
            self.node_type = action.text()
            self.type_button.setText(self.node_type.upper())

            self.update_type()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            if hasattr(self, 'input_socket'):
                self.input_socket.update_wires()
            if hasattr(self, 'output_socket'):
                self.output_socket.update_wires()

        elif change == QGraphicsItem.ItemSelectedHasChanged:
            color = "#FFCC00" if value else COLORS[self.node_type]
            self.type_button.setStyleSheet(f"color: {color}; background: transparent; text-align: left; border: 0; font-weight: bold;")

        return super().itemChange(change, value)

    def update_type(self):
        color = COLORS[self.node_type]

        self.type_button.setStyleSheet(f"""
            color: {color};
            background: transparent;
            text-align: left;
            border: 0;
            font-weight: bold;
        """)

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.remove_self()
        else:
            super().keyPressEvent(event)

    def remove_self(self):
        all_wires = self.input_socket.connected_wires + self.output_socket.connected_wires

        for wire in all_wires[:]:
            wire.remove_self()
        if self.scene():
            self.scene().removeItem(self)

    def get_data(self):
        return {
            "id": id(self),
            "type": self.node_type,
            "x": self.x(),
            "y": self.y(),
            "content": self.editor.toPlainText()
        }

class Stack(QGraphicsView):
    def __init__(self, stack_name: str, current_data: dict = None):
        super().__init__()

        self.stack_name = stack_name
        self.current_data = current_data

        self.scene = QGraphicsScene(-5000, -5000, 10000, 10000)
        self.setScene(self.scene)

        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.setRenderHint(QPainter.Antialiasing)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        self.node_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        self.node_shortcut.activated.connect(self.add_node_at_center)

        self.active_wire = None
        self.start_socket = None

        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.save_to_file)

        self.load_previous_data()

    def add_node_at_center(self):
        center_point = self.mapToScene(self.viewport().rect().center())
        new_node = Node(center_point.x(), center_point.y())

        self.scene.addItem(new_node)

    def make_connection(self, end_socket):
        self.active_wire.end_socket = end_socket

        self.start_socket.connected_wires.append(self.active_wire)
        end_socket.connected_wires.append(self.active_wire)

        self.active_wire.update_path()

    def start_connection(self, socket):
        self.setDragMode(QGraphicsView.NoDrag)

        self.start_socket = socket
        self.active_wire = Wire(socket, socket)

        self.scene.addItem(self.active_wire)

    def mouseMoveEvent(self, event):
        if self.active_wire:
            mouse_scene_pos = self.mapToScene(event.pos())

            path = QPainterPath()
            p1 = self.start_socket.scenePos()
            p2 = mouse_scene_pos
            path.moveTo(p1)

            path.cubicTo(p1.x() + 50, p1.y(), p2.x() - 50, p2.y(), p2.x(), p2.y())

            self.active_wire.setPath(path)
        else:
            super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if not item:
            if self.scene.focusItem():
                self.scene.focusItem().clearFocus()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        if self.active_wire:
            scene_pos = self.mapToScene(event.pos())
            items = self.scene.items(scene_pos)

            target_socket = None
            for item in items:
                if isinstance(item, Socket) and item != self.start_socket:
                    target_socket = item
                    break

            if target_socket and target_socket.is_input != self.start_socket.is_input:
                self.make_connection(target_socket)

            else:
                self.scene.removeItem(self.active_wire)

            if self.active_wire:
                self.active_wire.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)

            self.active_wire = None
            self.start_socket = None

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

    def load_previous_data(self):
        data = self.current_data["data"][self.stack_name]["content"]

        id_map = {}
        for n_data in data.get("nodes", []):
            node = Node(n_data["x"], n_data["y"], n_data["type"])
            node.editor.setPlainText(n_data["content"])
            self.scene.addItem(node)

            id_map[n_data["id"]] = node

        for w_data in data.get("wires", []):
            start_node = id_map.get(w_data["start_node"])
            end_node = id_map.get(w_data["end_node"])

            if start_node and end_node:
                wire = Wire(start_node.output_socket, end_node.input_socket)
                self.scene.addItem(wire)

                start_node.output_socket.connected_wires.append(wire)
                end_node.input_socket.connected_wires.append(wire)

                wire.update_path()

    def serialize(self):
        nodes_data = []
        wires_data = []

        for item in self.scene.items():
            if isinstance(item, Node):
                nodes_data.append(item.get_data())
            elif isinstance(item, Wire):
                wires_data.append({
                    "start_node": id(item.start_socket.parentItem()),
                    "end_node": id(item.end_socket.parentItem())
                })

        return {"nodes": nodes_data, "wires": wires_data}

    def save_to_file(self):
        self.current_data["data"][self.stack_name]["content"] = self.serialize()

        with open("temp.json", "w", encoding="utf-8") as f:
            json.dump(self.current_data, f, indent=4)

    def get_data(self):
        self.current_data["data"][self.stack_name]["content"] = self.serialize()
        return self.current_data
