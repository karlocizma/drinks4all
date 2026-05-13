const errorEl = document.getElementById('error');
const reportOut = document.getElementById('report-output');
const monthInput = document.getElementById('report-month');
const userList = document.getElementById('user-list');
const pendingUserList = document.getElementById('pending-user-list');
const drinkList = document.getElementById('drink-list');
const statsCards = document.getElementById('stats-cards');
const statsUsers = document.getElementById('stats-users');
const statsDrinks = document.getElementById('stats-drinks');
const statsStock = document.getElementById('stats-stock');
const rawReportPanel = document.getElementById('raw-report-panel');
const toggleRawReportBtn = document.getElementById('toggle-raw-report');
const reportStatusEl = document.getElementById('report-status');

let users = [];
let pendingUsers = [];
let drinks = [];
let rawReportVisible = false;

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function eur(value) {
  return `€${Number(value || 0).toFixed(2)}`;
}

async function api(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || 'Request failed');
  }
  return res;
}

function renderUsers() {
  userList.innerHTML = users.map((u) => `
    <div class="drink-admin-row">
      <div style="flex:1;min-width:0;">
        <strong>${u.name}</strong>
        <span style="font-size:0.8rem;color:var(--fg-muted);margin-left:0.4rem;">${u.email}</span>
        <span class="stock-pill ${u.is_active ? 'ok' : 'low'}" style="margin-left:0.4rem;">${u.role}</span>
        ${!u.is_active ? '<span class="stock-pill low" style="margin-left:0.25rem;">inactive</span>' : ''}
      </div>
      <div style="display:flex;gap:0.4rem;">
        <button class="btn btn-secondary btn-icon" data-act="user-edit" data-id="${u.id}">
          <i data-lucide="pencil" style="width:15px;height:15px;pointer-events:none;"></i>
        </button>
        <button class="btn btn-danger btn-icon" data-act="user-del" data-id="${u.id}">
          <i data-lucide="trash-2" style="width:15px;height:15px;pointer-events:none;"></i>
        </button>
      </div>
    </div>
  `).join('') || '<p style="color:var(--fg-muted);">No users</p>';
  lucide.createIcons();
}

function renderPendingUsers() {
  pendingUserList.innerHTML = pendingUsers.map((u) => `
    <div class="drink-admin-row">
      <span style="flex:1;">#${u.id} ${u.name} (${u.email})</span>
      <div style="display:flex;gap:0.4rem;">
        <button class="btn btn-primary btn-icon" data-act="pending-approve" data-id="${u.id}">Approve</button>
        <button class="btn btn-danger btn-icon" data-act="pending-reject" data-id="${u.id}">Reject</button>
      </div>
    </div>
  `).join('') || '<p style="color:var(--fg-muted);">No pending approvals</p>';
  lucide.createIcons();
}

function renderDrinks() {
  drinkList.innerHTML = drinks.map((d) => {
    const stockClass = d.stock_quantity == null ? 'inf' : (d.stock_quantity <= d.low_stock_threshold ? 'low' : 'ok');
    const stockLabel = d.stock_quantity == null ? '∞' : d.stock_quantity;
    return `
      <div class="drink-admin-row" style="opacity:${d.is_active ? 1 : 0.55}">
        ${d.photo_url ? `<img src="${d.photo_url}" alt="${d.name}" style="width:40px;height:40px;object-fit:cover;border-radius:6px;flex-shrink:0;">` : '<div style="width:40px;height:40px;background:var(--bg2);border-radius:6px;flex-shrink:0;"></div>'}
        <div style="flex:1;min-width:0;">
          <strong>${d.name}</strong>
          <span style="font-size:0.8rem;color:var(--fg-muted);margin-left:0.4rem;">${eur(d.unit_price)}</span>
          <span class="stock-pill ${stockClass}" style="margin-left:0.4rem;">stock: ${stockLabel}</span>
          ${!d.is_active ? '<span class="stock-pill low" style="margin-left:0.25rem;">inactive</span>' : ''}
        </div>
        <button class="btn btn-secondary btn-icon" data-act="drink-edit" data-id="${d.id}">
          <i data-lucide="pencil" style="width:15px;height:15px;pointer-events:none;"></i>
        </button>
      </div>
    `;
  }).join('') || '<p style="color:var(--fg-muted);">No drinks</p>';
  lucide.createIcons();
}

async function loadUsers() {
  const res = await api('/admin/users');
  users = await res.json();
  renderUsers();
  const pendingRes = await api('/admin/users/pending');
  pendingUsers = await pendingRes.json();
  renderPendingUsers();
}

