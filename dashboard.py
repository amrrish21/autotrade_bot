"""
dashboard.py — Flask web server that serves the live trading dashboard.

Run alongside bot.py:
    Terminal 1:  python bot.py
    Terminal 2:  python dashboard.py

Then open:  http://localhost:5000  in your browser.

The dashboard reads from bot_state.json which bot.py writes every scan cycle.
"""

import json
import os
from flask import Flask, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)
STATE_FILE = os.path.join(os.path.dirname(__file__), "bot_state.json")

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>StockSarthi AI — Live Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --g:#00e676;--b:#00b0ff;--r:#ff1744;--o:#ff6d00;--p:#d500f9;
  --bg0:#030a05;--bg1:#061008;--bg2:#0a1a0d;--card:#071510;
  --bord:rgba(0,230,118,.15);--bordb:rgba(0,176,255,.15);
  --t1:#e8fff2;--t2:#7ab890;--t3:#2d5c3a;
}
body{background:var(--bg0);color:var(--t1);font-family:'Space Grotesk',sans-serif;min-height:100vh}
.mono{font-family:'JetBrains Mono',monospace}

/* topbar */
.topbar{background:var(--bg1);border-bottom:1px solid var(--bord);padding:0 20px;height:52px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.logo{display:flex;align-items:center;gap:10px}
.logo-mark{width:32px;height:32px;border-radius:8px;background:rgba(0,230,118,.1);border:1px solid var(--g);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:var(--g)}
.logo-text{font-size:15px;font-weight:700;letter-spacing:1.5px;color:var(--g)}
.logo-sub{font-size:9px;color:var(--t2);letter-spacing:.5px}
.topbar-right{display:flex;align-items:center;gap:14px;font-size:11px}
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 9px;border-radius:20px;font-size:10px;font-weight:700;letter-spacing:.3px}
.bg{background:rgba(0,230,118,.1);color:var(--g);border:1px solid rgba(0,230,118,.25)}
.bb{background:rgba(0,176,255,.1);color:var(--b);border:1px solid rgba(0,176,255,.2)}
.br{background:rgba(255,23,68,.1);color:var(--r);border:1px solid rgba(255,23,68,.2)}
.bo{background:rgba(255,109,0,.1);color:var(--o);border:1px solid rgba(255,109,0,.2)}
.bp{background:rgba(213,0,249,.1);color:var(--p);border:1px solid rgba(213,0,249,.2)}
.pdot{width:7px;height:7px;border-radius:50%;background:var(--g);display:inline-block;animation:pulse 1.4s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.2}}

/* layout */
.main{padding:20px;max-width:1400px;margin:0 auto}
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
.grid-2-1{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-bottom:16px}
@media(max-width:900px){.grid-4,.grid-3{grid-template-columns:1fr 1fr}.grid-2-1{grid-template-columns:1fr}}
@media(max-width:600px){.grid-4,.grid-3,.grid-2{grid-template-columns:1fr}}

/* cards */
.card{background:var(--card);border:1px solid var(--bord);border-radius:10px;padding:14px}
.card-b{border-color:var(--bordb)}
.card-g{border-color:rgba(0,230,118,.3)}
.card-r{border-color:rgba(255,23,68,.25)}
.lbl{font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}
.val{font-size:22px;font-weight:700;font-family:'JetBrains Mono',monospace}
.val-sm{font-size:14px;font-weight:600;font-family:'JetBrains Mono',monospace}
.sec{font-size:9px;font-weight:700;color:var(--t2);text-transform:uppercase;letter-spacing:1.2px;margin-bottom:10px}
.row{display:flex;align-items:center}
.btwn{justify-content:space-between}
.gap8{gap:8px}

/* stat card */
.stat-card{background:var(--card);border:1px solid var(--bord);border-radius:10px;padding:14px;position:relative;overflow:hidden}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent,var(--g))}
.stat-icon{font-size:20px;margin-bottom:6px}

/* index bar */
.idx-bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.idx-pill{padding:8px 14px;background:var(--bg2);border:1px solid var(--bord);border-radius:8px;flex:1;min-width:120px}
.idx-name{font-size:9px;color:var(--t2);text-transform:uppercase;letter-spacing:.8px;margin-bottom:2px}
.idx-val{font-size:15px;font-weight:700;font-family:'JetBrains Mono',monospace}
.idx-chg{font-size:10px;margin-top:1px}

