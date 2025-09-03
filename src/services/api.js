// src/services/api.js - Servicio de API corregido con endpoints exactos del backend

class APIService {
  constructor() {
    // Detectar entorno automáticamente
    this.baseURL = this.detectEnvironment();
    this.companyId = null;
    this.defaultTimeout = 15000; // 15 segundos
    
    console.log(`🔗 API Service initialized with baseURL: ${this.baseURL}`);
  }

  detectEnvironment() {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    const port = window.location.port;

    // Railway production
    if (hostname.includes('railway.app') || hostname.includes('.up.railway.app')) {
      return `${protocol}//${hostname}`;
    }
    
    // Desarrollo local
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      // Si estamos en el puerto del frontend, usar el puerto del backend
      if (port === '3000') {
        return `${protocol}//${hostname}:8080`;
      }
      return `${protocol}//${hostname}:${port || 8080}`;
    }
    
    // Por defecto, usar la misma origin
    return `${protocol}//${hostname}${port ? ':' + port : ''}`;
  }

  setCompanyId(companyId) {
    this.companyId = companyId;
    console.log(`🏢 Company ID set to: ${companyId}`);
  }

  getHeaders(includeCompany = true) {
    const headers = {
      'Content-Type': 'application/json',
    };

    if (includeCompany && this.companyId) {
      headers['X-Company-ID'] = this.companyId;
    }

    return headers;
  }

  async makeRequest(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const requestOptions = {
      timeout: this.defaultTimeout,
      headers: this.getHeaders(options.includeCompany !== false),
      ...options
    };

    // Si hay company_id y es una petición GET, añadirlo como query param también
    if (this.companyId && (!options.method || options.method === 'GET')) {
      const separator = endpoint.includes('?') ? '&' : '?';
      // Solo añadir company_id si no está ya en la URL
      if (!endpoint.includes('company_id=') && !endpoint.includes('/companies')) {
        endpoint += `${separator}company_id=${this.companyId}`;
      }
    }

    try {
      console.log(`📡 API Request: ${options.method || 'GET'} ${url}`);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), requestOptions.timeout);

      const response = await fetch(url, {
        ...requestOptions,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const responseData = await this.handleResponse(response);
      console.log(`✅ API Response: ${response.status}`, responseData);
      return responseData;
      
    } catch (error) {
      console.error(`❌ API Error: ${options.method || 'GET'} ${url}:`, error);
      throw this.processError(error);
    }
  }

  async handleResponse(response) {
    const contentType = response.headers.get('content-type');
    
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      
      try {
        if (contentType?.includes('application/json')) {
          const errorData = await response.json();
          errorMessage = errorData.message || errorData.error || errorMessage;
        } else {
          errorMessage = await response.text();
        }
      } catch (e) {
        // Si no se puede leer el error, usar el mensaje por defecto
      }
      
      throw new Error(errorMessage);
    }

    if (contentType?.includes('application/json')) {
      return await response.json();
    } else {
      return await response.text();
    }
  }

  processError(error) {
    if (error.name === 'AbortError') {
      return new Error('La petición tardó demasiado. Verifica tu conexión a internet.');
    }
    
    if (error.message.includes('Failed to fetch')) {
      return new Error('No se pudo conectar con el servidor. Verifica tu conexión a internet.');
    }
    
    if (error.message.includes('HTTP 404')) {
      return new Error('El recurso solicitado no fue encontrado');
    }
    
    if (error.message.includes('HTTP 500')) {
      return new Error('Error interno del servidor');
    }
    
    return error;
  }

  // ============================================================================
  // ENDPOINTS DE EMPRESAS
  // ============================================================================
  
  async getCompanies() {
    try {
      return await this.makeRequest('/api/companies', {
        includeCompany: false
      });
    } catch (error) {
      console.error('Error getting companies:', error);
      throw error;
    }
  }

  async getCompanyDetails(companyId) {
    try {
      const originalCompanyId = this.companyId;
      this.companyId = companyId;
      
      const result = await this.makeRequest(`/api/companies/${companyId}`);
      
      this.companyId = originalCompanyId;
      return result;
    } catch (error) {
      console.error(`Error getting company details for ${companyId}:`, error);
      throw error;
    }
  }

  async getCompanyStatus(companyId) {
    try {
      return await this.makeRequest(`/api/companies/${companyId}/status`, {
        includeCompany: false
      });
    } catch (error) {
      console.error(`Error getting company status for ${companyId}:`, error);
      throw error;
    }
  }

  // ============================================================================
  // ENDPOINTS DE SALUD Y SISTEMA
  // ============================================================================
  
  async getSystemHealth() {
    try {
      return await this.makeRequest('/api/health', {
        includeCompany: false
      });
    } catch (error) {
      console.error('Error getting system health:', error);
      // No lanzar error para health check, devolver estado de error
      return {
        status: 'error',
        message: 'No se pudo conectar con el sistema',
        error: error.message
      };
    }
  }

  async getSystemInfo() {
    try {
      return await this.makeRequest('/api/system/info', {
        includeCompany: false
      });
    } catch (error) {
      console.error('Error getting system info:', error);
      throw error;
    }
  }

  // ============================================================================
  // ENDPOINTS DE DOCUMENTOS
  // ============================================================================
  
  async getDocuments() {
    if (!this.companyId) {
      throw new Error('Company ID is required to get documents');
    }
    
    try {
      return await this.makeRequest('/api/documents');
    } catch (error) {
      console.error('Error getting documents:', error);
      throw error;
    }
  }

  async uploadDocument(formData) {
    if (!this.companyId) {
      throw new Error('Company ID is required to upload document');
    }

    try {
      // Para FormData, no establecer Content-Type (el navegador lo hace automáticamente)
      const headers = {};
      if (this.companyId) {
        headers['X-Company-ID'] = this.companyId;
      }

      const url = `${this.baseURL}/api/documents?company_id=${this.companyId}`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: headers,
        body: formData
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error('Error uploading document:', error);
      throw error;
    }
  }

  async deleteDocument(documentId) {
    if (!this.companyId) {
      throw new Error('Company ID is required to delete document');
    }

    try {
      return await this.makeRequest(`/api/documents/${documentId}`, {
        method: 'DELETE'
      });
    } catch (error) {
      console.error(`Error deleting document ${documentId}:`, error);
      throw error;
    }
  }

  async getDocumentStats() {
    if (!this.companyId) {
      throw new Error('Company ID is required to get document stats');
    }
    
    try {
      return await this.makeRequest('/api/documents/stats');
    } catch (error) {
      console.error('Error getting document stats:', error);
      throw error;
    }
  }

  // ============================================================================
  // ENDPOINTS DE CONVERSACIONES
  // ============================================================================
  
  async getConversations() {
    if (!this.companyId) {
      throw new Error('Company ID is required to get conversations');
    }
    
    try {
      return await this.makeRequest('/api/conversations');
    } catch (error) {
      console.error('Error getting conversations:', error);
      throw error;
    }
  }

  async getConversation(conversationId) {
    if (!this.companyId) {
      throw new Error('Company ID is required to get conversation');
    }
    
    try {
      return await this.makeRequest(`/api/conversations/${conversationId}`);
    } catch (error) {
      console.error(`Error getting conversation ${conversationId}:`, error);
      throw error;
    }
  }

  async sendMessage(message, conversationId = null, userId = 'web-user') {
    if (!this.companyId) {
      throw new Error('Company ID is required to send message');
    }
    
    try {
      const payload = {
        message: message.trim(),
        user_id: userId,
        company_id: this.companyId
      };

      if (conversationId) {
        payload.conversation_id = conversationId;
      }

      return await this.makeRequest('/api/conversations/message', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }

  async getConversationsStats() {
    if (!this.companyId) {
      throw new Error('Company ID is required to get conversation stats');
    }
    
    try {
      return await this.makeRequest('/api/conversations/stats');
    } catch (error) {
      console.error('Error getting conversation stats:', error);
      throw error;
    }
  }

  // ============================================================================
  // ENDPOINTS DE ADMIN
  // ============================================================================
  
  async runDiagnostics() {
    try {
      return await this.makeRequest('/api/admin/diagnostics', {
        includeCompany: false
      });
    } catch (error) {
      console.error('Error running diagnostics:', error);
      throw error;
    }
  }

  async reloadCompaniesConfig() {
    try {
      return await this.makeRequest('/api/admin/config/reload', {
        method: 'POST',
        includeCompany: false
      });
    } catch (error) {
      console.error('Error reloading companies config:', error);
      throw error;
    }
  }

  async updateGoogleCalendarConfig(companyId, googleCalendarUrl) {
    try {
      const payload = {
        company_id: companyId,
        google_calendar_url: googleCalendarUrl
      };

      return await this.makeRequest('/api/admin/config/google-calendar', {
        method: 'POST',
        body: JSON.stringify(payload),
        includeCompany: false
      });
    } catch (error) {
      console.error('Error updating Google Calendar config:', error);
      throw error;
    }
  }

  async clearVectors(companyId) {
    try {
      const payload = {
        company_id: companyId
      };

      return await this.makeRequest('/api/admin/vectors/clear', {
        method: 'POST',
        body: JSON.stringify(payload),
        includeCompany: false
      });
    } catch (error) {
      console.error('Error clearing vectors:', error);
      throw error;
    }
  }

  async rebuildVectors(companyId) {
    try {
      const payload = {
        company_id: companyId
      };

      return await this.makeRequest('/api/admin/vectors/rebuild', {
        method: 'POST',
        body: JSON.stringify(payload),
        includeCompany: false
      });
    } catch (error) {
      console.error('Error rebuilding vectors:', error);
      throw error;
    }
  }

  // ============================================================================
  // ENDPOINTS DE MULTIMEDIA
  // ============================================================================
  
  async processAudio(formData) {
    if (!this.companyId) {
      throw new Error('Company ID is required to process audio');
    }

    try {
      // Añadir company_id al FormData
      formData.append('company_id', this.companyId);

      // Para FormData, no establecer Content-Type
      const headers = {};
      if (this.companyId) {
        headers['X-Company-ID'] = this.companyId;
      }

      const url = `${this.baseURL}/api/multimedia/process-voice`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: headers,
        body: formData
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error('Error processing audio:', error);
      throw error;
    }
  }
}

// Crear instancia singleton
const apiService = new APIService();

export { apiService };
export default apiService;
