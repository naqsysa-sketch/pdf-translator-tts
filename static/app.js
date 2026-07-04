/* ==========================================
   State & Global Variables
   ========================================== */
let authToken = localStorage.getItem('auth_token') || null;
let currentProjectId = null;
let chaptersData = [];
let activeChapterIndex = -1;
let pollingInterval = null;
let isBulkProcessing = false;
let bulkAbortRequested = false;
let currentUserIsAdmin = false;
let selectedChapterIds = new Set();
let projectHasStoredPdf = false;
let serverConfig = {
    allow_registration: true,
    requires_registration_secret: false,
    configured_engines: {},
    max_upload_bytes: 10 * 1024 * 1024,
    max_upload_mb: 10,
};

let authMode = 'login';
const REMEMBERED_USERNAME_KEY = 'pdf_translator_remembered_username';

// DOM Elements - Auth
const authContainer = document.getElementById('auth-container');
const appContainer = document.getElementById('app-container');
const authCard = document.querySelector('.auth-card');
const authForm = document.getElementById('auth-form');
const authTabs = document.getElementById('auth-tabs');
const authTabLogin = document.getElementById('auth-tab-login');
const authTabRegister = document.getElementById('auth-tab-register');
const authUsername = document.getElementById('auth-username');
const authPassword = document.getElementById('auth-password');
const authConfirmPassword = document.getElementById('auth-confirm-password');
const authConfirmPasswordGroup = document.getElementById('auth-confirm-password-group');
const authSubmitBtn = document.getElementById('auth-submit-btn');
const authSubmitLabel = document.getElementById('auth-submit-label');
const authSubmitSpinner = document.getElementById('auth-submit-spinner');
const authRegistrationClosedPanel = document.getElementById('auth-registration-closed-panel');
const authRegistrationSecretGroup = document.getElementById('auth-registration-secret-group');
const authRegistrationSecret = document.getElementById('auth-registration-secret');
const authLoginOptions = document.getElementById('auth-login-options');
const authRememberMe = document.getElementById('auth-remember-me');
const authPasswordToggle = document.getElementById('auth-password-toggle');
const authPasswordToggleIcon = document.getElementById('auth-password-toggle-icon');
const authPasswordStrength = document.getElementById('auth-password-strength');
const authStrengthFill = document.getElementById('auth-strength-fill');
const authStrengthLabel = document.getElementById('auth-strength-label');
const authAlert = document.getElementById('auth-alert');
const authServerBadge = document.getElementById('auth-server-badge');
const authUsernameHint = document.getElementById('auth-username-hint');
const changePasswordBtn = document.getElementById('change-password-btn');
const changePasswordModal = document.getElementById('change-password-modal');
const changePasswordForm = document.getElementById('change-password-form');
const changePasswordClose = document.getElementById('change-password-close');
const changePasswordError = document.getElementById('change-password-error');

// DOM Elements - User Nav
const usernameDisplay = document.getElementById('username-display');
const dashboardBtn = document.getElementById('dashboard-btn');
const adminBtn = document.getElementById('admin-btn');
const logoutBtn = document.getElementById('logout-btn');

// DOM Elements - Admin
const adminCard = document.getElementById('admin-card');
const adminBackBtn = document.getElementById('admin-back-btn');
const adminStatsGrid = document.getElementById('admin-stats-grid');
const adminUsersTbody = document.getElementById('admin-users-tbody');
const adminProjectsTbody = document.getElementById('admin-projects-tbody');
const serverKeysBanner = document.getElementById('server-keys-banner');

// DOM Elements - Dashboard
const dashboardCard = document.getElementById('dashboard-card');
const projectsListTbody = document.getElementById('projects-list-tbody');
const newProjectBtn = document.getElementById('new-project-btn');

// DOM Elements - Workspace
const workspaceGrid = document.getElementById('workspace-grid');
const uploadCard = document.getElementById('upload-card');
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const sourceLangSelect = document.getElementById('source-lang-select');
const fileInfo = document.getElementById('file-info');
const uploadedFileName = document.getElementById('uploaded-file-name');
const uploadedFileSize = document.getElementById('uploaded-file-size');
const removeFileBtn = document.getElementById('remove-file-btn');

// DOM Elements - Settings
const settingsCard = document.getElementById('settings-card');
const translatorSelect = document.getElementById('translator-select');
const geminiSettings = document.getElementById('gemini-settings');
const geminiKey = document.getElementById('gemini-key');
const geminiModelSelect = document.getElementById('gemini-model-select');
const customModelInputGroup = document.getElementById('custom-model-input-group');
const customModelInput = document.getElementById('custom-model-input');

const deeplSettings = document.getElementById('deepl-settings');
const deeplKey = document.getElementById('deepl-key');

const openaiSettings = document.getElementById('openai-settings');
const openaiKey = document.getElementById('openai-key');
const openaiModelSelect = document.getElementById('openai-model-select');
const customOpenaiModelGroup = document.getElementById('custom-openai-model-group');
const customOpenaiModelInput = document.getElementById('custom-openai-model-input');

const claudeSettings = document.getElementById('claude-settings');
const claudeKey = document.getElementById('claude-key');
const claudeModelSelect = document.getElementById('claude-model-select');
const customClaudeModelGroup = document.getElementById('custom-claude-model-group');
const customClaudeModelInput = document.getElementById('custom-claude-model-input');

const libretranslateSettings = document.getElementById('libretranslate-settings');
const libreHost = document.getElementById('libre-host');
const libreKey = document.getElementById('libre-key');

const saveSettingsCheckbox = document.getElementById('save-settings-checkbox');
const voiceSelect = document.getElementById('voice-select');
const voiceRateSelect = document.getElementById('voice-rate-select');
const previewVoiceBtn = document.getElementById('preview-voice-btn');

// DOM Elements - Main Workspace Panels
const emptyState = document.getElementById('empty-state');
const chaptersCard = document.getElementById('chapters-card');
const chaptersListTbody = document.getElementById('chapters-list-tbody');
const translateAllBtn = document.getElementById('translate-all-btn');
const translateSelectedBtn = document.getElementById('translate-selected-btn');
const ttsSelectedBtn = document.getElementById('tts-selected-btn');
const selectAllChaptersCheckbox = document.getElementById('select-all-chapters');
const pageFromInput = document.getElementById('page-from-input');
const pageToInput = document.getElementById('page-to-input');
const reextractPanel = document.getElementById('reextract-panel');
const reextractPageFrom = document.getElementById('reextract-page-from');
const reextractPageTo = document.getElementById('reextract-page-to');
const reextractBtn = document.getElementById('reextract-btn');
const stopAllBtn = document.getElementById('stop-all-btn');
const exportZipBtn = document.getElementById('export-zip-btn');
const exportPdfBtn = document.getElementById('export-pdf-btn');
const exportAudiobookBtn = document.getElementById('export-audiobook-btn');
const bulkProgressContainer = document.getElementById('bulk-progress-container');
const bulkProgressStatus = document.getElementById('bulk-progress-status');
const bulkProgressPercent = document.getElementById('bulk-progress-percent');
const bulkProgressBar = document.getElementById('bulk-progress-bar');

// DOM Elements - Translation Preview & Player
const translationPreviewCard = document.getElementById('translation-preview-card');
const activeChapterTitle = document.getElementById('active-chapter-title');
const originalTextView = document.getElementById('original-text-view');
const translatedTextView = document.getElementById('translated-text-view');
const translationMethodBadge = document.getElementById('translation-method-badge');
const mainAudioPlayer = document.getElementById('main-audio-player');
const audioSource = document.getElementById('audio-source');
const audioTrack = document.getElementById('audio-track');
const subtitleSyncBox = document.getElementById('subtitle-sync-box');
const currentSpokenText = document.getElementById('current-spoken-text');
const downloadTextBtn = document.getElementById('download-text-btn');
const downloadPdfBtn = document.getElementById('download-pdf-btn');
const downloadAudioBtn = document.getElementById('download-audio-btn');
const saveTranslationBtn = document.getElementById('save-translation-btn');

// Toast Notification
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toast-message');
const toastIcon = document.getElementById('toast-icon');

/* ==========================================
   Initialization & Auth Routing
   ========================================== */
document.addEventListener('DOMContentLoaded', async () => {
    await loadServerConfig();
    applyServerConfigUI();
    initAuth();
    initSettingsListeners();
    loadSavedSettings();
});

async function loadServerConfig() {
    try {
        const res = await fetch('/api/config');
        if (res.ok) {
            serverConfig = await res.json();
        }
    } catch (err) {
        console.warn('Could not load server config:', err);
    }
}

function getMaxUploadBytes() {
    return serverConfig.max_upload_bytes || (10 * 1024 * 1024);
}

function formatUploadLimitMb() {
    const mb = serverConfig.max_upload_mb ?? (getMaxUploadBytes() / (1024 * 1024));
    return Number.isInteger(mb) ? String(mb) : String(mb);
}

