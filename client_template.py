import time
import os
import requests
import platform
import socket
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# --- INJECTED BY SERVER ---
API_KEY = "[[API_KEY_PLACEHOLDER]]"
SERVER_URL = "[[SERVER_URL_PLACEHOLDER]]"
# --------------------------

HOSTNAME = socket.gethostname()
OS_TYPE = f"{platform.system()} {platform.release()}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HONEY_DIR = os.path.join(BASE_DIR, "honeypot_monitor")

print(f"[*] -- SENTINEL AGENT V3.0 --")
print(f"[*] Identity: {API_KEY}")
print(f"[*] Device: {HOSTNAME} ({OS_TYPE})")
print(f"[*] Server: {SERVER_URL}")

if not os.path.exists(HONEY_DIR):
    os.makedirs(HONEY_DIR)
    with open(os.path.join(HONEY_DIR, "classified_data.txt"), "w") as f:
        f.write("CONFIDENTIAL: Do not modify this file.")

class AgentHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory: self.report("Modified", event.src_path)
    def on_created(self, event):
        if not event.is_directory: self.report("Created", event.src_path)
    def on_deleted(self, event):
        if not event.is_directory: self.report("Deleted", event.src_path)

    def report(self, event_type, path):
        filename = os.path.basename(path)
        if filename.startswith("."): return
        
        print(f"[!] ALERT: {event_type} - {filename}")
        
        # FIX: Use datetime.now() instead of utcnow() to get LOCAL time
        local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        payload = {
            "api_key": API_KEY,
            "event": event_type,
            "file": filename,
            "device": HOSTNAME,
            "os": OS_TYPE,
            "time": local_time  # <--- Sending Local Time now
        }
        
        try:
            requests.post(f"{SERVER_URL}/api/report", json=payload, timeout=5)
        except Exception as e:
            print(f" [X] Connection Failed: {e}")

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(AgentHandler(), path=HONEY_DIR, recursive=False)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
