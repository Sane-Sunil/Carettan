import os
import sys
import shutil
import pathlib
import subprocess

def main():
    print("🗑️ Starting Carettan Uninstaller...")
    
    home = pathlib.Path.home()
    app_dir = home / ".carettan"
    
    # 1. Kill any running background enforcer process first
    print("🛑 Stopping background Carettan services...")
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/f", "/im", "python.exe"], capture_output=True)
        subprocess.run(["taskkill", "/f", "/im", "pythonw.exe"], capture_output=True)
    else:
        subprocess.run(["pkill", "-f", "carettan.py"], capture_output=True)

    # 2. Remove application directory (~/.carettan)
    if app_dir.exists():
        print(f"🧹 Removing application directory: {app_dir}")
        shutil.rmtree(app_dir, ignore_errors=True)
    else:
        print("ℹ️ Application directory not found (already removed?).")

    # 3. Clean up OS-specific shortcuts, CLI commands, and app entries
    if sys.platform == "win32":
        desktop = pathlib.Path(os.path.expanduser("~/Desktop"))
        shortcut = desktop / "Carettan.lnk"
        if shortcut.exists():
            print("🧹 Removing Desktop shortcut...")
            shortcut.unlink()
            
    else:
        # Remove unix CLI wrapper
        launcher = home / ".local" / "bin" / "carettan"
        if launcher.exists():
            print("🧹 Removing terminal launcher...")
            launcher.unlink()
            
        if sys.platform.startswith("linux"):
            desktop_file = home / ".local" / "share" / "applications" / "carettan.desktop"
            if desktop_file.exists():
                print("🧹 Removing App Drawer menu item...")
                desktop_file.unlink()
        elif sys.platform == "Darwin":
            app_bundle = home / "Applications" / "Carettan.app"
            if app_bundle.exists():
                print("🧹 Removing macOS Launchpad app...")
                shutil.rmtree(app_bundle, ignore_errors=True)

    print("\n✨ Carettan has been completely uninstalled from your system.")

if __name__ == "__main__":
    main()