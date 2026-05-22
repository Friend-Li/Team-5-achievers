import os
import re
import extract_msg

def read_dropbox_emails():
    folder = "emails"
    students = []

    for file in os.listdir(folder):
        if file.endswith(".msg"):
            file_path = os.path.join(folder, file)

            try:
                msg = extract_msg.Message(file_path)
                subject = msg.subject
                body = msg.body

                student = extract_data(subject, body)

                if student:
                    students.append(student)

            except Exception as e:
                print(f"❌ Error reading {file}: {e}")

    print(f"📨 Extracted {len(students)} valid students")
    return students


def extract_data(subject, body):
    # ✅ Extract name from subject (inside parentheses)
    name_match = re.search(r"\((.*?)\)", subject)

    if not name_match:
        return None

    full_name = name_match.group(1).strip()
    name_parts = full_name.split()

    if len(name_parts) < 2:
        return None

    first_name = name_parts[0]
    last_name = name_parts[-1]

    # ✅ Extract email from body
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", body)

    valid_email = None

    for email in emails:
        email_lower = email.lower()

        if (
            "no-reply" in email_lower or
            "acuityscheduling" in email_lower or
            "cprlifeline" in email_lower or
            "info@" in email_lower
        ):
            continue

        valid_email = email
        break

    if not valid_email:
        return None

    return {
    "FirstName": first_name,
    "LastName": last_name,
    "Email": valid_email,
    "Subject": subject
}