async function loadDrinks() {
  const res = await api('/admin/drinks');
  drinks = await res.json();
  renderDrinks();
}

async function loadReport() {
  const month = monthInput.value || currentMonth();
  const res = await api(`/admin/reports?month=${month}`);
  const data = await res.json();
  reportOut.textContent = JSON.stringify(data, null, 2);
  renderStats(data);
}

function renderBar(label, value, maxValue, subtext) {
  const width = maxValue > 0 ? Math.max(6, Math.round((value / maxValue) * 100)) : 6;
  return `
    <div class="metric-row">
      <div class="metric-head">
        <span>${label}</span>
        <span>${subtext}</span>
      </div>
      <div class="metric-track"><div class="metric-fill" style="width:${width}%"></div></div>
    </div>
  `;
}

function renderStats(data) {
  const users = data.users || [];
  const drinks = data.drinks || [];
  const stock = data.low_stock || [];
  const overall = Number(data.overall_total || 0);
  const totalUnits = users.reduce((sum, u) => sum + Number(u.total_units || 0), 0);
  const activeUsers = users.filter((u) => Number(u.total_units || 0) > 0).length;
  const topDrink = [...drinks].sort((a, b) => Number(b.total_amount) - Number(a.total_amount))[0];

  statsCards.innerHTML = `
    <article class="stat-card"><span>💶 Revenue</span><strong>${eur(overall)}</strong></article>
    <article class="stat-card"><span>🥤 Units</span><strong>${totalUnits}</strong></article>
    <article class="stat-card"><span>🧑 Active Users</span><strong>${activeUsers}</strong></article>
    <article class="stat-card"><span>🏆 Top Drink</span><strong>${topDrink ? topDrink.drink_name : '-'}</strong></article>
  `;

  const maxUserAmount = Math.max(0, ...users.map((u) => Number(u.total_amount || 0)));
  statsUsers.innerHTML = users.length
    ? users
        .map((u) =>
          renderBar(
            u.name,
            Number(u.total_amount || 0),
            maxUserAmount,
            `${eur(u.total_amount)} · ${u.total_units} units`
          )
        )
        .join('')
    : '<p>No user data.</p>';

  const topDrinks = [...drinks]
    .sort((a, b) => Number(b.total_units) - Number(a.total_units))
    .slice(0, 6);
  const maxDrinkUnits = Math.max(0, ...topDrinks.map((d) => Number(d.total_units || 0)));
  statsDrinks.innerHTML = topDrinks.length
    ? topDrinks
        .map((d) =>
          renderBar(
            d.drink_name,
            Number(d.total_units || 0),
            maxDrinkUnits,
            `${d.total_units} units · ${eur(d.total_amount)}`
          )
        )
        .join('')
    : '<p>No drink data.</p>';

  statsStock.innerHTML = stock.length
    ? stock
        .map(
          (s) =>
            `<div class="stock-pill">⚠ ${s.drink_name}: ${s.stock_quantity} left (threshold ${s.low_stock_threshold})</div>`
        )
        .join('')
    : '<p>All good. No low stock alerts.</p>';

  reportStatusEl.textContent = data.is_closed
    ? `Month ${data.month} is closed. New drink entries for that month are blocked.`
    : `Month ${data.month} is open. Running billing will close it safely.`;
}

function setRawReportVisibility(visible) {
  rawReportVisible = visible;
  rawReportPanel.classList.toggle('hidden', !visible);
  if (visible) {
    rawReportPanel.removeAttribute('hidden');
  } else {
    rawReportPanel.setAttribute('hidden', '');
  }
  toggleRawReportBtn.textContent = visible ? 'Hide Raw Report JSON' : 'Show Raw Report JSON';
}

// Create user form
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
    e.target.reset();
    await loadUsers();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

// Create drink form
document.getElementById('drink-create-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';
  try {
    await api('/admin/drinks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('create-name').value,
        photo_url: document.getElementById('create-photo-url').value || '',
        unit_price: Number(document.getElementById('create-price').value),
        stock_quantity: document.getElementById('create-stock').value ? Number(document.getElementById('create-stock').value) : null,
        low_stock_threshold: Number(document.getElementById('create-threshold').value || 5),
        is_active: true,
      }),
    });
    e.target.reset();
    await loadDrinks();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

// Photo upload for create form
document.getElementById('upload-btn-create').addEventListener('click', () => {
  document.getElementById('upload-input-create').click();
});

