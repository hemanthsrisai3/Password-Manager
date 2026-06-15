#!/usr/bin/env python3
"""
Zero-Trust Password Manager - FastAPI Backend Server
"""

import os
import secrets
import sys
from typing import Optional, Dict, Any

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

from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.core import (
    VaultManager,
    load_config,
    save_config,
    generate_password,
    generate_passphrase,
    get_password_strength,
    secure_delete_file,
    VAULT_FILENAME
)

app = FastAPI(
    title="Zero-Trust Password Manager API",
    description="Local backend API server managing the zero-trust credentials vault.",
    version="1.0.0"
)

# Enable CORS for local development (if frontend is hosted on another port during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
vault = VaultManager(VAULT_FILENAME)
active_session_token: Optional[str] = None

# Pydantic models
class PasswordModel(BaseModel):
    password: str

class DecoySetupModel(BaseModel):
    password: str

class ChangePasswordModel(BaseModel):
    current_password: str
    new_password: str

class ConfigUpdateModel(BaseModel):
    theme_mode: str
    accent_color: str
    clipboard_timeout: int
    autolock_timeout: int

class CredentialModel(BaseModel):
    service: str
    username: str
    password: str
    notes: Optional[str] = ""
    category: Optional[str] = "login"
    custom_fields: Optional[Dict[str, Any]] = None

class StrengthCheckModel(BaseModel):
    password: str

# Helper to verify session token and vault unlock state
def verify_session(x_session_token: Optional[str] = Header(None)):
    global active_session_token
    if not vault.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vault is not initialized."
        )
    if not vault.derived_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vault is locked."
        )
    if not active_session_token or x_session_token != active_session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token."
        )
    return active_session_token

# ----------------------------------------------------------------------
# API ROUTES
# ----------------------------------------------------------------------

@app.get("/api/status")
def get_status():
    """Returns whether the vault exists and is unlocked."""
    exists = vault.exists()
    unlocked = vault.derived_key is not None
    config = load_config()
    return {
        "exists": exists,
        "unlocked": unlocked,
        "theme_mode": config.get("theme_mode", "dark"),
        "accent_color": config.get("accent_color", "#00adb5")
    }

@app.post("/api/init")
def initialize(payload: PasswordModel):
    """Initializes a new vault with the provided Master Password."""
    global active_session_token
    if vault.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vault already exists."
        )
    
    try:
        vault.initialize_vault(payload.password)
        # Reset failed attempts on init
        config = load_config()
        config["failed_attempts"] = 0
        save_config(config)
        
        active_session_token = secrets.token_hex(32)
        return {
            "message": "Vault initialized successfully.",
            "token": active_session_token,
            "config": config
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize vault: {str(e)}"
        )

@app.post("/api/unlock")
def unlock(payload: PasswordModel):
    """Unlocks the vault. Increments failed attempts and triggers self-destruct if invalid 5 times."""
    global active_session_token
    if not vault.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vault does not exist. Initialize it first."
        )
    
    config = load_config()
    
    success = vault.unlock_vault(payload.password)
    if not success:
        # Increment failed attempts
        attempts = config.get("failed_attempts", 0) + 1
        config["failed_attempts"] = attempts
        save_config(config)
        
        # Self-destruct if attempts >= 5
        if attempts >= 5:
            secure_delete_file(vault.filepath)
            # Reset failed attempts after wipe
            config["failed_attempts"] = 0
            save_config(config)
            # Invalidate session
            active_session_token = None
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Panic Self-Destruct triggered! The vault has been securely shredded due to 5 failed login attempts."
            )
        
        remaining = 5 - attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect master password. {remaining} attempts remaining before self-destruct."
        )
    
    # Reset failed attempts on success
    config["failed_attempts"] = 0
    save_config(config)
    
    active_session_token = secrets.token_hex(32)
    return {
        "message": "Vault unlocked successfully.",
        "token": active_session_token,
        "config": config,
        "is_decoy": vault.is_decoy
    }

@app.post("/api/lock")
def lock():
    """Locks the vault, clearing keys and invalidating the token."""
    global active_session_token
    vault.derived_key = None
    vault.salt = None
    vault.data = {"credentials": []}
    vault.is_decoy = False
    active_session_token = None
    return {"message": "Vault locked successfully."}

@app.get("/api/config", dependencies=[Depends(verify_session)])
def get_current_config():
    """Returns the current vault configuration settings."""
    return load_config()

@app.post("/api/config", dependencies=[Depends(verify_session)])
def update_current_config(payload: ConfigUpdateModel):
    """Updates the config settings."""
    config = load_config()
    config["theme_mode"] = payload.theme_mode
    config["accent_color"] = payload.accent_color
    config["clipboard_timeout"] = payload.clipboard_timeout
    config["autolock_timeout"] = payload.autolock_timeout
    save_config(config)
    return {"message": "Configuration updated successfully.", "config": config}

