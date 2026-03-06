const errorEl = document.getElementById('error');
const reportOut = document.getElementById('report-output');
const monthInput = document.getElementById('report-month');
const userList = document.getElementById('user-list');

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

async function api(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || 'Request failed');
  }
  return res;
}

async function loadUsers() {
  const res = await api('/admin/users');
  const users = await res.json();
  userList.innerHTML = users.map((u) => `${u.name} (${u.email}) - ${u.role} - ${u.is_active ? 'active' : 'inactive'}`).join('<br/>');
}

async function loadReport() {
  const month = monthInput.value || currentMonth();
  const res = await api(`/admin/reports?month=${month}`);
  const data = await res.json();
  reportOut.textContent = JSON.stringify(data, null, 2);
}

document.getElementById('user-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';
  try {
    await api('/admin/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('user-name').value,
        email: document.getElementById('user-email').value,
        password: document.getElementById('user-password').value,
        role: document.getElementById('user-role').value,
      }),
    });
    await loadUsers();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('drink-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';
  try {
    await api('/admin/drinks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('drink-name').value,
        photo_url: document.getElementById('drink-photo').value,
        unit_price: Number(document.getElementById('drink-price').value),
        is_active: true,
      }),
    });
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('load-report').addEventListener('click', async () => {
  try {
    await loadReport();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('download-csv').addEventListener('click', () => {
  const month = monthInput.value || currentMonth();
  window.location.href = `/admin/reports?month=${month}&format=csv`;
});

document.getElementById('download-pdf').addEventListener('click', () => {
  const month = monthInput.value || currentMonth();
  window.location.href = `/admin/reports?month=${month}&format=pdf`;
});

document.getElementById('run-billing').addEventListener('click', async () => {
  const month = monthInput.value || currentMonth();
  try {
    const res = await api(`/admin/run-billing?month=${month}`, { method: 'POST' });
    const data = await res.json();
    reportOut.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('logout-btn').addEventListener('click', async () => {
  await fetch('/auth/logout', { method: 'POST' });
  window.location.href = '/';
});

monthInput.value = currentMonth();
loadUsers().catch(() => {
  window.location.href = '/';
});
loadReport().catch(() => {});
