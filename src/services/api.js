// src/services/api.js - Servicio completo de API para comunicación con backend

class ApiService {
  constructor() {
    // Detectar URL base del API
    this.baseURL = process.env.REACT_APP_API_URL || '';
    this.defaultHeaders = {
      'Content-Type': 'application/json'
    };
    
    console.log('🔗 API Service initialized with base URL:', this.baseURL);
  }

  // Método genérico para hacer requests
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: { ...this.defaultHeaders, ...options.headers },
      ...options
    };

    console.log(`📡 API Request: ${options.method || 'GET'} ${endpoint}`);

    try {
      const response = await fetch(url, config);
      
      // Log de respuesta
      console.log(`📡 API Response: ${response.status} ${response.statusText}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.message || errorData.error || errorMessage;
        } catch {
          errorMessage = errorText || errorMessage;
        }
        
        throw new Error(errorMessage);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return await response.text();
    } catch (error) {
      console.error(`❌ API Error for ${endpoint}:`, error);
      throw error;
    }
  }

  // ========================================
  // SYSTEM & HEALTH ENDPOINTS
  // ========================================
  
  async getSystemInfo() {
    return await this.request('/api/system/info');
  }

  async getSystemHealth(companyId = null) {
    const params = companyId ? `?company_id=${companyId}` : '';
    return await this.request(`/api/health/full${params}`);
  }

  // ========================================
  // COMPANIES MANAGEMENT
  // ========================================
  
  async getCompanies() {
    return await this.request('/api/companies');
  }

  async getCompanyDetails(companyId) {
    return await this.request(`/api/companies/${companyId}`);
  }

  async getCompanyHealth(companyId) {
    return await this.request(`/api/companies/${companyId}/health`);
  }

  async getCompanyStats(companyId) {
    return await this.request(`/api/companies/${companyId}/stats`);
  }

  // ========================================
  // CHAT & CONVERSATIONS
  // ========================================
  
  async sendMessage(message, conversationId = null, userId = null, companyId = null) {
    const payload = {
      message,
      conversation_id: conversationId,
      user_id: userId || `user_${Date.now()}`,
      company_id: companyId
    };

    return await this.request('/api/webhook/chatwoot', {
      method: 'POST',
      headers: {
        ...(companyId && { 'X-Company-ID': companyId })
      },
      body: JSON.stringify(payload)
    });
  }

  async getConversations(companyId, page = 1, limit = 20) {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString()
    });
    
    return await this.request(`/api/conversations?${params}`, {
      headers: {
        'X-Company-ID': companyId
      }
    });
  }

  async getConversationDetails(conversationId, companyId) {
    return await this.request(`/api/conversations/${conversationId}`, {
      headers: {
        'X-Company-ID': companyId
      }
    });
  }

  async getConversationStats(companyId) {
    return await this.request('/api/conversations/stats', {
      headers: {
        'X-Company-ID': companyId
      }
    });
  }

  // ========================================
  // DOCUMENT MANAGEMENT
  // ========================================
  
  async getDocuments(companyId, page = 1, limit = 50) {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString()
    });
    
    return await this.request(`/api/documents?${params}`, {
      headers: {
        'X-Company-ID': companyId
      }
    });
  }

  async uploadDocument(formData) {
    // Para FormData, no establecer Content-Type (el browser lo hace automáticamente)
    return await this.request('/api/documents/upload', {
      method: 'POST',
      headers: {}, // Sin Content-Type para FormData
      body: formData
    });
  }

  async uploadMultipleDocuments(formData) {
    return await this.request('/api/documents/bulk-upload', {
      method: 'POST',
      headers: {},
      body: formData
    });
  }

  async searchDocuments(query, companyId, filters = {}) {
    const payload = {
      query,
      company_id: companyId,
      ...filters
    };

    return await this.request('/api/documents/search', {
      method: 'POST',
      headers: {
        'X-Company-ID': companyId
      },
      body: JSON.stringify(payload)
    });
  }

  async deleteDocument(documentId, companyId) {
    return await this.request(`/api/documents/${documentId}`, {
      method: 'DELETE',
      headers: {
        'X-Company-ID': companyId
      }
    });
  }

  async getDocumentContent(documentId, companyId) {
    return await this.request(`/api/documents/${documentId}/content`, {
      headers: {
        'X-Company-ID': companyId
      }
    });
  }

  // ========================================
  // MULTIMEDIA PROCESSING
  // ========================================
  
  async uploadAudio(audioBlob, companyId, userId = null) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'audio.wav');
    formData.append('company_id', companyId);
    if (userId) {
      formData.append('user_id', userId);
    }

    return await this.request('/api/multimedia/audio/upload', {
      method: 'POST',
      headers: {},
      body: formData
    });
  }

  async uploadImage(imageBlob, companyId, userId = null) {
    const formData = new FormData();
    formData.append('image', imageBlob, 'image.jpg');
    formData.append('company_id', companyId);
    if (userId) {
      formData.append('user_id', userId);
    }

    return await this.request('/api/multimedia/image/upload', {
      method: 'POST',
      headers: {},
      body: formData
    });
  }

  async processMultimedia(formData) {
    return await this.request('/api/multimedia/process', {
      method: 'POST',
      headers: {},
      body: formData
    });
  }

  // ========================================
  // ADMIN & DIAGNOSTICS
  // ========================================
  
  async runDiagnostics(companyId = null) {
    const payload = companyId ? { company_id: companyId } : {};
    
    return await this.request('/api/admin/diagnostics', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async cleanupVectorstore(companyId) {
    return await this.request('/api/admin/cleanup-vectorstore', {
      method: 'POST',
      headers: {
        'X-Company-ID': companyId
      },
      body: JSON.stringify({ company_id: companyId })
    });
  }

  async resetCompanyCache(companyId) {
    return await this.request(`/api/admin/companies/${companyId}/reset-cache`, {
      method: 'POST'
    });
  }

  async getSystemLogs(level = 'INFO', limit = 100) {
    const params = new URLSearchParams({
      level,
      limit: limit.toString()
    });
    
    return await this.request(`/api/admin/logs?${params}`);
  }

  async getMetrics(companyId = null, timeRange = '1h') {
    const params = new URLSearchParams({ time_range: timeRange });
    if (companyId) {
      params.append('company_id', companyId);
    }
    
    return await this.request(`/api/admin/metrics?${params}`);
  }

  // ========================================
  // EXTENDED FEATURES
  // ========================================
  
  async getCalendarEvents(companyId, startDate, endDate) {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate
    });
    
    return await this.request(`/api/companies/${companyId}/calendar/events?${params}`);
  }

  async createCalendarEvent(companyId, eventData) {
    return await this.request(`/api/companies/${companyId}/calendar/events`, {
      method: 'POST',
      headers: {
        'X-Company-ID': companyId
      },
      body: JSON.stringify(eventData)
    });
  }

  async testCompanyServices(companyId) {
    return await this.request(`/api/companies/${companyId}/test-services`, {
      method: 'POST'
    });
  }

  // ========================================
  // UTILITY METHODS
  // ========================================
  
  // Test de conectividad
  async testConnection() {
    try {
      const response = await this.getSystemInfo();
      return {
        success: true,
        data: response,
        message: 'Conexión exitosa'
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        message: 'Error de conexión'
      };
    }
  }

  // Obtener información de debug
  async getDebugInfo() {
    return await this.request('/debug/build-structure');
  }

  // Helper para construir headers con company context
  getCompanyHeaders(companyId) {
    return {
      ...this.defaultHeaders,
      'X-Company-ID': companyId
    };
  }

  // Helper para manejar respuestas con paginación
  async getPaginatedData(endpoint, companyId = null, page = 1, limit = 20) {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString()
    });
    
    const headers = companyId ? this.getCompanyHeaders(companyId) : this.defaultHeaders;
    
    return await this.request(`${endpoint}?${params}`, { headers });
  }
}

// Crear instancia global del servicio
export const apiService = new ApiService();

// Configurar interceptores globales para debugging en desarrollo
if (process.env.NODE_ENV === 'development') {
  console.log('🔧 API Service running in development mode');
  
  // Log de todas las requests en desarrollo
  const originalRequest = apiService.request.bind(apiService);
  apiService.request = async function(endpoint, options = {}) {
    const startTime = performance.now();
    
    try {
      const result = await originalRequest(endpoint, options);
      const duration = Math.round(performance.now() - startTime);
      console.log(`✅ API Success: ${endpoint} (${duration}ms)`, result);
      return result;
    } catch (error) {
      const duration = Math.round(performance.now() - startTime);
      console.error(`❌ API Error: ${endpoint} (${duration}ms)`, error);
      throw error;
    }
  };
}

export default ApiService;
