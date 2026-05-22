import os
import re
import time
import json
import requests
import pandas as pd
import paramiko
from msal import PublicClientApplication
from pandas.errors import EmptyDataError

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================
# LOAD DASHBOARD CONFIG
# =========================
CONFIG_FILE = "config.json"

def load_dashboard_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


config = load_dashboard_config()


# =========================
# CONFIG
# =========================
CLIENT_ID = config.get("azure_client_id", "").strip()
TENANT_ID = config.get("azure_tenant_id", "").strip()
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}" if TENANT_ID else ""
SCOPES = ["Mail.Read", "Mail.Send", "User.Read"]

# SFTP PRE-PROD / SANDBOX
SFTP_HOST = config.get("sftp_host", "").strip()
SFTP_PORT = int(config.get("sftp_port", "6239"))
SFTP_USER = config.get("sftp_user", "").strip()
SFTP_PASS = config.get("sftp_pass", "").strip()
SFTP_REMOTE_PATH = config.get("sftp_path", "/uploads/116286/preprod_cl.csv").strip()

# AHA
AHA_USERNAME = config.get("aha_user", "").strip()
AHA_PASSWORD = config.get("aha_pass", "").strip()
AHA_LOGIN_URL = "https://atlas.heart.org/"

DATA_DIR = "data"
LOG_FILE = "logs.txt"
HISTORY_FILE = "processed_emails.txt"
PROGRESS_FILE = os.path.join(DATA_DIR, "student_progress.csv")
AHA_FILE = os.path.join(DATA_DIR, "aha_output.csv")
RQI_FILE = os.path.join(DATA_DIR, "preprod_cl.csv")
STATUS_FILE = "status.txt"

GOOGLE_SHEET_NAME = "CPR Students"
POLL_SECONDS = 10

AHA_COLUMNS = [
    "EMAIL",
    "First Name",
    "M",
    "Last Name",
    "Phone",
    "Course",
    "Date",
    "Acuity Regist.",
    "AHA Regist.",
    "Reminder email sent",
    "LocationName",
    "StatusFlag",
]

RQI_COLUMNS = [
    "LocationID",
    "LocationName",
    "UserID",
    "FirstName",
    "MiddleName",
    "LastName",
    "Email",
    "JobCode",
    "JobName",
    "HireDate",
    "Status",
    "DateOfBirth",
    "Gender",
    "YearsofExperiences",
    "ActiveDate",
    "InactiveDate",
    "Group",
]

PROGRESS_COLUMNS = [
    "Email",
    "Course",
    "Progress",
    "Feedback",
    "LastReminderSent",
    "ReminderCount",
    "ReminderStatus"
]

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
    "tucker road": "Chamblee",
}

LOCATION_TEMPLATES = {
    "BARTLETT": {
        "subject": "CPR Lifeline - Bartlett Location Details",
        "body": "Thank you for registering with CPR Lifeline at our Bartlett location. Please complete your RQI setup before your skills check."
    },
    "BRENTWOOD": {
        "subject": "CPR Lifeline - Brentwood Location Details",
        "body": "Thank you for registering with CPR Lifeline at our Brentwood location. Please complete your RQI setup before your skills check."
    },
    "CHAMBLEE": {
        "subject": "CPR Lifeline - Chamblee Location Details",
        "body": "Thank you for registering with CPR Lifeline at our Chamblee location. Please complete your RQI setup before your skills check."
    },
    "DECATUR": {
        "subject": "CPR Lifeline - Decatur Location Details",
        "body": "Thank you for registering with CPR Lifeline at our Decatur location. Please complete your RQI setup before your skills check."
    },
    "THE EXCHANGE": {
        "subject": "CPR Lifeline - The Exchange Location Details",
        "body": "Thank you for registering with CPR Lifeline at The Exchange location. Please complete your RQI setup before your skills check."
    },
    "FILM HOUSE": {
        "subject": "CPR Lifeline - Film House Location Details",
        "body": "Thank you for registering with CPR Lifeline at the Film House location. Please complete your RQI setup before your skills check."
    },
    "MUSIC CIRCLE": {
        "subject": "CPR Lifeline - Music Circle Location Details",
        "body": "Thank you for registering with CPR Lifeline at Music Circle. Please complete your RQI setup before your skills check."
    },
    "PERKINS": {
        "subject": "CPR Lifeline - Perkins Location Details",
        "body": "Thank you for registering with CPR Lifeline at Perkins. Please complete your RQI setup before your skills check."
    },
    "POPLAR": {
        "subject": "CPR Lifeline - Poplar Location Details",
        "body": "Thank you for registering with CPR Lifeline at Poplar. Please complete your RQI setup before your skills check."
    },
    "SYCAMORE": {
        "subject": "CPR Lifeline - Sycamore Location Details",
        "body": "Thank you for registering with CPR Lifeline at Sycamore. Please complete your RQI setup before your skills check."
    },
    "SAC STATE": {
        "subject": "CPR Lifeline - Sac State Location Details",
        "body": "Thank you for registering with CPR Lifeline at Sac State. Please complete your RQI setup before your skills check."
    },
}


