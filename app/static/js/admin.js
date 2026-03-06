const errorEl = document.getElementById('error');
const reportOut = document.getElementById('report-output');
const monthInput = document.getElementById('report-month');
const userList = document.getElementById('user-list');
const pendingUserList = document.getElementById('pending-user-list');
const teamList = document.getElementById('team-list');
const fridgeList = document.getElementById('fridge-list');
const drinkList = document.getElementById('drink-list');
const statsCards = document.getElementById('stats-cards');
const statsUsers = document.getElementById('stats-users');
const statsDrinks = document.getElementById('stats-drinks');
const statsStock = document.getElementById('stats-stock');

let teams = [];
let fridges = [];
let users = [];
let pendingUsers = [];
let drinks = [];

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

function fillSelect(id, items, labelFn, includeEmpty = true) {
  const el = document.getElementById(id);
  const options = [];
  if (includeEmpty) {
    options.push('<option value="">None</option>');
  }
  options.push(...items.map((item) => `<option value="${item.id}">${labelFn(item)}</option>`));
  el.innerHTML = options.join('');
}

function renderTeams() {
  teamList.innerHTML = teams.map((t) => `
    <div class="line-item">
      <span>#${t.id} ${t.name}</span>
      <div class="inline-actions">
        <button data-act="team-edit" data-id="${t.id}">Edit</button>
        <button data-act="team-del" data-id="${t.id}">Delete</button>
      </div>
    </div>
  `).join('') || 'No teams';
}

function renderFridges() {
  fridgeList.innerHTML = fridges.map((f) => `
    <div class="line-item">
      <span>#${f.id} ${f.name} (${f.location || 'no location'}) team:${f.team_id || '-'}</span>
      <div class="inline-actions">
        <button data-act="fridge-edit" data-id="${f.id}">Edit</button>
        <button data-act="fridge-del" data-id="${f.id}">Delete</button>
      </div>
    </div>
  `).join('') || 'No fridges';
}

function renderUsers() {
  userList.innerHTML = users.map((u) => `
    <div class="line-item">
      <span>#${u.id} ${u.name} (${u.email}) ${u.role} team:${u.team_id || '-'} ${u.is_active ? 'active' : 'inactive'}</span>
      <div class="inline-actions">
        <button data-act="user-edit" data-id="${u.id}">Edit</button>
        <button data-act="user-pass" data-id="${u.id}">Reset Password</button>
        <button data-act="user-del" data-id="${u.id}">Delete</button>
      </div>
    </div>
  `).join('') || 'No users';
}

function renderPendingUsers() {
  pendingUserList.innerHTML = pendingUsers.map((u) => `
    <div class="line-item">
      <span>#${u.id} ${u.name} (${u.email}) pending</span>
      <div class="inline-actions">
        <button data-act="pending-approve" data-id="${u.id}">Approve</button>
        <button data-act="pending-reject" data-id="${u.id}">Reject</button>
      </div>
    </div>
  `).join('') || 'No pending users';
}

function renderDrinks() {
  drinkList.innerHTML = drinks.map((d) => `
    <div class="line-item">
      <span>#${d.id} ${d.name} ${eur(d.unit_price)} stock:${d.stock_quantity ?? 'unlimited'} team:${d.team_id || '-'} fridge:${d.fridge_id || '-'}</span>
      <div class="inline-actions">
        <button data-act="drink-edit" data-id="${d.id}">Edit</button>
        <button data-act="drink-del" data-id="${d.id}">Delete</button>
      </div>
    </div>
  `).join('') || 'No drinks';
}

async function loadTeamsAndFridges() {
  const tRes = await api('/admin/teams');
  const fRes = await api('/admin/fridges');
  teams = await tRes.json();
  fridges = await fRes.json();

  renderTeams();
  renderFridges();

  fillSelect('user-team', teams, (t) => t.name);
  fillSelect('drink-team', teams, (t) => t.name);
  fillSelect('fridge-team', teams, (t) => t.name);
  fillSelect('drink-fridge', fridges, (f) => f.name);
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
}

