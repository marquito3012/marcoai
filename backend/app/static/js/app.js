/* ============================================================
   Settings Module (Pro Max Refinement)
   ============================================================ */
const Settings = (() => {
  let currentLang = localStorage.getItem('marco_language') || 'en';

  function init() {
    console.log("[Settings] Module initialized.");
    
    const btnNav = document.getElementById('btn-settings-nav');
    if (btnNav) {
      // Remove any existing listeners first to be safe
      btnNav.removeEventListener('click', open);
      btnNav.addEventListener('click', open);
    }

    const langBtns = document.querySelectorAll('.lang-btn');
    langBtns.forEach(btn => {
      // Set initial state
      if (btn.dataset.lang === currentLang) {
        btn.classList.add('active');
        btn.setAttribute('aria-checked', 'true');
      } else {
        btn.classList.remove('active');
        btn.setAttribute('aria-checked', 'false');
      }

      btn.addEventListener('click', (e) => {
        langBtns.forEach(b => {
          b.classList.remove('active');
          b.setAttribute('aria-checked', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-checked', 'true');
        currentLang = btn.dataset.lang;
        console.log("[Settings] Language selected:", currentLang);
      });
    });

    const closeBtn = document.getElementById('settings-close');
    const saveBtn = document.getElementById('settings-save');
    if (closeBtn) closeBtn.onclick = close;
    if (saveBtn) saveBtn.onclick = save;
  }

  function open() {
    console.log("[Settings] Opening modal...");
    const modal = document.getElementById('modal-settings');
    if (modal) {
      modal.style.display = 'flex';
      modal.style.zIndex = '9999999';
      document.body.style.overflow = 'hidden';
      // CSS handle transition via .is-open
      requestAnimationFrame(() => {
        modal.classList.add('is-open');
      });
    }
  }

  function close() {
    const modal = document.getElementById('modal-settings');
    if (modal) {
      modal.classList.remove('is-open');
      setTimeout(() => {
        modal.style.display = 'none';
        document.body.style.overflow = '';
      }, 300);
    }
  }

  function save() {
    localStorage.setItem('marco_language', currentLang);
    console.log("[Settings] Saved language:", currentLang);
    close();
    
    if (typeof Chat !== 'undefined' && Chat.addBubble) {
      if (currentLang === 'es') {
        Chat.addBubble('Configuración guardada. Ahora hablaré en español.', 'assistant');
      } else {
        Chat.addBubble('Settings saved. I will now speak in English.', 'assistant');
      }
    }
  }

  function getLanguage() {
    return currentLang;
  }

  window.Settings = { init, getLanguage, open, close };
  return window.Settings;
})();

/* ============================================================
   Auth Module
   ============================================================ */
const Auth = (() => {
  async function init() {
    try {
      const res = await fetch('/auth/me');
      if (!res.ok) return;
      const user = await res.json();
      renderUser(user);
    } catch (_) {}
  }

  function renderUser(user) {
    const navUser = document.getElementById('nav-user');
    const avatar = document.getElementById('nav-avatar');
    const name = document.getElementById('nav-name');

    if (!navUser || !user) return;
    if (user.picture) {
      avatar.src = user.picture;
      avatar.alt = user.name || 'User';
    } else {
      avatar.style.display = 'none';
    }

    if (user.name) name.textContent = user.name;
    else if (user.email) name.textContent = user.email;

    navUser.style.removeProperty('display');
    navUser.style.opacity = '0';
    navUser.style.transition = 'opacity 300ms ease';
    requestAnimationFrame(() => { navUser.style.opacity = '1'; });
  }

  return { init };
})();

/* ============================================================
   Config & Helpers
   ============================================================ */
const API_BASE = '/api';
const USER_ID = localStorage.getItem('marco_user_id') || generateUserId();

function generateUserId() {
  const id = 'user-' + crypto.randomUUID().slice(0, 8);
  localStorage.setItem('marco_user_id', id);
  return id;
}

async function api(method, path, body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'className') node.className = v;
    else if (k === 'textContent') node.textContent = v;
    else if (k === 'innerHTML') node.innerHTML = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, v);
  }
  for (const c of children) {
    if (typeof c === 'string') node.appendChild(document.createTextNode(c));
    else if (c) node.appendChild(c);
  }
  return node;
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(amount || 0);
}

function formatDate(date) {
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function formatDateISO(date) { return date.toISOString().slice(0, 10); }
function nowTime() { return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }); }

const ICONS = {
  check: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
};

function showSkeleton(container, count = 2) {
  container.innerHTML = Array(count).fill('<div class="skeleton-block"></div>').join('');
}

/* ============================================================
   Chat Module
   ============================================================ */
