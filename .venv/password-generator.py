import random
import string
import os
import datetime
import sqlite3
import schedule
import time
from cryptography.fernet import Fernet

LOG_FILE = "password_generator_log.txt"

# Logging Function
def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# Encryption functions
def generate_key():
    return Fernet.generate_key()

def save_key(key, filename="secret.key"):
    with open(filename, "wb") as f:
        f.write(key)

def load_key(filename="secret.key"):
    if not os.path.exists(filename):
        key = generate_key()
        save_key(key)
        log("Generated and saved new encryption key.")
    with open(filename, "rb") as f:
        return f.read()

def encrypt_password(password, key):
    return Fernet(key).encrypt(password.encode()).decode()

def decrypt_password(password, key):
    return Fernet(key).decrypt(password.encode()).decode()

# Generation of Password
def generate_password(min_length=8, use_upper=True, use_lower=True, use_digits=True, use_symbols=True):
    characters = ""
    if use_upper:
        characters += string.ascii_uppercase
    if use_lower:
        characters += string.ascii_lowercase
    if use_digits:
        characters += string.digits
    if use_symbols:
        characters += string.punctuation
    if not characters:
        raise ValueError("No characters provided.")
    return "".join([random.choice(characters) for _ in range(random.randint(min_length,16))])

#SQLite DB Functions
def initialize_db():
    conn = sqlite3.connect("passwords.db")
    curr = conn.cursor()
    curr.execute('''CREATE TABLE IF NOT EXISTS passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT,
                    encrypted_password TEXT,
                    month TEXT
                    )''')
    conn.commit()
    conn.close()
    log("Initialized SQLite database.")

def store_password(label, encrypted_password, month):
    conn = sqlite3.connect("passwords.db")
    curr = conn.cursor()
    curr.execute("INSERT INTO passwords (label, encrypted_password, month) VALUES (?, ?, ?)",
                 (label, encrypted_password, month))
    conn.commit()
    conn.close()
    log(f"Stored password for {label} ({month}).")

def monthly_password_exists(month):
    conn = sqlite3.connect("passwords.db")
    curr = conn.cursor()
    curr.execute("SELECT COUNT(*) FROM passwords WHERE month = ?", (month,))
    count = curr.fetchone()[0]
    conn.close()
    return count > 0

#Scheduled Task
def run_monthly_password_generator():
    try:
        key = load_key()
        initialize_db()

        now = datetime.datetime.now()
        month_label = now.strftime("%B %Y")

        if monthly_password_exists(month_label):
            log(f"Password already exists for {month_label}. Skipping.")
            return

        password = generate_password(min_length=8, use_upper=True, use_lower=True, use_digits=True, use_symbols=False)
        encrypted_pwd = encrypt_password(password, key)

        store_password("Default Password", encrypted_pwd, month_label)
        log(f"[SUCCESS] Password stored in database for {month_label}: {encrypted_pwd}")

    except Exception as e:
        log(f"[ERROR] {e}")


#Schedule to run daily at 12:00 AM
schedule.every().day.at("00:00").do(lambda:
    run_monthly_password_generator() if datetime.datetime.now().day == 1 else None
)

log("[INFO] Scheduler is running. Waiting for the scheduled task...")
while True:
    schedule.run_pending()
    time.sleep(60)

