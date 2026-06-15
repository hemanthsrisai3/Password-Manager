// ----------------------------------------------------------------------
// APPLICATION STATE
// ----------------------------------------------------------------------
let sessionToken = null;
let credentials = [];
let activeCategory = 'all'; // all, login, credit_card, identity, secure_note, generator, trash
let searchQuery = '';
let config = {
    theme_mode: 'dark',
    accent_color: '#00adb5',
    clipboard_timeout: 30,
    autolock_timeout: 5
};
let isDecoy = false;

// Timers
let autoLockTimer = null;
let clipboardTimer = null;
let lastCopiedText = null;

// DOM Elements
const appContainer = document.getElementById('app-container');
const setupView = document.getElementById('setup-view');
const loginView = document.getElementById('login-view');
const dashboardView = document.getElementById('dashboard-view');
const generatorTab = document.getElementById('generator-tab');
const vaultListContainer = document.getElementById('vault-list-container');
const credentialsGrid = document.getElementById('credentials-grid');
const emptyState = document.getElementById('empty-state');
const searchInput = document.getElementById('search-input');
const searchContainer = document.getElementById('search-container');

// Forms & Inputs
const setupForm = document.getElementById('setup-form');
const loginForm = document.getElementById('login-form');
const credentialForm = document.getElementById('credential-form');
const setupPasswordInput = document.getElementById('setup-password');
const setupConfirmInput = document.getElementById('setup-confirm');
const loginPasswordInput = document.getElementById('login-password');
const loginError = document.getElementById('login-error');

// Modals
const credentialModal = document.getElementById('credential-modal');
const settingsModal = document.getElementById('settings-modal');
const credCategorySelect = document.getElementById('cred-category');
const credServiceInput = document.getElementById('cred-service');
const credNotesInput = document.getElementById('cred-notes');
const categoryFieldsContainer = document.getElementById('category-fields-container');
const passwordHistoryContainer = document.getElementById('password-history-container');
const passwordHistoryList = document.getElementById('password-history-list');

// Settings Fields
const settingsAccent = document.getElementById('settings-accent');
const settingsAutolock = document.getElementById('settings-autolock');
const settingsClipboard = document.getElementById('settings-clipboard');
const autolockVal = document.getElementById('autolock-val');
const clipboardVal = document.getElementById('clipboard-val');
const changePasswordForm = document.getElementById('change-password-form');
const setupDecoyForm = document.getElementById('setup-decoy-form');

// Buttons
const addCredentialBtn = document.getElementById('add-credential-btn');
const emptyTrashBtn = document.getElementById('empty-trash-btn');
const sidebarSettingsBtn = document.getElementById('sidebar-settings-btn');
const sidebarLockBtn = document.getElementById('sidebar-lock-btn');
const themeDarkBtn = document.getElementById('theme-dark-btn');
const themeLightBtn = document.getElementById('theme-light-btn');

// Generator Elements
const genOutput = document.getElementById('generator-output');
const genLengthSlider = document.getElementById('gen-length');
const genLengthVal = document.getElementById('length-val');
const genUpperChk = document.getElementById('gen-upper');
const genLowerChk = document.getElementById('gen-lower');
const genDigitsChk = document.getElementById('gen-digits');
const genSpecialChk = document.getElementById('gen-special');
const genAmbiguousChk = document.getElementById('gen-ambiguous');
const dicewareCountSlider = document.getElementById('diceware-count');
const dicewareCountVal = document.getElementById('diceware-count-val');
const dicewareSeparatorInput = document.getElementById('diceware-separator');
const generateTriggerBtn = document.getElementById('generate-trigger-btn');
const copyGeneratedBtn = document.getElementById('copy-generated-btn');
const strengthMeter = document.getElementById('strength-meter');
const strengthLabel = document.getElementById('strength-label');

let activeGenMode = 'standard'; // standard or diceware

// ----------------------------------------------------------------------
// INITIALIZATION
// ----------------------------------------------------------------------
window.addEventListener('DOMContentLoaded', async () => {
    await checkVaultStatus();
    setupEventListeners();
    setupActivityListeners();
});

// Check status of vault at start
async function checkVaultStatus() {
    try {
        const res = await fetch('/api/status');
        const status = await res.json();
        
        applyThemeSettings(status.theme_mode, status.accent_color);
        
        if (!status.exists) {
            showView('setup');
        } else if (!status.unlocked) {
            showView('login');
        } else {
            // Already unlocked (e.g. page refreshed while server active)
            showView('login'); // Secure fallback: enforce login on fresh browser reload
        }
    } catch (err) {
        showToast('Connection to backend failed!', 'error');
    }
}

// ----------------------------------------------------------------------
// THEMING & ACCENT COLORS
// ----------------------------------------------------------------------
function applyThemeSettings(mode, color) {
    config.theme_mode = mode || 'dark';
    config.accent_color = color || '#00adb5';
    
    // Apply theme class to body
    document.body.className = config.theme_mode === 'dark' ? 'dark-theme' : 'light-theme';
    
    // Inject accent color CSS variable
    document.documentElement.style.setProperty('--accent-color', config.accent_color);
    
    // Compute dark hover variant
    const hoverColor = adjustColorBrightness(config.accent_color, -15);
    document.documentElement.style.setProperty('--accent-hover', hoverColor);
    
    // Update color picker value
    if (settingsAccent) {
        settingsAccent.value = config.accent_color;
    }
    
    // Update theme toggle buttons in settings modal
    if (mode === 'dark') {
        themeDarkBtn.classList.add('active');
        themeLightBtn.classList.remove('active');
    } else {
        themeLightBtn.classList.add('active');
        themeDarkBtn.classList.remove('active');
    }
}

