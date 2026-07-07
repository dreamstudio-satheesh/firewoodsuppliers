import os
import tempfile
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
    QTabWidget, QMessageBox, QComboBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from reports import sales_register, sales_detail
from customer import get_all_customers
from exporter import export_csv, export_xlsx, export_pdf_table
from printer import open_pdf, generate_statement_pdf


class ReportTab(QWidget):
    def __init__(self, column_headers: list[str], column_keys: list[str],
                 fetch_fn, title: str, parent=None):
        super().__init__(parent)
        self._column_headers = column_headers
        self._column_keys = column_keys
        self._fetch_fn = fetch_fn
        self._title = title
        self._data: list[dict] = []
        self._extra_widgets = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(date(date.today().year, date.today().month, 1))
        self.date_from.setStyleSheet("padding: 4px 8px;")
        toolbar.addWidget(self.date_from)

        toolbar.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(date.today())
        self.date_to.setStyleSheet("padding: 4px 8px;")
        toolbar.addWidget(self.date_to)

        for w in self._extra_widgets:
            toolbar.addWidget(w)

        refresh_btn = QPushButton("  Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton { background: #3f51b5; color: white; padding: 6px 16px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #303f9f; }
        """)
        refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        xlsx_btn = QPushButton("  Excel")
        xlsx_btn.setStyleSheet("background: #4caf50; color: white; padding: 6px 14px; border: none; border-radius: 4px;")
        xlsx_btn.clicked.connect(lambda: self._export("xlsx"))
        toolbar.addWidget(xlsx_btn)

        pdf_btn = QPushButton("  PDF")
        pdf_btn.setStyleSheet("background: #ff9800; color: white; padding: 6px 14px; border: none; border-radius: 4px;")
        pdf_btn.clicked.connect(lambda: self._export("pdf"))
        toolbar.addWidget(pdf_btn)

        csv_btn = QPushButton("  CSV")
        csv_btn.setStyleSheet("background: #757575; color: white; padding: 6px 14px; border: none; border-radius: 4px;")
        csv_btn.clicked.connect(lambda: self._export("csv"))
        toolbar.addWidget(csv_btn)

        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self._column_headers))
        self.table.setHorizontalHeaderLabels(self._column_headers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 4px; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 6px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        header = self.table.horizontalHeader()
        for i in range(len(self._column_headers)):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        if self._column_headers:
            header.setSectionResizeMode(min(1, len(self._column_headers) - 1), QHeaderView.Stretch)
        layout.addWidget(self.table)

        self._refresh()

    def _refresh(self):
        from_date = self.date_from.date().toString("yyyy-MM-dd")
        to_date = self.date_to.date().toString("yyyy-MM-dd")

        try:
            if hasattr(self, '_fetch_extra'):
                self._data = self._fetch_fn(from_date, to_date, *self._fetch_extra)
            else:
                self._data = self._fetch_fn(from_date, to_date)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            self._data = []

        self.table.setRowCount(0)
        for row_data in self._data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col_idx, key in enumerate(self._column_keys):
                val = row_data.get(key, "")
                text = str(val) if not isinstance(val, float) else f"{val:,.2f}"
                item = QTableWidgetItem(text)
                if isinstance(val, float):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col_idx, item)

    def _export(self, fmt: str):
        if not self._data:
            QMessageBox.information(self, "Export", "No data to export.")
            return

        safe_title = self._title.replace(" ", "_")
        base = os.path.join(tempfile.gettempdir(), safe_title)
        path = f"{base}.{fmt}"

        try:
            if fmt == "csv":
                path = export_csv(self._data, self._column_headers, self._column_keys, path)
            elif fmt == "xlsx":
                path = export_xlsx(self._data, self._column_headers, self._column_keys,
                                   self._title[:31], path)
            elif fmt == "pdf":
                path = export_pdf_table(self._data, self._column_headers, self._column_keys,
                                        self._title, path)
            QMessageBox.information(
                self, "Exported",
                f"{fmt.upper()} saved to:\n{path}"
            )
            if fmt == "pdf":
                open_pdf(path)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))


class SalesRegisterTab(ReportTab):
    def __init__(self, parent=None):
        cols = ["Date", "Bill No", "Customer", "Vehicle", "Gross", "Tare", "Net Wt", "Amount"]
        keys = ["bill_date", "bill_no", "customer_name", "vehicle_no",
                "gross_weight", "tare_weight", "net_weight", "amount"]
        super().__init__(cols, keys, sales_detail, "Sales Register", parent)


class CustomerStatementTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Customer:"))
        self.cust_combo = QComboBox()
        self.cust_combo.setMinimumWidth(250)
        self.cust_combo.setStyleSheet("padding: 4px 8px;")
        row1.addWidget(self.cust_combo)

        row1.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(date(date.today().year, 1, 1))
        self.date_from.setStyleSheet("padding: 4px 8px;")
        row1.addWidget(self.date_from)

        row1.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(date.today())
        self.date_to.setStyleSheet("padding: 4px 8px;")
        row1.addWidget(self.date_to)

        gen_btn = QPushButton("  Generate Statement")
        gen_btn.setStyleSheet("""
            QPushButton { background: #ff9800; color: white; padding: 6px 16px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #f57c00; }
        """)
        gen_btn.clicked.connect(self._generate)
        row1.addWidget(gen_btn)

        print_btn = QPushButton("  Print PDF")
        print_btn.setStyleSheet("""
            QPushButton { background: #3f51b5; color: white; padding: 6px 16px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #303f9f; }
        """)
        print_btn.clicked.connect(self._print_pdf)
        row1.addWidget(print_btn)

        row1.addStretch()
        layout.addLayout(row1)
        layout.addSpacing(8)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Description", "Vehicle", "Net Wt", "Amount", "Received", "Balance"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 4px; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 6px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(0, QHeaderView.Interactive)
        h.setSectionResizeMode(2, QHeaderView.Interactive)
        h.setSectionResizeMode(3, QHeaderView.Interactive)
        h.setSectionResizeMode(4, QHeaderView.Interactive)
        h.setSectionResizeMode(5, QHeaderView.Interactive)
        h.setSectionResizeMode(6, QHeaderView.Interactive)
        h.resizeSection(0, 100)
        h.resizeSection(2, 100)
        h.resizeSection(3, 80)
        h.resizeSection(4, 100)
        h.resizeSection(5, 100)
        h.resizeSection(6, 100)
        layout.addWidget(self.table)

        self._stmt_data = None
        self._load_customers()

    def _load_customers(self):
        customers = get_all_customers()
        self.cust_combo.clear()
        for c in customers:
            self.cust_combo.addItem(f"{c['name']}  |  {c.get('mobile', '')}", c["id"])

    def _generate(self):
        idx = self.cust_combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Error", "Please select a customer.")
            return
        cid = self.cust_combo.itemData(idx)
        cname = self.cust_combo.currentText().split("  |")[0]
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")

        from reports import get_customer_statement
        self._stmt_data = get_customer_statement(cid, cname, date_from, date_to)

        self.table.setRowCount(0)

        # Opening balance row
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        item = QTableWidgetItem("Opening Balance")
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.table.setItem(row, 1, item)
        self.table.setItem(row, 2, QTableWidgetItem(""))
        self.table.setItem(row, 3, QTableWidgetItem(""))
        self.table.setItem(row, 4, QTableWidgetItem(""))
        self.table.setItem(row, 5, QTableWidgetItem(""))
        item = QTableWidgetItem(f"{self._stmt_data['opening_balance']:,.2f}")
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 6, item)

        for t in self._stmt_data["transactions"]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(t["tx_date"]))
            if t["type"] == "Bill":
                desc = f"Sale - {t['ref_no']}"
                self.table.setItem(row, 1, QTableWidgetItem(desc))
                self.table.setItem(row, 2, QTableWidgetItem(t.get("vehicle_no", "")))
                nw = QTableWidgetItem(f"{t.get('net_weight', 0):,.2f}")
                nw.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 3, nw)
                amt = QTableWidgetItem(f"{t['debit']:,.2f}")
                amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 4, amt)
                self.table.setItem(row, 5, QTableWidgetItem(""))
            else:
                desc = f"Payment - {t['ref_no']}"
                self.table.setItem(row, 1, QTableWidgetItem(desc))
                self.table.setItem(row, 2, QTableWidgetItem(""))
                self.table.setItem(row, 3, QTableWidgetItem(""))
                self.table.setItem(row, 4, QTableWidgetItem(""))
                rc = QTableWidgetItem(f"{t['credit']:,.2f}")
                rc.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 5, rc)
            b = QTableWidgetItem(f"{t['balance']:,.2f}")
            b.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 6, b)

        # Closing balance
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col in range(7):
            self.table.setItem(row, col, QTableWidgetItem(""))

        row = self.table.rowCount()
        self.table.insertRow(row)
        item = QTableWidgetItem("Closing Balance")
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.table.setItem(row, 1, item)
        for col in range(2, 6):
            self.table.setItem(row, col, QTableWidgetItem(""))
        item = QTableWidgetItem(f"{self._stmt_data['closing_balance']:,.2f}")
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 6, item)

    def _print_pdf(self):
        if not self._stmt_data:
            QMessageBox.warning(self, "Error", "Generate the statement first.")
            return
        try:
            path = generate_statement_pdf(
                customer_id=self._stmt_data["customer_id"],
                customer_name=self._stmt_data["customer_name"],
                date_from=self._stmt_data["date_from"],
                date_to=self._stmt_data["date_to"],
            )
            open_pdf(path)
            QMessageBox.information(self, "Printed", f"Statement saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh(self):
        self._load_customers()
        self._stmt_data = None
        self.table.setRowCount(0)


class ReportsWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Reports")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; background: white; border-radius: 4px; }
            QTabBar::tab { padding: 8px 20px; font-weight: bold; }
            QTabBar::tab:selected { background: #3f51b5; color: white; }
        """)

        self.statement_tab = CustomerStatementTab()
        self.sales_tab = SalesRegisterTab()

        self.tabs.addTab(self.statement_tab, "  Customer Statement")
        self.tabs.addTab(self.sales_tab, "  Sales Register")

        layout.addWidget(self.tabs)

    def refresh(self):
        idx = self.tabs.currentIndex()
        tab = self.tabs.widget(idx)
        if tab and hasattr(tab, "_refresh"):
            tab._refresh()