/* positions table */
.pos-table{width:100%;border-collapse:collapse}
.pos-table th{font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:.8px;padding:6px 10px;text-align:left;border-bottom:1px solid rgba(0,230,118,.1)}
.pos-table td{padding:10px;font-size:12px;border-bottom:1px solid rgba(255,255,255,.04)}
.pos-table tr:last-child td{border-bottom:none}
.pos-table tr:hover td{background:rgba(0,230,118,.03)}
.no-pos{text-align:center;color:var(--t2);font-size:12px;padding:30px}

/* trade log */
.log-item{display:flex;gap:10px;padding:9px 12px;border-bottom:1px solid rgba(255,255,255,.04);align-items:flex-start}
.log-item:last-child{border-bottom:none}
.log-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:4px}
.log-time{font-size:9px;color:var(--t3);font-family:'JetBrains Mono',monospace;flex-shrink:0;min-width:55px}
.log-msg{font-size:11px;color:var(--t2);flex:1}
.log-pnl{font-size:11px;font-weight:600;font-family:'JetBrains Mono',monospace;flex-shrink:0}

/* progress bar */
.prog-wrap{margin-top:6px}
.prog-track{height:5px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden;margin-top:4px}
.prog-fill{height:100%;border-radius:3px;transition:width .6s ease}

/* bot status ring */
.bot-ring{width:70px;height:70px;border-radius:50%;border:2px solid var(--g);background:rgba(0,230,118,.05);display:flex;align-items:center;justify-content:center;font-size:26px;margin:0 auto 10px;animation:glow 2s ease-in-out infinite}
@keyframes glow{0%,100%{box-shadow:0 0 8px rgba(0,230,118,.3)}50%{box-shadow:0 0 20px rgba(0,230,118,.6)}}
.bot-halted{border-color:var(--r);animation:none;box-shadow:0 0 12px rgba(255,23,68,.3)}

/* refresh indicator */
.refresh-dot{width:6px;height:6px;border-radius:50%;background:var(--g);display:inline-block;animation:pulse 1.4s infinite}
.last-updated{font-size:10px;color:var(--t3);font-family:'JetBrains Mono',monospace}
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">
    <div class="logo-mark">SS</div>
    <div>
      <div class="logo-text">STOCKSARTHI AI</div>
      <div class="logo-sub">UPSTOX AUTO TRADING DASHBOARD</div>
    </div>
  </div>
  <div class="topbar-right">
    <span class="badge bg" id="mktBadge"><span class="pdot"></span> MARKET OPEN</span>
    <span class="mono" id="clock" style="font-size:12px;color:var(--t2)">--:--:--</span>
    <span class="badge bb" id="modeBadge">PAPER</span>
    <span class="row gap8"><span class="refresh-dot"></span><span class="last-updated" id="lastUpdated">Connecting...</span></span>
  </div>
</div>

