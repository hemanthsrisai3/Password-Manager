#!/usr/bin/env python3
"""
Zero-Trust Password Manager - Desktop Launcher
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser

# --- Python 3.14 Compatibility Monkey-Patch for Pydantic ---
if sys.version_info >= (3, 14):
    try:
        import typing
        import pydantic._internal._typing_extra as typing_extra
        def patched_eval_type(value, globalns=None, localns=None, type_params=None):
            try:
                evaluated = typing._eval_type(value, globalns, localns, type_params=type_params, prefer_fwd_module=True)
            except TypeError:
                evaluated = typing._eval_type(value, globalns, localns, type_params=type_params)
            if evaluated is None:
                evaluated = type(None)
            return evaluated
        typing_extra._eval_type = patched_eval_type
    except ImportError:
        pass
    except Exception:
        pass
# -----------------------------------------------------------

def check_and_create_venv():
    # Detect if already running in a virtual environment
    is_in_venv = (sys.prefix != sys.base_prefix) or hasattr(sys, "real_prefix")
    if is_in_venv:
        return

    print("Application is not running in a virtual environment.")
    print("Checking for/creating a local virtual environment (.venv)...")
    
    venv_dir = os.path.abspath(".venv")
    if not os.path.exists(venv_dir):
        print("Creating virtual environment in .venv...")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            print("Virtual environment created successfully.")
        except Exception as e:
            print(f"Warning: Failed to create virtual environment: {e}")
            print("Attempting to run in the current global environment instead.")
            return

    if sys.platform == "win32":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")

    if os.path.exists(venv_python):
        print(f"Re-launching application inside virtual environment: {venv_python}")
        try:
            result = subprocess.run([venv_python] + sys.argv)
            sys.exit(result.returncode)
        except Exception as e:
            print(f"Warning: Failed to re-launch in virtual environment: {e}")
            print("Attempting to run in the current global environment instead.")
    else:
        print("Warning: Virtual environment Python interpreter not found.")
        print("Attempting to run in the current global environment instead.")

def install_dependencies():
    print("Checking application dependencies...")
    try:
        import fastapi
        import uvicorn
        import cryptography
        import pydantic
        print("All dependencies are already installed.")
    except ImportError:
        print("Some required dependencies are missing. Installing now...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("Dependencies installed successfully.")
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            print("Please run 'pip install -r requirements.txt' manually.")
            sys.exit(1)

def open_browser():
    # Allow the server a moment to spin up before opening the page
    time.sleep(1.5)
    url = "http://localhost:8000"
    print(f"\n[Launcher] Launching default web browser to: {url}")
    webbrowser.open(url)

def main():
    # Make sure we're in the correct working directory (root folder of project)
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # Automatically check/create/use virtual environment
    check_and_create_venv()

    # Automatically check/install missing packages
    install_dependencies()

    # Ensure project root is in python path
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    # Launch browser in a separate background thread
    threading.Thread(target=open_browser, daemon=True).start()

    print("\n[Launcher] Starting local FastAPI server on http://localhost:8000...")
    print("[Launcher] Press Ctrl+C to stop the server.\n")
    
    # Run uvicorn by dynamically importing the app
    from backend.app import app
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000, reload=False)

if __name__ == "__main__":
    main()
