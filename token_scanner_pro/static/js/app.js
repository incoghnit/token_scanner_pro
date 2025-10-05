const API_URL = window.location.origin + '/api';
let scanInterval = null;
let currentFilter = 'all';
let currentView = 'grid'; // 'grid' ou 'list'
let allTokens = [];
let currentUser = null;
let userFavorites = new Set();
let lastScanTimestamp = null;

// Initialisation
window.addEventListener('load', async () => {
    await checkAuth();
    await loadPreviousResults();
});

// Authentification
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
            
            // Afficher le lien admin si admin
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

// Tabs
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
            console.log('Connexion réussie !');
            // Recharger la page pour afficher le bouton admin si nécessaire
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
            console.log('Compte créé avec succès !');
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
        console.log('Déconnexion réussie');
        window.location.reload();
    } catch (error) {
        console.error('Erreur déconnexion:', error);
    }
}

// Favoris
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
            // Recharger l'affichage
            displayTokens(allTokens);
            console.log(data.message);
        }
    } catch (error) {
        console.error('Erreur favori:', error);
    }
}

// Scan
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

        // Afficher le timestamp
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

function displayTokens(tokens) {
    const grid = document.getElementById('tokensGrid');
    grid.innerHTML = '';

    const filtered = tokens.filter(token => {
        if (currentFilter === 'all') return true;
        if (currentFilter === 'safe') return token.risk_score < 50;
        if (currentFilter === 'danger') return token.risk_score >= 50;
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

function createTokenCard(token) {
    const card = document.createElement('div');
    let riskClass = 'safe';
    if (token.risk_score >= 50) riskClass = 'danger';
    else if (token.risk_score >= 20) riskClass = 'warning';

    card.className = `token-card ${riskClass}`;
    
    const shortAddr = token.address.substring(0, 8) + '...' + token.address.substring(token.address.length - 6);
    const key = `${token.address}-${token.chain}`;
    const isFavorite = userFavorites.has(key);

    // Icon HTML
    const iconHtml = token.icon 
        ? `<div class="token-icon"><img src="${token.icon}" alt="${token.chain}" onerror="this.parentElement.innerHTML='<span class=\\'token-icon-placeholder\\'>🪙</span>'"></div>`
        : `<div class="token-icon"><span class="token-icon-placeholder">🪙</span></div>`;

    // Créer le cercle de progression du risque
    const circumference = 2 * Math.PI * 24; // rayon 24
    const offset = circumference - (token.risk_score / 100) * circumference;

    card.innerHTML = `
        <div class="token-header">
            <div class="token-address-section">
                ${iconHtml}
                <div class="token-info">
                    <div class="token-address">${shortAddr}</div>
                    <span class="chain-badge">${token.chain}</span>
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
            ${currentView === 'list' ? `
            <div class="metric">
                <div class="metric-label">👥 Holders</div>
                <div class="metric-value">${token.security.holder_count || 'N/A'}</div>
            </div>
            <div class="metric">
                <div class="metric-label">💸 Prix USD</div>
                <div class="metric-value">$${token.market.price_usd ? token.market.price_usd.toFixed(8) : 'N/A'}</div>
            </div>
            <div class="metric">
                <div class="metric-label">📈 Change 24h</div>
                <div class="metric-value" style="color: ${token.market.price_change_24h >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">
                    ${token.market.price_change_24h ? token.market.price_change_24h.toFixed(2) : '0'}%
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">🔒 Sécurité</div>
                <div class="metric-value">
                    ${token.security.is_honeypot ? '⚠️' : '✅'} 
                    ${token.security.is_open_source ? '✅' : '⚠️'}
                </div>
            </div>
            ` : ''}
        </div>
    `;

    // Événement clic sur le bouton favori
    const favoriteBtn = card.querySelector('.btn-icon');
    favoriteBtn.addEventListener('click', (e) => toggleFavorite(token, e));

    // Événement clic sur la card (sauf sur le bouton)
    card.addEventListener('click', (e) => {
        if (!e.target.closest('.btn-icon')) {
            openModal(token);
        }
    });

    return card;
}

// Modal détails du token
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

    // Icon dans le modal
    const iconHtml = token.icon 
        ? `<img src="${token.icon}" alt="${token.chain}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid var(--border-color);" onerror="this.style.display='none'">`
        : '';

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

        ${token.warnings && token.warnings.length > 0 ? `
        <div class="detail-section">
            <div class="detail-section-title">⚠️ Alertes Détectées (${token.warnings.length})</div>
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

// Fermer modal au clic extérieur
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('tokenModal').addEventListener('click', (e) => {
        if (e.target.id === 'tokenModal') {
            closeModal();
        }
    });

    // Fermer modal avec ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
});

// Utilities
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