<div class="main">

  <!-- Index bar -->
  <div class="idx-bar" id="idxBar">
    <div class="idx-pill"><div class="idx-name">NIFTY 50</div><div class="idx-val" id="nifty50">—</div><div class="idx-chg" id="nifty50c">—</div></div>
    <div class="idx-pill"><div class="idx-name">SENSEX</div><div class="idx-val" id="sensex">—</div><div class="idx-chg" id="sensexc">—</div></div>
    <div class="idx-pill"><div class="idx-name">BANK NIFTY</div><div class="idx-val" id="banknifty">—</div><div class="idx-chg" id="bankniftyc">—</div></div>
    <div class="idx-pill"><div class="idx-name">NIFTY IT</div><div class="idx-val" id="niftyit">—</div><div class="idx-chg" id="niftyitc">—</div></div>
  </div>

  <!-- Stat cards row -->
  <div class="grid-4">
    <div class="stat-card" style="--accent:var(--g)">
      <div class="stat-icon">💰</div>
      <div class="lbl">Today P&amp;L</div>
      <div class="val" id="todayPnl" style="color:var(--g)">₹0.00</div>
      <div style="font-size:10px;color:var(--t2);margin-top:2px" id="pnlPct">0.00%</div>
    </div>
    <div class="stat-card" style="--accent:var(--b)">
      <div class="stat-icon">📊</div>
      <div class="lbl">Total Trades</div>
      <div class="val" id="totalTrades" style="color:var(--b)">0</div>
      <div style="font-size:10px;color:var(--t2);margin-top:2px" id="winRate">Win rate: 0%</div>
    </div>
    <div class="stat-card" style="--accent:var(--p)">
      <div class="stat-icon">📈</div>
      <div class="lbl">Open Positions</div>
      <div class="val" id="openPos" style="color:var(--p)">0</div>
      <div style="font-size:10px;color:var(--t2);margin-top:2px">Active trades</div>
    </div>
    <div class="stat-card" style="--accent:var(--o)">
      <div class="stat-icon">🛡️</div>
      <div class="lbl">Capital Deployed</div>
      <div class="val" id="capitalDeployed" style="color:var(--o)">₹0</div>
      <div style="font-size:10px;color:var(--t2);margin-top:2px" id="capitalPct">0% of limit</div>
    </div>
  </div>

  <!-- P&L chart + Bot status -->
  <div class="grid-2-1">
    <div class="card">
      <div class="sec">LIVE P&amp;L CURVE (TODAY)</div>
      <div style="position:relative;height:200px">
        <canvas id="pnlChart"></canvas>
      </div>
    </div>
    <div class="card card-g" style="text-align:center">
      <div class="lbl" style="margin-bottom:8px">BOT STATUS</div>
      <div class="bot-ring" id="botRing">🤖</div>
      <div style="font-size:13px;font-weight:700;color:var(--g)" id="botStatus">SCANNING...</div>
      <div style="font-size:10px;color:var(--t2);margin:4px 0 14px" id="botMode">Paper Trading Mode</div>
      <div class="badge bg" id="stratBadge" style="margin-bottom:8px">EMA + RSI + MACD</div>
      <div style="margin-top:12px">
        <div class="lbl">Daily Target Progress</div>
        <div class="row btwn" style="margin-top:4px"><span style="font-size:10px;color:var(--t2)" id="targetLabel">₹0 / ₹0</span><span style="font-size:10px;color:var(--g)" id="targetPct">0%</span></div>
        <div class="prog-track"><div class="prog-fill" style="background:var(--g)" id="targetBar"></div></div>
      </div>
      <div style="margin-top:10px">
        <div class="lbl">Loss Limit</div>
        <div class="row btwn" style="margin-top:4px"><span style="font-size:10px;color:var(--t2)" id="lossLabel">₹0 / ₹0</span><span style="font-size:10px;color:var(--r)" id="lossPct">0%</span></div>
        <div class="prog-track"><div class="prog-fill" style="background:var(--r)" id="lossBar"></div></div>
      </div>
    </div>
  </div>

  <!-- Open positions -->
  <div class="card" style="margin-bottom:16px">
    <div class="sec">OPEN POSITIONS</div>
    <div id="positionsTable">
      <div class="no-pos">No open positions — bot is scanning for signals</div>
    </div>
  </div>

  <!-- Trade log + Watchlist signals -->
  <div class="grid-2">
    <div class="card">
      <div class="sec">TRADE LOG (TODAY)</div>
      <div id="tradeLog" style="max-height:280px;overflow-y:auto">
        <div class="no-pos">No trades yet today</div>
      </div>
    </div>
    <div class="card">
      <div class="sec">WATCHLIST SIGNALS</div>
      <div id="signalsList" style="max-height:280px;overflow-y:auto">
        <div class="no-pos">Waiting for scan...</div>
      </div>
    </div>
  </div>

  <!-- Daily stats row -->
  <div class="grid-3" style="margin-top:16px">
    <div class="card">
      <div class="sec">SESSION RUNTIME</div>
      <div class="val" id="runtime" style="color:var(--b);font-size:20px">00:00:00</div>
      <div style="font-size:10px;color:var(--t2);margin-top:4px">Since 9:15 AM IST</div>
    </div>
    <div class="card">
      <div class="sec">SIGNALS PROCESSED</div>
      <div class="val" id="sigCount" style="color:var(--p);font-size:20px">0</div>
      <div style="font-size:10px;color:var(--t2);margin-top:4px">Last scan: <span id="lastScan">--</span></div>
    </div>
    <div class="card">
      <div class="sec">BEST TRADE TODAY</div>
      <div class="val" id="bestTrade" style="color:var(--g);font-size:20px">₹0.00</div>
      <div style="font-size:10px;color:var(--t2);margin-top:4px" id="bestSymbol">—</div>
    </div>
  </div>

