// src/index.js - Punto de entrada principal de React corregido
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// Service Worker para PWA (opcional)
import * as serviceWorkerRegistration from './serviceWorkerRegistration';

// Reportar métricas web vitals (opcional)
import reportWebVitals from './reportWebVitals';

// Configuración global de errores
const originalError = console.error;
console.error = (...args) => {
  // Log estructurado para debugging en producción
  if (window.location.hostname.includes('railway')) {
    const errorInfo = {
      timestamp: new Date().toISOString(),
      level: 'ERROR',
      message: args.join(' '),
      url: window.location.href,
      userAgent: navigator.userAgent
    };
    console.log('🚨 FRONTEND_ERROR:', JSON.stringify(errorInfo));
  }
  originalError.apply(console, args);
};

// Crear root de React
const container = document.getElementById('root');
const root = ReactDOM.createRoot(container);

// Renderizar aplicación con manejo de errores
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);

// Error Boundary component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Log error para debugging
    console.error('🚨 React Error Boundary:', {
      error: error.message,
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
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          fontFamily: 'Inter, sans-serif'
        }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            borderRadius: '16px',
            padding: '2rem',
            maxWidth: '500px',
            margin: '1rem',
            textAlign: 'center',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>💥</div>
            <h1 style={{ 
              color: '#1f2937', 
              marginBottom: '1rem',
              fontSize: '1.5rem',
              fontWeight: '600'
            }}>
              Error en la Aplicación
            </h1>
            <p style={{ 
              color: '#6b7280', 
              marginBottom: '1.5rem',
              lineHeight: '1.6'
            }}>
              Algo salió mal. Por favor recarga la página o contacta al soporte técnico.
            </p>
            
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => window.location.reload()}
                style={{
                  background: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s'
                }}
                onMouseOver={(e) => e.target.style.background = '#2563eb'}
                onMouseOut={(e) => e.target.style.background = '#3b82f6'}
              >
                🔄 Recargar Página
              </button>
              
              <button
                onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
                style={{
                  background: '#f3f4f6',
                  color: '#374151',
                  border: '1px solid #d1d5db',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s'
                }}
                onMouseOver={(e) => e.target.style.background = '#e5e7eb'}
                onMouseOut={(e) => e.target.style.background = '#f3f4f6'}
              >
                ↩️ Intentar de Nuevo
              </button>
            </div>

            {/* Debug info para desarrollo */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details style={{ 
                marginTop: '1.5rem', 
                textAlign: 'left',
                background: '#f9fafb',
                padding: '1rem',
                borderRadius: '0.5rem',
                fontSize: '0.75rem'
              }}>
                <summary style={{ 
                  cursor: 'pointer', 
                  fontWeight: '500',
                  color: '#374151',
                  marginBottom: '0.5rem'
                }}>
                  🔧 Debug Info (Solo Desarrollo)
                </summary>
                <div style={{ color: '#6b7280' }}>
                  <strong>Error:</strong> {this.state.error.message}<br/>
                  <strong>Stack:</strong><br/>
                  <pre style={{ 
                    whiteSpace: 'pre-wrap', 
                    fontSize: '0.6rem',
                    marginTop: '0.25rem',
                    maxHeight: '100px',
                    overflow: 'auto'
                  }}>
                    {this.state.error.stack}
                  </pre>
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Service Worker registration
serviceWorkerRegistration.register({
  onSuccess: (registration) => {
    console.log('✅ Service Worker registered successfully:', registration);
  },
  onUpdate: (registration) => {
    console.log('🔄 Service Worker update available:', registration);
    if (window.confirm('Nueva versión disponible. ¿Recargar la aplicación?')) {
      window.location.reload();
    }
  }
});

// Web Vitals reporting
reportWebVitals((metric) => {
  // Solo en desarrollo o si se configuran analytics
  if (process.env.NODE_ENV === 'development') {
    console.log('📊 Web Vital:', metric);
  }
  
  // Enviar a analytics si está configurado
  if (window.gtag) {
    window.gtag('event', metric.name, {
      event_category: 'Web Vitals',
      value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
      event_label: metric.id,
      non_interaction: true,
    });
  }
});

// Ocultar splash screen inicial
const initialLoading = document.getElementById('initial-loading');
if (initialLoading) {
  setTimeout(() => {
    initialLoading.style.opacity = '0';
    initialLoading.style.transition = 'opacity 0.5s ease-out';
    setTimeout(() => {
      initialLoading.style.display = 'none';
    }, 500);
  }, 1000);
}
