import cv2
import mediapipe as mp
import time
import tkinter as tk
import platform
import json
import os
import sys
import socket
import datetime
import warnings

# Suppress the deprecation warning from Google Protobuf / MediaPipe
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.symbol_database")

lock_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    lock_socket.bind(('127.0.0.1', 47123))
except socket.error:
    print("Enforcer is already running in the background. Exiting duplicate.")
    sys.exit()

CONFIG_FILE = "posture_config.json"

current_config = {
    "is_active": False,
    "grace_time": 10, 
    "penalty_time": 10,
    "use_schedule": False,
    "schedule_start": "09:00",
    "schedule_end": "17:00",
    "slouch_threshold": 0.15,
    "close_threshold": 0.60,
    "min_confidence": 0.7
}

def load_config():
    global current_config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                current_config.update(json.load(f))
        except Exception:
            pass 

def is_within_schedule():
    """Checks if the current time falls within the configured schedule window"""
    if not current_config.get("use_schedule", False):
        return True
    
    try:
        now = datetime.datetime.now().time()
        start = datetime.datetime.strptime(current_config["schedule_start"], "%H:%M").time()
        end = datetime.datetime.strptime(current_config["schedule_end"], "%H:%M").time()
        
        if start <= end:
            return start <= now <= end
        else:
            return start <= now or now <= end
    except:
        return True 

cap = None
pose = None

is_showing_warning = False
punishment_served = False
bad_posture_start_time = None
good_posture_start_time = None 
recovery_start_time = None 
last_recovery_time = 0  
consecutive_strikes = 0


root = tk.Tk()
if platform.system() == "Darwin": root.update_idletasks()
root.attributes('-fullscreen', True)
root.attributes('-topmost', True)
root.configure(bg='black')
root.attributes('-alpha', 0.0) 
root.withdraw()

warning_label = tk.Label(root, text="", font=("Helvetica", 64, "bold"), fg="red", bg="black")
warning_label.pack(expand=True)

def dismiss_warning():
    global is_showing_warning, punishment_served, bad_posture_start_time
    global good_posture_start_time, recovery_start_time, last_recovery_time, consecutive_strikes
    
    root.grab_release()
    for i in range(10, -1, -1):
        root.attributes('-alpha', (i / 10.0) * 0.95)
        root.update()
        time.sleep(0.01)
        
    root.withdraw() 
    dismiss_btn.pack_forget() 
    
    is_showing_warning = False
    punishment_served = False
    bad_posture_start_time = None 
    good_posture_start_time = None 
    recovery_start_time = None
    last_recovery_time = time.time()
    
    if consecutive_strikes >= 3:
        consecutive_strikes = 0

dismiss_btn = tk.Button(root, text="", font=("Helvetica", 24, "bold"), bg="white", fg="black", padx=20, pady=10, command=dismiss_warning)
escape_info = tk.Label(root, text="Press ESC to resume (Disabled during penalty)", font=("Helvetica", 14), fg="#555555", bg="black")
escape_info.pack(side="bottom", pady=30)

root.protocol("WM_DELETE_WINDOW", lambda: None)
root.bind("<Alt-F4>", lambda e: "break")

def handle_escape(event=None):
    if is_showing_warning:
        if not punishment_served:
            escape_info.config(text="🚫 Cannot resume during penalty! Sit up straight.", fg="red")
        else:
            dismiss_warning()
    return "break"
root.bind("<Escape>", handle_escape)

def trigger_warning(violation_text):
    global is_showing_warning, punishment_served
    is_showing_warning = True
    punishment_served = False
    
    warning_label.config(text=violation_text)
    dismiss_btn.config(text="Sit up straight to start unlock timer!", state=tk.DISABLED, fg="red")
    dismiss_btn.pack(pady=40, before=escape_info) 
    escape_info.config(text="Press ESC to resume (Disabled during penalty)", fg="#555555")
    
    root.deiconify() 
    root.focus_force()
    root.grab_set()
    
    for i in range(1, 11):
        root.attributes('-alpha', (i / 10.0) * 0.95)
        root.update() 
        time.sleep(0.01)

