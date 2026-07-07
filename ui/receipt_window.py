from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDoubleSpinBox, QDateEdit,
    QFormLayout, QGroupBox, QDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from receipt import (
    create_receipt, search_receipts, get_receipt, cancel_receipt,
)
from database import get_next_receipt_no
from customer import search_customers, get_all_customers, get_customer
from billing import search_sale_bills, get_sale_bill
from printer import generate_receipt_pdf, open_pdf


class ReceiptWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Receipts")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        toolbar = QHBoxLayout()

        self.list_search = QLineEdit()
        self.list_search.setPlaceholderText("Search by Receipt No, Bill No, Company...")
        self.list_search.setStyleSheet("padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;")
        self.list_search.textChanged.connect(self._search)
        toolbar.addWidget(self.list_search, 1)

        self.list_date_from = QDateEdit()
        self.list_date_from.setCalendarPopup(True)
        self.list_date_from.setDate(date(date.today().year, date.today().month, 1))
        self.list_date_from.setStyleSheet("padding: 4px 8px;")
        toolbar.addWidget(QLabel("From:"))
        toolbar.addWidget(self.list_date_from)

        self.list_date_to = QDateEdit()
        self.list_date_to.setCalendarPopup(True)
        self.list_date_to.setDate(date.today())
        self.list_date_to.setStyleSheet("padding: 4px 8px;")
        toolbar.addWidget(QLabel("To:"))
        toolbar.addWidget(self.list_date_to)

        refresh_btn = QPushButton("  ")
        refresh_btn.setFixedWidth(36)
        refresh_btn.clicked.connect(self._search)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        create_btn = QPushButton("+ Create Receipt (Alt+R)")
        create_btn.setStyleSheet("""
            QPushButton { background: #4caf50; color: white; padding: 8px 20px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388e3c; }
        """)
        create_btn.setShortcut("Alt+R")
        create_btn.clicked.connect(self._open_create_dialog)
        toolbar.addWidget(create_btn)

        layout.addLayout(toolbar)
        layout.addSpacing(12)

        self.list_table = QTableWidget()
        self.list_table.setColumnCount(7)
        self.list_table.setHorizontalHeaderLabels(
            ["Receipt No", "Bill Ref", "Company", "Date", "Amount", "Status", ""]
        )
        self.list_table.setAlternatingRowColors(True)
        self.list_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.list_table.verticalHeader().setVisible(False)
        self.list_table.verticalHeader().setDefaultSectionSize(40)
        self.list_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 4px; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 6px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        header = self.list_table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        header.setSectionResizeMode(6, QHeaderView.Interactive)
        header.resizeSection(0, 130)
        header.resizeSection(1, 120)
        header.resizeSection(3, 100)
        header.resizeSection(4, 110)
        header.resizeSection(5, 60)
        header.resizeSection(6, 110)
        layout.addWidget(self.list_table)

        self._search()

    def _search(self):
        query = self.list_search.text()
        date_from = self.list_date_from.date().toString("yyyy-MM-dd")
        date_to = self.list_date_to.date().toString("yyyy-MM-dd")
        receipts = search_receipts(query, date_from, date_to)

        self.list_table.setRowCount(0)
        for rec in receipts:
            row = self.list_table.rowCount()
            self.list_table.insertRow(row)
            self.list_table.setItem(row, 0, QTableWidgetItem(rec["receipt_no"]))
            self.list_table.setItem(row, 1, QTableWidgetItem(rec.get("bill_no", "")))
            self.list_table.setItem(row, 2, QTableWidgetItem(rec["customer_name"]))
            self.list_table.setItem(row, 3, QTableWidgetItem(rec["receipt_date"]))
            self.list_table.setItem(row, 4, QTableWidgetItem(f"  {rec['amount']:,.2f}"))
            self.list_table.setItem(row, 5, QTableWidgetItem(rec["status"].title()))

            action_w = QWidget()
            al = QHBoxLayout(action_w)
            al.setContentsMargins(2, 2, 2, 2)
            al.setSpacing(4)

            rec_id = rec["id"]
            print_btn = QPushButton("Print")
            print_btn.setFixedSize(50, 26)
            print_btn.setStyleSheet("background: #ff9800; color: white; border: none; border-radius: 3px;")
            print_btn.clicked.connect(lambda checked, rid=rec_id: self._print_receipt(rid))
            al.addWidget(print_btn)

            if rec["status"] == "active":
                cancel_btn = QPushButton("Cancel")
                cancel_btn.setFixedSize(55, 26)
                cancel_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
                cancel_btn.clicked.connect(lambda checked, rid=rec_id: self._cancel_receipt(rid))
                al.addWidget(cancel_btn)

            self.list_table.setCellWidget(row, 6, action_w)

    def _print_receipt(self, receipt_id: int):
        try:
            path = generate_receipt_pdf(receipt_id)
            open_pdf(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _cancel_receipt(self, receipt_id: int):
        ok = QMessageBox.question(
            self, "Confirm", "Cancel this receipt?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok == QMessageBox.Yes:
            cancel_receipt(receipt_id)
            self._search()

    def _open_create_dialog(self):
        dialog = CreateReceiptDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._search()

    def refresh_list(self):
        self._search()


class CreateReceiptDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Receipt")
        self.setMinimumWidth(600)
        self.setModal(True)

        self._customer = None
        self._bill_data = None
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Receipt info row
        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("Receipt No:"))
        self.rc_no_label = QLabel("...")
        self.rc_no_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.rc_no_label.setStyleSheet("color: #1a237e;")
        info_row.addWidget(self.rc_no_label)
        info_row.addStretch()
        info_row.addWidget(QLabel("Date:"))
        self.rc_date = QDateEdit()
        self.rc_date.setCalendarPopup(True)
        self.rc_date.setDate(date.today())
        self.rc_date.setStyleSheet("padding: 4px 8px;")
        info_row.addWidget(self.rc_date)
        layout.addLayout(info_row)

        # Customer selection
        cust_group = QGroupBox("Customer")
        cust_group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 6px;
                        margin-top: 10px; padding-top: 16px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)
        cust_layout = QVBoxLayout(cust_group)
        cust_search_row = QHBoxLayout()
        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("Search customer by name or mobile...")
        self.cust_search.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        self.cust_search.textChanged.connect(self._search_customers_ui)
        cust_search_row.addWidget(self.cust_search, 1)
        self.cust_combo = QComboBox()
        self.cust_combo.setMinimumWidth(300)
        self.cust_combo.setStyleSheet("padding: 4px 8px;")
        self.cust_combo.currentIndexChanged.connect(self._on_customer_selected)
        cust_search_row.addWidget(self.cust_combo)
        cust_layout.addLayout(cust_search_row)
        self.cust_info = QLabel("<i>Select a customer</i>")
        self.cust_info.setStyleSheet("color: #757575; padding: 4px;")
        cust_layout.addWidget(self.cust_info)
        layout.addWidget(cust_group)

        # Payment details
        pay_group = QGroupBox("Payment Details")
        pay_group.setStyleSheet(cust_group.styleSheet())
        pay_layout = QFormLayout(pay_group)
        pay_layout.setSpacing(8)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 99999999)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setPrefix("  ")
        self.amount_spin.setFixedWidth(200)
        self.amount_spin.setStyleSheet("padding: 4px 8px;")
        self.amount_spin.valueChanged.connect(self._on_amount_change)
        pay_layout.addRow("Amount:", self.amount_spin)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Cash", "Bank Transfer", "Cheque", "UPI", "Card", "Other"])
        self.mode_combo.setStyleSheet("padding: 4px 8px;")
        pay_layout.addRow("Mode:", self.mode_combo)

        self.ref_no = QLineEdit()
        self.ref_no.setPlaceholderText("Cheque/Transaction/UPI ref (optional)")
        self.ref_no.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        pay_layout.addRow("Reference:", self.ref_no)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional notes")
        self.notes_input.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        pay_layout.addRow("Notes:", self.notes_input)

        layout.addWidget(pay_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._save_btn = QPushButton("  Save Receipt")
        self._save_btn.setFixedHeight(40)
        self._save_btn.setStyleSheet("""
            QPushButton { background: #3f51b5; color: white; padding: 10px 30px;
                          border: none; border-radius: 4px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #303f9f; }
        """)
        self._save_btn.clicked.connect(self._save)
        self._save_btn.setEnabled(False)
        btn_layout.addWidget(self._save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton { background: #f5f5f5; padding: 8px 20px;
                          border: 1px solid #ccc; border-radius: 4px; }
            QPushButton:hover { background: #e0e0e0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self._generate_rc_no()
        self._load_customers()

    def _generate_rc_no(self):
        self.rc_no = get_next_receipt_no("RC")
        self.rc_no_label.setText(self.rc_no)

    def _load_customers(self):
        customers = get_all_customers()
        self.cust_combo.clear()
        for c in customers:
            self.cust_combo.addItem(f"{c['name']}  |  {c.get('mobile', '')}", c["id"])

    def _search_customers_ui(self):
        query = self.cust_search.text()
        customers = search_customers(query)
        self.cust_combo.blockSignals(True)
        self.cust_combo.clear()
        for c in customers:
            self.cust_combo.addItem(f"{c['name']}  |  {c.get('mobile', '')}", c["id"])
        self.cust_combo.blockSignals(False)
        self._on_customer_selected()

    def _on_customer_selected(self):
        idx = self.cust_combo.currentIndex()
        if idx < 0:
            self._customer = None
            self.cust_info.setText("<i>Select a customer</i>")
            self.cust_info.setStyleSheet("color: #757575; padding: 4px;")
            self._save_btn.setEnabled(False)
            return
        cid = self.cust_combo.itemData(idx)
        c = get_customer(cid)
        if not c:
            return
        self._customer = c
        self.cust_info.setText(
            f"<b>{c['name']}</b>  |  Mobile: {c.get('mobile', '')}"
        )
        self.cust_info.setStyleSheet("color: #1a237e; padding: 4px;")
        if self.amount_spin.value() > 0:
            self._save_btn.setEnabled(True)

    def _on_amount_change(self, val):
        self._save_btn.setEnabled(self._customer is not None and val > 0)

    def _save(self):
        if not self._customer:
            QMessageBox.warning(self, "Error", "Please select a customer.")
            return
        amount = self.amount_spin.value()
        if amount <= 0:
            QMessageBox.warning(self, "Error", "Amount must be greater than zero.")
            return
        words = self._amount_in_words(amount)
        try:
            create_receipt(
                receipt_no=self.rc_no,
                customer_id=self._customer["id"],
                customer_name=self._customer["name"],
                customer_mobile=self._customer.get("mobile", ""),
                receipt_date=self.rc_date.date().toString("yyyy-MM-dd"),
                amount=amount,
                amount_in_words=words,
                mode=self.mode_combo.currentText(),
                reference_no=self.ref_no.text(),
                notes=self.notes_input.text(),
            )
            QMessageBox.information(
                self, "Saved",
                f"Receipt {self.rc_no} saved successfully!",
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save receipt:\n{str(e)}")

    def _amount_in_words(self, amount: float) -> str:
        if amount == 0:
            return "Zero Rupees Only"
        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
        teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
                 "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

        def _under_1000(n):
            res = ""
            if n >= 100:
                res += units[n // 100] + " Hundred "
                n %= 100
            if 10 < n < 20:
                res += teens[n - 10] + " "
            else:
                if n >= 20:
                    res += tens[n // 10] + " "
                    n %= 10
                if n > 0:
                    res += units[n] + " "
            return res.strip()

        amt = int(round(amount))
        words = ""
        if amt >= 100000:
            lakhs = amt // 100000
            words += _under_1000(lakhs) + " Lakh "
            amt %= 100000
        if amt >= 1000:
            thousands = amt // 1000
            words += _under_1000(thousands) + " Thousand "
            amt %= 1000
        if amt > 0:
            words += _under_1000(amt)
        return words.strip() + " Rupees Only"
