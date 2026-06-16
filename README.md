# Local-First Zero-Trust Password Manager & Secure Vault

A secure, local-first, zero-trust password manager and credentials vault designed to run entirely offline. Built with a high-performance **FastAPI** backend in Python and a modern, responsive **Vanilla HTML/CSS/JS** single-page frontend.

The application operates entirely on your local machine (`localhost`), ensuring that your Master Password, salts, encryption keys, and decrypted credentials never leave your device.

---

## 🛠️ System Stack

- **Backend:** Python 3.10+, FastAPI (Asynchronous Web Framework), Uvicorn (ASGI Server), Cryptography (Fernet/AES-256-CBC, PBKDF2-HMAC-SHA256), Pydantic (Data Validation).
- **Frontend:** HTML5, Vanilla CSS3 (Custom design system, CSS variables, dark/light theme engine), Modern JavaScript (ES6+, Fetch API, custom clipboard controls, inactivity tracking).
- **Database:** Local encrypted JSON store (`vault.json`).

---

## 🔒 Security Architecture & Features

### 1. Zero-Trust Cryptography
- **Key Derivation:** Uses **PBKDF2-HMAC-SHA256** with 100,000 iterations to derive a secure 256-bit encryption key from your Master Password and a cryptographically secure random 16-byte salt.
- **Payload Encryption:** Credentials are encrypted and decrypted locally using **Fernet (AES-128/256 in CBC mode with HMAC-SHA256)**.
- **Privacy:** No cloud synchronization, no remote telemetry, and zero external network dependencies.

### 2. Plausible Deniability (Duress Vault / Decoy Mode)
- Configure an alternate decoy Master Password in the Settings panel.
- Entering this decoy password during authentication unlocks an isolated, decoy vault containing pre-configured fake credentials.
- Decoy vaults utilize an independent random salt and key derivation path, making them cryptographically indistinguishable from the primary vault.

### 3. Panic Self-Destruct
- Tracks consecutive failed authentication attempts locally.
- Upon the **5th consecutive failed attempt**, a panic sequence is executed: the vault database file (`vault.json`) is securely shredded by overwriting it with cryptographically secure random bytes (`os.urandom`) and deleted from the storage disk before the request is rejected.

### 4. Password History & Rotation
- Tracks the last 5 passwords for credentials to prevent lockout or loss of access during credential rotation.

### 5. Multi-Category Schemas
- Specialized views with dedicated form fields:
  - **🔑 Logins:** Website/Service URL, Username, Password, Custom Notes.
  - **💳 Credit Cards:** Cardholder Name, Card Number, CVV, PIN, Expiration Date.
  - **👤 Identities:** Full Name, Email, Phone Number, Address.
  - **📝 Secure Notes:** Custom text-box formatted notes.

### 6. Trash Bin (Soft Deletions)
- Deleted credentials are moved to the Trash Bin where they can be restored, permanently purged individually, or wiped entirely via the **Empty Trash** action.

### 7. Memorable Diceware Generator
- Generates secure, memorable, offline passphrases using a built-in dictionary list.
- Configurable word counts (3 to 12 words) and custom separators (e.g. `correct-horse-battery-staple`).

### 8. Real-time Entropy Meter
- Calculates real-time Shannon entropy for standard passwords and passphrases.
- Displays dynamic color-coded indicators representing password strength (Very Weak, Weak, Medium, Strong).

### 9. Automatic Security Safeguards
- **Clipboard Auto-Clear:** Clears copied credentials from the system clipboard after a configurable delay (default: 30 seconds) to prevent clipboard theft.
- **Inactivity Auto-Lock:** Monitors mouse movement and keyboard input, automatically locking the vault and destroying in-memory encryption keys after a configurable timeout (default: 5 minutes).

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher.
- A modern web browser.

### Installation & Launch

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/hemanthsrisai3/Password-Manager.git
   cd Password-Manager
   ```

2. **Run the Application Launcher:**
   Execute the launcher script. The script automatically manages the environment setup: it will detect if a local virtual environment exists, create `.venv` if needed, install all necessary dependencies locally, and run the backend server under the isolated environment before opening the browser.
   ```bash
   python run.py
   ```

3. **Access the Web Interface:**
   If your browser does not open automatically, navigate to:
   [http://localhost:8000](http://localhost:8000)

---

## 🧪 Testing & Diagnostics

### Running Unit Tests
To run the automated FastAPI endpoint test suite directly:
```bash
.venv/Scripts/python -m unittest backend.tests.test_api
```
*(On Unix/macOS, use `.venv/bin/python -m unittest backend.tests.test_api`)*

### Robustness & Load Verification
To execute the robustness test suite, which runs the endpoint test matrix 1,000 times (13,000 assertions) to ensure consistent performance under memory and CPU loads:
```bash
python run_load_tests.py
```

---

## ⚠️ Security Notice & Backups
This application is local-first: **there is no cloud recovery option**. If you lose or forget your Master Password, or if the Panic Self-Destruct sequence is triggered, your credentials will be permanently lost. It is highly recommended to maintain secure offline backups of your `vault.json` database in a secondary location.
