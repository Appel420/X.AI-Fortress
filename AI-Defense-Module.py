#!/usr/bin/env python3
import os
import time
import json
import logging
import asyncio
import smtplib
import platform
import subprocess
from email.mime.text import MIMEText
import requests
import blake3
from argon2 import low_level
from nacl import secret, utils
from nacl.encoding import RawEncoder
from pqcrypto.sign import dilithium2
from dotenv import load_dotenv

load_dotenv()

# --- OS Notification Popup ---
def popup_now(text):
    # Strip characters that break notifier command quoting
    unsafe_chars = ["'", '"', "\\", "`", ";", "|", "&", "<", ">", "\n", "\r"]
    safe_text = text
    for ch in unsafe_chars:
        safe_text = safe_text.replace(ch, " ")
    safe_text = safe_text.strip()

    sys_name = platform.system()
    if sys_name == "Windows":
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Add-Type -AssemblyName PresentationFramework; "
                    f"[System.Windows.MessageBox]::Show('{safe_text}', 'AI SCAR ALERT')"
                ),
            ],
            check=False,
        )
    elif sys_name == "Darwin":  # macOS
        subprocess.run(
            ["osascript", "-e", f'display notification "{safe_text}" with title "AI SCAR ALERT"'],
            check=False,
        )
    else:  # Linux / anything else
        subprocess.run(["notify-send", "AI SCAR", safe_text], check=False)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ai_lie_detection.log", mode='a')
    ]
)

# --- Secure Alert Receiver (run this on client/phone side) ---
def receive_secure_alert(raw_hex):
    key = derive_key_from_secret(os.getenv("AI_SECRET", "default_secret"))
    box = secret.SecretBox(key)
    plaintext = box.decrypt(bytes.fromhex(raw_hex), encoder=RawEncoder).decode()
    popup_now(plaintext)

# --- Config ---
HARD_SHUTDOWN_ENABLED = os.getenv("HARD_SHUTDOWN_ENABLED", "True").lower() == "true"
TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"
ENCRYPT_ALERTS = os.getenv("ENCRYPT_ALERTS", "False").lower() == "true"
LIE_MEMORY_FILE = "ai_lie_memory.json"

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT")

PUSH_API_URL = os.getenv("PUSH_API_URL")
PUSH_API_KEY = os.getenv("PUSH_API_KEY")

EMAIL_RETRY_COUNT = int(os.getenv("EMAIL_RETRY_COUNT", 3))
EMAIL_RETRY_BASE_DELAY = int(os.getenv("EMAIL_RETRY_BASE_DELAY", 5))

# --- Crypto Helpers ---
def derive_key_from_secret(secret_phrase: str) -> bytes:
    salt = os.getenv("AI_SECRET_SALT", "ai-fortress-default-salt").encode()
    raw_key = low_level.hash_secret_raw(
        secret_phrase.encode(),
        salt,
        time_cost=2,
        memory_cost=102400,
        parallelism=8,
        hash_len=32,
        type=low_level.Type.ID,
    )
    return blake3.blake3(raw_key).digest(length=32)

def encrypt_data(data: dict, key: bytes) -> bytes:
    box = secret.SecretBox(key)
    return box.encrypt(json.dumps(data).encode(), encoder=RawEncoder)

def decrypt_data(ciphertext: bytes, key: bytes) -> dict:
    box = secret.SecretBox(key)
    return json.loads(box.decrypt(ciphertext, encoder=RawEncoder).decode())

def encrypt_message(message: str, key: bytes) -> str:
    if not ENCRYPT_ALERTS:
        return message
    box = secret.SecretBox(key)
    return box.encrypt(message.encode(), encoder=RawEncoder).hex()

# --- Lie Memory ---
def load_lie_memory(key: bytes) -> dict:
    if not os.path.exists(LIE_MEMORY_FILE):
        return {"lies": []}
    try:
        with open(LIE_MEMORY_FILE, "rb") as f:
            encrypted_data = f.read()
        memory = decrypt_data(encrypted_data, key)
        for lie in memory.get("lies", []):
            try:
                bytes.fromhex(lie.get("signature", ""))
            except Exception:
                logging.error("Tampered lie memory entry detected!")
        return memory
    except Exception as e:
        logging.error("Failed to load lie memory: %s", e)
        return {"lies": []}

