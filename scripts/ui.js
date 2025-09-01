// scripts/ui.js - UI Utilities Module
'use strict';

/**
 * UI Utilities Manager for Multi-Tenant Admin Panel
 * Handles loading states, toasts, modals, and other UI interactions
 */
class UIManager {
    constructor() {
        this.toastCount = 0;
        this.maxToasts = window.APP_CONFIG.UI.max_toast_count || 5;
        this.toastDuration = window.APP_CONFIG.UI.toast_duration || 5000;
        this.isInitialized = false;
        
        this.init();
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

/**
 * Create progress indicator
 */
function createProgressIndicator(progress, showPercentage = true) {
    const container = document.createElement('div');
    container.className = 'progress-indicator';
    
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';
    
    const progressFill = document.createElement('div');
    progressFill.className = 'progress-fill';
    progressFill.style.width = `${Math.max(0, Math.min(100, progress))}%`;
    
    progressBar.appendChild(progressFill);
    container.appendChild(progressBar);
    
    if (showPercentage) {
        const percentage = document.createElement('span');
        percentage.className = 'progress-percentage';
        percentage.textContent = `${Math.round(progress)}%`;
        container.appendChild(percentage);
    }
    
    return container;
}

/**
 * Create collapsible section
 */
function createCollapsibleSection(title, content, isOpen = false) {
    const section = document.createElement('div');
    section.className = 'collapsible-section';
    
    const header = document.createElement('div');
    header.className = 'collapsible-header';
    header.innerHTML = `
        <span class="collapsible-title">${title}</span>
        <span class="collapsible-toggle">${isOpen ? '▼' : '▶'}</span>
    `;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'collapsible-content';
    contentDiv.style.display = isOpen ? 'block' : 'none';
    contentDiv.innerHTML = content;
    
    header.addEventListener('click', () => {
        const isCurrentlyOpen = contentDiv.style.display === 'block';
        contentDiv.style.display = isCurrentlyOpen ? 'none' : 'block';
        header.querySelector('.collapsible-toggle').textContent = isCurrentlyOpen ? '▶' : '▼';
    });
    
    section.appendChild(header);
    section.appendChild(contentDiv);
    
    return section;
}

/**
 * Create data table
 */
function createDataTable(data, columns, options = {}) {
    const table = document.createElement('table');
    table.className = 'data-table';
    
    // Create header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    columns.forEach(column => {
        const th = document.createElement('th');
        th.textContent = column.title || column.key;
        if (column.sortable) {
            th.classList.add('sortable');
            th.addEventListener('click', () => {
                // Implement sorting if needed
                console.log(`Sort by ${column.key}`);
            });
        }
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Create body
    const tbody = document.createElement('tbody');
    
    data.forEach((row, index) => {
        const tr = document.createElement('tr');
        
        columns.forEach(column => {
            const td = document.createElement('td');
            
            if (column.render) {
                td.innerHTML = column.render(row[column.key], row, index);
            } else {
                td.textContent = row[column.key] || '-';
            }
            
            tr.appendChild(td);
        });
        
        tbody.appendChild(tr);
    });
    
    table.appendChild(tbody);
    
    // Wrap in container for responsive scrolling
    const container = document.createElement('div');
    container.className = 'table-container';
    container.appendChild(table);
    
    return container;
}

/**
 * Create search filter input
 */
function createSearchFilter(placeholder = 'Buscar...', onSearch = null) {
    const container = document.createElement('div');
    container.className = 'search-filter';
    
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = placeholder;
    input.className = 'form-control';
    
    const icon = document.createElement('span');
    icon.className = 'search-icon';
    icon.textContent = '🔍';
    
    container.appendChild(icon);
    container.appendChild(input);
    
    if (onSearch) {
        const debouncedSearch = window.UI.debounce(onSearch, 300);
        input.addEventListener('input', (e) => {
            debouncedSearch(e.target.value);
        });
    }
    
    return container;
}

// Global UI manager instance
window.UI = new UIManager();

// Window resize handler for responsive updates
window.addEventListener('resize', window.UI.throttle(() => {
    window.UI.updateResponsiveUI();
}, 250));

// Initial responsive setup
document.addEventListener('DOMContentLoaded', () => {
    window.UI.updateResponsiveUI();
});

// Export utilities for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        UIManager,
        setButtonLoading,
        createStatusBadge,
        createProgressIndicator,
        createCollapsibleSection,
        createDataTable,
        createSearchFilter
    };
}
     * Initialize UI Manager
     */
    init() {
        if (this.isInitialized) return;
        
        this.setupToastContainer();
        this.setupLoadingOverlay();
        this.setupModalHandlers();
        this.setupKeyboardShortcuts();
        
        this.isInitialized = true;
        
        if (window.APP_CONFIG.DEBUG.enabled) {
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
        }, window.APP_CONFIG.UI.loading_timeout || 60000);
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
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
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

            // Add hover to pause auto-removal
            let timeoutId;
            const scheduleRemoval = () => {
                timeoutId = setTimeout(() => {
                    this.removeToast(toast);
                }, toastDuration);
            };

            toast.addEventListener('mouseenter', () => {
                clearTimeout(timeoutId);
            });

            toast.addEventListener('mouseleave', () => {
                scheduleRemoval();
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

    // ==================== FORM UTILITIES ====================

    /**
     * Disable form
     */
    disableForm(formId) {
        const form = document.getElementById(formId);
        if (form) {
            const inputs = form.querySelectorAll('input, textarea, select, button');
            inputs.forEach(input => {
                input.disabled = true;
            });
        }
    }

    /**
     * Enable form
     */
    enableForm(formId) {
        const form = document.getElementById(formId);
        if (form) {
            const inputs = form.querySelectorAll('input, textarea, select, button');
            inputs.forEach(input => {
                input.disabled = false;
            });
        }
    }

    /**
     * Clear form
     */
    clearForm(formId) {
        const form = document.getElementById(formId);
        if (form) {
            const inputs = form.querySelectorAll('input, textarea');
            inputs.forEach(input => {
                if (input.type !== 'file') {
                    input.value = '';
                }
            });

            const selects = form.querySelectorAll('select');
            selects.forEach(select => {
                select.selectedIndex = 0;
            });
        }
    }

    /**
     * Validate form
     */
    validateForm(formId) {
        const form = document.getElementById(formId);
        if (!form) return false;

        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        let firstInvalidField = null;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
                if (!firstInvalidField) {
                    firstInvalidField = field;
                }
            } else {
                field.classList.remove('is-invalid');
            }
        });

        if (!isValid && firstInvalidField) {
            firstInvalidField.focus();
        }

        return isValid;
    }

    // ==================== UTILITY FUNCTIONS ====================

    /**
     * Format date for display
     */
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return dateString;
        }
    }

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

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

    /**
     * Copy text to clipboard
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('✅ Copiado al portapapeles', 'success');
            return true;
        } catch {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {
                document.execCommand('copy');
                textArea.remove();
                this.showToast('✅ Copiado al portapapeles', 'success');
                return true;
            } catch {
                textArea.remove();
                this.showToast('❌ No se pudo copiar al portapapeles', 'error');
                return false;
            }
        }
    }

    /**
     * Animate element
     */
    animateElement(element, animation, duration = 300) {
        return new Promise((resolve) => {
            element.style.animation = `${animation} ${duration}ms ease`;
            
            setTimeout(() => {
                element.style.animation = '';
                resolve();
            }, duration);
        });
    }

    /**
     * Smooth scroll to element
     */
    scrollToElement(elementId, offset = 0) {
        const element = document.getElementById(elementId);
        if (element) {
            const elementPosition = element.offsetTop - offset;
            window.scrollTo({
                top: elementPosition,
                behavior: 'smooth'
            });
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
