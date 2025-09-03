// src/App.js - Frontend React Multi-Tenant completamente funcional

import React, { useState, useEffect, useCallback } from 'react';
import './styles/globals.css';

// Componentes principales
import CompanySelector from './components/CompanySelector';
import Dashboard from './components/Dashboard';
import DocumentManager from './components/DocumentManager';
import ChatTester from './components/ChatTester';
import AdminPanel from './components/AdminPanel';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorBoundary from './components/ErrorBoundary';

// Services
import { apiService } from './services/api';

function App() {
  // Estados principales
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [systemStatus, setSystemStatus] = useState({});

  // Cargar datos iniciales
  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('🚀 Initializing Multi-Tenant Admin App...');
      
      // Cargar empresas disponibles
      const companiesResponse = await apiService.getCompanies();
      if (companiesResponse?.companies) {
        setCompanies(companiesResponse.companies);
        console.log(`✅ Loaded ${companiesResponse.companies.length} companies`);
        
        // Seleccionar primera empresa por defecto
        if (companiesResponse.companies.length > 0) {
          setSelectedCompany(companiesResponse.companies[0]);
        }
      }
      
      // Verificar estado del sistema
      const healthResponse = await apiService.getSystemHealth();
      if (healthResponse) {
        setSystemStatus(healthResponse);
        console.log('✅ System health status loaded');
      }
      
    } catch (err) {
      console.error('❌ App initialization failed:', err);
      setError('Error al inicializar la aplicación. Verificando conexión...');
      
      // Intentar reintentar después de un delay
      setTimeout(() => {
        initializeApp();
      }, 5000);
    } finally {
      setLoading(false);
    }
  };

  const handleCompanyChange = useCallback(async (company) => {
    try {
      setLoading(true);
      setSelectedCompany(company);
      console.log(`🏢 Switched to company: ${company.company_name}`);
      
      // Actualizar configuración del API service
      apiService.setCompanyId(company.company_id);
      
    } catch (err) {
      console.error('Error switching company:', err);
      setError('Error al cambiar de empresa');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleTabChange = useCallback((tab) => {
    setActiveTab(tab);
    console.log(`📑 Tab changed to: ${tab}`);
  }, []);

  const refreshData = useCallback(async () => {
    await initializeApp();
  }, []);

  // Loading state
  if (loading && !selectedCompany) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="large" />
          <h2 className="mt-4 text-xl font-semibold text-gray-700">
            Cargando Sistema Multi-Tenant...
          </h2>
          <p className="mt-2 text-gray-500">
            Inicializando empresas y configuraciones
          </p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !selectedCompany) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-red-100 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="text-red-500 text-6xl mb-4">⚠️</div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              Error de Conexión
            </h2>
            <p className="text-gray-600 mb-4">{error}</p>
            <button
              onClick={initializeApp}
              className="btn-primary"
            >
              Reintentar Conexión
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold text-sm">MT</span>
                  </div>
                  <h1 className="text-xl font-bold text-gray-900">
                    Multi-Tenant Admin
                  </h1>
                </div>
                
                {/* System Status Indicator */}
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    systemStatus.status === 'healthy' ? 'bg-green-500' :
                    systemStatus.status === 'partial' ? 'bg-yellow-500' : 'bg-red-500'
                  }`}></div>
                  <span className="text-sm text-gray-500">
                    {systemStatus.status === 'healthy' ? 'Sistema Operativo' :
                     systemStatus.status === 'partial' ? 'Funcionamiento Parcial' : 'Sistema con Problemas'}
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <button
                  onClick={refreshData}
                  className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                  title="Actualizar datos"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </button>
                
                {/* Company Selector */}
                <CompanySelector
                  companies={companies}
                  selectedCompany={selectedCompany}
                  onCompanyChange={handleCompanyChange}
                />
              </div>
            </div>
          </div>
        </header>

        {/* Navigation Tabs */}
        <nav className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex space-x-8">
              {[
                { id: 'dashboard', label: 'Dashboard', icon: '📊' },
                { id: 'documents', label: 'Documentos', icon: '📁' },
                { id: 'chat', label: 'Test Chat', icon: '💬' },
                { id: 'admin', label: 'Admin', icon: '⚙️' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`flex items-center space-x-2 py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <LoadingSpinner />
            </div>
          ) : (
            <>
              {activeTab === 'dashboard' && (
                <Dashboard 
                  company={selectedCompany}
                  systemStatus={systemStatus}
                  onRefresh={refreshData}
                />
              )}
              
              {activeTab === 'documents' && (
                <DocumentManager 
                  company={selectedCompany}
                />
              )}
              
              {activeTab === 'chat' && (
                <ChatTester 
                  company={selectedCompany}
                />
              )}
              
              {activeTab === 'admin' && (
                <AdminPanel 
                  company={selectedCompany}
                  companies={companies}
                  systemStatus={systemStatus}
                  onRefresh={refreshData}
                />
              )}
            </>
          )}
        </main>

        {/* Footer */}
        <footer className="bg-white border-t border-gray-200 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex justify-between items-center text-sm text-gray-500">
              <div>
                Multi-Tenant Chatbot System v1.0.0
              </div>
              <div className="flex items-center space-x-4">
                <span>Empresas: {companies.length}</span>
                <span>•</span>
                <span>Empresa Activa: {selectedCompany?.company_name || 'Ninguna'}</span>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </ErrorBoundary>
  );
}

export default App;
