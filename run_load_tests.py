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
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