# =========================
# UTILITIES
# =========================
def ensure_dirs_and_files() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(AHA_FILE):
        pd.DataFrame(columns=AHA_COLUMNS).to_csv(AHA_FILE, index=False)

    if not os.path.exists(RQI_FILE):
        pd.DataFrame(columns=RQI_COLUMNS).to_csv(RQI_FILE, index=False)

    if not os.path.exists(PROGRESS_FILE):
        pd.DataFrame(columns=PROGRESS_COLUMNS).to_csv(PROGRESS_FILE, index=False)

    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, "w", encoding="utf-8").close()


def log(msg: str) -> None:
    ensure_dirs_and_files()
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8", errors="ignore") as f:
        f.write(msg + "\n")


def update_status(new_students: int, total_students: int) -> None:
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(f"{new_students},{total_students}")


def is_valid_email(email: str) -> bool:
    if not email:
        return False
    email = str(email).strip().lower()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}$", email):
        return False
    blocked = [
        "no-reply", "postmaster", "daemon", "microsoft", "exchange",
        "mailer-daemon", "noreply"
    ]
    return not any(x in email for x in blocked)


def detect_course(text: str) -> str:
    text = str(text).lower()
    if "acls" in text:
        return "ACLS"
    if "pals" in text:
        return "PALS"
    return "BLS"


def detect_location(text: str) -> str:
    text = str(text).lower()
    for key, value in LOCATION_MAP.items():
        if key in text:
            return value
    return "Brentwood"


