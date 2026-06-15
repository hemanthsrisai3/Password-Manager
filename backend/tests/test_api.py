#!/usr/bin/env python3
"""
Unit Tests for Zero-Trust Password Manager FastAPI Backend
"""

import unittest
import os
import json
import shutil
import sys
from fastapi.testclient import TestClient

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

import backend.core
backend.core.PBKDF2_ITERATIONS = 1  # Speed up PBKDF2 for tests

import backend.app as app_mod
from backend.app import app
from backend.core import VAULT_FILENAME, CONFIG_FILENAME

class TestPasswordManagerAPI(unittest.TestCase):
    def setUp(self):
        # Reset backend global states to ensure test isolation
        app_mod.vault.filepath = VAULT_FILENAME
        app_mod.vault.derived_key = None
        app_mod.vault.salt = None
        app_mod.vault.data = {"credentials": []}
        app_mod.vault.is_decoy = False
        app_mod.active_session_token = None
        
        # Remove database and config files
        for path in (VAULT_FILENAME, CONFIG_FILENAME):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        self.client = TestClient(app)

    def tearDown(self):
        # Clean up database and config files after each test
        for path in (VAULT_FILENAME, CONFIG_FILENAME):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    def test_get_status_uninitialized(self):
        """Test status returns uninitialized if vault.json does not exist."""
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["exists"])
        self.assertFalse(data["unlocked"])

    def test_initialize_vault(self):
        """Test initializing the vault creates the vault and returns a session token."""
        response = self.client.post("/api/init", json={"password": "MyMasterPassword123!"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("config", data)
        self.assertTrue(os.path.exists(VAULT_FILENAME))

        # Check status again
        status_resp = self.client.get("/api/status")
        self.assertTrue(status_resp.json()["exists"])

    def test_initialize_duplicate_fails(self):
        """Test initializing an already existing vault returns 400."""
        self.client.post("/api/init", json={"password": "PasswordOne!"})
        response = self.client.post("/api/init", json={"password": "PasswordTwo!"})
        self.assertEqual(response.status_code, 400)

    def test_unlock_vault_success(self):
        """Test unlocking the vault returns session token."""
        self.client.post("/api/init", json={"password": "MyMasterPassword123!"})
        
        # Lock session first
        self.client.post("/api/lock")
        
        response = self.client.post("/api/unlock", json={"password": "MyMasterPassword123!"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertFalse(data["is_decoy"])

    def test_unlock_vault_incorrect_password(self):
        """Test unlocking with incorrect password returns 401."""
        self.client.post("/api/init", json={"password": "MyMasterPassword123!"})
        self.client.post("/api/lock")
        
        response = self.client.post("/api/unlock", json={"password": "WrongPassword!"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("attempts remaining", response.json()["detail"])

    def test_unlocked_restrictions(self):
        """Test credentials access is blocked if locked or token is missing/invalid."""
        # Uninitialized
        response = self.client.get("/api/credentials")
        self.assertEqual(response.status_code, 400)

        # Initialized and logged in but accessing without header
        self.client.post("/api/init", json={"password": "MyMasterPassword123!"})
        response = self.client.get("/api/credentials")
        self.assertEqual(response.status_code, 401)

        # Invalid token
        response = self.client.get("/api/credentials", headers={"X-Session-Token": "invalid_token"})
        self.assertEqual(response.status_code, 401)

    def test_credential_lifecycle(self):
        """Test adding, fetching, updating, trashing, restoring, and permanently deleting credentials."""
        init_res = self.client.post("/api/init", json={"password": "MyMasterPassword123!"})
        token = init_res.json()["token"]
        headers = {"X-Session-Token": token}

        # Add a credential (login)
        cred_data = {
            "service": "Github",
            "username": "my_git_user",
            "password": "gitPasswordPass",
            "notes": "Dev account",
            "category": "login"
        }
        add_res = self.client.post("/api/credentials", json=cred_data, headers=headers)
        self.assertEqual(add_res.status_code, 200)
        self.assertEqual(add_res.json()["credential"]["service"], "Github")
        cred_id = add_res.json()["credential"]["id"]

        # Fetch all
        get_res = self.client.get("/api/credentials", headers=headers)
        self.assertEqual(len(get_res.json()), 1)
        self.assertEqual(get_res.json()[0]["service"], "Github")

        # Update credential (also checks history tracking)
        update_data = {
            "service": "Github Enterprise",
            "username": "my_git_user",
            "password": "NEWgitPasswordPass",
            "notes": "Updated notes",
            "category": "login"
        }
        update_res = self.client.put(f"/api/credentials/{cred_id}", json=update_data, headers=headers)
        self.assertEqual(update_res.status_code, 200)

        # Verify update and password history
        get_res = self.client.get("/api/credentials", headers=headers)
        updated_cred = get_res.json()[0]
        self.assertEqual(updated_cred["service"], "Github Enterprise")
        self.assertEqual(updated_cred["password"], "NEWgitPasswordPass")
        self.assertEqual(updated_cred["history"], ["gitPasswordPass"])

        # Soft Delete (moves to trash)
        del_res = self.client.delete(f"/api/credentials/{cred_id}", headers=headers)
        self.assertEqual(del_res.status_code, 200)

        # Confirm category is trash
        get_res = self.client.get("/api/credentials", headers=headers)
        self.assertEqual(get_res.json()[0]["category"], "trash")
        self.assertEqual(get_res.json()[0]["orig_category"], "login")

        # Restore from trash
        restore_res = self.client.post(f"/api/credentials/{cred_id}/restore", headers=headers)
        self.assertEqual(restore_res.status_code, 200)

        # Confirm category restored
        get_res = self.client.get("/api/credentials", headers=headers)
        self.assertEqual(get_res.json()[0]["category"], "login")
        self.assertNotIn("orig_category", get_res.json()[0])

        # Delete again (moves to trash)
        self.client.delete(f"/api/credentials/{cred_id}", headers=headers)
        
        # Permanent Delete from within trash
        perm_del_res = self.client.delete(f"/api/credentials/{cred_id}", headers=headers)
        self.assertEqual(perm_del_res.status_code, 200)

        # Confirm empty
        get_res = self.client.get("/api/credentials", headers=headers)
        self.assertEqual(len(get_res.json()), 0)

    def test_empty_trash(self):
        """Test emptying trash permanently deletes all trashed credentials."""
        init_res = self.client.post("/api/init", json={"password": "MyMasterPassword123!"})
        token = init_res.json()["token"]
        headers = {"X-Session-Token": token}

        # Add two credentials
        c1 = self.client.post("/api/credentials", json={"service": "S1", "username": "U1", "password": "P1", "category": "login"}, headers=headers).json()["credential"]
        c2 = self.client.post("/api/credentials", json={"service": "S2", "username": "U2", "password": "P2", "category": "login"}, headers=headers).json()["credential"]

        # Trash one
        self.client.delete(f"/api/credentials/{c1['id']}", headers=headers)

        # Empty trash
        empty_res = self.client.post("/api/credentials/empty-trash", headers=headers)
        self.assertEqual(empty_res.status_code, 200)

        # Fetch remaining
        get_res = self.client.get("/api/credentials", headers=headers)
        self.assertEqual(len(get_res.json()), 1)
        self.assertEqual(get_res.json()[0]["id"], c2["id"])

    def test_config_management(self):
        """Test reading and writing settings configurations."""
        init_res = self.client.post("/api/init", json={"password": "MyMasterPassword123!"})
        token = init_res.json()["token"]
        headers = {"X-Session-Token": token}

        # Get current config
        config_res = self.client.get("/api/config", headers=headers)
        self.assertEqual(config_res.status_code, 200)
        self.assertEqual(config_res.json()["theme_mode"], "dark")

        # Update config
        update_payload = {
            "theme_mode": "light",
            "accent_color": "#ff0000",
            "clipboard_timeout": 45,
            "autolock_timeout": 10
        }
        save_res = self.client.post("/api/config", json=update_payload, headers=headers)
        self.assertEqual(save_res.status_code, 200)
        
        # Verify changes
        config_res = self.client.get("/api/config", headers=headers)
        data = config_res.json()
        self.assertEqual(data["theme_mode"], "light")
        self.assertEqual(data["accent_color"], "#ff0000")
        self.assertEqual(data["clipboard_timeout"], 45)
        self.assertEqual(data["autolock_timeout"], 10)

    def test_decoy_vault_isolation(self):
        """Test decoy vault configuration and separate decryption environment."""
        init_res = self.client.post("/api/init", json={"password": "RealMasterPassword123!"})
        token = init_res.json()["token"]
        headers = {"X-Session-Token": token}

        # Add real credential
        self.client.post("/api/credentials", json={"service": "RealBank", "username": "real_user", "password": "realPassword", "category": "login"}, headers=headers)

        # Setup decoy vault
        decoy_res = self.client.post("/api/config/decoy", json={"password": "DecoyMasterPassword123!"}, headers=headers)
        self.assertEqual(decoy_res.status_code, 200)

        # Lock session
        self.client.post("/api/lock")

        # Login to Decoy Vault
        login_decoy = self.client.post("/api/unlock", json={"password": "DecoyMasterPassword123!"})
        self.assertEqual(login_decoy.status_code, 200)
        decoy_token = login_decoy.json()["token"]
        self.assertTrue(login_decoy.json()["is_decoy"])

        # Fetch credentials from Decoy - should only show decoy default accounts (Facebook, Netflix)
        decoy_headers = {"X-Session-Token": decoy_token}
        get_decoy_res = self.client.get("/api/credentials", headers=decoy_headers)
        self.assertEqual(len(get_decoy_res.json()), 2)
        services = [c["service"] for c in get_decoy_res.json()]
        self.assertIn("Facebook", services)
        self.assertIn("Netflix", services)
        self.assertNotIn("RealBank", services)

    def test_change_master_password(self):
        """Test master password rotation re-encrypts database and functions with new key."""
        init_res = self.client.post("/api/init", json={"password": "OldPassword123!"})
        token = init_res.json()["token"]
        headers = {"X-Session-Token": token}

        # Add a credential
        self.client.post("/api/credentials", json={"service": "Test", "username": "user", "password": "pwd", "category": "login"}, headers=headers)

        # Change master password
        rotate_res = self.client.post("/api/config/change-password", json={
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!"
        }, headers=headers)
        self.assertEqual(rotate_res.status_code, 200)

        # Lock
        self.client.post("/api/lock")

        # Unlock with old fails
        unlock_old = self.client.post("/api/unlock", json={"password": "OldPassword123!"})
        self.assertEqual(unlock_old.status_code, 401)

        # Unlock with new succeeds
        unlock_new = self.client.post("/api/unlock", json={"password": "NewPassword123!"})
        self.assertEqual(unlock_new.status_code, 200)

    def test_generator_endpoints(self):
        """Test password generator, Diceware passphrase generator, and strength meter APIs."""
        # Standard Generator
        gen_res = self.client.get("/api/generate/password?length=20&use_upper=true&use_lower=true&use_digits=true&use_special=true")
        self.assertEqual(gen_res.status_code, 200)
        password = gen_res.json()["password"]
        self.assertEqual(len(password), 20)

        # Diceware Generator
        phrase_res = self.client.get("/api/generate/passphrase?words_count=5&separator=--")
        self.assertEqual(phrase_res.status_code, 200)
        phrase = phrase_res.json()["passphrase"]
        self.assertEqual(len(phrase.split("--")), 5)

        # Strength Meter API
        strength_res = self.client.post("/api/generate/strength", json={"password": "SuperSecureComplexPassword123!#"})
        self.assertEqual(strength_res.status_code, 200)
        self.assertEqual(strength_res.json()["label"], "Strong")

    def test_panic_self_destruct(self):
        """Test that 5 consecutive failed login attempts securely wipe and delete the vault file."""
        # Initialize vault
        self.client.post("/api/init", json={"password": "MyMasterPassword123!"})
        self.assertTrue(os.path.exists(VAULT_FILENAME))

        # Lock session
        self.client.post("/api/lock")

        # Attempt 4 failed unlocks
        for _ in range(4):
            resp = self.client.post("/api/unlock", json={"password": "WrongPassword!"})
            self.assertEqual(resp.status_code, 401)
            self.assertTrue(os.path.exists(VAULT_FILENAME)) # Vault still exists

        # Attempt 5th failed unlock
        resp5 = self.client.post("/api/unlock", json={"password": "WrongPassword!"})
        self.assertEqual(resp5.status_code, 410) # 410 Gone (shredded)
        self.assertFalse(os.path.exists(VAULT_FILENAME)) # Vault file was deleted!

if __name__ == "__main__":
    unittest.main()
