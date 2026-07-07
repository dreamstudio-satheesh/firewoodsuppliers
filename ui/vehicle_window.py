from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from vehicle import (
    search_vehicles, get_vehicle, add_vehicle, update_vehicle, delete_vehicle,
)


class VehicleDialog(QDialog):
    def __init__(self, vehicle_id: int = 0, parent=None):
        super().__init__(parent)
        self.vehicle_id = vehicle_id
        self.setWindowTitle("Edit Vehicle" if vehicle_id else "Add Vehicle")
        self.setMinimumWidth(400)

        form = QFormLayout(self)
        form.setSpacing(10)

        self.vehicle_no = QLineEdit()
        self.vehicle_no.setPlaceholderText("e.g., TN38 AB 1234")
        self.vehicle_no.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Vehicle No:", self.vehicle_no)

        self.owner_name = QLineEdit()
        self.owner_name.setPlaceholderText("Owner name")
        self.owner_name.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Owner Name:", self.owner_name)

        self.mobile = QLineEdit()
        self.mobile.setPlaceholderText("Mobile number")
        self.mobile.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Mobile:", self.mobile)

        if vehicle_id:
            v = get_vehicle(vehicle_id)
            if v:
                self.vehicle_no.setText(v["vehicle_no"])
                self.owner_name.setText(v.get("owner_name", ""))
                self.mobile.setText(v.get("mobile", ""))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _validate(self):
        if not self.vehicle_no.text().strip():
            QMessageBox.warning(self, "Error", "Vehicle number is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "vehicle_no": self.vehicle_no.text().strip(),
            "owner_name": self.owner_name.text().strip(),
            "mobile": self.mobile.text().strip(),
        }


class VehicleWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Vehicles")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by vehicle no, owner, or mobile...")
        self.search_edit.setFixedWidth(350)
        self.search_edit.setStyleSheet("padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;")
        self.search_edit.textChanged.connect(self._refresh)
        toolbar.addWidget(self.search_edit)

        toolbar.addStretch()

        add_btn = QPushButton("+ Add Vehicle")
        add_btn.setStyleSheet("""
            QPushButton { background: #4caf50; color: white; padding: 8px 20px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388e3c; }
        """)
        add_btn.clicked.connect(self._add_vehicle)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)
        layout.addSpacing(12)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Vehicle No", "Owner Name", "Mobile", ""]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setColumnHidden(0, True)
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 4px; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 6px; font-weight: bold; }
            QTableWidget::item { padding: 6px; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self._refresh()

    def _refresh(self):
        query = self.search_edit.text()
        vehicles = search_vehicles(query)
        self.table.setRowCount(0)
        for v in vehicles:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(v["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(v["vehicle_no"]))
            self.table.setItem(row, 2, QTableWidgetItem(v.get("owner_name", "")))
            self.table.setItem(row, 3, QTableWidgetItem(v.get("mobile", "")))

            action_w = QWidget()
            action_layout = QHBoxLayout(action_w)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)

            vid = v["id"]
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(50, 26)
            edit_btn.setStyleSheet("background: #2196f3; color: white; border: none; border-radius: 3px;")
            edit_btn.clicked.connect(lambda checked, vid=vid: self._edit_vehicle(vid))
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("Del")
            del_btn.setFixedSize(50, 26)
            del_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
            del_btn.clicked.connect(lambda checked, vid=vid: self._delete_vehicle(vid))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 4, action_w)

    def _add_vehicle(self):
        dialog = VehicleDialog(0, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            add_vehicle(**data)
            self._refresh()

    def _edit_vehicle(self, vehicle_id: int):
        dialog = VehicleDialog(vehicle_id, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            update_vehicle(vehicle_id, **data)
            self._refresh()

    def _delete_vehicle(self, vehicle_id: int):
        ok = QMessageBox.question(
            self, "Confirm", "Delete this vehicle?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok == QMessageBox.Yes:
            delete_vehicle(vehicle_id)
            self._refresh()
