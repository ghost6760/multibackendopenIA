// src/components/Dashboard.js - Panel principal del dashboard

import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const Dashboard = ({ company, systemStatus, onRefresh }) => {
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (company) {
      loadDashboardData();
    }
  }, [company]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [documentsStats, conversations] = await Promise.allSettled([
        apiService.getDocumentStats(),
        apiService.getConversations()
      ]);

      const dashboardStats = {
        documents: documentsStats.status === 'fulfilled' ? documentsStats.value : { statistics: {} },
        conversations: conversations.status === 'fulfilled' ? conversations.value : { conversations: [] }
      };

      setStats(dashboardStats);
    } catch (err) {
      console.error('Error loading dashboard data:', err);
      setError('Error cargando datos del dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <div className="text-red-600 mb-2">Error</div>
        <p className="text-red-800">{error}</p>
        <button
          onClick={loadDashboardData}
          className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header del Dashboard */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Dashboard - {company?.company_name}
            </h2>
            <p className="text-gray-600 mt-1">{company?.description}</p>
          </div>
          <button
            onClick={onRefresh}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Actualizar</span>
          </button>
        </div>
      </div>

      {/* Métricas del Sistema */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100 text-blue-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Documentos</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats.documents?.statistics?.total_documents || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100 text-green-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Conversaciones</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats.conversations?.conversations?.length || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-purple-100 text-purple-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Servicios</p>
              <p className="text-2xl font-semibold text-gray-900">
                {company?.services_count || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className={`p-3 rounded-full ${
              systemStatus.status === 'healthy' ? 'bg-green-100 text-green-600' :
              systemStatus.status === 'partial' ? 'bg-yellow-100 text-yellow-600' :
              'bg-red-100 text-red-600'
            }`}>
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Estado Sistema</p>
              <p className="text-lg font-semibold text-gray-900 capitalize">
                {systemStatus.status === 'healthy' ? 'Operativo' :
                 systemStatus.status === 'partial' ? 'Parcial' : 'Con Problemas'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Información de la Empresa */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Información de la Empresa
          </h3>
          <div className="space-y-3">
            <div>
              <span className="text-sm font-medium text-gray-500">ID:</span>
              <span className="ml-2 text-sm text-gray-900">{company?.company_id}</span>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-500">Industria:</span>
              <span className="ml-2 text-sm text-gray-900">{company?.industry || 'No especificada'}</span>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-500">Ubicación:</span>
              <span className="ml-2 text-sm text-gray-900">{company?.location || 'No especificada'}</span>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-500">Config. Extendida:</span>
              <span className={`ml-2 text-sm ${company?.has_extended_config ? 'text-green-600' : 'text-gray-500'}`}>
                {company?.has_extended_config ? 'Activa' : 'No configurada'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Estado de Servicios
          </h3>
          <div className="space-y-3">
            {systemStatus.services && Object.entries(systemStatus.services).map(([service, status]) => (
              <div key={service} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 capitalize">
                  {service.replace('_', ' ')}
                </span>
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${
                    status ? 'bg-green-500' : 'bg-red-500'
                  }`}></div>
                  <span className={`text-sm ${
                    status ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {status ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Actividad Reciente */}
      {stats.conversations?.conversations?.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Conversaciones Recientes
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Usuario
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Último Mensaje
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Fecha
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {stats.conversations.conversations.slice(0, 5).map((conversation, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {conversation.user_id || 'Usuario desconocido'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                      {conversation.last_message || 'Sin mensajes'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {conversation.updated_at ? new Date(conversation.updated_at).toLocaleDateString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
