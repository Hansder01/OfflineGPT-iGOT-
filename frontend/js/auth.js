/**
 * Offline GPT — User Authentication & Session UI Manager
 */

document.addEventListener('DOMContentLoaded', () => {
    const authModal = document.getElementById('auth-modal');
    const userProfileBtn = document.getElementById('user-profile-btn');
    const closeModalBtn = document.getElementById('close-auth-modal');
    const userDisplayName = document.getElementById('user-display-name');

    const loginTabBtn = document.getElementById('auth-tab-login');
    const regTabBtn = document.getElementById('auth-tab-register');
    const loginForm = document.getElementById('login-form');
    const regForm = document.getElementById('register-form');
    const loginErr = document.getElementById('login-error');
    const regErr = document.getElementById('register-error');

    let currentUser = null;

    // Check user auth status on start
    async function checkAuthStatus() {
        try {
            const data = await ApiClient.getProfile();
            if (data.authenticated && data.user) {
                currentUser = data.user;
                userDisplayName.innerText = currentUser.username;
                userProfileBtn.classList.add('logged-in');
            } else {
                currentUser = null;
                userDisplayName.setAttribute('data-i18n', 'guest_user');
                userDisplayName.innerText = translations[currentLang]?.guest_user || "Guest";
            }
        } catch (e) {
            currentUser = null;
        }
    }

    userProfileBtn.addEventListener('click', () => {
        if (currentUser) {
            if (confirm(`Logged in as ${currentUser.username}. Do you want to logout?`)) {
                ApiClient.logout().then(() => {
                    ApiClient.setToken(null);
                    checkAuthStatus();
                    showToast("Logged out of session.");
                });
            }
        } else {
            authModal.classList.remove('hidden');
        }
    });

    closeModalBtn.addEventListener('click', () => {
        authModal.classList.add('hidden');
    });

    loginTabBtn.addEventListener('click', () => {
        loginTabBtn.classList.add('active');
        regTabBtn.classList.remove('active');
        loginForm.classList.remove('hidden');
        regForm.classList.add('hidden');
    });

    regTabBtn.addEventListener('click', () => {
        regTabBtn.classList.add('active');
        loginTabBtn.classList.remove('active');
        regForm.classList.remove('hidden');
        loginForm.classList.add('hidden');
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginErr.classList.add('hidden');
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        try {
            const res = await ApiClient.login(username, password);
            ApiClient.setToken(res.access_token);
            authModal.classList.add('hidden');
            checkAuthStatus();
            showToast(`Welcome back, ${res.user.username}!`);
            if (window.loadRateLimitStatus) window.loadRateLimitStatus();
        } catch (err) {
            loginErr.innerText = err.message;
            loginErr.classList.remove('hidden');
        }
    });

    regForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        regErr.classList.add('hidden');
        const username = document.getElementById('reg-username').value;
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;

        try {
            const res = await ApiClient.register(username, email, password);
            ApiClient.setToken(res.access_token);
            authModal.classList.add('hidden');
            checkAuthStatus();
            showToast(`Account created for ${res.user.username}!`);
            if (window.loadRateLimitStatus) window.loadRateLimitStatus();
        } catch (err) {
            regErr.innerText = err.message;
            regErr.classList.remove('hidden');
        }
    });

    checkAuthStatus();
});
