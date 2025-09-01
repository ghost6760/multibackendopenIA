// scripts/ui.js - UI Utilities Module - FIXED STRUCTURE
'use strict';

/**
 * UI Utilities Manager for Multi-Tenant Admin Panel
 * Handles loading states, toasts, modals, and other UI interactions
 */
class UIManager {
    constructor() {
        this.toastCount = 0;
        this.maxToasts = window.APP_CONFIG?.UI?.max_toast_count || 5;
        this.toastDuration = window.APP_CONFIG?.UI?.toast_duration || 5000;
        this.isInitialized = false;
        
        this.init();
    }

    /**
     * Initialize UI Manager - MOVED INSIDE CLASS
     */
    init() {
        if (this.isInitialized) return;
        
        this.setupToastContainer();
        this.setupLoadingOverlay();
        this.setupModalHandlers();
        this.setupKeyboardShortcuts();
        
        this.isInitialized = true;
        
        if (window.APP_CONFIG?.DEBUG?.enabled) {
            console.log('🎨 UI Manager initialized');
        }
    }

    /**
     * Setup toast container if it doesn't exist
     */
    setupToastContainer() {
        if (!document.getElementById('toastContainer')) {
            const container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
    }

    /**
     * Setup loading overlay if it doesn't exist
     */
    setupLoadingOverlay() {
        if (!document.getElementById('loadingOverlay')) {
            const overlay = document.createElement('div');
            overlay.id = 'loadingOverlay';
            overlay.className = 'loading-overlay';
            overlay.style.display = 'none';
            overlay.innerHTML = `
                <div class="loading-content">
                    <div class="loading-spinner">
                        <div class="spinner"></div>
                    </div>
                    <p id="loadingMessage" class="loading-message">Cargando...</p>
                    <div id="loadingProgress" class="loading-progress" style="display: none;">
                        <div class="progress-bar">
                            <div id="progressFill" class="progress-fill"></div>
                        </div>
                        <span id="progressText" class="progress-text">0%</span>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);
        }
    }

    /**
     * Setup modal event handlers
     */
    setupModalHandlers() {
        // Close modal when clicking outside
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.remove();
            }
        });

        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const modals = document.querySelectorAll('.modal');
                modals.forEach(modal => modal.remove());
            }
        });
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+K or Cmd+K for quick search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.getElementById('searchQuery');
                if (searchInput) {
                    searchInput.focus();
                }
            }

            // Ctrl+R or Cmd+R for refresh (prevent default and use our refresh)
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                if (window.AdminApp && window.AdminApp.loadCompanies) {
                    window.AdminApp.loadCompanies();
                }
            }
        });
    }

    // ==================== LOADING STATES ====================

    /**
     * Show loading overlay
     */
    showLoading(message = 'Cargando...') {
        const loadingMessage = document.getElementById('loadingMessage');
        const loadingOverlay = document.getElementById('loadingOverlay');
        const loadingProgress = document.getElementById('loadingProgress');
        
        if (loadingMessage) {
            loadingMessage.textContent = message;
        }
        
        if (loadingProgress) {
            loadingProgress.style.display = 'none';
        }
        
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
            loadingOverlay.style.opacity = '0';
            
            // Animate in
            requestAnimationFrame(() => {
                loadingOverlay.style.transition = 'opacity 0.3s ease';
                loadingOverlay.style.opacity = '1';
            });
        }

        // Auto-hide after timeout to prevent stuck loading
        setTimeout(() => {
            if (loadingOverlay && loadingOverlay.style.display === 'flex') {
                console.warn('⚠️ Loading timeout - auto-hiding loading overlay');
                this.hideLoading();
            }
        }, window.APP_CONFIG?.UI?.loading_timeout || 60000);
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.style.transition = 'opacity 0.3s ease';
            loadingOverlay.style.opacity = '0';
            
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
            }, 300);
        }
    }

    /**
     * Show loading with progress
     */
    showLoadingWithProgress(message = 'Procesando...', progress = 0) {
        this.showLoading(message);
        
        const loadingProgress = document.getElementById('loadingProgress');
        
        if (loadingProgress) {
            loadingProgress.style.display = 'block';
        }
        
        this.updateProgress(progress);
    }

    /**
     * Update progress bar
     */
    updateProgress(progress) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        const clampedProgress = Math.max(0, Math.min(100, progress));
        
        if (progressFill) {
            progressFill.style.width = `${clampedProgress}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${Math.round(clampedProgress)}%`;
        }
    }

    // ==================== TOAST NOTIFICATIONS ====================

    /**
     * Show toast notification
     */
    showToast(message, type = 'info', duration = null) {
        // Prevent too many toasts
        if (this.toastCount >= this.maxToasts) {
            this.removeOldestToast();
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.setAttribute('data-timestamp', Date.now());
        
        const container = document.getElementById('toastContainer');
        if (container) {
            container.appendChild(toast);
            this.toastCount++;

            // Animate in
            setTimeout(() => {
                toast.style.transform = 'translateX(0)';
            }, 10);

            // Auto remove
            const toastDuration = duration || this.toastDuration;
            setTimeout(() => {
                this.removeToast(toast);
            }, toastDuration);

            // Remove on click
            toast.addEventListener('click', () => {
                this.removeToast(toast);
            });
        }
    }

    /**
     * Remove specific toast
     */
    removeToast(toast) {
        if (toast && toast.parentNode) {
            toast.style.transform = 'translateX(100%)';
            toast.style.opacity = '0';
            
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                    this.toastCount--;
                }
            }, 300);
        }
    }

    /**
     * Remove oldest toast
     */
    removeOldestToast() {
        const container = document.getElementById('toastContainer');
        if (container) {
            const toasts = container.querySelectorAll('.toast');
            if (toasts.length > 0) {
                let oldestToast = toasts[0];
                let oldestTimestamp = parseInt(oldestToast.getAttribute('data-timestamp')) || 0;

                toasts.forEach(toast => {
                    const timestamp = parseInt(toast.getAttribute('data-timestamp')) || 0;
                    if (timestamp < oldestTimestamp) {
                        oldestTimestamp = timestamp;
                        oldestToast = toast;
                    }
                });

                this.removeToast(oldestToast);
            }
        }
    }

    /**
     * Clear all toasts
     */
    clearAllToasts() {
        const container = document.getElementById('toastContainer');
        if (container) {
            const toasts = container.querySelectorAll('.toast');
            toasts.forEach(toast => this.removeToast(toast));
        }
    }

    // ==================== MODALS ====================

    /**
     * Show modal dialog
     */
    showModal(title, content, options = {}) {
        const modal = document.createElement('div');
        modal.className = 'modal modal-info';
        modal.style.display = 'none';

        const modalContent = `
            <div class="modal-content" style="max-width: ${options.maxWidth || '600px'}">
                <div class="modal-header">
                    <h3 class="modal-title">
                        ${options.icon ? `<span class="modal-icon">${options.icon}</span>` : ''}
                        ${title}
                    </h3>
                    <button class="btn-close" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                <div class="modal-footer">
                    ${options.buttons || '<button onclick="this.closest(\'.modal\').remove()" class="btn btn-secondary">Cerrar</button>'}
                </div>
            </div>
        `;

        modal.innerHTML = modalContent;
        document.body.appendChild(modal);

        // Animate in
        modal.style.display = 'flex';
        modal.style.opacity = '0';
        
        requestAnimationFrame(() => {
            modal.style.transition = 'opacity 0.3s ease';
            modal.style.opacity = '1';
            
            const modalContentEl = modal.querySelector('.modal-content');
            if (modalContentEl) {
                modalContentEl.style.transform = 'scale(0.9)';
                modalContentEl.style.transition = 'transform 0.3s ease';
                
                requestAnimationFrame(() => {
                    modalContentEl.style.transform = 'scale(1)';
                });
            }
        });

        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal(modal);
            }
        });

        return modal;
    }

    /**
     * Show confirmation modal
     */
    showConfirmModal(title, message, onConfirm, onCancel = null) {
        const buttons = `
            <button onclick="this.closest('.modal').remove()" class="btn btn-secondary">Cancelar</button>
            <button id="confirmModalBtn" class="btn btn-danger">Confirmar</button>
        `;

        const modal = this.showModal(title, message, {
            icon: '⚠️',
            buttons: buttons
        });

        const confirmBtn = modal.querySelector('#confirmModalBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                this.closeModal(modal);
                if (onConfirm) onConfirm();
            });
        }

        return modal;
    }

    /**
     * Close modal with animation
     */
    closeModal(modal) {
        if (modal) {
            modal.style.opacity = '0';
            const modalContent = modal.querySelector('.modal-content');
            if (modalContent) {
                modalContent.style.transform = 'scale(0.9)';
            }

            setTimeout(() => {
                if (modal.parentNode) {
                    modal.remove();
                }
            }, 300);
        }
    }

    // ==================== RESPONSIVE UTILITIES ====================

    /**
     * Check if mobile device
     */
    isMobile() {
        return window.innerWidth <= 768;
    }

    /**
     * Check if tablet device
     */
    isTablet() {
        return window.innerWidth > 768 && window.innerWidth <= 1024;
    }

    /**
     * Check if desktop device
     */
    isDesktop() {
        return window.innerWidth > 1024;
    }

    /**
     * Update UI for responsive design
     */
    updateResponsiveUI() {
        const body = document.body;
        
        if (this.isMobile()) {
            body.classList.add('mobile-view');
            body.classList.remove('tablet-view', 'desktop-view');
        } else if (this.isTablet()) {
            body.classList.add('tablet-view');
            body.classList.remove('mobile-view', 'desktop-view');
        } else {
            body.classList.add('desktop-view');
            body.classList.remove('mobile-view', 'tablet-view');
        }
    }

    // ==================== UTILITY FUNCTIONS ====================

    /**
     * Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Throttle function
     */
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// ==================== ADDITIONAL UI UTILITIES ====================

/**
 * Create loading button state
 */
function setButtonLoading(buttonId, isLoading, loadingText = 'Cargando...') {
    const button = document.getElementById(buttonId);
    if (!button) return;

    if (isLoading) {
        button.dataset.originalText = button.textContent;
        button.textContent = loadingText;
        button.disabled = true;
        button.classList.add('loading');
    } else {
        button.textContent = button.dataset.originalText || button.textContent;
        button.disabled = false;
        button.classList.remove('loading');
        delete button.dataset.originalText;
    }
}

/**
 * Create status badge
 */
function createStatusBadge(status, text = null) {
    const badge = document.createElement('span');
    badge.className = `status-badge status-${status}`;
    badge.textContent = text || status;
    
    const statusIcons = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'loading': '⏳'
    };
    
    if (statusIcons[status]) {
        badge.textContent = `${statusIcons[status]} ${badge.textContent}`;
    }
    
    return badge;
}

// Create global UI manager instance
console.log('🎨 Creating UI Manager...');
window.UI = new UIManager();

// Window resize handler for responsive updates
window.addEventListener('resize', window.UI.throttle(() => {
    window.UI.updateResponsiveUI();
}, 250));

// Initial responsive setup
document.addEventListener('DOMContentLoaded', () => {
    window.UI.updateResponsiveUI();
});

console.log('✅ UI module loaded successfully');

// Export utilities for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        UIManager,
        setButtonLoading,
        createStatusBadge
    };
}
