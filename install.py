import os
import sys
import subprocess
import urllib.request
import urllib.error
import pathlib
import socket

# --- CONFIGURATION ---
REPO_URL = "https://raw.githubusercontent.com/Sane-Sunil/Carettan/master"
FILES_TO_DOWNLOAD = ["gui.py", "enforcer.py", "uninstall.py"]

def progress_reporthook(block_num, block_size, total_size):
    """Draws a real-time progress bar in the terminal"""
    if total_size <= 0:
        total_size = 100000  # Fallback if content-length is missing
    
    downloaded = block_num * block_size
    percentage = min(int(downloaded * 100 / total_size), 100)
    
    bar_length = 30
    filled_length = int(bar_length * percentage // 100)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    
    # \r resets the cursor to the start of the line for a smooth live animation
    sys.stdout.write(f"\r    [{bar}] {percentage}% ({downloaded / 1024 / 1024:.2f} MB)")
    sys.stdout.flush()

def download_file(url, dest_path):
    """Downloads a file with status code checking and size validation"""
    socket.setdefaulttimeout(15)
    print(f"⬇️ Downloading {dest_path.name} from {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"\n❌ Error: Received HTTP status {response.status} for {dest_path.name}")
                sys.exit(1)
                
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(dest_path, 'wb') as out_file:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        percentage = min(int(downloaded * 100 / total_size), 100)
                        bar_length = 25
                        filled = int(bar_length * percentage // 100)
                        bar = '█' * filled + '-' * (bar_length - filled)
                        sys.stdout.write(f"\r    [{bar}] {percentage}% ({downloaded / 1024:.1f} KB)")
                    else:
                        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'][int(downloaded / chunk_size) % 10]
                        sys.stdout.write(f"\r    {spinner} Downloading... ({downloaded / 1024:.1f} KB received)")
                    
                    sys.stdout.flush()
            print()
            
            # Verify file isn't empty
            if dest_path.stat().st_size == 0:
                print(f"\n❌ Error: {dest_path.name} downloaded as 0 bytes. Check your GitHub repository link.")
                sys.exit(1)
                
    except urllib.error.HTTPError as e:
        print(f"\n❌ HTTP Error {e.code}: Could not find '{dest_path.name}'. Check if it's pushed to GitHub.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Failed to download {dest_path.name}: {e}")
        sys.exit(1)
             
def main():
    print("🚀 Starting Carettan Universal Installer...")
    
    home = pathlib.Path.home()
    app_dir = home / ".carettan"
    app_dir.mkdir(exist_ok=True, parents=True)
    
    # 1. Download application files with live progress
    for filename in FILES_TO_DOWNLOAD:
        url = f"{REPO_URL}/{filename}"
        dest = app_dir / filename
        download_file(url, dest)
        
    # 2. Setup Virtual Environment
    print("🐍 Setting up isolated Python environment...")
    venv_dir = app_dir / "venv"
    if not (venv_dir / "bin" / "python").exists() and not (venv_dir / "Scripts" / "python.exe").exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    
    if sys.platform == "win32":
        pip_path = venv_dir / "Scripts" / "pip"
        python_path = venv_dir / "Scripts" / "python.exe"
        pythonw_path = venv_dir / "Scripts" / "pythonw.exe"
    else:
        pip_path = venv_dir / "bin" / "pip"
        python_path = venv_dir / "bin" / "python"
        
    # 3. Install dependencies
    print("📦 Installing required AI and GUI libraries (this may take a moment)...")
    subprocess.run([str(pip_path), "install", "--upgrade", "pip", "--quiet"], check=True)
    subprocess.run([str(pip_path), "install", "opencv-python", "mediapipe==0.10.14", "customtkinter", "pillow", "--quiet"], check=True)
    
    # 4. Register App, CLI Command, & Launchers
    if sys.platform == "win32":
        print("🪟 Configuring Windows command 'carettan' and shortcut...")
        batch_path = app_dir / "carettan.bat"
        batch_content = f'''@echo off
cd /d "{app_dir}"
if "%1"=="--uninstall" (
    "{python_path}" uninstall.py
) else (
    start "" "{pythonw_path}" gui.py %* > "{app_dir}\\error.log" 2>&1
)
'''
        batch_path.write_text(batch_content)
        
        desktop = pathlib.Path(os.path.expanduser("~/Desktop"))
        shortcut_path = desktop / "Carettan.lnk"
        ps_script = f"""
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "{batch_path}"
        $Shortcut.WorkingDirectory = "{app_dir}"
        $Shortcut.Save()
        """
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True)

    else:
        print("🐧/🍎 Configuring 'carettan' terminal command and App menu...")
        bin_dir = home / ".local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        launcher = bin_dir / "carettan"
        
        launcher.write_text(f'''#!/bin/bash
cd "{app_dir}"
if [ "$1" = "--uninstall" ]; then
    exec "{python_path}" uninstall.py
else
    "{python_path}" gui.py "$@" > "{app_dir}/error.log" 2>&1 &
fi
''')
        launcher.chmod(0o755)
        
        if sys.platform.startswith("linux"):
            desktop_dir = home / ".local" / "share" / "applications"
            desktop_dir.mkdir(parents=True, exist_ok=True)
            desktop_file = desktop_dir / "carettan.desktop"
            desktop_file.write_text(f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Carettan
Comment=AI Posture Monitoring Enforcer
Exec={launcher}
Terminal=false
Categories=Utility;Health;
""")
        elif sys.platform == "Darwin":
            app_bundle = home / "Applications" / "Carettan.app"
            app_bundle.mkdir(parents=True, exist_ok=True)
            contents = app_bundle / "Contents"
            macos = contents / "MacOS"
            macos.mkdir(parents=True, exist_ok=True)
            
            app_launcher = macos / "Carettan"
            app_launcher.write_text(f'''#!/bin/bash
cd "{app_dir}"
if [ "$1" = "--uninstall" ]; then
    exec "{python_path}" uninstall.py
else
    "{python_path}" gui.py "$@" > "{app_dir}/error.log" 2>&1 &
fi
''')
            app_launcher.chmod(0o755)

    print("\n✅ Installation Complete!")
    print("Type `carettan` to launch the GUI dashboard.")

if __name__ == "__main__":
    main()