// Adjust brightness of hex color (percentage: e.g. -15 for 15% darker)
function adjustColorBrightness(hex, percent) {
    let R = parseInt(hex.substring(1, 3), 16);
    let G = parseInt(hex.substring(3, 5), 16);
    let B = parseInt(hex.substring(5, 7), 16);

    R = parseInt(R * (100 + percent) / 100);
    G = parseInt(G * (100 + percent) / 100);
    B = parseInt(B * (100 + percent) / 100);

    R = (R < 255) ? R : 255;
    G = (G < 255) ? G : 255;
    B = (B < 255) ? B : 255;

    R = (R > 0) ? R : 0;
    G = (G > 0) ? G : 0;
    B = (B > 0) ? B : 0;

    const rHex = R.toString(16).padStart(2, '0');
    const gHex = G.toString(16).padStart(2, '0');
    const bHex = B.toString(16).padStart(2, '0');

    return `#${rHex}${gHex}${bHex}`;
}

// ----------------------------------------------------------------------
// VIEW NAVIGATION
// ----------------------------------------------------------------------
function showView(view) {
    setupView.classList.add('hidden');
    loginView.classList.add('hidden');
    dashboardView.classList.add('hidden');
    
    if (view === 'setup') {
        setupView.classList.remove('hidden');
    } else if (view === 'login') {
        loginView.classList.remove('hidden');
        loginPasswordInput.value = '';
        loginPasswordInput.focus();
    } else if (view === 'dashboard') {
        dashboardView.classList.remove('hidden');
        switchCategory(activeCategory);
    }
}

function switchCategory(cat) {
    activeCategory = cat;
    
    // Update active nav items
    document.querySelectorAll('.nav-item').forEach(btn => {
        if (btn.getAttribute('data-category') === cat) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // Toggle main content sections
    if (cat === 'generator') {
        generatorTab.classList.remove('hidden');
        vaultListContainer.classList.add('hidden');
        searchContainer.classList.add('hidden');
        addCredentialBtn.classList.add('hidden');
        emptyTrashBtn.classList.add('hidden');
        generatePasswordInTab();
    } else {
        generatorTab.classList.add('hidden');
        vaultListContainer.classList.remove('hidden');
        searchContainer.classList.remove('hidden');
        
        if (cat === 'trash') {
            addCredentialBtn.classList.add('hidden');
            emptyTrashBtn.classList.remove('hidden');
        } else {
            addCredentialBtn.classList.remove('hidden');
            emptyTrashBtn.classList.add('hidden');
        }
        
        renderCredentialsGrid();
    }
}

// ----------------------------------------------------------------------
// EVENT LISTENERS CONFIG
// ----------------------------------------------------------------------
function setupEventListeners() {
    // 1. Setup Form Submit
    setupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const pwd = setupPasswordInput.value;
        const confirm = setupConfirmInput.value;
        if (pwd !== confirm) {
            showToast('Passwords do not match!', 'error');
            return;
        }
        try {
            const res = await fetch('/api/init', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: pwd })
            });
            const data = await res.json();
            if (res.ok) {
                sessionToken = data.token;
                applyConfig(data.config);
                showToast('Vault initialized successfully!', 'success');
                showView('dashboard');
                loadCredentials();
            } else {
                showToast(data.detail || 'Initialization failed.', 'error');
            }
        } catch (err) {
            showToast('API error initializing vault.', 'error');
        }
    });

    // 2. Login Form Submit
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const pwd = loginPasswordInput.value;
        try {
            const res = await fetch('/api/unlock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: pwd })
            });
            const data = await res.json();
            if (res.ok) {
                sessionToken = data.token;
                isDecoy = data.is_decoy;
                applyConfig(data.config);
                loginError.classList.add('hidden');
                
                if (isDecoy) {
                    showToast('Unlocked Decoy Vault (Duress Mode)', 'warning');
                } else {
                    showToast('Vault unlocked successfully!', 'success');
                }
                
                showView('dashboard');
                loadCredentials();
            } else {
                if (res.status === 410) {
                    // Self destructed
                    loginError.textContent = 'WARNING: Vault self-destructed and was shredded!';
                    loginError.classList.remove('hidden');
                    showToast('Vault wiped due to security lockout!', 'error');
                    setTimeout(() => {
                        window.location.reload();
                    }, 4000);
                } else {
                    loginError.textContent = data.detail || 'Incorrect password.';
                    loginError.classList.remove('hidden');
                    loginPasswordInput.value = '';
                    loginPasswordInput.focus();
                }
            }
        } catch (err) {
            showToast('API error unlocking vault.', 'error');
        }
    });

    // 3. Category Switching Buttons
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const cat = e.currentTarget.getAttribute('data-category');
            switchCategory(cat);
        });
    });

    // 4. Search Filter
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase().trim();
        renderCredentialsGrid();
    });

    // 5. Add Credential Trigger
    addCredentialBtn.addEventListener('click', () => {
        openCredentialModal();
    });

    // 6. Empty Trash Trigger
    emptyTrashBtn.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to permanently delete all items in the Trash Bin? This action is irreversible.')) {
            return;
        }
        try {
            const res = await fetch('/api/credentials/empty-trash', {
                method: 'POST',
                headers: getHeaders()
            });
            if (res.ok) {
                showToast('Trash Bin emptied successfully!', 'success');
                loadCredentials();
            } else {
                showToast('Failed to empty trash.', 'error');
            }
        } catch (err) {
            showToast('API error emptying trash.', 'error');
        }
    });

    // 7. Lock Button
    sidebarLockBtn.addEventListener('click', lockVault);

    // 8. Settings Modals Trigger
    sidebarSettingsBtn.addEventListener('click', () => {
        openSettingsModal();
    });

    // 9. Close Modal Triggers
    document.getElementById('modal-close-btn').addEventListener('click', () => {
        credentialModal.classList.add('hidden');
    });
    document.getElementById('modal-cancel-btn').addEventListener('click', () => {
        credentialModal.classList.add('hidden');
    });
    document.getElementById('settings-close-btn').addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });

    // 10. Dynamic Category Fields
    credCategorySelect.addEventListener('change', (e) => {
        renderCategoryFields(e.target.value);
    });

    // 11. Save Credential Submit
    credentialForm.addEventListener('submit', handleSaveCredential);

    // 12. Settings Accent Color Selection
    settingsAccent.addEventListener('input', (e) => {
        applyThemeSettings(config.theme_mode, e.target.value);
    });

    // 13. Settings Timeout Sliders
    settingsAutolock.addEventListener('input', (e) => {
        autolockVal.textContent = e.target.value;
    });
    settingsClipboard.addEventListener('input', (e) => {
        clipboardVal.textContent = e.target.value;
    });

    // 14. Theme Toggle buttons
    themeDarkBtn.addEventListener('click', () => applyThemeSettings('dark', config.accent_color));
    themeLightBtn.addEventListener('click', () => applyThemeSettings('light', config.accent_color));

    // 15. Settings Modal Save (Triggers actual config update on server)
    document.getElementById('settings-save-btn').addEventListener('click', saveSettingsOnServer);

    // 16. Master Password Rotation Form
    changePasswordForm.addEventListener('submit', handleRotatePassword);

    // 17. Decoy Vault Configuration Form
    setupDecoyForm.addEventListener('submit', handleSetupDecoy);

    // 18. Generator Settings Inputs
    genLengthSlider.addEventListener('input', (e) => {
        genLengthVal.textContent = e.target.value;
        if (activeGenMode === 'standard') {
            generatePasswordInTab();
        }
    });
    dicewareCountSlider.addEventListener('input', (e) => {
        dicewareCountVal.textContent = e.target.value;
        if (activeGenMode === 'diceware') {
            generatePasswordInTab();
        }
    });

    // 19. Generator Mode Tabs
    document.querySelectorAll('.gen-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.gen-tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            activeGenMode = e.target.getAttribute('data-gen-mode');
            if (activeGenMode === 'standard') {
                document.getElementById('standard-generator-settings').classList.remove('hidden');
                document.getElementById('diceware-generator-settings').classList.add('hidden');
                generateTriggerBtn.textContent = 'Generate Password';
            } else {
                document.getElementById('standard-generator-settings').classList.add('hidden');
                document.getElementById('diceware-generator-settings').classList.remove('hidden');
                generateTriggerBtn.textContent = 'Generate Passphrase';
            }
            generatePasswordInTab();
        });
    });

    // 20. Generator Copy & Trigger
    generateTriggerBtn.addEventListener('click', generatePasswordInTab);
    copyGeneratedBtn.addEventListener('click', () => {
        copyToClipboard(genOutput.value);
    });
}

