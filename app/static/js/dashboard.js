const monthInput = document.getElementById('month-picker');
const summaryEl = document.getElementById('summary');
const grid = document.getElementById('drink-grid');
const errorEl = document.getElementById('error');

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

async function loadSummary() {
  const month = monthInput.value || currentMonth();
  const res = await fetch(`/me/summary?month=${month}`);
  if (!res.ok) {
    summaryEl.textContent = 'Please log in again.';
    return;
  }
  const data = await res.json();
  summaryEl.textContent = `Month ${data.month}: ${data.total_units} drinks | Total ${data.total_amount.toFixed(2)}`;
}

async function addDrink(drinkId) {
  const res = await fetch('/consumptions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drink_id: drinkId, quantity: 1 }),
  });
  if (!res.ok) {
    errorEl.textContent = 'Failed to add drink.';
    return;
  }
  await loadSummary();
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
        <p>Price: ${Number(drink.unit_price).toFixed(2)}</p>
        <button data-id="${drink.id}">+1 Drink</button>
      </div>
    `;
    card.querySelector('button').addEventListener('click', () => addDrink(drink.id));
    grid.appendChild(card);
  });
}

document.getElementById('logout-btn').addEventListener('click', async () => {
  await fetch('/auth/logout', { method: 'POST' });
  window.location.href = '/';
});

document.getElementById('refresh-summary').addEventListener('click', loadSummary);
monthInput.value = currentMonth();

loadDrinks();
loadSummary();
