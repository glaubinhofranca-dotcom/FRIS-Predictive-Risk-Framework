let currentUser = null;
window.currentUser = null;

function hideSplash() {
  const splash = document.getElementById('splash');
  if (!splash) return;
  splash.style.animation = 'fadeOut 0.5s ease forwards';
  setTimeout(() => splash.remove(), 500);
}

function spawnAuthParticles() {
  const container = document.getElementById('authParticles');
  if (!container) return;
  const emojis = ['⚽','🏆','🥇','🎯','⭐','🔴','🟡'];
  for (let i = 0; i < 12; i++) {
    const el = document.createElement('div');
    el.className = 'auth-particle';
    el.textContent = emojis[Math.floor(Math.random() * emojis.length)];
    el.style.cssText = `left:${Math.random()*100}%;bottom:-50px;animation-duration:${8+Math.random()*12}s;animation-delay:${Math.random()*8}s;font-size:${1+Math.random()*1.5}rem;`;
    container.appendChild(el);
  }
}

function switchView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === `view-${name}`));
  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.view === name));
  if (name === 'album') Album.init();
  if (name === 'dashboard') loadDashboard();
  if (name === 'group') loadGroupView();
}

async function loadDashboard() {
  const statsEl = document.getElementById('dashStats');
  const membersEl = document.getElementById('membersGrid');
  statsEl.innerHTML = '<div class="stat-card"><div class="skeleton" style="height:60px"></div></div>'.repeat(4);
  try {
    const users = await Api.listUsers();
    const totalDups = users.reduce((a, u) => a + u.duplicate_count, 0);
    const totalWanted = users.reduce((a, u) => a + u.wanted_count, 0);
    statsEl.innerHTML = `
      <div class="stat-card"><span class="stat-icon">👥</span><span class="stat-value">${users.length}/11</span><span class="stat-label">Membros no grupo</span></div>
      <div class="stat-card"><span class="stat-icon">🔴</span><span class="stat-value">${totalDups}</span><span class="stat-label">Figurinhas repetidas</span></div>
      <div class="stat-card"><span class="stat-icon">🔵</span><span class="stat-value">${totalWanted}</span><span class="stat-label">Figurinhas desejadas</span></div>
      <div class="stat-card"><span class="stat-icon">⚽</span><span class="stat-value">670</span><span class="stat-label">Figurinhas no álbum</span></div>`;
    membersEl.innerHTML = '';
    users.forEach((u, i) => {
      const isMe = u.id === currentUser?.id;
      const card = document.createElement('div');
      card.className = `member-card ${isMe ? 'is-me' : ''}`;
      card.style.animationDelay = `${i * 0.05}s`;
      card.innerHTML = `
        <div class="member-avatar" style="background:${u.avatar_color}">${u.username.slice(0,2).toUpperCase()}</div>
        <div class="member-name">${u.username}</div>
        ${isMe ? '<div class="member-badge">✨ Você</div>' : ''}
        <div class="member-stats">
          <div class="member-stat"><span class="ms-value" style="color:#f87171">${u.duplicate_count}</span><span class="ms-label">Repetidas</span></div>
          <div class="member-stat"><span class="ms-value" style="color:#60a5fa">${u.wanted_count}</span><span class="ms-label">Faltas</span></div>
        </div>`;
      membersEl.appendChild(card);
    });
  } catch (e) {
    statsEl.innerHTML = `<p style="color:var(--red)">${e.message}</p>`;
  }
}