</div><!-- /main -->

<script>
// ── Clock ──────────────────────────────────────────────────────────────────
function updateClock(){
  const n = new Date();
  document.getElementById('clock').textContent =
    n.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});

  const h = n.getHours(), m = n.getMinutes();
  const open   = (h === 9 && m >= 15) || h > 9;
  const closed  = h >= 15 && m >= 30;
  const badge   = document.getElementById('mktBadge');
  if(closed){
    badge.innerHTML = '⛔ MARKET CLOSED';
    badge.className = 'badge br';
  } else if(open){
    badge.innerHTML = '<span class="pdot"></span> MARKET OPEN';
    badge.className = 'badge bg';
  } else {
    badge.innerHTML = '⏳ PRE-MARKET';
    badge.className = 'badge bo';
  }
}
setInterval(updateClock, 1000);
updateClock();

// ── P&L Chart ──────────────────────────────────────────────────────────────
const pnlCtx = document.getElementById('pnlChart').getContext('2d');
const pnlChart = new Chart(pnlCtx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [{
      label: 'P&L (₹)',
      data: [],
      borderColor: '#00e676',
      backgroundColor: 'rgba(0,230,118,.07)',
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      borderWidth: 2,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 400 },
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#2d5c3a', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,.04)' } },
      y: { ticks: { color: '#2d5c3a', font: { size: 9 }, callback: v => '₹' + v.toLocaleString('en-IN') },
           grid: { color: 'rgba(255,255,255,.04)' } }
    }
  }
});