// ----------------------------------------------------------------------
// SESSION CONFIG RETRIEVAL
// ----------------------------------------------------------------------
function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken
    };
}

function applyConfig(cfg) {
    config = cfg;
    applyThemeSettings(config.theme_mode, config.accent_color);
    
    if (settingsAutolock) {
        settingsAutolock.value = config.autolock_timeout;
        autolockVal.textContent = config.autolock_timeout;
    }
    if (settingsClipboard) {
        settingsClipboard.value = config.clipboard_timeout;
        clipboardVal.textContent = config.clipboard_timeout;
    }
    resetAutoLockTimer();
}

// ----------------------------------------------------------------------
// DATA EXCHANGE (API CALLS)
// ----------------------------------------------------------------------
async function loadCredentials() {
    try {
        const res = await fetch('/api/credentials', { headers: getHeaders() });
        if (res.ok) {
            credentials = await res.json();
            renderCredentialsGrid();
        } else {
            showToast('Failed to fetch credentials.', 'error');
            if (res.status === 401) {
                lockVault();
            }
        }
    } catch (err) {
        showToast('Error loading credentials.', 'error');
    }
}

// ----------------------------------------------------------------------
// RENDER CREDENTIAL CARDS
// ----------------------------------------------------------------------
function renderCredentialsGrid() {
    credentialsGrid.innerHTML = '';
    
    // Filter credentials
    const filtered = credentials.filter(cred => {
        // Category Filter
        if (activeCategory !== 'all') {
            if (cred.category !== activeCategory) {
                return false;
            }
        } else {
            // "all" category excludes soft-deleted items (trash)
            if (cred.category === 'trash') {
                return false;
            }
        }
        
        // Search Filter
        if (searchQuery) {
            const service = (cred.service || '').toLowerCase();
            const username = (cred.username || '').toLowerCase();
            const notes = (cred.notes || '').toLowerCase();
            
            // card specific custom field checks
            let extraMatch = false;
            if (cred.cardholder) extraMatch = extraMatch || cred.cardholder.toLowerCase().includes(searchQuery);
            if (cred.email) extraMatch = extraMatch || cred.email.toLowerCase().includes(searchQuery);
            if (cred.name) extraMatch = extraMatch || cred.name.toLowerCase().includes(searchQuery);
            
            return service.includes(searchQuery) || username.includes(searchQuery) || notes.includes(searchQuery) || extraMatch;
        }
        
        return true;
    });

    if (filtered.length === 0) {
        emptyState.classList.remove('hidden');
        credentialsGrid.classList.add('hidden');
        return;
    }

    emptyState.classList.add('hidden');
    credentialsGrid.classList.remove('hidden');

    filtered.forEach(cred => {
        const card = document.createElement('div');
        card.className = 'cred-card';
        
        // Build card fields based on category
        let fieldsHtml = '';
        if (cred.category === 'login') {
            fieldsHtml = `
                <div class="card-field-row">
                    <span class="field-label">Username</span>
                    <div class="field-value-group">
                        <span class="field-value">${escapeHtml(cred.username)}</span>
                        <button class="btn-icon" onclick="copyToClipboard('${escapeJs(cred.username)}')">📋</button>
                    </div>
                </div>
                <div class="card-field-row">
                    <span class="field-label">Password</span>
                    <div class="field-value-group">
                        <span class="field-value masked" id="pw-${cred.id}">••••••••</span>
                        <div style="display:flex; gap: 4px;">
                            <button class="btn-icon" onclick="toggleFieldMasking('${cred.id}', '${escapeJs(cred.password)}')">👁️</button>
                            <button class="btn-icon" onclick="copyToClipboard('${escapeJs(cred.password)}')">📋</button>
                        </div>
                    </div>
                </div>
            `;
        } else if (cred.category === 'credit_card') {
            fieldsHtml = `
                <div class="card-field-row">
                    <span class="field-label">Cardholder</span>
                    <div class="field-value-group">
                        <span class="field-value">${escapeHtml(cred.cardholder || '')}</span>
                    </div>
                </div>
                <div class="card-field-row">
                    <span class="field-label">Card Number</span>
                    <div class="field-value-group">
                        <span class="field-value masked" id="num-${cred.id}">•••• •••• •••• ••••</span>
                        <div style="display:flex; gap: 4px;">
                            <button class="btn-icon" onclick="toggleCardNumberMasking('${cred.id}', '${escapeJs(cred.card_number || '')}')">👁️</button>
                            <button class="btn-icon" onclick="copyToClipboard('${escapeJs(cred.card_number || '')}')">📋</button>
                        </div>
                    </div>
                </div>
                <div class="card-field-row">
                    <span class="field-label">CVV / PIN / Expiry</span>
                    <div class="field-value-group">
                        <span class="field-value">CVV: <span class="masked" id="cvv-${cred.id}">•••</span> | PIN: <span class="masked" id="pin-${cred.id}">••••</span> | Exp: ${escapeHtml(cred.expiry || '')}</span>
                        <div style="display:flex; gap: 4px;">
                            <button class="btn-icon" onclick="toggleCvvPinMasking('${cred.id}', '${escapeJs(cred.cvv || '')}', '${escapeJs(cred.pin || '')}')">👁️</button>
                            <button class="btn-icon" onclick="copyToClipboard('${escapeJs(cred.pin || '')}')" title="Copy PIN">📋</button>
                        </div>
                    </div>
                </div>
            `;
        } else if (cred.category === 'identity') {
            fieldsHtml = `
                <div class="card-field-row">
                    <span class="field-label">Full Name / Email</span>
                    <div class="field-value-group">
                        <span class="field-value">${escapeHtml(cred.name || '')} (${escapeHtml(cred.email || '')})</span>
                        <button class="btn-icon" onclick="copyToClipboard('${escapeJs(cred.email || '')}')">📋</button>
                    </div>
                </div>
                <div class="card-field-row">
                    <span class="field-label">Phone / Address</span>
                    <div class="field-value-group">
                        <span class="field-value" style="font-size:0.85rem;">Ph: ${escapeHtml(cred.phone || '')}<br>Add: ${escapeHtml(cred.address || '')}</span>
                        <button class="btn-icon" onclick="copyToClipboard('${escapeJs(cred.address || '')}')">📋</button>
                    </div>
                </div>
            `;
        } else if (cred.category === 'secure_note') {
            fieldsHtml = `
                <div class="card-field-row">
                    <span class="field-label">Secure Note Content</span>
                    <div class="field-value-group" style="align-items:flex-start; margin-top: 4px;">
                        <textarea readonly rows="4" class="field-value" style="width:100%; max-width:100%; font-size:0.85rem; padding: 6px; resize:none;">${escapeHtml(cred.notes || '')}</textarea>
                        <button class="btn-icon" onclick="copyToClipboard('${escapeJs(cred.notes || '')}')" style="margin-top: 4px;">📋</button>
                    </div>
                </div>
            `;
        } else if (cred.category === 'trash') {
            const origCatName = cred.orig_category ? cred.orig_category.toUpperCase().replace('_', ' ') : 'LOGIN';
            fieldsHtml = `
                <div class="card-field-row">
                    <span class="field-label">Original Category</span>
                    <span class="field-value">${origCatName}</span>
                </div>
                <div class="card-field-row" style="margin-top: 6px;">
                    <span class="field-label">Reference</span>
                    <span class="field-value">${escapeHtml(cred.username || cred.name || 'Secure Note')}</span>
                </div>
            `;
        }

        // Show badge
        const badgeText = cred.category.replace('_', ' ');

        let cardControls = '';
        if (cred.category === 'trash') {
            cardControls = `
                <button class="btn-icon" onclick="restoreCredential('${cred.id}')" title="Restore to Vault">🔄 Restore</button>
                <button class="btn-icon btn-icon-danger" onclick="deleteCredential('${cred.id}')" title="Permanently Delete">🗑️ Delete Permanently</button>
            `;
        } else {
            cardControls = `
                <button class="btn-icon" onclick="openCredentialModal('${cred.id}')" title="Edit">✏️ Edit</button>
                <button class="btn-icon btn-icon-danger" onclick="deleteCredential('${cred.id}')" title="Move to Trash">🗑️ Trash</button>
            `;
        }

        card.innerHTML = `
            <div class="card-header">
                <div class="card-title-group">
                    <h4>${escapeHtml(cred.service)}</h4>
                </div>
                <span class="card-category-badge">${badgeText}</span>
            </div>
            <div class="card-fields">
                ${fieldsHtml}
                ${cred.notes && cred.category !== 'secure_note' ? `
                    <div class="card-field-row">
                        <span class="field-label">Notes</span>
                        <span class="field-value" style="font-size:0.8rem; font-style:italic;">${escapeHtml(cred.notes)}</span>
                    </div>
                ` : ''}
            </div>
            <div class="card-actions">
                ${cardControls}
            </div>
        `;
        
        credentialsGrid.appendChild(card);
    });
}