def clean_text(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>|</div>|</tr>|</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&amp;|&#39;|&quot;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


# =========================
# AHA AUTOMATION
# =========================
def build_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def aha_login(driver):
    driver.get(AHA_LOGIN_URL)
    wait = WebDriverWait(driver, 30)

    username_selectors = [
        (By.NAME, "email"),
        (By.NAME, "username"),
        (By.ID, "email"),
        (By.ID, "username"),
        (By.XPATH, "//input[contains(@type,'email')]"),
    ]

    password_selectors = [
        (By.NAME, "password"),
        (By.ID, "password"),
        (By.XPATH, "//input[contains(@type,'password')]"),
    ]

    username_box = None
    password_box = None

    for by, selector in username_selectors:
        try:
            username_box = wait.until(EC.presence_of_element_located((by, selector)))
            break
        except Exception:
            pass

    for by, selector in password_selectors:
        try:
            password_box = wait.until(EC.presence_of_element_located((by, selector)))
            break
        except Exception:
            pass

    if username_box is None or password_box is None:
        raise RuntimeError("Could not find AHA login fields.")

    username_box.clear()
    username_box.send_keys(AHA_USERNAME)

    password_box.clear()
    password_box.send_keys(AHA_PASSWORD)

    login_btn = None
    login_xpaths = [
        "//button[contains(., 'Sign In')]",
        "//button[contains(., 'Login')]",
        "//input[@type='submit']",
    ]

    for xpath in login_xpaths:
        try:
            login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            break
        except Exception:
            pass

    if login_btn is None:
        raise RuntimeError("Could not find AHA login button.")

    login_btn.click()
    time.sleep(5)
    log("AHA login attempted")


def accept_student_in_aha(driver, student: dict) -> bool:
    wait = WebDriverWait(driver, 20)

    first_name = str(student.get("First Name", "")).strip()
    last_name = str(student.get("Last Name", "")).strip()
    email_value = str(student.get("EMAIL", "")).strip()

    try:
        search_box = None
        search_selectors = [
            (By.XPATH, "//input[contains(@placeholder,'Search')]"),
            (By.XPATH, "//input[contains(@type,'search')]"),
            (By.NAME, "search"),
            (By.ID, "search"),
        ]

        for by, selector in search_selectors:
            try:
                search_box = wait.until(EC.presence_of_element_located((by, selector)))
                break
            except Exception:
                pass

        if search_box is None:
            raise RuntimeError("Search box not found in AHA.")

        search_box.clear()
        search_box.send_keys(email_value if email_value else f"{first_name} {last_name}")
        time.sleep(2)

        match_xpath = (
            f"//*[contains(text(), '{email_value}') or contains(text(), '{first_name}') "
            f"or contains(text(), '{last_name}')]"
        )
        row = wait.until(EC.presence_of_element_located((By.XPATH, match_xpath)))
        driver.execute_script("arguments[0].scrollIntoView(true);", row)
        time.sleep(1)

        accept_btn = None
        accept_xpaths = [
            "//button[contains(., 'Accept')]",
            "//button[contains(., 'Approve')]",
            "//button[contains(., 'Register')]",
            "//a[contains(., 'Accept')]",
        ]

        for xpath in accept_xpaths:
            try:
                accept_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                break
            except Exception:
                pass

        if accept_btn is None:
            raise RuntimeError("Accept button not found in AHA.")

        accept_btn.click()
        time.sleep(2)

        log(f"AHA accepted student: {first_name} {last_name} | {email_value}")
        return True

    except Exception as e:
        log(f"AHA accept failed for {first_name} {last_name} | {email_value}: {e}")
        return False


def auto_accept_aha_students(students: list[dict]) -> None:
    if not students:
        return

    driver = None
    try:
        driver = build_driver()
        aha_login(driver)

        for student in students:
            accepted = accept_student_in_aha(driver, student)
            if accepted:
                student["AHA Regist."] = "Accepted"
            else:
                student["AHA Regist."] = "Pending"

    except Exception as e:
        log(f"AHA automation error: {e}")

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# =========================
# AZURE GRAPH
# =========================
def validate_config() -> None:
    if not CLIENT_ID or not TENANT_ID:
        raise RuntimeError("Missing AZURE_CLIENT_ID or AZURE_TENANT_ID.")


def get_token() -> str:
    validate_config()

    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    flow = app.initiate_device_flow(scopes=SCOPES)

    if "user_code" not in flow:
        raise RuntimeError("Failed to create device login flow.")

    print("\n==============================")
    print("AZURE LOGIN REQUIRED")
    print("==============================")
    print(flow["message"])
    print("\nLogin only with your Azure organizational account.")
    print("Do not use the personal Outlook account.\n")

    result = app.acquire_token_by_device_flow(flow)
    token = result.get("access_token")
    if not token:
        raise RuntimeError(f"Azure login failed: {result}")

    id_claims = result.get("id_token_claims", {})
    username = id_claims.get("preferred_username", "")
    if "onmicrosoft.com" not in username.lower():
        raise RuntimeError(f"Wrong account used: {username}")

    log(f"Azure login successful: {username}")
    return token


def fetch_emails(token: str, max_messages: int = 5000) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Prefer": 'outlook.body-content-type="text"',
    }

    url = (
        "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
        "?$top=1000"
        "&$select=subject,from,body,receivedDateTime"
        "&$orderby=receivedDateTime desc"
    )

    all_messages = []
    page = 1

    while url and len(all_messages) < max_messages:
        try:
            log(f"Fetching mailbox page {page}...")
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()

            batch = data.get("value", [])
            all_messages.extend(batch)

            log(f"Fetched {len(batch)} messages on page {page}. Total so far: {len(all_messages)}")

            url = data.get("@odata.nextLink")
            page += 1

        except requests.exceptions.Timeout:
            log(f"Fetch emails timeout on page {page}. Retrying in 3 seconds...")
            time.sleep(3)
        except Exception as e:
            log(f"Mailbox paging error on page {page}: {e}")
            break

    return {"value": all_messages[:max_messages]}


