import customtkinter as ctk
import json
import os
import subprocess
import sys
import platform
import pathlib

APP_DIR = pathlib.Path(__file__).parent.absolute()
CONFIG_FILE = APP_DIR / "posture_config.json"
ENFORCER_SCRIPT = APP_DIR / "enforcer.py"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green") 

DEFAULT_CONFIG = {
    "grace_time": 10, 
    "penalty_time": 10,
    "use_schedule": False,
    "schedule_start": "09:00",
    "schedule_end": "17:00",
    "slouch_threshold": 0.15,
    "close_threshold": 0.60,
    "min_confidence": 0.7
}

class PostureDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Posture Control Center")
        self.geometry("500x580")
        self.resizable(True, True)

        # Load existing config or apply defaults
        self.config = {"is_active": False}
        self.config.update(DEFAULT_CONFIG)
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config.update(json.load(f))
            except:
                pass

        self.build_ui()
        self.update_ui_state()

    def build_ui(self):
        # --- HEADER SECTION ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.status_lbl = ctk.CTkLabel(self.header_frame, text="Status: Offline", font=("Segoe UI", 20, "bold"), text_color="gray")
        self.status_lbl.pack(pady=(0, 15))

        self.btn_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.btn_frame.pack(fill="x")

        self.toggle_btn = ctk.CTkButton(self.btn_frame, text="▶ START ENFORCER", font=("Segoe UI", 14, "bold"), 
                                        height=45, command=self.toggle_enforcer)
        self.toggle_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.default_btn = ctk.CTkButton(self.btn_frame, text="↺ Defaults", font=("Segoe UI", 12, "bold"), 
                                         fg_color="#444444", hover_color="#555555", width=80, height=45, command=self.restore_defaults)
        self.default_btn.pack(side="right")

        # --- TABS SECTION ---
        self.tabview = ctk.CTkTabview(self, width=460, height=350)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        self.tab_basic = self.tabview.add("Basic")
        self.tab_sched = self.tabview.add("Schedule")
        self.tab_adv = self.tabview.add("Advanced")

        self._build_basic_tab(self.tab_basic)
        self._build_schedule_tab(self.tab_sched)
        self._build_advanced_tab(self.tab_adv)

    def _build_basic_tab(self, parent):
        # Grace Time
        ctk.CTkLabel(parent, text="Slouch Tolerance (Seconds before penalty):", font=("Segoe UI", 13)).pack(anchor="w", padx=10, pady=(15, 0))
        
        grace_frame = ctk.CTkFrame(parent, fg_color="transparent")
        grace_frame.pack(fill="x", padx=10, pady=(5, 15))
        
        self.grace_val_lbl = ctk.CTkLabel(grace_frame, text=f"{self.config['grace_time']}s", font=("Segoe UI", 14, "bold"), width=40)
        self.grace_val_lbl.pack(side="right")
        
        self.grace_slider = ctk.CTkSlider(grace_frame, from_=3, to=30, number_of_steps=27, 
                                          command=lambda v: self.update_slider_label(self.grace_val_lbl, v, "s"))
        self.grace_slider.set(self.config["grace_time"])
        self.grace_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Penalty Time
        ctk.CTkLabel(parent, text="Base Penalty Duration (Seconds):", font=("Segoe UI", 13)).pack(anchor="w", padx=10, pady=(15, 0))
        
        penalty_frame = ctk.CTkFrame(parent, fg_color="transparent")
        penalty_frame.pack(fill="x", padx=10, pady=(5, 15))
        
        self.penalty_val_lbl = ctk.CTkLabel(penalty_frame, text=f"{self.config['penalty_time']}s", font=("Segoe UI", 14, "bold"), width=40)
        self.penalty_val_lbl.pack(side="right")
        
        self.penalty_slider = ctk.CTkSlider(penalty_frame, from_=5, to=60, number_of_steps=55, 
                                            command=lambda v: self.update_slider_label(self.penalty_val_lbl, v, "s"))
        self.penalty_slider.set(self.config["penalty_time"])
        self.penalty_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def _build_schedule_tab(self, parent):
        ctk.CTkLabel(parent, text="Automate when the enforcer is active.", text_color="gray").pack(pady=(15, 15))
        
        self.schedule_switch = ctk.CTkSwitch(parent, text="Enable Working Hours Schedule", font=("Segoe UI", 13, "bold"), command=self.save_config)
        if self.config["use_schedule"]: self.schedule_switch.select()
        self.schedule_switch.pack(pady=10)

        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(pady=20)

        ctk.CTkLabel(frame, text="Start Time (HH:MM):").grid(row=0, column=0, padx=10, pady=10)
        self.start_time_var = ctk.StringVar(value=self.config["schedule_start"])
        self.start_entry = ctk.CTkEntry(frame, textvariable=self.start_time_var, width=100, justify="center")
        self.start_entry.grid(row=0, column=1)
        self.start_time_var.trace_add("write", lambda *args: self.save_config())

        ctk.CTkLabel(frame, text="End Time (HH:MM):").grid(row=1, column=0, padx=10, pady=10)
        self.end_time_var = ctk.StringVar(value=self.config["schedule_end"])
        self.end_entry = ctk.CTkEntry(frame, textvariable=self.end_time_var, width=100, justify="center")
        self.end_entry.grid(row=1, column=1)
        self.end_time_var.trace_add("write", lambda *args: self.save_config())
        
        ctk.CTkLabel(parent, text="* Use 24-hour format (e.g. 09:00, 17:30)", text_color="gray", font=("Segoe UI", 11)).pack(pady=10)

    def _build_advanced_tab(self, parent):
        # Slouch Threshold
        ctk.CTkLabel(parent, text="Slouch Height Threshold (Higher = stricter):", font=("Segoe UI", 13)).pack(anchor="w", padx=10, pady=(15, 0))
        slouch_frame = ctk.CTkFrame(parent, fg_color="transparent")
        slouch_frame.pack(fill="x", padx=10, pady=(5, 10))
        self.slouch_val_lbl = ctk.CTkLabel(slouch_frame, text=f"{self.config['slouch_threshold']:.2f}", font=("Segoe UI", 14, "bold"), width=40)
        self.slouch_val_lbl.pack(side="right")
        self.slouch_slider = ctk.CTkSlider(slouch_frame, from_=0.05, to=0.35, number_of_steps=30, 
                                           command=lambda v: self.update_slider_label(self.slouch_val_lbl, v, "", 2))
        self.slouch_slider.set(self.config["slouch_threshold"])
        self.slouch_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Close Threshold
        ctk.CTkLabel(parent, text="Screen Proximity Threshold (Lower = stricter):", font=("Segoe UI", 13)).pack(anchor="w", padx=10, pady=(10, 0))
        close_frame = ctk.CTkFrame(parent, fg_color="transparent")
        close_frame.pack(fill="x", padx=10, pady=(5, 10))
        self.close_val_lbl = ctk.CTkLabel(close_frame, text=f"{self.config['close_threshold']:.2f}", font=("Segoe UI", 14, "bold"), width=40)
        self.close_val_lbl.pack(side="right")
        self.close_slider = ctk.CTkSlider(close_frame, from_=0.30, to=1.00, number_of_steps=14, 
                                          command=lambda v: self.update_slider_label(self.close_val_lbl, v, "", 2))
        self.close_slider.set(self.config["close_threshold"])
        self.close_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Confidence
        ctk.CTkLabel(parent, text="Prediction Confidence:", font=("Segoe UI", 13)).pack(anchor="w", padx=10, pady=(10, 0))
        conf_frame = ctk.CTkFrame(parent, fg_color="transparent")
        conf_frame.pack(fill="x", padx=10, pady=(5, 5))
        self.conf_val_lbl = ctk.CTkLabel(conf_frame, text=f"{self.config['min_confidence']:.1f}", font=("Segoe UI", 14, "bold"), width=40)
        self.conf_val_lbl.pack(side="right")
        self.conf_slider = ctk.CTkSlider(conf_frame, from_=0.4, to=0.9, number_of_steps=5, 
                                         command=lambda v: self.update_slider_label(self.conf_val_lbl, v, "", 1))
        self.conf_slider.set(self.config["min_confidence"])
        self.conf_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def update_slider_label(self, label, value, suffix="", decimals=0):
        """Updates the text next to the slider in real-time and saves"""
        if decimals == 0:
            label.configure(text=f"{int(value)}{suffix}")
        else:
            label.configure(text=f"{value:.{decimals}f}{suffix}")
        self.save_config()

    def restore_defaults(self):
        """Snaps all UI elements back to default values"""
        self.grace_slider.set(DEFAULT_CONFIG["grace_time"])
        self.update_slider_label(self.grace_val_lbl, DEFAULT_CONFIG["grace_time"], "s")
        
        self.penalty_slider.set(DEFAULT_CONFIG["penalty_time"])
        self.update_slider_label(self.penalty_val_lbl, DEFAULT_CONFIG["penalty_time"], "s")
        
        if DEFAULT_CONFIG["use_schedule"]: self.schedule_switch.select()
        else: self.schedule_switch.deselect()
            
        self.start_time_var.set(DEFAULT_CONFIG["schedule_start"])
        self.end_time_var.set(DEFAULT_CONFIG["schedule_end"])
        
        self.slouch_slider.set(DEFAULT_CONFIG["slouch_threshold"])
        self.update_slider_label(self.slouch_val_lbl, DEFAULT_CONFIG["slouch_threshold"], "", 2)
        
        self.close_slider.set(DEFAULT_CONFIG["close_threshold"])
        self.update_slider_label(self.close_val_lbl, DEFAULT_CONFIG["close_threshold"], "", 2)
        
        self.conf_slider.set(DEFAULT_CONFIG["min_confidence"])
        self.update_slider_label(self.conf_val_lbl, DEFAULT_CONFIG["min_confidence"], "", 1)
        
        self.save_config()

    def save_config(self):
        self.config["grace_time"] = int(self.grace_slider.get())
        self.config["penalty_time"] = int(self.penalty_slider.get())
        self.config["use_schedule"] = bool(self.schedule_switch.get())
        self.config["schedule_start"] = self.start_time_var.get()
        self.config["schedule_end"] = self.end_time_var.get()
        self.config["slouch_threshold"] = round(self.slouch_slider.get(), 2)
        self.config["close_threshold"] = round(self.close_slider.get(), 2)
        self.config["min_confidence"] = round(self.conf_slider.get(), 1)
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def toggle_enforcer(self):
        self.config["is_active"] = not self.config["is_active"]
        self.save_config()

        if self.config["is_active"]:
            # Resolve absolute paths and virtual environment python interpreter for installed instances
            app_dir = pathlib.Path(__file__).parent.absolute()
            enforcer_script = app_dir / ENFORCER_SCRIPT
            
            if platform.system() == "Windows":
                python_executable = app_dir / "venv" / "Scripts" / "pythonw.exe"
                if not python_executable.exists():
                    python_executable = app_dir / "venv" / "Scripts" / "python.exe"
            else:
                python_executable = app_dir / "venv" / "bin" / "python"
                
            if not python_executable.exists():
                python_executable = sys.executable

            # Set the Current Working Directory to ensure enforcer finds the config file and camera properly
            kwargs = {
                "cwd": str(app_dir)
            }
            
            if platform.system() == "Windows":
                kwargs['creationflags'] = 0x00000008 | 0x00000200
            else:
                kwargs['start_new_session'] = True
                
            try:
                subprocess.Popen([str(python_executable), str(enforcer_script)], **kwargs)
            except Exception as e:
                print(f"Failed to start enforcer: {e}")
            
        self.update_ui_state()

    def update_ui_state(self):
        if self.config["is_active"]:
            self.toggle_btn.configure(text="■ STOP ENFORCER", fg_color="#E53935", hover_color="#C62828")
            self.status_lbl.configure(text="Status: Active & Watching", text_color="#4CAF50")
        else:
            self.toggle_btn.configure(text="▶ START ENFORCER", fg_color="#2E7D32", hover_color="#1B5E20")
            self.status_lbl.configure(text="Status: Offline", text_color="gray")

if __name__ == "__main__":
    app = PostureDashboard()
    app.mainloop()