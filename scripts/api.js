// scripts/api.js - API Communication Module with Railway Support
'use strict';

/**
 * API Manager for Multi-Tenant Chatbot
 * Handles all API communications with Railway production optimizations
 */
class APIManager {
    constructor() {
        this.baseURL = window.APP_CONFIG.API.BASE_URL;
        this.timeouts = window.APP_CONFIG.API.TIMEOUTS;
        this.isRailway = window.APP_CONFIG.ENV.is_railway;
        this.currentCompanyId = null;
        
        // Railway-specific configurations
        this.healthCheckRetries = 0;
        this.maxHealthCheckRetries = 3;
        this.scheduleServiceAvailable = null; // null = unknown, true/false = known status
        
        this.initializeHealthCheck();
    }

    /**
     * Initialize health check with Railway optimizations
     */
    async initializeHealthCheck() {
        if (this.isRailway) {
            // Check if schedule service is available (handle port 4040 error)
            await this.checkScheduleServiceAvailability();
        }
    }

    /**
     * Check if schedule service is available (handles port 4040 connection refused)
     */
    async checkScheduleServiceAvailability() {
        try {
            const response = await this.makeRequest('/health/schedule-service', {
                method: 'GET',
                timeout: 3000 // Short timeout for this check
            });
            
            this.scheduleServiceAvailable = response.status === 'success';
            
            if (window.APP_CONFIG.DEBUG.railway_debug.log_service_failures) {
                console.log('📅 Schedule service status:', this.scheduleServiceAvailable ? 'Available' : 'Unavailable');
            }
        } catch (error) {
            this.scheduleServiceAvailable = false;
            if (window.APP_CONFIG.DEBUG.railway_debug.log_service_failures) {
                console.warn('⚠️ Schedule service unavailable (port 4040 connection refused):', error.message);
            }
        }
    }

    /**
     * Set current company ID for multi-tenant requests
     */
    setCompanyId(companyId) {
        this.currentCompanyId = companyId;
    }

    /**
     * Get headers for API requests
     */
    getHeaders(additionalHeaders = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...additionalHeaders
        };

        // Add company context header if available
        if (this.currentCompanyId) {
            headers[window.APP_CONFIG.TENANT.company_context_header] = this.currentCompanyId;
        }

