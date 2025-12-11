import time
import requests
import os
import platform
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ================= CONFIGURATION =================
# TODO: PASTE YOUR RENDER URL HERE (Ensure it ends with /alert)
BACKEND_URL = "https://YOUR-APP-NAME.onrender.com/alert"

# TODO: SET YOUR EMAIL (Must match the one you login with)
USER_EMAIL = "student@test.com"

# Setup Paths
HOME = os.path.expanduser("~")
TARGET_FOLDER = os.path.join(HOME, "Desktop", "SecureFiles") 
HONEYPOT_NAME = "!000_BAIT_FILE.docx"
# =================================================

class SecurityAgent:
    def __init__(self):
        self.os_type = platform.system()
        print(f"🖥️  OS DETECTED: {self.os_type}")

    def setup_honeypot(self):
        if not os.path.exists(TARGET_FOLDER):
            os.makedirs(TARGET_FOLDER)
        
        path = os.path.join(TARGET_FOLDER, HONEYPOT_NAME)
        with open(path, 'w') as f:
            f.write("This is a trap file. Do not delete.")
        
        # Hide the file on Windows
        if self.os_type == "Windows":
            subprocess.run(f'attrib +h "{path}"', shell=True)
        
        return path

    def kill_switch(self, folder_path):
        print("\n⚡ ENGAGING KILL SWITCH...")
        
        # 1. Lock Folder
        try:
            if self.os_type == "Windows":
                cmd = f'icacls "{folder_path}" /deny Everyone:(W)'
                subprocess.run(cmd, shell=True)
            else:
                cmd = f'chmod 555 "{folder_path}"'
                subprocess.run(cmd, shell=True)
            print("🔒 Folder LOCKED (Read-Only).")
        except Exception as e:
            print(f"❌ Lock Failed: {e}")

        # 2. Cut Network (Simulation)
        try:
            if self.os_type == "Windows":
                print("✂️  Cutting Network Adapter...")
                subprocess.run("ipconfig /release", shell=True)
            else:
                print("✂️  [SIMULATION] Network Cut (Requires Root).")
        except:
            pass

class ThreatHandler(FileSystemEventHandler):
    def __init__(self, agent, bait_path):
        self.agent = agent
        self.bait_path = bait_path
        self.triggered = False

    def on_any_event(self, event):
        # We trigger if the bait file is Modified or Deleted
        if not self.triggered and event.src_path == self.bait_path:
            if event.event_type in ["deleted", "modified"]:
                self.trigger_defense()

    def trigger_defense(self):
        self.triggered = True
        print("\n🚨 HONEYPOT TRIGGERED! RANSOMWARE DETECTED!")
        
        # Active Response
        self.agent.kill_switch(os.path.dirname(self.bait_path))
        
        # Send Alert
        self.send_alert()

    def send_alert(self):
        payload = {
            "user_email": USER_EMAIL,
            "os": self.agent.os_type,
            "file": HONEYPOT_NAME,
            "event": "RANSOMWARE_BLOCKED",
            "timestamp": time.time()
        }
        try:
            requests.post(BACKEND_URL, json=payload, timeout=5)
            print("📡 Alert sent to SOC Dashboard.")
        except:
            print("⚠️  Dashboard unreachable (Network likely cut).")

if __name__ == "__main__":
    agent = SecurityAgent()
    bait_path = agent.setup_honeypot()

    observer = Observer()
    handler = ThreatHandler(agent, bait_path)
    observer.schedule(handler, TARGET_FOLDER, recursive=False)
    observer.start()

    print(f"🛡️  Protection Active at: {TARGET_FOLDER}")
    print("-----------------------------------------")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 Agent Stopped.")
        if agent.os_type == "Windows":
            print("👉 To restore internet: ipconfig /renew")
            print(f"👉 To unlock folder: icacls \"{TARGET_FOLDER}\" /reset")
    observer.join()
