const Trades = {
  async generate() {
    const btn = document.getElementById('generateTradesBtn');
    const status = document.getElementById('tradesStatus');
    const container = document.getElementById('tradesContainer');
    btn.disabled = true;
    btn.innerHTML = '<span class="btn-icon spin">⚽</span> Calculando...';
    status.textContent = '';
    try {
      const result = await Api.generateTrades();
      this.render(result);
    } catch (e) {
      container.innerHTML = `<div class="trades-empty"><div class="empty-icon">⚠️</div><h3>Erro ao gerar sugestões</h3><p>${e.message}</p></div>`;
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span class="btn-icon">⚡</span> Gerar Sugestões';
    }
  },

  render(result) {
    const container = document.getElementById('tradesContainer');
    const status = document.getElementById('tradesStatus');
    if (!result || result.trades.length === 0) {
      container.innerHTML = `<div class="trades-empty"><div class="empty-icon">🤝</div><h3>Nenhuma troca possível no momento</h3><p>Adicione mais figurinhas repetidas e faltas!</p></div>`;
      return;
    }
    const ts = new Date(result.generated_at + 'Z').toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    status.textContent = `${result.trades.length} troca(s) · ${result.total_exchanges} figurinha(s) · ${ts}`;
    container.innerHTML = '';
    const summary = document.createElement('div');
    summary.className = 'glass-card';
    summary.style.cssText = 'padding:1.25rem 1.5rem;display:flex;gap:2rem;align-items:center;flex-wrap:wrap;margin-bottom:0.5rem;';
    summary.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:2px">
        <span style="font-family:var(--font-title);font-size:2rem;color:var(--gold);line-height:1">${result.trades.length}</span>
        <span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase">Trocas Sugeridas</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:2px">
        <span style="font-family:var(--font-title);font-size:2rem;color:var(--green);line-height:1">${result.total_exchanges}</span>
        <span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase">Figurinhas em Jogo</span>
      </div>
      <div style="margin-left:auto;font-size:0.8rem;color:var(--text-muted)">✨ Combinações randomizadas e otimizadas</div>
    `;
    container.appendChild(summary);
    result.trades.forEach((trade, i) => {
      const card = document.createElement('div');
      card.className = 'trade-card new-trade';
      card.style.animationDelay = `${i * 0.08}s`;
      const scorePercent = Math.round(trade.score * 100);
      const uA = trade.from_user, uB = trade.to_user;
      card.innerHTML = `
        <div class="trade-card-header">
          <div class="trade-users">
            <div class="trade-avatar" style="background:${uA.avatar_color}">${uA.username.slice(0,2).toUpperCase()}</div>
            <div>
              <div style="font-weight:600;font-size:0.9rem">${uA.username}</div>
              <div style="font-size:0.72rem;color:var(--text-muted)">${uA.duplicate_count} repetidas</div>
            </div>
            <div class="trade-arrow">⇄</div>
            <div class="trade-avatar" style="background:${uB.avatar_color}">${uB.username.slice(0,2).toUpperCase()}</div>
            <div>
              <div style="font-weight:600;font-size:0.9rem">${uB.username}</div>
              <div style="font-size:0.72rem;color:var(--text-muted)">${uB.duplicate_count} repetidas</div>
            </div>
          </div>
          <div class="trade-score">${scorePercent}% match
            <div class="score-bar"><div class="score-fill" style="width:${scorePercent}%"></div></div>
          </div>
        </div>
        <div class="trade-body">
          <div class="trade-side">
            <div class="trade-side-label">🔴 ${uA.username} dá para ${uB.username}</div>
            ${trade.stickers_given.length > 0
              ? trade.stickers_given.map(s => `<div class="trade-sticker-pill"><span class="pill-num">#${s.sticker_number}</span><span class="pill-name" title="${s.name}">${s.name}</span></div>`).join('')
              : '<span style="color:var(--text-muted);font-size:0.8rem">Nenhuma</span>'}
          </div>
          <div class="trade-center"><span class="trade-exchange-icon">🔄</span></div>
          <div class="trade-side">
            <div class="trade-side-label">🔴 ${uB.username} dá para ${uA.username}</div>
            ${trade.stickers_received.length > 0
              ? trade.stickers_received.map(s => `<div class="trade-sticker-pill"><span class="pill-num">#${s.sticker_number}</span><span class="pill-name" title="${s.name}">${s.name}</span></div>`).join('')
              : '<span style="color:var(--text-muted);font-size:0.8rem">Nenhuma</span>'}
          </div>
        </div>`;
      container.appendChild(card);
    });
    if (result.total_exchanges >= 3) spawnConfetti();
  },
};

function spawnConfetti() {
  const colors = ['#FFD700','#FFA500','#10b981','#3b82f6','#ef4444','#8b5cf6'];
  for (let i = 0; i < 40; i++) {
    const el = document.createElement('div');
    el.className = 'confetti-piece';
    el.style.cssText = `left:${Math.random()*100}vw;top:-20px;background:${colors[Math.floor(Math.random()*colors.length)]};width:${6+Math.random()*8}px;height:${6+Math.random()*8}px;border-radius:${Math.random()>0.5?'50%':'2px'};animation-duration:${1.5+Math.random()*2}s;animation-delay:${Math.random()*0.8}s;position:fixed;z-index:9998;pointer-events:none;`;
    document.body.appendChild(el);
    el.addEventListener('animationend', () => el.remove());
  }
}
