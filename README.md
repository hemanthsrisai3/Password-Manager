# Zero-Trust Password Manager & Secure Vault

A secure, local-first, zero-trust password manager and credentials vault. Built as a full-stack desktop application using a **FastAPI** backend in Python and a responsive **Vanilla HTML/CSS/JS** single-page frontend.

The application runs entirely on your local machine (`localhost`), ensuring that your Master Password, salts, and decrypted credentials never leave your device.

---

## 🛠️ Tech Stack
*   **Backend:** Python 3.10+, FastAPI, Uvicorn, Cryptography (Fernet/PBKDF2HMAC), Pydantic.
*   **Frontend:** HTML5, Vanilla CSS3 (Custom styling, variables, light/dark theme support), Modern Javascript (ES6+, Fetch API, activity listeners, clipboard controls).
*   **Database:** Local encrypted JSON store (`vault.json`).

---

## 🔒 Security & Features

### 1. Zero-Trust Cryptography
*   Uses **PBKDF2-HMAC-SHA256** with 100,000 iterations to derive a 256-bit encryption key from your Master Password and a secure random 16-byte salt.
*   All credential payloads are encrypted/decrypted locally using **Fernet (AES-128/256 in CBC mode with HMAC-SHA256)**.
*   No cloud sync, no tracking, and no external requests.

### 2. Plausible Deniability (Decoy Vault / Duress Mode)
*   Define a decoy Master Password in settings. 
*   Entering this decoy password on the login screen unlocks an isolated decoy vault containing fake, realistic credentials (e.g. Netflix, Facebook).
*   The decoy vault verification utilizes an independent salt and key derivation, making it cryptographically indistinguishable from the primary vault.

### 3. Panic Self-Destruct
*   Tracks consecutive failed login attempts in configuration.
*   Upon the **5th consecutive failed attempt**, a panic sequence is triggered: the vault file (`vault.json`) is securely shredded by overwriting it with random bytes (`os.urandom`) and deleted from disk before the server rejects the request.

### 4. Password History & Rotation
*   Tracks the last 5 passwords for any login account to prevent losing access to rotated credentials.

### 5. Multi-Category Support
*   Specialized categories with dedicated UI fields:
    *   **🔑 Logins:** Website/Service, Username, Password, Notes.
    *   **💳 Credit Cards:** Cardholder Name, Card Number, CVV, PIN, Expiry.
    *   **👤 Identities:** Name, Email, Phone, Address.
    *   **📝 Secure Notes:** Custom text-box formatted notes.

### 6. Trash Bin (Soft Deletes)
*   Deleted credentials are moved to the Trash Bin.
*   Trash items can be restored to their original category, permanently deleted individually, or purged all at once via the **Empty Trash** button.

### 7. Memorable Diceware Passphrase Generator
*   Generates secure, offline passphrases using a built-in list of 200 curated words.
*   Supports word count configuration (3 to 12 words) and custom separators (e.g., `correct-horse-battery-staple`).

### 8. Visual Password Strength Meter
*   Calculates real-time Shannon entropy for standard passwords and passphrases.
*   Displays dynamic color indicators (Very Weak, Weak, Medium, Strong) under the inputs.

### 9. Automatic Clipboard & Inactivity Locks
*   **Clipboard Auto-Clear:** Clears copied passwords from the system clipboard after a configurable delay (default: 30 seconds).
*   **Inactivity Auto-Lock:** Monitors local mouse/keyboard activity and automatically locks the vault after a timeout (default: 5 minutes).

---

## 🚀 Getting Started

### Prerequisites
*   Python 3.10 or higher.
*   A web browser.

### Installation & Launch

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/wonderful-volta.git
    cd wonderful-volta
    ```

2.  **Run the Application:**
    Simply run the launcher script. It will automatically check, create a virtual environment if needed, install dependencies, spin up the backend server, and open your default browser:
    ```bash
    python run.py
    ```

3.  **Access the Web UI:**
    If your browser does not open automatically, navigate to:
    [http://localhost:8000](http://localhost:8000)

---

## 🧪 Testing

### Running Unit Tests
To run the automated FastAPI endpoint test suite:
```bash
.venv/bin/python -m unittest backend.tests.test_api
```
*(On Windows, use `.venv\Scripts\python -m unittest backend.tests.test_api`)*

### 1,000x Robustness Execution
To run the loop execution harness to verify that all API endpoints perform with a 100% success rate across 13,000 distinct tests:
```bash
python run_load_tests.py
```

---

## ⚠️ Security Warning & Backups
Since this manager is local-first, **there is no cloud recovery option**. If you forget your Master Password, or if the Panic Self-Destruct is triggered, your credentials will be lost forever. It is highly recommended to maintain encrypted backups of your `vault.json` database in a secure secondary location.
