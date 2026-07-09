from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QLabel, QFrame, QSizePolicy, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QGridLayout, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QFont, QIcon, QColor, QPalette, QAction, QShortcut, QKeySequence

from billing import get_dashboard_data
from database import backup_database, close
from ui.customer_window import CustomerWindow

from ui.billing_window import BillingWindow
from ui.reports_window import ReportsWindow
from ui.receipt_window import ReceiptWindow
from ui.blank_invoice_window import BlankInvoiceWindow
from settings import get_company, save_company, get_db_setting, set_db_setting


class SidebarButton(QPushButton):
    def __init__(self, text: str, page_index: int, parent=None):
        super().__init__(text, parent)
        self.page_index = page_index
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 20px;
                border: none;
                border-radius: 0;
                background: transparent;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background: #2a3a5c;
            }
            QPushButton:checked {
                background: #3f51b5;
                color: white;
                font-weight: bold;
            }
        """)


class CardWidget(QFrame):
    def __init__(self, title: str, value: str, color: str = "#3f51b5", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            CardWidget {{
                background: white;
                border-radius: 8px;
                border-left: 4px solid {color};
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 9))
        self.title_label.setStyleSheet("color: #757575;")
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Firewood Billing")
        self.setMinimumSize(1200, 750)
        self.setMinimumSize(1400, 850)
        self.resize(1920, 1000)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background: #1a237e;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        title_label = QLabel("Firewood Billing")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_label.setStyleSheet("color: white; padding: 20px 16px;")
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #3f51b5; max-height: 1px;")
        sidebar_layout.addWidget(sep)

        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setStyleSheet("QScrollArea { background: transparent; }"
                                 "QScrollBar:vertical { width: 4px; background: transparent; }"
                                 "QScrollBar::handle:vertical { background: #3f51b5; border-radius: 2px; }"
                                 "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        self.nav_buttons = []
        nav_items = [
            ("  &Dashboard        Alt+D", 0),
            ("  &Companies        Alt+C", 1),
            ("  &New Bill         Alt+N", 2),
            ("  &Bills List       Alt+L", 3),
            ("  &Reports          Alt+R", 4),
            ("  Receip&ts         Alt+T", 5),
            ("  &Blank Invoice    Alt+B", 6),
            ("  &Settings         Alt+S", 7),
        ]
        for text, idx in nav_items:
            btn = SidebarButton(text, idx)
            btn.clicked.connect(self._on_nav_click)
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_layout.addStretch()
        nav_scroll.setWidget(nav_container)
        sidebar_layout.addWidget(nav_scroll, 1)

        # Keyboard shortcuts for sidebar navigation (Alt+ mnemonics don't work through scrollarea)
        QShortcut(QKeySequence("Alt+L"), self, lambda: self._nav_to(3))
        QShortcut(QKeySequence("Alt+D"), self, lambda: self._nav_to(0))
        QShortcut(QKeySequence("Alt+C"), self, lambda: self._nav_to(1))
        QShortcut(QKeySequence("Alt+N"), self, lambda: self._nav_to(2))
        QShortcut(QKeySequence("Alt+R"), self, lambda: self._nav_to(4))
        QShortcut(QKeySequence("Alt+T"), self, lambda: self._nav_to(5))
        QShortcut(QKeySequence("Alt+B"), self, lambda: self._nav_to(6))
        QShortcut(QKeySequence("Alt+S"), self, lambda: self._nav_to(7))

        backup_btn = QPushButton("  &Backup DB")
        backup_btn.setFixedHeight(44)
        backup_btn.setCursor(Qt.PointingHandCursor)
        backup_btn.setFont(QFont("Segoe UI", 10))
        backup_btn.setStyleSheet("""
            QPushButton {
                text-align: left; padding: 10px 20px;
                border: none; border-radius: 0;
                background: transparent; color: #e0e0e0;
            }
            QPushButton:hover { background: #2a3a5c; }
        """)
        backup_btn.clicked.connect(self._backup_db)
        sidebar_layout.addWidget(backup_btn)

        main_layout.addWidget(sidebar)

        content_frame = QFrame()
        content_frame.setStyleSheet("background: #f5f5f5;")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        self.dashboard_widget = self._build_dashboard()
        self.stack.addWidget(self.dashboard_widget)

        self.customer_window = CustomerWindow()
        self.stack.addWidget(self.customer_window)

        self.billing_window = BillingWindow()
        self.stack.addWidget(self.billing_window)

        self.bills_list_window = BillingWindow(list_mode=True)
        self.stack.addWidget(self.bills_list_window)

        self.reports_window = ReportsWindow()
        self.stack.addWidget(self.reports_window)

        self.receipt_window = ReceiptWindow()
        self.stack.addWidget(self.receipt_window)

        self.blank_invoice_window = BlankInvoiceWindow()
        self.stack.addWidget(self.blank_invoice_window)

        self.settings_widget = self._build_settings_page()
        self.stack.addWidget(self.settings_widget)

        content_layout.addWidget(self.stack)
        main_layout.addWidget(content_frame, 1)

        self.nav_buttons[0].setChecked(True)
        self.stack.setCurrentIndex(0)

    def _nav_to(self, index: int):
        """Programmatically navigate to a sidebar page by index."""
        for b in self.nav_buttons:
            b.setChecked(b.page_index == index)
        self.stack.setCurrentIndex(index)
        self._refresh_page(index)

    def _refresh_page(self, index: int):
        if index == 0:
            self._refresh_dashboard()
        elif index == 1:
            self.customer_window._refresh()
        elif index == 2:
            self.billing_window.refresh_for_new()
        elif index == 3:
            self.bills_list_window.refresh_list()
        elif index == 4:
            self.reports_window.refresh()
        elif index == 5:
            self.receipt_window.refresh_list()
        elif index == 6:
            self.blank_invoice_window.refresh_for_new()
        elif index == 7:
            self._refresh_settings()

    def _on_nav_click(self):
        btn = self.sender()
        for b in self.nav_buttons:
            b.setChecked(b is btn)
        idx = btn.page_index
        self.stack.setCurrentIndex(idx)
        self._refresh_page(idx)

    def _build_dashboard(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Dashboard")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(16)

        self.dash_cards = {}
        card_grid = QGridLayout()
        card_grid.setSpacing(16)

        cards_data = [
            ("today_sales", "Today's Sales", " 0", "#4caf50"),
            ("total_customers", "Total Companies", "0", "#2196f3"),
            ("total_farmers", "Total Farmers", "0", "#ff9800"),
            ("total_bills", "Bills", "0", "#9c27b0"),
        ]
        for i, (key, title, val, color) in enumerate(cards_data):
            card = CardWidget(title, val, color)
            card_grid.addWidget(card, i // 2, i % 2)
            self.dash_cards[key] = card.value_label

        layout.addLayout(card_grid)
        layout.addSpacing(24)

        recent_label = QLabel("Recent Bills")
        recent_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(recent_label)
        layout.addSpacing(8)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(
            ["Bill #", "Company", "Date", "Amount", "Status"]
        )
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.verticalHeader().setDefaultSectionSize(40)
        self.recent_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 4px; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 6px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.recent_table)

        return w

    def _refresh_dashboard(self):
        data = get_dashboard_data()
        self.dash_cards["today_sales"].setText(f"  {data['today_sales']:,.2f}")
        self.dash_cards["total_customers"].setText(str(data["total_customers"]))
        self.dash_cards["total_farmers"].setText(str(data["total_farmers"]))
        self.dash_cards["total_bills"].setText(str(data["total_bills"]))

        self.recent_table.setRowCount(0)
        for bill in data["recent_bills"]:
            row = self.recent_table.rowCount()
            self.recent_table.insertRow(row)
            self.recent_table.setItem(row, 0, QTableWidgetItem(bill["bill_no"]))
            self.recent_table.setItem(row, 1, QTableWidgetItem(bill["customer_name"]))
            self.recent_table.setItem(row, 2, QTableWidgetItem(bill["bill_date"]))
            self.recent_table.setItem(row, 3, QTableWidgetItem(f"  {bill['amount']:,.2f}"))
            self.recent_table.setItem(row, 4, QTableWidgetItem("Active"))

    def _build_settings_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Company Settings")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(16)

        from PySide6.QtWidgets import QFormLayout, QLineEdit, QTextEdit, QGroupBox, QPushButton, QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(12)
        form.setContentsMargins(0, 0, 0, 0)

        company = get_company()

        self.settings_fields = {}
        fields = [
            ("address", "Address", lambda: QTextEdit()),
            ("phone", "Phone", QLineEdit),
            ("email", "Email", QLineEdit),
            ("website", "Website", QLineEdit),
            ("pan", "PAN", QLineEdit),
            ("bank_name", "Bank Name", QLineEdit),
            ("bank_account", "Account Number", QLineEdit),
            ("bank_ifsc", "IFSC Code", QLineEdit),
            ("invoice_prefix", "Bill Prefix", QLineEdit),
            ("footer_line1", "Footer Line 1", QLineEdit),
            ("footer_line2", "Footer Line 2", QLineEdit),
        ]

        company_name_label = QLabel(
            "<b>Ragumani Transport &amp; Fire Woods Suppliers</b>"
        )
        company_name_label.setStyleSheet("font-size: 14px; color: #1a237e; padding: 8px 0;")
        form.addRow("Company:", company_name_label)

        for key, label, widget_type in fields:
            wgt = widget_type()
            if isinstance(wgt, QTextEdit):
                wgt.setFixedHeight(60)
            elif isinstance(wgt, QLineEdit):
                wgt.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
            form.addRow(f"{label}:", wgt)
            if key in company:
                val = company[key] or ""
                if isinstance(wgt, QTextEdit):
                    wgt.setPlainText(val)
                else:
                    wgt.setText(val)
            self.settings_fields[key] = wgt

        form.addRow("", QLabel(""))
        terms_label = QLabel("Terms & Conditions (for bill print):")
        terms_label.setStyleSheet("font-weight: bold; color: #1a237e; margin-top: 8px;")
        form.addRow(terms_label)
        self.terms_edit = QTextEdit()
        self.terms_edit.setFixedHeight(100)
        self.terms_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 9pt;")
        self.terms_edit.setPlainText(get_db_setting("terms",
            "1. All disputes subject to local jurisdiction.\n"
            "2. Payment due within 15 days from bill date.\n"
            "3. Goods once sold will not be taken back."))
        form.addRow("Terms:", self.terms_edit)

        form.addRow("", QLabel(""))

        save_btn = QPushButton("  Save Settings")
        save_btn.setStyleSheet("""
            QPushButton { background: #3f51b5; color: white; padding: 10px 30px;
                          border: none; border-radius: 4px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #303f9f; }
        """)
        save_btn.clicked.connect(self._save_settings)
        form.addRow(save_btn)

        scroll.setWidget(form_widget)
        layout.addWidget(scroll)
        return w

    def _save_settings(self):
        try:
            data = {}
            for key, wgt in self.settings_fields.items():
                if isinstance(wgt, QTextEdit):
                    data[key] = wgt.toPlainText()
                else:
                    data[key] = wgt.text()
            save_company(data)
            set_db_setting("terms", self.terms_edit.toPlainText())
            QMessageBox.information(self, "Saved", "Company settings saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings:\n{e}")

    def _refresh_settings(self):
        company = get_company()
        for key, wgt in self.settings_fields.items():
            val = company.get(key, "")
            if isinstance(wgt, QTextEdit):
                wgt.setPlainText(val)
            else:
                wgt.setText(val)
        self.terms_edit.setPlainText(get_db_setting("terms",
            "1. All disputes subject to local jurisdiction.\n"
            "2. Payment due within 15 days from bill date.\n"
            "3. Goods once sold will not be taken back."))

    def _backup_db(self):
        try:
            path = backup_database()
            QMessageBox.information(self, "Backup Complete", f"Database backed up to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", str(e))

    def closeEvent(self, event):
        close()
        event.accept()