async function loadGroupView() {
  const container = document.getElementById('groupContainer');
  container.innerHTML = '<div class="skeleton" style="height:200px;border-radius:16px"></div>';
  try {
    const overview = await Api.getGroupOverview();
    if (overview.length === 0) {
      container.innerHTML = '<div class="trades-empty"><div class="empty-icon">👥</div><h3>Nenhum membro ainda</h3></div>';
      return;
    }
    container.innerHTML = '';
    overview.forEach(entry => {
      const u = entry.user;
      const isMe = u.id === currentUser?.id;
      const card = document.createElement('div');
      card.className = 'group-user-card';
      const dupNums = entry.duplicates.map(d => d.sticker_number);
      const wantNums = entry.wanted;
      card.innerHTML = `
        <div class="group-user-header" onclick="toggleGroupCard(this)">
          <div style="width:40px;height:40px;border-radius:50%;background:${u.avatar_color};display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff;flex-shrink:0">${u.username.slice(0,2).toUpperCase()}</div>
          <span style="font-weight:600">${u.username}${isMe?' (você)':''}</span>
          <div class="group-user-stats">
            <span class="group-stat"><span style="color:#f87171;font-weight:700">${dupNums.length}</span> repetidas</span>
            <span class="group-stat"><span style="color:#60a5fa;font-weight:700">${wantNums.length}</span> faltas</span>
          </div>
          <span class="section-arrow">▶</span>
        </div>
        <div class="group-details" style="display:none">
          ${dupNums.length > 0 ? `<div style="padding:0.75rem 1.25rem;border-bottom:1px solid var(--border)"><div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;font-weight:500;text-transform:uppercase">🔴 Repetidas</div><div class="group-sticker-list">${dupNums.sort((a,b)=>a-b).map(n=>`<span class="gsb gsb-dup">#${n}</span>`).join('')}</div></div>` : ''}
          ${wantNums.length > 0 ? `<div style="padding:0.75rem 1.25rem"><div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;font-weight:500;text-transform:uppercase">🔵 Faltas</div><div class="group-sticker-list">${wantNums.sort((a,b)=>a-b).map(n=>`<span class="gsb gsb-want">#${n}</span>`).join('')}</div></div>` : ''}
          ${dupNums.length===0&&wantNums.length===0?'<div style="padding:1rem 1.25rem;color:var(--text-muted);font-size:0.85rem">Nenhuma figurinha cadastrada ainda.</div>':''}
        </div>`;
      container.appendChild(card);
    });
  } catch (e) {
    container.innerHTML = `<p style="color:var(--red);padding:1rem">${e.message}</p>`;
  }
}

function toggleGroupCard(header) {
  const details = header.nextElementSibling;
  const arrow = header.querySelector('.section-arrow');
  const isOpen = details.style.display !== 'none';
  details.style.display = isOpen ? 'none' : 'block';
  arrow.classList.toggle('open', !isOpen);
}

function setupAuth() {
  document.getElementById('tabLogin').addEventListener('click', () => {
    document.getElementById('tabLogin').classList.add('active');
    document.getElementById('tabRegister').classList.remove('active');
    document.getElementById('loginForm').classList.add('active');
    document.getElementById('registerForm').classList.remove('active');
  });
  document.getElementById('tabRegister').addEventListener('click', () => {
    document.getElementById('tabRegister').classList.add('active');
    document.getElementById('tabLogin').classList.remove('active');
    document.getElementById('registerForm').classList.add('active');
    document.getElementById('loginForm').classList.remove('active');
  });
  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const err = document.getElementById('loginError');
    err.classList.add('hidden');
    try {
      const res = await Api.login({ username: document.getElementById('loginUsername').value, password: document.getElementById('loginPassword').value });
      Api.setToken(res.access_token); currentUser = res.user; window.currentUser = res.user; enterApp();
    } catch (ex) { err.textContent = ex.message; err.classList.remove('hidden'); }
  });
  document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const err = document.getElementById('registerError');
    err.classList.add('hidden');
    try {
      const res = await Api.register({ username: document.getElementById('regUsername').value, email: document.getElementById('regEmail').value, password: document.getElementById('regPassword').value });
      Api.setToken(res.access_token); currentUser = res.user; window.currentUser = res.user; enterApp();
    } catch (ex) { err.textContent = ex.message; err.classList.remove('hidden'); }
  });
}

function enterApp() {
  document.getElementById('view-auth').classList.remove('active');
  document.getElementById('navbar').classList.remove('hidden');
  const avatar = document.getElementById('navAvatar');
  avatar.textContent = currentUser.username.slice(0,2).toUpperCase();
  avatar.style.background = currentUser.avatar_color;
  document.getElementById('navUsername').textContent = currentUser.username;
  switchView('dashboard');
}

function setupNav() {
  document.querySelectorAll('.nav-btn').forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.view)));
  document.getElementById('logoutBtn').addEventListener('click', () => {
    Api.setToken(null); currentUser = null; window.currentUser = null;
    document.getElementById('navbar').classList.add('hidden');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-auth').classList.add('active');
  });
}

async function boot() {
  spawnAuthParticles();
  setupAuth();
  setupNav();
  Api.loadToken();
  if (Api._token) {
    try { const user = await Api.getMe(); currentUser = user; window.currentUser = user; hideSplash(); enterApp(); return; }
    catch (_) { Api.setToken(null); }
  }
  hideSplash();
  document.getElementById('view-auth').classList.add('active');
}

window.addEventListener('DOMContentLoaded', () => setTimeout(boot, 1600));
