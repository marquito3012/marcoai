/* ============================================================
   Settings Module (Bulletproof version)
   ============================================================ */
const Settings = (() => {
  let currentLang = localStorage.getItem('marco_language') || 'en';

  function init() {
    console.log("[Settings] Module initialized.");
    
    // Attach listener using native JS to avoid scope issues
    const btnNav = document.getElementById('btn-settings-nav');
    if (btnNav) {
      btnNav.addEventListener('click', open);
    } else {
      console.warn("[Settings] Could not find #btn-settings-nav");
    }

    // Set initial active state on buttons
    const langBtns = document.querySelectorAll('.lang-btn');
    langBtns.forEach(btn => {
      if (btn.dataset.lang === currentLang) btn.classList.add('active');
      else btn.classList.remove('active');

      btn.addEventListener('click', (e) => {
        langBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentLang = btn.dataset.lang;
      });
    });

    const closeBtn = document.getElementById('settings-close');
    const saveBtn = document.getElementById('settings-save');
    if (closeBtn) closeBtn.addEventListener('click', close);
    if (saveBtn) saveBtn.addEventListener('click', save);
  }

  function open() {
    const modal = document.getElementById('modal-settings');
    if (modal) {
      modal.style.display = 'flex';
      modal.style.zIndex = '9999999';
      document.body.style.overflow = 'hidden';
      // Trigger a small delay to ensure CSS transitions play if any
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
    close();
    
    // If Chat is fully loaded, send a message
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
    } catch (_) {
      // Network error — do nothing, server-side redirect already handles unauth
    }
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

    if (user.name) {
      name.textContent = user.name;
    } else if (user.email) {
      name.textContent = user.email;
    }

    // Fade in
    navUser.style.removeProperty('display');
    navUser.style.opacity = '0';
    navUser.style.transition = 'opacity 300ms ease';
    requestAnimationFrame(() => { navUser.style.opacity = '1'; });
  }

  return { init };
})();

/* ============================================================
   Config
   ============================================================ */
const API_BASE = '/api';
const USER_ID = localStorage.getItem('marco_user_id') || generateUserId();

function generateUserId() {
  const id = 'user-' + crypto.randomUUID().slice(0, 8);
  localStorage.setItem('marco_user_id', id);
  return id;
}

/* ============================================================
   API Helpers
   ============================================================ */
async function api(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

/* ============================================================
   DOM Helpers
   ============================================================ */
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
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount || 0);
}

function formatDate(date) {
  return date.toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
  });
}

function formatDateISO(date) {
  return date.toISOString().slice(0, 10);
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
}

const ICONS = {
  check: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
  smile: '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" x2="9.01" y1="9" y2="9"/><line x1="15" x2="15.01" y1="9" y2="9"/></svg>',
  heart: '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>',
};

function showEmpty(container, icon, message) {
  container.innerHTML = `
    <div class="empty-state">${icon}<p>${message}</p></div>
  `;
}