// ----------------------------------------------------------------------
// FORM & FIELD RENDERING
// ----------------------------------------------------------------------
function renderCategoryFields(category, data = {}) {
    categoryFieldsContainer.innerHTML = '';
    
    if (category === 'login') {
        categoryFieldsContainer.innerHTML = `
            <div class="form-group">
                <label for="cred-username">Username</label>
                <input type="text" id="cred-username" required placeholder="Enter username or email..." value="${escapeHtml(data.username || '')}">
            </div>
            <div class="form-group">
                <label for="cred-password">Password</label>
                <div style="display:flex; gap:6px;">
                    <input type="text" id="cred-password" required placeholder="Enter password..." value="${escapeHtml(data.password || '')}" style="flex-grow:1;">
                    <button type="button" class="btn btn-secondary" onclick="autofillGeneratedPassword()">Autofill</button>
                </div>
                <div class="strength-bar-container" style="margin-top: 6px; margin-bottom: 0;">
                    <div id="modal-strength-meter" class="strength-meter-bar"></div>
                    <span id="modal-strength-label" class="strength-text">Empty</span>
                </div>
            </div>
        `;
        // Attach listener to calculate strength in real time
        const passInput = document.getElementById('cred-password');
        passInput.addEventListener('input', (e) => calculateStrength(e.target.value, 'modal-strength-meter', 'modal-strength-label'));
        if (data.password) {
            calculateStrength(data.password, 'modal-strength-meter', 'modal-strength-label');
        }
    } else if (category === 'credit_card') {
        categoryFieldsContainer.innerHTML = `
            <div class="form-group">
                <label for="cred-cardholder">Cardholder Name</label>
                <input type="text" id="cred-cardholder" required placeholder="Cardholder name..." value="${escapeHtml(data.cardholder || '')}">
            </div>
            <div class="form-group">
                <label for="cred-cardnumber">Card Number</label>
                <input type="text" id="cred-cardnumber" required placeholder="16-digit card number..." value="${escapeHtml(data.card_number || '')}">
            </div>
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;">
                <div class="form-group">
                    <label for="cred-expiry">Expiry Date</label>
                    <input type="text" id="cred-expiry" required placeholder="MM/YY" value="${escapeHtml(data.expiry || '')}">
                </div>
                <div class="form-group">
                    <label for="cred-cvv">CVV</label>
                    <input type="password" id="cred-cvv" required placeholder="3 digits" value="${escapeHtml(data.cvv || '')}">
                </div>
                <div class="form-group">
                    <label for="cred-pin">PIN</label>
                    <input type="password" id="cred-pin" required placeholder="4 digits" value="${escapeHtml(data.pin || '')}">
                </div>
            </div>
        `;
    } else if (category === 'identity') {
        categoryFieldsContainer.innerHTML = `
            <div class="form-group">
                <label for="cred-name">Full Name</label>
                <input type="text" id="cred-name" required placeholder="Full name..." value="${escapeHtml(data.name || '')}">
            </div>
            <div class="form-group">
                <label for="cred-email">Email Address</label>
                <input type="text" id="cred-email" required placeholder="Email address..." value="${escapeHtml(data.email || '')}">
            </div>
            <div class="form-group">
                <label for="cred-phone">Phone Number</label>
                <input type="text" id="cred-phone" placeholder="Phone number..." value="${escapeHtml(data.phone || '')}">
            </div>
            <div class="form-group">
                <label for="cred-address">Full Address</label>
                <textarea id="cred-address" rows="2" placeholder="Street, City, Zip...">${escapeHtml(data.address || '')}</textarea>
            </div>
        `;
    }
}

