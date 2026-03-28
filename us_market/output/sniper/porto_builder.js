// ── Proxy state ──
const _state = { selected: {} };
const state = new Proxy(_state, {
  set(target, prop, value) {
    target[prop] = value;
    if (prop === 'selected') recalculateAllocation();
    return true;
  }
});

function toggleStock(ticker) {
  const newSel = { ...state.selected };
  if (newSel[ticker]) {
    delete newSel[ticker];
  } else {
    const s = STOCKS.find(s => s.ticker === ticker);
    if (s) newSel[ticker] = { score: s.score, tf: s.tf };
  }
  state.selected = newSel;
  updateCardUI(ticker);
}

function recalculateAllocation() {
  const sel   = state.selected;
  const ticks = Object.keys(sel);
  const total = ticks.reduce((sum, t) => sum + sel[t].score, 0);
  ticks.forEach(ticker => {
    const alloc = total > 0 ? (sel[ticker].score / total) * 100 : 0;
    sel[ticker].alloc = alloc;
    const card = document.querySelector('[data-ticker="' + ticker + '"]');
    if (card) {
      const el = card.querySelector('.alloc-val');
      if (el) el.textContent = 'Alloc: ' + alloc.toFixed(1) + '%';
    }
  });
  updateFooter();
}

function updateCardUI(ticker) {
  const card  = document.querySelector('[data-ticker="' + ticker + '"]');
  if (!card) return;
  const isSel = !!state.selected[ticker];
  card.classList.toggle('selected', isSel);
  const chk = card.querySelector('.check-icon');
  if (chk) chk.textContent = isSel ? '\u2713' : '';
  const allocEl = card.querySelector('.alloc-val');
  if (allocEl && !isSel) allocEl.textContent = 'Alloc: \u2014';
}

function updateFooter() {
  const sel   = state.selected;
  const ticks = Object.keys(sel);
  const count = ticks.length;
  document.getElementById('footerCount').textContent = count;
  const chipsEl = document.getElementById('footerChips');
  const evEl    = document.getElementById('footerEv');
  if (count === 0) {
    chipsEl.innerHTML = '<span class="footer-empty">No stocks selected</span>';
    evEl.textContent  = '\u2014';
    evEl.style.color  = 'var(--dim)';
    return;
  }
  let totalEv = 0;
  ticks.forEach(ticker => {
    const s = STOCKS.find(s => s.ticker === ticker);
    if (s) totalEv += s.ev[sel[ticker].tf || '20D'];
  });
  const avgEv = totalEv / count;
  evEl.textContent = (avgEv >= 0 ? '+' : '') + avgEv.toFixed(2) + '%';
  evEl.style.color  = avgEv >= 0 ? 'var(--green)' : 'var(--red)';
  chipsEl.innerHTML = ticks.map(t => {
    const alloc = sel[t].alloc || 0;
    return '<span class="footer-chip">' + t + ' ' + alloc.toFixed(1) + '%</span>';
  }).join('');
}

// ── TF change ──
function changeTf(ticker, tf) {
  const s = STOCKS.find(s => s.ticker === ticker);
  if (!s) return;
  s.tf = tf;
  const card = document.querySelector('[data-ticker="' + ticker + '"]');
  if (card) {
    const evEl = card.querySelector('.ev-val');
    if (evEl) {
      const ev = s.ev[tf];
      evEl.textContent = 'EV: ' + (ev >= 0 ? '+' : '') + ev.toFixed(2) + '%';
    }
  }
  if (state.selected[ticker]) {
    const newSel = { ...state.selected };
    newSel[ticker].tf = tf;
    state.selected = newSel;
  }
}

// ── Stress test ──
let _stressTicker = null;
let _stressTf     = '20D';

function openStress(ticker) {
  _stressTicker = ticker;
  const s = STOCKS.find(s => s.ticker === ticker);
  _stressTf = s ? s.tf : '20D';
  renderStress();
  document.getElementById('stressOverlay').classList.add('active');
}

function switchStressTf(tf) {
  _stressTf = tf;
  renderStress();
}

