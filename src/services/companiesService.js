// src/services/companiesService.js
import { apiClient } from './apiClient';

export const companiesService = {
  async getAll() {
    const response = await apiClient.get('/companies');
    return response.data;
  },

  async getById(companyId) {
    const response = await apiClient.get(`/companies/${companyId}`);
    return response.data;
  },

  async getStatus(companyId) {
    const response = await apiClient.get(`/companies/${companyId}/status`);
    return response.data;
  },

  async reloadConfig() {
    const response = await apiClient.post('/admin/companies/reload-config');
    return response.data;
  },

  async updateGoogleCalendar(companyId, url) {
    const response = await apiClient.post('/admin/config/google-calendar', {
      company_id: companyId,
      google_calendar_url: url
    }, {
      headers: {
        'X-Company-ID': companyId
      }
    });
    return response.data;
  }
};
