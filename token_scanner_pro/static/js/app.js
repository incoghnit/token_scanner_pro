const API_URL = window.location.origin + '/api';
let scanInterval = null;
let currentFilter = 'all';
let currentView = 'grid';
let allTokens = [];
let currentUser = null;
let userFavorites = new Set();
let lastScanTimestamp = null;

// ==================== INITIALISATION ====================

window.addEventListener('load', async () => {
    await checkAuth();
    await loadPreviousResults();
    initializeSearchBar();
});

// ==================== 🆕 RECHERCHE DE TOKENS ====================

function initializeSearchBar() {
    const searchBtn = document.getElementById('tokenSearchBtn');
    const searchInput = document.getElementById('tokenSearchInput');
    
    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', () => performTokenSearch());
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performTokenSearch();
            }
        });
    }
}

async function performTokenSearch() {
    const searchInput = document.getElementById('tokenSearchInput');
    const query = searchInput.value.trim();
    
    if (!query || query.length < 2) {
        alert('Entrez au moins 2 caractères pour la recherche');
        return;
    }
    
    const searchBtn = document.getElementById('tokenSearchBtn');
    const originalHTML = searchBtn.innerHTML;
    searchBtn.disabled = true;
    searchBtn.innerHTML = '<span class="spinner"></span> Recherche...';
    
    try {
        const response = await fetch(`${API_URL}/token/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success && data.results.length > 0) {
            displaySearchResults(data.results);
        } else {
            alert(`Aucun résultat trouvé pour "${query}"`);
        }
    } catch (error) {
        alert('Erreur lors de la recherche');
        console.error(error);
    } finally {
        searchBtn.disabled = false;
        searchBtn.innerHTML = originalHTML;
    }
}

function displaySearchResults(results) {
    // Ouvrir le modal de recherche
    const modal = document.getElementById('searchResultsModal');
    const container = document.getElementById('searchResultsContainer');
    
    if (!modal || !container) {
        console.error('Modal de recherche non trouvé');
        return;
    }
    
    container.innerHTML = '';
    
    results.forEach(token => {
        const card = document.createElement('div');
        card.className = 'search-result-card';
        
        const iconHtml = token.icon 
            ? `<img src="${token.icon}" alt="${token.symbol}" class="search-result-icon" onerror="this.src=''">`
            : '<span class="search-result-icon-placeholder">🪙</span>';
        
        card.innerHTML = `
            ${iconHtml}
            <div class="search-result-info">
                <div class="search-result-name">${token.name || 'N/A'}</div>
                <div class="search-result-symbol">${token.symbol || 'N/A'}</div>
                <div class="search-result-chain">${token.chain.toUpperCase()}</div>
                <div class="search-result-address">${token.address.substring(0, 10)}...${token.address.substring(token.address.length - 8)}</div>
            </div>
            <div class="search-result-stats">
                ${token.priceUsd ? `<div class="search-result-stat">💰 $${parseFloat(token.priceUsd).toFixed(8)}</div>` : ''}
                ${token.liquidity ? `<div class="search-result-stat">💧 $${formatNumber(token.liquidity)}</div>` : ''}
                ${token.marketCap ? `<div class="search-result-stat">📊 $${formatNumber(token.marketCap)}</div>` : ''}
            </div>
            <button class="btn btn-primary" onclick='analyzeSearchedToken(${JSON.stringify(token).replace(/'/g, "&#39;")})'>
                🔍 Analyser
            </button>
        `;
        
        container.appendChild(card);
    });
    
    modal.classList.add('active');
}

async function analyzeSearchedToken(token) {
    closeSearchResultsModal();
    
    const loadingModal = document.createElement('div');
    loadingModal.className = 'modal active';
    loadingModal.innerHTML = `
        <div class="modal-content small">
            <div class="modal-body" style="text-align: center; padding: 60px 40px;">
                <div class="spinner-large"></div>
                <h3 style="margin-top: 24px;">Analyse en cours...</h3>
                <p style="color: var(--text-secondary);">${token.name} (${token.symbol})</p>
            </div>
        </div>
    `;
    document.body.appendChild(loadingModal);
    
    try {
        const response = await fetch(`${API_URL}/token/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                address: token.address,
                chain: token.chain
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.body.removeChild(loadingModal);
            openModal(data.token);
        } else {
            alert('Erreur: ' + data.error);
        }
    } catch (error) {
        alert('Erreur lors de l\'analyse');
        console.error(error);
    } finally {
        if (document.body.contains(loadingModal)) {
            document.body.removeChild(loadingModal);
        }
    }
}