function renderStress() {
  const s = STOCKS.find(s => s.ticker === _stressTicker);
  if (!s) return;
  document.getElementById('stressTicker').textContent = s.ticker + ' \u2014 ' + s.company;
  const tabs = ['5D', '10D', '20D'].map(tf =>
    '<button class="stress-tf-btn' + (tf === _stressTf ? ' active' : '') + '" ' +
    'onclick="switchStressTf(\'' + tf + '\')">' + tf + '</button>'
  ).join('');
  document.getElementById('stressTabs').innerHTML = tabs;
  const tf  = _stressTf;
  const wr  = s.wr[tf];
  const lr  = 100 - wr;
  const aw  = s.aw[tf];
  const al  = s.al[tf];
  const ev  = s.ev[tf];
  const n   = s.sample;
  function col(v)   { return v >= 0 ? 'var(--green)' : 'var(--red)'; }
  function wrCol(v) {
    if (v >= 60) return 'var(--green)';
    if (v >= 50) return 'var(--green2)';
    if (v >= 40) return 'var(--orange)';
    return 'var(--red)';
  }
  document.getElementById('stressGrid').innerHTML =
    '<div class="stress-cell"><div class="stress-cell-label">Win Rate</div>' +
      '<div class="stress-cell-val" style="color:' + wrCol(wr) + '">' + wr.toFixed(1) + '%</div></div>' +
    '<div class="stress-cell"><div class="stress-cell-label">Loss Rate</div>' +
      '<div class="stress-cell-val" style="color:var(--dim)">' + lr.toFixed(1) + '%</div></div>' +
    '<div class="stress-cell"><div class="stress-cell-label">Avg Win</div>' +
      '<div class="stress-cell-val" style="color:' + col(aw) + '">' + (aw >= 0 ? '+' : '') + aw.toFixed(2) + '%</div></div>' +
    '<div class="stress-cell"><div class="stress-cell-label">Avg Loss</div>' +
      '<div class="stress-cell-val" style="color:' + col(al) + '">' + (al >= 0 ? '+' : '') + al.toFixed(2) + '%</div></div>' +
    '<div class="stress-cell"><div class="stress-cell-label">EV (' + tf + ')</div>' +
      '<div class="stress-cell-val" style="color:' + col(ev) + '">' + (ev >= 0 ? '+' : '') + ev.toFixed(2) + '%</div></div>' +
    '<div class="stress-cell"><div class="stress-cell-label">Sample (N)</div>' +
    '<div class="stress-cell-val" style="color:var(--white)">' + n + '</div></div>';
}

function closeStress() {
  document.getElementById('stressOverlay').classList.remove('active');
}

// ── How overlay ──
function openHow()  { document.getElementById('howOverlay').classList.add('active'); }
function closeHow() { document.getElementById('howOverlay').classList.remove('active'); }

// ── Keyboard close ──
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeHow(); closeStress(); }
});

// ── Render cards ──
function renderCards() {
  const grid = document.getElementById('cardGrid');
  grid.innerHTML = STOCKS.map(s => {
    const ev     = s.ev[s.tf];
    const evSign = ev >= 0 ? '+' : '';
    const evDisp = 'EV: ' + evSign + ev.toFixed(2) + '%';
    // Split onto separate lines
    const tierLine = s.tier + '<br>' + s.sharia;
    return [
      '<div class="card" data-ticker="', s.ticker, '">',
        '<div class="zone-a zone-a-btn" data-ticker="', s.ticker, '">',
          '<div class="zone-a-inner"><span class="check-icon"></span></div>',
        '</div>',
        '<div class="zone-b">',
          '<div class="ticker-block">',
            '<a class="ticker-link" href="html/', s.ticker, '.html">', s.ticker, '</a>',
            '<div class="tier-line">', tierLine, '</div>',
          '</div>',
          '<div class="mid-block">',
            '<div class="tf-row">TF:&nbsp;',
              '<select class="tf-select" data-ticker="', s.ticker, '">',
                '<option value="5D">5 D</option>',
                '<option value="10D">10 D</option>',
                '<option value="20D" selected>20 D</option>',
              '</select>',
            '</div>',
            '<div class="score-row">Score: <span class="score-val">', s.score.toFixed(1), '</span></div>',
          '</div>',
        '</div>',
        '<div class="zone-c zone-c-btn" data-ticker="', s.ticker, '">',
          '<div class="ev-label ev-val">', evDisp, '</div>',
          '<div class="alloc-label alloc-val">Alloc: \u2014</div>',
        '</div>',
      '</div>'
    ].join('');
  }).join('');

  // Event delegation
  grid.addEventListener('click', function(e) {
    const zoneA = e.target.closest('.zone-a-btn');
    if (zoneA) { toggleStock(zoneA.dataset.ticker); return; }
    const zoneC = e.target.closest('.zone-c-btn');
    if (zoneC) { openStress(zoneC.dataset.ticker); return; }
  });

  grid.addEventListener('change', function(e) {
    if (e.target.classList.contains('tf-select')) {
      changeTf(e.target.dataset.ticker, e.target.value);
    }
  });
}

renderCards();