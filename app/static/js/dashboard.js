const monthInput = document.getElementById('month-picker');
const summaryEl = document.getElementById('summary');
const breakdownEl = document.getElementById('breakdown');
const grid = document.getElementById('drink-grid');
const errorEl = document.getElementById('error');
const paypalBtn = document.getElementById('paypal-pay-btn');
const drinkConfirmModal = document.getElementById('drink-confirm-modal');
const drinkConfirmText = document.getElementById('drink-confirm-text');
const confirmDrinkBtn = document.getElementById('confirm-drink-btn');
const cancelDrinkBtn = document.getElementById('cancel-drink-btn');
const passwordModal = document.getElementById('password-modal');
const cancelPasswordBtn = document.getElementById('cancel-password-btn');

let pendingDrink = null;

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function eur(value) {
  return `€${Number(value || 0).toFixed(2)}`;
}

function formatMonthLabel(monthStr) {
  if (!monthStr) return '';
  const [year, month] = monthStr.split('-');
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleString('default', { month: 'long', year: 'numeric' });
}

async function loadUser() {
  try {
    const res = await fetch('/me');
    if (!res.ok) return;
    const data = await res.json();
    const usernameEl = document.getElementById('topbar-username');
    if (usernameEl && data.name) {
      usernameEl.textContent = data.name;
    }
  } catch (_) {
    // silently ignore — topbar username is non-critical
  }
}

async function loadSummary() {
  const month = monthInput.value || currentMonth();
  const res = await fetch(`/me/summary?month=${month}`);
  if (!res.ok) {
    summaryEl.textContent = 'Please log in again.';
    return;
  }
  const data = await res.json();
  summaryEl.textContent = `Month ${data.month}: ${data.total_units} drinks | Total ${eur(data.total_amount)}`;
  const topbarMonth = document.getElementById('topbar-month');
  if (topbarMonth) {
    topbarMonth.textContent = formatMonthLabel(data.month);
  }
  if (data.paypal_url) {
    paypalBtn.href = data.paypal_url;
    paypalBtn.style.display = 'inline-block';
  } else {
    paypalBtn.style.display = 'none';
  }
  if (!data.drinks?.length) {
    breakdownEl.innerHTML = '<p>No drinks yet this month.</p>';
    return;
  }
  breakdownEl.innerHTML = data.drinks
    .map((d) => `<div>${d.drink_name}: ${d.total_units} units (${eur(d.total_amount)})</div>`)
    .join('');
}

async function addDrink(drinkId) {
  const res = await fetch('/consumptions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drink_id: drinkId, quantity: 1 }),
  });
  if (!res.ok) {
    const text = await res.text();
    errorEl.textContent = text || 'Failed to add drink.';
    return;
  }
  await loadDrinks();
  await loadSummary();
}

function openDrinkConfirm(drink) {
  pendingDrink = drink;
  drinkConfirmText.textContent = `Add 1x ${drink.name} for ${eur(drink.unit_price)}?`;
  drinkConfirmModal.classList.remove('hidden');
  drinkConfirmModal.removeAttribute('hidden');
}

function closeDrinkConfirm() {
  pendingDrink = null;
  drinkConfirmModal.classList.add('hidden');
  drinkConfirmModal.setAttribute('hidden', '');
}

function openPasswordModal() {
  errorEl.textContent = '';
  passwordModal.classList.remove('hidden');
  passwordModal.removeAttribute('hidden');
}

function closePasswordModal() {
  passwordModal.classList.add('hidden');
  passwordModal.setAttribute('hidden', '');
}

async function loadDrinks() {
  const res = await fetch('/drinks');
  if (!res.ok) {
    window.location.href = '/';
    return;
  }

  const drinks = await res.json();
  grid.innerHTML = '';
  drinks.forEach((d) => {
    const card = document.createElement('div');
    card.className = 'drink';
    card.dataset.id = d.id;
    card.dataset.name = d.name;
    card.dataset.price = d.unit_price;
    const stockWarn = (d.stock_quantity !== null && d.stock_quantity !== undefined && d.stock_quantity <= d.low_stock_threshold)
      ? `<div style="font-size:0.75rem;color:#f59e0b;margin-top:0.35rem;text-align:center;">⚠ ${d.stock_quantity} left</div>`
      : '';
    card.innerHTML = `<div style="height:140px;overflow:hidden;"><img src="${d.photo_url || ''}" alt="${d.name}" style="width:100%;height:100%;object-fit:cover;"></div><div class="drink-body" style="padding:0.65rem;"><div style="font-weight:600;font-size:0.9rem;margin-bottom:0.25rem;">${d.name}</div><div style="color:var(--accent);font-size:0.85rem;margin-bottom:0.5rem;">${eur(d.unit_price)}</div><button class="btn btn-primary add-drink-btn" data-id="${d.id}" style="width:100%;min-height:44px;">+1 Drink</button>${stockWarn}</div>`;
    card.querySelector('.add-drink-btn').addEventListener('click', () => openDrinkConfirm(d));
    grid.appendChild(card);
  });
}

confirmDrinkBtn.addEventListener('click', async () => {
  if (!pendingDrink) return;
  errorEl.textContent = '';
  const drinkId = pendingDrink.id;
  closeDrinkConfirm();
  await addDrink(drinkId);
});

cancelDrinkBtn.addEventListener('click', closeDrinkConfirm);

drinkConfirmModal?.addEventListener('click', (e) => {
  if (e.target === drinkConfirmModal) {
    closeDrinkConfirm();
  }
});

// Overflow menu toggle
const overflowBtn = document.getElementById('overflow-btn');
const overflowMenu = document.getElementById('overflow-menu');
if (overflowBtn) {
  overflowBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    overflowMenu.style.display = overflowMenu.style.display === 'none' ? 'block' : 'none';
  });
  document.addEventListener('click', () => {
    overflowMenu.style.display = 'none';
  });
}

const changePasswordBtn = document.getElementById('change-password-btn');
if (changePasswordBtn) {
  changePasswordBtn.addEventListener('click', () => {
    overflowMenu.style.display = 'none';
    openPasswordModal();
  });
}

cancelPasswordBtn.addEventListener('click', closePasswordModal);

passwordModal?.addEventListener('click', (e) => {
  if (e.target === passwordModal) {
    closePasswordModal();
  }
});

document.getElementById('undo-btn').addEventListener('click', async () => {
  const res = await fetch('/consumptions/last', { method: 'DELETE' });
  if (!res.ok) {
    errorEl.textContent = 'No last drink to undo.';
    return;
  }
  await loadDrinks();
  await loadSummary();
});

document.getElementById('password-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';
  const old_password = document.getElementById('old-password').value;
  const new_password = document.getElementById('new-password').value;
  const res = await fetch('/me/change-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ old_password, new_password }),
  });
  if (!res.ok) {
    errorEl.textContent = await res.text();
    return;
  }
  document.getElementById('old-password').value = '';
  document.getElementById('new-password').value = '';
  errorEl.textContent = 'Password changed.';
  closePasswordModal();
});

document.getElementById('logout-btn').addEventListener('click', async () => {
  await fetch('/auth/logout', { method: 'POST' });
  window.location.href = '/';
});

monthInput.addEventListener('change', loadSummary);
monthInput.value = currentMonth();

loadUser();
loadDrinks();
loadSummary();