// ----------------------------------------------------------------------
// ADD / EDIT CREDENTIAL OPERATIONS
// ----------------------------------------------------------------------
function openCredentialModal(credId = null) {
    credentialForm.reset();
    passwordHistoryContainer.classList.add('hidden');
    passwordHistoryList.innerHTML = '';
    
    if (credId) {
        // Edit existing credential
        const cred = credentials.find(c => c.id === credId);
        if (!cred) return;
        
        document.getElementById('cred-id').value = cred.id;
        document.getElementById('modal-title').textContent = 'Edit Credential';
        credCategorySelect.value = cred.category;
        credCategorySelect.disabled = true; // Lock category editing
        
        credServiceInput.value = cred.service;
        credNotesInput.value = cred.notes || '';
        
        // Populate dynamic fields
        renderCategoryFields(cred.category, cred);
        
        // Populate custom details inside credentials container
        if (cred.category === 'login') {
            document.getElementById('cred-username').value = cred.username || '';
            document.getElementById('cred-password').value = cred.password || '';
            calculateStrength(cred.password || '', 'modal-strength-meter', 'modal-strength-label');
        } else if (cred.category === 'credit_card') {
            document.getElementById('cred-cardholder').value = cred.cardholder || '';
            document.getElementById('cred-cardnumber').value = cred.card_number || '';
            document.getElementById('cred-expiry').value = cred.expiry || '';
            document.getElementById('cred-cvv').value = cred.cvv || '';
            document.getElementById('cred-pin').value = cred.pin || '';
        } else if (cred.category === 'identity') {
            document.getElementById('cred-name').value = cred.name || '';
            document.getElementById('cred-email').value = cred.email || '';
            document.getElementById('cred-phone').value = cred.phone || '';
            document.getElementById('cred-address').value = cred.address || '';
        }

        // Render Password History if available
        if (cred.category === 'login' && cred.history && cred.history.length > 0) {
            passwordHistoryContainer.classList.remove('hidden');
            passwordHistoryList.innerHTML = '';
            cred.history.forEach((oldPass, index) => {
                const li = document.createElement('li');
                li.className = 'history-item';
                li.innerHTML = `
                    <span>🔑 ${escapeHtml(oldPass)}</span>
                    <button type="button" class="btn-icon" onclick="copyToClipboard('${escapeJs(oldPass)}')">📋</button>
                `;
                passwordHistoryList.appendChild(li);
            });
        }
    } else {
        // Create new credential
        document.getElementById('cred-id').value = '';
        document.getElementById('modal-title').textContent = 'Add Credential';
        credCategorySelect.disabled = false;
        
        // Default category from navbar if active
        if (['login', 'credit_card', 'identity', 'secure_note'].includes(activeCategory)) {
            credCategorySelect.value = activeCategory;
        } else {
            credCategorySelect.value = 'login';
        }
        
        renderCategoryFields(credCategorySelect.value);
    }
    
    credentialModal.classList.remove('hidden');
    credServiceInput.focus();
}