document.getElementById('upload-input-create').addEventListener('change', async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await api('/admin/drinks/upload-image', { method: 'POST', body: fd });
    const payload = await res.json();
    document.getElementById('create-photo-url').value = payload.photo_url;
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

// User list actions
userList.addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const item = users.find((u) => u.id === id);
  if (!item) return;
  if (btn.dataset.act === 'user-edit') openUserModal(item);
  if (btn.dataset.act === 'user-del') confirmDeleteUser(id, item);
});

async function confirmDeleteUser(id, item) {
  if (!confirm(`Delete user ${item.email}?`)) return;
  try {
    await api(`/admin/users/${id}`, { method: 'DELETE' });
    await loadUsers();
  } catch (err) {
    errorEl.textContent = err.message;
  }
}

pendingUserList.addEventListener('click', async (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const item = pendingUsers.find((u) => u.id === id);
  if (!item) return;
  try {
    if (btn.dataset.act === 'pending-approve') {
      await api(`/admin/users/${id}/approve`, { method: 'POST' });
    }
    if (btn.dataset.act === 'pending-reject') {
      if (!confirm(`Reject and delete pending user ${item.email}?`)) return;
      await api(`/admin/users/${id}`, { method: 'DELETE' });
    }
    await loadUsers();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

// Drink list actions
drinkList.addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const item = drinks.find((d) => d.id === id);
  if (!item) return;
  if (btn.dataset.act === 'drink-edit') openDrinkModal(item);
});

// Drink edit modal
const drinkModal = document.getElementById('drink-modal');

function openDrinkModal(drink) {
  document.getElementById('edit-drink-id').value = drink.id;
  document.getElementById('edit-name').value = drink.name;
  document.getElementById('edit-photo-url').value = drink.photo_url || '';
  document.getElementById('edit-price').value = drink.unit_price;
  document.getElementById('edit-stock').value = drink.stock_quantity ?? '';
  document.getElementById('edit-threshold').value = drink.low_stock_threshold ?? 5;
  document.getElementById('edit-active').checked = drink.is_active;
  const thumb = document.getElementById('edit-thumb');
  thumb.src = drink.photo_url || '';
  thumb.style.display = drink.photo_url ? '' : 'none';
  updateDrinkActiveLabel(drink.is_active);
  const modalErr = document.getElementById('drink-modal-error');
  modalErr.textContent = '';
  modalErr.style.display = 'none';
  drinkModal.style.display = '';
  lucide.createIcons();
}

function closeDrinkModal() {
  drinkModal.style.display = 'none';
}

function updateDrinkActiveLabel(active) {
  document.getElementById('edit-active-label').textContent = active
    ? 'Active — visible to users'
    : 'Inactive — hidden from users';
}

document.getElementById('edit-active').addEventListener('change', (e) => {
  updateDrinkActiveLabel(e.target.checked);
});

document.getElementById('drink-modal-close').addEventListener('click', closeDrinkModal);
document.getElementById('drink-cancel-btn').addEventListener('click', closeDrinkModal);

drinkModal.addEventListener('click', (e) => {
  if (e.target === drinkModal) closeDrinkModal();
});

document.getElementById('drink-save-btn').addEventListener('click', async () => {
  const id = Number(document.getElementById('edit-drink-id').value);
  errorEl.textContent = '';
  try {
    await api(`/admin/drinks/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('edit-name').value,
        photo_url: document.getElementById('edit-photo-url').value || '',
        unit_price: Number(document.getElementById('edit-price').value),
        stock_quantity: document.getElementById('edit-stock').value !== '' ? Number(document.getElementById('edit-stock').value) : null,
        low_stock_threshold: Number(document.getElementById('edit-threshold').value || 5),
        is_active: document.getElementById('edit-active').checked,
      }),
    });
    closeDrinkModal();
    await loadDrinks();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('drink-delete-btn').addEventListener('click', async () => {
  const id = Number(document.getElementById('edit-drink-id').value);
  const drink = drinks.find((d) => d.id === id);
  const modalErr = document.getElementById('drink-modal-error');
  modalErr.textContent = '';
  modalErr.style.display = 'none';

  if (!confirm(`Delete drink "${drink ? drink.name : id}"?`)) return;

  // First attempt — without force, to detect consumption records
  const probe = await fetch(`/admin/drinks/${id}`, { method: 'DELETE' });
  if (probe.status === 409) {
    const count = await probe.json().then((j) => j.detail).catch(() => '?');
    const word = Number(count) === 1 ? 'record' : 'records';
    if (!confirm(`This drink has ${count} consumption ${word}.\n\nAll consumption history will be permanently deleted. Continue?`)) return;
    try {
      await api(`/admin/drinks/${id}?force=true`, { method: 'DELETE' });
    } catch (err) {
      modalErr.textContent = err.message;
      modalErr.style.display = 'block';
      return;
    }
  } else if (!probe.ok) {
    const message = await probe.text();
    modalErr.textContent = message || 'Delete failed.';
    modalErr.style.display = 'block';
    return;
  }

  closeDrinkModal();
  await loadDrinks();
});

// Photo upload for edit modal
document.getElementById('upload-btn-edit').addEventListener('click', () => {
  document.getElementById('upload-input-edit').click();
});

document.getElementById('upload-input-edit').addEventListener('change', async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await api('/admin/drinks/upload-image', { method: 'POST', body: fd });
    const payload = await res.json();
    document.getElementById('edit-photo-url').value = payload.photo_url;
    const thumb = document.getElementById('edit-thumb');
    thumb.src = payload.photo_url;
    thumb.style.display = '';
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

// Sync thumb when URL field changes
document.getElementById('edit-photo-url').addEventListener('input', (e) => {
  const thumb = document.getElementById('edit-thumb');
  if (e.target.value) {
    thumb.src = e.target.value;
    thumb.style.display = '';
  } else {
    thumb.style.display = 'none';
  }
});

// User edit modal
const userModal = document.getElementById('user-modal');

function openUserModal(user) {
  document.getElementById('edit-user-id').value = user.id;
  document.getElementById('edit-user-name').value = user.name;
  document.getElementById('edit-user-role').value = user.role;
  document.getElementById('edit-user-active').checked = user.is_active;
  userModal.style.display = '';
  lucide.createIcons();
}

function closeUserModal() {
  userModal.style.display = 'none';
}

document.getElementById('user-modal-close').addEventListener('click', closeUserModal);
document.getElementById('user-cancel-btn').addEventListener('click', closeUserModal);

userModal.addEventListener('click', (e) => {
  if (e.target === userModal) closeUserModal();
});

document.getElementById('user-save-btn').addEventListener('click', async () => {
  const id = Number(document.getElementById('edit-user-id').value);
  errorEl.textContent = '';
  try {
    await api(`/admin/users/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('edit-user-name').value,
        role: document.getElementById('edit-user-role').value,
        is_active: document.getElementById('edit-user-active').checked,
      }),
    });
    closeUserModal();
    await loadUsers();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('user-reset-pw-btn').addEventListener('click', async () => {
  const id = Number(document.getElementById('edit-user-id').value);
  const password = prompt('New password (min 6 chars)');
  if (!password) return;
  try {
    await api(`/admin/users/${id}/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    closeUserModal();
    errorEl.textContent = 'Password reset successfully.';
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('user-delete-btn').addEventListener('click', async () => {
  const id = Number(document.getElementById('edit-user-id').value);
  const user = users.find((u) => u.id === id);
  if (!confirm(`Delete user ${user ? user.email : id}?`)) return;
  try {
    await api(`/admin/users/${id}`, { method: 'DELETE' });
    closeUserModal();
    await loadUsers();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

// Reporting controls
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
    if (!confirm(`Run billing and close month ${month}? This does not delete data, but it blocks new drink entries for that month.`)) {
      return;
    }
    const res = await api(`/admin/run-billing?month=${month}`, { method: 'POST' });
    const data = await res.json();
    reportOut.textContent = JSON.stringify(data, null, 2);
    errorEl.textContent = `Billing finished for ${data.month}. Closed periods: ${data.closed_periods}.`;
    await loadReport();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('reset-month').addEventListener('click', async () => {
  const month = monthInput.value || currentMonth();
  const confirmation = prompt(`Type RESET ${month} to delete all billing data and consumptions for that month.`);
  if (confirmation !== `RESET ${month}`) {
    errorEl.textContent = 'Month reset cancelled.';
    return;
  }
  try {
    const res = await api(`/admin/reset-month?month=${month}`, { method: 'POST' });
    const data = await res.json();
    errorEl.textContent = `Month ${data.month} reset. Deleted consumptions: ${data.deleted_consumptions}. Restored stock units: ${data.restored_stock_units}.`;
    reportOut.textContent = JSON.stringify(data, null, 2);
    await loadDrinks();
    await loadReport();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

toggleRawReportBtn.addEventListener('click', () => {
  setRawReportVisibility(!rawReportVisible);
});

document.getElementById('logout-btn').addEventListener('click', async () => {
  await fetch('/auth/logout', { method: 'POST' });
  window.location.href = '/';
});

// Init
monthInput.value = currentMonth();
setRawReportVisibility(false);
Promise.all([loadUsers(), loadDrinks(), loadReport()]).catch(() => {
  window.location.href = '/';
});