document.getElementById('team-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';
  try {
    await api('/admin/teams', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: document.getElementById('team-name').value }),
    });
    document.getElementById('team-name').value = '';
    await loadTeamsAndFridges();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('fridge-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';
  try {
    await api('/admin/fridges', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('fridge-name').value,
        location: document.getElementById('fridge-location').value || null,
        team_id: document.getElementById('fridge-team').value ? Number(document.getElementById('fridge-team').value) : null,
      }),
    });
    document.getElementById('fridge-name').value = '';
    document.getElementById('fridge-location').value = '';
    await loadTeamsAndFridges();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

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
        team_id: document.getElementById('user-team').value ? Number(document.getElementById('user-team').value) : null,
      }),
    });
    await loadUsers();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('upload-image').addEventListener('click', async () => {
  const input = document.getElementById('drink-image-file');
  const file = input.files?.[0];
  if (!file) {
    errorEl.textContent = 'Please choose an image file first.';
    return;
  }

  const fd = new FormData();
  fd.append('file', file);

  try {
    const res = await api('/admin/drinks/upload-image', { method: 'POST', body: fd });
    const payload = await res.json();
    document.getElementById('drink-photo').value = payload.photo_url;
    errorEl.textContent = 'Image uploaded.';
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
        stock_quantity: document.getElementById('drink-stock').value ? Number(document.getElementById('drink-stock').value) : null,
        low_stock_threshold: Number(document.getElementById('drink-threshold').value || 5),
        team_id: document.getElementById('drink-team').value ? Number(document.getElementById('drink-team').value) : null,
        fridge_id: document.getElementById('drink-fridge').value ? Number(document.getElementById('drink-fridge').value) : null,
        is_active: true,
      }),
    });
    errorEl.textContent = 'Drink created.';
    await loadDrinks();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

teamList.addEventListener('click', async (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const item = teams.find((t) => t.id === id);
  if (!item) return;
  try {
    if (btn.dataset.act === 'team-edit') {
      const name = prompt('New team name', item.name);
      if (!name) return;
      await api(`/admin/teams/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
    }
    if (btn.dataset.act === 'team-del') {
      if (!confirm(`Delete team ${item.name}?`)) return;
      await api(`/admin/teams/${id}`, { method: 'DELETE' });
    }
    await loadTeamsAndFridges();
    await loadUsers();
    await loadDrinks();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

fridgeList.addEventListener('click', async (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const item = fridges.find((f) => f.id === id);
  if (!item) return;
  try {
    if (btn.dataset.act === 'fridge-edit') {
      const name = prompt('Fridge name', item.name);
      if (!name) return;
      const location = prompt('Location', item.location || '') ?? '';
      const teamIdRaw = prompt('Team id (empty for none)', item.team_id || '');
      const team_id = teamIdRaw ? Number(teamIdRaw) : null;
      await api(`/admin/fridges/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, location, team_id }),
      });
    }
    if (btn.dataset.act === 'fridge-del') {
      if (!confirm(`Delete fridge ${item.name}?`)) return;
      await api(`/admin/fridges/${id}`, { method: 'DELETE' });
    }
    await loadTeamsAndFridges();
    await loadDrinks();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

userList.addEventListener('click', async (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const item = users.find((u) => u.id === id);
  if (!item) return;
  try {
    if (btn.dataset.act === 'user-edit') {
      const name = prompt('Name', item.name);
      if (!name) return;
      const role = prompt('Role (USER or ADMIN)', item.role);
      if (!role) return;
      const teamIdRaw = prompt('Team id (empty for none)', item.team_id || '');
      const team_id = teamIdRaw ? Number(teamIdRaw) : null;
      const is_active = confirm('User active? Click OK=yes, Cancel=no');
      await api(`/admin/users/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, role, team_id, is_active }),
      });
    }
    if (btn.dataset.act === 'user-pass') {
      const password = prompt('New password (min 6 chars)');
      if (!password) return;
      await api(`/admin/users/${id}/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
    }
    if (btn.dataset.act === 'user-del') {
      if (!confirm(`Delete user ${item.email}?`)) return;
      await api(`/admin/users/${id}`, { method: 'DELETE' });
    }
    await loadUsers();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

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

drinkList.addEventListener('click', async (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const item = drinks.find((d) => d.id === id);
  if (!item) return;
  try {
    if (btn.dataset.act === 'drink-edit') {
      const name = prompt('Drink name', item.name);
      if (!name) return;
      const unit_price = Number(prompt('Price in EUR', item.unit_price));
      if (Number.isNaN(unit_price)) return;
      const stockRaw = prompt('Stock quantity (empty for unlimited)', item.stock_quantity ?? '');
      const stock_quantity = stockRaw === '' ? null : Number(stockRaw);
      const low_stock_threshold = Number(prompt('Low stock threshold', item.low_stock_threshold));
      const teamRaw = prompt('Team id (empty for none)', item.team_id || '');
      const fridgeRaw = prompt('Fridge id (empty for none)', item.fridge_id || '');
      await api(`/admin/drinks/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          photo_url: item.photo_url,
          unit_price,
          stock_quantity,
          low_stock_threshold,
          team_id: teamRaw ? Number(teamRaw) : null,
          fridge_id: fridgeRaw ? Number(fridgeRaw) : null,
          is_active: item.is_active,
        }),
      });
    }
    if (btn.dataset.act === 'drink-del') {
      if (!confirm(`Delete drink ${item.name}?`)) return;
      await api(`/admin/drinks/${id}`, { method: 'DELETE' });
    }
    await loadDrinks();
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
Promise.all([loadTeamsAndFridges(), loadUsers(), loadDrinks(), loadReport()]).catch(() => {
  window.location.href = '/';
});
