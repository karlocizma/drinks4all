const form = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const errorEl = document.getElementById('error');

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
});