function closeSearchResultsModal() {
    const modal = document.getElementById('searchResultsModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// ==================== AUTHENTIFICATION ====================

async function checkAuth() {
    try {
        const response = await fetch(`${API_URL}/auth/me`, {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            updateUI(true);
            await loadFavorites();
            
            if (data.user.is_admin) {
                const adminBtn = document.createElement('button');
                adminBtn.className = 'btn btn-secondary';
                adminBtn.innerHTML = '🛡️ Admin';
                adminBtn.onclick = () => window.location.href = '/admin';
                document.getElementById('userSection').querySelector('.user-menu').prepend(adminBtn);
            }
        } else {
            updateUI(false);
        }
    } catch (error) {
        updateUI(false);
    }
}

function updateUI(isLoggedIn) {
    document.getElementById('userSection').style.display = isLoggedIn ? 'flex' : 'none';
    document.getElementById('guestSection').style.display = isLoggedIn ? 'none' : 'flex';
}

function showAuthModal(tab) {
    document.getElementById('authModal').classList.add('active');
    if (tab === 'register') {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === 'register');
        });
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === 'registerTab');
        });
    }
}

function closeAuthModal() {
    document.getElementById('authModal').classList.remove('active');
    document.getElementById('authAlert').innerHTML = '';
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(tab + 'Tab').classList.add('active');
            document.getElementById('authAlert').innerHTML = '';
        });
    });
});

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (data.success) {
            currentUser = data.user;
            updateUI(true);
            closeAuthModal();
            await loadFavorites();
            window.location.reload();
        } else {
            document.getElementById('authAlert').innerHTML = 
                `<div class="alert error">❌ ${data.error}</div>`;
        }
    } catch (error) {
        document.getElementById('authAlert').innerHTML = 
            `<div class="alert error">❌ Erreur de connexion</div>`;
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;

    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (data.success) {
            currentUser = data.user;
            updateUI(true);
            closeAuthModal();
        } else {
            document.getElementById('authAlert').innerHTML = 
                `<div class="alert error">❌ ${data.error}</div>`;
        }
    } catch (error) {
        document.getElementById('authAlert').innerHTML = 
            `<div class="alert error">❌ Erreur lors de l'inscription</div>`;
    }
}

async function logout() {
    try {
        await fetch(`${API_URL}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        currentUser = null;
        userFavorites.clear();
        updateUI(false);
        window.location.reload();
    } catch (error) {
        console.error('Erreur déconnexion:', error);
    }
}

// ==================== FAVORIS ====================

async function loadFavorites() {
    if (!currentUser) return;

    try {
        const response = await fetch(`${API_URL}/favorites`, {
            credentials: 'include'
        });
        const data = await response.json();

        if (data.success) {
            userFavorites.clear();
            data.favorites.forEach(fav => {
                userFavorites.add(`${fav.token_address}-${fav.token_chain}`);
            });
        }
    } catch (error) {
        console.error('Erreur chargement favoris:', error);
    }
}

async function toggleFavorite(token, event) {
    event.stopPropagation();

    if (!currentUser) {
        alert('Connexion requise pour ajouter aux favoris');
        showAuthModal('login');
        return;
    }

    const key = `${token.address}-${token.chain}`;
    const isFavorite = userFavorites.has(key);

    try {
        const endpoint = isFavorite ? '/favorites/remove' : '/favorites/add';
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                token_address: token.address,
                token_chain: token.chain,
                token_data: token
            })
        });

        const data = await response.json();

        if (data.success) {
            if (isFavorite) {
                userFavorites.delete(key);
            } else {
                userFavorites.add(key);
            }
            displayTokens(allTokens);
        }
    } catch (error) {
        console.error('Erreur favori:', error);
    }
}

// ==================== SCAN ====================

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('startScanBtn').addEventListener('click', async () => {
        await startNewScan();
    });

    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentView = btn.dataset.view;
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const grid = document.getElementById('tokensGrid');
            if (currentView === 'list') {
                grid.classList.add('list-view');
            } else {
                grid.classList.remove('list-view');
            }
        });
    });

    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterTokens(e.target.value);
        });
    }

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            displayTokens(allTokens);
        });
    });
});

async function startNewScan() {
    const btn = document.getElementById('startScanBtn');
    
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Scan en cours...';

    const progressSection = document.getElementById('progressSection');
    progressSection.classList.add('active');

    try {
        const response = await fetch(`${API_URL}/scan/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ 
                max_tokens: 10,
                nitter_url: 'http://192.168.1.19:8080'
            })
        });

        const data = await response.json();

        if (data.success) {
            startProgressTracking();
        } else {
            alert('Erreur: ' + data.error);
            btn.disabled = false;
            btn.innerHTML = '▶️ Nouveau Scan';
        }
    } catch (error) {
        alert('Erreur de connexion au serveur');
        btn.disabled = false;
        btn.innerHTML = '▶️ Nouveau Scan';
    }
}

