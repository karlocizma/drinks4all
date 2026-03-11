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

let pendingDrink = null;

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function eur(value) {
  return `€${Number(value || 0).toFixed(2)}`;
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

async function loadDrinks() {
  const res = await fetch('/drinks');
  if (!res.ok) {
    window.location.href = '/';
    return;
  }

  const drinks = await res.json();
  grid.innerHTML = '';
  drinks.forEach((drink) => {
    const card = document.createElement('article');
    card.className = 'drink';
    card.innerHTML = `
      <img src="${drink.photo_url}" alt="${drink.name}" />
      <div class="content">
        <h3>${drink.name}</h3>
        <p>Price: ${eur(drink.unit_price)}</p>
        <p>Stock: ${drink.stock_quantity ?? 'unlimited'}</p>
        <button data-id="${drink.id}">+1 Drink</button>
      </div>
    `;
    card.querySelector('button').addEventListener('click', () => openDrinkConfirm(drink));
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

document.getElementById('undo-last').addEventListener('click', async () => {
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
});

document.getElementById('logout-btn').addEventListener('click', async () => {
  await fetch('/auth/logout', { method: 'POST' });
  window.location.href = '/';
});

document.getElementById('refresh-summary').addEventListener('click', loadSummary);
monthInput.value = currentMonth();

loadDrinks();
loadSummary();
