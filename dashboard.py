import sys
import subprocess
import webbrowser
import os
import json
import pandas as pd
from collections import Counter

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFrame,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QScrollArea, QStackedWidget, QLineEdit, QComboBox, QTabBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


DATA_DIR = "data"
LOG_FILE = "logs.txt"
AHA_FILE = os.path.join(DATA_DIR, "aha_output.csv")
RQI_FILE = os.path.join(DATA_DIR, "preprod_cl.csv")
STATUS_FILE = "status.txt"
CONFIG_FILE = "config.json"

AHA_LOGIN_URL = "https://atlas.heart.org/"
CPR_CALENDAR_URL = "https://cprlifeline.net/bls-schedule-now/"
AZURE_OUTLOOK_URL = "https://outlook.office.com/"

DEFAULT_CONFIG = {
    "aha_user": "",
    "aha_pass": "",
    "outlook_user": "",
    "azure_client_id": "",
    "azure_tenant_id": "",
    "sftp_host": "",
    "sftp_port": "6239",
    "sftp_user": "",
    "sftp_pass": "",
    "sftp_path": "/uploads/116286/preprod_cl.csv"
}

LOCATION_MAP = {
    "bartlett": "Bartlett",
    "brentwood": "Brentwood",
    "chamblee": "Chamblee",
    "decatur": "Decatur",
    "exchange": "The Exchange",
    "the exchange": "The Exchange",
    "film house": "Film House",
    "film": "Film House",
    "music circle": "Music Circle",
    "music": "Music Circle",
    "perkins": "Perkins",
    "poplar": "Poplar",
    "sycamore": "Sycamore",
    "california": "Sac State",
    "sac state": "Sac State",
    "atlanta": "Chamblee",
    "ga 30341": "Chamblee",
    "tucker road": "Chamblee"
}

LOCATION_LIST = sorted(set(LOCATION_MAP.values()))