function startProgressTracking() {
    scanInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/scan/progress`);
            const data = await response.json();

            if (data.in_progress) {
                const percentage = Math.round(data.percentage);
                document.getElementById('progressFill').style.width = percentage + '%';
                document.getElementById('progressPercentage').textContent = percentage + '%';
                document.getElementById('progressText').textContent = 
                    `Analyse ${data.current} sur ${data.total} tokens...`;
            } else if (data.completed) {
                clearInterval(scanInterval);
                await loadResults();
                document.getElementById('progressSection').classList.remove('active');
                document.getElementById('startScanBtn').disabled = false;
                document.getElementById('startScanBtn').innerHTML = '▶️ Nouveau Scan';
            }
        } catch (error) {
            console.error('Erreur:', error);
        }
    }, 1000);
}

async function loadResults() {
    try {
        const response = await fetch(`${API_URL}/scan/results`);
        const data = await response.json();

        if (!data.success) return;

        allTokens = data.results;
        lastScanTimestamp = data.last_scan_timestamp;

        updateTimestampDisplay();

        document.getElementById('statsGrid').classList.add('active');
        document.getElementById('totalTokens').textContent = data.total_analyzed;
        document.getElementById('safeTokens').textContent = data.safe_count;
        document.getElementById('dangerTokens').textContent = data.dangerous_count;

        const avgRisk = data.results.reduce((sum, t) => sum + t.risk_score, 0) / data.results.length;
        document.getElementById('avgRisk').textContent = Math.round(avgRisk);

        displayTokens(allTokens);
    } catch (error) {
        console.error('Erreur:', error);
    }
}

function updateTimestampDisplay() {
    const timestampContainer = document.getElementById('timestampContainer');
    if (!timestampContainer || !lastScanTimestamp) return;

    const date = new Date(lastScanTimestamp);
    const timeStr = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const dateStr = date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });

    timestampContainer.innerHTML = `
        <div class="live-badge">
            <span class="live-dot"></span>
            <span>Analyse en temps réel</span>
        </div>
        <div class="timestamp-badge">
            <span>🕐</span>
            <span>Dernière analyse: ${timeStr} • ${dateStr}</span>
        </div>
        <button class="btn btn-secondary" onclick="startNewScan()" title="Actualiser l'analyse">
            🔄 Actualiser
        </button>
    `;
}

async function loadPreviousResults() {
    try {
        const response = await fetch(`${API_URL}/scan/results`);
        if (response.ok) {
            await loadResults();
        }
    } catch (error) {
        console.log('Aucun résultat précédent');
    }
}

function filterTokens(searchQuery) {
    if (!searchQuery) {
        displayTokens(allTokens);
        return;
    }

    const filtered = allTokens.filter(token => 
        token.address.toLowerCase().includes(searchQuery.toLowerCase()) ||
        token.chain.toLowerCase().includes(searchQuery.toLowerCase())
    );

    displayTokens(filtered);
}

// ==================== AFFICHAGE DES TOKENS ====================

function displayTokens(tokens) {
    const grid = document.getElementById('tokensGrid');
    grid.innerHTML = '';

    const filtered = tokens.filter(token => {
        if (currentFilter === 'all') return true;
        if (currentFilter === 'safe') return token.risk_score < 50;
        if (currentFilter === 'danger') return token.risk_score >= 50;
        if (currentFilter === 'pump_dump') return token.is_pump_dump_suspect;
    });

    if (filtered.length === 0) {
        grid.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><h3 class="empty-title">Aucun token trouvé</h3><p class="empty-text">Essayez un autre filtre</p></div>';
        return;
    }

    filtered.forEach(token => {
        const card = createTokenCard(token);
        grid.appendChild(card);
    });
}

function getPumpDumpBadge(pumpDumpRisk, pumpDumpScore) {
    const badges = {
        'CRITICAL': { emoji: '🚨', text: 'PUMP CRITIQUE', class: 'pump-critical' },
        'HIGH': { emoji: '⚠️', text: 'PUMP HIGH', class: 'pump-high' },
        'MEDIUM': { emoji: '⚡', text: 'PUMP MODÉRÉ', class: 'pump-medium' },
        'LOW': { emoji: '💨', text: 'PUMP FAIBLE', class: 'pump-low' },
        'SAFE': { emoji: '✅', text: 'SAFE', class: 'pump-safe' },
        'UNKNOWN': { emoji: '❓', text: 'INCONNU', class: 'pump-unknown' }
    };

    return badges[pumpDumpRisk] || badges['UNKNOWN'];
}

// 🆕 Badge RSI
function getRSIBadge(rsiSignal, rsiValue) {
    const badges = {
        'SURACHETÉ': { emoji: '🔥', class: 'rsi-overbought', color: 'var(--accent-red)' },
        'HAUSSIER': { emoji: '📈', class: 'rsi-bullish', color: 'var(--accent-green)' },
        'NEUTRE': { emoji: '➖', class: 'rsi-neutral', color: 'var(--text-secondary)' },
        'SURVENDU': { emoji: '❄️', class: 'rsi-oversold', color: 'var(--accent-blue)' }
    };
    
    return badges[rsiSignal] || badges['NEUTRE'];
}

function createTokenCard(token) {
    const card = document.createElement('div');
    let riskClass = 'safe';
    if (token.risk_score >= 50) riskClass = 'danger';
    else if (token.risk_score >= 20) riskClass = 'warning';

    card.className = `token-card ${riskClass}`;
    
    const shortAddr = token.address.substring(0, 8) + '...' + token.address.substring(token.address.length - 6);
    const key = `${token.address}-${token.chain}`;
    const isFavorite = userFavorites.has(key);

    const iconHtml = token.icon 
        ? `<div class="token-icon"><img src="${token.icon}" alt="${token.chain}" onerror="this.parentElement.innerHTML='<span class=\\'token-icon-placeholder\\'>🪙</span>'"></div>`
        : `<div class="token-icon"><span class="token-icon-placeholder">🪙</span></div>`;

    const circumference = 2 * Math.PI * 24;
    const offset = circumference - (token.risk_score / 100) * circumference;

    const pumpDumpBadge = getPumpDumpBadge(token.pump_dump_risk, token.pump_dump_score);
    const showPumpDumpBadge = token.pump_dump_score >= 30;
    
    // 🆕 RSI Badge
    const rsiBadge = getRSIBadge(token.rsi_signal, token.rsi_value);

    card.innerHTML = `
        <div class="token-header">
            <div class="token-address-section">
                ${iconHtml}
                <div class="token-info">
                    <div class="token-address">${shortAddr}</div>
                    <span class="chain-badge">${token.chain}</span>
                    ${showPumpDumpBadge ? `<span class="pump-badge ${pumpDumpBadge.class}" title="Score Pump & Dump: ${token.pump_dump_score}/100">
                        ${pumpDumpBadge.emoji} ${pumpDumpBadge.text}
                    </span>` : ''}
                    ${token.rsi_value ? `<span class="rsi-badge ${rsiBadge.class}" style="background: rgba(${rsiBadge.color === 'var(--accent-red)' ? '244, 67, 54' : rsiBadge.color === 'var(--accent-green)' ? '76, 175, 80' : '74, 144, 226'}, 0.15); border-color: ${rsiBadge.color}; color: ${rsiBadge.color};" title="RSI: ${token.rsi_value}">
                        ${rsiBadge.emoji} RSI ${token.rsi_value}
                    </span>` : ''}
                </div>
            </div>
            <div class="token-actions">
                <button class="btn-icon ${isFavorite ? 'active' : ''}" title="${isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}">
                    ${isFavorite ? '⭐' : '☆'}
                </button>
                <div class="risk-circle">
                    <svg width="60" height="60">
                        <circle class="risk-circle-bg" cx="30" cy="30" r="24"></circle>
                        <circle class="risk-circle-progress ${riskClass}" 
                                cx="30" cy="30" r="24"
                                stroke-dasharray="${circumference}"
                                stroke-dashoffset="${offset}"></circle>
                    </svg>
                    <div class="risk-circle-text">${token.risk_score}</div>
                </div>
            </div>
        </div>
        <div class="token-metrics">
            <div class="metric">
                <div class="metric-label">💧 Liquidité</div>
                <div class="metric-value">$${formatNumber(token.market.liquidity_usd || 0)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">📊 Volume 24h</div>
                <div class="metric-value">$${formatNumber(token.market.volume_24h || 0)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">💰 Market Cap</div>
                <div class="metric-value">$${formatNumber(token.market.market_cap || 0)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">🐦 Score Social</div>
                <div class="metric-value">${token.social_score || 0}/100</div>
            </div>
        </div>
    `;

    const favoriteBtn = card.querySelector('.btn-icon');
    favoriteBtn.addEventListener('click', (e) => toggleFavorite(token, e));

    card.addEventListener('click', (e) => {
        if (!e.target.closest('.btn-icon')) {
            openModal(token);
        }
    });

    return card;
}

// ==================== MODAL DÉTAILS (SUITE DANS LE PROCHAIN MESSAGE) ====================

function formatNumber(num) {
    if (num >= 1000000000) return (num / 1000000000).toFixed(2) + 'B';
    if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(2) + 'K';
    return num.toFixed(2);
}

function showFavorites() {
    window.location.href = '/favorites';
}

function showProfile() {
    alert('Page profil à venir !');
}

// ==================== MODAL DÉTAILS COMPLET ====================

function openModal(token) {
    const modal = document.getElementById('tokenModal');
    const modalBody = document.getElementById('modalBody');

    document.getElementById('modalAddress').textContent = token.address;
    document.getElementById('modalChain').textContent = token.chain;

    let riskClass = 'safe';
    let riskLabel = 'Sûr';
    if (token.risk_score >= 50) {
        riskClass = 'danger';
        riskLabel = 'Dangereux';
    } else if (token.risk_score >= 20) {
        riskClass = 'warning';
        riskLabel = 'Modéré';
    }

    const iconHtml = token.icon 
        ? `<img src="${token.icon}" alt="${token.chain}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid var(--border-color);" onerror="this.style.display='none'">`
        : '';

    // Pump & Dump Badge
    const pumpDumpBadge = getPumpDumpBadge(token.pump_dump_risk, token.pump_dump_score);
    
    // 🆕 RSI Badge
    const rsiBadge = getRSIBadge(token.rsi_signal, token.rsi_value);
    
    // 🆕 SECTION RSI COMPLÈTE
    const rsiSection = token.rsi_value ? `
        <div class="detail-section" style="background: linear-gradient(135deg, rgba(74, 144, 226, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%); border: 2px solid rgba(74, 144, 226, 0.3); border-radius: 16px; padding: 24px;">
            <div class="detail-section-title" style="color: var(--accent-blue);">📊 Analyse RSI (Relative Strength Index)</div>
            
            <div style="display: grid; grid-template-columns: auto 1fr; gap: 24px; align-items: center; margin-bottom: 20px;">
                <div style="width: 120px; height: 120px; border-radius: 50%; background: conic-gradient(
                    ${token.rsi_value >= 70 ? 'var(--accent-red)' : token.rsi_value >= 50 ? 'var(--accent-green)' : token.rsi_value >= 30 ? 'var(--accent-yellow)' : 'var(--accent-blue)'} ${token.rsi_value * 3.6}deg,
                    var(--bg-secondary) ${token.rsi_value * 3.6}deg
                ); display: flex; align-items: center; justify-content: center; position: relative; border: 4px solid var(--border-color);">
                    <div style="width: 90px; height: 90px; border-radius: 50%; background: var(--bg-card); display: flex; flex-direction: column; align-items: center; justify-content: center;">
                        <div style="font-size: 32px; font-weight: 900;">${token.rsi_value}</div>
                        <div style="font-size: 12px; color: var(--text-secondary);">RSI</div>
                    </div>
                </div>
                
                <div>
                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                        <span style="font-size: 32px;">${rsiBadge.emoji}</span>
                        <div>
                            <div style="font-size: 24px; font-weight: 700; color: ${rsiBadge.color};">${token.rsi_signal}</div>
                            <div style="font-size: 14px; color: var(--text-secondary);">${token.rsi_interpretation}</div>
                        </div>
                    </div>
                    
                    <div style="background: var(--bg-secondary); padding: 12px; border-radius: 8px; margin-top: 12px;">
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">Échelle RSI</div>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <div style="flex: 1; background: linear-gradient(90deg, var(--accent-blue) 0%, var(--accent-yellow) 50%, var(--accent-red) 100%); height: 8px; border-radius: 4px; position: relative;">
                                <div style="position: absolute; left: ${token.rsi_value}%; top: -2px; width: 4px; height: 12px; background: white; border: 2px solid var(--bg-primary); border-radius: 2px; transform: translateX(-50%);"></div>
                            </div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-secondary); margin-top: 4px;">
                            <span>0 (Survendu)</span>
                            <span>30</span>
                            <span>50</span>
                            <span>70</span>
                            <span>100 (Suracheté)</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div style="background: var(--bg-secondary); padding: 16px; border-radius: 12px; border-left: 4px solid ${rsiBadge.color};">
                <div style="font-weight: 600; margin-bottom: 8px;">💡 Interprétation Trading</div>
                <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.6;">
                    ${token.rsi_value >= 70 ? '⚠️ Le token est en zone de SURACHETÉ. Risque élevé de correction ou dump imminent. Prudence recommandée.' :
                      token.rsi_value >= 50 ? '✅ Momentum haussier détecté. Le prix a une tendance positive, mais restez vigilant.' :
                      token.rsi_value >= 30 ? '➖ Zone neutre. Pas de signal clair de direction. Attendre des confirmations.' :
                      '💎 Zone de SURVENDU. Potentiel rebond technique possible, mais vérifier les autres indicateurs.'}
                </div>
            </div>
        </div>
    ` : '';

    // 🆕 SECTION FIBONACCI COMPLÈTE
    const fibonacciSection = token.fibonacci_levels && Object.keys(token.fibonacci_levels).length > 0 ? `
        <div class="detail-section" style="background: linear-gradient(135deg, rgba(255, 193, 7, 0.05) 0%, rgba(255, 152, 0, 0.05) 100%); border: 2px solid rgba(255, 193, 7, 0.3); border-radius: 16px; padding: 24px;">
            <div class="detail-section-title" style="color: var(--accent-yellow);">📐 Niveaux de Fibonacci</div>
            
            <div style="margin-bottom: 20px;">
                <div style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">Position actuelle: ${token.fibonacci_position}</div>
                <div style="font-size: 13px; color: var(--text-secondary);">${token.fibonacci_percentage}% entre le low et high 24h</div>
            </div>
            
            <div style="background: var(--bg-secondary); padding: 20px; border-radius: 12px; position: relative;">
                <div style="height: 300px; position: relative; background: linear-gradient(180deg, 
                    rgba(244, 67, 54, 0.1) 0%,
                    rgba(255, 152, 0, 0.1) 30%,
                    rgba(255, 193, 7, 0.1) 50%,
                    rgba(76, 175, 80, 0.1) 70%,
                    rgba(76, 175, 80, 0.15) 100%
                ); border-radius: 8px; border: 1px solid var(--border-color);">
                    ${Object.entries(token.fibonacci_levels).reverse().map(([level, price], index) => {
                        const position = 100 - (parseFloat(level) / 100 * 100);
                        const isCurrentPrice = Math.abs(parseFloat(level) - token.fibonacci_percentage) < 5;
                        return `
                            <div style="position: absolute; left: 0; right: 0; top: ${position}%; transform: translateY(-50%); display: flex; align-items: center;">
                                <div style="flex: 1; height: ${isCurrentPrice ? '3px' : '1px'}; background: ${isCurrentPrice ? 'white' : 'rgba(255, 255, 255, 0.3)'}; position: relative;">
                                    ${isCurrentPrice ? '<div style="position: absolute; right: 0; top: 50%; transform: translateY(-50%); width: 12px; height: 12px; border-radius: 50%; background: var(--accent-green); border: 3px solid var(--bg-primary); box-shadow: 0 0 10px var(--accent-green);"></div>' : ''}
                                </div>
                                <div style="margin-left: 12px; min-width: 120px; text-align: right;">
                                    <div style="font-size: ${isCurrentPrice ? '14px' : '12px'}; font-weight: ${isCurrentPrice ? '700' : '500'}; color: ${isCurrentPrice ? 'var(--accent-green)' : 'var(--text-secondary)'};">
                                        ${level} ${isCurrentPrice ? '← PRIX' : ''}
                                    </div>
                                    <div style="font-size: 11px; color: var(--text-secondary);">$${price.toFixed(8)}</div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 20px;">
                ${Object.entries(token.fibonacci_levels).map(([level, price]) => `
                    <div style="background: var(--bg-card); padding: 12px; border-radius: 8px; border: 1px solid var(--border-color);">
                        <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">Niveau ${level}</div>
                        <div style="font-size: 14px; font-weight: 600; font-family: monospace;">$${price.toFixed(8)}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    ` : '';

    // SECTION PUMP & DUMP
    const pumpDumpSection = token.pump_dump_score > 0 ? `
        <div class="detail-section pump-dump-section">
            <div class="detail-section-title">🚨 Analyse Pump & Dump ${token.token_age_hours !== 'N/A' ? `<span style="font-size: 14px; font-weight: normal; color: var(--text-secondary);">(Token de ${token.token_age_hours}h)</span>` : ''}</div>
            
            <div class="pump-dump-score-container">
                <div class="pump-score-circle ${pumpDumpBadge.class}">
                    <div class="pump-score-value">${token.pump_dump_score}</div>
                    <div class="pump-score-label">/100</div>
                </div>
                <div class="pump-risk-badge ${pumpDumpBadge.class}">
                    <span class="pump-risk-emoji">${pumpDumpBadge.emoji}</span>
                    <span class="pump-risk-text">${pumpDumpBadge.text}</span>
                    <div class="pump-risk-subtitle">Niveau de risque Pump & Dump</div>
                </div>
            </div>

            ${token.pump_dump_warnings && token.pump_dump_warnings.length > 0 ? `
                <div class="pump-warnings-container">
                    <h4 style="font-size: 16px; margin-bottom: 12px; color: var(--accent-red);">
                        ⚠️ Signaux suspects détectés (${token.pump_dump_warnings.length})
                    </h4>
                    <div class="warning-list">
                        ${token.pump_dump_warnings.map(w => `
                            <div class="warning-item pump-warning">
                                <span class="warning-icon">🚨</span>
                                <span>${w}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}

            <div class="pump-indicators-grid">
                <h4 style="font-size: 16px; margin-bottom: 16px; grid-column: span 2;">📊 Indicateurs détaillés</h4>
                ${token.pump_dump_indicators ? Object.entries({
                    volume_spike: '📈 Volume Spike',
                    price_spike: '💸 Price Spike',
                    holder_concentration: '👥 Concentration',
                    low_liquidity: '💧 Liquidité faible',
                    new_token: '🆕 Token récent'
                }).map(([key, label]) => {
                    if (token.pump_dump_indicators[key] !== undefined) {
                        const value = token.pump_dump_indicators[key];
                        return `
                            <div class="pump-indicator-item">
                                <div class="pump-indicator-label">${label}</div>
                                <div class="pump-indicator-bar">
                                    <div class="pump-indicator-fill" style="width: ${value}%; background: ${value > 75 ? 'var(--accent-red)' : value > 50 ? 'var(--accent-orange)' : 'var(--accent-green)'}"></div>
                                </div>
                                <div class="pump-indicator-value">${value}/100</div>
                            </div>
                        `;
                    }
                    return '';
                }).join('') : ''}
            </div>
        </div>
    ` : '';

    // 🆕 SECTION TOP 5 HOLDERS
    const topHoldersSection = token.security && token.security.top_holders && token.security.top_holders.length > 0 ? `
        <div class="detail-section">
            <div class="detail-section-title">👥 Top 5 Holders</div>
            <div style="background: var(--bg-secondary); padding: 16px; border-radius: 12px;">
                ${token.security.top_holders.map(holder => `
                    <div style="display: flex; align-items: center; gap: 16px; padding: 12px; background: var(--bg-card); border-radius: 8px; margin-bottom: 12px; border: 1px solid var(--border-color);">
                        <div style="width: 40px; height: 40px; border-radius: 50%; background: var(--gradient-primary); display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 700; flex-shrink: 0;">
                            #${holder.rank}
                        </div>
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-family: 'Courier New', monospace; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 4px;">
                                ${holder.address}
                            </div>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                                ${holder.is_contract ? '<span style="font-size: 10px; padding: 2px 8px; background: rgba(74, 144, 226, 0.2); border: 1px solid var(--accent-blue); border-radius: 4px; color: var(--accent-blue);">📜 Contract</span>' : ''}
                                ${holder.is_locked ? '<span style="font-size: 10px; padding: 2px 8px; background: rgba(76, 175, 80, 0.2); border: 1px solid var(--accent-green); border-radius: 4px; color: var(--accent-green);">🔒 Locked</span>' : ''}
                            </div>
                        </div>
                        <div style="text-align: right; flex-shrink: 0;">
                            <div style="font-size: 20px; font-weight: 700; color: ${holder.percent > 20 ? 'var(--accent-red)' : holder.percent > 10 ? 'var(--accent-orange)' : 'var(--accent-green)'};">
                                ${holder.percent}%
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary);">
                                ${formatNumber(holder.balance)} tokens
                            </div>
                        </div>
                    </div>
                `).join('')}
                
                <div style="margin-top: 16px; padding: 12px; background: var(--bg-card); border-radius: 8px; border-left: 4px solid var(--accent-blue);">
                    <div style="font-size: 12px; color: var(--text-secondary);">
                        💡 <strong>Concentration totale Top 5:</strong> ${token.security.top_holders.reduce((sum, h) => sum + h.percent, 0).toFixed(2)}%
                    </div>
                </div>
            </div>
        </div>
    ` : '';

    modalBody.innerHTML = `
        ${iconHtml ? `<div style="text-align: center; margin-bottom: 24px;">${iconHtml}</div>` : ''}
        
        <div class="detail-section">
            <div class="detail-section-title">🎯 Score de Risque</div>
            <div class="detail-grid">
                <div class="detail-item" style="grid-column: span 2;">
                    <div class="detail-label">Score Total</div>
                    <div class="detail-value">
                        <span class="risk-badge ${riskClass}" style="font-size: 24px;">
                            ${token.risk_score}/100 - ${riskLabel}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        ${rsiSection}
        ${fibonacciSection}
        ${pumpDumpSection}

        <div class="detail-section">
            <div class="detail-section-title">💹 Données de Marché</div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Prix USD</div>
                    <div class="detail-value">$${token.market.price_usd ? token.market.price_usd.toFixed(8) : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Variation 24h</div>
                    <div class="detail-value" style="color: ${token.market.price_change_24h >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">
                        ${token.market.price_change_24h ? token.market.price_change_24h.toFixed(2) : '0'}%
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Liquidité USD</div>
                    <div class="detail-value">$${formatNumber(token.market.liquidity_usd || 0)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Volume 24h</div>
                    <div class="detail-value">$${formatNumber(token.market.volume_24h || 0)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Market Cap</div>
                    <div class="detail-value">$${formatNumber(token.market.market_cap || 0)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Transactions 24h</div>
                    <div class="detail-value">
                        <span style="color: var(--accent-green);">↑${token.market.txns_24h_buys || 0}</span> / 
                        <span style="color: var(--accent-red);">↓${token.market.txns_24h_sells || 0}</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="detail-section">
            <div class="detail-section-title">🔒 Analyse de Sécurité</div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Honeypot</div>
                    <div class="detail-value" style="color: ${token.security.is_honeypot ? 'var(--accent-red)' : 'var(--accent-green)'}">
                        ${token.security.is_honeypot ? '⚠️ OUI' : '✅ NON'}
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Code Open Source</div>
                    <div class="detail-value" style="color: ${token.security.is_open_source ? 'var(--accent-green)' : 'var(--accent-orange)'}">
                        ${token.security.is_open_source ? '✅ OUI' : '⚠️ NON'}
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Mintable</div>
                    <div class="detail-value" style="color: ${token.security.is_mintable ? 'var(--accent-orange)' : 'var(--accent-green)'}">
                        ${token.security.is_mintable ? '⚠️ OUI' : '✅ NON'}
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Propriétaire Caché</div>
                    <div class="detail-value" style="color: ${token.security.hidden_owner ? 'var(--accent-red)' : 'var(--accent-green)'}">
                        ${token.security.hidden_owner ? '⚠️ OUI' : '✅ NON'}
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Taxe Achat</div>
                    <div class="detail-value" style="color: ${token.security.buy_tax > 10 ? 'var(--accent-red)' : 'var(--accent-green)'}">
                        ${token.security.buy_tax || 0}%
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Taxe Vente</div>
                    <div class="detail-value" style="color: ${token.security.sell_tax > 10 ? 'var(--accent-red)' : 'var(--accent-green)'}">
                        ${token.security.sell_tax || 0}%
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Holders</div>
                    <div class="detail-value">${token.security.holder_count || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Destructible</div>
                    <div class="detail-value" style="color: ${token.security.selfdestruct ? 'var(--accent-red)' : 'var(--accent-green)'}">
                        ${token.security.selfdestruct ? '⚠️ OUI' : '✅ NON'}
                    </div>
                </div>
            </div>
        </div>

        ${topHoldersSection}

        ${token.warnings && token.warnings.length > 0 ? `
        <div class="detail-section">
            <div class="detail-section-title">⚠️ Alertes Sécurité (${token.warnings.length})</div>
            <div class="warning-list">
                ${token.warnings.map(w => `
                    <div class="warning-item">
                        <span class="warning-icon">⚠️</span>
                        <span>${w}</span>
                    </div>
                `).join('')}
            </div>
        </div>
        ` : ''}

        ${token.twitter ? `
        <div class="detail-section">
            <div class="detail-section-title">🐦 Analyse Twitter</div>
            <div class="twitter-section">
                <div class="detail-item" style="margin-bottom: 16px;">
                    <div class="detail-label">Compte Twitter</div>
                    <div class="detail-value">
                        <a href="${token.twitter}" target="_blank" style="color: var(--accent-blue); text-decoration: none;">
                            ${token.twitter}
                        </a>
                    </div>
                </div>
                
                ${token.social_score > 0 ? `
                <div class="detail-item" style="margin-bottom: 16px;">
                    <div class="detail-label">Score Social Global</div>
                    <div class="detail-value">
                        <span class="risk-badge ${token.social_score >= 60 ? 'safe' : token.social_score >= 30 ? 'warning' : 'danger'}">
                            ${token.social_score}/100
                        </span>
                    </div>
                </div>

                <div class="twitter-stats">
                    <div class="twitter-stat">
                        <div class="twitter-stat-value">${formatNumber(token.social_details.followers || 0)}</div>
                        <div class="twitter-stat-label">Followers</div>
                    </div>
                    <div class="twitter-stat">
                        <div class="twitter-stat-value">${formatNumber(token.social_details.following || 0)}</div>
                        <div class="twitter-stat-label">Following</div>
                    </div>
                    <div class="twitter-stat">
                        <div class="twitter-stat-value">${formatNumber(token.social_details.tweets || 0)}</div>
                        <div class="twitter-stat-label">Tweets</div>
                    </div>
                </div>

                <div class="detail-grid" style="margin-top: 16px;">
                    <div class="detail-item">
                        <div class="detail-label">Évaluation Followers</div>
                        <div class="detail-value">${token.social_details.followers_score || 'N/A'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Ratio F/F</div>
                        <div class="detail-value">${token.social_details.ratio_score || 'N/A'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Activité</div>
                        <div class="detail-value">${token.social_details.activity_score || 'N/A'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Vérifié</div>
                        <div class="detail-value">${token.social_details.verified || 'Non'}</div>
                    </div>
                </div>

                ${token.twitter_data && token.twitter_data.bio ? `
                <div class="detail-item" style="margin-top: 16px;">
                    <div class="detail-label">Bio</div>
                    <div class="detail-value" style="font-size: 14px; line-height: 1.6;">
                        ${token.twitter_data.bio}
                    </div>
                </div>
                ` : ''}
                ` : '<p style="color: var(--text-secondary);">Données Twitter non disponibles</p>'}
            </div>
        </div>
        ` : ''}

        ${token.description && token.description !== 'N/A' ? `
        <div class="detail-section">
            <div class="detail-section-title">📝 Description</div>
            <div class="detail-item">
                <div class="detail-value" style="font-size: 14px; line-height: 1.8;">
                    ${token.description}
                </div>
            </div>
        </div>
        ` : ''}

        <div class="detail-section">
            <div class="detail-section-title">🔗 Liens</div>
            <div class="detail-grid">
                ${token.url ? `
                <div class="detail-item">
                    <div class="detail-label">DexScreener</div>
                    <div class="detail-value">
                        <a href="${token.url}" target="_blank" style="color: var(--accent-blue); text-decoration: none;">
                            Voir sur DexScreener →
                        </a>
                    </div>
                </div>
                ` : ''}
                <div class="detail-item">
                    <div class="detail-label">Adresse Contrat</div>
                    <div class="detail-value" style="font-family: 'Courier New', monospace; font-size: 12px; word-break: break-all;">
                        ${token.address}
                    </div>
                </div>
            </div>
        </div>

        <div class="detail-section">
            <div class="detail-item">
                <div class="detail-label">Analysé le</div>
                <div class="detail-value" style="font-size: 14px;">
                    ${new Date(token.timestamp).toLocaleString('fr-FR')}
                </div>
            </div>
        </div>
    `;

    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('tokenModal').classList.remove('active');
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('tokenModal').addEventListener('click', (e) => {
        if (e.target.id === 'tokenModal') {
            closeModal();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            closeSearchResultsModal();
        }
    });
});