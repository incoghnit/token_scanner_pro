/**
 * Token Scanner Pro - Reusable UI Components
 * Eliminates code duplication and provides consistent styling
 */

// ==================== BADGE COMPONENTS ====================

/**
 * Generate trading signal badge (BUY/SELL/HOLD)
 */
function createTradingSignalBadge(tradingSignal, size = 'small') {
    if (!tradingSignal) return '';

    const signal = tradingSignal.signal || 'HOLD';
    const confidence = tradingSignal.confidence || 0;

    const colors = {
        'STRONG_BUY': {bg: 'rgba(34, 197, 94, 0.25)', color: '#22c55e', border: '#22c55e', icon: '🟢'},
        'BUY': {bg: 'rgba(74, 222, 128, 0.2)', color: '#4ade80', border: '#4ade80', icon: '🟢'},
        'HOLD': {bg: 'rgba(156, 163, 175, 0.2)', color: '#9ca3af', border: '#9ca3af', icon: '⏸️'},
        'SELL': {bg: 'rgba(251, 146, 60, 0.2)', color: '#fb923c', border: '#fb923c', icon: '🔴'},
        'STRONG_SELL': {bg: 'rgba(239, 68, 68, 0.25)', color: '#ef4444', border: '#ef4444', icon: '🔴'}
    };

    const style = colors[signal] || colors.HOLD;
    const text = signal.replace('_', ' ');

    if (size === 'large') {
        return `
            <div style="background: ${style.bg}; border: 2px solid ${style.border}; border-radius: 0.75rem; padding: 0.75rem 1.5rem; display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.25rem;">${style.icon}</span>
                <div>
                    <div style="font-weight: 800; font-size: 1.125rem; color: ${style.color};">${text}</div>
                    <div style="font-size: 0.75rem; color: var(--text-tertiary); font-weight: 600;">${confidence}% confidence</div>
                </div>
            </div>
        `;
    } else {
        return `<span style="background: ${style.bg}; color: ${style.color}; padding: 0.2rem 0.6rem; border-radius: 0.75rem; font-size: 0.7rem; font-weight: 700; border: 1.5px solid ${style.border}; box-shadow: 0 2px 8px ${style.bg}; text-transform: uppercase; letter-spacing: 0.5px;">${style.icon} ${text}</span>`;
    }
}

/**
 * Generate safety badge (SAFE/RISKY)
 * @param {boolean} isSafe - Whether the token is safe
 * @param {string} size - 'small' for tiles, 'large' for modal header
 */
function createSafetyBadge(isSafe, size = 'small') {
    if (size === 'large') {
        return isSafe
            ? '<span style="background: rgba(34, 197, 94, 0.2); color: #22c55e; padding: 0.5rem 1rem; border-radius: 1rem; font-weight: 600;">✅ SAFE</span>'
            : '<span style="background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 0.5rem 1rem; border-radius: 1rem; font-weight: 600;">⚠️ RISKY</span>';
    }
    return isSafe
        ? '<span class="badge badge-safe">✅ SAFE</span>'
        : '<span class="badge badge-risky">⚠️ RISKY</span>';
}

/**
 * Generate pump & dump badge
 */
function createPumpDumpBadge(isPumpDump) {
    return isPumpDump
        ? '<span class="badge badge-pump-dump">🚨 P&D</span>'
        : '';
}

/**
 * Generate scammer badge
 */
function createScammerBadge(creatorSecurity) {
    return creatorSecurity?.is_malicious
        ? '<span class="badge badge-scammer">💀 SCAMMER</span>'
        : '';
}

/**
 * Generate rug-pull badge with level
 */
function createRugpullBadge(rugpullDetection) {
    if (!rugpullDetection?.is_rugpull_risk) return '';

    const level = rugpullDetection.rugpull_risk_level?.toUpperCase() || 'RISK';
    const levelColor = level === 'HIGH' ? '#ef4444' : '#f59e0b';

    return `<span style="background: rgba(245, 158, 11, 0.2); color: ${levelColor}; padding: 0.15rem 0.5rem; border-radius: 0.75rem; font-size: 0.7rem; font-weight: 600;">🎣 ${level}</span>`;
}

/**
 * Generate spam badge
 */
function createSpamBadge(market, security) {
    return (market?.possible_spam || security?.possible_spam)
        ? '<span class="badge badge-spam">⚠️ SPAM?</span>'
        : '';
}

/**
 * Generate Solana Beta badge
 */
function createSolanaBetaBadge(security) {
    return security?.data_warning === 'solana_beta_limited_data'
        ? '<span class="badge badge-solana-beta" title="GoPlus Solana API is in Beta - some data may be limited">⚠️ SOLANA BETA</span>'
        : '';
}

