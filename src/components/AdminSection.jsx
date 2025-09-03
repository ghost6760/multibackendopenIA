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

export default AdminSection;
};

export default AdminSection;