const Chat = (() => {
  let messagesEl, inputEl, sendEl, welcomeEl;
  let isLoading = false;

  function init() {
    messagesEl = $('#chat-messages');
    inputEl = $('#chat-input');
    sendEl = $('#chat-send');
    welcomeEl = $('#chat-welcome');

    if (sendEl) sendEl.onclick = send;
    if (inputEl) {
      inputEl.onkeydown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          send();
        }
      };
    }
  }

  function addBubble(text, role) {
    if (welcomeEl) welcomeEl.style.display = 'none';
    const bubble = el('div', { className: `chat-bubble ${role}` }, [
      document.createTextNode(text),
      el('span', { className: 'bubble-time', textContent: nowTime() }),
    ]);
    messagesEl.appendChild(bubble);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return bubble;
  }

  async function send() {
    const message = inputEl.value.trim();
    if (!message || isLoading) return;
    inputEl.value = '';
    addBubble(message, 'user');
    isLoading = true;
    inputEl.disabled = true;
    sendEl.disabled = true;

    try {
      const data = await api('POST', '/chat', {
        message, user_id: USER_ID, language: Settings.getLanguage(),
      });
      addBubble(data.response || 'No response.', 'assistant');
      Calendar.refresh(); Finance.refresh(); Habits.refresh();
    } catch (e) {
      addBubble(`Error: ${e.message}`, 'assistant');
    } finally {
      isLoading = false;
      inputEl.disabled = false;
      sendEl.disabled = false;
      inputEl.focus();
    }
  }

  return { init, addBubble };
})();

/* ============================================================
   Calendar Module
   ============================================================ */
const Calendar = (() => {
  let currentDate = new Date();
  let listEl, dateEl;

  function init() {
    listEl = $('#event-list');
    dateEl = $('#cal-date');
    $('#cal-prev').onclick = () => { currentDate.setDate(currentDate.getDate()-1); refresh(); };
    $('#cal-next').onclick = () => { currentDate.setDate(currentDate.getDate()+1); refresh(); };
    refresh();
  }

  async function refresh() {
    dateEl.textContent = formatDate(currentDate);
    showSkeleton(listEl, 1);
    try {
      const data = await api('GET', `/calendar/events?date=${formatDateISO(currentDate)}&user_id=${USER_ID}`);
      render(data.events || []);
    } catch (e) {
      listEl.innerHTML = '<p class="p-4 text-center text-txt-m text-xs italic">Calendar not connected.</p>';
    }
  }

  function render(events) {
    listEl.innerHTML = '';
    if (events.length === 0) {
      listEl.innerHTML = '<p class="p-4 text-center text-txt-m text-xs italic">No events.</p>';
      return;
    }
    events.forEach((ev) => {
      const time = ev.start ? new Date(ev.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
      listEl.appendChild(el('div', { className: 'event-item' }, [
        el('span', { className: 'event-time', textContent: time }),
        el('span', { className: 'event-title', textContent: ev.summary || 'Untitled' }),
      ]));
    });
  }
  return { init, refresh };
})();

/* ============================================================
   Finance Module
   ============================================================ */
const Finance = (() => {
  let monthEl, incomeEl, expenseEl, balanceEl;
  function init() {
    monthEl = $('#finance-month'); incomeEl = $('#finance-income');
    expenseEl = $('#finance-expense'); balanceEl = $('#finance-balance');
    refresh();
  }
  async function refresh() {
    const now = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
    monthEl.textContent = month;
    try {
      const data = await api('GET', `/finance/balance?month=${month}&user_id=${USER_ID}`);
      incomeEl.textContent = formatCurrency(data.income);
      expenseEl.textContent = formatCurrency(data.expense);
      balanceEl.textContent = formatCurrency(data.balance);
    } catch (e) {
      incomeEl.textContent = formatCurrency(0); expenseEl.textContent = formatCurrency(0); balanceEl.textContent = formatCurrency(0);
    }
  }
  return { init, refresh };
})();

/* ============================================================
   Habits Module
   ============================================================ */
const Habits = (() => {
  let listEl, streakEl, streakContainer;
  function init() {
    listEl = $('#habit-list'); streakEl = $('#streak-count'); streakContainer = $('#habit-streak');
    refresh();
  }
  async function refresh() {
    showSkeleton(listEl, 1);
    try {
      const data = await api('GET', `/habits?user_id=${USER_ID}`);
      render(data.habits || []);
    } catch (e) {
      listEl.innerHTML = '<p class="p-4 text-center text-txt-m text-xs italic">No habits.</p>';
    }
  }
  function render(habits) {
    listEl.innerHTML = '';
    habits.forEach((habit) => {
      const completed = !!habit.completed;
      listEl.appendChild(el('div', { 
        className: `habit-item ${completed ? 'completed' : ''}`,
        onclick: () => toggle(habit.name)
      }, [
        el('div', { className: 'habit-checkbox', innerHTML: ICONS.check }),
        el('span', { className: 'habit-name', textContent: habit.name }),
      ]));
    });
    streakContainer.style.display = habits.length > 0 ? 'flex' : 'none';
    streakEl.textContent = `${habits.filter(h=>h.completed).length}/${habits.length} done`;
  }
  async function toggle(name) {
    await api('POST', '/habits/track', { habit_name: name, date: formatDateISO(new Date()), user_id: USER_ID });
    refresh();
  }
  return { init, refresh };
})();

/* ============================================================
   Boot
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  if (typeof lucide !== 'undefined') lucide.createIcons();
  [Auth, Settings, Chat, Calendar, Finance, Habits].forEach(m => {
    try { m.init(); } catch (e) { console.error(`[App] Failed: ${m.name}`, e); }
  });
});
