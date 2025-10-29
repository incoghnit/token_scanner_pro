/**
 * Token Discovery Client - WebSocket Client pour Token Scanner Pro
 * =================================================================
 *
 * Client WebSocket qui se connecte au Token Discovery Service pour recevoir
 * les nouveaux tokens en temps réel, partagés entre tous les utilisateurs.
 *
 * Features:
 * - Connexion WebSocket automatique
 * - Reconnexion automatique en cas de déconnexion
 * - Réception des nouveaux tokens en temps réel
 * - Événements personnalisables (callbacks)
 * - Gestion des erreurs et retry logic
 *
 * Usage:
 *   const client = new TokenDiscoveryClient();
 *
 *   client.on('new_token', (token) => {
 *       console.log('Nouveau token:', token);
 *       // Mettre à jour l'UI
 *   });
 *
 *   client.on('scan_started', () => {
 *       console.log('Scan démarré...');
 *   });
 *
 *   client.connect();
 */

class TokenDiscoveryClient {
    constructor(options = {}) {
        // Configuration
        this.serverUrl = options.serverUrl || window.location.origin;
        this.autoReconnect = options.autoReconnect !== undefined ? options.autoReconnect : true;
        this.reconnectDelay = options.reconnectDelay || 3000;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 10;

        // État
        this.socket = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.reconnectTimer = null;

        // Événements et callbacks
        this.eventHandlers = {
            'connected': [],
            'disconnected': [],
            'new_token': [],
            'scan_started': [],
            'scan_completed': [],
            'scan_error': [],
            'discovery_status': [],
            'error': []
        };

        // Stats
        this.tokensReceived = 0;
        this.scansCompleted = 0;
        this.connectionTime = null;

        console.log('🔌 Token Discovery Client initialisé');
    }

    // ==================== CONNEXION ====================

    /**
     * Se connecte au serveur WebSocket
     */
    connect() {
        if (this.connected) {
            console.warn('⚠️ Déjà connecté au serveur');
            return;
        }

        if (!window.io) {
            console.error('❌ Socket.IO library not loaded. Include: <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>');
            this._triggerEvent('error', { message: 'Socket.IO library missing' });
            return;
        }

        console.log(`🔌 Connexion au serveur WebSocket: ${this.serverUrl}`);

        try {
            // Créer la connexion Socket.IO
            this.socket = io(this.serverUrl, {
                transports: ['websocket', 'polling'],
                reconnection: false  // On gère la reconnexion manuellement
            });

            // Configurer les événements Socket.IO
            this._setupSocketEvents();

        } catch (error) {
            console.error('❌ Erreur lors de la connexion:', error);
            this._triggerEvent('error', { message: error.message, error });

            if (this.autoReconnect) {
                this._scheduleReconnect();
            }
        }
    }

    /**
     * Se déconnecte du serveur
     */
    disconnect() {
        console.log('🔌 Déconnexion du serveur...');

        this.autoReconnect = false;  // Désactiver la reconnexion auto

        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }

