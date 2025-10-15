/* ==================== TOKEN SCANNER PRO - VERSION OPTIMISÉE ==================== */

const API_URL = window.location.origin + '/api';

let allTokens = [];
let currentFilter = 'all';
let currentView = 'grid';
let userFavorites = new Set();
let currentUser = null;
let lastScanTimestamp = null;

// ==================== AUTHENTICATION ====================

async function checkAuth() {
    try {
        const response = await fetch(`${API_URL}/auth/check`, {
            credentials: 'include'
        });
        const data = await response.json();

        if (data.authenticated) {
            currentUser = data.user;
            updateUI(true);
            await loadFavorites();
        } else {
            updateUI(false);
        }
    } catch (error) {
        console.error('Erreur auth:', error);
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
            await loadFavorites();
            updateUI(true);
            closeAuthModal();
            window.location.reload();
        } else {
            document.getElementById('authAlert').innerHTML = 
                `<div class="alert error">❌ ${data.error}</div>`;
        }
    } catch (error) {
        document.getElementById('authAlert').innerHTML = 
            `<div class="alert error">❌ Erreur lors de la connexion</div>`;
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
            window.location.reload();
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
    checkAuth();
    
    // 🔥 IMPORTANT : Charger les tokens en cache au démarrage
    loadPreviousResults();

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
    const progressSection = document.getElementById('progressSection');
    const tokensGrid = document.getElementById('tokensGrid');
    const startBtn = document.getElementById('startScanBtn');

    progressSection.style.display = 'block';
    tokensGrid.innerHTML = '<div class="skeleton skeleton-card"></div>'.repeat(6);
    startBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/scan/start`, {
            method: 'POST',
            credentials: 'include'
        });

        const data = await response.json();

        if (data.success) {
            pollProgress();
        } else {
            alert('Erreur: ' + data.error);
            progressSection.style.display = 'none';
            startBtn.disabled = false;
        }
    } catch (error) {
        console.error('Erreur scan:', error);
        progressSection.style.display = 'none';
        startBtn.disabled = false;
    }
}

async function pollProgress() {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/scan/progress`, {
                credentials: 'include'
            });
            const data = await response.json();

            if (data.success) {
                updateProgress(data.progress);

                if (data.progress.percentage >= 100) {
                    clearInterval(interval);
                    setTimeout(() => {
                        loadResults();
                        document.getElementById('progressSection').style.display = 'none';
                        document.getElementById('startScanBtn').disabled = false;
                    }, 500);
                }
            }
        } catch (error) {
            console.error('Erreur poll:', error);
            clearInterval(interval);
        }
    }, 2000);
}