# --- MAIN SERVICE LOOP ---
def service_loop():
    global cap, pose, bad_posture_start_time, good_posture_start_time
    global recovery_start_time, last_recovery_time, consecutive_strikes, punishment_served
    
    load_config()

    # Determine if we should be active right now (Master Switch AND Schedule)
    should_be_active = current_config["is_active"] and is_within_schedule()

    if not should_be_active:
        if cap is not None:
            cap.release()
            cap = None
            pose = None 
        if is_showing_warning:
            dismiss_warning()
            
        root.after(1000, service_loop) 
        return

    if cap is None:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) if platform.system() == "Windows" else cv2.VideoCapture(0)
        # Initialize Pose model with Custom Confidence setting
        pose = mp.solutions.pose.Pose(min_detection_confidence=current_config["min_confidence"])

    success, frame = cap.read()
    if not success:
        root.after(50, service_loop)
        return

    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)
    
    is_bad_posture = False
    current_violation = ""
    
    # Advanced Thresholds from Dashboard
    TOO_CLOSE = current_config["close_threshold"]
    SLOUCHING = current_config["slouch_threshold"]

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        shoulder_width = abs(landmarks[11].x - landmarks[12].x)
        posture_height = ((landmarks[11].y + landmarks[12].y) / 2) - landmarks[0].y 
        
        if shoulder_width > TOO_CLOSE or posture_height < SLOUCHING:
            is_bad_posture = True
            if shoulder_width > TOO_CLOSE and posture_height < SLOUCHING: current_violation = "SLOUCHING & TOO CLOSE!"
            elif shoulder_width > TOO_CLOSE: current_violation = "TOO CLOSE TO SCREEN!"
            else: current_violation = "SLOUCHING!"
    else:
        is_bad_posture = True
        current_violation = "NO BODY DETECTED IN CAMERA!"

    recovery_target = current_config["penalty_time"] + (consecutive_strikes * 5)
    slouch_target = current_config["grace_time"]

    # EXIT LOGIC
    if is_showing_warning:
        root.focus_force()
        if is_bad_posture:
            recovery_start_time = None
            punishment_served = False
            dismiss_btn.config(text=f"Still {current_violation} - Timer reset!", state=tk.DISABLED, fg="red")
            escape_info.config(text="Press ESC to resume (Disabled during penalty)", fg="#555555")
        else:
            if recovery_start_time is None: 
                recovery_start_time = time.time()
                punishment_served = False
                
            time_left = max(0, int(recovery_target - (time.time() - recovery_start_time)))
            
            if time_left > 0:
                punishment_served = False
                pen_txt = f" (+{consecutive_strikes * 5}s Penalty)" if consecutive_strikes > 0 else ""
                dismiss_btn.config(text=f"Hold perfect posture for {time_left}s...{pen_txt}", state=tk.DISABLED, fg="black")
            else:
                punishment_served = True 
                dismiss_btn.config(text="Unlock (Click to Resume)", state=tk.NORMAL, fg="green")
                escape_info.config(text="Press ESC or click Unlock to resume working", fg="#cccccc")
    
    # ENTRY LOGIC
    else:
        if is_bad_posture:
            good_posture_start_time = None 
            if bad_posture_start_time is None:
                if last_recovery_time > 0 and (time.time() - last_recovery_time) < 60:
                    if consecutive_strikes < 10: 
                        consecutive_strikes += 1
                else:
                    consecutive_strikes = 0 
                    
                bad_posture_start_time = time.time()
                
                if consecutive_strikes >= 3:
                    trigger_warning(f"3 STRIKES!\n{current_violation}")
                
            elif time.time() - bad_posture_start_time >= slouch_target:
                trigger_warning(current_violation)
                
        else:
            if consecutive_strikes > 0 and last_recovery_time > 0 and (time.time() - last_recovery_time) >= 60:
                consecutive_strikes = 0
                last_recovery_time = 0 

            if bad_posture_start_time is not None:
                if good_posture_start_time is None:
                    good_posture_start_time = time.time()
                elif time.time() - good_posture_start_time >= 1.5:
                    bad_posture_start_time = None
                    good_posture_start_time = None
                    last_recovery_time = time.time()
            
    root.after(50, service_loop)

print("🛡️ Advanced Enforcer Service running silently in background...")
root.after(50, service_loop)
root.mainloop()