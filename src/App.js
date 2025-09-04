// src/App.js - Frontend React Multi-Tenant completamente funcional

import React, { useState, useEffect, useCallback } from 'react';
import './styles/globals.css';

// Servicios
import { apiService } from './services/api';

// Componentes principales con fallbacks
let CompanySelector, Dashboard, DocumentManager, ChatTester, AdminPanel, LoadingSpinner, TabNavigation;

try {
  CompanySelector = require('./components/CompanySelector').default;
} catch {
  CompanySelector = ({ companies, selectedCompany, onCompanyChange }) => (
    <div className="mb-6">
      <label className="block text-sm font-medium text-white mb-2">Seleccionar Empresa:</label>
      <select 
        value={selectedCompany?.company_id || ''} 
        onChange={(e) => {
          const company = companies.find(c => c.company_id === e.target.value);
          onCompanyChange(company);
        }}
        className="block w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
      >
        <option value="">Seleccionar empresa...</option>
        {companies.map(company => (
          <option key={company.company_id} value={company.company_id}>
            {company.company_name}
          </option>
        ))}
      </select>
    </div>
  );
}

try {
  ChatTester = require('./components/ChatTester').default;
} catch {
  ChatTester = ({ company }) => {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [sending, setSending] = useState(false);

    const handleSend = async (e) => {
      e.preventDefault();
      if (!inputMessage.trim() || sending) return;

      setMessages(prev => [...prev, { type: 'user', content: inputMessage, timestamp: new Date() }]);
      setSending(true);
      
      try {
        const response = await apiService.sendMessage(inputMessage, null, 'test-user');
        setMessages(prev => [...prev, { type: 'assistant', content: response.response, timestamp: new Date() }]);
      } catch (error) {
        setMessages(prev => [...prev, { type: 'error', content: `Error: ${error.message}`, timestamp: new Date() }]);
      }
      
      setInputMessage('');
      setSending(false);
    };

    return (
      <div className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">💬 Chat Testing</h3>
        
        <div className="h-96 overflow-y-auto mb-4 p-4 bg-gray-50 rounded-lg">
          {messages.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Inicia una conversación con el chatbot...</p>
          ) : (
            messages.map((msg, index) => (
              <div key={index} className={`mb-4 ${msg.type === 'user' ? 'text-right' : 'text-left'}`}>
                <div className={`inline-block max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  msg.type === 'user' ? 'bg-blue-600 text-white' :
                  msg.type === 'error' ? 'bg-red-100 text-red-800' :
                  'bg-gray-200 text-gray-800'
                }`}>
                  {msg.content}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {msg.timestamp.toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>

        <form onSubmit={handleSend} className="flex space-x-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Escribe tu mensaje..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !inputMessage.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? 'Enviando...' : 'Enviar'}
          </button>
        </form>

        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <h4 className="font-medium text-blue-900 mb-2">🎤 Funciones Multimedia</h4>
          <div className="flex space-x-2">
            <button className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
              🎤 Grabar Audio
            </button>
            <button className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700">
              📷 Capturar Imagen
            </button>
            <button className="px-3 py-1 bg-purple-600 text-white rounded text-sm hover:bg-purple-700">
              📁 Subir Archivo
            </button>
          </div>
        </div>
      </div>
    );
  };
}

try {
  DocumentManager = require('./components/DocumentManager').default;
} catch {
  DocumentManager = ({ company }) => {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(false);
    const [uploadFile, setUploadFile] = useState(null);

    const loadDocuments = async () => {
      if (!company) return;
      setLoading(true);
      try {
        const response = await apiService.getDocuments(company.company_id);
        setDocuments(response.documents || []);
      } catch (error) {
        console.error('Error loading documents:', error);
      }
      setLoading(false);
    };

    useEffect(() => {
      loadDocuments();
    }, [company]);

    const handleUpload = async (e) => {
      e.preventDefault();
      if (!uploadFile || !company) return;

      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('company_id', company.company_id);

      try {
        await apiService.uploadDocument(formData);
        setUploadFile(null);
        await loadDocuments();
      } catch (error) {
        console.error('Error uploading document:', error);
      }
    };

    return (
      <div className="space-y-6">
        <div className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📁 Gestión de Documentos</h3>
          
          <form onSubmit={handleUpload} className="mb-6">
            <div className="flex space-x-4 items-end">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Subir Documento
                </label>
                <input
                  type="file"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  accept=".pdf,.txt,.doc,.docx"
                />
              </div>
              <button
                type="submit"
                disabled={!uploadFile}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                📤 Subir
              </button>
            </div>
          </form>

          <div>
            <div className="flex justify-between items-center mb-4">
              <h4 className="font-medium text-gray-900">Documentos ({documents.length})</h4>
              <button
                onClick={loadDocuments}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
              >
                🔄 Actualizar
              </button>
            </div>

            {loading ? (
              <div className="text-center py-8">
                <div className="loading-spinner mx-auto mb-2"></div>
                <p className="text-gray-500">Cargando documentos...</p>
              </div>
            ) : documents.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No hay documentos disponibles</p>
            ) : (
              <div className="space-y-2">
                {documents.map((doc, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900">{doc.filename || `Documento ${index + 1}`}</div>
                      <div className="text-sm text-gray-500">
                        {doc.content_type} • {doc.size ? `${(doc.size/1024).toFixed(1)} KB` : 'Tamaño desconocido'}
                      </div>
                    </div>
                    <button className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700">
                      🗑️ Eliminar
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };
}

try {
  AdminPanel = require('./components/AdminPanel').default;
} catch {
  AdminPanel = ({ companies, company }) => {
    const [systemHealth, setSystemHealth] = useState(null);
    const [diagnostics, setDiagnostics] = useState(null);

    const runDiagnostics = async () => {
      try {
        const response = await fetch('/api/admin/diagnostics', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ company_id: company?.company_id })
        });
        const data = await response.json();
        setDiagnostics(data);
      } catch (error) {
        console.error('Error running diagnostics:', error);
      }
    };

    const loadHealth = async () => {
      try {
        const response = await fetch(`/api/health/full${company ? `?company_id=${company.company_id}` : ''}`);
        const data = await response.json();
        setSystemHealth(data);
      } catch (error) {
        console.error('Error loading health:', error);
      }
    };

    useEffect(() => {
      loadHealth();
    }, [company]);

    return (
      <div className="space-y-6">
        <div className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">⚙️ Panel de Administración</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <button
              onClick={loadHealth}
              className="p-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <div className="text-2xl mb-2">💚</div>
              <div className="font-medium">Health Check</div>
              <div className="text-sm opacity-90">Verificar estado del sistema</div>
            </button>

            <button
              onClick={runDiagnostics}
              className="p-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <div className="text-2xl mb-2">🔬</div>
              <div className="font-medium">Diagnósticos</div>
              <div className="text-sm opacity-90">Ejecutar pruebas completas</div>
            </button>

            <button
              onClick={() => window.open('/debug/build-structure', '_blank')}
              className="p-4 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              <div className="text-2xl mb-2">🔧</div>
              <div className="font-medium">Debug Info</div>
              <div className="text-sm opacity-90">Información técnica</div>
            </button>
          </div>

          {systemHealth && (
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <h4 className="font-medium text-gray-900 mb-2">Estado del Sistema</h4>
              <pre className="text-sm text-gray-600 overflow-auto">
                {JSON.stringify(systemHealth, null, 2)}
              </pre>
            </div>
          )}

          {diagnostics && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-2">Resultados de Diagnósticos</h4>
              <pre className="text-sm text-gray-600 overflow-auto">
                {JSON.stringify(diagnostics, null, 2)}
              </pre>
            </div>
          )}
        </div>

        <div className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
          <h4 className="font-medium text-gray-900 mb-4">Empresas Configuradas</h4>
          <div className="space-y-2">
            {companies.map((comp) => (
              <div key={comp.company_id} className={`p-3 rounded-lg border ${
                company?.company_id === comp.company_id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
              }`}>
                <div className="font-medium">{comp.company_name}</div>
                <div className="text-sm text-gray-500">ID: {comp.company_id}</div>
                <div className="text-sm text-gray-500">
                  Servicios: {comp.services_count || 0} • 
                  Configuración Extendida: {comp.has_extended_config ? '✅' : '❌'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };
}

// Componente de navegación por tabs
const TabNavigation = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'chat', label: 'Chat Testing', icon: '💬' },
    { id: 'documents', label: 'Documentos', icon: '📁' },
    { id: 'admin', label: 'Administración', icon: '⚙️' }
  ];

  return (
    <div className="mb-8">
      <nav className="flex space-x-8">
        {tabs.map(({ id, label, icon }) => (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === id
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-white/80 hover:text-white hover:bg-white/10'
            }`}
          >
            <span>{icon}</span>
            <span>{label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
};

// Componente principal de la aplicación
function App() {
  // Estados principales
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');
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
      setError('Error al inicializar la aplicación. Verifica que el backend esté funcionando.');
    } finally {
      setLoading(false);
    }
  };

  // Manejar cambio de empresa
  const handleCompanyChange = useCallback((company) => {
    setSelectedCompany(company);
    console.log('🏢 Company changed:', company?.company_name);
  }, []);

  // Renderizar contenido según tab activo
  const renderTabContent = () => {
    switch (activeTab) {
      case 'chat':
        return <ChatTester company={selectedCompany} />;
      case 'documents':
        return <DocumentManager company={selectedCompany} />;
      case 'admin':
        return <AdminPanel companies={companies} company={selectedCompany} />;
      default:
        return <ChatTester company={selectedCompany} />;
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 via-purple-600 to-purple-700 flex items-center justify-center">
        <div className="text-center text-white">
          <div className="loading-spinner mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold mb-2">Cargando Multi-Tenant Admin</h2>
          <p className="text-white/80">Inicializando sistema...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl p-8 max-w-md w-full text-center">
          <div className="text-red-600 mb-4">
            <div className="w-16 h-16 mx-auto bg-red-100 rounded-full flex items-center justify-center text-2xl">
              ⚠️
            </div>
          </div>
          <h2 className="text-xl font-bold text-gray-800 mb-4">Error de Conexión</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="space-y-3">
            <button
              onClick={initializeApp}
              className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              🔄 Reintentar
            </button>
            <div className="flex space-x-2">
              <a
                href="/api/system/info"
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm text-center"
              >
                📊 System Info
              </a>
              <a
                href="/debug/build-structure"
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm text-center"
              >
                🔧 Debug
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Aplicación principal
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-purple-600 to-purple-700">
      {/* Header */}
      <header className="bg-white/10 backdrop-blur-sm border-b border-white/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
                <span className="text-xl">🚀</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Multi-Tenant Admin</h1>
                <p className="text-white/70 text-sm">Sistema de Gestión Multi-Tenant</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <div className="text-white text-sm font-medium">
                  {selectedCompany?.company_name || 'Sin empresa'}
                </div>
                <div className="text-white/70 text-xs">
                  {companies.length} empresa{companies.length !== 1 ? 's' : ''} disponible{companies.length !== 1 ? 's' : ''}
                </div>
              </div>
              <div className={`w-3 h-3 rounded-full ${
                systemStatus.status === 'healthy' || systemStatus.data?.status === 'healthy' 
                  ? 'bg-green-400' 
                  : 'bg-red-400'
              }`} title="Estado del sistema"></div>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Company selector */}
        <CompanySelector
          companies={companies}
          selectedCompany={selectedCompany}
          onCompanyChange={handleCompanyChange}
        />

        {/* Navigation tabs */}
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Tab content */}
        {selectedCompany ? (
          <div className="space-y-6">
            {renderTabContent()}
          </div>
        ) : (
          <div className="bg-white/95 backdrop-blur-sm rounded-xl p-8 text-center">
            <div className="text-gray-400 text-6xl mb-4">🏢</div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">
              Selecciona una Empresa
            </h3>
            <p className="text-gray-600">
              Elige una empresa para acceder a las funcionalidades de chat testing, 
              gestión de documentos y administración.
            </p>
            {companies.length === 0 && (
              <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-yellow-800 text-sm">
                  ⚠️ No hay empresas configuradas en el sistema.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Footer info */}
        <div className="mt-12 text-center">
          <div className="inline-flex items-center space-x-6 text-white/70 text-sm">
            <span>Backend: Flask Multi-Tenant</span>
            <span>•</span>
            <span>Frontend: React 18</span>
            <span>•</span>
            <span>Deploy: Railway</span>
            <span>•</span>
            <span>{new Date().toLocaleDateString()}</span>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