def send_graph_email(token: str, to_email: str, subject: str, body_text: str) -> None:
    if not is_valid_email(to_email):
        log(f"Skipping invalid email: {to_email}")
        return

    url = "https://graph.microsoft.com/v1.0/me/sendMail"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body_text},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        }
    }

    response = requests.post(url, headers=headers, json=body, timeout=30)
    if response.status_code >= 400:
        raise RuntimeError(f"Send mail failed: {response.status_code} {response.text}")

    log(f"Email sent to {to_email}: {subject}")


# =========================
# EXTRACTION
# =========================
def extract_aha_data(emails: dict) -> list[dict]:
    students = []

    messages = emails.get("value", [])
    log(f"Total emails fetched from Azure inbox: {len(messages)}")

    for msg in messages:
        subject = str(msg.get("subject", "") or "")
        subject_lower = subject.lower()

        sender = str(msg.get("from", {}).get("emailAddress", {}).get("address", "") or "")
        body_raw = str(msg.get("body", {}).get("content", "") or "")
        body = clean_text(body_raw)
        body_lower = body.lower()

        if (
            "undeliverable" in subject_lower or
            "cpr reminder" in subject_lower or
            "weekly digest" in subject_lower or
            "delivery has failed" in subject_lower or
            "returned mail" in subject_lower
        ):
            log("Skipped system/reminder email")
            continue

        if any(x in sender.lower() for x in [
            "no-reply", "microsoft", "exchange", "postmaster", "daemon", "mailer-daemon"
        ]):
            log("Skipped sender-based system email")
            continue

        looks_like_registration = (
            "scheduled by a client" in body_lower or
            "appointment scheduled" in body_lower or
            "thank you for registering" in body_lower or
            "name:" in body_lower or
            "email:" in body_lower or
            "phone:" in body_lower or
            "online bls" in body_lower or
            "online acls" in body_lower or
            "online pals" in body_lower
        )

        if not looks_like_registration:
            log("Skipped non-registration email")
            continue

        log(f"Accepted registration-like email subject: {subject[:120]}")

        name = ""
        match = re.search(r"Name:\s*([A-Za-z' .\-]+)", body, flags=re.IGNORECASE)
        if match:
            name = match.group(1).strip()

        if not name:
            match = re.search(r"for\s+([A-Za-z' .\-]+)", body, flags=re.IGNORECASE)
            if match:
                name = match.group(1).strip()

        email_value = ""
        match = re.search(
            r"Email:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
            body,
            flags=re.IGNORECASE
        )
        if match:
            email_value = match.group(1).strip()

        if not email_value:
            found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", body)
            for e in found:
                e_lower = e.lower().strip()
                if not is_valid_email(e_lower):
                    continue
                if e_lower in [
                    "sacstatecpr@outlook.com",
                    "csc131-team02@csussandbox.onmicrosoft.com",
                    "info@cprlifeline.net"
                ]:
                    continue
                email_value = e.strip()
                break

        if not is_valid_email(email_value):
            log("Skipped email because no valid student email was found")
            continue

        if not name:
            local = email_value.split("@")[0]
            local = re.sub(r"[^A-Za-z._-]", " ", local).replace(".", " ").replace("_", " ").replace("-", " ")
            pieces = [p for p in local.split() if p]
            if len(pieces) >= 2:
                first = pieces[0].capitalize()
                last = pieces[-1].capitalize()
            elif len(pieces) == 1:
                first = pieces[0].capitalize()
                last = ""
            else:
                first = "Unknown"
                last = ""
        else:
            parts = [p for p in name.split() if p]
            first = parts[0] if parts else "Unknown"
            last = parts[-1] if len(parts) > 1 else ""

        phone = ""
        match = re.search(r"Phone:\s*([+\d()\-\s]+)", body, flags=re.IGNORECASE)
        if match:
            phone = match.group(1).strip()

        course = detect_course(subject + " " + body)

        date_value = time.strftime("%Y-%m-%d")
        match = re.search(r"When\s+(.*?)Where", body, re.DOTALL | re.IGNORECASE)
        if match:
            date_value = match.group(1).strip()

        location = detect_location(subject + " " + body)

        students.append({
            "EMAIL": email_value,
            "First Name": first,
            "M": "",
            "Last Name": last,
            "Phone": phone,
            "Course": course,
            "Date": date_value,
            "Acuity Regist.": "Yes",
            "AHA Regist.": "Pending",
            "Reminder email sent": "No",
            "LocationName": location,
        })

        log(f"Accepted student: {first} {last} | {email_value} | {course} | {location}")

    return students


