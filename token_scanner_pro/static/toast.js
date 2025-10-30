/**
 * Simple Toast Notification System
 * No dependencies required
 *
 * Usage:
 *   toast.success("Token added to favorites!");
 *   toast.error("Failed to load data");
 *   toast.warning("API rate limit approaching");
 *   toast.info("New tokens discovered");
 *   toast.loading("Scanning tokens...");
 */

(function(window) {
    'use strict';

    // Toast container styles
    const styles = `
        .toast-container {
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 99999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        }

        .toast {
            background: var(--bg-card, #1a1a2e);
            border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
            border-radius: 0.75rem;
            padding: 1rem 1.25rem;
            min-width: 300px;
            max-width: 400px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(10px);
            display: flex;
            align-items: start;
            gap: 0.75rem;
            animation: slideIn 0.3s ease-out;
            pointer-events: auto;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .toast:hover {
            transform: translateX(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
        }

        .toast.hiding {
            animation: slideOut 0.3s ease-out forwards;
        }

        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }

        .toast-icon {
            font-size: 1.5rem;
            flex-shrink: 0;
            animation: bounceIn 0.5s ease-out;
        }

        @keyframes bounceIn {
            0%, 20%, 50%, 80%, 100% {
                transform: translateY(0);
            }
            40% {
                transform: translateY(-10px);
            }
            60% {
                transform: translateY(-5px);
            }
        }

        .toast-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .toast-title {
            font-weight: 700;
            font-size: 0.95rem;
            margin: 0;
        }

        .toast-message {
            font-size: 0.85rem;
            color: var(--text-secondary, #a0a0a0);
            margin: 0;
            line-height: 1.4;
        }

        .toast-close {
            flex-shrink: 0;
            background: none;
            border: none;
            color: var(--text-tertiary, #707070);
            cursor: pointer;
            font-size: 1.25rem;
            padding: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 0.25rem;
            transition: all 0.2s;
        }

        .toast-close:hover {
            background: var(--bg-glass, rgba(255, 255, 255, 0.05));
            color: var(--text-primary, #f0f0f0);
        }

        /* Type-specific styles */
        .toast.success {
            border-left: 4px solid #22c55e;
        }

        .toast.success .toast-title {
            color: #22c55e;
        }

        .toast.error {
            border-left: 4px solid #ef4444;
        }

        .toast.error .toast-title {
            color: #ef4444;
        }

        .toast.warning {
            border-left: 4px solid #f59e0b;
        }

        .toast.warning .toast-title {
            color: #f59e0b;
        }

        .toast.info {
            border-left: 4px solid #3b82f6;
        }

        .toast.info .toast-title {
            color: #3b82f6;
        }

        .toast.loading {
            border-left: 4px solid #667eea;
        }

        .toast.loading .toast-title {
            color: #667eea;
        }

        .toast.loading .toast-icon {
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            from {
                transform: rotate(0deg);
            }
            to {
                transform: rotate(360deg);
            }
        }

        /* Mobile responsive */
        @media (max-width: 768px) {
            .toast-container {
                top: 60px;
                right: 10px;
                left: 10px;
            }

            .toast {
                min-width: auto;
                max-width: 100%;
            }
        }
    `;

    // Inject styles
    const styleSheet = document.createElement('style');
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);

    // Create toast container
    let container = null;

    function getContainer() {
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    }

    // Icon mapping
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️',
        loading: '⏳'
    };

    // Title mapping
    const titles = {
        success: 'Succès',
        error: 'Erreur',
        warning: 'Attention',
        info: 'Information',
        loading: 'Chargement'
    };

    // Toast counter for unique IDs
    let toastCounter = 0;

    // Active toasts map
    const activeToasts = new Map();

    /**
     * Show a toast notification
     * @param {string} type - Toast type: success, error, warning, info, loading
     * @param {string} message - Message to display
     * @param {Object} options - Optional configuration
     * @returns {string} Toast ID
     */
    function showToast(type, message, options = {}) {
        const {
            title = titles[type],
            duration = type === 'loading' ? 0 : 4000,
            id = null,
            closeable = true
        } = options;

        const toastId = id || `toast-${++toastCounter}`;

        // Remove existing toast with same ID
        if (activeToasts.has(toastId)) {
            dismissToast(toastId);
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.id = toastId;

        toast.innerHTML = `
            <div class="toast-icon">${icons[type]}</div>
            <div class="toast-content">
                <p class="toast-title">${title}</p>
                ${message ? `<p class="toast-message">${message}</p>` : ''}
            </div>
            ${closeable ? '<button class="toast-close">✕</button>' : ''}
        `;

        // Add to container
        const cont = getContainer();
        cont.appendChild(toast);

        // Store in active toasts
        activeToasts.set(toastId, toast);

        // Close button handler
        if (closeable) {
            const closeBtn = toast.querySelector('.toast-close');
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                dismissToast(toastId);
            });
        }

        // Click to dismiss
        toast.addEventListener('click', () => {
            dismissToast(toastId);
        });

        // Auto dismiss (except loading)
        if (duration > 0) {
            setTimeout(() => {
                dismissToast(toastId);
            }, duration);
        }

        return toastId;
    }

    /**
     * Dismiss a toast
     * @param {string} toastId - Toast ID to dismiss
     */
    function dismissToast(toastId) {
        const toast = activeToasts.get(toastId);
        if (!toast) return;

        toast.classList.add('hiding');

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            activeToasts.delete(toastId);

            // Remove container if empty
            if (container && container.children.length === 0) {
                container.remove();
                container = null;
            }
        }, 300);
    }

    /**
     * Update an existing toast (useful for loading states)
     * @param {string} toastId - Toast ID to update
     * @param {string} type - New type
     * @param {string} message - New message
     */
    function updateToast(toastId, type, message) {
        dismissToast(toastId);
        return showToast(type, message, { id: toastId });
    }

    /**
     * Dismiss all toasts
     */
    function dismissAll() {
        const toastIds = Array.from(activeToasts.keys());
        toastIds.forEach(id => dismissToast(id));
    }

    // Public API
    window.toast = {
        success: (message, options) => showToast('success', message, options),
        error: (message, options) => showToast('error', message, options),
        warning: (message, options) => showToast('warning', message, options),
        info: (message, options) => showToast('info', message, options),
        loading: (message, options) => showToast('loading', message, { ...options, duration: 0 }),
        dismiss: dismissToast,
        update: updateToast,
        dismissAll: dismissAll
    };

})(window);

/**
 * USAGE EXAMPLES:
 *
 * // Simple success message
 * toast.success("Token added to favorites!");
 *
 * // Error with custom title
 * toast.error("Failed to load data", { title: "Network Error" });
 *
 * // Loading state
 * const loadingId = toast.loading("Scanning tokens...");
 * // ... do work ...
 * toast.update(loadingId, 'success', "Scan complete!");
 *
 * // Custom duration
 * toast.warning("Rate limit approaching", { duration: 6000 });
 *
 * // Persistent notification (manual dismiss)
 * toast.info("Server maintenance at 2 AM", { duration: 0, closeable: true });
 *
 * // Dismiss specific toast
 * const id = toast.success("Processing...");
 * toast.dismiss(id);
 *
 * // Dismiss all toasts
 * toast.dismissAll();
 */