/**
 * Generate risk score badge
 * @param {number} riskScore - Risk score (0-100)
 * @param {string} size - 'small' for tiles, 'large' for modal header
 */
function createRiskScoreBadge(riskScore, size = 'small') {
    if (size === 'large') {
        return `<span style="background: var(--gradient-primary); color: white; padding: 0.5rem 1rem; border-radius: 1rem; font-weight: 700;">Risk: ${riskScore}/100</span>`;
    }
    const color = getRiskColor(riskScore);
    return `<span style="background: ${color}; color: white; padding: 0.15rem 0.5rem; border-radius: 0.75rem; font-size: 0.7rem; font-weight: 600;">Risk: ${riskScore}</span>`;
}

/**
 * Generate chain badge
 * @param {string} chain - Blockchain name
 * @param {string} size - 'small' for tiles, 'large' for modal header
 */
function createChainBadge(chain, size = 'small') {
    if (size === 'large') {
        return `<span style="background: var(--bg-glass); padding: 0.5rem 1rem; border-radius: 1rem; font-weight: 600;">${chain.toUpperCase()}</span>`;
    }
    return `<span class="badge badge-chain">${chain}</span>`;
}

/**
 * Generate all status badges for a token
 */
function createAllBadges(token) {
    return `
        <span class="badge badge-chain">${token.chain}</span>
        ${createSafetyBadge(token.is_safe)}
        ${createPumpDumpBadge(token.is_pump_dump_suspect)}
        ${createScammerBadge(token.creator_security)}
        ${createRugpullBadge(token.rugpull_detection)}
        ${createSpamBadge(token.market, token.security)}
        ${createSolanaBetaBadge(token.security)}
        ${createTradingSignalBadge(token.technical_analysis?.trading_signal, 'small')}
    `;
}

// ==================== CARD COMPONENTS ====================

/**
 * Generate market data card
 */
function createMarketDataCard(market) {
    if (!market || market.error) return '';

    return `
        <div class="info-card">
            <h3 class="info-card-title">💹 Market Data</h3>
            <div class="info-card-content">
                <div class="info-row"><span>Price:</span><span class="info-value">$${market.price_usd?.toFixed(8) || 'N/A'}</span></div>
                <div class="info-row"><span>24h Change:</span><span class="info-value" style="color: ${market.price_change_24h >= 0 ? '#22c55e' : '#ef4444'};">${(market.price_change_24h >= 0 ? '+' : '')}${market.price_change_24h?.toFixed(2) || '0'}%</span></div>
                <div class="info-row"><span>Liquidity:</span><span class="info-value">$${(market.liquidity_usd / 1000).toFixed(2)}K</span></div>
                <div class="info-row"><span>Volume 24h:</span><span class="info-value">$${(market.volume_24h / 1000).toFixed(2)}K</span></div>
                <div class="info-row"><span>Market Cap:</span><span class="info-value">$${(market.market_cap / 1000).toFixed(2)}K</span></div>
                <div class="info-row"><span>Buys/Sells:</span><span class="info-value">${market.txns_24h_buys || 0}/${market.txns_24h_sells || 0}</span></div>
            </div>
        </div>
    `;
}

/**
 * Generate security card
 */
function createSecurityCard(security) {
    if (!security || security.error) return '';

    return `
        <div class="info-card">
            <h3 class="info-card-title">🔒 Security</h3>
            <div class="info-card-content">
                <div class="info-row"><span>Buy Tax:</span><span class="info-value" style="color: ${security.buy_tax > 10 ? '#ef4444' : '#22c55e'};">${security.buy_tax?.toFixed(1) || 0}%</span></div>
                <div class="info-row"><span>Sell Tax:</span><span class="info-value" style="color: ${security.sell_tax > 10 ? '#ef4444' : '#22c55e'};">${security.sell_tax?.toFixed(1) || 0}%</span></div>
                <div class="info-row"><span>Honeypot:</span><span class="info-value" style="color: ${security.is_honeypot ? '#ef4444' : '#22c55e'};">${security.is_honeypot ? '❌ Yes' : '✅ No'}</span></div>
                <div class="info-row"><span>Mintable:</span><span class="info-value" style="color: ${security.is_mintable ? '#f59e0b' : '#22c55e'};">${security.is_mintable ? '⚠️ Yes' : '✅ No'}</span></div>
                <div class="info-row"><span>Open Source:</span><span class="info-value" style="color: ${security.is_open_source ? '#22c55e' : '#f59e0b'};">${security.is_open_source ? '✅ Yes' : '⚠️ No'}</span></div>
                <div class="info-row"><span>Holders:</span><span class="info-value">${security.holder_count || 'N/A'}</span></div>
            </div>
        </div>
    `;
}