# =========================
# CSV / FILES
# =========================
def filter_new(aha_data: list[dict]) -> tuple[list[dict], list[dict]]:
    ensure_dirs_and_files()

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        processed = set(f.read().splitlines())

    new_data = []
    all_data = []

    for row in aha_data:
        key = f"{row['EMAIL']}|{row.get('Course', '')}|{row.get('LocationName', '')}"
        if key not in processed:
            row["StatusFlag"] = "NEW"
            new_data.append(row)
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(key + "\n")
        else:
            row["StatusFlag"] = "OLD"
        all_data.append(row)

    return new_data, all_data


def save_aha_csv(data: list[dict]) -> None:
    ensure_dirs_and_files()
    df = pd.DataFrame(data)
    for col in AHA_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[AHA_COLUMNS]
    df.to_csv(AHA_FILE, index=False)
    log("AHA CSV created")


def convert_to_rqi(data: list[dict]) -> list[dict]:
    rqi_data = []
    for row in data:
        rqi_data.append({
            "LocationID": "116286",
            "LocationName": row.get("LocationName", ""),
            "UserID": row["EMAIL"],
            "FirstName": row["First Name"],
            "MiddleName": row["M"],
            "LastName": row["Last Name"],
            "Email": row["EMAIL"],
            "JobCode": "Student",
            "JobName": "Student",
            "HireDate": "",
            "Status": "Active",
            "DateOfBirth": "",
            "Gender": "",
            "YearsofExperiences": "",
            "ActiveDate": "",
            "InactiveDate": "",
            "Group": row["Course"],
        })
    return rqi_data


def save_rqi_csv(data: list[dict]) -> None:
    ensure_dirs_and_files()

    new_df = pd.DataFrame(data, columns=RQI_COLUMNS)

    if os.path.exists(RQI_FILE):
        try:
            old_df = pd.read_csv(RQI_FILE)
        except Exception:
            old_df = pd.DataFrame(columns=RQI_COLUMNS)
    else:
        old_df = pd.DataFrame(columns=RQI_COLUMNS)

    if new_df.empty and not old_df.empty:
        log("RQI CSV kept existing data")
        return

    combined = pd.concat([old_df, new_df], ignore_index=True)

    if not combined.empty:
        combined = combined.drop_duplicates(subset=["Email", "Group"], keep="last")

    for col in RQI_COLUMNS:
        if col not in combined.columns:
            combined[col] = ""

    combined = combined[RQI_COLUMNS]
    combined.to_csv(RQI_FILE, index=False)
    log("RQI CSV updated")


