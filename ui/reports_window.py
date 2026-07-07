import os
import tempfile
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
    QTabWidget, QMessageBox, QRadioButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from reports import sales_register
from exporter import export_csv, export_xlsx, export_pdf_table
from printer import open_pdf


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
        self._period = "day"

        cols = ["Date", "Bills", "Total Amount ()"]
        keys = ["period", "bill_count", "total"]

        self.day_radio = QRadioButton("Day-wise")
        self.day_radio.setChecked(True)
        self.month_radio = QRadioButton("Month-wise")

        super().__init__(cols, keys, sales_register, "Sales Register", parent)

        self._extra_widgets = [QLabel("Group:"), self.day_radio, self.month_radio]

        self.day_radio.clicked.connect(self._on_period_change)
        self.month_radio.clicked.connect(self._on_period_change)

    def _on_period_change(self):
        self._period = "month" if self.month_radio.isChecked() else "day"
        self._refresh()

    def _refresh(self):
        from_date = self.date_from.date().toString("yyyy-MM-dd")
        to_date = self.date_to.date().toString("yyyy-MM-dd")
        try:
            self._data = sales_register(from_date, to_date, self._period)
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
                if isinstance(val, (int, float)):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col_idx, item)


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

        self.sales_tab = SalesRegisterTab()

        self.tabs.addTab(self.sales_tab, "  Sales Register")

        layout.addWidget(self.tabs)

    def refresh(self):
        idx = self.tabs.currentIndex()
        tab = self.tabs.widget(idx)
        if tab and hasattr(tab, "_refresh"):
            tab._refresh()
