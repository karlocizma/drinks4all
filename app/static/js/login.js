const form = document.getElementById('login-form');
const errorEl = document.getElementById('error');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';

  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  const response = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    errorEl.textContent = 'Login failed. Check credentials.';
    return;
  }

  const user = await response.json();
  window.location.href = user.role === 'ADMIN' ? '/admin' : '/dashboard';
});
