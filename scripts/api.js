// scripts/api.js - API Communication Layer
'use strict';

/**
 * API Client for Multi-Tenant Chatbot Admin Panel
 * Handles all HTTP requests and responses
 */
class APIClient {
    constructor() {
        this.config = window.APP_CONFIG.API;
        this.currentCompanyId = null;
        this.requestInterceptors = [];
        this.responseInterceptors = [];
        
        this.init();
    }
    
    init() {
        // Setup default request interceptors
        this.addRequestInterceptor(this.addCompanyHeader.bind(this));
        this.addRequestInterceptor(this.addDefaultHeaders.bind(this));
        
        // Setup default response interceptors
        this.addResponseInterceptor(this.logResponse.bind(this));
        this.addResponseInterceptor(this.handleErrors.bind(this));
        
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🌐 API Client initialized');
        }
    }
    
    /**
     * Set current company context
     */
    setCompanyContext(companyId) {
        this.currentCompanyId = companyId;
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🏢 Company context set to:', companyId);
        }
    }
    
    /**
     * Add request interceptor
     */
    addRequestInterceptor(interceptor) {
        this.requestInterceptors.push(interceptor);
    }
    
    /**
     * Add response interceptor
     */
    addResponseInterceptor(interceptor) {
        this.responseInterceptors.push(interceptor);
    }
    
    /**
     * Apply request interceptors
     */
    async applyRequestInterceptors(config) {
        let processedConfig = { ...config };
        
        for (const interceptor of this.requestInterceptors) {
            processedConfig = await interceptor(processedConfig) || processedConfig;
        }
        
        return processedConfig;
    }
    
    /**
     * Apply response interceptors
     */
    async applyResponseInterceptors(response) {
        let processedResponse = response;
        
        for (const interceptor of this.responseInterceptors) {
            processedResponse = await interceptor(processedResponse) || processedResponse;
        }
        
        return processedResponse;
    }
    
    /**
     * Default request interceptor - Add company header
     */
    addCompanyHeader(config) {
        if (this.currentCompanyId) {
            config.headers = config.headers || {};
            config.headers['X-Company-ID'] = this.currentCompanyId;
        }
        return config;
    }
    
    /**
     * Default request interceptor - Add default headers
     */
    addDefaultHeaders(config) {
        config.headers = {
            ...this.config.default_headers,
            ...(config.headers || {})
        };
        return config;
    }
    
    /**
     * Default response interceptor - Log response
     */
    logResponse(response) {
        if (window.APP_CONFIG.DEBUG.show_network_logs) {
            console.log('📡 API Response:', {
                url: response.url,
                status: response.status,
                company: this.currentCompanyId
            });
        }
        return response;
    }
    
    /**
     * Default response interceptor - Handle errors
     */
    async handleErrors(response) {
        if (!response.ok) {
            let errorMessage = window.APP_CONFIG.MESSAGES.errors.server;
            
            try {
                const errorData = await response.json();
                errorMessage = errorData.message || errorMessage;
            } catch {
                // Use default error message
            }
            
            const error = new Error(errorMessage);
            error.status = response.status;
            error.response = response;
            
            throw error;
        }
        
        return response;
    }
    
    /**
     * Make HTTP request
     */
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? 
            endpoint : 
            this.config.base_url + endpoint;
        
        let config = {
            method: 'GET',
            headers: {},
            timeout: this.config.timeout,
            ...options
        };
        
        // Apply request interceptors
        config = await this.applyRequestInterceptors(config);
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), config.timeout);
            
            const response = await fetch(url, {
                ...config,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            // Apply response interceptors
            const processedResponse = await this.applyResponseInterceptors(response);
            
            // Parse JSON response
            const data = await processedResponse.json();
            
            return data;
            
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error(window.APP_CONFIG.MESSAGES.errors.timeout);
            }
            
            if (!navigator.onLine) {
                throw new Error(window.APP_CONFIG.MESSAGES.errors.network);
            }
            
            throw error;
        }
    }
    
    /**
     * GET request
     */
    async get(endpoint, params = {}, options = {}) {
        const url = new URL(endpoint.startsWith('http') ? endpoint : this.config.base_url + endpoint);
        
        Object.keys(params).forEach(key => {
            if (params[key] !== undefined && params[key] !== null) {
                url.searchParams.append(key, params[key]);
            }
        });
        
        return this.request(url.toString(), {
            method: 'GET',
            ...options
        });
    }
    
    /**
     * POST request
     */
    async post(endpoint, data = null, options = {}) {
        const config = {
            method: 'POST',
            ...options
        };
        
        if (data) {
            if (data instanceof FormData) {
                config.body = data;
                // Remove Content-Type header for FormData (browser sets it automatically)
                if (config.headers && config.headers['Content-Type']) {
                    delete config.headers['Content-Type'];
                }
            } else {
                config.body = JSON.stringify(data);
            }
        }
        
        return this.request(endpoint, config);
    }
    
    /**
     * PUT request
     */
    async put(endpoint, data = null, options = {}) {
        return this.post(endpoint, data, { ...options, method: 'PUT' });
    }
    
    /**
     * DELETE request
     */
    async delete(endpoint, options = {}) {
        return this.request(endpoint, {
            method: 'DELETE',
            ...options
        });
    }
    
    // ===========================================
    // COMPANIES API METHODS
    // ===========================================
    
    /**
     * Get all companies
     */
    async getCompanies() {
        return this.get(this.config.endpoints.companies);
    }
    
    /**
     * Get company status
     */
    async getCompanyStatus(companyId) {
        const endpoint = window.APP_UTILS.formatUrl(
            this.config.endpoints.company_status,
            { id: companyId }
        );
        return this.get(endpoint);
    }
    
    /**
     * Get company health
     */
    async getCompanyHealth(companyId) {
        const endpoint = window.APP_UTILS.formatUrl(
            this.config.endpoints.company_health,
            { id: companyId }
        );
        return this.get(endpoint);
    }
    
    // ===========================================
    // DOCUMENTS API METHODS
    // ===========================================
    
    /**
     * Upload document file
     */
    async uploadDocument(formData) {
        return this.post(this.config.endpoints.upload_document, formData);
    }
    
    /**
     * Add document manually
     */
    async addDocument(content, metadata = {}) {
        return this.post(this.config.endpoints.documents, {
            content,
            metadata
        });
    }
    
    /**
     * Bulk add documents
     */
    async bulkAddDocuments(documents) {
        return this.post(this.config.endpoints.documents_bulk, {
            documents
        });
    }
    
    /**
     * Search documents
     */
    async searchDocuments(query, k = 3) {
        return this.post(this.config.endpoints.documents_search, {
            query,
            k
        });
    }
    
    /**
     * List documents
     */
    async listDocuments(page = 1, pageSize = 20) {
        return this.get(this.config.endpoints.documents, {
            page,
            page_size: pageSize
        });
    }
    
    /**
     * Delete document
     */
    async deleteDocument(docId) {
        return this.delete(`${this.config.endpoints.documents}/${docId}`);
    }
    
    /**
     * List vectors
     */
    async listVectors() {
        return this.get(this.config.endpoints.documents_vectors);
    }
    
    /**
     * Clean orphaned vectors
     */
    async cleanOrphanedVectors() {
        return this.delete(this.config.endpoints.documents_vectors_orphaned);
    }
    
    /**
     * Cleanup documents
     */
    async cleanupDocuments(dryRun = false) {
        return this.post(this.config.endpoints.documents_cleanup, {
            dry_run: dryRun
        });
    }
    
    // ===========================================
    // CHAT API METHODS
    // ===========================================
    
    /**
     * Send chat message
     */
    async sendChatMessage(message, userId = 'test_user') {
        return this.post(this.config.endpoints.chat_message, {
            message,
            user_id: userId,
            company_id: this.currentCompanyId
        });
    }
    
    /**
     * Get chat history
     */
    async getChatHistory(userId) {
        const endpoint = window.APP_UTILS.formatUrl(
            this.config.endpoints.chat_history,
            { userId }
        );
        return this.get(endpoint);
    }
    
    /**
     * Test conversation
     */
    async testConversation(userId, message) {
        const endpoint = window.APP_UTILS.formatUrl(
            this.config.endpoints.conversation_test,
            { userId }
        );
        return this.post(endpoint, { message });
    }
    
    /**
     * List conversations
     */
    async listConversations(page = 1, pageSize = 20) {
        return this.get(this.config.endpoints.conversations, {
            page,
            page_size: pageSize
        });
    }
    
    /**
     * Delete conversation
     */
    async deleteConversation(userId) {
        return this.delete(`${this.config.endpoints.conversations}/${userId}`);
    }
    
    // ===========================================
    // MULTIMEDIA API METHODS
    // ===========================================
    
    /**
     * Transcribe audio
     */
    async transcribeAudio(audioFile, processWithChat = false, userId = 'multimedia_user') {
        const formData = new FormData();
        formData.append('audio', audioFile);
        formData.append('process_chat', processWithChat.toString());
        formData.append('user_id', userId);
        
        return this.post(this.config.endpoints.audio_transcribe, formData);
    }
    
    /**
     * Analyze image
     */
    async analyzeImage(imageFile, message = 'Analiza esta imagen', processWithChat = false, userId = 'multimedia_user') {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('message', message);
        formData.append('process_chat', processWithChat.toString());
        formData.append('user_id', userId);
        
        return this.post(this.config.endpoints.image_analyze, formData);
    }
    
    /**
     * Capture and analyze image
     */
    async captureImage(imageDataURL, message = 'Analiza esta imagen capturada', userId = 'camera_user') {
        return this.post(this.config.endpoints.image_capture, {
            image_data: imageDataURL,
            message,
            user_id: userId
        });
    }
    
    /**
     * Process voice message (legacy endpoint)
     */
    async processVoiceMessage(audioFile, userId = 'test_user') {
        const formData = new FormData();
        formData.append('audio', audioFile);
        formData.append('user_id', userId);
        formData.append('company_id', this.currentCompanyId);
        
        return this.post(this.config.endpoints.process_voice, formData);
    }
    
    /**
     * Process image message (legacy endpoint)
     */
    async processImageMessage(imageFile, question = '¿Qué hay en esta imagen?', userId = 'test_user') {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('user_id', userId);
        formData.append('question', question);
        formData.append('company_id', this.currentCompanyId);
        
        return this.post(this.config.endpoints.process_image, formData);
    }
    
    // ===========================================
    // CONFIGURATION API METHODS
    // ===========================================
    
    /**
     * Get company configuration
     */
    async getConfiguration() {
        return this.get(this.config.endpoints.configuration);
    }
    
    /**
     * Update company configuration
     */
    async updateConfiguration(configData) {
        return this.post(this.config.endpoints.configuration, configData);
    }
    
    /**
     * Update Google Calendar configuration
     */
    async updateGoogleCalendarConfig(gcalConfig) {
        return this.post(this.config.endpoints.google_calendar_config, gcalConfig);
    }
    
    /**
     * Update Schedule Agent configuration
     */
    async updateScheduleAgentConfig(scheduleConfig) {
        return this.post(this.config.endpoints.schedule_agent_config, scheduleConfig);
    }
    
    // ===========================================
    // ADMIN API METHODS
    // ===========================================
    
    /**
     * Get system health
     */
    async getSystemHealth() {
        return this.get(this.config.endpoints.health);
    }
    
    /**
     * Get admin status
     */
    async getAdminStatus() {
        return this.get(this.config.endpoints.admin_status);
    }
    
    /**
     * Reset system cache
     */
    async resetSystemCache(resetAll = false) {
        return this.post(this.config.endpoints.admin_reset, {
            reset_all: resetAll
        });
    }
    
    /**
     * Reload configuration
     */
    async reloadConfiguration() {
        return this.post(this.config.endpoints.admin_reload_config);
    }
}

// Create global API instance
window.API = new APIClient();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIClient;
}

console.log('✅ API module loaded successfully');
