// src/components/AdminPanel.js - Panel de administración del sistema

import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const AdminPanel = ({ company, companies, systemStatus, onRefresh }) => {
  const [diagnostics, setDiagnostics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [multimedia, setMultimedia] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);

  useEffect(() => {
    loadSystemInfo();
  }, []);

  const loadSystemInfo = async () => {
    try {
      const info = await apiService.getSystemInfo();
      setSystemInfo(info);
    } catch (err) {
      console.error('Error loading system info:', err);
    }
  };

  const runDiagnostics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await apiService.runDiagnostics();
      setDiagnostics(result);
    } catch (err) {
      console.error('Error running diagnostics:', err);
      setError('Error ejecutando diagnósticos: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const reloadCompaniesConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await apiService.reloadCompaniesConfig();
      if (result.success) {
        onRefresh(); // Refrescar datos de la app
      } else {
        throw new Error(result.error || 'Error recargando configuración');
      }
    } catch (err) {
      console.error('Error reloading companies:', err);
      setError('Error recargando empresas: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const testMultimedia = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await apiService.testMultimedia();
      setMultimedia(result);
    } catch (err) {
      console.error('Error testing multimedia:', err);
      setError('Error probando multimedia: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-gray-900">
          Panel de Administración
        </h2>
        <p className="text-gray-600 mt-1">
          Herramientas de diagnóstico y administración del sistema
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div className="ml-3">
              <p className="text-red-800">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-400 hover:text-red-600"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Admin Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Diagnósticos del Sistema
          </h3>
          <p className="text-gray-600 mb-4">
            Ejecutar diagnósticos completos del sistema multi-tenant
          </p>
          <button
            onClick={runDiagnostics}
            disabled={loading}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? <LoadingSpinner size="small" /> : null}
            <span>Ejecutar Diagnósticos</span>
          </button>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Recargar Configuración
          </h3>
          <p className="text-gray-600 mb-4">
            Recargar configuración de empresas desde archivos
          </p>
          <button
            onClick={reloadCompaniesConfig}
            disabled={loading}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            {loading ? <LoadingSpinner size="small" /> : null}
            <span>Recargar Config</span>
          </button>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Test Multimedia
          </h3>
          <p className="text-gray-600 mb-4">
            Probar integración de multimedia para la empresa actual
          </p>
          <button
            onClick={testMultimedia}
            disabled={loading || !company}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            {loading ? <LoadingSpinner size="small" /> : null}
            <span>Test Multimedia</span>
          </button>
        </div>
      </div>

      {/* System Information */}
      {systemInfo && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Información del Sistema
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">General</h4>
              <div className="space-y-1 text-sm text-gray-600">
                <p>Tipo: {systemInfo.system_type}</p>
                <p>Versión: {systemInfo.version}</p>
                <p>Empresas configuradas: {systemInfo.companies_configured}</p>
                <p>Estado: {systemInfo.status}</p>
              </div>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Características</h4>
              <div className="space-y-1 text-sm text-gray-600">
                {systemInfo.features?.map((feature, index) => (
                  <p key={index}>• {feature}</p>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Companies List */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Empresas Configuradas ({companies.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ID / Nombre
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Industria
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Servicios
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Config. Extendida
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {companies.map((comp) => (
                <tr key={comp.company_id} className={`hover:bg-gray-50 ${
                  company?.company_id === comp.company_id ? 'bg-blue-50' : ''
                }`}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {comp.company_name}
                      </div>
                      <div className="text-sm text-gray-500">
                        {comp.company_id}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {comp.industry || 'No especificada'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {comp.services_count || 0}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      comp.has_extended_config 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {comp.has_extended_config ? 'Activa' : 'No configurada'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Diagnostics Results */}
      {diagnostics && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Resultados de Diagnósticos
          </h3>
          <div className="bg-gray-50 rounded p-4 overflow-x-auto">
            <pre className="text-sm text-gray-800">
              {JSON.stringify(diagnostics, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Multimedia Test Results */}
      {multimedia && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Resultados de Test Multimedia
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Empresa</h4>
              <p className="text-sm text-gray-600">{multimedia.company_id}</p>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">OpenAI Service</h4>
              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                multimedia.openai_service_available 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                {multimedia.openai_service_available ? 'Disponible' : 'No disponible'}
              </span>
            </div>
          </div>
          
          {multimedia.multimedia_integration && (
            <div className="mt-4">
              <h4 className="font-medium text-gray-900 mb-2">Integración Multimedia</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(multimedia.multimedia_integration).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">{key.replace(/_/g, ' ')}</span>
                    <span className={`text-sm ${value ? 'text-green-600' : 'text-red-600'}`}>
                      {value ? '✓' : '✗'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AdminPanel;
