import logging
import os

# Create logs folder if not exists
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_info(message):
    print(message)
    logging.info(message)

def log_error(message):
    print(message)
    logging.error(message)