# =========================
# SFTP
# =========================
def upload_sftp() -> None:
    try:
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.put(RQI_FILE, SFTP_REMOTE_PATH)
        sftp.close()
        transport.close()
        log("SFTP upload successful")
    except Exception as e:
        log(f"SFTP error: {e}")


# =========================
# PROGRESS
# =========================
def load_progress() -> pd.DataFrame:
    ensure_dirs_and_files()
    try:
        df = pd.read_csv(PROGRESS_FILE)
    except EmptyDataError:
        df = pd.DataFrame(columns=PROGRESS_COLUMNS)
        df.to_csv(PROGRESS_FILE, index=False)
        return df
    except Exception:
        df = pd.DataFrame(columns=PROGRESS_COLUMNS)
        df.to_csv(PROGRESS_FILE, index=False)
        return df

    for col in PROGRESS_COLUMNS:
        if col not in df.columns:
            if col == "ReminderCount":
                df[col] = 0
            else:
                df[col] = ""

    if not df.empty and "Email" in df.columns:
        df = df[df["Email"].astype(str).apply(is_valid_email)].copy()
        save_progress(df)

    return df[PROGRESS_COLUMNS]


def save_progress(df: pd.DataFrame) -> None:
    ensure_dirs_and_files()
    for col in PROGRESS_COLUMNS:
        if col not in df.columns:
            if col == "ReminderCount":
                df[col] = 0
            else:
                df[col] = ""
    df = df[PROGRESS_COLUMNS]
    df.to_csv(PROGRESS_FILE, index=False)


def update_progress(students: list[dict]) -> None:
    df = load_progress()

    for s in students:
        email_value = s["EMAIL"]
        course = s["Course"]
        exists = ((df["Email"] == email_value) & (df["Course"] == course)).any()

        if not exists:
            df = pd.concat(
                [df, pd.DataFrame([{
                    "Email": email_value,
                    "Course": course,
                    "Progress": "NOT_STARTED",
                    "Feedback": "",
                    "LastReminderSent": "",
                    "ReminderCount": 0,
                    "ReminderStatus": "NOT_SENT",
                }])],
                ignore_index=True,
            )

    save_progress(df)


# =========================
# EMAIL ACTIONS
# =========================
def send_location_email(token: str, student: dict) -> None:
    location_key = str(student.get("LocationName", "")).upper()
    tpl = LOCATION_TEMPLATES.get(location_key)
    if not tpl:
        log(f"No location template found for: {location_key}")
        return

    send_graph_email(token, student["EMAIL"], tpl["subject"], tpl["body"])


def should_send_reminder(row: pd.Series) -> bool:
    status = str(row.get("ReminderStatus", "NOT_SENT")).strip().upper()
    count = str(row.get("ReminderCount", "0")).strip()
    last_sent = str(row.get("LastReminderSent", "")).strip()
    progress = str(row.get("Progress", "")).strip().upper()

    try:
        count_int = int(float(count))
    except Exception:
        count_int = 0

    if status == "BOUNCED":
        return False
    if progress == "COMPLETED":
        return False
    if count_int >= 3:
        return False

    if not last_sent:
        return True

    try:
        last_dt = pd.to_datetime(last_sent)
        now_dt = pd.Timestamp.now()
        hours_passed = (now_dt - last_dt).total_seconds() / 3600.0
        return hours_passed >= 24
    except Exception:
        return True


