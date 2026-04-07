/* ============================================================
   Translations Module (i18n v12)
   ============================================================ */
const Translations = {
  en: {
    calendar: "CALENDAR", finance: "FINANCE", habits: "HABITS", chat: "CHAT",
    income: "Income", expense: "Expenses", balance: "Balance",
    today: "Today", prev: "Prev", next: "Next", status: "Online",
    settings: "Settings", agent_lang: "Agent Language", save: "Save Changes",
    lang_desc: "Marco will adapt his thinking and responses to your preferred language.",
    welcome: "Hey! I'm <strong>Marco</strong>. Ask me anything — manage your calendar, check your budget, or track a habit.",
    settings_saved: "Settings saved. Marco will now speak in English.",
    chat_placeholder: "Type a message...",
    no_events: "Free day! Enjoy your time.",
    no_habits: "No habits set yet. Ask Marco to add one!",
    loading: "Thinking..."
  },
  es: {
    calendar: "CALENDARIO", finance: "FINANZAS", habits: "HÁBITOS", chat: "CHAT",
    income: "Ingresos", expense: "Gastos", balance: "Balance",
    today: "Hoy", prev: "Ant", next: "Sig", status: "En línea",
    settings: "Ajustes", agent_lang: "Idioma del Agente", save: "Guardar Cambios",
    lang_desc: "Marco adaptará su razonamiento y respuestas a tu idioma preferido.",
    welcome: "¡Hola! Soy <strong>Marco</strong>. Pregúntame lo que quieras — gestiona tu calendario, revisa tu presupuesto o sigue un hábito.",
    settings_saved: "Configuración guardada. Marco hablará en español.",
    chat_placeholder: "Escribe un mensaje...",
    no_events: "¡Día libre! Disfruta de tu tiempo.",
    no_habits: "Aún no hay hábitos. ¡Pídele a Marco que añada uno!",
    loading: "Pensando..."
  }
};

/* ============================================================
   Settings Module (Pro Max i18n v12)
   ============================================================ */
