from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDoubleSpinBox, QDateEdit,
    QFormLayout, QGroupBox, QGridLayout, QDialog,
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QFont

from customer import search_customers, get_all_customers, add_customer
from database import get_next_bill_no
from ui.customer_window import CustomerDialog
from billing import (
    create_sale_bill, search_sale_bills, get_sale_bill,
    update_sale_bill, cancel_sale_bill, delete_sale_bill,
)
from printer import generate_bill_pdf, generate_consolidated_bill_pdf, open_pdf


def _amount_in_words(amount: float) -> str:
    """Convert a numeric amount to words (e.g. 1250 → One Thousand Two Hundred Fifty Rupees Only)."""
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
        words += _under_1000(amt // 100000) + " Lakh "
        amt %= 100000
    if amt >= 1000:
        words += _under_1000(amt // 1000) + " Thousand "
        amt %= 1000
    if amt > 0:
        words += _under_1000(amt)
    return words.strip() + " Rupees Only"


class BillingWindow(QWidget):
    def __init__(self, list_mode: bool = False):
        super().__init__()
        self.list_mode = list_mode
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        if list_mode:
            self._build_list_ui(layout)
        else:
            self._build_billing_ui(layout)

    def _build_billing_ui(self, layout: QVBoxLayout):
        header = QLabel("New Sale Bill")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        meta_grid = QGridLayout()
        meta_grid.setSpacing(10)

        meta_grid.addWidget(QLabel("Bill No:"), 0, 0)
        self.bill_no_label = QLabel("...")
        self.bill_no_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.bill_no_label.setStyleSheet("color: #1a237e;")
        meta_grid.addWidget(self.bill_no_label, 0, 1)

        meta_grid.addWidget(QLabel("Date:"), 0, 2)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        self.date_edit.setFixedWidth(160)
        self.date_edit.setStyleSheet("padding: 4px 8px;")
        meta_grid.addWidget(self.date_edit, 0, 3)

        layout.addLayout(meta_grid)
        layout.addSpacing(8)

        cust_group = QGroupBox("Company (Buyer)")
        cust_group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 6px;
                        margin-top: 10px; padding-top: 16px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)
        cust_layout = QGridLayout(cust_group)
        cust_layout.setSpacing(8)

        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("Search company by name or mobile...")
        self.cust_search.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        self.cust_search.textChanged.connect(self._search_customers_ui)
        self.cust_search.installEventFilter(self)
        cust_layout.addWidget(self.cust_search, 0, 0)

        add_cust_btn = QPushButton("Add Company (Ctrl+A)")
        add_cust_btn.setToolTip("Add new company")
        add_cust_btn.setShortcut("Ctrl+A")
        add_cust_btn.setStyleSheet("""
            QPushButton { background: #4caf50; color: #1a237e; font-weight: bold;
                          border: none; border-radius: 4px; font-size: 13px; padding: 6px 14px; }
            QPushButton:hover { background: #388e3c; color: white; }
        """)
        add_cust_btn.clicked.connect(self._quick_add_customer)
        cust_layout.addWidget(add_cust_btn, 0, 1)

        self.cust_combo = QComboBox()
        self.cust_combo.setMinimumWidth(300)
        self.cust_combo.setStyleSheet("""
            QComboBox { padding: 4px 8px; color: #333; }
            QComboBox QAbstractItemView {
                color: #333; background: white; selection-background-color: #3f51b5;
                selection-color: white; outline: none;
            }
        """)
        cust_layout.addWidget(self.cust_combo, 1, 0, 1, 2)

        self.cust_mobile_label = QLabel("")
        self.cust_mobile_label.setStyleSheet("color: #555;")
        cust_layout.addWidget(self.cust_mobile_label, 2, 0, 1, 2)

        layout.addWidget(cust_group)
        layout.addSpacing(8)

        detail_group = QGroupBox("Details")
        detail_group.setStyleSheet(cust_group.styleSheet())
        detail_layout = QFormLayout(detail_group)
        detail_layout.setSpacing(8)

        self.vehicle_no = QLineEdit()
        self.vehicle_no.setPlaceholderText("Enter vehicle number")
        self.vehicle_no.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        self.vehicle_no.installEventFilter(self)
        detail_layout.addRow("Vehicle No:", self.vehicle_no)

        weight_layout = QHBoxLayout()
        weight_layout.setSpacing(10)

        wl = QVBoxLayout()
        wl.addWidget(QLabel("Gross Weight (Kg):"))
        self.gross_weight = QDoubleSpinBox()
        self.gross_weight.setRange(0, 999999)
        self.gross_weight.setDecimals(2)
        self.gross_weight.setFixedWidth(150)
        self.gross_weight.setStyleSheet("padding: 4px 8px;")
        self.gross_weight.valueChanged.connect(self._recalc)
        wl.addWidget(self.gross_weight)
        weight_layout.addLayout(wl)

        wl2 = QVBoxLayout()
        wl2.addWidget(QLabel("Tare Weight (Kg):"))
        self.tare_weight = QDoubleSpinBox()
        self.tare_weight.setRange(0, 999999)
        self.tare_weight.setDecimals(2)
        self.tare_weight.setFixedWidth(150)
        self.tare_weight.setStyleSheet("padding: 4px 8px;")
        self.tare_weight.valueChanged.connect(self._recalc)
        wl2.addWidget(self.tare_weight)
        weight_layout.addLayout(wl2)

        wl3 = QVBoxLayout()
        wl3.addWidget(QLabel("Net Weight (Kg):"))
        self.net_weight_label = QLabel("0.00")
        self.net_weight_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.net_weight_label.setStyleSheet("color: #1a237e;")
        wl3.addWidget(self.net_weight_label)
        weight_layout.addLayout(wl3)

        detail_layout.addRow("", weight_layout)

        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0, 999999)
        self.rate_spin.setDecimals(2)
        self.rate_spin.setPrefix("  ")
        self.rate_spin.setFixedWidth(150)
        self.rate_spin.setStyleSheet("padding: 4px 8px;")
        self.rate_spin.valueChanged.connect(self._recalc)
        self.rate_spin.installEventFilter(self)
        detail_layout.addRow("Rate per Kg:", self.rate_spin)

        self.amount_label = QLabel(" 0.00")
        self.amount_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.amount_label.setStyleSheet("color: #1a237e;")
        detail_layout.addRow("Total Amount:", self.amount_label)

        layout.addWidget(detail_group)
        layout.addSpacing(12)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("  Save Entry")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet("""
            QPushButton { background: #3f51b5; color: white; padding: 10px 30px;
                          border: none; border-radius: 4px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #303f9f; }
        """)
        save_btn.clicked.connect(self._save_bill)
        save_btn.setDefault(True)
        btn_layout.addWidget(save_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(36)
        clear_btn.setStyleSheet("""
            QPushButton { background: #f5f5f5; padding: 6px 20px;
                          border: 1px solid #ccc; border-radius: 4px; }
            QPushButton:hover { background: #e0e0e0; }
        """)
        clear_btn.clicked.connect(self._clear_form)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addStretch()

        self._load_customers()
        self._generate_bill_no()
        self._on_customer_selected()

        # Tab order for fast keyboard entry
        self.setTabOrder(self.cust_search, self.vehicle_no)
        self.setTabOrder(self.vehicle_no, self.gross_weight)
        self.setTabOrder(self.gross_weight, self.tare_weight)
        self.setTabOrder(self.tare_weight, self.rate_spin)
        self.setTabOrder(self.rate_spin, save_btn)

    def _search_customers_ui(self):
        query = self.cust_search.text()
        customers = search_customers(query)
        self.cust_combo.blockSignals(True)
        self.cust_combo.clear()
        for c in customers:
            label = f"{c['name']}  |  {c.get('mobile', '')}"
            self.cust_combo.addItem(label, c["id"])
        self.cust_combo.blockSignals(False)
        self._on_customer_selected()

    def _load_customers(self):
        customers = get_all_customers()
        self.cust_combo.clear()
        for c in customers:
            label = f"{c['name']}  |  {c.get('mobile', '')}"
            self.cust_combo.addItem(label, c["id"])

    def _on_customer_selected(self):
        idx = self.cust_combo.currentIndex()
        if idx >= 0:
            cid = self.cust_combo.itemData(idx)
            from customer import get_customer
            c = get_customer(cid) if cid else None
            if c:
                self.cust_mobile_label.setText(f"  {c.get('mobile', '')}")
                return
        self.cust_mobile_label.setText("")

    def _quick_add_customer(self):
        dialog = CustomerDialog(0, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            new_id = add_customer(**data)
            self._load_customers()
            for i in range(self.cust_combo.count()):
                if self.cust_combo.itemData(i) == new_id:
                    self.cust_combo.setCurrentIndex(i)
                    break
            self.cust_search.clear()
            self._on_customer_selected()
            self.vehicle_no.setFocus()

    def eventFilter(self, obj, event):
        if obj == self.cust_search and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Down:
                idx = self.cust_combo.currentIndex()
                if idx < self.cust_combo.count() - 1:
                    self.cust_combo.setCurrentIndex(idx + 1)
                self.cust_combo.showPopup()
                return True
            elif event.key() == Qt.Key_Up:
                idx = self.cust_combo.currentIndex()
                if idx > 0:
                    self.cust_combo.setCurrentIndex(idx - 1)
                self.cust_combo.showPopup()
                return True
            elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
                self._quick_add_customer()
                return True
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if obj in (self.cust_search, self.vehicle_no, self.gross_weight,
                       self.tare_weight, self.rate_spin):
                self._save_bill()
                return True
        return super().eventFilter(obj, event)

    def _generate_bill_no(self):
        self.bill_no = get_next_bill_no("BL")
        self.bill_no_label.setText(self.bill_no)

    def _recalc(self):
        gross = self.gross_weight.value()
        tare = self.tare_weight.value()
        net = max(0, gross - tare)
        self.net_weight_label.setText(f"{net:.2f}")

        rate = self.rate_spin.value()
        amount = net * rate
        self.amount_label.setText(f" {amount:,.2f}")

    def _amount_in_words(self, amount: float) -> str:
        return _amount_in_words(amount)

    def _save_bill(self):
        idx = self.cust_combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Error", "Please select a company.")
            return

        cid = self.cust_combo.itemData(idx)
        from customer import get_customer
        c = get_customer(cid) if cid else None
        if not c:
            QMessageBox.warning(self, "Error", "Invalid company.")
            return

        gross = self.gross_weight.value()
        if gross <= 0:
            QMessageBox.warning(self, "Error", "Gross weight must be greater than zero.")
            return

        tare = self.tare_weight.value()
        net = max(0, gross - tare)
        rate = self.rate_spin.value()
        amount = net * rate

        create_sale_bill(
            bill_no=self.bill_no,
            customer_id=c["id"],
            customer_name=c["name"],
            customer_mobile=c.get("mobile", ""),
            vehicle_no=self.vehicle_no.text().strip(),
            gross_weight=gross,
            tare_weight=tare,
            net_weight=net,
            weight_unit="Kg",
            rate=rate,
            amount=amount,
            bill_date=self.date_edit.date().toString("yyyy-MM-dd"),
            amount_in_words=self._amount_in_words(amount),
        )

        QMessageBox.information(
            self, "Saved",
            f"Entry {self.bill_no} saved."
        )
        self._clear_form()

    def _clear_form(self):
        self.gross_weight.setValue(0)
        self.tare_weight.setValue(0)
        self.net_weight_label.setText("0.00")
        self.rate_spin.setValue(0)
        self.amount_label.setText(" 0.00")
        self.vehicle_no.clear()
        self.cust_search.clear()
        self._generate_bill_no()
        self.cust_search.setFocus()

    def refresh_for_new(self):
        self._clear_form()
        self._load_customers()
        self.cust_search.setFocus()

    def _build_list_ui(self, layout: QVBoxLayout):
        header = QLabel("Bills List")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        search_layout = QHBoxLayout()
        self.list_search = QLineEdit()
        self.list_search.setPlaceholderText("Search by bill no, company name, or mobile...")
        self.list_search.setStyleSheet("padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;")
        self.list_search.textChanged.connect(self._search_reset)
        search_layout.addWidget(self.list_search, 1)

        self.list_date_from = QDateEdit()
        self.list_date_from.setCalendarPopup(True)
        self.list_date_from.setDate(date(date.today().year, date.today().month, 1))
        self.list_date_from.setStyleSheet("padding: 4px 8px;")
        search_layout.addWidget(QLabel("From:"))
        search_layout.addWidget(self.list_date_from)

        self.list_date_to = QDateEdit()
        self.list_date_to.setCalendarPopup(True)
        self.list_date_to.setDate(date.today())
        self.list_date_to.setStyleSheet("padding: 4px 8px;")
        search_layout.addWidget(QLabel("To:"))
        search_layout.addWidget(self.list_date_to)

        refresh_btn = QPushButton("  ")
        refresh_btn.setFixedWidth(36)
        refresh_btn.clicked.connect(self._search_refresh)
        search_layout.addWidget(refresh_btn)

        layout.addLayout(search_layout)
        layout.addSpacing(8)

        invoice_layout = QHBoxLayout()
        invoice_layout.addWidget(QLabel("Customer:"))
        self.invoice_cust_combo = QComboBox()
        self.invoice_cust_combo.setMinimumWidth(250)
        self.invoice_cust_combo.setStyleSheet("padding: 4px 8px;")
        invoice_layout.addWidget(self.invoice_cust_combo)

        gen_btn = QPushButton("  Generate Invoice")
        gen_btn.setStyleSheet("""
            QPushButton { background: #ff9800; color: white; padding: 6px 16px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #f57c00; }
        """)
        gen_btn.clicked.connect(self._generate_invoice)
        invoice_layout.addWidget(gen_btn)

        invoice_layout.addStretch()
        layout.addLayout(invoice_layout)
        layout.addSpacing(12)

        self.list_table = QTableWidget()
        self.list_table.setColumnCount(7)
        self.list_table.setHorizontalHeaderLabels(
            ["Bill #", "Company", "Date", "Amount", "Weight", "Status", ""]
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
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        header.setSectionResizeMode(6, QHeaderView.Interactive)
        header.resizeSection(0, 130)
        header.resizeSection(2, 90)
        header.resizeSection(3, 105)
        header.resizeSection(4, 80)
        header.resizeSection(5, 60)
        header.resizeSection(6, 230)
        layout.addWidget(self.list_table)

        page_layout = QHBoxLayout()
        page_layout.addStretch()
        self.prev_btn = QPushButton("   Previous")
        self.prev_btn.setFixedWidth(100)
        self.prev_btn.setStyleSheet("padding: 4px 10px; border: 1px solid #ccc; border-radius: 3px; background: white;")
        self.prev_btn.clicked.connect(self._prev_page)
        page_layout.addWidget(self.prev_btn)

        self.page_label = QLabel("Page 1")
        self.page_label.setStyleSheet("padding: 4px 12px; font-weight: bold;")
        page_layout.addWidget(self.page_label)

        self.next_btn = QPushButton("Next  ")
        self.next_btn.setFixedWidth(100)
        self.next_btn.setStyleSheet("padding: 4px 10px; border: 1px solid #ccc; border-radius: 3px; background: white;")
        self.next_btn.clicked.connect(self._next_page)
        page_layout.addWidget(self.next_btn)

        page_layout.addStretch()
        layout.addLayout(page_layout)

        self._current_page = 1
        self._total_pages = 1
        self._load_invoice_customers()
        self._search_bills()

    def _load_invoice_customers(self):
        customers = get_all_customers()
        self.invoice_cust_combo.clear()
        for c in customers:
            label = f"{c['name']}  |  {c.get('mobile', '')}"
            self.invoice_cust_combo.addItem(label, c["id"])

    def _generate_invoice(self):
        idx = self.invoice_cust_combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Error", "Please select a customer.")
            return
        cid = self.invoice_cust_combo.itemData(idx)
        cname = self.invoice_cust_combo.currentText().split("  |")[0]
        date_from = self.list_date_from.date().toString("yyyy-MM-dd")
        date_to = self.list_date_to.date().toString("yyyy-MM-dd")

        from customer import get_customer
        c = get_customer(cid)
        if not c:
            QMessageBox.warning(self, "Error", "Invalid customer.")
            return

        try:
            path = generate_consolidated_bill_pdf(
                customer_id=cid,
                customer_name=c["name"],
                date_from=date_from,
                date_to=date_to,
            )
            open_pdf(path)
            QMessageBox.information(self, "Invoice Generated",
                                    f"Invoice saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _search_reset(self):
        self._current_page = 1
        self._search_bills()

    def _search_refresh(self):
        self._current_page = 1
        self._search_bills()

    def _search_bills(self):
        query = self.list_search.text()
        date_from = self.list_date_from.date().toString("yyyy-MM-dd")
        date_to = self.list_date_to.date().toString("yyyy-MM-dd")
        bills, total = search_sale_bills(query, date_from, date_to, page=self._current_page)

        self._total_pages = max(1, (total + 19) // 20)
        self.page_label.setText(f"Page {self._current_page} / {self._total_pages}")
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)

        self.list_table.setRowCount(0)
        for bill in bills:
            row = self.list_table.rowCount()
            self.list_table.insertRow(row)
            self.list_table.setItem(row, 0, QTableWidgetItem(bill["bill_no"]))
            self.list_table.setItem(row, 1, QTableWidgetItem(bill["customer_name"]))
            self.list_table.setItem(row, 2, QTableWidgetItem(bill["bill_date"]))
            self.list_table.setItem(row, 3, QTableWidgetItem(f"  {bill['amount']:,.2f}"))
            self.list_table.setItem(row, 4, QTableWidgetItem(f"{bill['net_weight']:.1f} Kg"))
            self.list_table.setItem(row, 5, QTableWidgetItem(bill["status"].title()))

            action_w = QWidget()
            al = QHBoxLayout(action_w)
            al.setContentsMargins(2, 2, 2, 2)
            al.setSpacing(4)

            bill_id = bill["id"]
            view_btn = QPushButton("View")
            view_btn.setFixedSize(45, 26)
            view_btn.setStyleSheet("background: #3f51b5; color: white; border: none; border-radius: 3px;")
            view_btn.clicked.connect(lambda checked, bid=bill_id: self._view_bill(bid))
            al.addWidget(view_btn)

            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(40, 26)
            edit_btn.setStyleSheet("background: #2196f3; color: white; border: none; border-radius: 3px;")
            edit_btn.clicked.connect(lambda checked, bid=bill_id: self._edit_bill(bid))
            al.addWidget(edit_btn)

            if bill["status"] == "active":
                cancel_btn = QPushButton("Cancel")
                cancel_btn.setFixedSize(50, 26)
                cancel_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
                cancel_btn.clicked.connect(lambda checked, bid=bill_id: self._cancel_bill(bid))
                al.addWidget(cancel_btn)

            del_btn = QPushButton("Del")
            del_btn.setFixedSize(36, 26)
            del_btn.setStyleSheet("background: #d32f2f; color: white; border: none; border-radius: 3px;")
            del_btn.clicked.connect(lambda checked, bid=bill_id: self._delete_bill(bid))
            al.addWidget(del_btn)

            self.list_table.setCellWidget(row, 6, action_w)

    def _view_bill(self, bill_id: int):
        try:
            path = generate_bill_pdf(bill_id)
            open_pdf(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _edit_bill(self, bill_id: int):
        bill = get_sale_bill(bill_id)
        if not bill:
            QMessageBox.warning(self, "Error", "Bill not found.")
            return
        dialog = BillEditDialog(bill, self)
        if dialog.exec() == QDialog.Accepted:
            self._current_page = 1
            self._search_bills()

    def _cancel_bill(self, bill_id: int):
        ok = QMessageBox.question(
            self, "Confirm", "Cancel this bill?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok == QMessageBox.Yes:
            cancel_sale_bill(bill_id)
            self._search_bills()

    def _delete_bill(self, bill_id: int):
        ok = QMessageBox.question(
            self, "Confirm",
            "Permanently delete this bill?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok == QMessageBox.Yes:
            delete_sale_bill(bill_id)
            self._current_page = 1
            self._search_bills()

    def _prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._search_bills()

    def _next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._search_bills()

    def refresh_list(self):
        self._current_page = 1
        self._load_invoice_customers()
        self._search_bills()


class BillEditDialog(QDialog):
    """Dialog for editing an existing sale bill."""

    def __init__(self, bill: dict, parent=None):
        super().__init__(parent)
        self.bill_id = bill["id"]
        self.setWindowTitle(f"Edit Bill — {bill['bill_no']}")
        self.setMinimumWidth(500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel(f"Editing: {bill['bill_no']}")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)

        # --- Date ---
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(
            date.fromisoformat(bill["bill_date"]) if bill.get("bill_date") else date.today()
        )
        self.date_edit.setStyleSheet("padding: 4px 8px;")
        form.addRow("Date:", self.date_edit)

        # --- Customer ---
        from customer import get_all_customers
        self.cust_combo = QComboBox()
        self.cust_combo.setMinimumWidth(280)
        self.cust_combo.setStyleSheet("padding: 4px 8px;")
        customers = get_all_customers()
        selected_idx = 0
        for i, c in enumerate(customers):
            label = f"{c['name']}  |  {c.get('mobile', '')}"
            self.cust_combo.addItem(label, c["id"])
            if c["id"] == bill["customer_id"]:
                selected_idx = i
        self.cust_combo.setCurrentIndex(selected_idx)
        self._selected_customer_id = bill["customer_id"]
        self.cust_combo.currentIndexChanged.connect(self._on_cust_changed)
        form.addRow("Company:", self.cust_combo)

        # --- Vehicle No ---
        self.vehicle_no = QLineEdit()
        self.vehicle_no.setText(bill.get("vehicle_no", ""))
        self.vehicle_no.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Vehicle No:", self.vehicle_no)

        # --- Weights ---
        weight_row = QHBoxLayout()
        self.gross_weight = QDoubleSpinBox()
        self.gross_weight.setRange(0, 999999)
        self.gross_weight.setDecimals(2)
        self.gross_weight.setValue(bill.get("gross_weight", 0))
        self.gross_weight.setStyleSheet("padding: 4px 8px;")
        self.gross_weight.valueChanged.connect(self._recalc)
        weight_row.addWidget(QLabel("Gross:"))
        weight_row.addWidget(self.gross_weight)
        weight_row.addSpacing(10)

        self.tare_weight = QDoubleSpinBox()
        self.tare_weight.setRange(0, 999999)
        self.tare_weight.setDecimals(2)
        self.tare_weight.setValue(bill.get("tare_weight", 0))
        self.tare_weight.setStyleSheet("padding: 4px 8px;")
        self.tare_weight.valueChanged.connect(self._recalc)
        weight_row.addWidget(QLabel("Tare:"))
        weight_row.addWidget(self.tare_weight)
        weight_row.addSpacing(10)

        self.net_label = QLabel(f"{bill.get('net_weight', 0):.2f}")
        self.net_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.net_label.setStyleSheet("color: #1a237e;")
        weight_row.addWidget(QLabel("Net:"))
        weight_row.addWidget(self.net_label)
        form.addRow("Weights (Kg):", weight_row)

        # --- Rate ---
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0, 999999)
        self.rate_spin.setDecimals(2)
        self.rate_spin.setValue(bill.get("rate", 0))
        self.rate_spin.setStyleSheet("padding: 4px 8px;")
        self.rate_spin.valueChanged.connect(self._recalc)
        form.addRow("Rate per Kg:", self.rate_spin)

        # --- Amount (read-only display) ---
        self.amount_label = QLabel(f"  {bill.get('amount', 0):,.2f}")
        self.amount_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.amount_label.setStyleSheet("color: #1a237e;")
        form.addRow("Total Amount:", self.amount_label)

        layout.addLayout(form)
        layout.addSpacing(12)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("  Save Changes")
        save_btn.setFixedHeight(38)
        save_btn.setStyleSheet("""
            QPushButton { background: #3f51b5; color: white; padding: 8px 24px;
                          border: none; border-radius: 4px; font-size: 13px; font-weight: bold; }
            QPushButton:hover { background: #303f9f; }
        """)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet("""
            QPushButton { background: #f5f5f5; padding: 8px 20px;
                          border: 1px solid #ccc; border-radius: 4px; }
            QPushButton:hover { background: #e0e0e0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_cust_changed(self):
        idx = self.cust_combo.currentIndex()
        if idx >= 0:
            self._selected_customer_id = self.cust_combo.itemData(idx)

    def _recalc(self):
        gross = self.gross_weight.value()
        tare = self.tare_weight.value()
        net = max(0, gross - tare)
        self.net_label.setText(f"{net:.2f}")
        rate = self.rate_spin.value()
        amount = net * rate
        self.amount_label.setText(f"  {amount:,.2f}")

    def _save(self):
        idx = self.cust_combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Error", "Please select a company.")
            return

        cid = self.cust_combo.itemData(idx)
        from customer import get_customer
        c = get_customer(cid) if cid else None
        if not c:
            QMessageBox.warning(self, "Error", "Invalid company.")
            return

        gross = self.gross_weight.value()
        if gross <= 0:
            QMessageBox.warning(self, "Error", "Gross weight must be greater than zero.")
            return

        tare = self.tare_weight.value()
        net = max(0, gross - tare)
        rate = self.rate_spin.value()
        amount = net * rate

        update_sale_bill(
            bill_id=self.bill_id,
            customer_id=c["id"],
            customer_name=c["name"],
            customer_mobile=c.get("mobile", ""),
            vehicle_no=self.vehicle_no.text().strip(),
            gross_weight=gross,
            tare_weight=tare,
            net_weight=net,
            weight_unit="Kg",
            rate=rate,
            amount=amount,
            bill_date=self.date_edit.date().toString("yyyy-MM-dd"),
            amount_in_words=_amount_in_words(amount),
        )

        QMessageBox.information(self, "Saved", "Bill updated successfully.")
        self.accept()