async function handleSaveCredential(e) {
    e.preventDefault();
    
    const credId = document.getElementById('cred-id').value;
    const category = credCategorySelect.value;
    const service = credServiceInput.value;
    const notes = credNotesInput.value;
    
    let username = '';
    let password = '';
    let customFields = {};
    
    if (category === 'login') {
        username = document.getElementById('cred-username').value;
        password = document.getElementById('cred-password').value;
    } else if (category === 'credit_card') {
        username = document.getElementById('cred-cardholder').value; // Map cardholder name as primary identifier
        customFields = {
            cardholder: document.getElementById('cred-cardholder').value,
            card_number: document.getElementById('cred-cardnumber').value,
            expiry: document.getElementById('cred-expiry').value,
            cvv: document.getElementById('cred-cvv').value,
            pin: document.getElementById('cred-pin').value
        };
    } else if (category === 'identity') {
        username = document.getElementById('cred-email').value; // Map email as primary identifier
        customFields = {
            name: document.getElementById('cred-name').value,
            email: document.getElementById('cred-email').value,
            phone: document.getElementById('cred-phone').value,
            address: document.getElementById('cred-address').value
        };
    }

    const payload = {
        service,
        username,
        password,
        notes,
        category,
        custom_fields: customFields
    };

    try {
        let res;
        if (credId) {
            // Update
            res = await fetch(`/api/credentials/${credId}`, {
                method: 'PUT',
                headers: getHeaders(),
                body: JSON.stringify(payload)
            });
        } else {
            // Add
            res = await fetch('/api/credentials', {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify(payload)
            });
        }
        
        if (res.ok) {
            showToast(credId ? 'Credential updated!' : 'Credential added!', 'success');
            credentialModal.classList.add('hidden');
            loadCredentials();
        } else {
            const data = await res.json();
            showToast(data.detail || 'Failed to save credential.', 'error');
        }
    } catch (err) {
        showToast('API error saving credential.', 'error');
    }
}

