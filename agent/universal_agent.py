import time
import requests
import os
import sys
import platform
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ================= CONFIGURATION =================
# Replace with your Render URL
BACKEND_URL = "https://YOUR-APP-NAME.onrender.com/alert"
USER_EMAIL = "student@test.com"

# FOLDERS TO PROTECT
HOME = os.path.expanduser("~")
TARGET_FOLDER = os.path.join(HOME, "Desktop", "SecureFiles") 
HONEYPOT_NAME = "!000_BAIT_FILE.docx"
# =================================================

class OSManager:
    """Handles OS-specific commands for Windows, Linux, and Mac"""
    def __init__(self):
        self.os_type = platform.system() # 'Windows', 'Linux', or 'Darwin' (Mac)
        print(f"🖥️  OS Detected: {self.os_type}")

    def hide_file(self, path):
        """Hides the honeypot file so users don't see it"""
        if self.os_type == "Windows":
            subprocess.run(f'attrib +h "{path}"', shell=True)
        else:
            # On Linux/Mac, files starting with '.' are hidden automatically
            # Our file starts with '!', so we can rename it or just leave it as bait.
            pass 

    def lock_folder(self, path):
        """Makes folder Read-Only to stop Ransomware encryption"""
        print(f"🔒 Locking folder: {path}")
        try:
            if self.os_type == "Windows":
                # Deny Write access to Everyone
                subprocess.run(f'icacls "{path}" /deny Everyone:(W)', shell=True)
            else:
                # Linux/Mac: Remove Write permissions (chmod 555)
                subprocess.run(f'chmod 555 "{path}"', shell=True)
            return True
        except Exception as e:
            print(f"❌ Lock failed: {e}")
            return False

    def cut_network(self):
        """Simulates a Network Kill Switch to stop data theft"""
        print("✂️  Cutting Network Connection...")
        try:
            if self.os_type == "Windows":
                subprocess.run("ipconfig /release", shell=True)
            else:
                # Linux/Mac require sudo for network changes, so we simulate this for safety
                print("⚠️  [SIMULATION] Network cut command executed (Root required on Linux/Mac).")
        except Exception as e:
            print(f"Network cut failed: {e}")

class IntelligentHandler(FileSystemEventHandler):
    def __init__(self, os_manager, honeypot_path):
        self.osm = os_manager
        self.honeypot_path = honeypot_path
        self.triggered = False

    def activate_defense(self):
        if self.triggered: return
        self.triggered = True

        print("\n" + "!"*40)
        print("🚨 HONEYPOT TRIGGERED! MALWARE DETECTED!")
        print("!"*40)

        # 1. Active Response
        self.osm.cut_network()
        folder = os.path.dirname(self.honeypot_path)
        self.osm.lock_folder(folder)

        # 2. Send Alert
        self.send_alert("RANSOMWARE_BLOCKED")

        # 3. User Notification
        print("✅ Threat Contained. System Locked.")

    def send_alert(self, event_type, filename="Honeypot"):
        payload = {
            "user_email": USER_EMAIL,
            "os": self.osm.os_type,  # <--- Sending OS info to Dashboard
            "file": filename,
            "event": event_type,
            "timestamp": time.time()
        }
        try:
            requests.post(BACKEND_URL, json=payload, timeout=3)
            print("📡 Alert sent to Dashboard.")
        except:
            print("⚠️  Could not reach Dashboard (Internet might be cut).")

    def on_modified(self, event):
        if event.src_path == self.honeypot_path: self.activate_defense()
    def on_deleted(self, event):
        if event.src_path == self.honeypot_path: self.activate_defense()

# --- MAIN SETUP ---
if __name__ == "__main__":
    if not os.path.exists(TARGET_FOLDER):
        os.makedirs(TARGET_FOLDER)
    
    # Create Bait File
    bait_path = os.path.join(TARGET_FOLDER, HONEYPOT_NAME)
    with open(bait_path, 'w') as f:
        f.write("This file is a trap.")
    
    # Initialize Manager
    os_manager = OSManager()
    os_manager.hide_file(bait_path)

    # Start Watchdog
    observer = Observer()
    handler = IntelligentHandler(os_manager, bait_path)
    observer.schedule(handler, TARGET_FOLDER, recursive=False)
    observer.start()

    print(f"\n🛡️  Agent Running on {os_manager.os_type}")
    print(f"🍯 Honeypot Active at: {TARGET_FOLDER}")
    print("---------------------------------------")

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 Agent Stopped.")
        # Cleanup instructions
        if os_manager.os_type == "Windows":
            print("👉 To restore internet: run 'ipconfig /renew'")
            print(f"👉 To unlock folder: run 'icacls \"{TARGET_FOLDER}\" /reset'")
        else:
            print(f"👉 To unlock folder: run 'chmod 755 \"{TARGET_FOLDER}\"'")
    observer.join()