// ── Helpers ────────────────────────────────────────────────────────────────
function fmt(n){ return '₹' + parseFloat(n).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function fmtPnl(n){
  const v = parseFloat(n);
  return (v >= 0 ? '+' : '') + fmt(v);
}
function pnlColor(n){ return parseFloat(n) >= 0 ? 'var(--g)' : 'var(--r)'; }

// ── Fetch state from Flask API ─────────────────────────────────────────────
let scanCount = 0;

async function fetchState(){
  try {
    const resp = await fetch('/api/state');
    if(!resp.ok) throw new Error('Server error');
    const d = await resp.json();
    scanCount++;

    document.getElementById('lastUpdated').textContent =
      'Updated ' + new Date().toLocaleTimeString('en-IN', {hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});

    // Mode badge
    const modeBadge = document.getElementById('modeBadge');
    modeBadge.textContent = d.paper_trading ? 'PAPER' : 'LIVE';
    modeBadge.className = d.paper_trading ? 'badge bb' : 'badge bg';

    // Stat cards
    const pnl = parseFloat(d.daily_pnl || 0);
    document.getElementById('todayPnl').textContent = fmtPnl(pnl);
    document.getElementById('todayPnl').style.color = pnlColor(pnl);
    document.getElementById('pnlPct').textContent = (d.pnl_pct || '0.00') + '% of capital';

    document.getElementById('totalTrades').textContent = d.total_trades || 0;
    document.getElementById('winRate').textContent = 'Win rate: ' + (d.win_rate || 0) + '%';

    document.getElementById('openPos').textContent = Object.keys(d.positions || {}).length;

    const deployed = parseFloat(d.capital_deployed || 0);
    document.getElementById('capitalDeployed').textContent = fmt(deployed);
    document.getElementById('capitalPct').textContent =
      ((deployed / parseFloat(d.max_capital || 50000)) * 100).toFixed(1) + '% of limit';

    // Bot status
    const halted  = d.trading_halted;
    const ring    = document.getElementById('botRing');
    const status  = document.getElementById('botStatus');
    ring.className = 'bot-ring' + (halted ? ' bot-halted' : '');
    if(halted){
      status.textContent = '⛔ ' + (d.halt_reason || 'HALTED');
      status.style.color = 'var(--r)';
    } else {
      status.textContent = '✅ TRADING ACTIVE';
      status.style.color = 'var(--g)';
    }
    document.getElementById('botMode').textContent =
      (d.paper_trading ? '📄 Paper' : '💰 Live') + ' · ' + (d.strategy || 'EMA+RSI+MACD') +
      ' · ' + (d.interval || '30m') + ' candles';

    // Target progress
    const cap = parseFloat(d.max_capital || 50000);
    const tgt = cap * parseFloat(d.daily_profit_target_pct || 3) / 100;
    const tgtPct = Math.min(100, Math.max(0, (pnl / tgt) * 100));
    document.getElementById('targetLabel').textContent = fmtPnl(pnl) + ' / ' + fmt(tgt);
    document.getElementById('targetPct').textContent = tgtPct.toFixed(1) + '%';
    document.getElementById('targetBar').style.width = tgtPct + '%';

    // Loss progress
    const lossLimit = cap * parseFloat(d.daily_loss_limit_pct || 5) / 100;
    const lossSoFar = Math.max(0, -pnl);
    const lossPct   = Math.min(100, (lossSoFar / lossLimit) * 100);
    document.getElementById('lossLabel').textContent = fmt(lossSoFar) + ' / ' + fmt(lossLimit);
    document.getElementById('lossPct').textContent = lossPct.toFixed(1) + '%';
    document.getElementById('lossBar').style.width = lossPct + '%';

    // P&L chart
    const pnlHistory = d.pnl_history || [];
    pnlChart.data.labels  = pnlHistory.map(p => p.time);
    pnlChart.data.datasets[0].data  = pnlHistory.map(p => p.pnl);
    pnlChart.data.datasets[0].borderColor = pnl >= 0 ? '#00e676' : '#ff1744';
    pnlChart.data.datasets[0].backgroundColor = pnl >= 0 ? 'rgba(0,230,118,.07)' : 'rgba(255,23,68,.07)';
    pnlChart.update();

    // Positions table
    const positions = d.positions || {};
    const posDiv = document.getElementById('positionsTable');
    if(Object.keys(positions).length === 0){
      posDiv.innerHTML = '<div class="no-pos">No open positions — bot is scanning for signals</div>';
    } else {
      let html = `<table class="pos-table">
        <thead><tr>
          <th>Symbol</th><th>Direction</th><th>Qty</th>
          <th>Entry</th><th>LTP</th><th>P&L</th><th>SL</th><th>TP</th>
        </tr></thead><tbody>`;
      for(const [sym, pos] of Object.entries(positions)){
        const ltp    = parseFloat(pos.ltp || pos.entry_price);
        const posPnL = pos.direction === 'BUY'
          ? (ltp - pos.entry_price) * pos.qty
          : (pos.entry_price - ltp) * pos.qty;
        html += `<tr>
          <td><strong>${sym}</strong></td>
          <td><span class="badge ${pos.direction === 'BUY' ? 'bg' : 'br'}">${pos.direction}</span></td>
          <td class="mono">${pos.qty}</td>
          <td class="mono">${fmt(pos.entry_price)}</td>
          <td class="mono">${fmt(ltp)}</td>
          <td class="mono" style="color:${posPnL >= 0 ? 'var(--g)' : 'var(--r)'}">${fmtPnl(posPnL)}</td>
          <td class="mono" style="color:var(--r)">${fmt(pos.stop_loss)}</td>
          <td class="mono" style="color:var(--g)">${fmt(pos.take_profit)}</td>
        </tr>`;
      }
      html += '</tbody></table>';
      posDiv.innerHTML = html;
    }

    // Trade log
    const trades = (d.trade_log || []).slice().reverse();
    const logDiv = document.getElementById('tradeLog');
    if(trades.length === 0){
      logDiv.innerHTML = '<div class="no-pos">No trades yet today</div>';
    } else {
      logDiv.innerHTML = trades.map(t => {
        const pnl = parseFloat(t.pnl);
        const col  = pnl >= 0 ? 'var(--g)' : 'var(--r)';
        const dot  = pnl >= 0 ? 'var(--g)' : 'var(--r)';
        const time = t.timestamp ? t.timestamp.substring(11,19) : '--';
        return `<div class="log-item">
          <div class="log-dot" style="background:${dot}"></div>
          <div class="log-time">${time}</div>
          <div class="log-msg">${t.direction} ${t.qty}× <strong>${t.symbol}</strong><br>
            <span style="font-size:9px">${t.reason || ''}</span></div>
          <div class="log-pnl" style="color:${col}">${fmtPnl(pnl)}</div>
        </div>`;
      }).join('');
    }

    // Signals
    const signals = d.last_signals || {};
    const sigDiv  = document.getElementById('signalsList');
    if(Object.keys(signals).length === 0){
      sigDiv.innerHTML = '<div class="no-pos">Waiting for scan...</div>';
    } else {
      const colorMap  = { BUY:'bg', SELL:'br', HOLD:'bb' };
      sigDiv.innerHTML = Object.entries(signals).map(([sym, sig]) => {
        const cls = colorMap[sig.signal] || 'bb';
        return `<div class="log-item">
          <div class="log-dot" style="background:${sig.signal==='BUY'?'var(--g)':sig.signal==='SELL'?'var(--r)':'var(--b)'}"></div>
          <div class="log-msg"><strong>${sym}</strong> <span class="badge ${cls}" style="font-size:8px">${sig.signal}</span><br>
            <span style="font-size:9px;color:var(--t2)">${(sig.reason||'').substring(0,60)}</span></div>
          <div class="log-pnl" style="font-size:10px;color:var(--t2)">${sig.price ? fmt(sig.price) : ''}</div>
        </div>`;
      }).join('');
    }

    // Stats row
    document.getElementById('sigCount').textContent = scanCount * Object.keys(d.watchlist || {}).length;
    document.getElementById('lastScan').textContent = new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:false});

    const allTrades = d.trade_log || [];
    const best = allTrades.reduce((b, t) => parseFloat(t.pnl) > b ? parseFloat(t.pnl) : b, 0);
    const bestT = allTrades.find(t => parseFloat(t.pnl) === best);
    document.getElementById('bestTrade').textContent = fmtPnl(best);
    document.getElementById('bestTrade').style.color = best >= 0 ? 'var(--g)' : 'var(--r)';
    document.getElementById('bestSymbol').textContent = bestT ? bestT.symbol : '—';

    // Runtime
    if(d.session_start){
      const diff = Math.floor((Date.now() - new Date(d.session_start).getTime()) / 1000);
      const h = String(Math.floor(diff/3600)).padStart(2,'0');
      const m = String(Math.floor((diff%3600)/60)).padStart(2,'0');
      const s = String(diff%60).padStart(2,'0');
      document.getElementById('runtime').textContent = h+':'+m+':'+s;
    }

    // Indices
    const idx = d.indices || {};
    function setIdx(id, valId, chgId, val, chg){
      document.getElementById(valId).textContent = val || '—';
      const el = document.getElementById(chgId);
      if(chg){
        const up = chg.startsWith('+') || parseFloat(chg) >= 0;
        el.textContent = (up ? '▲ ' : '▼ ') + chg;
        el.style.color = up ? 'var(--g)' : 'var(--r)';
      }
    }
    setIdx('n','nifty50','nifty50c', idx.nifty50?.value, idx.nifty50?.change);
    setIdx('s','sensex','sensexc',   idx.sensex?.value,  idx.sensex?.change);
    setIdx('b','banknifty','bankniftyc', idx.banknifty?.value, idx.banknifty?.change);
    setIdx('i','niftyit','niftyitc', idx.niftyit?.value, idx.niftyit?.change);

  } catch(err){
    document.getElementById('lastUpdated').textContent = 'Bot offline — start bot.py';
  }
}

fetchState();
setInterval(fetchState, 3000);   // refresh every 3 seconds
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/state")
def state():
    """Read the latest bot state from bot_state.json."""
    if not os.path.exists(STATE_FILE):
        return jsonify({
            "error": "bot_state.json not found — is bot.py running?",
            "daily_pnl": 0,
            "total_trades": 0,
            "positions": {},
            "trade_log": [],
            "trading_halted": False,
            "paper_trading": True,
        })
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("="*55)
    print("  StockSarthi Dashboard")
    print("="*55)
    print("  Open in browser:  http://localhost:5000")
    print("  (Start bot.py in a separate terminal)")
    print("="*55)
    app.run(host="0.0.0.0", port=5000, debug=False)
