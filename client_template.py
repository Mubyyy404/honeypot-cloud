import time
import os
import requests
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# --- SERVER INJECTS DATA HERE ---
API_KEY = "[[API_KEY_PLACEHOLDER]]"
SERVER_URL = "[[SERVER_URL_PLACEHOLDER]]"
# --------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HONEY_DIR = os.path.join(BASE_DIR, "honeypot_monitor")

print(f"[*] Starting Ransomware Monitor Agent")
print(f"[*] ID: {API_KEY}")
print(f"[*] Connecting to: {SERVER_URL}")

if not os.path.exists(HONEY_DIR):
    os.makedirs(HONEY_DIR)
    with open(os.path.join(HONEY_DIR, "do_not_touch.txt"), "w") as f:
        f.write("CONFIDENTIAL DATA. Do not modify.")

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
        
        print(f"[!] THREAT DETECTED: {event_type} - {filename}")
        
        payload = {
            "api_key": API_KEY,
            "event": event_type,
            "file": filename,
            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            r = requests.post(f"{SERVER_URL}/api/report", json=payload)
            if r.status_code == 200:
                print(" -> Alert sent to HQ successfully.")
            else:
                print(f" -> Server Error: {r.status_code}")
        except Exception as e:
            print(f" -> Connection Failed: {e}")

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(AgentHandler(), path=HONEY_DIR, recursive=False)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
