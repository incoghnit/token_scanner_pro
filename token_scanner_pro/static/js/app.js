// ==================== CONFIGURATION ====================
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
    initializeModals(); // 🔧 FIX: Initialiser les modals correctement
});

// 🔧 FIX: Fonction pour initialiser les modals
function initializeModals() {
    // Fermer modal en cliquant sur l'overlay
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Fermer modal avec bouton close
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const modal = btn.closest('.modal');
            if (modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Échap pour fermer
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.active').forEach(modal => {
                modal.classList.remove('active');
            });
        }
    });
}

// 🔧 FIX: Fonction closeModal améliorée
function closeModal(modalId) {
    const modal = modalId ? document.getElementById(modalId) : document.querySelector('.modal.active');
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
    closeModal('authModal');
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

    // View Switcher
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

    // Search
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterTokens(e.target.value);
        });
    }

    // Filtres
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
        ? `<img src="${token.icon}" alt="${token.chain}" class="token-icon" onerror="this.style.display='none'">`
        : `<div class="token-icon-placeholder">${token.chain[0].toUpperCase()}</div>`;

    const pumpBadge = getPumpDumpBadge(token.pump_dump_risk, token.pump_dump_score);

    card.innerHTML = `
        <div class="token-header">
            ${iconHtml}
            <div class="token-info">
                <div class="token-address">${shortAddr}</div>
                <span class="chain-badge">${token.chain.toUpperCase()}</span>
            </div>
            <button class="favorite-btn ${isFavorite ? 'active' : ''}" onclick="toggleFavorite(allTokens.find(t => t.address === '${token.address}'), event)">
                ${isFavorite ? '⭐' : '☆'}
            </button>
        </div>

        <div class="token-risk">
            <div class="risk-circle">
                <svg width="60" height="60">
                    <circle cx="30" cy="30" r="25" class="risk-circle-bg"/>
                    <circle cx="30" cy="30" r="25" class="risk-circle-progress ${riskClass}" 
                            style="stroke-dasharray: 157; stroke-dashoffset: ${157 - (token.risk_score / 100) * 157}"/>
                </svg>
                <div class="risk-circle-text">${token.risk_score}</div>
            </div>
            <div class="risk-info">
                <div class="risk-label">Score de Risque</div>
                <div class="risk-badge ${riskClass}">${token.risk_score < 30 ? 'Faible' : token.risk_score < 50 ? 'Modéré' : 'Élevé'}</div>
            </div>
        </div>

        ${token.is_pump_dump_suspect ? `
            <div class="pump-badge ${pumpBadge.class}">
                ${pumpBadge.emoji} ${pumpBadge.text} (${token.pump_dump_score}/100)
            </div>
        ` : ''}

        <div class="token-metrics">
            <div class="metric">
                <div class="metric-label">Prix USD</div>
                <div class="metric-value">${token.market.price_usd ? '$' + token.market.price_usd.toFixed(8) : 'N/A'}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Liquidité</div>
                <div class="metric-value">${token.market.liquidity_usd ? '$' + (token.market.liquidity_usd / 1000).toFixed(1) + 'K' : 'N/A'}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Volume 24h</div>
                <div class="metric-value">${token.market.volume_24h ? '$' + (token.market.volume_24h / 1000).toFixed(1) + 'K' : 'N/A'}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Var. 24h</div>
                <div class="metric-value" style="color: ${token.market.price_change_24h >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">
                    ${token.market.price_change_24h ? token.market.price_change_24h.toFixed(2) + '%' : 'N/A'}
                </div>
            </div>
        </div>
    `;

    card.onclick = () => openTokenModal(token);
    return card;
}