/**
 * Generate RSI gauge component
 */
function createRSIGauge(rsi) {
    if (rsi === null || rsi === undefined) return '';

    const status = rsi < 30 ? 'OVERSOLD' : rsi > 70 ? 'OVERBOUGHT' : 'NEUTRAL';
    const statusColor = rsi < 30 ? '#22c55e' : rsi > 70 ? '#ef4444' : '#9ca3af';
    const statusIcon = rsi < 30 ? '🟢' : rsi > 70 ? '🔴' : '⚪';
    const hint = rsi < 30 ? 'Buy opportunity' : rsi > 70 ? 'Sell signal' : 'No clear signal';

    return `
        <div class="ta-card">
            <h4 class="ta-card-title">📈 RSI (Relative Strength Index)</h4>
            <div style="display: flex; align-items: center; gap: 1.5rem;">
                <div style="flex: 1;">
                    <div class="rsi-gauge">
                        <div class="rsi-indicator" style="left: ${rsi}%;"></div>
                        <div class="rsi-value" style="left: ${rsi}%;">${rsi.toFixed(1)}</div>
                    </div>
                    <div class="rsi-labels">
                        <span>0 (Oversold)</span>
                        <span>30</span>
                        <span>50</span>
                        <span>70</span>
                        <span>100 (Overbought)</span>
                    </div>
                </div>
                <div style="text-align: center; min-width: 120px;">
                    <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: 0.5rem;">Status</div>
                    <div style="font-weight: 700; font-size: 1rem; color: ${statusColor};">
                        ${statusIcon} ${status}
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-tertiary); margin-top: 0.25rem;">
                        ${hint}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Generate support/resistance visual display
 */
function createSupportResistance(supportResistance) {
    if (!supportResistance) return '';

    const supports = supportResistance.support || [];
    const resistances = supportResistance.resistance || [];
    const currentPrice = supportResistance.current_price;

    const supportHTML = supports.length > 0
        ? supports.map((s, idx) => `
            <div class="sr-level support-level">
                <div class="sr-label">S${idx + 1}</div>
                <div class="sr-price">$${s.toFixed(8)}</div>
            </div>
        `).join('')
        : '<div style="text-align: center; color: var(--text-tertiary); font-size: 0.75rem;">No support detected</div>';

    const resistanceHTML = resistances.length > 0
        ? resistances.map((r, idx) => `
            <div class="sr-level resistance-level">
                <div class="sr-label">R${idx + 1}</div>
                <div class="sr-price">$${r.toFixed(8)}</div>
            </div>
        `).join('')
        : '<div style="text-align: center; color: var(--text-tertiary); font-size: 0.75rem;">No resistance detected</div>';

    return `
        <div class="ta-card">
            <h4 class="ta-card-title">📍 Support & Resistance Levels</h4>
            <div class="sr-container">
                <div class="sr-column">
                    <div class="sr-column-title support-title">🟢 SUPPORT</div>
                    ${supportHTML}
                </div>
                <div class="sr-current">
                    <div style="font-size: 0.7rem; color: rgba(255,255,255,0.7); margin-bottom: 0.25rem;">Current</div>
                    <div class="sr-current-price">$${currentPrice.toFixed(8)}</div>
                </div>
                <div class="sr-column">
                    <div class="sr-column-title resistance-title">🔴 RESISTANCE</div>
                    ${resistanceHTML}
                </div>
            </div>
        </div>
    `;
}

// ==================== UTILITY FUNCTIONS ====================

/**
 * Format large numbers (K, M, B)
 */
function formatNumber(num) {
    if (!num) return '0';
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
    return num.toFixed(2);
}

/**
 * Format price with appropriate decimals
 */
function formatPrice(price) {
    if (!price) return '$0.00';
    if (price >= 1) return `$${price.toFixed(4)}`;
    return `$${price.toFixed(8)}`;
}

/**
 * Format percentage change with color
 */
function formatChange(change) {
    if (!change) return '0%';
    return `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
}

/**
 * Get color for price change
 */
function colorChange(change) {
    if (!change) return 'var(--text-tertiary)';
    return change >= 0 ? '#22c55e' : '#ef4444';
}

/**
 * Get risk color based on score
 */
function getRiskColor(score) {
    if (score >= 70) return 'linear-gradient(135deg, #dc2626 0%, #ef4444 100%)';
    if (score >= 50) return 'linear-gradient(135deg, #f59e0b 0%, #fb923c 100%)';
    if (score >= 30) return 'linear-gradient(135deg, #eab308 0%, #fbbf24 100%)';
    return 'linear-gradient(135deg, #22c55e 0%, #4ade80 100%)';
}
