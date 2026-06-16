#!/usr/bin/env python3
"""
API Robustness Loop Harness - Runs the test suite 1000 times
"""

import unittest
import sys
import os

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

# Ensure the root directory is in the import search path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

import subprocess

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

# Run virtual environment initialization
check_and_create_venv()
# Run dependency installation
install_dependencies()

from backend.tests.test_api import TestPasswordManagerAPI

def main():
    loader = unittest.TestLoader()
    # Run with verbosity 0 to keep the output clean and concise
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=0)
    
    print("Starting 1000x API robustness execution loop...")
    for i in range(1, 1001):
        # Reinitialize test suite to prevent test case caching issues
        suite = unittest.TestSuite()
        suite.addTests(loader.loadTestsFromTestCase(TestPasswordManagerAPI))

        result = runner.run(suite)
        if not result.wasSuccessful():
            print(f"\nCRITICAL: API Test failed at iteration {i}!")
            # Print failure details
            for failure in result.failures:
                print(f"Failure in {failure[0]}: {failure[1]}")
            for error in result.errors:
                print(f"Error in {error[0]}: {error[1]}")
            sys.exit(1)
            
        if i % 100 == 0:
            print(f"Completed {i}/1000 runs successfully.")
            
    print("\nSUCCESS: API Robustness check finished. 1000/1000 runs passed (100% success rate).")
    sys.exit(0)

if __name__ == "__main__":
    main()
