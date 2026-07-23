const SCALE_IDS = ['jace', 'shelly', 'shira', 'meredith', 'kaleb', 'kyle', 'engineering', 'micromasters'];
const TEAM_IDS = ['jace', 'shelly', 'shira', 'meredith', 'kaleb', 'kyle'];
const DEBOUNCE_MS = 400;
const POLL_MS = 3000;

let debounceTimers = {};
let remoteValues = {};

// --- Possum rendering ---

function possumCount(v) {
  if (v >= 100) return 5;
  if (v >= 85) return 4;
  if (v >= 70) return 3;
  if (v >= 50) return 2;
  return 1;
}

function possumSize(v) {
  // px: 40 at 0, 90 at 100
  return Math.round(40 + (v / 100) * 50);
}

function possumClass(v) {
  if (v >= 85) return 'possum-chaos';
  if (v >= 60) return 'possum-shake';
  if (v >= 35) return 'possum-wobble';
  if (v >= 15) return 'possum-twitch';
  return '';
}

function possumFilter(v) {
  if (v >= 85) return `saturate(2) hue-rotate(${Math.round((v-85)*3)}deg) brightness(1.1)`;
  if (v >= 60) return `saturate(${1 + (v-60)*0.02})`;
  return 'none';
}

function renderPossums(containerId, value) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const count = possumCount(value);
  const size = possumSize(value);
  const cls = possumClass(value);
  const filter = possumFilter(value);

  container.innerHTML = '';
  for (let i = 0; i < count; i++) {
    const img = document.createElement('img');
    img.src = '/static/possum.png';
    img.alt = 'AHHH';
    img.className = 'possum-img' + (cls ? ' ' + cls : '');
    img.style.width = size + 'px';
    img.style.height = size + 'px';
    img.style.filter = filter;
    if (i > 0) img.style.marginLeft = '-12px';
    // stagger chaos timing so they don't all move in sync
    if (cls) img.style.animationDelay = (i * 0.07) + 's';
    container.appendChild(img);
  }
}

function renderHeaderPossums(avgValue) {
  renderPossums('header-possums', avgValue);
}

// --- Card state ---

function cardClass(v) {
  if (v >= 75) return 'ahhh-panic';
  if (v >= 50) return 'ahhh-high';
  if (v >= 25) return 'ahhh-medium';
  return 'ahhh-low';
}

function updateCard(id, value) {
  const slider = document.getElementById('slider-' + id);
  const valueEl = document.getElementById('value-' + id);
  const card = document.getElementById('card-' + id);
  if (!valueEl || !card) return;

  if (slider) {
    slider.value = value;
    slider.style.setProperty('--pct', value + '%');
  }
  valueEl.textContent = value + '%';
  valueEl.style.color = value >= 75 ? '#e63946' : value >= 50 ? '#f4a261' : value >= 25 ? '#c8a000' : '#1a1a1a';

  card.className = 'scale-card ' + (id === 'platform' ? 'platform-card ' : '') + cardClass(value);
  renderPossums('possums-' + id, value);
}

function updateOverall(values) {
  const vals = TEAM_IDS.filter(id => values[id] !== undefined).map(id => values[id].value);
  const avg = vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : 0;

  document.getElementById('overall-bar').style.width = avg + '%';
  document.getElementById('overall-value').textContent = avg + '%';
  renderHeaderPossums(avg);

  document.body.classList.toggle('full-chaos', avg >= 95);

  const title = document.getElementById('main-title');
  const extras = Math.floor(avg / 20);
  title.textContent = 'AHHH' + 'H'.repeat(extras);
}

function formatUpdated(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  return d.toLocaleDateString();
}

// --- API ---

async function fetchValues() {
  try {
    const res = await fetch('/api/values');
    const data = await res.json();
    remoteValues = data;

    SCALE_IDS.forEach(id => {
      if (data[id] !== undefined) {
        const activeSlider = document.getElementById('slider-' + id);
        if (activeSlider !== document.activeElement && !debounceTimers[id]) {
          updateCard(id, data[id].value);
        }
        const updatedEl = document.getElementById('updated-' + id);
        if (updatedEl) updatedEl.textContent = formatUpdated(data[id].updated_at);
      }
    });

    if (data['__platform__']) updatePlatformHeader(
      data['__platform__'].value,
      data['__platform__'].description,
      data['__platform__'].updated_at
    );
    updateOverall(data);
  } catch (e) {
    console.error('Failed to fetch values', e);
  }
}

async function postValue(id, value) {
  try {
    await fetch('/api/values', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, value }),
    });
  } catch (e) {
    console.error('Failed to post value', e);
  }
}

// --- Slider events ---

document.querySelectorAll('.ahhh-slider').forEach(slider => {
  const id = slider.dataset.id;

  slider.addEventListener('input', () => {
    const value = parseInt(slider.value, 10);
    updateCard(id, value);
    // optimistically update overall
    const merged = { ...remoteValues, [id]: { value, updated_at: new Date().toISOString() } };
    updateOverall(merged);

    clearTimeout(debounceTimers[id]);
    debounceTimers[id] = setTimeout(async () => {
      await postValue(id, value);
      delete debounceTimers[id];
    }, DEBOUNCE_MS);
  });
});

// --- Platform header ---

function updatePlatformHeader(value, description, fetchedAt) {
  renderPossums('platform-possums', value);
  const valEl = document.getElementById('platform-header-value');
  if (valEl) valEl.textContent = value + '%';
  const descEl = document.getElementById('platform-header-desc');
  if (descEl) descEl.textContent = description || '';
  const updEl = document.getElementById('platform-header-updated');
  if (updEl) updEl.textContent = fetchedAt ? 'checked ' + formatUpdated(fetchedAt) : '';
}

// --- Init & poll ---

fetchValues();
setInterval(fetchValues, POLL_MS);