const Settings = (() => {
  let currentLang = localStorage.getItem('marco_language') || 'en';

  function init() {
    console.log("[Settings] Module v12 (i18n) initialized.");
    updateUI(); // Initial translation apply

    const btnNav = document.getElementById('btn-settings-nav');
    if (btnNav) {
      btnNav.onclick = null; 
      btnNav.addEventListener('click', open);
    }

    const langBtns = document.querySelectorAll('.lang-btn');
    langBtns.forEach(btn => {
      const active = btn.dataset.lang === currentLang;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-checked', active ? 'true' : 'false');

      btn.addEventListener('click', () => {
        langBtns.forEach(b => { b.classList.remove('active'); b.setAttribute('aria-checked', 'false'); });
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

  function updateUI() {
    const t = Translations[currentLang] || Translations.en;
    
    // Header labels
    const map = {
      'header-calendar': 'calendar', 'header-finance': 'finance', 'header-habits': 'habits', 'header-chat': 'chat',
      'label-income': 'income', 'label-expense': 'expense', 'label-balance': 'balance',
      'label-today': 'today', 'nav-prev': 'prev', 'nav-next': 'next',
      'label-settings': 'settings', 'label-agent-lang': 'agent_lang', 'label-save': 'save',
      'label-lang-desc': 'lang_desc', 'welcome-text': 'welcome', 'chat-input': 'chat_placeholder'
    };

    for (const [id, key] of Object.entries(map)) {
      const el = document.getElementById(id);
      if (el) {
        if (key === 'welcome') el.innerHTML = t[key];
        else if (key === 'chat_placeholder') el.placeholder = t[key];
        else el.textContent = t[key];
      }
    }

    // Status label (special case)
    const statusEl = document.getElementById('chat-status');
    if (statusEl) {
      const dot = '<span class="w-1.5 h-1.5 rounded-full bg-emerald"></span> ';
      statusEl.innerHTML = dot + t.status;
    }

    // Refresh components to apply localized dates/messages
    if (window.Calendar && Calendar.refresh) Calendar.refresh();
    if (window.Finance && Finance.refresh) Finance.refresh();
    if (window.Habits && Habits.refresh) Habits.refresh();
  }

  function open() {
    const modal = document.getElementById('modal-settings');
    if (modal) {
      modal.style.display = 'flex';
      requestAnimationFrame(() => modal.classList.add('is-open'));
      document.body.style.overflow = 'hidden';
    }
  }

  function close() {
    const modal = document.getElementById('modal-settings');
    if (modal) {
      modal.classList.remove('is-open');
      setTimeout(() => { modal.style.display = 'none'; document.body.style.overflow = ''; }, 300);
    }
  }

  function save() {
    localStorage.setItem('marco_language', currentLang);
    updateUI();
    close();
    
    if (typeof Chat !== 'undefined' && Chat.addBubble) {
      const t = Translations[currentLang] || Translations.en;
      Chat.addBubble(t.settings_saved, 'assistant');
    }
  }

  function getLanguage() { return currentLang; }

  window.Settings = { init, getLanguage, open, close, updateUI };
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
    if (user.picture) { avatar.src = user.picture; avatar.alt = user.name || 'User'; }
    if (user.name) name.textContent = user.name;
    
    // Sync identity (v21 sync + persistence)
    if (user.sub) {
      USER_ID = user.sub;
      localStorage.setItem('marco_user_id', USER_ID);
      console.log("[Auth] Identity synced & persisted:", USER_ID);
      
      // Force refresh of all components with correct ID
      if (window.Finance) Finance.refresh();
      if (window.Calendar) Calendar.refresh();
      if (window.Habits) Habits.refresh();
    }

    navUser.style.removeProperty('display');
    navUser.style.opacity = '0';
    navUser.style.transition = 'opacity 300ms ease';
    requestAnimationFrame(() => navUser.style.opacity = '1');
  }
  return { init };
})();

/* ============================================================
   Dashboard Modules (v12 i18n)
   ============================================================ */
const API_BASE = '/api';
let USER_ID = localStorage.getItem('marco_user_id') || ('user-' + crypto.randomUUID().slice(0,8));
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

const formatCurrency = (a) => {
  const lang = Settings.getLanguage() === 'es' ? 'es-ES' : 'en-US';
  return new Intl.NumberFormat(lang, { style:'currency', currency:'EUR'}).format(a || 0);
};

/* --- Chat --- */
const Chat = (() => {
  let messagesEl, inputEl, sendEl, welcomeEl;
  let isLoading = false;
  function init() {
    messagesEl = $('#chat-messages'); inputEl = $('#chat-input'); sendEl = $('#chat-send'); welcomeEl = $('#chat-welcome');
    if (sendEl) sendEl.onclick = send;
    if (inputEl) inputEl.onkeydown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } };
  }
  function addBubble(text, role) {
    if (welcomeEl) welcomeEl.style.display = 'none';
    const time = new Date().toLocaleTimeString([], { hour:'2-digit', minute:'2-digit', hour12:false });
    const bubble = el('div', { className:`chat-bubble ${role}` }, [
      document.createTextNode(text), el('span', { className:'bubble-time', textContent:time })
    ]);
    messagesEl.appendChild(bubble); messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  async function send() {
    const msg = inputEl.value.trim(); if (!msg || isLoading) return;
    inputEl.value = ''; addBubble(msg, 'user');
    isLoading = true; inputEl.disabled = true; sendEl.disabled = true;
    try {
      const d = await api('POST', '/chat', { message:msg, user_id:USER_ID, language:Settings.getLanguage() });
      addBubble(d.response || 'No response.', 'assistant');
      Calendar.refresh(); Finance.refresh(); Habits.refresh();
    } catch (e) { addBubble(`Error: ${e.message}`, 'assistant'); }
    finally { isLoading = false; inputEl.disabled = false; sendEl.disabled = false; inputEl.focus(); }
  }
  return { init, addBubble };
})();

/* --- Calendar --- */
const Calendar = (() => {
  let cur = new Date();
  let listEl, dateEl;
  function init() {
    listEl = $('#event-list'); dateEl = $('#cal-date');
    if ($('#cal-prev')) $('#cal-prev').onclick = () => { cur.setDate(cur.getDate()-1); refresh(); };
    if ($('#cal-next')) $('#cal-next').onclick = () => { cur.setDate(cur.getDate()+1); refresh(); };
    refresh();
  }
  async function refresh() {
    const lang = Settings.getLanguage() === 'es' ? 'es-ES' : 'en-US';
    dateEl.textContent = cur.toLocaleDateString(lang, { weekday:'short', month:'short', day:'numeric' });
    try {
      const d = await api('GET', `/calendar/events?date=${cur.toISOString().slice(0,10)}&user_id=${USER_ID}`);
      render(d.events || []);
    } catch (_) { render([]); }
  }
  function render(evs) {
    listEl.innerHTML = ''; const t = Translations[Settings.getLanguage()] || Translations.en;
    if (evs.length === 0) { listEl.innerHTML = `<p class="p-4 text-center text-txt-m text-[11px] italic">${t.no_events}</p>`; return; }
    evs.forEach(e => {
      const tm = e.start ? new Date(e.start).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' }) : '';
      listEl.appendChild(el('div', { className:'event-item' }, [
        el('span', { className:'event-time', textContent:tm }),
        el('span', { className:'event-title', textContent:e.summary || 'Untitled' })
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
  let listEl, sEl, sCont;
  function init() { listEl=$('#habit-list'); sEl=$('#streak-count'); sCont=$('#habit-streak'); refresh(); }
  async function refresh() {
    try { const d = await api('GET', `/habits?user_id=${USER_ID}`); render(d.habits || []); } catch (_) { render([]); }
  }
  function render(hbs) {
    listEl.innerHTML = ''; const t = Translations[Settings.getLanguage()] || Translations.en;
    if (hbs.length === 0) { listEl.innerHTML = `<p class="p-4 text-center text-txt-m text-[11px] italic">${t.no_habits}</p>`; return; }
    hbs.forEach(h => {
      listEl.appendChild(el('div', { className:`habit-item ${h.completed?'completed':''}`, onclick:()=>tg(h.name) }, [
        el('div', { className:'habit-checkbox', innerHTML:'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' }),
        el('span', { className:'habit-name', textContent:h.name })
      ]));
    });
    sCont.style.display = hbs.length > 0 ? 'flex' : 'none';
    const done = hbs.filter(x=>x.completed).length;
    sEl.textContent = `${done}/${hbs.length} ${Settings.getLanguage()==='es'?'completados':'done'}`;
  }
  async function tg(n) {
    await api('POST', '/habits/track', { habit_name:n, date:new Date().toISOString().slice(0,10), user_id:USER_ID });
    refresh();
  }
  return { init, refresh };
})();

/* --- Boot --- */
document.addEventListener('DOMContentLoaded', () => {
  if (typeof lucide !== 'undefined') lucide.createIcons();
  [Auth, Settings, Chat, Calendar, Finance, Habits].forEach(m => { try { m.init(); } catch (e) { console.error(e); } });
});