        return headers;
    }

    /**
     * Make API request with Railway optimizations and error handling
     */
    // CAMBIO MÍNIMO REQUERIDO EN scripts/api.js
    // Reemplaza SOLO la línea 79 por estas líneas:
    
    async makeRequest(endpoint, options = {}) {
        // FIX: Construir URL correctamente
        let url;
        if (endpoint.startsWith('http')) {
            url = endpoint;
        } else if (endpoint.startsWith('/')) {
            // Para rutas absolutas como '/health'
            url = `${this.baseURL}${endpoint}`;
        } else {
            // Para rutas relativas como 'companies' -> '/api/companies'
            url = `${this.baseURL}/api/${endpoint}`;
        }
        
        const timeout = options.timeout || this.timeouts.default;
        
        const requestOptions = {
            method: 'GET',
            headers: this.getHeaders(options.headers),
            ...options
        };
    
        // Create timeout controller
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
    
        try {
            const response = await fetch(url, {
                ...requestOptions,
                signal: controller.signal
            });
    
            clearTimeout(timeoutId);
    
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
    
            const data = await response.json();
            
            // Log API calls in development
            if (window.APP_CONFIG.DEBUG.log_api_calls) {
                console.log(`API Call: ${requestOptions.method} ${url}`, { options: requestOptions, response: data });
            }
    
            return data;
            
        } catch (error) {
            clearTimeout(timeoutId);
            
            // Handle Railway-specific errors
            if (this.isRailway) {
                return this.handleRailwayError(error, endpoint, options);
            }
            
            throw error;
        }
    }

    /**
     * Handle Railway-specific errors with graceful degradation
     */
    async handleRailwayError(error, endpoint, options) {
        // Handle schedule service connection refused (port 4040)
        if (error.message.includes('4040') || endpoint.includes('schedule')) {
            if (window.APP_CONFIG.RAILWAY_OPTIMIZATIONS.graceful_degradation.schedule_service) {
                console.warn('⚠️ Schedule service unavailable, using fallback mode');
                return {
                    status: 'warning',
                    message: 'Schedule service temporarily unavailable',
                    fallback_mode: true
                };
            }
        }

        // Handle connection timeouts
        if (error.name === 'AbortError') {
            if (this.healthCheckRetries < this.maxHealthCheckRetries) {
                this.healthCheckRetries++;
                console.warn(`⚠️ Request timeout, retrying (${this.healthCheckRetries}/${this.maxHealthCheckRetries})`);
                
                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, window.APP_CONFIG.RAILWAY.retry_delay));
                
                return this.makeRequest(endpoint, options);
            }
        }

        // Log Railway errors
        if (window.APP_CONFIG.DEBUG.railway_debug.log_service_failures) {
            console.error('🚨 Railway API Error:', {
                error: error.message,
                endpoint,
                timestamp: new Date().toISOString()
            });
        }

        throw error;
    }

    // ==================== COMPANY MANAGEMENT ====================

    /**
     * Get all companies
     */
    async getCompanies() {
        return this.makeRequest('companies');
    }

    /**
     * Get company status
     */
    async getCompanyStatus(companyId) {
        return this.makeRequest(`status/${companyId}`);
    }

    /**
     * Reload company configuration
     */
    async reloadCompanyConfig() {
        return this.makeRequest('admin/companies/reload-config', {
            method: 'POST'
        });
    }

    // ==================== HEALTH CHECKS ====================

    /**
     * System health check with Railway optimizations
     */
    async systemHealthCheck() {
        try {
            const health = await this.makeRequest('health', {
                timeout: this.timeouts.health_check
            });

            // Add schedule service status if known
            if (this.scheduleServiceAvailable !== null) {
                health.schedule_service_available = this.scheduleServiceAvailable;
            }

            return health;
        } catch (error) {
            // Return partial health status for Railway
            if (this.isRailway) {
                return {
                    status: 'partial',
                    message: 'Some services unavailable',
                    main_app: 'healthy',
                    schedule_service_available: this.scheduleServiceAvailable || false,
                    error: error.message
                };
            }
            throw error;
        }
    }

    /**
     * Company-specific health check
     */
    async companyHealthCheck(companyId) {
        return this.makeRequest(`health/company/${companyId}`, {
            timeout: this.timeouts.health_check
        });
    }

    // ==================== DOCUMENT MANAGEMENT ====================

    /**
     * Add document
     */
    async addDocument(content, metadata = {}) {
        return this.makeRequest('documents', {
            method: 'POST',
            body: JSON.stringify({
                content,
                metadata,
                company_id: this.currentCompanyId
            })
        });
    }

    /**
     * Bulk upload documents
     */
    async bulkUploadDocuments(files) {
        const formData = new FormData();
        
        for (let file of files) {
            formData.append('files', file);
        }
        
        if (this.currentCompanyId) {
            formData.append('company_id', this.currentCompanyId);
        }

        return this.makeRequest('documents/bulk-upload', {
            method: 'POST',
            headers: {
                // Remove Content-Type to let browser set it with boundary
                [window.APP_CONFIG.TENANT.company_context_header]: this.currentCompanyId
            },
            body: formData,
            timeout: this.timeouts.upload
        });
    }

    /**
     * Search documents
     */
    async searchDocuments(query, k = 3) {
        return this.makeRequest('documents/search', {
            method: 'POST',
            body: JSON.stringify({
                query,
                k,
                company_id: this.currentCompanyId
            })
        });
    }

    /**
     * List documents
     */
    async listDocuments() {
        return this.makeRequest(`documents?company_id=${this.currentCompanyId}`);
    }

    /**
     * Delete document
     */
    async deleteDocument(docId) {
        return this.makeRequest(`documents/${docId}`, {
            method: 'DELETE'
        });
    }

    // ==================== CHAT TESTING ====================

    /**
     * Send chat message
     */
    async sendChatMessage(message, userId, conversationId = null) {
        return this.makeRequest('chat', {
            method: 'POST',
            body: JSON.stringify({
                message,
                user_id: userId,
                conversation_id: conversationId,
                company_id: this.currentCompanyId
            })
        });
    }

    /**
     * Process voice message
     */
    async processVoiceMessage(audioFile, userId) {
        const formData = new FormData();
        formData.append('audio', audioFile);
        formData.append('user_id', userId);
        formData.append('company_id', this.currentCompanyId);

        return this.makeRequest('multimedia/process-voice', {
            method: 'POST',
            headers: {
                [window.APP_CONFIG.TENANT.company_context_header]: this.currentCompanyId
            },
            body: formData,
            timeout: this.timeouts.upload
        });
    }

    /**
     * Process image message
     */
    async processImageMessage(imageFile, question = '¿Qué hay en esta imagen?') {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('question', question);
        formData.append('company_id', this.currentCompanyId);

        return this.makeRequest('multimedia/process-image', {
            method: 'POST',
            headers: {
                [window.APP_CONFIG.TENANT.company_context_header]: this.currentCompanyId
            },
            body: formData,
            timeout: this.timeouts.upload
        });
    }

    // ==================== ADMIN OPERATIONS ====================

    /**
     * Reset company cache
     */
    async resetCompanyCache() {
        return this.makeRequest('admin/system/reset', {
            method: 'POST',
            body: JSON.stringify({
                reset_all: false,
                company_id: this.currentCompanyId
            })
        });
    }

    /**
     * Get system statistics
     */
    async getSystemStats() {
        return this.makeRequest(`admin/stats/${this.currentCompanyId}`);
    }

    /**
     * Cleanup orphaned vectors
     */
    async cleanupVectors(dryRun = false) {
        return this.makeRequest('documents/cleanup', {
            method: 'POST',
            body: JSON.stringify({
                dry_run: dryRun,
                company_id: this.currentCompanyId
            })
        });
    }

    /**
     * Force vectorstore recovery
     */
    async forceVectorRecovery() {
        return this.makeRequest('admin/vectorstore/force-recovery', {
            method: 'POST',
            body: JSON.stringify({
                company_id: this.currentCompanyId
            })
        });
    }

    /**
     * Get vectorstore protection status
     */
    async getProtectionStatus() {
        return this.makeRequest(`admin/vectorstore/protection-status?company_id=${this.currentCompanyId}`);
    }

    /**
     * Export configuration
     */
    async exportConfiguration() {
        return this.makeRequest(`admin/config/export?company_id=${this.currentCompanyId}`);
    }

    // ==================== GOOGLE CALENDAR INTEGRATION ====================

    /**
     * Get available slots for appointment scheduling
     */
    async getAvailableSlots(date, treatmentType) {
        // Check if schedule service is available
        if (this.scheduleServiceAvailable === false) {
            return {
                status: 'warning',
                message: 'Schedule service temporarily unavailable',
                available_slots: [],
                fallback_mode: true
            };
        }

        return this.makeRequest('schedule/available-slots', {
            method: 'POST',
            body: JSON.stringify({
                date,
                treatment_type: treatmentType,
                company_id: this.currentCompanyId
            })
        });
    }

    /**
     * Create appointment booking
     */
    async createAppointment(bookingData) {
        // Check if schedule service is available
        if (this.scheduleServiceAvailable === false) {
            return {
                status: 'warning',
                message: 'Appointment scheduling temporarily unavailable',
                fallback_mode: true
            };
        }

        return this.makeRequest('schedule/book', {
            method: 'POST',
            body: JSON.stringify({
                ...bookingData,
                company_id: this.currentCompanyId
            })
        });
    }
}

