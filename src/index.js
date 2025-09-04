// src/index.js - Punto de entrada simplificado y robusto
import React from 'react';
import ReactDOM from 'react-dom/client';

// Importar CSS base ANTES que cualquier componente
import './styles/globals.css';

// Error boundary simplificado
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('🚨 React Application Error:', {
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
      url: window.location.href
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #ef4444, #dc2626)',
          color: 'white',
          fontFamily: 'system-ui, sans-serif',
          textAlign: 'center',
          padding: '2rem'
        }}>
          <div style={{
            background: 'white',
            color: '#1f2937',
            padding: '2rem',
            borderRadius: '0.75rem',
            maxWidth: '400px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
          }}>
            <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem', fontWeight: 'bold' }}>
              Error de Aplicación
            </h2>
            <p style={{ marginBottom: '1.5rem', color: '#6b7280' }}>
              Hubo un problema al cargar la aplicación.
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                background: '#dc2626',
                color: 'white',
                padding: '0.75rem 1.5rem',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontSize: '1rem'
              }}
            >
              🔄 Recargar
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Componente App simplificado para testing
function App() {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif'
    }}>
      <div style={{
        background: 'white',
        padding: '3rem',
        borderRadius: '1rem',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        textAlign: 'center',
        maxWidth: '500px',
        margin: '1rem'
      }}>
        <div style={{
          width: '60px',
          height: '60px',
          background: 'linear-gradient(135deg, #667eea, #764ba2)',
          borderRadius: '50%',
          margin: '0 auto 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.5rem'
        }}>
          🚀
        </div>
        
        <h1 style={{
          fontSize: '2rem',
          fontWeight: 'bold',
          color: '#1f2937',
          marginBottom: '1rem'
        }}>
          Multi-Tenant Admin
        </h1>
        
        <p style={{
          color: '#6b7280',
          marginBottom: '2rem',
          fontSize: '1.1rem',
          lineHeight: '1.6'
        }}>
          Sistema de Gestión Multi-Tenant
          <br />
          <span style={{ fontSize: '0.9rem' }}>
            Backend Flask + Frontend React
          </span>
        </p>
        
        <div style={{
          display: 'flex',
          gap: '1rem',
          justifyContent: 'center',
          flexWrap: 'wrap'
        }}>
          <a
            href="/api/system/info"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              background: '#3b82f6',
              color: 'white',
              padding: '0.75rem 1.5rem',
              borderRadius: '0.5rem',
              textDecoration: 'none',
              fontWeight: '500',
              fontSize: '0.9rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            📊 System Info
          </a>
          
          <a
            href="/debug/build-structure"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              background: '#10b981',
              color: 'white',
              padding: '0.75rem 1.5rem',
              borderRadius: '0.5rem',
              textDecoration: 'none',
              fontWeight: '500',
              fontSize: '0.9rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            🔧 Debug Info
          </a>
        </div>
        
        <div style={{
          marginTop: '2rem',
          padding: '1rem',
          background: '#f3f4f6',
          borderRadius: '0.5rem',
          fontSize: '0.8rem',
          color: '#6b7280'
        }}>
          <strong>Status:</strong> ✅ React App Loaded Successfully
          <br />
          <strong>Build:</strong> {process.env.NODE_ENV || 'production'}
          <br />
          <strong>Timestamp:</strong> {new Date().toLocaleString()}
        </div>
      </div>
    </div>
  );
}

// Función de inicialización robusta
function initializeApp() {
  console.log('🚀 Starting Multi-Tenant React App...');
  
  try {
    const root = ReactDOM.createRoot(document.getElementById('root'));
    
    root.render(
      <React.StrictMode>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </React.StrictMode>
    );
    
    console.log('✅ React app rendered successfully');
    
    // Ocultar loading screen si existe
    const loadingScreen = document.getElementById('loading-screen');
    if (loadingScreen) {
      setTimeout(() => {
        loadingScreen.style.opacity = '0';
        setTimeout(() => {
          loadingScreen.remove();
          console.log('✅ Loading screen removed');
        }, 300);
      }, 500);
    }
    
  } catch (error) {
    console.error('❌ Failed to initialize React app:', error);
    
    // Fallback manual si React falla
    document.body.innerHTML = `
      <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; font-family: system-ui;">
        <div style="text-align: center; padding: 2rem;">
          <h1 style="font-size: 2rem; margin-bottom: 1rem;">⚠️ Error Crítico</h1>
          <p style="margin-bottom: 1.5rem; opacity: 0.9;">No se pudo inicializar la aplicación React.</p>
          <p style="margin-bottom: 1.5rem; font-size: 0.9rem; opacity: 0.8;">Error: ${error.message}</p>
          <button onclick="window.location.reload()" style="background: white; color: #dc2626; padding: 0.75rem 1.5rem; border: none; border-radius: 0.5rem; font-weight: bold; cursor: pointer; font-size: 1rem;">
            🔄 Recargar Página
          </button>
        </div>
      </div>
    `;
  }
}

// Esperar a que el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}

// Global error handlers para debugging
window.addEventListener('error', (event) => {
  console.error('🚨 Global JavaScript Error:', {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    timestamp: new Date().toISOString(),
    url: window.location.href
  });
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('🚨 Unhandled Promise Rejection:', {
    reason: event.reason,
    timestamp: new Date().toISOString(),
    url: window.location.href
  });
});
