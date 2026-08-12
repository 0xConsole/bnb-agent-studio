// BNB Agent Studio Marketplace — Frontend JS

// ---- Toast ----
function showToast(title, msg, isError) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.className = 'toast' + (isError ? ' error show' : ' show');
  t.querySelector('.toast-title').textContent = title;
  t.querySelector('.toast-msg').textContent = msg;
  setTimeout(() => { t.className = 'toast'; }, 4000);
}

// ---- Wallet helpers ----
function getWallet() {
  return localStorage.getItem('bnb_wallet') || '0x3f567c3254E9Dc9C2813E2a8b71BB3604Ba53155';
}
function setWallet(addr) {
  localStorage.setItem('bnb_wallet', addr);
}

// ---- Format ----
function formatUsd(v) {
  if (v >= 1e6) return '$' + (v / 1e6).toFixed(2) + 'M';
  if (v >= 1e3) return '$' + (v / 1e3).toFixed(1) + 'K';
  return '$' + v.toFixed(2);
}
function formatNum(v) {
  if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M';
  if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K';
  return v.toFixed(1);
}

// ---- Activate / Deactivate ----
async function toggleActivation(agentId, btn) {
  const wallet = getWallet();
  if (btn.classList.contains('activated')) {
    // Deactivate
    try {
      const r = await fetch('/api/deactivate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId, wallet_address: wallet })
      });
      const data = await r.json();
      if (data.status === 'deactivated') {
        btn.classList.remove('activated');
        btn.textContent = 'Activate';
        showToast('Deactivated', 'Agent has been deactivated', false);
      }
    } catch (e) {
      showToast('Error', 'Failed to deactivate agent', true);
    }
  } else {
    // Activate
    try {
      const r = await fetch('/api/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId, wallet_address: wallet })
      });
      const data = await r.json();
      if (data.status === 'activated') {
        btn.classList.add('activated');
        btn.textContent = 'Active ✓';
        showToast('Agent Activated!', `${data.activation.agent_name} is now active on your wallet`, false);
      }
    } catch (e) {
      showToast('Error', 'Failed to activate agent', true);
    }
  }
}

// ---- Run Demo ----
async function runDemo() {
  const btn = document.getElementById('demo-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Running...'; }
  try {
    const r = await fetch('/api/demo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wallet_address: getWallet() })
    });
    const data = await r.json();
    if (data.demo === 'complete') {
      showToast('Demo Complete!', `${data.steps.length} steps executed across ${data.categories_covered.length} categories`, false);
      if (btn) { btn.textContent = '✓ Demo Complete'; }
    }
  } catch (e) {
    showToast('Error', 'Demo failed to run', true);
    if (btn) { btn.disabled = false; btn.textContent = 'Run Demo'; }
  }
}

// ---- Refresh chain status ----
async function refreshChain() {
  try {
    const r = await fetch('/api/chain');
    const data = await r.json();
    const el = document.getElementById('chain-block');
    if (el) el.textContent = data.mainnet.latest_block.toLocaleString();
    const elGas = document.getElementById('chain-gas');
    if (elGas) elGas.textContent = data.mainnet.gas_price_gwei + ' Gwei';
    const elTest = document.getElementById('chain-testnet-block');
    if (elTest) elTest.textContent = data.testnet.latest_block.toLocaleString();
  } catch (e) { console.warn('chain refresh failed', e); }
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', function() {
  // Auto-refresh chain status every 30s
  if (document.getElementById('chain-block')) {
    refreshChain();
    setInterval(refreshChain, 30000);
  }

  // Wallet input
  const walletInput = document.getElementById('wallet-input');
  if (walletInput) {
    walletInput.value = getWallet();
    walletInput.addEventListener('change', function() {
      setWallet(this.value.trim());
      showToast('Wallet Updated', 'Demo wallet address saved', false);
    });
  }

  // Demo button
  const demoBtn = document.getElementById('demo-btn');
  if (demoBtn) {
    demoBtn.addEventListener('click', runDemo);
  }

  // Activate buttons
  document.querySelectorAll('.btn-activate').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const agentId = this.getAttribute('data-agent-id');
      toggleActivation(agentId, this);
    });
  });
});