async function readApiResponse(res) {
    const text = await res.text();
    if (!text) return { data: null, text: '' };
    try {
        return { data: JSON.parse(text), text };
    } catch {
        return { data: null, text };
    }
}

function describeUploadFailure(res, text) {
    if (res.status === 413 || /request entity too large/i.test(text)) {
        return `حجم الملف كبير جداً. الحد الأقصى على هذه الاستضافة هو ${formatUploadLimitMb()} ميجابايت.`;
    }
    return text || `خطأ من الخادم (${res.status})`;
}

function updateSelectionButtons() {
    const count = selectedChapterIds.size;
    if (translateSelectedBtn) translateSelectedBtn.disabled = count === 0 || isBulkProcessing;
    if (ttsSelectedBtn) ttsSelectedBtn.disabled = count === 0 || isBulkProcessing;
}

function syncSelectAllCheckbox() {
    if (!selectAllChaptersCheckbox || chaptersData.length === 0) {
        if (selectAllChaptersCheckbox) selectAllChaptersCheckbox.checked = false;
        return;
    }
    const allSelected = chaptersData.every(ch => selectedChapterIds.has(ch.id));
    selectAllChaptersCheckbox.checked = allSelected;
}

function getSelectedChapters() {
    if (selectedChapterIds.size === 0) return [];
    return chaptersData.filter(ch => selectedChapterIds.has(ch.id));
}

function toggleChapterSelection(chapterId, checked) {
    if (checked) {
        selectedChapterIds.add(chapterId);
    } else {
        selectedChapterIds.delete(chapterId);
    }
    updateSelectionButtons();
    syncSelectAllCheckbox();
}

function setEngineKeyUI(engine, keyGroupId, badgeId) {
    const configured = isEngineKeyConfigured(engine);
    const keyGroup = document.getElementById(keyGroupId);
    const badge = document.getElementById(badgeId);
    if (keyGroup) keyGroup.style.display = configured ? 'none' : 'block';
    if (badge) badge.style.display = configured ? 'block' : 'none';
}

function applyServerConfigUI() {
    const keyGroupIds = [
        'gemini-key-group', 'deepl-key-group', 'openai-key-group',
        'claude-key-group', 'libre-key-group'
    ];
    const badgeIds = [
        'gemini-server-key-badge', 'deepl-server-key-badge', 'openai-server-key-badge',
        'claude-server-key-badge', 'libre-server-key-badge'
    ];

    if (serverConfig.hide_client_api_keys) {
        if (serverKeysBanner) serverKeysBanner.style.display = 'block';
        keyGroupIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        badgeIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    } else {
        if (serverKeysBanner) serverKeysBanner.style.display = 'none';
        setEngineKeyUI('gemini', 'gemini-key-group', 'gemini-server-key-badge');
        setEngineKeyUI('deepl', 'deepl-key-group', 'deepl-server-key-badge');
        setEngineKeyUI('openai', 'openai-key-group', 'openai-server-key-badge');
        setEngineKeyUI('claude', 'claude-key-group', 'claude-server-key-badge');
        setEngineKeyUI('libretranslate', 'libre-key-group', 'libre-server-key-badge');
    }

    if (!serverConfig.allow_registration) {
        if (authTabRegister) {
            authTabRegister.hidden = true;
            authTabRegister.style.display = 'none';
        }
        if (authTabs) {
            authTabs.classList.add('auth-tabs--login-only');
            authTabs.style.gridTemplateColumns = '1fr';
        }
        if (authRegistrationClosedPanel) authRegistrationClosedPanel.hidden = false;
        setAuthMode('login', false);
    } else {
        if (authTabRegister) {
            authTabRegister.hidden = false;
            authTabRegister.style.display = '';
        }
        if (authTabs) authTabs.classList.remove('auth-tabs--login-only');
        if (authRegistrationClosedPanel) authRegistrationClosedPanel.hidden = true;
    }

    updateAuthServerBadge();

    const uploadLimitEl = document.getElementById('upload-size-limit');
    if (uploadLimitEl) {
        uploadLimitEl.textContent = `الحد الأقصى لحجم الملف: ${formatUploadLimitMb()} ميجابايت`;
    }
}

function updateAuthServerBadge() {
    if (!authServerBadge) return;
    const storage = serverConfig.storage_backend || 'local';
    const storageLabel = storage === 'supabase' ? 'تخزين سحابي' : storage === 's3' ? 'تخزين S3' : 'تخزين مؤقت';
    authServerBadge.innerHTML = `<i class="fa-solid fa-circle-check"></i> متصل — ${storageLabel}`;
}

function isRegisterMode() {
    return authMode === 'register';
}

function setAuthMode(mode, focus = true) {
    if (!serverConfig.allow_registration && mode === 'register') {
        showAuthAlert('التسجيل مغلق حالياً. تواصل مع مسؤول النظام لإنشاء حساب.', 'info');
        mode = 'login';
    }
    authMode = mode;

    if (authTabLogin) {
        authTabLogin.classList.toggle('active', mode === 'login');
        authTabLogin.setAttribute('aria-selected', mode === 'login' ? 'true' : 'false');
    }
    if (authTabRegister) {
        authTabRegister.classList.toggle('active', mode === 'register');
        authTabRegister.setAttribute('aria-selected', mode === 'register' ? 'true' : 'false');
    }

    if (authSubmitLabel) {
        authSubmitLabel.textContent = mode === 'register' ? 'إنشاء حساب' : 'دخول';
    }
    if (authLoginOptions) {
        authLoginOptions.hidden = mode !== 'login';
    }
    if (authConfirmPasswordGroup) {
        authConfirmPasswordGroup.hidden = mode !== 'register';
    }
    if (authUsernameHint) {
        authUsernameHint.textContent = mode === 'register'
            ? '3–50 حرفاً — حروف إنجليزية وأرقام و _ فقط'
            : 'أدخل اسم المستخدم الذي أنشأه المسؤول';
    }
    if (authPassword) {
        authPassword.autocomplete = mode === 'register' ? 'new-password' : 'current-password';
        authPassword.placeholder = mode === 'register' ? '6 أحرف على الأقل' : 'أدخل كلمة المرور';
    }
    if (authPasswordStrength) {
        authPasswordStrength.hidden = mode !== 'register';
    }

    updateRegistrationSecretVisibility();
    clearAuthErrors();
    clearAuthAlert();

    if (focus && authUsername) {
        authUsername.focus();
    }
}

function updateRegistrationSecretVisibility() {
    if (!authRegistrationSecretGroup) return;
    const show = isRegisterMode() && serverConfig.allow_registration && serverConfig.requires_registration_secret;
    authRegistrationSecretGroup.hidden = !show;
    if (authRegistrationSecret) {
        authRegistrationSecret.required = show;
    }
}

function clearAuthAlert() {
    if (!authAlert) return;
    authAlert.hidden = true;
    authAlert.textContent = '';
    authAlert.className = 'auth-alert';
}

function showAuthAlert(message, type = 'error') {
    if (!authAlert) return;
    const icon = type === 'success' ? 'fa-circle-check' : type === 'info' ? 'fa-circle-info' : 'fa-triangle-exclamation';
    authAlert.className = `auth-alert ${type}`;
    authAlert.innerHTML = `<i class="fa-solid ${icon}"></i><span>${escapeHtml(message)}</span>`;
    authAlert.hidden = false;
}

function clearAuthErrors() {
    document.querySelectorAll('.auth-field-error').forEach((el) => {
        el.hidden = true;
        el.textContent = '';
    });
    [authUsername, authPassword, authConfirmPassword, authRegistrationSecret].forEach((input) => {
        if (input) input.classList.remove('invalid');
    });
}

function setFieldError(inputEl, errorEl, message) {
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.hidden = false;
    }
    if (inputEl) inputEl.classList.add('invalid');
}

function validateUsername(username) {
    if (!username || username.length < 3) {
        return 'اسم المستخدم يجب أن يكون 3 أحرف على الأقل.';
    }
    if (username.length > 50) {
        return 'اسم المستخدم طويل جداً (50 حرفاً كحد أقصى).';
    }
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        return 'استخدم حروفاً إنجليزية وأرقاماً و _ فقط بدون مسافات.';
    }
    return '';
}

function validatePassword(password) {
    if (!password || password.length < 6) {
        return 'كلمة المرور يجب أن تكون 6 أحرف على الأقل.';
    }
    return '';
}

function getPasswordStrength(password) {
    if (!password) return { score: 0, label: '', color: 'transparent' };
    let score = 0;
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;

    if (score <= 1) return { score: 25, label: 'ضعيفة', color: '#ef4444' };
    if (score <= 3) return { score: 55, label: 'متوسطة', color: '#f59e0b' };
    return { score: 100, label: 'قوية', color: '#10b981' };
}

