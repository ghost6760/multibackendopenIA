// src/index.js - Punto de entrada completo con todas las funcionalidades
import React from 'react';
import ReactDOM from 'react-dom/client';

// Importar CSS base ANTES que cualquier componente
import './styles/globals.css';

// Error boundary mejorado
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('🚨 React Application Error:', {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString()
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
          fontFamily: 'system-ui, sans-serif'
        }}>
          <div style={{
            background: 'white',
            color: '#1f2937',
            padding: '2rem',
            borderRadius: '0.75rem',
            maxWidth: '500px',
            textAlign: 'center',
            margin: '1rem'
          }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>
              Error de Aplicación
            </h2>
            <p style={{ marginBottom: '1rem', color: '#6b7280' }}>
              La aplicación encontró un error inesperado.
            </p>
            <details style={{ textAlign: 'left', marginBottom: '1.5rem' }}>
              <summary style={{ cursor: 'pointer', marginBottom: '0.5rem' }}>
                Ver detalles del error
              </summary>
              <pre style={{
                background: '#f3f4f6',
                padding: '1rem',
                borderRadius: '0.5rem',
                fontSize: '0.8rem',
                overflow: 'auto',
                maxHeight: '200px'
              }}>
                {this.state.error?.message}
                {'\n\n'}
                {this.state.error?.stack}
              </pre>
            </details>
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
              🔄 Recargar Aplicación
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Importar el componente App completo con manejo de errores
let App;

try {
  // Intentar cargar el App completo
  App = require('./App').default;
  console.log('✅ App completo cargado exitosamente');
} catch (error) {
  console.error('❌ Error cargando App completo:', error);
  
  // Fallback: App simplificado si hay problemas
  App = function SimpleApp() {
    const [debugInfo, setDebugInfo] = React.useState(null);
    const [systemInfo, setSystemInfo] = React.useState(null);

    React.useEffect(() => {
      // Cargar información del sistema
      fetch('/api/system/info')
        .then(res => res.json())
        .then(data => {
          setSystemInfo(data);
          console.log('✅ System info loaded:', data);
        })
        .catch(err => {
          console.error('❌ Error loading system info:', err);
        });

      // Cargar información de debug
      fetch('/debug/build-structure')
        .then(res => res.json())
        .then(data => {
          setDebugInfo(data);
          console.log('✅ Debug info loaded:', data);
        })
        .catch(err => {
          console.error('❌ Error loading debug info:', err);
        });
    }, []);

    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'system-ui, sans-serif',
        padding: '1rem'
      }}>
        <div style={{
          background: 'white',
          padding: '2rem',
          borderRadius: '1rem',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
          maxWidth: '800px',
          width: '100%'
        }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <div style={{
              width: '60px',
              height: '60px',
              background: 'linear-gradient(135deg, #667eea, #764ba2)',
              borderRadius: '50%',
              margin: '0 auto 1rem',
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
              marginBottom: '0.5rem'
            }}>
              Multi-Tenant Admin
            </h1>
            
            <p style={{
              color: '#6b7280',
              marginBottom: '1rem'
            }}>
              Modo de recuperación - App completo no disponible
            </p>
          </div>

          <div style={{ marginBottom: '2rem' }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: '#1f2937' }}>
              🔧 Información del Sistema
            </h3>
            
            {systemInfo ? (
              <div style={{
                background: '#f3f4f6',
                padding: '1rem',
                borderRadius: '0.5rem',
                fontSize: '0.9rem'
              }}>
                <div style={{ marginBottom: '0.5rem' }}>
                  <strong>Estado:</strong> {systemInfo.status}
                </div>
                <div style={{ marginBottom: '0.5rem' }}>
                  <strong>Empresas configuradas:</strong> {systemInfo.companies_configured || 'N/A'}
                </div>
                <div style={{ marginBottom: '0.5rem' }}>
                  <strong>Frontend Build:</strong> {systemInfo.frontend_build?.exists ? '✅ Existe' : '❌ No existe'}
                </div>
                <div>
                  <strong>Funcionalidades:</strong> {systemInfo.features?.join(', ') || 'N/A'}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '1rem' }}>
                <div style={{
                  width: '30px',
                  height: '30px',
                  border: '3px solid #f3f4f6',
                  borderTop: '3px solid #3b82f6',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                  margin: '0 auto'
                }}></div>
                <p style={{ marginTop: '0.5rem', color: '#6b7280' }}>Cargando...</p>
              </div>
            )}
          </div>

          <div style={{
            display: 'flex',
            gap: '1rem',
            justifyContent: 'center',
            flexWrap: 'wrap',
            marginBottom: '1.5rem'
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
                fontSize: '0.9rem'
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
                fontSize: '0.9rem'
              }}
            >
              🔧 Debug Info
            </a>

            <a
              href="/api/health/full"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                background: '#8b5cf6',
                color: 'white',
                padding: '0.75rem 1.5rem',
                borderRadius: '0.5rem',
                textDecoration: 'none',
                fontWeight: '500',
                fontSize: '0.9rem'
              }}
            >
              💚 Health Check
            </a>
          </div>

          <div style={{
            background: '#fef3c7',
            border: '1px solid #fbbf24',
            borderRadius: '0.5rem',
            padding: '1rem',
            textAlign: 'center'
          }}>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#92400e' }}>
              ⚠️ <strong>Modo de Recuperación:</strong> El App completo con chat testing, gestión de documentos y panel admin no está disponible. 
              Verifica que todos los componentes estén correctamente importados.
            </p>
          </div>
        </div>

        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  };
}

// Función de inicialización
function initializeApp() {
  console.log('🚀 Initializing Multi-Tenant React App...');
  
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
    
    // Fallback completo si todo falla
    document.body.innerHTML = `
      <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; font-family: system-ui; text-align: center; padding: 2rem;">
        <div style="max-width: 500px;">
          <h1 style="font-size: 2rem; margin-bottom: 1rem;">⚠️ Error Crítico</h1>
          <p style="margin-bottom: 1rem; opacity: 0.9;">No se pudo inicializar la aplicación React.</p>
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

// Global error handlers
window.addEventListener('error', (event) => {
  console.error('🚨 Global JavaScript Error:', {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    timestamp: new Date().toISOString()
  });
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('🚨 Unhandled Promise Rejection:', {
    reason: event.reason,
    timestamp: new Date().toISOString()
  });
});
