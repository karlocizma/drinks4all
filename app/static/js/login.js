const form = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const registerModal = document.getElementById('register-modal');
const openRegisterModalBtn = document.getElementById('open-register-modal');
const closeRegisterModalBtn = document.getElementById('close-register-modal');
const errorEl = document.getElementById('error');

const loginCard = document.getElementById('login-card');
const resetPasswordCard = document.getElementById('reset-password-card');
const resetPasswordForm = document.getElementById('reset-password-form');
const resetErrorEl = document.getElementById('reset-error');

const forgotPasswordModal = document.getElementById('forgot-password-modal');
const openForgotPasswordModalBtn = document.getElementById('open-forgot-password-modal');
const closeForgotPasswordModalBtn = document.getElementById('close-forgot-password-modal');
const forgotPasswordForm = document.getElementById('forgot-password-form');
const forgotPasswordMessageEl = document.getElementById('forgot-password-message');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';

  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const remember_me = document.getElementById('remember-me').checked;

  const response = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, remember_me }),
  });

  if (!response.ok) {
    const msg = await response.text();
    errorEl.textContent = msg || 'Login failed. Check credentials.';
    return;
  }

  const user = await response.json();
  window.location.href = user.role === 'ADMIN' ? '/admin' : '/dashboard';
});

registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';

  const name = document.getElementById('reg-name').value;
  const email = document.getElementById('reg-email').value;
  const password = document.getElementById('reg-password').value;

  const response = await fetch('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });

  if (!response.ok) {
    const msg = await response.text();
    errorEl.textContent = msg || 'Registration failed.';
    return;
  }

  errorEl.textContent = 'Registration submitted. Wait for admin approval.';
  registerForm.reset();
  closeRegisterModal();
});

function openRegisterModal() {
  registerModal.classList.remove('hidden');
  registerModal.removeAttribute('hidden');
}

function closeRegisterModal() {
  registerModal.classList.add('hidden');
  registerModal.setAttribute('hidden', '');
}

openRegisterModalBtn?.addEventListener('click', openRegisterModal);
closeRegisterModalBtn?.addEventListener('click', closeRegisterModal);

registerModal?.addEventListener('click', (e) => {
  if (e.target === registerModal) {
    closeRegisterModal();
  }
});

function openForgotPasswordModal() {
  forgotPasswordMessageEl.textContent = '';
  forgotPasswordModal.classList.remove('hidden');
  forgotPasswordModal.removeAttribute('hidden');
}

function closeForgotPasswordModal() {
  forgotPasswordModal.classList.add('hidden');
  forgotPasswordModal.setAttribute('hidden', '');
}

openForgotPasswordModalBtn?.addEventListener('click', openForgotPasswordModal);
closeForgotPasswordModalBtn?.addEventListener('click', closeForgotPasswordModal);

forgotPasswordModal?.addEventListener('click', (e) => {
  if (e.target === forgotPasswordModal) {
    closeForgotPasswordModal();
  }
});

forgotPasswordForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('forgot-email').value;

  const response = await fetch('/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });

  const data = await response.json();
  forgotPasswordMessageEl.textContent = data.message || 'If that email exists, a reset link has been sent.';
});

const resetToken = new URLSearchParams(window.location.search).get('reset_token');
if (resetToken) {
  loginCard.classList.add('hidden');
  loginCard.setAttribute('hidden', '');
  resetPasswordCard.classList.remove('hidden');
  resetPasswordCard.removeAttribute('hidden');
}

resetPasswordForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  resetErrorEl.textContent = '';

  const new_password = document.getElementById('reset-new-password').value;

  const response = await fetch('/auth/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: resetToken, new_password }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    resetErrorEl.textContent = data.detail || 'Could not reset password.';
    return;
  }

  window.location.href = '/';
});