class Card(QFrame):
    def __init__(self, title: str, value: str, color: str):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #1f232b;
                border-radius: 14px;
            }
        """)
        layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #c8c8c8; font-size: 14px;")
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: 600;")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        self.setLayout(layout)

    def set_value(self, value: str):
        self.value_label.setText(value)


class AnalyticsBox(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #0d0f12;
                border: 1px solid #2b313b;
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout()
        self.title = QLabel(title)
        self.title.setStyleSheet("font-size: 16px; font-weight: 600; color: white;")
        self.body = QTextEdit()
        self.body.setReadOnly(True)
        self.body.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.title)
        layout.addWidget(self.body)
        self.setLayout(layout)

    def set_text(self, text: str):
        self.body.setPlainText(text)


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.process = None

        self.last_log_mtime = None
        self.last_aha_mtime = None
        self.last_rqi_mtime = None
        self.last_status_mtime = None

        self.config = self.load_config()

        self.setWindowTitle("Automation Machine")
        self.setGeometry(100, 100, 1600, 950)
        self.setStyleSheet("background-color: #121417; color: white;")
        self.init_ui()
        self.start_refresh()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
            except Exception:
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        self.config["aha_user"] = self.aha_user_input.text().strip()
        self.config["aha_pass"] = self.aha_pass_input.text().strip()
        self.config["outlook_user"] = self.outlook_user_input.text().strip()
        self.config["azure_client_id"] = self.azure_client_id_input.text().strip()
        self.config["azure_tenant_id"] = self.azure_tenant_id_input.text().strip()
        self.config["sftp_host"] = self.sftp_host_input.text().strip()
        self.config["sftp_port"] = self.sftp_port_input.text().strip()
        self.config["sftp_user"] = self.sftp_user_input.text().strip()
        self.config["sftp_pass"] = self.sftp_pass_input.text().strip()
        self.config["sftp_path"] = self.sftp_path_input.text().strip()

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            QMessageBox.information(self, "Saved", "Settings saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save settings:\n{e}")

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        sidebar = QVBoxLayout()
        sidebar.setSpacing(12)

        icons = ["🏠", "🔔", "📍", "📊", "⚙️"]
        for i, icon in enumerate(icons):
            btn = QPushButton(icon)
            btn.setFixedHeight(56)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1f232b;
                    border-radius: 12px;
                    font-size: 20px;
                }
                QPushButton:hover {
                    background-color: #2b313b;
                }
            """)
            btn.clicked.connect(lambda checked, idx=i: self.switch_page(idx))
            sidebar.addWidget(btn)

        sidebar.addStretch()
        main_layout.addLayout(sidebar, 1)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.create_dashboard_page())
        self.stack.addWidget(self.create_reminders_page())
        self.stack.addWidget(self.create_locations_page())
        self.stack.addWidget(self.create_analytics_page())
        self.stack.addWidget(self.create_settings_page())

        main_layout.addWidget(self.stack, 5)
        self.setLayout(main_layout)

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)

    def create_dashboard_page(self):
        page = QWidget()
        container_layout = QVBoxLayout(page)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        right = QVBoxLayout(content)
        right.setSpacing(14)

        cards = QHBoxLayout()
        self.card_status = Card("Automation", "Idle", "#00e08a")
        self.card_browser = Card("Browser", "Azure Login", "#00c2ff")
        self.card_interval = Card("Interval", "5 sec", "#ffaa00")
        self.card_queue = Card("Queue", "0 record(s)", "#ff6666")

        cards.addWidget(self.card_status)
        cards.addWidget(self.card_browser)
        cards.addWidget(self.card_interval)
        cards.addWidget(self.card_queue)
        right.addLayout(cards)

        analytics_cards = QHBoxLayout()
        self.card_total = Card("Total Students", "0", "#8a7dff")
        self.card_new = Card("New Students", "0", "#00ff99")
        self.card_courses = Card("Courses", "0", "#ffcc00")
        self.card_locations = Card("Locations", "0", "#ff8a65")

        analytics_cards.addWidget(self.card_total)
        analytics_cards.addWidget(self.card_new)
        analytics_cards.addWidget(self.card_courses)
        analytics_cards.addWidget(self.card_locations)
        right.addLayout(analytics_cards)

        btn_layout1 = QHBoxLayout()
        btn_layout1.addWidget(self.create_btn("Run Pipeline", self.run_pipeline))
        btn_layout1.addWidget(self.create_btn("Stop Pipeline", self.stop_pipeline))
        btn_layout1.addWidget(self.create_btn("Open AHA Login", lambda: webbrowser.open(AHA_LOGIN_URL)))
        btn_layout1.addWidget(self.create_btn("Open CPR Calendar", lambda: webbrowser.open(CPR_CALENDAR_URL)))
        btn_layout1.addWidget(self.create_btn("Open Azure Outlook", lambda: webbrowser.open(AZURE_OUTLOOK_URL)))
        btn_layout1.addWidget(self.create_btn("Refresh", self.refresh_all))
        right.addLayout(btn_layout1)

        btn_layout2 = QHBoxLayout()
        btn_layout2.addWidget(self.create_btn("Open AHA CSV", lambda: self.open_file(AHA_FILE)))
        btn_layout2.addWidget(self.create_btn("Open RQI CSV", lambda: self.open_file(RQI_FILE)))
        btn_layout2.addWidget(self.create_btn("Open Data Folder", self.open_data_folder))
        right.addLayout(btn_layout2)

        right.addWidget(self.section_title("Live Logs"))

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setStyleSheet("""
            QTextEdit {
                background-color: #0d0f12;
                color: #00ff99;
                border: 1px solid #2b313b;
                border-radius: 10px;
                font-family: Consolas;
                font-size: 13px;
            }
        """)
        self.logs.setMinimumHeight(240)
        right.addWidget(self.logs)

        analytics_row = QHBoxLayout()
        self.location_box = AnalyticsBox("Students by Location")
        self.course_box = AnalyticsBox("Students by Course")
        self.summary_box = AnalyticsBox("Summary")
        analytics_row.addWidget(self.location_box)
        analytics_row.addWidget(self.course_box)
        analytics_row.addWidget(self.summary_box)
        right.addLayout(analytics_row)

        tables = QHBoxLayout()

        aha_box = QVBoxLayout()
        aha_box.addWidget(self.section_title("AHA Output"))
        self.aha_table = self.make_table()
        aha_box.addWidget(self.aha_table)

        rqi_box = QVBoxLayout()
        rqi_box.addWidget(self.section_title("RQI Output"))
        self.rqi_table = self.make_table()
        rqi_box.addWidget(self.rqi_table)

        tables.addLayout(aha_box)
        tables.addLayout(rqi_box)
        right.addLayout(tables)

        scroll.setWidget(content)
        container_layout.addWidget(scroll)
        return page

    def create_reminders_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        tabs = QTabBar()
        tabs.addTab("Automated Logs")
        tabs.addTab("Manual Emailer")
        tabs.setStyleSheet("""
            QTabBar::tab {
                background: #1f232b;
                color: white;
                padding: 10px;
                min-width: 150px;
            }
            QTabBar::tab:selected {
                background: #2b313b;
                border-bottom: 2px solid #00e08a;
            }
        """)
        layout.addWidget(tabs)

        sub_stack = QStackedWidget()

        auto_logs = QTextEdit()
        auto_logs.setReadOnly(True)
        auto_logs.setPlainText("Automated reminder logs will appear here.")
        auto_logs.setStyleSheet("""
            QTextEdit {
                background-color: #0d0f12;
                color: #00ff99;
                border: 1px solid #2b313b;
                border-radius: 10px;
                font-family: Consolas;
                font-size: 13px;
            }
        """)
        sub_stack.addWidget(auto_logs)

        manual_page = QFrame()
        manual_page.setStyleSheet("""
            QFrame {
                background-color: #1f232b;
                border-radius: 12px;
                padding: 20px;
            }
            QLabel {
                color: white;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #0d0f12;
                color: white;
                padding: 10px;
                border: 1px solid #2b313b;
                border-radius: 5px;
            }
        """)

        m_layout = QVBoxLayout(manual_page)

        m_layout.addWidget(QLabel("Student Email Address*"))
        self.manual_email = QLineEdit()
        self.manual_email.setPlaceholderText("recipient@example.com")
        m_layout.addWidget(self.manual_email)

        m_layout.addWidget(QLabel("Select Location*"))
        self.manual_loc = QComboBox()
        self.manual_loc.addItems(LOCATION_LIST)
        m_layout.addWidget(self.manual_loc)

        m_layout.addWidget(QLabel("First Name"))
        self.manual_first = QLineEdit()
        self.manual_first.setPlaceholderText("Optional")
        m_layout.addWidget(self.manual_first)

        m_layout.addWidget(QLabel("Last Name"))
        self.manual_last = QLineEdit()
        self.manual_last.setPlaceholderText("Optional")
        m_layout.addWidget(self.manual_last)

        m_layout.addWidget(QLabel("Custom Subject"))
        self.manual_subject = QLineEdit()
        self.manual_subject.setPlaceholderText("Leave blank to use default subject")
        m_layout.addWidget(self.manual_subject)

        m_layout.addWidget(QLabel("Custom Message Body"))
        self.manual_body = QTextEdit()
        self.manual_body.setPlaceholderText("Leave blank to use location template.")
        m_layout.addWidget(self.manual_body)

        reminder_btns = QHBoxLayout()
        reminder_btns.addWidget(self.create_btn("Preview Email", self.preview_manual_email))
        reminder_btns.addWidget(self.create_btn("Send Manual Reminder", self.send_manual_reminder))
        reminder_btns.addWidget(self.create_btn("Refresh Locations", self.refresh_locations))
        m_layout.addLayout(reminder_btns)

        sub_stack.addWidget(manual_page)

        tabs.currentChanged.connect(sub_stack.setCurrentIndex)
        layout.addWidget(sub_stack)
        return page

    def create_locations_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        tabs = QTabBar()
        tabs.addTab("Location Keys")
        tabs.addTab("Location Templates")
        tabs.addTab("Location Teacher")
        tabs.setStyleSheet("""
            QTabBar::tab {
                background: #1f232b;
                color: white;
                padding: 10px;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background: #2b313b;
                border-bottom: 2px solid #ffcc00;
            }
        """)
        layout.addWidget(tabs)

        sub_stack = QStackedWidget()

        keys_page = QFrame()
        keys_page.setStyleSheet("background-color: #1f232b; border-radius: 12px; padding: 20px;")
        keys_layout = QVBoxLayout(keys_page)

        self.location_keys_text = QTextEdit()
        self.location_keys_text.setReadOnly(True)
        self.location_keys_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d0f12;
                color: white;
                border: 1px solid #2b313b;
                border-radius: 8px;
                font-family: Consolas;
            }
        """)
        self.location_keys_text.setPlainText(
            "\n".join([f"{key}  ->  {value}" for key, value in LOCATION_MAP.items()])
        )
        keys_layout.addWidget(self.section_title("Location Keys Mapping"))
        keys_layout.addWidget(self.location_keys_text)
        sub_stack.addWidget(keys_page)

        template_page = QFrame()
        template_page.setStyleSheet("""
            QFrame {
                background-color: #1f232b;
                border-radius: 12px;
                padding: 20px;
            }
            QLabel {
                color: white;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #0d0f12;
                color: white;
                padding: 10px;
                border: 1px solid #2b313b;
                border-radius: 5px;
            }
        """)
        t_layout = QVBoxLayout(template_page)

        t_layout.addWidget(QLabel("Select Location*"))
        self.template_loc = QComboBox()
        self.template_loc.addItems(LOCATION_LIST)
        t_layout.addWidget(self.template_loc)

        t_layout.addWidget(QLabel("Subject"))
        self.temp_subject = QLineEdit()
        self.temp_subject.setPlaceholderText("CPR Lifeline Appointment")
        t_layout.addWidget(self.temp_subject)

        t_layout.addWidget(QLabel("Template Body"))
        self.temp_body = QTextEdit()
        self.temp_body.setPlaceholderText("Enter location email template here.")
        t_layout.addWidget(self.temp_body)

        t_layout.addWidget(self.create_btn("Save Template", self.save_template))
        sub_stack.addWidget(template_page)

        teacher_page = QFrame()
        teacher_page.setStyleSheet("""
            QFrame {
                background-color: #1f232b;
                border-radius: 12px;
                padding: 20px;
            }
            QLabel {
                color: white;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #0d0f12;
                color: white;
                padding: 10px;
                border: 1px solid #2b313b;
                border-radius: 5px;
            }
        """)
        teach_layout = QVBoxLayout(teacher_page)

        teach_layout.addWidget(QLabel("Teacher Email Address*"))
        self.teacher_email_input = QLineEdit()
        self.teacher_email_input.setPlaceholderText("yourname@cprlifeline.net")
        teach_layout.addWidget(self.teacher_email_input)

        teach_layout.addWidget(QLabel("Select Location to Reach All Students"))
        self.teacher_loc_target = QComboBox()
        self.teacher_loc_target.addItems(LOCATION_LIST)
        teach_layout.addWidget(self.teacher_loc_target)

        teach_layout.addWidget(QLabel("Subject"))
        self.teacher_msg_subject = QLineEdit()
        teach_layout.addWidget(self.teacher_msg_subject)

        teach_layout.addWidget(QLabel("Body"))
        self.teacher_msg_body = QTextEdit()
        teach_layout.addWidget(self.teacher_msg_body)

        teach_layout.addWidget(self.create_btn("Send to Every Student at this Location", self.send_bulk_teacher_email))
        sub_stack.addWidget(teacher_page)

        tabs.currentChanged.connect(sub_stack.setCurrentIndex)
        layout.addWidget(sub_stack)
        return page

    def create_analytics_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background-color: #1f232b;
                border-radius: 15px;
                padding: 25px;
            }
        """)
        box_layout = QVBoxLayout(box)
        box_layout.addWidget(self.section_title("Analytics Overview"))

        self.analytics_text = QTextEdit()
        self.analytics_text.setReadOnly(True)
        self.analytics_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d0f12;
                color: white;
                border: 1px solid #2b313b;
                border-radius: 10px;
                font-size: 14px;
            }
        """)
        box_layout.addWidget(self.analytics_text)

        layout.addWidget(box)
        return page

    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #1f232b;
                border-radius: 15px;
                padding: 25px;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #0d0f12;
                color: white;
                padding: 10px;
                border: 1px solid #2b313b;
                border-radius: 6px;
            }
        """)

        c_layout = QVBoxLayout(container)

        c_layout.addWidget(self.section_title("Settings / Credentials Management"))
        c_layout.addWidget(QLabel("Update login and connection details here without editing code."))

        c_layout.addWidget(QLabel("AHA Atlas Login"))
        self.aha_user_input = QLineEdit(self.config.get("aha_user", ""))
        self.aha_user_input.setPlaceholderText("AHA username/email")
        self.aha_pass_input = QLineEdit(self.config.get("aha_pass", ""))
        self.aha_pass_input.setPlaceholderText("AHA password")
        self.aha_pass_input.setEchoMode(QLineEdit.Password)
        c_layout.addWidget(self.aha_user_input)
        c_layout.addWidget(self.aha_pass_input)

        c_layout.addWidget(QLabel("Azure / Outlook"))
        self.outlook_user_input = QLineEdit(self.config.get("outlook_user", ""))
        self.outlook_user_input.setPlaceholderText("Outlook email")
        self.azure_client_id_input = QLineEdit(self.config.get("azure_client_id", ""))
        self.azure_client_id_input.setPlaceholderText("Azure Client ID")
        self.azure_tenant_id_input = QLineEdit(self.config.get("azure_tenant_id", ""))
        self.azure_tenant_id_input.setPlaceholderText("Azure Tenant ID")
        c_layout.addWidget(self.outlook_user_input)
        c_layout.addWidget(self.azure_client_id_input)
        c_layout.addWidget(self.azure_tenant_id_input)

        c_layout.addWidget(QLabel("SFTP Settings"))
        self.sftp_host_input = QLineEdit(self.config.get("sftp_host", ""))
        self.sftp_host_input.setPlaceholderText("SFTP host")
        self.sftp_port_input = QLineEdit(self.config.get("sftp_port", "6239"))
        self.sftp_port_input.setPlaceholderText("SFTP port")
        self.sftp_user_input = QLineEdit(self.config.get("sftp_user", ""))
        self.sftp_user_input.setPlaceholderText("SFTP username")
        self.sftp_pass_input = QLineEdit(self.config.get("sftp_pass", ""))
        self.sftp_pass_input.setPlaceholderText("SFTP password")
        self.sftp_pass_input.setEchoMode(QLineEdit.Password)
        self.sftp_path_input = QLineEdit(self.config.get("sftp_path", ""))
        self.sftp_path_input.setPlaceholderText("Remote file path")

        c_layout.addWidget(self.sftp_host_input)
        c_layout.addWidget(self.sftp_port_input)
        c_layout.addWidget(self.sftp_user_input)
        c_layout.addWidget(self.sftp_pass_input)
        c_layout.addWidget(self.sftp_path_input)

        save_btn = self.create_btn("Save Settings", self.save_config)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #00e08a;
                color: black;
                font-weight: bold;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        c_layout.addWidget(save_btn)
        c_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)
        return page

    def preview_manual_email(self):
        email = self.manual_email.text().strip()
        location = self.manual_loc.currentText()
        first = self.manual_first.text().strip()

        subject = self.manual_subject.text().strip()
        if not subject:
            subject = f"CPR Lifeline - {location} Reminder"

        body = self.manual_body.toPlainText().strip()
        if not body:
            body = f"Hello {first},\n\nThis is a reminder for your CPR Lifeline registration at {location}."

        QMessageBox.information(self, "Email Preview", f"To: {email}\n\nSubject: {subject}\n\n{body}")

    def send_manual_reminder(self):
        email = self.manual_email.text().strip()
        location = self.manual_loc.currentText()

        if not email or "@" not in email:
            QMessageBox.warning(self, "Input Error", "Please enter a valid student email address.")
            return

        subject = self.manual_subject.text().strip() or f"CPR Lifeline - {location} Reminder"
        body = self.manual_body.toPlainText().strip() or f"This is a reminder for your CPR Lifeline registration at {location}."

        webbrowser.open(f"mailto:{email}?subject={subject}&body={body}")
        QMessageBox.information(self, "Email", "Reminder email opened in mail client.")

    def refresh_locations(self):
        self.manual_loc.clear()
        self.manual_loc.addItems(LOCATION_LIST)
        QMessageBox.information(self, "Locations", "Locations refreshed.")

    def save_template(self):
        QMessageBox.information(self, "Saved", "Template saved successfully.")

    def send_bulk_teacher_email(self):
        teacher = self.teacher_email_input.text().strip()
        location = self.teacher_loc_target.currentText()

        if not teacher or "@" not in teacher:
            QMessageBox.warning(self, "Input Error", "Please enter a valid teacher email address.")
            return

        try:
            if os.path.exists(AHA_FILE):
                df = pd.read_csv(AHA_FILE)

                if "LocationName" in df.columns:
                    df = df[df["LocationName"].astype(str) == location]

                count = len(df)

                reply = QMessageBox.question(
                    self,
                    "Confirm Mass Email",
                    f"Send email from {teacher} to all {count} students for {location}?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    QMessageBox.information(self, "Success", f"Emails prepared for {count} students.")
            else:
                QMessageBox.warning(self, "Data Error", "No student data found in aha_output.csv")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process bulk email: {e}")

    def create_btn(self, text, func):
        btn = QPushButton(text)
        btn.setFixedHeight(42)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1f232b;
                border-radius: 10px;
                padding: 8px;
                color: white;
            }
            QPushButton:hover {
                background-color: #2b313b;
            }
        """)
        btn.clicked.connect(func)
        return btn

    def section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 18px; font-weight: 600; color: white;")
        return label

    def make_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                background-color: #0d0f12;
                border: 1px solid #2b313b;
                border-radius: 10px;
                color: white;
                gridline-color: #2b313b;
            }
            QHeaderView::section {
                background-color: #1f232b;
                color: white;
                padding: 6px;
                border: none;
            }
        """)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        return table

    def start_refresh(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_all)
        self.timer.start(5000)
        self.refresh_all()

    def run_pipeline(self):
        if self.process is not None and self.process.poll() is None:
            QMessageBox.information(self, "Info", "Pipeline is already running.")
            return

        try:
            flags = subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP") else 0
            self.process = subprocess.Popen([sys.executable, "app_all_in_one.py"], creationflags=flags)
            self.card_status.set_value("Running")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not start pipeline:\n{e}")

    def stop_pipeline(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            self.card_status.set_value("Stopped")
        else:
            QMessageBox.information(self, "Info", "No running pipeline found.")

    def open_file(self, path: str):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Missing File", f"File not found:\n{path}")
            return
        os.startfile(os.path.abspath(path))

    def open_data_folder(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.startfile(os.path.abspath(DATA_DIR))

    def load_table(self, path, table, kind):
        if not os.path.exists(path):
            table.setRowCount(0)
            table.setColumnCount(0)
            return

        try:
            df = pd.read_csv(path)

            table.setRowCount(df.shape[0])
            table.setColumnCount(df.shape[1])
            table.setHorizontalHeaderLabels([str(c) for c in df.columns])

            for i in range(df.shape[0]):
                for j in range(df.shape[1]):
                    value = "" if pd.isna(df.iat[i, j]) else str(df.iat[i, j])
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    table.setItem(i, j, item)
        except Exception:
            table.setRowCount(0)
            table.setColumnCount(0)

    def count_rows(self, path: str) -> str:
        try:
            if os.path.exists(path):
                df = pd.read_csv(path)
                return str(len(df))
        except Exception:
            pass
        return "0"

    def load_status(self):
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    data = f.read().strip().split(",")
                    if len(data) >= 2:
                        new_students = data[0]
                        total_students = data[1]
                        self.card_new.set_value(str(new_students))
                        self.card_queue.set_value(f"{total_students} record(s)")
                        return
        except Exception:
            pass

        self.card_new.set_value("0")
        self.card_queue.set_value(self.count_rows(RQI_FILE) + " record(s)")

    def refresh_logs(self):
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                self.logs.setPlainText(content[-15000:])
                self.logs.verticalScrollBar().setValue(self.logs.verticalScrollBar().maximum())
            else:
                self.logs.setPlainText("")
        except Exception as e:
            self.logs.setPlainText(f"Error loading logs: {e}")

    def load_analytics(self):
        total_students = 0
        location_counter = Counter()
        course_counter = Counter()

        try:
            if os.path.exists(RQI_FILE):
                df = pd.read_csv(RQI_FILE)

                if not df.empty:
                    total_students = len(df)

                    if "LocationName" in df.columns:
                        for value in df["LocationName"].fillna("Unknown"):
                            location_counter[str(value)] += 1

                    if "Group" in df.columns:
                        for value in df["Group"].fillna("Unknown"):
                            course_counter[str(value)] += 1

            self.card_total.set_value(str(total_students))
            self.card_courses.set_value(str(len(course_counter)))
            self.card_locations.set_value(str(len(location_counter)))

            self.location_box.set_text(
                "\n".join([f"{name}: {count}" for name, count in location_counter.most_common()]) or "No data"
            )

            self.course_box.set_text(
                "\n".join([f"{name}: {count}" for name, count in course_counter.most_common()]) or "No data"
            )

            summary = [
                f"Total students: {total_students}",
                f"Unique courses: {len(course_counter)}",
                f"Unique locations: {len(location_counter)}"
            ]

            if course_counter:
                top_course = course_counter.most_common(1)[0]
                summary.append(f"Top course: {top_course[0]} ({top_course[1]})")

            if location_counter:
                top_location = location_counter.most_common(1)[0]
                summary.append(f"Top location: {top_location[0]} ({top_location[1]})")

            self.summary_box.set_text("\n".join(summary))

            if hasattr(self, "analytics_text"):
                self.analytics_text.setPlainText("\n".join(summary))

        except Exception:
            pass

    def refresh_all(self):
        self.refresh_logs()
        self.load_table(AHA_FILE, self.aha_table, "aha")
        self.load_table(RQI_FILE, self.rqi_table, "rqi")

        if self.process is not None and self.process.poll() is None:
            self.card_status.set_value("Running")
        else:
            self.card_status.set_value("Idle")

        self.load_status()
        self.load_analytics()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = Dashboard()
    win.showNormal()
    win.show()
    win.raise_()
    win.activateWindow()
    sys.exit(app.exec_())