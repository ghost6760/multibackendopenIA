// src/components/CompanySelector.jsx
import React from 'react';

const CompanySelector = ({ companies, currentCompanyId, onCompanyChange }) => {
  return (
    <div className="flex items-center space-x-4">
      <select
        value={currentCompanyId}
        onChange={(e) => onCompanyChange(e.target.value)}
        className="px-4 py-2 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[200px]"
      >
        <option value="">Seleccionar empresa</option>
        {Object.entries(companies).map(([id, company]) => (
          <option key={id} value={id}>
            {company.company_name || id}
          </option>
        ))}
      </select>
      
      {currentCompanyId && companies[currentCompanyId] && (
        <div className="text-sm text-gray-600">
          <span className="font-medium">
            {companies[currentCompanyId].agents?.length || 0}
          </span> agentes activos
        </div>
      )}
    </div>
  );
};

export default CompanySelector;
