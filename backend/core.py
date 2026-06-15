#!/usr/bin/env python3
"""
Zero-Trust Password Manager - Core Cryptography & Data Engine
"""

import os
import json
import base64
import secrets
import string
import uuid
import math
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet

# ----------------------------------------------------------------------
# CONSTANTS & CONFIGURATION DEFINITIONS
# ----------------------------------------------------------------------
VAULT_FILENAME = "vault.json"
CONFIG_FILENAME = "config.json"

DEFAULT_CONFIG = {
    "theme_mode": "dark",
    "accent_color": "#00adb5",
    "clipboard_timeout": 30,
    "autolock_timeout": 5,
    "failed_attempts": 0
}

def secure_delete_file(filepath: str) -> None:
    """Securely overwrites a file with random bytes before deleting it."""
    if os.path.exists(filepath):
        try:
            size = os.path.getsize(filepath)
            with open(filepath, "wb") as f:
                f.write(os.urandom(size))
                f.flush()
                os.fsync(f.fileno())
            os.remove(filepath)
        except Exception:
            try:
                os.remove(filepath)
            except Exception:
                pass


def load_config() -> dict:
    """Loads configuration settings from a local JSON file."""
    if os.path.exists(CONFIG_FILENAME):
        try:
            with open(CONFIG_FILENAME, "r") as f:
                data = json.load(f)
                # Ensure all default keys exist
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Saves configuration settings to a local JSON file."""
    try:
        with open(CONFIG_FILENAME, "w") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


PBKDF2_ITERATIONS = 100000

def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derives a 256-bit URL-safe base64 encryption key from the Master Password
    using PBKDF2 with SHA-256 and iterations count.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS
    )
    derived_bytes = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(derived_bytes)


class VaultManager:
    """
    Manages the lifecycle, loading, saving, encryption, and decryption of
    the local zero-trust credentials database.
    """
    def __init__(self, filepath: str = VAULT_FILENAME):
        self.filepath = filepath
        self.salt = None
        self.derived_key = None
        self.data = {"credentials": []}
        self.is_decoy = False

    def exists(self) -> bool:
        """Checks if the encrypted vault file exists."""
        return os.path.exists(self.filepath)

    def initialize_vault(self, master_password: str) -> None:
        """
        Creates a new vault file on disk by generating a secure random salt,
        deriving a key from the master password, and encrypting an empty credentials list.
        """
        self.salt = os.urandom(16)
        self.derived_key = derive_key(master_password, self.salt)
        self.data = {"credentials": []}
        self.is_decoy = False
        self.save_vault()

    def unlock_vault(self, master_password: str) -> bool:
        """
        Attempts to unlock the vault. Derives the key using the stored salt and
        attempts decryption. Returns True if successful, False otherwise.
        """
        try:
            with open(self.filepath, "r") as f:
                payload = json.load(f)
        except Exception:
            return False

        # 1. Try real vault
        try:
            self.salt = bytes.fromhex(payload["salt"])
            ciphertext = payload["ciphertext"].encode("utf-8")
            self.derived_key = derive_key(master_password, self.salt)
            fernet = Fernet(self.derived_key)
            decrypted_bytes = fernet.decrypt(ciphertext)
            self.data = json.loads(decrypted_bytes.decode("utf-8"))
            self.is_decoy = False
            return True
        except Exception:
            pass

        # 2. Try decoy vault (duress mode)
        if "decoy_salt" in payload and "decoy_ciphertext" in payload:
            try:
                self.salt = bytes.fromhex(payload["decoy_salt"])
                ciphertext = payload["decoy_ciphertext"].encode("utf-8")
                self.derived_key = derive_key(master_password, self.salt)
                fernet = Fernet(self.derived_key)
                decrypted_bytes = fernet.decrypt(ciphertext)
                self.data = json.loads(decrypted_bytes.decode("utf-8"))
                self.is_decoy = True
                return True
            except Exception:
                pass

        # Unlock failed
        self.derived_key = None
        self.salt = None
        return False

    def save_vault(self) -> None:
        """
        Encrypts the current credentials structure and writes it to the local vault file.
        Preserves whichever vault (real or decoy) is NOT currently unlocked.
        """
        if not self.derived_key or not self.salt:
            raise PermissionError("Vault is not unlocked or initialized.")

        # Read existing payload first to preserve whichever vault is not active
        payload = {}
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    payload = json.load(f)
            except Exception:
                pass

        plaintext_bytes = json.dumps(self.data).encode("utf-8")
        fernet = Fernet(self.derived_key)
        ciphertext = fernet.encrypt(plaintext_bytes)

        if self.is_decoy:
            payload["decoy_salt"] = self.salt.hex()
            payload["decoy_ciphertext"] = ciphertext.decode("utf-8")
        else:
            payload["salt"] = self.salt.hex()
            payload["ciphertext"] = ciphertext.decode("utf-8")

        with open(self.filepath, "w") as f:
            json.dump(payload, f, indent=2)

    def add_credential(self, service: str, username: str, password: str, notes: str = "", category: str = "login", **kwargs) -> dict:
        """Adds a new credential with metadata fields matching its category."""
        cred = {
            "id": str(uuid.uuid4()),
            "category": category,
            "service": service,
            "username": username,
            "password": password,
            "notes": notes,
            "history": []
        }
        # Add optional category fields
        for k, v in kwargs.items():
            cred[k] = v

        self.data.setdefault("credentials", []).append(cred)
        self.save_vault()
        return cred

    def update_credential(self, cred_id: str, service: str, username: str, password: str, notes: str = "", **kwargs) -> None:
        """Updates an existing credential and records password changes in rotation history."""
        for cred in self.data.get("credentials", []):
            if cred["id"] == cred_id:
                # Track password history
                old_pass = cred.get("password")
                if old_pass and old_pass != password:
                    history = cred.setdefault("history", [])
                    if old_pass not in history:
                        history.append(old_pass)
                        # Keep only the last 5 old passwords
                        if len(history) > 5:
                            history.pop(0)

                cred["service"] = service
                cred["username"] = username
                cred["password"] = password
                cred["notes"] = notes
                
                # Clear legacy/unneeded fields depending on category
                # Update optional custom category fields
                for k, v in kwargs.items():
                    cred[k] = v
                break
        self.save_vault()

    def delete_credential(self, cred_id: str) -> None:
        """Moves a credential to the Trash Bin, or permanently deletes it if it is already in the Trash."""
        for cred in self.data.get("credentials", []):
            if cred["id"] == cred_id:
                if cred.get("category") != "trash":
                    # Move to Trash bin
                    cred["orig_category"] = cred.get("category", "login")
                    cred["category"] = "trash"
                else:
                    # Permanent Delete
                    self.data["credentials"] = [
                        c for c in self.data["credentials"] if c["id"] != cred_id
                    ]
                break
        self.save_vault()

    def restore_credential(self, cred_id: str) -> None:
        """Restores a credential from the Trash Bin to its original category."""
        for cred in self.data.get("credentials", []):
            if cred["id"] == cred_id:
                cred["category"] = cred.get("orig_category", "login")
                if "orig_category" in cred:
                    del cred["orig_category"]
                break
        self.save_vault()

    def empty_trash(self) -> None:
        """Permanently deletes all credentials currently in the Trash Bin."""
        self.data["credentials"] = [
            c for c in self.data.get("credentials", []) if c.get("category") != "trash"
        ]
        self.save_vault()

    def initialize_decoy_vault(self, decoy_password: str) -> None:
        """Initializes a decoy vault inside the vault file with dummy credentials."""
        decoy_salt = os.urandom(16)
        decoy_key = derive_key(decoy_password, decoy_salt)
        
        dummy_data = {
            "credentials": [
                {
                    "id": str(uuid.uuid4()),
                    "category": "login",
                    "service": "Facebook",
                    "username": "decoy_user@gmail.com",
                    "password": "decoyPassword123!",
                    "notes": "Decoy social media account."
                },
                {
                    "id": str(uuid.uuid4()),
                    "category": "login",
                    "service": "Netflix",
                    "username": "netflix_decoy",
                    "password": "superSafeDecoyPass",
                    "notes": "Decoy streaming account."
                }
            ]
        }
        
        plaintext_bytes = json.dumps(dummy_data).encode("utf-8")
        fernet = Fernet(decoy_key)
        ciphertext = fernet.encrypt(plaintext_bytes)

        payload = {}
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    payload = json.load(f)
            except Exception:
                pass

        payload["decoy_salt"] = decoy_salt.hex()
        payload["decoy_ciphertext"] = ciphertext.decode("utf-8")

        with open(self.filepath, "w") as f:
            json.dump(payload, f, indent=2)

    def change_master_password(self, current_password: str, new_password: str) -> bool:
        """
        Rotates the vault master password. Verifies the current password first,
        then generates a new salt, derives the new key, re-encrypts the vault data,
        and saves the vault file. Returns True if successful.
        """
        # Verify current password by trying to unlock in a separate temporary instance
        verify_vm = VaultManager(self.filepath)
        if not verify_vm.unlock_vault(current_password):
            return False

        # Generate a new random salt and derive the new key
        self.salt = os.urandom(16)
        self.derived_key = derive_key(new_password, self.salt)
        
        # Save vault (encrypts existing self.data with the new derived_key)
        self.save_vault()
        return True


# ----------------------------------------------------------------------
# SECURE PASSWORD GENERATOR MODULE
# ----------------------------------------------------------------------
def generate_password(
    length: int,
    use_upper: bool,
    use_lower: bool,
    use_digits: bool,
    use_special: bool,
    exclude_ambiguous: bool
) -> str:
    """
    Generates a secure password based on configuration criteria.
    Uses Python's secrets module for cryptographically secure randomness.
    """
    upper_chars = string.ascii_uppercase
    lower_chars = string.ascii_lowercase
    digits_chars = string.digits
    special_chars = "!@#$%^&*()-_=+[]{}|;:,.<>?"

    if exclude_ambiguous:
        ambiguous = "l1Io0O"
        upper_chars = "".join(c for c in upper_chars if c not in ambiguous)
        lower_chars = "".join(c for c in lower_chars if c not in ambiguous)
        digits_chars = "".join(c for c in digits_chars if c not in ambiguous)
        special_chars = "".join(c for c in special_chars if c not in ambiguous)

    chars = ""
    guaranteed = []

    if use_upper:
        chars += upper_chars
        guaranteed.append(secrets.choice(upper_chars))
    if use_lower:
        chars += lower_chars
        guaranteed.append(secrets.choice(lower_chars))
    if use_digits:
        chars += digits_chars
        guaranteed.append(secrets.choice(digits_chars))
    if use_special:
        chars += special_chars
        guaranteed.append(secrets.choice(special_chars))

    if not chars:
        raise ValueError("At least one character set must be selected.")

    remaining_length = length - len(guaranteed)
    if remaining_length < 0:
        password_chars = [secrets.choice(chars) for _ in range(length)]
    else:
        password_chars = guaranteed + [secrets.choice(chars) for _ in range(remaining_length)]
        secrets.SystemRandom().shuffle(password_chars)

    return "".join(password_chars)


WORDLIST = [
    "apple", "banana", "cherry", "danger", "eagle", "forest", "grape", "harbor", "island", "jungle",
    "kitten", "lemon", "mountain", "needle", "ocean", "python", "queen", "river", "shadow", "tiger",
    "umbrella", "valley", "winter", "yellow", "zebra", "active", "bright", "clever", "daring", "eager",
    "friendly", "gentle", "happy", "iconic", "joyful", "keen", "lively", "mighty", "noble", "optim",
    "proud", "quick", "robust", "silent", "tough", "unique", "vibrant", "warm", "young", "zealous",
    "beacon", "canyon", "desert", "emerald", "feather", "glacier", "horizon", "indigo", "journey", "keynote",
    "lantern", "meadow", "nomad", "oasis", "pebble", "quartz", "riddle", "summit", "timber", "universe",
    "vortex", "whisper", "xenon", "yacht", "zenith", "anchor", "bridge", "castle", "dolphin", "echo",
    "falcon", "galaxy", "helmet", "ivory", "jasper", "knight", "legend", "meteor", "nebula", "orchid",
    "planet", "quiver", "runway", "shield", "temple", "utopia", "voyage", "wizard", "yonder", "zodiac",
    "autumn", "breeze", "clover", "dawn", "ember", "frost", "garden", "harvest", "indigo", "jasmine",
    "lunar", "maple", "nectar", "olive", "petal", "ripple", "sunset", "tulip", "velvet", "willow",
    "accent", "bronze", "copper", "detail", "effort", "focus", "growth", "hazard", "impact", "justice",
    "kernel", "legacy", "matrix", "nature", "output", "pattern", "quarry", "relief", "status", "theory",
    "update", "vector", "wisdom", "yield", "zenith", "alpha", "beta", "gamma", "delta", "epsilon",
    "zeta", "eta", "theta", "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron",
    "pi", "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega", "first",
    "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "beacon",
    "carbon", "diesel", "engine", "filter", "garage", "hammer", "jacket", "magnet", "nozzle", "oxygen"
]


def generate_passphrase(words_count: int, separator: str = "-") -> str:
    """Generates a secure, memorable Diceware passphrase from the built-in word list."""
    chosen = [secrets.choice(WORDLIST) for _ in range(words_count)]
    return separator.join(chosen)


def get_password_strength(password: str):
    """Calculates password entropy and returns a strength score, description, and color."""
    if not password:
        return 0.0, "Empty", "#888888"
    
    pool = 0
    if any(c.isupper() for c in password): pool += 26
    if any(c.islower() for c in password): pool += 26
    if any(c.isdigit() for c in password): pool += 10
    if any(c not in (string.ascii_letters + string.digits) for c in password): pool += 32
    if pool == 0: pool = 1
    
    entropy = len(password) * math.log2(pool)
    
    if entropy < 40:
        return entropy, "Very Weak", "#e74c3c"
    elif entropy < 60:
        return entropy, "Weak", "#e67e22"
    elif entropy < 80:
        return entropy, "Medium", "#f1c40f"
    else:
        return entropy, "Strong", "#2ecc71"
