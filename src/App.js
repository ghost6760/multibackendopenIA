// src/App.js - Frontend React Multi-Tenant completamente funcional

import React, { useState, useEffect, useCallback } from 'react';

// Servicios
import { apiService } from './services/api';

// Componentes principales con fallbacks
CompanySelector = ({ companies, selectedCompany, onCompanyChange }) => (
  <div style={{ marginBottom: '1.5rem' }}>
    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: 'white', marginBottom: '0.5rem' }}>
      Seleccionar Empresa:
    </label>
    <select 
      value={selectedCompany?.company_id || ''} 
      onChange={(e) => {
        console.log('Company selected:', e.target.value); // Debug
        const company = companies.find(c => c.company_id === e.target.value);
        console.log('Found company:', company); // Debug
        if (company) {
          onCompanyChange(company); // Pasar el objeto completo, no solo el ID
        }
      }}
      style={{
        display: 'block',
        width: '100%',
        padding: '0.75rem',
        border: '1px solid #d1d5db',
        borderRadius: '0.375rem',
        background: 'white',
        fontSize: '1rem'
      }}
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
      <div style={{
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(4px)',
        borderRadius: '0.75rem',
        padding: '1.5rem'
      }}>
        <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#1f2937', marginBottom: '1rem' }}>
          💬 Chat Testing
        </h3>
        
        <div style={{
          height: '24rem',
          overflowY: 'auto',
          marginBottom: '1rem',
          padding: '1rem',
          background: '#f9fafb',
          borderRadius: '0.5rem',
          border: '1px solid #e5e7eb'
        }}>
          {messages.length === 0 ? (
            <p style={{ color: '#6b7280', textAlign: 'center', padding: '2rem 0' }}>
              Inicia una conversación con el chatbot...
            </p>
          ) : (
            messages.map((msg, index) => (
              <div key={index} style={{
                marginBottom: '1rem',
                textAlign: msg.type === 'user' ? 'right' : 'left'
              }}>
                <div style={{
                  display: 'inline-block',
                  maxWidth: '20rem',
                  padding: '0.75rem 1rem',
                  borderRadius: '0.5rem',
                  background: msg.type === 'user' ? '#3b82f6' : 
                            msg.type === 'error' ? '#fef2f2' : '#f3f4f6',
                  color: msg.type === 'user' ? 'white' :
                         msg.type === 'error' ? '#dc2626' : '#1f2937'
                }}>
                  {msg.content}
                </div>
                <div style={{
                  fontSize: '0.75rem',
                  color: '#6b7280',
                  marginTop: '0.25rem'
                }}>
                  {msg.timestamp.toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>

        <form onSubmit={handleSend} style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Escribe tu mensaje..."
            style={{
              flex: 1,
              padding: '0.75rem 1rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.5rem',
              fontSize: '1rem',
              outline: 'none'
            }}
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !inputMessage.trim()}
            style={{
              padding: '0.75rem 1.5rem',
              background: sending || !inputMessage.trim() ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: sending || !inputMessage.trim() ? 'not-allowed' : 'pointer',
              fontSize: '1rem'
            }}
          >
            {sending ? 'Enviando...' : 'Enviar'}
          </button>
        </form>

        <div style={{
          marginTop: '1rem',
          padding: '1rem',
          background: '#dbeafe',
          borderRadius: '0.5rem'
        }}>
          <h4 style={{ fontWeight: '500', color: '#1e40af', marginBottom: '0.5rem' }}>
            🎤 Funciones Multimedia
          </h4>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button style={{
              padding: '0.5rem 0.75rem',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              fontSize: '0.875rem',
              cursor: 'pointer'
            }}>
              🎤 Grabar Audio
            </button>
            <button style={{
              padding: '0.5rem 0.75rem',
              background: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              fontSize: '0.875rem',
              cursor: 'pointer'
            }}>
              📷 Capturar Imagen
            </button>
            <button style={{
              padding: '0.5rem 0.75rem',
              background: '#8b5cf6',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              fontSize: '0.875rem',
              cursor: 'pointer'
            }}>
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
      <div>
        <div style={{
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(4px)',
          borderRadius: '0.75rem',
          padding: '1.5rem'
        }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#1f2937', marginBottom: '1rem' }}>
            📁 Gestión de Documentos
          </h3>
          
          <form onSubmit={handleUpload} style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'end' }}>
              <div style={{ flex: 1 }}>
                <label style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  color: '#374151',
                  marginBottom: '0.25rem'
                }}>
                  Subir Documento
                </label>
                <input
                  type="file"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.5rem'
                  }}
                  accept=".pdf,.txt,.doc,.docx"
                />
              </div>
              <button
                type="submit"
                disabled={!uploadFile}
                style={{
                  padding: '0.75rem 1.5rem',
                  background: !uploadFile ? '#9ca3af' : '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: !uploadFile ? 'not-allowed' : 'pointer'
                }}
              >
                📤 Subir
              </button>
            </div>
          </form>

          <div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1rem'
            }}>
              <h4 style={{ fontWeight: '500', color: '#111827' }}>
                Documentos ({documents.length})
              </h4>
              <button
                onClick={loadDocuments}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  cursor: 'pointer'
                }}
              >
                🔄 Actualizar
              </button>
            </div>

            {loading ? (
              <div style={{ textAlign: 'center', padding: '2rem 0' }}>
                <div className="loading-spinner" style={{ margin: '0 auto 0.5rem' }}></div>
                <p style={{ color: '#6b7280' }}>Cargando documentos...</p>
              </div>
            ) : documents.length === 0 ? (
              <p style={{ color: '#6b7280', textAlign: 'center', padding: '2rem 0' }}>
                No hay documentos disponibles
              </p>
            ) : (
              <div>
                {documents.map((doc, index) => (
                  <div key={index} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem',
                    background: '#f9fafb',
                    borderRadius: '0.5rem',
                    marginBottom: '0.5rem'
                  }}>
                    <div>
                      <div style={{ fontWeight: '500', color: '#111827' }}>
                        {doc.filename || `Documento ${index + 1}`}
                      </div>
                      <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                        {doc.content_type} • {doc.size ? `${(doc.size/1024).toFixed(1)} KB` : 'Tamaño desconocido'}
                      </div>
                    </div>
                    <button style={{
                      padding: '0.25rem 0.75rem',
                      background: '#ef4444',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.25rem',
                      fontSize: '0.875rem',
                      cursor: 'pointer'
                    }}>
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
      <div>
        <div style={{
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(4px)',
          borderRadius: '0.75rem',
          padding: '1.5rem',
          marginBottom: '1.5rem'
        }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#1f2937', marginBottom: '1rem' }}>
            ⚙️ Panel de Administración
          </h3>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem',
            marginBottom: '1.5rem'
          }}>
            <button
              onClick={loadHealth}
              style={{
                padding: '1rem',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>💚</div>
              <div style={{ fontWeight: '500' }}>Health Check</div>
              <div style={{ fontSize: '0.875rem', opacity: 0.9 }}>Verificar estado del sistema</div>
            </button>

            <button
              onClick={runDiagnostics}
              style={{
                padding: '1rem',
                background: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>🔬</div>
              <div style={{ fontWeight: '500' }}>Diagnósticos</div>
              <div style={{ fontSize: '0.875rem', opacity: 0.9 }}>Ejecutar pruebas completas</div>
            </button>

            <button
              onClick={() => window.open('/debug/build-structure', '_blank')}
              style={{
                padding: '1rem',
                background: '#8b5cf6',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>🔧</div>
              <div style={{ fontWeight: '500' }}>Debug Info</div>
              <div style={{ fontSize: '0.875rem', opacity: 0.9 }}>Información técnica</div>
            </button>
          </div>

          {systemHealth && (
            <div style={{
              background: '#f9fafb',
              borderRadius: '0.5rem',
              padding: '1rem',
              marginBottom: '1rem'
            }}>
              <h4 style={{ fontWeight: '500', color: '#111827', marginBottom: '0.5rem' }}>
                Estado del Sistema
              </h4>
              <pre style={{
                fontSize: '0.875rem',
                color: '#4b5563',
                overflow: 'auto',
                whiteSpace: 'pre-wrap'
              }}>
                {JSON.stringify(systemHealth, null, 2)}
              </pre>
            </div>
          )}

          {diagnostics && (
            <div style={{
              background: '#f9fafb',
              borderRadius: '0.5rem',
              padding: '1rem'
            }}>
              <h4 style={{ fontWeight: '500', color: '#111827', marginBottom: '0.5rem' }}>
                Resultados de Diagnósticos
              </h4>
              <pre style={{
                fontSize: '0.875rem',
                color: '#4b5563',
                overflow: 'auto',
                whiteSpace: 'pre-wrap'
              }}>
                {JSON.stringify(diagnostics, null, 2)}
              </pre>
            </div>
          )}
        </div>

        <div style={{
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(4px)',
          borderRadius: '0.75rem',
          padding: '1.5rem'
        }}>
          <h4 style={{ fontWeight: '500', color: '#111827', marginBottom: '1rem' }}>
            Empresas Configuradas
          </h4>
          <div>
            {companies.map((comp) => (
              <div key={comp.company_id} style={{
                padding: '0.75rem',
                borderRadius: '0.5rem',
                border: company?.company_id === comp.company_id ? '2px solid #3b82f6' : '1px solid #e5e7eb',
                background: company?.company_id === comp.company_id ? '#eff6ff' : 'white',
                marginBottom: '0.5rem'
              }}>
                <div style={{ fontWeight: '500' }}>{comp.company_name}</div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>ID: {comp.company_id}</div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
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
    <div style={{ marginBottom: '2rem' }}>
      <nav style={{ display: 'flex', gap: '2rem' }}>
        {tabs.map(({ id, label, icon }) => (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.75rem 1rem',
              borderRadius: '0.5rem',
              fontWeight: '500',
              border: 'none',
              cursor: 'pointer',
              background: activeTab === id ? 'white' : 'transparent',
              color: activeTab === id ? '#3b82f6' : 'rgba(255, 255, 255, 0.8)',
              boxShadow: activeTab === id ? '0 1px 3px rgba(0, 0, 0, 0.1)' : 'none',
              transition: 'all 0.2s ease'
            }}
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
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #3b82f6, #8b5cf6, #8b5cf6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{ textAlign: 'center', color: 'white' }}>
          <div className="loading-spinner" style={{ margin: '0 auto 1rem' }}></div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Cargando Multi-Tenant Admin
          </h2>
          <p style={{ color: 'rgba(255, 255, 255, 0.8)' }}>Inicializando sistema...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #ef4444, #dc2626)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem'
      }}>
        <div style={{
          background: 'white',
          borderRadius: '0.75rem',
          padding: '2rem',
          maxWidth: '28rem',
          width: '100%',
          textAlign: 'center'
        }}>
          <div style={{
            color: '#dc2626',
            marginBottom: '1rem'
          }}>
            <div style={{
              width: '4rem',
              height: '4rem',
              margin: '0 auto',
              background: '#fef2f2',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.5rem'
            }}>
              ⚠️
            </div>
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#1f2937', marginBottom: '1rem' }}>
            Error de Conexión
          </h2>
          <p style={{ color: '#4b5563', marginBottom: '1.5rem' }}>{error}</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <button
              onClick={initializeApp}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                background: '#dc2626',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontWeight: '500'
              }}
            >
              🔄 Reintentar
            </button>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <a
                href="/api/system/info"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  flex: 1,
                  padding: '0.5rem 0.75rem',
                  background: '#4b5563',
                  color: 'white',
                  textDecoration: 'none',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  textAlign: 'center'
                }}
              >
                📊 System Info
              </a>
              <a
                href="/debug/build-structure"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  flex: 1,
                  padding: '0.5rem 0.75rem',
                  background: '#3b82f6',
                  color: 'white',
                  textDecoration: 'none',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  textAlign: 'center'
                }}
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
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #3b82f6, #8b5cf6, #8b5cf6)'
    }}>
      {/* Header */}
      <header style={{
        background: 'rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(4px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.2)'
      }}>
        <div style={{
          maxWidth: '80rem',
          margin: '0 auto',
          padding: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              width: '2.5rem',
              height: '2.5rem',
              background: 'white',
              borderRadius: '0.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <span style={{ fontSize: '1.25rem' }}>🚀</span>
            </div>
            <div>
              <h1 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', margin: 0 }}>
                Multi-Tenant Admin
              </h1>
              <p style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.875rem', margin: 0 }}>
                Sistema de Gestión Multi-Tenant
              </p>
            </div>
          </div>
          
          {/* Información del estado en la parte derecha del header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ color: 'white', fontSize: '0.875rem', fontWeight: '500' }}>
                {selectedCompany?.company_name || 'Sin empresa'}
              </div>
              <div style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.75rem' }}>
                {companies.length} empresa{companies.length !== 1 ? 's' : ''} disponible{companies.length !== 1 ? 's' : ''}
              </div>
            </div>
            <div style={{
              width: '0.75rem',
              height: '0.75rem',
              borderRadius: '50%',
              background: systemStatus.status === 'healthy' || systemStatus.data?.status === 'healthy' 
                ? '#4ade80' 
                : '#ef4444'
            }} title="Estado del sistema"></div>
          </div>
        </div>
      </header>
  
      {/* Contenido principal */}
      <main style={{
        maxWidth: '80rem',
        margin: '0 auto',
        padding: '2rem 1rem'
      }}>
        {/* Selector de empresa */}
        <CompanySelector
          companies={companies}
          selectedCompany={selectedCompany}
          onCompanyChange={handleCompanyChange}
        />
  
        {/* Navegación por tabs */}
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
  
        {/* Contenido según la pestaña activa */}
        {selectedCompany ? (
          <div>
            {renderTabContent()}
          </div>
        ) : (
          <div style={{
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(4px)',
            borderRadius: '0.75rem',
            padding: '2rem',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '3.75rem', color: '#9ca3af', marginBottom: '1rem' }}>🏢</div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#1f2937', marginBottom: '0.5rem' }}>
              Selecciona una Empresa
            </h3>
            <p style={{ color: '#4b5563' }}>
              Elige una empresa para acceder a las funcionalidades de chat testing, 
              gestión de documentos y administración.
            </p>
            {companies.length === 0 && (
              <div style={{
                marginTop: '1rem',
                padding: '1rem',
                background: '#fef3c7',
                border: '1px solid #fbbf24',
                borderRadius: '0.5rem'
              }}>
                <p style={{ margin: 0, fontSize: '0.875rem', color: '#92400e' }}>
                  ⚠️ No hay empresas configuradas en el sistema.
                </p>
              </div>
            )}
          </div>
        )}
  
        {/* Información del pie de página */}
        <div style={{ marginTop: '3rem', textAlign: 'center' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '1.5rem',
            color: 'rgba(255, 255, 255, 0.7)',
            fontSize: '0.875rem'
          }}>
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