function updateProgress(progress) {
    document.getElementById('progressFill').style.width = `${progress.percentage}%`;
    document.getElementById('progressPercentage').textContent = `${Math.round(progress.percentage)}%`;
    document.getElementById('progressText').textContent = progress.message || 'Scan en cours...';
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

    filtered.forEach((token, index) => {
        const card = createTokenCard(token);
        card.style.animationDelay = `${index * 0.05}s`;
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

// 🆕 ==================== CREATE TOKEN CARD - VERSION OPTIMISÉE ====================

function createTokenCard(token) {
    const card = document.createElement('div');
    let riskClass = 'safe';
    if (token.risk_score >= 50) riskClass = 'danger';
    else if (token.risk_score >= 20) riskClass = 'warning';

    card.className = `token-card ${riskClass}`;
    
    const shortAddr = token.address.substring(0, 6) + '...' + token.address.substring(token.address.length - 4);
    const key = `${token.address}-${token.chain}`;
    const isFavorite = userFavorites.has(key);

    const iconHtml = token.icon 
        ? `<img src="${token.icon}" alt="${token.chain}" class="token-icon" onerror="this.style.display='none'">`
        : `<div class="token-icon-placeholder">${token.chain[0].toUpperCase()}</div>`;

    const pumpBadge = getPumpDumpBadge(token.pump_dump_risk, token.pump_dump_score);

    card.innerHTML = `
        <div class="token-header">
            <div class="token-address-section">
                ${iconHtml}
                <div class="token-info">
                    <div class="token-address">${shortAddr}</div>
                    <span class="chain-badge">${token.chain.toUpperCase()}</span>
                </div>
            </div>
            <button class="favorite-btn ${isFavorite ? 'active' : ''}" onclick="toggleFavorite(allTokens.find(t => t.address === '${token.address}'), event)">
                ${isFavorite ? '⭐' : '☆'}
            </button>
        </div>

        <div class="pump-dump-section">
            <span class="pump-badge ${pumpBadge.class}">${pumpBadge.emoji} ${pumpBadge.text}</span>
            <span class="pump-score">${token.pump_dump_score}/100</span>
        </div>
        
        <!-- 🆕 AI ANALYSIS SECTION -->
        <div class="token-ai-section" id="ai-${token.address}">
            <span class="ai-mini-badge">🤖 ANALYSE IA</span>
            <div class="ai-loading">
                <div class="ai-spinner"></div>
                <span>Analyse en cours...</span>
            </div>
        </div>

        <div class="token-metrics">
            <div class="metric">
                <div class="metric-label">Risque</div>
                <div class="metric-value">${token.risk_score}/100</div>
            </div>
            <div class="metric">
                <div class="metric-label">Liquidité</div>
                <div class="metric-value">${token.market.liquidity ? '$' + (token.market.liquidity / 1000).toFixed(1) + 'K' : 'N/A'}</div>
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

    card.onclick = (e) => {
        if (!e.target.closest('.favorite-btn')) {
            openTokenModal(token);
        }
    };
    
    // 🆕 Charger l'analyse IA après le rendu avec un délai aléatoire
    setTimeout(() => loadAIAnalysisForToken(token), Math.random() * 1000 + 500);
    
    return card;
}

// 🆕 ==================== AI ANALYSIS - NOUVEAU ====================

async function loadAIAnalysisForToken(token) {
    const aiSection = document.getElementById(`ai-${token.address}`);
    if (!aiSection) return;

    try {
        const response = await fetch(`${API_URL}/ai/quick-analysis`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                token_address: token.address,
                token_chain: token.chain,
                risk_score: token.risk_score,
                pump_dump_score: token.pump_dump_score,
                market_data: token.market
            })
        });

        const data = await response.json();

        if (data.success && data.analysis) {
            const analysis = data.analysis;
            
            // Déterminer la classe de score
            let scoreClass = 'high';
            if (analysis.confidence < 60) scoreClass = 'low';
            else if (analysis.confidence < 80) scoreClass = 'medium';

            // Déterminer l'action avec emoji
            let actionEmoji = '🟡';
            let actionText = 'ATTENDRE';
            let actionClass = 'medium';
            
            if (analysis.action === 'BUY') {
                actionEmoji = '🟢';
                actionText = 'ACHETER';
                actionClass = 'high';
            } else if (analysis.action === 'SELL') {
                actionEmoji = '🔴';
                actionText = 'ÉVITER';
                actionClass = 'low';
            }

            aiSection.innerHTML = `
                <span class="ai-mini-badge">🤖 ANALYSE IA</span>
                <div class="ai-score">
                    <span class="ai-score-label">Confiance:</span>
                    <span class="ai-score-value ${scoreClass}">${analysis.confidence}%</span>
                </div>
                <div class="ai-score">
                    <span class="ai-score-label">Action:</span>
                    <span class="ai-score-value ${actionClass}">
                        ${actionEmoji} ${actionText}
                    </span>
                </div>
                ${analysis.recommendation ? 
                    `<div class="ai-recommendation">${analysis.recommendation}</div>` : ''}
            `;

            // Animation d'apparition
            aiSection.style.animation = 'fadeIn 0.5s ease-out';
        } else {
            // Fallback si pas d'analyse dispo
            aiSection.innerHTML = `
                <span class="ai-mini-badge">🤖 ANALYSE IA</span>
                <div class="ai-recommendation" style="color: var(--text-secondary);">
                    Non disponible
                </div>
            `;
        }
    } catch (error) {
        console.error('Erreur AI analysis:', error);
        aiSection.innerHTML = `
            <span class="ai-mini-badge">🤖 ANALYSE IA</span>
            <div class="ai-recommendation" style="color: var(--accent-red);">
                ⚠️ Erreur chargement
            </div>
        `;
    }
}

// ==================== MODAL ====================

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
            <div class="detail-section" style="border-left: 4px solid var(--accent-red);">
                <div class="detail-section-title">
                    <span class="pump-badge ${pumpBadge.class}">${pumpBadge.emoji} ${pumpBadge.text}</span>
                </div>
                <div class="detail-value" style="color: var(--text-secondary); font-size: 14px;">
                    Score P&D: ${token.pump_dump_score}/100
                </div>
            </div>
        ` : ''}

        <div class="detail-section">
            <div class="detail-section-title">📊 Données de Marché</div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Prix</div>
                    <div class="detail-value">${token.market.price || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Liquidité</div>
                    <div class="detail-value">${token.market.liquidity ? '$' + token.market.liquidity.toLocaleString() : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Volume 24h</div>
                    <div class="detail-value">${token.market.volume_24h ? '$' + token.market.volume_24h.toLocaleString() : 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Variation 24h</div>
                    <div class="detail-value" style="color: ${token.market.price_change_24h >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">
                        ${token.market.price_change_24h ? token.market.price_change_24h.toFixed(2) + '%' : 'N/A'}
                    </div>
                </div>
            </div>
        </div>
    `;

    modal.classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

console.log('✅ App.js chargé !');