// 🔧 FIX: Fonction openTokenModal améliorée avec RSI, FIBO et Top 5 Holders
function openTokenModal(token) {
    const modal = document.getElementById('tokenModal');
    const modalBody = document.getElementById('modalBody');
    const modalAddress = document.getElementById('modalAddress');
    const modalChain = document.getElementById('modalChain');

    modalAddress.textContent = token.address;
    modalChain.textContent = token.chain.toUpperCase();
    modalChain.className = `chain-badge ${token.chain}`;

    let riskClass = 'safe';
    let riskLabel = 'Faible Risque';
    if (token.risk_score >= 50) {
        riskClass = 'danger';
        riskLabel = 'Risque Élevé';
    } else if (token.risk_score >= 20) {
        riskClass = 'warning';
        riskLabel = 'Risque Modéré';
    }

    const iconHtml = token.icon 
        ? `<img src="${token.icon}" alt="${token.chain}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid var(--border-color);" onerror="this.style.display='none'">`
        : '';

    const pumpBadge = getPumpDumpBadge(token.pump_dump_risk, token.pump_dump_score);

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

        ${token.is_pump_dump_suspect ? `
        <div class="detail-section">
            <div class="detail-section-title">🚨 Détection Pump & Dump</div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Score P&D</div>
                    <div class="detail-value">
                        <span class="pump-badge ${pumpBadge.class}" style="font-size: 18px;">
                            ${pumpBadge.emoji} ${token.pump_dump_score}/100
                        </span>
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Niveau de Risque</div>
                    <div class="detail-value">
                        <span class="pump-badge ${pumpBadge.class}">
                            ${pumpBadge.text}
                        </span>
                    </div>
                </div>
            </div>
        </div>
        ` : ''}

        <!-- 🆕 RSI & FIBONACCI SECTION -->
        <div class="detail-section">
            <div class="detail-section-title">📊 Indicateurs Techniques</div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">RSI (14)</div>
                    <div class="detail-value" style="font-size: 24px; font-weight: 700; color: ${
                        token.rsi_value < 30 ? 'var(--accent-green)' : 
                        token.rsi_value > 70 ? 'var(--accent-red)' : 
                        'var(--accent-orange)'
                    }">
                        ${token.rsi_value ? token.rsi_value.toFixed(1) : 'N/A'}
                    </div>
                    <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
                        ${token.rsi_signal || 'N/A'}
                        ${token.rsi_interpretation ? `<br>${token.rsi_interpretation}` : ''}
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Position Fibonacci</div>
                    <div class="detail-value" style="font-size: 24px; font-weight: 700;">
                        ${token.fibonacci_position ? token.fibonacci_position.toFixed(1) + '%' : 'N/A'}
                    </div>
                    <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
                        ${token.fibonacci_level || 'Niveau non défini'}
                    </div>
                </div>
                ${token.trading_score !== undefined ? `
                <div class="detail-item">
                    <div class="detail-label">Score Trading</div>
                    <div class="detail-value" style="font-size: 24px; font-weight: 700; color: ${
                        token.trading_score > 70 ? 'var(--accent-green)' : 
                        token.trading_score > 40 ? 'var(--accent-orange)' : 
                        'var(--accent-red)'
                    }">
                        ${token.trading_score}/100
                    </div>
                </div>
                ` : ''}
                ${token.trading_signal ? `
                <div class="detail-item">
                    <div class="detail-label">Signal Trading</div>
                    <div class="detail-value">
                        <span style="padding: 6px 12px; border-radius: 8px; font-weight: 700; background: ${
                            token.trading_signal === 'BUY' ? 'rgba(76, 175, 80, 0.2)' :
                            token.trading_signal === 'SELL' ? 'rgba(244, 67, 54, 0.2)' :
                            'rgba(255, 152, 0, 0.2)'
                        }; color: ${
                            token.trading_signal === 'BUY' ? 'var(--accent-green)' :
                            token.trading_signal === 'SELL' ? 'var(--accent-red)' :
                            'var(--accent-orange)'
                        }">
                            ${token.trading_signal === 'BUY' ? '💰 BUY' : 
                              token.trading_signal === 'SELL' ? '💸 SELL' : 
                              '⏸️ HOLD'}
                        </span>
                    </div>
                </div>
                ` : ''}
            </div>
        </div>

        <!-- 🆕 TOP 5 HOLDERS SECTION -->
        ${token.top_holders && token.top_holders.length > 0 ? `
        <div class="detail-section">
            <div class="detail-section-title">👥 Top 5 Holders</div>
            <div style="margin-top: 12px;">
                ${token.top_holders.slice(0, 5).map((holder, index) => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--bg-secondary); border-radius: 8px; margin-bottom: 8px; border: 1px solid var(--border-color);">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="font-size: 20px; font-weight: 700; color: var(--text-secondary);">
                                #${index + 1}
                            </div>
                            <div>
                                <div style="font-family: 'Courier New', monospace; font-size: 13px;">
                                    ${holder.address ? holder.address.substring(0, 10) + '...' + holder.address.substring(holder.address.length - 8) : 'N/A'}
                                </div>
                                ${holder.tag ? `<div style="font-size: 11px; color: var(--accent-blue);">${holder.tag}</div>` : ''}
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 18px; font-weight: 700; color: ${
                                holder.percentage > 20 ? 'var(--accent-red)' :
                                holder.percentage > 10 ? 'var(--accent-orange)' :
                                'var(--accent-green)'
                            }">
                                ${holder.percentage ? holder.percentage.toFixed(2) + '%' : 'N/A'}
                            </div>
                            ${holder.balance ? `<div style="font-size: 11px; color: var(--text-secondary);">${holder.balance.toLocaleString()} tokens</div>` : ''}
                        </div>
                    </div>
                `).join('')}
                <div style="margin-top: 12px; padding: 12px; background: ${
                    token.holder_concentration > 50 ? 'rgba(244, 67, 54, 0.1)' :
                    token.holder_concentration > 30 ? 'rgba(255, 152, 0, 0.1)' :
                    'rgba(76, 175, 80, 0.1)'
                }; border-radius: 8px; border: 1px solid ${
                    token.holder_concentration > 50 ? 'var(--accent-red)' :
                    token.holder_concentration > 30 ? 'var(--accent-orange)' :
                    'var(--accent-green)'
                }">
                    <strong>Concentration Top 5:</strong> 
                    <span style="font-size: 18px; font-weight: 700; color: ${
                        token.holder_concentration > 50 ? 'var(--accent-red)' :
                        token.holder_concentration > 30 ? 'var(--accent-orange)' :
                        'var(--accent-green)'
                    }">
                        ${token.holder_concentration ? token.holder_concentration.toFixed(1) + '%' : 'N/A'}
                    </span>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                        ${token.holder_concentration > 50 ? '⚠️ Concentration très élevée - Risque de manipulation' :
                          token.holder_concentration > 30 ? '⚡ Concentration moyenne - Surveiller' :
                          '✅ Distribution saine'}
                    </div>
                </div>
            </div>
        </div>
        ` : ''}

        <div class="detail-section">
            <div class="detail-section-title">💹 Données de Marché</div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Prix USD</div>
                    <div class="detail-value">${token.market.price_usd ? token.market.price_usd.toFixed(8) : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Variation 24h</div>
                    <div class="detail-value" style="color: ${token.market.price_change_24h >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">
                        ${token.market.price_change_24h ? token.market.price_change_24h.toFixed(2) + '%' : 'N/A'}
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Variation 1h</div>
                    <div class="detail-value" style="color: ${token.market.price_change_1h >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">
                        ${token.market.price_change_1h ? token.market.price_change_1h.toFixed(2) + '%' : 'N/A'}
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Market Cap</div>
                    <div class="detail-value">${token.market.market_cap ? '$' + (token.market.market_cap / 1000000).toFixed(2) + 'M' : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Liquidité</div>
                    <div class="detail-value">${token.market.liquidity_usd ? '$' + token.market.liquidity_usd.toLocaleString() : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Volume 24h</div>
                    <div class="detail-value">${token.market.volume_24h ? '$' + token.market.volume_24h.toLocaleString() : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Ratio Vol/Liq</div>
                    <div class="detail-value">${token.market.liquidity_usd && token.market.volume_24h ? (token.market.volume_24h / token.market.liquidity_usd).toFixed(2) : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">FDV</div>
                    <div class="detail-value">${token.market.fdv ? '$' + (token.market.fdv / 1000000).toFixed(2) + 'M' : 'N/A'}</div>
                </div>
            </div>
        </div>

        <div class="detail-section">
            <div class="detail-section-title">🔒 Sécurité</div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Honeypot</div>
                    <div class="detail-value">${token.security.is_honeypot ? '⚠️ OUI' : '✅ NON'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Code Vérifié</div>
                    <div class="detail-value">${token.security.is_open_source ? '✅ OUI' : '⚠️ NON'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Mintable</div>
                    <div class="detail-value">${token.security.is_mintable ? '⚠️ OUI' : '✅ NON'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Owner Caché</div>
                    <div class="detail-value">${token.security.hidden_owner ? '⚠️ OUI' : '✅ NON'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Tax Achat</div>
                    <div class="detail-value">${token.security.buy_tax ? token.security.buy_tax + '%' : '0%'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Tax Vente</div>
                    <div class="detail-value">${token.security.sell_tax ? token.security.sell_tax + '%' : '0%'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Holders</div>
                    <div class="detail-value">${token.security.holder_count ? token.security.holder_count.toLocaleString() : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Âge du Token</div>
                    <div class="detail-value">${token.age_info ? token.age_info : 'N/A'}</div>
                </div>
            </div>
        </div>

        ${token.twitter_data ? `
        <div class="detail-section">
            <div class="detail-section-title">🐦 Données Twitter</div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Username</div>
                    <div class="detail-value">@${token.twitter_data.username || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Followers</div>
                    <div class="detail-value">${token.twitter_data.followers ? token.twitter_data.followers.toLocaleString() : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Following</div>
                    <div class="detail-value">${token.twitter_data.following ? token.twitter_data.following.toLocaleString() : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Tweets</div>
                    <div class="detail-value">${token.twitter_data.tweets ? token.twitter_data.tweets.toLocaleString() : 'N/A'}</div>
                </div>
                ${token.twitter_data.score !== undefined ? `
                <div class="detail-item">
                    <div class="detail-label">Score Social</div>
                    <div class="detail-value">${token.twitter_data.score}/100</div>
                </div>
                ` : ''}
            </div>
            ${token.twitter_data.bio ? `
            <div class="detail-item" style="margin-top: 16px;">
                <div class="detail-label">Bio</div>
                <div class="detail-value" style="font-size: 14px; line-height: 1.6;">
                    ${token.twitter_data.bio}
                </div>
            </div>
            ` : ''}
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
                        <a href="${token.url}" target="_blank" class="btn btn-primary btn-small">
                            Voir sur DexScreener 🔗
                        </a>
                    </div>
                </div>
                ` : ''}
                ${token.twitter ? `
                <div class="detail-item">
                    <div class="detail-label">Twitter</div>
                    <div class="detail-value">
                        <a href="${token.twitter}" target="_blank" class="btn btn-primary btn-small">
                            Voir Twitter 🐦
                        </a>
                    </div>
                </div>
                ` : ''}
            </div>
        </div>
    `;

    modal.classList.add('active');
}

function showFavorites() {
    window.location.href = '/favorites';
}

function showProfile() {
    alert('Profil utilisateur - À implémenter');
}