function updatePasswordStrengthMeter() {
    if (!authPasswordStrength || !isRegisterMode()) return;
    const strength = getPasswordStrength(authPassword.value);
    authPasswordStrength.hidden = !authPassword.value;
    if (authStrengthFill) {
        authStrengthFill.style.width = `${strength.score}%`;
        authStrengthFill.style.background = strength.color;
    }
    if (authStrengthLabel) {
        authStrengthLabel.textContent = strength.label;
    }
}

function validateAuthForm() {
    clearAuthErrors();
    let valid = true;

    const username = authUsername.value.trim();
    const password = authPassword.value;
    const usernameError = validateUsername(username);
    if (usernameError) {
        setFieldError(authUsername, document.getElementById('auth-username-error'), usernameError);
        valid = false;
    }

    const passwordError = validatePassword(password);
    if (passwordError) {
        setFieldError(authPassword, document.getElementById('auth-password-error'), passwordError);
        valid = false;
    }

    if (isRegisterMode()) {
        if (password !== authConfirmPassword.value) {
            setFieldError(
                authConfirmPassword,
                document.getElementById('auth-confirm-password-error'),
                'كلمتا المرور غير متطابقتين.'
            );
            valid = false;
        }
        if (serverConfig.requires_registration_secret && !authRegistrationSecret.value.trim()) {
            setFieldError(
                authRegistrationSecret,
                document.getElementById('auth-registration-secret-error'),
                'رمز التسجيل مطلوب.'
            );
            valid = false;
        }
    }

    if (!valid && authCard) {
        authCard.classList.remove('shake');
        void authCard.offsetWidth;
        authCard.classList.add('shake');
    }
    return valid;
}

function setAuthLoading(loading) {
    if (!authSubmitBtn) return;
    authSubmitBtn.disabled = loading;
    if (authSubmitSpinner) authSubmitSpinner.hidden = !loading;
    if (authSubmitLabel) authSubmitLabel.style.opacity = loading ? '0.85' : '1';
}

function loadRememberedUsername() {
    const remembered = localStorage.getItem(REMEMBERED_USERNAME_KEY);
    if (remembered && authUsername) {
        authUsername.value = remembered;
    }
}

function persistRememberedUsername(username) {
    if (authRememberMe && authRememberMe.checked) {
        localStorage.setItem(REMEMBERED_USERNAME_KEY, username);
    } else {
        localStorage.removeItem(REMEMBERED_USERNAME_KEY);
    }
}

function togglePasswordVisibility() {
    if (!authPassword || !authPasswordToggleIcon) return;
    const show = authPassword.type === 'password';
    authPassword.type = show ? 'text' : 'password';
    authPasswordToggleIcon.className = show ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye';
    if (authPasswordToggle) {
        authPasswordToggle.setAttribute('aria-label', show ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور');
    }
}

function initAuth() {
    loadRememberedUsername();
    setAuthMode('login', false);

    if (authToken) {
        checkTokenAndLoadApp();
    } else {
        showAuthScreen();
    }

    authForm.addEventListener('submit', handleAuthSubmit);
    authTabLogin?.addEventListener('click', () => setAuthMode('login'));
    authTabRegister?.addEventListener('click', () => setAuthMode('register'));
    authPasswordToggle?.addEventListener('click', togglePasswordVisibility);
    authPassword?.addEventListener('input', updatePasswordStrengthMeter);

    dashboardBtn.addEventListener('click', showDashboard);
    adminBtn.addEventListener('click', showAdminPanel);
    adminBackBtn.addEventListener('click', showDashboard);
    logoutBtn.addEventListener('click', handleLogout);
    changePasswordBtn?.addEventListener('click', openChangePasswordModal);
    changePasswordClose?.addEventListener('click', closeChangePasswordModal);
    changePasswordModal?.addEventListener('click', (e) => {
        if (e.target === changePasswordModal) closeChangePasswordModal();
    });
    changePasswordForm?.addEventListener('submit', handleChangePasswordSubmit);

    newProjectBtn.addEventListener('click', startNewProjectWorkspace);
}

function openChangePasswordModal() {
    if (!changePasswordModal) return;
    changePasswordForm?.reset();
    if (changePasswordError) changePasswordError.hidden = true;
    changePasswordModal.style.display = 'flex';
    changePasswordModal.setAttribute('aria-hidden', 'false');
}

function closeChangePasswordModal() {
    if (!changePasswordModal) return;
    changePasswordModal.style.display = 'none';
    changePasswordModal.setAttribute('aria-hidden', 'true');
}

async function handleChangePasswordSubmit(e) {
    e.preventDefault();
    const current = document.getElementById('current-password')?.value || '';
    const next = document.getElementById('new-password')?.value || '';
    const confirm = document.getElementById('new-password-confirm')?.value || '';

    if (next.length < 6) {
        if (changePasswordError) {
            changePasswordError.textContent = 'كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل.';
            changePasswordError.hidden = false;
        }
        return;
    }
    if (next !== confirm) {
        if (changePasswordError) {
            changePasswordError.textContent = 'تأكيد كلمة المرور غير متطابق.';
            changePasswordError.hidden = false;
        }
        return;
    }

    try {
        const res = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            },
            body: JSON.stringify({ current_password: current, new_password: next }),
        });
        const { data } = await readApiResponse(res);
        if (res.ok && data?.success) {
            closeChangePasswordModal();
            showToast('تم تحديث كلمة المرور بنجاح.', 'success');
        } else {
            if (changePasswordError) {
                changePasswordError.textContent = data?.detail || 'تعذر تغيير كلمة المرور.';
                changePasswordError.hidden = false;
            }
        }
    } catch {
        if (changePasswordError) {
            changePasswordError.textContent = 'تعذر الاتصال بالخادم.';
            changePasswordError.hidden = false;
        }
    }
}

function showAuthScreen() {
    authContainer.style.display = 'flex';
    appContainer.style.display = 'none';
}

function showDashboard() {
    stopPolling();
    currentProjectId = null;
    workspaceGrid.style.display = 'none';
    adminCard.style.display = 'none';
    dashboardCard.style.display = 'block';
    loadUserProjects();
}

function showAdminPanel() {
    if (!currentUserIsAdmin) return;
    stopPolling();
    currentProjectId = null;
    workspaceGrid.style.display = 'none';
    dashboardCard.style.display = 'none';
    adminCard.style.display = 'block';
    loadAdminPanel();
}

async function checkTokenAndLoadApp() {
    try {
        const res = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const data = await res.json();
            currentUserIsAdmin = !!data.is_admin;
            usernameDisplay.textContent = data.username;
            adminBtn.style.display = currentUserIsAdmin ? 'inline-flex' : 'none';
            authContainer.style.display = 'none';
            appContainer.style.display = 'block';
            showDashboard();
        } else {
            handleLogout();
        }
    } catch (err) {
        showToast('فشل الاتصال بالخادم الرئيسي.', 'error');
        handleLogout();
    }
}

function toggleAuthMode(e) {
    e.preventDefault();
    setAuthMode(isRegisterMode() ? 'login' : 'register');
}

async function handleAuthSubmit(e) {
    e.preventDefault();
    clearAuthAlert();
    if (!validateAuthForm()) return;

    const username = authUsername.value.trim();
    const password = authPassword.value;
    setAuthLoading(true);

    try {
        if (isRegisterMode()) {
            const payload = { username, password };
            if (serverConfig.requires_registration_secret) {
                payload.registration_secret = authRegistrationSecret.value.trim();
            }
            const res = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const { data } = await readApiResponse(res);
            if (res.ok && data?.success) {
                showAuthAlert('تم إنشاء الحساب بنجاح! جاري تسجيل الدخول...', 'success');
                setAuthMode('login', false);
                await handleLoginFlow(username, password, false);
            } else {
                showAuthAlert(data?.detail || 'فشل إنشاء الحساب.', 'error');
            }
        } else {
            await handleLoginFlow(username, password, true);
        }
    } catch {
        showAuthAlert('تعذر الاتصال بالخادم. تحقق من الإنترنت أو جرّب لاحقاً.', 'error');
    } finally {
        setAuthLoading(false);
    }
}

async function handleLoginFlow(username, password, showSuccessToast = true) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    let res;
    try {
        res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        });
    } catch {
        showAuthAlert('تعذر الاتصال بالخادم. تأكد أنك تستخدم الرابط الصحيح للتطبيق.', 'error');
        return;
    }

    const { data } = await readApiResponse(res);
    if (res.ok && data?.access_token) {
        authToken = data.access_token;
        localStorage.setItem('auth_token', authToken);
        persistRememberedUsername(username);
        if (showSuccessToast) {
            showToast('تم تسجيل الدخول بنجاح!', 'success');
        }
        authPassword.value = '';
        if (authConfirmPassword) authConfirmPassword.value = '';
        clearAuthErrors();
        clearAuthAlert();
        checkTokenAndLoadApp();
    } else {
        const message = data?.detail || 'اسم المستخدم أو كلمة المرور غير صحيحة.';
        showAuthAlert(message, 'error');
        setFieldError(authPassword, document.getElementById('auth-password-error'), message);
        if (authCard) {
            authCard.classList.remove('shake');
            void authCard.offsetWidth;
            authCard.classList.add('shake');
        }
        authPassword.focus();
        authPassword.select();
    }
}

