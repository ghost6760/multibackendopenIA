// src/App.js - Aplicación principal corregida con endpoints del backend
import React, { useState, useEffect } from 'react';
import apiService from './services/api';

// Componentes corregidos
import ChatSection from './components/ChatSection';
import DocumentsSection from './components/DocumentsSection';
import ConversationsSection from './components/ConversationsSection';

// Importar estilos CSS
import './styles/global.css';

function App() {
  const [companies, setCompanies] = useState({});
  const [currentCompanyId, setCurrentCompanyId] = useState('');
  const [activeTab, setActiveTab] = useState('chat');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);

  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('🚀 Initializing app...');
      
      // Cargar empresas y salud del sistema en paralelo
      const [companiesResponse, healthResponse] = await Promise.allSettled([
        apiService.getCompanies(),
        apiService.getSystemHealth()
      ]);

      // Procesar respuesta de empresas
      if (companiesResponse.status === 'fulfilled') {
        const companiesData = companiesResponse.value;
        console.log('🏢 Companies loaded:', companiesData);
        
        if (companiesData && companiesData.status === 'success') {
          const companiesObj = {};
          companiesData.companies.forEach(company => {
            companiesObj[company.company_id] = company;
          });
          setCompanies(companiesObj);
          
          // Seleccionar primera empresa por defecto
          const firstCompanyId = Object.keys(companiesObj)[0];
          if (firstCompanyId) {
            setCurrentCompanyId(firstCompanyId);
            apiService.setCompanyId(firstCompanyId);
          }
        } else {
          throw new Error('Formato de respuesta de empresas inválido');
        }
      } else {
        console.error('❌ Error loading companies:', companiesResponse.reason);
        throw companiesResponse.reason;
      }

      // Procesar respuesta de salud del sistema (no crítico)
      if (healthResponse.status === 'fulfilled') {
        setSystemHealth(healthResponse.value);
        console.log('💚 System health loaded:', healthResponse.value);
      } else {
        console.warn('⚠️ Could not load system health:', healthResponse.reason);
      }

    } catch (error) {
      console.error('❌ Error initializing app:', error);
      setError(`Error inicializando aplicación: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompanyChange = (companyId) => {
    console.log('🏢 Changing company to:', companyId);
    setCurrentCompanyId(companyId);
    apiService.setCompanyId(companyId);
  };

  const refreshSystemHealth = async () => {
    try {
      const health = await apiService.getSystemHealth();
      setSystemHealth(health);
      console.log('💚 System health refreshed:', health);
    } catch (error) {
      console.warn('⚠️ Could not refresh system health:', error);
    }
  };

  const tabs = [
    { id: 'chat', name: '💬 Chat de Prueba', icon: '💬' },
    { id: 'documents', name: '📄 Documentos', icon: '📄' },
    { id: 'conversations', name: '📋 Conversaciones', icon: '📋' },
    { id: 'system', name: '⚙️ Sistema', icon: '⚙️' }
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-700 mb-2">Cargando Sistema Multi-Tenant</h2>
          <p className="text-gray-500">Conectando con el backend...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-orange-50 flex items-center justify-center">
        <div className="bg-white/90 backdrop-blur rounded-lg p-8 max-w-md w-full mx-4 text-center">
          <div className="text-4xl mb-4">❌</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Error de Conexión</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={initializeApp}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            🔄 Reintentar Conexión
          </button>
          
          <div className="mt-6 p-4 bg-gray-50 rounded-lg text-left">
            <h3 className="font-semibold text-sm mb-2">🔧 Información de Debug:</h3>
            <div className="text-xs text-gray-600 space-y-1">
              <div><strong>Base URL:</strong> {apiService.baseURL}</div>
              <div><strong>Endpoint:</strong> GET /api/companies</div>
              <div><strong>Timestamp:</strong> {new Date().toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
      {/* Header */}
      <header className="bg-white/90 backdrop-blur shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo y Título */}
            <div className="flex items-center space-x-4">
              <div className="text-2xl font-bold text-blue-600">
                🤖 Multi-Tenant Chatbot
              </div>
              
              {systemHealth && (
                <div 
                  className={`px-2 py-1 rounded-full text-xs font-medium cursor-pointer ${
                    systemHealth.status === 'healthy' 
                      ? 'bg-green-100 text-green-700' 
                      : systemHealth.status === 'partial'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}
                  onClick={refreshSystemHealth}
                  title="Click para actualizar estado"
                >
                  {systemHealth.status === 'healthy' ? '🟢' : 
                   systemHealth.status === 'partial' ? '🟡' : '🔴'} 
                  {systemHealth.status}
                </div>
              )}
            </div>

            {/* Selector de Empresa */}
            <div className="flex items-center space-x-4">
              <label htmlFor="company-select" className="text-sm font-medium text-gray-700">
                🏢 Empresa:
              </label>
              <select
                id="company-select"
                value={currentCompanyId}
                onChange={(e) => handleCompanyChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 bg-white"
              >
                <option value="">Seleccionar empresa...</option>
                {Object.values(companies).map((company) => (
                  <option key={company.company_id} value={company.company_id}>
                    {company.company_name} ({company.company_id})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Tabs */}
          <nav className="flex space-x-8 border-b">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="flex items-center space-x-2">
                  <span>{tab.icon}</span>
                  <span>{tab.name}</span>
                </span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'chat' && (
          <ChatSection 
            currentCompanyId={currentCompanyId} 
            companies={companies}
          />
        )}
        
        {activeTab === 'documents' && (
          <DocumentsSection 
            currentCompanyId={currentCompanyId} 
            companies={companies}
          />
        )}
        
        {activeTab === 'conversations' && (
          <ConversationsSection 
            currentCompanyId={currentCompanyId} 
            companies={companies}
          />
        )}
        
        {activeTab === 'system' && (
          <SystemSection 
            systemHealth={systemHealth}
            companies={companies}
            onRefresh={refreshSystemHealth}
            apiService={apiService}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white/90 backdrop-blur mt-16 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-gray-600">
          <p className="text-sm">
            🤖 Multi-Tenant Chatbot System • 
            {currentCompanyId && ` Empresa Activa: ${companies[currentCompanyId]?.company_name}`} • 
            {Object.keys(companies).length} empresas configuradas
          </p>
          <div className="mt-2 text-xs text-gray-500">
            Endpoints: /api/companies, /api/documents, /api/conversations, /api/health
          </div>
        </div>
      </footer>
    </div>
  );
}

// Componente Sistema
const SystemSection = ({ systemHealth, companies, onRefresh, apiService }) => {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await onRefresh();
    setIsRefreshing(false);
  };

  return (
    <div className="space-y-6">
      {/* System Health */}
      <div className="bg-white/90 backdrop-blur rounded-lg p-6">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-2xl font-bold text-gray-800">⚙️ Estado del Sistema</h2>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="px-3 py-1 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors disabled:opacity-50"
          >
            {isRefreshing ? '🔄 Actualizando...' : '🔄 Actualizar'}
          </button>
        </div>

        {systemHealth ? (
          <div className="space-y-4">
            <div className={`p-4 rounded-lg ${
              systemHealth.status === 'healthy' 
                ? 'bg-green-50 border border-green-200' 
                : systemHealth.status === 'partial'
                ? 'bg-yellow-50 border border-yellow-200'
                : 'bg-red-50 border border-red-200'
            }`}>
              <div className="flex items-center mb-2">
                <span className="text-2xl mr-2">
                  {systemHealth.status === 'healthy' ? '🟢' : 
                   systemHealth.status === 'partial' ? '🟡' : '🔴'}
                </span>
                <h3 className="font-semibold">
                  Estado General: {systemHealth.status?.toUpperCase()}
                </h3>
              </div>
              <p className="text-sm text-gray-600">
                Última actualización: {new Date(systemHealth.timestamp).toLocaleString('es-ES')}
              </p>
            </div>

            {systemHealth.services && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(systemHealth.services).map(([service, status]) => (
                  <div
                    key={service}
                    className={`p-3 rounded-lg text-center ${
                      status 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-red-100 text-red-700'
                    }`}
                  >
                    <div className="font-medium capitalize">{service}</div>
                    <div className="text-sm">
                      {status ? '✅ Activo' : '❌ Inactivo'}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {systemHealth.schedule_service_note && (
              <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
                <h4 className="font-medium text-blue-800 mb-1">📋 Nota del Servicio de Calendario</h4>
                <p className="text-sm text-blue-700">{systemHealth.schedule_service_note}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">⚙️</div>
            <p>Estado del sistema no disponible</p>
          </div>
        )}
      </div>

      {/* Companies Configuration */}
      <div className="bg-white/90 backdrop-blur rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">🏢 Empresas Configuradas</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.values(companies).map((company) => (
            <div
              key={company.company_id}
              className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center mb-2">
                <span className="text-xl mr-2">🏢</span>
                <div>
                  <h4 className="font-medium text-gray-800">{company.company_name}</h4>
                  <p className="text-sm text-gray-600">ID: {company.company_id}</p>
                </div>
              </div>
              
              {company.description && (
                <p className="text-sm text-gray-700 mb-2">{company.description}</p>
              )}
              
              <div className="text-xs text-gray-500 space-y-1">
                {company.industry && <div>🏭 {company.industry}</div>}
                {company.website && <div>🌐 {company.website}</div>}
                {company.contact_email && <div>📧 {company.contact_email}</div>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* API Endpoints */}
      <div className="bg-white/90 backdrop-blur rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">📡 Endpoints de API</h3>
        
        <div className="space-y-2 font-mono text-sm">
          <div className="flex items-center space-x-2">
            <span className="bg-green-100 text-green-700 px-2 py-1 rounded">GET</span>
            <span>/api/companies</span>
            <span className="text-gray-500">- Lista empresas</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded">GET</span>
            <span>/api/documents</span>
            <span className="text-gray-500">- Lista documentos</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded">POST</span>
            <span>/api/documents</span>
            <span className="text-gray-500">- Sube documento</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded">GET</span>
            <span>/api/conversations</span>
            <span className="text-gray-500">- Lista conversaciones</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded">POST</span>
            <span>/api/conversations/message</span>
            <span className="text-gray-500">- Envía mensaje</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="bg-green-100 text-green-700 px-2 py-1 rounded">GET</span>
            <span>/api/health</span>
            <span className="text-gray-500">- Estado del sistema</span>
          </div>
        </div>

        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-semibold text-sm mb-2">🔧 Configuración Actual:</h4>
          <div className="text-xs text-gray-600 space-y-1">
            <div><strong>Base URL:</strong> {apiService.baseURL}</div>
            <div><strong>Environment:</strong> {window.location.hostname.includes('railway') ? 'Production (Railway)' : 'Development'}</div>
            <div><strong>Company ID:</strong> {apiService.getCompanyId() || 'No seleccionada'}</div>
            <div><strong>Total Companies:</strong> {Object.keys(companies).length}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
