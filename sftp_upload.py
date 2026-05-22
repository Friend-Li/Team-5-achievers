import paramiko
from config import *

def upload_file(local_file):
    try:
        print("🔌 Connecting to SFTP...")

        transport = paramiko.Transport((HOST, PORT))
        transport.connect(username=USER, password=PASS)

        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_path = f"{PATH}/{FILE}"

        print("⬆️ Uploading file...")
        sftp.put(local_file, remote_path)

        sftp.close()
        transport.close()

        print("✅ Upload Successful!")

    except Exception as e:
        print("❌ Upload Failed:", str(e))