function showError(container, message) {
  container.innerHTML = `
    <div class="error-state">${message}</div>
  `;
}

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

    if (sendEl) sendEl.addEventListener('click', send);
    if (inputEl) {
      inputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          send();
        }
      });
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

  function showLoading() {
    const loader = el('div', { className: 'chat-loading', id: 'chat-loader' }, [
      el('span'), el('span'), el('span'),
    ]);
    messagesEl.appendChild(loader);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function hideLoading() {
    const loader = $('#chat-loader');
    if (loader) loader.remove();
  }

  async function send() {
    const message = inputEl.value.trim();
    if (!message || isLoading) return;

    inputEl.value = '';
    addBubble(message, 'user');

    isLoading = true;
    inputEl.disabled = true;
    sendEl.disabled = true;
    showLoading();

    try {
      const data = await api('POST', '/chat', {
        message,
        user_id: USER_ID,
        language: Settings.getLanguage(),
      });
      hideLoading();
      addBubble(data.response || 'No response received.', 'assistant');

      // Refresh dashboard cards after any chat response
      // (the orchestrator might have used tools)
      Calendar.refresh();
      Finance.refresh();
      Habits.refresh();
    } catch (e) {
      hideLoading();
      addBubble(`Sorry, something went wrong: ${e.message}`, 'assistant');
    } finally {
      isLoading = false;
      inputEl.disabled = false;
      sendEl.disabled = false;
      inputEl.focus();
    }
  }

  return { init };
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

    $('#cal-prev').addEventListener('click', () => {
      currentDate.setDate(currentDate.getDate() - 1);
      refresh();
    });
    $('#cal-next').addEventListener('click', () => {
      currentDate.setDate(currentDate.getDate() + 1);
      refresh();
    });

    refresh();
  }

  async function refresh() {
    dateEl.textContent = formatDate(currentDate);
    showSkeleton(listEl, 2);

    try {
      const data = await api('GET',
        `/calendar/events?date=${formatDateISO(currentDate)}&user_id=${USER_ID}`
      );
      render(data.events || []);
    } catch (e) {
      showEmpty(listEl, ICONS.smile,
        'Calendar not connected yet. Ask Marco to set it up!');
    }
  }

  function render(events) {
    listEl.innerHTML = '';

    if (events.length === 0) {
      showEmpty(listEl, ICONS.smile, 'No events today — enjoy your free time!');
      return;
    }

    events.forEach((ev) => {
      const time = ev.start
        ? new Date(ev.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
        : '';
      const item = el('div', { className: 'event-item' }, [
        el('span', { className: 'event-time', textContent: time }),
        el('span', { className: 'event-title', textContent: ev.summary || ev.title || 'Untitled' }),
      ]);
      listEl.appendChild(item);
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
    monthEl = $('#finance-month');
    incomeEl = $('#finance-income');
    expenseEl = $('#finance-expense');
    balanceEl = $('#finance-balance');

    refresh();
  }

  function currentMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }

  async function refresh() {
    const month = currentMonth();
    monthEl.textContent = month;

    try {
      const data = await api('GET', `/finance/balance?month=${month}&user_id=${USER_ID}`);
      incomeEl.textContent = formatCurrency(data.income);
      expenseEl.textContent = formatCurrency(data.expense);
      balanceEl.textContent = formatCurrency(data.balance);
    } catch (e) {
      // Show zeroes on error (new user, no transactions yet)
      incomeEl.textContent = formatCurrency(0);
      expenseEl.textContent = formatCurrency(0);
      balanceEl.textContent = formatCurrency(0);
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
    listEl = $('#habit-list');
    streakEl = $('#streak-count');
    streakContainer = $('#habit-streak');

    refresh();
  }

  async function refresh() {
    showSkeleton(listEl, 2);

    try {
      const data = await api('GET', `/habits?user_id=${USER_ID}`);
      render(data.habits || []);
    } catch (e) {
      showEmpty(listEl, ICONS.heart, 'No habits yet. Ask Marco to add one!');
      streakContainer.style.display = 'none';
    }
  }

  function render(habits) {
    listEl.innerHTML = '';

    if (habits.length === 0) {
      showEmpty(listEl, ICONS.heart, 'No habits yet. Ask Marco to add one!');
      streakContainer.style.display = 'none';
      return;
    }

    habits.forEach((habit) => {
      const completed = !!habit.completed;
      const item = el('div', {
        className: `habit-item ${completed ? 'completed' : ''}`,
        onClick: () => toggleHabit(habit.name || habit.id),
      }, [
        el('div', { className: 'habit-checkbox', innerHTML: ICONS.check }),
        el('span', { className: 'habit-name', textContent: habit.name }),
      ]);
      listEl.appendChild(item);
    });

    // Show streak if any habits are completed
    const completedCount = habits.filter(h => h.completed).length;
    if (completedCount > 0) {
      streakContainer.style.display = 'flex';
      streakEl.textContent = `${completedCount}/${habits.length} done today`;
    } else {
      streakContainer.style.display = 'flex';
      streakEl.textContent = `0/${habits.length} done today`;
    }
  }

  async function toggleHabit(name) {
    try {
      await api('POST', '/habits/track', {
        habit_name: name,
        date: formatDateISO(new Date()),
        user_id: USER_ID,
      });
      refresh();
    } catch (e) {
      console.error('Failed to toggle habit:', e);
    }
  }

  return { init, refresh };
})();


/* ============================================================
   Boot
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }

  // Initialize all modules with safety wrappers
  const modules = [
    { name: 'Auth',     init: Auth.init },
    { name: 'Settings', init: Settings.init },
    { name: 'Chat',     init: Chat.init },
    { name: 'Calendar', init: Calendar.init },
    { name: 'Finance',  init: Finance.init },
    { name: 'Habits',   init: Habits.init },
  ];

  modules.forEach(m => {
    try {
      m.init();
    } catch (e) {
      console.error(`[App] Failed to init module: ${m.name}`, e);
    }
  });
});
