from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from customer import (
    search_customers, get_customer, add_customer, update_customer, delete_customer,
)


class CustomerDialog(QDialog):
    def __init__(self, customer_id: int = 0, parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.setWindowTitle("Edit Company" if customer_id else "Add Company")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Company name *")
        self.name_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Name:", self.name_edit)

        self.mobile_edit = QLineEdit()
        self.mobile_edit.setPlaceholderText("Mobile number")
        self.mobile_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Mobile:", self.mobile_edit)

        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("Address")
        self.address_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Address:", self.address_edit)

        layout.addLayout(form)

        if customer_id:
            c = get_customer(customer_id)
            if c:
                self.name_edit.setText(c["name"])
                self.mobile_edit.setText(c.get("mobile", ""))
                self.address_edit.setText(c.get("address", ""))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Error", "Company name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "mobile": self.mobile_edit.text().strip(),
            "address": self.address_edit.text().strip(),
        }


class CustomerWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Companies")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name or mobile...")
        self.search_edit.setFixedWidth(350)
        self.search_edit.setStyleSheet("padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;")
        self.search_edit.textChanged.connect(self._refresh)
        toolbar.addWidget(self.search_edit)

        toolbar.addStretch()

        add_btn = QPushButton("+ Add Company")
        add_btn.setStyleSheet("""
            QPushButton { background: #4caf50; color: white; padding: 8px 20px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388e3c; }
        """)
        add_btn.clicked.connect(self._add_customer)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)
        layout.addSpacing(12)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Name", "Mobile", "Address", "Added On", ""]
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
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self._refresh()

    def _refresh(self):
        query = self.search_edit.text()
        customers = search_customers(query)
        self.table.setRowCount(0)
        for c in customers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(c["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(c["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(c.get("mobile", "")))
            self.table.setItem(row, 3, QTableWidgetItem(c.get("address", "")))
            self.table.setItem(row, 4, QTableWidgetItem(c.get("created_at", "")[:10]))

            action_w = QWidget()
            action_layout = QHBoxLayout(action_w)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)

            cid = c["id"]
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(50, 26)
            edit_btn.setStyleSheet("background: #2196f3; color: white; border: none; border-radius: 3px;")
            edit_btn.clicked.connect(lambda checked, cid=cid: self._edit_customer(cid))
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("Del")
            del_btn.setFixedSize(50, 26)
            del_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
            del_btn.clicked.connect(lambda checked, cid=cid: self._delete_customer(cid))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 5, action_w)

    def _add_customer(self):
        dialog = CustomerDialog(0, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            add_customer(**data)
            self._refresh()

    def _edit_customer(self, customer_id: int):
        dialog = CustomerDialog(customer_id, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            update_customer(customer_id, **data)
            self._refresh()

    def _delete_customer(self, customer_id: int):
        ok = QMessageBox.question(
            self, "Confirm", "Delete this customer?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok == QMessageBox.Yes:
            delete_customer(customer_id)
            self._refresh()