// ==================== UTILITY FUNCTIONS ====================

/**
 * Handle API errors with user-friendly messages
 */
function handleAPIError(error, context = '') {
    let message = 'Error desconocido';
    
    if (error.message) {
        if (error.message.includes('fetch')) {
            message = 'Error de conexión. Verifica tu conexión a internet.';
        } else if (error.message.includes('timeout')) {
            message = 'La solicitud ha tardado demasiado. Inténtalo de nuevo.';
        } else if (error.message.includes('4040')) {
            message = 'Servicio de agendamiento temporalmente no disponible.';
        } else if (error.message.includes('404')) {
            message = 'Recurso no encontrado.';
        } else if (error.message.includes('403')) {
            message = 'No tienes permisos para realizar esta acción.';
        } else if (error.message.includes('500')) {
            message = 'Error interno del servidor.';
        } else {
            message = error.message;
        }
    }
    
    if (context) {
        message = `${context}: ${message}`;
    }
    
    // Log detailed error in development
    if (window.APP_CONFIG.DEBUG.verbose_errors) {
        console.error('API Error Details:', error);
    }
    
    return message;
}

/**
 * Retry API call with exponential backoff
 */
async function retryAPICall(apiCall, maxRetries = 3, baseDelay = 1000) {
    let lastError;
    
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await apiCall();
        } catch (error) {
            lastError = error;
            
            if (i < maxRetries - 1) {
                const delay = baseDelay * Math.pow(2, i);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    
    throw lastError;
}

// Global API manager instance
window.API = new APIManager();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { APIManager, handleAPIError, retryAPICall };
}