async function deleteCredential(credId) {
    const cred = credentials.find(c => c.id === credId);
    if (!cred) return;
    
    const isTrash = cred.category === 'trash';
    const message = isTrash 
        ? `Are you sure you want to permanently delete '${cred.service}'? This cannot be undone.`
        : `Move '${cred.service}' to the Trash Bin?`;
        
    if (isTrash && !confirm(message)) {
        return;
    }

    try {
        const res = await fetch(`/api/credentials/${credId}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        if (res.ok) {
            showToast(isTrash ? 'Permanently deleted!' : 'Moved to Trash Bin.', 'success');
            loadCredentials();
        } else {
            showToast('Failed to delete credential.', 'error');
        }
    } catch (err) {
        showToast('API error deleting credential.', 'error');
    }
}

async function restoreCredential(credId) {
    try {
        const res = await fetch(`/api/credentials/${credId}/restore`, {
            method: 'POST',
            headers: getHeaders()
        });
        if (res.ok) {
            showToast('Credential restored from Trash!', 'success');
            loadCredentials();
        } else {
            showToast('Failed to restore credential.', 'error');
        }
    } catch (err) {
        showToast('API error restoring credential.', 'error');
    }
}

// ----------------------------------------------------------------------
// SETTINGS OVERLAY OPERATIONS
// ----------------------------------------------------------------------
function openSettingsModal() {
    settingsModal.classList.remove('hidden');
    // Load config values
    settingsAutolock.value = config.autolock_timeout;
    autolockVal.textContent = config.autolock_timeout;
    settingsClipboard.value = config.clipboard_timeout;
    clipboardVal.textContent = config.clipboard_timeout;
    settingsAccent.value = config.accent_color;
    
    changePasswordForm.reset();
    setupDecoyForm.reset();
}

async function saveSettingsOnServer() {
    const theme = config.theme_mode;
    const accent = settingsAccent.value;
    const autolock = parseInt(settingsAutolock.value);
    const clipboard = parseInt(settingsClipboard.value);
    
    const payload = {
        theme_mode: theme,
        accent_color: accent,
        autolock_timeout: autolock,
        clipboard_timeout: clipboard
    };

    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const data = await res.json();
            applyConfig(data.config);
            showToast('Settings saved successfully.', 'success');
            settingsModal.classList.add('hidden');
        } else {
            showToast('Failed to save settings.', 'error');
        }
    } catch (err) {
        showToast('API error saving config settings.', 'error');
    }
}

async function handleRotatePassword(e) {
    e.preventDefault();
    const currentPass = document.getElementById('rotate-current').value;
    const newPass = document.getElementById('rotate-new').value;
    
    if (isDecoy) {
        showToast('Password rotation is disabled in decoy mode.', 'error');
        return;
    }

    try {
        const res = await fetch('/api/config/change-password', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({
                current_password: currentPass,
                new_password: newPass
            })
        });
        if (res.ok) {
            showToast('Master Password rotated successfully!', 'success');
            changePasswordForm.reset();
        } else {
            const data = await res.json();
            showToast(data.detail || 'Password rotation failed.', 'error');
        }
    } catch (err) {
        showToast('API error rotating password.', 'error');
    }
}

async function handleSetupDecoy(e) {
    e.preventDefault();
    const decoyPass = document.getElementById('decoy-password').value;
    
    if (isDecoy) {
        showToast('Cannot configure decoy settings inside decoy environment.', 'error');
        return;
    }

    try {
        const res = await fetch('/api/config/decoy', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ password: decoyPass })
        });
        if (res.ok) {
            showToast('Decoy Vault configured successfully!', 'success');
            setupDecoyForm.reset();
        } else {
            const data = await res.json();
            showToast(data.detail || 'Decoy configuration failed.', 'error');
        }
    } catch (err) {
        showToast('API error configuring decoy vault.', 'error');
    }
}

// ----------------------------------------------------------------------
// SECURE PASSWORD GENERATION
// ----------------------------------------------------------------------
async function generatePasswordInTab() {
    if (activeGenMode === 'standard') {
        const length = parseInt(genLengthSlider.value);
        const upper = genUpperChk.checked;
        const lower = genLowerChk.checked;
        const digits = genDigitsChk.checked;
        const special = genSpecialChk.checked;
        const ambiguous = genAmbiguousChk.checked;
        
        if (!upper && !lower && !digits && !special) {
            showToast('At least one character set must be selected.', 'error');
            return;
        }

        const query = `?length=${length}&use_upper=${upper}&use_lower=${lower}&use_digits=${digits}&use_special=${special}&exclude_ambiguous=${ambiguous}`;
        try {
            const res = await fetch(`/api/generate/password${query}`);
            if (res.ok) {
                const data = await res.json();
                genOutput.value = data.password;
                calculateStrength(data.password, 'strength-meter', 'strength-label');
            }
        } catch (err) {
            showToast('Failed to generate password.', 'error');
        }
    } else {
        const count = parseInt(dicewareCountSlider.value);
        const separator = encodeURIComponent(dicewareSeparatorInput.value || '-');
        
        try {
            const res = await fetch(`/api/generate/passphrase?words_count=${count}&separator=${separator}`);
            if (res.ok) {
                const data = await res.json();
                genOutput.value = data.passphrase;
                calculateStrength(data.passphrase, 'strength-meter', 'strength-label');
            }
        } catch (err) {
            showToast('Failed to generate Diceware passphrase.', 'error');
        }
    }
}

// Request real-time strength details from API backend
async function calculateStrength(password, meterId, labelId) {
    const meterEl = document.getElementById(meterId);
    const labelEl = document.getElementById(labelId);
    if (!meterEl || !labelEl) return;

    if (!password) {
        meterEl.style.width = '0%';
        meterEl.style.backgroundColor = '#888888';
        labelEl.textContent = 'Empty';
        labelEl.style.color = '#888888';
        return;
    }

    try {
        const res = await fetch('/api/generate/strength', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });
        if (res.ok) {
            const data = await res.json();
            
            // Map entropy values to meter width percentage (cap at 120 bits)
            const pct = Math.min((data.entropy / 100) * 100, 100);
            meterEl.style.width = `${pct}%`;
            meterEl.style.backgroundColor = data.color;
            labelEl.textContent = `${data.label} (${data.entropy} bits)`;
            labelEl.style.color = data.color;
        }
    } catch (err) {
        // Fallback calculation if server strength check fails
        meterEl.style.width = '25%';
        meterEl.style.backgroundColor = '#888888';
        labelEl.textContent = 'Strength API Unavailable';
    }
}

function autofillGeneratedPassword() {
    const genVal = genOutput.value;
    const credPass = document.getElementById('cred-password');
    if (credPass && genVal) {
        credPass.value = genVal;
        calculateStrength(genVal, 'modal-strength-meter', 'modal-strength-label');
        showToast('Password autofilled from generator!', 'success');
    } else {
        showToast('Generate a password in the sidebar/tab first.', 'warning');
    }
}

// ----------------------------------------------------------------------
// CLIPBOARD COPY & SECURITY TIMEOUTS
// ----------------------------------------------------------------------
function copyToClipboard(text) {
    if (!text) return;
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
        
        // Save copied text context for clearing
        lastCopiedText = text;
        
        // Reset old clear timer if running
        if (clipboardTimer) {
            clearTimeout(clipboardTimer);
        }
        
        // Start clear timer
        const seconds = config.clipboard_timeout || 30;
        clipboardTimer = setTimeout(() => {
            clearClipboard();
        }, seconds * 1000);
    }).catch(() => {
        showToast('Failed to copy to clipboard.', 'error');
    });
}

function clearClipboard() {
    navigator.clipboard.readText().then(text => {
        if (text === lastCopiedText) {
            navigator.clipboard.writeText('').then(() => {
                showToast('Clipboard cleared for security.', 'warning');
            });
        }
    }).catch(() => {
        // Fallback: silently overwrite without read verify
        navigator.clipboard.writeText('');
    });
    clipboardTimer = null;
}

// ----------------------------------------------------------------------
// AUTOLOCK INACTIVITY TRACKER
// ----------------------------------------------------------------------
function resetAutoLockTimer() {
    if (!sessionToken) return;
    
    if (autoLockTimer) {
        clearTimeout(autoLockTimer);
    }
    
    const minutes = config.autolock_timeout || 5;
    autoLockTimer = setTimeout(() => {
        lockVault();
        showToast('Session locked due to inactivity.', 'warning');
    }, minutes * 60 * 1000);
}

function setupActivityListeners() {
    // Reset autolock timers on key/mouse events
    ['mousemove', 'mousedown', 'keydown', 'click', 'scroll', 'touchstart'].forEach(eventName => {
        document.addEventListener(eventName, resetAutoLockTimer, true);
    });
}

async function lockVault() {
    if (autoLockTimer) clearTimeout(autoLockTimer);
    if (clipboardTimer) clearTimeout(clipboardTimer);
    
    try {
        await fetch('/api/lock', { method: 'POST' });
    } catch(e) {}
    
    sessionToken = null;
    credentials = [];
    isDecoy = false;
    showView('login');
}

// ----------------------------------------------------------------------
// CARD MASKING TOGGLES
// ----------------------------------------------------------------------
function toggleFieldMasking(id, plainValue) {
    const el = document.getElementById(`pw-${id}`);
    if (el) {
        if (el.classList.contains('masked')) {
            el.textContent = plainValue;
            el.classList.remove('masked');
        } else {
            el.textContent = '••••••••';
            el.classList.add('masked');
        }
    }
}

function toggleCardNumberMasking(id, plainValue) {
    const el = document.getElementById(`num-${id}`);
    if (el) {
        if (el.classList.contains('masked')) {
            // Add spaces every 4 characters
            const spaced = plainValue.replace(/(.{4})/g, '$1 ').trim();
            el.textContent = spaced;
            el.classList.remove('masked');
        } else {
            el.textContent = '•••• •••• •••• ••••';
            el.classList.add('masked');
        }
    }
}

function toggleCvvPinMasking(id, cvv, pin) {
    const cvvEl = document.getElementById(`cvv-${id}`);
    const pinEl = document.getElementById(`pin-${id}`);
    if (cvvEl && pinEl) {
        if (cvvEl.classList.contains('masked')) {
            cvvEl.textContent = cvv;
            cvvEl.classList.remove('masked');
            pinEl.textContent = pin;
            pinEl.classList.remove('masked');
        } else {
            cvvEl.textContent = '•••';
            cvvEl.classList.add('masked');
            pinEl.textContent = '••••';
            pinEl.classList.add('masked');
        }
    }
}

// ----------------------------------------------------------------------
// TOAST NOTIFICATIONS
// ----------------------------------------------------------------------
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '❌';
    if (type === 'warning') icon = '⚠️';
    
    toast.innerHTML = `
        <span style="display:flex; align-items:center; gap:0.5rem;">
            <span>${icon}</span>
            <span>${message}</span>
        </span>
        <button class="btn-icon" style="color:inherit;" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    container.appendChild(toast);
    
    // Auto-dismiss after 4 seconds
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ----------------------------------------------------------------------
// ESCAPE UTILITIES
// ----------------------------------------------------------------------
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function escapeJs(str) {
    if (!str) return '';
    return str
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r');
}
