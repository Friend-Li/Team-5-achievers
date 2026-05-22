from dotenv import load_dotenv
import os

load_dotenv()

HOST = os.getenv("SFTP_HOST")
PORT = int(os.getenv("SFTP_PORT"))
USER = os.getenv("SFTP_USER")
PASS = os.getenv("SFTP_PASS")
PATH = os.getenv("SFTP_PATH")
FILE = os.getenv("FILE_NAME")