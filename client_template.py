import time
import os
import requests
import platform
import socket
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# --- CONFIG (Injected by Server) ---
API_KEY = "[[API_KEY_PLACEHOLDER]]"
SERVER_URL = "[[SERVER_URL_PLACEHOLDER]]"
# -----------------------------------

HOSTNAME = socket.gethostname()
OS_TYPE = f"{platform.system()} {platform.release()}"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HONEY_DIR = os.path.join(BASE_DIR, "Sentinel_Protected_Folder")
TRAP_FILE = os.path.join(HONEY_DIR, "important_passwords.txt")

print(f"[*] SENTINEL AGENT ACTIVATED")
print(f"[*] Monitoring Device: {HOSTNAME}")
print(f"[*] Target File: {TRAP_FILE}")
print(f"[*] Status: ARMED AND WATCHING...")

# 1. Create the Trap Folder
if not os.path.exists(HONEY_DIR):
    os.makedirs(HONEY_DIR)

# 2. Create the Trap File (if missing)
if not os.path.exists(TRAP_FILE):
    with open(TRAP_FILE, "w") as f:
        f.write("CONFIDENTIAL PASSWORDS\n\nFacebook: pass123\nGmail: secret456\n\nDO NOT MODIFY THIS FILE.")
    print("[+] Trap file created.")

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
        
        print(f"\n[!!!] ALERT TRIGGERED: {event_type} on {filename}")
        
        payload = {
            "api_key": API_KEY,
            "event": event_type,
            "file": filename,
            "device": HOSTNAME,
            "os": OS_TYPE,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            requests.post(f"{SERVER_URL}/api/report", json=payload, timeout=5)
            print(" -> Alert sent to Server & Email.")
        except:
            print(" -> Failed to reach server (Check Internet).")

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(AgentHandler(), path=HONEY_DIR, recursive=False)
    observer.start()
    
    # Keep the window open so user knows it's running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
