// src/components/AdminSection.jsx
import React from 'react';
import { 
  Settings, Building, MessageSquare, Users, AlertTriangle, 
  Activity, BarChart3, Calendar, Download, Shield, Zap, 
  Database, RefreshCw, Eye 
} from 'lucide-react';

const AdminSection = ({
  currentCompanyId,
  companies,
  conversations,
  setShowConfigModal,
  checkSystemHealth,
  showToast
}) => {
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  const adminActions = [
    {
      title: 'Sistema',
      actions: [
        { 
          id: 'health', 
          label: 'Verificar Salud', 
          icon: Activity, 
          color: 'green', 
          action: checkSystemHealth,
          description: 'Verificar estado de todos los servicios'
        },
        { 
          id: 'stats', 
          label: 'Estadísticas', 
          icon: BarChart3, 
          color: 'blue', 
          action: () => showToast('🚧 Función en desarrollo', 'info'),
          description: 'Ver métricas del sistema'
        },
        { 
          id: 'companies', 
          label: 'Ver Empresas', 
          icon: Building, 
          color: 'purple', 
          action: () => showToast(`📊 ${Object.keys(companies).length} empresas configuradas`, 'info'),
          description: 'Listar todas las empresas'
        }
      ]
    },
    {
      title: 'Configuración',
      actions: [
        { 
          id: 'calendar', 
          label: 'Google Calendar', 
          icon: Calendar, 
          color: 'orange', 
          action: () => setShowConfigModal(true),
          description: 'Configurar integración con Google Calendar'
        },
        { 
          id: 'export', 
          label: 'Exportar Config', 
          icon: Download, 
          color: 'gray', 
          action: () => showToast('🚧 Función en desarrollo', 'info'),
          description: 'Exportar configuración actual'
        },
        { 
          id: 'protection', 
          label: 'Estado Protección', 
          icon: Shield, 
          color: 'green', 
          action: () => showToast('🚧 Función en desarrollo', 'info'),
          description: 'Ver estado de protecciones activas'
        }
      ]
    },
    {
      title: 'Herramientas',
      actions: [
        { 
          id: 'recovery', 
          label: 'Forzar Recovery', 
          icon: Zap, 
          color: 'red', 
          action: () => showToast('🚧 Función en desarrollo', 'info'),
          description: 'Forzar recuperación del vectorstore'
        },
        { 
          id: 'diagnostics', 
          label: 'Diagnósticos', 
          icon: Database, 
          color: 'blue', 
          action: () => showToast('🚧 Función en desarrollo', 'info'),
          description: 'Ejecutar diagnósticos del sistema'
        },
        { 
          id: 'migration', 
          label: 'Migración', 
          icon: RefreshCw, 
          color: 'purple', 
          action: () => showToast('🚧 Función en desarrollo', 'info'),
          description: 'Herramientas de migración de datos'
        }
      ]
    }
  ];

  const getColorClasses = (color) => {
    const colors = {
      green: 'bg-green-600 hover:bg-green-700 border-green-600',
      blue: 'bg-blue-600 hover:bg-blue-700 border-blue-600',
      purple: 'bg-purple-600 hover:bg-purple-700 border-purple-600',
      orange: 'bg-orange-600 hover:bg-orange-700 border-orange-600',
      red: 'bg-red-600 hover:bg-red-700 border-red-600',
      gray: 'bg-gray-600 hover:bg-gray-700 border-gray-600'
    };
    return colors[color] || colors.blue;
  };

  return (
    <div className="space-y-6">
      {/* Información del sistema */}
      <div className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-6 flex items-center">
          <Settings className="h-5 w-5 mr-2" />
          Panel de Administración
        </h3>

        {currentCompanyId ? (
          <>
            {/* Información de la empresa actual */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <div className="flex items-center">
                  <Building className="h-8 w-8 text-blue-600 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-600">Empresa Actual</p>
                    <p className="text-lg font-semibold text-blue-600 truncate">
                      {companies[currentCompanyId]?.company_name || currentCompanyId}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <div className="flex items-center">
                  <MessageSquare className="h-8 w-8 text-green-600 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-600">Conversaciones</p>
                    <p className="text-lg font-semibold text-green-600">
                      {conversations.length}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                <div className="flex items-center">
                  <Users className="h-8 w-8 text-purple-600 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Empresas</p>
                    <p className="text-lg font-semibold text-purple-600">
                      {Object.keys(companies).length}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
                <div className="flex items-center">
                  <Activity className="h-8 w-8 text-orange-600 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-600">Agentes</p>
                    <p className="text-lg font-semibold text-orange-600">
                      {companies[currentCompanyId]?.agents?.length || 0}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Información detallada de la empresa */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">
                Detalles de {companies[currentCompanyId]?.company_name || currentCompanyId}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">ID:</span>
                  <span className="ml-2 font-mono text-gray-800">{currentCompanyId}</span>
                </div>
                <div>
                  <span className="text-gray-600">Tipo de negocio:</span>
                  <span className="ml-2 text-gray-800">
                    {companies[currentCompanyId]?.business_type || 'No especificado'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Agentes disponibles:</span>
                  <span className="ml-2 text-gray-800">
                    {companies[currentCompanyId]?.agents?.join(', ') || 'Ninguno'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Estado:</span>
                  <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                    Activo
                  </span>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
              <p className="text-yellow-800">
                Selecciona una empresa para acceder a todas las funcionalidades administrativas.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Grupos de acciones administrativas */}
      {adminActions.map((group) => (
        <div key={group.title} className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
          <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center">
            🔧 <span className="ml-2">{group.title}</span>
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {group.actions.map((action) => {
              const Icon = action.icon;
              const isDisabled = !currentCompanyId && action.id !== 'health' && action.id !== 'companies';

              return (
                <div key={action.id} className="relative">
                  <button
                    onClick={action.action}
                    disabled={isDisabled}
                    className={`w-full p-4 text-white rounded-lg transition-all duration-200 flex flex-col items-center text-center space-y-2 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 hover:shadow-lg ${
                      getColorClasses(action.color)
                    }`}
                  >
                    <Icon className="h-6 w-6" />
                    <div>
                      <span className="font-medium">{action.label}</span>
                      <p className="text-xs opacity-90 mt-1">
                        {action.description}
                      </p>
                    </div>
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* Lista de conversaciones recientes */}
      {currentCompanyId && conversations.length > 0 && (
        <div className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
          <div className="flex justify-between items-center mb-4">
            <h4 className="text-md font-semibold text-gray-800 flex items-center">
              💬 <span className="ml-2">Conversaciones Recientes</span>
            </h4>
            <span className="text-sm text-gray-500">
              Últimas {Math.min(conversations.length, 10)} conversaciones
            </span>
          </div>

          <div className="space-y-3 max-h-96 overflow-y-auto">
            {conversations.slice(0, 10).map((conv, index) => (
              <div key={conv.id || index} 
                   className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <MessageSquare className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        Usuario: {conv.user_id || 'Desconocido'}
                      </p>
                      <div className="flex items-center space-x-4 text-xs text-gray-500 mt-1">
                        <span>Mensajes: {conv.message_count || 0}</span>
                        <span>Última actividad: {formatDate(conv.last_activity)}</span>
                        <span className="px-2 py-1 bg-gray-200 rounded-full">
                          {conv.status || 'Activa'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => showToast(`🔍 Ver conversación ${conv.id || index + 1}`, 'info')}
                  className="ml-4 p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="Ver detalles"
                >
                  <Eye className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>

          {conversations.length === 0 && (
            <div className="text-center py-8">
              <MessageSquare className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">No hay conversaciones recientes</p>
            </div>
          )}
        </div>
      )}

      {/* Información adicional del sistema */}
      <div className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
        <h4 className="text-md font-semibold text-gray-800 mb-4">
          ℹ️ Información del Sistema
        </h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <p><span className="font-medium">Versión:</span> Multi-Tenant v1.0.0</p>
            <p><span className="font-medium">Entorno:</span> Production (Railway)</p>
            <p><span className="font-medium">Base de datos:</span> Redis + ChromaDB</p>
          </div>
          <div className="space-y-2">
            <p><span className="font-medium">Modelo IA:</span> GPT-4o-mini</p>
            <p><span className="font-medium">Embeddings:</span> text-embedding-3-small</p>
            <p><span className="font-medium">Última actualización:</span> {formatDate(new Date())}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminSection;
