// src/services/apiClient.js
const API_BASE = window.location.origin.includes('localhost') 
  ? 'http://localhost:8080/api' 
  : '/api';

class ApiClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    // No agregar Content-Type para FormData
    if (options.body instanceof FormData) {
      delete config.headers['Content-Type'];
    }

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Error desconocido' }));
        throw new Error(errorData.message || `HTTP ${response.status}`);
      }

      const data = await response.json();
      
      if (data.status === 'error') {
        throw new Error(data.message || 'Error en la respuesta del servidor');
      }

      return { data, response };
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        throw new Error('Error de conexión. Verifica que el servidor esté ejecutándose.');
      }
      throw error;
    }
  }

  async get(endpoint, options = {}) {
    return this.request(endpoint, { method: 'GET', ...options });
  }

  async post(endpoint, data, options = {}) {
    const body = data instanceof FormData ? data : JSON.stringify(data);
    return this.request(endpoint, { method: 'POST', body, ...options });
  }

  async put(endpoint, data, options = {}) {
    const body = data instanceof FormData ? data : JSON.stringify(data);
    return this.request(endpoint, { method: 'PUT', body, ...options });
  }

  async delete(endpoint, options = {}) {
    return this.request(endpoint, { method: 'DELETE', ...options });
  }

  // Método helper para añadir company context
  withCompany(companyId) {
    return {
      get: (endpoint, options = {}) => this.get(endpoint, {
        ...options,
        headers: { 'X-Company-ID': companyId, ...options.headers }
      }),
      post: (endpoint, data, options = {}) => this.post(endpoint, data, {
        ...options,
        headers: { 'X-Company-ID': companyId, ...options.headers }
      }),
      put: (endpoint, data, options = {}) => this.put(endpoint, data, {
        ...options,
        headers: { 'X-Company-ID': companyId, ...options.headers }
      }),
      delete: (endpoint, options = {}) => this.delete(endpoint, {
        ...options,
        headers: { 'X-Company-ID': companyId, ...options.headers }
      })
    };
  }
}

export const apiClient = new ApiClient(API_BASE);
