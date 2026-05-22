import pandas as pd
import os
from google_sheets_reader import read_google_sheet
from delta_processor import get_new_records


def get_group(course):
    course = str(course).lower()

    if "bls" in course:
        return "BLS"
    elif "acls" in course:
        return "ACLS"
    elif "pals" in course:
        return "PALS"

    return "Default"


def transform_to_rqi_format(data):
    transformed = []

    for row in data:
        email = row.get("EMAIL", "")
        first_name = row.get("First Name", "")
        last_name = row.get("Last Name", "")
        course = row.get("Course", "")

        # ✅ filter invalid rows
        if not email or "@" not in email:
            continue

        record = {
            "LocationID": "116286",
            "LocationName": "CPR Lifeline",
            "UserID": email,
            "FirstName": first_name,
            "MiddleName": "",
            "LastName": last_name,
            "Email": email,
            "JobCode": "Student",
            "JobName": "Student",
            "HireDate": "",
            "Status": "Active",
            "DateOfBirth": "",
            "Gender": "",
            "YearsofExperiences": "",
            "ActiveDate": "",
            "InactiveDate": "",
            "Group": get_group(course)
        }

        transformed.append(record)

    return transformed


def generate_csv():
    os.makedirs("data", exist_ok=True)

    data = read_google_sheet()

    if not data:
        print("⚠️ No data from Google Sheets")
        return None

    transformed_data = transform_to_rqi_format(data)

    df_new = get_new_records(transformed_data)

    if df_new.empty:
        print("⚠️ No NEW records")
        return None

    file_path = "data/preprod_cl.csv"
    df_new.to_csv(file_path, index=False)

    print("✅ RQI CSV Created from AHA Sheet")

    return file_path