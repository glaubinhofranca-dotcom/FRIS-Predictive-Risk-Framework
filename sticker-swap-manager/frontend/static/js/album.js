const Album = {
  catalog: [], sections: [],
  myDups: new Map(), myWanted: new Set(),
  filter: 'all', openSections: new Set(),
  groupData: [], _toastTimer: null,

  async init() {
    const [catalog, sections, dups, wanted] = await Promise.all([
      Api.getCatalog(), Api.getSections(),
      Api.getMyDuplicates(), Api.getMyWanted(),
    ]);
    this.catalog = catalog;
    this.sections = sections;
    this.myDups = new Map(dups.map(d => [d.sticker_number, d.quantity]));
    this.myWanted = new Set(wanted.map(w => w.sticker_number));
    if (sections.length > 0) this.openSections.add(sections[0].id);
    this.render();
    this._setupFilters();
    this._loadGroupData();
  },

  async _loadGroupData() {
    try { this.groupData = await Api.getGroupOverview(); } catch (_) {}
  },

  _setupFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.filter = btn.dataset.filter;
        this.render();
      });
    });
  },

  render() {
    const container = document.getElementById('albumSections');
    container.innerHTML = '';
    this.sections.forEach(sec => {
      const filtered = this._filterStickers(sec.stickers);
      if (this.filter !== 'all' && filtered.length === 0) return;
      const dupCount = sec.stickers.filter(n => this.myDups.has(n)).length;
      const wantCount = sec.stickers.filter(n => this.myWanted.has(n)).length;
      const isOpen = this.openSections.has(sec.id);
      const el = document.createElement('div');
      el.className = 'album-section';
      el.dataset.secId = sec.id;
      el.innerHTML = `
        <div class="section-header" onclick="Album.toggleSection('${sec.id}')">
          <span class="section-emoji">${sec.emoji}</span>
          <span class="section-name">${sec.name}</span>
          <div class="section-badge">
            ${dupCount > 0 ? `<span class="badge badge-dup">🔴 ${dupCount} rep.</span>` : ''}
            ${wantCount > 0 ? `<span class="badge badge-want">🔵 ${wantCount} falta(s)</span>` : ''}
          </div>
          <span class="section-arrow ${isOpen ? 'open' : ''}">▶</span>
        </div>
        <div class="stickers-grid" style="display:${isOpen ? 'grid' : 'none'}">
          ${this._renderStickers(sec)}
        </div>`;
      container.appendChild(el);
    });
  },

  _filterStickers(numbers) {
    if (this.filter === 'duplicates') return numbers.filter(n => this.myDups.has(n));
    if (this.filter === 'wanted') return numbers.filter(n => this.myWanted.has(n));
    return numbers;
  },

  _renderStickers(sec) {
    const nums = this.filter === 'all' ? sec.stickers : this._filterStickers(sec.stickers);
    return nums.map(n => {
      const isDup = this.myDups.has(n);
      const isWant = this.myWanted.has(n);
      const qty = this.myDups.get(n) || 0;
      let cls = isDup && isWant ? 'dup want' : isDup ? 'dup' : isWant ? 'want' : '';
      return `<div class="sticker-cell ${cls}" onclick="Album.openModal(${n})" data-num="${n}">
        ${isDup && qty > 1 ? `<div class="sticker-qty">${qty}</div>` : ''}
        <span class="sticker-icon">${sec.emoji}</span>
        <span class="sticker-num">#${n}</span>
      </div>`;
    }).join('');
  },

  toggleSection(id) {
    if (this.openSections.has(id)) this.openSections.delete(id);
    else this.openSections.add(id);
    this.render();
  },

  jumpTo() {
    const num = parseInt(document.getElementById('stickerSearch').value);
    if (!num || num < 1 || num > 670) return;
    const sec = this.sections.find(s => s.stickers.includes(num));
    if (!sec) return;
    this.openSections.add(sec.id);
    this.filter = 'all';
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b.dataset.filter === 'all'));
    this.render();
    setTimeout(() => {
      const cell = document.querySelector(`[data-num="${num}"]`);
      if (cell) { cell.scrollIntoView({ behavior: 'smooth', block: 'center' }); cell.classList.add('just-toggled'); setTimeout(() => cell.classList.remove('just-toggled'), 500); }
    }, 100);
  },

  async openModal(num) {
    const info = this.catalog.find(s => s.number === num) || { number: num, name: `Figurinha #${num}`, section: '?', section_emoji: '⭐' };
    const isDup = this.myDups.has(num);
    const isWant = this.myWanted.has(num);
    const qty = this.myDups.get(num) || 0;
    const othersHave = this.groupData.filter(u => u.duplicates.some(d => d.sticker_number === num) && u.user.id !== window.currentUser?.id).map(u => u.user);
    const othersWant = this.groupData.filter(u => u.wanted.includes(num) && u.user.id !== window.currentUser?.id).map(u => u.user);
    document.getElementById('modalContent').innerHTML = `
      <div class="modal-sticker-num">#${num}</div>
      <div class="modal-sticker-name">${info.name}</div>
      <div class="modal-sticker-section">${info.section_emoji} ${info.section}</div>
      <div class="modal-actions">
        <button class="modal-btn ${isDup ? 'active-dup' : ''}" onclick="Album.toggleDup(${num}, ${qty})">
          <span style="font-size:1.5rem">🔴</span>
          <span>${isDup ? `Repetida (${qty}x)` : 'Marcar Repetida'}</span>
          ${isDup ? '<span style="font-size:0.7rem;color:var(--text-muted)">Clique p/ remover</span>' : ''}
        </button>
        <button class="modal-btn ${isWant ? 'active-want' : ''}" onclick="Album.toggleWant(${num})">
          <span style="font-size:1.5rem">🔵</span>
          <span>${isWant ? 'Falta (marcada)' : 'Marcar Falta'}</span>
          ${isWant ? '<span style="font-size:0.7rem;color:var(--text-muted)">Clique p/ remover</span>' : ''}
        </button>
      </div>
      ${othersHave.length > 0 ? `<div class="modal-who"><div class="modal-who-title">👥 Quem tem repetida:</div><div class="who-tags">${othersHave.map(u => `<span class="who-tag" style="background:${u.avatar_color}">${u.username}</span>`).join('')}</div></div>` : ''}
      ${othersWant.length > 0 ? `<div class="modal-who" style="margin-top:0.75rem"><div class="modal-who-title">❤️ Quem quer essa figurinha:</div><div class="who-tags">${othersWant.map(u => `<span class="who-tag" style="background:${u.avatar_color}">${u.username}</span>`).join('')}</div></div>` : ''}
    `;
    document.getElementById('stickerModal').classList.remove('hidden');
  },

  async toggleDup(num, currentQty) {
    try {
      if (this.myDups.has(num)) { await Api.removeDuplicate(num); this.myDups.delete(num); this.showToast(`#${num} removida das repetidas`); }
      else { await Api.addDuplicate(num, 1); this.myDups.set(num, 1); this.showToast(`#${num} marcada como repetida! 🔴`); }
    } catch (e) { this.showToast(e.message, true); return; }
    closeModal(); this.render(); this._loadGroupData();
  },

  async toggleWant(num) {
    try {
      if (this.myWanted.has(num)) { await Api.removeWanted(num); this.myWanted.delete(num); this.showToast(`#${num} removida das faltas`); }
      else { await Api.addWanted(num); this.myWanted.add(num); this.showToast(`#${num} marcada como falta! 🔵`); }
    } catch (e) { this.showToast(e.message, true); return; }
    closeModal(); this.render(); this._loadGroupData();
  },

  showToast(msg, isError = false) {
    const el = document.getElementById('albumToast');
    el.textContent = msg;
    el.style.background = isError ? 'var(--red)' : 'var(--green)';
    el.classList.remove('hidden');
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => el.classList.add('hidden'), 2500);
  },
};

function closeModal() { document.getElementById('stickerModal').classList.add('hidden'); }
