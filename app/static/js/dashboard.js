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
const viewGridBtn = document.getElementById('view-grid-btn');
const viewListBtn = document.getElementById('view-list-btn');

let pendingDrink = null;
let viewMode = localStorage.getItem('drinks-view') || 'grid';

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

function applyViewMode() {
  if (viewMode === 'list') {
    grid.classList.add('list-mode');
    viewGridBtn.classList.remove('active');
    viewListBtn.classList.add('active');
  } else {
    grid.classList.remove('list-mode');
    viewGridBtn.classList.add('active');
    viewListBtn.classList.remove('active');
  }
}

viewGridBtn.addEventListener('click', () => {
  viewMode = 'grid';
  localStorage.setItem('drinks-view', viewMode);
  applyViewMode();
});

viewListBtn.addEventListener('click', () => {
  viewMode = 'list';
  localStorage.setItem('drinks-view', viewMode);
  applyViewMode();
});

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
    const stockClass = d.stock_quantity == null ? 'inf' : (d.stock_quantity <= d.low_stock_threshold ? 'low' : 'ok');
    const stockLabel = d.stock_quantity == null ? '&#8734;' : `${d.stock_quantity} left`;
    const stockBadge = `<div class="drink-stock stock-pill ${stockClass}">${stockLabel}</div>`;
    card.innerHTML = `
      <div class="drink-photo"><img src="${d.photo_url || ''}" alt="${d.name}"></div>
      <div class="drink-body">
        <div class="drink-title">${d.name}</div>
        <div class="drink-price">${eur(d.unit_price)}</div>
        <button class="btn btn-primary add-drink-btn" data-id="${d.id}">+1 Drink</button>
        ${stockBadge}
      </div>`;
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
  document.addEventListener('click', (e) => {
    if (!overflowMenu.contains(e.target) && e.target !== overflowBtn) {
      overflowMenu.style.display = 'none';
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overflowMenu.style.display !== 'none') {
      overflowMenu.style.display = 'none';
      overflowBtn.focus();
    }
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

applyViewMode();
loadUser();
loadDrinks();
loadSummary();