function handleLogout() {
    authToken = null;
    currentUserIsAdmin = false;
    adminBtn.style.display = 'none';
    localStorage.removeItem('auth_token');
    closeChangePasswordModal();
    setAuthMode('login', false);
    showAuthScreen();
}

/* ==========================================
   Admin panel
   ========================================== */
async function loadAdminPanel() {
    await Promise.all([loadAdminStats(), loadAdminUsers(), loadAdminProjects()]);
}

async function loadAdminStats() {
    try {
        const res = await fetch('/api/admin/stats', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error();
        const stats = await res.json();
        adminStatsGrid.innerHTML = `
            <div class="admin-stat-card"><span class="admin-stat-label">المستخدمون</span><strong>${stats.users_count}</strong></div>
            <div class="admin-stat-card"><span class="admin-stat-label">المشاريع</span><strong>${stats.projects_count}</strong></div>
            <div class="admin-stat-card"><span class="admin-stat-label">الفصول</span><strong>${stats.chapters_count}</strong></div>
            <div class="admin-stat-card"><span class="admin-stat-label">ترجمات مكتملة</span><strong>${stats.completed_translations}</strong></div>
            <div class="admin-stat-card"><span class="admin-stat-label">ملفات صوتية</span><strong>${stats.completed_tts}</strong></div>
        `;
    } catch (err) {
        showToast('فشل تحميل إحصائيات الإدارة.', 'error');
    }
}

async function loadAdminUsers() {
    try {
        const res = await fetch('/api/admin/users', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error();
        const users = await res.json();
        adminUsersTbody.innerHTML = '';
        users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user.id}</td>
                <td><strong>${escapeHtml(user.username)}</strong></td>
                <td>${user.is_admin ? '<span class="badge success">مسؤول</span>' : '<span class="badge warning">مستخدم</span>'}</td>
                <td>${user.projects_count}</td>
                <td>
                    <button class="btn btn-sm btn-secondary danger" onclick="deleteAdminUser(${user.id})" ${user.is_admin ? 'disabled' : ''}>
                        <i class="fa-solid fa-trash"></i> حذف
                    </button>
                </td>
            `;
            adminUsersTbody.appendChild(tr);
        });
    } catch (err) {
        showToast('فشل تحميل قائمة المستخدمين.', 'error');
    }
}

async function loadAdminProjects() {
    try {
        const res = await fetch('/api/admin/projects', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error();
        const projects = await res.json();
        adminProjectsTbody.innerHTML = '';
        if (projects.length === 0) {
            adminProjectsTbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px;">لا توجد مشاريع.</td></tr>`;
            return;
        }
        projects.forEach(project => {
            const dateStr = new Date(project.created_at).toLocaleDateString('ar-EG');
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${escapeHtml(project.filename)}</strong></td>
                <td>${escapeHtml(project.owner)}</td>
                <td>${escapeHtml(project.status)}</td>
                <td style="font-family:var(--font-en);">${dateStr}</td>
                <td>
                    <button class="btn btn-sm btn-secondary danger" onclick="deleteAdminProject('${project.id}')">
                        <i class="fa-solid fa-trash"></i> حذف
                    </button>
                </td>
            `;
            adminProjectsTbody.appendChild(tr);
        });
    } catch (err) {
        showToast('فشل تحميل قائمة المشاريع.', 'error');
    }
}

window.deleteAdminUser = async function(userId) {
    if (!confirm('هل تريد حذف هذا المستخدم وجميع مشاريعه؟')) return;
    try {
        const res = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await res.json();
        if (res.ok) {
            showToast('تم حذف المستخدم.', 'success');
            loadAdminPanel();
        } else {
            showToast(data.detail || 'فشل حذف المستخدم.', 'error');
        }
    } catch (err) {
        showToast('فشل الاتصال بالخادم.', 'error');
    }
};

window.deleteAdminProject = async function(projectId) {
    if (!confirm('هل تريد حذف هذا المشروع نهائياً؟')) return;
    try {
        const res = await fetch(`/api/admin/projects/${projectId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await res.json();
        if (res.ok) {
            showToast('تم حذف المشروع.', 'success');
            loadAdminPanel();
        } else {
            showToast(data.detail || 'فشل حذف المشروع.', 'error');
        }
    } catch (err) {
        showToast('فشل الاتصال بالخادم.', 'error');
    }
};

/* ==========================================
   Dashboard logic (Projects List)
   ========================================== */
async function loadUserProjects() {
    try {
        const res = await fetch('/api/projects', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error();
        const projects = await res.json();
        
        projectsListTbody.innerHTML = '';
        if (projects.length === 0) {
            projectsListTbody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 30px;">
                        لا توجد كتب مرفوعة مسبقاً. اضغط على زر "كتاب جديد" للبدء.
                    </td>
                </tr>
            `;
            return;
        }
        
        projects.forEach(p => {
            const dateStr = new Date(p.created_at).toLocaleDateString('ar-EG', {
                year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });
            
            let statusBadge = '';
            if (p.status === 'processing') {
                statusBadge = '<span class="badge warning"><i class="fa-solid fa-spinner fa-spin"></i> جاري التقسيم...</span>';
            } else if (p.status === 'completed') {
                statusBadge = '<span class="badge success"><i class="fa-solid fa-circle-check"></i> جاهز</span>';
            } else {
                statusBadge = '<span class="badge danger"><i class="fa-solid fa-triangle-exclamation"></i> فشل</span>';
            }
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${escapeHtml(p.filename)}</strong></td>
                <td>${statusBadge}</td>
                <td style="font-family: var(--font-en); font-size: 0.9rem;">${dateStr}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="openProject('${p.id}')">
                        <i class="fa-solid fa-eye"></i> عرض المشروع
                    </button>
                </td>
            `;
            projectsListTbody.appendChild(tr);
        });
    } catch (err) {
        showToast('فشل تحميل المشاريع.', 'error');
    }
}

function startNewProjectWorkspace() {
    stopPolling();
    currentProjectId = null;
    chaptersData = [];
    activeChapterIndex = -1;
    
    // Toggle views
    dashboardCard.style.display = 'none';
    workspaceGrid.style.display = 'grid';
    uploadCard.style.display = 'block';
    
    // Reset Upload Container
    fileInput.value = '';
    uploadZone.style.display = 'block';
    fileInfo.style.display = 'none';
    
    // Hide Work Panels
    emptyState.innerHTML = `
        <div class="empty-icon-wrap">
            <i class="fa-solid fa-book-open"></i>
        </div>
        <h2>ابدأ برفع ملف PDF الخاص بك</h2>
        <p>سيقوم نظامنا باستخراج النص وتقسيم الفصول في الخلفية عبر طوابير المهام، مع توفير خيارات الترجمة والـ TTS لكل فصل.</p>
    `;
    emptyState.style.display = 'flex';
    chaptersCard.style.display = 'none';
    translationPreviewCard.style.display = 'none';
    selectedChapterIds.clear();
    if (selectAllChaptersCheckbox) selectAllChaptersCheckbox.checked = false;
    updateSelectionButtons();
    if (reextractPanel) reextractPanel.style.display = 'none';
}

function openProject(projectId) {
    stopPolling();
    selectedChapterIds.clear();
    if (selectAllChaptersCheckbox) selectAllChaptersCheckbox.checked = false;
    updateSelectionButtons();
    currentProjectId = projectId;
    dashboardCard.style.display = 'none';
    workspaceGrid.style.display = 'grid';
    uploadCard.style.display = 'none';

    emptyState.style.display = 'flex';
    chaptersCard.style.display = 'none';
    translationPreviewCard.style.display = 'none';

    fetchProjectDetails();
    startPolling();
}

/* ==========================================
   Polling & Task Progress Refresher
   ========================================== */
function startPolling() {
    stopPolling();
    pollingInterval = setInterval(fetchProjectDetails, 3000);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

async function fetchProjectDetails() {
    if (!currentProjectId) return;
    try {
        const res = await fetch(`/api/projects/${currentProjectId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) {
            stopPolling();
            showToast('خطأ في استرجاع تفاصيل المشروع.', 'error');
            showDashboard();
            return;
        }
        
        const project = await res.json();
        
        if (project.status === 'processing') {
            emptyState.innerHTML = `
                <div class="empty-icon-wrap">
                    <i class="fa-solid fa-spinner fa-spin"></i>
                </div>
                <h2>جاري تقسيم وفك ضغط الكتاب...</h2>
                <p>يتم الآن معالجة وتقسيم كتاب <strong>${escapeHtml(project.filename)}</strong> في الخلفية آلياً. يرجى الانتظار.</p>
            `;
            emptyState.style.display = 'flex';
            chaptersCard.style.display = 'none';
            translationPreviewCard.style.display = 'none';
            return;
        }
        
        if (project.status === 'failed') {
            stopPolling();
            emptyState.innerHTML = `
                <div class="empty-icon-wrap danger" style="color: var(--danger);">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                </div>
                <h2>فشلت عملية معالجة الكتاب!</h2>
                <p>تعذر على النظام استخراج النصوص أو تقسيم الفصول. يرجى التأكد من صلاحية ملف الـ PDF والمحاولة مجدداً.</p>
            `;
            emptyState.style.display = 'flex';
            chaptersCard.style.display = 'none';
            return;
        }
        
        // Render Chapters List
        chaptersData = project.chapters;
        projectHasStoredPdf = !!project.has_stored_pdf;
        if (reextractPanel) {
            reextractPanel.style.display = projectHasStoredPdf ? 'block' : 'none';
        }
        const knownIds = new Set(chaptersData.map(ch => ch.id));
        selectedChapterIds = new Set([...selectedChapterIds].filter(id => knownIds.has(id)));
        renderChaptersList();
        updateSelectionButtons();
        syncSelectAllCheckbox();
        
        emptyState.style.display = 'none';
        chaptersCard.style.display = 'block';
        
        // Update export buttons disabled state
        const hasAllAudio = chaptersData.every(ch => ch.tts_status === 'completed');
        const hasAnyTranslation = chaptersData.some(
            ch => ch.translation_status === 'completed' && ch.translated_text && ch.translated_text.trim()
        );
        exportZipBtn.disabled = chaptersData.length === 0;
        exportPdfBtn.disabled = !hasAnyTranslation;
        exportAudiobookBtn.disabled = !hasAllAudio;
        
        // Update active preview panels in place if someone views it
        if (activeChapterIndex !== -1) {
            const activeChapter = chaptersData.find(c => c.id === chaptersData[activeChapterIndex].id);
            if (activeChapter) {
                // Update translation view if status changed
                const textarea = document.getElementById('translated-text-view');
                const originalView = document.getElementById('original-text-view');
                if (originalView && originalView.textContent !== activeChapter.original_text) {
                    originalView.textContent = activeChapter.original_text;
                }
                if (activeChapter.translation_status === 'completed' && textarea.value !== activeChapter.translated_text) {
                    textarea.value = activeChapter.translated_text;
                    translationMethodBadge.textContent = `بواسطة ${activeChapter.translation_engine}`;
                    translationMethodBadge.style.display = 'inline-block';
                    if (activeChapter.translation_warning) {
                        showToast(activeChapter.translation_warning, 'warning');
                    }
                }
                
                // Update Audio control if ready
                const player = document.getElementById('main-audio-player');
                const downloadAudio = document.getElementById('download-audio-btn');
                const downloadText = document.getElementById('download-text-btn');
                
                downloadText.disabled = !activeChapter.translated_text;
                const downloadPdf = document.getElementById('download-pdf-btn');
                if (downloadPdf) {
                    downloadPdf.disabled = !activeChapter.translated_text;
                }
                
                if (activeChapter.tts_status === 'completed') {
                    downloadAudio.disabled = false;
                    if (audioSource.src !== activeChapter.audio_url) {
                        setupAudioPlayer(activeChapter.audio_url, activeChapter.vtt_url);
                    }
                } else {
                    downloadAudio.disabled = true;
                }
            }
        }
        
        // Stop polling if nothing is running in Celery worker
        const anythingRunning = chaptersData.some(ch => 
            ch.translation_status === 'processing' || ch.tts_status === 'processing'
        );
        if (!anythingRunning) {
            stopPolling();
        }
        
    } catch (err) {
        console.error(err);
    }
}

/* ==========================================
   Chapters rendering & Individual actions
   ========================================== */
function renderChaptersList() {
    chaptersListTbody.innerHTML = '';
    
    chaptersData.forEach((ch, idx) => {
        let transBadge = '';
        if (ch.translation_status === 'pending') {
            transBadge = '<span class="badge warning">معلق</span>';
        } else if (ch.translation_status === 'processing') {
            transBadge = '<span class="badge warning"><i class="fa-solid fa-spinner fa-spin"></i> جاري الترجمة...</span>';
        } else if (ch.translation_status === 'completed') {
            transBadge = `<span class="badge success"><i class="fa-solid fa-circle-check"></i> مكتمل (${escapeHtml(ch.translation_engine)})</span>`;
        } else {
            transBadge = '<span class="badge danger">فشل</span>';
        }
        
        let ttsBadge = '';
        if (ch.tts_status === 'pending') {
            ttsBadge = '<span class="badge warning">معلق</span>';
        } else if (ch.tts_status === 'processing') {
            ttsBadge = '<span class="badge warning"><i class="fa-solid fa-spinner fa-spin"></i> جاري توليد الصوت...</span>';
        } else if (ch.tts_status === 'completed') {
            ttsBadge = '<span class="badge success"><i class="fa-solid fa-circle-check"></i> مكتمل</span>';
        } else {
            ttsBadge = '<span class="badge danger">فشل</span>';
        }
        
        const checked = selectedChapterIds.has(ch.id) ? 'checked' : '';
        const isSelected = (idx === activeChapterIndex);
        const tr = document.createElement('tr');
        if (isSelected) tr.classList.add('active-row');
        
        tr.innerHTML = `
            <td class="col-select"><input type="checkbox" class="chapter-select" data-id="${ch.id}" ${checked}></td>
            <td><strong>${ch.chapter_num}</strong></td>
            <td><span class="chapter-title-span">${escapeHtml(ch.title)}</span></td>
            <td style="font-family: var(--font-en); font-size: 0.9rem;">${ch.start_page} - ${ch.end_page}</td>
            <td>${transBadge}</td>
            <td>${ttsBadge}</td>
            <td>
                <div class="actions-group">
                    <button class="btn btn-sm btn-secondary" onclick="showChapterPreview(${idx})">
                        <i class="fa-solid fa-eye"></i> معاينة
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="translateChapter(${ch.id}, ${idx})" ${ch.translation_status === 'processing' ? 'disabled' : ''}>
                        <i class="fa-solid fa-globe"></i> ترجمة
                    </button>
                    <button class="btn btn-sm btn-emerald" onclick="generateTTS(${ch.id}, ${idx})" ${(ch.translation_status !== 'completed' || ch.tts_status === 'processing') ? 'disabled' : ''}>
                        <i class="fa-solid fa-volume-high"></i> توليد صوت
                    </button>
                </div>
            </td>
        `;
        chaptersListTbody.appendChild(tr);
    });

    chaptersListTbody.querySelectorAll('.chapter-select').forEach(box => {
        box.addEventListener('change', (e) => {
            toggleChapterSelection(Number(e.target.dataset.id), e.target.checked);
        });
    });
}

function showChapterPreview(index) {
    activeChapterIndex = index;
    const chapter = chaptersData[index];
    
    // Mark row active
    renderChaptersList();
    
    // Toggle Card show
    translationPreviewCard.style.display = 'block';
    
    // Set text contents
    activeChapterTitle.textContent = `الفصل ${chapter.chapter_num}: ${chapter.title}`;
    originalTextView.textContent = chapter.original_text;
    translatedTextView.value = chapter.translated_text || '';
    
    if (chapter.translation_status === 'completed') {
        translationMethodBadge.textContent = `بواسطة ${chapter.translation_engine}`;
        translationMethodBadge.style.display = 'inline-block';
        if (chapter.translation_warning) {
            showToast(chapter.translation_warning, 'warning');
        }
    } else {
        translationMethodBadge.style.display = 'none';
    }
    
    // Setup Audio Player
    if (chapter.tts_status === 'completed') {
        setupAudioPlayer(chapter.audio_url, chapter.vtt_url);
        downloadAudioBtn.disabled = false;
    } else {
        resetAudioPlayer();
        downloadAudioBtn.disabled = true;
    }
    
    downloadTextBtn.disabled = !chapter.translated_text;
    downloadPdfBtn.disabled = !chapter.translated_text;
    saveTranslationBtn.disabled = !chapter.translated_text;
    
    // Scroll down to preview smoothly
    translationPreviewCard.scrollIntoView({ behavior: 'smooth' });
}

async function translateChapter(chapterId, index) {
    const engine = translatorSelect.value;
    let apiKeyVal = null;
    let modelVal = null;
    let customHostVal = null;
    
    if (engine === 'gemini') {
        if (!isEngineKeyConfigured('gemini')) {
            apiKeyVal = geminiKey.value ? geminiKey.value.trim() : null;
        }
        modelVal = geminiModelSelect.value;
        if (modelVal === 'custom') {
            modelVal = customModelInput.value.trim();
            if (!modelVal) {
                showToast('يرجى إدخال اسم الموديل المخصص لـ Gemini.', 'error');
                return;
            }
        }
    } else if (engine === 'deepl') {
        if (!isEngineKeyConfigured('deepl')) {
            apiKeyVal = deeplKey.value ? deeplKey.value.trim() : null;
            if (!apiKeyVal) {
                showToast('مفتاح DeepL مطلوب. أضفه في .env على الخادم أو في الإعدادات.', 'error');
                return;
            }
        }
    } else if (engine === 'openai') {
        if (!isEngineKeyConfigured('openai')) {
            apiKeyVal = openaiKey.value ? openaiKey.value.trim() : null;
            if (!apiKeyVal) {
                showToast('مفتاح OpenAI مطلوب. أضفه في .env على الخادم أو في الإعدادات.', 'error');
                return;
            }
        }
        modelVal = openaiModelSelect.value;
        if (modelVal === 'custom') {
            modelVal = customOpenaiModelInput.value.trim();
            if (!modelVal) {
                showToast('يرجى إدخال اسم الموديل المخصص لـ OpenAI.', 'error');
                return;
            }
        }
    } else if (engine === 'claude') {
        if (!isEngineKeyConfigured('claude')) {
            apiKeyVal = claudeKey.value ? claudeKey.value.trim() : null;
            if (!apiKeyVal) {
                showToast('مفتاح Claude مطلوب. أضفه في .env على الخادم أو في الإعدادات.', 'error');
                return;
            }
        }
        modelVal = claudeModelSelect.value;
        if (modelVal === 'custom') {
            modelVal = customClaudeModelInput.value.trim();
            if (!modelVal) {
                showToast('يرجى إدخال اسم الموديل المخصص لـ Claude.', 'error');
                return;
            }
        }
    } else if (engine === 'libretranslate') {
        customHostVal = libreHost.value ? libreHost.value.trim() : 'https://libretranslate.de';
        if (!isEngineKeyConfigured('libretranslate')) {
            apiKeyVal = libreKey.value ? libreKey.value.trim() : null;
        }
    }
    
    showToast(`بدأت ترجمة الفصل ${chaptersData[index].chapter_num} في الخلفية...`, 'info');
    
    try {
        const res = await fetch('/api/translate', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                chapter_id: chapterId,
                engine: engine,
                api_key: apiKeyVal,
                model: modelVal,
                custom_host: customHostVal
            })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            chaptersData[index].translation_status = 'processing';
            renderChaptersList();
            startPolling();
        } else {
            showToast(data.detail || 'فشل تشغيل مهمة الترجمة.', 'error');
        }
    } catch (err) {
        showToast('فشل الاتصال بالخادم لطلب الترجمة.', 'error');
    }
}

async function generateTTS(chapterId, index) {
    const selectedVoice = voiceSelect.value;
    const selectedRate = voiceRateSelect.value;
    
    showToast(`بدأ توليد الصوت للفصل ${chaptersData[index].chapter_num} في الخلفية...`, 'info');
    
    try {
        const res = await fetch('/api/tts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                chapter_id: chapterId,
                voice: selectedVoice,
                rate: selectedRate
            })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            chaptersData[index].tts_status = 'processing';
            renderChaptersList();
            startPolling();
        } else {
            showToast(data.detail || 'فشل تشغيل مهمة تحويل الصوت.', 'error');
        }
    } catch (err) {
        showToast('فشل الاتصال بالخادم لطلب توليد الصوت.', 'error');
    }
}

/* ==========================================
   Upload Book handlers
   ========================================== */
uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});
uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});
uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

function handleFileSelect(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showToast('يرجى اختيار ملف PDF صالح فقط.', 'error');
        return;
    }
    
    const maxFileSize = getMaxUploadBytes();
    if (file.size > maxFileSize) {
        showToast(`حجم الملف كبير جداً. الحد الأقصى المسموح به هو ${formatUploadLimitMb()} ميجابايت.`, 'error');
        return;
    }
    
    uploadedFileName.textContent = file.name;
    uploadedFileSize.textContent = formatBytes(file.size);
    uploadZone.style.display = 'none';
    fileInfo.style.display = 'flex';
    
    uploadPDFFile(file);
}

removeFileBtn.addEventListener('click', () => {
    fileInput.value = '';
    uploadZone.style.display = 'block';
    fileInfo.style.display = 'none';
    emptyState.style.display = 'flex';
    chaptersCard.style.display = 'none';
    translationPreviewCard.style.display = 'none';
    stopPolling();
    currentProjectId = null;
    chaptersData = [];
    activeChapterIndex = -1;
});

async function uploadPDFFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_lang', sourceLangSelect.value);
    if (pageFromInput && pageFromInput.value) {
        formData.append('page_from', pageFromInput.value);
    }
    if (pageToInput && pageToInput.value) {
        formData.append('page_to', pageToInput.value);
    }
    
    showToast('جاري رفع ومعالجة ملف الـ PDF في الخلفية...', 'info');
    
    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });

        const { data, text } = await readApiResponse(res);
        if (res.ok && data?.success) {
            currentProjectId = data.project_id;
            showToast('تم رفع الكتاب وبدأت التجزئة في الخلفية!', 'success');
            startPolling();
        } else {
            const detail = data?.detail || describeUploadFailure(res, text);
            throw new Error(detail);
        }
    } catch (err) {
        showToast(`فشل رفع الملف: ${err.message}`, 'error');
        removeFileBtn.click();
    }
}

/* ==========================================
   Bulk processing (Translate / TTS All)
   ========================================== */
function updateBulkProgress(completedSteps, totalSteps, statusText) {
    const pct = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
    bulkProgressPercent.textContent = `${pct}%`;
    bulkProgressBar.style.width = `${pct}%`;
    bulkProgressStatus.textContent = statusText;
}

function resetBulkUI() {
    isBulkProcessing = false;
    bulkAbortRequested = false;
    translateAllBtn.disabled = false;
    if (translateSelectedBtn) translateSelectedBtn.disabled = selectedChapterIds.size === 0;
    if (ttsSelectedBtn) ttsSelectedBtn.disabled = selectedChapterIds.size === 0;
    stopAllBtn.disabled = false;
    stopAllBtn.style.display = 'none';
    bulkProgressContainer.style.display = 'none';
    bulkProgressBar.style.width = '0%';
    bulkProgressPercent.textContent = '0%';
    updateSelectionButtons();
}

async function waitForChapterStep(chapterId, step, timeoutMs = 300000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        if (bulkAbortRequested) return false;
        await fetchProjectDetails();
        const chapter = chaptersData.find(ch => ch.id === chapterId);
        if (!chapter) return false;

        const status = step === 'translation' ? chapter.translation_status : chapter.tts_status;
        if (status === 'completed') return true;
        if (status === 'failed') return false;
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    return false;
}

async function runBulkPipeline(targetChapters, { doTranslate = true, doTts = true } = {}) {
    if (isBulkProcessing || targetChapters.length === 0) return;

    isBulkProcessing = true;
    bulkAbortRequested = false;
    translateAllBtn.disabled = true;
    if (translateSelectedBtn) translateSelectedBtn.disabled = true;
    if (ttsSelectedBtn) ttsSelectedBtn.disabled = true;
    stopAllBtn.style.display = 'inline-flex';
    bulkProgressContainer.style.display = 'block';
    startPolling();

    let chaptersNeedingTranslation = 0;
    let chaptersNeedingTts = 0;
    if (doTranslate) {
        chaptersNeedingTranslation = targetChapters.filter(
            ch => ch.translation_status !== 'completed' && ch.translation_status !== 'processing'
        ).length;
    }
    if (doTts) {
        chaptersNeedingTts = targetChapters.filter(
            ch => ch.translation_status === 'completed' && ch.tts_status !== 'completed' && ch.tts_status !== 'processing'
        ).length;
    }
    const totalSteps = chaptersNeedingTranslation + chaptersNeedingTts;
    let completedSteps = 0;

    updateBulkProgress(0, totalSteps, 'بدء المعالجة...');

    for (let i = 0; i < targetChapters.length; i++) {
        if (bulkAbortRequested) break;

        let chapter = targetChapters[i];
        const idx = chaptersData.findIndex(ch => ch.id === chapter.id);

        if (doTranslate && chapter.translation_status !== 'completed' && chapter.translation_status !== 'processing') {
            updateBulkProgress(completedSteps, totalSteps, `ترجمة الفصل ${chapter.chapter_num}...`);
            await translateChapter(chapter.id, idx);
            const translated = await waitForChapterStep(chapter.id, 'translation');
            if (!translated) {
                if (!bulkAbortRequested) {
                    showToast(`توقفت المعالجة عند الفصل ${chapter.chapter_num}.`, 'error');
                }
                break;
            }
            completedSteps++;
            chapter = chaptersData.find(ch => ch.id === chapter.id) || chapter;
        }

        if (bulkAbortRequested) break;

        if (doTts && chapter.translation_status === 'completed' && chapter.tts_status !== 'completed' && chapter.tts_status !== 'processing') {
            updateBulkProgress(completedSteps, totalSteps, `توليد الصوت للفصل ${chapter.chapter_num}...`);
            await generateTTS(chapter.id, idx);
            const voiced = await waitForChapterStep(chapter.id, 'tts');
            if (!voiced) {
                if (!bulkAbortRequested) {
                    showToast(`توقفت المعالجة عند الفصل ${chapter.chapter_num} (TTS).`, 'error');
                }
                break;
            }
            completedSteps++;
        }
    }

    if (bulkAbortRequested) {
        showToast('تم إيقاف المعالجة.', 'info');
    } else if (totalSteps > 0 && completedSteps === totalSteps) {
        updateBulkProgress(totalSteps, totalSteps, 'اكتملت المعالجة بنجاح!');
        showToast('اكتملت معالجة الفصول المحددة!', 'success');
    }

    resetBulkUI();
    await fetchProjectDetails();
}

translateAllBtn.addEventListener('click', async () => {
    if (chaptersData.length === 0) return;
    showToast('بدأت ترجمة وتوليد الصوت لكافة الفصول.', 'info');
    await runBulkPipeline(chaptersData, { doTranslate: true, doTts: true });
});

if (translateSelectedBtn) {
    translateSelectedBtn.addEventListener('click', async () => {
        const selected = getSelectedChapters();
        if (selected.length === 0) {
            showToast('حدد فصلاً واحداً على الأقل.', 'warning');
            return;
        }
        showToast(`بدأت ترجمة ${selected.length} فصل محدد.`, 'info');
        await runBulkPipeline(selected, { doTranslate: true, doTts: false });
    });
}

if (ttsSelectedBtn) {
    ttsSelectedBtn.addEventListener('click', async () => {
        const selected = getSelectedChapters().filter(ch => ch.translation_status === 'completed');
        if (selected.length === 0) {
            showToast('حدد فصولاً مترجمة لتوليد الصوت.', 'warning');
            return;
        }
        showToast(`بدأ توليد الصوت لـ ${selected.length} فصل.`, 'info');
        await runBulkPipeline(selected, { doTranslate: false, doTts: true });
    });
}

if (selectAllChaptersCheckbox) {
    selectAllChaptersCheckbox.addEventListener('change', (e) => {
        if (e.target.checked) {
            chaptersData.forEach(ch => selectedChapterIds.add(ch.id));
        } else {
            selectedChapterIds.clear();
        }
        renderChaptersList();
        updateSelectionButtons();
    });
}

if (reextractBtn) {
    reextractBtn.addEventListener('click', async () => {
        if (!currentProjectId || !projectHasStoredPdf) return;
        if (!confirm('سيتم حذف الفصول الحالية وإعادة تقسيم الكتاب. هل تريد المتابعة؟')) return;

        const body = {};
        if (reextractPageFrom && reextractPageFrom.value) body.page_from = Number(reextractPageFrom.value);
        if (reextractPageTo && reextractPageTo.value) body.page_to = Number(reextractPageTo.value);

        reextractBtn.disabled = true;
        try {
            const res = await fetch(`/api/projects/${currentProjectId}/re-extract`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify(body)
            });
            const data = await res.json();
            if (res.ok && data.success) {
                selectedChapterIds.clear();
                showToast('بدأت إعادة تقسيم الكتاب...', 'info');
                startPolling();
            } else {
                showToast(data.detail || 'فشل إعادة التقسيم.', 'error');
            }
        } catch (err) {
            showToast('فشل الاتصال بالخادم.', 'error');
        } finally {
            reextractBtn.disabled = false;
        }
    });
}

stopAllBtn.addEventListener('click', () => {
    if (!isBulkProcessing) return;
    bulkAbortRequested = true;
    stopAllBtn.disabled = true;
    showToast('جاري إيقاف المعالجة الجماعية...', 'info');
});

/* ==========================================
   Authenticated file download helper
   ========================================== */
async function downloadAuthenticatedFile(url, filename, successMessage, expectedMimeParts = []) {
    showToast('جاري تحضير الملف...', 'info');
    try {
        const res = await fetch(url, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.status === 401) {
            throw new Error('انتهت الجلسة. سجّل الدخول مجدداً ثم أعد المحاولة.');
        }
        if (!res.ok) {
            const { data, text } = await readApiResponse(res);
            throw new Error((data && data.detail) || text || 'تعذر التحميل');
        }

        const contentType = (res.headers.get('content-type') || '').toLowerCase();
        if (expectedMimeParts.length && !expectedMimeParts.some((part) => contentType.includes(part))) {
            throw new Error('الملف المستلم غير صالح. أعد تسجيل الدخول وحاول مرة أخرى.');
        }

        const buffer = await res.arrayBuffer();
        if (!buffer.byteLength) {
            throw new Error('الملف فارغ.');
        }

        const mimeType = contentType.split(';')[0] || 'application/octet-stream';
        const blob = new Blob([buffer], { type: mimeType });
        const blobUrl = window.URL.createObjectURL(blob);
        const safeName = (filename || 'download').replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_');
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = safeName;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();

        // Opening PDF in a new tab helps when the browser blocks programmatic downloads.
        if (mimeType.includes('pdf')) {
            const viewer = window.open(blobUrl, '_blank', 'noopener,noreferrer');
            if (!viewer) {
                showToast('إذا لم يبدأ التحميل، اسمح بالنوافذ المنبثقة ثم أعد المحاولة.', 'warning');
            }
        }

        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(blobUrl);
        }, 4000);

        if (successMessage) showToast(successMessage, 'success');
    } catch (err) {
        showToast(err.message || 'تعذر تحميل الملف.', 'error');
    }
}

/* ==========================================
   Exports (ZIP / PDF / Audiobook)
   ========================================== */
exportZipBtn.addEventListener('click', () => {
    if (!currentProjectId) return;
    downloadAuthenticatedFile(
        `/api/projects/${currentProjectId}/export-zip`,
        `book_project_${currentProjectId}.zip`,
        'تم تحميل ملف ZIP بنجاح!',
        ['zip', 'octet-stream']
    );
});

exportPdfBtn.addEventListener('click', () => {
    if (!currentProjectId) return;
    const bookName = (uploadedFileName && uploadedFileName.textContent)
        ? uploadedFileName.textContent.replace(/\.pdf$/i, '_Arabic.pdf')
        : `book_${currentProjectId}_Arabic.pdf`;
    downloadAuthenticatedFile(
        `/api/projects/${currentProjectId}/export-pdf`,
        bookName,
        'تم تحميل كتاب PDF العربي بنجاح!',
        ['pdf']
    );
});

exportAudiobookBtn.addEventListener('click', async () => {
    if (!currentProjectId) return;
    showToast('جاري تجميع ودمج الصوتيات لإنشاء كتاب صوتي كامل...', 'info');
    
    exportAudiobookBtn.disabled = true;
    
    try {
        const formData = new FormData();
        formData.append('pause_seconds', 2);
        
        const res = await fetch(`/api/projects/${currentProjectId}/export-audiobook`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });
        
        const data = await res.json();
        if (res.ok && data.audiobook_url) {
            showToast('اكتمل دمج الكتاب الصوتي! سيبدأ التحميل الآن.', 'success');
            // Download the audiobook file
            const a = document.createElement('a');
            a.href = data.audiobook_url;
            a.target = '_blank';
            a.download = `audiobook_${currentProjectId}.mp3`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            showToast(data.detail || 'فشل دمج الكتاب الصوتي.', 'error');
        }
    } catch (err) {
        showToast('خطأ أثناء الاتصال بالخادم لدمج الكتاب الصوتي.', 'error');
    } finally {
        exportAudiobookBtn.disabled = false;
    }
});

/* ==========================================
   Voice Preview & Player Logic
   ========================================== */
previewVoiceBtn.addEventListener('click', async () => {
    const selectedVoice = voiceSelect.value;
    
    previewVoiceBtn.disabled = true;
    showToast('جاري توليد عينة الصوت...', 'info');
    
    try {
        const res = await fetch('/api/tts', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                chapter_id: -1,
                voice: selectedVoice,
                rate: "+0%"
            })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast('تم توليد عينة الصوت بنجاح!', 'success');
            const audio = new Audio(data.audio_url);
            audio.play();
        } else {
            showToast(data.detail || 'فشل توليد عينة الصوت.', 'error');
        }
    } catch (err) {
        showToast('فشل الاتصال بالخادم لتوليد عينة الصوت.', 'error');
    } finally {
        previewVoiceBtn.disabled = false;
    }
});

saveTranslationBtn.addEventListener('click', async () => {
    if (activeChapterIndex === -1) return;
    const chapter = chaptersData[activeChapterIndex];
    const editedText = translatedTextView.value.trim();
    if (!editedText) {
        showToast('لا يوجد نص للحفظ.', 'error');
        return;
    }

    saveTranslationBtn.disabled = true;
    try {
        const res = await fetch(`/api/chapters/${chapter.id}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ translated_text: editedText })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            chapter.translated_text = editedText;
            chapter.translation_status = 'completed';
            chapter.translation_engine = chapter.translation_engine || 'manual';
            translationMethodBadge.textContent = 'تعديل يدوي';
            translationMethodBadge.style.display = 'inline-block';
            downloadTextBtn.disabled = false;
            renderChaptersList();
            showToast('تم حفظ الترجمة المعدّلة.', 'success');
        } else {
            showToast(data.detail || 'فشل حفظ الترجمة.', 'error');
        }
    } catch (err) {
        showToast('فشل الاتصال بالخادم أثناء حفظ الترجمة.', 'error');
    } finally {
        saveTranslationBtn.disabled = false;
    }
});

translatedTextView.addEventListener('input', () => {
    if (activeChapterIndex === -1) return;
    saveTranslationBtn.disabled = !translatedTextView.value.trim();
});

// Download buttons
downloadTextBtn.addEventListener('click', () => {
    if (activeChapterIndex === -1) return;
    const chapter = chaptersData[activeChapterIndex];
    const textToDownload = translatedTextView.value.trim() || chapter.translated_text;
    if (!textToDownload) return;

    const blob = new Blob([textToDownload], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Chapter_${chapter.chapter_num}_Arabic.txt`;
    a.click();
    URL.revokeObjectURL(url);
});

downloadPdfBtn.addEventListener('click', () => {
    if (activeChapterIndex === -1) return;
    const chapter = chaptersData[activeChapterIndex];
    if (!chapter.translated_text) return;
    downloadAuthenticatedFile(
        `/api/chapters/${chapter.id}/export-pdf`,
        `Chapter_${chapter.chapter_num}_Arabic.pdf`,
        'تم تحميل PDF الفصل بنجاح!',
        ['pdf']
    );
});

downloadAudioBtn.addEventListener('click', () => {
    if (activeChapterIndex === -1) return;
    const chapter = chaptersData[activeChapterIndex];
    if (!chapter.audio_url) return;
    
    const a = document.createElement('a');
    a.href = chapter.audio_url;
    a.target = '_blank';
    a.download = `Chapter_${chapter.chapter_num}_Arabic.mp3`;
    a.click();
});

function setupAudioPlayer(audioUrl, vttUrl) {
    audioSource.src = audioUrl;
    
    // Add subtitle track if VTT exists
    const oldTrack = document.getElementById('audio-track');
    if (oldTrack) oldTrack.remove();
    
    if (vttUrl) {
        const track = document.createElement('track');
        track.id = 'audio-track';
        track.kind = 'subtitles';
        track.src = vttUrl;
        track.srclang = 'ar';
        track.label = 'العربية';
        track.default = true;
        mainAudioPlayer.appendChild(track);
        
        subtitleSyncBox.style.display = 'block';
        initSubtitlesTrack();
    } else {
        subtitleSyncBox.style.display = 'none';
    }
    
    mainAudioPlayer.load();
}

function resetAudioPlayer() {
    audioSource.src = '';
    const track = document.getElementById('audio-track');
    if (track) track.remove();
    subtitleSyncBox.style.display = 'none';
    mainAudioPlayer.load();
}

function initSubtitlesTrack() {
    mainAudioPlayer.addEventListener('timeupdate', () => {
        const activeCues = mainAudioPlayer.textTracks[0]?.activeCues;
        if (activeCues && activeCues.length > 0) {
            currentSpokenText.textContent = activeCues[0].text;
            subtitleSyncBox.classList.add('active');
        } else {
            subtitleSyncBox.classList.remove('active');
        }
    });
}

/* ==========================================
   Settings Management (Local Storage)
   ========================================== */
function initSettingsListeners() {
    translatorSelect.addEventListener('change', (e) => {
        // Toggle settings panels based on engine
        const engine = e.target.value;
        geminiSettings.style.display = (engine === 'gemini') ? 'block' : 'none';
        deeplSettings.style.display = (engine === 'deepl') ? 'block' : 'none';
        openaiSettings.style.display = (engine === 'openai') ? 'block' : 'none';
        claudeSettings.style.display = (engine === 'claude') ? 'block' : 'none';
        libretranslateSettings.style.display = (engine === 'libretranslate') ? 'block' : 'none';
        
        if (saveSettingsCheckbox.checked) saveSettings();
    });
    
    geminiModelSelect.addEventListener('change', (e) => {
        customModelInputGroup.style.display = (e.target.value === 'custom') ? 'block' : 'none';
        if (saveSettingsCheckbox.checked) saveSettings();
    });
    
    openaiModelSelect.addEventListener('change', (e) => {
        customOpenaiModelGroup.style.display = (e.target.value === 'custom') ? 'block' : 'none';
        if (saveSettingsCheckbox.checked) saveSettings();
    });
    
    claudeModelSelect.addEventListener('change', (e) => {
        customClaudeModelGroup.style.display = (e.target.value === 'custom') ? 'block' : 'none';
        if (saveSettingsCheckbox.checked) saveSettings();
    });
    
    // Auto save on key/value changes if checkbox enabled
    [geminiKey, customModelInput, deeplKey, openaiKey, customOpenaiModelInput, claudeKey, customClaudeModelInput, libreHost, libreKey, voiceSelect, voiceRateSelect].forEach(elem => {
        elem.addEventListener('change', () => {
            if (saveSettingsCheckbox.checked) saveSettings();
        });
    });
    
    saveSettingsCheckbox.addEventListener('change', (e) => {
        if (e.target.checked) {
            saveSettings();
        } else {
            clearSavedSettings();
        }
    });
}

function saveSettings() {
    const settings = {
        engine: translatorSelect.value,
        gemini_model: geminiModelSelect.value,
        gemini_custom: customModelInput.value,
        openai_model: openaiModelSelect.value,
        openai_custom: customOpenaiModelInput.value,
        claude_model: claudeModelSelect.value,
        claude_custom: customClaudeModelInput.value,
        libre_host: libreHost.value,
        voice: voiceSelect.value,
        rate: voiceRateSelect.value
    };
    localStorage.setItem('translator_settings', JSON.stringify(settings));
    localStorage.setItem('save_settings_enabled', 'true');
}

function loadSavedSettings() {
    const enabled = localStorage.getItem('save_settings_enabled') === 'true';
    saveSettingsCheckbox.checked = enabled;
    
    if (!enabled) return;
    
    const settingsStr = localStorage.getItem('translator_settings');
    if (!settingsStr) return;
    
    try {
        const settings = JSON.parse(settingsStr);
        translatorSelect.value = settings.engine || 'google';
        translatorSelect.dispatchEvent(new Event('change'));
        
        geminiModelSelect.value = settings.gemini_model || 'gemini-3.5-flash';
        geminiModelSelect.dispatchEvent(new Event('change'));
        customModelInput.value = settings.gemini_custom || '';
        
        openaiModelSelect.value = settings.openai_model || 'gpt-4o-mini';
        openaiModelSelect.dispatchEvent(new Event('change'));
        customOpenaiModelInput.value = settings.openai_custom || '';
        
        claudeModelSelect.value = settings.claude_model || 'claude-3-5-sonnet-latest';
        claudeModelSelect.dispatchEvent(new Event('change'));
        customClaudeModelInput.value = settings.claude_custom || '';
        
        libreHost.value = settings.libre_host || 'https://libretranslate.de';
        
        voiceSelect.value = settings.voice || 'ar-SA-HamedNeural';
        voiceRateSelect.value = settings.rate || '+0%';
    } catch (e) {
        console.error(e);
    }
}

function clearSavedSettings() {
    localStorage.removeItem('translator_settings');
    localStorage.removeItem('save_settings_enabled');
}

/* ==========================================
   Utility Helpers
   ========================================== */
function showToast(message, type = 'info') {
    toastMessage.textContent = message;
    
    // Setup Icon based on type
    toastIcon.className = 'fa-solid';
    if (type === 'success') {
        toastIcon.classList.add('fa-circle-check', 'success-icon');
        toast.className = 'toast show success';
    } else if (type === 'error') {
        toastIcon.classList.add('fa-circle-exclamation', 'error-icon');
        toast.className = 'toast show error';
    } else if (type === 'warning') {
        toastIcon.classList.add('fa-triangle-exclamation', 'warning-icon');
        toast.className = 'toast show warning';
    } else {
        toastIcon.classList.add('fa-circle-info', 'info-icon');
        toast.className = 'toast show info';
    }
    
    // Hide toast after 4.5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 4500);
}

function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}