def send_smart_reminder(token: str, row: pd.Series) -> bool:
    email_value = str(row["Email"]).strip()
    if not is_valid_email(email_value):
        log(f"Skipping invalid reminder email: {email_value}")
        return False

    course = str(row["Course"])
    progress = str(row["Progress"])
    feedback = str(row["Feedback"])

    if progress == "NOT_STARTED":
        msg = f"Please sign in and start your {course} course."
    elif progress == "IN_PROGRESS":
        msg = f"You started {course}. Please complete it."
    elif progress == "COMPLETED" and not feedback:
        msg = f"Congrats. Please share your feedback for {course}."
    elif any(x in feedback.lower() for x in ["bad", "poor", "negative"]):
        msg = "We value your feedback. Please tell us how we can improve."
    else:
        msg = "Great job. Please consider your next course with us."

    try:
        send_graph_email(token, email_value, f"CPR Reminder - {course}", msg)
        return True
    except Exception as e:
        log(f"Reminder send failed for {email_value}: {e}")
        return False


def process_reminders(token: str) -> None:
    df = load_progress()

    if df.empty:
        return

    changed = False

    for idx, row in df.iterrows():
        if not should_send_reminder(row):
            continue

        success = send_smart_reminder(token, row)

        if success:
            current_count = row.get("ReminderCount", 0)
            try:
                current_count = int(float(current_count))
            except Exception:
                current_count = 0

            df.at[idx, "LastReminderSent"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            df.at[idx, "ReminderCount"] = current_count + 1
            df.at[idx, "ReminderStatus"] = "SENT"
            changed = True

    if changed:
        save_progress(df)
        log("Reminder status updated")


# =========================
# GOOGLE SHEET
# =========================
def upload_to_google_sheet() -> None:
    if not GSPREAD_AVAILABLE:
        log("Google Sheet update skipped: gspread not installed.")
        return
    if not os.path.exists("credentials.json"):
        log("Google Sheet update skipped: credentials.json not found.")
        return
    if not os.path.exists(RQI_FILE):
        log("Google Sheet update skipped: preprod_cl.csv not found.")
        return

    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1

        df = pd.read_csv(RQI_FILE)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())
        log("Google Sheet updated")
    except Exception as e:
        log(f"Google Sheet update error: {e}")


# =========================
# CLEANUP
# =========================
def cleanup_bad_data() -> None:
    ensure_dirs_and_files()

    if os.path.exists(HISTORY_FILE):
        cleaned = []
        with open(HISTORY_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("|")
                if parts and is_valid_email(parts[0]):
                    cleaned.append(line)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for line in cleaned:
                f.write(line + "\n")

    try:
        df = pd.read_csv(PROGRESS_FILE)
        for col in PROGRESS_COLUMNS:
            if col not in df.columns:
                if col == "ReminderCount":
                    df[col] = 0
                else:
                    df[col] = ""
        if "Email" in df.columns:
            df = df[df["Email"].astype(str).apply(is_valid_email)].copy()
            save_progress(df)
    except Exception:
        pd.DataFrame(columns=PROGRESS_COLUMNS).to_csv(PROGRESS_FILE, index=False)


# =========================
# MAIN
# =========================
def main() -> None:
    ensure_dirs_and_files()
    cleanup_bad_data()
    log("Automation started")

    token = get_token()

    while True:
        try:
            emails = fetch_emails(token, max_messages=5000)
            aha_data = extract_aha_data(emails)
            new_students, all_students = filter_new(aha_data)

            update_status(len(new_students), len(all_students))
            log(f"New students: {len(new_students)}")
            log(f"Total students: {len(all_students)}")

            if new_students:
                auto_accept_aha_students(new_students)

            save_aha_csv(all_students)

            if new_students:
                rqi_data = convert_to_rqi(new_students)
                save_rqi_csv(rqi_data)
                upload_sftp()
                update_progress(new_students)
                upload_to_google_sheet()

                for student in new_students:
                    send_location_email(token, student)
                    student["Reminder email sent"] = "Yes"
            else:
                log("No new students")

            process_reminders(token)

        except Exception as e:
            log(f"Error: {e}")

        log(f"Waiting {POLL_SECONDS} seconds...\n")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()