@app.post("/api/config/decoy", dependencies=[Depends(verify_session)])
def setup_decoy(payload: DecoySetupModel):
    """Initializes the decoy vault under a secondary duress password."""
    if vault.is_decoy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot set up a decoy vault from within the decoy environment itself."
        )
    try:
        vault.initialize_decoy_vault(payload.password)
        return {"message": "Decoy vault configured successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure decoy vault: {str(e)}"
        )

@app.post("/api/config/change-password", dependencies=[Depends(verify_session)])
def change_password(payload: ChangePasswordModel):
    """Changes/rotates the primary master password."""
    if vault.is_decoy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password rotation is disabled in decoy mode."
        )
    success = vault.change_master_password(payload.current_password, payload.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current master password verification failed."
        )
    return {"message": "Master password rotated successfully."}

@app.get("/api/credentials", dependencies=[Depends(verify_session)])
def get_credentials():
    """Gets all credentials currently stored in the unlocked vault database."""
    return vault.data.get("credentials", [])

@app.post("/api/credentials", dependencies=[Depends(verify_session)])
def add_new_credential(payload: CredentialModel):
    """Adds a new credential to the vault database."""
    extra_fields = payload.custom_fields or {}
    try:
        cred = vault.add_credential(
            service=payload.service,
            username=payload.username,
            password=payload.password,
            notes=payload.notes or "",
            category=payload.category or "login",
            **extra_fields
        )
        return {"message": "Credential added successfully.", "credential": cred}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add credential: {str(e)}"
        )

@app.put("/api/credentials/{cred_id}", dependencies=[Depends(verify_session)])
def update_existing_credential(cred_id: str, payload: CredentialModel):
    """Updates an existing credential in the vault database."""
    extra_fields = payload.custom_fields or {}
    try:
        # Check if credential exists
        exists = any(c["id"] == cred_id for c in vault.data.get("credentials", []))
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found."
            )
        
        vault.update_credential(
            cred_id=cred_id,
            service=payload.service,
            username=payload.username,
            password=payload.password,
            notes=payload.notes or "",
            **extra_fields
        )
        return {"message": "Credential updated successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update credential: {str(e)}"
        )

@app.delete("/api/credentials/{cred_id}", dependencies=[Depends(verify_session)])
def delete_existing_credential(cred_id: str):
    """Soft-deletes a credential by moving it to the Trash, or permanently deletes it if already in Trash."""
    try:
        exists = any(c["id"] == cred_id for c in vault.data.get("credentials", []))
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found."
            )
        
        vault.delete_credential(cred_id)
        return {"message": "Credential deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete credential: {str(e)}"
        )

@app.post("/api/credentials/{cred_id}/restore", dependencies=[Depends(verify_session)])
def restore_existing_credential(cred_id: str):
    """Restores a soft-deleted credential from the Trash Bin."""
    try:
        exists = any(c["id"] == cred_id for c in vault.data.get("credentials", []))
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found."
            )
        
        vault.restore_credential(cred_id)
        return {"message": "Credential restored successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore credential: {str(e)}"
        )

@app.post("/api/credentials/empty-trash", dependencies=[Depends(verify_session)])
def clear_all_trash():
    """Permanently empties all credentials currently inside the Trash Bin."""
    try:
        vault.empty_trash()
        return {"message": "Trash emptied successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to empty trash: {str(e)}"
        )

# Generators (Public endpoints for UI utility or session-validated)
@app.get("/api/generate/password")
def api_generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_special: bool = True,
    exclude_ambiguous: bool = False
):
    """Generates a secure password based on parameters."""
    try:
        pwd = generate_password(
            length=length,
            use_upper=use_upper,
            use_lower=use_lower,
            use_digits=use_digits,
            use_special=use_special,
            exclude_ambiguous=exclude_ambiguous
        )
        return {"password": pwd}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@app.get("/api/generate/passphrase")
def api_generate_passphrase(words_count: int = 4, separator: str = "-"):
    """Generates a secure memorable Diceware passphrase."""
    try:
        phrase = generate_passphrase(words_count=words_count, separator=separator)
        return {"passphrase": phrase}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/api/generate/strength")
def api_check_strength(payload: StrengthCheckModel):
    """Calculates the strength details of a password input."""
    entropy, label, color = get_password_strength(payload.password)
    return {
        "entropy": round(entropy, 2),
        "label": label,
        "color": color
    }

# ----------------------------------------------------------------------
# STATIC FILE SERVING
# ----------------------------------------------------------------------
# Mount frontend directory to serve the Single Page Web Application
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    # If starting server from backend/ directory
    alternative_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
    if os.path.exists(alternative_frontend):
        app.mount("/", StaticFiles(directory=alternative_frontend, html=True), name="frontend")
