# Carettan 🤖
> A posture monitoring and enforcement desktop application.

Carettan runs locally using your webcam and **MediaPipe** to keep an eye on your posture in the background. It features a dark-mode **CustomTkinter** dashboard (`gui.py`) that communicates independently with a resource-efficient background vision service (`enforcer.py`).

---

## ✨ Features
* **Decoupled Architecture:** Close the dashboard UI at any time—the background enforcer keeps watching without interruption.
* **Reset Button:** Instantly restore optimal factory defaults with a single click.
* **Smart Installer & Uninstaller:** Zero-fuss installation that isolates dependencies in a Python virtual environment and registers global command shortcuts.

---

## 🚀 Installation


Open your terminal and run the following command:

```bash
python3 -c "$(curl -sSL https://raw.githubusercontent.com/Sane-Sunil/Carettan/master/install.py)"
```

## ⬇️ Running

Open from your app drawer. 

You can also use:
```bash
carettan
```

---

## 🗑️ Uninstallation

Uninstall:
```bash
carettan --uninstall
```