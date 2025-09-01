// scripts/config.js - Configuration Module (EMERGENCY FIX VERSION)
'use strict';

/**
 * Global Configuration for Multi-Tenant Admin Panel
 * EMERGENCY VERSION - Ensures all required objects are defined
 */

// Ensure this loads first and defines all required global objects
(function initializeGlobalConfig() {
    // Define APP_CONFIG first
    window.APP_CONFIG = {
        // Environment Configuration
        ENV: {
            is_development: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1',
            is_railway: window.location.hostname.includes('railway') || window.location.hostname.includes('.app'),
            is_production: window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
        },
        
        // API Configuration
        API: {
            BASE_URL: window.location.origin,
            TIMEOUTS: {
                default: 10000,
                upload: 30000,
                health_check: 5000
            }
        },
        
        // Debug Configuration
        DEBUG: {
            enabled: window.location.hostname === 'localhost' || window.location.search.includes('debug=true'),
            verbose_errors: window.location.search.includes('verbose=true'),
            railway_debug: {
                log_health_checks: true,
                log_service_failures: true
            }
        },
        
        // UI Configuration
        UI: {
            max_toast_count: 5,
            toast_duration: 5000,
            loading_timeout: 30000
        },
        
        // Multi-tenant Configuration
        TENANT: {
            company_context_header: 'X-Company-ID',
            auto_select_first_company: true
        }
    };

    // Basic UI Manager (simplified version to prevent errors)
    window.UI = {
        showLoading: function(message = 'Cargando...') {
            console.log('🔄 Loading:', message);
            const overlay = document.getElementById('loadingOverlay');
            const messageEl = document.getElementById('loadingMessage');
            
            if (overlay) {
                overlay.style.display = 'flex';
                if (messageEl) messageEl.textContent = message;
            }
        },
        
        hideLoading: function() {
            console.log('✅ Loading complete');
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {
                overlay.style.display = 'none';
            }
        },
        
        showToast: function(message, type = 'info') {
            console.log(`📢 Toast (${type}):`, message);
            
            // Create toast element
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            toast.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : type === 'warning' ? '#ffc107' : '#007bff'};
                color: ${type === 'warning' ? '#000' : '#fff'};
                border-radius: 4px;
                z-index: 10000;
                max-width: 300px;
                word-wrap: break-word;
                font-size: 14px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            `;
            
            // Add to container or body
            const container = document.getElementById('toastContainer') || document.body;
            container.appendChild(toast);
            
            // Auto remove
            setTimeout(() => {
                if (toast && toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 5000);
        }
    };

    // Basic API Manager (simplified version to prevent errors)
    window.API = {
        baseURL: window.location.origin,
        currentCompanyId: null,
        scheduleServiceAvailable: false,
        
        setCompanyId: function(companyId) {
            this.currentCompanyId = companyId;
            console.log('🏢 Company context set to:', companyId);
        },
        
        makeRequest: async function(endpoint, options = {}) {
            try {
                const url = endpoint.startsWith('http') ? endpoint : this.baseURL + (endpoint.startsWith('/') ? endpoint : '/' + endpoint);
                
                const response = await fetch(url, {
                    timeout: 10000,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Company-ID': this.currentCompanyId || ''
                    },
                    ...options
                });
                
                if (!response.ok) {
                    throw new Error(`API Error: ${response.status} ${response.statusText}`);
                }
                
                return await response.json();
            } catch (error) {
                console.error('API Request failed:', error);
                throw error;
            }
        },
        
        getCompanies: async function() {
            try {
                return await this.makeRequest('/api/companies');
            } catch (error) {
                console.warn('Companies API failed, using fallback');
                return {
                    companies: {
                        'fallback': {
                            name: 'Modo de Emergencia',
                            status: 'warning'
                        }
                    }
                };
            }
        },
        
        systemHealthCheck: async function() {
            try {
                return await this.makeRequest('/health');
            } catch (error) {
                console.warn('Health check failed');
                return {
                    status: 'degraded',
                    message: 'Health check unavailable'
                };
            }
        }
    };

    // Log successful config initialization
    console.log('✅ Emergency config initialized');
    console.log('🔧 Environment:', window.APP_CONFIG.ENV);
    
    // Mark as ready
    window.CONFIG_READY = true;
    
})();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.APP_CONFIG;
}
