import schedule
import time
from datetime import datetime

from csv_generator import generate_csv
from sftp_upload import upload_file


def job():
    print("\n==============================")
    print(f"⏱ Job started at {datetime.now()}")

    try:
        file_path = generate_csv()

        if file_path:
            upload_file(file_path)
        else:
            print("⏭ Skipping upload (no new data)")

        print(f"✅ Job completed at {datetime.now()}")

    except Exception as e:
        print("❌ Job failed:", str(e))


# TEST → change to 15 later
schedule.every(15).minutes.do(job)

print("🚀 Scheduler started...")

job()

while True:
    schedule.run_pending()
    time.sleep(1)