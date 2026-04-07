/* ============================================================
   Settings Module (Pro Max Refinement v11)
   ============================================================ */
const Settings = (() => {
  let currentLang = localStorage.getItem('marco_language') || 'en';

  function init() {
    console.log("[Settings] Module v11 initialized.");
    
    const btnNav = document.getElementById('btn-settings-nav');
    if (btnNav) {
      // Clean start: remove any potential pre-existing handlers
      btnNav.onclick = null; 
      btnNav.addEventListener('click', open);
    }

    const langBtns = document.querySelectorAll('.lang-btn');
    langBtns.forEach(btn => {
      // Set initial UI state from persistence
      if (btn.dataset.lang === currentLang) {
        btn.classList.add('active');
        btn.setAttribute('aria-checked', 'true');
      } else {
        btn.classList.remove('active');
        btn.setAttribute('aria-checked', 'false');
      }

      // Selection logic with visual feedback
      btn.addEventListener('click', () => {
        langBtns.forEach(b => {
          b.classList.remove('active');
          b.setAttribute('aria-checked', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-checked', 'true');
        currentLang = btn.dataset.lang;
      });
    });

    const closeBtn = document.getElementById('settings-close');
    const saveBtn = document.getElementById('settings-save');
    if (closeBtn) closeBtn.onclick = close;
    if (saveBtn) saveBtn.onclick = save;
  }

  function open() {
    const modal = document.getElementById('modal-settings');
    if (modal) {
      modal.style.display = 'flex';
      modal.style.zIndex = '9999999';
      document.body.style.overflow = 'hidden';
      // CSS handles the smooth slide/fade via .is-open
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
    
    // Notify the user in the new language if Chat is ready
    if (typeof Chat !== 'undefined' && Chat.addBubble) {
      if (currentLang === 'es') {
        Chat.addBubble('Configuración guardada. Marco hablará en español.', 'assistant');
      } else {
        Chat.addBubble('Settings saved. Marco will now speak in English.', 'assistant');
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
   Dashboard Ecosystem (v11)
   ============================================================ */
const API_BASE = '/api';
const USER_ID = localStorage.getItem('marco_user_id') || ('user-' + crypto.randomUUID().slice(0,8));
localStorage.setItem('marco_user_id', USER_ID);

async function api(method, path, body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}, children = []) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'className') n.className = v;
    else if (k === 'textContent') n.textContent = v;
    else if (k === 'innerHTML') n.innerHTML = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2).toLowerCase(), v);
    else n.setAttribute(k, v);
  }
  children.forEach(c => {
    if (typeof c === 'string') n.appendChild(document.createTextNode(c));
    else if (c) n.appendChild(c);
  });
  return n;
};

const formatCurrency = (a) => new Intl.NumberFormat('es-ES', { style:'currency', currency:'EUR'}).format(a || 0);

/* --- Chat --- */
const Chat = (() => {
  let messagesEl, inputEl, sendEl, welcomeEl;
  let isLoading = false;

  function init() {
    messagesEl = $('#chat-messages'); inputEl = $('#chat-input');
    sendEl = $('#chat-send'); welcomeEl = $('#chat-welcome');

    if (sendEl) sendEl.onclick = send;
    if (inputEl) {
      inputEl.onkeydown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } };
    }
  }

  function addBubble(text, role) {
    if (welcomeEl) welcomeEl.style.display = 'none';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    const bubble = el('div', { className: `chat-bubble ${role}` }, [
      document.createTextNode(text),
      el('span', { className: 'bubble-time', textContent: time }),
    ]);
    messagesEl.appendChild(bubble);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return bubble;
  }

  async function send() {
    const message = inputEl.value.trim();
    if (!message || isLoading) return;
    inputEl.value = ''; addBubble(message, 'user');
    isLoading = true; inputEl.disabled = true; sendEl.disabled = true;

    try {
      const data = await api('POST', '/chat', { message, user_id: USER_ID, language: Settings.getLanguage() });
      addBubble(data.response || 'No response.', 'assistant');
      Calendar.refresh(); Finance.refresh(); Habits.refresh();
    } catch (e) {
      addBubble(`Error: ${e.message}`, 'assistant');
    } finally {
      isLoading = false; inputEl.disabled = false; sendEl.disabled = false; inputEl.focus();
    }
  }
  return { init, addBubble };
})();

/* --- Calendar --- */
const Calendar = (() => {
  let cur = new Date();
  let list, date;

  function init() {
    list = $('#event-list'); date = $('#cal-date');
    $('#cal-prev').onclick = () => { cur.setDate(cur.getDate()-1); refresh(); };
    $('#cal-next').onclick = () => { cur.setDate(cur.getDate()+1); refresh(); };
    refresh();
  }

  async function refresh() {
    date.textContent = cur.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    list.innerHTML = '<div class="skeleton-block"></div>';
    try {
      const d = await api('GET', `/calendar/events?date=${cur.toISOString().slice(0,10)}&user_id=${USER_ID}`);
      render(d.events || []);
    } catch (_) { list.innerHTML = '<p class="p-4 text-center text-txt-m text-xs italic">Not connected.</p>'; }
  }

  function render(evs) {
    list.innerHTML = '';
    if (evs.length === 0) { list.innerHTML = '<p class="p-4 text-center text-txt-m text-xs italic">Free day!</p>'; return; }
    evs.forEach(e => {
      const t = e.start ? new Date(e.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
      list.appendChild(el('div', { className: 'event-item' }, [
        el('span', { className: 'event-time', textContent: t }),
        el('span', { className: 'event-title', textContent: e.summary || 'Untitled' }),
      ]));
    });
  }
  return { init, refresh };
})();

/* --- Finance --- */
const Finance = (() => {
  let mEl, iEl, eEl, bEl;
  function init() { mEl=$('#finance-month'); iEl=$('#finance-income'); eEl=$('#finance-expense'); bEl=$('#finance-balance'); refresh(); }
  async function refresh() {
    const now = new Date(); const m = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`; mEl.textContent = m;
    try {
      const d = await api('GET', `/finance/balance?month=${m}&user_id=${USER_ID}`);
      iEl.textContent = formatCurrency(d.income); eEl.textContent = formatCurrency(d.expense); bEl.textContent = formatCurrency(d.balance);
    } catch (_) { iEl.textContent=eEl.textContent=bEl.textContent=formatCurrency(0); }
  }
  return { init, refresh };
})();

/* --- Habits --- */
const Habits = (() => {
  let list, streak, sCont;
  function init() { list=$('#habit-list'); streak=$('#streak-count'); sCont=$('#habit-streak'); refresh(); }
  async function refresh() {
    list.innerHTML = '<div class="skeleton-block"></div>';
    try {
      const d = await api('GET', `/habits?user_id=${USER_ID}`); render(d.habits || []);
    } catch (_) { list.innerHTML = ''; }
  }
  function render(hbs) {
    list.innerHTML = ''; hbs.forEach(h => {
      const c = !!h.completed;
      list.appendChild(el('div', { className: `habit-item ${c?'completed':''}`, onclick: () => tg(h.name) }, [
        el('div', { className: 'habit-checkbox', innerHTML: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' }),
        el('span', { className: 'habit-name', textContent: h.name }),
      ]));
    });
    sCont.style.display = hbs.length > 0 ? 'flex' : 'none';
    streak.textContent = `${hbs.filter(x=>x.completed).length}/${hbs.length} done`;
  }
  async function tg(n) {
    await api('POST', '/habits/track', { habit_name: n, date: new Date().toISOString().slice(0,10), user_id: USER_ID });
    refresh();
  }
  return { init, refresh };
})();

/* --- Boot --- */
document.addEventListener('DOMContentLoaded', () => {
  if (typeof lucide !== 'undefined') lucide.createIcons();
  [Auth, Settings, Chat, Calendar, Finance, Habits].forEach(m => {
    try { m.init(); } catch (e) { console.error(`[App] Failed: ${m.name}`, e); }
  });
});
