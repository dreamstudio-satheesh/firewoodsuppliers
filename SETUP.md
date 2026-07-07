# Firewood Billing — Windows Setup

## Prerequisites

1. **Git for Windows** — [Download](https://git-scm.com/download/win)
   - Install with default options (Git Bash, Git GUI, etc.)

2. **Python 3.12+** — [Download](https://www.python.org/downloads/)
   - **IMPORTANT**: Check **"Add Python to PATH"** during installation

## Install

Open **Git Bash** or **Command Prompt** and run:

```batch
cd C:\
git clone git@github.com:dreamstudio-satheesh/firewoodsuppliers.git
cd firewoodsuppliers
```

## Run

### First time (auto-installs dependencies)

Double-click **`run.vbs`** — it will:
1. Create a Python virtual environment (`venv\`)
2. Install dependencies (PySide6, reportlab, openpyxl)
3. Launch the application

Or double-click **`run.bat`** if you want to see the console window.

### Subsequent runs

Just double-click **`run.vbs`** — it reuses the existing `venv\` and launches immediately.

## Update (when code changes)

```batch
cd C:\firewoodsuppliers
git pull
run.vbs
```

Git pull fetches latest changes; `run.vbs` handles the rest.

## Uninstall

Delete the folder `C:\firewoodsuppliers` — no registry changes, no system install.