        this.connected = false;
        this.connectionTime = null;
    }

    /**
     * Configure les événements du socket
     */
    _setupSocketEvents() {
        // Connexion réussie
        this.socket.on('connect', () => {
            console.log('✅ Connecté au Token Discovery Service');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.connectionTime = new Date();

            // Rejoindre la room discovery
            this.socket.emit('join_discovery');

            // Demander le statut initial
            this.socket.emit('request_status');

            this._triggerEvent('connected', {
                connectionTime: this.connectionTime,
                socketId: this.socket.id
            });
        });

        // Déconnexion
        this.socket.on('disconnect', (reason) => {
            console.log(`🔌 Déconnecté: ${reason}`);
            this.connected = false;

            this._triggerEvent('disconnected', { reason });

            // Reconnexion automatique si nécessaire
            if (this.autoReconnect && reason !== 'io client disconnect') {
                this._scheduleReconnect();
            }
        });

        // Erreur de connexion
        this.socket.on('connect_error', (error) => {
            console.error('❌ Erreur de connexion:', error.message);
            this._triggerEvent('error', { message: error.message, error });

            if (this.autoReconnect) {
                this._scheduleReconnect();
            }
        });

        // ==================== ÉVÉNEMENTS DISCOVERY ====================

        // Nouveau token découvert
        this.socket.on('new_token', (token) => {
            console.log('📢 Nouveau token:', token.name || token.symbol || 'Unknown');
            this.tokensReceived++;
            this._triggerEvent('new_token', token);
        });

        // Scan démarré
        this.socket.on('scan_started', (data) => {
            console.log('🔍 Scan démarré:', data);
            this._triggerEvent('scan_started', data);
        });

        // Scan terminé
        this.socket.on('scan_completed', (data) => {
            console.log('✅ Scan terminé:', data);
            this.scansCompleted++;
            this._triggerEvent('scan_completed', data);
        });

        // Erreur de scan
        this.socket.on('scan_error', (data) => {
            console.error('❌ Erreur de scan:', data.error);
            this._triggerEvent('scan_error', data);
        });

        // Statut du service
        this.socket.on('discovery_status', (status) => {
            console.log('📊 Statut Discovery:', status);
            this._triggerEvent('discovery_status', status);
        });

        // Confirmation de room join
        this.socket.on('joined_discovery', (data) => {
            console.log('👥 Rejoint la room discovery:', data.message);
        });
    }

    /**
     * Programme une tentative de reconnexion
     */
    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error(`❌ Nombre maximum de tentatives de reconnexion atteint (${this.maxReconnectAttempts})`);
            this._triggerEvent('error', {
                message: 'Max reconnect attempts reached',
                attempts: this.reconnectAttempts
            });
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.min(this.reconnectAttempts, 5);

        console.log(`⏳ Tentative de reconnexion ${this.reconnectAttempts}/${this.maxReconnectAttempts} dans ${delay}ms...`);

        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, delay);
    }

    // ==================== ACTIONS ====================

    /**
     * Déclenche un scan manuel des DERNIERS tokens (découverte)
     *
     * ⚠️ IMPORTANT: Ce scan est PARTAGÉ entre tous les utilisateurs.
     *
     * Pour scanner UN TOKEN SPÉCIFIQUE (adresse/URL), utilisez plutôt
     * la route /api/scan/start qui est PRIVÉE et non partagée.
     *
     * @param {Object} options - Options du scan
     * @param {number} options.maxTokens - Nombre de tokens (défaut: 20)
     * @param {string} options.chain - Blockchain spécifique (optionnel)
     */
    triggerScan(options = {}) {
        if (!this.connected) {
            console.error('❌ Pas connecté au serveur');
            return Promise.reject(new Error('Not connected'));
        }

        const maxTokens = options.maxTokens || 20;
        const chain = options.chain || null;

        console.log('🔍 Déclenchement d\'un scan Discovery...', { maxTokens, chain });

        return fetch('/api/discovery/trigger', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                max_tokens: maxTokens,
                chain: chain
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('✅ Discovery scan déclenché avec succès');
                return data;
            } else {
                throw new Error(data.error || 'Scan failed');
            }
        })
        .catch(error => {
            console.error('❌ Erreur lors du déclenchement du scan:', error);
            throw error;
        });
    }

    /**
     * Demande le statut du service
     */
    requestStatus() {
        if (!this.connected) {
            console.error('❌ Pas connecté au serveur');
            return Promise.reject(new Error('Not connected'));
        }

        return fetch('/api/discovery/status')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    return data.status;
                } else {
                    throw new Error(data.error || 'Failed to get status');
                }
            });
    }

    /**
     * Récupère les statistiques
     */
    getStats() {
        return fetch('/api/discovery/stats')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    return data.stats;
                } else {
                    throw new Error(data.error || 'Failed to get stats');
                }
            });
    }

    /**
     * Récupère les tokens récents
     */
    getRecentTokens(limit = 50, chain = null) {
        const params = new URLSearchParams();
        params.append('limit', limit);
        if (chain) params.append('chain', chain);

        return fetch(`/api/discovery/recent?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    return data.tokens;
                } else {
                    throw new Error(data.error || 'Failed to get recent tokens');
                }
            });
    }

    // ==================== ÉVÉNEMENTS ====================

    /**
     * Enregistre un callback pour un événement
     */
    on(eventName, callback) {
        if (!this.eventHandlers[eventName]) {
            this.eventHandlers[eventName] = [];
        }

        this.eventHandlers[eventName].push(callback);

        return () => {
            // Retourne une fonction pour désinscrire le callback
            this.off(eventName, callback);
        };
    }

    /**
     * Désinscrit un callback
     */
    off(eventName, callback) {
        if (!this.eventHandlers[eventName]) return;

        const index = this.eventHandlers[eventName].indexOf(callback);
        if (index > -1) {
            this.eventHandlers[eventName].splice(index, 1);
        }
    }

    /**
     * Déclenche un événement
     */
    _triggerEvent(eventName, data) {
        if (!this.eventHandlers[eventName]) return;

        this.eventHandlers[eventName].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`❌ Erreur dans callback ${eventName}:`, error);
            }
        });
    }

    // ==================== GETTERS ====================

    /**
     * Retourne l'état de connexion
     */
    isConnected() {
        return this.connected;
    }

    /**
     * Retourne les statistiques du client
     */
    getClientStats() {
        return {
            connected: this.connected,
            tokensReceived: this.tokensReceived,
            scansCompleted: this.scansCompleted,
            reconnectAttempts: this.reconnectAttempts,
            connectionTime: this.connectionTime,
            uptime: this.connectionTime ? Date.now() - this.connectionTime.getTime() : 0
        };
    }
}

// Export pour utilisation en module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TokenDiscoveryClient;
}

// Rendre disponible globalement
if (typeof window !== 'undefined') {
    window.TokenDiscoveryClient = TokenDiscoveryClient;
}