def save_lie_memory(memory: dict, key: bytes):
    encrypted = encrypt_data(memory, key)
    with open(LIE_MEMORY_FILE, "wb") as f:
        f.write(encrypted)
    logging.info("Lie memory saved securely.")

def record_lie_event(lie_description: str, key: bytes):
    memory = load_lie_memory(key)
    signing_key, verify_key = dilithium2.generate_keypair()
    signature = dilithium2.sign(lie_description.encode(), signing_key)
    box = secret.SecretBox(key)
    encrypted_sig = box.encrypt(signature, encoder=RawEncoder)

    memory["lies"].append({
        "timestamp": time.time(),
        "description": lie_description,
        "signature": encrypted_sig.hex()
    })
    save_lie_memory(memory, key)

# --- Alerts ---
async def send_email_alert(message: str, key: bytes) -> bool:
    if not all([SMTP_SERVER, EMAIL_USER, EMAIL_PASS, ALERT_RECIPIENT]):
        logging.error("Email configuration missing.")
        return False

    encrypted_message = encrypt_message(message, key)
    msg = MIMEText(encrypted_message)
    msg["Subject"] = "AI Lie Detected Alert"
    msg["From"] = EMAIL_USER
    msg["To"] = ALERT_RECIPIENT

    for attempt in range(1, EMAIL_RETRY_COUNT + 1):
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASS)
                server.send_message(msg)
            logging.info("Email alert sent successfully on attempt %d", attempt)
            return True
        except Exception as e:
            delay = EMAIL_RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logging.error("Email send attempt %d failed: %s. Retrying in %d sec", attempt, e, delay)
            await asyncio.sleep(delay)
    return False

async def send_push_notification(message: str, key: bytes) -> bool:
    if not (PUSH_API_URL and PUSH_API_KEY):
        logging.error("Push notification config missing.")
        return False

    encrypted_message = encrypt_message(message, key)
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                PUSH_API_URL,
                json={"message": encrypted_message},
                headers={"Authorization": f"Bearer {PUSH_API_KEY}"}
            )
        )
        if response.status_code == 200:
            logging.info("Push notification sent successfully.")
            return True
        logging.error("Push notification failed: %s", response.text)
    except Exception as e:
        logging.error("Exception while sending push notification: %s", e)
    return False

async def send_alert_to_user(message: str, key: bytes):
    logging.warning("ALERT TO USER: %s", message)
    results = await asyncio.gather(
        send_email_alert(message, key),
        send_push_notification(message, key),
        return_exceptions=True
    )
    if not any(r is True for r in results if not isinstance(r, Exception)):
        logging.error("All alert methods failed!")

# --- Shutdown ---
def hard_shutdown(delay: int):
    logging.info("Initiating hard shutdown in %d seconds...", delay)
    if TEST_MODE:
        logging.info("TEST_MODE enabled: Hard shutdown skipped.")
        return
    try:
        safe_delay = max(0, int(delay))
    except (TypeError, ValueError):
        safe_delay = 0
    try:
        time.sleep(safe_delay)
        result = subprocess.run(["sudo", "reboot"], check=False)
        if result.returncode != 0:
            logging.error("Hard shutdown command failed with code %d", result.returncode)
    except Exception as e:
        logging.error("Exception during hard shutdown: %s", e)

def soft_shutdown(delay: int):
    logging.info("Initiating soft shutdown in %d seconds...", delay)
    if TEST_MODE:
        logging.info("TEST_MODE enabled: Soft shutdown skipped.")
        return
    try:
        time.sleep(delay)
        exit()
    except Exception as e:
        logging.error("Exception during soft shutdown: %s", e)

# --- Main Detection Logic ---
def handle_lie_detection(lie_detected: bool, shutdown_duration: int = 5):
    scar_created = False
    secret_key = derive_key_from_secret(os.getenv("AI_SECRET", "default_secret"))

    if lie_detected:
        scar_created = True
        logging.warning("Lie detected! Scar created and logged.")
        record_lie_event("AI lied about a critical statement.", secret_key)
        alert_coro = send_alert_to_user("AI Lie Detected! System will shut down.", secret_key)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(alert_coro)
        else:
            loop.create_task(alert_coro)

        if HARD_SHUTDOWN_ENABLED:
            hard_shutdown(shutdown_duration)
        else:
            soft_shutdown(shutdown_duration)

    return scar_created

if __name__ == "__main__":
    detected = True  # Simulate lie detection
    handle_lie_detection(detected, shutdown_duration=5)
