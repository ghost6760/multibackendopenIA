// src/components/LoadingOverlay.jsx
import React from 'react';

const LoadingOverlay = ({ isVisible, message = 'Cargando...' }) => {
  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 flex items-center space-x-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="text-gray-700">{message}</span>
      </div>
    </div>
  );
};

export default LoadingOverlay;

// src/components/ToastContainer.jsx  
import React from 'react';

const ToastContainer = ({ toasts, onHide }) => {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`p-4 rounded-lg shadow-lg ${
            toast.type === 'success' ? 'bg-green-100 text-green-800' :
            toast.type === 'error' ? 'bg-red-100 text-red-800' :
            toast.type === 'warning' ? 'bg-yellow-100 text-yellow-800' :
            'bg-blue-100 text-blue-800'
          }`}
        >
          <div className="flex justify-between items-center">
            <span>{toast.message}</span>
            <button
              onClick={() => onHide(toast.id)}
              className="ml-4 text-gray-500 hover:text-gray-700"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ToastContainer;

// src/components/TabNavigation.jsx
import React from 'react';

const TabNavigation = ({ activeTab, tabs, onTabChange }) => {
  return (
    <nav className="flex space-x-8 border-b">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
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
  );
};

export default TabNavigation;

// src/components/CompanySelector.jsx
import React from 'react';

const CompanySelector = ({ companies, currentCompanyId, onChange }) => {
  return (
    <div className="flex items-center space-x-4">
      <label htmlFor="company-select" className="text-sm font-medium text-gray-700">
        Empresa:
      </label>
      <select
        id="company-select"
        value={currentCompanyId}
        onChange={(e) => onChange(e.target.value)}
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
  );
};

export default CompanySelector;

// src/components/ChatMessage.jsx
import React from 'react';

const ChatMessage = ({ message, isUser, timestamp }) => {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-800'
        }`}
      >
        <p className="whitespace-pre-wrap">{message}</p>
        <p
          className={`text-xs mt-1 ${
            isUser ? 'text-blue-200' : 'text-gray-500'
          }`}
        >
          {timestamp}
        </p>
      </div>
    </div>
  );
};

export default ChatMessage;

// src/components/AdminSection.jsx
import React from 'react';

const AdminSection = ({ systemHealth, companies, onRefresh }) => {
  return (
    <div className="space-y-6">
      <div className="bg-white/90 backdrop-blur rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">Estado del Sistema</h2>
        
        {systemHealth ? (
          <div className="space-y-4">
            <div className={`p-4 rounded-lg ${
              systemHealth.status === 'healthy' 
                ? 'bg-green-50 border border-green-200' 
                : 'bg-red-50 border border-red-200'
            }`}>
              <h3 className="font-semibold">
                Estado General: {systemHealth.status?.toUpperCase()}
              </h3>
              <p className="text-sm text-gray-600">
                Última actualización: {new Date(systemHealth.timestamp).toLocaleString('es-ES')}
              </p>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">⚙️</div>
            <p>Estado del sistema no disponible</p>
          </div>
        )}

        <button
          onClick={onRefresh}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Actualizar Estado
        </button>
      </div>

      {/* Companies Info */}
      <div className="bg-white/90 backdrop-blur rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Empresas Configuradas</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.values(companies).map((company) => (
            <div
              key={company.company_id}
              className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <h4 className="font-medium text-gray-800">{company.company_name}</h4>
              <p className="text-sm text-gray-600">ID: {company.company_id}</p>
              {company.description && (
                <p className="text-sm text-gray-700 mt-1">{company.description}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AdminSection;
